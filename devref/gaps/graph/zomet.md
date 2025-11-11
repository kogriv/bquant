# Zone Metrics Visualization Enhancement

**Дата создания**: 2025-11-07
**Дата обновления**: 2025-11-11 (ревизия 6.0: критическое обновление после реализации gloswing.md)
**Статус**: Готов к реализации
**Приоритет**: ВЫСОКИЙ

## Контекст

В результате аналитического исследования ([05_case_study_zone_consistency.py](../../../research/notebooks/05_case_study_zone_consistency.py)) была подтверждена состоятельность MACD bull-зон: средние ап-свинги статистически превосходят даун-свинги (p-value 0.0015 < 0.05 для zigzag стратегии). См. отчет: [macd_zone_consistency_case_study.md](../../../docs/analytics/zones/macd_zone_consistency_case_study.md).

Однако текущий визуализатор не позволяет:
1. Видеть сами **свинг-точки** (разворотные точки, экстремумы) на графике
2. Отображать **свинг-метрики и шейп-метрики** при детальном просмотре зоны
3. Видеть **агрегированную статистику по метрикам** в режиме overview
4. Управлять существующим блоком `show_zone_stats` так, чтобы он не конфликтовал с новыми карточками метрик

Это ограничивает возможность визуальной проверки результатов анализа и понимания внутренней структуры зон.

---

## Текущее состояние реализации (2025-11-11)

### ✅ Готовые компоненты

**Глобальный расчёт свингов (gloswing.md)** — **ПОЛНОСТЬЮ РЕАЛИЗОВАН**:
- ✅ `SwingPoint` и `SwingContext` в `bquant/analysis/zones/models.py:33-173`
- ✅ `ZoneInfo.swing_context` — поле доступно (models.py:207)
- ✅ `ZoneInfo.get_zone_swings()` — метод работает (models.py:214-230)
- ✅ Pipeline API `.with_swing_scope('global')` функционирует
- ✅ Тесты: `tests/integration/test_pipeline_global_swings.py` проходят
- ✅ Примеры: `examples/zone_analysis_global_swings.py`
- ✅ Документация: `docs/user_guide/swing_strategies.md`

**Расчёт метрик**:
- ✅ `swing_metrics` автоматически рассчитываются в `bquant/analysis/zones/zone_features.py:403-425`
- ✅ `shape_metrics` автоматически рассчитываются в `zone_features.py:428-450`
- ✅ Метрики сохраняются в `zone.features['metadata']['swing_metrics']` и `zone.features['metadata']['shape_metrics']`

### ❌ Отсутствующие компоненты (предмет данного документа)

**Визуализация**:
- ❌ Методы `_extract_zone_metrics()`, `_add_zone_metrics_annotation()` в `zones.py`
- ❌ Метод `_aggregate_zone_metrics()` для агрегации статистики
- ❌ Метод `_add_swing_overlay()` для отображения свинг-точек
- ❌ Обновление `_normalize_zone()` для сохранения `swing_context` и `original_zone`

### 🚀 Готовность к разработке

**Все 3 этапа можно начинать НЕМЕДЛЕННО** (все зависимости выполнены)

---

## Зависимости

### ✅ ЗАВИСИМОСТЬ ВЫПОЛНЕНА (2025-11-10)

Глобальный расчёт свингов из [gloswing.md](../swing/gloswing.md) **ПОЛНОСТЬЮ РЕАЛИЗОВАН**.

**Доступные компоненты**:
```python
from bquant.analysis.zones.models import SwingPoint, SwingContext, ZoneInfo

# SwingContext содержит все необходимые координаты
zone.swing_context  # SwingContext | None
zone.get_zone_swings()  # List[SwingPoint]

# Pipeline API
result = (
    analyze_zones(df)
    .with_swing_scope('global')  # ✅ Работает!
    .build()
)
```

**Ключевое преимущество**: `SwingContext` уже содержит все координаты свинг-точек (`SwingPoint.timestamp`, `SwingPoint.index`, `SwingPoint.price`, `SwingPoint.swing_type`), что устраняет необходимость:
- ❌ Создания отдельного индикатора `SwingPointsIndicator`
- ❌ Опционального сохранения координат в `SwingMetrics`
- ❌ Пересчёта свинг-точек on-demand с кэшированием
- ❌ Сложной индикаторной инфраструктуры для overlay

**Результат**: Экономия **6-11 часов** на реализации Этапа 3.

**Статус**: Все этапы (1, 2, 3) готовы к параллельной реализации.

---

## Структура данных и доступ к метрикам

### Таблица доступа к данным

| Источник | Путь доступа | Тип | Обработка None |
|----------|-------------|-----|----------------|
| **Swing metrics** | `zone.features['metadata']['swing_metrics']` | `dict \| None` | Проверять через `.get('swing_metrics')` |
| **Shape metrics** | `zone.features['metadata']['shape_metrics']` | `dict \| None` | Проверять через `.get('shape_metrics')` |
| **Swing context** | `zone.swing_context` (ZoneInfo) или `zone.get('swing_context')` (dict) | `SwingContext \| None` | Fallback на global context |
| **Исходная зона** | `zone` (если dict с `original_zone`) | `ZoneInfo \| None` | Для вызова методов ZoneInfo |

### Структура swing_metrics

```python
swing_metrics = {
    'swings_count': int,           # Общее количество свингов
    'rally_count': int,            # Количество восходящих свингов
    'drop_count': int,             # Количество нисходящих свингов
    'avg_rally': float,            # Средняя амплитуда роста (%)
    'avg_drop': float,             # Средняя амплитуда падения (%)
    'rally_to_drop_ratio': float,  # Отношение роста к падению
    'avg_rally_duration': float,   # Средняя длительность роста (bars)
    'avg_drop_duration': float     # Средняя длительность падения (bars)
}
```

### Структура shape_metrics

```python
shape_metrics = {
    'hist_skewness': float,   # Асимметрия распределения индикатора
    'hist_kurtosis': float,   # Эксцесс (островершинность)
    'hist_mean': float,       # Среднее значение
    'hist_std': float         # Стандартное отклонение
}
```

### Важные ограничения

