# Примеры использования BQuant

## 📚 Обзор

Примеры использования BQuant демонстрируют различные сценарии применения библиотеки от простых до сложных.

## 🗂️ Категории примеров

### 🚀 Примеры универсального анализа зон
- **01_basic_indicators.py** — **ОСНОВЫ ИНДИКАТОРОВ** (314 строк)
  - **IndicatorFactory и LibraryManager:** базовые SMA, RSI, MACD, Bollinger Bands
  - **Создание данных:** `create_sample_ohlcv_data()` без внешних источников
  - **Авто-загрузка библиотек:** `LibraryManager.load_all_libraries()` и интеграция с pandas-ta

- **02a_universal_zones.py** — **ГЛАВНЫЙ ТУТОРИАЛ** (552 строки)
  - **Универсальный API:** MACD, RSI, AO, MA crossover, Stochastic, кастомные индикаторы и preloaded-зоны
  - **Отсутствие дублирования:** один pipeline для всех стратегий детекции
  - **Кэширование и сохранение:** pickle, JSON и parquet для результатов анализа
  - **Модульный запуск:** отдельные функции для подготовки, анализа и визуализации

- **02_macd_zone_analysis.py** — **РУКОВОДСТВО ПО МИГРАЦИИ** (319 строк)
- **Legacy vs Universal (сравнение):** пошаговое сопоставление старого и нового API
- **Предупреждения об устаревании (Deprecation Warnings):** демонстрация предупреждений и путей миграции
- **Бенчмарк производительности:** измерение времени и памяти для обоих подходов
  - **Несколько стратегий:** `zero_crossing`, `line_crossing`, комбинированные правила

### 📈 Примеры продвинутых возможностей
- **03_data_processing.py** — **ДЕМОНСТРАЦИЯ PIPELINE ДАННЫХ** (510 строк)
- **ETL-конвейер:** очистка, агрегация и нормализация рыночных данных
- **Инженерия признаков (feature engineering):** генерация признаков для последующего анализа зон
  - **Отчётность:** структурированный вывод метрик и логирование прогресса

- **04_comprehensive_analysis.py** — **ПОЛНЫЙ PIPELINE** (301 строка)
  - **UniversalZoneAnalyzer:** конфигурация через `ZoneDetectionRegistry`
  - **Смешанные режимы рынка:** демонстрация тренда, коррекции и боковика
  - **Полный цикл:** от подготовки данных до сохранения результатов анализа

- **05_strategies_demo.py** — **ГЛУБОКОЕ ПОГРУЖЕНИЕ В СТРАТЕГИИ** (339 строк)
- **Колебательные и дивергенционные стратегии:** FindPeaks, PivotPoints, ZigZag, классические дивергенции
- **`.with_strategies()` API:** комбинирование нескольких стратегий в одном пайплайне
- **`zone.features`:** доступ к расширенным метрикам и печать симметрии длительности

- **06_regression_demo.py** — **РЕГРЕССИОННЫЙ АНАЛИЗ** (273 строки)
  - **Статистическое моделирование:** регрессия по метрикам зон
  - **Подготовка признаков:** масштабирование, train/test split и оценка
  - **Валидация:** сравнение моделей и вывод коэффициентов

- **07_validation_demo.py** — **ФРЕЙМВОРК ВАЛИДАЦИИ** (413 строк)
- **Кросс-валидация (cross-validation):** проверка стабильности стратегий на нескольких срезах
  - **Метрики качества:** precision/recall, вероятность срабатывания и устойчивость
  - **Стресс-тесты:** анализ поведения при разных объёмах данных

### 🔬 Исследовательские ноутбуки
- [**03_zones_universal.py**](../../research/notebooks/03_zones_universal.py) — Глубокий разбор универсального анализа зон (412 строк)
- [**03_analysis_new_features.py**](../../research/notebooks/03_analysis_new_features.py) — Тестирование новых аналитических возможностей

## 🎯 Быстрый старт с примерами

### 1. Универсальный анализ зон

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
    .detect_zones('threshold', indicator_col='RSI_14',  # колонка создаётся pandas-ta
                  upper_threshold=70, lower_threshold=30)
    .analyze(clustering=True)
    .build()
)

# Выводим результаты
print(f"Найдено зон: {len(result.zones)}")
if not result.zones:
    print("⚠️ RSI на текущем датасете не пересёк пороги 70/30 — зон может не быть.")
print(f"Статистика: {result.statistics}")
```

### 2. Руководство по миграции — Legacy vs New API

```python
# examples/02_macd_zone_analysis.py

# ⚠️ УСТАРЕВШИЙ СПОСОБ (DEPRECATED)
from bquant.indicators import MACDZoneAnalyzer
analyzer = MACDZoneAnalyzer()
result = analyzer.analyze_complete(data)

# ✅ Новый способ: Universal Pipeline
from bquant.analysis.zones import analyze_zones
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)
    .build()
)
```

### 3. Продвинутые возможности — стратегии и анализ

```python
# examples/05_strategies_demo.py
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

data = get_sample_data('tv_xauusd_1h')

# Продвинутые стратегии
result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(
        swing='find_peaks',      # Анализ swing-движений
        divergence='classic',    # Обнаружение дивергенций
        volume='standard',       # Анализ объёма
        volatility='combined'    # Анализ волатильности
    )
    .analyze(clustering=True)
    .build()
)

# Hypothesis tests автоматически в pipeline
if result.hypothesis_tests:
    for test_name, test_result in result.hypothesis_tests.results.items():
        p_value = test_result.get('p_value')
        if p_value is not None:
            print(f"{test_name}: p={p_value:.4f}")
        else:
            print(f"{test_name}: {test_result}")
```

## 🗺️ Навигация по примерам

### 🚀 Quick Start
- [Basic Indicators](../../examples/01_basic_indicators.py) — стартовая демонстрация IndicatorFactory
- [Universal Zones](../../examples/02a_universal_zones.py) — **НАЧНИТЕ ЗДЕСЬ**: любой индикатор за 3 строки

### 📚 Маршрут изучения
- [Migration Guide](../../examples/02_macd_zone_analysis.py) — переход с deprecated API
- [Strategies Deep Dive](../../examples/05_strategies_demo.py) — все типы стратегий
- [Regression Analysis](../../examples/06_regression_demo.py) — статистическое моделирование
- [Validation Framework](../../examples/07_validation_demo.py) — проверка качества

### 🔗 Перекрёстные ссылки
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
import plotly.io as pio

logging.basicConfig(level=logging.INFO)
pio.renderers.default = "json"  # безопасный renderer для headless-среды
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
    try:
        fig = charts.plot_macd_with_zones(data, result.zones)
        fig.show()
    except Exception as exc:
        print(f"⚠️ Визуализация недоступна: {exc}")

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
git clone https://github.com/bquant-team/bquant.git
cd bquant
```

### 2. Установка зависимостей
```bash
pip install -e .
```

### 3. Запуск примера
```bash
# Базовый пример
python examples/01_basic_indicators.py

# Продвинутый пример
python examples/02a_universal_zones.py

# С параметрами
python examples/06_regression_demo.py
```

### 4. В Jupyter Notebook
```python
# Запускаем пример в интерактивном режиме
from pathlib import Path
import runpy

example_path = Path("examples/02a_universal_zones.py")
try:
    runpy.run_path(example_path, run_name="__main__")
except TypeError as exc:
    print("⚠️ Скрипт ожидает явное имя датасета в get_sample_data():", exc)
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

**Начать изучение:** [02a_universal_zones.py](../../examples/02a_universal_zones.py) 🚀
