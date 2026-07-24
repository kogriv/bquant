# User Guide - Руководство пользователя BQuant

## 📖 Обзор

Руководство пользователя BQuant содержит всю необходимую информацию для эффективного использования библиотеки.

## 📚 Содержание

### 🚀 [Quick Start](quick_start.md) - Быстрый старт
- Установка BQuant
- Первый анализ за 5 минут
- Основные концепции

### 🧠 [Core Concepts](core_concepts.md) - Базовые концепции
- Универсальный пайплайн Zone Analysis
- Конфигурация индикаторов и стратегий
- Как интерпретировать результаты `ZoneAnalysisResult`
- Переход к практическим сценариям

### 🔄 [Zone Analysis Guide](zone_analysis.md) - Полный пайплайн анализа зон
- Детальная архитектура системы
- Пошаговое выполнение pipeline
- Стратегии детекции зон (ZeroCrossing, Threshold, LineCrossing, Preloaded, Combined)
- Извлечение признаков и анализ
- Модели данных (ZoneInfo, ZoneAnalysisResult)
- Примеры использования от простых до продвинутых
- Кэширование и персистентность

### 💾 [Caching Reference](caching.md) - Справочник по кэшированию
- Архитектура кэша (memory + disk)
- Где хранится кэш, как настраивать
- Когда и как очищать кэш
- Zone Analysis: формирование ключей, авто-инвалидация

### ✅ [Best Practices](best_practices.md) - Практика анализа зон
- Когда выбирать полный пайплайн vs модульные шаги
- Рекомендуемая структура хранения артефактов
- Паттерны переиспользования результатов
- Версионирование и интеграция с внешними системами

### 📋 [Структура результата и экспорт в артефакты](zone_analysis_result.md) - Справочник по результату анализа зон
- Полная структура `ZoneAnalysisResult` и `ZoneInfo` (поля, иерархия, источники)
- Структура `zone.features` и `metadata` (swing_metrics, shape_metrics и др.)
- Соответствие полей результата и артефактам из Best Practices
- Примеры кода для получения файлов 01_…08_, full_analysis, summary

### 🏗️ [Core Modules](../api/core/README.md) - Основные модули
- Архитектура BQuant
- Основные компоненты
- Принципы работы

### 📊 [Data Management](../api/data/README.md) - Работа с данными
- Загрузка данных
- Обработка и очистка
- Валидация данных
- Sample данные

### 📈 [Technical Analysis](../api/indicators/README.md) - Технический анализ
- Universal Zone Analysis Pipeline v2.1
- Анализ зон с любыми индикаторами (MACD, RSI, AO, custom)
- Создание индикаторов
- «Простой способ» работы с pandas-ta через [LibraryManager](../api/indicators/library_manager.md)

### 📊 [Visualization](../api/visualization/README.md) - Визуализация
- Создание графиков
- Настройка тем
- Экспорт графиков
- Интерактивные элементы

### 🔬 [Statistical Analysis](../api/analysis/README.md) - Статистический анализ
- Гипотезное тестирование
- Анализ распределений
- Корреляционный анализ
- Интерпретация результатов

### ⚡ [Performance](../api/core/README.md) - Производительность
- Оптимизация алгоритмов
- Кэширование
- Профилирование
- Масштабирование

### 🔧 [Configuration](../api/core/README.md) - Конфигурация
- Настройка параметров
- Логирование
- Обработка ошибок
- Пользовательские настройки

## 🎯 Целевая аудитория

Это руководство предназначено для:

- **Аналитиков данных** - работа с финансовыми данными
- **Трейдеров** - технический анализ и индикаторы
- **Исследователей** - статистический анализ и тестирование гипотез
- **Разработчиков** - интеграция BQuant в свои проекты

## 📋 Предварительные требования

### Базовые знания
- Python 3.11+
- Основы работы с pandas и numpy
- Понимание финансовых данных (OHLCV)

### Установленные библиотеки
```bash
pip install pandas numpy matplotlib seaborn plotly
```

## 🚀 Начать изучение

Рекомендуемый порядок изучения:

1. **[Quick Start](quick_start.md)** - Быстрый старт
2. **[Core Concepts](core_concepts.md)** - Ключевые идеи Universal Pipeline
3. **[Zone Analysis Guide](zone_analysis.md)** - Детальное описание пайплайна анализа зон
4. **[Best Practices](best_practices.md)** - Практические рекомендации и рабочие паттерны
5. **[Core Modules](../api/core/README.md)** - Основные модули
6. **[Data Management](../api/data/README.md)** - Работа с данными
7. **[Technical Analysis aka Indicators](../api/indicators/README.md)** - Universal Zone Analysis v2.1
8. **[Visualization](../api/visualization/README.md)** - Визуализация
9. **[Statistical Analysis](../api/analysis/README.md)** - Статистический анализ

## 💡 Советы по изучению

- **Практикуйтесь** - Используйте sample данные для экспериментов
- **Изучайте примеры** - Смотрите папку `examples/` для готовых решений
- **Задавайте вопросы** - Используйте GitHub Issues для вопросов
- **Вносите вклад** - Делитесь своими примерами и улучшениями

## 🔗 Связанные разделы

- **[API Reference](../api/README.md)** - Подробная документация API
- **[Tutorials](../tutorials/README.md)** - Обучающие материалы
- **[Examples](../examples/README.md)** - Примеры использования
- **[Developer Guide](../developer_guide/README.md)** - Для разработчиков
- **[MIGRATION_v2](../migration/MIGRATION_v2.md)** - Переход со старого `MACDZoneAnalyzer`

---

**Следующий шаг:** [Quick Start](quick_start.md) 🚀
