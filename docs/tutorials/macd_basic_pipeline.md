# Tutorial: MACD zones (Пример 1) — базовый pipeline и визуализация

## 🎯 Цели
- Повторить базовый конвейер из [справочника пайплайна](../api/analysis/pipeline.md)
- Получить результат `ZoneAnalysisResult` с минимальными настройками
- Построить обзорную и детальную визуализацию через `ZoneVisualizer`

## 🔧 Предварительные требования
- Установленный `bquant`
- Библиотеки для визуализации (`plotly` ставится как зависимость)
- Понимание структуры OHLCV-данных

## 📥 Данные
Используем встроенный датасет `tv_xauusd_1h`, описанный в разделе [BQuant Sample Data](../api/data/samples.md). Он содержит 1000 строк с часовыми котировками XAUUSD и подходит для демонстрации MACD.

```python
from bquant.data.samples import get_sample_data

# Загрузим данные как DataFrame
raw = get_sample_data('tv_xauusd_1h')
print(raw.head())
```

## 🛠️ Шаг 1. Сборка базового pipeline
Используем fluent builder `analyze_zones()` с настройками из Примера 1. Главное — задать источник индикатора и стратегию детекции.

```python
from bquant.analysis.zones import analyze_zones

result = (
    analyze_zones(raw)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

print(f"Всего зон: {len(result.zones)}")
print(f"Первые 3 типа зон: {[z.type for z in result.zones[:3]]}")
```

### Что делает каждая стадия
| Метод | Назначение |
|-------|-----------|
| `with_indicator` | рассчитывает MACD на базе исходного DataFrame |
| `detect_zones` | применяет стратегию `zero_crossing` для MACD histogram |
| `analyze` | включает кластеризацию (по умолчанию k=3) и извлечение признаков |
| `build` | выполняет pipeline и возвращает `ZoneAnalysisResult` |

## 🔎 Шаг 2. Работа с результатами
`ZoneAnalysisResult` содержит зоны, признаки и статистику. Через `indicator_context` можно проверить, как была настроена детекция.

```python
first_zone = result.zones[0]
print(first_zone.indicator_context['detection_strategy'])  # 'zero_crossing'
print(result.statistics['avg_duration'])
```

## 📈 Шаг 3. Визуализация зон
В модели `ZoneAnalysisResult` уже встроен доступ к `ZoneVisualizer`. Используем стандартные режимы визуализации.

```python
# 1. Общий обзор зон на цене
overview_fig = result.visualize('overview', title='MACD Zones Overview')
overview_fig.show()

# 2. Детальный просмотр конкретной зоны
zone_fig = result.visualize('detail', zone_id=0, context_bars=20)
zone_fig.show()

# 3. Статистическое резюме
stats_fig = result.visualize('statistics')
stats_fig.show()
```

> ℹ️ `ZoneVisualizer` автоматически использует Plotly backend и поддерживает экспорт через `write_html()` или `write_image()`.

## ✅ Лучшие практики
1. **Фильтрация по длительности** — по умолчанию (`min_duration=1`) зоны мостят
   ряд точно и ничего не теряется. Если коротких зон слишком много для вашей
   задачи, просите отсев на стадии анализа: `.analyze(min_duration=N)`. Он не
   удаляет зоны из `result.zones`, а выводит их из агрегатов, и говорит об этом
   в `result.metadata['duration_filter']` — иначе соседство зон в анализе
   последовательностей перестаёт быть соседством.
2. **Контекст индикатора** — сохраняйте `result.zones[i].indicator_context` для трассировки параметров, особенно при нескольких перезапусках pipeline.
3. **Кэширование** — для больших данных включайте `.with_cache(enable=True, ttl=3600)` до `with_indicator`, чтобы повторные вызовы были быстрее.
4. **Сохранение артефактов** — используйте `result.save('macd_result.pkl')`, чтобы потом строить графики без пересчёта.

## 🚀 Что дальше
- Добавьте другие индикаторы в pipeline или переключите стратегию детекции (см. Tutorial по RSI).
- Подключите swing/shape/divergence стратегии через `.with_strategies()`.
- Сравните результаты с legacy-подходом из `examples/02_macd_zone_analysis.py`.
