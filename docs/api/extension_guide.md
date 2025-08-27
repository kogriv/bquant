# Руководство по расширению API BQuant

## 📚 Обзор

Это руководство поможет вам расширить функциональность BQuant, создавая собственные индикаторы, анализаторы, визуализации и модули данных.

## 🎯 Принципы расширения

### Модульность
- Каждый новый компонент должен быть независимым
- Используйте интерфейсы и абстрактные классы
- Минимизируйте зависимости между модулями

### Совместимость
- Следуйте существующим паттернам API
- Используйте стандартные типы данных
- Поддерживайте обратную совместимость

### Производительность
- Используйте NumPy для вычислений
- Оптимизируйте для больших данных
- Применяйте кэширование где возможно

## 🏗️ Создание собственного индикатора

### Шаг 1: Наследование от BaseIndicator

```python
from bquant.indicators.base import BaseIndicator, IndicatorResult
import pandas as pd
import numpy as np

class CustomIndicator(BaseIndicator):
    """Кастомный индикатор"""
    
    def __init__(self, param1=10, param2=20):
        super().__init__('CustomIndicator', {
            'param1': param1,
            'param2': param2
        })
    
    def calculate(self, data):
        """Расчет индикатора"""
        if not self.validate_data(data):
            raise ValueError("Invalid data for CustomIndicator")
        
        # Ваша логика расчета
        result = self._calculate_indicator(data)
        
        return IndicatorResult(
            indicator_name='CustomIndicator',
            values=result,
            params=self.params,
            metadata={'calculated_at': pd.Timestamp.now()}
        )
    
    def validate_data(self, data):
        """Валидация данных"""
        required_columns = ['close', 'volume']
        return all(col in data.columns for col in required_columns)
    
    def _calculate_indicator(self, data):
        """Внутренний метод расчета"""
        param1 = self.params['param1']
        param2 = self.params['param2']
        
        # Пример расчета
        indicator = (data['close'] * data['volume']).rolling(window=param1).mean()
        return indicator
```

### Шаг 2: Регистрация в фабрике

```python
from bquant.indicators.factory import IndicatorFactory

# Регистрация индикатора
factory = IndicatorFactory()
factory.register_indicator(CustomIndicator)

# Использование
indicator = factory.create('CustomIndicator', param1=15, param2=25)
result = indicator.calculate(data)
```

## 🔬 Создание собственного анализатора

### Шаг 1: Наследование от BaseAnalyzer

```python
from bquant.analysis.base import BaseAnalyzer, AnalysisResult
import numpy as np

class CustomAnalyzer(BaseAnalyzer):
    """Кастомный анализатор"""
    
    def __init__(self, analysis_type='default'):
        super().__init__('CustomAnalyzer', {'analysis_type': analysis_type})
    
    def analyze(self, data):
        """Выполнение анализа"""
        if not self.validate_data(data):
            raise ValueError("Invalid data for CustomAnalyzer")
        
        # Ваша логика анализа
        analysis_result = self._perform_analysis(data)
        
        return AnalysisResult(
            analyzer_name='CustomAnalyzer',
            data=analysis_result['data'],
            statistics=analysis_result['statistics'],
            params=self.params
        )
    
    def validate_data(self, data):
        """Валидация данных"""
        return len(data) > 0 and 'close' in data.columns
    
    def _perform_analysis(self, data):
        """Внутренний метод анализа"""
        analysis_type = self.params['analysis_type']
        
        if analysis_type == 'volatility':
            result = self._analyze_volatility(data)
        elif analysis_type == 'trend':
            result = self._analyze_trend(data)
        else:
            result = self._analyze_default(data)
        
        return result
    
    def _analyze_volatility(self, data):
        """Анализ волатильности"""
        returns = data['close'].pct_change()
        volatility = returns.rolling(window=20).std()
        
        return {
            'data': volatility,
            'statistics': {
                'mean_volatility': volatility.mean(),
                'max_volatility': volatility.max(),
                'current_volatility': volatility.iloc[-1]
            }
        }
```

### Шаг 2: Интеграция с системой

```python
# Использование анализатора
analyzer = CustomAnalyzer(analysis_type='volatility')
result = analyzer.analyze(data)

print(f"Mean volatility: {result.statistics['mean_volatility']:.4f}")
```

