"""
Система кэширования для BQuant

Модуль предоставляет различные стратегии кэширования для оптимизации производительности
расчетов индикаторов и анализа данных.
"""

import hashlib
import pickle
import time
from typing import Any, Dict, Optional, Callable, Union, Tuple
from functools import wraps
from pathlib import Path
import pandas as pd
import numpy as np
from dataclasses import dataclass
from datetime import datetime, timedelta

from .logging_config import get_logger
from .config import get_cache_config

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """
    Запись в кэше.
    
    Attributes:
        data: Кэшированные данные
        timestamp: Время создания записи
        hits: Количество обращений к записи
        expiry: Время истечения записи (None = не истекает)
        size_bytes: Размер данных в байтах
        metadata: Дополнительные метаданные
    """
    data: Any
    timestamp: datetime
    hits: int = 0
    expiry: Optional[datetime] = None
    size_bytes: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # Приблизительный расчет размера
        if self.size_bytes == 0:
            self.size_bytes = self._estimate_size()
    
    def _estimate_size(self) -> int:
        """Приблизительная оценка размера данных."""
        try:
            if isinstance(self.data, pd.DataFrame):
                return self.data.memory_usage(deep=True).sum()
            elif isinstance(self.data, pd.Series):
                return self.data.memory_usage(deep=True)
            elif isinstance(self.data, np.ndarray):
                return self.data.nbytes
            else:
                return len(pickle.dumps(self.data))
        except Exception:
            return 1024  # Fallback размер
    
    def is_expired(self) -> bool:
        """Проверяет, истекла ли запись."""
        if self.expiry is None:
            return False
        return datetime.now() > self.expiry
    
    def touch(self):
        """Обновляет счетчик обращений."""
        self.hits += 1


