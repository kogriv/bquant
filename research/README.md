# BQuant Research Directory

Папка для исследований, экспериментов и аналитических ноутбуков BQuant.

## 📁 Структура

### 📓 `notebooks/`
Jupyter ноутбуки для исследований и анализа:
- Исследование данных и паттернов
- Тестирование гипотез и стратегий
- Прототипирование новых индикаторов
- Демонстрация возможностей BQuant

**Планируемые ноутбуки:**
- `01_data_exploration.ipynb` - Исследование данных
- `02_macd_zones_analysis.ipynb` - Анализ MACD зон
- `03_hypothesis_testing.ipynb` - Статистическое тестирование
- `04_visualization_examples.ipynb` - Примеры визуализации
- `05_performance_optimization.ipynb` - Оптимизация производительности

### 🔬 `methodology/`
Методологические материалы и документация:
- Описание используемых методов анализа
- Теоретические основы индикаторов
- Статистические методы и их применение
- Best practices для количественного анализа

**Планируемые материалы:**
- `statistical_methods.md` - Статистические методы
- `technical_indicators.md` - Технические индикаторы
- `hypothesis_testing.md` - Методы тестирования гипотез
- `data_validation.md` - Валидация данных
- `performance_measurement.md` - Измерение производительности

### 🧪 `experiments/`
Экспериментальные исследования и прототипы:
- Новые алгоритмы и подходы
- Сравнительный анализ методов
- A/B тестирование стратегий
- Экспериментальные индикаторы

**Структура экспериментов:**
```
experiments/
├── experiment_001_new_indicator/
│   ├── README.md           # Описание эксперимента
│   ├── hypothesis.md       # Гипотеза
│   ├── methodology.md      # Методология
│   ├── results.md          # Результаты
│   └── code/              # Код эксперимента
├── experiment_002_strategy_comparison/
└── ...
```

### 📊 `studies/`
Комплексные исследования и case studies:
- Анализ рыночных условий
- Долгосрочные исследования
- Межрыночный анализ
- Исторические исследования

**Структура исследований:**
```
studies/
├── market_analysis_2024/
│   ├── overview.md         # Обзор исследования
│   ├── data/              # Данные
│   ├── analysis/          # Анализ
│   └── conclusions.md     # Выводы
├── cross_market_study/
└── ...
```

## 🚀 Использование

### Запуск Jupyter Lab
```bash
# Активируйте виртуальное окружение
venv_bquant_dell\Scripts\activate

# Установите зависимости для ноутбуков (если не установлены)
pip install -e .[notebooks]

# Запустите Jupyter Lab
jupyter lab research/notebooks/
```

### Импорт BQuant в ноутбуках
```python
# Добавление пути к проекту
import sys
sys.path.append('..')

# Импорт основных модулей BQuant
from bquant.data import load_symbol_data, clean_ohlcv_data
from bquant.analysis.statistical import run_all_hypothesis_tests
from bquant.analysis.zones import analyze_zones, analyze_macd_zones
from bquant.visualization import FinancialCharts, set_default_theme

# Установка темы для визуализации
set_default_theme('bquant_light')
```

### Создание нового эксперимента
```bash
# Создайте папку для эксперимента
mkdir research/experiments/experiment_XXX_description

# Скопируйте шаблон
cp research/templates/experiment_template/* research/experiments/experiment_XXX_description/

# Отредактируйте файлы описания
```

## 📋 Guidelines

### Naming Convention
- **Ноутбуки**: `XX_descriptive_name.ipynb` (где XX - номер)
- **Эксперименты**: `experiment_XXX_short_description/`
- **Исследования**: `descriptive_name_YYYY/` (где YYYY - год)

### Documentation Standards
- Каждый ноутбук должен содержать markdown ячейки с описанием
- Все функции и классы должны быть документированы
- Результаты должны быть воспроизводимыми
- Используйте версионирование для данных

### Code Quality
- Следуйте стандартам кодирования BQuant
- Используйте type hints
- Добавляйте docstrings к функциям
- Оптимизируйте производительность для больших данных

### Data Management
- Используйте относительные пути
- Не коммитьте большие файлы данных
- Документируйте источники данных
- Используйте сэмплы для демонстрации

## 🔗 Связанные ресурсы

- [BQuant Documentation](../docs/)
- [API Reference](../docs/api/)
- [Examples](../examples/)
- [Tests](../tests/)

## 📝 TODO

- [ ] Создание базовых ноутбуков (Шаг 6.2 - отложен)
- [ ] Добавление шаблонов экспериментов
- [ ] Создание методологической документации
- [ ] Настройка CI/CD для тестирования ноутбуков

## 📞 Support

Для вопросов и предложений:
- Issues: [GitHub Issues](https://github.com/kogriv/bquant/issues)
- Email: kogriv@gmail.com

---

**Примечание**: Эта структура создана в рамках миграции проекта BQuant. Детальное наполнение контентом планируется после завершения основной миграции и публикации пакета.
