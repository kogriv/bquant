"""
Модуль анализа характеристик зон BQuant

Адаптировано из scripts/research/macd_analysis.py с улучшениями для новой архитектуры.
Предоставляет функции для анализа признаков и распределения торговых зон.
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.signal import find_peaks
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass

from ...core.logging_config import get_logger
from ...core.exceptions import AnalysisError
from ...core.config import create_swing_strategy, create_divergence_strategy, create_shape_strategy, create_volume_strategy, create_volatility_strategy
from .. import AnalysisResult, BaseAnalyzer
from .models import ZoneInfo

# Получаем логгер для модуля
logger = get_logger(__name__)


@dataclass
class ZoneFeatures:
    """
    Характеристики торговой зоны.
    
    Attributes:
        zone_id: Уникальный идентификатор зоны
        zone_type: Тип зоны ('bull' или 'bear')
        duration: Длительность зоны в периодах
        start_price: Цена в начале зоны
        end_price: Цена в конце зоны
        price_return: Доходность за зону
        line_amplitude: Размах роли ``line`` индикатора внутри зоны
            (``max − min``). ``None``, если индикатор линии не объявляет — у RSI
            её нет, и это не «нет данных», а «такой роли не существует».

            Поле называлось ``macd_amplitude``: универсальная метрика носила имя
            одного индикатора. Читателю приходилось знать, что на зонах RSI это
            поле пусто по устройству, а не по недостатку данных, — и именно эта
            путаница стоила проекту G23, где пустой предиктор с MACD-овским
            именем уносил всю выборку регрессии.
        oscillator_amplitude: Размах **того ряда, по которому детектировались
            зоны** (``max − min``) — какой бы индикатор его ни дал. Поле
            называлось ``hist_amplitude``, и это было неверно на любом наборе,
            кроме MACD по гистограмме: на зонах RSI там лежал размах RSI.
        price_range_pct: Ценовой диапазон в процентах
        atr_normalized_return: Доходность, нормализованная на ATR
        correlation_price_oscillator: Корреляция цены с рядом детекции
            (бывшее ``correlation_price_hist``)
        num_peaks: Количество пиков в зоне
        num_troughs: Количество впадин в зоне
        drawdown_from_peak: Экскурсия цены от максимума зоны к её концу
            (``end/max - 1``, значение ≤ 0). Считается для **любой** зоны.
        rally_from_trough: Экскурсия цены от минимума зоны к её концу
            (``end/min - 1``, значение ≥ 0). Считается для **любой** зоны.
        peak_time_ratio: Положение максимума внутри зоны (0.0-1.0). Для любой зоны.
        trough_time_ratio: Положение минимума внутри зоны (0.0-1.0). Для любой зоны.

            Все четыре считаются безусловно и не зависят от имени типа зоны. Какая
            из них содержательна — решает потребитель по объявленной полярности
            типа (:meth:`ZoneVocabulary.polarity_of`): у приподнятой зоны говорящая
            величина — просадка от пика, у подавленной — отскок от минимума.
            ``None`` в этих полях означает, что зону не удалось измерить (нулевая
            цена), а не «метрика неприменима к этому типу».
        oscillator_slope: Максимальная скорость изменения ряда детекции
            (бывшее ``hist_slope``)
        start_idx: Позиция первого бара зоны во входном кадре (``iloc``), если известна.
        end_idx: Позиция последнего бара зоны во входном кадре (``iloc``), включительно.

            Границы нужны потребителям, которые рассуждают о **соседстве** зон.
            Анализ последовательностей читает соседние элементы списка как переход;
            если между зонами есть пропуск (например, короткая зона отброшена по
            ``min_duration``), такой «переход» произошёл не между соседями. Без этих
            полей отличить одно от другого нельзя, и разрыв неотличим от стыка
            (разбор: ``devref/gaps/sequence/``).
        metadata: Дополнительные метаданные
    """
    zone_id: str
    zone_type: str
    duration: int
    start_price: float
    end_price: float
    price_return: float
    line_amplitude: Optional[float] = None  # Optional - для универсальности
    oscillator_amplitude: Optional[float] = None  # Optional - для универсальности
    price_range_pct: float = 0.0
    atr_normalized_return: Optional[float] = None
    correlation_price_oscillator: Optional[float] = None
    num_peaks: Optional[int] = None
    num_troughs: Optional[int] = None
    drawdown_from_peak: Optional[float] = None
    rally_from_trough: Optional[float] = None
    peak_time_ratio: Optional[float] = None
    trough_time_ratio: Optional[float] = None
    oscillator_slope: Optional[float] = None
    start_idx: Optional[int] = None
    end_idx: Optional[int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь."""
        result = {}
        for field, value in self.__dict__.items():
            if isinstance(value, (int, float, str, bool)) or value is None:
                result[field] = value
            elif isinstance(value, dict):
                result[field] = value
        return result