1. **Метрики в metadata**: Метрики ВСЕГДА находятся в `zone.features['metadata']`, не в корне `zone.features`.
2. **None значения**: Метрики могут быть `None` при ошибках расчёта или отсутствии данных.
3. **_normalize_zone**: Текущая реализация **НЕ** сохраняет `swing_context` и `original_zone` (требуется доработка в Этапе 1).
4. **Два бэкенда**: Визуализатор поддерживает Plotly и Matplotlib — каждое изменение требует реализации в обоих.

---

## Упрощённый план реализации

### 🎯 Этап 1: Метрики в Detail режиме

**Приоритет**: ВЫСОКИЙ
**Затраты**: 4-6 часов
**Цель**: Добавить текстовое отображение swing/shape метрик на графике detail
**Зависимости**: Нет (можно начинать сразу)

#### Реализация

```python
def plot_zone_detail(
    self,
    price_data: pd.DataFrame,
    zone: Union[Dict, ZoneInfo],
    context_bars: int = 20,

    # === НОВЫЕ ПАРАМЕТРЫ ===
    show_zone_metrics: bool = True,  # Показать текстовый блок с метриками

    # === СУЩЕСТВУЮЩИЕ ===
    show_indicators: bool = True,
    show_volume: bool = True,
    show_zone_stats: bool = None,  # Используем default_config если None
    **kwargs
) -> go.Figure:
    """
    Детальный просмотр зоны с опциональными метриками.

    NEW PARAMS:
        show_zone_metrics: Отображать swing/shape метрики как текстовую аннотацию.
            При True метрики объединяются с show_zone_stats в единый блок.
    """
    # ... existing code ...

    # НОВОЕ: Объединённый блок метрик
    if show_zone_metrics or (show_zone_stats is None and self.default_config['show_zone_stats']):
        annotation_text = self._build_zone_annotation_text(
            zone,
            include_basic_stats=(show_zone_stats or self.default_config['show_zone_stats']),
            include_metrics=show_zone_metrics
        )

        if annotation_text:
            # Позиция из default_config (унифицирована для всех режимов)
            position = self.default_config.get('metrics_annotation_position', 'top-left')

            self._add_annotation(
                fig,
                text=annotation_text,
                position=position,
                row=1, col=1  # Price panel
            )

    return fig
```

#### Визуальное представление

**Режим 1: show_zone_stats=True, show_zone_metrics=True (объединённый блок)**

```
┌─────────────────────────────────────┐
│ Zone #42 (bull) • 18 bars           │
│ Strength: 0.85                      │
│ ─────────────────                   │
│ 📊 Swing Metrics:                   │
│   Swings: 4 (3↑ / 2↓)               │
│   Avg Rally: +1.2% (3.5 bars)       │
│   Avg Drop: -0.8% (2.1 bars)        │
│   Rally/Drop Ratio: 1.5x            │
│ ─────────────────                   │
│ 📈 Shape Metrics (MACD hist):       │
│   Skewness: +0.43 (right-tailed)    │
│   Kurtosis: 2.1 (platykurtic)       │
└─────────────────────────────────────┘
```

**Режим 2: show_zone_stats=False, show_zone_metrics=True (только метрики)**

```
┌─────────────────────────────────────┐
│ 📊 Swing Metrics:                   │
│   Swings: 4 (3↑ / 2↓)               │
│   Avg Rally: +1.2% (3.5 bars)       │
│   Avg Drop: -0.8% (2.1 bars)        │
│   Rally/Drop Ratio: 1.5x            │
│ ─────────────────                   │
│ 📈 Shape Metrics (MACD hist):       │
│   Skewness: +0.43 (right-tailed)    │
│   Kurtosis: 2.1 (platykurtic)       │
└─────────────────────────────────────┘
```

**Режим 3: Метрики отсутствуют (swing_metrics=None и shape_metrics=None)**

```
┌─────────────────────────────────────┐
│ Zone #42 (bull) • 18 bars           │
│ Strength: 0.85                      │
│ ─────────────────                   │
│ 📊 Swing Metrics: Not available     │
│ 📈 Shape Metrics: Not available     │
└─────────────────────────────────────┘
```

#### Подзадачи

1. **Обновить `_normalize_zone()`** так, чтобы он сохранял `swing_context` и `original_zone` — **0.5 часа**

   ```python
   def _normalize_zone(self, zone: Union[Dict[str, Any], ZoneInfo, Any]) -> Dict[str, Any]:
       """Приведение зоны к словарю с сохранением метаданных ZoneInfo."""

       if isinstance(zone, dict):
           return zone  # Уже нормализован

       if isinstance(zone, ZoneInfo):
           return {
               'zone_id': zone.zone_id,
               'type': zone.type,
               'start_idx': zone.start_idx,
               'end_idx': zone.end_idx,
               'start_time': zone.start_time,
               'end_time': zone.end_time,
               'duration': zone.duration,
               'data': zone.data,
               'features': zone.features,
               'indicator_context': zone.indicator_context,

               # NEW: Сохранение контекста для Этапа 3
               'swing_context': zone.swing_context,  # Для get_zone_swings()
               'original_zone': zone,                 # Для методов ZoneInfo
           }

       # Fallback для других типов
       normalized = self._prepare_zone_data([zone])
       if not normalized:
           raise ValueError("Unable to normalize zone object")
       return normalized[0]
   ```

2. **Реализовать `_extract_zone_metrics()`** c учётом структуры данных — **1 час**

   ```python
   def _extract_zone_metrics(self, zone: Union[Dict, ZoneInfo]) -> Dict[str, Any]:
       """
       Извлечь метрики из зоны для отображения.

       Returns:
           Dict с ключами:
           - 'swing_metrics': dict | None
           - 'shape_metrics': dict | None
           - 'indicator_name': str (для shape_metrics label)
       """
       # Доступ к features
       if isinstance(zone, ZoneInfo):
           features = zone.features or {}
       else:
           features = zone.get('features', {})

       metadata = features.get('metadata', {})

       # Извлечь метрики
       swing_metrics = metadata.get('swing_metrics')  # dict | None
       shape_metrics = metadata.get('shape_metrics')  # dict | None

       # Определить имя индикатора для shape_metrics
       indicator_context = zone.indicator_context if isinstance(zone, ZoneInfo) else zone.get('indicator_context', {})
       indicator_name = indicator_context.get('detection_indicator', 'indicator')

       return {
           'swing_metrics': swing_metrics,
           'shape_metrics': shape_metrics,
           'indicator_name': indicator_name
       }
   ```

