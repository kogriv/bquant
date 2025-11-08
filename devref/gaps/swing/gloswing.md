# Глобальный расчёт свингов и последующее сопоставление с зонами

## Краткое описание проблемы

Сейчас пайплайн `ZoneAnalysisPipeline` рассчитывает свинговые метрики отдельно для каждой зоны, передавая стратегиям (Find Peaks, Pivot Points, ZigZag) локальные фреймы `zone.data`. Такой подход приводит к искажению анализа: если границы зоны разрезают более крупный трендовый ход, локальные алгоритмы не видят свинги целиком и возвращают неполные либо пустые метрики. В сравнении с глобальным ZigZag, построенным на всём ряде котировок, результат получается беднее и менее надёжен.

**Примеры искажений**:
1. **Потеря пивотов на границах зон**: Свинг-точка перед началом зоны или после её окончания не учитывается, хотя она критична для понимания внутренней динамики.
2. **Ложные свинги из-за малого контекста**: На узких зонах (5-10 баров) алгоритмы детектируют шум как значимые свинги.
3. **Несопоставимость метрик между зонами**: Разные длины зон → разные пороги детекции → статистически несравнимые результаты.

## Архитектурный разбор текущего решения

### 1. Пайплайн анализа зон
```
ZoneAnalysisPipeline.build()
  ├─> _run_without_cache()
  │     ├─> prepare_dataframe()
  │     ├─> detect_zones()
  │     │      └─> ZoneDetector.detect()  # выделение зон на всём диапазоне данных
  │     └─> UniversalZoneAnalyzer(...)
  │             └─> ZoneFeaturesAnalyzer.extract_all_zones_features(zones)
  │                    └─> swing_strategy.calculate(zone.data)
```
* Детектор зон работает на глобальном DataFrame, но на этапе упаковки результатов каждая зона получает собственный срез `df.iloc[start_idx:end_idx+1]`, который складывается в `ZoneInfo.data`.
* `UniversalZoneAnalyzer`/`ZoneFeaturesAnalyzer` видят только локальные данные зоны, потому что `zone.data` передаётся напрямую в свинговую стратегию.

### 2. Стратегии свингов
```python
class ZigZagSwingStrategy:
    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        pivot_series = ta.zigzag(..., zone_data)
        pivots = _collect_pivots(pivot_series)
        return _calculate_swing_metrics(pivots)
```
* Стратегия полностью изолирована: она строит индикатор, извлекает пивоты и агрегирует метрики, не зная о глобальном контексте.
* Аналогичный паттерн повторяется в `FindPeaksSwingStrategy` и `PivotPointsSwingStrategy`.

### 3. Побочные эффекты
* Зоны, начинающиеся/заканчивающиеся внутри большого движения, теряют внешние пивоты и часто дают `num_swings = 0`.
* Отчёты (например, `research/notebooks/05_case_study_zone_consistency.py`) показывают сильный разброс в покрытии свингами:
  - `find_peaks`: 7/37 зон (18.9%) имеют свинги
  - `pivot_points`: 3/37 зон (8.1%)
  - `zigzag`: 23/37 зон (62.2%)
* Порог «auto» (`with_auto_swing_thresholds(True)`) пересчитывается на локальном срезе, из-за чего итог ещё больше зависит от ширины зоны.

## Предлагаемое решение: глобальный расчёт и нарезка на зоны

### Общая идея
* Один раз посчитать свинговые пивоты на глобальном DataFrame, затем для каждой зоны извлекать соответствующие точки и агрегировать метрики.
* Сохранить опцию текущего поведения («per_zone»), добавив переключатель конфигурации.

---

## 1. Новые модели данных

### 1.1. `SwingPoint` — структурированная точка свинга

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class SwingPoint:
    """
    Точка свинга на глобальном уровне.

    Attributes:
        point_id: Уникальный идентификатор точки в последовательности
        timestamp: Временная метка (значение индекса DataFrame)
        index: Позиция в полном датасете (integer location)
        price: Цена в точке свинга
        swing_type: Тип свинга ('peak' | 'trough')
        amplitude_to_next: Процентное изменение до следующей точки свинга
        duration_to_next: Количество баров до следующей точки свинга
        strategy_name: Имя стратегии, которая детектировала свинг
        strategy_params: Параметры стратегии для трассируемости

    Advantages:
        - Богатая структура данных для дополнительного анализа
        - Хранит метаданные стратегии → полная трассируемость
        - Можно визуализировать независимо от зон
        - Расширяемость через дополнительные поля
    """
    point_id: int
    timestamp: datetime
    index: int  # Position in full dataset
    price: float
    swing_type: str  # 'peak' | 'trough'
    amplitude_to_next: Optional[float] = None  # % change to next swing
    duration_to_next: Optional[int] = None     # bars to next swing

    # Метаданные алгоритма
    strategy_name: str = ''
    strategy_params: Dict[str, Any] = None

    def __post_init__(self):
        if self.strategy_params is None:
            self.strategy_params = {}
```

### 1.2. `SwingContext` — глобальный контекст свингов

```python
import numpy as np
from bisect import bisect_left, bisect_right

