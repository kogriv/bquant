# Кэширование

Где хранится кэш, из чего складывается ключ, когда его чистить и в каком случае он
сегодня отдаёт не то, что вы просили.

## 1. Обзор архитектуры кэширования

BQuant использует **двухуровневую** систему кэширования:

| Уровень | Назначение | Расположение |
| :--- | :--- | :--- |
| **Memory** | Быстрый доступ, LRU-эвикция при переполнении | RAM процесса |
| **Disk** | Долговременное хранение между запусками | `~/.cache/bquant/` |

Менеджер кэша (`CacheManager`) объединяет оба уровня: при `get()` сначала проверяется память, при промахе — диск. При записи данные сохраняются и в память, и на диск (если включён дисковый кэш).

### Компоненты

- **`bquant.core.cache`** — общий менеджер (`CacheManager`), `MemoryCache`, `DiskCache`, `get_cache_manager()`, `clear_cache()`, `cache_stats()`.
- **`bquant.analysis.zones.cache.ZoneAnalysisCache`** — специализированная обёртка для результатов анализа зон (версионирование, формирование ключей).

## 2. Где хранится кэш

### Директория по умолчанию

```
~/.cache/bquant/
```

Файлы zone analysis: `zone_analysis_<hash>.pkl` (pickle).

### Переопределение через конфигурацию

```python
from bquant.core.config import CACHE_CONFIG, get_cache_config

# Текущая конфигурация
config = get_cache_config()
# {'enable_memory_cache': True, 'enable_disk_cache': True, 'memory_size': 100, ...}
```

Параметр `cache_dir` в `CACHE_CONFIG` (`bquant.core.config`) по умолчанию `None` — используется `Path.home() / ".cache" / "bquant"`.

## 3. Кэширование Zone Analysis

### Включение и отключение

Кэш **включён по умолчанию**. Управление через fluent API:

```python
from bquant.analysis.zones import analyze_zones

# С кэшем (по умолчанию)
result = analyze_zones(df).detect_zones(...).build()

# Отключить кэш (для экспериментов, отладки)
result = analyze_zones(df).with_cache(enable=False).detect_zones(...).build()

# Кэш с TTL 2 часа
result = analyze_zones(df).with_cache(ttl=7200).detect_zones(...).build()
```

### Формирование ключа кэша

Ключ складывается из четырёх частей:

1. **Версия схемы** — поднимается, когда меняется форма результата.
2. **Хеш данных** — OHLCV-колонки (`open`, `high`, `low`, `close`).
3. **Подпись конфигурации** — индикатор, детекция, `swing_scope`, `min_duration`,
   кластеризация, регрессия, валидация.
4. **Подпись свингов** — стратегия свингов, пресет, авто-пороги.

Версию не переписывайте из документации — спрашивайте у кода:

```python
from bquant.analysis.zones.cache import ZoneAnalysisCache

print(ZoneAnalysisCache.CACHE_VERSION)   # 15
```

Смена любого из перечисленного даёт **другой ключ**, и старые записи просто не находятся —
ручная очистка не нужна.

> **Чего в ключе нет.** Стратегии метрик `shape`, `divergence`, `volatility` и `volume`
> в подпись не входят — только свинги. Поэтому включение или смена одной из этих четырёх
> **не меняет ключ**, и при включённом кэше вы получите результат прошлого прогона,
> посчитанный без неё, без единого предупреждения. Пока это не исправлено, сравнивайте
> такие стратегии с `.with_cache(enable=False)`. Разбор:
> `devref/gaps/cache/g36_the_cache_key_does_not_see_the_strategies_2026-08.md`.

### Автоматическая инвалидация по версии

При чтении из кэша проверяется `cache_version` в сохранённых метаданных:

- Если `cached_version < CACHE_VERSION` → запись помечается как устаревшая, удаляется, возвращается `None` (пересчёт).
- В лог пишется: `"Cache invalidated due to schema upgrade (vN → vM). Recalculating..."`.

Ручная очистка при обновлении библиотеки **не обязательна** — устаревшие записи игнорируются автоматически.