3. **Реализовать `_build_zone_annotation_text()`** — объединение старых и новых метрик — **2 часа**

   ```python
   def _build_zone_annotation_text(
       self,
       zone: Union[Dict, ZoneInfo],
       include_basic_stats: bool = True,
       include_metrics: bool = True
   ) -> str:
       """
       Построить объединённый текст аннотации зоны.

       Логика объединения:
       1. show_zone_stats=True, show_zone_metrics=False → Старое поведение (Type, Duration, Strength)
       2. show_zone_stats=False, show_zone_metrics=True → Только новые метрики (Swings, Shape)
       3. Оба True → Объединённый блок с разделителем
       """
       parts = []

       # === БАЗОВАЯ ИНФОРМАЦИЯ (старый show_zone_stats) ===
       if include_basic_stats:
           zone_dict = zone if isinstance(zone, dict) else self._normalize_zone(zone)
           zone_id = zone_dict.get('zone_id', '?')
           zone_type = zone_dict.get('type', 'n/a')
           duration = zone_dict.get('duration', 'n/a')

           parts.append(f"Zone #{zone_id} ({zone_type}) • {duration} bars")

           # Старые метрики (strength)
           features = zone_dict.get('features', {})
           if 'strength' in features:
               parts.append(f"Strength: {features['strength']:.2f}")

       # === НОВЫЕ МЕТРИКИ ===
       if include_metrics:
           metrics = self._extract_zone_metrics(zone)

           # Разделитель (если были базовые статы)
           if parts:
               parts.append("─────────────────")

           # Swing Metrics
           swing_text = self._format_swing_metrics(metrics['swing_metrics'])
           parts.append(swing_text)

           # Shape Metrics
           shape_text = self._format_shape_metrics(
               metrics['shape_metrics'],
               indicator_name=metrics['indicator_name']
           )
           parts.append(shape_text)

       return '<br>'.join(parts) if self.backend == 'plotly' else '\n'.join(parts)
   ```

4. **Реализовать форматирование метрик** — **1 час**

   ```python
   def _format_swing_metrics(self, swing_metrics: Optional[Dict]) -> str:
       """Форматирование swing_metrics в читаемый текст."""
       if swing_metrics is None:
           return "📊 Swing Metrics: Not available"

       # Обработка нулевых свингов
       swings_count = swing_metrics.get('swings_count', 0)
       if swings_count == 0:
           return "📊 Swing Metrics: No swings detected"

       rally_count = swing_metrics.get('rally_count', 0)
       drop_count = swing_metrics.get('drop_count', 0)
       avg_rally = swing_metrics.get('avg_rally')
       avg_drop = swing_metrics.get('avg_drop')
       ratio = swing_metrics.get('rally_to_drop_ratio')
       avg_rally_dur = swing_metrics.get('avg_rally_duration')
       avg_drop_dur = swing_metrics.get('avg_drop_duration')

       parts = ["📊 Swing Metrics:"]
       parts.append(f"  Swings: {swings_count} ({rally_count}↑ / {drop_count}↓)")

       if avg_rally is not None:
           dur_text = f" ({avg_rally_dur:.1f} bars)" if avg_rally_dur else ""
           parts.append(f"  Avg Rally: {avg_rally:+.2%}{dur_text}")

       if avg_drop is not None:
           dur_text = f" ({avg_drop_dur:.1f} bars)" if avg_drop_dur else ""
           parts.append(f"  Avg Drop: {avg_drop:+.2%}{dur_text}")

       if ratio is not None:
           parts.append(f"  Rally/Drop Ratio: {ratio:.2f}x")

       return '<br>'.join(parts) if self.backend == 'plotly' else '\n'.join(parts)

   def _format_shape_metrics(self, shape_metrics: Optional[Dict], indicator_name: str = 'indicator') -> str:
       """Форматирование shape_metrics в читаемый текст."""
       if shape_metrics is None:
           return "📈 Shape Metrics: Not available"

       skewness = shape_metrics.get('hist_skewness')
       kurtosis = shape_metrics.get('hist_kurtosis')

       if skewness is None and kurtosis is None:
           return "📈 Shape Metrics: Not available"

       parts = [f"📈 Shape Metrics ({indicator_name}):"]

       if skewness is not None:
           skew_label = "right-tailed" if skewness > 0 else "left-tailed" if skewness < 0 else "symmetric"
           parts.append(f"  Skewness: {skewness:+.2f} ({skew_label})")

       if kurtosis is not None:
           kurt_label = "leptokurtic" if kurtosis > 3 else "platykurtic" if kurtosis < 3 else "mesokurtic"
           parts.append(f"  Kurtosis: {kurtosis:.2f} ({kurt_label})")

       return '<br>'.join(parts) if self.backend == 'plotly' else '\n'.join(parts)
   ```

5. **Graceful degradation и логирование** — **0.5 часа**
   - Логировать `logger.debug("No metrics available for zone %s", zone_id)` при отсутствии метрик
   - Показывать "Not available" вместо сокрытия блока (более информативно для пользователя)

6. **Тестирование и примеры** — **1 час**
   - Plotly: проверить аннотации, позиционирование
   - Matplotlib: проверить `fig.text()` с bbox
   - Примеры: зона с метриками, зона без метрик, объединённый блок

---

### 🎯 Этап 2: Агрегированные метрики в Overview

**Приоритет**: СРЕДНИЙ
**Затраты**: 3-4 часа
**Цель**: Добавить статистику по всем зонам в overview режиме
**Зависимости**: Нет (можно начинать параллельно с Этапом 1)

#### Реализация

