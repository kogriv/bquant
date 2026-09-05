"""
Модуль оптимизации производительности для BQuant

Содержит инструменты для профилирования, мониторинга и оптимизации производительности.
"""

import time
import functools
import threading
from typing import Dict, Any, Callable, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import psutil
import os
from contextlib import contextmanager

from .logging_config import get_logger
from .cache import get_cache_manager, cached

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """
    Метрики производительности.
    
    Attributes:
        function_name: Имя функции
        execution_time: Время выполнения в секундах
        memory_before: Использование памяти до выполнения (MB)
        memory_after: Использование памяти после выполнения (MB) 
        memory_peak: Пиковое использование памяти (MB)
        cpu_percent: Использование CPU (%)
        call_count: Количество вызовов
        timestamp: Время измерения
    """
    function_name: str
    execution_time: float
    memory_before: float
    memory_after: float
    memory_peak: float
    cpu_percent: float
    call_count: int = 1
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class PerformanceMonitor:
    """
    Монитор производительности для отслеживания метрик функций.
    """
    
    def __init__(self):
        self.metrics: Dict[str, List[PerformanceMetrics]] = {}
        self.lock = threading.RLock()
        self.process = psutil.Process(os.getpid())
        self.logger = get_logger(f"{__name__}.PerformanceMonitor")
    
    def record(self, metrics: PerformanceMetrics):
        """Записать метрики."""
        with self.lock:
            if metrics.function_name not in self.metrics:
                self.metrics[metrics.function_name] = []
            self.metrics[metrics.function_name].append(metrics)
    
    def get_stats(self, function_name: str = None) -> Dict[str, Any]:
        """
        Получить статистику производительности.
        
        Args:
            function_name: Имя функции (None для всех)
        
        Returns:
            Словарь со статистикой
        """
        with self.lock:
            if function_name:
                if function_name not in self.metrics:
                    return {}
                data = self.metrics[function_name]
                return self._calculate_stats(function_name, data)
            else:
                stats = {}
                for name, data in self.metrics.items():
                    stats[name] = self._calculate_stats(name, data)
                return stats
    
    def _calculate_stats(self, name: str, data: List[PerformanceMetrics]) -> Dict[str, Any]:
        """Рассчитать статистику для функции."""
        if not data:
            return {}
        
        times = [m.execution_time for m in data]
        memory_deltas = [m.memory_after - m.memory_before for m in data]
        cpu_usage = [m.cpu_percent for m in data]
        
        return {
            'function_name': name,
            'call_count': len(data),
            'total_time': sum(times),
            'avg_time': np.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'std_time': np.std(times),
            'avg_memory_delta': np.mean(memory_deltas),
            'max_memory_delta': max(memory_deltas),
            'avg_cpu_percent': np.mean(cpu_usage),
            'max_cpu_percent': max(cpu_usage),
            'last_call': data[-1].timestamp
        }
    
    def clear_stats(self, function_name: str = None):
        """Очистить статистику."""
        with self.lock:
            if function_name:
                if function_name in self.metrics:
                    del self.metrics[function_name]
            else:
                self.metrics.clear()
    
    def export_stats(self, file_path: str = None) -> pd.DataFrame:
        """
        Экспортировать статистику в DataFrame.
        
        Args:
            file_path: Путь для сохранения CSV (optional)
        
        Returns:
            DataFrame со статистикой
        """
        stats = self.get_stats()
        if not stats:
            return pd.DataFrame()
        
        df = pd.DataFrame(stats.values())
        
        if file_path:
            df.to_csv(file_path, index=False)
            self.logger.info(f"Performance stats exported to {file_path}")
        
        return df


