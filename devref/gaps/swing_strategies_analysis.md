# Анализ инструментов для реализации Swing-стратегий

**Дата:** 2025-10-09  
**Задача:** Определить инструменты для реализации SwingCalculationStrategy (Фаза 3.1 из impl.md)

**Статус:** ⚠️ **УСТАРЕЛ** - данный документ содержит первичный анализ. Актуальные выводы и рекомендации см. в `swing_detection_approaches.md`

---

## Резюме

✅ **pandas-ta ZigZag ДОСТУПЕН** через систему BQuant (`LibraryManager`)  
✅ **scipy find_peaks УЖЕ ИСПОЛЬЗУЕТСЯ** в проекте  
❌ **Bollinger Bands НЕ ПОДХОДЯТ** для прямого определения свингов (индикатор волатильности)  
❌ **ATR НЕ ПОДХОДИТ** для прямого определения свингов (мера волатильности)  
✅ **Исправлен баг** в `bquant/indicators/library/manager.py` (передавал 'library' вместо library_name)

> **⚠️ ВАЖНОЕ ОБНОВЛЕНИЕ:** После детального анализа выяснилось, что Bollinger Bands и ATR **НЕ подходят** для определения свингов, так как это индикаторы **волатильности**, а не инструменты поиска пиков/впадин. 
>
> Детальный анализ правильности подходов и полноты метрик см. в **`devref/gaps/swing_detection_approaches.md`**

---

## 1. Доступные инструменты для Swing Detection

### 1.1. pandas-ta ZigZag (РЕКОМЕНДУЕТСЯ для базовой версии)

**Статус:** ✅ Работает через `LibraryManager`

**Как использовать:**
```python
from bquant.indicators import LibraryManager

zigzag = LibraryManager.create_indicator(
    'pandas_ta', 
    'zigzag',
    legs=10,        # Количество баров для подтверждения разворота
    deviation=0.05  # Минимальное отклонение в процентах (5%)
)

result = zigzag.calculate(zone_data)
# Результат содержит 3 колонки:
# - ZIGZAGs_<params>: направление свинга (-1 = вниз, 1 = вверх)
# - ZIGZAGv_<params>: значение цены в точке свинга
# - ZIGZAGd_<params>: расстояние/дистанция до предыдущего свинга
```

**Сигнатура функции:**
```python
zigzag(high, low, close=None, legs: int = None, 
       deviation: float = None, backtest: bool = None, 
       offset: int = None)
```

**Параметры:**
- `legs` (int): Количество баров для подтверждения пика/впадины
- `deviation` (float): Минимальное процентное отклонение (например, 0.05 = 5%)
- `backtest` (bool): Режим бэктестинга (None = авто)

**Преимущества:**
- Готовый, протестированный алгоритм
- Интеграция через систему пакета
- Настраиваемые параметры
- Выдает не только точки, но и направление/амплитуду

**Ограничения:**
- Требует настройки параметров под конкретный актив
- В текущем тесте с дефолтными параметрами выдал только 1 точку (нужна калибровка)

---

### 1.2. Bollinger Bands

**Статус:** ✅ Работает через `LibraryManager`

**Как использовать:**
```python
from bquant.indicators import LibraryManager

bbands = LibraryManager.create_indicator(
    'pandas_ta', 
    'bbands',
    length=20,  # Период скользящей средней
    std=2.0     # Количество стандартных отклонений
)

result = bbands.calculate(zone_data)
# Результат содержит:
# - BBL_<params>: нижняя полоса
# - BBM_<params>: средняя линия
# - BBU_<params>: верхняя полоса
```

**Стратегия определения свингов:**
- Пробитие верхней полосы = потенциальный пик
- Пробитие нижней полосы = потенциальная впадина
- Возврат внутрь полос = подтверждение разворота

---

### 1.3. ATR (Average True Range)

**Статус:** ✅ УЖЕ РАССЧИТЫВАЕТСЯ в `zone_data['atr']`

**Как использовать:**
```python
# ATR уже доступен в zone_data после calculate_macd_with_atr()
atr_threshold = zone_data['atr'].mean() * 1.5

# Определяем значимые свинги:
# - Если изменение цены > atr_threshold, это потенциальный свинг
```

