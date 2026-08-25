# API Reference - Справочник API BQuant

## 📚 Обзор

Справочник API содержит подробную документацию всех модулей, классов и функций BQuant.

## 🗂️ Структура API

### 🏗️ Core Modules - Базовые модули
- **bquant.core.config** - Конфигурация и настройки
- **bquant.core.exceptions** - Исключения и ошибки
- **bquant.core.logging_config** - Настройка логирования
- **bquant.core.performance** - Производительность и профилирование
- **bquant.core.utils** - Утилиты и вспомогательные функции

### 📊 Data Modules - Модули данных
- **bquant.data.loader** - Загрузка данных из различных источников
- **bquant.data.processor** - Обработка и очистка данных
- **bquant.data.validator** - Валидация данных
- **bquant.data.samples** - Встроенные sample данные
- **bquant.data.schemas** - Схемы данных и типы

### 📈 Indicators - Технические индикаторы
- **bquant.indicators.base** - Базовые классы индикаторов
- **bquant.indicators.macd** - MACD индикатор с анализом зон
- **bquant.indicators.preloaded** - PRELOADED индикаторы для готовых данных
- **bquant.indicators.factory** - Фабрика индикаторов
- **bquant.indicators.library_manager** - Управление внешними библиотеками (pandas-ta, TA-Lib)

### 🔬 Analysis - Аналитические модули
- **bquant.analysis.statistical** - Статистический анализ
- **bquant.analysis.zones** - Universal Zone Analysis Pipeline v2.1
- **bquant.analysis.base** - Базовые классы анализа

### 📊 Visualization - Модули визуализации
- **bquant.visualization.charts** - Финансовые графики
- **bquant.visualization.zones** - Визуализация зон
- **bquant.visualization.statistical** - Статистические графики
- **bquant.visualization.themes** - Темы и стили

## 🔍 Поиск по API

> **📊 Статистика пакета (на 24.10.2025):** BQuant содержит **1110+ сущностей** в **85 модулях**:
> - **491 класс** (индикаторы, анализаторы, визуализаторы)
> - **619 функций** (утилиты, расчеты, обработка данных)
> - **164+ индикатора** (включая pandas-ta интеграцию)
> 
> Ниже перечислены только **ключевые entry points** для быстрого старта. 
> Полная документация доступна в соответствующих разделах.

### 🎯 Основные entry points

#### 🚀 Быстрый старт
- `analyze_zones()` - **Universal Pipeline** для анализа зон (основной API)
- `load_ohlcv_data()` - Загрузка OHLCV данных
- `get_sample_data()` - Получение sample данных

#### 🔧 Ключевые компоненты
- `ZoneAnalysisBuilder` - Fluent builder для Universal Pipeline
- `IndicatorFactory` - Фабрика индикаторов (164+ доступных)
- `FinancialCharts` - Создание финансовых графиков

### 📚 Подробная документация

#### 📈 Indicators API - 164+ индикаторов
- **6 встроенных:** SMA, EMA, RSI, MACD, Bollinger Bands, Custom
- **158 pandas-ta:** Полная интеграция с pandas-ta библиотекой
- **PRELOADED:** Готовые индикаторы для sample данных
- **Factory pattern:** Универсальное создание любых индикаторов

#### 🔬 Analysis API - Аналитические модули
- **Universal Zone Analysis v2.1:** Анализ зон с любыми индикаторами
- **5 Detection Strategies:** zero_crossing, threshold, line_crossing, preloaded, combined
- **5 Analysis Strategies:** swing, divergence, shape, volume, volatility
- **Statistical Analysis:** Гипотезные тесты, регрессия, валидация
- **Clustering:** Автоматическая группировка зон

#### 📊 Visualization API - Графики и визуализация
- **FinancialCharts:** Candlestick, line, bar графики
- **ZoneVisualizer:** Визуализация зон с контекстом
- **StatisticalPlots:** Статистические графики и распределения
- **Themes:** 5 готовых тем оформления

#### 💾 Data API - Работа с данными
- **Loader:** Загрузка OHLCV данных из файлов
- **Processor:** Очистка и валидация данных
- **Samples:** 8 встроенных sample датасетов
- **Schemas:** Типизация и валидация структур данных

### 🔍 Поиск по функциональности

#### 📊 Работа с данными
- `load_ohlcv_data()` - Загрузка OHLCV данных
- `get_sample_data()` - Получение sample данных  
- `clean_ohlcv_data()` - Очистка и валидация данных

#### 📈 Технические индикаторы
- `IndicatorFactory.create()` - Создание любого из 164+ индикаторов
- `MACDPreloadedIndicator` - PRELOADED MACD для готовых данных
- `BaseIndicator` - Базовый класс для создания custom индикаторов