# Глобальный монитор производительности
_global_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Получить глобальный монитор производительности."""
    return _global_monitor


def performance_monitor(func: Optional[Callable] = None, *, enable_cpu: bool = True,
                        enable_memory: bool = True):
    """
    Декоратор для мониторинга производительности функций.

    Принимает обе формы записи:

    ``@performance_monitor`` — без скобок, и ``@performance_monitor()`` — со
    скобками. До 2026-09-01 работала только вторая, а первая **молча ломала
    функцию**: декоратор без скобок получал саму функцию вместо флага, и
    декорированное имя начинало возвращать внутренний ``wrapper`` вместо
    результата. Ни исключения, ни предупреждения — вызов возвращал объект, у
    которого правильный вид (G43). Форма без скобок при этом стояла в
    инструкции проекта (`AGENTS.md`) как рекомендуемый образец.

    Args:
        func: декорируемая функция при записи без скобок
        enable_cpu: мониторить CPU usage
        enable_memory: мониторить memory usage
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            process = monitor.process
            
            # Измерения до выполнения
            memory_before = process.memory_info().rss / 1024 / 1024 if enable_memory else 0
            cpu_before = process.cpu_percent() if enable_cpu else 0
            
            start_time = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                
                # Измерения после выполнения
                end_time = time.perf_counter()
                execution_time = end_time - start_time
                
                memory_after = process.memory_info().rss / 1024 / 1024 if enable_memory else 0
                cpu_after = process.cpu_percent() if enable_cpu else 0
                
                # Создаем метрики
                metrics = PerformanceMetrics(
                    function_name=f"{func.__module__}.{func.__name__}",
                    execution_time=execution_time,
                    memory_before=memory_before,
                    memory_after=memory_after,
                    memory_peak=max(memory_before, memory_after),
                    cpu_percent=max(cpu_before, cpu_after)
                )
                
                # Записываем метрики
                monitor.record(metrics)
                
                return result
                
            except Exception as e:
                logger.error(f"Performance monitoring failed for {func.__name__}: {e}")
                raise

        return wrapper

    if func is not None:
        if not callable(func):
            raise TypeError(
                "performance_monitor: first argument must be the decorated function. "
                "Pass enable_cpu/enable_memory by keyword: @performance_monitor(enable_cpu=False)"
            )
        return decorator(func)
    return decorator


@contextmanager
def performance_context(name: str):
    """
    Контекстный менеджер для измерения производительности блока кода.
    
    Args:
        name: Имя операции
    """
    monitor = get_performance_monitor()
    process = monitor.process
    
    memory_before = process.memory_info().rss / 1024 / 1024
    start_time = time.perf_counter()
    
    try:
        yield
    finally:
        end_time = time.perf_counter()
        memory_after = process.memory_info().rss / 1024 / 1024
        
        metrics = PerformanceMetrics(
            function_name=name,
            execution_time=end_time - start_time,
            memory_before=memory_before,
            memory_after=memory_after,
            memory_peak=memory_after,
            cpu_percent=0  # CPU не измеряем в контексте
        )
        
        monitor.record(metrics)


# Оптимизированные NumPy функции для индикаторов
def require_period(name: str, value: int) -> int:
    """A period is a positive integer; anything else is refused by name."""
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")
    return int(value)


def require_macd_periods(fast: int, slow: int, signal: int) -> Tuple[int, int, int]:
    """``fast > 0``, ``slow > fast``, ``signal > 0`` — the one check for every MACD.

    Until G58 the optimized MACD accepted ``fast=0`` (a division by one in the
    smoothing factor, not an error) and ``slow <= fast`` (a line with the sign
    flipped), and the custom MACD accepted the latter too.
    """
    fast, slow, signal = (require_period('fast', fast), require_period('slow', slow),
                          require_period('signal', signal))
    if slow <= fast:
        raise ValueError(
            f"slow period must exceed fast period, got fast={fast}, slow={slow}; "
            "with them swapped the MACD line changes sign."
        )
    return fast, slow, signal


def ema_warmup(period: int) -> int:
    """Bars an EMA of ``period`` has not yet filled: ``period - 1``."""
    return period - 1


