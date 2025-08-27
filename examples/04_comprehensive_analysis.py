#!/usr/bin/env python3
"""
BQuant - Комплексный пример анализа

Этот пример объединяет все возможности BQuant:
1. Загрузку и подготовку данных
2. Расчет технических индикаторов
3. MACD анализ зон с полной статистикой
4. Создание торговой системы
5. Бэктестинг и анализ результатов
6. Экспорт результатов и отчетов

Требования:
- Установленный BQuant пакет: pip install -e .
- Достаточно данных для полноценного анализа
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json

# Добавляем путь к BQuant для импорта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bquant.data import (
    create_sample_data, calculate_derived_indicators,
    validate_ohlcv_data, clean_data, normalize_data
)
from bquant.indicators import (
    calculate_moving_averages, calculate_macd, calculate_rsi,
    calculate_bollinger_bands, get_available_indicators
)
from bquant.indicators.macd import (
    MACDZoneAnalyzer, analyze_macd_zones
)
from bquant.core.config import get_indicator_params


class ComprehensiveTradingAnalyzer:
    """
    Комплексный анализатор для создания и тестирования торговых систем.
    
    Объединяет:
    - Технические индикаторы
    - MACD анализ зон
    - Правила торговой системы
    - Бэктестинг
    - Статистику результатов
    """
    
    def __init__(self, symbol: str = "XAUUSD", timeframe: str = "1h"):
        """Инициализация анализатора."""
        self.symbol = symbol
        self.timeframe = timeframe
        self.data = None
        self.indicators_data = None
        self.macd_analysis = None
        self.signals = None
        self.trades = []
        self.performance_stats = {}
        
        print(f"🚀 Comprehensive Trading Analyzer инициализирован")
        print(f"   📊 Символ: {symbol}")
        print(f"   ⏰ Таймфрейм: {timeframe}")
    
    def load_and_prepare_data(self, start_date: str, end_date: str, 
                             rows: Optional[int] = None) -> pd.DataFrame:
        """Загрузка и подготовка данных для анализа."""
        
        print(f"\n📥 Загрузка и подготовка данных:")
        
        # Создаем реалистичные данные
        if rows:
            self.data = self._create_realistic_market_data(rows)
        else:
            self.data = create_sample_data(
                symbol=self.symbol,
                start_date=start_date,
                end_date=end_date,
                timeframe=self.timeframe
            )
        
        print(f"   ✅ Загружено {len(self.data)} баров")
        print(f"   📅 Период: {self.data.index[0]} - {self.data.index[-1]}")
        
        # Валидация данных
        validation_result = validate_ohlcv_data(self.data)
        if isinstance(validation_result, dict) and validation_result.get('is_valid', False):
            print(f"   ✅ Данные прошли валидацию")
        else:
            print(f"   ⚠️ Данные требуют очистки")
            self.data = clean_data(self.data)
            print(f"   ✅ Данные очищены: {len(self.data)} баров")
        
        # Базовая статистика
        price_change = ((self.data['close'].iloc[-1] / self.data['close'].iloc[0]) - 1) * 100
        volatility = self.data['close'].pct_change().std() * np.sqrt(252) * 100  # Годовая волатильность
        
        print(f"   📈 Общее изменение цены: {price_change:.2f}%")
        print(f"   📊 Годовая волатильность: {volatility:.2f}%")
        
        return self.data
    
    def _create_realistic_market_data(self, rows: int) -> pd.DataFrame:
        """Создание реалистичных рыночных данных с различными режимами."""
        
        dates = pd.date_range(start='2024-01-01', periods=rows, freq='1H')
        np.random.seed(42)
        
        # Базовая цена для разных инструментов
        price_map = {
            'XAUUSD': 2000, 'EURUSD': 1.1000, 'GBPUSD': 1.2500,
            'USDJPY': 145.0, 'BTCUSD': 45000, 'AUDCAD': 0.9200
        }
        base_price = price_map.get(self.symbol, 2000)
        
        prices = [base_price]
        
        # Создаем различные рыночные режимы
        for i in range(1, rows):
            # Определяем текущий режим рынка
            cycle_position = i / rows
            
            if cycle_position < 0.3:
                # Медвежий тренд
                trend = -0.0008
                volatility = 0.008
            elif cycle_position < 0.4:
                # Консолидация
                trend = 0
                volatility = 0.004
            elif cycle_position < 0.7:
                # Бычий тренд
                trend = 0.0012
                volatility = 0.006
            elif cycle_position < 0.8:
                # Коррекция
                trend = -0.0006
                volatility = 0.010
            else:
                # Боковик
                trend = 0.0002 * np.sin(i / 20)
                volatility = 0.005
            
            # Добавляем случайные шоки
            if i % 100 == 0:
                shock = np.random.choice([-0.015, 0.015], p=[0.5, 0.5])
            else:
                shock = 0
            
            # Рассчитываем изменение цены
            noise = np.random.normal(0, volatility)
            total_change = trend + noise + shock
            
            new_price = prices[-1] * (1 + total_change)
            prices.append(max(new_price, base_price * 0.1))
        
        # Создаем OHLCV структуру
        data = []
        for i, close_price in enumerate(prices):
            open_price = prices[i-1] if i > 0 else close_price
            
            # Реалистичные high/low с учетом волатильности
            price_range = abs(close_price - open_price) * np.random.uniform(1.5, 3.0)
            high = max(open_price, close_price) + price_range * np.random.uniform(0, 0.7)
            low = min(open_price, close_price) - price_range * np.random.uniform(0, 0.7)
            
            # Объем коррелирует с волатильностью
            price_change = abs((close_price - open_price) / open_price)
            base_volume = 100000
            volume_multiplier = 1 + price_change * 10
            volume = int(base_volume * volume_multiplier * np.random.uniform(0.5, 2.0))
            
            data.append({
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume
            })
        
        return pd.DataFrame(data, index=dates)
    
    def calculate_all_indicators(self) -> pd.DataFrame:
        """Расчет всех технических индикаторов."""
        
        print(f"\n🔧 Расчет технических индикаторов:")
        
        if self.data is None:
            raise ValueError("Данные не загружены. Вызовите load_and_prepare_data() сначала.")
        
        # Начинаем с исходных данных
        self.indicators_data = self.data.copy()
        
        # 1. Скользящие средние
        print(f"   📈 Скользящие средние...")
        ma_data = calculate_moving_averages(self.data, periods=[10, 20, 50, 200])
        for col in ma_data.columns:
            if col.startswith('sma_'):
                self.indicators_data[col] = ma_data[col]
        
        # 2. RSI
        print(f"   📊 RSI...")
        rsi_data = calculate_rsi(self.data, period=14)
        self.indicators_data['rsi'] = rsi_data['rsi']
        
        # 3. MACD
        print(f"   📉 MACD...")
        macd_data = calculate_macd(self.data)
        for col in ['macd', 'macd_signal', 'macd_hist']:
            self.indicators_data[col] = macd_data[col]
        
        # 4. Bollinger Bands
        print(f"   📊 Bollinger Bands...")
        bb_data = calculate_bollinger_bands(self.data, period=20, std_dev=2)
        for col in bb_data.columns:
            if col.startswith('bb_'):
                self.indicators_data[col] = bb_data[col]
        
        # 5. Производные индикаторы
        print(f"   🔄 Производные индикаторы...")
        derived_data = calculate_derived_indicators(self.indicators_data)
        
        # Добавляем только новые колонки
        for col in derived_data.columns:
            if col not in self.indicators_data.columns:
                self.indicators_data[col] = derived_data[col]
        
        print(f"   ✅ Рассчитано индикаторов: {len(self.indicators_data.columns) - len(self.data.columns)}")
        print(f"   📊 Общее количество колонок: {len(self.indicators_data.columns)}")
        
        return self.indicators_data
    
    def perform_macd_zone_analysis(self) -> None:
        """Выполнение полного MACD анализа зон."""
        
        print(f"\n🎯 MACD анализ зон:")
        
        if self.indicators_data is None:
            raise ValueError("Индикаторы не рассчитаны. Вызовите calculate_all_indicators() сначала.")
        
        # Выполняем анализ зон MACD
        self.macd_analysis = analyze_macd_zones(
            self.indicators_data,
            perform_clustering=True,
            n_clusters=3
        )
        
        print(f"   ✅ Найдено зон: {len(self.macd_analysis.zones)}")
        
        if self.macd_analysis.zones:
            bull_zones = [z for z in self.macd_analysis.zones if z.type == 'bull']
            bear_zones = [z for z in self.macd_analysis.zones if z.type == 'bear']
            
            print(f"   🐂 Бычьих зон: {len(bull_zones)}")
            print(f"   🐻 Медвежьих зон: {len(bear_zones)}")
            
            # Статистики зон
            if self.macd_analysis.statistics:
                stats = self.macd_analysis.statistics
                print(f"   📊 Средняя длительность бычьих зон: {stats.get('bull_duration_mean', 0):.1f} баров")
                print(f"   📊 Средняя длительность медвежьих зон: {stats.get('bear_duration_mean', 0):.1f} баров")
            
            # Результаты гипотез
            if self.macd_analysis.hypothesis_tests:
                significant_tests = [name for name, result in self.macd_analysis.hypothesis_tests.items() 
                                   if result.get('significant', False)]
                print(f"   🧪 Значимых статистических тестов: {len(significant_tests)}")
                
            # Кластеризация
            if self.macd_analysis.clustering:
                n_clusters = self.macd_analysis.clustering['n_clusters']
                print(f"   🎯 Зоны сгруппированы в {n_clusters} кластера")
    
    def generate_trading_signals(self) -> pd.DataFrame:
        """Генерация торговых сигналов на основе комплексного анализа."""
        
        print(f"\n📡 Генерация торговых сигналов:")
        
        if self.indicators_data is None:
            raise ValueError("Индикаторы не рассчитаны.")
        
        signals_data = self.indicators_data.copy()
        
        # Инициализируем колонки сигналов
        signals_data['signal'] = 0  # 0 = hold, 1 = buy, -1 = sell
        signals_data['signal_strength'] = 0  # Сила сигнала 0-1
        signals_data['signal_reason'] = ''
        
        # 1. Сигналы на основе трендовых индикаторов
        print(f"   📈 Анализ трендовых сигналов...")
        
        # SMA кроссоверы
        sma_10_20_cross = np.where(
            (signals_data['sma_10'] > signals_data['sma_20']) & 
            (signals_data['sma_10'].shift(1) <= signals_data['sma_20'].shift(1)), 1, 0
        )
        sma_20_50_cross = np.where(
            (signals_data['sma_20'] > signals_data['sma_50']) & 
            (signals_data['sma_20'].shift(1) <= signals_data['sma_50'].shift(1)), 1, 0
        )
        
        # 2. Сигналы на основе импульса
        print(f"   ⚡ Анализ импульсных сигналов...")
        
        # RSI сигналы
        rsi_oversold = signals_data['rsi'] < 30
        rsi_overbought = signals_data['rsi'] > 70
        
        # MACD сигналы
        macd_bullish = (signals_data['macd'] > signals_data['macd_signal']) & \
                       (signals_data['macd'].shift(1) <= signals_data['macd_signal'].shift(1))
        macd_bearish = (signals_data['macd'] < signals_data['macd_signal']) & \
                       (signals_data['macd'].shift(1) >= signals_data['macd_signal'].shift(1))
        
        # 3. Сигналы на основе волатильности
        print(f"   🌊 Анализ волатильностных сигналов...")
        
        # Bollinger Bands сигналы
        bb_oversold = signals_data['close'] < signals_data['bb_lower']
        bb_overbought = signals_data['close'] > signals_data['bb_upper']
        
        # 4. Комбинированные сигналы
        print(f"   🎯 Создание комбинированных сигналов...")
        
        for i in range(len(signals_data)):
            signal_score = 0
            reasons = []
            
            # Бычьи сигналы
            if sma_10_20_cross[i]:
                signal_score += 0.3
                reasons.append("SMA10>SMA20")
            
            if sma_20_50_cross[i]:
                signal_score += 0.2
                reasons.append("SMA20>SMA50")
            
            if macd_bullish[i]:
                signal_score += 0.3
                reasons.append("MACD_bullish")
            
            if rsi_oversold[i]:
                signal_score += 0.2
                reasons.append("RSI_oversold")
            
            if bb_oversold[i]:
                signal_score += 0.2
                reasons.append("BB_oversold")
            
            # Медвежьи сигналы
            if macd_bearish[i]:
                signal_score -= 0.3
                reasons.append("MACD_bearish")
            
            if rsi_overbought[i]:
                signal_score -= 0.2
                reasons.append("RSI_overbought")
            
            if bb_overbought[i]:
                signal_score -= 0.2
                reasons.append("BB_overbought")
            
            # Определяем финальный сигнал
            if signal_score >= 0.5:
                signals_data.loc[signals_data.index[i], 'signal'] = 1
                signals_data.loc[signals_data.index[i], 'signal_strength'] = min(signal_score, 1.0)
            elif signal_score <= -0.5:
                signals_data.loc[signals_data.index[i], 'signal'] = -1
                signals_data.loc[signals_data.index[i], 'signal_strength'] = min(abs(signal_score), 1.0)
            
            signals_data.loc[signals_data.index[i], 'signal_reason'] = '; '.join(reasons)
        
        self.signals = signals_data
        
        # Статистика сигналов
        buy_signals = (signals_data['signal'] == 1).sum()
        sell_signals = (signals_data['signal'] == -1).sum()
        
        print(f"   ✅ Сгенерировано сигналов:")
        print(f"      📈 Buy: {buy_signals}")
        print(f"      📉 Sell: {sell_signals}")
        print(f"      📊 Общий процент активности: {((buy_signals + sell_signals) / len(signals_data) * 100):.1f}%")
        
        return signals_data
    
    def backtest_strategy(self, initial_capital: float = 10000, 
                         commission: float = 0.001) -> Dict[str, Any]:
        """Бэктестинг торговой стратегии."""
        
        print(f"\n📊 Бэктестинг торговой стратегии:")
        print(f"   💰 Начальный капитал: ${initial_capital:,.2f}")
        print(f"   💸 Комиссия: {commission:.3%}")
        
        if self.signals is None:
            raise ValueError("Сигналы не сгенерированы. Вызовите generate_trading_signals() сначала.")
        
        # Инициализация переменных
        capital = initial_capital
        position = 0  # 0 = нет позиции, 1 = long, -1 = short
        position_size = 0
        entry_price = 0
        trades = []
        equity_curve = [initial_capital]
        
        for i, (timestamp, row) in enumerate(self.signals.iterrows()):
            current_price = row['close']
            signal = row['signal']
            signal_strength = row['signal_strength']
            
            # Закрытие существующих позиций
            if position != 0:
                # Условия закрытия позиции
                should_close = False
                close_reason = ""
                
                # Противоположный сигнал
                if (position == 1 and signal == -1) or (position == -1 and signal == 1):
                    should_close = True
                    close_reason = "opposite_signal"
                
                # Стоп-лосс/тейк-профит (упрощенно)
                if position == 1:  # Long позиция
                    pnl_pct = (current_price - entry_price) / entry_price
                    if pnl_pct <= -0.02:  # 2% стоп-лосс
                        should_close = True
                        close_reason = "stop_loss"
                    elif pnl_pct >= 0.04:  # 4% тейк-профит
                        should_close = True
                        close_reason = "take_profit"
                
                elif position == -1:  # Short позиция
                    pnl_pct = (entry_price - current_price) / entry_price
                    if pnl_pct <= -0.02:  # 2% стоп-лосс
                        should_close = True
                        close_reason = "stop_loss"
                    elif pnl_pct >= 0.04:  # 4% тейк-профит
                        should_close = True
                        close_reason = "take_profit"
                
                # Закрываем позицию
                if should_close:
                    # Рассчитываем P&L
                    if position == 1:  # Закрытие long
                        pnl = position_size * (current_price - entry_price)
                    else:  # Закрытие short
                        pnl = position_size * (entry_price - current_price)
                    
                    commission_cost = position_size * current_price * commission
                    net_pnl = pnl - commission_cost
                    capital += net_pnl
                    
                    # Записываем сделку
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': timestamp,
                        'position_type': 'long' if position == 1 else 'short',
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'size': position_size,
                        'pnl': pnl,
                        'commission': commission_cost,
                        'net_pnl': net_pnl,
                        'close_reason': close_reason
                    })
                    
                    position = 0
                    position_size = 0
            
            # Открытие новых позиций
            if position == 0 and signal != 0 and signal_strength >= 0.6:
                position = signal
                entry_price = current_price
                entry_time = timestamp
                
                # Размер позиции зависит от силы сигнала
                risk_per_trade = 0.02  # 2% риска на сделку
                position_value = capital * risk_per_trade * signal_strength
                position_size = position_value / current_price
                
                commission_cost = position_size * current_price * commission
                capital -= commission_cost
            
            # Обновляем equity curve
            current_equity = capital
            if position != 0:
                if position == 1:
                    unrealized_pnl = position_size * (current_price - entry_price)
                else:
                    unrealized_pnl = position_size * (entry_price - current_price)
                current_equity += unrealized_pnl
            
            equity_curve.append(current_equity)
        
        self.trades = trades
        
        # Расчет статистики
        if trades:
            total_trades = len(trades)
            winning_trades = [t for t in trades if t['net_pnl'] > 0]
            losing_trades = [t for t in trades if t['net_pnl'] < 0]
            
            win_rate = len(winning_trades) / total_trades
            total_pnl = sum(t['net_pnl'] for t in trades)
            avg_win = np.mean([t['net_pnl'] for t in winning_trades]) if winning_trades else 0
            avg_loss = np.mean([t['net_pnl'] for t in losing_trades]) if losing_trades else 0
            
            max_equity = max(equity_curve)
            min_equity_after_max = min(equity_curve[equity_curve.index(max_equity):])
            max_drawdown = (max_equity - min_equity_after_max) / max_equity
            
            final_capital = equity_curve[-1]
            total_return = (final_capital - initial_capital) / initial_capital
            
            self.performance_stats = {
                'initial_capital': initial_capital,
                'final_capital': final_capital,
                'total_return': total_return,
                'total_pnl': total_pnl,
                'total_trades': total_trades,
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
                'max_drawdown': max_drawdown,
                'equity_curve': equity_curve
            }
            
            print(f"   ✅ Бэктестинг завершен:")
            print(f"      📈 Итоговый капитал: ${final_capital:,.2f}")
            print(f"      📊 Общая доходность: {total_return:.2%}")
            print(f"      🎯 Сделок: {total_trades}")
            print(f"      ✅ Процент выигрышных: {win_rate:.1%}")
            print(f"      📉 Максимальная просадка: {max_drawdown:.2%}")
            
        else:
            print(f"   ⚠️ Сделок не совершено")
            self.performance_stats = {'total_trades': 0}
        
        return self.performance_stats
    
    def generate_comprehensive_report(self, save_to_file: bool = True) -> Dict[str, Any]:
        """Генерация комплексного отчета по анализу."""
        
        print(f"\n📋 Генерация комплексного отчета:")
        
        report = {
            'analysis_info': {
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'analysis_timestamp': datetime.now().isoformat(),
                'data_period': {
                    'start': self.data.index[0].isoformat() if hasattr(self.data.index[0], 'isoformat') else str(self.data.index[0]),
                    'end': self.data.index[-1].isoformat() if hasattr(self.data.index[-1], 'isoformat') else str(self.data.index[-1]),
                    'total_bars': len(self.data)
                }
            },
            'data_statistics': {
                'price_change': float(((self.data['close'].iloc[-1] / self.data['close'].iloc[0]) - 1) * 100),
                'volatility': float(self.data['close'].pct_change().std() * np.sqrt(252) * 100),
                'max_price': float(self.data['high'].max()),
                'min_price': float(self.data['low'].min()),
                'avg_volume': float(self.data['volume'].mean())
            },
            'indicators_summary': {
                'total_indicators': len(self.indicators_data.columns) - len(self.data.columns),
                'current_values': {
                    'sma_20': float(self.indicators_data['sma_20'].iloc[-1]) if 'sma_20' in self.indicators_data.columns else None,
                    'rsi': float(self.indicators_data['rsi'].iloc[-1]) if 'rsi' in self.indicators_data.columns else None,
                    'macd': float(self.indicators_data['macd'].iloc[-1]) if 'macd' in self.indicators_data.columns else None,
                }
            },
            'macd_zone_analysis': {},
            'trading_signals': {},
            'backtest_results': self.performance_stats
        }
        
        # Добавляем MACD анализ
        if self.macd_analysis:
            report['macd_zone_analysis'] = {
                'total_zones': len(self.macd_analysis.zones),
                'bull_zones': len([z for z in self.macd_analysis.zones if z.type == 'bull']),
                'bear_zones': len([z for z in self.macd_analysis.zones if z.type == 'bear']),
                'statistics': self.macd_analysis.statistics,
                'hypothesis_tests': self.macd_analysis.hypothesis_tests,
                'clustering_performed': self.macd_analysis.clustering is not None
            }
        
        # Добавляем статистику сигналов
        if self.signals is not None:
            buy_signals = (self.signals['signal'] == 1).sum()
            sell_signals = (self.signals['signal'] == -1).sum()
            
            report['trading_signals'] = {
                'total_buy_signals': int(buy_signals),
                'total_sell_signals': int(sell_signals),
                'signal_frequency': float((buy_signals + sell_signals) / len(self.signals) * 100)
            }
        
        print(f"   ✅ Отчет сгенерирован")
        print(f"   📊 Разделов в отчете: {len(report)}")
        
        # Сохранение в файл
        if save_to_file:
            report_file = f"examples/comprehensive_analysis_report_{self.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            try:
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                print(f"   💾 Отчет сохранен: {report_file}")
            except Exception as e:
                print(f"   ❌ Ошибка сохранения отчета: {e}")
        
        return report


def run_comprehensive_analysis():
    """Запуск полного комплексного анализа."""
    
    print("🚀 BQuant - Комплексный анализ торговой системы")
    print("=" * 70)
    
    # Создаем анализатор
    analyzer = ComprehensiveTradingAnalyzer("XAUUSD", "1h")
    
    try:
        # 1. Загрузка данных
        data = analyzer.load_and_prepare_data(
            start_date="2024-01-01", 
            end_date="2024-03-01",
            rows=1000  # Используем больше данных для качественного анализа
        )
        
        # 2. Расчет индикаторов
        indicators = analyzer.calculate_all_indicators()
        
        # 3. MACD анализ зон
        analyzer.perform_macd_zone_analysis()
        
        # 4. Генерация сигналов
        signals = analyzer.generate_trading_signals()
        
        # 5. Бэктестинг
        performance = analyzer.backtest_strategy(
            initial_capital=10000,
            commission=0.001
        )
        
        # 6. Комплексный отчет
        report = analyzer.generate_comprehensive_report()
        
        # 7. Сохранение данных
        print(f"\n💾 Сохранение результатов анализа:")
        
        # Сохраняем основные датасеты
        data.to_csv("examples/comprehensive_market_data.csv")
        indicators.to_csv("examples/comprehensive_indicators.csv")
        signals.to_csv("examples/comprehensive_signals.csv")
        
        # Сохраняем сделки
        if analyzer.trades:
            trades_df = pd.DataFrame(analyzer.trades)
            trades_df.to_csv("examples/comprehensive_trades.csv", index=False)
            print(f"   ✅ Сохранено сделок: {len(analyzer.trades)}")
        
        print(f"   ✅ Основные данные сохранены в папке examples/")
        
        return analyzer, report
        
    except Exception as e:
        print(f"\n❌ Ошибка анализа: {e}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    try:
        # Запускаем комплексный анализ
        analyzer, report = run_comprehensive_analysis()
        
        if analyzer and report:
            print(f"\n🎉 Комплексный анализ завершен успешно!")
            print(f"\n📊 Краткие итоги:")
            
            if report['backtest_results'].get('total_trades', 0) > 0:
                stats = report['backtest_results']
                print(f"   💰 Итоговая доходность: {stats['total_return']:.2%}")
                print(f"   🎯 Сделок выполнено: {stats['total_trades']}")
                print(f"   ✅ Процент выигрышных: {stats['win_rate']:.1%}")
                print(f"   📉 Максимальная просадка: {stats['max_drawdown']:.2%}")
            
            if 'macd_zone_analysis' in report:
                macd_stats = report['macd_zone_analysis']
                print(f"   🎯 MACD зон найдено: {macd_stats['total_zones']}")
                print(f"   🐂 Бычьих зон: {macd_stats['bull_zones']}")
                print(f"   🐻 Медвежьих зон: {macd_stats['bear_zones']}")
            
            print(f"\n💡 Ключевые возможности продемонстрированы:")
            print(f"   ✓ Комплексная подготовка данных")
            print(f"   ✓ Расчет множественных технических индикаторов")
            print(f"   ✓ Продвинутый MACD анализ зон")
            print(f"   ✓ Генерация торговых сигналов")
            print(f"   ✓ Полноценный бэктестинг")
            print(f"   ✓ Подробная статистика и отчетность")
            print(f"   ✓ Экспорт всех результатов")
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
