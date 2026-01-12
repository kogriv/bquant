# Миграция на Universal Zone Analysis v2

Документ помогает перенести проекты со старого `MACDZoneAnalyzer` на универсальный пайплайн `analyze_zones`. Основой служит сценарий из Example 7 – Validation Demo (см. исходный код), где строится проверка качества зон и регрессионный анализ.

## Ключевые отличия

| Старый подход (`MACDZoneAnalyzer`) | Новый пайплайн (`analyze_zones`) |
| --- | --- |
| Класс-обертка `MACDZoneAnalyzer`, инициализируется с параметрами индикатора и зон.  | Функция-конструктор `analyze_zones(df)` возвращает builder с fluent API.  |
| Метод `analyze_complete(df, ...)` выполняет все шаги и возвращает `ZoneAnalysisResult`.  | Последовательность builder-методов (`with_indicator → detect_zones → analyze → build`) формирует тот же `ZoneAnalysisResult`.  |
| Конфигурация захардкожена для MACD, требуется обертка.  | Можно подставлять любые индикаторы и стратегии детекции, включая комбинации из примера 7.  |
| Валидация и кастомные шаги приходилось накладывать поверх результата вручную. | Builder предоставляет `.with_strategies(...)`, `.analyze(...)`, а результат совместим с существующим кодом Example 7 без доработок.  |

## Сценарий миграции: Example 7

### Шаг 1. Загрузка данных

```python
from bquant.data.samples import get_sample_data

data = get_sample_data("btc_hourly")
```

Эти строки остаются неизменными и совпадают с примером. 

### Шаг 2. Старый способ (для сравнения)

```python
from bquant.indicators.macd import MACDZoneAnalyzer

analyzer = MACDZoneAnalyzer()
legacy_result = analyzer.analyze_complete(
    data,
    perform_clustering=False,
    n_clusters=3,
)
legacy_zones = list(legacy_result.zones)
```

`analyze_complete` внутри делегирует в универсальный пайплайн, но параметры жёстко завязаны на MACD. 

### Шаг 3. Новый пайплайн (рекомендуемый)

```python
from bquant.analysis.zones import analyze_zones

modern_result = (
    analyze_zones(data)
    .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
    .detect_zones("zero_crossing", indicator_col="macd_hist", min_duration=2)
    .with_strategies(swing="find_peaks", shape="statistical")
    .analyze(clustering=False)
    .build()
)
modern_zones = list(modern_result.zones)
```

Фрагмент повторяет функцию `run_pipeline` из Example 7, поэтому дальнейшая обработка (сбор признаков, регрессии, валидации) не требует изменений. 

### Шаг 4. Повторное использование последующих шагов

После миграции блоки Example 7, отвечающие за сбор признаков и метрик (`summarize_zone`, `collect_zone_features`, `run_linear_regression`, `evaluate_*`), работают поверх `modern_zones` без модификаций. 

### Шаг 5. Сравнение результатов

- `legacy_result.zones` и `modern_result.zones` содержат совместимые объекты `ZoneInfo`.
- `ZoneAnalysisResult` предоставляет одинаковые атрибуты (`zones`, `metadata`, `save()`), поэтому текущие пайплайны экспорта/валидации можно переключить на `modern_result` одной заменой переменной.

## Чеклист миграции

1. **Замените импорт**: `from bquant.indicators.macd import MACDZoneAnalyzer` → `from bquant.analysis.zones import analyze_zones`.
2. **Перепишите инициализацию**: вместо `MACDZoneAnalyzer()` используйте `builder = analyze_zones(df)`.
3. **Передайте параметры индикатора** через `.with_indicator(...)` (используйте те же `fast`, `slow`, `signal`, что и раньше).
4. **Настройте детекцию**: `.detect_zones("zero_crossing", indicator_col="macd_hist", min_duration=2)` повторяет старую конфигурацию.
5. **Добавьте дополнительные стратегии** (при необходимости) с `.with_strategies(...)` — Example 7 включает swing и shape анализ.
6. **Финализируйте анализ**: `.analyze(clustering=perform_clustering, n_clusters=3).build()` возвращает `ZoneAnalysisResult`.
7. **Переиспользуйте пост-обработку**: весь код, который читал `ZoneAnalysisResult` или список зон, продолжает работать без изменений.
8. **Удалите предупреждения**: после миграции можно убрать зависимость от `bquant.indicators.macd` и связанных deprecated API.

## Полезные ссылки

- [Zone Analysis Guide](user_guide/zone_analysis.md) — подробное описание архитектуры и конфигурации.
- [Best Practices анализа зон](user_guide/best_practices.md) — рекомендации по работе с пайплайном и модульными шагами.
- **Example 7 – Validation Demo** (см. исходный код) — референс реализации продвинутой валидации.
