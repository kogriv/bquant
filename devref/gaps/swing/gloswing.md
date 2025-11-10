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

**⚠️ ВАЖНОЕ ОГРАНИЧЕНИЕ (Current Scope)**:

В этой версии поддерживается **только ОДНА swing стратегия** за раз.

- Поле `swing_context` хранит результат **ОДНОЙ** стратегии
- `Pipeline.with_strategies(swing='zigzag')` принимает **строку** (не список)
- Если передать список `swing=['zigzag', 'find_peaks']` → ValueError с понятным сообщением

**Обоснование**: Это упрощает реализацию и позволяет сфокусироваться на решении проблемы per_zone границ без дополнительной сложности множественных стратегий.

**Для множественных стратегий**: Запуск нескольких стратегий одновременно (consensus analysis, strategy comparison) описан в отдельном документе [multiswing.md](multiswing.md). Эта фича будет реализована **ПОСЛЕ** завершения global swing calculation как самостоятельное расширение.

---

```python
# В bquant/analysis/zones/models.py

@dataclass
class ZoneInfo:
    """
    Информация о зоне (универсальная структура).

    NEW FIELD:
        swing_context: Optional[SwingContext] - ссылка на глобальный контекст свингов
                                                  (ОДНОЙ стратегии)
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

### Фаза 1: Модели данных (Week 1)
**Приоритет: ВЫСОКИЙ**

**📖 Обязательное pre-reading**:
- **Раздел 1** - "Новые модели данных" (строки 55-266) - полная спецификация SwingPoint, SwingContext, обновления ZoneInfo
- **Раздел 10, Риск 2** - "Потребление памяти" (строки 1649-1752) - ограничения на дизайн моделей для больших датасетов
- **Раздел 2** - "Расширение конфигурации" (строки 268-306) - требования к ZoneAnalysisConfig

---

**Задачи**:

1.1. ✅ **Создать `SwingPoint` dataclass** (`bquant/analysis/zones/models.py`)

     **Спецификация**: См. раздел 1.1 (строки 55-101) - полный список из 9 полей

     **Checklist**:
     - [ ] Все 9 полей согласно таблице в Attributes (раздел 1.1, строки 70-78)
     - [ ] `__post_init__` валидация для strategy_params (строки 98-100)
     - [ ] Type hints: `point_id: int`, `timestamp: datetime`, `swing_type: str`, etc.
     - [ ] Docstring с примерами (Google Style Guide)

     **Проверка**: Код должен совпадать с примером из раздела 1.1 (строки 64-101)

1.2. ✅ **Создать `SwingContext` dataclass** (`bquant/analysis/zones/models.py`)

     **Спецификация**: См. раздел 1.2 (строки 103-200) - полная структура с методами

     **Checklist**:
     - [ ] 5 полей: swing_points, indices, full_data_length, strategy_name, strategy_params (строки 124-128)
     - [ ] Метод `slice()` с bisect алгоритмом (строки 130-165) - **КРИТИЧЕСКИ ВАЖНО**
     - [ ] Метод `get_swings_for_zone()` (строки 167-177)
     - [ ] Метод `to_dict()` для сериализации (строки 179-199)
     - [ ] indices как `np.ndarray` для O(log N) поиска

     **Алгоритм slice()**:
     - Использовать `bisect_left`/`bisect_right` для границ (строки 158-159)
     - Захватить соседние пивоты: `left-1` и `right+1` (строки 162-163)
     - См. визуальный пример в строках 140-145

     **Memory constraint**: Оценка ~264 bytes/point (раздел 10, строки 1652-1669)

1.3. ✅ **Обновить `ZoneInfo`** (`bquant/analysis/zones/models.py`)

     **Спецификация**: См. раздел 1.3 (строки 202-264)

     **Checklist**:
     - [ ] Добавить поле `swing_context: Optional[SwingContext] = None` (строка 225)
     - [ ] Реализовать метод `get_zone_swings()` (строки 227-243)
     - [ ] Обновить `to_analyzer_format()` - включить swing_context (строки 245-263)
     - [ ] Docstrings с примерами использования (строки 228-239)

1.4. ✅ **Добавить `swing_scope` в `ZoneAnalysisConfig`** (`bquant/analysis/zones/pipeline.py`)

     **Спецификация**: См. раздел 2.1 (строки 268-300)

     **Checklist**:
     - [ ] Поле `swing_scope: Literal["per_zone", "global"] = "per_zone"` (строка 289)
     - [ ] Обновить `to_cache_key()` - включить swing_scope (строка 298)
     - [ ] Default = "per_zone" для обратной совместимости
     - [ ] Docstring объясняет оба режима (строки 278-286)

1.5. ✅ **Обновить кэширование с версией** (`bquant/analysis/zones/cache.py`)

     **Спецификация**: См. раздел 9.4 (строки 2090-2209) - миграция существующих кэшей

     **Checklist** (двусторонняя схема WRITE + READ):
     - [ ] Добавить константу `CACHE_VERSION = 2` в ZoneAnalysisCache
     - [ ] Обновить `_generate_cache_key()` - включить `f"version={self.CACHE_VERSION}"` в key_parts
     - [ ] **WRITE PATH**: Обновить `save()` - записывать `'cache_version': self.CACHE_VERSION` в payload
     - [ ] **READ PATH**: Обновить `load()` - проверять `cached_version = cached_data.get('cache_version', 1)`
     - [ ] Добавить инвалидацию: `if cached_version < self.CACHE_VERSION: return None`
     - [ ] Логировать INFO при инвалидации кэша, DEBUG при сохранении

---

**✅ Post-completion checklist**:

**Immediate (проверить сейчас)**:
- [ ] Все модели из раздела 1 реализованы (SwingPoint, SwingContext, ZoneInfo updates)
- [ ] Кэширование обновлено (CACHE_VERSION = 2, инвалидация старых кэшей)
- [ ] API совпадает с примерами из раздела 1 (вручную сравнить сигнатуры методов)
- [ ] **ТЕСТ**: Запустить `mypy bquant/analysis/zones/models.py` - проверить type hints
- [ ] **ТЕСТ**: Создать smoke test на сериализацию - вызвать `SwingContext.to_dict()`, проверить что Dict содержит все поля
- [ ] **ТЕСТ**: Создать smoke test на memory - создать SwingContext с 1000 SwingPoint, измерить через `sys.getsizeof()`, проверить ~264 KB ±50%
- [ ] **ТЕСТ**: Создать smoke test на cache invalidation - создать fake кэш с version=1, попытаться загрузить, проверить что вернулся None
- [ ] Docstrings соответствуют Google Style Guide (проверить вручную или через linter)

**Future compatibility (⏳ подготовка к Фазе 5)**:
- [ ] ⏳ Код готов к edge case тестам: `SwingContext.slice()` корректно обрабатывает границы массива (включает проверки `max(0, left-1)` и `min(len, right+1)`)
- [ ] ⏳ Код готов к integration тестам: `ZoneInfo.get_zone_swings()` возвращает пустой список если `swing_context is None`
- [ ] ⏳ Код готов к cache migration тестам: старые кэши автоматически инвалидируются при CACHE_VERSION увеличении

### Фаза 2: Протокол и стратегии свингов (Week 2)
**Приоритет: ВЫСОКИЙ**

**📖 Обязательное pre-reading**:
- **Раздел 3** - "Обновление API стратегий свингов" (строки 308-689) - полная спецификация протокола и примеры реализации
- **Раздел 6** - "Адаптивные пороги в глобальном режиме" (строки 946-992) - особенности адаптивных стратегий
- **Раздел 10, Риск 4** - "Расширяемость стратегий" (строка 1765-1770) - требования к протоколу

---

**Задачи**:

2.1. ✅ **Обновить протокол `SwingCalculationStrategy`** (`bquant/analysis/zones/strategies/base.py`)

     **Спецификация**: См. раздел 3.1 (строки 310-401) - Protocol с 3 методами

     **Checklist**:
     - [ ] `@runtime_checkable` decorator для проверки в runtime
     - [ ] Метод `calculate_global(full_data) -> SwingContext` (строки 329-350)
     - [ ] Метод `aggregate_for_zone(zone, context) -> SwingMetrics` (строки 352-374)
     - [ ] Метод `calculate(zone_data) -> SwingMetrics` помечен как DEPRECATED (строки 376-391)
     - [ ] Метод `config_hash() -> Dict[str, Any]` (строки 393-400)
     - [ ] Полные docstrings для каждого метода

     **ВАЖНО**: Методы calculate_global() и aggregate_for_zone() - PRIORITY, calculate() - только BC

2.2. ✅ **Реализовать `calculate_global()` для `ZigZagSwingStrategy`** (`strategies/swing/zigzag.py`)

     **Спецификация**: См. раздел 3.2 (строки 419-527) - полный пример реализации

     **Checklist**:
     - [ ] Валидация входных данных (строки 436-439)
     - [ ] Применение pandas-ta ZigZag (строки 442-448)
     - [ ] Обработка edge cases (недостаточно колонок, мало точек) (строки 450-472)
     - [ ] Преобразование в SwingPoint объекты (строки 474-517)
     - [ ] Определение swing_type (peak/trough) по направлению (строки 482-491)
     - [ ] Расчёт amplitude_to_next и duration_to_next (строки 493-502)
     - [ ] Возврат SwingContext с полными метаданными (строки 521-527)

     **Алгоритм**:
     1. Извлечь swing_values из ZigZag result (строка 461)
     2. Итерация по swing_points_series (строка 478)
     3. Получить position через `full_data.index.get_loc()` (строка 479)
     4. Определить swing_type по сравнению с prev/next (строки 482-491)

2.3. ✅ **Реализовать `aggregate_for_zone()` для `ZigZagSwingStrategy`** (`strategies/swing/zigzag.py`)

     **Спецификация**: См. раздел 3.2 (строки 529-577) - агрегация глобальных свингов

     **Checklist**:
     - [ ] Получение zone_swings через `context.get_swings_for_zone(zone)` (строка 542)
     - [ ] Проверка минимального количества свингов (строки 544-548)
     - [ ] Разделение на rallies и drops по price_change_pct (строки 550-574)
     - [ ] Вызов `_aggregate_metrics()` для финальной агрегации (строка 577)

2.4. ✅ **Извлечь `_aggregate_metrics()` как общий метод** (`strategies/swing/zigzag.py`)

     **Спецификация**: См. раздел 3.2 (строки 579-679) - общая логика агрегации

     **Checklist**:
     - [ ] Принимает `rallies: List[Dict]` и `drops: List[Dict]`
     - [ ] Рассчитывает ВСЕ 23 поля SwingMetrics (строки 588-676)
     - [ ] Вызывает `metrics.validate()` перед возвратом (строка 678)
     - [ ] Используется и в calculate() (legacy), и в aggregate_for_zone()

     **ВАЖНО**: Этот метод используется повторно - не дублировать логику!

2.5. ✅ **Обновить `FindPeaksSwingStrategy`** (`strategies/swing/find_peaks.py`)

     **Спецификация**: Аналогично ZigZagSwingStrategy (раздел 3.2)

     **Checklist**:
     - [ ] Реализовать `calculate_global()` с scipy.signal.find_peaks на глобальных данных
     - [ ] Реализовать `aggregate_for_zone()` аналогично ZigZag
     - [ ] Извлечь `_aggregate_metrics()` из существующего calculate()
     - [ ] Сохранить legacy метод calculate() для BC

2.6. ✅ **Обновить `PivotPointsSwingStrategy`** (`strategies/swing/pivot_points.py`)

     **Спецификация**: Аналогично ZigZagSwingStrategy

     **Checklist**:
     - [ ] calculate_global(), aggregate_for_zone(), _aggregate_metrics()
     - [ ] Те же паттерны, что и для ZigZag/FindPeaks

2.7. ✅ **Обновить `_AdaptiveSwingStrategy`** (`strategies/swing/thresholds.py`)

     **Спецификация**: См. раздел 6 (строки 946-992) - wrapper для адаптивных порогов

     **Checklist**:
     - [ ] Добавить `_global_threshold_cache` поле (строка 961)
     - [ ] Реализовать `calculate_global()` - пороги ONE TIME на глобальных данных (строки 963-980)
     - [ ] Реализовать `aggregate_for_zone()` - использовать глобальные пороги (строки 982-991)

     **КРИТИЧЕСКИ ВАЖНО**: Пороги рассчитываются ОДИН РАЗ на полных данных, НЕ для каждой зоны!

---

**✅ Post-completion checklist**:

**Immediate (проверить сейчас)**:
- [ ] Протокол SwingCalculationStrategy обновлён в base.py (3 метода: calculate_global, aggregate_for_zone, calculate)
- [ ] Все 3 стратегии (ZigZag, FindPeaks, PivotPoints) реализуют новые методы
- [ ] `_aggregate_metrics()` извлечён как отдельный метод (без дублирования кода)
- [ ] Адаптивная обёртка `_AdaptiveSwingStrategy` имеет поле `_global_threshold_cache`
- [ ] **ТЕСТ**: Запустить `mypy` на strategies/ - проверить type hints и Protocol compliance
- [ ] **ТЕСТ**: Создать smoke test для ZigZag - вызвать `calculate_global(sample_data)`, проверить что вернулся SwingContext с swing_points
- [ ] **ТЕСТ**: Создать smoke test для агрегации - вызвать `aggregate_for_zone(zone, context)`, проверить что вернулся SwingMetrics
- [ ] Docstrings обновлены (Google Style) - все новые методы задокументированы

**Future compatibility (⏳ подготовка к Фазе 5)**:
- [ ] ⏳ Код готов к unit тестам из Фазы 5: `calculate_global()` возвращает пустой SwingContext если данных < legs*2 (не падает с исключением)
- [ ] ⏳ Код готов к unit тестам из Фазы 5: `aggregate_for_zone()` возвращает empty metrics если zone_swings < 2
- [ ] ⏳ Код готов к BC тестам: Legacy метод `calculate()` сохранён и работает как раньше (можно вызвать на zone.data)
- [ ] ⏳ Код готов к adaptive threshold тестам: Пороги рассчитываются ONE TIME в `calculate_global()` и кэшируются в `_global_threshold_cache`

### Фаза 3: Обновление Pipeline (Week 3)
**Приоритет: СРЕДНИЙ**

**📖 Обязательное pre-reading**:
- **Раздел 4** - "Обновление ZoneAnalysisPipeline" (строки 691-867) - полная спецификация изменений в Pipeline
- **Раздел 7** - "Схема обновлённого воркфлоу" (строки 996-1028) - визуализация нового workflow
- **Раздел 9.3** - "Graceful Degradation" (строки 1623-1636) - логика fallback при ошибках

---

**Задачи**:

3.1. ✅ **Добавить `_calculate_global_swings()` в `ZoneAnalysisPipeline`** (`bquant/analysis/zones/pipeline.py`)

     **Спецификация**: См. раздел 4.1 (строки 746-780) - новый метод расчёта

     **Checklist**:
     - [ ] Сигнатура: `_calculate_global_swings(data: pd.DataFrame) -> SwingContext`
     - [ ] Проверка поддержки глобального режима (строки 767-771)
     - [ ] Вызов `self._swing_strategy.calculate_global(data)` (строка 774)
     - [ ] Логирование количества обнаруженных свингов (строки 776-778)
     - [ ] Обработка исключений (ValueError, RuntimeError)

     **Важные детали**:
     - Проверить `hasattr(self._swing_strategy, 'calculate_global')` перед вызовом
     - Логирование на INFO уровне: "Calculating global swings with strategy..."

3.2. ✅ **Добавить `_inject_swing_context()` в `ZoneAnalysisPipeline`**

     **Спецификация**: См. раздел 4.1 (строки 782-804) - инжекция контекста в зоны

     **Checklist**:
     - [ ] Сигнатура: `_inject_swing_context(zones: List[ZoneInfo], swing_context: SwingContext) -> None`
     - [ ] Итерация по зонам: `for zone in zones: zone.swing_context = swing_context` (строки 799-800)
     - [ ] Side effect: модификация in-place (строка 797)
     - [ ] Логирование на DEBUG уровне (строки 802-804)

3.3. ✅ **Обновить `_run_without_cache()` с новым воркфлоу**

     **Спецификация**: См. раздел 4.1 (строки 707-744) + диаграмма раздел 7 (строки 999-1028)

     **Checklist**:
     - [ ] Шаг 1: prepare_dataframe() - без изменений (строка 721)
     - [ ] Шаг 2: Вызов _calculate_global_swings() если swing_scope=="global" (строки 724-732)
     - [ ] Шаг 2a: try-except с fallback на per_zone (строки 726-732)
     - [ ] Шаг 3: detect_zones() - без изменений (строка 735)
     - [ ] Шаг 4: _inject_swing_context() если контекст существует (строки 738-739)
     - [ ] Шаг 5: analyze_zones() - без изменений (строка 742)

     **Критический блок fallback** (строки 726-732):
     ```python
     try:
         global_swing_context = self._calculate_global_swings(df_prepared)
     except Exception as e:
         self.logger.warning(
             f"Global swing calculation failed, falling back to per_zone mode: {e}"
         )
         # Fallback: продолжаем без глобального контекста
     ```

3.4. ✅ **Добавить `with_swing_scope()` в `ZoneAnalysisBuilder`**

     **Спецификация**: См. раздел 4.2 (строки 806-867) - Builder API метод

     **Checklist**:
     - [ ] Сигнатура: `with_swing_scope(scope: Literal["per_zone", "global"]) -> 'ZoneAnalysisBuilder'`
     - [ ] Валидация scope: raise ValueError если не 'per_zone' или 'global' (строки 856-860)
     - [ ] Установка: `self.pipeline._config.swing_scope = scope` (строка 862)
     - [ ] Логирование: `self.logger.info(f"Swing calculation mode set to: {scope}")` (строка 864)
     - [ ] Возврат self для fluent API (строка 866)
     - [ ] Полный docstring с примерами (строки 820-854)

     **Примеры использования**: См. строки 837-854 в docstring

3.5. ✅ **Обновить логирование для отслеживания режима**

     **Checklist**:
     - [ ] INFO: "Calculating global swings with strategy: ..." (строка 763)
     - [ ] INFO: "Global swings calculated: N swing points detected" (строка 776)
     - [ ] WARNING: "Global swing calculation failed, falling back..." (строка 729)
     - [ ] INFO: "Swing calculation mode set to: global/per_zone" (строка 864)
     - [ ] DEBUG: "Injected swing_context into N zones" (строка 802)

---

**✅ Post-completion checklist**:

**Immediate (проверить сейчас)**:
- [ ] Методы `_calculate_global_swings()` и `_inject_swing_context()` реализованы в ZoneAnalysisPipeline
- [ ] Workflow `_run_without_cache()` обновлён: prepare → calculate_global (if global) → detect → inject → analyze
- [ ] Builder API метод `with_swing_scope()` реализован и валидирует scope ('per_zone' | 'global')
- [ ] **ТЕСТ**: Создать smoke test на fallback - передать некорректные данные, проверить что WARNING залогирован и execution продолжается
- [ ] **ТЕСТ**: Создать smoke test на логирование - вызвать с swing_scope='global', проверить наличие INFO "Calculating global swings..."
- [ ] **ТЕСТ**: Создать smoke test на переключение режимов - запустить с 'per_zone', затем с 'global', убедиться что результаты отличаются

**Future compatibility (⏳ подготовка к Фазе 5)**:
- [ ] ⏳ Код готов к integration тестам из Фазы 5: try-except блок в _run_without_cache() ловит все Exception и делает fallback на per_zone
- [ ] ⏳ Код готов к integration тестам из Фазы 5: `_inject_swing_context()` присваивает один и тот же объект SwingContext всем зонам (проверяется через `zone_a.swing_context is zone_b.swing_context`)
- [ ] ⏳ Код готов к cache collision тестам: `swing_scope` включён в cache key generation (разные результаты для per_zone vs global)

### Фаза 4: Обновление ZoneFeaturesAnalyzer (Week 3)
**Приоритет: СРЕДНИЙ**

**📖 Обязательное pre-reading**:
- **Раздел 5** - "Обновление ZoneFeaturesAnalyzer" (строки 869-942) - логика выбора режима в extract_zone_features()
- **Раздел 1.3** - "Обновление ZoneInfo" (строки 202-264) - использование ZoneInfo.swing_context

---

**Задачи**:

4.1. ✅ **Обновить `extract_zone_features()` с логикой выбора режима** (`bquant/analysis/zones/zone_features.py`)

     **Спецификация**: См. раздел 5 (строки 872-942) - полная логика ветвления

     **Checklist**:
     - [ ] Проверка наличия swing_context в zone_info (строка 894)
     - [ ] ВЕТКА GLOBAL: Создание temp_zone с swing_context (строки 896-909)
     - [ ] ВЕТКА GLOBAL: Вызов `strategy.aggregate_for_zone(temp_zone, context)` (строки 911-914)
     - [ ] ВЕТКА GLOBAL: Установка metadata['swing_calculation_mode'] = 'global' (строка 916)
     - [ ] ВЕТКА PER_ZONE: Вызов `strategy.calculate(data)` (строка 926)
     - [ ] ВЕТКА PER_ZONE: Установка metadata['swing_calculation_mode'] = 'per_zone' (строка 928)
     - [ ] Логирование для обеих веток (строки 918-933)
     - [ ] Обработка исключений (строки 937-939)

     **Критический блок** (строки 894-934):
     ```python
     swing_context = zone_info.get('swing_context')

     if swing_context is not None:
         # ГЛОБАЛЬНЫЙ РЕЖИМ
         temp_zone = ZoneInfo(...)
         swing_metrics = self.swing_strategy.aggregate_for_zone(temp_zone, swing_context)
         metadata['swing_calculation_mode'] = 'global'
     else:
         # PER-ZONE РЕЖИМ (legacy или fallback)
         swing_metrics = self.swing_strategy.calculate(data)
         metadata['swing_calculation_mode'] = 'per_zone'
     ```

4.2. ✅ **Добавить маркер `swing_calculation_mode` в metadata**

     **Checklist**:
     - [ ] Поле 'swing_calculation_mode' в metadata dict
     - [ ] Значение 'global' для глобального режима (строка 916)
     - [ ] Значение 'per_zone' для legacy режима (строка 928)
     - [ ] Использование в integration тестах для проверки режима

4.3. ✅ **Обновить логирование**

     **Checklist**:
     - [ ] DEBUG уровень для global mode: "Swing metrics aggregated from global context: N rallies, M drops, ratio=X" (строки 918-922)
     - [ ] DEBUG уровень для per_zone mode: "Swing metrics calculated in per_zone mode: N rallies, M drops" (строки 930-933)
     - [ ] WARNING при ошибках: "Failed to calculate swing metrics: {e}" (строка 938)

---

**✅ Post-completion checklist**:

**Immediate (проверить сейчас)**:
- [ ] Метод `extract_zone_features()` имеет if-else ветвление: `if swing_context is not None: ... else: ...`
- [ ] ВЕТКА GLOBAL: создаётся temp_zone и вызывается `strategy.aggregate_for_zone(temp_zone, swing_context)`
- [ ] ВЕТКА PER_ZONE: вызывается `strategy.calculate(data)`
- [ ] Поле `metadata['swing_calculation_mode']` устанавливается в 'global' или 'per_zone'
- [ ] **ТЕСТ**: Создать smoke test на global режим - создать zone_info с swing_context, вызвать extract_zone_features(), проверить metadata['swing_calculation_mode'] == 'global'
- [ ] **ТЕСТ**: Создать smoke test на per_zone режим - создать zone_info БЕЗ swing_context, проверить metadata['swing_calculation_mode'] == 'per_zone'
- [ ] **ТЕСТ**: Создать smoke test на exception handling - передать битую стратегию, проверить что WARNING залогирован и metadata['swing_metrics'] == None

**Future compatibility (⏳ подготовка к Фазе 5)**:
- [ ] ⏳ Код готов к integration тестам из Фазы 5: try-except блок оборачивает всю swing calculation логику (не падает на ошибках стратегии)
- [ ] ⏳ Код готов к integration тестам из Фазы 5: temp_zone создаётся с правильными параметрами (start_idx, end_idx, swing_context из zone_info)

### Фаза 5: Тестирование

**Приоритет**: КРИТИЧЕСКИЙ

**📖 Обязательное pre-reading**:
- **Раздел 10** - "Риски и меры" - все edge cases и риски для тестирования
- **Раздел 1.2** - "SwingContext.slice()" - алгоритм нарезки для тестирования границ
- **Раздел 9** - "Совместимость, кэширование и fallback" - сценарии для интеграционных тестов
- **Раздел 14** - "Метрики успешности" - KPI для измерения результатов

---

**ВАЖНО**: Фаза 5 разделена на **MVP (обязательные тесты)** и **Comprehensive (желательные тесты)**.

MVP тесты **блокируют релиз**, Comprehensive тесты **повышают confidence** но могут быть реализованы после релиза.

---

### Фаза 5.1: MVP Testing (Week 4, Days 1-2) - БЛОКИРУЕТ РЕЛИЗ

**Приоритет: КРИТИЧЕСКИЙ**

**5.1.1. Unit-тесты (минимальный набор)**:
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

**Edge Case тесты (НОВОЕ - КРИТИЧЕСКИ ВАЖНО)**:
```python
# tests/unit/test_swing_edge_cases.py

