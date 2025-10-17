# Zone Analysis Architecture Documentation

Документация архитектуры универсального анализатора зон (Zone Analysis).

---

## Документы

### [`zonan.md`](zonan.md) - Основная архитектура и спецификация

**Версия:** v7 (Complete Specification + Caching)  
**Объем:** ~3750 строк  
**Статус:** Ready for Implementation

**Содержание:**
- Проблема текущего монолитного `MACDZoneAnalyzer`
- Решение: двухслойная архитектура + Pipeline
- Слой 1: Zone Detection Strategies (5 стратегий)
- Слой 2: Universal Zone Analyzer
- Pipeline + Builder (fluent API)
- Интеграция с `IndicatorFactory`
- **Полные заготовки кода** для всех компонентов
- **Точки расширения** архитектуры (7 областей)
- **Визуализация** (детальный просмотр зон)
- **Кэширование** (автоматическое + персистентное хранение)
- **План миграции** (5 этапов, 11-17 дней)

**Используйте для:**
- Понимания архитектуры
- Реализации компонентов (есть готовые заготовки)
- Планирования работ
- Reference при разработке

---

### [`zomodul.md`](zomodul.md) - Модульное использование компонентов

**Версия:** v1.0  
**Объем:** ~650 строк  
**Статус:** Companion Guide

**Содержание:**
- Принципы модульности архитектуры
- Граф зависимостей компонентов (5 уровней)
- **12 сценариев** модульного использования:
  1. Только детекция зон (без анализа)
  2. Анализ готовых зон (без детекции)
  3. Только извлечение признаков
  4. Только статистический анализ
  5. Только тестирование гипотез
  6. Только анализ последовательностей
  7. Пошаговое построение с сохранением
  8. Комбинирование результатов разных стратегий
  9. Работа с preloaded зонами
  10. Визуализация без полного анализа
  11. Feature engineering для ML
  12. Кастомный анализ с выбором компонентов
- Сводная таблица сохранения/загрузки
- Best Practices
- Интеграция с MT5/cTrader

**Используйте для:**
- Использования компонентов по отдельности
- Сохранения промежуточных результатов
- Интеграции с внешними системами
- ML feature engineering
- Оптимизации производительности

---

## Quick Start

### Полный Pipeline (простой способ)

```python
from bquant.analysis.zones import analyze_zones

result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast=12, slow=26)
    .detect_zones('zero_crossing', indicator_col='macd')
    .analyze(clustering=True)
    .build()
)

# Визуализация
result.visualize('overview')

# Сохранение
result.save('results/analysis.pkl')
```

### Модульное использование (гибкий способ)

```python
from bquant.analysis.zones.detection import ZoneDetectionRegistry, ZoneDetectionConfig
from bquant.analysis.zones import UniversalZoneAnalyzer

# Шаг 1: Детекция
detector = ZoneDetectionRegistry.get('zero_crossing')
zones = detector.detect_zones(df, config)
pickle.dump(zones, open('zones.pkl', 'wb'))

# Шаг 2: Анализ (позже)
zones = pickle.load(open('zones.pkl', 'rb'))
analyzer = UniversalZoneAnalyzer()
result = analyzer.analyze_zones(zones, df)
result.save('analysis.pkl')
```

---

## Связанные документы

- **Основная архитектура:** [`zonan.md`](zonan.md)
- **Модульное использование:** [`zomodul.md`](zomodul.md)
- **Migration plan:** См. "План миграции" в `zonan.md`
- **Extension points:** См. "Точки расширения" в `zonan.md`

---

**Обновлено:** 2025-10-17  
**Авторы:** AI Assistant (Claude Sonnet 4.5), Ivan

