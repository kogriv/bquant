# Анализ универсальности инструментария для зонального анализа

**Дата:** 2025-10-13  
**Вопрос:** Насколько текущая реализация "заточена" под MACD? Можно ли использовать для других индикаторов (AO, Bollinger, кастомных)?

---

## Executive Summary

**Краткий ответ:** 🟡 **Частично универсальна, требует минимального рефакторинга**

**Текущее состояние:**
- ✅ **70-80% кода универсально** - стратегии, статистика, валидация, regression
- 🟡 **20-30% привязано к MACD** - ZoneFeatures, некоторые метрики
- ✅ **Архитектура готова** к универсализации через небольшой рефакторинг

**Усилия для адаптации:**
- **Минимальные (1-2 дня):** Для индикаторов со схожей структурой (AO, Stochastic)
- **Умеренные (3-5 дней):** Для индикаторов с другой структурой (Bollinger, Ichimoku)
- **Полная универсализация (1-2 недели):** Создание абстрактного базового класса

---

## 1. Детальный анализ компонентов

### 1.1. Универсальные компоненты (✅ готовы к использованию as-is)

#### A. Все стратегии (100% универсальны)

| Стратегия | Зависимость от MACD | Универсальность |
|-----------|---------------------|------------------|
| **SwingStrategy** | ❌ Нет | ✅ 100% - работает с любыми OHLC |
| **ShapeStrategy** | ❌ Нет* | ✅ 100% - работает с любым числовым рядом |
| **DivergenceStrategy** | ❌ Нет | ✅ 100% - сравнивает price с любым индикатором |
| **VolatilityStrategy** | ❌ Нет | ✅ 100% - Bollinger + ATR независимы |
| **VolumeStrategy** | ❌ Нет | ✅ 100% - работает с volume колонкой |

\* *ShapeStrategy рассчитывает skewness/kurtosis для колонки, которую вы передаете*

**Вывод:** Все 8 реализованных стратегий могут работать с любым индикатором без изменений!

#### B. Статистический анализ (95% универсален)

| Компонент | Зависимость от MACD | Требует изменений |
|-----------|---------------------|-------------------|
| **HypothesisTestSuite** | 🟡 Частичная | Минимальные |
| - H1 (Duration) | ❌ Нет | ✅ Готов |
| - H3 (Bull/Bear Asymmetry) | ❌ Нет | ✅ Готов |
| - H4 (Correlation-Drawdown) | 🟡 Использует `correlation_price_hist` | 🔧 Переименовать поле |
| - ADF (Stationarity) | ❌ Нет | ✅ Готов |
| - H5 (S/R Levels) | ❌ Нет | ✅ Готов |

**Изменения для H4:** Просто переименовать поле `correlation_price_hist` → `correlation_price_indicator`

#### C. Регрессия и валидация (100% универсальны)

| Компонент | Универсальность |
|-----------|-----------------|
| **ZoneRegressionAnalyzer** | ✅ 100% - работает с любыми признаками |
| **ValidationSuite** | ✅ 100% - агностичен к источнику данных |

#### D. Последовательности и кластеризация (90% универсальны)

| Компонент | Зависимость от MACD | Требует изменений |
|-----------|---------------------|-------------------|
| **ZoneSequenceAnalyzer** | 🟡 Частичная | Минимальные |
| - `analyze_zone_transitions()` | ❌ Нет | ✅ Готов |
| - `cluster_zones()` | 🟡 Default features list включает MACD | 🔧 Сделать configurable |

**Текущий код (`cluster_zones()`):**
```python
if features_to_use is None:
    features_to_use = [
        'duration', 'macd_amplitude', 'hist_amplitude',  # ← MACD-specific
        'price_range_pct', 'correlation_price_hist'      # ← MACD-specific
    ]
```

**Решение:** Передавать `features_to_use` извне или конфигурировать через config.

---

### 1.2. MACD-зависимые компоненты (требуют рефакторинга)

#### A. ZoneFeatures dataclass (🟡 частично MACD-specific)

**Проблемные поля (4 из 18):**

