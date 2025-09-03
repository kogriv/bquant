"""
Тесты для проверки миграции импортов.

Проверяет корректность импортов после рефакторинга.
"""

import pytest
import pandas as pd
import numpy as np


class TestImportsMigration:
    """Тесты для проверки миграции импортов."""
    
    def test_main_module_imports(self):
        """Тест импортов из главного модуля indicators."""
        try:
            from bquant.indicators import (
                BaseIndicator, PreloadedIndicator, CustomIndicator, LibraryIndicator,
                IndicatorFactory, IndicatorSource, IndicatorConfig
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать из главного модуля: {e}")
    
    def test_base_module_imports(self):
        """Тест импортов из base модуля."""
        try:
            from bquant.indicators.base import (
                BaseIndicator, PreloadedIndicator, CustomIndicator, LibraryIndicator,
                IndicatorFactory, IndicatorSource, IndicatorConfig
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать из base модуля: {e}")
    
    def test_custom_module_imports(self):
        """Тест импортов из custom модуля."""
        try:
            from bquant.indicators.custom import (
                SimpleMovingAverage, ExponentialMovingAverage,
                RelativeStrengthIndex, MACD, BollingerBands
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать из custom модуля: {e}")
    
    def test_preloaded_module_imports(self):
        """Тест импортов из preloaded модуля."""
        try:
            from bquant.indicators.preloaded import MACDPreloadedIndicator
            assert True
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать из preloaded модуля: {e}")
    
    def test_library_module_imports(self):
        """Тест импортов из library модуля."""
        try:
            from bquant.indicators.library import LibraryManager
            assert True
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать из library модуля: {e}")
    
    def test_calculators_module_imports(self):
        """Тест импортов из calculators модуля."""
        try:
            from bquant.indicators.calculators import (
                IndicatorCalculator, calculate_moving_averages,
                create_indicator_suite
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать из calculators модуля: {e}")
    
    def test_legacy_imports_compatibility(self):
        """Тест совместимости со старыми импортами."""
        try:
            # Старые импорты должны работать
            from bquant.indicators import IndicatorFactory
            from bquant.indicators import BaseIndicator
            
            # Проверяем, что классы доступны
            assert IndicatorFactory is not None
            assert BaseIndicator is not None
            
        except ImportError as e:
            pytest.fail(f"Старые импорты не работают: {e}")
    
    def test_new_imports_availability(self):
        """Тест доступности новых импортов."""
        try:
            # Новые импорты должны быть доступны
            from bquant.indicators import IndicatorSource
            from bquant.indicators import IndicatorConfig
            
            # Проверяем, что классы доступны
            assert IndicatorSource is not None
            assert IndicatorConfig is not None
            
        except ImportError as e:
            pytest.fail(f"Новые импорты не работают: {e}")
    
    def test_indicator_factory_imports(self):
        """Тест импортов IndicatorFactory."""
        try:
            from bquant.indicators import IndicatorFactory
            
            # Проверяем, что фабрика доступна
            assert IndicatorFactory is not None
            
            # Проверяем, что методы доступны
            assert hasattr(IndicatorFactory, 'create')
            assert hasattr(IndicatorFactory, 'create_indicator')
            assert hasattr(IndicatorFactory, 'list_indicators')
            
        except ImportError as e:
            pytest.fail(f"IndicatorFactory не работает: {e}")
    
    def test_custom_indicators_imports(self):
        """Тест импортов кастомных индикаторов."""
        try:
            from bquant.indicators.custom import SimpleMovingAverage
            from bquant.indicators.custom import ExponentialMovingAverage
            from bquant.indicators.custom import RelativeStrengthIndex
            from bquant.indicators.custom import MACD
            from bquant.indicators.custom import BollingerBands
            
            # Проверяем, что все индикаторы доступны
            assert SimpleMovingAverage is not None
            assert ExponentialMovingAverage is not None
            assert RelativeStrengthIndex is not None
            assert MACD is not None
            assert BollingerBands is not None
            
        except ImportError as e:
            pytest.fail(f"Кастомные индикаторы не работают: {e}")
    
    def test_preloaded_indicators_imports(self):
        """Тест импортов preloaded индикаторов."""
        try:
            from bquant.indicators.preloaded import MACDPreloadedIndicator
            
            # Проверяем, что индикатор доступен
            assert MACDPreloadedIndicator is not None
            
        except ImportError as e:
            pytest.fail(f"Preloaded индикаторы не работают: {e}")
    
    def test_library_indicators_imports(self):
        """Тест импортов library индикаторов."""
        try:
            from bquant.indicators.base import LibraryIndicator
            from bquant.indicators.library import LibraryManager
            
            # Проверяем, что классы доступны
            assert LibraryIndicator is not None
            assert LibraryManager is not None
            
        except ImportError as e:
            pytest.fail(f"Library индикаторы не работают: {e}")
    
    def test_calculators_imports(self):
        """Тест импортов calculators."""
        try:
            from bquant.indicators.calculators import IndicatorCalculator
            
            # Проверяем, что класс доступен
            assert IndicatorCalculator is not None
            
        except ImportError as e:
            pytest.fail(f"Calculators не работают: {e}")
    
    def test_utility_functions_imports(self):
        """Тест импортов утилитарных функций."""
        try:
            from bquant.indicators.calculators import calculate_moving_averages
            from bquant.indicators.calculators import create_indicator_suite
            
            # Проверяем, что функции доступны
            assert calculate_moving_averages is not None
            assert create_indicator_suite is not None
            
        except ImportError as e:
            pytest.fail(f"Утилитарные функции не работают: {e}")
