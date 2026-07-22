# Результаты анализа свинг-метрик MACD зон

## Итоговая сводка работы с пакетом BQuant

Дата: 2025-10-28

---

## 🎯 Цель анализа

Проверить "профпригодность" индикатора MACD (12,26,9) через анализ **свинг-метрик ВНУТРИ зон**:
- Есть ли достаточные колебания для торговли?
- "Дает ли море" - можно ли заработать на внутренних rally/drop?
- Есть ли асимметрия (rally > drop в bull зонах)?

**Ключевая идея**: Не просто анализировать "от начала до конца зоны", а исследовать **колебания внутри зон** используя ZigZag индикатор.

---

## 🔧 Что использовано из пакета BQuant

### ✅ Успешно использованные компоненты:

1. **ZoneDetection:** `zero_crossing` стратегия
   - Детекция bull/bear зон по пересечению MACD histogram нуля
   - 79 зон найдено (40 bull, 39 bear)

2. **SwingStrategy:** `zigzag` (pandas_ta ZigZag)
   - **23 поля метрик** (SwingMetrics dataclass)
   - Автоматический расчет rally/drop амплитуд, длительностей, скоростей
   - Сохранение в `zone.features['metadata']['swing_metrics']`

3. **ShapeStrategy:** `statistical`
   - Skewness, Kurtosis гистограммы

4. **DivergenceStrategy:** `classic`
   - Classic divergences detection

5. **VolumeStrategy:** `standard`
   - Volume-indicator correlation

6. **UniversalZoneAnalyzer**
   - Полный pipeline анализа
   - Clustering (3 кластера)
   - Hypothesis testing

---

## 📊 Результаты анализа

### MACD (12,26,9) + ZigZag (default: deviation=0.05, legs=10)

| Тип зоны | Кол-во зон | Среднее rally в зоне | Среднее drop в зоне | Средняя амплитуда rally | Средняя амплитуда drop |
|----------|------------|----------------------|---------------------|-------------------------|------------------------|
| **BULL** | 40         | 0.1                  | 0.1                 | 0.251%                  | 0.258%                 |
| **BEAR** | 39         | 0.1                  | 0.1                 | 0.200%                  | 0.257%                 |

### Интерпретация:

#### 🟡 Амплитуды (0.20-0.26%)
**ПОЛОЖИТЕЛЬНО:** Достаточны для торговли на XAUUSD (> 0.05% минимум)

#### 🔴 Количество колебаний (0.1 rally/drop)
**ПРОБЛЕМА:** Очень мало свингов в зоне!
- Дефолтные параметры ZigZag слишком строгие (deviation=5%)
- Для XAUUSD 15min нужно уменьшить до 1-2% (deviation=0.01-0.02)

#### 🟡 Асимметрия
- **BULL зоны:** ratio=0.97 (rally ≈ drop) - НЕТ асимметрии
- **BEAR зоны:** ratio=1.28 (drop > rally) - ЕСТЬ асимметрия!

### Вердикт:

🟢 **BEAR зоны:** Потенциал есть (амплитуда + асимметрия), но мало колебаний
🟡 **BULL зоны:** Амплитуда есть, но нет асимметрии и мало колебаний

**Рекомендация:** Оптимизировать параметры ZigZag (уменьшить deviation до 0.01-0.02)

---

## ✅ Что работает отлично в пакете

### 1. Универсальность
- Один API для всех индикаторов (MACD, RSI, AO, custom)
- indicator_context - зоны "знают" как они были обнаружены

### 2. Полнота SwingMetrics (23 поля)

```python
SwingMetrics = {
    # Счетчики
    'rally_count': int,
    'drop_count': int,
    'num_swings': int,

    # Амплитуды
    'avg_rally_pct': float,
    'avg_drop_pct': float,
    'max_rally_pct': float,
    'max_drop_pct': float,
    'min_rally_pct': float,
    'min_drop_pct': float,
    'rally_amplitude_std': float,
    'drop_amplitude_std': float,
    'rally_amplitude_median': float,
    'drop_amplitude_median': float,

    # Длительности
    'avg_rally_duration_bars': float,
    'avg_drop_duration_bars': float,
    'max_rally_duration_bars': int,
    'max_drop_duration_bars': int,

    # Скорости
    'avg_rally_speed_pct_per_bar': float,
    'avg_drop_speed_pct_per_bar': float,
    'max_rally_speed_pct_per_bar': float,
    'max_drop_speed_pct_per_bar': float,

    # Соотношения
    'rally_to_drop_ratio': float,
    'duration_symmetry': float,
}
```

### 3. Интеграция pandas_ta
- ZigZag из pandas_ta успешно работает через LibraryManager
- 158 индикаторов доступны

### 4. Модульность
- Можно использовать отдельные компоненты
- Расширяемая архитектура (Strategy Pattern)

---

## ❌ Что отсутствует в пакете (TODO для разработки)

### 1. Swing Metrics в top-level features
**Текущее состояние:**
```python
swing_metrics = zone.features['metadata']['swing_metrics']
```

**Желаемое:**
```python
avg_rally = zone.features['avg_rally_pct']  # Прямой доступ
```

**Причина:** Удобство доступа, совместимость с ML pipeline

---

### 2. Backtesting модуль для swing торговли
**Отсутствует:**
- Симуляция входов/выходов на swing точках
- Расчет win rate, profit factor для swing стратегий
- Position sizing на основе swing амплитуд