```python
def plot_zones_on_price_chart(
    self,
    ...
    show_aggregate_metrics: bool = False,  # Показать агрегированные метрики
    ...
):
    """
    Overview всех зон с опциональной агрегированной статистикой.

    NEW PARAMS:
        show_aggregate_metrics: Отображать статистику по всем зонам
    """
    # ... existing code ...

    # НОВОЕ: Агрегировать и отобразить метрики
    if show_aggregate_metrics and zones:
        aggregated = self._aggregate_zone_metrics(
            zones,
            metrics=('avg_rally', 'avg_drop', 'rally_drop_ratio', 'swings_count'),
            aggregation_mode='mean_std',
            skip_none=True
        )

        if aggregated:
            annotation_text = self._format_aggregate_metrics(aggregated)
            position = self.default_config.get('metrics_annotation_position', 'top-right')

            self._add_annotation(
                fig,
                text=annotation_text,
                position=position,
                row=1, col=1
            )

    return fig
```

#### Визуальное представление

```
┌─────────────────────────────────────────────────┐
│ Overview: 37 bull zones, 35 bear zones          │
│                                                 │
│ 📊 Bull Zones - Swing Statistics:              │
│   Avg Rally: +1.18% ± 0.45%                    │
│   Avg Drop: -0.92% ± 0.38%                     │
│   Rally/Drop Ratio: 1.28x (median)             │
│   Zones with swings: 23/37 (62%)               │
│                                                 │
│ 📊 Bear Zones - Swing Statistics:              │
│   Avg Rally: +0.85% ± 0.32%                    │
│   Avg Drop: -1.05% ± 0.41%                     │
│   Rally/Drop Ratio: 0.81x (median)             │
│   Zones with swings: 19/35 (54%)               │
│                                                 │
│ 📈 Shape Statistics (MACD histogram):          │
│   Bull Skewness: +0.35 ± 0.22 (right-tailed)   │
│   Bear Skewness: -0.28 ± 0.19 (left-tailed)    │
│   Bull Kurtosis: 2.45 ± 0.65 (platykurtic)     │
│   Bear Kurtosis: 2.38 ± 0.58 (platykurtic)     │
└─────────────────────────────────────────────────┘
```

#### Спецификация агрегатора

```python
def _aggregate_zone_metrics(
    self,
    zones: List[Union[Dict, ZoneInfo]],
    metrics: Tuple[str, ...] = ('avg_rally', 'avg_drop', 'rally_drop_ratio', 'swings_count'),
    aggregation_mode: str = 'mean_std',
    skip_none: bool = True
) -> Dict[str, Any]:
    """
    Агрегировать метрики по всем зонам.

    Args:
        zones: Список зон
        metrics: Метрики для агрегации
        aggregation_mode: 'mean_std' | 'median' | 'sum'
        skip_none: Пропускать зоны без метрик

    Returns:
        {
            'bull': {'avg_rally_mean': float, 'avg_rally_std': float, ...},
            'bear': {...},
            'shape': {'bull_skewness_mean': float, ...}
        }
    """
    bull_zones = [z for z in zones if self._get_zone_type(z) == 'bull']
    bear_zones = [z for z in zones if self._get_zone_type(z) == 'bear']

    result = {
        'bull': self._aggregate_for_zone_type(bull_zones, metrics, aggregation_mode, skip_none),
        'bear': self._aggregate_for_zone_type(bear_zones, metrics, aggregation_mode, skip_none),
        'shape': self._aggregate_shape_metrics([bull_zones, bear_zones], skip_none)
    }

    return result
```

#### Подзадачи

1. Реализовать `_aggregate_zone_metrics()` — **1 час**
2. Реализовать `_format_aggregate_metrics()` — **1.5 часа**
3. Покрыть сценарии отсутствующих данных (юнит-тест) — **0.5 часа**
4. Тестирование и примеры — **1 час**

---

### 🎯 Этап 3: Визуализация свинг-точек

**Приоритет**: ВЫСОКИЙ
**Затраты**: 3-4 часа
**Цель**: Отображать свинг-точки из `SwingContext` на графиках
**Зависимости**: ✅ Нет (gloswing.md реализован)

#### Реализация

```python
def plot_zone_detail(
    self,
    data: pd.DataFrame,
    zone: Union[Dict, ZoneInfo],

    # === НОВЫЕ ПАРАМЕТРЫ ===
    show_swings: bool = False,           # Показать свинг-точки
    swing_marker_size: int = 10,         # Размер маркеров

    **kwargs
) -> go.Figure:
    """
    Детальный просмотр зоны с опциональными свинг-точками.

    NEW PARAMS:
        show_swings: Отображать свинг-точки из zone.swing_context
        swing_marker_size: Размер маркеров свингов
    """
    # ... existing code ...

    # НОВОЕ: Добавить свинг-точки если доступны
    if show_swings:
        swing_context = self._resolve_swing_context(zone)
        if swing_context:
            zone_swings = swing_context.get_swings_for_zone(
                zone if isinstance(zone, ZoneInfo) else zone.get('original_zone')
            )
            self._add_swing_overlay(
                fig,
                zone_swings,
                row=1, col=1,  # Price panel
                marker_size=swing_marker_size
            )

    return fig

def _add_swing_overlay(
    self,
    fig: go.Figure,
    swing_points: List[SwingPoint],
    row: int,
    col: int,
    marker_size: int = 10
) -> None:
    """
    Добавить свинг-точки как scatter overlay.

    Args:
        fig: Plotly/Matplotlib figure
        swing_points: Список SwingPoint из SwingContext
        row, col: Позиция subplot
        marker_size: Размер маркеров
    """
    # Использовать цвета из темы
    theme = self.theme or self._get_default_theme()
    peak_color = theme.colors.get('swing_peak', '#d62728')
    trough_color = theme.colors.get('swing_trough', '#2ca02c')

    # Разделить на peaks и troughs
    peaks = [sp for sp in swing_points if sp.swing_type == 'peak']
    troughs = [sp for sp in swing_points if sp.swing_type == 'trough']

    if self.backend == 'plotly':
        # Plotly implementation
        if peaks:
            fig.add_trace(
                go.Scatter(
                    x=[sp.timestamp for sp in peaks],
                    y=[sp.price for sp in peaks],
                    mode='markers',
                    marker=dict(
                        symbol='triangle-down',
                        size=marker_size,
                        color=peak_color,
                        line=dict(width=1, color='darkred')
                    ),
                    name='Swing Peaks',
                    hovertemplate='<b>Peak</b><br>Price: %{y:.2f}<extra></extra>'
                ),
                row=row, col=col
            )

        if troughs:
            fig.add_trace(
                go.Scatter(
                    x=[sp.timestamp for sp in troughs],
                    y=[sp.price for sp in troughs],
                    mode='markers',
                    marker=dict(
                        symbol='triangle-up',
                        size=marker_size,
                        color=trough_color,
                        line=dict(width=1, color='darkgreen')
                    ),
                    name='Swing Troughs',
                    hovertemplate='<b>Trough</b><br>Price: %{y:.2f}<extra></extra>'
                ),
                row=row, col=col
            )

    else:  # matplotlib
        ax = fig.axes[row - 1]  # Matplotlib uses 0-indexed axes

        if peaks:
            ax.scatter(
                [sp.timestamp for sp in peaks],
                [sp.price for sp in peaks],
                marker='v',
                s=marker_size * 10,
                color=peak_color,
                edgecolors='darkred',
                linewidths=1,
                label='Swing Peaks',
                zorder=5
            )

        if troughs:
            ax.scatter(
                [sp.timestamp for sp in troughs],
                [sp.price for sp in troughs],
                marker='^',
                s=marker_size * 10,
                color=trough_color,
                edgecolors='darkgreen',
                linewidths=1,
                label='Swing Troughs',
                zorder=5
            )
```

