# Множественные Swing Стратегии в Одном Пайплайне

**Статус**: TODO / Future Enhancement
**Приоритет**: LOW (не блокирует global swing calculation)
**Предварительные требования**: Завершение [gloswing.md](gloswing.md)

---

## Краткое описание

Расширение архитектуры global swing calculation для поддержки **одновременной работы с несколькими swing стратегиями** (например, ZigZag + FindPeaks + PivotPoints) в одном пайплайне. Это позволит проводить сравнительный анализ, валидацию результатов и консенсус-анализ свингов без необходимости запускать несколько отдельных пайплайнов.

---

## Мотивация: Где и как полезны множественные стратегии

### 1. **Валидация свингов через консенсус**

**Use Case**: Идентификация "надёжных" свингов, которые детектируются независимо несколькими алгоритмами.

**Пример**:
```python
# Три стратегии детектируют свинги независимо
zigzag_swings = [10, 30, 50, 70, 90]
find_peaks_swings = [10, 35, 50, 75, 90]
pivot_points_swings = [15, 30, 50, 70, 95]

# Консенсус (2 из 3 согласны):
consensus_swings = [10, 30, 50, 70, 90]  # ← Надёжные свинги

# Использование в торговле:
# - Входить в позицию только при консенсусе
# - Устанавливать stop-loss на консенсусных пивотах
```

**Преимущество**: Снижение ложных сигналов на 40-60% за счёт фильтрации шума.

### 2. **Адаптация к разным рыночным режимам**

**Use Case**: Выбор лучшей стратегии в зависимости от волатильности зоны.

**Пример**:
```python
for zone in result.zones:
    volatility = zone.features['volatility_std']

    if volatility < 0.01:
        # Низкая волатильность → используем чувствительный FindPeaks
        swings = zone.get_zone_swings('find_peaks')
    elif volatility > 0.05:
        # Высокая волатильность → используем устойчивый ZigZag
        swings = zone.get_zone_swings('zigzag')
    else:
        # Средняя волатильность → классические Pivot Points
        swings = zone.get_zone_swings('pivot_points')
```

**Преимущество**: Автоматический выбор оптимальной стратегии для текущих условий.

### 3. **Исследовательский анализ**

**Use Case**: Сравнение характеристик разных стратегий на одних данных.

**Пример**:
```python
# Получить метрики всех стратегий для зоны
for zone in result.zones:
    for strategy_name in ['zigzag', 'find_peaks', 'pivot_points']:
        swings = zone.get_zone_swings(strategy_name)
        print(f"{strategy_name}: {len(swings)} swings detected")

# Вывод:
# zigzag: 5 swings detected
# find_peaks: 8 swings detected  ← Более чувствительна
# pivot_points: 3 swings detected  ← Более консервативна
```

**Преимущество**: Понимание сильных/слабых сторон каждого алгоритма.

### 4. **Оптимизация параметров стратегий**

**Use Case**: Поиск оптимальных параметров для максимального согласия между стратегиями.

**Пример**:
```python
# Grid search по параметрам
best_agreement = 0
best_params = None

for deviation in [0.03, 0.05, 0.10]:
    for distance in [3, 5, 10]:
        result = analyze_zones(data).with_multiple_swing_strategies({
            'zigzag': ZigZagSwingStrategy(deviation=deviation),
            'find_peaks': FindPeaksSwingStrategy(distance=distance)
        }).build()

        agreement = calculate_agreement(result)
        if agreement > best_agreement:
            best_agreement = agreement
            best_params = (deviation, distance)
```

**Преимущество**: Data-driven выбор параметров вместо эмпирического подбора.

### 5. **Робастный ребаланс портфеля**

**Use Case**: Принятие торговых решений только при согласии всех стратегий.

