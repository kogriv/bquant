# Tutorials - Обучающие материалы BQuant

## 📚 Обзор

Обучающие материалы помогут вам освоить BQuant от базовых концепций до продвинутых техник.

## 🎓 Содержание

### 🚀 [Quick Start (5 minutes)](../examples/02a_universal_zones.py) - Universal Zone Analysis
- **7 разделов:** MACD, RSI, AO, MA crossover, Preloaded zones, Caching, Modular usage
- **Universal API:** демонстрация fluent builder для всех индикаторов
- **Zero Code Duplication:** таблица сравнения индикаторов без дублирования кода
- **297 строк** production-ready кода

### 📊 [Deep Dive (30 minutes)](../research/notebooks/03_zones_universal.py) - Complete Analysis Pipeline
- **10 шагов NotebookSimulator:** от загрузки данных до модульных сценариев
- **Old vs New API Comparison:** производительность и функциональность
- **Detection Strategies Experiments:** все 5 типов стратегий
- **Parameter Sensitivity Analysis:** влияние параметров на качество зон
- **Full Analysis Pipeline:** features, clustering, statistical tests, sequence analysis
- **412 строк** comprehensive analysis

### 🔬 [Advanced Features](../research/notebooks/03_analysis_new_features.py) - Swing, Divergence, Regression
- **10 steps:** от базового анализа до regression & validation
- **Swing Strategies:** FindPeaks, PivotPoints, ZigZag (все 3 работают!)
- **Advanced Features:** divergence, volume, volatility analysis
- **v2.1 Migration:** полный переход с deprecated API
- **Hypothesis Tests Automation:** статистические тесты в pipeline

### 🔄 [Migration Guide](../examples/02_macd_zone_analysis.py) - Old vs New API
- **Legacy vs New API:** сравнение старого и нового подходов
- **Deprecation Warnings:** демонстрация предупреждений
- **Performance Comparison:** время выполнения и использование памяти
- **Multiple Strategies:** zero_crossing, line_crossing, combined rules
- **241 строка** migration examples

### 🏗️ [Future Tutorials (TODO)] - Planned Materials
- **Custom Strategy Development** - создание собственных стратегий детекции
- **ML Integration Patterns** - интеграция с машинным обучением
- **Performance Optimization** - оптимизация производительности
- **Production Deployment** - развертывание в продакшене

## 🎯 Целевая аудитория

### 👶 Начинающие
- **Quick Start** - Universal API basics
- **Migration Guide** - Transition from legacy API

### 👨‍💻 Продвинутые пользователи
- **Deep Dive** - Complete analysis pipeline
- **Advanced Features** - Swing, divergence, regression

### 🚀 Эксперты
- **Future Tutorials** - Custom strategies, ML integration
- **Performance Optimization** - Production deployment

## 📋 Предварительные требования

### Базовые знания
- Python 3.8+
- Pandas и NumPy
- Основы статистики
- Финансовые данные (OHLCV)

### Установка
```bash
pip install bquant
```

## 🚀 Рекомендуемый порядок изучения

### Architecture Learning Path
1. **[Quick Start](../examples/02a_universal_zones.py)** - Universal API basics → Fluent Builder Pattern
2. **[Deep Dive](../research/notebooks/03_zones_universal.py)** - Complete understanding → Two-Layer Architecture
3. **[Advanced Features](../research/notebooks/03_analysis_new_features.py)** - Advanced capabilities → Strategy Configuration
4. **[Migration Guide](../examples/02_macd_zone_analysis.py)** - Legacy transition → Deprecation Patterns

## 💡 Советы по изучению

### 🎯 Практический подход
- **Выполняйте все примеры** - Не просто читайте, а запускайте код
- **Экспериментируйте** - Изменяйте параметры и наблюдайте результаты
- **Используйте sample данные** - Для безопасных экспериментов
- **Ведите заметки** - Записывайте важные моменты

### 🔧 Технические советы
- **Используйте Jupyter Notebooks** - Для интерактивного изучения
- **Создайте виртуальное окружение** - Для изоляции зависимостей
- **Изучайте ошибки** - Они помогают понять систему
- **Задавайте вопросы** - Используйте GitHub Issues

### 📚 Дополнительные ресурсы
- **[API Reference](../api/)** - Подробная документация
- **[Examples](../examples/)** - Готовые примеры
- **[User Guide](../user_guide/)** - Руководство пользователя

## 🎓 Структура каждого tutorial

Каждый tutorial содержит:

### 📖 Теория
- Объяснение концепций
- Математические основы
- Принципы работы

### 💻 Практика
- Пошаговые примеры
- Готовый код
- Интерактивные упражнения

### 🔍 Анализ
- Интерпретация результатов
- Лучшие практики
- Типичные ошибки

### 🚀 Следующие шаги
- Продолжение изучения
- Дополнительные ресурсы
- Практические задания

## 🤝 Поддержка

### Если что-то не работает
1. **Проверьте версии** - Убедитесь в совместимости
2. **Изучите ошибки** - Читайте сообщения об ошибках
3. **Создайте issue** - На GitHub с подробным описанием

### Если нужна помощь
1. **GitHub Issues** - Для багов и проблем
2. **GitHub Discussions** - Для вопросов и обсуждений
3. **Documentation** - Изучите API Reference

## 🔗 Связанные разделы

- **[User Guide](../user_guide/)** - Руководство пользователя
- **[API Reference](../api/)** - Справочник API
- **[Examples](../examples/)** - Примеры использования
- **[Developer Guide](../developer_guide/)** - Для разработчиков

---

**Начать изучение:** [Quick Start Tutorial](quick_start_tutorial.md) 🚀