#### Поддержка overview режима

```python
def plot_zones_on_price_chart(
    self,
    ...
    show_swings: bool = False,  # Показать все глобальные свинги
    ...
):
    """
    Overview всех зон с опциональными свинг-точками.

    NEW PARAMS:
        show_swings: Отображать глобальные свинги из SwingContext
    """
    # ... existing code ...

    # НОВОЕ: Отобразить глобальные свинги (если доступны)
    if show_swings and zones:
        swing_context = self._resolve_global_swing_context(zones)
        if swing_context:
            # Фильтровать свинги по видимому диапазону
            visible_swings = [
                sp for sp in swing_context.swing_points
                if data.index[0] <= sp.timestamp <= data.index[-1]
            ]
            self._add_swing_overlay(fig, visible_swings, row=1, col=1)

    return fig
```

#### Подзадачи

1. Реализовать `_resolve_swing_context()` и `_resolve_global_swing_context()` — **0.5 часа**
2. Реализовать `_add_swing_overlay()` с поддержкой Plotly и Matplotlib — **2 часа**
3. Добавить параметры в `plot_zone_detail()` и `plot_zones_on_price_chart()` — **0.5 часа**
4. Интеграция с системой тем (убрать хардкод цветов) — **0.5 часа**
5. Тестирование и примеры — **1 час**

---

## Итоговая оценка трудозатрат

| Этап | Описание | Затраты | Приоритет | Зависимости |
|------|----------|---------|-----------|-------------|
| **1** | Метрики в Detail | 4-6 часов | ВЫСОКИЙ | ✅ Нет |
| **2** | Агрегированные метрики в Overview | 3-4 часа | СРЕДНИЙ | ✅ Нет |
| **3** | Визуализация свинг-точек | 3-4 часа | ВЫСОКИЙ | ✅ Нет (gloswing.md готов) |
| **ИТОГО** | | **10-14 часов** | | |

**Сравнение с первоначальной оценкой**:
- Было (с созданием инфраструктуры): 25-36 часов
- Стало (только визуализация): 10-14 часов
- **Экономия: 15-22 часа** благодаря готовому `SwingContext`

---

## Последовательность реализации

### ✅ Рекомендуемый подход: Параллельная реализация

Поскольку **gloswing.md полностью реализован** (2025-11-10), все этапы независимы:

```
┌──────────────────────────────────────────┐
│ Этапы 1, 2, 3 — параллельная реализация │
│                                          │
│ Разработчик A: Этап 1 (4-6ч)            │
│ Разработчик B: Этап 2 (3-4ч)            │
│ Разработчик C: Этап 3 (3-4ч)            │
│                                          │
│ Итого: ~6 часов календарного времени    │
└──────────────────────────────────────────┘
```

**Преимущества**:
- ✅ Минимальное время до релиза (6 часов вместо 14)
- ✅ Независимые изменения (минимум конфликтов merge)
- ✅ Параллельное тестирование

### Альтернатива: Последовательная реализация

Если доступен только один разработчик:

1. **Этап 1** (метрики в detail) — 4-6 часов
2. **Этап 2** (агрегация) — 3-4 часа
3. **Этап 3** (свинги) — 3-4 часа

**Итого**: ~10-14 часов календарного времени

---

## Изменяемые файлы

### Основной модуль визуализации

**`bquant/visualization/zones.py`**:
- Этап 1: `_normalize_zone()`, `_extract_zone_metrics()`, `_build_zone_annotation_text()`, `_format_swing_metrics()`, `_format_shape_metrics()`
- Этап 2: `_aggregate_zone_metrics()`, `_format_aggregate_metrics()`
- Этап 3: `_add_swing_overlay()`, `_resolve_swing_context()`, `_resolve_global_swing_context()`
- Общее: Обновить `plot_zone_detail()` и `plot_zones_on_price_chart()`

### Конфигурация

**`bquant/visualization/zones.py` (default_config)**:
```python
self.default_config = {
    ...
    'show_zone_stats': True,
    'show_zone_metrics': False,  # NEW: По умолчанию выключено (BC)
    'show_aggregate_metrics': False,  # NEW
    'show_swings': False,  # NEW
    'metrics_annotation_position': 'top-left',  # NEW: Унифицированная позиция
    ...
}
```

### Тесты

**Новые файлы**:
- `tests/visualization/test_zone_metrics_display.py` — тесты отображения метрик
- `tests/visualization/test_zone_metrics_aggregation.py` — тесты агрегатора
- `tests/visualization/test_swing_overlay.py` — тесты свинг-точек

**Обновить**:
- `tests/visualization/test_zones_visualizer.py` — проверить BC

### Примеры