**Пример желаемого API:**
```python
from bquant.backtest import SwingBacktester

backtester = SwingBacktester(
    entry_strategy='rally_start',   # Вход в начале rally
    exit_strategy='rally_end',       # Выход в конце rally
    risk_per_trade=0.01             # 1% на сделку
)

results = backtester.run(zones=result.zones, data=df)
print(f"Win rate: {results.win_rate:.2%}")
print(f"Profit factor: {results.profit_factor:.2f}")
```

---

### 3. Оптимизатор параметров ZigZag
**Отсутствует:**
- Grid search по параметрам (deviation, legs)
- Walk-forward validation
- Автоматический подбор оптимальных параметров

**Пример желаемого API:**
```python
from bquant.optimization import ZigZagOptimizer

optimizer = ZigZagOptimizer(
    deviation_range=(0.01, 0.10, 0.01),  # от 1% до 10% с шагом 1%
    legs_range=(5, 20, 5),                # от 5 до 20 с шагом 5
    metric='avg_rally_amplitude'          # Метрика для оптимизации
)

best_params = optimizer.optimize(zones=result.zones)
print(f"Best deviation: {best_params.deviation}")
print(f"Best legs: {best_params.legs}")
```

---

### 4. Визуализация swing points
**Отсутствует:**
- Отметки rally/drop на графиках зон
- Entry/exit точки для swing торговли
- Интерактивные графики с зонами

**Пример желаемого API:**
```python
from bquant.visualization import plot_zone_swings

fig = plot_zone_swings(
    zone=result.zones[0],
    show_rally_points=True,
    show_drop_points=True,
    show_entry_exit=True
)
fig.show()
```

---

### 5. Machine Learning для swing предсказаний
**Отсутствует:**
- Регрессия: предсказание avg_rally_pct по zone features
- Классификация: profitable_swing vs unprofitable
- Feature importance для swing метрик

**Пример желаемого API:**
```python
from bquant.ml import SwingPredictor

predictor = SwingPredictor(model='random_forest')
predictor.fit(zones=result.zones[:60])  # Обучение на первых 60 зонах

prediction = predictor.predict(zone=result.zones[61])
print(f"Predicted avg_rally: {prediction.avg_rally_pct:.3f}%")
print(f"Confidence: {prediction.confidence:.2f}")
```

---

### 6. Фильтр зон по swing качеству
**Отсутствует:**
- Swing Quality Score (0-100)
- Автоматический отбор зон с лучшими swing метриками
- Ранжирование зон по профитабельности

**Пример желаемого API:**
```python
from bquant.analysis.zones import filter_zones_by_swing_quality

best_zones = filter_zones_by_swing_quality(
    zones=result.zones,
    min_rally_count=2.0,           # Минимум 2 rally в зоне
    min_avg_rally_pct=0.15,        # Минимум 0.15% амплитуда
    min_asymmetry_ratio=1.2,       # Rally > Drop * 1.2
    return_top_n=10                # Топ-10 зон
)

for zone in best_zones:
    print(f"Zone {zone.zone_id}: swing_quality_score={zone.swing_quality_score}")
```

---

## 📝 Выводы

### Что удалось сделать:
✅ Правильно использовать весь инструментарий пакета BQuant
✅ Извлечь SwingMetrics из metadata (23 поля метрик)
✅ Проанализировать колебания ВНУТРИ зон (не просто от начала до конца)
✅ Оценить "дает ли море" - есть ли альфа в свингах
✅ Идентифицировать недостающие компоненты для production использования

### Архитектура пакета:
🟢 **Отлично спроектирована** - универсальная, расширяемая, модульная
🟢 **SwingMetrics полностью реализованы** - 23 детальных поля
🟢 **Strategy Pattern** - легко добавлять новые стратегии

### Недостающие компоненты:
🔴 Backtesting для swing торговли
🔴 Оптимизатор параметров
🔴 Визуализация swing points
🔴 ML для предсказаний
🔴 Фильтр зон по качеству

---

## 🚀 Рекомендации для дальнейшей разработки

### Приоритет 1 (Critical):
1. **Backtesting модуль** - необходим для проверки реальной профитабельности
2. **Swing Metrics в top-level features** - удобство доступа
3. **Оптимизатор параметров ZigZag** - автоматический подбор

### Приоритет 2 (High):
4. **Визуализация swing points** - критично для анализа
5. **Фильтр зон по swing качеству** - отбор лучших зон

### Приоритет 3 (Medium):
6. **ML модуль для предсказаний** - продвинутый анализ

---

## 📚 Примеры кода

### Как правильно извлечь swing метрики:

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

# Загрузка данных
df = get_sample_data('mt_xauusd_m15')

# Анализ с ZigZag
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist', min_duration=3)
    .with_strategies(swing='zigzag')  # ZigZag из pandas_ta
    .build()
)

# Извлечение swing metrics из METADATA
for zone in result.zones:
    metadata = zone.features.get('metadata', {})
    swing_metrics = metadata.get('swing_metrics')

    if swing_metrics:
        print(f"Zone {zone.zone_id} ({zone.type}):")
        print(f"  Rally count: {swing_metrics['rally_count']}")
        print(f"  Avg rally: {swing_metrics['avg_rally_pct']:.3f}%")
        print(f"  Avg drop: {swing_metrics['avg_drop_pct']:.3f}%")
        print(f"  Ratio: {swing_metrics['rally_to_drop_ratio']:.2f}")
```

---

**Дата создания:** 2025-10-28
**Версия пакета:** BQuant 0.0.1
**Автор анализа:** Claude Code + kogriv
