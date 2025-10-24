# API Reference - Справочник API BQuant

## 📚 Обзор

Справочник API содержит подробную документацию всех модулей, классов и функций BQuant.

## 🗂️ Структура API

### 🏗️ [Core Modules](core/README.md) - Базовые модули
- **bquant.core.config** - Конфигурация и настройки
- **bquant.core.exceptions** - Исключения и ошибки
- **bquant.core.logging_config** - Настройка логирования
- **bquant.core.performance** - Производительность и профилирование
- **bquant.core.utils** - Утилиты и вспомогательные функции

### 📊 [Data Modules](data/README.md) - Модули данных
- **bquant.data.loader** - Загрузка данных из различных источников
- **bquant.data.processor** - Обработка и очистка данных
- **bquant.data.validator** - Валидация данных
- **bquant.data.samples** - Встроенные sample данные
- **bquant.data.schemas** - Схемы данных и типы

### 📈 [Indicators](indicators/README.md) - Технические индикаторы
- **bquant.indicators.base** - Базовые классы индикаторов
- **bquant.indicators.macd** - MACD индикатор с анализом зон
- **bquant.indicators.preloaded** - PRELOADED индикаторы для готовых данных
- **bquant.indicators.factory** - Фабрика индикаторов
- **bquant.indicators.library_manager** - Управление внешними библиотеками (pandas-ta, TA-Lib)

### 🔬 [Analysis](analysis/README.md) - Аналитические модули
- **bquant.analysis.statistical** - Статистический анализ
- **bquant.analysis.zones** - Universal Zone Analysis Pipeline v2.1
- **bquant.analysis.base** - Базовые классы анализа

### 📊 [Visualization](visualization/README.md) - Модули визуализации
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

#### 📈 [Indicators API](indicators/README.md) - 164+ индикаторов
- **6 встроенных:** SMA, EMA, RSI, MACD, Bollinger Bands, Custom
- **158 pandas-ta:** Полная интеграция с pandas-ta библиотекой
- **PRELOADED:** Готовые индикаторы для sample данных
- **Factory pattern:** Универсальное создание любых индикаторов

#### 🔬 [Analysis API](analysis/README.md) - Аналитические модули
- **Universal Zone Analysis v2.1:** Анализ зон с любыми индикаторами
- **5 Detection Strategies:** zero_crossing, threshold, line_crossing, preloaded, combined
- **5 Analysis Strategies:** swing, divergence, shape, volume, volatility
- **Statistical Analysis:** Гипотезные тесты, регрессия, валидация
- **Clustering:** Автоматическая группировка зон

#### 📊 [Visualization API](visualization/README.md) - Графики и визуализация
- **FinancialCharts:** Candlestick, line, bar графики
- **ZoneVisualizer:** Визуализация зон с контекстом
- **StatisticalPlots:** Статистические графики и распределения
- **Themes:** 5 готовых тем оформления

#### 💾 [Data API](data/README.md) - Работа с данными
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

### ⚠️ Deprecated API
- `MACDZoneAnalyzer` - Используйте `analyze_zones()` вместо этого
- `analyze_complete()` - Заменен на Universal Pipeline
- `_zone_to_dict()` - Заменен на `zone.features.get()`

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
    .detect_zones('zero_crossing', indicator_col='macd_hist')
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
    .detect_zones('zero_crossing', indicator_col='macd')
    .analyze(clustering=False)
    .build()
)
```

## 📖 Как читать документацию

### Структура документации класса

```python
class MACDZoneAnalyzer:  # ⚠️ DEPRECATED - используйте analyze_zones()
    """
    Анализатор MACD с идентификацией зон.
    
    ⚠️ DEPRECATED: Этот класс устарел. Используйте Universal Pipeline:
    analyze_zones().with_indicator('custom', 'macd').detect_zones().build()
    
    Этот класс выполняет полный анализ MACD индикатора,
    включая расчет значений, идентификацию зон и статистический анализ.
    
    Attributes:
        macd_params (dict): Параметры MACD (fast, slow, signal)
        zone_params (dict): Параметры зон (min_duration, min_amplitude)
    
    Example (DEPRECATED):
        >>> analyzer = MACDZoneAnalyzer()  # ⚠️ Не рекомендуется
        >>> result = analyzer.analyze_complete(data)
        >>> print(f"Найдено зон: {len(result.zones)}")
        
    Example (рекомендуемый):
        >>> result = analyze_zones(data).with_indicator('custom', 'macd').build()
    """
    
    def __init__(self, macd_params=None, zone_params=None):
        """
        Инициализация анализатора.
        
        Args:
            macd_params (dict, optional): Параметры MACD. 
                Defaults to {'fast': 12, 'slow': 26, 'signal': 9}.
            zone_params (dict, optional): Параметры зон.
                Defaults to {'min_duration': 2, 'min_amplitude': 0.001}.
        """
    
    def analyze_complete(self, data):
        """
        Выполняет полный анализ данных.
        
        ⚠️ DEPRECATED: Используйте analyze_zones().build() вместо этого метода.
        
        Args:
            data (pd.DataFrame): OHLCV данные
            
        Returns:
            ZoneAnalysisResult: Результат анализа с зонами и статистикой
            
        Raises:
            DataError: Если данные некорректны
            AnalysisError: Если анализ не может быть выполнен
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

**Начать изучение:** [Core Modules](core/) 🏗️