**Новые файлы**:
- `examples/09_zone_metrics_visualization.py` — демонстрация всех возможностей

**Обновить**:
- `examples/zone_analysis_global_swings.py` — добавить визуализацию свингов

### Benchmark тест

**Обновить** (критически важно):
- `research/notebooks/04_zones_sample.py` — добавить тесты новой функциональности
  - После Этапа 1: добавить шаг "Zone Metrics in Detail Mode"
  - После Этапа 2: добавить шаг "Aggregate Metrics in Overview Mode"
  - После Этапа 3: добавить шаг "Swing Points Visualization" + обновить pipeline на `.with_swing_scope('global')`
  - **Важно**: Сохранить все существующие шаги для backward compatibility тестирования

---

## Тестирование и валидация

### Benchmark тест: `research/notebooks/04_zones_sample.py`

**Назначение**: Комплексный benchmark скрипт для валидации визуализации зон после реализации zomet.md.

**Текущее состояние**: Скрипт содержит полное покрытие существующего API визуализации:
- Overview режим (с/без индикаторов, dense/timeseries)
- Detail режим (единичная зона)
- Comparison режим (2-6 зон)
- Statistics режим
- Custom configuration (все параметры ZoneVisualizer)
- Convenience functions (plot_zone_detail, plot_zones_comparison)

**Требования после реализации zomet.md**:

#### Этап 1: Добавить тесты метрик в detail режиме

```python
# После Этапа 1 - добавить в 04_zones_sample.py
nb.step("Zone Metrics in Detail Mode")
with nb.error_handling("Testing zone metrics display"):
    target_zone = result.zones[0]

    # Тест 1: Метрики включены (новая функциональность)
    fig_metrics = result.visualize(
        'detail',
        zone_id=target_zone.zone_id,
        show_zone_metrics=True,  # NEW
        context_bars=20
    )
    nb.success("Zone metrics displayed successfully")

    # Тест 2: Объединенный блок (старые + новые метрики)
    fig_combined = result.visualize(
        'detail',
        zone_id=target_zone.zone_id,
        show_zone_stats=True,   # Старое
        show_zone_metrics=True,  # Новое
    )
    nb.success("Combined stats+metrics block displayed")

    # Тест 3: Backward compatibility (только старые статы)
    fig_bc = result.visualize(
        'detail',
        zone_id=target_zone.zone_id,
        show_zone_stats=True,
        show_zone_metrics=False  # Явно выключено
    )
    nb.success("Backward compatibility maintained")

    if SAVE_IMAGES:
        save_figure(fig_metrics, "test_zone_metrics", output_dir=str(OUTPUT_DIR))
        save_figure(fig_combined, "test_combined_stats_metrics", output_dir=str(OUTPUT_DIR))
        save_figure(fig_bc, "test_backward_compat", output_dir=str(OUTPUT_DIR))
nb.wait()
```

#### Этап 2: Добавить тесты агрегированных метрик

```python
# После Этапа 2 - добавить в 04_zones_sample.py
nb.step("Aggregate Metrics in Overview Mode")
with nb.error_handling("Testing aggregate metrics"):
    # Тест 1: Агрегированные метрики в overview
    fig_agg = result.visualize(
        'overview',
        show_aggregate_metrics=True,  # NEW
        title="Overview with Aggregate Metrics"
    )
    nb.success("Aggregate metrics displayed in overview")

    # Тест 2: Проверка расчета метрик
    # Должны быть видны статистики по bull/bear зонам отдельно
    bull_count = len([z for z in result.zones if z.type == 'bull'])
    bear_count = len([z for z in result.zones if z.type == 'bear'])
    nb.log(f"Bull zones: {bull_count}, Bear zones: {bear_count}")
    nb.log("Aggregate metrics should show separate stats for each type")

    if SAVE_IMAGES:
        save_figure(fig_agg, "test_aggregate_metrics", output_dir=str(OUTPUT_DIR))
nb.wait()
```

#### Этап 3: Добавить тесты визуализации свингов

```python
# После Этапа 3 - добавить в 04_zones_sample.py (в начало pipeline)
nb.step("Zone Analysis with Global Swings")
with nb.error_handling("Building pipeline with global swing scope"):
    # ВАЖНО: Использовать global swing scope для Этапа 3
    result = (
        analyze_zones(df)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_col="macd_hist")
        .with_strategies(swing='zigzag')
        .with_swing_scope('global')  # NEW: Глобальный расчет свингов
        .analyze(clustering=True, n_clusters=3)
        .build()
    )
    nb.success(f"Pipeline completed with global swings: zones={len(result.zones)}")
nb.wait()

# ... позже в скрипте ...

nb.step("Swing Points Visualization")
with nb.error_handling("Testing swing points overlay"):
    target_zone = result.zones[0]

    # Тест 1: Свинги в detail режиме
    fig_swings_detail = result.visualize(
        'detail',
        zone_id=target_zone.zone_id,
        show_swings=True,  # NEW
        show_zone_metrics=True,
        swing_marker_size=12,
        context_bars=30
    )
    nb.success("Swing points displayed in detail mode")

    # Тест 2: Свинги в overview режиме
    fig_swings_overview = result.visualize(
        'overview',
        show_swings=True,  # NEW: Глобальные свинги
        show_aggregate_metrics=True,
        title="Overview with Global Swing Points"
    )
    nb.success("Global swing points displayed in overview mode")

    # Тест 3: Полная интеграция (все новые функции)
    fig_full = result.visualize(
        'detail',
        zone_id=target_zone.zone_id,
        show_zone_stats=True,
        show_zone_metrics=True,
        show_swings=True,
        swing_marker_size=10,
    )
    nb.success("Full integration test: stats + metrics + swings")

    if SAVE_IMAGES:
        save_figure(fig_swings_detail, "test_swings_detail", output_dir=str(OUTPUT_DIR))
        save_figure(fig_swings_overview, "test_swings_overview", output_dir=str(OUTPUT_DIR))
        save_figure(fig_full, "test_full_integration", output_dir=str(OUTPUT_DIR))
nb.wait()
```

### Критерии успешного прохождения benchmark теста

#### ✅ Этап 1 (Метрики в detail)