**Стратегия определения свингов:**
- Вычислить среднее ATR для зоны
- Значимое движение = изменение цены > ATR × multiplier
- Искать локальные экстремумы среди значимых движений

---

## 2. scipy.signal.find_peaks

**Статус:** ✅ УЖЕ ИСПОЛЬЗУЕТСЯ в проекте (`bquant/analysis/zones/zone_features.py`)

**Как использовать:**
```python
from scipy.signal import find_peaks

# Найти пики (локальные максимумы)
peaks_idx, _ = find_peaks(zone_data['high'].values, prominence=threshold)

# Найти впадины (локальные минимумы)
troughs_idx, _ = find_peaks(-zone_data['low'].values, prominence=threshold)
```

**Преимущества:**
- Уже используется в пакете
- Быстрый, векторизованный
- Настраиваемый (prominence, distance, width)

**Ограничения:**
- НЕ классический ZigZag (находит ВСЕ локальные экстремумы)
- Требует постфильтрации по амплитуде движения

---

## 3. Рекомендуемый план реализации

### Фаза 3.1: ZigZagSwingStrategy (ПРИОРИТЕТ 1)

**Вариант A: Использование pandas-ta ZigZag (РЕКОМЕНДУЕТСЯ)**

```python
# bquant/analysis/zones/strategies/swing/zigzag.py

from dataclasses import dataclass
from typing import Dict, Any
import pandas as pd
from bquant.indicators import LibraryManager
from ..base import SwingMetrics, SwingCalculationStrategy

@dataclass
class ZigZagSwingStrategy(SwingCalculationStrategy):
    """
    Определение свингов через pandas-ta ZigZag.
    """
    legs: int = 10
    deviation: float = 0.05  # 5%
    
    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        """
        Вычисляет свинг-метрики через ZigZag.
        """
        # 1. Создать ZigZag индикатор
        zigzag = LibraryManager.create_indicator(
            'pandas_ta', 
            'zigzag',
            legs=self.legs,
            deviation=self.deviation
        )
        
        # 2. Вычислить ZigZag
        result = zigzag.calculate(zone_data)
        
        # 3. Извлечь свинг-точки
        swing_signal = result.data.iloc[:, 0]  # ZIGZAGs_<params>
        swing_values = result.data.iloc[:, 1]  # ZIGZAGv_<params>
        
        # 4. Найти изменения направления
        swings = swing_values.dropna()
        
        if len(swings) < 2:
            return SwingMetrics(
                rally_count=0, drop_count=0,
                avg_rally_pct=0.0, avg_drop_pct=0.0,
                max_rally_pct=0.0, max_drop_pct=0.0
            )
        
        # 5. Вычислить метрики
        rallies = []
        drops = []
        
        for i in range(1, len(swings)):
            price_change_pct = (swings.iloc[i] / swings.iloc[i-1] - 1) * 100
            
            if price_change_pct > 0:
                rallies.append(price_change_pct)
            else:
                drops.append(abs(price_change_pct))
        
        return SwingMetrics(
            rally_count=len(rallies),
            drop_count=len(drops),
            avg_rally_pct=sum(rallies) / len(rallies) if rallies else 0.0,
            avg_drop_pct=sum(drops) / len(drops) if drops else 0.0,
            max_rally_pct=max(rallies) if rallies else 0.0,
            max_drop_pct=max(drops) if drops else 0.0
        )
    
    def get_name(self) -> str:
        return f"zigzag_legs{self.legs}_dev{self.deviation}"
```

**Преимущества варианта A:**
- Готовое решение через pandas-ta
- Использует систему пакета
- Классический ZigZag алгоритм
- ~50-70 строк кода

**Параметры по умолчанию:**
- `legs=10`: Требуется 10 баров для подтверждения разворота
- `deviation=0.05`: Минимальное движение 5% для признания свинга

---

**Вариант B: Самописный ZigZag через find_peaks + фильтрация**

