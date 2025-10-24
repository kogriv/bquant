# Examples - Примеры использования BQuant

## 📚 Обзор

Примеры использования BQuant демонстрируют различные сценарии применения библиотеки от простых до сложных.

## 🗂️ Категории примеров

### 🚀 Universal Zone Analysis Examples
- **02a_universal_zones.py** - **MAIN TUTORIAL** (297 строк)
  - **Universal API demonstration:** MACD, RSI, AO, MA crossover, Preloaded zones
  - **Zero Code Duplication:** один API для всех индикаторов
  - **Caching & Persistence:** 3 формата сохранения (pickle, JSON, parquet)
  - **Modular Usage:** детекция отдельно, анализ отдельно

- **02_macd_zone_analysis.py** - **MIGRATION GUIDE** (241 строка)
  - **Legacy vs New API:** сравнение старого и нового подходов
  - **Deprecation Warnings:** демонстрация предупреждений
  - **Performance Comparison:** время выполнения и использование памяти
  - **Multiple Strategies:** zero_crossing, line_crossing, combined rules

### 📈 Advanced Features Examples  
- **05_strategies_demo.py** - **STRATEGIES DEEP DIVE**
  - **Swing Strategies:** FindPeaks, PivotPoints, ZigZag
  - **Strategy Configuration:** `.with_strategies()` API
  - **Feature Extraction:** доступ к zone.features

- **06_regression_demo.py** - **REGRESSION ANALYSIS**
  - **Statistical Modeling:** регрессионный анализ зон
  - **Feature Engineering:** подготовка данных для ML
  - **Model Validation:** оценка качества моделей

- **07_validation_demo.py** - **VALIDATION FRAMEWORK**
  - **Cross-validation:** проверка стабильности результатов
  - **Performance Metrics:** оценка качества детекции
  - **Robustness Testing:** тестирование на разных данных

### 🔬 Research Notebooks
- **03_zones_universal.py** - Deep dive analysis (412 строк)
- **03_analysis_new_features.py** - Advanced features testing

## 🎯 Быстрый старт с примерами

### 1. Universal Zone Analysis

```python
# examples/02a_universal_zones.py
import bquant as bq
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

# Загружаем данные
data = get_sample_data('tv_xauusd_1h')

# Universal Pipeline - любой индикатор
result = (
    analyze_zones(data)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='rsi', 
                  upper_threshold=70, lower_threshold=30)
    .analyze(clustering=True)
    .build()
)

# Выводим результаты
print(f"Найдено зон: {len(result.zones)}")
print(f"Статистика: {result.statistics}")
```

### 2. Migration Guide - Legacy vs New API

```python
# examples/02_macd_zone_analysis.py

# ⚠️ DEPRECATED: Старый способ
from bquant.indicators import MACDZoneAnalyzer
analyzer = MACDZoneAnalyzer()
result = analyzer.analyze_complete(data)

# ✅ NEW: Universal Pipeline
from bquant.analysis.zones import analyze_zones
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)
    .build()
)
```

### 3. Advanced Features - Strategies & Analysis

```python
# examples/05_strategies_demo.py
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

# Advanced strategies
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(
        swing='find_peaks',      # Swing analysis
        divergence='classic',    # Divergence detection
        volume='standard',       # Volume analysis
        volatility='combined'    # Volatility analysis
    )
    .analyze(clustering=True)
    .build()
)

# Hypothesis tests автоматически в pipeline
if result.hypothesis_tests:
    for test_name, test_result in result.hypothesis_tests.results.items():
        print(f"{test_name}: p={test_result['p_value']:.4f}")
```

## 🗺️ Examples Navigation

### 🚀 Quick Start
- [Universal Zones](02a_universal_zones.py) - **START HERE** - любой индикатор за 3 строки

### 📚 Learning Path  
- [Migration Guide](02_macd_zone_analysis.py) - переход с deprecated API
- [Strategies Deep Dive](05_strategies_demo.py) - все типы стратегий
- [Regression Analysis](06_regression_demo.py) - статистическое моделирование
- [Validation Framework](07_validation_demo.py) - проверка качества

### 🔗 Cross-References
- **API Documentation:** [Pipeline API](../api/analysis/pipeline.md)
- **Strategy Reference:** [Detection Strategies](../api/analysis/strategies.md)
- **Visualization:** [Zone Visualization](../api/visualization/README.md)
- **Developer Guide:** [Architecture Patterns](../developer_guide/README.md)

## 📊 Структура каждого примера

### 📖 Заголовок и описание
```python
"""
Пример: Анализ MACD с зонами

Этот пример демонстрирует:
- Загрузку sample данных
- Создание анализатора MACD
- Выполнение полного анализа
- Визуализацию результатов

Автор: BQuant Team
Дата: 2024
"""
```

### 🔧 Импорты и настройка
```python
import bquant as bq
from bquant.data.samples import get_sample_data
from bquant.indicators import MACDZoneAnalyzer
from bquant.visualization import FinancialCharts

# Настройка логирования
import logging
logging.basicConfig(level=logging.INFO)
```