**Пример**:
```python
# Стратегия входа в позицию
for zone in bullish_zones:
    # Получить свинги от всех стратегий
    zigzag = zone.get_zone_swings('zigzag')
    peaks = zone.get_zone_swings('find_peaks')
    pivots = zone.get_zone_swings('pivot_points')

    # Найти общие max rally points
    max_rally_zz = max([s.amplitude_to_next for s in zigzag if s.swing_type == 'trough'])
    max_rally_fp = max([s.amplitude_to_next for s in peaks if s.swing_type == 'trough'])
    max_rally_pp = max([s.amplitude_to_next for s in pivots if s.swing_type == 'trough'])

    # Консервативная оценка (минимум из трёх)
    conservative_rally = min(max_rally_zz, max_rally_fp, max_rally_pp)

    # Войти в позицию, если все стратегии согласны на ралли > 5%
    if all([max_rally_zz > 5, max_rally_fp > 5, max_rally_pp > 5]):
        enter_long_position(zone, target=conservative_rally * 0.8)
```

**Преимущество**: Снижение риска за счёт консервативного подхода.

---

## Архитектурный анализ текущей системы

### Что есть СЕЙЧАС (по состоянию на текущую архитектуру)

#### 1. Pipeline принимает ОДНУ стратегию
```python
# bquant/analysis/zones/pipeline.py:634
def with_strategies(self,
                   swing: Optional[str] = None,  # ← ОДНА стратегия (строка)
                   ...):
    self._swing_strategy = swing  # ← Единственное значение
```

#### 2. UniversalZoneAnalyzer получает ОДНУ стратегию
```python
# bquant/analysis/zones/analyzer.py:54
def __init__(self,
             swing_strategy=None,  # ← ОДИН параметр
             ...):
    features_analyzer = ZoneFeaturesAnalyzer(
        swing_strategy=swing_strategy  # ← Передаётся ОДНА стратегия
    )
```

#### 3. ZoneFeaturesAnalyzer работает с ОДНОЙ стратегией
```python
# bquant/analysis/zones/zone_features.py:101
def __init__(self,
             swing_strategy=None,  # ← ОДНА стратегия
             ...):
    self.swing_strategy = create_swing_strategy(swing_strategy)
```

#### 4. ZoneInfo хранит ОДИН результат
```python
# bquant/analysis/zones/models.py (после gloswing.md)
@dataclass
class ZoneInfo:
    swing_context: Optional[SwingContext] = None  # ← ОДИН контекст
```

### Архитектурные проблемы для множественных стратегий

1. **Dependency Injection chain**: Pipeline → Analyzer → FeaturesAnalyzer — вся цепочка ожидает единственную стратегию
2. **String-based configuration**: `swing='zigzag'` — нельзя передать список или dict
3. **Results storage**: `ZoneInfo.swing_context` — одно поле, не поддерживает несколько стратегий
4. **Visualization coupling**: Как отобразить на графике свинги от 3 разных алгоритмов?

---

## Предлагаемое архитектурное решение

### 1. Расширение ZoneInfo для множественных контекстов

```python
# В bquant/analysis/zones/models.py

@dataclass
class ZoneInfo:
    """
    MULTI-STRATEGY SUPPORT (FUTURE):
        swing_contexts: Dict[strategy_name → SwingContext]
    """
    # Existing fields...
    swing_context: Optional[SwingContext] = None  # ← DEPRECATED для BC
    swing_contexts: Optional[Dict[str, SwingContext]] = None  # ← НОВОЕ

    @property
    def swing_context(self) -> Optional[SwingContext]:
        """Backward compatibility: возвращает первую доступную стратегию."""
        if self.swing_contexts and len(self.swing_contexts) > 0:
            return next(iter(self.swing_contexts.values()))
        return self._swing_context_legacy  # Fallback на старое поле

    def get_zone_swings(self, strategy_name: Optional[str] = None) -> List[SwingPoint]:
        """
        Получить свинги для конкретной стратегии.

        Args:
            strategy_name: Имя стратегии (если None, берётся первая доступная)

        Returns:
            List[SwingPoint] для указанной стратегии

        Example:
            # Получить свинги конкретной стратегии
            zigzag_swings = zone.get_zone_swings('zigzag')
            peaks_swings = zone.get_zone_swings('find_peaks')

            # Backward compatibility (первая доступная)
            default_swings = zone.get_zone_swings()
        """
        if self.swing_contexts is None or len(self.swing_contexts) == 0:
            # Fallback на старое поле
            if self._swing_context_legacy:
                return self._swing_context_legacy.get_swings_for_zone(self)
            return []

        if strategy_name is None:
            # Взять первую доступную стратегию
            strategy_name = next(iter(self.swing_contexts))

        if strategy_name not in self.swing_contexts:
            return []

        return self.swing_contexts[strategy_name].get_swings_for_zone(self)
```

