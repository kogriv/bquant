# Tutorial: RSI zones (Пример 5) — смена стратегии детекции

## 🎯 Цели
- Реализовать pipeline из Примера 5: RSI через talib (см. документацию)
- Показать, как переключаться между `threshold` и `line_crossing` без пересчёта индикатора
- Сравнить контекст и распределение зон после смены стратегии

## 🔧 Предварительные требования
- `pip install bquant talib-binary` (или установленный TA-Lib)
- Набор данных с колонками OHLCV (используем sample `tv_xauusd_1h`)
- Понимание логики порогов RSI

## 📥 Подготовка данных
```python
from bquant.data.samples import get_sample_data

df = get_sample_data('tv_xauusd_1h')
```

## 🛠️ Шаг 1. Базовый threshold-подход
Следуем конфигурации из Примера 5: рассчитываем RSI через `talib` и применяем стратегию `threshold` с уровнями 70/30.

```python
from bquant.analysis.zones import analyze_zones

rsi_threshold = (
    analyze_zones(df)
    .with_indicator('talib', 'rsi', timeperiod=14)
    .detect_zones('threshold', indicator_col='RSI', upper_threshold=70, lower_threshold=30)
    .analyze(clustering=True)
    .build()
)

print(f"Threshold zones: {len(rsi_threshold.zones)}")
print(rsi_threshold.statistics['zone_distribution'])
```

## ♻️ Шаг 2. Переключение стратегии без пересчёта индикатора
`ZoneAnalysisResult` возвращает DataFrame с уже рассчитанным RSI в поле `data`. Сохраним его и построим сигнал для сравнения линий.

```python
# Извлекаем DataFrame с RSI (он уже содержит колонку 'RSI')
rsi_data = rsi_threshold.data.copy()
rsi_data['RSI_signal'] = rsi_data['RSI'].rolling(5, min_periods=1).mean()
```

Теперь перезапускаем pipeline только со стадией детекции, используя `line_crossing`. Эта стратегия сопоставляет RSI и его сглаженную версию и позволяет обнаруживать смены тренда.

```python
rsi_line = (
    analyze_zones(rsi_data)
    .detect_zones('line_crossing', line1_col='RSI', line2_col='RSI_signal')
    .analyze(clustering=True, min_duration=3)
    .build()
)

print(f"Line-crossing zones: {len(rsi_line.zones)}")
first_ctx = rsi_line.zones[0].indicator_context
print(first_ctx['detection_strategy'])  # 'line_crossing'
print(first_ctx['signal_line'])          # 'RSI_signal'
```

### Сравнение результатов
```python
print("Threshold win-rate:", rsi_threshold.statistics.get('win_rate'))
print("Line crossing win-rate:", rsi_line.statistics.get('win_rate'))
```

## 📊 Визуализация смены стратегии
Для быстрой проверки используем встроенную визуализацию.

```python
# Threshold контекст
threshold_fig = rsi_threshold.visualize('overview', title='RSI Threshold Zones')
threshold_fig.show()

# Line crossing контекст
line_fig = rsi_line.visualize('overview', title='RSI Line Crossing Zones')
line_fig.show()
```

> 💡 При необходимости можно вызвать `visualize('detail', zone_id=...)`, чтобы сравнить структуру конкретной зоны до и после смены стратегии.

## ✅ Лучшие практики
1. **Переиспользуйте данные** — работайте с `result.data`, чтобы не пересчитывать индикаторы при экспериментировании со стратегиями.
2. **Логируйте контекст** — сохраняйте `zone.indicator_context` в отчёты, чтобы понимать, какие правила сработали в каждом запуске.
3. **Подбор параметров** — используйте разные окна для `RSI_signal` (3–7 баров), чтобы регулировать чувствительность `line_crossing`.
4. **Комбинируйте стратегии** — начните с `threshold`, чтобы отфильтровать экстремумы, затем запускайте `line_crossing` для уточнения точек выхода.

## 🚀 Что дальше
- Добавьте `CombinedRulesDetection` с дополнительным условием по объёму.
- Подготовьте backtest: сохраните `rsi_line.zones` и прогоните через торговый симулятор.
- Изучите `examples/02a_universal_zones.py` для дополнительных сценариев работы с RSI.