### 💻 Основной код
```python
def main():
    """Основная функция примера"""
    
    # 1. Загрузка данных
    print("Загружаем данные...")
    data = get_sample_data('tv_xauusd_1h')
    
    # 2. Анализ
    print("Выполняем анализ...")
    analyzer = MACDZoneAnalyzer()
    result = analyzer.analyze_complete(data)
    
    # 3. Результаты
    print("Результаты анализа:")
    print(f"  - Зон найдено: {len(result.zones)}")
    print(f"  - Статистика: {result.statistics}")
    
    # 4. Визуализация
    print("Создаем визуализацию...")
    charts = FinancialCharts()
    fig = charts.plot_macd_with_zones(data, result.zones)
    fig.show()

if __name__ == "__main__":
    main()
```

### 📋 Документация
- **Описание** - Что делает пример
- **Требования** - Необходимые зависимости
- **Запуск** - Как запустить пример
- **Результаты** - Что ожидать на выходе

## 📏 Example Quality Standards

### Self-contained
- **Независимость** - каждый пример работает без внешних зависимостей
- **Sample данные** - использование встроенных sample данных
- **Полный код** - все необходимые импорты и функции включены

### Well-documented
- **Подробные комментарии** - объяснение каждого шага
- **Docstrings** - документация для всех функций
- **Примеры вывода** - ожидаемые результаты

### Error-handled
- **Graceful degradation** - обработка отсутствующих опциональных компонентов
- **Try/except блоки** - обработка возможных ошибок
- **Информативные сообщения** - понятные сообщения об ошибках

### Performance-aware
- **Демонстрация кэширования** - показ возможностей оптимизации
- **Время выполнения** - измерение производительности
- **Memory usage** - контроль использования памяти

## 🔗 Integration with Documentation

### API Cross-links
- **Ссылки на API** - каждый пример ссылается на соответствующие разделы API
- **Code examples** - примеры кода в документации соответствуют примерам
- **Parameter references** - ссылки на параметры и их значения

### Tutorial Integration
- **Связь с учебными материалами** - примеры интегрированы с tutorials
- **Learning path** - логическая последовательность изучения
- **Progressive complexity** - от простого к сложному

### Developer Resources
- **Архитектурные принципы** - ссылки на design patterns
- **Extension points** - показ возможностей расширения
- **Best practices** - демонстрация лучших практик

## 🚀 Как запускать примеры

### 1. Клонирование репозитория
```bash
git clone https://github.com/your-username/bquant.git
cd bquant
```

### 2. Установка зависимостей
```bash
pip install -e .
```

### 3. Запуск примера
```bash
# Базовый пример
python docs/examples/basic/simple_macd.py

# Продвинутый пример
python docs/examples/advanced/macd_zone_analysis.py

# С параметрами
python docs/examples/real_world/trading_analysis.py --symbol XAUUSD --timeframe 1h
```

### 4. В Jupyter Notebook
```python
# Загружаем пример как модуль
import sys
sys.path.append('docs/examples/basic')
import simple_macd

# Запускаем
simple_macd.main()
```

## 💡 Советы по использованию примеров

### 🎯 Для изучения
- **Начните с basic/** - Освойте базовые концепции
- **Изучайте код** - Читайте комментарии и docstrings
- **Экспериментируйте** - Изменяйте параметры и наблюдайте результаты
- **Задавайте вопросы** - Если что-то непонятно

### 🔧 Для разработки
- **Используйте как шаблоны** - Адаптируйте под свои нужды
- **Изучайте паттерны** - Обратите внимание на структуру кода
- **Тестируйте изменения** - Проверяйте работу после модификаций
- **Документируйте** - Добавляйте комментарии к своим изменениям

### 🚀 Для продакшена
- **Адаптируйте под данные** - Замените sample данные на реальные
- **Добавьте обработку ошибок** - Используйте try/except блоки
- **Оптимизируйте производительность** - Примените техники из performance/
- **Настройте логирование** - Добавьте информативные логи

## 🔗 Связанные разделы

- **[User Guide](../user_guide/)** - Руководство пользователя
- **[API Reference](../api/)** - Справочник API
- **[Tutorials](../tutorials/)** - Обучающие материалы
- **[Developer Guide](../developer_guide/)** - Для разработчиков

## 🤝 Вклад в примеры

### Добавление нового примера
1. **Создайте файл** в соответствующей папке
2. **Добавьте документацию** - описание, требования, запуск
3. **Протестируйте** - убедитесь что пример работает
4. **Создайте PR** - предложите изменения

### Структура нового примера
```python
"""
Название: Краткое описание

Подробное описание что делает пример и как его использовать.

Требования:
- bquant
- pandas
- matplotlib

Запуск:
python examples/category/example_name.py

Автор: Ваше имя
Дата: YYYY-MM-DD
"""

import bquant as bq
# ... остальные импорты

def main():
    """Основная функция"""
    pass

if __name__ == "__main__":
    main()
```

---

**Начать изучение:** [Basic Examples](basic/) 🚀
