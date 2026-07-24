# bquant.analysis.zones.strategies — паттерн Strategy

> **✅ v2.1 - Универсальные стратегии**
> 
> Все аналитические стратегии теперь работают с **ЛЮБЫМ индикатором**!
> 
> **Что изменилось:**
> - Все стратегии принимают явный параметр `indicator_col`
> - `VolumeMetrics.volume_macd_corr` → `volume_indicator_corr` (универсальное именование)
> - Сигнатуры протоколов обновлены для универсальности
> 
> **Примеры:** Каждая стратегия теперь показывает использование с MACD, RSI, AO и пользовательскими индикаторами
>
> **Подтверждено:** Работает с FICTIONAL_INDICATOR_99 и 10+ реальными индикаторами (100% покрытие тестами)
>
> **Стабильность API:** 🟢 STABLE - этот API не изменится после универсализации

> 📘 Для разработчиков: см. [Zone Detection Strategies — Developer Guide](../../developer_guide/zone_detection_strategies.md)
> для пошаговой инструкции по созданию собственных стратегий детекции зон.

## Обзор

BQuant использует **Strategy Pattern** для расширяемого расчета метрик зон. Это позволяет:
- Добавлять новые алгоритмы анализа без изменения основного кода
- Переключаться между алгоритмами через конфигурацию
- A/B тестировать разные подходы
- Комбинировать несколько стратегий одновременно

## Архитектура

```
ZoneFeaturesAnalyzer
├── SwingStrategy → SwingMetrics (23 поля)
├── ShapeStrategy → ShapeMetrics (3 поля)
├── DivergenceStrategy → DivergenceMetrics (4 поля)
├── VolatilityStrategy → VolatilityMetrics (10 полей)
└── VolumeStrategy → VolumeMetrics (4 поля)
```

Каждая стратегия:
1. Реализует протокол (`Protocol`)
2. Возвращает типизированный результат (`Dataclass`)
3. Регистрируется в `StrategyRegistry`
4. Создается через фабрику из `config.py`

---

## Protocols и Dataclasses

### SwingCalculationStrategy Protocol

```python
class SwingCalculationStrategy(Protocol):
    # Глобальный режим (по умолчанию)
    def calculate_global(self, full_data: pd.DataFrame) -> SwingContext: ...
    def aggregate_for_zone(self, zone: ZoneInfo, context: SwingContext) -> SwingMetrics: ...
    # Легаси per-zone режим (совместимость)
    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics: ...
    def get_metadata(self) -> Dict[str, Any]: ...
    def config_hash(self) -> Dict[str, Any]: ...
```

> 📖 Полный разбор глобального контракта (`calculate_global`/`aggregate_for_zone`) и
> реализаций ZigZag/FindPeaks/PivotPoints — в
> [Глобальные свинги: стратегии](zones/global_swings_strategies.md).

### SwingMetrics Dataclass (23 поля)

Полный результат анализа свингов в зоне.

**Категории метрик:**

#### Базовые (6 полей)
- `num_swings`: Количество свингов (пар impulse+correction)
- `avg_rally_pct`: Средняя амплитуда ралли (%)
- `avg_drop_pct`: Средняя амплитуда откатов (%)
- `max_rally_pct`: Максимальная амплитуда ралли (%)
- `max_drop_pct`: Максимальная амплитуда откатов (%)
- `rally_to_drop_ratio`: Отношение среднего ралли к среднему откату

#### Счетчики (2 поля)
- `rally_count`: Количество восходящих движений
- `drop_count`: Количество нисходящих движений

#### Минимумы и распределение (6 полей)
- `min_rally_pct`: Минимальная амплитуда ралли (%)
- `min_drop_pct`: Минимальная амплитуда откатов (%)
- `rally_amplitude_std`: Стандартное отклонение амплитуд ралли
- `drop_amplitude_std`: Стандартное отклонение амплитуд откатов
- `rally_amplitude_median`: Медиана амплитуд ралли (%)
- `drop_amplitude_median`: Медиана амплитуд откатов (%)

#### Длительность в барах (4 поля)
- `avg_rally_duration_bars`: Средняя длительность ралли (бары)
- `avg_drop_duration_bars`: Средняя длительность откатов (бары)
- `max_rally_duration_bars`: Максимальная длительность ралли (бары)
- `max_drop_duration_bars`: Максимальная длительность откатов (бары)