```python
# Псевдокод для справки

from scipy.signal import find_peaks

def calculate_zigzag_swings(zone_data, threshold_pct=0.02):
    # 1. Найти все локальные пики и впадины
    peaks, _ = find_peaks(zone_data['high'].values)
    troughs, _ = find_peaks(-zone_data['low'].values)
    
    # 2. Объединить и отсортировать по времени
    all_extrema = [(idx, 'peak', zone_data['high'].iloc[idx]) for idx in peaks] + \
                   [(idx, 'trough', zone_data['low'].iloc[idx]) for idx in troughs]
    all_extrema.sort(key=lambda x: x[0])
    
    # 3. Фильтровать: оставить только движения > threshold_pct
    filtered = []
    for i in range(1, len(all_extrema)):
        prev_price = all_extrema[i-1][2]
        curr_price = all_extrema[i][2]
        change_pct = abs(curr_price / prev_price - 1)
        
        if change_pct > threshold_pct:
            filtered.append(all_extrema[i])
    
    # 4. Вычислить метрики
    # ...
```

**Преимущества варианта B:**
- Полный контроль над алгоритмом
- Использует уже импортированный `find_peaks`

**Недостатки варианта B:**
- Больше кода (~100-150 строк)
- Нужно тестировать корректность
- Может давать ложные свинги

---

### Фаза 3.2: BollingerSwingStrategy (ПРИОРИТЕТ 2)

```python
# bquant/analysis/zones/strategies/swing/bollinger.py

@dataclass
class BollingerSwingStrategy(SwingCalculationStrategy):
    length: int = 20
    std: float = 2.0
    
    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        # 1. Вычислить Bollinger Bands
        bbands = LibraryManager.create_indicator(
            'pandas_ta', 'bbands',
            length=self.length, std=self.std
        )
        result = bbands.calculate(zone_data)
        
        # 2. Найти пробития полос
        upper = result.data.iloc[:, 2]  # BBU_<params>
        lower = result.data.iloc[:, 0]  # BBL_<params>
        
        upper_breaks = zone_data['close'] > upper
        lower_breaks = zone_data['close'] < lower
        
        # 3. Определить свинги между пробитиями
        # ...
```

**Параметры по умолчанию:**
- `length=20`: Период SMA
- `std=2.0`: 2 стандартных отклонения

---

### Фаза 3.3: ATRSwingStrategy (ПРИОРИТЕТ 3)

```python
# bquant/analysis/zones/strategies/swing/atr_based.py

@dataclass
class ATRSwingStrategy(SwingCalculationStrategy):
    multiplier: float = 1.5
    
    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        # ATR уже есть в данных!
        atr_threshold = zone_data['atr'].mean() * self.multiplier
        
        # Найти значимые движения (> ATR threshold)
        price_changes = zone_data['close'].diff().abs()
        significant = price_changes > atr_threshold
        
        # Определить свинги
        # ...
```

**Параметры по умолчанию:**
- `multiplier=1.5`: Движение > 1.5 × ATR считается значимым

---

## 4. Итоговые рекомендации (ОБНОВЛЕНО)

> **⚠️ ВАЖНО:** Данный раздел обновлен после детального анализа. Bollinger и ATR **ИСКЛЮЧЕНЫ** из SwingStrategies.

### ✅ Правильные подходы для определения свингов:

**См. детальный анализ в `devref/gaps/swing_detection_approaches.md` (разделы 1-3)**

1. **Реализовать `ZigZagSwingStrategy`** (pandas-ta) - **ПРИОРИТЕТ 1**
   - Простая интеграция через LibraryManager
   - Готовый, протестированный алгоритм
   - Параметры: `legs=10`, `deviation=0.05`
   - ~50-70 строк кода

2. **Реализовать `FindPeaksSwingStrategy`** (scipy) - **ПРИОРИТЕТ 2**
   - Использует `scipy.signal.find_peaks` (уже в проекте!)
   - Гибкая настройка параметров
   - Требует постфильтрации по амплитуде
   - ~70-100 строк кода

3. **Реализовать `PivotPointsSwingStrategy`** - **ПРИОРИТЕТ 3**
   - Классический N-bar pattern
   - Параметры: `left_bars=2`, `right_bars=2`
   - ~60-80 строк кода

4. **Опционально: `NBarSwingStrategy`** - обобщение Pivot
   - Асимметричное окно подтверждения
   - Более гибкая настройка

5. **Опционально: `FractalSwingStrategy`** - Williams Fractal
   - Фиксированный паттерн из 5 баров
   - Широко используется трейдерами

### ❌ ЧТО НЕ ДЕЛАТЬ:

- ~~`BollingerSwingStrategy`~~ - **ИСКЛЮЧЕНО**. Bollinger это индикатор волатильности, не подходит для поиска свингов
- ~~`ATRSwingStrategy`~~ - **ИСКЛЮЧЕНО**. ATR это мера волатильности, не подходит для поиска свингов

### ✅ Вместо этого - создать отдельные метрики волатильности:

- Создать `VolatilityMetrics` dataclass
- Создать `VolatilityStrategy` для расчета через Bollinger/ATR
- Использовать для оценки **волатильности зоны**, а не свингов

### Параметры по умолчанию (обновлено):

| Стратегия | Параметры | Значения |
|-----------|-----------|----------|
| ZigZag (pandas-ta) | `legs`, `deviation` | `10`, `0.05` (5%) |
| FindPeaks (scipy) | `prominence`, `distance`, `min_amplitude_pct` | TBD, TBD, `0.02` |
| Pivot Points | `left_bars`, `right_bars` | `2`, `2` |
| N-bar Swing | `left_bars`, `right_bars` | `3`, `2` |
| Fractal | фиксировано | 5 баров |

---

## 5. Исправленный баг

**Файл:** `bquant/indicators/library/manager.py`  
**Строка:** 162 (было), 161 (стало)

**Проблема:**
```python
# БЫЛО (неправильно):
return IndicatorFactory.create('library', full_name, **kwargs)
# Передавал 'library' вместо реального имени библиотеки
```

**Решение:**
```python
# СТАЛО (правильно):
return IndicatorFactory.create(library_name, indicator_name, **kwargs)
# Передает 'pandas_ta', 'zigzag'
```

**Результат:**  
✅ `LibraryManager.create_indicator('pandas_ta', 'zigzag')` теперь работает корректно

---

## 6. Следующие шаги (ОБНОВЛЕНО)

### Обязательные:

- [ ] Обновить `SwingMetrics` dataclass (+17 полей, см. `swing_detection_approaches.md`, раздел 5)
- [ ] Создать `bquant/analysis/zones/strategies/swing/zigzag.py` (ZigZagSwingStrategy)
- [ ] Создать `bquant/analysis/zones/strategies/swing/find_peaks.py` (FindPeaksSwingStrategy)
- [ ] Создать `bquant/analysis/zones/strategies/swing/pivot_points.py` (PivotPointsSwingStrategy)
- [ ] Зарегистрировать стратегии в `StrategyRegistry`
- [ ] Написать unit-тесты для каждой стратегии (проверка всех 23 полей SwingMetrics)
- [ ] Протестировать на реальных данных, подобрать параметры

### Создать метрики волатильности (вместо Bollinger/ATR свингов):

- [ ] Создать `VolatilityMetrics` dataclass в `strategies/base.py`
- [ ] Создать `VolatilityStrategy` для расчета через Bollinger/ATR
- [ ] Интегрировать в `ZoneFeaturesAnalyzer` как отдельную метрику (не в SwingMetrics!)

### Опционально:

- [ ] Реализовать `NBarSwingStrategy`
- [ ] Реализовать `FractalSwingStrategy`

---

## 7. Ссылки на связанные документы

- **Детальный анализ подходов:** `devref/gaps/swing_detection_approaches.md`
  - Раздел 1: Оценка предложенных подходов (почему Bollinger/ATR не подходят)
  - Раздел 2: Дополнительные подходы (Pivot Points, Fractal, N-bar)
  - Раздел 3: Итоговая таблица подходов
  - Раздел 4: Анализ полноты метрик (+17 полей)
  - Раздел 5: Обновленный SwingMetrics dataclass
  - Раздел 6: План действий

- **План реализации:** `devref/gaps/impl.md`
  - Раздел 6.3: Фаза 3.1 (детальный чек-лист)
  - Раздел 7.1.1: Спецификация метрик свингов
  - Раздел 7.6: Архитектура Strategy Pattern

---

**Вывод (обновлен):** 
- ✅ Правильные инструменты ДОСТУПНЫ: pandas-ta ZigZag, scipy find_peaks, Pivot Points
- ❌ Bollinger/ATR НЕ подходят для свингов - использовать для метрик волатильности
- ⚠️ Текущий SwingMetrics НЕПОЛНЫЙ - требуется +17 полей
- 📊 Рекомендуется начать с ZigZagSwingStrategy, затем FindPeaksSwingStrategy

