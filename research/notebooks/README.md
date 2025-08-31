# BQuant Research Notebooks

Jupyter ноутбуки и Python-скрипты для исследований и анализа с использованием BQuant.

## 📓 Notebook-Style Scripts API

Для исследовательских задач, требующих версионирования и возможности запуска в CI/CD, в проекте используется подход "notebook-style" Python-скриптов. Они сочетают интерактивность Jupyter с надежностью обычных скриптов.

**Функциональность перенесена в основной пакет BQuant:**

➡️ **[API Documentation: bquant.core.nb](../../docs/api/core/nb.md)** - Полная документация API

### Быстрый старт

```python
from bquant.core.nb import NotebookSimulator

# Одна строка - всё настроено автоматически!
nb = NotebookSimulator("My Analysis Script")

# Пошаговое выполнение
nb.step("Data Loading")
# код загрузки данных
nb.success("Data loaded successfully")
nb.wait()

nb.step("Analysis")
# код анализа
nb.success("Analysis completed")
nb.wait()

nb.finish()
```

### Преимущества нового API

- **Нулевой boilerplate код** - одна строка инициализации
- **Автоопределение параметров** - имя скрипта, лог файл, аргументы CLI
- **Встроенная обработка ошибок** - контекстные менеджеры для критических операций  
- **Богатое форматирование** - эмодзи, разделители, структурированный вывод
- **Автоматическое логирование** - консоль + файл без дополнительной настройки

## 📓 Планируемые ноутбуки

- **01_data_exploration.ipynb** - Исследование финансовых данных
- **02_macd_zones_analysis.ipynb** - Анализ MACD зон и их характеристик
- **03_hypothesis_testing.ipynb** - Статистическое тестирование гипотез
- **04_visualization_examples.ipynb** - Примеры визуализации данных

---

*Создано в рамках миграции BQuant проекта*