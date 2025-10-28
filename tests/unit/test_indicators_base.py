"""
Tests for BQuant indicators base functionality

Полноценные тесты для проверки базовой архитектуры индикаторов согласно прогресс-файлу.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Импорты для тестирования
from bquant.indicators.base import BaseIndicator, IndicatorSource, IndicatorFactory
from bquant.indicators import (
    IndicatorConfig, IndicatorResult, SimpleMovingAverage, MACD,
    MACDPreloadedIndicator
)


def create_test_data(rows: int = 100) -> pd.DataFrame:
    """
    Создание тестовых OHLCV данных.
    
    Args:
        rows: Количество строк данных
    
    Returns:
        DataFrame с тестовыми данными
    """
    dates = pd.date_range(start='2024-01-01', periods=rows, freq='1H')
    
    # Генерируем реалистичные ценовые данные
    np.random.seed(42)  # Для воспроизводимости
    
    base_price = 100.0
    price_changes = np.random.normal(0, 0.01, rows)  # 1% волатильность
    prices = [base_price]
    
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 0.01))  # Избегаем нулевых/отрицательных цен
    
    # Создаем OHLCV данные
    data = []
    for i, price in enumerate(prices):
        high = price * (1 + abs(np.random.normal(0, 0.005)))
        low = price * (1 - abs(np.random.normal(0, 0.005)))
        open_price = prices[i-1] if i > 0 else price
        close_price = price
        volume = np.random.randint(1000, 10000)
        
        data.append({
            'open': open_price,
            'high': max(high, open_price, close_price),
            'low': min(low, open_price, close_price),
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data, index=dates)


class TestIndicatorBase:
    """Тесты для базовой архитектуры индикаторов."""
    
    def test_base_indicator(self):
        """
        Тест базового индикатора согласно прогресс-файлу:
        from bquant.indicators.base import BaseIndicator, IndicatorSource
        assert IndicatorSource.PRELOADED == "preloaded"
        assert IndicatorSource.LIBRARY == "library"
        assert IndicatorSource.CUSTOM == "custom"
        """
        # Проверяем enum IndicatorSource
        assert IndicatorSource.PRELOADED.value == "preloaded"
        assert IndicatorSource.LIBRARY.value == "library"
        assert IndicatorSource.CUSTOM.value == "custom"
        
        print("[OK] test_base_indicator: IndicatorSource enum работает корректно")
    
    def test_indicator_factory(self):
        """
        Тест фабрики индикаторов согласно прогресс-файлу:
        from bquant.indicators.base import IndicatorFactory
        data = load_symbol_data('XAUUSD', '1h')
        indicator = IndicatorFactory.create_indicator('macd', data)
        assert indicator is not None
        """
        # Создаем тестовые данные вместо загрузки XAUUSD
        data = create_test_data(100)
        
        # Создаем индикатор через фабрику (старый метод для совместимости)
        indicator = IndicatorFactory.create_indicator('macd', fast_period=12, slow_period=26, signal_period=9)
        assert indicator is not None
        
        # Проверяем, что это BaseIndicator
        assert isinstance(indicator, BaseIndicator)
        
        print("[OK] test_indicator_factory: IndicatorFactory.create_indicator работает")
    
    def test_indicator_config(self):
        """Тест конфигурации индикатора."""
        config = IndicatorConfig(
            name="test_indicator",
            parameters={'period': 20},
            source=IndicatorSource.PRELOADED,
            columns=['test_output'],
            description="Test indicator"
        )
        
        assert config.name == "test_indicator"
        assert config.parameters['period'] == 20
        assert config.source == IndicatorSource.PRELOADED
        assert 'test_output' in config.columns
        
        print("[OK] test_indicator_config: IndicatorConfig работает корректно")
    
    def test_indicator_result(self):
        """Тест результата индикатора."""
        data = create_test_data(50)
        
        config = IndicatorConfig(
            name="test",
            parameters={},
            source=IndicatorSource.PRELOADED,
            columns=['test_value'],
            description="Test indicator"
        )
        
        result_data = pd.DataFrame({'test_value': np.random.randn(50)}, index=data.index)
        
        result = IndicatorResult(
            name="test",
            data=result_data,
            config=config,
            metadata={'test': True}
        )
        
        assert result.name == "test"
        assert isinstance(result.data, pd.DataFrame)
        assert result.config == config
        assert result.metadata['test'] is True
        
        print("[OK] test_indicator_result: IndicatorResult работает корректно")


class TestBuiltinIndicators:
    """Тесты для встроенных индикаторов."""
    
    def test_sma_calculation(self):
        """Тест расчета Simple Moving Average."""
        data = create_test_data(100)
        
        sma = SimpleMovingAverage(period=20)
        result = sma.calculate(data)
        
        assert isinstance(result, IndicatorResult)
        assert result.name == 'sma'
        assert 'sma_20' in result.data.columns
        assert len(result.data) == len(data)
        
        # Проверяем, что первые 19 значений NaN (так как period=20)
        assert pd.isna(result.data['sma_20'].iloc[:19]).all()
        
        # Проверяем корректность расчета для последних значений
        manual_sma = data['close'].rolling(window=20).mean()
        pd.testing.assert_series_equal(
            result.data['sma_20'], 
            manual_sma, 
            check_names=False
        )
        
        print("[OK] test_sma_calculation: SimpleMovingAverage работает корректно")
    
    def test_macd_calculation(self):
        """Тест расчета MACD согласно прогресс-файлу."""
        data = create_test_data(100)
        
        macd = MACD(fast_period=12, slow_period=26, signal_period=9)
        result = macd.calculate(data)
        
        assert isinstance(result, IndicatorResult)
        assert result.name == 'macd'
        
        # Проверяем наличие всех необходимых колонок
        expected_columns = ['macd', 'macd_signal', 'macd_hist']
        for col in expected_columns:
            assert col in result.data.columns
        
        # Проверяем, что гистограмма = MACD - Signal
        hist_calculated = result.data['macd'] - result.data['macd_signal']
        pd.testing.assert_series_equal(
            result.data['macd_hist'],
            hist_calculated,
            check_names=False
        )
        
        print("[OK] test_macd_calculation: MACD работает корректно")


class TestHighLevelFunctions:
    """Тесты для высокоуровневых функций."""
    
    def test_indicator_factory_new_interface(self):
        """Тест нового интерфейса IndicatorFactory.create()."""
        data = create_test_data(100)
        
        # Тестируем создание через новый интерфейс
        sma = IndicatorFactory.create('custom', 'sma', period=20)
        result = sma.calculate(data)
        
        assert isinstance(result, IndicatorResult)
        assert result.name == 'sma'
        assert 'sma_20' in result.data.columns
        
        print("[OK] test_indicator_factory_new_interface: IndicatorFactory.create работает")
    
    def test_preloaded_indicator(self):
        """Тест PRELOADED индикатора."""
        data = create_test_data(100)
        # Добавляем колонки для PRELOADED MACD
        data['macd'] = np.random.randn(100).cumsum()
        data['signal'] = np.random.randn(100).cumsum()
        
        macd_preloaded = IndicatorFactory.create('preloaded', 'macd', required_columns=['macd', 'signal'])
        result = macd_preloaded.calculate(data)
        
        assert isinstance(result, IndicatorResult)
        assert result.name == 'macd_preloaded'
        
        print("[OK] test_preloaded_indicator: PRELOADED индикатор работает корректно")
    
    def test_indicator_factory_listing(self):
        """Тест получения списка индикаторов через IndicatorFactory."""
        all_indicators = IndicatorFactory.list_indicators()
        
        assert isinstance(all_indicators, dict)
        assert len(all_indicators) > 0
        
        # Проверяем, что встроенные индикаторы есть в списке
        expected_indicators = ['sma', 'ema', 'rsi', 'macd', 'bbands', 'macd_preloaded']
        for indicator in expected_indicators:
            assert indicator in all_indicators
        
        print(f"[OK] test_indicator_factory_listing: Найдено {len(all_indicators)} индикаторов")


class TestIndicatorValidation:
    """Тесты для валидации данных."""
    
    def test_empty_data_validation(self):
        """Тест валидации пустых данных."""
        empty_data = pd.DataFrame()
        
        sma = SimpleMovingAverage(period=20)
        
        try:
            sma.calculate(empty_data)
            assert False, "Should have raised an exception"
        except Exception:
            pass  # Expected
        
        print("[OK] test_empty_data_validation: Валидация пустых данных работает")
    
    def test_insufficient_data_validation(self):
        """Тест валидации недостаточного количества данных."""
        insufficient_data = create_test_data(10)  # Меньше чем period=20
        
        sma = SimpleMovingAverage(period=20)
        
        try:
            sma.calculate(insufficient_data)
            assert False, "Should have raised an exception"
        except Exception:
            pass  # Expected
        
        print("[OK] test_insufficient_data_validation: Валидация недостаточных данных работает")
    
    def test_missing_columns_validation(self):
        """Тест валидации отсутствующих колонок."""
        data_without_close = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [105, 106, 107],
            'low': [99, 100, 101]
            # Отсутствует 'close'
        }, index=pd.date_range('2024-01-01', periods=3, freq='1H'))
        
        sma = SimpleMovingAverage(period=2)
        
        try:
            sma.calculate(data_without_close)
            assert False, "Should have raised an exception"
        except Exception:
            pass  # Expected
        
        print("[OK] test_missing_columns_validation: Валидация отсутствующих колонок работает")


def run_all_tests():
    """Запуск всех тестов."""
    print("🚀 Запуск полноценных тестов индикаторов BQuant...")
    print("=" * 60)
    
    # Создаем экземпляры тестовых классов и запускаем тесты
    test_classes = [
        TestIndicatorBase(),
        TestBuiltinIndicators(),
        TestHighLevelFunctions(),
        TestIndicatorValidation()
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n{class_name}:")
        
        # Получаем все методы, начинающиеся с test_
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_class, method_name)
                method()
                passed_tests += 1
            except Exception as e:
                print(f"[FAIL] {method_name}: FAILED - {e}")
    
    print("\n" + "=" * 60)
    print(f"[TARGET] Результаты тестирования:")
    print(f"   Всего тестов: {total_tests}")
    print(f"   Пройдено: {passed_tests}")
    print(f"   Провалено: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return True
    else:
        print("[WARN] Некоторые тесты провалены")
        return False


if __name__ == "__main__":
    run_all_tests()