@dataclass
class SwingContext:
    """
    Глобальный контекст свингов для всего датасета.

    Attributes:
        swing_points: Список SwingPoint объектов в хронологическом порядке
        indices: Отсортированный массив индексов для быстрой нарезки (bisect)
        full_data_length: Длина исходного датасета
        strategy_name: Имя стратегии расчёта
        strategy_params: Параметры стратегии

    Key Method:
        slice(start_idx, end_idx) — нарезка с захватом соседних пивотов
    """
    swing_points: List[SwingPoint]
    indices: np.ndarray  # Sorted indices for bisect performance
    full_data_length: int
    strategy_name: str
    strategy_params: Dict[str, Any]

    def slice(self, start_idx: int, end_idx: int) -> List[SwingPoint]:
        """
        Нарезка пивотов с захватом соседних точек для восстановления амплитуд.

        Алгоритм:
        1. Найти первый pivot >= start_idx
        2. Найти первый pivot > end_idx
        3. Захватить pivot слева (left-1) и справа (right) для полных свингов

        Example:
            Global pivots: P0────P1────P2────P3────P4────P5
            Zone A:              |──────────|
                               start_idx  end_idx

            Without neighbors: [P2, P3]         ← Потеряли P1→P2 и P3→P4 свинги!
            With neighbors:    [P1, P2, P3, P4] ✅ Полные свинги

        Args:
            start_idx: Начальный индекс зоны (inclusive)
            end_idx: Конечный индекс зоны (inclusive)

        Returns:
            List[SwingPoint] с захватом соседних точек
        """
        if len(self.swing_points) == 0:
            return []

        # Бинарный поиск границ
        left = bisect_left(self.indices, start_idx)
        right = bisect_right(self.indices, end_idx)

        # Захват соседних пивотов
        left_with_neighbor = max(0, left - 1)
        right_with_neighbor = min(len(self.swing_points), right + 1)

        return self.swing_points[left_with_neighbor:right_with_neighbor]

    def get_swings_for_zone(self, zone: 'ZoneInfo') -> List[SwingPoint]:
        """
        Удобный метод для получения свингов зоны.

        Args:
            zone: ZoneInfo объект с start_idx и end_idx

        Returns:
            List[SwingPoint] внутри зоны (с соседними)
        """
        return self.slice(zone.start_idx, zone.end_idx)

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация для кэширования."""
        return {
            'swing_points': [
                {
                    'point_id': sp.point_id,
                    'timestamp': sp.timestamp.isoformat(),
                    'index': sp.index,
                    'price': sp.price,
                    'swing_type': sp.swing_type,
                    'amplitude_to_next': sp.amplitude_to_next,
                    'duration_to_next': sp.duration_to_next,
                    'strategy_name': sp.strategy_name,
                    'strategy_params': sp.strategy_params
                }
                for sp in self.swing_points
            ],
            'full_data_length': self.full_data_length,
            'strategy_name': self.strategy_name,
            'strategy_params': self.strategy_params
        }
```

### 1.3. Обновление `ZoneInfo`

```python
# В bquant/analysis/zones/models.py

@dataclass
class ZoneInfo:
    """
    Информация о зоне (универсальная структура).

    NEW FIELD:
        swing_context: Optional[SwingContext] - ссылка на глобальный контекст свингов
    """
    zone_id: int
    type: str
    start_idx: int
    end_idx: int
    start_time: datetime
    end_time: datetime
    duration: int
    data: pd.DataFrame
    features: Optional[Dict[str, Any]] = None
    indicator_context: Optional[Dict[str, Any]] = None
    swing_context: Optional[SwingContext] = None  # НОВОЕ ПОЛЕ

    def get_zone_swings(self) -> List[SwingPoint]:
        """
        Получить свинги внутри зоны из глобального контекста.

        Удобный API для доступа к свингам без прямой работы с контекстом.

        Returns:
            List[SwingPoint] внутри зоны (пустой список если контекст отсутствует)

        Example:
            for zone in result.zones:
                swings = zone.get_zone_swings()
                print(f"Zone {zone.zone_id}: {len(swings)} swings")
        """
        if self.swing_context is None:
            return []
        return self.swing_context.get_swings_for_zone(self)

    def to_analyzer_format(self) -> Dict[str, Any]:
        """
        Формат для передачи в анализаторы.

        UPDATED: Добавлен swing_context в выходной словарь
        """
        return {
            'zone_id': self.zone_id,
            'type': self.type,
            'start_idx': self.start_idx,
            'end_idx': self.end_idx,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'data': self.data,
            'indicator_context': self.indicator_context,
            'swing_context': self.swing_context,  # НОВОЕ: передаём контекст
            **(self.features or {})
        }
```

---

## 2. Расширение конфигурации

### 2.1. Добавление `swing_scope` в `ZoneAnalysisConfig`

```python
# В bquant/analysis/zones/pipeline.py

from typing import Literal

@dataclass
class ZoneAnalysisConfig:
    """
    Конфигурация анализа зон.

    NEW FIELD:
        swing_scope: Режим расчёта свингов
            - "per_zone" (default): Изолированный расчёт для каждой зоны (legacy)
            - "global": Глобальный расчёт на всём датасете с последующей нарезкой
    """
    # ... existing fields ...

    swing_scope: Literal["per_zone", "global"] = "per_zone"

    def to_cache_key(self) -> str:
        """
        Генерация ключа кэша.

        UPDATED: Включает swing_scope для разделения режимов кэширования
        """
        # ... existing cache key generation ...
        key_parts.append(f"swing_scope={self.swing_scope}")
        # ...
```

**Обоснование**:
- ✅ Настройка сериализуется вместе с конфигом
- ✅ Участвует в кэш-ключах → результаты разных режимов не смешиваются
- ✅ Явная часть конфигурации, доступная для инспекции

---

## 3. Обновление API стратегий свингов

### 3.1. Новый протокол `SwingCalculationStrategy`

```python
# В bquant/analysis/zones/strategies/base.py

from typing import Protocol, runtime_checkable

@runtime_checkable
class SwingCalculationStrategy(Protocol):
    """
    Протокол для стратегий расчёта свингов.

    Стратегия должна поддерживать два режима:
    1. Глобальный расчёт: calculate_global() → SwingContext
    2. Агрегация для зоны: aggregate_for_zone() → SwingMetrics
    3. Legacy расчёт: calculate() → SwingMetrics (для обратной совместимости)
    """

    def calculate_global(self, full_data: pd.DataFrame) -> SwingContext:
        """
        Рассчитать свинги на ВСЁМ датасете.

        PRIORITY METHOD: Используется в режиме swing_scope="global"

        Args:
            full_data: Полный DataFrame с OHLCV + индикаторами

        Returns:
            SwingContext с глобальными SwingPoint объектами

        Raises:
            ValueError: Если данных недостаточно для расчёта
            RuntimeError: При ошибках алгоритма

        Example:
            strategy = ZigZagSwingStrategy(legs=10, deviation=0.05)
            context = strategy.calculate_global(full_data)
            print(f"Detected {len(context.swing_points)} global swing points")
        """
        ...

    def aggregate_for_zone(self, zone: ZoneInfo, context: SwingContext) -> SwingMetrics:
        """
        Агрегировать глобальные свинги в метрики для зоны.

        PRIORITY METHOD: Используется в режиме swing_scope="global"

        Process:
        1. Извлечь свинги внутри зоны через context.get_swings_for_zone(zone)
        2. Разделить на rallies (восходящие) и drops (нисходящие)
        3. Агрегировать в SwingMetrics

        Args:
            zone: Информация о зоне
            context: Глобальный контекст свингов

        Returns:
            SwingMetrics с агрегированными метриками

        Example:
            zone_swings = context.get_swings_for_zone(zone)
            metrics = strategy.aggregate_for_zone(zone, context)
        """
        ...

    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        """
        Legacy: расчёт для изолированной зоны.

        DEPRECATED (но сохранён для обратной совместимости)

        Используется в режиме swing_scope="per_zone" или как fallback
        при ошибках глобального расчёта.

        Args:
            zone_data: DataFrame только для этой зоны

        Returns:
            SwingMetrics с локально рассчитанными метриками
        """
        ...

    def config_hash(self) -> Dict[str, Any]:
        """
        Возвращает параметры конфигурации для кэш-ключей.

        Returns:
            Dict с параметрами стратегии
        """
        ...
```

### 3.2. Пример реализации для `ZigZagSwingStrategy`

```python
# В bquant/analysis/zones/strategies/swing/zigzag.py

@StrategyRegistry.register_swing_strategy('zigzag')
@dataclass
class ZigZagSwingStrategy:
    """
    Swing detection using pandas-ta ZigZag algorithm.

    UPDATED: Поддержка глобального режима расчёта
    """
    legs: int = 10
    deviation: float = 0.05  # 5% minimum movement

    def calculate_global(self, full_data: pd.DataFrame) -> SwingContext:
        """
        Рассчитать ZigZag на всём датасете.

        Algorithm:
        1. Применить pandas-ta ZigZag к полным данным
        2. Извлечь все точки пивотов
        3. Определить типы (peak/trough) по направлению изменения
        4. Рассчитать амплитуды и длительности между соседними точками
        5. Упаковать в SwingContext
        """
        from .....indicators import LibraryManager
        from .....core.logging_config import get_logger

        logger = get_logger(__name__)

        # Validate input
        if len(full_data) < self.legs * 2:
            raise ValueError(
                f"Insufficient data for ZigZag: {len(full_data)} bars < {self.legs * 2}"
            )

        # 1. Calculate ZigZag indicator
        zigzag = LibraryManager.create_indicator(
            'pandas_ta',
            'zigzag',
            legs=self.legs,
            deviation=self.deviation
        )
        result = zigzag.calculate(full_data)

        # 2. Extract swing values
        if result.data.shape[1] < 2:
            logger.warning("ZigZag returned insufficient columns, no swings detected")
            return SwingContext(
                swing_points=[],
                indices=np.array([]),
                full_data_length=len(full_data),
                strategy_name='zigzag',
                strategy_params={'legs': self.legs, 'deviation': self.deviation}
            )

        swing_values = result.data.iloc[:, 1]  # Column with prices
        swing_points_series = swing_values.dropna()

        if len(swing_points_series) < 2:
            logger.warning(f"ZigZag detected only {len(swing_points_series)} points")
            return SwingContext(
                swing_points=[],
                indices=np.array([]),
                full_data_length=len(full_data),
                strategy_name='zigzag',
                strategy_params={'legs': self.legs, 'deviation': self.deviation}
            )

        # 3. Convert to SwingPoint objects
        swing_points = []
        indices = []

        for i, (timestamp, price) in enumerate(swing_points_series.items()):
            position = full_data.index.get_loc(timestamp)

            # Determine swing_type by price change direction
            if i > 0:
                prev_price = swing_points_series.iloc[i-1]
                swing_type = 'peak' if price > prev_price else 'trough'
            else:
                # First point: determine by next point
                if i < len(swing_points_series) - 1:
                    next_price = swing_points_series.iloc[i+1]
                    swing_type = 'trough' if next_price > price else 'peak'
                else:
                    swing_type = 'trough'  # Single point default

            # Calculate amplitude and duration to next point
            amplitude_to_next = None
            duration_to_next = None
            if i < len(swing_points_series) - 1:
                next_timestamp = swing_points_series.index[i + 1]
                next_price = swing_points_series.iloc[i + 1]
                next_position = full_data.index.get_loc(next_timestamp)

                amplitude_to_next = (next_price / price - 1) * 100
                duration_to_next = next_position - position

            swing_point = SwingPoint(
                point_id=i,
                timestamp=timestamp,
                index=position,
                price=float(price),
                swing_type=swing_type,
                amplitude_to_next=amplitude_to_next,
                duration_to_next=duration_to_next,
                strategy_name='zigzag',
                strategy_params={'legs': self.legs, 'deviation': self.deviation}
            )

            swing_points.append(swing_point)
            indices.append(position)

        logger.info(f"ZigZag global: detected {len(swing_points)} swing points")

        return SwingContext(
            swing_points=swing_points,
            indices=np.array(indices),
            full_data_length=len(full_data),
            strategy_name='zigzag',
            strategy_params={'legs': self.legs, 'deviation': self.deviation}
        )

    def aggregate_for_zone(self, zone: ZoneInfo, context: SwingContext) -> SwingMetrics:
        """
        Агрегировать глобальные свинги для зоны.

        Process:
        1. Получить свинги внутри зоны (с соседними через slice)
        2. Разделить на rallies и drops
        3. Агрегировать метрики
        """
        from .....core.logging_config import get_logger
        logger = get_logger(__name__)

        # 1. Get swings for zone (with neighbors)
        zone_swings = context.get_swings_for_zone(zone)

        if len(zone_swings) < 2:
            logger.debug(
                f"Zone {zone.zone_id}: insufficient swings ({len(zone_swings)} points)"
            )
            return self._empty_metrics()

        # 2. Separate into rallies and drops
        rallies = []
        drops = []

        for i in range(len(zone_swings) - 1):
            curr = zone_swings[i]
            next_swing = zone_swings[i + 1]

            price_change_pct = (next_swing.price / curr.price - 1) * 100
            duration_bars = next_swing.index - curr.index

            if price_change_pct > 0:
                # Rally (up movement)
                rallies.append({
                    'amplitude_pct': price_change_pct,
                    'duration_bars': duration_bars,
                    'speed_pct_per_bar': price_change_pct / duration_bars if duration_bars > 0 else 0
                })
            else:
                # Drop (down movement)
                drops.append({
                    'amplitude_pct': abs(price_change_pct),
                    'duration_bars': duration_bars,
                    'speed_pct_per_bar': abs(price_change_pct) / duration_bars if duration_bars > 0 else 0
                })

        # 3. Aggregate metrics (reuse existing logic)
        return self._aggregate_metrics(rallies, drops)

    def _aggregate_metrics(self, rallies: List[Dict], drops: List[Dict]) -> SwingMetrics:
        """
        Агрегировать rallies и drops в SwingMetrics.

        EXTRACTED: Общая логика для calculate() и aggregate_for_zone()
        """
        rally_count = len(rallies)
        drop_count = len(drops)

        # Amplitude metrics
        if rally_count > 0:
            rally_amps = [r['amplitude_pct'] for r in rallies]
            avg_rally_pct = np.mean(rally_amps)
            max_rally_pct = np.max(rally_amps)
            min_rally_pct = np.min(rally_amps)
            rally_amplitude_std = np.std(rally_amps)
            rally_amplitude_median = np.median(rally_amps)
        else:
            avg_rally_pct = max_rally_pct = min_rally_pct = 0.0
            rally_amplitude_std = rally_amplitude_median = 0.0

        if drop_count > 0:
            drop_amps = [d['amplitude_pct'] for d in drops]
            avg_drop_pct = np.mean(drop_amps)
            max_drop_pct = np.max(drop_amps)
            min_drop_pct = np.min(drop_amps)
            drop_amplitude_std = np.std(drop_amps)
            drop_amplitude_median = np.median(drop_amps)
        else:
            avg_drop_pct = max_drop_pct = min_drop_pct = 0.0
            drop_amplitude_std = drop_amplitude_median = 0.0

        # Duration metrics
        if rally_count > 0:
            rally_durs = [r['duration_bars'] for r in rallies]
            avg_rally_duration_bars = float(np.mean(rally_durs))
            max_rally_duration_bars = int(np.max(rally_durs))
        else:
            avg_rally_duration_bars = 0.0
            max_rally_duration_bars = 0

        if drop_count > 0:
            drop_durs = [d['duration_bars'] for d in drops]
            avg_drop_duration_bars = float(np.mean(drop_durs))
            max_drop_duration_bars = int(np.max(drop_durs))
        else:
            avg_drop_duration_bars = 0.0
            max_drop_duration_bars = 0

        # Speed metrics
        if rally_count > 0:
            rally_speeds = [r['speed_pct_per_bar'] for r in rallies]
            avg_rally_speed_pct_per_bar = np.mean(rally_speeds)
            max_rally_speed_pct_per_bar = np.max(rally_speeds)
        else:
            avg_rally_speed_pct_per_bar = max_rally_speed_pct_per_bar = 0.0

        if drop_count > 0:
            drop_speeds = [d['speed_pct_per_bar'] for d in drops]
            avg_drop_speed_pct_per_bar = np.mean(drop_speeds)
            max_drop_speed_pct_per_bar = np.max(drop_speeds)
        else:
            avg_drop_speed_pct_per_bar = max_drop_speed_pct_per_bar = 0.0

        # Ratio and symmetry
        rally_to_drop_ratio = avg_rally_pct / avg_drop_pct if avg_drop_pct > 0 else 0.0
        duration_symmetry = (avg_rally_duration_bars / avg_drop_duration_bars
                           if avg_drop_duration_bars > 0 else 0.0)

        num_swings = min(rally_count, drop_count)

        metrics = SwingMetrics(
            num_swings=num_swings,
            avg_rally_pct=avg_rally_pct,
            avg_drop_pct=avg_drop_pct,
            max_rally_pct=max_rally_pct,
            max_drop_pct=max_drop_pct,
            rally_to_drop_ratio=rally_to_drop_ratio,
            rally_count=rally_count,
            drop_count=drop_count,
            min_rally_pct=min_rally_pct,
            min_drop_pct=min_drop_pct,
            rally_amplitude_std=rally_amplitude_std,
            drop_amplitude_std=drop_amplitude_std,
            rally_amplitude_median=rally_amplitude_median,
            drop_amplitude_median=drop_amplitude_median,
            avg_rally_duration_bars=avg_rally_duration_bars,
            avg_drop_duration_bars=avg_drop_duration_bars,
            max_rally_duration_bars=max_rally_duration_bars,
            max_drop_duration_bars=max_drop_duration_bars,
            avg_rally_speed_pct_per_bar=avg_rally_speed_pct_per_bar,
            avg_drop_speed_pct_per_bar=avg_drop_speed_pct_per_bar,
            max_rally_speed_pct_per_bar=max_rally_speed_pct_per_bar,
            max_drop_speed_pct_per_bar=max_drop_speed_pct_per_bar,
            duration_symmetry=duration_symmetry,
            strategy_name='zigzag',
            strategy_params={'legs': self.legs, 'deviation': self.deviation}
        )

        metrics.validate()
        return metrics

    def calculate(self, zone_data: pd.DataFrame) -> SwingMetrics:
        """
        Legacy per-zone calculation (DEPRECATED, но оставлен для BC).

        Используется как fallback при swing_scope="per_zone"
        """
        # Existing implementation без изменений
        # ... (current code from zigzag.py)
```

---

## 4. Обновление `ZoneAnalysisPipeline`

### 4.1. Добавление глобального расчёта свингов

```python
# В bquant/analysis/zones/pipeline.py

class ZoneAnalysisPipeline:
    """
    Пайплайн анализа зон.

    UPDATED: Поддержка глобального расчёта свингов
    """

    def _run_without_cache(self) -> ZoneAnalysisResult:
        """
        Выполнение анализа без кэширования.

        UPDATED: Добавлен этап глобального расчёта свингов

        Workflow:
        1. prepare_dataframe() — добавление индикаторов
        2. [NEW] _calculate_global_swings() — глобальный расчёт (если swing_scope="global")
        3. detect_zones() — детекция зон
        4. [NEW] _inject_swing_context() — инжекция контекста в зоны
        5. _analyze_zones_internal() — анализ зон
        """
        # 1. Prepare data
        df_prepared = self._prepare_dataframe()

        # 2. НОВОЕ: Calculate global swings (если включено)
        global_swing_context = None
        if self._config.swing_scope == "global" and self._swing_strategy is not None:
            try:
                global_swing_context = self._calculate_global_swings(df_prepared)
            except Exception as e:
                self.logger.warning(
                    f"Global swing calculation failed, falling back to per_zone mode: {e}"
                )
                # Fallback: продолжаем без глобального контекста

        # 3. Detect zones
        zones = self._detect_zones_internal(df_prepared)

        # 4. НОВОЕ: Inject swing_context into zones
        if global_swing_context is not None:
            self._inject_swing_context(zones, global_swing_context)

        # 5. Analyze zones
        result = self._analyze_zones_internal(zones, df_prepared)

        return result

    def _calculate_global_swings(self, data: pd.DataFrame) -> SwingContext:
        """
        Рассчитать глобальные свинги для всего датасета.

        NEW METHOD

        Args:
            data: Подготовленный DataFrame с индикаторами

        Returns:
            SwingContext с глобальными свингами

        Raises:
            ValueError: Если стратегия не поддерживает глобальный расчёт
            RuntimeError: При ошибках алгоритма
        """
        self.logger.info(
            f"Calculating global swings with strategy: {self._swing_strategy.__class__.__name__}"
        )

        # Проверка поддержки глобального режима
        if not hasattr(self._swing_strategy, 'calculate_global'):
            raise ValueError(
                f"Strategy {self._swing_strategy.__class__.__name__} "
                f"does not support global swing calculation"
            )

        # Вызов глобального расчёта
        swing_context = self._swing_strategy.calculate_global(data)

        self.logger.info(
            f"Global swings calculated: {len(swing_context.swing_points)} swing points detected"
        )

        return swing_context

    def _inject_swing_context(
        self,
        zones: List[ZoneInfo],
        swing_context: SwingContext
    ) -> None:
        """
        Инжектировать глобальный SwingContext в каждую зону.

        NEW METHOD

        Args:
            zones: Список детектированных зон
            swing_context: Глобальный контекст свингов

        Side Effects:
            Модифицирует zones in-place, устанавливая zone.swing_context
        """
        for zone in zones:
            zone.swing_context = swing_context

        self.logger.debug(
            f"Injected swing_context into {len(zones)} zones"
        )
```

### 4.2. Builder API

```python
# В bquant/analysis/zones/pipeline.py

class ZoneAnalysisBuilder:
    """
    Fluent API для настройки анализа зон.

    UPDATED: Добавлен метод with_swing_scope()
    """

    def with_swing_scope(self, scope: Literal["per_zone", "global"]) -> 'ZoneAnalysisBuilder':
        """
        Выбор режима расчёта свингов.

        NEW METHOD

        Args:
            scope: Режим расчёта
                - "per_zone": Изолированный расчёт для каждой зоны (legacy, default)
                - "global": Глобальный расчёт на всём датасете (рекомендуется)

        Returns:
            Self для fluent API

        Raises:
            ValueError: Если передан некорректный scope

        Example:
            # Глобальный режим (рекомендуется для корректного анализа)
            result = (
                analyze_zones(data)
                .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
                .detect_zones('zero_crossing', indicator_col='macd_hist')
                .with_strategies(swing='zigzag')
                .with_swing_scope('global')  # ← Глобальный расчёт
                .analyze()
                .build()
            )

            # Legacy режим (для совместимости)
            result = (
                analyze_zones(data)
                ...
                .with_swing_scope('per_zone')  # ← Изолированный расчёт
                .build()
            )
        """
        if scope not in ['per_zone', 'global']:
            raise ValueError(
                f"Invalid swing_scope: {scope}. "
                f"Must be 'per_zone' or 'global'"
            )

        self.pipeline._config.swing_scope = scope

        self.logger.info(f"Swing calculation mode set to: {scope}")

        return self
```

---

## 5. Обновление `ZoneFeaturesAnalyzer`

```python
# В bquant/analysis/zones/zone_features.py

class ZoneFeaturesAnalyzer:
    """
    Анализатор характеристик торговых зон.

    UPDATED: Поддержка глобального расчёта свингов
    """

    def extract_zone_features(self, zone_info: Dict[str, Any]) -> ZoneFeatures:
        """
        Извлечение признаков из информации о зоне.

        UPDATED: Добавлена логика выбора режима расчёта свингов
        """
        # ... existing code ...

        # Calculate swing metrics using strategy
        if self.swing_strategy is not None:
            try:
                swing_context = zone_info.get('swing_context')

                if swing_context is not None:
                    # ГЛОБАЛЬНЫЙ РЕЖИМ
                    # Создаём временный ZoneInfo для aggregate_for_zone
                    temp_zone = ZoneInfo(
                        zone_id=zone_info['zone_id'],
                        type=zone_info['type'],
                        start_idx=zone_info['start_idx'],
                        end_idx=zone_info['end_idx'],
                        start_time=zone_info['start_time'],
                        end_time=zone_info['end_time'],
                        duration=zone_info['duration'],
                        data=data,
                        swing_context=swing_context
                    )

                    swing_metrics = self.swing_strategy.aggregate_for_zone(
                        temp_zone,
                        swing_context
                    )

                    metadata['swing_calculation_mode'] = 'global'

                    self.logger.debug(
                        f"Swing metrics aggregated from global context: "
                        f"{swing_metrics.rally_count} rallies, {swing_metrics.drop_count} drops, "
                        f"ratio={swing_metrics.rally_to_drop_ratio:.2f}"
                    )

                else:
                    # PER-ZONE РЕЖИМ (legacy или fallback)
                    swing_metrics = self.swing_strategy.calculate(data)

                    metadata['swing_calculation_mode'] = 'per_zone'

                    self.logger.debug(
                        f"Swing metrics calculated in per_zone mode: "
                        f"{swing_metrics.rally_count} rallies, {swing_metrics.drop_count} drops"
                    )

                metadata['swing_metrics'] = swing_metrics.to_dict()

            except Exception as e:
                self.logger.warning(f"Failed to calculate swing metrics: {e}")
                metadata['swing_metrics'] = None

        # ... rest of existing code ...
```

---

## 6. Адаптивные пороги в глобальном режиме

```python
# В bquant/analysis/zones/strategies/swing/thresholds.py

class _AdaptiveSwingStrategy:
    """
    Wrapper для адаптивных порогов свингов.

    UPDATED: Поддержка глобального режима
    """

    def __init__(self, base_strategy, adaptive_params: Dict[str, Any]):
        self.base_strategy = base_strategy
        self.adaptive_params = adaptive_params
        self._global_threshold_cache = None  # Кэш для глобального режима

    def calculate_global(self, full_data: pd.DataFrame) -> SwingContext:
        """
        Глобальный расчёт с адаптивными порогами.

        NEW METHOD

        ВАЖНО: Пороги рассчитываются ОДИН РАЗ на глобальных данных
        и применяются ко всем зонам.
        """
        # 1. Calculate adaptive thresholds on FULL data
        thresholds = self._calculate_adaptive_thresholds(full_data)
        self._global_threshold_cache = thresholds

        # 2. Apply thresholds to base strategy
        self._apply_thresholds_to_strategy(self.base_strategy, thresholds)

        # 3. Delegate to base strategy
        return self.base_strategy.calculate_global(full_data)

    def aggregate_for_zone(self, zone: ZoneInfo, context: SwingContext) -> SwingMetrics:
        """
        Агрегация с применением глобальных порогов.

        NEW METHOD

        Пороги НЕ пересчитываются для каждой зоны — используются глобальные!
        """
        # Используем глобальные пороги (уже применены в calculate_global)
        return self.base_strategy.aggregate_for_zone(zone, context)
```

---

## 7. Схема обновлённого воркфлоу

```
┌────────────────────────────────────────────────────────────────────┐
│               ZoneAnalysisPipeline._run_without_cache              │
├────────────────────────────────────────────────────────────────────┤
│ 1. prepare_dataframe()                                            │
│    └─> df_prepared (with indicators)                              │
│                                                                    │
│ 2. if config.swing_scope == "global":                             │
│    └─> _calculate_global_swings(df_prepared)                      │
│        └─> swing_strategy.calculate_global(df_prepared)           │
│            └─> SwingContext(swing_points=[...], indices=[...])    │
│                                                                    │
│ 3. _detect_zones_internal(df_prepared)                            │
│    └─> zones: List[ZoneInfo]                                      │
│                                                                    │
│ 4. if global_swing_context:                                       │
│    └─> _inject_swing_context(zones, global_swing_context)         │
│        └─> for zone in zones: zone.swing_context = context        │
│                                                                    │
│ 5. _analyze_zones_internal(zones, df_prepared)                    │
│    └─> UniversalZoneAnalyzer.analyze_zones(zones, df)             │
│        └─> ZoneFeaturesAnalyzer.extract_all_zones_features(zones) │
│            └─> for zone in zones:                                 │
│                if zone.swing_context:                             │
│                    swing_strategy.aggregate_for_zone(zone, ctx)   │
│                    └─> zone_swings = ctx.slice(zone.range)        │
│                        └─> SwingMetrics                            │
│                else:                                               │
│                    swing_strategy.calculate(zone.data)            │
│                    └─> SwingMetrics (legacy)                       │
└────────────────────────────────────────────────────────────────────┘
```

---

## 8. Миграционная стратегия

### Фаза 1: Модели и конфигурация (Week 1)
**Приоритет: ВЫСОКИЙ**

1. ✅ Добавить `SwingPoint` dataclass в `bquant/analysis/zones/models.py`
2. ✅ Добавить `SwingContext` dataclass в `bquant/analysis/zones/models.py`
3. ✅ Обновить `ZoneInfo`: добавить `swing_context` поле и метод `get_zone_swings()`
4. ✅ Обновить `ZoneInfo.to_analyzer_format()` для передачи `swing_context`
5. ✅ Добавить `swing_scope` в `ZoneAnalysisConfig`
6. ✅ Обновить `ZoneAnalysisConfig.to_cache_key()` с учётом `swing_scope`

**Критерий готовности**: Все модели определены, тесты на сериализацию/десериализацию проходят

### Фаза 2: Обновление стратегий (Week 2)
**Приоритет: ВЫСОКИЙ**

1. ✅ Обновить протокол `SwingCalculationStrategy` в `strategies/base.py`
2. ✅ Реализовать `calculate_global()` для `ZigZagSwingStrategy`
3. ✅ Реализовать `aggregate_for_zone()` для `ZigZagSwingStrategy`
4. ✅ Извлечь `_aggregate_metrics()` как общий метод
5. ✅ Аналогично обновить `FindPeaksSwingStrategy`
6. ✅ Аналогично обновить `PivotPointsSwingStrategy`
7. ✅ Обновить `_AdaptiveSwingStrategy` для поддержки глобальных порогов

**Критерий готовности**: Все стратегии поддерживают оба режима, unit-тесты проходят

### Фаза 3: Обновление Pipeline (Week 3)
**Приоритет: СРЕДНИЙ**

1. ✅ Добавить `_calculate_global_swings()` в `ZoneAnalysisPipeline`
2. ✅ Добавить `_inject_swing_context()` в `ZoneAnalysisPipeline`
3. ✅ Обновить `_run_without_cache()` с новым воркфлоу
4. ✅ Добавить `with_swing_scope()` в `ZoneAnalysisBuilder`
5. ✅ Обновить логирование для отслеживания режима

**Критерий готовности**: Pipeline корректно переключается между режимами

### Фаза 4: Обновление ZoneFeaturesAnalyzer (Week 3)
**Приоритет: СРЕДНИЙ**

1. ✅ Обновить `extract_zone_features()` с логикой выбора режима
2. ✅ Добавить маркер `swing_calculation_mode` в metadata
3. ✅ Обновить логирование

**Критерий готовности**: Анализатор использует глобальный контекст если доступен

### Фаза 5: Тестирование (Week 4)
**Приоритет: КРИТИЧЕСКИЙ**

**Unit-тесты**:
```python
# tests/unit/test_swing_global_calculation.py
def test_zigzag_global_vs_isolated():
    """Сравнение глобального и изолированного режимов ZigZag."""
    # Создать искусственный ряд с явными свингами
    # Убедиться, что глобальный режим находит больше свингов

def test_swing_context_slice_with_neighbors():
    """Проверка корректности захвата соседних пивотов."""
    # Создать SwingContext с 5 точками
    # Slice [2:3] должен вернуть [1, 2, 3, 4] (с соседними)

def test_adaptive_thresholds_global_mode():
    """Проверка, что адаптивные пороги рассчитываются глобально."""
    # Убедиться, что порог рассчитан на полном датасете
```

**Интеграционные тесты**:
```python
# tests/integration/test_pipeline_global_swings.py
def test_pipeline_global_swing_scope():
    """Полный пайплайн с global swing_scope."""
    result = (
        analyze_zones(sample_data)
        .with_indicator('custom', 'macd', ...)
        .detect_zones('zero_crossing', indicator_col='macd_hist')
        .with_strategies(swing='zigzag')
        .with_swing_scope('global')
        .analyze()
        .build()
    )

    # Проверить, что все зоны имеют swing_context
    assert all(zone.swing_context is not None for zone in result.zones)

    # Проверить, что метрики помечены как 'global'
    for zone in result.zones:
        if zone.features and 'metadata' in zone.features:
            assert zone.features['metadata'].get('swing_calculation_mode') == 'global'

def test_fallback_to_per_zone():
    """Fallback на per_zone при ошибках глобального расчёта."""
    # Создать данные, на которых global расчёт упадёт
    # Убедиться, что пайплайн не падает и использует per_zone
```

**Сравнительные тесты**:
```python
# research/notebooks/test_global_swing_coverage.py
def compare_swing_coverage():
    """
    Сравнить покрытие зон свингами в двух режимах.

    Expected:
        Global mode: 60-80% зон имеют свинги
        Per-zone mode: 20-40% зон имеют свинги
    """
    # Запустить 05_case_study с обоими режимами
    # Сравнить pct_with_swings
```

### Фаза 6: Документация и примеры (Week 4)
**Приоритет: СРЕДНИЙ**

1. ✅ Обновить `docs/user_guide/zone_analysis.md` с примерами global режима
2. ✅ Добавить migration guide для существующих пользователей
3. ✅ Обновить примеры в `examples/`
4. ✅ Обновить docstrings во всех затронутых модулях

---

## 9. Совместимость, кэширование и fallback

### 9.1. Обратная совместимость
- ✅ **Default = "per_zone"**: Старое поведение сохраняется по умолчанию
- ✅ **Legacy метод `calculate()`**: Продолжает работать для old code
- ✅ **Автоматический fallback**: Если глобальный расчёт не удался → откат на per_zone

### 9.2. Кэширование
```python
# В bquant/analysis/zones/cache.py

class ZoneAnalysisCache:
    """
    Кэш результатов анализа зон.

    UPDATED: Разделение кэша по swing_scope
    """

    def _generate_cache_key(self, config: ZoneAnalysisConfig, data_hash: str) -> str:
        """
        Генерация ключа кэша.

        UPDATED: Включает swing_scope в ключ
        """
        key_parts = [
            f"data={data_hash}",
            f"indicator={config.indicator_config.to_hash()}",
            f"detection={config.detection_config.to_hash()}",
            f"swing_scope={config.swing_scope}",  # НОВОЕ
            # ... other parts ...
        ]
        return hashlib.sha256('|'.join(key_parts).encode()).hexdigest()
```

### 9.3. Graceful Degradation
```python
# Fallback logic в Pipeline

try:
    global_swing_context = self._calculate_global_swings(df_prepared)
except Exception as e:
    self.logger.warning(
        f"Global swing calculation failed: {e}. "
        f"Falling back to per_zone mode for this analysis."
    )
    global_swing_context = None
    # Продолжаем выполнение с per_zone логикой
```

---

## 10. Риски и меры

### Риск 1: Границы пивотов
**Проблема**: Некорректная нарезка может обрезать свинги на границах зон.

**Мера**: Алгоритм `slice()` с захватом соседних пивотов (bisect_left/right + расширение на 1 элемент).

**Тест**: Unit-тест на пограничные случаи (зона начинается ровно на пивоте, зона между двумя пивотами, и т.д.)

### Риск 2: Производительность
**Проблема**: Глобальный расчёт на больших датасетах (>100k баров) может быть медленным.

**Меры**:
- ✅ Глобальный расчёт выполняется **один раз** (vs N раз для N зон)
- ✅ Bisect для нарезки → O(log N) поиск
- ✅ Профилирование на больших датасетах

**Benchmark**: Сравнить время выполнения для датасета 10k, 50k, 100k баров.

### Риск 3: Расширяемость стратегий
**Проблема**: Новые стратегии должны поддерживать оба метода.

**Мера**: Формальный протокол `SwingCalculationStrategy` с проверкой в runtime.

**Тест**: Попытка использовать стратегию без `calculate_global()` в global mode → читаемая ошибка.

---

## 11. Итоговые преимущества

### ✅ Корректность анализа
- Свинги рассчитаны на глобальном уровне → нет потери граничных точек
- Единые пороги для всех зон → статистическая сопоставимость
- Соответствие результатам "ручного" ZigZag анализа

### ✅ Производительность
- Глобальный расчёт **1 раз** вместо N раз (для N зон)
- Агрегация через bisect + фильтрацию → O(k log n) где k = число свингов в зоне
- Кэширование глобального контекста

### ✅ Гибкость
- Выбор режима через `.with_swing_scope('global' | 'per_zone')`
- Backward compatibility с legacy режимом
- Graceful fallback при ошибках

### ✅ Расширяемость
- `SwingContext` можно сохранить/загрузить независимо
- Можно визуализировать глобальные свинги
- Можно анализировать свинги вне зон
- Формальный контракт для новых стратегий

### ✅ Качество кода
- Чёткое разделение ответственности (расчёт vs агрегация)
- Богатая модель данных (`SwingPoint` с метаданными)
- Полная трассируемость (strategy_name, strategy_params)
- Удобный API (`zone.get_zone_swings()`)

---

## 12. Резюме

Введя глобальный расчёт свингов и последующую нарезку пивотов на зоны, мы получим:

1. **Согласованный набор метрик**, совпадающий с результатами глобального ZigZag
2. **Устранение искажений** анализа из-за изолированного расчёта
3. **Повышение воспроизводимости** результатов
4. **Закладку основы** для дальнейшего развития свинговых стратегий
5. **Обратную совместимость** с существующим кодом через fallback

**Рекомендуемая последовательность реализации**: Фазы 1→2→3→4→5→6

**Ожидаемый эффект на 05_case_study**: Покрытие зон свингами увеличится с 20-60% до 70-90% в зависимости от стратегии.