```python
@dataclass
class ZoneFeatures:
    # === УНИВЕРСАЛЬНЫЕ ПОЛЯ (14) ===
    zone_id: str                           # ✅ Универсально
    zone_type: str                         # ✅ Универсально
    duration: int                          # ✅ Универсально
    start_price: float                     # ✅ Универсально
    end_price: float                       # ✅ Универсально
    price_return: float                    # ✅ Универсально
    price_range_pct: float                 # ✅ Универсально
    atr_normalized_return: Optional[float] # ✅ Универсально
    num_peaks: Optional[int]               # ✅ Универсально
    num_troughs: Optional[int]             # ✅ Универсально
    drawdown_from_peak: Optional[float]    # ✅ Универсально
    rally_from_trough: Optional[float]     # ✅ Универсально
    peak_time_ratio: Optional[float]       # ✅ Универсально
    trough_time_ratio: Optional[float]     # ✅ Универсально
    
    # === MACD-СПЕЦИФИЧНЫЕ ПОЛЯ (4) ===
    macd_amplitude: float                  # 🔴 MACD-specific
    hist_amplitude: float                  # 🔴 MACD-specific
    correlation_price_hist: Optional[float]# 🔴 MACD-specific (название)
    hist_slope: Optional[float]            # 🔴 MACD-specific (название)
    
    metadata: Dict[str, Any]               # ✅ Универсально
```

**Проблема:** 4 поля жестко привязаны к MACD.

#### B. ZoneFeaturesAnalyzer.extract_zone_features() (🟡 частично MACD-specific)

**Проблемные строки:**

```python
def extract_zone_features(self, zone_info: Dict[str, Any]) -> ZoneFeatures:
    data = zone_info['data']
    
    # === MACD-специфичный код ===
    max_macd = float(data['macd'].max())                    # Требует 'macd' колонку
    min_macd = float(data['macd'].min())
    macd_amplitude = max_macd - min_macd
    
    max_hist = float(data['macd_hist'].max())               # Требует 'macd_hist' колонку
    min_hist = float(data['macd_hist'].min())
    hist_amplitude = max_hist - min_hist
    
    hist_slope = float(data['macd_hist'].diff().abs().max()) # Требует 'macd_hist' колонку
    
    # Корреляция цены и гистограммы
    correlation_price_hist = data['close'].corr(data['macd_hist'])  # Требует 'macd_hist'
    
    # === Универсальный код (остальное) ===
    # Все остальное работает только с OHLCV и ATR
```

**Проблема:** Hardcoded ссылки на колонки `'macd'` и `'macd_hist'`.

#### C. MACDZoneAnalyzer (🔴 полностью MACD-specific)

Этот класс **специально создан для MACD** и является:
- Facade над модульными анализаторами
- Zone detector для MACD индикатора
- Интеграционным слоем

**Роль:** Аналогичный класс нужен для каждого индикатора (AOZoneAnalyzer, BollingerZoneAnalyzer, etc.)

---

## 2. Рефакторинг для универсальности

### Вариант 1: Минимальный рефакторинг (быстро, для 1-2 индикаторов)

**Усилия:** 1-2 дня  
**Подходит для:** AO, Stochastic, CCI, Williams %R

#### Изменения:

**1. Сделать ZoneFeatures гибким (Option A: Simple)**

```python
@dataclass
class ZoneFeatures:
    # Базовые (всегда есть)
    zone_id: str
    zone_type: str
    duration: int
    start_price: float
    end_price: float
    price_return: float
    
    # Индикаторные метрики (Optional, переименовать)
    indicator_amplitude: Optional[float] = None      # было: macd_amplitude
    signal_amplitude: Optional[float] = None         # было: hist_amplitude
    correlation_price_indicator: Optional[float] = None  # было: correlation_price_hist
    signal_slope: Optional[float] = None             # было: hist_slope
    
    # Остальное универсально
    ...
```

**2. Параметризовать колонки в ZoneFeaturesAnalyzer**

```python
class ZoneFeaturesAnalyzer(BaseAnalyzer):
    def __init__(self, 
                 min_duration: int = 2,
                 min_amplitude: float = 0.001,
                 # NEW: Configurable columns
                 indicator_col: str = 'macd',        # какую колонку использовать для амплитуды
                 signal_col: str = 'macd_hist',      # какую колонку для signal/hist
                 # ... остальное
                 ):
        self.indicator_col = indicator_col
        self.signal_col = signal_col
```

**3. Обновить extract_zone_features()**