## 4. Когда нужно очищать кэш

| Ситуация | Действие |
| :--- | :--- |
| Изменение индикатора, детекции, свинг-стратегии, пресета или scope | **Не требуется** — новый ключ, новые записи |
| Изменение стратегии `shape` / `divergence` / `volatility` / `volume` | **Кэш выключить** — ключ их не различает (см. врезку выше) |
| Обновление BQuant с изменением схемы результата | **Не требуется** — автo-инвалидация по версии |
| Подозрение на битые/устаревшие файлы | Очистить вручную |
| Освобождение места на диске | Очистить вручную |
| Отладка (исключить влияние кэша) | Отключить кэш `.with_cache(enable=False)` или очистить |

## 5. Как очищать кэш

### Программно (в коде)

```python
# Полная очистка глобального кэша (память + диск)
from bquant.core.cache import clear_cache
clear_cache()

# Инвалидация только для конкретного датасета (требует доступ к pipeline)
from bquant.analysis.zones import analyze_zones
# ... построить pipeline с enable_cache=True ...
# pipeline.invalidate_cache(df)  # требует экземпляр ZoneAnalysisPipeline
```

**Примечание:** `invalidate_cache(df)` — метод `ZoneAnalysisPipeline`, вызывается после `build()` через возвращённый pipeline. Через fluent API напрямую вызывать нельзя; для полной очистки используйте `clear_cache()`.

### Вручную (в терминале)

```bash
# Очистить все файлы кэша zone analysis
rm -rf ~/.cache/bquant/zone_analysis_*.pkl

# Очистить весь кэш BQuant
rm -rf ~/.cache/bquant/*.pkl

# Удалить директорию кэша полностью
rm -rf ~/.cache/bquant
```

## 6. Настройка кэша

### Глобальная конфигурация (`bquant.core.config`)

```python
CACHE_CONFIG = {
    'enable_memory_cache': True,
    'enable_disk_cache': True,
    'memory_size': 100,        # макс. записей в памяти (LRU)
    'default_ttl': 3600,       # время жизни по умолчанию (секунды)
    'cache_dir': None,         # None = ~/.cache/bquant
    'auto_cleanup': True,
    'cleanup_interval': 300,
}
```

Изменение требует правки `bquant/core/config.py` или подмены до инициализации менеджера.

### Per-pipeline настройка

```python
result = (
    analyze_zones(df)
    .with_cache(enable=True, ttl=7200)  # 2 часа
    .detect_zones(...)
    .build()
)
```

## 7. Статистика и диагностика

```python
from bquant.core.cache import cache_stats, get_cache_manager

# Общая статистика
stats = cache_stats()
# memory: entries, max_size, hits, misses, hit_rate, evictions,
#         total_size_bytes, avg_size_bytes
# disk:   entries, cache_dir

# Очистка истекших записей
manager = get_cache_manager()
cleaned = manager.cleanup()
# {'memory_cleaned': 2, 'disk_cleaned': 1}
```

## 8. Особенности Zone Analysis Cache

### Рекомендации

- **Исследования и A/B-тесты:** `.with_cache(enable=False)` — чтобы не смешивать результаты разных параметров.
- **Продакшен и отчёты:** оставить кэш включённым, задать `ttl` под частоту обновления данных.
- **Lambda в правилах детекции (`combined`):** кэш не сработает никогда. Функция попадает
  в ключ своим `repr` — `<function <lambda> at 0x7db6877c54e0>`, — а адрес меняется от
  запуска к запуску, поэтому два одинаковых по смыслу прогона дают разные ключи. Промах
  безвреден (лишний пересчёт), но кэш здесь просто не работает — не рассчитывайте на него.

## 9. Связанные материалы

- [Анализ зон на практике](zone_analysis.md) — выбор стратегий, для которых кэш придётся выключить
- [Best Practices](best_practices.md) — хранение артефактов и переиспользование
- [Миграция global swings](../migration/global_swings_migration.md) — Шаг 3: очистка кэша при миграции
- [API: bquant.core.config](../api/core/config.md) — `get_cache_config()`, `CACHE_CONFIG`