def test_single_bar_zone():
    """
    Зона из одного бара (start_idx == end_idx).

    Expected behavior:
        - slice() должен вернуть соседние пивоты (если есть)
        - aggregate_for_zone() должен вернуть empty metrics (0 swings)
        - Не должно быть IndexError или других исключений
    """
    # Создать датасет с 100 барами
    # Создать SwingContext с пивотами на индексах [10, 30, 50, 70, 90]
    # Создать зону [50:50] (один бар)
    zone = ZoneInfo(zone_id=0, start_idx=50, end_idx=50, ...)

    # Должен вернуть [30, 50, 70] (соседние пивоты)
    swings = context.get_swings_for_zone(zone)
    assert len(swings) == 3
    assert swings[0].index == 30  # left neighbor
    assert swings[1].index == 50  # zone pivot
    assert swings[2].index == 70  # right neighbor

    # Метрики должны быть пустыми (недостаточно внутренних свингов)
    metrics = strategy.aggregate_for_zone(zone, context)
    assert metrics.num_swings == 0
    assert metrics.rally_count == 0
    assert metrics.drop_count == 0

def test_zone_without_internal_swings():
    """
    Зона без внутренних пивотов (все пивоты вне зоны).

    Expected behavior:
        - slice() вернёт только соседние пивоты (2 точки)
        - aggregate_for_zone() вернёт metrics с 1 свингом (движение между соседними)
    """
    # Пивоты: [10, 50, 90]
    # Зона: [20:40] (между пивотами 10 и 50)
    zone = ZoneInfo(zone_id=0, start_idx=20, end_idx=40, ...)

    swings = context.get_swings_for_zone(zone)
    assert len(swings) == 2  # [pivot@10, pivot@50]

    metrics = strategy.aggregate_for_zone(zone, context)
    # Один свинг между двумя соседними пивотами
    assert metrics.num_swings == 1 or (metrics.rally_count == 1 or metrics.drop_count == 1)