def _as_optional_int(value: Any) -> Optional[int]:
    """Coerce numpy/pandas integers to a plain ``int``; pass ``None`` through."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

class ZoneFeaturesAnalyzer(BaseAnalyzer):
    """
    Анализатор характеристик торговых зон с поддержкой стратегий.
    
    Предоставляет методы для:
    - Извлечения признаков зон
    - Анализа распределения характеристик
    - Статистического анализа зон
    - Сравнительного анализа типов зон
    
    Поддерживает расширяемую архитектуру метрик через Strategy Pattern (Phase 3.0+).
    """
    
    def __init__(self,
                 swing_strategy=None,
                 divergence_strategy=None,
                 shape_strategy=None,
                 volume_strategy=None,
                 volatility_strategy=None):
        """
        Инициализация анализатора.

        Args:
            swing_strategy: Стратегия расчета свингов (по умолчанию из config)
            divergence_strategy: Стратегия расчета дивергенций (по умолчанию из config)
            shape_strategy: Стратегия расчета формы (по умолчанию из config)
            volume_strategy: Стратегия расчета объема (по умолчанию из config)
            volatility_strategy: Стратегия расчета волатильности (по умолчанию из config)

        Note:
            Стратегии по умолчанию загружаются из ANALYSIS_CONFIG['zone_features'].
            Если стратегия не указана и не настроена в config, используется None.

            Здесь больше нет ``min_duration`` и ``min_amplitude``. Первый был
            **вторым** фильтром длительности — короткую зону он не пропускал, а
            вызывающий узнавал об этом из предупреждения в логе; отсев коротких
            зон стал явным параметром стадии анализа. Второй не использовался
            нигде: он хранился, логировался и попадал в метаданные результата,
            но ни одной величины не менял.
        """
        super().__init__("ZoneFeaturesAnalyzer")

        # v2.1: Стратегии через фабрики (support string names from Builder API)
        # Factory converts string names to strategy instances
        self.swing_strategy = create_swing_strategy(swing_strategy)
        self.divergence_strategy = create_divergence_strategy(divergence_strategy)
        self.shape_strategy = create_shape_strategy(shape_strategy)
        self.volume_strategy = create_volume_strategy(volume_strategy)
        self.volatility_strategy = create_volatility_strategy(volatility_strategy)
        
        self.logger = get_logger(f"{__name__}.ZoneFeaturesAnalyzer")
        
        strategy_info = {
            'swing': self.swing_strategy.__class__.__name__ if self.swing_strategy else 'None',
            'divergence': self.divergence_strategy.__class__.__name__ if self.divergence_strategy else 'None',
            'shape': self.shape_strategy.__class__.__name__ if self.shape_strategy else 'None',
            'volume': self.volume_strategy.__class__.__name__ if self.volume_strategy else 'None',
            'volatility': self.volatility_strategy.__class__.__name__ if self.volatility_strategy else 'None'
        }
        
        self.logger.info(
            f"Initialized zone features analyzer with strategies={strategy_info}"
        )
    
    def extract_zone_features(self, zone_info: Dict[str, Any]) -> ZoneFeatures:
        """
        Извлечение признаков из информации о зоне.
        
        UNIVERSAL METHOD (v2.1):
        - Reads indicator_context from zone_info
        - Passes correct indicator_col to strategies
        - Fallback to generic oscillator detection if context missing
        
        Args:
            zone_info: Словарь с информацией о зоне
                - zone_id: ID зоны
                - type: Метка типа зоны — открытый словарь, задаваемый
                  стратегией детекции. Извлечение метрик от неё не зависит:
                  все метрики считаются одинаково для любого типа.  
                - duration: Длительность
                - data: DataFrame с OHLCV + индикаторы
                - indicator_context: (v2.1 NEW) Контекст детекции (detection_indicator, signal_line)
        
        Returns:
            ZoneFeatures: Объект с характеристиками зоны
        """
        try:
            data = zone_info['data']
            zone_type = zone_info['type']
            zone_id = zone_info.get('zone_id', f"{zone_type}_{len(data)}")
            
            # v2.1: Read indicator context from zone_info
            indicator_context = zone_info.get('indicator_context', {})
            primary_indicator = indicator_context.get('detection_indicator')
            signal_line = indicator_context.get('signal_line')
            column_schema = zone_info.get('column_schema')
            
            if len(data) == 0:
                raise AnalysisError(
                    f"Zone {zone_id} carries no bars; nothing to measure"
                )

            # Базовые характеристики
            start_price = float(data['close'].iloc[0])
            end_price = float(data['close'].iloc[-1])
            price_return = (end_price / start_price) - 1
            
            # v2.1: Generic oscillator metrics (UNIVERSAL - use context)
            # Fields oscillator_amplitude, oscillator_slope are now UNIVERSAL (not MACD-specific)
            oscillator_amplitude = None
            oscillator_slope = None
            max_line = None
            min_line = None
            line_amplitude = None
            
            if primary_indicator and primary_indicator in data.columns:
                # Calculate from primary indicator (ANY oscillator)
                osc_values = data[primary_indicator]
                max_osc = float(osc_values.max())
                min_osc = float(osc_values.min())
                oscillator_amplitude = max_osc - min_osc  # Reusing field for universal amplitude
                
                # Calculate max rate of change (universal slope)
                if len(data) >= 2:
                    oscillator_slope = float(osc_values.diff().abs().max())
                
                slope_str = f"{oscillator_slope:.4f}" if oscillator_slope is not None else "0.0000"
                self.logger.debug(
                    f"Oscillator metrics for '{primary_indicator}': "
                    f"amplitude={oscillator_amplitude:.4f}, slope={slope_str}"
                )
                
                # Амплитуда **линии** индикатора — там, где линия вообще есть.
                # Раньше здесь стояло `if 'macd' in primary_indicator.lower()` и
                # `if 'macd' in data.columns`: угадывание по подстроке в имени
                # колонки, то самое, из-за чего заведён G8. Оно ломалось молча —
                # у осциллятора без линии (RSI) поле оставалось `None` во всех
                # зонах, и регрессия, где оно предиктор по умолчанию, оставалась
                # без единого наблюдения (см. G23).
                line_col = column_schema.column('line') if column_schema else None
                if line_col and line_col in data.columns:
                    max_line = float(data[line_col].max())
                    min_line = float(data[line_col].min())
                    line_amplitude = max_line - min_line
            else:
                # Fallback: try to find ANY oscillator (if context missing)
                fallback_col = self._find_any_oscillator(data)
                if fallback_col and fallback_col in data.columns:
                    osc_values = data[fallback_col]
                    max_osc = float(osc_values.max())
                    min_osc = float(osc_values.min())
                    oscillator_amplitude = max_osc - min_osc
                    
                    if len(data) >= 2:
                        oscillator_slope = float(osc_values.diff().abs().max())
                    
                    self.logger.debug(
                        f"Oscillator metrics (fallback to '{fallback_col}'): "
                        f"amplitude={oscillator_amplitude:.4f}"
                    )
            
            # Ценовые характеристики
            max_price = float(data['high'].max())
            min_price = float(data['low'].min())
            price_range_pct = (max_price / min_price) - 1
            
            # ATR нормализация
            atr_normalized_return = None
            if 'atr' in data.columns and data['atr'].iloc[0] > 0:
                atr_normalized_return = price_return / float(data['atr'].iloc[0])
            
            # v2.1: Price-indicator correlation (UNIVERSAL - use context)
            correlation_price_oscillator = None
            if len(data) >= 3:
                # Use primary_indicator from context (already available from line 177)
                if primary_indicator and primary_indicator in data.columns:
                    try:
                        correlation_price_oscillator = float(data['close'].corr(data[primary_indicator]))
                        self.logger.debug(
                            f"Price-{primary_indicator} correlation: {correlation_price_oscillator:.3f}"
                        )
                    except Exception as e:
                        self.logger.debug(f"Failed to calculate price-{primary_indicator} correlation: {e}")
                        correlation_price_oscillator = None
                else:
                    # Fallback: use generic oscillator detection (if context missing)
                    fallback_col = self._find_any_oscillator(data)
                    if fallback_col:
                        try:
                            correlation_price_oscillator = float(data['close'].corr(data[fallback_col]))
                            self.logger.debug(
                                f"Price-{fallback_col} correlation (fallback): {correlation_price_oscillator:.3f}"
                            )
                        except Exception as e:
                            self.logger.debug(f"Correlation calculation failed: {e}")
                            correlation_price_oscillator = None
            
            # Анализ пиков и впадин
            num_peaks = None
            num_troughs = None
            try:
                peaks, _ = find_peaks(data['high'].values, height=data['high'].mean())
                troughs, _ = find_peaks(-data['low'].values, height=-data['low'].mean())
                num_peaks = len(peaks)
                num_troughs = len(troughs)
            except:
                pass
            
            # Экскурсии от экстремумов и их положение во времени.
            #
            # Раньше здесь стояло `if zone_type == 'bull' ... elif == 'bear'`, и
            # три метрики из четырёх обнулялись в зависимости от ИМЕНИ типа зоны.
            # Ветвление не считало их по-разному — оно их отбрасывало: все четыре
            # величины выводятся из `end_price`, `max_price`, `min_price` и позиций
            # экстремумов, посчитанных выше безусловно, и определены для любой зоны
            # независимо от того, как она называется.
            #
            # Следствия были два. Зоны с любым другим словарём (`overbought`,
            # `regime_a`, …) не получали ни одной из четырёх метрик. А потребитель
            # тут же пытался потерю отменить: `hypothesis_testing` брал `abs()` от
            # обеих экскурсий «для унификации» — то есть сам возвращался к величине,
            # которую ветвление разделило.
            #
            # Какая из четырёх ИНТЕРЕСНА — решает потребитель, спрашивая полярность
            # типа зоны (`ZoneVocabulary.polarity_of`). Это знание о смысле, и его
            # место не здесь. Разбор: devref/gaps/zone_types/.
            drawdown_from_peak = (end_price / max_price) - 1 if max_price else None
            rally_from_trough = (end_price / min_price) - 1 if min_price else None

            peak_idx = data['high'].idxmax()
            peak_time_ratio = data.index.get_loc(peak_idx) / len(data)

            trough_idx = data['low'].idxmin()
            trough_time_ratio = data.index.get_loc(trough_idx) / len(data)
            
            # Метаданные (универсальные)
            metadata = {
                'data_points': len(data),
                'start_timestamp': str(data.index[0]) if hasattr(data.index[0], '__str__') else None,
                'end_timestamp': str(data.index[-1]) if hasattr(data.index[-1], '__str__') else None,
                'max_price': max_price,
                'min_price': min_price,
                'price_range': max_price - min_price
            }
            
            # Статистика по объявленным ролям индикатора — только по тем, которые
            # он действительно объявил и которые есть в кадре. Раньше блок
            # включался по наличию колонок с именами `macd` и `macd_hist`, то
            # есть по угадыванию строки: с любым другим индикатором он молча не
            # срабатывал, а с чужой колонкой по имени `macd` (её несёт выгрузка
            # TradingView) срабатывал на данных, которые считал не он.
            if column_schema:
                for role in ('line', 'hist'):
                    column = column_schema.column(role)
                    if not column or column not in data.columns:
                        continue
                    series = data[column]
                    # Ключ — **роль**, а не имя одного индикатора: `max_macd` на
                    # зонах RSI означал бы то же самое, что и на MACD, но врал бы
                    # именем. Форма единая с `oscillator_*` ниже: раньше три ключа
                    # шли как `max_X`/`min_X`/`avg_X`, а четвёртый — как `X_std`.
                    metadata.update({
                        f'{role}_max': float(series.max()),
                        f'{role}_min': float(series.min()),
                        f'{role}_avg': float(series.mean()),
                        f'{role}_std': float(series.std()),
                    })
            
            # v2.1: Generic oscillator metadata (UNIVERSAL - use primary_indicator)
            if primary_indicator and primary_indicator in data.columns:
                # Add generic oscillator statistics to metadata
                metadata.update({
                    'oscillator_name': primary_indicator,
                    'oscillator_max': float(data[primary_indicator].max()),
                    'oscillator_min': float(data[primary_indicator].min()),
                    'oscillator_avg': float(data[primary_indicator].mean()),
                    'oscillator_std': float(data[primary_indicator].std()),
                })
                
                # Здесь стояли алиасы «для обратной совместимости»: те же четыре
                # числа под именами `hist_max`/`rsi_max`/`ao_max` рядом с
                # `oscillator_max`, выбираемые по подстроке в имени колонки.
                # Убраны. Во-первых, их не читал никто — проверено по всему
                # дереву, кроме истории. Во-вторых, выбор по подстроке ошибочен
                # сам по себе: `'ao' in name.lower()` истинно для любой колонки,
                # где встречается эта пара букв. В-третьих, совместимость не с
                # кем обеспечивать — внешних пользователей у проекта нет, и это
                # зафиксированное решение, а не недосмотр. Универсальные
                # `oscillator_*` остаются и говорят то же самое без угадывания.

            if 'atr' in data.columns:
                metadata.update({
                    'atr_start': float(data['atr'].iloc[0]),
                    'atr_end': float(data['atr'].iloc[-1]),
                    'avg_atr': float(data['atr'].mean())
                })
            
            # Calculate swing metrics using strategy (if available)
            if self.swing_strategy is not None:
                swing_context = zone_info.get('swing_context')

                # Pre-set calculation mode for logging and metadata consistency.
                if swing_context is not None:
                    metadata['swing_calculation_mode'] = 'global'
                else:
                    metadata['swing_calculation_mode'] = 'per_zone'

                try:
                    if swing_context is not None:
                        temp_zone = ZoneInfo(
                            zone_id=zone_info['zone_id'],
                            type=zone_info['type'],
                            start_idx=zone_info['start_idx'],
                            end_idx=zone_info['end_idx'],
                            start_time=zone_info['start_time'],
                            end_time=zone_info['end_time'],
                            duration=zone_info['duration'],
                            data=data,
                            indicator_context=zone_info.get('indicator_context'),
                            swing_context=swing_context,
                        )

                        swing_metrics = self.swing_strategy.aggregate_for_zone(
                            temp_zone,
                            swing_context,
                        )
                        metadata['swing_metrics'] = swing_metrics.to_dict()
                        self.logger.debug(
                            "Swing metrics aggregated from global context: %s rallies, %s drops, ratio=%.2f",
                            swing_metrics.rally_count,
                            swing_metrics.drop_count,
                            swing_metrics.rally_to_drop_ratio,
                        )
                    else:
                        swing_metrics = self.swing_strategy.calculate(data)
                        metadata['swing_metrics'] = swing_metrics.to_dict()
                        self.logger.debug(
                            "Swing metrics calculated in per_zone mode: %s rallies, %s drops, ratio=%.2f",
                            swing_metrics.rally_count,
                            swing_metrics.drop_count,
                            swing_metrics.rally_to_drop_ratio,
                        )
                except Exception as e:
                    self.logger.warning(f"Failed to calculate swing metrics: {e}")
                    metadata['swing_metrics'] = None
            
            # Calculate shape metrics using strategy (v2.1 - with indicator_col parameter)
            if self.shape_strategy is not None:
                try:
                    # Use primary_indicator from context if available
                    if primary_indicator and primary_indicator in data.columns:
                        shape_metrics = self.shape_strategy.calculate(data, indicator_col=primary_indicator)
                        metadata['shape_metrics'] = shape_metrics.to_dict()
                        self.logger.debug(
                            f"Shape metrics calculated for '{primary_indicator}': "
                            f"skewness={shape_metrics.hist_skewness:.2f}, kurtosis={shape_metrics.hist_kurtosis:.2f}"
                        )
                    else:
                        # Fallback: try to find ANY oscillator column (universal, no hardcoded names)
                        fallback_col = self._find_any_oscillator(data)
                        if fallback_col:
                            shape_metrics = self.shape_strategy.calculate(data, indicator_col=fallback_col)
                            metadata['shape_metrics'] = shape_metrics.to_dict()
                            self.logger.debug(f"Shape analysis used fallback column: {fallback_col}")
                        else:
                            metadata['shape_metrics'] = None
                            self.logger.debug("No suitable column for shape analysis")
                except Exception as e:
                    self.logger.debug(f"Shape metrics not available: {e}")
                    metadata['shape_metrics'] = None
            
            # Calculate divergence metrics using strategy (v2.1 - with indicator parameters)
            if self.divergence_strategy is not None:
                try:
                    # Use primary_indicator and signal_line from context if available
                    if primary_indicator and primary_indicator in data.columns:
                        divergence_metrics = self.divergence_strategy.calculate_divergence(
                            data,
                            indicator_col=primary_indicator,
                            indicator_line_col=signal_line if signal_line and signal_line in data.columns else None
                        )
                        metadata['divergence_metrics'] = divergence_metrics.to_dict()
                        self.logger.debug(
                            f"Divergence metrics calculated for '{primary_indicator}': "
                            f"type={divergence_metrics.divergence_type}, count={divergence_metrics.divergence_count}"
                        )
                    else:
                        # Fallback: try to find ANY oscillator column
                        fallback_col = self._find_any_oscillator(data)
                        if fallback_col:
                            divergence_metrics = self.divergence_strategy.calculate_divergence(
                                data, indicator_col=fallback_col
                            )
                            metadata['divergence_metrics'] = divergence_metrics.to_dict()
                            self.logger.debug(f"Divergence analysis used fallback column: {fallback_col}")
                        else:
                            metadata['divergence_metrics'] = None
                            self.logger.debug("No suitable column for divergence analysis")
                except Exception as e:
                    self.logger.debug(f"Divergence metrics not available: {e}")
                    metadata['divergence_metrics'] = None
            
            # Calculate volatility metrics using strategy (if available)
            if self.volatility_strategy is not None:
                try:
                    volatility_metrics = self.volatility_strategy.calculate_volatility(data)
                    metadata['volatility_metrics'] = volatility_metrics.to_dict()
                    self.logger.debug(
                        f"Volatility metrics calculated: score={volatility_metrics.volatility_score:.2f}, "
                        f"regime={volatility_metrics.volatility_regime}, "
                        f"bb_width={volatility_metrics.bollinger_width_pct:.2f}%"
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to calculate volatility metrics: {e}")
                    metadata['volatility_metrics'] = None
            
            # Calculate volume metrics using strategy (v2.1 - with indicator_col parameter)
            if self.volume_strategy is not None and 'volume' in data.columns:
                try:
                    # Calculate baseline volume (average of previous bars, if available)
                    # For now, we don't have access to pre-zone data, so baseline_volume=None
                    # Strategy will handle this gracefully
                    
                    # v2.1: Pass indicator_col for volume-indicator correlation
                    volume_metrics = self.volume_strategy.calculate_volume(
                        data, 
                        baseline_volume=None,
                        indicator_col=primary_indicator  # From context (or None)
                    )
                    metadata['volume_metrics'] = volume_metrics.to_dict()
                    self.logger.debug(
                        f"Volume metrics calculated: avg={volume_metrics.avg_volume_zone}"
                    )
                except Exception as e:
                    self.logger.debug(f"Volume metrics not available: {e}")
                    metadata['volume_metrics'] = None
            
            return ZoneFeatures(
                zone_id=zone_id,
                zone_type=zone_type,
                duration=len(data),
                start_price=start_price,
                end_price=end_price,
                price_return=price_return,
                line_amplitude=line_amplitude,
                oscillator_amplitude=oscillator_amplitude,
                price_range_pct=price_range_pct,
                atr_normalized_return=atr_normalized_return,
                correlation_price_oscillator=correlation_price_oscillator,
                num_peaks=num_peaks,
                num_troughs=num_troughs,
                drawdown_from_peak=drawdown_from_peak,
                rally_from_trough=rally_from_trough,
                peak_time_ratio=peak_time_ratio,
                trough_time_ratio=trough_time_ratio,
                oscillator_slope=oscillator_slope,
                # int(), а не как есть: детекторы отдают numpy-целые, а `to_dict()`
                # пропускает только питоновские скаляры — иначе границы молча
                # выпали бы из сериализованных фич, там где они и нужны.
                start_idx=_as_optional_int(zone_info.get('start_idx')),
                end_idx=_as_optional_int(zone_info.get('end_idx')),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Failed to extract zone features: {e}")
            raise AnalysisError(f"Failed to extract zone features: {e}")
    
    def extract_all_zones_features(
        self,
        zones: List,
        column_schema: Optional["ColumnSchema"] = None,
    ) -> List[ZoneFeatures]:
        """
        Извлечение признаков для списка зон (новая архитектура).
        
        Args:
            zones: Список ZoneInfo объектов
            column_schema: Отображение ``(индикатор, роль) → колонка``, если оно
                известно. Метрики, которым нужен конкретный выход индикатора
                (например амплитуда его **линии**), спрашивают роль, а не
                угадывают имя колонки по подстроке.
        
        Returns:
            List[ZoneFeatures] длиной **ровно** ``len(zones)``: элемент ``i``
            соответствует ``zones[i]``, а ``None`` на его месте означает, что
            измерить зону не удалось.

            Раньше метод возвращал только удачи, из-за чего вызывающий
            (:meth:`UniversalZoneAnalyzer.analyze_zones`) сшивал зоны с
            признаками через ``zip`` **по позиции** — и после первой же неудачи
            каждая следующая зона получала признаки чужой. Это не гипотеза:
            при ``min_duration=1`` на встроенном сэмпле 66 зон из 83 несли
            чужие числа, и результат при этом выглядел совершенно нормально.
            Выравнивание по позиции — свойство контракта, а не забота
            вызывающего.

        Example:
            from bquant.analysis.zones.models import ZoneInfo

            # zones - это List[ZoneInfo] из detection стратегии
            analyzer = ZoneFeaturesAnalyzer()
            features = analyzer.extract_all_zones_features(zones)
            measured = [f for f in features if f is not None]
        """
        features_list: List[Optional[ZoneFeatures]] = []
        failures: List[str] = []

        for zone in zones:
            try:
                # Конвертируем ZoneInfo в формат для extract_zone_features
                zone_dict = zone.to_analyzer_format()
                if column_schema is not None:
                    zone_dict['column_schema'] = column_schema
                features_list.append(self.extract_zone_features(zone_dict))
            except Exception as e:
                features_list.append(None)
                failures.append(f"{zone.zone_id}: {e}")

        if failures:
            self.logger.warning(
                "Could not measure %d of %d zones; they are reported as "
                "unmeasured rather than dropped. First few: %s",
                len(failures), len(zones), "; ".join(failures[:3]),
            )

        self.logger.info(
            f"Extracted features for {len(zones) - len(failures)}/{len(zones)} zones"
        )

        return features_list
    
    def analyze_zones_distribution(self, zones_features: List[Union[ZoneFeatures, Dict[str, Any]]]) -> AnalysisResult:
        """
        Анализ распределения характеристик зон.
        
        Args:
            zones_features: Список объектов ZoneFeatures или словарей
        
        Returns:
            AnalysisResult с анализом распределения
        """
        try:
            self.logger.info(f"Analyzing distribution of {len(zones_features)} zones")
            
            if not zones_features:
                raise AnalysisError("No zones features provided")
            
            # Конвертируем в DataFrame
            features_dicts = []
            for zone in zones_features:
                if isinstance(zone, ZoneFeatures):
                    features_dicts.append(zone.to_dict())
                elif isinstance(zone, dict):
                    features_dicts.append(zone)
                else:
                    raise AnalysisError(f"Invalid zone features type: {type(zone)}")
            
            df_features = pd.DataFrame(features_dicts)
            
            # Разделяем по типу зон
            bull_zones = df_features[df_features['zone_type'] == 'bull']
            bear_zones = df_features[df_features['zone_type'] == 'bear']
            
            # Общая статистика
            total_stats = {
                'total_zones': len(df_features),
                'bull_zones_count': len(bull_zones),
                'bear_zones_count': len(bear_zones),
                'bull_ratio': len(bull_zones) / len(df_features) if len(df_features) > 0 else 0,
                'bear_ratio': len(bear_zones) / len(df_features) if len(df_features) > 0 else 0
            }
            
            # Статистика по длительности
            duration_stats = self._calculate_distribution_stats(df_features, bull_zones, bear_zones, 'duration')
            
            # Статистика по доходности
            return_stats = self._calculate_distribution_stats(df_features, bull_zones, bear_zones, 'price_return')
            
            # Статистика по амплитуде MACD (только если колонка есть)
            line_amplitude_stats = None
            if 'line_amplitude' in df_features.columns and df_features['line_amplitude'].notna().any():
                line_amplitude_stats = self._calculate_distribution_stats(df_features, bull_zones, bear_zones, 'line_amplitude')
            
            # Статистика по амплитуде гистограммы (только если колонка есть)
            oscillator_amplitude_stats = None
            if 'oscillator_amplitude' in df_features.columns and df_features['oscillator_amplitude'].notna().any():
                oscillator_amplitude_stats = self._calculate_distribution_stats(df_features, bull_zones, bear_zones, 'oscillator_amplitude')
            
            # Дополнительные метрики
            additional_stats = {}
            
            # Корреляции
            if 'correlation_price_oscillator' in df_features.columns:
                correlation_data = df_features['correlation_price_oscillator'].dropna()
                if len(correlation_data) > 0:
                    additional_stats['price_hist_correlation'] = {
                        'mean': float(correlation_data.mean()),
                        'std': float(correlation_data.std()),
                        'positive_correlations': len(correlation_data[correlation_data > 0]),
                        'negative_correlations': len(correlation_data[correlation_data < 0]),
                        'strong_correlations': len(correlation_data[abs(correlation_data) > 0.7])
                    }
            
            # Пики и впадины
            if 'num_peaks' in df_features.columns and 'num_troughs' in df_features.columns:
                peaks_data = df_features['num_peaks'].dropna()
                troughs_data = df_features['num_troughs'].dropna()
                
                if len(peaks_data) > 0 and len(troughs_data) > 0:
                    additional_stats['peaks_troughs'] = {
                        'avg_peaks_per_zone': float(peaks_data.mean()),
                        'avg_troughs_per_zone': float(troughs_data.mean()),
                        'zones_with_peaks': len(peaks_data[peaks_data > 0]),
                        'zones_with_troughs': len(troughs_data[troughs_data > 0])
                    }
            
            # Объединяем все результаты
            results = {
                'total_statistics': total_stats,
                'duration_distribution': duration_stats,
                'return_distribution': return_stats,
                'line_amplitude_distribution': line_amplitude_stats,
                'oscillator_amplitude_distribution': oscillator_amplitude_stats,
                'additional_metrics': additional_stats
            }
            
            metadata = {
                'analyzer': 'ZoneFeaturesAnalyzer',
                'analysis_method': 'zones_distribution',
                'timestamp': datetime.now().isoformat()
            }
            
            return AnalysisResult(
                analysis_type='zones_distribution',
                results=results,
                data_size=len(zones_features),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Zones distribution analysis failed: {e}")
            raise AnalysisError(f"Zones distribution analysis failed: {e}")
    
    def _calculate_distribution_stats(self, df_all: pd.DataFrame, 
                                    df_bull: pd.DataFrame, 
                                    df_bear: pd.DataFrame, 
                                    column: str) -> Dict[str, Any]:
        """
        Вычисление статистики распределения для конкретной характеристики.
        
        Args:
            df_all: Все зоны
            df_bull: Бычьи зоны
            df_bear: Медвежьи зоны
            column: Название колонки для анализа
        
        Returns:
            Словарь со статистикой распределения
        """
        stats_dict = {}
        
        # Общая статистика
        if column in df_all.columns:
            all_data = df_all[column].dropna()
            if len(all_data) > 0:
                stats_dict['overall'] = {
                    'mean': float(all_data.mean()),
                    'median': float(all_data.median()),
                    'std': float(all_data.std()),
                    'min': float(all_data.min()),
                    'max': float(all_data.max()),
                    'q25': float(all_data.quantile(0.25)),
                    'q75': float(all_data.quantile(0.75)),
                    'skewness': float(all_data.skew()),
                    'kurtosis': float(all_data.kurtosis())
                }
        
        # Статистика для бычьих зон
        if column in df_bull.columns and len(df_bull) > 0:
            bull_data = df_bull[column].dropna()
            if len(bull_data) > 0:
                stats_dict['bull'] = {
                    'mean': float(bull_data.mean()),
                    'median': float(bull_data.median()),
                    'std': float(bull_data.std()),
                    'min': float(bull_data.min()),
                    'max': float(bull_data.max()),
                    'count': len(bull_data)
                }
        
        # Статистика для медвежьих зон
        if column in df_bear.columns and len(df_bear) > 0:
            bear_data = df_bear[column].dropna()
            if len(bear_data) > 0:
                stats_dict['bear'] = {
                    'mean': float(bear_data.mean()),
                    'median': float(bear_data.median()),
                    'std': float(bear_data.std()),
                    'min': float(bear_data.min()),
                    'max': float(bear_data.max()),
                    'count': len(bear_data)
                }
        
        # Сравнительная статистика
        if ('bull' in stats_dict and 'bear' in stats_dict and 
            column in df_bull.columns and column in df_bear.columns):
            
            bull_data = df_bull[column].dropna()
            bear_data = df_bear[column].dropna()
            
            if len(bull_data) > 1 and len(bear_data) > 1:
                try:
                    # t-тест для сравнения средних
                    t_stat, p_value = stats.ttest_ind(bull_data, bear_data)
                    
                    stats_dict['comparison'] = {
                        't_statistic': float(t_stat),
                        'p_value': float(p_value),
                        'significant_difference': p_value < 0.05,
                        'bull_vs_bear_ratio': stats_dict['bull']['mean'] / stats_dict['bear']['mean'] if stats_dict['bear']['mean'] != 0 else None
                    }
                except Exception as e:
                    self.logger.warning(f"Failed to calculate comparison stats for {column}: {e}")
        
        return stats_dict
    
    def get_zone_features_summary(self, zones_features: List[Union[ZoneFeatures, Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Получение краткой сводки по характеристикам зон.
        
        Args:
            zones_features: Список объектов ZoneFeatures или словарей
        
        Returns:
            Словарь с краткой сводкой
        """
        try:
            if not zones_features:
                return {'error': 'No zones features provided'}
            
            # Конвертируем в DataFrame
            features_dicts = []
            for zone in zones_features:
                if isinstance(zone, ZoneFeatures):
                    features_dicts.append(zone.to_dict())
                elif isinstance(zone, dict):
                    features_dicts.append(zone)
            
            df_features = pd.DataFrame(features_dicts)
            
            bull_zones = df_features[df_features['zone_type'] == 'bull']
            bear_zones = df_features[df_features['zone_type'] == 'bear']
            
            summary = {
                'total_zones': len(df_features),
                'bull_zones': len(bull_zones),
                'bear_zones': len(bear_zones),
                'avg_duration': float(df_features['duration'].mean()) if 'duration' in df_features.columns else None,
                'avg_return': float(df_features['price_return'].mean()) if 'price_return' in df_features.columns else None,
                'positive_returns': len(df_features[df_features['price_return'] > 0]) if 'price_return' in df_features.columns else None,
                'negative_returns': len(df_features[df_features['price_return'] < 0]) if 'price_return' in df_features.columns else None
            }
            
            if len(bull_zones) > 0:
                summary['bull_avg_duration'] = float(bull_zones['duration'].mean()) if 'duration' in bull_zones.columns else None
                summary['bull_avg_return'] = float(bull_zones['price_return'].mean()) if 'price_return' in bull_zones.columns else None
            
            if len(bear_zones) > 0:
                summary['bear_avg_duration'] = float(bear_zones['duration'].mean()) if 'duration' in bear_zones.columns else None
                summary['bear_avg_return'] = float(bear_zones['price_return'].mean()) if 'price_return' in bear_zones.columns else None
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get zone features summary: {e}")
            return {'error': str(e)}
    
    def _find_any_oscillator(self, data: pd.DataFrame) -> Optional[str]:
        """
        Find first suitable oscillator column (UNIVERSAL - no hardcoded names).
        
        Strategy (v2.1):
        1. Get all numeric columns
        2. Exclude OHLCV and known auxiliary columns (generic exclusion)
        3. Return first remaining column
        
        This is TRULY UNIVERSAL - doesn't know about specific indicators!
        No hardcoded patterns like 'RSI_', 'MACD_', 'AO_'
        
        Returns:
            str: First suitable oscillator column, or None if not found
        """
        # Generic exclusion list (NOT indicator-specific!)
        excluded = {
            # Price data
            'open', 'high', 'low', 'close', 'volume',
            # Time data
            'time', 'timestamp', 'date', 'datetime',
            # Auxiliary (not oscillators)
            'atr', 'true_range', 'tr',
            # Index-like
            'index', 'id', 'zone_id'
        }
        
        # Get numeric columns
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        
        # Filter out excluded (case-insensitive)
        candidates = [
            col for col in numeric_cols 
            if col.lower() not in excluded
        ]
        
        if candidates:
            selected = candidates[0]
            self.logger.debug(
                f"Generic oscillator detection: selected '{selected}' from {len(candidates)} candidates"
            )
            return selected
        
        return None


# Удобные функции для быстрого использования
def analyze_zones_distribution(
    zones_features: List[Union[ZoneFeatures, Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Анализ распределения зон.

    Args:
        zones_features: Список характеристик зон

    Returns:
        Словарь с результатами анализа
    """
    analyzer = ZoneFeaturesAnalyzer()
    analysis_result = analyzer.analyze_zones_distribution(zones_features)
    return analysis_result.results


# Экспорт
__all__ = [
    'ZoneFeatures',
    'ZoneFeaturesAnalyzer',
    'analyze_zones_distribution'
]
