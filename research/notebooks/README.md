# BQuant Research Notebooks

Jupyter ноутбуки для исследований и анализа с использованием BQuant.

## 📓 Планируемые ноутбуки

### Основные ноутбуки
- **01_data_exploration.ipynb** - Исследование финансовых данных
- **02_macd_zones_analysis.ipynb** - Анализ MACD зон и их характеристик
- **03_hypothesis_testing.ipynb** - Статистическое тестирование гипотез
- **04_visualization_examples.ipynb** - Примеры визуализации данных
- **05_performance_optimization.ipynb** - Оптимизация производительности

### Продвинутые ноутбуки
- **06_custom_indicators.ipynb** - Создание пользовательских индикаторов
- **07_backtesting_strategies.ipynb** - Бэктестинг торговых стратегий
- **08_multi_timeframe_analysis.ipynb** - Анализ множественных таймфреймов
- **09_risk_management.ipynb** - Управление рисками
- **10_portfolio_optimization.ipynb** - Оптимизация портфеля

## 🚀 Быстрый старт

```python
# Импорт основных модулей
import sys
sys.path.append('..')

from bquant.data import load_symbol_data
from bquant.indicators import MACDAnalyzer
from bquant.visualization import FinancialCharts

# Загрузка данных
data = load_symbol_data('XAUUSD', '1h', periods=1000)

# Анализ MACD
analyzer = MACDAnalyzer(data)
zones = analyzer.identify_zones()

# Визуализация
charts = FinancialCharts()
fig = charts.plot_macd_with_zones(analyzer.calculate_macd(), zones)
fig.show()
```

## 📋 Статус

**Текущий статус**: Структура создана, ноутбуки будут добавлены после завершения основной миграции (Шаг 6.2 отложен).

## 🔗 Ресурсы

- [BQuant API](../../docs/api/)
- [Примеры использования](../../examples/)
- [Документация](../../docs/)

---

*Создано в рамках миграции BQuant проекта*