def test_zone_at_dataset_boundaries():
    """
    Зона на самом начале или конце датасета.

    Expected behavior:
        - Зона в начале: захват только правого соседнего пивота
        - Зона в конце: захват только левого соседнего пивота
        - Нет IndexError при выходе за границы
    """
    # Датасет: 100 баров [0:99]
    # Пивоты: [5, 30, 50, 70, 95]

    # Зона в начале [0:10]
    zone_start = ZoneInfo(zone_id=0, start_idx=0, end_idx=10, ...)
    swings_start = context.get_swings_for_zone(zone_start)
    # Должно быть [pivot@5, pivot@30] (нет левого соседа)
    assert swings_start[0].index >= 0  # Не выходит за границы

    # Зона в конце [90:99]
    zone_end = ZoneInfo(zone_id=1, start_idx=90, end_idx=99, ...)
    swings_end = context.get_swings_for_zone(zone_end)
    # Должно быть [pivot@70, pivot@95] (нет правого соседа)
    assert swings_end[-1].index <= 99  # Не выходит за границы

def test_overlapping_zones():
    """
    Перекрывающиеся зоны (если детектор создаёт такие).

    Expected behavior:
        - Каждая зона получает корректные свинги
        - SwingContext используется совместно (не дублируется)
        - Метрики могут отличаться из-за разных границ
    """
    # Пивоты: [10, 30, 50, 70, 90]
    # Зона A: [20:60]  → swings [10, 30, 50, 70]
    # Зона B: [40:80]  → swings [30, 50, 70, 90]

    zone_a = ZoneInfo(zone_id=0, start_idx=20, end_idx=60, ...)
    zone_b = ZoneInfo(zone_id=1, start_idx=40, end_idx=80, ...)

    swings_a = context.get_swings_for_zone(zone_a)
    swings_b = context.get_swings_for_zone(zone_b)

    # Разные границы → разные свинги
    assert swings_a != swings_b

    # Но оба используют один SwingContext (проверка по id)
    assert zone_a.swing_context is zone_b.swing_context

def test_zone_with_all_peaks_or_all_troughs():
    """
    Зона, содержащая только peaks или только troughs.

    Expected behavior:
        - Метрики корректно обрабатывают асимметрию
        - rally_count или drop_count может быть 0
        - Не должно быть division by zero в метриках
    """
    # Создать искусственный случай:
    # Пивоты: peak@10, peak@30, trough@50, peak@70
    # Зона: [5:40] → содержит [peak@10, peak@30]

    zone = ZoneInfo(zone_id=0, start_idx=5, end_idx=40, ...)
    metrics = strategy.aggregate_for_zone(zone, context)

    # Только drops (между двумя peaks)
    # rally_count может быть 0
    assert metrics.drop_count >= 0
    assert metrics.rally_count >= 0

    # Проверка на division by zero
    if metrics.avg_drop_pct == 0:
        assert metrics.rally_to_drop_ratio == 0.0  # Не NaN или Inf

def test_zone_exactly_matching_swing_boundaries():
    """
    Зона, границы которой точно совпадают с пивотами.

    Expected behavior:
        - Граничные пивоты включены в результат
        - Соседние пивоты также захвачены
    """
    # Пивоты: [10, 30, 50, 70, 90]
    # Зона: [30:70] (границы точно на пивотах)

    zone = ZoneInfo(zone_id=0, start_idx=30, end_idx=70, ...)
    swings = context.get_swings_for_zone(zone)

    # Должно быть [10, 30, 50, 70, 90] (включая соседние)
    assert 30 in [s.index for s in swings]  # Граница включена
    assert 70 in [s.index for s in swings]  # Граница включена
    assert 10 in [s.index for s in swings]  # Левый сосед
    assert 90 in [s.index for s in swings]  # Правый сосед

def test_empty_swing_context():
    """
    SwingContext без пивотов (алгоритм не нашёл свингов).

    Expected behavior:
        - get_swings_for_zone() возвращает []
        - aggregate_for_zone() возвращает empty metrics
        - Нет исключений
    """
    empty_context = SwingContext(
        swing_points=[],
        indices=np.array([]),
        full_data_length=100,
        strategy_name='zigzag',
        strategy_params={}
    )

    zone = ZoneInfo(zone_id=0, start_idx=20, end_idx=40, ...)
    zone.swing_context = empty_context

    swings = zone.get_zone_swings()
    assert swings == []

    metrics = strategy.aggregate_for_zone(zone, empty_context)
    assert metrics.num_swings == 0
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

**5.4. Сравнительные тесты**:
```python
# research/notebooks/test_global_swing_coverage.py
def compare_swing_coverage():
    """
    Сравнить покрытие зон свингами в двух режимах.

    Expected:
        Global mode: 70-90% зон имеют свинги
        Per-zone mode: 20-60% зон имеют свинги

    Обоснование: См. раздел 12 "Резюме" - ожидаемый эффект на 05_case_study
    """
    # Запустить 05_case_study с обоими режимами
    # Сравнить pct_with_swings
```

---

### Фаза 5.2: Comprehensive Testing (Post-MVP, optional) - НЕ БЛОКИРУЕТ РЕЛИЗ

**ВАЖНО**: Эти тесты **повышают confidence** и качество продукта, но **НЕ блокируют релиз**. Могут быть реализованы после выкатки MVP.

**5.2.1. Дополнительные Edge Case тесты**:

**test_overlapping_zones()** - Перекрывающиеся зоны используют один SwingContext
```python
def test_overlapping_zones():
    """
    Цель: Проверить что перекрывающиеся зоны используют один SwingContext

    Given: Две зоны [20:60] и [40:80]
    When: calculate_global() вызван один раз
    Then: zone1.swing_context is zone2.swing_context (один объект)
    """
    global_context = strategy.calculate_global(data)
    zone1_swings = global_context.slice(20, 60)
    zone2_swings = global_context.slice(40, 80)
    # Проверить что общая часть [40:60] идентична
    assert zone1_swings[-n:] == zone2_swings[:n]
```

**test_zone_with_all_peaks_or_all_troughs()** - Избежать division by zero
```python
def test_zone_with_all_peaks_or_all_troughs():
    """
    Цель: Проверить расчёт метрик для зоны с только пиками (или только впадинами)

    Given: Зона [30:50] содержит только peaks [32, 38, 45]
    When: aggregate_for_zone() расчитывает метрики
    Then: SwingMetrics.avg_amplitude может быть NaN или 0 (но не исключение)
    """
    # Создать SwingContext с только peaks
    peaks_only = [SwingPoint(32, 100.5, 'peak'), SwingPoint(38, 101.0, 'peak')]
    context = SwingContext(swing_points=peaks_only, indices=[32, 38])

    metrics = context.aggregate_for_zone(30, 50)
    assert metrics.num_swings == 0  # Нет полных swings (нужны peaks + troughs)
    assert not math.isnan(metrics.num_swings)  # Должно быть число, не NaN
```

**test_zone_exactly_matching_swing_boundaries()** - Граница точно на пивоте
```python
def test_zone_exactly_matching_swing_boundaries():
    """
    Цель: Проверить включение соседних пивотов при точном совпадении границ

    Given: Пивоты [10, 30, 50, 70, 90]
          Зона [30:70] (точно на пивотах)
    When: slice(30, 70)
    Then: Возвращает [10, 30, 50, 70, 90] (включая соседние)
    """
    context = SwingContext(
        swing_points=[SwingPoint(i, 100.0, 'peak') for i in [10, 30, 50, 70, 90]],
        indices=[10, 30, 50, 70, 90]
    )
    result = context.slice(30, 70)
    assert [sp.index for sp in result] == [10, 30, 50, 70, 90]
```

**test_empty_swing_context()** - SwingContext с пустым списком
```python
def test_empty_swing_context():
    """
    Цель: Проверить обработку пустого SwingContext

    Given: SwingContext(swing_points=[], indices=[])
    When: slice(20, 40) или aggregate_for_zone(20, 40)
    Then: Возвращает пустой результат (не исключение)
    """
    empty_context = SwingContext(swing_points=[], indices=[])
    result = empty_context.slice(20, 40)
    assert result == []

    metrics = empty_context.aggregate_for_zone(20, 40)
    assert metrics.num_swings == 0
    assert metrics.avg_amplitude == 0.0
```

**5.2.2. Дополнительные Performance тесты**:

**test_memory_consumption_estimate()** - Оценка потребления памяти
```python
def test_memory_consumption_estimate():
    """
    Цель: Проверить что фактическое потребление памяти близко к оценке (264 bytes/point)

    When: Создать 1000 SwingPoint объектов
    Then: sys.getsizeof(SwingContext) ≈ 264KB ± 50% tolerance
    """
    swing_points = [
        SwingPoint(i, 100.0 + i * 0.1, 'peak' if i % 2 == 0 else 'trough')
        for i in range(1000)
    ]
    context = SwingContext(swing_points=swing_points, indices=list(range(1000)))

    actual_bytes = sys.getsizeof(context)
    expected_bytes = 264 * 1000  # 264 bytes per point
    tolerance = 0.5  # 50% tolerance

    assert actual_bytes < expected_bytes * (1 + tolerance)
    assert actual_bytes > expected_bytes * (1 - tolerance)
```

**benchmark_global_vs_perzone()** - Сравнительный benchmark производительности
```python
def benchmark_global_vs_perzone():
    """
    Цель: Измерить разницу во времени выполнения для разных размеров датасета

    Датасеты: 10k, 50k, 100k bars
    Режимы: global vs per_zone
    Критерий: global ≤ 1.5× время per_zone
    """
    for dataset_size in [10_000, 50_000, 100_000]:
        data = generate_synthetic_data(dataset_size)
        zones = detect_zones(data)

        # Benchmark global mode
        start = time.perf_counter()
        global_context = strategy.calculate_global(data)
        for zone in zones:
            zone_swings = global_context.slice(zone.start_idx, zone.end_idx)
        global_time = time.perf_counter() - start

        # Benchmark per_zone mode
        start = time.perf_counter()
        for zone in zones:
            zone_data = data.iloc[zone.start_idx:zone.end_idx+1]
            zone_context = strategy.calculate(zone_data)
        perzone_time = time.perf_counter() - start

        ratio = global_time / perzone_time
        print(f"{dataset_size} bars: global {global_time:.3f}s, per_zone {perzone_time:.3f}s, ratio {ratio:.2f}×")
        assert ratio <= 1.5, f"Global mode too slow: {ratio:.2f}× per_zone"
```

**5.2.3. Дополнительный Comparative тест**:

**compare_swing_coverage()** - Сравнение покрытия в реальном сценарии (уже описан выше, строки 1670-1685)

---

**✅ Post-completion checklist Фазы 5**:

### 🚨 ФАЗА 5.1: MVP TESTING (БЛОКИРУЕТ РЕЛИЗ)

**A. MVP Unit-тесты** (tests/unit/test_swing_global_calculation.py):
- [ ] **ТЕСТ СОЗДАН**: test_zigzag_global_vs_isolated() - искусственные данные, global находит больше свингов
- [ ] **ТЕСТ СОЗДАН**: test_swing_context_slice_with_neighbors() - SwingContext.slice() включает соседние точки
- [ ] **ТЕСТ СОЗДАН**: test_adaptive_thresholds_global_mode() - адаптивная стратегия, _global_threshold_cache заполнен

**B. MVP Edge Case тесты** (tests/unit/test_swing_edge_cases.py) - КРИТИЧЕСКИ ВАЖНО:
- [ ] **ТЕСТ СОЗДАН**: test_single_bar_zone() - зона [50:50], возвращает соседние пивоты, metrics.num_swings == 0
- [ ] **ТЕСТ СОЗДАН**: test_zone_at_dataset_boundaries() - зоны [0:10] и [90:99], отсутствие IndexError

**C. MVP Integration тесты** (tests/integration/test_pipeline_global_swings.py):
- [ ] **ТЕСТ СОЗДАН**: test_pipeline_global_swing_scope() - полный pipeline с .with_swing_scope('global'), все зоны имеют swing_context
- [ ] **ТЕСТ СОЗДАН**: test_fallback_to_per_zone() - некорректные данные, WARNING в логах, продолжение выполнения

**Критерии успеха MVP (БЛОКИРУЕТ РЕЛИЗ)**:
- [ ] ✅ **Все 3 unit-теста проходят**
- [ ] ✅ **Оба edge case теста проходят** (БЕЗ IndexError)
- [ ] ✅ **Оба integration теста проходят** (pipeline работает + fallback работает)

**❌ Если хоть один MVP тест НЕ проходит → РЕЛИЗ БЛОКИРОВАН**

---

### ⭐ ФАЗА 5.2: COMPREHENSIVE TESTING (НЕ БЛОКИРУЕТ РЕЛИЗ)

**D. Дополнительные Edge Case тесты** (tests/unit/test_swing_edge_cases.py):
- [ ] **ТЕСТ СОЗДАН**: test_zone_without_internal_swings() - зона [20:40] между пивотами [10, 50], 2 точки и 1 свинг
- [ ] **ТЕСТ СОЗДАН**: test_overlapping_zones() - зоны [20:60] и [40:80], swing_context одинаковый объект
- [ ] **ТЕСТ СОЗДАН**: test_zone_with_all_peaks_or_all_troughs() - только peaks в зоне, отсутствие division by zero
- [ ] **ТЕСТ СОЗДАН**: test_zone_exactly_matching_swing_boundaries() - границы [30:70] точно на пивотах, включение соседних
- [ ] **ТЕСТ СОЗДАН**: test_empty_swing_context() - SwingContext с пустым списком, empty metrics

**E. Сравнительные тесты** (research/notebooks/test_global_swing_coverage.py):
- [ ] **ТЕСТ СОЗДАН**: compare_swing_coverage() - запустить 05_case_study в обоих режимах, сравнить pct_with_swings

**F. Performance и Memory тесты** (tests/performance/):
- [ ] **ТЕСТ СОЗДАН**: test_memory_consumption_estimate() - создать 1000 SwingPoint, измерить через sys.getsizeof(), проверить ~264 bytes/point ±50%
- [ ] **BENCHMARK СОЗДАН**: benchmark_global_vs_perzone() - датасеты 10k, 50k, 100k баров, измерить время выполнения

**Критерии успеха Comprehensive (ПОВЫШАЕТ CONFIDENCE, но НЕ блокирует релиз)**:
- [ ] ⭐ Все 5 дополнительных edge case тестов проходят
- [ ] ⭐ Сравнительный тест показывает улучшение: global mode 70-90% coverage vs per_zone 20-60%
- [ ] ⭐ Memory test: фактическое потребление < 400 bytes/point (264 bytes + 50% tolerance)
- [ ] ⭐ Benchmark: global mode НЕ медленнее чем 1.5× per_zone

**✅ Если Comprehensive тесты НЕ проходят → можно выпустить релиз с предупреждением (warning), исправить в следующей версии**

**Future validation (проверка готовности предыдущих фаз)**:
- [ ] 🔄 **РЕТРОСПЕКТИВА Фазы 1**: Smoke tests из Фазы 1 теперь покрыты формальными unit-тестами
- [ ] 🔄 **РЕТРОСПЕКТИВА Фазы 2**: Smoke tests из Фазы 2 теперь покрыты формальными unit-тестами
- [ ] 🔄 **РЕТРОСПЕКТИВА Фазы 3**: Smoke tests из Фазы 3 теперь покрыты integration-тестами
- [ ] 🔄 **РЕТРОСПЕКТИВА Фазы 4**: Smoke tests из Фазы 4 теперь покрыты integration-тестами

**Если хоть один тест НЕ проходит**:
1. Определить в какой фазе (1-4) был допущен баг
2. Вернуться в ту фазу и исправить код
3. Перезапустить все тесты снова
4. Только когда ВСЕ тесты зелёные → двигаться в Фазу 6

### Фаза 6.1: MVP Documentation (Week 4, Day 3) - БЛОКИРУЕТ РЕЛИЗ
**Приоритет: ВЫСОКИЙ**

**ВАЖНО**: Фаза 6 разделена на **MVP (минимальная документация для релиза)** и **Comprehensive (полная документация)**.

MVP документация **блокирует релиз**, Comprehensive документация **желательна** но может быть создана после релиза.