## 📊 Создание собственной визуализации

### Шаг 1: Наследование от BaseChart

```python
from bquant.visualization.base import BaseChart
import plotly.graph_objects as go
import plotly.express as px

class CustomChart(BaseChart):
    """Кастомный график"""
    
    def __init__(self, theme='default'):
        super().__init__(theme)
    
    def create_chart(self, data, title="Custom Chart", **kwargs):
        """Создание графика"""
        # Ваша логика создания графика
        fig = self._build_chart(data, title, **kwargs)
        
        # Применение темы
        self._apply_theme(fig)
        
        return fig
    
    def _build_chart(self, data, title, **kwargs):
        """Построение графика"""
        fig = go.Figure()
        
        # Добавление данных
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['close'],
            mode='lines',
            name='Close Price',
            line=dict(color=self.theme.colors['primary'])
        ))
        
        # Настройка макета
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Price",
            height=600
        )
        
        return fig
    
    def _apply_theme(self, fig):
        """Применение темы"""
        fig.update_layout(
            template=self.theme.template,
            font=dict(
                family=self.theme.font_family,
                size=self.theme.font_size
            )
        )
```

### Шаг 2: Использование

```python
# Создание и использование графика
chart = CustomChart(theme='dark')
fig = chart.create_chart(data, title="My Custom Chart")
fig.show()
```

## 📥 Создание собственного загрузчика данных

### Шаг 1: Наследование от DataLoader

```python
from bquant.data.loader import DataLoader
import pandas as pd

class CustomDataLoader(DataLoader):
    """Кастомный загрузчик данных"""
    
    def __init__(self, source_type='custom'):
        super().__init__()
        self.source_type = source_type
    
    def load(self, source, **kwargs):
        """Загрузка данных"""
        if self.source_type == 'custom':
            return self._load_custom_data(source, **kwargs)
        else:
            return super().load(source, **kwargs)
    
    def _load_custom_data(self, source, **kwargs):
        """Загрузка кастомных данных"""
        # Ваша логика загрузки
        data = pd.read_csv(source, **kwargs)
        
        # Стандартизация колонок
        data = self._standardize_columns(data)
        
        return data
    
    def _standardize_columns(self, data):
        """Стандартизация колонок"""
        # Маппинг колонок к стандартным именам
        column_mapping = {
            'Date': 'time',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }
        
        data = data.rename(columns=column_mapping)
        
        # Установка индекса времени
        if 'time' in data.columns:
            data['time'] = pd.to_datetime(data['time'])
            data.set_index('time', inplace=True)
        
        return data
```

## 🔧 Создание собственного процессора данных

### Шаг 1: Наследование от DataProcessor

```python
from bquant.data.processor import DataProcessor
import pandas as pd
import numpy as np

class CustomDataProcessor(DataProcessor):
    """Кастомный процессор данных"""
    
    def __init__(self, processing_config=None):
        super().__init__()
        self.config = processing_config or {}
    
    def process(self, data):
        """Обработка данных"""
        processed_data = data.copy()
        
        # Применение кастомных обработок
        if self.config.get('remove_outliers', False):
            processed_data = self._remove_outliers(processed_data)
        
        if self.config.get('add_features', False):
            processed_data = self._add_features(processed_data)
        
        if self.config.get('normalize', False):
            processed_data = self._normalize_data(processed_data)
        
        return processed_data
    
    def _remove_outliers(self, data):
        """Удаление выбросов"""
        for col in ['open', 'high', 'low', 'close']:
            if col in data.columns:
                Q1 = data[col].quantile(0.25)
                Q3 = data[col].quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                data = data[(data[col] >= lower_bound) & (data[col] <= upper_bound)]
        
        return data
    
    def _add_features(self, data):
        """Добавление признаков"""
        # Технические индикаторы
        data['sma_20'] = data['close'].rolling(window=20).mean()
        data['sma_50'] = data['close'].rolling(window=50).mean()
        data['rsi'] = self._calculate_rsi(data['close'])
        
        return data
    
    def _calculate_rsi(self, prices, period=14):
        """Расчет RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _normalize_data(self, data):
        """Нормализация данных"""
        for col in ['open', 'high', 'low', 'close']:
            if col in data.columns:
                data[col] = (data[col] - data[col].mean()) / data[col].std()
        
        return data
```