def macd_warmup(slow: int, signal: int) -> Tuple[int, int]:
    """``(line_warmup, signal_warmup)`` — the contract every MACD publishes under.

    The line waits for the slow EMA (``slow - 1``); the signal line and the
    histogram wait for their own EMA on top of that (``slow + signal - 2``).
    This is what the custom MACD masks (G45); until G58 the optimized MACD
    published from bar 0 under the same name.
    """
    line = ema_warmup(slow)
    return line, line + ema_warmup(signal)


def _ema_raw(prices: np.ndarray, period: int) -> np.ndarray:
    """Recursive EMA over the whole array, no warm-up mask — for internal chaining.

    MACD feeds the line into another EMA and RSI feeds gains and losses into
    one; a masked head would turn into NaN that never recovers, so the pieces
    are chained unmasked and masked once at the end.
    """
    prices = np.asarray(prices, dtype=float)
    if len(prices) == 0:
        return np.array([], dtype=float)
    alpha = 2.0 / (period + 1)
    ema_values = np.empty(len(prices), dtype=float)
    ema_values[0] = prices[0]
    for i in range(1, len(prices)):
        ema_values[i] = alpha * prices[i] + (1 - alpha) * ema_values[i - 1]
    return ema_values


class OptimizedIndicators:
    """
    Оптимизированные реализации популярных индикаторов с использованием NumPy.

    Every method takes ``prices`` as float (G58: ``np.zeros_like`` on an integer
    array used to truncate every EMA value to an integer, and the RSI and MACD
    built on it inherited the loss) and publishes under the same warm-up
    contract as the custom indicators.
    """
    
    @staticmethod
    @cached(ttl=3600, disk=True, key_prefix="opt_")
    @performance_monitor()
    def sma(prices: np.ndarray, period: int) -> np.ndarray:
        """
        Оптимизированная простая скользящая средняя.
        
        Args:
            prices: Массив цен
            period: Период усреднения
        
        Returns:
            Массив SMA значений
        """
        prices = np.asarray(prices, dtype=float)
        period = require_period('period', period)
        if len(prices) < period:
            return np.full(len(prices), np.nan)

        # Окно — хвостовое: значение в точке i считается по prices[i-period+1 : i+1].
        # Было `np.convolve(..., mode='same')`, то есть окно **центрированное** и
        # дополненное нулями с обоих концов: индикатор заглядывал вперёд, а последние
        # period//2 значений усреднялись с нулями и падали почти вдвое — 1597 при
        # ценах около 2900 (G44). `mode='valid'` даёт ровно len-period+1 значений,
        # посчитанных без единого добавленного нуля.
        kernel = np.ones(period) / period
        sma_values = np.full(len(prices), np.nan)
        sma_values[period - 1:] = np.convolve(prices, kernel, mode='valid')

        return sma_values
    
    @staticmethod
    @cached(ttl=3600, disk=True, key_prefix="opt_")
    @performance_monitor()
    def ema(prices: np.ndarray, period: int) -> np.ndarray:
        """
        Оптимизированная экспоненциальная скользящая средняя.
        
        Args:
            prices: Массив цен
            period: Период усреднения
        
        Returns:
            Массив EMA значений
        """
        period = require_period('period', period)
        ema_values = _ema_raw(prices, period)
        # Warm-up: the first `period - 1` values are computed on an unfilled
        # window and are not published — the same contract as the custom EMA.
        ema_values[:ema_warmup(period)] = np.nan
        return ema_values
    
    @staticmethod
    @cached(ttl=3600, disk=True, key_prefix="opt_")
    @performance_monitor()
    def rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """
        Оптимизированный RSI.
        
        Args:
            prices: Массив цен закрытия
            period: Период расчета
        
        Returns:
            Массив RSI значений
        """
        prices = np.asarray(prices, dtype=float)
        period = require_period('period', period)
        if len(prices) < period + 1:
            return np.full(len(prices), np.nan)
        
        # Вычисляем изменения цен
        deltas = np.diff(prices)
        
        # Разделяем на положительные и отрицательные изменения
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Добавляем нулевое значение в начало для соответствия размерности
        gains = np.concatenate(([0], gains))
        losses = np.concatenate(([0], losses))
        
        # Рассчитываем RSI используя EMA для усреднения
        avg_gains = _ema_raw(gains, period)
        avg_losses = _ema_raw(losses, period)
        
        # Деление на ноль — не «ноль», а край шкалы. Раньше здесь стояло
        # `np.where(avg_losses != 0, avg_gains / avg_losses, 0)`: при отсутствии
        # падений RS обнулялся, и строго растущий ряд получал **RSI 0** — отметку
        # предельной перепроданности, ту же, что у строго падающего и у плоского
        # (G44). Плюс обе ветви `np.where` вычисляются, поэтому деление на ноль
        # исполнялось всегда и сыпало RuntimeWarning.
        rsi_values = np.full(len(prices), np.nan)

        both_zero = (avg_gains == 0) & (avg_losses == 0)
        no_losses = (avg_losses == 0) & ~both_zero
        measurable = avg_losses != 0

        rs = np.divide(avg_gains, avg_losses, out=np.zeros_like(avg_gains),
                       where=measurable)
        rsi_values[measurable] = 100 - (100 / (1 + rs[measurable]))
        rsi_values[no_losses] = 100.0
        # Ряд без движения в обе стороны: RSI не определён, и это не 50 и не 0.
        rsi_values[both_zero] = np.nan

        # Устанавливаем NaN для первых period значений
        rsi_values[:period] = np.nan

        return rsi_values
    
    @staticmethod
    @cached(ttl=3600, disk=True, key_prefix="opt_")
    @performance_monitor()
    def macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Оптимизированный MACD.
        
        Args:
            prices: Массив цен закрытия
            fast: Быстрый период
            slow: Медленный период  
            signal: Период сигнальной линии
        
        Returns:
            Кортеж (MACD line, Signal line, Histogram)
        """
        prices = np.asarray(prices, dtype=float)
        fast, slow, signal = require_macd_periods(fast, slow, signal)
        if len(prices) < slow:
            nan_array = np.full(len(prices), np.nan)
            return nan_array, nan_array, nan_array
        
        # EMAs chained unmasked, masked once under the shared contract
        macd_line = _ema_raw(prices, fast) - _ema_raw(prices, slow)
        signal_line = _ema_raw(macd_line, signal)
        histogram = macd_line - signal_line

        line_warmup, signal_warmup = macd_warmup(slow, signal)
        macd_line[:line_warmup] = np.nan
        signal_line[:signal_warmup] = np.nan
        histogram[:signal_warmup] = np.nan
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    @cached(ttl=3600, disk=True, key_prefix="opt_")
    @performance_monitor()
    def bollinger_bands(prices: np.ndarray, period: int = 20, std_dev: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Оптимизированные полосы Боллинджера.
        
        Args:
            prices: Массив цен
            period: Период расчета
            std_dev: Множитель стандартного отклонения
        
        Returns:
            Кортеж (Upper Band, Middle Band, Lower Band)
        """
        prices = np.asarray(prices, dtype=float)
        period = require_period('period', period)
        if len(prices) < period:
            nan_array = np.full(len(prices), np.nan)
            return nan_array, nan_array, nan_array
        
        # Средняя линия (SMA)
        middle_band = OptimizedIndicators.sma(prices, period)
        
        # Стандартное отклонение для окна
        std_values = np.zeros(len(prices), dtype=float)
        for i in range(period-1, len(prices)):
            window = prices[i-period+1:i+1]
            std_values[i] = np.std(window)
        
        # Устанавливаем NaN для первых period-1 значений
        std_values[:period-1] = np.nan
        
        # Верхняя и нижняя полосы
        upper_band = middle_band + (std_dev * std_values)
        lower_band = middle_band - (std_dev * std_values)
        
        return upper_band, middle_band, lower_band


