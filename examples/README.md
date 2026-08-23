# BQuant Examples

Публичные примеры использования BQuant для быстрого старта и документации.

## 📁 Структура примеров

### Базовые примеры

**01_basic_indicators.py**
- Основы работы с индикаторами
- IndicatorFactory и разные источники (custom, pandas_ta, talib)
- Простые примеры расчета MACD, RSI, SMA

### Zone Analysis (анализ зон)

**02_macd_zone_analysis.py** ⭐ **START HERE**
- Быстрый пресет `analyze_macd_zones()` — одна строка
- Fluent API (builder) `analyze_zones()` — полный контроль
- Разные стратегии детекции зон
- Модульное использование
- Базовая визуализация

**Рекомендуется для:**
- Знакомства с универсальной архитектурой
- Выбора между пресетом и билдером
- Изучения основ zone analysis

**02a_universal_zones.py** ⭐ **RECOMMENDED**
- Демонстрация универсального API для ВСЕХ индикаторов
- MACD, RSI, AO, MA crossover, preloaded zones
- Кэширование и персистентное хранение
- Модульное использование компонентов

**Рекомендуется для:**
- Понимания универсальности архитектуры
- Изучения разных стратегий детекции
- Работы с разными индикаторами

**04_comprehensive_analysis.py**
- Полный pipeline от начала до конца
- Подготовка данных → индикаторы → детекция → анализ → визуализация
- Сравнение разных индикаторов
- Сохранение и загрузка результатов

**Рекомендуется для:**
- Создания production-ready pipelines
- Понимания всех этапов анализа
- Работы с результатами

**08_macd_swing_analysis.py** ⭐ **NEW**
- Правильное использование встроенных SwingMetrics (23 поля)
- Анализ колебаний ВНУТРИ зон (не просто "от начала до конца")
- ZigZag из pandas_ta через LibraryManager
- Оценка "дает ли море" - есть ли альфа в свингах
- БЕЗ хардкода анализа - только встроенный функционал пакета

**Рекомендуется для:**
- Анализа профпригодности индикаторов
- Понимания SwingMetrics и их применения
- Тестирования swing торговых стратегий
- Изучения metadata['swing_metrics'] структуры

**09_zones_visualization_demo.py** ⭐ **NEW**
- Все возможности визуализации зон
- Обзорная, детальная, сравнительная и статистическая визуализация
- Автоматическое определение индикаторов из контекста
- Кастомизация внешнего вида и настроек
- Поддержка разных backends (Plotly/Matplotlib)

**Рекомендуется для:**
- Визуального анализа зон
- Создания презентационных графиков
- Понимания различий между типами визуализации
- Изучения настроек визуализации

### Другие примеры

**03_data_processing.py**
- Работа с данными (загрузка, валидация, обработка)
- Производные индикаторы

**05_strategies_demo.py**
- Демонстрация различных стратегий анализа
- Swing, shape, divergence, volatility, volume strategies

**06_regression_demo.py**
- Регрессионный анализ зон
- Предсказание длительности и доходности

**07_validation_demo.py**
- Валидация моделей и стратегий
- Walk-forward тестирование

## 🚀 Быстрый старт

### Для новых пользователей

**Шаг 1:** Базовый анализ MACD зон
```bash
python examples/02_macd_zone_analysis.py
```

**Шаг 2:** Универсальный подход для разных индикаторов
```bash
python examples/02a_universal_zones.py
```

**Шаг 3:** Полный comprehensive pipeline
```bash
python examples/04_comprehensive_analysis.py
```

### Для опытных пользователей

Смотрите также:
- `research/notebooks/` - детальные исследовательские ноутбуки с NotebookSimulator
- `devref/gaps/zo/zomodul.md` - модульное использование компонентов (12 сценариев)
- `devref/gaps/zo/zonan.md` - полная архитектура и спецификация

## 🎯 Рекомендуемый путь обучения

1. **Начинающие:**
   - `01_basic_indicators.py` - основы индикаторов
   - `02_macd_zone_analysis.py` - основы zone analysis
   - `03_data_processing.py` - работа с данными

2. **Средний уровень:**
   - `02a_universal_zones.py` - универсальный API
   - `04_comprehensive_analysis.py` - полный pipeline
   - `05_strategies_demo.py` - разные стратегии

3. **Продвинутые:**
   - `06_regression_demo.py` - ML подходы
   - `07_validation_demo.py` - валидация моделей
   - `research/notebooks/03_zones_universal.py` - детальное исследование

## 📖 Ключевые концепции

### Универсальная архитектура (v2.0+)

**Старый подход (удалён в 0.0.5, приведён для миграции):**
```text
from bquant.indicators.macd import MACDZoneAnalyzer
analyzer = MACDZoneAnalyzer()
result = analyzer.analyze_complete(df)
```

**Новый подход (recommended):**
```python
from bquant.analysis.zones import analyze_zones

result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .analyze(clustering=True)
    .build()
)
```

**Преимущества нового подхода:**
- ✅ Один API для всех индикаторов (MACD, RSI, AO, любой кастомный)
- ✅ Множество стратегий детекции (zero_crossing, threshold, line_crossing, preloaded, combined)
- ✅ Модульность - используйте только нужные компоненты
- ✅ Автоматическое кэширование результатов
- ✅ Расширяемость - легко добавлять новые стратегии

### Convenience Presets

Для частых сценариев используйте готовые функции:

```python
from bquant.analysis.zones.presets import (
    analyze_macd_zones,
    analyze_rsi_zones,
    analyze_ao_zones
)

# Одна строка вместо builder цепочки
result = analyze_macd_zones(df, fast=12, slow=26, signal=9)
```

## 🔧 Требования

- Python 3.8+
- BQuant пакет: `pip install -e .`
- Опционально: matplotlib, plotly для визуализации

## 💡 Советы

1. **Начните с простого:** Используйте preset функции для быстрого старта
2. **Изучите builder API:** Для большей гибкости и контроля
3. **Экспериментируйте:** Пробуйте разные стратегии и параметры
4. **Используйте кэширование:** Включено по умолчанию, ускоряет повторные запуски
5. **Сохраняйте результаты:** Используйте result.save() для персистентности

## 🐛 Помощь и поддержка

- **Документация:** `docs/api/analysis/zones.md`
- **Архитектура:** `devref/gaps/zo/zonan.md`
- **Модульность:** `devref/gaps/zo/zomodul.md`
- **Issues:** GitHub Issues

## 📝 Примечания

- Все примеры самодостаточные - можно запускать независимо
- Данные генерируются автоматически для демонстрации
- Для production использования замените на реальные данные
- Примеры оптимизированы для понимания, не для производительности