1. **Функциональность**:
   - ✅ `show_zone_metrics=True` отображает блок метрик
   - ✅ Swing metrics показываются (если доступны)
   - ✅ Shape metrics показываются (если доступны)
   - ✅ При отсутствии метрик показывается "Not available"

2. **Backward Compatibility**:
   - ✅ `show_zone_metrics=False` не ломает существующие графики
   - ✅ `show_zone_stats=True` продолжает работать как раньше
   - ✅ Все существующие тесты в `04_zones_sample.py` проходят без изменений

3. **Визуальная валидация**:
   - ✅ Блок метрик читаем и не перекрывает график
   - ✅ Объединенный блок (stats+metrics) корректно форматирован
   - ✅ Позиционирование работает (top-left по умолчанию)

#### ✅ Этап 2 (Агрегированные метрики)

1. **Функциональность**:
   - ✅ `show_aggregate_metrics=True` отображает статистику
   - ✅ Разделение по bull/bear зонам работает
   - ✅ Расчет mean, std, median корректен
   - ✅ Обработка отсутствующих метрик (показ "n/N zones")

2. **Визуальная валидация**:
   - ✅ Агрегированный блок компактен и читаем
   - ✅ Не загромождает overview график
   - ✅ Позиционирование (top-right по умолчанию)

#### ✅ Этап 3 (Свинг-точки)

1. **Функциональность**:
   - ✅ `show_swings=True` отображает свинг-точки
   - ✅ Peaks показываются треугольниками вниз
   - ✅ Troughs показываются треугольниками вверх
   - ✅ Работает в detail и overview режимах
   - ✅ Цвета берутся из темы (не хардкод)

2. **Производительность**:
   - ✅ Визуализация зоны с 50+ свингами < 100ms
   - ✅ Overview с 200+ глобальными свингами < 500ms

3. **Интеграция**:
   - ✅ Совместная работа: `show_zone_metrics=True` + `show_swings=True`
   - ✅ Визуализация корректна при отсутствии swing_context

### Регрессионное тестирование

После каждого этапа запустить **весь** скрипт `04_zones_sample.py` и проверить:

1. **Все существующие шаги проходят без ошибок**
2. **Генерируются корректные изображения** (визуальная проверка)
3. **Логи NotebookSimulator не содержат WARNING/ERROR**
4. **Размер PNG/HTML файлов разумен** (< 5MB для PNG, < 10MB для HTML)

### Команда запуска benchmark теста

```bash
# Из корня проекта
python research/notebooks/04_zones_sample.py

# Проверка результатов
ls -lh research/notebooks/outputs/vis/04_zones_sample/

# Ожидаемые файлы после полной реализации:
# - 01_overview*.png/html
# - 02_detail_*.png/html
# - 03_comparison*.png/html
# - 04_statistics.png/html
# - 05_*_full_params.png/html
# - 08_custom_*.png/html
# - test_zone_metrics.png/html  (NEW - Этап 1)
# - test_combined_stats_metrics.png/html  (NEW - Этап 1)
# - test_aggregate_metrics.png/html  (NEW - Этап 2)
# - test_swings_*.png/html  (NEW - Этап 3)
# - test_full_integration.png/html  (NEW - Этап 3)
```

### Чеклист валидации

После реализации всех 3 этапов:

- [ ] **Запустить `04_zones_sample.py`** — скрипт завершается без ошибок
- [ ] **Проверить логи** — нет WARNING/ERROR (кроме ожидаемых DEBUG о missing метриках)
- [ ] **Визуальная проверка** — открыть все PNG/HTML, проверить корректность:
  - [ ] Метрики отображаются в detail режиме
  - [ ] Агрегированные метрики в overview компактны и читаемы
  - [ ] Свинг-точки видны, цвета корректны (peaks красные, troughs зеленые)
  - [ ] Объединенный блок (stats+metrics) не дублирует информацию
  - [ ] Позиционирование не перекрывает графики
- [ ] **Backward compatibility** — старые графики без новых параметров выглядят как раньше
- [ ] **Производительность** — время выполнения скрипта < 30 секунд (с SAVE_IMAGES=True)
- [ ] **Размер файлов** — PNG < 5MB, HTML < 10MB

### Интеграция в CI/CD

**Рекомендация**: Добавить `04_zones_sample.py` в automated test suite:

```yaml
# .github/workflows/test.yml (или аналогичный)
- name: Run visualization benchmark
  run: |
    python research/notebooks/04_zones_sample.py
    # Проверить, что скрипт не упал
    if [ $? -ne 0 ]; then
      echo "Benchmark test failed"
      exit 1
    fi
    # Проверить наличие ожидаемых файлов
    test -f research/notebooks/outputs/vis/04_zones_sample/test_zone_metrics.png
    test -f research/notebooks/outputs/vis/04_zones_sample/test_aggregate_metrics.png
    test -f research/notebooks/outputs/vis/04_zones_sample/test_swings_detail.png
```

---

## Обновление документации

После завершения реализации обновить:

### 1. User Guide

**`docs/user_guide/zone_analysis.md`**:
- Добавить раздел "Visualizing Zone Metrics"
- Примеры использования `show_zone_metrics`, `show_aggregate_metrics`, `show_swings`
- Скриншоты графиков с метриками

### 2. API Documentation

**`docs/api/visualization/zones.md`**:
- Документировать новые параметры `plot_zone_detail()`:
  - `show_zone_metrics`
  - `show_swings`
  - `swing_marker_size`
- Документировать новые параметры `plot_zones_on_price_chart()`:
  - `show_aggregate_metrics`
  - `show_swings`
- Документировать внутренние методы (для расширения):
  - `_build_zone_annotation_text()`
  - `_aggregate_zone_metrics()`
  - `_add_swing_overlay()`

### 3. Примеры

**`examples/README.md`**:
- Добавить ссылку на `09_zone_metrics_visualization.py`
- Описание возможностей визуализации метрик

---

## Связанные документы

