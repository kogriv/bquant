#!/usr/bin/env python3
"""
BQuant - Базовый пример использования индикаторов

Этот пример демонстрирует:
1. Загрузку и подготовку данных
2. Расчет технических индикаторов (SMA, RSI, MACD, Bollinger Bands)
3. Вывод результатов и базовую визуализацию

Требования:
- Установленный BQuant пакет: pip install -e .
- Данные в формате OHLCV
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Добавляем путь к BQuant для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bquant.indicators import IndicatorFactory, LibraryManager
# Функции-обёртки живут в подмодуле `calculators` и намеренно не поднимаются в
# `__all__` пакета: наверху — классы и фабрика. Пример импортировал их из
# `bquant.indicators` и не запускался вовсе.
from bquant.indicators.calculators import (
    calculate_indicator, calculate_macd, calculate_rsi,
    calculate_bollinger_bands, calculate_moving_averages,
    get_available_indicators,
)
from bquant.core.config import get_indicator_params


def create_sample_ohlcv_data(rows: int = 100, symbol: str = "XAUUSD") -> pd.DataFrame:
    """
    Создание примера OHLCV данных для демонстрации.
    
    Args:
        rows: Количество строк данных
        symbol: Символ инструмента
        
    Returns:
        DataFrame с OHLCV данными
    """
    print(f"📊 Создание примера данных для {symbol}...")
    
    # Генерируем временной ряд
    dates = pd.date_range(start='2024-01-01', periods=rows, freq='1h')
    np.random.seed(42)  # Для воспроизводимости
    
    # Создаем реалистичные ценовые данные
    base_price = 2000.0
    prices = [base_price]
    
    for i in range(1, rows):
        # Добавляем тренд и случайность
        trend = 0.0001 * np.sin(i / 20)  # Слабый синусоидальный тренд
        volatility = np.random.normal(0, 0.01)  # 1% волатильность
        
        change = trend + volatility
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 100.0))  # Минимальная цена
    
    # Создаем OHLCV структуру
    data = []
    for i, close_price in enumerate(prices):
        if i == 0:
            open_price = close_price
        else:
            open_price = prices[i-1]
        
        # Случайные high/low относительно open/close
        high = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.005)))
        low = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.005)))
        volume = np.random.randint(1000, 10000)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data, index=dates)
    print(f"✅ Создано {len(df)} строк данных за период {df.index[0]} - {df.index[-1]}")
    return df


def demonstrate_basic_indicators():
    """Демонстрация базовых технических индикаторов."""
    
    print("🚀 BQuant - Демонстрация базовых индикаторов")
    print("=" * 60)
    
    # 1. Создаем тестовые данные
    data = create_sample_ohlcv_data(200, "XAUUSD")
    print(f"\n📈 Исходные данные:")
    print(f"   Период: {data.index[0]} - {data.index[-1]}")
    print(f"   Количество баров: {len(data)}")
    print(f"   Начальная цена: ${data['close'].iloc[0]:.2f}")
    print(f"   Конечная цена: ${data['close'].iloc[-1]:.2f}")
    print(f"   Изменение: {((data['close'].iloc[-1] / data['close'].iloc[0]) - 1) * 100:.2f}%")
    
    # 2. Получаем список доступных индикаторов
    print(f"\n🔧 Доступные индикаторы:")
    available_indicators = get_available_indicators()
    for indicator in available_indicators:
        print(f"   ✓ {indicator}")
    
    # 3. Загружаем внешние библиотеки и создаём индикатор pandas-ta
    print(f"\n🔌 Индикаторы pandas-ta через LibraryManager:")
    load_results = LibraryManager.load_all_libraries()
    print(f"   Доступные библиотеки: {load_results}")

    try:
        ta_rsi = LibraryManager.create_indicator('pandas_ta', 'rsi', length=14)
        ta_rsi_result = ta_rsi.calculate(data)
        latest_ta_rsi = ta_rsi_result.data.iloc[-1]
        print(f"   ✅ pandas-ta RSI: {latest_ta_rsi.iloc[0]:.2f}")
    except Exception as e:
        print(f"   ⚠️ Не удалось создать индикатор pandas-ta: {e}")
        ta_rsi_result = None

    # 4. Рассчитываем скользящие средние
    print(f"\n📊 Расчет скользящих средних:")
    try:
        ma_data = calculate_moving_averages(data, periods=[10, 20, 50])
        print(f"   ✅ Рассчитаны SMA: {[col for col in ma_data.columns if col.startswith('sma')]}")
        
        # Выводим последние значения (цена — из исходного кадра: калькулятор отдаёт только средние)
        latest_values = ma_data[['sma_10', 'sma_20', 'sma_50']].join(data[['close']]).iloc[-1]
        print(f"   Последние значения:")
        for col, val in latest_values.items():
            print(f"     {col}: ${val:.2f}")
            
    except Exception as e:
        raise RuntimeError(f"Ошибка расчета SMA: {e}") from e
    
    # 5. Рассчитываем RSI
    print(f"\n📈 Расчет RSI:")
    try:
        rsi_params = get_indicator_params('rsi')
        print(f"   Параметры RSI: {rsi_params}")
        
        rsi_data = calculate_rsi(data, period=rsi_params.get('period', 14))   # Series
        current_rsi = rsi_data.iloc[-1]
        print(f"   ✅ Текущий RSI: {current_rsi:.2f}")
        
        # Интерпретация RSI
        if current_rsi > 70:
            interpretation = "Перекупленность"
        elif current_rsi < 30:
            interpretation = "Перепроданность"
        else:
            interpretation = "Нейтральная зона"
        print(f"   📊 Интерпретация: {interpretation}")
        
    except Exception as e:
        raise RuntimeError(f"Ошибка расчета RSI: {e}") from e
    
    # 6. Рассчитываем MACD
    print(f"\n📉 Расчет MACD:")
    try:
        macd_params = get_indicator_params('macd')
        print(f"   Параметры MACD: {macd_params}")
        
        macd_data = calculate_macd(
            data, 
            fast=macd_params['fast'], 
            slow=macd_params['slow'], 
            signal=macd_params['signal']
        )
        
        # Колонки адресуются по РОЛИ: имена несут параметры (macd_12_26_9__line),
        # и литерал 'macd_signal' молча расходился с ними (G8, G65)
        macd_cols = IndicatorFactory.create(
            'custom', 'macd', fast_period=macd_params['fast'],
            slow_period=macd_params['slow'], signal_period=macd_params['signal'],
        ).get_output_roles()
        latest_macd = macd_data.iloc[-1]
        print(f"   ✅ MACD: {latest_macd[macd_cols['line']]:.4f}")
        print(f"   ✅ Signal: {latest_macd[macd_cols['signal']]:.4f}")
        print(f"   ✅ Histogram: {latest_macd[macd_cols['hist']]:.4f}")
        
        # Сигналы MACD
        if latest_macd[macd_cols['line']] > latest_macd[macd_cols['signal']]:
            macd_signal = "Бычий сигнал" if latest_macd[macd_cols['hist']] > 0 else "Слабый бычий"
        else:
            macd_signal = "Медвежий сигнал" if latest_macd[macd_cols['hist']] < 0 else "Слабый медвежий"
        print(f"   📊 Сигнал: {macd_signal}")
        
    except Exception as e:
        raise RuntimeError(f"Ошибка расчета MACD: {e}") from e
    
    # 7. Рассчитываем Bollinger Bands
    print(f"\n📊 Расчет Bollinger Bands:")
    try:
        bb_data = calculate_bollinger_bands(data, period=20, std_dev=2)
        bb_cols = IndicatorFactory.create('custom', 'bbands', period=20, std_dev=2).get_output_roles()
        latest_bb = bb_data.iloc[-1]
        
        print(f"   ✅ Upper Band: ${latest_bb[bb_cols['upper']]:.2f}")
        print(f"   ✅ Middle Band (SMA): ${latest_bb[bb_cols['middle']]:.2f}")
        print(f"   ✅ Lower Band: ${latest_bb[bb_cols['lower']]:.2f}")
        print(f"   ✅ Bandwidth: {latest_bb[bb_cols['width']]:.4f}")
        print(f"   ✅ %B: {latest_bb[bb_cols['percent']]:.2f}")
        
        # Интерпретация позиции цены
        price = data['close'].iloc[-1]
        if price > latest_bb[bb_cols['upper']]:
            bb_interpretation = "Цена выше верхней полосы (возможна коррекция)"
        elif price < latest_bb[bb_cols['lower']]:
            bb_interpretation = "Цена ниже нижней полосы (возможен отскок)"
        else:
            bb_interpretation = "Цена в пределах полос (нормальное движение)"
        print(f"   📊 Интерпретация: {bb_interpretation}")
        
    except Exception as e:
        raise RuntimeError(f"Ошибка расчета Bollinger Bands: {e}") from e
    
    # 8. Комбинированный анализ
    print(f"\n🎯 Комбинированный технический анализ:")
    try:
        # Собираем все индикаторы
        combined_data = data.copy()
        
        # Добавляем индикаторы
        ma_result = calculate_moving_averages(data, periods=[20])
        combined_data['sma_20'] = ma_result['sma_20']
        
        combined_data['rsi'] = calculate_rsi(data)
        
        macd_result = calculate_macd(data)
        macd_cols = IndicatorFactory.create('custom', 'macd').get_output_roles()
        for role in ('line', 'signal', 'hist'):
            combined_data[f'macd_{role}'] = macd_result[macd_cols[role]]
        
        # Анализ последних значений
        latest = combined_data.iloc[-1]
        signals = []
        
        # Анализ тренда (цена vs SMA)
        if latest['close'] > latest['sma_20']:
            signals.append("Восходящий тренд (цена > SMA20)")
        else:
            signals.append("Нисходящий тренд (цена < SMA20)")
        
        # Анализ импульса (RSI)
        if latest['rsi'] > 70:
            signals.append("RSI: Перекупленность")
        elif latest['rsi'] < 30:
            signals.append("RSI: Перепроданность")
        else:
            signals.append("RSI: Нейтральная зона")
        
        # Анализ MACD
        if latest['macd_line'] > latest['macd_signal']:
            signals.append("MACD: Бычий импульс")
        else:
            signals.append("MACD: Медвежий импульс")
        
        print("   📊 Технические сигналы:")
        for i, signal in enumerate(signals, 1):
            print(f"     {i}. {signal}")
        
        # Итоговый score
        bullish_signals = sum(1 for s in signals if 'восходящий' in s.lower() or 'бычий' in s.lower())
        bearish_signals = sum(1 for s in signals if 'нисходящий' in s.lower() or 'медвежий' in s.lower())
        
        if bullish_signals > bearish_signals:
            overall_sentiment = "Умеренно бычий"
        elif bearish_signals > bullish_signals:
            overall_sentiment = "Умеренно медвежий"
        else:
            overall_sentiment = "Нейтральный"
        
        print(f"   🎯 Общий сигнал: {overall_sentiment}")
        
    except Exception as e:
        raise RuntimeError(f"Ошибка комбинированного анализа: {e}") from e
    
    # 9. Сводная информация
    print(f"\n📋 Сводка расчетов:")
    print(f"   ✅ Количество индикаторов: {len(available_indicators)}")
    print(f"   ✅ Период анализа: {len(data)} баров")
    print(f"   ✅ Временной диапазон: {data.index[-1] - data.index[0]}")

    if ta_rsi_result is not None:
        print(f"   📘 Подробности: см. docs/api/indicators/library_manager.md")
    
    return combined_data


def save_results_to_csv(data: pd.DataFrame, filename: str = "indicator_results.csv"):
    """Сохранение результатов в CSV файл."""
    try:
        # Рядом со скриптом, а не в "examples/" относительно cwd: запуск из другого
        # каталога падал на несуществующем пути и печатал "❌" с кодом 0
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        data.to_csv(filepath)
        print(f"\n💾 Результаты сохранены в файл: {filepath}")
        print(f"   📊 Колонки: {', '.join(data.columns.tolist())}")
        print(f"   📈 Строк данных: {len(data)}")
    except Exception as e:
        raise RuntimeError(f"Ошибка сохранения: {e}") from e


if __name__ == "__main__":
    try:
        # Запускаем демонстрацию
        results = demonstrate_basic_indicators()
        
        # Сохраняем результаты
        if results is not None:
            save_results_to_csv(results)
        
        print(f"\n🎉 Демонстрация завершена успешно!")
        print(f"\n💡 Для изучения других примеров, см. файлы в папке examples/")
        
    except Exception as e:
        print(f"\n❌ Ошибка выполнения: {e}")
        import traceback
        traceback.print_exc()
        # Пример, который упал, обязан сказать это кодом возврата: до G65 он печатал
        # трейсбек и выходил с 0, и батарея перед релизом считала его зелёным.
        sys.exit(1)