**📖 Обязательное pre-reading**:
- **Раздел 11** - "Итоговые преимущества" - ключевые выгоды для документирования
- **Раздел 4.2** - "Builder API" - примеры для migration guide
- **Раздел 12** - "Резюме" - ключевые сообщения для migration guide

---

**6.1.1. Docstrings в коде** (КРИТИЧЕСКИ ВАЖНО):

✅ **Обновить docstrings во всех новых/изменённых классах и методах**:

```python
# bquant/analysis/zones/models.py
@dataclass
class SwingPoint:
    """Представление одной swing точки (пик или впадина) в ценовом ряде.

    Attributes:
        index: Позиция точки в исходном датасете (integer index)
        value: Цена в этой точке (float)
        swing_type: Тип точки - 'peak' (максимум) или 'trough' (минимум)

    Example:
        >>> sp = SwingPoint(index=42, value=1850.5, swing_type='peak')
        >>> sp.index
        42
    """
    index: int
    value: float
    swing_type: Literal['peak', 'trough']

@dataclass
class SwingContext:
    """Глобальный контекст swing точек для всего датасета.

    Используется для эффективного хранения и извлечения swing точек
    для любой зоны без повторного расчёта.

    Attributes:
        swing_points: Список всех swing точек для датасета
        indices: Отсортированный список индексов swing_points для быстрого поиска

    Methods:
        slice(start_idx, end_idx): Извлечь swing точки для зоны [start_idx:end_idx]
        aggregate_for_zone(start_idx, end_idx): Рассчитать SwingMetrics для зоны

    Example:
        >>> context = SwingContext(
        ...     swing_points=[SwingPoint(10, 100.0, 'peak'), SwingPoint(30, 95.0, 'trough')],
        ...     indices=[10, 30]
        ... )
        >>> zone_swings = context.slice(5, 35)  # Включает соседние точки
        >>> len(zone_swings)
        2
    """
    swing_points: List[SwingPoint]
    indices: List[int]

    def slice(self, start_idx: int, end_idx: int) -> List[SwingPoint]:
        """Извлечь swing точки для зоны с включением соседних точек.

        Args:
            start_idx: Начальный индекс зоны (inclusive)
            end_idx: Конечный индекс зоны (inclusive)

        Returns:
            Список SwingPoint внутри зоны ПЛЮС один соседний слева и справа

        Example:
            >>> context.indices = [10, 30, 50, 70, 90]
            >>> result = context.slice(40, 60)  # Зона [40:60]
            >>> [sp.index for sp in result]
            [30, 50, 70]  # Включает соседние 30 и 70
        """
        ...

@dataclass
class ZoneInfo:
    """Информация о MACD зоне с результатами анализа.

    Attributes:
        swing_context: Глобальный SwingContext (NEW in v0.X.Y)
            Заполняется только в global режиме, None в per_zone режиме

    Methods:
        get_zone_swings() -> List[SwingPoint]:
            Рекомендуемый способ получения swing точек для зоны.
            Автоматически использует swing_context.slice() если доступен.
    """
    swing_context: Optional[SwingContext] = None

    def get_zone_swings(self) -> List[SwingPoint]:
        """Получить swing точки для этой зоны.

        Returns:
            Список SwingPoint внутри зоны (с соседними точками)
            Пустой список если swing_context не заполнен

        Example:
            >>> zone.swing_context = global_context
            >>> swings = zone.get_zone_swings()
            >>> len(swings)
            5  # Зависит от зоны и стратегии
        """
        ...
```

```python
# bquant/analysis/zones/pipeline.py
class ZoneAnalysisBuilder:
    """Builder для настройки ZoneAnalysisPipeline.

    Methods:
        with_swing_scope(scope: Literal['per_zone', 'global']) -> Self:
            Настроить режим расчёта swing точек (NEW in v0.X.Y)
    """

    def with_swing_scope(self, scope: Literal['per_zone', 'global']) -> 'ZoneAnalysisBuilder':
        """Установить режим расчёта swing точек.

        Args:
            scope: 'per_zone' (default) - рассчитывать для каждой зоны отдельно
                   'global' - рассчитать один раз для всего датасета

        Returns:
            Self для method chaining

        Example:
            >>> result = (
            ...     analyze_zones(data)
            ...     .with_strategies(swing='zigzag')
            ...     .with_swing_scope('global')  # Рекомендуется для 70-90% coverage
            ...     .build()
            ... )
        """
        ...

class ZoneAnalysisPipeline:
    """Пайплайн для анализа MACD зон."""

    def _calculate_global_swings(self, data: pd.DataFrame) -> SwingContext:
        """Рассчитать swing точки для всего датасета один раз.

        Вызывается только в global режиме. Использует strategy.calculate_global().

        Args:
            data: Полный датасет с OHLCV колонками

        Returns:
            SwingContext со всеми swing точками для датасета

        Raises:
            ValueError: Если swing_strategy не установлена
        """
        ...
```

```python
# bquant/analysis/zones/strategies/base.py
class SwingCalculationStrategy(Protocol):
    """Протокол для стратегий расчёта swing точек.

    Methods:
        calculate(data): Legacy метод для per_zone режима
        calculate_global(data): Новый метод для global режима (v0.X.Y)
        aggregate_for_zone(context, start_idx, end_idx): Агрегация метрик
    """

    def calculate_global(self, data: pd.DataFrame) -> SwingContext:
        """Рассчитать swing точки для всего датасета.

        Args:
            data: DataFrame с колонками ['time', 'open', 'high', 'low', 'close']

        Returns:
            SwingContext со всеми swing точками

        Example:
            >>> strategy = ZigZagSwingStrategy(threshold=0.02)
            >>> context = strategy.calculate_global(data)
            >>> len(context.swing_points)
            127  # Зависит от данных и threshold
        """
        ...
```

**6.1.2. CHANGELOG.md** (ОБЯЗАТЕЛЬНО):

✅ **`CHANGELOG.md`** (ОБНОВИТЬ)
```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- Global swing calculation mode for zone analysis (`with_swing_scope('global')`)
- `SwingPoint` and `SwingContext` data models for efficient swing storage
- `ZoneInfo.swing_context` field for accessing global swing context
- `ZoneInfo.get_zone_swings()` helper method
- Cache versioning system (CACHE_VERSION = 2) for schema upgrades

### Changed
- `SwingCalculationStrategy` protocol extended with `calculate_global()` and `aggregate_for_zone()`
- Zone coverage with swing metrics improved: 70-90% (global mode) vs 18-62% (per_zone mode)

### Fixed
- Boundary artifacts in per_zone swing calculation causing low zone coverage
- Cache collisions between different strategy parameters

### Migration
See `docs/migration/global_swings_migration.md` for upgrade instructions.
```

**6.1.3. Short Migration Guide** (ОБЯЗАТЕЛЬНО):

✅ **`docs/migration/global_swings_migration.md`** (СОЗДАТЬ НОВЫЙ) - КРАТКАЯ ВЕРСИЯ

```markdown
# Migration to Global Swing Calculation

## Why Migrate?

**Problem**: Per-zone swing calculation suffers from boundary artifacts, leading to low zone coverage:
- find_peaks: 18.9% zones have swing metrics
- pivot_points: 8.1% zones have swing metrics
- zigzag: 62.2% zones have swing metrics

**Solution**: Global mode calculates swings once for entire dataset, then slices for each zone:
- **70-90% zone coverage** (improvement: +20-50 percentage points)
- **Faster**: 1 calculation instead of N
- **Consistent**: No boundary artifacts

## Migration Steps

### Step 1: Update pipeline configuration

```python
# BEFORE (per_zone mode - implicit default)
result = (
    analyze_zones(data)
    .with_strategies(swing='zigzag')
    .build()
)

# AFTER (global mode - add one line)
result = (
    analyze_zones(data)
    .with_strategies(swing='zigzag')
    .with_swing_scope('global')  # ← ADD THIS
    .build()
)
```

### Step 2: Access swing points (if needed)

```python
# Recommended API
for zone in result.zones:
    swings = zone.get_zone_swings()  # Returns List[SwingPoint]
    print(f"Zone {zone.id}: {len(swings)} swing points")
```

### Step 3: Clear cache (one-time)

Old cached results are automatically invalidated. If you see "Cache invalidated due to schema upgrade" in logs - this is expected.

## Breaking Changes

**None** - per_zone mode remains the default. Global mode is opt-in via `with_swing_scope('global')`.

## Troubleshooting

**Q**: "I'm getting warnings about cache invalidation"
**A**: Normal - cache version changed from 1 to 2. Old caches are automatically invalidated.

**Q**: "Global mode is slower than per_zone"
**A**: Global mode is faster when you have many zones. For <10 zones, per_zone may be faster.

**Q**: "Some zones still have no swings"
**A**: Even in global mode, zones can have no internal swings (e.g., single-bar zones). This is expected.

## Performance

- **Recommended**: Datasets <1M bars
- **Benchmark**: Global mode ≤1.5× per_zone time for 100k bars, 100 zones
- **Memory**: ~264 bytes per swing point

## Next Steps

For detailed examples and API reference, see:
- User Guide: `docs/user_guide/zone_analysis.md` (Section "Global vs Per-Zone Swing Calculation")
- API Reference: `docs/api/analysis/zones/models.md` (SwingPoint, SwingContext)
```

---

### Фаза 6.2: Comprehensive Documentation (Post-MVP, optional) - НЕ БЛОКИРУЕТ РЕЛИЗ

**ВАЖНО**: Эта документация **повышает usability** и помогает пользователям, но **НЕ блокирует релиз**. Может быть создана после выкатки MVP.

**6.2.1. User Guide - Обновления**:

1. ✅ **`docs/user_guide/zone_analysis.md`** (ОБНОВИТЬ)
   - Добавить раздел "Global vs Per-Zone Swing Calculation"
   - Примеры использования `.with_swing_scope('global')`
   - Сравнительная таблица режимов (преимущества, использование)
   - Код примеры с визуализацией результатов

2. ✅ **`docs/user_guide/swing_strategies.md`** (СОЗДАТЬ НОВЫЙ)
   - Обзор всех доступных swing стратегий
   - Параметры каждой стратегии (ZigZag, FindPeaks, PivotPoints)
   - Рекомендации по выбору стратегии для разных сценариев
   - Примеры настройки адаптивных порогов

**6.2.2. API Reference - Обновления**:

3. ✅ **`docs/api/analysis/zones/models.md`** (ОБНОВИТЬ)
   - `SwingPoint` dataclass - полная спецификация полей
   - `SwingContext` dataclass - методы и использование
   - `ZoneInfo.swing_context` - новое поле
   - `ZoneInfo.get_zone_swings()` - API метод

4. ✅ **`docs/api/analysis/zones/pipeline.md`** (ОБНОВИТЬ)
   - `ZoneAnalysisPipeline._calculate_global_swings()` - новый метод
   - `ZoneAnalysisPipeline._inject_swing_context()` - новый метод
   - `ZoneAnalysisBuilder.with_swing_scope()` - новый метод
   - Обновлённый workflow diagram