def benchmark_function(func: Callable, *args, iterations: int = 100, **kwargs) -> Dict[str, float]:
    """
    Бенчмарк функции.
    
    Args:
        func: Функция для тестирования
        *args: Аргументы функции
        iterations: Количество итераций
        **kwargs: Именованные аргументы функции
    
    Returns:
        Словарь с результатами бенчмарка
    """
    times = []
    process = psutil.Process(os.getpid())
    
    for i in range(iterations):
        start_time = time.perf_counter()
        memory_before = process.memory_info().rss / 1024 / 1024
        
        try:
            result = func(*args, **kwargs)
            
            end_time = time.perf_counter()
            memory_after = process.memory_info().rss / 1024 / 1024
            
            execution_time = end_time - start_time
            times.append(execution_time)
            
        except Exception as e:
            logger.error(f"Benchmark iteration {i} failed: {e}")
            continue
    
    if not times:
        return {'error': 'All benchmark iterations failed'}
    
    return {
        'iterations': len(times),
        'total_time': sum(times),
        'avg_time': np.mean(times),
        'min_time': min(times),
        'max_time': max(times),
        'std_time': np.std(times),
        'median_time': np.median(times),
        'p95_time': np.percentile(times, 95),
        'p99_time': np.percentile(times, 99)
    }