```python
def extract_zone_features(self, zone_info):
    data = zone_info['data']
    
    # Динамические колонки
    if self.indicator_col in data.columns:
        max_ind = float(data[self.indicator_col].max())
        min_ind = float(data[self.indicator_col].min())
        indicator_amplitude = max_ind - min_ind
    else:
        indicator_amplitude = None
    
    if self.signal_col in data.columns:
        max_sig = float(data[self.signal_col].max())
        min_sig = float(data[self.signal_col].min())
        signal_amplitude = max_sig - min_sig
        signal_slope = float(data[self.signal_col].diff().abs().max())
        correlation_price_indicator = data['close'].corr(data[self.signal_col])
    else:
        signal_amplitude = None
        signal_slope = None
        correlation_price_indicator = None
```

**4. Создать AOZoneAnalyzer (by analogy with MACDZoneAnalyzer)**

```python
class AOZoneAnalyzer:
    """Анализатор зон Awesome Oscillator."""
    
    def calculate_ao_with_atr(self, df):
        # Расчет AO и ATR
        pass
    
    def identify_zones(self, df):
        # Определение зон по знаку AO (аналогично MACD)
        pass
    
    def analyze_complete_modular(self, df):
        # Использует ZoneFeaturesAnalyzer с indicator_col='ao', signal_col='ao'
        features_analyzer = ZoneFeaturesAnalyzer(
            indicator_col='ao',
            signal_col='ao'  # AO не имеет отдельной гистограммы, используем сам AO
        )
        # ... остальное как в MACDZoneAnalyzer
```

**Результат:** Можно использовать для индикаторов со схожей структурой (осцилляторы).

---

### Вариант 2: Средний рефакторинг (оптимально, для любых индикаторов)

**Усилия:** 3-5 дней  
**Подходит для:** Любых индикаторов

#### Изменения:

**1. Создать базовый класс BaseZoneFeatures**

```python
@dataclass
class BaseZoneFeatures:
    """Универсальные признаки зоны (не зависят от индикатора)."""
    zone_id: str
    zone_type: str
    duration: int
    start_price: float
    end_price: float
    price_return: float
    price_range_pct: float
    atr_normalized_return: Optional[float] = None
    num_peaks: Optional[int] = None
    num_troughs: Optional[int] = None
    drawdown_from_peak: Optional[float] = None
    rally_from_trough: Optional[float] = None
    peak_time_ratio: Optional[float] = None
    trough_time_ratio: Optional[float] = None
    metadata: Dict[str, Any] = None


@dataclass
class IndicatorZoneFeatures(BaseZoneFeatures):
    """Признаки зоны с метриками индикатора."""
    indicator_amplitude: Optional[float] = None
    signal_amplitude: Optional[float] = None
    correlation_price_indicator: Optional[float] = None
    signal_slope: Optional[float] = None


# Backward compatibility alias
ZoneFeatures = IndicatorZoneFeatures
```

**2. Создать BaseZoneAnalyzer**

```python
class BaseZoneAnalyzer:
    """
    Базовый анализатор зон для любого индикатора.
    
    Подклассы должны реализовать:
    - calculate_indicator(df) -> df with indicator columns
    - identify_zones(df) -> List[ZoneInfo]
    - get_indicator_config() -> dict with column names
    """
    
    def __init__(self, indicator_params=None, zone_params=None):
        self.indicator_params = indicator_params or {}
        self.zone_params = zone_params or {}
        self.indicator_config = self.get_indicator_config()
    
    @abstractmethod
    def calculate_indicator(self, df: pd.DataFrame) -> pd.DataFrame:
        """Рассчитать индикатор и добавить колонки."""
        pass
    
    @abstractmethod
    def identify_zones(self, df: pd.DataFrame) -> List[ZoneInfo]:
        """Определить зоны на основе индикатора."""
        pass
    
    @abstractmethod
    def get_indicator_config(self) -> Dict[str, str]:
        """
        Вернуть конфигурацию колонок индикатора.
        
        Returns:
            {
                'indicator_col': 'name_of_main_indicator_column',
                'signal_col': 'name_of_signal_column',  # optional
                'required_cols': ['col1', 'col2']       # для валидации
            }
        """
        pass
    
    def analyze_complete_modular(self, df, perform_clustering=True, n_clusters=3):
        """Универсальный метод анализа (одинаков для всех индикаторов)."""
        # 1. Расчет индикатора
        df_with_indicator = self.calculate_indicator(df)
        
        # 2. Определение зон
        zones = self.identify_zones(df_with_indicator)
        
        # 3. Извлечение признаков через ZoneFeaturesAnalyzer
        features_analyzer = ZoneFeaturesAnalyzer(
            indicator_col=self.indicator_config['indicator_col'],
            signal_col=self.indicator_config.get('signal_col'),
            **self.zone_params
        )
        
        zones_features = []
        for zone in zones:
            zone_dict = self._zone_to_dict(zone)
            features = features_analyzer.extract_zone_features(zone_dict)
            zones_features.append(features)
        
        # 4-7. Остальное универсально
        # - HypothesisTestSuite
        # - ZoneSequenceAnalyzer
        # - ZoneRegressionAnalyzer
        # - ValidationSuite
        
        return ZoneAnalysisResult(...)
```