class MemoryCache:
    """
    Кэш в памяти с поддержкой TTL и LRU эвикции.
    """
    
    def __init__(self, max_size: int = 100, default_ttl: int = 3600):
        """
        Инициализация кэша.
        
        Args:
            max_size: Максимальное количество записей
            default_ttl: Время жизни записи по умолчанию (секунды)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []
        self.logger = get_logger(f"{__name__}.MemoryCache")
        
        # Статистика
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Генерирует ключ кэша на основе функции и аргументов."""
        # Создаем строку для хэширования
        key_parts = [func_name]
        
        # Добавляем args
        for arg in args:
            if isinstance(arg, pd.DataFrame):
                # Для DataFrame используем хэш данных
                key_parts.append(pd.util.hash_pandas_object(arg).sum())
            elif isinstance(arg, (pd.Series, np.ndarray)):
                key_parts.append(str(hash(arg.tobytes() if hasattr(arg, 'tobytes') else str(arg))))
            else:
                key_parts.append(str(hash(str(arg))))
        
        # Добавляем kwargs
        sorted_kwargs = sorted(kwargs.items())
        for k, v in sorted_kwargs:
            key_parts.append(f"{k}={hash(str(v))}")
        
        # Создаем хэш
        key_string = "|".join(str(part) for part in key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша."""
        if key not in self._cache:
            self._misses += 1
            return None
        
        entry = self._cache[key]
        
        # Проверяем истечение
        if entry.is_expired():
            self.logger.debug(f"Cache entry expired: {key}")
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            self._misses += 1
            return None
        
        # Обновляем статистику и порядок доступа
        entry.touch()
        self._hits += 1
        
        # Перемещаем в конец списка (LRU)
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        self.logger.debug(f"Cache hit: {key}")
        return entry.data
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Сохранить значение в кэше."""
        # Определяем время истечения
        expiry = None
        if ttl is not None or self.default_ttl > 0:
            ttl_seconds = ttl if ttl is not None else self.default_ttl
            expiry = datetime.now() + timedelta(seconds=ttl_seconds)
        
        # Создаем запись
        entry = CacheEntry(
            data=value,
            timestamp=datetime.now(),
            expiry=expiry
        )
        
        # Проверяем, нужна ли эвикция
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_lru()
        
        # Сохраняем запись
        self._cache[key] = entry
        
        # Обновляем порядок доступа
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        self.logger.debug(f"Cache put: {key}, expires: {expiry}")
    
    def _evict_lru(self) -> None:
        """Удаляет наименее недавно использованную запись."""
        if not self._access_order:
            return
        
        lru_key = self._access_order[0]
        del self._cache[lru_key]
        self._access_order.remove(lru_key)
        self._evictions += 1
        
        self.logger.debug(f"Evicted LRU entry: {lru_key}")
    
    def invalidate(self, key: str) -> bool:
        """Удалить запись из кэша."""
        if key in self._cache:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            self.logger.debug(f"Invalidated cache entry: {key}")
            return True
        return False
    
    def clear(self) -> None:
        """Очистить весь кэш."""
        count = len(self._cache)
        self._cache.clear()
        self._access_order.clear()
        self.logger.info(f"Cleared cache: {count} entries removed")
    
    def cleanup_expired(self) -> int:
        """Удалить истекшие записи."""
        expired_keys = []
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            self.invalidate(key)
        
        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired entries")
        
        return len(expired_keys)
    
    def stats(self) -> Dict[str, Any]:
        """Получить статистику кэша."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        total_size = sum(entry.size_bytes for entry in self._cache.values())
        
        return {
            'entries': len(self._cache),
            'max_size': self.max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': hit_rate,
            'evictions': self._evictions,
            'total_size_bytes': total_size,
            'avg_size_bytes': total_size / len(self._cache) if self._cache else 0
        }


class DiskCache:
    """
    Кэш на диске для долгосрочного хранения результатов.
    """
    
    def __init__(self, cache_dir: Union[str, Path] = None):
        """
        Инициализация дискового кэша.
        
        Args:
            cache_dir: Директория для кэша (по умолчанию .cache/bquant)
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "bquant"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = get_logger(f"{__name__}.DiskCache")
        self.logger.info(f"Disk cache initialized: {self.cache_dir}")
    
    def _get_file_path(self, key: str) -> Path:
        """Получить путь к файлу кэша."""
        return self.cache_dir / f"{key}.pkl"
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из дискового кэша."""
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'rb') as f:
                entry = pickle.load(f)
            
            if entry.is_expired():
                file_path.unlink()
                return None
            
            entry.touch()
            return entry.data
            
        except Exception as e:
            self.logger.warning(f"Failed to load from disk cache {key}: {e}")
            # Удаляем поврежденный файл
            if file_path.exists():
                file_path.unlink()
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Сохранить значение в дисковый кэш."""
        file_path = self._get_file_path(key)
        
        # Определяем время истечения
        expiry = None
        if ttl is not None:
            expiry = datetime.now() + timedelta(seconds=ttl)
        
        # Создаем запись
        entry = CacheEntry(
            data=value,
            timestamp=datetime.now(),
            expiry=expiry
        )
        
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(entry, f)
            
            self.logger.debug(f"Saved to disk cache: {key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save to disk cache {key}: {e}")
            return False
    
    def invalidate(self, key: str) -> bool:
        """Удалить файл из дискового кэша."""
        file_path = self._get_file_path(key)
        
        if file_path.exists():
            file_path.unlink()
            self.logger.debug(f"Removed from disk cache: {key}")
            return True
        return False
    
    def clear(self) -> int:
        """Очистить весь дисковый кэш."""
        count = 0
        for file_path in self.cache_dir.glob("*.pkl"):
            file_path.unlink()
            count += 1
        
        self.logger.info(f"Cleared disk cache: {count} files removed")
        return count
    
    def cleanup_expired(self) -> int:
        """Удалить истекшие файлы."""
        expired_count = 0
        
        for file_path in self.cache_dir.glob("*.pkl"):
            try:
                with open(file_path, 'rb') as f:
                    entry = pickle.load(f)
                
                if entry.is_expired():
                    file_path.unlink()
                    expired_count += 1
                    
            except Exception:
                # Удаляем поврежденные файлы
                file_path.unlink()
                expired_count += 1
        
        if expired_count > 0:
            self.logger.info(f"Cleaned up {expired_count} expired disk cache entries")
        
        return expired_count


class CacheManager:
    """
    Менеджер кэширования, объединяющий память и диск.
    """
    
    def __init__(self, memory_size: int = 100, disk_cache: bool = True):
        """
        Инициализация менеджера кэша.
        
        Args:
            memory_size: Размер кэша в памяти
            disk_cache: Использовать ли дисковый кэш
        """
        self.memory_cache = MemoryCache(max_size=memory_size)
        self.disk_cache = DiskCache() if disk_cache else None
        self.logger = get_logger(f"{__name__}.CacheManager")
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша (сначала память, потом диск)."""
        # Сначала проверяем память
        result = self.memory_cache.get(key)
        if result is not None:
            return result
        
        # Потом диск
        if self.disk_cache:
            result = self.disk_cache.get(key)
            if result is not None:
                # Сохраняем в память для быстрого доступа
                self.memory_cache.put(key, result)
                return result
        
        return None
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None, disk: bool = True) -> None:
        """Сохранить значение в кэш."""
        # Всегда сохраняем в память
        self.memory_cache.put(key, value, ttl)
        
        # Сохраняем на диск если разрешено
        if disk and self.disk_cache:
            self.disk_cache.put(key, value, ttl)
    
    def invalidate(self, key: str) -> None:
        """Удалить из всех кэшей."""
        self.memory_cache.invalidate(key)
        if self.disk_cache:
            self.disk_cache.invalidate(key)
    
    def clear(self) -> None:
        """Очистить все кэши."""
        self.memory_cache.clear()
        if self.disk_cache:
            self.disk_cache.clear()
    
    def cleanup(self) -> Dict[str, int]:
        """Очистить истекшие записи."""
        memory_cleaned = self.memory_cache.cleanup_expired()
        disk_cleaned = self.disk_cache.cleanup_expired() if self.disk_cache else 0
        
        return {
            'memory_cleaned': memory_cleaned,
            'disk_cleaned': disk_cleaned
        }
    
    def stats(self) -> Dict[str, Any]:
        """Получить общую статистику."""
        stats = {
            'memory': self.memory_cache.stats()
        }
        
        if self.disk_cache:
            disk_files = len(list(self.disk_cache.cache_dir.glob("*.pkl")))
            stats['disk'] = {
                'entries': disk_files,
                'cache_dir': str(self.disk_cache.cache_dir)
            }
        
        return stats


# Глобальный менеджер кэша
_global_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Получить глобальный менеджер кэша."""
    global _global_cache_manager
    
    if _global_cache_manager is None:
        cache_config = get_cache_config()
        _global_cache_manager = CacheManager(
            memory_size=cache_config.get('memory_size', 100),
            disk_cache=cache_config.get('enable_disk_cache', True)
        )
    
    return _global_cache_manager


def cached(ttl: Optional[int] = None, disk: bool = True, key_prefix: str = ""):
    """
    Декоратор для кэширования результатов функций.
    
    Args:
        ttl: Время жизни кэша в секундах
        disk: Сохранять ли на диск
        key_prefix: Префикс для ключа кэша
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            
            # Генерируем ключ
            func_name = f"{key_prefix}{func.__module__}.{func.__name__}"
            key = cache_manager.memory_cache._generate_key(func_name, args, kwargs)
            
            # Проверяем кэш
            result = cache_manager.get(key)
            if result is not None:
                logger.debug(f"Cache hit for {func_name}")
                return result
            
            # Вычисляем результат
            logger.debug(f"Cache miss for {func_name}, calculating...")
            result = func(*args, **kwargs)
            
            # Сохраняем в кэш
            cache_manager.put(key, result, ttl, disk)
            
            return result
        
        return wrapper
    return decorator


def cache_key(*args, **kwargs) -> str:
    """Генерирует ключ кэша для заданных аргументов."""
    cache_manager = get_cache_manager()
    return cache_manager.memory_cache._generate_key("manual_key", args, kwargs)


def clear_cache():
    """Очистить глобальный кэш."""
    global _global_cache_manager
    if _global_cache_manager:
        _global_cache_manager.clear()


def cache_stats() -> Dict[str, Any]:
    """Получить статистику глобального кэша."""
    cache_manager = get_cache_manager()
    return cache_manager.stats()


# Экспорт
__all__ = [
    'CacheEntry',
    'MemoryCache',
    'DiskCache', 
    'CacheManager',
    'get_cache_manager',
    'cached',
    'cache_key',
    'clear_cache',
    'cache_stats'
]