#### 🔬 Universal Zone Analysis (v2.1)
- `analyze_zones()` - **Основной API** для анализа зон
- `ZoneAnalysisBuilder` - Fluent builder с полной настройкой
- `run_all_hypothesis_tests()` - Статистические тесты

#### 📊 Визуализация
- `FinancialCharts` - Создание финансовых графиков
- `ZoneVisualizer` - Визуализация зон с контекстом
- `create_candlestick_chart()` - Быстрое создание candlestick

### 🗑️ Удалённый API

Удалено в 0.0.5 — при обновлении замените:

| Было | Стало |
|------|-------|
| `MACDZoneAnalyzer` | `analyze_zones()` / пресет `analyze_macd_zones()` |
| `analyze_complete()` | `.analyze().build()` |
| `_zone_to_dict()` | `zone.features.get()` |

Полное соответствие — в [MIGRATION_v2](../migration/MIGRATION_v2.md).

## Актуальные примеры работы с MACD

### Universal Pipeline (рекомендуемый подход)

```python
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

# Загружаем данные
data = get_sample_data('tv_xauusd_1h')

# Анализ MACD через Universal Pipeline
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .with_strategies(swing='find_peaks', shape='statistical')
    .analyze(clustering=True, n_clusters=3)
    .build()
)

print(f"Найдено зон: {len(result.zones)}")
print(f"Статистика: {result.statistics}")
```

### PRELOADED MACD индикатор

```python
from bquant.indicators.preloaded import MACDPreloadedIndicator

# Создание PRELOADED MACD индикатора
macd_indicator = MACDPreloadedIndicator()
macd_data = macd_indicator.calculate(data)

# Использование в Universal Pipeline
result = (
    analyze_zones(data)
    .with_indicator('preloaded', 'macd_preloaded')
    .detect_zones('zero_crossing', indicator_role='line')
    .analyze(clustering=False)
    .build()
)
```

## 📖 Как читать документацию

### Структура документации класса

```python
class MACD(CustomIndicator):
    """
    Moving Average Convergence Divergence (MACD) indicator.

    Измеряет соотношение двух скользящих средних для выявления смены импульса.

    Attributes:
        fast_period (int): Период быстрой EMA
        slow_period (int): Период медленной EMA
        signal_period (int): Период сигнальной линии

    Example:
        >>> macd = MACD(fast_period=12, slow_period=26, signal_period=9)
        >>> result = macd.calculate(data)
        >>> print(result.data.columns.tolist())
        ['macd_12_26_9__line', 'macd_12_26_9__signal', 'macd_12_26_9__hist']
    """

    def __init__(self, fast_period: int = 12, slow_period: int = 26,
                 signal_period: int = 9):
        """
        Инициализация индикатора.

        Args:
            fast_period (int, optional): Период быстрой EMA. Defaults to 12.
            slow_period (int, optional): Период медленной EMA. Defaults to 26.
            signal_period (int, optional): Период сигнальной линии. Defaults to 9.
        """

    def calculate(self, data):
        """
        Рассчитывает значения индикатора.

        Args:
            data (pd.DataFrame): OHLCV данные

        Returns:
            IndicatorResult: Результат с колонками ролей line/signal/hist
                (имена канонические: `{слаг}__{роль}`)

        Raises:
            DataError: Если данные некорректны
        """
```

### Структура документации функции

```python
def load_ohlcv_data(file_path, **kwargs):
    """
    Загружает OHLCV данные из файла.
    
    Поддерживает различные форматы файлов: CSV, Excel, JSON.
    Автоматически определяет формат и кодировку файла.
    
    Args:
        file_path (str): Путь к файлу с данными
        **kwargs: Дополнительные параметры для pandas.read_csv/read_excel
        
    Returns:
        pd.DataFrame: DataFrame с OHLCV данными
        
    Raises:
        FileNotFoundError: Если файл не найден
        DataError: Если данные некорректны
        
    Example:
        >>> data = load_ohlcv_data('data.csv')
        >>> print(f"Загружено {len(data)} записей")
    """
```

## 🔗 Связанные разделы

- **[User Guide](../user_guide/README.md)** - Руководство пользователя
- **[Tutorials](../tutorials/README.md)** - Обучающие материалы
- **[Examples](../examples/README.md)** - Примеры использования
- **[Developer Guide](../developer_guide/README.md)** - Для разработчиков

## 💡 Советы по использованию API

1. **Начните с базовых модулей** - изучите core и data
2. **Используйте sample данные** для экспериментов
3. **Читайте docstrings** - они содержат примеры использования
4. **Изучайте типы данных** - понимайте что возвращают функции
5. **Обрабатывайте исключения** - используйте try/except для ошибок

## 🚀 Расширение API

Хотите создать собственные индикаторы, анализаторы или визуализации? 
Изучите **[Extension Guide](extension_guide.md)** для подробного руководства по расширению BQuant.

---

**Начать изучение:** Core Modules 🏗️