#### Скорость движения (4 поля)
- `avg_rally_speed_pct_per_bar`: Средняя скорость ралли (% за бар)
- `avg_drop_speed_pct_per_bar`: Средняя скорость откатов (% за бар)
- `max_rally_speed_pct_per_bar`: Максимальная скорость ралли (% за бар)
- `max_drop_speed_pct_per_bar`: Максимальная скорость откатов (% за бар)

#### Симметрия (1 поле)
- `duration_symmetry`: Отношение средней длительности ралли к откатам

#### Метаданные
- `strategy_name`: Имя использованной стратегии
- `strategy_params`: Параметры стратегии

**Интерпретация:**
- `rally_to_drop_ratio > 2`: Сильные импульсы, слабые коррекции
- `duration_symmetry > 1.5`: Импульсы длиннее коррекций
- Высокое значение `*_speed`: Быстрые резкие движения
- Низкое значение `*_std`: Однородные свинги

---

### ShapeCalculationStrategy Protocol

```python
class ShapeCalculationStrategy(Protocol):
    def calculate(self, zone_data: pd.DataFrame, indicator_col: str) -> ShapeMetrics: ...
    #                                            ^^^^^^^^^^^^^^^^^^
    #                                            v2.1: обязателен (без авто-детекта)
    def get_metadata(self) -> Dict[str, Any]: ...
```

**Универсальное использование v2.1:**

Параметр `indicator_col` **обязателен** для универсального использования с любым осциллятором.

**Примеры:**
```python
from bquant.analysis.zones.strategies.shape import StatisticalShapeStrategy

strategy = StatisticalShapeStrategy()

# MACD
shape = strategy.calculate(zone_data, indicator_col='macd_hist')

# RSI
shape = strategy.calculate(zone_data, indicator_col='RSI_14')

# Awesome Oscillator
shape = strategy.calculate(zone_data, indicator_col='AO_5_34')

# CCI
shape = strategy.calculate(zone_data, indicator_col='CCI_20')

# Custom indicator
shape = strategy.calculate(zone_data, indicator_col='MY_CUSTOM_OSC')
```

**Все возвращают одну и ту же структуру ShapeMetrics:**
- `hist_skewness`: Асимметрия распределения
- `hist_kurtosis`: Острота пика
- `hist_smoothness`: Согласованность изменений

### ShapeMetrics Dataclass (3 поля)

Характеристики формы гистограммы индикатора.

- `hist_skewness`: Асимметрия распределения
- `hist_kurtosis`: Эксцесс (острота пика)
- `hist_smoothness`: Гладкость изменения значений

**Интерпретация:**
- **Skewness > 0:** Правосторонняя асимметрия (больше положительных значений)
- **Skewness < 0:** Левосторонняя асимметрия (больше отрицательных значений)
- **Kurtosis > 3:** Острый пик (лептокуртический)
- **Kurtosis < 3:** Плоское распределение (платикуртический)
- **Smoothness высокая:** Плавное изменение индикатора
- **Smoothness низкая:** Резкие скачки индикатора

---

### DivergenceCalculationStrategy Protocol

```python
class DivergenceCalculationStrategy(Protocol):
    def calculate_divergence(self,
                           zone_data: pd.DataFrame,
                           indicator_col: str,
                           indicator_line_col: str = None) -> DivergenceMetrics: ...
    #                       ^^^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^
    #                       обязателен          v2.1: 2-линейные индикаторы (MACD + signal)
    def get_metadata(self) -> Dict[str, Any]: ...
```

**Универсальные примеры v2.1:**
```python
from bquant.analysis.zones.strategies.divergence import ClassicDivergenceStrategy

strategy = ClassicDivergenceStrategy()

# RSI divergence
div = strategy.calculate_divergence(data, indicator_col='RSI_14')

# MACD histogram divergence
div = strategy.calculate_divergence(data, indicator_col='macd_hist')

# MACD with signal line (2-line divergence)
div = strategy.calculate_divergence(data, 
                                    indicator_col='macd',
                                    indicator_line_col='macd_signal')

# Awesome Oscillator divergence
div = strategy.calculate_divergence(data, indicator_col='AO_5_34')
```

### DivergenceMetrics Dataclass (4 поля)

Информация о дивергенциях между ценой и индикатором.