**3. Реализовать конкретные анализаторы**

```python
class MACDZoneAnalyzer(BaseZoneAnalyzer):
    def get_indicator_config(self):
        return {
            'indicator_col': 'macd',
            'signal_col': 'macd_hist',
            'required_cols': ['macd', 'signal', 'macd_hist']
        }
    
    def calculate_indicator(self, df):
        # Existing implementation
        return self.calculate_macd_with_atr(df)
    
    def identify_zones(self, df):
        # Existing implementation
        return self.identify_zones(df)


class AOZoneAnalyzer(BaseZoneAnalyzer):
    def get_indicator_config(self):
        return {
            'indicator_col': 'ao',
            'signal_col': 'ao',  # AO сам себе сигнал
            'required_cols': ['ao']
        }
    
    def calculate_indicator(self, df):
        # Расчет AO = SMA(median_price, 5) - SMA(median_price, 34)
        median_price = (df['high'] + df['low']) / 2
        df['ao'] = median_price.rolling(5).mean() - median_price.rolling(34).mean()
        return df
    
    def identify_zones(self, df):
        # Зоны по знаку AO (как у MACD)
        zones = []
        current_zone = None
        
        for idx, row in df.iterrows():
            if row['ao'] > 0:  # bull zone
                if current_zone is None or current_zone['type'] != 'bull':
                    if current_zone:
                        zones.append(ZoneInfo(**current_zone))
                    current_zone = {'type': 'bull', 'start_idx': idx, 'data': []}
            else:  # bear zone
                if current_zone is None or current_zone['type'] != 'bear':
                    if current_zone:
                        zones.append(ZoneInfo(**current_zone))
                    current_zone = {'type': 'bear', 'start_idx': idx, 'data': []}
            
            if current_zone:
                current_zone['data'].append(row)
        
        return zones


class BollingerZoneAnalyzer(BaseZoneAnalyzer):
    """
    Зоны на основе Bollinger Bands.
    
    Логика зон:
    - Bull zone: цена выше средней полосы
    - Bear zone: цена ниже средней полосы
    - Или: зоны касания верхней/нижней полос
    """
    
    def get_indicator_config(self):
        return {
            'indicator_col': 'bb_middle',
            'signal_col': 'bb_width',  # ширина полос как сигнал
            'required_cols': ['bb_upper', 'bb_middle', 'bb_lower']
        }
    
    def calculate_indicator(self, df):
        # Bollinger Bands
        sma = df['close'].rolling(20).mean()
        std = df['close'].rolling(20).std()
        df['bb_upper'] = sma + 2 * std
        df['bb_middle'] = sma
        df['bb_lower'] = sma - 2 * std
        df['bb_width'] = df['bb_upper'] - df['bb_lower']
        return df
    
    def identify_zones(self, df):
        # Зоны по положению цены относительно средней линии
        # (аналогично MACD/AO)
        pass
```

**Результат:** Полная универсальность, можно добавлять любые индикаторы.

---

### Вариант 3: Полная универсализация (максимальная гибкость)

**Усилия:** 1-2 недели  
**Подходит для:** Production-ready универсальная библиотека

#### Дополнительно к Варианту 2:

**1. Стратегия определения зон**

```python
class ZoneDetectionStrategy(Protocol):
    """Протокол для стратегий определения зон."""
    
    def detect_zones(self, df: pd.DataFrame) -> List[ZoneInfo]:
        """Определить зоны на данных."""
        ...


class SignChangeZoneDetection:
    """Зоны по смене знака индикатора (MACD, AO)."""
    def detect_zones(self, df, indicator_col='macd'):
        # Логика смены знака
        pass


class BandCrossZoneDetection:
    """Зоны по пересечению полос (Bollinger, Keltner)."""
    def detect_zones(self, df, price_col='close', band_col='bb_middle'):
        # Логика пересечения
        pass


class ThresholdZoneDetection:
    """Зоны по превышению порогов (RSI, Stochastic)."""
    def detect_zones(self, df, indicator_col='rsi', upper=70, lower=30):
        # Логика порогов
        pass
```