## 🧪 Тестирование расширений

### Создание тестов

```python
import pytest
import pandas as pd
import numpy as np
from bquant.indicators import CustomIndicator
from bquant.analysis import CustomAnalyzer

class TestCustomIndicator:
    """Тесты для кастомного индикатора"""
    
    @pytest.fixture
    def sample_data(self):
        """Тестовые данные"""
        dates = pd.date_range('2024-01-01', periods=100, freq='H')
        data = pd.DataFrame({
            'close': np.random.randn(100).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
        return data
    
    def test_indicator_calculation(self, sample_data):
        """Тест расчета индикатора"""
        indicator = CustomIndicator(param1=10, param2=20)
        result = indicator.calculate(sample_data)
        
        assert result.indicator_name == 'CustomIndicator'
        assert len(result.values) == len(sample_data)
        assert not result.values.isna().all()
    
    def test_indicator_validation(self, sample_data):
        """Тест валидации данных"""
        indicator = CustomIndicator()
        
        # Тест с валидными данными
        assert indicator.validate_data(sample_data) == True
        
        # Тест с невалидными данными
        invalid_data = sample_data.drop(columns=['close'])
        assert indicator.validate_data(invalid_data) == False

class TestCustomAnalyzer:
    """Тесты для кастомного анализатора"""
    
    @pytest.fixture
    def sample_data(self):
        """Тестовые данные"""
        dates = pd.date_range('2024-01-01', periods=100, freq='H')
        data = pd.DataFrame({
            'close': np.random.randn(100).cumsum() + 100
        }, index=dates)
        return data
    
    def test_analyzer_volatility(self, sample_data):
        """Тест анализа волатильности"""
        analyzer = CustomAnalyzer(analysis_type='volatility')
        result = analyzer.analyze(sample_data)
        
        assert result.analyzer_name == 'CustomAnalyzer'
        assert 'mean_volatility' in result.statistics
        assert result.statistics['mean_volatility'] > 0
```

### Запуск тестов

```bash
# Запуск всех тестов
pytest tests/test_custom_extensions.py -v

# Запуск с покрытием
pytest tests/test_custom_extensions.py --cov=bquant --cov-report=html
```

## 📦 Упаковка расширений

### Структура пакета

```
my_bquant_extension/
├── setup.py
├── README.md
├── requirements.txt
├── my_bquant_extension/
│   ├── __init__.py
│   ├── indicators/
│   │   ├── __init__.py
│   │   └── custom_indicator.py
│   ├── analyzers/
│   │   ├── __init__.py
│   │   └── custom_analyzer.py
│   └── visualizations/
│       ├── __init__.py
│       └── custom_chart.py
└── tests/
    ├── __init__.py
    ├── test_indicators.py
    ├── test_analyzers.py
    └── test_visualizations.py
```

### setup.py

```python
from setuptools import setup, find_packages

setup(
    name="my-bquant-extension",
    version="0.1.0",
    description="Custom extension for BQuant",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "bquant>=0.0.0",
        "pandas>=1.3.0",
        "numpy>=1.20.0",
        "plotly>=5.0.0"
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.0.0"
        ]
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ]
)
```

### Автоматическая регистрация

```python
# my_bquant_extension/__init__.py
from .indicators.custom_indicator import CustomIndicator
from .analyzers.custom_analyzer import CustomAnalyzer
from .visualizations.custom_chart import CustomChart

# Автоматическая регистрация при импорте
def register_extensions():
    """Регистрация расширений"""
    from bquant.indicators.factory import IndicatorFactory
    from bquant.analysis.registry import AnalysisRegistry
    
    # Регистрация индикаторов
    factory = IndicatorFactory()
    factory.register_indicator(CustomIndicator)
    
    # Регистрация анализаторов
    registry = AnalysisRegistry()
    registry.register_analyzer(CustomAnalyzer)

# Автоматическая регистрация при импорте модуля
register_extensions()
```

## 🔗 Интеграция с существующим API

### Использование в скриптах