- `divergence_type`: Тип ('regular_bullish', 'regular_bearish', 'hidden_bullish', 'hidden_bearish', None)
- `divergence_count`: Количество обнаруженных дивергенций
- `divergence_strength`: Сила дивергенции (0.0-1.0)
- `divergence_direction`: Направление дивергенции (+1, -1, 0)

**Интерпретация:**
- **Regular bullish:** Цена формирует более низкий минимум (lower low), индикатор — более высокий минимум (higher low) → потенциальный разворот вверх
- **Regular bearish:** Цена формирует более высокий максимум (higher high), индикатор — более низкий максимум (lower high) → потенциальный разворот вниз
- **Strength > 0.7:** Сильная дивергенция
- **Strength < 0.3:** Слабая дивергенция

---

### VolatilityCalculationStrategy Protocol

```python
class VolatilityCalculationStrategy(Protocol):
    def calculate_volatility(self, zone_data: pd.DataFrame) -> VolatilityMetrics: ...
    def get_metadata(self) -> Dict[str, Any]: ...
```

### VolatilityMetrics Dataclass (10 полей)

Оценка волатильности в зоне через Bollinger Bands и ATR.

**Bollinger Bands метрики (5):**
- `bollinger_width_pct`: Ширина полос (% от цены)
- `bollinger_width_std`: Ширина в стандартных отклонениях
- `bollinger_squeeze_ratio`: Отношение текущей ширины к средней
- `bollinger_upper_touches`: Количество касаний верхней полосы
- `bollinger_lower_touches`: Количество касаний нижней полосы

**ATR метрики (3):**
- `atr_normalized_range`: Диапазон зоны нормализованный на ATR
- `atr_trend`: Тренд ATR в зоне (-1: падает, 0: стабилен, +1: растет)
- `avg_atr`: Средний ATR в зоне

**Композитные метрики (2):**
- `volatility_score`: Комплексный скор 0-10 (weighted avg)
- `volatility_regime`: Классификация ('low', 'medium', 'high', 'extreme')

**Интерпретация volatility_score:**
- **0-3:** Low volatility - спокойный рынок
- **3-6:** Medium volatility - нормальный рынок
- **6-8:** High volatility - повышенная волатильность
- **8-10:** Extreme volatility - экстремальная волатильность

---

### VolumeCalculationStrategy Protocol

```python
class VolumeCalculationStrategy(Protocol):
    def calculate_volume(self, zone_data: pd.DataFrame,
                         baseline_volume: Optional[float] = None,
                         indicator_col: Optional[str] = None) -> VolumeMetrics: ...
    #                    v2.1: indicator_col для универсальной корреляции объём↔индикатор
    def get_metadata(self) -> Dict[str, Any]: ...
```

### VolumeMetrics Dataclass (4 поля)

Анализ объемов торгов в зоне (v2.1: универсальный для ЛЮБОГО индикатора).

- `volume_zone_ratio`: Отношение среднего объема зоны к baseline
- `volume_at_entry_change`: Изменение объема при входе в зону (%)
- `volume_indicator_corr`: Корреляция объема с индикатором ✨ **v2.1: переименовано из volume_macd_corr**
- `avg_volume_zone`: Средний объем в зоне

**Интерпретация:**
- `volume_zone_ratio > 1.5`: Высокий объем - сильное движение
- `volume_zone_ratio < 0.7`: Низкий объем - слабое движение
- `volume_indicator_corr > 0.7`: Объем подтверждает индикатор ✨ **v2.1: универсальный**
- `volume_at_entry_change > 0.5`: Объем растет при входе — подтверждение

**Универсальные примеры v2.1:**
```python
from bquant.analysis.zones.strategies.volume import StandardVolumeStrategy

strategy = StandardVolumeStrategy()

# MACD correlation
vol = strategy.calculate_volume(zone_data, baseline_volume=1000, indicator_col='macd_hist')

# RSI correlation
vol = strategy.calculate_volume(zone_data, baseline_volume=1000, indicator_col='RSI_14')

# AO correlation
vol = strategy.calculate_volume(zone_data, baseline_volume=1000, indicator_col='AO_5_34')

# Access universal field
print(f"Volume-Indicator correlation: {vol.volume_indicator_corr:.2f}")
```

---

## StrategyRegistry

Централизованный реестр всех стратегий.

### Регистрация стратегий