**2. Конфигурируемые features**

```python
@dataclass
class ZoneAnalysisConfig:
    """Конфигурация для анализа зон любого индикатора."""
    
    # Колонки данных
    price_cols: Dict[str, str] = field(default_factory=lambda: {
        'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close'
    })
    indicator_cols: Dict[str, str] = field(default_factory=dict)  # {'main': 'macd', 'signal': 'macd_hist'}
    
    # Стратегия определения зон
    zone_detection_strategy: ZoneDetectionStrategy = None
    
    # Метрики для расчета
    calculate_indicator_amplitude: bool = True
    calculate_signal_amplitude: bool = True
    calculate_correlation: bool = True
    calculate_slope: bool = True
    
    # Стратегии метрик
    swing_strategy: str = 'zigzag'
    shape_strategy: str = 'statistical'
    divergence_strategy: Optional[str] = None
    volatility_strategy: Optional[str] = None
    volume_strategy: Optional[str] = None


class UniversalZoneAnalyzer:
    """Универсальный анализатор зон для любого индикатора."""
    
    def __init__(self, config: ZoneAnalysisConfig):
        self.config = config
    
    def analyze(self, df: pd.DataFrame):
        # 1. Определение зон через стратегию
        zones = self.config.zone_detection_strategy.detect_zones(df)
        
        # 2. Извлечение признаков с учетом конфигурации
        features_analyzer = ZoneFeaturesAnalyzer(
            indicator_col=self.config.indicator_cols.get('main'),
            signal_col=self.config.indicator_cols.get('signal'),
            # ...
        )
        
        # 3. Остальное универсально
        pass
```

**Результат:** Production-ready универсальная система для любых индикаторов и методов зон.

---

## 3. Практические примеры адаптации

### Пример 1: Awesome Oscillator (AO) - Минимальный рефакторинг

**Что нужно:**
1. Создать `AOZoneAnalyzer` (копия MACDZoneAnalyzer с AO логикой)
2. Изменить 2 строки в `ZoneFeaturesAnalyzer.__init__()`:
   ```python
   indicator_col='ao'
   signal_col='ao'  # AO сам себе сигнал
   ```

**Что работает без изменений:**
- ✅ Все 8 стратегий (Swing, Shape, Divergence, Volatility, Volume)
- ✅ HypothesisTestSuite (все 5 тестов)
- ✅ ZoneSequenceAnalyzer
- ✅ ZoneRegressionAnalyzer
- ✅ ValidationSuite

**Усилия:** 4-6 часов

---

### Пример 2: Bollinger Bands - Средний рефакторинг

**Что нужно:**
1. Создать `BollingerZoneAnalyzer` с логикой определения зон
2. Определить что такое "amplitude":
   - Вариант A: ширина полос (`bb_width = upper - lower`)
   - Вариант B: отклонение цены от средней
3. Настроить `ZoneFeaturesAnalyzer`:
   ```python
   indicator_col='bb_middle'
   signal_col='bb_width'
   ```

**Логика зон:**
```python
def identify_zones(self, df):
    """
    Bull zone: close > bb_middle
    Bear zone: close < bb_middle
    """
    zones = []
    for ...:
        if df['close'] > df['bb_middle']:
            zone_type = 'bull'
        else:
            zone_type = 'bear'
```

**Что работает:**
- ✅ Swing, Volatility, Volume, Shape стратегии - без изменений
- ✅ Divergence - с модификацией (дивергенция между ценой и bb_middle)
- ✅ Все остальное без изменений

**Усилия:** 1-2 дня

---

### Пример 3: Custom индикатор - Полная универсализация

**Пример:** Ваш кастомный индикатор `MyIndicator` с сигнальной линией.

**Шаги:**
1. Реализовать подкласс `BaseZoneAnalyzer`:
   ```python
   class MyIndicatorZoneAnalyzer(BaseZoneAnalyzer):
       def get_indicator_config(self):
           return {
               'indicator_col': 'my_indicator',
               'signal_col': 'my_signal',
               'required_cols': ['my_indicator', 'my_signal']
           }
       
       def calculate_indicator(self, df):
           df['my_indicator'] = ...  # ваш расчет
           df['my_signal'] = ...     # ваша сигнальная линия
           return df
       
       def identify_zones(self, df):
           # ваша логика зон
           pass
   ```

