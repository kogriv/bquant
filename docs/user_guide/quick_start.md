# Quick Start - Быстрый старт с BQuant

## 🚀 Установка

### Установка через pip

```bash
pip install bquant
```

### Установка из исходного кода

```bash
git clone https://github.com/kogriv/bquant.git
cd bquant
pip install -e .
```

### Проверка установки

```python
import bquant
print(f"BQuant version: {bquant.__version__}")
```

## ⚡ Первый анализ за 5 минут

### 1. Импорт библиотек

```python
import bquant as bq
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones
from bquant.visualization import FinancialCharts
```

### 2. Загрузка данных

```python
# Используем встроенные sample данные
data = get_sample_data('tv_xauusd_1h')
print(f"Загружено {len(data)} записей")
print(f"Период: {data.index[0]} - {data.index[-1]}")
```

### 3. Universal Zone Analysis

```python
# Universal Pipeline - работает с любым индикатором
result = (
    analyze_zones(data)
    .with_indicator('pandas_ta', 'rsi', length=14)
    .detect_zones('threshold', indicator_col='RSI_14',
                  upper_threshold=70, lower_threshold=30)
    .analyze(clustering=True)
    .build()
)
```

### 4. Анализ результатов

```python
# Получаем зоны
zones = result.zones
print(f"Найдено зон: {len(zones)}")

# Статистика
stats = result.statistics
print(f"Bull зон: {stats.get('bull_zones', 0)}")
print(f"Bear зон: {stats.get('bear_zones', 0)}")

# Доступ к features зон
for i, zone in enumerate(zones[:3]):  # Первые 3 зоны
    if zone.features:
        print(f"Зона {i}: {zone.features.get('zone_type', 'unknown')}")
```

### 5. Визуализация

```python
# Создаем график
from bquant.visualization.zones import ZoneVisualizer
import plotly.io as pio

pio.renderers.default = "json"  # Безопасный renderer для headless-среды
charts = FinancialCharts()
zone_viz = ZoneVisualizer()

# Candlestick график с RSI
fig_price = charts.create_candlestick_chart(
    data,
    title="XAUUSD 1H - RSI Zone Analysis"
)
fig_price.show()

# Зоны RSI на ценовом графике
fig_zones = zone_viz.plot_zones_on_price_chart(
    data,
    zones,
    title="XAUUSD 1H - RSI Zones"
)

# Показываем график
fig_zones.show()
```

### 6. Подключение внешних индикаторов одной командой

```python
from bquant.indicators import LibraryManager

# Загружаем внешние библиотеки (pandas-ta и TA-Lib при наличии)
LibraryManager.load_all_libraries()

# «Простой способ»: создаём индикатор pandas-ta без ручной регистрации
rsi = LibraryManager.create_indicator('pandas_ta', 'rsi', length=14)
rsi_result = rsi.calculate(data)

print(rsi_result.data[['RSI_14']].tail())
```

> ℹ️ Подробности и дополнительные примеры смотрите в разделе
> [LibraryManager — управление внешними индикаторами](../api/indicators/library_manager.md).

## 📊 Полный пример - Universal Pipeline

```python
import bquant as bq
from bquant.data.samples import get_sample_data, list_dataset_names
from bquant.analysis.zones import analyze_zones
from bquant.visualization import FinancialCharts
import plotly.io as pio

pio.renderers.default = "json"

def quick_analysis():
    """Быстрый анализ sample данных с Universal Pipeline"""
    
    # 1. Выбираем dataset
    datasets = list_dataset_names()
    print(f"Доступные datasets: {datasets}")
    
    dataset_name = datasets[0]  # Первый доступный
    print(f"Анализируем: {dataset_name}")
    
    # 2. Загружаем данные
    data = get_sample_data(dataset_name)
    print(f"Данные: {len(data)} записей")
    
    # 3. Universal Pipeline - RSI анализ
    result = (
        analyze_zones(data)
        .with_indicator('pandas_ta', 'rsi', length=14)
        .detect_zones('threshold', indicator_col='RSI_14',
                      upper_threshold=70, lower_threshold=30)
        .analyze(clustering=True)
        .build()
    )
    
    # 4. Результаты
    zones = result.zones
    stats = result.statistics
    
    print(f"\n📊 РЕЗУЛЬТАТЫ АНАЛИЗА:")
    print(f"   • Всего зон: {len(zones)}")
    print(f"   • Bull зон: {stats.get('bull_zones', 0)}")
    print(f"   • Bear зон: {stats.get('bear_zones', 0)}")
    
    # 5. Hypothesis tests (автоматически в pipeline)
    if result.hypothesis_tests:
        print(f"   • Статистические тесты: ✅ выполнено")
        for test_name, test_result in result.hypothesis_tests.results.items():
            print(f"     - {test_name}: p={test_result['p_value']:.4f}")
    else:
        print(f"   • Статистические тесты: ⚠️ не выполнено")
    
    # 6. Визуализация
    try:
        charts = FinancialCharts()
        fig = charts.create_candlestick_chart(
            data, 
            title=f"RSI Zone Analysis - {dataset_name}"
        )
        print(f"   • Визуализация: ✅ создана")
        return fig
    except Exception as e:
        print(f"   • Визуализация: ⚠️ {e}")
        return None

# Запускаем анализ
if __name__ == "__main__":
    fig = quick_analysis()
    if fig:
        fig.show()
```

## 🔄 Migration Guide - Legacy API

```python
# ⚠️ DEPRECATED: Старый способ
from bquant.indicators import MACDZoneAnalyzer

analyzer = MACDZoneAnalyzer()  # Deprecated wrapper
result = analyzer.analyze_complete(data)  # Delegates to analyze_zones()

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

## 🎯 Что дальше?

После освоения быстрого старта:

### 📚 Learning Path
1. **[Universal Pipeline API](../api/analysis/pipeline.md)** - Полная документация Universal Pipeline v2.1
2. **[Detection Strategies](../api/analysis/strategies.md)** - 5 типов стратегий детекции зон
3. **[Statistical Analysis](../api/analysis/statistical.md)** - Автоматические hypothesis tests
4. **[Examples](../examples/README.md)** - Готовые примеры для всех индикаторов

### 🔬 Advanced Features
5. **[Deep Dive Tutorial](../../research/notebooks/03_zones_universal.py)** - Comprehensive analysis (412 строк)
6. **[Advanced Features](../../research/notebooks/03_analysis_new_features.py)** - Swing, divergence, regression
7. **[Migration Guide](../../examples/02_macd_zone_analysis.py)** - Переход с deprecated API

### 🏗️ Developer Resources
8. **[Architecture Patterns](../developer_guide/README.md)** - Design Patterns, Extension Points
9. **[Testing Framework](../../tests/integration/)** - Integration tests, Backward compatibility
10. **[Visualization](../api/visualization/README.md)** - Zone visualization, Statistical plots

## 💡 Советы

- **Используйте sample данные** для экспериментов
- **Начните с простого** - один индикатор, один dataset
- **Изучайте результаты** - анализируйте статистику и зоны
- **Экспериментируйте** - пробуйте разные параметры

## 🆘 Если что-то не работает

1. **Проверьте установку:**
   ```python
   import bquant
   print(bquant.__version__)
   ```

2. **Проверьте sample данные:**
   ```python
   from bquant.data.samples import list_dataset_names
   print(list_dataset_names())
   ```

3. **Создайте issue** на GitHub с описанием проблемы

---

**Следующий шаг:** [Core Concepts](core_concepts.md) 🏗️