```python
from bquant.analysis.zones.strategies.registry import StrategyRegistry

# Register swing strategy
@StrategyRegistry.register_swing_strategy('my_strategy')
class MySwingStrategy:
    pass

# Manual registration
StrategyRegistry.register_swing_strategy('another', AnotherStrategy)
```

### Получение стратегий

```python
# Get strategy class
StrategyClass = StrategyRegistry.get_swing_strategy('zigzag')

# Create instance
strategy = StrategyClass(legs=10, deviation=0.05)

# List all available
print(StrategyRegistry.list_swing_strategies())
# ['zigzag', 'find_peaks', 'pivot_points']
```

### Статистика реестра

```python
stats = StrategyRegistry.get_registry_stats()
print(f"Total strategies: {stats['total']}")
print(f"By type: {stats['by_type']}")
# {'swing': 3, 'shape': 1, 'divergence': 1, 'volatility': 1, 'volume': 1}
```

---

## Реализованные стратегии

### Стратегии свингов

#### ZigZagSwingStrategy

**Алгоритм:** Использует индикатор pandas-ta ZigZag для обнаружения значимых разворотов цены.

**Параметры:**
- `legs` (по умолчанию: 10): Количество баров для анализа назад/вперед
- `deviation` (по умолчанию: 0.05): Минимальное изменение цены 5% для формирования новой ноги

**Когда применять:**
- ✅ Плавные трендовые рынки
- ✅ Старшие таймфреймы (H4, D1)
- ✅ Необходимо отфильтровать шум

**Пример:**
```python
from bquant.analysis.zones import ZoneFeaturesAnalyzer

analyzer = ZoneFeaturesAnalyzer(swing_strategy='zigzag')
# Or with custom parameters
from bquant.core.config import create_swing_strategy
strategy = create_swing_strategy('zigzag', legs=15, deviation=0.03)
analyzer = ZoneFeaturesAnalyzer(swing_strategy=strategy)
```

**Фокус метрик:** Более крупные и значимые свинги

---

#### FindPeaksSwingStrategy

**Алгоритм:** Использует scipy.signal.find_peaks для обнаружения всех локальных экстремумов.

**Параметры:**
- `prominence` (по умолчанию: 0.02): Минимальная выраженность 2% для пика
- `distance` (по умолчанию: 3): Минимум 3 бара между пиками

**Когда применять:**
- ✅ Рынки во флэте/волатильные диапазоны
- ✅ Нужно находить все локальные экстремумы
- ✅ Младшие таймфреймы (M15, H1)
- ✅ Детальный анализ свингов

**Пример:**
```python
analyzer = ZoneFeaturesAnalyzer(swing_strategy='find_peaks')
# Custom parameters
strategy = create_swing_strategy('find_peaks', prominence=0.01, distance=5)
```

**Фокус метрик:** Более многочисленные, но меньшие свинги

---

#### PivotPointsSwingStrategy

**Алгоритм:** Классический N-барный паттерн — максимум/минимум, являющийся наивысшим/наименьшим среди N баров слева и справа.

**Параметры:**
- `left_bars` (по умолчанию: 5): Количество баров слева от пивота
- `right_bars` (по умолчанию: 5): Количество баров справа от пивота

**Когда применять:**
- ✅ Классический подход технического анализа
- ✅ Требуются четко определенные пивоты
- ✅ Любой таймфрейм
- ✅ Консервативное определение свингов

**Пример:**
```python
analyzer = ZoneFeaturesAnalyzer(swing_strategy='pivot_points')
# Asymmetric window
strategy = create_swing_strategy('pivot_points', left_bars=7, right_bars=3)
```

**Фокус метрик:** Подтвержденные, проверенные свинги

---

### Стратегии формы

#### StatisticalShapeStrategy

**Алгоритм:** Статистический анализ формы гистограммы индикатора с использованием scipy.stats.

**Параметры:** Нет (используются статистические моменты)

**Рассчитываемые метрики:**
- `hist_skewness`: Коэффициент асимметрии (scipy.stats.skew)
- `hist_kurtosis`: Куртозис (scipy.stats.kurtosis)
- `hist_smoothness`: Гладкость (обратная дисперсии изменений)

**Когда применять:**
- ✅ Понять характеристики распределения
- ✅ Выявить взрывные vs плавные зоны
- ✅ Кластеризовать зоны по форме
- ✅ Любой индикатор с гистограммой