2. Использовать:
   ```python
   analyzer = MyIndicatorZoneAnalyzer()
   result = analyzer.analyze_complete_modular(df)
   ```

**Что получаете:**
- ✅ Все стратегии
- ✅ Вся статистика
- ✅ Всю валидацию
- ✅ Все тесты

**Усилия:** 2-4 часа (только ваша логика индикатора и зон)

---

## 4. Рекомендации

### Для быстрого старта (сегодня-завтра):

1. **Используйте Вариант 1** (минимальный рефакторинг)
2. Создайте класс для вашего индикатора по аналогии с `MACDZoneAnalyzer`
3. Параметризуйте колонки при создании `ZoneFeaturesAnalyzer`
4. Все стратегии и анализаторы работают as-is

### Для production-ready решения (1-2 недели):

1. **Реализуйте Вариант 2** (средний рефакторинг)
2. Создайте `BaseZoneAnalyzer` с абстрактными методами
3. Рефакторите `ZoneFeatures` в `BaseZoneFeatures` + `IndicatorZoneFeatures`
4. Все новые индикаторы - простые подклассы

### Для универсальной библиотеки (будущее):

1. **Реализуйте Вариант 3** (полная универсализация)
2. Стратегии определения зон
3. Полностью конфигурируемые feature extraction
4. Plugin система для индикаторов

---

## 5. Миграционный путь (рекомендуемый)

### Этап 1: Backward compatibility (неделя 1)

1. Переименовать поля в `ZoneFeatures`:
   - `macd_amplitude` → `indicator_amplitude` (с alias для BC)
   - `hist_amplitude` → `signal_amplitude`
   - `correlation_price_hist` → `correlation_price_indicator`
   - `hist_slope` → `signal_slope`

2. Параметризовать колонки в `ZoneFeaturesAnalyzer`

3. Обновить `MACDZoneAnalyzer` для использования новых параметров

**Результат:** Все текущее работает + готовность к новым индикаторам

### Этап 2: Base classes (неделя 2)

1. Создать `BaseZoneAnalyzer`
2. Рефакторить `MACDZoneAnalyzer` как подкласс
3. Создать 1-2 примера (AOZoneAnalyzer, RSIZoneAnalyzer)

**Результат:** Архитектура готова для любых индикаторов

### Этап 3: Стратегии зон (неделя 3, optional)

1. `ZoneDetectionStrategy` протокол
2. Реализации для разных типов зон
3. Конфигурируемость через `ZoneAnalysisConfig`

**Результат:** Production-ready универсальная система

---

## 6. Заключение

### Ответы на вопросы:

**Q: Насколько "заточено" под MACD?**  
A: 70-80% кода универсально, 20-30% использует MACD-специфичные поля.

**Q: Можно ли использовать для других индикаторов?**  
A: ✅ **Да, с минимальными изменениями** (1-2 дня для большинства случаев).

**Q: Что работает без изменений?**  
A: ✅ Все стратегии, вся статистика, regression, validation.

**Q: Что требует рефакторинга?**  
A: 🔧 `ZoneFeatures` (4 поля), `ZoneFeaturesAnalyzer` (hardcoded колонки).

**Q: Как быстро адаптировать?**  
A:
- **AO, Stochastic:** 4-6 часов
- **Bollinger, Ichimoku:** 1-2 дня
- **Кастомный индикатор:** 2-4 часа (только логика индикатора)

### Итоговая оценка универсальности: 7.5/10

**Сильные стороны:**
- ✅ Стратегии полностью универсальны
- ✅ Статистика почти полностью универсальна
- ✅ Архитектура легко расширяемая

**Слабые стороны:**
- 🔧 Hardcoded MACD колонки в нескольких местах
- 🔧 MACD-специфичные названия полей
- 🔧 Нет базового класса для индикаторов

**Вывод:** Система **готова к универсализации** и требует минимальных усилий для адаптации под другие индикаторы. С рефакторингом на 1-2 недели станет полностью универсальной.

---

**Следующие шаги:**
1. Выбрать вариант рефакторинга (рекомендую Вариант 2)
2. Начать с Этапа 1 (backward compatibility)
3. Протестировать на 1-2 других индикаторах
4. Документировать extension guide

