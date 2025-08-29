# Quick Start - Быстрый старт с BQuant

## 🚀 Установка

### Установка через pip

```bash
pip install bquant
```

### Установка из исходного кода

```bash
git clone https://github.com/your-username/bquant.git
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
from bquant.indicators import MACDZoneAnalyzer
from bquant.visualization import FinancialCharts
```

### 2. Загрузка данных

```python
# Используем встроенные sample данные
data = get_sample_data('tv_xauusd_1h')
print(f"Загружено {len(data)} записей")
print(f"Период: {data.index[0]} - {data.index[-1]}")
```

### 3. Создание анализатора

```python
# Создаем анализатор MACD с зонами
analyzer = MACDZoneAnalyzer()

# Выполняем полный анализ
result = analyzer.analyze_complete(data)
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

# Текущие значения MACD
current_macd = stats.get('current_macd', 0)
current_signal = stats.get('current_signal', 0)
print(f"Текущий MACD: {current_macd:.4f}")
print(f"Текущий Signal: {current_signal:.4f}")
```

### 5. Визуализация

```python
# Создаем график
charts = FinancialCharts()

# Candlestick график с MACD
fig = charts.create_candlestick_chart(
    data, 
    title="XAUUSD 1H - MACD Analysis"
)

# Добавляем MACD с зонами
fig = charts.plot_macd_with_zones(data, zones)

# Показываем график
fig.show()
```

## 📊 Полный пример

```python
import bquant as bq
from bquant.data.samples import get_sample_data, list_dataset_names
from bquant.indicators import MACDZoneAnalyzer
from bquant.visualization import FinancialCharts
from bquant.analysis.statistical import run_all_hypothesis_tests

def quick_analysis():
    """Быстрый анализ sample данных"""
    
    # 1. Выбираем dataset
    datasets = list_dataset_names()
    print(f"Доступные datasets: {datasets}")
    
    dataset_name = datasets[0]  # Первый доступный
    print(f"Анализируем: {dataset_name}")
    
    # 2. Загружаем данные
    data = get_sample_data(dataset_name)
    print(f"Данные: {len(data)} записей")
    
    # 3. MACD анализ
    analyzer = MACDZoneAnalyzer()
    result = analyzer.analyze_complete(data)
    
    # 4. Результаты
    zones = result.zones
    stats = result.statistics
    
    print(f"\n📊 РЕЗУЛЬТАТЫ АНАЛИЗА:")
    print(f"   • Всего зон: {len(zones)}")
    print(f"   • Bull зон: {stats.get('bull_zones', 0)}")
    print(f"   • Bear зон: {stats.get('bear_zones', 0)}")
    print(f"   • Текущий MACD: {stats.get('current_macd', 0):.4f}")
    print(f"   • Текущий Signal: {stats.get('current_signal', 0):.4f}")
    
    # 5. Статистические тесты
    try:
        zones_info = {
            'zones_features': [zone.features for zone in zones if zone.features],
            'zones': zones,
            'statistics': stats
        }
        hypothesis_results = run_all_hypothesis_tests(zones_info)
        print(f"   • Статистические тесты: ✅ выполнено")
    except Exception as e:
        print(f"   • Статистические тесты: ⚠️ {e}")
    
    # 6. Визуализация
    try:
        charts = FinancialCharts()
        fig = charts.create_candlestick_chart(
            data, 
            title=f"Analysis of {dataset_name}"
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

## 🎯 Что дальше?

После освоения быстрого старта:

1. **[Core Concepts](../api/core/README.md)** - Изучите архитектуру BQuant
2. **[Data Management](../api/data/README.md)** - Работа с собственными данными
3. **[Technical Analysis](../api/indicators/README.md)** - Продвинутый технический анализ
4. **[Examples](../examples/README.md)** - Изучите готовые примеры

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