**Пример:**
```python
analyzer = ZoneFeaturesAnalyzer(shape_strategy='statistical')

features = analyzer.extract_zone_features(zone_dict)
shape = features.metadata['shape_metrics']

print(f"Skewness: {shape.hist_skewness:.2f}")
print(f"Kurtosis: {shape.hist_kurtosis:.2f}")
print(f"Smoothness: {shape.hist_smoothness:.2f}")
```

**Интерпретация:**
- Положительная асимметрия + высокий куртозис → Взрывные движения
- Отрицательная асимметрия + низкий куртозис → Плавное снижение
- Высокая гладкость → Устойчивый тренд
- Низкая гладкость → Рваное движение

---

### Стратегии дивергенций

#### ClassicDivergenceStrategy

**Алгоритм:** Обнаруживает обычные бычьи/медвежьи дивергенции через детекцию пиков.

**Параметры:**
- `use_macd_line` (по умолчанию: False): Использовать линию MACD вместо гистограммы

**Типы дивергенций:**
- **Regular Bullish:** Цена формирует lower low, индикатор — higher low
- **Regular Bearish:** Цена формирует higher high, индикатор — lower high

**Когда применять:**
- ✅ Потенциальные точки разворота
- ✅ Подтверждение сигналов на вход
- ✅ Генерация сигналов на выход
- ✅ Работает с любым осциллятором

**Пример:**
```python
analyzer = ZoneFeaturesAnalyzer(divergence_strategy='classic')

features = analyzer.extract_zone_features(zone_dict)
div = features.metadata['divergence_metrics']

if div.divergence_count > 0:
    print(f"Divergence detected: {div.divergence_type}")
    print(f"Strength: {div.divergence_strength:.2f}")
    print(f"Count: {div.divergence_count}")
```

**Расчет силы:**
- Основан на вертикальном расстоянии между пиками
- Нормализованная корреляция между пиками цены и индикатора
- Диапазон: 0.0 (слабая) до 1.0 (сильная)

**Применение в торговле:**
- Фильтрация входов: принимать сигналы только при `divergence_strength > 0.5`
- Размер позиции: увеличивать для более сильных дивергенций
- Установка стопов: ориентироваться на `divergence_direction`

---

### Стратегии волатильности

#### CombinedVolatilityStrategy

**Алгоритм:** Комбинированная оценка через Bollinger Bands и ATR.

**Параметры:**
- `bb_window` (по умолчанию: 20): Окно для полос Боллинджера
- `bb_std` (по умолчанию: 2): Количество стандартных отклонений
- `atr_window` (по умолчанию: 14): Окно ATR
- `atr_multiplier` (по умолчанию: 1.0): Множитель ATR для диапазона

**Компоненты:**

**Bollinger Bands:**
- Метрики ширины: насколько широкие/узкие полосы
- Обнаружение сжатия: полосы сужаются
- Подсчет касаний: цена тестирует полосы

**ATR:**
- Нормализованный диапазон: диапазон зоны относительно типичного
- Тренд ATR: волатильность растет/снижается
- Постепенная деградация: оценки через True Range при отсутствии колонки ATR

**Показатель волатильности (0-10):**
Взвешенная комбинация:
- 40%: перцентиль ширины полос Боллинджера
- 30%: тренд ATR
- 30%: коэффициент сжатия

**Классификация режимов:**
- **Low (0-3):** Консолидация, торговля в диапазоне
- **Medium (3-6):** Нормальная волатильность, стандартные стратегии
- **High (6-8):** Повышенный риск, меньшие позиции
- **Extreme (8-10):** Кризисный режим, минимальная экспозиция

**Пример:**
```python
analyzer = ZoneFeaturesAnalyzer(volatility_strategy='combined')

features = analyzer.extract_zone_features(zone_dict)
vol = features.metadata['volatility_metrics']

print(f"Volatility score: {vol.volatility_score:.1f}/10")
print(f"Regime: {vol.volatility_regime}")
print(f"Bollinger width: {vol.bollinger_width_pct:.2%}")
print(f"Upper touches: {vol.bollinger_upper_touches}")

# Adaptive position sizing
if vol.volatility_regime == 'low':
    position_size = 2.0  # Larger position
elif vol.volatility_regime == 'medium':
    position_size = 1.0  # Normal
elif vol.volatility_regime == 'high':
    position_size = 0.5  # Smaller
else:  # extreme
    position_size = 0.25  # Minimal
```

