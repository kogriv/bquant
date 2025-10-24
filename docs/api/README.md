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

### По функциональности

#### 📊 Работа с данными
- `bquant.data.loader.load_ohlcv_data()` - Загрузка OHLCV данных
- `bquant.data.samples.get_sample_data()` - Получение sample данных
- `bquant.data.processor.clean_ohlcv_data()` - Очистка данных

#### 📈 Технические индикаторы
- `bquant.indicators.MACDZoneAnalyzer` - ⚠️ Deprecated wrapper (используйте analyze_zones())
- `bquant.indicators.MACDPreloadedIndicator` - PRELOADED MACD индикатор
- `bquant.indicators.BaseIndicator` - Базовый класс индикатора
- `bquant.indicators.IndicatorFactory` - Фабрика индикаторов

#### 🔬 Universal Zone Analysis (v2.1)
- `bquant.analysis.zones.analyze_zones()` - Universal Pipeline entry point
- `bquant.analysis.zones.ZoneAnalysisBuilder` - Fluent builder interface
- `bquant.analysis.zones.UniversalZoneAnalyzer` - Zone-agnostic analyzer
- `bquant.analysis.statistical.run_all_hypothesis_tests()` - Статистические тесты

#### 📊 Визуализация
- `bquant.visualization.FinancialCharts` - Создание финансовых графиков
- `bquant.visualization.ZoneVisualizer` - Визуализация зон
- `bquant.visualization.StatisticalPlots` - Статистические графики

### По типу

#### 🏗️ Классы
- `BaseIndicator` - Базовый класс для индикаторов
- `PreloadedIndicator` - Базовый класс для PRELOADED индикаторов
- `MACDPreloadedIndicator` - PRELOADED MACD индикатор
- `MACDZoneAnalyzer` - ⚠️ Deprecated анализатор MACD
- `ZoneAnalysisBuilder` - Fluent builder для Universal Pipeline
- `UniversalZoneAnalyzer` - Zone-agnostic анализатор
- `FinancialCharts` - Создание графиков

#### 🔧 Функции
- `load_ohlcv_data()` - Загрузка данных
- `get_sample_data()` - Получение sample данных
- `analyze_zones()` - Universal Pipeline entry point
- `run_all_hypothesis_tests()` - Статистические тесты
- `create_candlestick_chart()` - Создание candlestick графика

#### 📋 Исключения
- `BQuantError` - Базовое исключение BQuant
- `DataError` - Ошибки данных
- `AnalysisError` - Ошибки анализа
- `VisualizationError` - Ошибки визуализации

## 📖 Как читать документацию

### Структура документации класса

```python
class MACDZoneAnalyzer:
    """
    Анализатор MACD с идентификацией зон.
    
    Этот класс выполняет полный анализ MACD индикатора,
    включая расчет значений, идентификацию зон и статистический анализ.
    
    Attributes:
        macd_params (dict): Параметры MACD (fast, slow, signal)
        zone_params (dict): Параметры зон (min_duration, min_amplitude)
    
    Example:
        >>> analyzer = MACDZoneAnalyzer()
        >>> result = analyzer.analyze_complete(data)
        >>> print(f"Найдено зон: {len(result.zones)}")
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