5. ✅ **`docs/api/analysis/zones/strategies.md`** (ОБНОВИТЬ)
   - `SwingCalculationStrategy` protocol - новые методы
   - `calculate_global()` - спецификация
   - `aggregate_for_zone()` - спецификация
   - Обновление для ZigZagSwingStrategy, FindPeaksSwingStrategy

**6.2.3. Research Notebooks - Обновления**:

6. ✅ **`research/notebooks/05_case_study_zone_consistency.py`** (ОБНОВИТЬ)
   - Добавить сравнение per_zone vs global режимов
   - Визуализация различий в покрытии зон
   - Статистический анализ улучшений
   - Обновить выводы с новыми результатами

7. ✅ **`research/notebooks/06_swing_strategy_comparison.py`** (СОЗДАТЬ НОВЫЙ)
   - Сравнение ZigZag, FindPeaks, PivotPoints на одних данных
   - Запуск отдельных пайплайнов для каждой стратегии
   - Performance benchmarks для каждой стратегии
   - Рекомендации по выбору стратегии

**6.2.4. Examples - Обновления**:

8. ✅ **`examples/zone_analysis_global_swings.py`** (СОЗДАТЬ НОВЫЙ)
    - Минимальный пример global режима
    - Визуализация результатов
    - Сравнение с per_zone режимом

---

**✅ Post-completion checklist Фазы 6**:

### 🚨 ФАЗА 6.1: MVP DOCUMENTATION (БЛОКИРУЕТ РЕЛИЗ)

**A. Docstrings в коде** (КРИТИЧЕСКИ ВАЖНО):
- [ ] **ОБНОВЛЕНЫ**: bquant/analysis/zones/models.py - SwingPoint, SwingContext, ZoneInfo (Google Style)
- [ ] **ОБНОВЛЕНЫ**: bquant/analysis/zones/pipeline.py - ZoneAnalysisBuilder.with_swing_scope(), _calculate_global_swings()
- [ ] **ОБНОВЛЕНЫ**: bquant/analysis/zones/strategies/base.py - SwingCalculationStrategy.calculate_global()
- [ ] **ТЕСТ**: Запустить `python -m pydoc bquant.analysis.zones.models` - проверить корректный парсинг

**B. CHANGELOG.md** (ОБЯЗАТЕЛЬНО):
- [ ] **CHANGELOG.md ОБНОВЛЁН**: Добавлен раздел [X.Y.Z] с датой релиза
- [ ] Секция "Added": SwingPoint, SwingContext, with_swing_scope('global'), cache versioning
- [ ] Секция "Changed": SwingCalculationStrategy protocol extended, 70-90% coverage
- [ ] Секция "Fixed": Boundary artifacts, low zone coverage (18-62% → 70-90%)
- [ ] Секция "Migration": Ссылка на docs/migration/global_swings_migration.md
- [ ] **REVIEW**: Changelog прошёл code review

**C. Short Migration Guide** (ОБЯЗАТЕЛЬНО):
- [ ] **ДОКУМЕНТ СОЗДАН**: docs/migration/global_swings_migration.md
- [ ] Секция "Why Migrate?" с метриками: 18-62% → 70-90% coverage
- [ ] Секция "Migration Steps" с before/after code examples
- [ ] Секция "Troubleshooting" с FAQ (cache invalidation, performance, empty swings)
- [ ] **ТЕСТ**: Выполнить миграцию по guide на sample data, убедиться что работает

**Критерии успеха MVP Documentation (БЛОКИРУЕТ РЕЛИЗ)**:
- [ ] ✅ **Все docstrings в новых классах присутствуют** и корректно парсятся
- [ ] ✅ **CHANGELOG.md содержит все изменения** (Added/Changed/Fixed/Migration)
- [ ] ✅ **Migration guide протестирован** на sample data и работает

**❌ Если хоть один MVP документ отсутствует → РЕЛИЗ БЛОКИРОВАН**

---

### ⭐ ФАЗА 6.2: COMPREHENSIVE DOCUMENTATION (НЕ БЛОКИРУЕТ РЕЛИЗ)

**D. User Guides** (желательно):
- [ ] **ДОКУМЕНТ ОБНОВЛЁН**: docs/user_guide/zone_analysis.md - раздел "Global vs Per-Zone Swing Calculation"
- [ ] **ДОКУМЕНТ СОЗДАН**: docs/user_guide/swing_strategies.md - обзор ZigZag/FindPeaks/PivotPoints
- [ ] **ТЕСТ**: Запустить все примеры кода из user guides

**E. API Reference** (желательно):
- [ ] **ДОКУМЕНТ ОБНОВЛЁН**: docs/api/analysis/zones/models.md - полная спецификация SwingPoint, SwingContext
- [ ] **ДОКУМЕНТ ОБНОВЛЁН**: docs/api/analysis/zones/pipeline.md - workflow diagram с global mode
- [ ] **ДОКУМЕНТ ОБНОВЛЁН**: docs/api/analysis/zones/strategies.md - протокол с 3 методами
- [ ] **ТЕСТ**: Проверить все code snippets совпадают с реальным кодом

**F. Research Notebooks** (желательно):
- [ ] **СКРИПТ ОБНОВЛЁН**: research/notebooks/05_case_study_zone_consistency.py - сравнение per_zone vs global
- [ ] **СКРИПТ СОЗДАН**: research/notebooks/06_swing_strategy_comparison.py - сравнение стратегий
- [ ] **ТЕСТ**: Запустить оба скрипта, проверить визуализации

**G. Examples** (желательно):
- [ ] **ПРИМЕР СОЗДАН**: examples/zone_analysis_global_swings.py - минимальный working example
- [ ] **ТЕСТ**: Запустить пример, проверить output

**Критерии успеха Comprehensive Documentation (ПОВЫШАЕТ USABILITY, но НЕ блокирует релиз)**:
- [ ] ⭐ Все 2 user guides обновлены/созданы
- [ ] ⭐ Все 3 API reference docs обновлены
- [ ] ⭐ Оба research notebooks работают
- [ ] ⭐ Example запускается и показывает разницу режимов

**✅ Если Comprehensive документация НЕ готова → можно выпустить релиз с пометкой "documentation in progress"**

---

**Future validation (финальная проверка)**:
- [ ] 🎯 **MVP ГОТОВ**: Фазы 1-6.1 завершены, все MVP тесты зелёные, MVP документация готова
- [ ] 🎯 **READY FOR RELEASE**: Code review пройден, changelog утверждён, можно создавать release tag
- [ ] 📚 **POST-RELEASE**: Фазы 5.2 и 6.2 (Comprehensive) можно завершить после релиза

---

## 9. Совместимость, кэширование и fallback

### 9.1. Обратная совместимость
- ✅ **Default = "per_zone"**: Старое поведение сохраняется по умолчанию
- ✅ **Legacy метод `calculate()`**: Продолжает работать для old code
- ✅ **Автоматический fallback**: Если глобальный расчёт не удался → откат на per_zone

### 9.2. Кэширование с учётом swing стратегий
```python
# В bquant/analysis/zones/cache.py

class ZoneAnalysisCache:
    """
    Кэш результатов анализа зон.

    UPDATED: Разделение кэша по swing_scope И параметрам стратегий
    """

    def _generate_cache_key(self, config: ZoneAnalysisConfig, data_hash: str) -> str:
        """
        Генерация ключа кэша.

        CRITICAL UPDATE: Включает имена и параметры swing стратегий для предотвращения коллизий

        Проблема без этого:
            - ZigZag(legs=10, deviation=0.05) и ZigZag(legs=20, deviation=0.10)
              получили бы один кэш-ключ → некорректные результаты!
            - Переключение между стратегиями ('zigzag' → 'find_peaks')
              возвращало бы старые результаты

        Решение:
            - Хэшировать все параметры каждой стратегии
            - Включить имена стратегий в ключ
        """
        key_parts = [
            f"data={data_hash}",
            f"indicator={config.indicator_config.to_hash()}",
            f"detection={config.detection_config.to_hash()}",
            f"swing_scope={config.swing_scope}",  # Режим расчёта
            # ... other parts ...
        ]

        # НОВОЕ: Добавление swing стратегий с параметрами
        swing_strategies_hash = self._hash_swing_strategies(config)
        if swing_strategies_hash:
            key_parts.append(f"swing={swing_strategies_hash}")

        return hashlib.sha256('|'.join(key_parts).encode()).hexdigest()

    def _hash_swing_strategies(self, config: ZoneAnalysisConfig) -> str:
        """
        Генерация хэша для swing стратегии.

        NEW METHOD

        Args:
            config: Конфигурация анализа зон

        Returns:
            Хэш строка вида "zigzag_legs10_dev0.05"

        Example:
            config._swing_strategy = ZigZagSwingStrategy(legs=10, deviation=0.05)
            hash = _hash_swing_strategies(config)
            # → "zigzag_dev005_legs10"
        """
        if not hasattr(config, '_swing_strategy') or config._swing_strategy is None:
            return ""

        strategy = config._swing_strategy
        strategy_name = strategy.get_metadata()['name'].lower()
        params_hash = self._hash_strategy_params(strategy.config_hash())

        return f"{strategy_name}_{params_hash}"

    def _hash_strategy_params(self, params: Dict[str, Any]) -> str:
        """
        Генерация короткого хэша параметров стратегии.

        NEW METHOD

        Args:
            params: Dict с параметрами стратегии из config_hash()

        Returns:
            Короткая строка вида "legs10_dev0.05"

        Example:
            params = {'legs': 10, 'deviation': 0.05}
            hash = _hash_strategy_params(params)
            # → "dev0.05_legs10" (alphabetically sorted keys)
        """
        if not params:
            return "default"

        # Сортировка ключей для консистентности
        sorted_params = sorted(params.items())

        # Короткие имена для распространённых параметров
        short_names = {
            'legs': 'legs',
            'deviation': 'dev',
            'distance': 'dist',
            'prominence': 'prom',
            'window': 'win',
            'min_amplitude_pct': 'amp'
        }

        parts = []
        for key, value in sorted_params:
            short_key = short_names.get(key, key[:4])  # Первые 4 символа если нет mapping
            # Форматирование значения
            if isinstance(value, float):
                formatted_value = f"{value:.2f}".replace('.', '')
            else:
                formatted_value = str(value)
            parts.append(f"{short_key}{formatted_value}")

        return '_'.join(parts)


# ПОЛНЫЙ ПРИМЕР КЭШ-КЛЮЧА:

# Конфигурация:
# - Data: XAUUSD 1H, 10000 bars
# - MACD: fast=12, slow=26, signal=9
# - Detection: zero_crossing
# - Swing: ZigZag(legs=10, deviation=0.05)
# - Scope: global

# Сгенерированный ключ:
# "data=a3f2b8c1...
#  indicator=macd_fast12_slow26_sig9...
#  detection=zero_crossing...
#  swing_scope=global...
#  swing=zigzag_dev005_legs10"
# → SHA256 → "e7a9c4f2d8b3..."

# Если изменить deviation на 0.10:
# swing=zigzag_dev010_legs10
# → SHA256 → "f1b8d5c3a2e7..." ← ДРУГОЙ ключ! ✅
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

### 9.4. Миграция существующих кэшей

**Проблема**: Результаты, закэшированные до внедрения global mode, не содержат поле `swing_context` в ZoneInfo.

**Сценарий**:
```python
# До обновления: пользователь запустил анализ с per_zone (implicit default)
result_old = analyze_zones(data).build()
# → Результат закэширован БЕЗ поля swing_context

