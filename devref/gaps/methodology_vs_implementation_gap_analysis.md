# Gap Analysis: Research Methodology vs. Code Implementation

This document provides a detailed comparison between the goals outlined in `research/methodology/macd_research.md` and the actual implementation within the `bquant` package.

The analysis highlights a key architectural issue: **two parallel, non-synchronized implementations** of the analysis logic.
- **`MACDZoneAnalyzer`**: A self-contained class in `bquant/indicators/macd.py` that appears to be an older, more direct implementation of the research.
- **`bquant.analysis` package**: A newer, more modular but less complete implementation (`ZoneFeaturesAnalyzer`, `HypothesisTestSuite`, etc.).

## Comparison Table

| Требование из методологии (Requirement from Methodology) | Реализация в `MACDZoneAnalyzer` (`macd.py`) | Реализация в пакете (`bquant.analysis.*`) | Статус и комментарии |
| :--- | :--- | :--- | :--- |
| **1. Сегментация зон (Zone Segmentation)** | | | |
| Определение зон по знаку MACD | ✔️ `identify_zones()` | ✔️ (Предполагается, что зоны передаются в анализаторы) | **OK** |
| Учет мин. длительности зоны | ✔️ `__init__` (параметр `zone_params['min_duration']`) | ✔️ `ZoneFeaturesAnalyzer.__init__` (параметр `min_duration`) | **OK** |
| Нормализация по ATR | ✔️ `calculate_macd_with_atr()`, `calculate_zone_features()` | ◐ `ZoneFeaturesAnalyzer.extract_zone_features()` (использует `atr`, если колонка уже есть) | **OK**. `MACDZoneAnalyzer` является основным исполнителем. |
| **2. Инжиниринг признаков (Feature Engineering)** | | | |
| Длительность, доходность, амплитуда | ✔️ `calculate_zone_features()` | ✔️ `ZoneFeaturesAnalyzer.extract_zone_features()` | **Дублирование**. |
| Просадка/отскок от пика/дна | ✔️ `calculate_zone_features()` | ✔️ `ZoneFeaturesAnalyzer.extract_zone_features()` | **Дублирование**. |
| Корреляция цены и гистограммы | ✔️ `calculate_zone_features()` | ✔️ `ZoneFeaturesAnalyzer.extract_zone_features()` | **Дублирование**. |
| Кол-во пиков/впадин (свинги) | ✔️ `calculate_zone_features()` (используя `scipy.signal.find_peaks`) | ✔️ `ZoneFeaturesAnalyzer.extract_zone_features()` (используя `scipy.signal.find_peaks`) | **Дублирование**. |
| Метрики времени (Time-to-peak ratio) | ✔️ `calculate_zone_features()` (рассчитывает `peak_time_ratio`, `trough_time_ratio`) | ❌ **Отсутствует** | **Пробел/Несоответствие**. Реализовано только в `MACDZoneAnalyzer`. |
| Продвинутый анализ свингов | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел**. Нет расчета среднего размера ралли/откатов. |
| Метрики дивергенций | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел**. |
| Метрики объема | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел**. |
| Метрики формы (Skew, Kurtosis) | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел**. |
| **3. Статистический анализ (Statistical Analysis)** | | | |
| Описательные статистики | ✔️ `analyze_zones_distribution()` | ✔️ `ZoneFeaturesAnalyzer.analyze_zones_distribution()` | **Дублирование**. Обе реализации существуют. |
| Тест на стационарность (ADF) | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел**. |
| **4. Проверка гипотез (Hypothesis Testing)** | | | |
| H1: Длина зоны vs. разворот | ✔️ `test_hypotheses()` | ✔️ `HypothesisTestSuite.test_zone_duration_hypothesis()` | **Дублирование**. |
| H2: Наклон гистограммы vs. длина | ❌ **Отсутствует** | ◐ `HypothesisTestSuite.test_histogram_slope_hypothesis()` (Тест есть, но требует `hist_slope`, который не рассчитывается) | **Пробел**. Неработоспособный тест в пакете. |
| H4: Корреляция vs. просадка | ✔️ `test_hypotheses()` | ❌ **Отсутствует** | **Пробел/Несоответствие**. Реализовано только в `MACDZoneAnalyzer`. |
| H5: Уровни поддержки/сопротивления | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел**. |
| **5. Моделирование (Modeling)** | | | |
| Кластеризация (K-Means) | ✔️ `cluster_zones_by_shape()` | ✔️ `ZoneSequenceAnalyzer.cluster_zones()` | **Дублирование**. Обе реализации существуют. |
| Цепи Маркова | ◐ `analyze_zone_sequences()` (Только переходы `bull`/`bear`) | ✔️ `ZoneSequenceAnalyzer._markov_chain_analysis()` (Более полная версия с расчетом стац. распределения) | **Частичная реализация**. Продвинутая версия в пакете, но обе не используют сложные состояния. |
| Регрессия (OLS) | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел**. |
| **6. Валидация (Validation)** | | | |
| Out-of-Sample / Walk-Forward | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел**. Нет встроенных инструментов. |
| Анализ чувствительности | ❌ **Отсутствует** | ❌ **Отсутствует** | **Пробел**. |

## Выводы

1.  **Фундамент заложен:** Основные механизмы для анализа зон реализованы.
2.  **Архитектурный долг:** Существование двух параллельных систем анализа (`MACDZoneAnalyzer` и `bquant.analysis`) является серьезной проблемой, которую нужно решать. Это приводит к несоответствиям и усложняет поддержку.
3.  **Значительные пробелы:** Наиболее продвинутые части методологии (детали свингов, дивергенции, объем, регрессия, ADF-тесты, валидация) не реализованы.
4.  **Несоответствие реализаций:** Некоторые функции реализованы только в одном из двух мест, что делает модульный подход `bquant.analysis` неполным.

**Рекомендация:** Первоочередной задачей должна стать **консолидация логики**. Необходимо выбрать единый источник правды (предпочтительно, модульный пакет `bquant.analysis`) и перенести в него всю функциональность из `MACDZoneAnalyzer`, устранив пробелы.
