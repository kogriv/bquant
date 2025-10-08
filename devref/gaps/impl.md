# Анализ реализации методологии исследования в пакете BQuant

## Введение

Настоящий документ представляет собой анализ пакета `bquant` с целью определения, насколько полно в нем реализованы задачи, описанные в методологии исследования MACD ([research/methodology/macd_research.md](../../research/methodology/macd_research.md)). Анализ охватывает основные функциональные блоки пакета: технические индикаторы, статистические методы, зональный анализ и машинное обучение.

---

## 1. Общий вывод

Пакет `bquant` в значительной степени реализует большинство концепций, изложенных в методологии. Присутствуют модули для расчета всех ключевых индикаторов, проведения статистических тестов, анализа зон и применения методов машинного обучения.

### Ключевая архитектурная проблема

Наблюдается наличие **двух параллельных, частично дублирующих друг друга реализаций**:

1. **Модульная архитектура:** Набор узкоспециализированных, мощных и хорошо структурированных анализаторов в директории `bquant/analysis/`:
   - `ZoneFeaturesAnalyzer` — анализ признаков зон
   - `HypothesisTestSuite` — проверка гипотез
   - `ZoneSequenceAnalyzer` — анализ последовательностей и кластеризация

2. **Монолитная архитектура:** Крупный класс `MACDZoneAnalyzer` в `bquant/indicators/macd.py`, который объединяет в себе множество функций, но реализует их проще и менее гибко.

**Последствия дублирования:**
- Избыточность кода
- Потенциальные несоответствия между реализациями
- Усложнение поддержки и развития пакета
- `MACDZoneAnalyzer`, по-видимому, является наследием более раннего, скриптового подхода к анализу

**Статус рефакторинга:** 

> ✅ **Фаза 1 завершена** (2025-10-08): Создан метод `analyze_complete_modular()`, который использует модульные анализаторы. Результаты идентичны старой версии (подтверждено тестами). Подробности см. в разделе 6.3 и отчете `devref/gaps/phase1_completion_report.md`.

---

## 2. Анализ архитектуры пакета BQuant

Архитектура пакета `bquant` реализована на высоком качественном уровне, с соблюдением современных принципов проектирования ПО.

### 2.1. Сильные стороны

#### Четкая модульность и разделение ответственности (Separation of Concerns)

Проект имеет логичную структуру каталогов, где каждый компонент имеет свое место:
- `bquant/core`: Ядро системы (конфигурация, логирование, исключения, утилиты). Централизует общую функциональность и избегает дублирования кода.
- `bquant/indicators`: Все, что связано с техническими индикаторами. Есть четкое разделение на:
  - Базовые классы (`base.py`)
  - Загрузчики из внешних библиотек (`loaders.py`)
  - Конкретные реализации (`library.py`, `macd.py`)
  - Высокоуровневые калькуляторы (`calculators.py`)
- `bquant/analysis`: Модули для различных видов анализа (`zones`, `statistical` и т.д.). Каждый вид анализа вынесен в свой подпакет.
- `bquant/visualization`: Логика для построения графиков отделена от логики расчетов.
- `tests/`: Наличие отдельных каталогов для `unit` и `integration` тестов является стандартом хорошей практики.

#### Расширяемость и гибкость

- **Базовые классы:** Использование абстрактных базовых классов (`BaseIndicator`, `BaseAnalyzer`) позволяет легко добавлять новые индикаторы и методы анализа, сохраняя единый интерфейс.
- **Фабрика индикаторов (`IndicatorFactory`):** Применение паттерна "Фабрика" для создания индикаторов позволяет системе динамически работать с индикаторами из разных источников (встроенными, из библиотек, пользовательскими).
- **Загрузчики библиотек (`loaders.py`):** Система спроектирована для интеграции с популярными библиотеками (`pandas-ta`, `TA-Lib`).

#### Продуманная конфигурация и обработка ошибок

- **Централизованная конфигурация (`core/config.py`):** Все ключевые параметры (пути, параметры индикаторов, таймфреймы) вынесены в один файл.
- **Система логирования (`core/logging_config.py`):** Наличие централизованной и настраиваемой системы логирования — признак профессионального подхода.
- **Пользовательские исключения (`core/exceptions.py`):** Создание собственной иерархии исключений (например, `DataError`, `AnalysisError`).

#### Ориентация на производительность

В `core/performance.py` и `core/cache.py` заложены механизмы для:
- Мониторинга производительности
- Кэширования в памяти и на диске
- Использования оптимизированных `NumPy` функций

### 2.2. Области для развития (статус "в разработке")

- **Множество "заглушек" (Stubs):** Многие модули анализа (`candlestick`, `chart`, `technical`, `timeseries`) на данный момент являются заглушками. Фундамент для их реализации уже заложен.
- **ML-модуль:** Пакет `bquant/ml` также является заглушкой, что логично — машинное обучение является следующим шагом после построения базового аналитического инструментария.

**Вывод:** Архитектура `bquant` является зрелой, масштабируемой и хорошо продуманной. Она закладывает прочную основу для создания мощного и гибкого инструмента для количественных исследований.

---

## 3. Детальное сравнение с методологией исследования MACD

Пакет `bquant` в значительной степени реализует цели и задачи, изложенные в методологии анализа MACD. Видно, что документ `macd_research.md` служил прямым руководством для разработки модулей `analysis.zones`, `analysis.statistical` и `indicators.macd`.

### 3.1. Технический анализ

**Требования методологии:**
- MACD, SMA, EMA, RSI, Bollinger Bands
- Кастомные индикаторы

**Реализация в `bquant`:**
- **Полнота:** ✅ Высокая
- **Расположение:** `bquant/indicators/library.py`
- **Описание:** Все перечисленные индикаторы реализованы в виде классов, унаследованных от `PreloadedIndicator`. Архитектура `IndicatorFactory` (в `bquant/indicators/base.py`) позволяет легко регистрировать и использовать как встроенные, так и кастомные индикаторы.
- **Соответствие:** Реализация полностью соответствует требованиям методологии.

### 3.2. Сегментация на зоны

**Требования методологии:**
- Разбиение на зоны по знаку MACD
- Обработка пограничных случаев (минимальная длительность)
- Нормализация по ATR

**Реализация в `bquant`:**
- **Статус:** ✅ Полностью реализовано
- **Реализация:**
  - Класс `MACDZoneAnalyzer` (файл `bquant/indicators/macd.py`), метод `identify_zones`
  - Логика точно соответствует описанию: зоны определяются по смене знака линии MACD
  - Есть фильтрация по минимальной длительности
  - Реализован расчет ATR и его использование для нормализации признаков (например, `price_return_atr`)

### 3.3. Инжиниринг признаков (Feature Engineering)

**Реализовано (✅):**
- Базовые метрики: `duration`, `price_return`, `macd_amplitude`
- Уточненные метрики: `drawdown_from_peak`, `rally_from_trough`
- Метрики согласованности: `price_hist_corr` (корреляция цены и гистограммы)
- Анализ свингов (базовый): подсчет количества пиков и впадин (`num_peaks`, `num_troughs`)
- Метрики времени (частично): в `macd.py` есть расчет `peak_time_ratio`, `trough_time_ratio`

**Дублирование:**
- Класс `ZoneFeatures` в `bquant/analysis/zones/zone_features.py` и метод `calculate_zone_features` в `MACDZoneAnalyzer` рассчитывают одни и те же метрики

**Отсутствует (❌):**
- Продвинутый анализ свингов: средний/максимальный размер импульсов и коррекций, их соотношение (`rally_to_drop_ratio`)
- Метрики дивергенций: расчет типа и силы дивергенций
- Метрики объема: пакет на данный момент не использует данные по объему
- Продвинутые метрики формы: `skewness` и `kurtosis` для гистограммы MACD

### 3.4. Статистический анализ и проверка гипотез

**Реализация:**
- **Полнота:** ◐ Высокая, но фрагментированная
- **Расположение:**
  - `bquant/analysis/statistical/hypothesis_testing.py` (мощная, неиспользуемая реализация)
  - `bquant/indicators/macd.py` (упрощенная, используемая реализация)
  - `bquant/analysis/zones/zone_features.py` (анализ распределений)