# После обновления: пользователь запускает тот же анализ
result_new = analyze_zones(data).with_swing_scope('global').build()
# → Что произойдёт с существующим кэшем?
```

**Риски без миграции**:
1. Десериализация старого кэша упадёт, если SwingContext стал обязательным полем
2. Коллизии кэш-ключей, если `swing_scope` не участвует в хэшировании
3. Использование старых результатов в новом коде приведёт к AttributeError

---

**Стратегия миграции** (рекомендуется для Phase 1):

**Option A: Cache Invalidation** ✅ РЕКОМЕНДУЕТСЯ

Автоматическая инвалидация всех старых кэшей при обновлении.

**Двусторонняя схема (bidirectional flow)**:
1. **WRITE**: `save()` записывает `cache_version: 2` в payload при сохранении
2. **READ**: `load()` читает `cache_version` из payload и сравнивает с `CACHE_VERSION`
3. **KEY**: `_generate_cache_key()` включает версию в ключ (опционально, для namespace isolation)

```python
# В bquant/analysis/zones/cache.py

class ZoneAnalysisCache:
    CACHE_VERSION = 2  # НОВОЕ: Увеличено с 1 до 2

    def _generate_cache_key(self, config: ZoneAnalysisConfig, data_hash: str) -> str:
        """
        UPDATED: Включает версию кэша в ключ
        """
        key_parts = [
            f"version={self.CACHE_VERSION}",  # ← НОВОЕ
            f"data={data_hash}",
            # ... остальные части
        ]
        return hashlib.sha256('|'.join(key_parts).encode()).hexdigest()

    def save(self, cache_key: str, result: ZoneAnalysisResult) -> None:
        """
        UPDATED: Сохранение результата с версией схемы (WRITE path)
        """
        serialized_data = {
            'cache_version': self.CACHE_VERSION,  # ← НОВОЕ: Явно записываем версию в payload
            'result': self._serialize(result),
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'schema': 'ZoneAnalysisResult_v2',  # Для debugging
                'bquant_version': __version__
            }
        }

        self._write_to_disk(cache_key, serialized_data)
        self.logger.debug(
            f"Saved cache with version {self.CACHE_VERSION}: {cache_key[:12]}..."
        )

    def load(self, cache_key: str) -> Optional[ZoneAnalysisResult]:
        """
        UPDATED: Проверка версии при загрузке (READ path)
        """
        cached_data = self._read_from_disk(cache_key)

        if cached_data is None:
            return None

        # Проверка версии
        cached_version = cached_data.get('cache_version', 1)  # Default 1 для старых кэшей

        if cached_version < self.CACHE_VERSION:
            self.logger.info(
                f"Cache invalidated due to schema upgrade "
                f"(v{cached_version} → v{self.CACHE_VERSION}). "
                f"Recalculating analysis..."
            )
            return None  # Инвалидация старого кэша

        return self._deserialize(cached_data['result'])
```

**Пример сохранённого payload** (для понимания формата):

```json
{
  "cache_version": 2,
  "result": {
    "zones": [...],
    "swing_context": {...},
    ...
  },
  "metadata": {
    "created_at": "2025-11-10T14:32:15.123456",
    "schema": "ZoneAnalysisResult_v2",
    "bquant_version": "0.3.0"
  }
}
```

Старые кэши (v1) не имеют поля `cache_version`, поэтому `cached_data.get('cache_version', 1)` вернёт `1`, что меньше `CACHE_VERSION = 2`, и кэш будет инвалидирован.

---

**Преимущества**:
- ✅ Простая реализация (одно число инкрементировать)
- ✅ Гарантирует корректность (нет смешивания old/new форматов)
- ✅ Автоматическая (пользователь ничего не делает)
- ✅ Для production кэши обычно ephemeral (можно пересчитать)

**Недостатки**:
- ⚠️ Первый запуск после обновления будет медленнее (пересчёт)
- ⚠️ Потеря накопленных кэшей (для больших датасетов это может быть дорого)

---

**Option B: Backward Compatible Deserialization** (для будущих версий)

Поддержка старого формата при десериализации.

```python
def _deserialize(self, cached_data: Dict) -> ZoneAnalysisResult:
    """
    FUTURE: Поддержка нескольких версий формата
    """
    version = cached_data.get('cache_version', 1)

    if version == 1:
        # Legacy формат: добавляем swing_context = None ко всем зонам
        for zone_data in cached_data['zones']:
            if 'swing_context' not in zone_data:
                zone_data['swing_context'] = None

    # Далее обычная десериализация
    return ZoneAnalysisResult.from_dict(cached_data)
```

**Когда использовать**:
- Кэши дорогие (cloud storage, большие датасеты)
- Нужна плавная миграция без пересчётов

**Для текущей версии**: НЕ рекомендуется (усложняет код без явной выгоды)

---

**Реализация для Phase 1**:

**Фаза 1, задача 1.5** (НОВАЯ):
- [ ] Добавить `CACHE_VERSION = 2` в ZoneAnalysisCache
- [ ] Обновить `_generate_cache_key()` - включить version в ключ
- [ ] Обновить `load()` - проверять версию и инвалидировать старые кэши
- [ ] Логировать INFO при инвалидации

**Фаза 5, тест** (НОВЫЙ):
- [ ] **ТЕСТ СОЗДАН**: test_cache_invalidation_on_version_upgrade() - создать кэш v1, попытаться загрузить с CACHE_VERSION=2, проверить что вернулся None и залогирован INFO

---

## 10. Риски и меры

### Риск 1: Границы пивотов
**Проблема**: Некорректная нарезка может обрезать свинги на границах зон.

**Мера**: Алгоритм `slice()` с захватом соседних пивотов (bisect_left/right + расширение на 1 элемент).

**Тест**: Unit-тест на пограничные случаи (зона начинается ровно на пивоте, зона между двумя пивотами, и т.д.)

### Риск 2: Потребление памяти на больших датасетах
**Проблема**: SwingContext хранит все swing points в памяти. На очень больших датасетах (>1M баров) с плотными свингами это может привести к значительному потреблению памяти.

**Оценка размера SwingPoint**:
```python
# Размер одного SwingPoint объекта в памяти
import sys

@dataclass
class SwingPoint:
    point_id: int           # 28 bytes (Python int object)
    timestamp: datetime     # 48 bytes (datetime object)
    index: int              # 28 bytes
    price: float            # 24 bytes (Python float)
    swing_type: str         # 49+ bytes (string "peak"/"trough" + overhead)
    amplitude_to_next: Optional[float]  # 24 bytes + 8 (Optional overhead)
    duration_to_next: Optional[int]     # 28 bytes + 8
    strategy_name: str      # ~55 bytes (e.g., "zigzag" + overhead)
    strategy_params: Dict   # ~240 bytes (dict with 2-3 keys)

# Итого: ~264 bytes per SwingPoint (приблизительно)
```

**Примеры потребления памяти**:

| Датасет      | Bars    | Swings (5% deviation) | Memory (SwingContext) |
|--------------|---------|----------------------|----------------------|
| XAUUSD 1H    | 10,000  | ~50-100              | 13-26 KB             |
| XAUUSD 1H    | 100,000 | ~500-1,000           | 130-260 KB           |
| XAUUSD 1M    | 1,000,000| ~5,000-10,000       | 1.3-2.6 MB           |
| Multi-pair 1M| 10,000,000| ~50,000-100,000    | 13-26 MB             |

**Оценка**: Для большинства real-world сценариев (<1M bars) потребление памяти **приемлемо** (<3 MB).

---

**Решение в текущей версии**:

- **Нет специальных оптимизаций** - используем стандартные Python dataclasses
- **Recommendation**: Для датасетов >1M баров использовать per_zone режим

**Рекомендации по использованию**:
- ✅ **Датасеты <100k баров**: Никаких ограничений, используйте global mode
- ⚠️ **Датасеты 100k-1M баров**: Мониторить потребление памяти (~1-3 MB)
- ❌ **Датасет >1M баров**: Использовать per_zone режим или разбить данные на периоды

**Тест для проверки оценки**:
```python
def test_memory_consumption_estimate():
    """Проверка оценки потребления памяти."""
    # Создать SwingContext с 1000 точек
    # Измерить фактическую память через sys.getsizeof + gc
    # Сравнить с оценкой ~264 bytes/point
    assert actual_memory < estimated_memory * 1.5  # 50% tolerance