- **[gloswing.md](../swing/gloswing.md)** ✅ РЕАЛИЗОВАН (2025-11-10) — глобальный расчёт свингов
- [Case Study: MACD Zone Consistency](../../../docs/analytics/zones/macd_zone_consistency_case_study.md) — исследование, подтверждающее необходимость визуализации
- [Zone Analysis User Guide](../../../docs/user_guide/zone_analysis.md) — документация для пользователей
- [Swing Strategies Guide](../../../docs/user_guide/swing_strategies.md) — документация по глобальному режиму

---

## Критерии успеха

### Этап 1 (Метрики в detail)

- ✅ `plot_zone_detail()` принимает `show_zone_metrics=True`
- ✅ `_normalize_zone()` возвращает `swing_context` и `original_zone`
- ✅ Метрики отображаются как текстовая аннотация на графике
- ✅ Поддерживаются swing_metrics и shape_metrics
- ✅ Backward compatibility: старые вызовы без новых параметров работают
- ✅ Блок метрик корректно сосуществует с `show_zone_stats` (объединённый режим)
- ✅ Graceful degradation: при отсутствии метрик показывается "Not available"
- ✅ Демо-скрипт работает без ошибок (Plotly и Matplotlib)

### Этап 2 (Агрегированные метрики)

- ✅ `plot_zones_on_price_chart()` принимает `show_aggregate_metrics=True`
- ✅ `_aggregate_zone_metrics()` поддерживает режимы `mean_std`, `median`, `sum`
- ✅ Агрегированная статистика корректно вычисляется по всем зонам, отдельно для bull/bear
- ✅ Отображается в виде компактного текстового блока (Plotly и Matplotlib)
- ✅ При смешанных данных отображается `n/a (k/N)` и логируется предупреждение
- ✅ Не загромождает график

### Этап 3 (Свинг-точки)

- ✅ `_add_swing_overlay()` корректно отображает SwingPoint объекты (Plotly и Matplotlib)
- ✅ Работает для `detail` и `overview` режимов
- ✅ Peaks отображаются треугольниками вниз (цвет из темы)
- ✅ Troughs отображаются треугольниками вверх (цвет из темы)
- ✅ Производительность: визуализация зоны с 100 свингами < 100ms
- ✅ Демо-скрипт работает без ошибок (оба бэкенда)

---

## Примеры использования

### Пример 1: Метрики в detail

```python
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='zigzag')
    .with_swing_scope('global')  # ✅ Доступно!
    .analyze()
    .build()
)

# Визуализация с метриками
fig = result.visualize(
    'detail',
    zone_id=5,
    show_zone_metrics=True,  # Показать swing/shape метрики
    show_zone_stats=True     # Объединить со старыми статами
)
fig.show()
```

### Пример 2: Агрегированные метрики в overview

```python
# Визуализация всех зон с агрегированной статистикой
fig = result.visualize(
    'overview',
    show_aggregate_metrics=True  # Показать статистику по bull/bear зонам
)
fig.show()
```

### Пример 3: Свинг-точки

```python
# Глобальный расчёт свингов (gloswing.md реализован!)
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', ...)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='zigzag')
    .with_swing_scope('global')  # ← Глобальный расчёт
    .analyze()
    .build()
)

# Визуализация с метриками и свингами
fig = result.visualize(
    'detail',
    zone_id=5,
    show_zone_metrics=True,
    show_swings=True,           # ← Использует zone.swing_context
    swing_marker_size=12
)
fig.show()

# Overview со всеми свингами
fig = result.visualize(
    'overview',
    show_aggregate_metrics=True,
    show_swings=True  # ← Отображает глобальные свинги
)
fig.show()
```

### Пример 4: Только старые статы (BC)

```python
# Backward compatibility: старое поведение сохранено
fig = result.visualize(
    'detail',
    zone_id=5,
    show_zone_stats=True,
    show_zone_metrics=False  # Только Type/Duration/Strength
)
fig.show()
```

---

## Следующие шаги

### ✅ Завершено

1. ✅ **Утверждение упрощённого плана** (2025-11-08)
2. ✅ **Реализация gloswing.md** (2025-11-10)

### 🚀 Готово к выполнению

3. **Реализация Этапа 1**: Метрики в detail (4-6 часов) — **МОЖНО НАЧИНАТЬ**
   - Реализовать методы в `bquant/visualization/zones.py`
   - Обновить `research/notebooks/04_zones_sample.py` (добавить тесты метрик)
   - Запустить benchmark тест и проверить backward compatibility

4. **Реализация Этапа 2**: Агрегированные метрики (3-4 часа) — **МОЖНО НАЧИНАТЬ**
   - Реализовать агрегацию в `bquant/visualization/zones.py`
   - Обновить `research/notebooks/04_zones_sample.py` (добавить тесты агрегации)
   - Запустить benchmark тест

5. **Реализация Этапа 3**: Визуализация свингов (3-4 часа) — **МОЖНО НАЧИНАТЬ**
   - Реализовать `_add_swing_overlay()` в `bquant/visualization/zones.py`
   - Обновить `research/notebooks/04_zones_sample.py` (pipeline + тесты свингов)
   - Запустить benchmark тест на полной интеграции

### ⏳ После реализации

6. **Валидация**: Полный прогон `04_zones_sample.py` + визуальная проверка всех графиков
7. **Юнит-тесты**: Создать `test_zone_metrics_display.py`, `test_zone_metrics_aggregation.py`, `test_swing_overlay.py`
8. **Code review**: Проверка архитектуры и backward compatibility
9. **Документация**: Обновление user guide и API docs
10. **Релиз v1.0**: Полная визуализация метрик и свингов

---

**Автор**: Claude Code (ред. claude-sonnet-4.5)
**Версия документа**: 6.1 (добавлен раздел тестирования и валидации)
**Дата обновления**: 2025-11-11

> **Важное изменение (v6.0)**: Документ обновлён с учётом завершения gloswing.md (2025-11-10). Все 3 этапа готовы к параллельной реализации без ожидания зависимостей.

> **Новое в v6.1**: Добавлен раздел "Тестирование и валидация" с использованием `research/notebooks/04_zones_sample.py` как benchmark теста для проверки новой функциональности и backward compatibility.

> ASCII-макеты выше — концепты для Plotly. В Matplotlib допускается разница в отступах и шрифтах; важна информационная насыщенность, а не пиксель-перфект.