---

### Стратегии объема

#### StandardVolumeStrategy

**Алгоритм:** Стандартный анализ объема с сопоставлением с базовым значением.

**Параметры:**
- `baseline_volume` (опционально): Эталонный объем для сравнения

**Метрики:**
- `volume_zone_ratio`: Объем зоны / базовый объем
- `volume_at_entry_change`: Изменение объема при входе в зону (%)
- `volume_indicator_corr`: Корреляция между объемом и индикатором ✨ **v2.1: универсальный**
- `avg_volume_zone`: Средний объем в зоне

**Постепенная деградация:**
- Работает без baseline (ratio = None)
- Работает без колонки объема (все метрики = None)
- Не падает при отсутствии данных

**Когда применять:**
- ✅ Подтверждать силу сигнала
- ✅ Определять накопление/распределение
- ✅ Дивергенции объема и цены
- ✅ Любой рынок с объемами

**Пример:**
```python
# Without baseline
analyzer = ZoneFeaturesAnalyzer(volume_strategy='standard')

# With baseline (e.g., overall average)
overall_avg_volume = data['volume'].mean()
strategy = create_volume_strategy('standard')
analyzer = ZoneFeaturesAnalyzer(volume_strategy=strategy)

features = analyzer.extract_zone_features(zone_dict)
vol = features.metadata.get('volume_metrics')

if vol:
    print(f"Volume ratio: {vol.volume_zone_ratio:.2f}")
    print(f"Volume-Indicator correlation: {vol.volume_indicator_corr:.2f}")  # v2.1: universal
    
    # Trading decision
    if vol.volume_zone_ratio > 1.5 and vol.volume_indicator_corr > 0.6:
        print("✅ Strong volume confirmation")
```

---

## Примеры использования

### Базовый: использование Universal Pipeline v2.1

```python
from bquant.analysis.zones import analyze_zones

# Universal Pipeline with strategies
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='zigzag', volatility='combined')
    .analyze(clustering=True)
    .build()
)

# Access metrics from first zone
zone = result.zones[0]
if zone.features:
    print(f"Duration: {zone.features.get('duration', 'N/A')}")
    print(f"Swings: {zone.features.get('num_swings', 0)}")
    print(f"Volatility: {zone.features.get('volatility_regime', 'unknown')}")
```

### Продвинутый: переключение стратегий в Universal Pipeline

```python
from bquant.analysis.zones import analyze_zones

# Try different swing strategies with Universal Pipeline
strategies = ['zigzag', 'find_peaks', 'pivot_points']

for strategy_name in strategies:
    result = (
        analyze_zones(df)
        .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(swing=strategy_name)
        .analyze(clustering=True)
        .build()
    )
    
    if result.zones and result.zones[0].features:
        features = result.zones[0].features
        print(f"\n{strategy_name}:")
        print(f"  Swings: {features.get('num_swings', 0)}")
        print(f"  Avg rally: {features.get('avg_rally_pct', 0):.2%}")
```

### Экспертный: A/B-тестирование стратегий в Universal Pipeline

```python
import pandas as pd
from bquant.analysis.zones import analyze_zones

# Test all swing strategies on multiple zones using Universal Pipeline
results = []

# Get base result for zone iteration
base_result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)
    .build()
)

for zone in base_result.zones[:10]:  # First 10 zones
    for strategy_name in ['zigzag', 'find_peaks', 'pivot_points']:
        # Re-analyze with specific strategy
        result = (
            analyze_zones(df)
            .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
            .detect_zones('zero_crossing', indicator_col='macd_hist')
            .with_strategies(swing=strategy_name)
            .analyze(clustering=True)
            .build()
        )
        
        # Find matching zone by time range
        matching_zone = None
        for z in result.zones:
            if (z.start_time == zone.start_time and z.end_time == zone.end_time):
                matching_zone = z
                break
        
        if matching_zone and matching_zone.features:
            results.append({
                'zone_id': zone.zone_id,
                'strategy': strategy_name,
                'num_swings': matching_zone.features.get('num_swings', 0),
                'avg_rally': matching_zone.features.get('avg_rally_pct', 0),
                'rally_count': matching_zone.features.get('rally_count', 0)
            })

# Analyze results
df_results = pd.DataFrame(results)
summary = df_results.groupby('strategy').agg({
    'num_swings': 'mean',
    'avg_rally': 'mean',
    'rally_count': 'mean'
})

print(summary)

# Choose best strategy for your needs
# - ZigZag: fewer, larger swings
# - FindPeaks: more, smaller swings
# - PivotPoints: balanced, validated swings
```