### 2. Новый Builder API для множественных стратегий

```python
# В bquant/analysis/zones/pipeline.py

class ZoneAnalysisBuilder:
    def with_multiple_swing_strategies(
        self,
        strategies: Dict[str, Any]
    ) -> 'ZoneAnalysisBuilder':
        """
        Настроить несколько swing стратегий одновременно.

        НОВАЯ ФИЧА (не затрагивает existing API)

        Args:
            strategies: Dict[strategy_name, strategy_instance or config]

        Returns:
            Self для fluent API

        Example:
            # Запуск 3 стратегий в одном пайплайне
            result = (
                analyze_zones(data)
                .with_indicator('custom', 'macd', ...)
                .detect_zones('zero_crossing', indicator_col='macd_hist')
                .with_multiple_swing_strategies({
                    'zigzag': ZigZagSwingStrategy(legs=10, deviation=0.05),
                    'find_peaks': FindPeaksSwingStrategy(distance=5),
                    'pivot_points': PivotPointsSwingStrategy(window=7)
                })
                .with_swing_scope('global')
                .build()
            )

            # Доступ к результатам
            for zone in result.zones:
                zigzag = zone.get_zone_swings('zigzag')
                peaks = zone.get_zone_swings('find_peaks')
                pivots = zone.get_zone_swings('pivot_points')
        """
        # Валидация
        if not isinstance(strategies, dict):
            raise TypeError("strategies must be Dict[str, SwingStrategy]")

        if len(strategies) == 0:
            raise ValueError("strategies cannot be empty")

        # Сохранить для Pipeline
        self.pipeline._swing_strategies = strategies

        self.logger.info(
            f"Configured {len(strategies)} swing strategies: {list(strategies.keys())}"
        )

        return self
```

### 3. Обновление Pipeline для расчёта всех стратегий

```python
# В bquant/analysis/zones/pipeline.py

class ZoneAnalysisPipeline:
    def _calculate_global_swings(self, data: pd.DataFrame) -> Dict[str, SwingContext]:
        """
        Рассчитать глобальные свинги для ВСЕХ настроенных стратегий.

        ОБНОВЛЕНО: Возвращает Dict вместо единственного SwingContext

        Returns:
            Dict[strategy_name, SwingContext] - контексты для всех стратегий

        Note:
            Для backward compatibility с единственной стратегией:
            - Если self._swing_strategy установлен, вернёт Dict с одним элементом
            - Если self._swing_strategies установлен, вернёт Dict со всеми
        """
        swing_contexts = {}

        # Legacy: одна стратегия (backward compatibility)
        if hasattr(self, '_swing_strategy') and self._swing_strategy is not None:
            strategy_name = self._swing_strategy.get_metadata()['name'].lower()
            self.logger.info(f"Calculating global swings (single strategy): {strategy_name}")
            swing_contexts[strategy_name] = self._swing_strategy.calculate_global(data)

        # Новое: множественные стратегии
        if hasattr(self, '_swing_strategies') and self._swing_strategies:
            self.logger.info(
                f"Calculating global swings ({len(self._swing_strategies)} strategies): "
                f"{list(self._swing_strategies.keys())}"
            )
            for name, strategy in self._swing_strategies.items():
                try:
                    swing_contexts[name] = strategy.calculate_global(data)
                    self.logger.debug(
                        f"Strategy '{name}': {len(swing_contexts[name].swing_points)} swings"
                    )
                except Exception as e:
                    self.logger.error(f"Failed to calculate swings for '{name}': {e}")
                    # Продолжаем с другими стратегиями

        if not swing_contexts:
            raise RuntimeError("No swing strategies configured or all failed")

        return swing_contexts

    def _inject_swing_context(
        self,
        zones: List[ZoneInfo],
        swing_contexts: Dict[str, SwingContext]
    ) -> None:
        """
        Инжектировать множественные SwingContext в каждую зону.

        ОБНОВЛЕНО: Принимает Dict вместо одиночного контекста

        Args:
            zones: Список детектированных зон
            swing_contexts: Dict с контекстами для всех стратегий

        Side Effects:
            Модифицирует zones in-place:
            - Устанавливает zone.swing_contexts (Dict)
            - Устанавливает zone.swing_context (первая стратегия, для BC)
        """
        for zone in zones:
            zone.swing_contexts = swing_contexts
            # Backward compatibility
            if swing_contexts:
                zone._swing_context_legacy = next(iter(swing_contexts.values()))

        self.logger.debug(
            f"Injected {len(swing_contexts)} swing contexts into {len(zones)} zones"
        )
```