```

---

**Возможные оптимизации (НЕ в scope текущей реализации)**:

Если в будущем возникнет потребность в датасетах >5M баров, см. **[future_optimizations.md](future_optimizations.md)** для детального описания с псевдокодом:
- **Lazy Loading**: Загрузка SwingPoint по требованию из disk cache (~83% экономия памяти)
- **Chunking**: Разбиение датасета на временные интервалы (support для >10M bars)
- **Numpy structured arrays**: ~50% экономии памяти вместо Python objects
- **MemoryError fallback**: Автоматический откат на per_zone при нехватке памяти

Эти оптимизации **не требуются** для типичных use cases (<1M bars) и будут реализованы только при наличии **измеренной** реальной потребности (после profiling и cost-benefit analysis).

### Риск 3: Производительность
**Проблема**: Глобальный расчёт на больших датасетах (>100k баров) может быть медленным.

**Меры**:
- ✅ Глобальный расчёт выполняется **один раз** (vs N раз для N зон)
- ✅ Bisect для нарезки → O(log N) поиск
- ✅ Профилирование на больших датасетах
- ✅ См. Риск 2 для memory-performance tradeoffs

**Benchmark**: Сравнить время выполнения для датасета 10k, 50k, 100k баров.

### Риск 4: Расширяемость стратегий
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

## 12. Матрица покрытия плана (Coverage Matrix)

Эта таблица гарантирует, что **всё содержание документа учтено в плане разработки** (раздел 8). Каждый описательный раздел (1-7, 9-11) должен иметь хотя бы одну ссылку из фаз 1-6.

| Раздел документа | Используется в фазе | Тип использования | Статус |
|------------------|-------------------|-------------------|---------|
| **1. Новые модели данных** | | | |
| 1.1 SwingPoint dataclass | Фаза 1, задача 1.1 | Спецификация (строки 55-101) | ✅ |
| 1.2 SwingContext dataclass | Фаза 1, задача 1.2 | Спецификация + алгоритм slice() (строки 103-200) | ✅ |
| 1.3 Обновление ZoneInfo | Фаза 1, задача 1.3 | Спецификация API (строки 202-264) | ✅ |
| **2. Расширение конфигурации** | | | |
| 2.1 swing_scope в ZoneAnalysisConfig | Фаза 1, задача 1.4 | Спецификация поля (строки 268-300) | ✅ |
| **3. Обновление API стратегий** | | | |
| 3.1 Протокол SwingCalculationStrategy | Фаза 2, задача 2.1 | Спецификация протокола (строки 310-401) | ✅ |
| 3.2 Пример ZigZagSwingStrategy | Фаза 2, задачи 2.2-2.4 | Реализация calculate_global(), aggregate_for_zone() (строки 403-689) | ✅ |
| **4. Обновление ZoneAnalysisPipeline** | | | |
| 4.1 Новые методы Pipeline | Фаза 3, задачи 3.1-3.3 | _calculate_global_swings(), _inject_swing_context() (строки 693-805) | ✅ |
| 4.2 Builder API with_swing_scope() | Фаза 3, задача 3.4 | Спецификация метода + примеры (строки 807-867) | ✅ |
| **5. Обновление ZoneFeaturesAnalyzer** | | | |
| 5.1 extract_zone_features() логика | Фаза 4, задача 4.1 | Ветвление global/per_zone (строки 869-942) | ✅ |
| **6. Адаптивные пороги** | | | |
| 6.1 _AdaptiveSwingStrategy глобальный режим | Фаза 2, задача 2.7 | Реализация (строки 946-992) | ✅ |
| **7. Схема воркфлоу** | | | |
| 7.1 Диаграмма обновлённого workflow | Фаза 3, задача 3.3 (pre-reading) | Визуализация (строки 996-1028) | ✅ |
| **9. Совместимость и кэширование** | | | |
| 9.1 Обратная совместимость | Фазы 1-6 (принцип) | Design constraint | ✅ |
| 9.2 Кэширование swing стратегий | Фаза 1, задача 1.4 | Hash generation для cache keys (строки 1487-1621) | ✅ |
| 9.3 Graceful Degradation | Фаза 3, задача 3.3 | Fallback логика (строки 1623-1636) | ✅ |
| **10. Риски и меры** | | | |
| 10. Риск 1: Границы пивотов | Фаза 5: Edge case тесты | test_single_bar_zone(), test_zone_at_dataset_boundaries() (строки 1642-1648) | ✅ |
| 10. Риск 2: Потребление памяти | Фаза 1, задача 1.2 (constraint) <br> Фаза 5: Memory тесты | Design constraint (строки 1649-1752) <br> test_memory_consumption_estimate() | ✅ |
| 10. Риск 3: Производительность | Фаза 5: Benchmark тесты | Benchmark 10k/50k/100k баров (строки 1754-1763) | ✅ |
| 10. Риск 4: Расширяемость стратегий | Фаза 2, задача 2.1 (pre-reading) | Protocol design (строки 1765-1770) | ✅ |
| **11. Итоговые преимущества** | | | |
| 11.1-11.5 Все преимущества | Фаза 6: Документация | Контент для migration guide и user guide (строки 2076-2104) | ✅ |

### Проверка полноты покрытия

**Покрыты все ключевые разделы**: ✅

- Раздел 1: Модели → Фаза 1 (все 3 подраздела)
- Раздел 2: Конфигурация → Фаза 1
- Раздел 3: Стратегии → Фаза 2 (все подразделы)
- Раздел 4: Pipeline → Фаза 3 (все подразделы)
- Раздел 5: Features Analyzer → Фаза 4
- Раздел 6: Адаптивные пороги → Фаза 2
- Раздел 7: Воркфлоу → Фаза 3 (pre-reading)
- Раздел 9: Совместимость → Фазы 1, 3 (design constraints)
- Раздел 10: Риски → Фазы 1, 2, 5 (constraints + tests)
- Раздел 11: Преимущества → Фаза 6 (documentation)

**Нет неиспользованного контента**: ✅

Все описательные разделы (1-7, 9-11) имеют минимум одну явную ссылку из плана разработки (раздел 8, Фазы 1-6).

**Вывод**: План разработки (раздел 8) полностью покрывает всё содержание документа. При работе по плану разработчик будет использовать ВСЕ спецификации, примеры, риски и преимущества, описанные в документе.

---

## 13. Резюме

Введя глобальный расчёт свингов и последующую нарезку пивотов на зоны, мы получим:

1. **Согласованный набор метрик**, совпадающий с результатами глобального ZigZag
2. **Устранение искажений** анализа из-за изолированного расчёта
3. **Повышение воспроизводимости** результатов
4. **Закладку основы** для дальнейшего развития свинговых стратегий
5. **Обратную совместимость** с существующим кодом через fallback

**Рекомендуемая последовательность реализации**: Фазы 1→2→3→4→5→6

**Ожидаемый эффект на 05_case_study**: Покрытие зон свингами увеличится с 20-60% до 70-90% в зависимости от стратегии.

---

## 14. Метрики успешности внедрения (Acceptance Criteria)

Этот раздел определяет **количественные критерии приёмки** для объективного решения о готовности к релизу.

### 14.1. Корректность (Correctness)

**KPI 1: Zone Coverage with Swings**
- **Baseline** (текущее состояние): 18-62% зон имеют swing метрики в per_zone режиме
  - `find_peaks`: 18.9% (7/37 зон)
  - `pivot_points`: 8.1% (3/37 зон)
  - `zigzag`: 62.2% (23/37 зон)
- **Target** (целевое значение): ≥70% зон имеют swing метрики в global режиме
- **Измерение**: Запустить `research/notebooks/05_case_study_zone_consistency.py` на XAUUSD 1H dataset
- **Критерий приёмки**:
  - ✅ Улучшение минимум на **+20 percentage points** для каждой стратегии
  - ✅ Все стратегии достигают ≥70% coverage

**KPI 2: Consistency with Manual Analysis**
- **Baseline**: Per_zone свинги НЕ совпадают с "ручным" ZigZag на полном датасете (потеря граничных пивотов)
- **Target**: Global свинги точно совпадают с ZigZag, построенным на полном датасете
- **Измерение**: Визуальное сравнение на 10 случайных зонах
- **Критерий приёмки**:
  - ✅ 100% визуальное совпадение (нет потерянных пивотов на границах)
  - ✅ Количество обнаруженных swings совпадает с global ZigZag ±1 точка

---

### 14.2. Производительность (Performance)

**KPI 3: Execution Time**
- **Baseline**: N вызовов стратегии (для N зон, например N=30 на типичном датасете)
- **Target**: 1 вызов стратегии + N быстрых slice операций
- **Измерение**: Benchmark на датасете 100 зон × 10,000 bars
- **Критерий приёмки**:
  - ✅ Global mode ≤ **1.5×** время per_zone mode
  - ⚠️ Допустим небольшой overhead на slice/aggregate, но НЕ должно быть медленнее более чем в 1.5 раза

**KPI 4: Memory Consumption**
- **Target**: < 3 MB для типичных датасетов (100k bars, 5% deviation → ~500-1000 swings)
- **Измерение**: `test_memory_consumption_estimate()` из Фазы 5
- **Критерий приёмки**:
  - ✅ SwingContext фактически потребляет **~264 bytes/point ±50%** (т.е. < 400 bytes/point)
  - ✅ Для 100k bars датасета: memory < 500 KB

---

### 14.3. Стабильность (Stability)

**KPI 5: Edge Cases Handling**
- **Target**: Все 7 edge case тестов проходят без исключений
- **Измерение**: Запустить `tests/unit/test_swing_edge_cases.py`
- **Критерий приёмки**:
  - ✅ Нет `IndexError` на границах датасета (test_zone_at_dataset_boundaries)
  - ✅ Нет `division by zero` при асимметричных свингах (test_zone_with_all_peaks_or_all_troughs)
  - ✅ Graceful handling пустых контекстов (test_empty_swing_context)
  - ✅ Корректная обработка single-bar зон (test_single_bar_zone)
  - ✅ ВСЕ 7 тестов зелёные

**KPI 6: Backward Compatibility**
- **Target**: Существующий код продолжает работать без изменений
- **Критерий приёмки**:
  - ✅ Default режим = `per_zone` (старое поведение сохранено)
  - ✅ Legacy метод `calculate()` работает как раньше
  - ✅ Нет breaking changes в public API (все тесты старого кода проходят)

---

### 14.4. Документация (Documentation)

**KPI 7: Migration Success Rate**
- **Target**: Пользователь может мигрировать на global mode за < 5 минут
- **Измерение**: Пройти migration guide на реальном проекте (dry run)
- **Критерий приёмки**:
  - ✅ Добавление `.with_swing_scope('global')` - **единственное** изменение кода
  - ✅ Migration guide содержит working examples (протестированы)
  - ✅ Troubleshooting section покрывает типичные проблемы

---

### 14.5. Acceptance Workflow

**Процесс принятия решения о релизе**:

```
1. Phase 5 завершена
   ↓
2. Запустить все тесты (unit + integration + edge cases)
   ↓
3. Измерить KPI 1-7 и записать фактические значения
   ↓
4. Проверка критериев:
   ├─ KPI 1: Zone Coverage ≥70%?
   ├─ KPI 2: Visual Match 100%?
   ├─ KPI 3: Performance ≤1.5× baseline?
   ├─ KPI 4: Memory < 3 MB for 100k bars?
   ├─ KPI 5: All 7 edge cases pass?
   ├─ KPI 6: Backward compatibility OK?
   └─ KPI 7: Migration < 5 min?
   ↓
5a. Если хоть один KPI НЕ достигнут:
    → Вернуться в соответствующую фазу (1-4)
    → Исправить проблему
    → Перезапустить workflow с шага 1
   ↓
5b. Если ВСЕ KPI достигнуты:
    → Phase 6 (Documentation)
    ↓
6. Code Review
   ↓
7. ✅ READY FOR RELEASE
```

### 14.6. Tracking Template

Заполнить после завершения Phase 5:

| KPI | Target | Actual | Status | Notes |
|-----|--------|--------|--------|-------|
| KPI 1: Coverage (find_peaks) | ≥70% | ___% | ⏳ | Baseline: 18.9% |
| KPI 1: Coverage (pivot_points) | ≥70% | ___% | ⏳ | Baseline: 8.1% |
| KPI 1: Coverage (zigzag) | ≥70% | ___% | ⏳ | Baseline: 62.2% |
| KPI 2: Visual Match | 100% | ___% | ⏳ | 10/10 zones |
| KPI 3: Performance | ≤1.5× | ___× | ⏳ | 100 zones × 10k bars |
| KPI 4: Memory | <3 MB | ___ MB | ⏳ | 100k bars dataset |
| KPI 5: Edge Cases | 7/7 pass | ___/7 | ⏳ | No exceptions |
| KPI 6: Backward Compat | No breaks | ___  | ⏳ | Old tests pass |
| KPI 7: Migration Time | <5 min | ___ min | ⏳ | Dry run |

**Критерий релиза**: ВСЕ статусы = ✅

---