**Описание:**
- `HypothesisTestSuite` — полноценный модуль для статистических тестов:
  - Расчет p-value, размера эффекта (Cohen's d)
  - Доверительные интервалы
  - Коррекция на множественные сравнения (Holm-Bonferroni)
  - **ПРОБЛЕМА:** Этот модуль не используется `MACDZoneAnalyzer`
- `MACDZoneAnalyzer` имеет собственный метод `test_hypotheses`:
  - Реализует только базовые t-тесты и корреляцию Пирсона без дополнительных метрик
- `ZoneFeaturesAnalyzer` предоставляет детальный анализ распределений (асимметрия и эксцесс)

**Реализовано (✅):**
- Описательные статистики: анализ распределений (среднее, медиана, std)
- Проверка гипотез для нескольких ключевых гипотез:
  - H1: Влияние длительности зоны на доходность
  - H3: Асимметрия между бычьими и медвежьими зонами
  - H4: Влияние корреляции на просадку (только в `macd.py`)
  - Случайность последовательностей зон

**Отсутствует (❌):**
- Тест на стационарность (ADF)
- H2: Гипотеза о наклоне гистограммы (тест есть, но неработоспособен — отсутствует признак `hist_slope`)
- H5: Гипотеза об уровнях поддержки/сопротивления

### 3.5. Зональный анализ

**Реализация:**
- **Полнота:** ◐ Высокая, но фрагментированная
- **Расположение:**
  - `bquant/analysis/zones/zone_features.py` (модульная реализация)
  - `bquant/indicators/macd.py` (монолитная реализация)

**Описание:**
- `MACDZoneAnalyzer` содержит методы `identify_zones` и `calculate_zone_features`
- `ZoneFeaturesAnalyzer` предлагает более структурированный подход с использованием дата-класса `ZoneFeatures` и более глубоким анализом
- Обе реализации покрывают требования методологии, но делают это параллельно

**Соответствие:** Высокое, но страдает от дублирования кода.

### 3.6. Моделирование и паттерн-анализ

**Реализация:**
- **Полнота:** ◐ Высокая, но фрагментированная
- **Расположение:**
  - `bquant/analysis/zones/sequence_analysis.py` (мощная реализация)
  - `bquant/indicators/macd.py` (упрощенная реализация)
  - `bquant/ml/` (пусто)

**Описание:**

`ZoneSequenceAnalyzer` — мощный модуль, который включает:
- Кластеризацию K-Means с нормализацией данных
- Оценку качества (Silhouette score)
- Анализ важности признаков
- Глубокий анализ последовательностей, включая цепи Маркова
- Поиск паттернов и тесты на случайность

`MACDZoneAnalyzer` также реализует кластеризацию и анализ последовательностей, но на базовом уровне, без продвинутых метрик и методов, описанных в `ZoneSequenceAnalyzer`.

**Реализовано (✅):**
- Цепи Маркова: базовый механизм для простых состояний "bull"/"bear"
- Кластеризация: реализована с помощью K-Means для группировки зон по признакам
- Анализ последовательностей: поиск N-грам (триплетов) и анализ серий

**Отсутствует (❌):**
- Регрессионное моделирование (OLS)
- Продвинутая кластеризация: не использует продвинутые признаки формы (`skewness`, `kurtosis`)
- Продвинутые состояния для цепей Маркова: не использует состояния "длинная бычья зона", "короткая медвежья зона"

### 3.7. Валидация и робастность

**Статус:** ❌ Не реализовано

В пакете отсутствуют встроенные инструменты для:
- Out-of-Sample валидации
- Walk-Forward валидации
- Анализа чувствительности к параметрам
- Бенчмаркинга

**Примечание:** Эти процессы предполагается выполнять вручную, используя библиотеку как инструмент. Валидация обычно является частью исследовательских скриптов, а не самого пакета.

---

## 4. Детальная таблица сравнения (Gap Analysis)

| Требование из методологии | Реализация в `MACDZoneAnalyzer` | Реализация в `bquant.analysis.*` | Статус и комментарии |
|:---|:---|:---|:---|
| **1. Сегментация зон** ||||
| Определение зон по знаку MACD | ✅ `identify_zones()` | ✅ (зоны передаются в анализаторы) | **OK** |
| Учет мин. длительности | ✅ параметр `min_duration` | ✅ `ZoneFeaturesAnalyzer` (`min_duration`) | **OK** |
| Нормализация по ATR | ✅ `calculate_macd_with_atr()` | ◐ `ZoneFeaturesAnalyzer` (использует ATR, если колонка уже есть) | **OK**. `MACDZoneAnalyzer` — основной исполнитель |
| **2. Инжиниринг признаков** ||||
| Базовые метрики (длительность, доходность, амплитуда) | ✅ `calculate_zone_features()` | ✅ `ZoneFeaturesAnalyzer.extract_zone_features()` | **Дублирование** |
| Просадка/отскок от пика/дна | ✅ `calculate_zone_features()` | ✅ `ZoneFeaturesAnalyzer.extract_zone_features()` | **Дублирование** |
| Корреляция цены и гистограммы | ✅ `calculate_zone_features()` | ✅ `ZoneFeaturesAnalyzer.extract_zone_features()` | **Дублирование** |
| Кол-во пиков/впадин (свинги) | ✅ `scipy.signal.find_peaks` | ✅ `scipy.signal.find_peaks` | **Дублирование** |
| Метрики времени (Time-to-peak ratio) | ✅ `peak_time_ratio`, `trough_time_ratio` | ❌ **Отсутствует** | **Пробел**. Только в `MACDZoneAnalyzer` |
| Продвинутый анализ свингов | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел**. Нет среднего размера ралли/откатов |
| Метрики дивергенций | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел** |
| Метрики объема | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел** |
| Метрики формы (Skew, Kurtosis) | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел** |
| **3. Статистический анализ** ||||
| Описательные статистики | ✅ `analyze_zones_distribution()` | ✅ `ZoneFeaturesAnalyzer.analyze_zones_distribution()` | **Дублирование** |
| Тест на стационарность (ADF) | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел** |
| **4. Проверка гипотез** ||||
| H1: Длина зоны vs. разворот | ✅ `test_hypotheses()` | ✅ `HypothesisTestSuite.test_zone_duration_hypothesis()` | **Дублирование** |
| H2: Наклон гистограммы vs. длина | ❌ **Отсутствует** | ◐ Тест есть, но требует `hist_slope` (не рассчитывается) | **Пробел**. Неработоспособный тест |
| H4: Корреляция vs. просадка | ✅ `test_hypotheses()` | ❌ **Отсутствует** | **Пробел**. Только в `MACDZoneAnalyzer` |
| H5: Уровни поддержки/сопротивления | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел** |
| **5. Моделирование** ||||
| Кластеризация (K-Means) | ✅ `cluster_zones_by_shape()` | ✅ `ZoneSequenceAnalyzer.cluster_zones()` | **Дублирование** |
| Цепи Маркова | ◐ Только переходы `bull`/`bear` | ✅ `_markov_chain_analysis()` (более полная версия) | **Частичная реализация**. Нет сложных состояний |
| Регрессия (OLS) | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел** |
| **6. Валидация** ||||
| Out-of-Sample / Walk-Forward | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел**. Нет встроенных инструментов |
| Анализ чувствительности | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел** |

---

## 5. Выводы и рекомендации

### 5.1. Итоговые выводы

1. **Фундамент заложен:** Основные механизмы для анализа зон MACD созданы и работают.

2. **Архитектурный долг:** Существование двух параллельных систем анализа (`MACDZoneAnalyzer` и `bquant.analysis`) является серьезной проблемой, которую нужно решать. Это приводит к:
   - Несоответствиям между реализациями
   - Усложнению поддержки
   - Путанице при выборе инструментов

3. **Значительные пробелы:** Наиболее продвинутые части методологии не реализованы:
   - Детали свингов
   - Дивергенции
   - Объем
   - Регрессия
   - ADF-тесты
   - Валидация

4. **Несоответствие реализаций:** Некоторые функции реализованы только в одном из двух мест, что делает модульный подход `bquant.analysis` неполным.

### 5.2. Рекомендации по рефакторингу

#### Первоочередная задача: Консолидация логики

Для устранения дублирования и улучшения архитектуры пакета `bquant` необходимо:

1. **Централизовать логику:** Модифицировать класс `MACDZoneAnalyzer` так, чтобы он не реализовывал логику анализа самостоятельно, а использовал специализированные анализаторы из `bquant/analysis/`:
   - Для расчета признаков зон — `ZoneFeaturesAnalyzer`
   - Для тестирования гипотез — `HypothesisTestSuite`
   - Для анализа последовательностей и кластеризации — `ZoneSequenceAnalyzer`

2. **Сделать `MACDZoneAnalyzer` оркестратором:** Класс должен стать оркестратором, который вызывает необходимые модули в правильном порядке, но не содержит сложной бизнес-логики. Его основная задача — управление процессом анализа от начала до конца.

3. **Удалить избыточный код:** После рефакторинга следует удалить дублирующие методы из `MACDZoneAnalyzer`:
   - `calculate_zone_features`
   - `test_hypotheses`
   - `analyze_zone_sequences`
   - `cluster_zones_by_shape`

   Оставить только вызовы к соответствующим модулям.

4. **Заполнить пробелы:** Необходимо реализовать отсутствующие компоненты:
   - Продвинутый анализ свингов
   - Метрики дивергенций
   - Метрики объема
   - Метрики формы (skewness, kurtosis)
   - Тест на стационарность (ADF)
   - Регрессионное моделирование
   - Инструменты валидации

Эти изменения позволят создать более поддерживаемую, модульную и расширяемую архитектуру, полностью соответствующую как духу, так и букве изложенной методологии исследования.

---

## 6. План практического рефакторинга

### 6.1. Анализ существующих интерфейсов

#### Текущие интерфейсы модульных анализаторов

**`ZoneFeaturesAnalyzer`:**
```python
# Вход: словарь zone_info с ключами:
{
    'zone_id': str/int,
    'type': 'bull'/'bear',
    'duration': int,
    'data': DataFrame  # с колонками: OHLCV + macd, macd_signal, macd_hist, atr
}

# Выход: объект ZoneFeatures с полями:
- zone_id, zone_type, duration
- start_price, end_price, price_return
- macd_amplitude, hist_amplitude, price_range_pct
- atr_normalized_return, correlation_price_hist
- num_peaks, num_troughs
- drawdown_from_peak (для bull), rally_from_trough (для bear)
- metadata: dict с дополнительными метриками
```

**`HypothesisTestSuite`:**
```python
# Вход: список словарей или объектов ZoneFeatures
zones_features: List[Dict[str, Any]]

# Методы возвращают: HypothesisTestResult с полями:
- hypothesis: str (описание гипотезы)
- test_type: str (тип теста)
- statistic: float
- p_value: float
- significant: bool
- effect_size: float
- metadata: dict
```

**`ZoneSequenceAnalyzer`:**
```python
# Вход: список ZoneFeatures или словарей
zones_features: List[Union[ZoneFeatures, Dict]]

# Выход: AnalysisResult с results содержащим:
- sequence_summary: {total_zones, total_transitions, ...}
- transitions: dict переходов
- transition_probabilities: dict вероятностей
- patterns: найденные паттерны
- markov_analysis: анализ цепей Маркова
```

#### Текущий интерфейс MACDZoneAnalyzer

**Метод `analyze_complete()`** возвращает `ZoneAnalysisResult`:
```python
ZoneAnalysisResult(
    zones: List[ZoneInfo],           # Список зон с данными
    statistics: Dict[str, Any],      # Статистики распределения
    hypothesis_tests: Dict[str, Any],# Результаты тестов
    clustering: Dict[str, Any],      # Результаты кластеризации
    sequence_analysis: Dict[str, Any],# Анализ последовательностей
    data: DataFrame,                 # Данные с индикаторами
    metadata: Dict[str, Any]         # Метаданные анализа
)
```

### 6.2. Стратегия минимальных изменений

**Ключевой инсайт:** Интерфейсы уже совместимы! Нужны только адаптеры для преобразования данных.

#### Этап 1: Подготовка (без breaking changes)

1. **Добавить вспомогательный метод конвертации `ZoneInfo` → словарь для анализаторов:**
   ```python
   def _zone_to_dict(self, zone: ZoneInfo) -> Dict[str, Any]:
       """Конвертация ZoneInfo в формат для модульных анализаторов."""
       return {
           'zone_id': zone.zone_id,
           'type': zone.type,
           'duration': zone.duration,
           'data': zone.data,
           # Добавляем features если есть
           **(zone.features or {})
       }
   ```

2. **Добавить метод конвертации результатов `ZoneFeatures` → словарь:**
   ```python
   def _features_to_dict(self, features: ZoneFeatures) -> Dict[str, Any]:
       """ZoneFeatures уже имеет метод to_dict(), используем его."""
       return features.to_dict()
   ```

#### Этап 2: Создание модульной версии (параллельно со старой)

1. **Создать новый метод `analyze_complete_modular()` рядом со старым `analyze_complete()`:**
   ```python
   def analyze_complete_modular(self, df: pd.DataFrame,
                               perform_clustering: bool = True,
                               n_clusters: int = 3) -> ZoneAnalysisResult:
       """
       Полный анализ зон с использованием модульных анализаторов.
       Новая версия - использует bquant.analysis.* вместо внутренних методов.
       """
       # 1. Расчет индикаторов и определение зон (без изменений)
       df_with_indicators = self.calculate_macd_with_atr(df)
       zones = self.identify_zones(df_with_indicators)

       if not zones:
           return self._empty_result(df_with_indicators)

       # 2. Расчет признаков через ZoneFeaturesAnalyzer
       from ..analysis.zones import ZoneFeaturesAnalyzer
       features_analyzer = ZoneFeaturesAnalyzer(
           min_duration=self.zone_params['min_duration']
       )

       zones_features = []
       for zone in zones:
           zone_dict = self._zone_to_dict(zone)
           zone_features = features_analyzer.extract_zone_features(zone_dict)
           zone.features = zone_features.to_dict()  # Сохраняем в zone
           zones_features.append(zone_features)

       # 3. Статистический анализ через ZoneFeaturesAnalyzer
       statistics = features_analyzer.analyze_zones_distribution(
           [f.to_dict() for f in zones_features]
       )

       # 4. Тестирование гипотез через HypothesisTestSuite
       from ..analysis.statistical import HypothesisTestSuite
       test_suite = HypothesisTestSuite(alpha=0.05)

       hypothesis_tests = {}
       features_dicts = [f.to_dict() for f in zones_features]

       # H1: Длительность vs доходность
       try:
           h1_result = test_suite.test_zone_duration_hypothesis(features_dicts)
           hypothesis_tests['zone_duration'] = h1_result.to_dict()
       except Exception as e:
           logger.warning(f"H1 test failed: {e}")

       # H3: Асимметрия bull/bear
       try:
           h3_result = test_suite.test_bull_bear_asymmetry_hypothesis(features_dicts)
           hypothesis_tests['bull_bear_asymmetry'] = h3_result.to_dict()
       except Exception as e:
           logger.warning(f"H3 test failed: {e}")

       # 5. Анализ последовательностей через ZoneSequenceAnalyzer
       from ..analysis.zones import ZoneSequenceAnalyzer
       sequence_analyzer = ZoneSequenceAnalyzer(min_sequence_length=3)

       sequence_result = sequence_analyzer.analyze_zone_transitions(zones_features)
       sequence_analysis = sequence_result.results

       # 6. Кластеризация через ZoneSequenceAnalyzer
       clustering = None
       if perform_clustering and len(zones) >= n_clusters:
           cluster_result = sequence_analyzer.cluster_zones(
               zones_features,
               n_clusters=n_clusters
           )
           clustering = cluster_result.results

       # 7. Формирование результата (тот же формат!)
       metadata = {
           'analysis_timestamp': datetime.now().isoformat(),
           'data_period': {
               'start': df.index[0].isoformat(),
               'end': df.index[-1].isoformat(),
               'total_bars': len(df)
           },
           'macd_params': self.macd_params,
           'zone_params': self.zone_params,
           'clustering_performed': clustering is not None,
           'modular_version': True  # Флаг новой версии
       }

       return ZoneAnalysisResult(
           zones=zones,
           statistics=statistics,
           hypothesis_tests=hypothesis_tests,
           clustering=clustering,
           sequence_analysis=sequence_analysis,
           data=df_with_indicators,
           metadata=metadata
       )
   ```

2. **Протестировать обе версии параллельно** и убедиться, что результаты идентичны

#### Этап 3: Миграция (постепенная замена)

1. **Обновить `analyze_complete()` чтобы внутри вызывал модульную версию:**
   ```python
   def analyze_complete(self, df: pd.DataFrame,
                       perform_clustering: bool = True,
                       n_clusters: int = 3) -> ZoneAnalysisResult:
       """
       Полный анализ зон MACD.
       DEPRECATED: Этот метод теперь вызывает analyze_complete_modular().
       """
       logger.info("Using modular analyzers (via analyze_complete_modular)")
       return self.analyze_complete_modular(df, perform_clustering, n_clusters)
   ```

2. **Пометить старые методы как deprecated:**
   ```python
   @deprecated("Use ZoneFeaturesAnalyzer.extract_zone_features() instead")
   def calculate_zone_features(self, zone: ZoneInfo) -> Dict[str, Any]:
       # Оставляем для обратной совместимости
       ...
   ```

#### Этап 4: Расширение функционала (заполнение пробелов)

**Добавить недостающие метрики в `ZoneFeaturesAnalyzer`:**

1. **Метрики времени (уже есть в MACDZoneAnalyzer, нужно перенести):**
   - `peak_time_ratio`
   - `trough_time_ratio`

2. **Метрики свингов (новые):**
   - `avg_rally_pct`, `avg_drop_pct`
   - `max_rally_pct`, `max_drop_pct`
   - `rally_to_drop_ratio`

3. **Метрики формы (новые):**
   - `hist_skewness` - асимметрия гистограммы
   - `hist_kurtosis` - эксцесс гистограммы

4. **Метрики дивергенций (новые):**
   - `divergence_type` - тип дивергенции
   - `divergence_strength` - сила дивергенции

5. **Метрики объема (новые, если данные доступны):**
   - `volume_zone_ratio`
   - `volume_macd_corr`

**Добавить недостающие тесты в `HypothesisTestSuite`:**

1. **H2: Наклон гистограммы** (нужно сначала добавить `hist_slope` в признаки)
2. **H4: Корреляция vs просадка** (уже есть данные, добавить тест)
3. **H5: Уровни поддержки/сопротивления** (новый функционал)
4. **ADF тест на стационарность** (новый тест)

**Добавить регрессионное моделирование:**

Создать новый класс `ZoneRegressionAnalyzer` в `bquant/analysis/statistical/`:
```python
class ZoneRegressionAnalyzer:
    """OLS регрессия для предсказания характеристик зон."""

    def predict_zone_duration(self, zones_features, ...):
        """Регрессия: duration ~ amplitude + volatility + prior_zone_length"""
        pass
```

**Добавить инструменты валидации:**

Создать новый модуль `bquant/analysis/validation/`:
```python
class ValidationSuite:
    """Инструменты для валидации моделей."""

    def out_of_sample_test(self, ...): pass
    def walk_forward_test(self, ...): pass
    def sensitivity_analysis(self, ...): pass
```

### 6.3. Порядок выполнения

**Фаза 1: Рефакторинг без breaking changes** ✅ **ЗАВЕРШЕНО**

> **Описание:** См. раздел 6.2 "Стратегия минимальных изменений", Этапы 1-2

1. [x] Создать адаптеры конвертации (`_zone_to_dict()`, `_features_to_dict()`)
2. [x] Реализовать `analyze_complete_modular()` в `MACDZoneAnalyzer`
3. [x] Добавить unit-тесты для сравнения результатов старой и новой версии
4. [x] Убедиться в идентичности результатов обеих версий

**Реализация:**
- Файл: `bquant/indicators/macd.py`
  - Добавлены методы: `_zone_to_dict()`, `_features_to_dict()`, `_adapt_statistics_format()`
  - Добавлен метод: `analyze_complete_modular()` (строки 758-900)
- Файл: `tests/unit/test_macd_analyzer.py`
  - Добавлен класс: `TestModularAnalyzer` с 4 тестами
  - Все тесты пройдены успешно (4/4)

**Результат тестирования:**
- ✅ Количество зон: идентично
- ✅ Типы зон: идентичны
- ✅ Длительности зон: идентичны
- ✅ Статистики распределения: идентичны
- ✅ Значения признаков: идентичны (11 общих признаков)

**Вывод:** Модульная версия работает корректно и дает идентичные результаты со старой версией.

**Фаза 2: Миграция**

> **Описание:** См. раздел 6.2 "Стратегия минимальных изменений", Этап 3

1. [ ] Обновить `analyze_complete()` для использования модульной версии внутри
2. [ ] Пометить старые методы как deprecated (`@deprecated` декоратор)
3. [ ] Обновить документацию и примеры использования

**Фаза 3: Расширение функционала**

**Фаза 3.0: Инфраструктура расширяемых метрик**

> **Описание:** См. раздел 7.6 "Архитектура расширяемых метрик (Strategy Pattern)", подразделы 7.6.1-7.6.4

1. [ ] Создать структуру папок `bquant/analysis/zones/strategies/` (см. 7.6.2)
2. [ ] Реализовать `base.py` с протоколами и датаклассами (SwingMetrics, DivergenceMetrics, ShapeMetrics, VolumeMetrics) (см. 7.6.4)
3. [ ] Реализовать `registry.py` с декораторами регистрации и реестром стратегий (см. 7.6.4)
4. [ ] Создать фабрики в `bquant/core/config.py` (create_swing_strategy, create_divergence_strategy и т.д.) (см. 7.6.4)
5. [ ] Добавить конфигурацию стратегий в `ANALYSIS_CONFIG` (см. 7.6.6)
6. [ ] Обновить `ZoneFeaturesAnalyzer.__init__()` для приема стратегий через параметры (см. 7.6.5)
7. [ ] Написать unit-тесты для инфраструктуры (проверка контрактов протоколов)

**Критерии готовности Фазы 3.0:**
- [ ] Можно зарегистрировать стратегию через `@StrategyRegistry.register_swing_strategy('name')`
- [ ] `ZoneFeaturesAnalyzer` принимает стратегии в конструкторе
- [ ] Фабрики создают стратегии из config
- [ ] Тесты проверяют контракты протоколов

**Фаза 3.1: Swing стратегии**

> **Описание:** См. раздел 7.1.1 "Метрики свингов (Swing Metrics)" и раздел 7.6.4 для примера реализации

1. [ ] Реализовать `ZigZagSwingStrategy` (базовая версия) в `strategies/swing/zigzag.py`
2. [ ] Реализовать `BollingerSwingStrategy` в `strategies/swing/bollinger.py`
3. [ ] Реализовать `ATRSwingStrategy` в `strategies/swing/atr.py`
4. [ ] Интегрировать в `ZoneFeaturesAnalyzer.extract_zone_features()` (см. 7.6.5)
5. [ ] Unit-тесты для каждой стратегии
6. [ ] Провести A/B тестирование стратегий (см. 7.6.6, вариант 2)

**Фаза 3.2: Shape стратегии**

> **Описание:** См. раздел 7.1.2 "Метрики формы (Shape Metrics)" и раздел 7.6.4

1. [ ] Реализовать `StatisticalShapeStrategy` (skewness, kurtosis) в `strategies/shape/statistical.py`
2. [ ] Интегрировать в `ZoneFeaturesAnalyzer.extract_zone_features()` (см. 7.6.5)
3. [ ] Unit-тесты для стратегии
4. [ ] Опционально: `FourierShapeStrategy` в `strategies/shape/fourier.py`

**Фаза 3.3: Метрики времени**

> **Описание:** См. раздел 3.3 "Инжиниринг признаков (Feature Engineering)", таблица Gap Analysis (строка "Метрики времени")

1. [ ] Перенести `peak_time_ratio` и `trough_time_ratio` из `MACDZoneAnalyzer` в `ZoneFeaturesAnalyzer`
2. [ ] Unit-тесты для метрик времени

**Фаза 3.4: Divergence стратегии**

> **Описание:** См. раздел 7.1.3 "Метрики дивергенций (Divergence Metrics)" и раздел 7.6.4

1. [ ] Реализовать `ClassicDivergenceStrategy` в `strategies/divergence/classic.py`
2. [ ] Интегрировать в `ZoneFeaturesAnalyzer.extract_zone_features()` (см. 7.6.5)
3. [ ] Unit-тесты для стратегии
4. [ ] Опционально: `RSIDivergenceStrategy` в `strategies/divergence/rsi.py`

**Фаза 3.5: Volume стратегии (опционально)**

> **Описание:** См. раздел 7.1.4 "Метрики объема (Volume Metrics)" и раздел 7.6.4

1. [ ] Реализовать `StandardVolumeStrategy` в `strategies/volume/standard.py`
2. [ ] Интегрировать в `ZoneFeaturesAnalyzer.extract_zone_features()` (см. 7.6.5)
3. [ ] Unit-тесты для стратегии
4. [ ] Опционально: `VWAPVolumeStrategy` в `strategies/volume/vwap.py`

**Фаза 3.6: Гипотезные тесты**

> **Описание:** См. раздел 7.2 "Новые гипотезные тесты в HypothesisTestSuite"

1. [ ] H2: Реализовать тест наклона гистограммы (см. 7.2.1) - предварительно добавить `hist_slope` в признаки
2. [ ] H4: Реализовать тест корреляции vs просадки (см. 7.2.2)
3. [ ] ADF: Реализовать тест на стационарность (см. 7.2.4)
4. [ ] Опционально: H5 - тест уровней поддержки/сопротивления (см. 7.2.3)

**Фаза 3.7: Моделирование и валидация (опционально)**

> **Описание:** См. раздел 7.3 "Новые анализаторы"

1. [ ] Создать `ZoneRegressionAnalyzer` в `bquant/analysis/statistical/regression.py` (см. 7.3.1)
2. [ ] Создать `ValidationSuite` в `bquant/analysis/validation/suite.py` (см. 7.3.2)

**Фаза 4: Очистка**

> **Описание:** См. раздел 6.2 "Стратегия минимальных изменений", Этап 4: Расширение функционала

1. [ ] Удалить deprecated методы из `MACDZoneAnalyzer` (после подтверждения что все работает)
2. [ ] Обновить все unit и integration тесты
3. [ ] Провести финальную проверку совместимости и производительности

### 6.4. Критерии успеха

1. **API совместимость:** `analyze_complete()` возвращает тот же формат результатов
2. **Функциональная полнота:** Все метрики из методологии реализованы
3. **Нет дублирования:** Логика анализа находится только в `bquant/analysis/`
4. **Тесты проходят:** 100% покрытие тестами для новых компонентов
5. **Документация обновлена:** Все изменения задокументированы

### 6.5. Минимальный набор изменений для старта

Если нужно начать немедленно, достаточно:

1. **Добавить метод `_zone_to_dict()` в `MACDZoneAnalyzer`** (5 строк кода)
2. **Создать `analyze_complete_modular()` в `MACDZoneAnalyzer`** (~50 строк кода)
3. **Написать unit-тест сравнения результатов** (~30 строк кода)

**Итого: ~100 строк кода для полной интеграции без breaking changes!**

Остальное можно делать постепенно, по мере необходимости.

---

## 7. Спецификации недостающих компонентов

Этот раздел содержит детальные спецификации для компонентов, которые будут реализованы в **Фазе 3 (Расширение функционала)** после завершения рефакторинга.

### 7.1. Расширение метрик в ZoneFeaturesAnalyzer

#### 7.1.1. Метрики свингов (Swing Metrics)

> **⚠️ Архитектурное примечание:** Данные метрики должны быть реализованы через паттерн **Strategy** согласно разделу 7.6. Базовая реализация - `ZigZagSwingStrategy`, расширения - `BollingerSwingStrategy`, `ATRSwingStrategy`. См. раздел 7.6.10 для порядка реализации.

**Назначение:** Детальный анализ внутренней структуры ценового движения в зоне для оценки характера тренда (плавный vs "рваный").

**Входные данные:**
- `zone_data: DataFrame` с колонками `high`, `low`, `close`
- Параметры для ZigZag алгоритма (например, `min_swing_threshold=0.02` - минимум 2% движения)

**Алгоритм:**
1. Применить ZigZag или `scipy.signal.find_peaks` для выделения локальных экстремумов
2. Идентифицировать свинги (импульсы вверх и коррекции вниз для бычьей зоны)
3. Рассчитать амплитуды каждого свинга в процентах от цены
4. Агрегировать статистики

**Выходные данные (добавить в ZoneFeatures):**
```python
num_swings: int               # Количество свингов (пар импульс+коррекция)
avg_rally_pct: float         # Средняя амплитуда импульсов вверх (%)
avg_drop_pct: float          # Средняя амплитуда коррекций вниз (%)
max_rally_pct: float         # Максимальный импульс вверх (%)
max_drop_pct: float          # Максимальная коррекция вниз (%)
rally_to_drop_ratio: float   # Отношение avg_rally / avg_drop
```

**Интерпретация:**
- `num_swings > 5` → "рваное" движение, высокая волатильность
- `rally_to_drop_ratio > 2.5` → сильный тренд (импульсы больше коррекций)
- `rally_to_drop_ratio < 1.5` → слабый тренд или боковик

**Связь с методологией:** Раздел "2. Анализ свингов (Swing Analysis)" в macd_research.md

---

#### 7.1.2. Метрики формы (Shape Metrics)

> **⚠️ Архитектурное примечание:** Данные метрики должны быть реализованы через паттерн **Strategy** согласно разделу 7.6. Базовая реализация - `StatisticalShapeStrategy` (skewness/kurtosis), расширения - `FourierShapeStrategy`, `WaveletShapeStrategy`. См. раздел 7.6.10 для порядка реализации.

**Назначение:** Классификация формы "бугра" гистограммы MACD для выявления архетипов зон.

**Входные данные:**
- `zone_data['macd_hist']: Series` - гистограмма MACD для зоны

**Алгоритм:**
1. Рассчитать асимметрию (skewness) гистограммы
2. Рассчитать эксцесс (kurtosis) гистограммы
3. Опционально: гладкость кривой `smoothness = std(histogram.diff())`

**Выходные данные (добавить в ZoneFeatures):**
```python
hist_skewness: float    # Асимметрия: <0 - пик в конце, >0 - пик в начале
hist_kurtosis: float    # Эксцесс: >3 - острый пик, <3 - плоский бугор
hist_smoothness: float  # Std производной (опционально)
```

**Интерпретация:**
- `skewness > 0.5` → "Ранний импульс" (пик в начале зоны)
- `skewness < -0.5` → "Поздний импульс" (пик в конце зоны)
- `kurtosis > 5` → "Резкий импульс" (острый пик)
- `kurtosis < 1` → "Плавная волна" (широкий плоский бугор)

**Использование для кластеризации:**
После расчета этих метрик можно применить K-Means для группировки зон в архетипы:
- Кластер 1: "Резкий ранний импульс" (skew>0, kurt>5)
- Кластер 2: "Плавный тренд" (skew≈0, kurt<3)
- Кластер 3: "Затухающая волна" (skew<0, kurt средний)

**Связь с методологией:** Раздел "3.5.а) Классификация формы зоны" в macd_research.md

---

#### 7.1.3. Метрики дивергенций (Divergence Metrics)

> **⚠️ Архитектурное примечание:** Данные метрики должны быть реализованы через паттерн **Strategy** согласно разделу 7.6. Базовая реализация - `ClassicDivergenceStrategy`, расширения - `RSIDivergenceStrategy`, `HiddenDivergenceStrategy`. См. раздел 7.6.10 для порядка реализации.

**Назначение:** Обнаружение и количественная оценка дивергенций между ценой и MACD.

**Входные данные:**
- `zone_data: DataFrame` с колонками `close`, `high`, `low`, `macd`, `macd_hist`
- `zone_type: str` ('bull' или 'bear')

**Алгоритм:**
1. Найти локальные экстремумы цены (пики для bull, впадины для bear)
2. Найти соответствующие экстремумы MACD в те же моменты времени
3. Сравнить направления:
   - **Регулярная дивергенция:** цена обновляет экстремум, MACD - нет
   - **Скрытая дивергенция:** MACD обновляет экстремум, цена - нет
4. Рассчитать силу: `|price_slope - macd_slope| * duration`

**Выходные данные (добавить в ZoneFeatures):**
```python
divergence_type: str       # 'none', 'regular', 'hidden', 'mixed'
divergence_count: int      # Количество дивергенций в зоне
divergence_strength: float # Средняя сила дивергенций
divergence_direction: str  # 'bullish', 'bearish', 'none'
```

**Интерпретация:**
- `divergence_type='regular'` + `zone_type='bull'` → Вероятный разворот вниз
- `divergence_strength > 0.5` → Сильная дивергенция, высокая вероятность разворота
- `divergence_count > 2` → Множественные дивергенции, усиленный сигнал

**Связь с методологией:** Раздел "3.4 Метрики дивергенций" в macd_research.md

---

#### 7.1.4. Метрики объема (Volume Metrics)

> **⚠️ Архитектурное примечание:** Данные метрики должны быть реализованы через паттерн **Strategy** согласно разделу 7.6. Базовая реализация - `StandardVolumeStrategy`, расширения - `VWAPVolumeStrategy`, `OBVVolumeStrategy`. См. раздел 7.6.10 для порядка реализации.

**Назначение:** Анализ объемов торгов для подтверждения силы движения в зоне.

**Входные данные:**
- `zone_data: DataFrame` с колонкой `volume`
- `baseline_volume: float` - средний объем за N предыдущих периодов (например, 50 баров)

**Условия применения:**
- Рассчитывается **только если** колонка `volume` присутствует и не пустая
- Если данных нет, метрики = `None`

**Алгоритм:**
1. Рассчитать средний объем в зоне
2. Сравнить с baseline
3. Рассчитать корреляцию между объемом и гистограммой MACD

**Выходные данные (добавить в ZoneFeatures):**
```python
volume_zone_ratio: Optional[float]      # Отношение avg_volume_in_zone / baseline_volume
volume_at_entry_change: Optional[float] # % изменение объема при входе в зону
volume_macd_corr: Optional[float]       # Корреляция между volume и macd_hist
avg_volume_zone: Optional[float]        # Средний объем в зоне
```

**Интерпретация:**
- `volume_zone_ratio > 1.5` → Повышенный интерес, сильное движение
- `volume_zone_ratio < 0.7` → Низкий интерес, слабое движение
- `volume_macd_corr > 0.6` → Объем подтверждает сигнал MACD (хорошо)
- `volume_macd_corr < 0.2` → Объем не подтверждает MACD (плохо, ложный сигнал)

**Связь с методологией:** Раздел "3.5 Метрики объема" в macd_research.md

---

### 7.2. Новые гипотезные тесты в HypothesisTestSuite

#### 7.2.1. H2: Тест наклона гистограммы

**Гипотеза:** "Зоны с крутым наклоном гистограммы MACD короче, чем зоны с плавным наклоном"

**Требования:**
1. Сначала добавить расчет `hist_slope` в `ZoneFeaturesAnalyzer.extract_zone_features()`:
   ```python
   # Наклон гистограммы = максимальное изменение за 1 период
   hist_slope = zone_data['macd_hist'].diff().abs().max()
   ```

**Метод теста:**
```python
def test_histogram_slope_hypothesis(self, zones_features: List[Dict]) -> HypothesisTestResult:
    """
    H0: Наклон гистограммы не влияет на длительность зоны
    H1: Крутой наклон → короткие зоны
    """
    # 1. Разделить зоны на steep (верхние 20% по hist_slope) и gentle (нижние 20%)
    # 2. Сравнить средние длительности (t-test)
    # 3. Рассчитать корреляцию Пирсона между hist_slope и duration
```

**Интерпретация результата:**
- `p_value < 0.05` + `negative correlation` → Гипотеза подтверждена
- Практическое применение: Если гистограмма резко растет → готовиться к скорому развороту

**Связь с методологией:** Гипотеза 2 в разделе "2. Проверка гипотез" в macd_research.md

---

#### 7.2.2. H4: Тест корреляции vs просадка

**Гипотеза:** "Зоны с высокой корреляцией между ценой и гистограммой MACD имеют меньшую просадку"

**Данные уже есть:**
- `correlation_price_hist` - уже рассчитывается
- `drawdown_from_peak` (для bull), `rally_from_trough` (для bear) - уже рассчитываются

**Метод теста:**
```python
def test_correlation_drawdown_hypothesis(self, zones_features: List[Dict]) -> HypothesisTestResult:
    """
    H0: Корреляция цены и MACD не влияет на просадку
    H1: Высокая корреляция → меньшая просадка
    """
    # Для бычьих зон:
    # 1. Разделить на high_corr (>0.7) и low_corr (<0.3)
    # 2. Сравнить средние drawdown_from_peak (t-test)
    # 3. Рассчитать effect size (Cohen's d)
```

**Интерпретация результата:**
- `p_value < 0.05` + `high_corr имеют меньший drawdown` → Гипотеза подтверждена
- Практическое применение: Использовать `correlation_price_hist` как фильтр качества сигнала

**Связь с методологией:** Гипотеза 4 в разделе "2. Проверка гипотез" в macd_research.md

---

#### 7.2.3. H5: Тест уровней поддержки/сопротивления

**Гипотеза:** "Зоны, начинающиеся у уровней поддержки/сопротивления, имеют иную длительность"

**Требования:**
1. Определить метод идентификации уровней (например, Pivot Points или локальные экстремумы за последние N баров)
2. Добавить в `ZoneFeaturesAnalyzer` проверку: начинается ли зона вблизи уровня (tolerance ±0.5% от цены)

**Метод теста:**
```python
def test_support_resistance_hypothesis(self, zones_features: List[Dict],
                                       price_levels: List[float]) -> HypothesisTestResult:
    """
    H0: Близость к уровням не влияет на длительность зоны
    H1: Зоны от уровней длиннее/короче

    Args:
        price_levels: Список идентифицированных уровней поддержки/сопротивления
    """
    # 1. Для каждой зоны определить: началась ли она у уровня (tolerance=0.5%)
    # 2. Разделить зоны на near_level и far_from_level
    # 3. Сравнить длительности (t-test или Mann-Whitney)
```

**Интерпретация результата:**
- `p_value < 0.05` → Уровни значимо влияют на характер зон
- Практическое применение: Учитывать уровни при прогнозировании длительности зоны

**Связь с методологией:** Гипотеза 5 в разделе "2. Проверка гипотез" в macd_research.md

---

#### 7.2.4. ADF тест на стационарность

**Назначение:** Проверить, меняется ли средняя длительность зон со временем (смена рыночного режима).

**Метод теста:**
```python
def test_zone_duration_stationarity(self, zones_features: List[Dict]) -> HypothesisTestResult:
    """
    Augmented Dickey-Fuller тест для проверки стационарности длительности зон.

    H0: Ряд длительностей нестационарный (среднее меняется во времени)
    H1: Ряд стационарный (среднее постоянно)
    """
    from statsmodels.tsa.stattools import adfuller

    # 1. Извлечь временной ряд длительностей зон
    durations = [z['duration'] for z in zones_features]

    # 2. Применить ADF тест
    adf_result = adfuller(durations, autolag='AIC')

    # 3. Интерпретировать результат
    # p_value < 0.05 → отклоняем H0 → ряд стационарный
```

**Интерпретация результата:**
- `p_value > 0.05` (H0 не отвергается) → Ряд **нестационарный**, среднее "плавает"
  - **Вывод:** Нельзя использовать общую среднюю длительность, рынок меняется
  - **Действие:** Использовать скользящие окна или адаптивные параметры
- `p_value < 0.05` (H0 отвергается) → Ряд **стационарный**, среднее стабильно
  - **Вывод:** Можно доверять исторической средней длительности
  - **Действие:** Использовать фиксированные параметры стратегии

**Связь с методологией:** Раздел "1.c) Тесты на стационарность" в macd_research.md

---

### 7.3. Новые анализаторы

#### 7.3.1. ZoneRegressionAnalyzer

**Назначение:** Построение регрессионных моделей для предсказания характеристик зон.

**Расположение:** `bquant/analysis/statistical/regression.py`

**API спецификация:**

```python
class ZoneRegressionAnalyzer:
    """OLS регрессия для моделирования зависимостей в зонах."""

    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha

    def predict_zone_duration(self,
                            zones_features: List[Dict],
                            predictors: List[str] = None) -> RegressionResult:
        """
        Регрессионная модель для предсказания длительности зоны.

        Модель: duration ~ macd_amplitude + atr + prev_zone_duration + ...

        Args:
            zones_features: Признаки зон
            predictors: Список предикторов (по умолчанию: стандартный набор)

        Returns:
            RegressionResult с полями:
            - model: OLS модель (statsmodels)
            - r_squared: R² модели
            - coefficients: Dict {predictor: coefficient}
            - p_values: Dict {predictor: p_value}
            - predictions: Предсказанные значения
            - residuals: Остатки модели
        """

    def predict_price_return(self,
                            zones_features: List[Dict]) -> RegressionResult:
        """
        Модель: price_return ~ duration + macd_amplitude + correlation_price_hist + ...
        """
```

**Предикторы по умолчанию:**
- Для `predict_zone_duration`: `['macd_amplitude', 'atr', 'prev_zone_duration', 'volatility']`
- Для `predict_price_return`: `['duration', 'macd_amplitude', 'correlation_price_hist', 'drawdown_from_peak']`

**Использование:**
```python
# Пример (концептуально):
analyzer = ZoneRegressionAnalyzer(alpha=0.05)
result = analyzer.predict_zone_duration(zones_features)

# Интерпретация
if result.r_squared > 0.3:
    print(f"Модель объясняет {result.r_squared*100}% вариации длительности")
    significant_predictors = {k: v for k, v in result.p_values.items() if v < 0.05}
    print(f"Значимые предикторы: {significant_predictors}")
```

**Связь с методологией:** Раздел "3. Моделирование зависимостей - Регрессия" в macd_research.md

---

#### 7.3.2. ValidationSuite

**Назначение:** Инструменты для валидации моделей и стратегий на устойчивость.

**Расположение:** `bquant/analysis/validation/suite.py`

**API спецификация:**

```python
class ValidationSuite:
    """Набор методов валидации для проверки робастности."""

    def out_of_sample_test(self,
                          analyze_func: Callable,
                          data: pd.DataFrame,
                          train_ratio: float = 0.7) -> ValidationResult:
        """
        Out-of-Sample валидация.

        Args:
            analyze_func: Функция анализа (например, lambda df: analyzer.analyze_complete(df))
            data: Полный датасет
            train_ratio: Доля данных для обучения (0.7 = 70% train, 30% test)

        Returns:
            ValidationResult с полями:
            - train_results: Результаты на обучающей выборке
            - test_results: Результаты на тестовой выборке
            - metrics_comparison: Сравнение ключевых метрик
            - degradation: Процент ухудшения метрик на тесте
        """

    def walk_forward_test(self,
                         analyze_func: Callable,
                         data: pd.DataFrame,
                         train_window: int = 1000,
                         test_window: int = 200,
                         step_size: int = 100) -> ValidationResult:
        """
        Walk-Forward валидация (скользящее окно).

        Имитирует реальную торговлю: обучение на [1..N], тест на [N+1..N+M],
        переобучение на [1..N+step], тест на [N+step+1..N+step+M], и т.д.

        Args:
            train_window: Размер окна обучения (в барах)
            test_window: Размер окна тестирования
            step_size: Шаг сдвига окна

        Returns:
            ValidationResult с результатами по всем итерациям
        """

    def sensitivity_analysis(self,
                           analyze_func: Callable,
                           data: pd.DataFrame,
                           param_ranges: Dict[str, List]) -> ValidationResult:
        """
        Анализ чувствительности к параметрам.

        Args:
            param_ranges: Диапазоны параметров для тестирования
                Например: {
                    'macd_fast': [8, 10, 12, 14],
                    'macd_slow': [20, 24, 26, 30],
                    'min_duration': [2, 3, 5]
                }

        Returns:
            ValidationResult с результатами для всех комбинаций параметров
        """

    def monte_carlo_test(self,
                        analyze_func: Callable,
                        data: pd.DataFrame,
                        n_simulations: int = 1000) -> ValidationResult:
        """
        Тест случайного блуждания (Monte Carlo).

        Генерирует синтетические данные со случайными ценами и проверяет,
        дает ли стратегия лучшие результаты чем на случайных данных.
        """
```

**Использование:**
```python
# Пример (концептуально):
validator = ValidationSuite()

# Out-of-Sample тест
oos_result = validator.out_of_sample_test(
    analyze_func=lambda df: analyzer.analyze_complete(df),
    data=full_data,
    train_ratio=0.7
)

# Проверка деградации
if oos_result.degradation < 0.2:  # Менее 20% ухудшения
    print("Модель робастна на новых данных")
else:
    print("Переобучение! Модель плохо обобщает")
```

**Связь с методологией:** Раздел "8. Валидация и повышение робастности" в macd_research.md

---

### 7.4. Рекомендуемый порядок реализации компонентов

> **Примечание:** Детальный план с разбивкой по фазам см. в разделе 6.3 "Порядок выполнения"

Рекомендуемая последовательность разработки компонентов в **Фазе 3**:

**Первоочередные компоненты:**
1. Инфраструктура стратегий (Фаза 3.0) - базовая архитектура для всех метрик
2. Метрики свингов (Фаза 3.1) - расширяют понимание внутренней структуры зон
3. Метрики формы (Фаза 3.2) - необходимы для улучшенной кластеризации
4. Метрики времени (Фаза 3.3) - уже частично реализованы в MACDZoneAnalyzer
5. H2 и H4 тесты (Фаза 3.6) - используют существующие данные, относительно просты

**Вторая очередь:**
6. Метрики дивергенций (Фаза 3.4) - более сложный алгоритм определения
7. ADF тест (Фаза 3.6) - важен для понимания стационарности данных
8. ZoneRegressionAnalyzer (Фаза 3.7) - базовая регрессия для моделирования

**Опциональные компоненты:**
9. Метрики объема (Фаза 3.5) - только если доступны данные по объему
10. H5 тест (Фаза 3.6) - требует определения уровней поддержки/сопротивления
11. ValidationSuite (Фаза 3.7) - полезен для production, но не критичен для исследований

### 7.5. Зависимости между компонентами

**Граф зависимостей:**
```
ZoneFeaturesAnalyzer (расширение метрик)
    ↓
    ├─→ H2: Тест наклона (требует hist_slope)
    ├─→ H4: Тест корреляции (требует correlation_price_hist + drawdown)
    └─→ ZoneRegressionAnalyzer (требует полный набор признаков)

HypothesisTestSuite (новые тесты)
    ↓
    └─→ ValidationSuite (использует результаты тестов для метрик)

Метрики формы (skewness, kurtosis)
    ↓
    └─→ Улучшенная кластеризация в ZoneSequenceAnalyzer
```

**Вывод:** Начинать нужно с расширения `ZoneFeaturesAnalyzer`, так как остальные компоненты зависят от полноты признаков.

---

### 7.6. Архитектура расширяемых метрик (Strategy Pattern)

#### 7.6.1. Обоснование

Для обеспечения гибкости и расширяемости системы анализа зон необходимо использовать паттерн **Strategy** для всех вычисляемых метрик. Это позволит:

- ✅ Добавлять новые алгоритмы без изменения существующего кода (Open/Closed Principle)
- ✅ Бесшовно переключаться между методами расчета
- ✅ Проводить A/B тестирование разных подходов на одних данных
- ✅ Комбинировать несколько методов (гибридные стратегии)
- ✅ Конфигурировать через `config.py` без изменения кода
- ✅ Легко добавлять ML-based методы расчета метрик

**Ключевая проблема текущей архитектуры:**

В текущей спецификации (разделы 7.1-7.4) метрики жестко закодированы в `ZoneFeaturesAnalyzer.extract_zone_features()`:

```python
# Текущий подход (негибкий)
def extract_zone_features(self, zone_info):
    # ...
    # Свинги ТОЛЬКО через ZigZag
    num_swings, avg_rally = self._calculate_swings_zigzag(data)
    # Нельзя легко поменять алгоритм
```

**Проблемы:**
- ❌ Невозможно переключиться на другой алгоритм (Bollinger, ATR-based и т.д.)
- ❌ Сложно A/B тестировать разные методы
- ❌ Нужно менять код `ZoneFeaturesAnalyzer` для каждого нового метода

#### 7.6.2. Базовая архитектура

**Компоненты:**

1. **Протоколы стратегий** (`bquant/analysis/zones/strategies/base.py`):
   - Определяют контракт для каждого типа метрики
   - Используют `Protocol` для type checking
   - Возвращают стандартизированные датаклассы с валидацией

2. **Реестр стратегий** (`bquant/analysis/zones/strategies/registry.py`):
   - Центральный реестр всех доступных стратегий
   - Декораторы для автоматической регистрации
   - Фабрики для создания стратегий по имени

3. **Конкретные реализации** (в подпапках):
   - `swing/` - стратегии расчета свингов
   - `divergence/` - стратегии расчета дивергенций
   - `shape/` - стратегии расчета формы
   - `volume/` - стратегии расчета объемных метрик

**Структура директорий:**

```
bquant/analysis/zones/strategies/
├── __init__.py
├── base.py                  # Протоколы и базовые датаклассы
├── registry.py              # Реестр и фабрики стратегий
├── swing/
│   ├── __init__.py
│   ├── zigzag.py           # ZigZagSwingStrategy
│   ├── bollinger.py        # BollingerSwingStrategy
│   ├── atr.py              # ATRSwingStrategy
│   └── hybrid.py           # HybridSwingStrategy (композиция)
├── divergence/
│   ├── __init__.py
│   ├── classic.py          # ClassicDivergenceStrategy
│   └── rsi.py              # RSIDivergenceStrategy
├── shape/
│   ├── __init__.py
│   ├── statistical.py      # StatisticalShapeStrategy
│   └── fourier.py          # FourierShapeStrategy
└── volume/
    ├── __init__.py
    └── standard.py         # StandardVolumeStrategy
```

#### 7.6.3. Типы стратегий

Каждый тип вычисляемых метрик должен иметь свой протокол и результирующий датакласс:

| Тип метрики | Протокол | Результат | Базовые стратегии |
|------------|----------|-----------|-------------------|
| Свинги | `SwingCalculationStrategy` | `SwingMetrics` | ZigZag, Bollinger, ATR, ML-based |
| Дивергенции | `DivergenceCalculationStrategy` | `DivergenceMetrics` | Classic, RSI, Hidden |
| Форма | `ShapeCalculationStrategy` | `ShapeMetrics` | Statistical, Fourier, Wavelet |
| Объем | `VolumeCalculationStrategy` | `VolumeMetrics` | Standard, VWAP, OBV |

#### 7.6.4. Спецификация базовых компонентов

**1. Протоколы и датаклассы (`bquant/analysis/zones/strategies/base.py`):**

```python
from dataclasses import dataclass
from typing import Protocol, Dict, Any, runtime_checkable
import pandas as pd

@dataclass
class SwingMetrics:
    """Стандартизированный результат расчета свингов."""
    num_swings: int
    avg_rally_pct: float
    avg_drop_pct: float
    max_rally_pct: float
    max_drop_pct: float
    rally_to_drop_ratio: float
    
    # Метаданные о методе расчета (для трейсабельности)
    strategy_name: str
    strategy_params: Dict[str, Any]
    
    def validate(self):
        """Валидация корректности метрик."""
        assert self.num_swings >= 0, "num_swings должно быть >= 0"
        assert self.rally_to_drop_ratio >= 0, "ratio должен быть >= 0"
        # ... другие проверки

@runtime_checkable
class SwingCalculationStrategy(Protocol):
    """Протокол для алгоритмов определения свингов."""
    
    def calculate_swings(self, zone_data: pd.DataFrame) -> SwingMetrics:
        """
        Рассчитать метрики свингов.
        
        Args:
            zone_data: DataFrame с колонками: high, low, close
        
        Returns:
            SwingMetrics с валидированными данными
        """
        ...
    
    def get_metadata(self) -> Dict[str, Any]:
        """Метаданные о стратегии для логирования."""
        ...
```

**Аналогично для других типов метрик:**

```python
@dataclass
class DivergenceMetrics:
    divergence_type: str
    divergence_count: int
    divergence_strength: float
    divergence_direction: str
    strategy_name: str
    strategy_params: Dict[str, Any]

@runtime_checkable
class DivergenceCalculationStrategy(Protocol):
    def calculate_divergence(self, zone_data: pd.DataFrame) -> DivergenceMetrics:
        ...
    def get_metadata(self) -> Dict[str, Any]:
        ...

@dataclass
class ShapeMetrics:
    hist_skewness: float
    hist_kurtosis: float
    hist_smoothness: float
    strategy_name: str
    strategy_params: Dict[str, Any]

@runtime_checkable
class ShapeCalculationStrategy(Protocol):
    def calculate_shape(self, zone_data: pd.DataFrame) -> ShapeMetrics:
        ...
    def get_metadata(self) -> Dict[str, Any]:
        ...

@dataclass
class VolumeMetrics:
    volume_zone_ratio: Optional[float]
    volume_at_entry_change: Optional[float]
    volume_macd_corr: Optional[float]
    avg_volume_zone: Optional[float]
    strategy_name: str
    strategy_params: Dict[str, Any]

@runtime_checkable
class VolumeCalculationStrategy(Protocol):
    def calculate_volume(self, zone_data: pd.DataFrame, baseline_volume: float) -> VolumeMetrics:
        ...
    def get_metadata(self) -> Dict[str, Any]:
        ...
```

**2. Реестр стратегий (`bquant/analysis/zones/strategies/registry.py`):**

```python
from typing import Dict, Type, Any, List

class StrategyRegistry:
    """Реестр стратегий для автоматической регистрации."""
    
    _swing_strategies: Dict[str, Type[SwingCalculationStrategy]] = {}
    _divergence_strategies: Dict[str, Type[DivergenceCalculationStrategy]] = {}
    _shape_strategies: Dict[str, Type[ShapeCalculationStrategy]] = {}
    _volume_strategies: Dict[str, Type[VolumeCalculationStrategy]] = {}
    
    @classmethod
    def register_swing_strategy(cls, name: str):
        """Декоратор для регистрации стратегии расчета свингов."""
        def decorator(strategy_class):
            cls._swing_strategies[name] = strategy_class
            return strategy_class
        return decorator
    
    @classmethod
    def get_swing_strategy(cls, name: str, **params) -> SwingCalculationStrategy:
        """Создать стратегию по имени."""
        if name not in cls._swing_strategies:
            raise ValueError(
                f"Unknown swing strategy: {name}. "
                f"Available: {list(cls._swing_strategies.keys())}"
            )
        return cls._swing_strategies[name](**params)
    
    @classmethod
    def list_swing_strategies(cls) -> List[str]:
        """Список доступных стратегий."""
        return list(cls._swing_strategies.keys())
    
    # Аналогичные методы для других типов стратегий:
    # register_divergence_strategy, get_divergence_strategy, list_divergence_strategies
    # register_shape_strategy, get_shape_strategy, list_shape_strategies
    # register_volume_strategy, get_volume_strategy, list_volume_strategies
```

**3. Пример конкретной реализации (`bquant/analysis/zones/strategies/swing/zigzag.py`):**

```python
from ..base import SwingMetrics, SwingCalculationStrategy
from ..registry import StrategyRegistry
import pandas as pd
import numpy as np

@StrategyRegistry.register_swing_strategy('zigzag')
class ZigZagSwingStrategy:
    """Определение свингов через ZigZag алгоритм."""
    
    def __init__(self, min_swing_threshold: float = 0.02):
        """
        Args:
            min_swing_threshold: Минимальная амплитуда свинга (2% по умолчанию)
        """
        self.threshold = min_swing_threshold
    
    def calculate_swings(self, zone_data: pd.DataFrame) -> SwingMetrics:
        """Рассчитать метрики свингов через ZigZag."""
        # Реализация алгоритма ZigZag
        # ...
        
        result = SwingMetrics(
            num_swings=num_swings,
            avg_rally_pct=avg_rally,
            avg_drop_pct=avg_drop,
            max_rally_pct=max_rally,
            max_drop_pct=max_drop,
            rally_to_drop_ratio=avg_rally / avg_drop if avg_drop > 0 else 0,
            strategy_name='zigzag',
            strategy_params={'threshold': self.threshold}
        )
        
        result.validate()  # Валидация результата
        return result
    
    def get_metadata(self) -> Dict[str, Any]:
        return {
            'name': 'ZigZag',
            'description': 'Swing detection via ZigZag algorithm',
            'params': {'threshold': self.threshold}
        }
```

**4. Фабрики в `bquant/core/config.py`:**

```python
from bquant.analysis.zones.strategies.registry import StrategyRegistry

def create_swing_strategy(config: Dict = None):
    """Создать стратегию расчета свингов из конфига."""
    if config is None:
        config = get_analysis_params('zone_features').get('swing_strategy', {})
    
    strategy_type = config.get('type', 'zigzag')
    params = config.get('params', {})
    
    return StrategyRegistry.get_swing_strategy(strategy_type, **params)

def create_divergence_strategy(config: Dict = None):
    """Создать стратегию расчета дивергенций из конфига."""
    if config is None:
        config = get_analysis_params('zone_features').get('divergence_strategy', {})
    
    strategy_type = config.get('type', 'classic')
    params = config.get('params', {})
    
    return StrategyRegistry.get_divergence_strategy(strategy_type, **params)

# Аналогично для shape и volume стратегий
```

#### 7.6.5. Интеграция с ZoneFeaturesAnalyzer

Модифицированный анализатор принимает стратегии через конструктор:

```python
class ZoneFeaturesAnalyzer(BaseAnalyzer):
    """Анализатор характеристик торговых зон с поддержкой стратегий."""
    
    def __init__(self, 
                 min_duration: int = 2,
                 min_amplitude: float = 0.001,
                 swing_strategy: Optional[SwingCalculationStrategy] = None,
                 divergence_strategy: Optional[DivergenceCalculationStrategy] = None,
                 shape_strategy: Optional[ShapeCalculationStrategy] = None,
                 volume_strategy: Optional[VolumeCalculationStrategy] = None):
        """
        Args:
            swing_strategy: Стратегия расчета свингов (по умолчанию из config)
            divergence_strategy: Стратегия расчета дивергенций (по умолчанию из config)
            shape_strategy: Стратегия расчета формы (по умолчанию из config)
            volume_strategy: Стратегия расчета объема (по умолчанию из config)
        """
        super().__init__("ZoneFeaturesAnalyzer")
        self.min_duration = min_duration
        self.min_amplitude = min_amplitude
        
        # Стратегии по умолчанию через фабрики из config
        self.swing_strategy = swing_strategy or create_swing_strategy()
        self.divergence_strategy = divergence_strategy or create_divergence_strategy()
        self.shape_strategy = shape_strategy or create_shape_strategy()
        self.volume_strategy = volume_strategy or create_volume_strategy()
    
    def extract_zone_features(self, zone_info: Dict[str, Any]) -> ZoneFeatures:
        """Извлечение признаков с использованием стратегий."""
        zone_data = zone_info['data']
        
        # ... базовые метрики ...
        
        # Вычисление через стратегии
        swing_metrics = self.swing_strategy.calculate_swings(zone_data)
        divergence_metrics = self.divergence_strategy.calculate_divergence(zone_data)
        shape_metrics = self.shape_strategy.calculate_shape(zone_data)
        
        # Volume опционально (если данные есть)
        volume_metrics = None
        if 'volume' in zone_data.columns and not zone_data['volume'].isna().all():
            baseline_volume = self._calculate_baseline_volume(zone_data)
            volume_metrics = self.volume_strategy.calculate_volume(zone_data, baseline_volume)
        
        return ZoneFeatures(
            # ... другие базовые поля ...
            
            # Метрики свингов
            num_swings=swing_metrics.num_swings,
            avg_rally_pct=swing_metrics.avg_rally_pct,
            avg_drop_pct=swing_metrics.avg_drop_pct,
            max_rally_pct=swing_metrics.max_rally_pct,
            max_drop_pct=swing_metrics.max_drop_pct,
            rally_to_drop_ratio=swing_metrics.rally_to_drop_ratio,
            
            # Метрики дивергенций
            divergence_type=divergence_metrics.divergence_type,
            divergence_count=divergence_metrics.divergence_count,
            divergence_strength=divergence_metrics.divergence_strength,
            divergence_direction=divergence_metrics.divergence_direction,
            
            # Метрики формы
            hist_skewness=shape_metrics.hist_skewness,
            hist_kurtosis=shape_metrics.hist_kurtosis,
            hist_smoothness=shape_metrics.hist_smoothness,
            
            # Метрики объема (опционально)
            volume_zone_ratio=volume_metrics.volume_zone_ratio if volume_metrics else None,
            volume_at_entry_change=volume_metrics.volume_at_entry_change if volume_metrics else None,
            volume_macd_corr=volume_metrics.volume_macd_corr if volume_metrics else None,
            
            # Метаданные о стратегиях
            metadata={
                'swing_strategy': self.swing_strategy.get_metadata(),
                'divergence_strategy': self.divergence_strategy.get_metadata(),
                'shape_strategy': self.shape_strategy.get_metadata(),
                'volume_strategy': self.volume_strategy.get_metadata() if volume_metrics else None
            }
        )
```

#### 7.6.6. Использование в оркестраторе

**Вариант 1: Через config.py (рекомендуется):**

```python
# В bquant/core/config.py
ANALYSIS_CONFIG = {
    'zone_features': {
        'min_duration': 2,
        'swing_strategy': {
            'type': 'zigzag',  # или 'bollinger', 'atr'
            'params': {'min_swing_threshold': 0.02}
        },
        'divergence_strategy': {
            'type': 'classic',
            'params': {}
        },
        'shape_strategy': {
            'type': 'statistical',
            'params': {}
        },
        'volume_strategy': {
            'type': 'standard',
            'params': {}
        }
    }
}

# В MACDZoneAnalyzer.analyze_complete_modular()
features_analyzer = ZoneFeaturesAnalyzer(
    min_duration=self.zone_params['min_duration']
    # Стратегии не указаны → используются из config.py
)
```

**Вариант 2: Программно (для A/B тестирования):**

```python
# Тестирование разных стратегий свингов
from bquant.analysis.zones.strategies.swing import (
    ZigZagSwingStrategy, 
    BollingerSwingStrategy, 
    ATRSwingStrategy
)

strategies = [
    ZigZagSwingStrategy(min_swing_threshold=0.02),
    BollingerSwingStrategy(period=20, num_std=2.0),
    ATRSwingStrategy(atr_multiplier=1.5)
]

results = {}
for strategy in strategies:
    analyzer = ZoneFeaturesAnalyzer(
        min_duration=2,
        swing_strategy=strategy
    )
    
    zones_features = []
    for zone in zones:
        zone_dict = analyzer._zone_to_dict(zone)
        zone_features = analyzer.extract_zone_features(zone_dict)
        zones_features.append(zone_features)
    
    # Анализ результатов
    avg_ratio = np.mean([z.rally_to_drop_ratio for z in zones_features])
    results[strategy.__class__.__name__] = {
        'avg_rally_to_drop_ratio': avg_ratio,
        'metadata': strategy.get_metadata()
    }

# Сравнение результатов
print("Strategy comparison:")
for strategy_name, metrics in results.items():
    print(f"{strategy_name}: ratio={metrics['avg_rally_to_drop_ratio']:.2f}")
```

**Вариант 3: Гибридная стратегия (композиция):**

```python
# bquant/analysis/zones/strategies/swing/hybrid.py
@StrategyRegistry.register_swing_strategy('hybrid')
class HybridSwingStrategy:
    """Композиция нескольких методов с усреднением результатов."""
    
    def __init__(self, strategies: List[str] = None, weights: List[float] = None):
        if strategies is None:
            strategies = ['zigzag', 'bollinger', 'atr']
        
        self.strategies = [
            StrategyRegistry.get_swing_strategy(name) for name in strategies
        ]
        self.weights = weights or [1.0] * len(self.strategies)
    
    def calculate_swings(self, zone_data: pd.DataFrame) -> SwingMetrics:
        # Получить результаты от всех стратегий
        results = [s.calculate_swings(zone_data) for s in self.strategies]
        
        # Взвешенное усреднение
        avg_rally = np.average(
            [r.avg_rally_pct for r in results], 
            weights=self.weights
        )
        # ... аналогично для других метрик
        
        return SwingMetrics(
            num_swings=int(np.mean([r.num_swings for r in results])),
            avg_rally_pct=avg_rally,
            # ...
            strategy_name='hybrid',
            strategy_params={
                'strategies': [s.get_metadata()['name'] for s in self.strategies],
                'weights': self.weights
            }
        )
```

#### 7.6.7. Преимущества архитектуры

✅ **1. Бесшовная замена алгоритмов:**

```python
# Легко сравнить разные методы
for strategy_name in ['zigzag', 'bollinger', 'atr']:
    strategy = StrategyRegistry.get_swing_strategy(strategy_name)
    analyzer = ZoneFeaturesAnalyzer(swing_strategy=strategy)
    results = analyzer.extract_zone_features(zone)
    print(f"{strategy_name}: ratio={results.rally_to_drop_ratio:.2f}")
```

✅ **2. A/B тестирование:**

```python
# Сравнить результаты стратегий на одних данных
results_a = analyze_with_strategy(ZigZagSwingStrategy())
results_b = analyze_with_strategy(BollingerSwingStrategy())

# Выбрать лучшую по метрике
if results_a.sharpe_ratio > results_b.sharpe_ratio:
    best_strategy = 'zigzag'
```

✅ **3. Конфигурация без изменения кода:**

```python
# Меняем только config.py, код не трогаем
ANALYSIS_CONFIG = {
    'swing_strategy': {'type': 'bollinger', 'params': {'period': 20}}
}
```

✅ **4. Легко добавлять новые методы:**

```python
# Добавляем новую стратегию - старый код не меняется
@StrategyRegistry.register_swing_strategy('ml_based')
class MachineLearningSwingStrategy:
    """Определение свингов через ML модель."""
    
    def __init__(self, model_path: str):
        self.model = load_model(model_path)
    
    def calculate_swings(self, zone_data):
        predictions = self.model.predict(zone_data)
        # ... обработка предсказаний
```

✅ **5. Трейсабельность результатов:**

```python
# В метаданных всегда сохраняется информация о стратегии
zone_features.metadata['swing_strategy']
# {'name': 'ZigZag', 'description': '...', 'params': {'threshold': 0.02}}
```

#### 7.6.8. Расширенные возможности

**1. Кэширование результатов:**

```python
from functools import lru_cache
from hashlib import md5

class CachedSwingStrategy:
    """Декоратор для кэширования результатов стратегии."""
    
    def __init__(self, strategy: SwingCalculationStrategy, cache_size: int = 128):
        self.strategy = strategy
        self.cache = {}
    
    def calculate_swings(self, zone_data: pd.DataFrame) -> SwingMetrics:
        # Создать ключ кэша из данных
        cache_key = md5(zone_data.values.tobytes()).hexdigest()
        
        if cache_key not in self.cache:
            self.cache[cache_key] = self.strategy.calculate_swings(zone_data)
        
        return self.cache[cache_key]
```

**2. Логирование и метрики производительности:**

```python
class InstrumentedSwingStrategy:
    """Обертка для логирования и сбора метрик."""
    
    def __init__(self, strategy: SwingCalculationStrategy):
        self.strategy = strategy
        self.logger = get_logger(f"{__name__}.{strategy.__class__.__name__}")
    
    def calculate_swings(self, zone_data: pd.DataFrame) -> SwingMetrics:
        start_time = time.perf_counter()
        
        try:
            result = self.strategy.calculate_swings(zone_data)
            
            elapsed = time.perf_counter() - start_time
            self.logger.debug(
                f"Swing calculation completed in {elapsed:.4f}s. "
                f"Found {result.num_swings} swings, ratio={result.rally_to_drop_ratio:.2f}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Swing calculation failed: {e}", exc_info=True)
            raise AnalysisError(f"Swing strategy failed: {e}") from e
```

**3. Автоматический выбор стратегии:**

```python
@StrategyRegistry.register_swing_strategy('auto')
class AutoSwingStrategy:
    """Интеллектуальная стратегия с автоматическим выбором метода."""
    
    def __init__(self):
        self.strategies = {
            'zigzag': ZigZagSwingStrategy(),
            'bollinger': BollingerSwingStrategy(),
            'atr': ATRSwingStrategy()
        }
    
    def _select_best_strategy(self, zone_data: pd.DataFrame) -> str:
        """Эвристика выбора стратегии на основе данных."""
        volatility = zone_data['close'].pct_change().std()
        
        # Если высокая волатильность → ATR
        if volatility > 0.03:
            return 'atr'
        # Если тренд → ZigZag
        elif self._is_trending(zone_data):
            return 'zigzag'
        # Иначе → Bollinger
        else:
            return 'bollinger'
    
    def calculate_swings(self, zone_data: pd.DataFrame) -> SwingMetrics:
        strategy_name = self._select_best_strategy(zone_data)
        logger.debug(f"Auto-selected swing strategy: {strategy_name}")
        return self.strategies[strategy_name].calculate_swings(zone_data)
```

#### 7.6.9. Обновление спецификаций разделов 7.1-7.4

**Важное примечание для реализации:**

Все метрики, описанные в разделах 7.1.1-7.1.4, должны быть реализованы через паттерн Strategy согласно данному разделу 7.6. 

**Обновления к разделам:**

- **Раздел 7.1.1 (Метрики свингов):** Реализовать через `SwingCalculationStrategy`. Базовая версия - `ZigZagSwingStrategy`, расширения - `BollingerSwingStrategy`, `ATRSwingStrategy`.

- **Раздел 7.1.2 (Метрики формы):** Реализовать через `ShapeCalculationStrategy`. Базовая версия - `StatisticalShapeStrategy` (skewness/kurtosis), расширения - `FourierShapeStrategy`, `WaveletShapeStrategy`.

- **Раздел 7.1.3 (Метрики дивергенций):** Реализовать через `DivergenceCalculationStrategy`. Базовая версия - `ClassicDivergenceStrategy`, расширения - `RSIDivergenceStrategy`, `HiddenDivergenceStrategy`.

- **Раздел 7.1.4 (Метрики объема):** Реализовать через `VolumeCalculationStrategy`. Базовая версия - `StandardVolumeStrategy`, расширения - `VWAPVolumeStrategy`, `OBVVolumeStrategy`.

#### 7.6.10. Порядок реализации в Фазе 3

> **Примечание:** Данный раздел дублирует информацию из раздела 6.3 "Порядок выполнения" для удобства навигации. Основной источник информации о порядке реализации - раздел 6.3.

**Фаза 3.0: Инфраструктура стратегий**

> **Описание:** См. подразделы 7.6.1-7.6.4 данного раздела

1. [ ] Создать структуру папок `bquant/analysis/zones/strategies/`
2. [ ] Реализовать `base.py` с протоколами и датаклассами для всех типов метрик
3. [ ] Реализовать `registry.py` с декораторами регистрации
4. [ ] Создать фабрики в `bquant/core/config.py`
5. [ ] Добавить конфигурацию стратегий в `ANALYSIS_CONFIG`
6. [ ] Обновить `ZoneFeaturesAnalyzer.__init__()` для приема стратегий
7. [ ] Написать unit-тесты для инфраструктуры

**Критерии готовности:**
- [ ] Можно зарегистрировать и создать стратегию через реестр
- [ ] `ZoneFeaturesAnalyzer` принимает стратегии в конструкторе
- [ ] Фабрики создают стратегии из config
- [ ] Тесты проверяют контракты протоколов

**Фаза 3.1: Swing стратегии**

> **Описание:** Реализация согласно разделу 7.1.1 через Strategy Pattern

1. [ ] `ZigZagSwingStrategy` - базовая реализация
2. [ ] `BollingerSwingStrategy` - через полосы Боллинджера
3. [ ] `ATRSwingStrategy` - через движения > N * ATR
4. [ ] Интегрировать в `ZoneFeaturesAnalyzer.extract_zone_features()`
5. [ ] Unit-тесты для каждой стратегии
6. [ ] A/B тестирование стратегий на примерах

**Фаза 3.2: Shape стратегии**

> **Описание:** Реализация согласно разделу 7.1.2 через Strategy Pattern

1. [ ] `StatisticalShapeStrategy` - через skewness/kurtosis
2. [ ] Интегрировать в `ZoneFeaturesAnalyzer.extract_zone_features()`
3. [ ] Unit-тесты
4. [ ] Опционально: `FourierShapeStrategy`

**Фаза 3.3: Divergence стратегии**

> **Описание:** Реализация согласно разделу 7.1.3 через Strategy Pattern

1. [ ] `ClassicDivergenceStrategy` - классический метод
2. [ ] Интегрировать в `ZoneFeaturesAnalyzer.extract_zone_features()`
3. [ ] Unit-тесты
4. [ ] Опционально: `RSIDivergenceStrategy`

**Фаза 3.4: Volume стратегии**

> **Описание:** Реализация согласно разделу 7.1.4 через Strategy Pattern

1. [ ] `StandardVolumeStrategy` - базовая реализация
2. [ ] Интегрировать в `ZoneFeaturesAnalyzer.extract_zone_features()`
3. [ ] Unit-тесты
4. [ ] Опционально: `VWAPVolumeStrategy`

#### 7.6.11. Критерии успеха архитектуры

1. [ ] **Расширяемость:** Можно добавить новую стратегию без изменения `ZoneFeaturesAnalyzer`
2. [ ] **Конфигурируемость:** Можно переключить стратегию через изменение одной строки в config
3. [ ] **Тестируемость:** Все стратегии проходят единые тесты на контракт
4. [ ] **Трейсабельность:** Метаданные о стратегии сохраняются в результатах анализа
5. [ ] **Производительность:** Кэширование работает корректно
6. [ ] **Обратная совместимость:** Старый код работает с дефолтными стратегиями

---