### Пользовательский: создание и использование собственной стратегии

```python
# 1. Create strategy
@StrategyRegistry.register_swing_strategy('threshold_based')
class ThresholdSwingStrategy:
    def __init__(self, threshold=0.02):
        self.threshold = threshold
    
    def calculate_swing(self, data):
        # Your algorithm
        return SwingMetrics(...)
    
    def get_name(self):
        return 'ThresholdBased'
    
    def get_metadata(self):
        return {'threshold': self.threshold}

# 2. Use it
analyzer = ZoneFeaturesAnalyzer(swing_strategy='threshold_based')

# 3. Or with custom parameters
strategy = ThresholdSwingStrategy(threshold=0.03)
analyzer = ZoneFeaturesAnalyzer(swing_strategy=strategy)
```

### Комбинация нескольких стратегий в Universal Pipeline

```python
# Use different strategies for different purposes with Universal Pipeline
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(
        swing='zigzag',         # For trend analysis
        shape='statistical',    # For clustering
        divergence='classic',   # For entries
        volatility='combined',  # For position sizing
        volume='standard'       # For confirmation
    )
    .analyze(clustering=True)
    .build()
)

# All strategies' results in zone.features
zone = result.zones[0]
if zone.features:
    print(f"Swing metrics: {zone.features.get('num_swings', 0)} swings")
    print(f"Shape metrics: {zone.features.get('hist_skewness', 0):.2f} skewness")
    print(f"Divergence: {zone.features.get('has_classic_divergence', False)}")
    print(f"Volatility: {zone.features.get('volatility_regime', 'unknown')}")
    print(f"Volume: {zone.features.get('volume_indicator_corr', 0):.2f} correlation")
```

---

## Сравнительная таблица стратегий

| Стратегия | Скорость | Детализация | Шум | Лучшее применение |
|-----------|----------|------------|-----|-------------------|
| **ZigZag** | Medium | Low | Low | Тренды, старшие ТФ |
| **FindPeaks** | Fast | High | High | Волатильные рынки, все экстремумы |
| **PivotPoints** | Medium | Medium | Low | Классический ТА |
| **Statistical** | Fast | N/A | N/A | Анализ формы |
| **Classic** | Medium | N/A | N/A | Дивергенции |
| **Combined** | Medium | High | N/A | Волатильность |
| **Standard** | Fast | Medium | N/A | Объем |

---

## 🔗 Связанные разделы

### 📚 Core API
- **[Universal Pipeline](pipeline.md)** - Полная документация Universal Pipeline v2.1
- **[Zone Features](zones.md)** - Универсальный API для анализа зон
- **[Statistical Analysis](statistical.md)** - Проверки гипотез и статистика
- **[Quick Start](../../user_guide/quick_start.md)** - Быстрый старт с Universal Pipeline

### 🎯 Learning Path
- **[Examples](../../examples/README.md)** - Готовые примеры использования
- **[Deep Dive Tutorial](../../research/notebooks/03_zones_universal.py)** - Подробный разбор
- **[Advanced Features](../../research/notebooks/03_analysis_new_features.py)** - Свинги, дивергенции, регрессия
- **[Migration Guide](../../examples/02_macd_zone_analysis.py)** - Переход с legacy API

### 🏗️ Developer Resources
- **[Architecture Patterns](../../developer_guide/README.md)** - Паттерны проектирования, точки расширения
- **[Testing Framework](../../tests/integration/)** - Интеграционные тесты, обратная совместимость
- **[Visualization](../../api/visualization/README.md)** - Визуализация зон, статистические графики
- **[Indicators](../../api/indicators/README.md)** - IndicatorFactory, пользовательские индикаторы

### 🔧 Technical Resources
- **Implementations:** `bquant/analysis/zones/strategies/`
- **Tests:** `tests/unit/test_*_strategy.py`
- **Technical docs:** `devref/archive/gaps/swing_detection_approaches.md`