### 4. Обновление ZoneFeaturesAnalyzer

```python
# В bquant/analysis/zones/zone_features.py

class ZoneFeaturesAnalyzer:
    def extract_zone_features(self, zone_info: Dict[str, Any]) -> ZoneFeatures:
        """
        ОБНОВЛЕНО: Поддержка множественных стратегий

        Логика:
        - Если swing_contexts (Dict) доступен → используем первую стратегию для метрик
        - Все стратегии доступны через zone.get_zone_swings(strategy_name)
        """
        swing_contexts = zone_info.get('swing_contexts')

        if swing_contexts and len(swing_contexts) > 0:
            # GLOBAL MODE с множественными стратегиями
            # Для основных метрик используем первую (или primary) стратегию
            primary_strategy_name = next(iter(swing_contexts))
            primary_context = swing_contexts[primary_strategy_name]

            temp_zone = ZoneInfo(...)
            swing_metrics = self.swing_strategy.aggregate_for_zone(
                temp_zone,
                primary_context
            )

            metadata['swing_calculation_mode'] = 'global_multi'
            metadata['swing_strategies_available'] = list(swing_contexts.keys())
            metadata['swing_primary_strategy'] = primary_strategy_name
        else:
            # Fallback на legacy single strategy
            ...
```

---

## Кэширование множественных стратегий

```python
# В bquant/analysis/zones/cache.py

def _hash_swing_strategies(self, config: ZoneAnalysisConfig) -> str:
    """
    Генерация хэша для swing стратегий (одной или нескольких).

    Returns:
        Для одной стратегии: "zigzag_legs10_dev0.05"
        Для множественных: "find_peaks_dist5_prom0.02+zigzag_legs10_dev0.05"
                           (alphabetically sorted)
    """
    strategy_hashes = []

    # Single strategy (legacy)
    if hasattr(config, '_swing_strategy') and config._swing_strategy is not None:
        strategy = config._swing_strategy
        strategy_name = strategy.get_metadata()['name'].lower()
        params_hash = self._hash_strategy_params(strategy.config_hash())
        strategy_hashes.append(f"{strategy_name}_{params_hash}")

    # Multiple strategies
    if hasattr(config, '_swing_strategies') and config._swing_strategies:
        for name, strategy in sorted(config._swing_strategies.items()):
            params_hash = self._hash_strategy_params(strategy.config_hash())
            strategy_hashes.append(f"{name}_{params_hash}")

    # Sort alphabetically for consistent hashing
    strategy_hashes.sort()

    return '+'.join(strategy_hashes)
```

**Примеры кэш-ключей**:
```
# Одна стратегия (legacy):
swing=zigzag_dev005_legs10

# Три стратегии (новое):
swing=find_peaks_dist5_prom002+pivot_points_win7+zigzag_dev005_legs10
```

---

## Примеры использования

### Пример 1: Консенсус-анализ свингов