```python
# Использование кастомных компонентов
from my_bquant_extension import CustomIndicator, CustomAnalyzer, CustomChart
from bquant.data.samples import get_sample_data

# Загрузка данных
data = get_sample_data('tv_xauusd_1h')

# Использование кастомного индикатора
indicator = CustomIndicator(param1=15, param2=25)
indicator_result = indicator.calculate(data)

# Использование кастомного анализатора
analyzer = CustomAnalyzer(analysis_type='volatility')
analysis_result = analyzer.analyze(data)

# Использование кастомного графика
chart = CustomChart(theme='dark')
fig = chart.create_chart(data, title="Custom Analysis")
fig.show()
```

### Интеграция с CLI

```python
# scripts/analysis/custom_analysis.py
import argparse
from my_bquant_extension import CustomIndicator, CustomAnalyzer
from bquant.data.samples import get_sample_data

def main():
    parser = argparse.ArgumentParser(description="Custom analysis script")
    parser.add_argument("--dataset", default="tv_xauusd_1h", help="Dataset name")
    parser.add_argument("--param1", type=int, default=15, help="Parameter 1")
    parser.add_argument("--param2", type=int, default=25, help="Parameter 2")
    
    args = parser.parse_args()
    
    # Загрузка данных
    data = get_sample_data(args.dataset)
    
    # Кастомный анализ
    indicator = CustomIndicator(param1=args.param1, param2=args.param2)
    indicator_result = indicator.calculate(data)
    
    analyzer = CustomAnalyzer(analysis_type='volatility')
    analysis_result = analyzer.analyze(data)
    
    # Вывод результатов
    print(f"Indicator result: {indicator_result.values.tail()}")
    print(f"Analysis result: {analysis_result.statistics}")

if __name__ == "__main__":
    main()
```

## 🚀 Лучшие практики

### Производительность

```python
# Используйте NumPy для быстрых вычислений
import numpy as np

def fast_calculation(data):
    """Быстрый расчет с NumPy"""
    prices = data['close'].values  # NumPy array
    returns = np.diff(prices) / prices[:-1]
    volatility = np.std(returns)
    return volatility

# Используйте векторизацию
def vectorized_operation(data):
    """Векторизованная операция"""
    return data['close'].rolling(window=20).mean()
```

### Обработка ошибок

```python
from bquant.core.exceptions import BQuantError, DataError

class CustomError(BQuantError):
    """Кастомное исключение"""
    pass

def safe_calculation(data):
    """Безопасный расчет с обработкой ошибок"""
    try:
        if data.empty:
            raise DataError("Empty dataset provided")
        
        if 'close' not in data.columns:
            raise DataError("Missing 'close' column")
        
        result = perform_calculation(data)
        return result
        
    except Exception as e:
        raise CustomError(f"Calculation failed: {str(e)}")
```

### Документация

```python
class CustomIndicator(BaseIndicator):
    """
    Кастомный индикатор для анализа финансовых данных.
    
    Этот индикатор рассчитывает специальный показатель на основе
    цены закрытия и объема торгов.
    
    Parameters
    ----------
    param1 : int, default=10
        Первый параметр индикатора
    param2 : int, default=20
        Второй параметр индикатора
    
    Examples
    --------
    >>> indicator = CustomIndicator(param1=15, param2=25)
    >>> result = indicator.calculate(data)
    >>> print(result.values.tail())
    
    Notes
    -----
    Индикатор использует скользящее среднее для сглаживания данных.
    """
    
    def calculate(self, data):
        """
        Расчет индикатора.
        
        Parameters
        ----------
        data : pd.DataFrame
            DataFrame с OHLCV данными
            
        Returns
        -------
        IndicatorResult
            Результат расчета индикатора
            
        Raises
        ------
        DataError
            Если данные некорректны
        """
        # Реализация
        pass
```

## 📚 Дополнительные ресурсы

- **[Core Modules](../core/)** - Базовые модули для расширения
- **[Indicators](../indicators/)** - Примеры индикаторов
- **[Analysis](../analysis/)** - Примеры анализаторов
- **[Visualization](../visualization/)** - Примеры визуализаций

---

**Следующий шаг:** Изучите существующие модули и создайте свое первое расширение! 🚀