def compare_implementations(implementations: Dict[str, Callable], test_data: Any, iterations: int = 50) -> pd.DataFrame:
    """
    Сравнить производительность различных реализаций.
    
    Args:
        implementations: Словарь {name: function}
        test_data: Тестовые данные
        iterations: Количество итераций для каждой реализации
    
    Returns:
        DataFrame с результатами сравнения
    """
    results = []
    
    for name, func in implementations.items():
        logger.info(f"Benchmarking {name}...")
        
        try:
            benchmark_results = benchmark_function(func, test_data, iterations=iterations)
            benchmark_results['implementation'] = name
            results.append(benchmark_results)
        except Exception as e:
            logger.error(f"Failed to benchmark {name}: {e}")
    
    if not results:
        return pd.DataFrame()
    
    df = pd.DataFrame(results)
    
    # Сортируем по среднему времени выполнения
    df = df.sort_values('avg_time').reset_index(drop=True)
    
    # Добавляем относительную производительность
    if len(df) > 1:
        fastest_time = df['avg_time'].min()
        df['speedup'] = fastest_time / df['avg_time']
        df['relative_performance'] = df['speedup'] * 100
    
    return df


def memory_usage_analysis(func: Callable, *args, **kwargs) -> Dict[str, Any]:
    """
    Анализ использования памяти функцией.
    
    Args:
        func: Функция для анализа
        *args: Аргументы функции
        **kwargs: Именованные аргументы
    
    Returns:
        Словарь с результатами анализа памяти
    """
    process = psutil.Process(os.getpid())
    
    # Измерения до выполнения
    memory_before = process.memory_info()
    
    # Выполняем функцию
    start_time = time.perf_counter()
    result = func(*args, **kwargs)
    end_time = time.perf_counter()
    
    # Измерения после выполнения
    memory_after = process.memory_info()
    
    return {
        'execution_time': end_time - start_time,
        'memory_before_mb': memory_before.rss / 1024 / 1024,
        'memory_after_mb': memory_after.rss / 1024 / 1024,
        'memory_delta_mb': (memory_after.rss - memory_before.rss) / 1024 / 1024,
        'vms_before_mb': memory_before.vms / 1024 / 1024,
        'vms_after_mb': memory_after.vms / 1024 / 1024,
        'vms_delta_mb': (memory_after.vms - memory_before.vms) / 1024 / 1024
    }


# Экспорт
__all__ = [
    'PerformanceMetrics',
    'PerformanceMonitor',
    'get_performance_monitor',
    'performance_monitor',
    'performance_context',
    'OptimizedIndicators',
    'require_period',
    'require_macd_periods',
    'ema_warmup',
    'macd_warmup',
    'benchmark_function',
    'compare_implementations',
    'memory_usage_analysis'
]