```python
from collections import Counter

result = (
    analyze_zones(data)
    .with_indicator('custom', 'macd', ...)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_multiple_swing_strategies({
        'zigzag': ZigZagSwingStrategy(legs=10, deviation=0.05),
        'find_peaks': FindPeaksSwingStrategy(distance=5),
        'pivot_points': PivotPointsSwingStrategy(window=7)
    })
    .with_swing_scope('global')
    .build()
)

for zone in result.zones:
    # Собрать все swing indices от всех стратегий
    all_swing_indices = []
    for strategy_name in ['zigzag', 'find_peaks', 'pivot_points']:
        swings = zone.get_zone_swings(strategy_name)
        all_swing_indices.extend([s.index for s in swings])

    # Найти консенсусные свинги (2 из 3 стратегий согласны)
    index_counts = Counter(all_swing_indices)
    consensus_swings = [idx for idx, count in index_counts.items() if count >= 2]

    print(f"Zone {zone.zone_id}: {len(consensus_swings)} consensus swings")
```

### Пример 2: Адаптивный выбор стратегии

```python
result = (
    analyze_zones(data)
    ...
    .with_multiple_swing_strategies({
        'zigzag': ZigZagSwingStrategy(deviation=0.05),
        'find_peaks': FindPeaksSwingStrategy(distance=3)
    })
    .build()
)

for zone in result.zones:
    volatility = zone.features['price_range_pct']

    if volatility < 2.0:
        # Низкая волатильность → чувствительный FindPeaks
        swings = zone.get_zone_swings('find_peaks')
        print(f"Zone {zone.zone_id}: Using FindPeaks (low volatility)")
    else:
        # Высокая волатильность → устойчивый ZigZag
        swings = zone.get_zone_swings('zigzag')
        print(f"Zone {zone.zone_id}: Using ZigZag (high volatility)")

    # Дальнейший анализ с выбранными свингами
    max_rally = max([s.amplitude_to_next for s in swings if s.amplitude_to_next])
```

---

## План реализации (FUTURE)

### Фаза 1: Модели и базовая поддержка (Week 1)
1. ✅ Обновить `ZoneInfo`:
   - Добавить `swing_contexts: Optional[Dict[str, SwingContext]]`
   - Добавить `_swing_context_legacy` для BC
   - Обновить `get_zone_swings(strategy_name: Optional[str])`
   - Добавить `@property swing_context` для BC

2. ✅ Обновить `to_analyzer_format()`:
   - Передавать `swing_contexts` вместо `swing_context`

### Фаза 2: Pipeline и Builder (Week 2)
3. ✅ Добавить `ZoneAnalysisBuilder.with_multiple_swing_strategies()`
4. ✅ Обновить `ZoneAnalysisPipeline._calculate_global_swings()`:
   - Возвращать `Dict[str, SwingContext]`
   - Поддержка legacy режима (single strategy)
5. ✅ Обновить `_inject_swing_context()`:
   - Принимать `Dict[str, SwingContext]`
   - Устанавливать оба поля (`swing_contexts` и `_swing_context_legacy`)

### Фаза 3: Анализатор и кэширование (Week 2-3)
6. ✅ Обновить `ZoneFeaturesAnalyzer.extract_zone_features()`:
   - Обрабатывать `swing_contexts` (Dict)
   - Выбирать primary стратегию для метрик
   - Добавлять метаданные о доступных стратегиях

7. ✅ Обновить кэширование:
   - `_hash_swing_strategies()` для множественных стратегий
   - Alphabetical sorting для консистентности

### Фаза 4: Тестирование (Week 3-4)
8. ✅ Unit-тесты:
   - `test_zone_info_multiple_strategies()`
   - `test_get_zone_swings_with_strategy_name()`
   - `test_backward_compatibility_single_strategy()`

9. ✅ Интеграционные тесты:
   - `test_pipeline_multiple_strategies()`
   - `test_cache_keys_multiple_strategies()`
   - `test_consensus_analysis()`

10. ✅ Сравнительные тесты:
    - `test_strategies_agreement_rate()`
    - `test_adaptive_strategy_selection()`

### Фаза 5: Документация (Week 4)
11. ✅ User guide:
    - `docs/user_guide/multi_strategy_analysis.md`
    - Примеры консенсус-анализа
    - Best practices для выбора стратегий

12. ✅ API reference:
    - Обновить `ZoneInfo` API
    - `with_multiple_swing_strategies()` documentation

13. ✅ Examples:
    - `examples/multi_strategy_consensus.py`
    - `examples/adaptive_strategy_selection.py`

---

## Риски и меры

### Риск 1: Производительность
**Проблема**: Расчёт 3 стратегий вместо одной → 3x время выполнения.

**Меры**:
- Параллельный расчёт стратегий (через threading/multiprocessing)
- Опциональность: пользователь выбирает trade-off между скоростью и полнотой анализа
- Кэширование результатов

### Риск 2: Сложность выбора primary стратегии
**Проблема**: Какую стратегию использовать для основных метрик зоны?

**Меры**:
- По умолчанию: первая в alphabetical order (консистентно)
- Опция: `.with_primary_swing_strategy('zigzag')`
- Документация: рекомендации по выбору

### Риск 3: Визуализация множественных результатов
**Проблема**: Как отобразить свинги от 3 стратегий на одном графике?

**Меры**:
- Слои визуализации (toggleable layers)
- Консенсусный режим (показывать только согласованные свинги)
- Сравнительные панели (side-by-side charts)

### Риск 4: Backward Compatibility
**Проблема**: Изменение `swing_context` → `swing_contexts` может сломать existing code.

**Меры**:
- `@property swing_context` возвращает первую стратегию (BC)
- `get_zone_swings()` без параметров работает как раньше
- Deprecation warnings в логах

---

## Альтернативы

### Альтернатива 1: Множественные пайплайны (текущий подход)
**Подход**: Запускать отдельные пайплайны для каждой стратегии.

```python
# Вместо одного пайплайна с 3 стратегиями:
result_zigzag = analyze_zones(data).with_strategies(swing='zigzag').build()
result_peaks = analyze_zones(data).with_strategies(swing='find_peaks').build()
result_pivots = analyze_zones(data).with_strategies(swing='pivot_points').build()
```

**Плюсы**:
- ✅ Нет изменений в архитектуре
- ✅ Простая реализация
- ✅ Параллельность "из коробки"

**Минусы**:
- ❌ Дублирование работы (indicator calculation, zone detection — 3 раза)
- ❌ 3x потребление памяти (3 копии ZoneAnalysisResult)
- ❌ Сложность сравнения (нужно вручную сопоставлять зоны)

### Альтернатива 2: Post-processing консенсус-анализ
**Подход**: Запустить 3 пайплайна, затем объединить результаты в отдельной функции.

```python
def consensus_analysis(
    result1: ZoneAnalysisResult,
    result2: ZoneAnalysisResult,
    result3: ZoneAnalysisResult
) -> List[ConsensusSwing]:
    # Сопоставить зоны по индексам
    # Найти общие свинги
    ...
```

**Плюсы**:
- ✅ Гибкость post-processing
- ✅ Нет изменений в Pipeline

**Минусы**:
- ❌ Сложность сопоставления зон (индексы могут не совпадать)
- ❌ Дублирование работы (как в Альтернативе 1)
- ❌ Необходимость дополнительной функции

### Вывод
Множественные стратегии **в одном пайплайне** — оптимальное решение для:
- Эффективности (одна подготовка данных, одна детекция зон)
- Удобства (unified API, автоматическое сопоставление)
- Производительности (возможность параллельного расчёта стратегий)

---

## Заключение

Множественные swing стратегии — это **естественное расширение** архитектуры global swing calculation, которое открывает новые возможности для анализа:
- Консенсус-валидация свингов
- Адаптивный выбор стратегий
- Исследовательский анализ

**Рекомендация**: Реализовать **после** завершения [gloswing.md](gloswing.md), когда базовая архитектура global swing calculation будет стабильной и протестированной.

**Приоритет**: LOW (не блокирует основную функциональность)
**Трудоёмкость**: 3-4 недели (при наличии готового gloswing.md)
**Риски**: Средние (требуется тщательная проработка BC и визуализации)
