# Zone Metrics Visualization Enhancement

**Дата создания**: 2025-11-07
**Дата обновления**: 2025-11-11 (ревизия 7.1: реализованы Этапы 0-3)
**Статус**: ✅ v1.0 РЕАЛИЗОВАН | 📋 v1.2 Planned (расширенная агрегация)
**Приоритет**: ВЫПОЛНЕНО (v1.0) | MEDIUM (v1.2)

**📚 Связанные документы**:
- [zomet_v1.2_advanced_aggregation.md](./zomet_v1.2_advanced_aggregation.md) — план расширенной агрегации (median/IQR, shape метрики)

## Контекст

В результате аналитического исследования ([05_case_study_zone_consistency.py](../../../research/notebooks/05_case_study_zone_consistency.py)) была подтверждена состоятельность MACD bull-зон: средние ап-свинги статистически превосходят даун-свинги (p-value 0.0015 < 0.05 для zigzag стратегии). См. отчет: [macd_zone_consistency_case_study.md](../../../docs/analytics/zones/macd_zone_consistency_case_study.md).

Однако текущий визуализатор не позволяет:
1. Видеть сами **свинг-точки** (разворотные точки, экстремумы) на графике
2. Отображать **свинг-метрики и шейп-метрики** при детальном просмотре зоны
3. Видеть **агрегированную статистику по метрикам** в режиме overview (MVP версия)
4. Управлять существующим блоком `show_zone_stats` так, чтобы он не конфликтовал с новыми карточками метрик

Это ограничивает возможность визуальной проверки результатов анализа и понимания внутренней структуры зон.

---

## Текущее состояние реализации (2025-11-11)

### ✅ v1.0 ПОЛНОСТЬЮ РЕАЛИЗОВАН

**Этап 0: Инфраструктура** (4-6 часов) — ✅ **РЕАЛИЗОВАН**:
- ✅ `_add_annotation()` — унифицированное добавление аннотаций (Plotly + Matplotlib)
- ✅ Интеграция с `ChartThemes` — цвета `swing_peak`, `swing_trough` с fallback
- ✅ `_prepare_zone_data()` — сохраняет `SwingContext` через `_normalize_zone()`
- ✅ `_normalize_zone()` — возвращает `swing_context` и `original_zone`
- ✅ `_validate_and_get_config()` — валидация kwargs с приоритетами
- ✅ `default_config` с новыми параметрами (`show_zone_metrics`, `show_aggregate_metrics`, `show_swings`)

**Этап 1: Detail Metrics** (6-8 часов) — ✅ **РЕАЛИЗОВАН**:
- ✅ `_extract_zone_metrics()` — извлечение swing/shape метрик из зон
- ✅ `_format_swing_metrics()` — форматирование с диагностикой отсутствующих данных
- ✅ `_format_shape_metrics()` — форматирование skewness/kurtosis с лейблами
- ✅ `_diagnose_missing_swing_metrics()` — диагностика причин отсутствия метрик
- ✅ `_build_zone_annotation_text()` — единый построитель аннотаций
- ✅ Интеграция в `plot_zone_detail()` с параметрами `show_zone_metrics`, `show_zone_stats`

**Этап 2: Aggregate Metrics MVP** (2-3 часа) — ✅ **РЕАЛИЗОВАН**:
- ✅ `_aggregate_zone_metrics_mvp()` — агрегация по bull/bear зонам (mean ± std)
- ✅ `_format_aggregate_metrics_mvp()` — форматирование с режимами `compact` (8 строк) и `full` (~16 строк)
- ✅ Интеграция в `plot_zones_on_price_chart()` с параметрами `show_aggregate_metrics`, `aggregate_metrics_mode`
- ✅ Поддержка несбалансированных свингов (зоны с только rally или только drop)
- ✅ Корректное форматирование процентов (`avg_rally_pct` уже в %, не умножаем на 100)

**Этап 3: Swing Visualization Plotly** (5-7 часов) — ✅ **РЕАЛИЗОВАН**:
- ✅ `_resolve_swing_context()` — извлечение SwingContext из зоны
- ✅ `_resolve_global_swing_context()` — поиск глобального SwingContext
- ✅ `_get_zone_swings_safe()` — безопасное получение свингов с fallback
- ✅ `_add_swing_overlay()` — визуализация peaks (▼ red) и troughs (▲ green) для Plotly
- ✅ Интеграция в `plot_zone_detail()` и `plot_zones_on_price_chart()` с параметром `show_swings`
- ✅ Matplotlib отложен до v1.1 (Этап 4) с предупреждением

**Итого v1.0**: 17-24 часа — ✅ **100% РЕАЛИЗОВАНО**

### 📋 v1.2 Запланировано

**Расширенная агрегация** (11-16 часов) — см. [zomet_v1.2_advanced_aggregation.md](./zomet_v1.2_advanced_aggregation.md):
- 📋 `_aggregate_zone_metrics_advanced()` — median/IQR (robust к выбросам)
- 📋 `_aggregate_zone_metrics_full()` — shape метрики в агрегации + min/max
- 📋 `_format_aggregate_metrics_advanced()` — 3 режима вывода (compact/full/detailed)
- 📋 `AggregateConfig` класс для гибкой настройки

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

---

## Структура данных и доступ к метрикам

### Таблица доступа к данным

| Источник | Путь доступа | Тип | Обработка None |
|----------|-------------|-----|----------------|
| **Swing metrics** | `zone.features['metadata']['swing_metrics']` | `dict \| None` | Проверять через `.get('swing_metrics')` |
| **Shape metrics** | `zone.features['metadata']['shape_metrics']` | `dict \| None` | Проверять через `.get('shape_metrics')` |
| **Swing context** | `zone.swing_context` (ZoneInfo) или `zone.get('swing_context')` (dict) | `SwingContext \| None` | Возврат `None` если отсутствует |
| **Исходная зона** | `zone.get('original_zone')` (для dict) | `ZoneInfo \| None` | Для вызова методов ZoneInfo |

### Структура swing_metrics

```python
swing_metrics = {
    'num_swings': int,             # Общее количество свингов (переименовано из swings_count)
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
3. **_normalize_zone**: Текущая реализация **НЕ** сохраняет `swing_context` и `original_zone` (требуется доработка в Этапе 0).
4. **Два бэкенда**: Plotly поддерживается полностью, Matplotlib — частично (см. Known Limitations).
5. **Fallback контекста**: При отсутствии `swing_context` методы возвращают `[]` или `None`, **без** fallback на global context.

---

## Backward Compatibility Strategy

### Приоритет параметров

Система разрешения конфигурации (реализуется в Этапе 0):

```
Явные параметры > default_config > Hardcoded defaults
```

**Пример**:
```python
# Явный параметр ВСЕГДА имеет приоритет
visualizer.plot_zone_detail(
    data, zone,
    show_indicators=True,  # ← Используется это значение
    **{'show_indicators': False}  # Игнорируется с WARNING
)
```

### Новые параметры default_config

Все новые флаги **выключены по умолчанию** для обеспечения BC:

```python
self.default_config = {
    ...
    'show_zone_stats': True,                    # Существующий (без изменений)
    'show_zone_metrics': False,                 # NEW: выключено для BC
    'show_aggregate_metrics': False,            # NEW: выключено для BC
    'aggregate_metrics_mode': 'compact',        # NEW: компактный режим по умолчанию
    'show_swings': False,                       # NEW: выключено для BC
    'metrics_annotation_position': 'top-left',  # NEW: позиция аннотаций
}
```

### Валидация kwargs

Этап 0 внедряет whitelist для валидации:

```python
ALLOWED_DETAIL_KWARGS = {
    'context_bars', 'max_zone_detail_bars',
    'xaxis_num_ticks', 'time_axis_mode',
    # ... другие документированные параметры
}

# При неизвестном ключе:
logger.warning("Unknown parameter '%s' will be ignored", unknown_key)
```

### Regression Testing

Обязательные тесты (добавляются в Этапе 0):
- Старые вызовы `plot_zone_detail(data, zone)` работают идентично
- Старые вызовы с `show_zone_stats=True` не меняют поведение
- Проверка приоритета: явный параметр > kwargs

---

## План реализации

### [x] 🎯 Этап 0: Infrastructure & Pre-requisites

**Приоритет**: КРИТИЧЕСКИЙ (блокирует Этапы 1-3)
**Затраты**: 4-6 часов
**Цель**: Создать инфраструктуру для безопасного добавления новых функций
**Зависимости**: Нет

#### Подзадачи

##### [x] 0.1. Рефакторинг `_prepare_zone_data()` для сохранения SwingContext (1.5 часа)

**Проблема**: Текущий код использует `asdict()` для dataclass, что теряет `SwingContext` и методы.

**Решение**:

```python
def _prepare_zone_data(self, zones_data: Union[List[Dict], pd.DataFrame, List[Any]]) -> List[Dict]:
    """
    Подготовка данных зон для визуализации.

    ВАЖНО: Для ZoneInfo всегда используем _normalize_zone() вместо asdict()
    для сохранения swing_context и original_zone.
    """
    if isinstance(zones_data, pd.DataFrame):
        return zones_data.to_dict('records')

    elif isinstance(zones_data, list):
        normalized: List[Dict[str, Any]] = []
        for zone in zones_data:
            if isinstance(zone, dict):
                normalized.append(zone)
                continue

            # КРИТИЧНО: Используем _normalize_zone для ZoneInfo
            if isinstance(zone, ZoneInfo):
                normalized.append(self._normalize_zone(zone))
                continue

            # Fallback для других объектов
            if hasattr(zone, "to_analyzer_format"):
                try:
                    normalized.append(zone.to_analyzer_format())
                    continue
                except Exception:
                    self.logger.debug("Failed to call to_analyzer_format() on %s", zone)

            if is_dataclass(zone):
                # Для других dataclasses (не ZoneInfo)
                normalized.append(asdict(zone))
            elif hasattr(zone, "__dict__"):
                normalized.append({
                    key: getattr(zone, key) for key in dir(zone)
                    if not key.startswith("_") and not callable(getattr(zone, key))
                })
            else:
                raise ValueError("Unsupported zone object type: %r" % (type(zone),))

        return normalized
    else:
        raise ValueError("zones_data must be DataFrame or list of dicts")
```

##### [x] 0.2. Обновление `_normalize_zone()` для сохранения контекста (0.5 часа)

   ```python
   def _normalize_zone(self, zone: Union[Dict[str, Any], ZoneInfo, Any]) -> Dict[str, Any]:
    """
    Приведение зоны к словарю с сохранением метаданных ZoneInfo.

    ВАЖНО: Сохраняет swing_context и original_zone для доступа к методам.
    """
       if isinstance(zone, dict):
        # Уже нормализован — возвращаем как есть
        return zone

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

            # NEW: Сохранение контекста для Этапов 1-3
            'swing_context': zone.swing_context,  # Для методов SwingContext
               'original_zone': zone,                 # Для методов ZoneInfo
           }

       # Fallback для других типов
       normalized = self._prepare_zone_data([zone])
       if not normalized:
           raise ValueError("Unable to normalize zone object")
       return normalized[0]
   ```

##### [x] 0.3. Создание helper `_add_annotation()` (1.5 часа)

   ```python
def _add_annotation(
    self,
    fig: Union[go.Figure, plt.Figure],
    text: str,
    position: str = 'top-left',
    row: int = 1,
    col: int = 1,
    **kwargs
) -> None:
    """
    Универсальный метод добавления текстовых аннотаций.

    Args:
        fig: Plotly или Matplotlib figure
        text: Текст аннотации (Plotly: с <br>, Matplotlib: с \n)
        position: Позиция ('top-left', 'top-right', 'bottom-left', 'bottom-right')
        row, col: Позиция subplot (только Plotly)
        **kwargs: Дополнительные параметры стилизации

    Notes:
        - Plotly: использует fig.add_annotation с xref/yref='paper'
        - Matplotlib: использует ax.text с transform=ax.transAxes
    """
    if self.backend == 'plotly':
        # Маппинг позиций в координаты
        position_coords = {
            'top-left': {'x': 0.02, 'y': 0.98, 'xanchor': 'left', 'yanchor': 'top'},
            'top-right': {'x': 0.98, 'y': 0.98, 'xanchor': 'right', 'yanchor': 'top'},
            'bottom-left': {'x': 0.02, 'y': 0.02, 'xanchor': 'left', 'yanchor': 'bottom'},
            'bottom-right': {'x': 0.98, 'y': 0.02, 'xanchor': 'right', 'yanchor': 'bottom'},
        }

        coords = position_coords.get(position, position_coords['top-left'])

        fig.add_annotation(
            text=text,
            xref='paper', yref='paper',
            x=coords['x'], y=coords['y'],
            xanchor=coords['xanchor'], yanchor=coords['yanchor'],
            showarrow=False,
            font=dict(size=kwargs.get('font_size', 10), family='monospace'),
            align='left',
            bgcolor=kwargs.get('bgcolor', 'rgba(255,255,255,0.8)'),
            bordercolor=kwargs.get('bordercolor', 'rgba(0,0,0,0.1)'),
            borderwidth=1,
            borderpad=4,
            row=row, col=col
        )

    else:  # matplotlib
        # Маппинг позиций в координаты axes
        position_coords = {
            'top-left': (0.02, 0.98, 'left', 'top'),
            'top-right': (0.98, 0.98, 'right', 'top'),
            'bottom-left': (0.02, 0.02, 'left', 'bottom'),
            'bottom-right': (0.98, 0.02, 'right', 'bottom'),
        }

        x, y, ha, va = position_coords.get(position, position_coords['top-left'])

        # Выбираем subplot (matplotlib использует 0-indexed axes)
        ax = fig.axes[row - 1] if row <= len(fig.axes) else fig.axes[0]

        # Конвертируем <br> в \n для Matplotlib
        matplotlib_text = text.replace('<br>', '\n')

        ax.text(
            x, y, matplotlib_text,
            transform=ax.transAxes,
            fontsize=kwargs.get('font_size', 8),
            fontfamily='monospace',
            ha=ha, va=va,
            bbox=dict(
                boxstyle='round,pad=0.5',
                facecolor=kwargs.get('bgcolor', 'wheat'),
                alpha=kwargs.get('alpha', 0.8),
                edgecolor=kwargs.get('bordercolor', 'black'),
                linewidth=kwargs.get('borderwidth', 1)
            )
        )
```

##### [x] 0.4. Интеграция с системой тем (1 час)

```python
# В __init__ ZoneVisualizer
def __init__(self, backend: str = 'plotly', theme: Optional[str] = None, **kwargs):
    super().__init__(backend)

    # Инициализация темы
    from copy import deepcopy
    from .themes import ChartThemes

    self.theme_manager = ChartThemes()
    self.theme_name = theme or 'bquant_light'

    # Глубокое копирование исключает побочные эффекты между инстансами
    self.theme = deepcopy(self.theme_manager.get_theme(self.theme_name))

    # Расширить тему цветами для свингов (если отсутствуют)
    colors = self.theme.setdefault('colors', {})
    if 'swing_peak' not in colors:
        colors['swing_peak'] = '#d62728'
    if 'swing_trough' not in colors:
        colors['swing_trough'] = '#2ca02c'

    # ... existing code ...
```

**Обновление ChartThemes** (добавить в `bquant/visualization/themes.py`):

```python
# В каждую тему добавить:
'colors': {
    ...
    'swing_peak': '#d62728',      # Красный для пиков
    'swing_trough': '#2ca02c',    # Зелёный для впадин
}
```

##### [x] 0.5. Система валидации kwargs (0.5 часа)

```python
# В начале модуля
import warnings

# Константы whitelists
ALLOWED_DETAIL_KWARGS = {
    'context_bars', 'max_zone_detail_bars',
    'xaxis_num_ticks', 'time_axis_mode',
}

ALLOWED_OVERVIEW_KWARGS = {
    'xaxis_num_ticks', 'time_axis_mode',
    'show_gap_lines',
}

def _validate_and_get_config(
    self,
    param_name: str,
    explicit_value: Any,
    kwargs: Dict[str, Any],
    default: Any,
    allowed_kwargs: Set[str]
) -> Tuple[Any, Dict]:
    """
    Унифицированное разрешение конфигурации с валидацией.

    Приоритет: explicit_value > default_config > default

    Returns:
        (resolved_value, cleaned_kwargs)
    """
    # Валидация kwargs
    unknown_keys = set(kwargs.keys()) - allowed_kwargs
    if unknown_keys:
        message = "Unknown parameters will be ignored: %s" % ', '.join(unknown_keys)
        self.logger.warning(message)
        warnings.warn(
            message,
            category=UserWarning,
            stacklevel=2
        )

    # Разрешение значения
    if explicit_value is not None:
        # Явный параметр имеет максимальный приоритет
        # Проверяем конфликт с kwargs
        if param_name in kwargs and kwargs[param_name] != explicit_value:
            self.logger.warning(
                "Parameter '%s' specified both explicitly and in kwargs. "
                "Using explicit value: %s (kwargs value %s ignored)",
                param_name, explicit_value, kwargs[param_name]
            )
        return explicit_value, {k: v for k, v in kwargs.items() if k in allowed_kwargs}

    # Проверяем kwargs
    if param_name in kwargs:
        return kwargs[param_name], {k: v for k, v in kwargs.items() if k in allowed_kwargs and k != param_name}

    # Проверяем default_config
    if param_name in self.default_config:
        return self.default_config[param_name], {k: v for k, v in kwargs.items() if k in allowed_kwargs}

    # Hardcoded default
    return default, {k: v for k, v in kwargs.items() if k in allowed_kwargs}
```

##### [x] 0.6. Тестирование инфраструктуры (1 час)

**Новые тесты** (`tests/visualization/test_infrastructure.py`):

```python
def test_prepare_zone_data_preserves_swing_context():
    """Проверка сохранения SwingContext при нормализации."""
    zone_info = ZoneInfo(
        ...,
        swing_context=SwingContext(...)
    )

    visualizer = ZoneVisualizer()
    normalized = visualizer._prepare_zone_data([zone_info])

    assert len(normalized) == 1
    assert 'swing_context' in normalized[0]
    assert 'original_zone' in normalized[0]
    assert normalized[0]['original_zone'] is zone_info

def test_add_annotation_plotly():
    """Проверка _add_annotation для Plotly."""
    visualizer = ZoneVisualizer(backend='plotly')
    fig = go.Figure()

    visualizer._add_annotation(
        fig,
        text="Test<br>Annotation",
        position='top-left'
    )

    assert len(fig.layout.annotations) == 1
    assert fig.layout.annotations[0].text == "Test<br>Annotation"

def test_kwargs_validation():
    """Проверка валидации kwargs."""
    visualizer = ZoneVisualizer()

    # Неизвестный параметр должен вызвать WARNING
    with pytest.warns(UserWarning, match="Unknown parameters"):
        visualizer._validate_and_get_config(
            'show_indicators',
            None,
            {'unknown_param': True},
            True,
            {'show_indicators'}
        )

def test_backward_compatibility():
    """Проверка обратной совместимости."""
    # Старый вызов должен работать без изменений
    visualizer = ZoneVisualizer()
    data = get_sample_data()
    zone = create_test_zone()

    fig = visualizer.plot_zone_detail(data, zone)
    # Должен создать фигуру без ошибок
    assert fig is not None
```

#### Критерии успеха Этапа 0

- ✅ `_prepare_zone_data()` сохраняет `swing_context` для ZoneInfo
- ✅ `_normalize_zone()` возвращает `original_zone` в словаре
- ✅ `_add_annotation()` работает для Plotly и Matplotlib
- ✅ Тема содержит цвета `swing_peak` и `swing_trough`
- ✅ Валидация kwargs логирует неизвестные параметры
- ✅ Regression tests: старые вызовы работают без изменений
- ✅ Нет breaking changes

---

### [x] 🎯 Этап 1: Метрики в Detail режиме

**Приоритет**: ВЫСОКИЙ
**Затраты**: 6-8 часов (увеличено с учетом BC и UX)
**Цель**: Добавить текстовое отображение swing/shape метрик на графике detail
**Зависимости**: ✅ Этап 0 завершён

#### Изменения в сигнатуре

```python
def plot_zone_detail(
    self,
    price_data: pd.DataFrame,
    zone: Union[Dict, ZoneInfo],
    context_bars: int = 20,

    # === НОВЫЕ ПАРАМЕТРЫ ===
    show_zone_metrics: bool = False,  # NEW: По умолчанию выключено для BC

    # === СУЩЕСТВУЮЩИЕ ===
    show_indicators: bool = True,
    show_volume: bool = True,
    show_zone_stats: bool = None,  # None = используем default_config
    time_axis_mode: str = 'dense',
    xaxis_num_ticks: int = 16,
    **kwargs
) -> Union[go.Figure, plt.Figure]:
    """
    Детальный просмотр зоны с опциональными метриками.

    NEW PARAMS (v1.0):
        show_zone_metrics: Отображать swing/shape метрики как текстовую аннотацию.
            При True метрики объединяются с show_zone_stats в единый блок.
            По умолчанию False для обратной совместимости.

    BEHAVIOR:
        - show_zone_stats=True, show_zone_metrics=False: Только базовая информация (BC)
        - show_zone_stats=True, show_zone_metrics=True: Объединённый блок
        - show_zone_stats=False, show_zone_metrics=True: Только метрики
        - Оба False: Без аннотаций
    """
    # Валидация и разрешение конфигурации
    show_zone_metrics, kwargs = self._validate_and_get_config(
        'show_zone_metrics',
        show_zone_metrics,
        kwargs,
        default=False,  # Hardcoded default для BC
        allowed_kwargs=ALLOWED_DETAIL_KWARGS
    )

    # ... existing code ...

    # Рефакторинг блока аннотаций
    if show_zone_stats is None:
        show_zone_stats = self.default_config.get('show_zone_stats', True)

    if show_zone_metrics or show_zone_stats:
        annotation_text = self._build_zone_annotation_text(
            zone,
            include_basic_stats=show_zone_stats,
            include_metrics=show_zone_metrics
        )

        if annotation_text:
            position = self.default_config.get('metrics_annotation_position', 'top-left')

            # Используем helper из Этапа 0
            self._add_annotation(
                fig,
                text=annotation_text,
                position=position,
                row=1, col=1
            )

    return fig
```

#### Подзадачи

##### [x] 1.1. Рефакторинг существующих аннотаций (1 час)

**Проблема**: Текущий код напрямую вызывает `fig.add_annotation()` в `_create_plotly_zone_detail()`.

**Решение**: Извлечь логику в `_build_zone_annotation_text()` для переиспользования.

   ```python
   def _build_zone_annotation_text(
       self,
       zone: Union[Dict, ZoneInfo],
       include_basic_stats: bool = True,
    include_metrics: bool = False
   ) -> str:
       """
       Построить объединённый текст аннотации зоны.

    Args:
        zone: Зона для отображения
        include_basic_stats: Включить базовую информацию (Type, Duration, Strength)
        include_metrics: Включить swing/shape метрики

    Returns:
        Форматированный текст (с <br> для Plotly или \n для Matplotlib)
       """
       parts = []

       # === БАЗОВАЯ ИНФОРМАЦИЯ (старый show_zone_stats) ===
       if include_basic_stats:
           zone_dict = zone if isinstance(zone, dict) else self._normalize_zone(zone)
           zone_id = zone_dict.get('zone_id', '?')
           zone_type = zone_dict.get('type', 'n/a')
           duration = zone_dict.get('duration', 'n/a')

           parts.append(f"Zone #{zone_id} ({zone_type}) • {duration} bars")

        # Старые метрики (strength, если есть)
           features = zone_dict.get('features', {})
           if 'strength' in features:
               parts.append(f"Strength: {features['strength']:.2f}")

       # === НОВЫЕ МЕТРИКИ ===
       if include_metrics:
           metrics = self._extract_zone_metrics(zone)

           # Разделитель (если были базовые статы)
           if parts:
            parts.append("-" * 20)

        # Swing Metrics с диагностикой
        swing_text = self._format_swing_metrics(
            metrics['swing_metrics'],
            zone_id=zone.get('zone_id') if isinstance(zone, dict) else zone.zone_id,
            zone_duration=zone.get('duration') if isinstance(zone, dict) else zone.duration
        )
           parts.append(swing_text)

           # Shape Metrics
           shape_text = self._format_shape_metrics(
               metrics['shape_metrics'],
               indicator_name=metrics['indicator_name']
           )
           parts.append(shape_text)

    separator = '<br>' if self.backend == 'plotly' else '\n'
    return separator.join(parts)
   ```

##### [x] 1.2. Реализация `_extract_zone_metrics()` (0.5 часа)

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
        indicator_context = zone.indicator_context
    else:
        features = zone.get('features', {})
        indicator_context = zone.get('indicator_context', {})

    metadata = features.get('metadata', {})

    # Извлечь метрики
    swing_metrics = metadata.get('swing_metrics')  # dict | None
    shape_metrics = metadata.get('shape_metrics')  # dict | None

    # Определить имя индикатора для shape_metrics
    indicator_name = indicator_context.get('detection_indicator', 'indicator')

    return {
        'swing_metrics': swing_metrics,
        'shape_metrics': shape_metrics,
        'indicator_name': indicator_name
    }
```

##### [x] 1.3. Форматирование метрик с диагностикой (2 часа)

```python
def _format_swing_metrics(
    self,
    swing_metrics: Optional[Dict],
    zone_id: Any = '?',
    zone_duration: int = 0
) -> str:
    """
    Форматирование swing_metrics в читаемый текст с диагностикой отсутствия.

    Args:
        swing_metrics: Словарь метрик или None
        zone_id: ID зоны (для логирования)
        zone_duration: Длительность зоны (для диагностики)
    """
       if swing_metrics is None:
        # Диагностика причины отсутствия
        reason = self._diagnose_missing_swing_metrics(zone_id, zone_duration)
        self.logger.info(
            "Zone %s has no swing metrics: %s",
            zone_id, reason
        )
        return f"📊 Swing Metrics: {reason}"

    # Проверка на пустые свинги
    num_swings = swing_metrics.get('num_swings', 0)
    if num_swings == 0:
        self.logger.debug("Zone %s has no swings detected", zone_id)
           return "📊 Swing Metrics: No swings detected"

    # Форматирование полных метрик
       rally_count = swing_metrics.get('rally_count', 0)
       drop_count = swing_metrics.get('drop_count', 0)
       avg_rally = swing_metrics.get('avg_rally')
       avg_drop = swing_metrics.get('avg_drop')
       ratio = swing_metrics.get('rally_to_drop_ratio')
       avg_rally_dur = swing_metrics.get('avg_rally_duration')
       avg_drop_dur = swing_metrics.get('avg_drop_duration')

       parts = ["📊 Swing Metrics:"]
    parts.append(f"  Swings: {num_swings} ({rally_count}↑ / {drop_count}↓)")

       if avg_rally is not None:
           dur_text = f" ({avg_rally_dur:.1f} bars)" if avg_rally_dur else ""
           parts.append(f"  Avg Rally: {avg_rally:+.2%}{dur_text}")

       if avg_drop is not None:
           dur_text = f" ({avg_drop_dur:.1f} bars)" if avg_drop_dur else ""
           parts.append(f"  Avg Drop: {avg_drop:+.2%}{dur_text}")

       if ratio is not None:
           parts.append(f"  Rally/Drop Ratio: {ratio:.2f}x")

    separator = '<br>' if self.backend == 'plotly' else '\n'
    return separator.join(parts)

def _diagnose_missing_swing_metrics(self, zone_id: Any, zone_duration: int) -> str:
    """
    Диагностика причины отсутствия swing метрик.

    Returns:
        Человекочитаемое объяснение
    """
    if zone_duration < 8:
        return f"Zone too short ({zone_duration} < 8 bars)"

    # Дополнительные проверки можно добавить:
    # - Проверка наличия swing_context
    # - Проверка вызова .analyze()
    # и т.д.

    return "Calculation failed or not performed"

def _format_shape_metrics(
    self,
    shape_metrics: Optional[Dict],
    indicator_name: str = 'indicator'
) -> str:
       """Форматирование shape_metrics в читаемый текст."""
       if shape_metrics is None:
           return "📈 Shape Metrics: Not available"

       skewness = shape_metrics.get('hist_skewness')
       kurtosis = shape_metrics.get('hist_kurtosis')

       if skewness is None and kurtosis is None:
           return "📈 Shape Metrics: Not available"

       parts = [f"📈 Shape Metrics ({indicator_name}):"]

       if skewness is not None:
        if abs(skewness) < 0.1:
            skew_label = "symmetric"
        elif skewness > 0:
            skew_label = "right-tailed"
        else:
            skew_label = "left-tailed"
           parts.append(f"  Skewness: {skewness:+.2f} ({skew_label})")

       if kurtosis is not None:
        if abs(kurtosis - 3) < 0.2:
            kurt_label = "mesokurtic"
        elif kurtosis > 3:
            kurt_label = "leptokurtic"
        else:
            kurt_label = "platykurtic"
           parts.append(f"  Kurtosis: {kurtosis:.2f} ({kurt_label})")

    separator = '<br>' if self.backend == 'plotly' else '\n'
    return separator.join(parts)
```

##### 1.4. Интеграция в `_create_plotly_zone_detail()` (1 час)

Заменить существующий блок аннотаций:

```python
# БЫЛО (старая реализация):
if self.default_config['show_zone_stats']:
    stats_parts = [
        f"Type: {zone.get('type', 'n/a')}",
        ...
    ]
    fig.add_annotation(...)

# СТАЛО (новая реализация):
# Вынесено в plot_zone_detail() с использованием _build_zone_annotation_text()
# (см. выше в "Изменения в сигнатуре")
```

##### 1.5. Edge Cases и граничные тесты (2 часа)

**Новые тесты** (`tests/visualization/test_zone_metrics_display.py`):

```python
def test_zone_without_swing_context():
    """Зона без swing_context (режим per_zone)."""
    zone = ZoneInfo(..., swing_context=None)
    visualizer = ZoneVisualizer()

    metrics = visualizer._extract_zone_metrics(zone)
    assert metrics['swing_metrics'] is None  # Допустимо

def test_zone_with_null_metrics():
    """Зона с swing_metrics=None (ошибка расчёта)."""
    zone = create_zone_with_features({
        'metadata': {'swing_metrics': None}
    })

    text = visualizer._format_swing_metrics(None, zone_id=1, zone_duration=15)
    assert "Not available" in text or "failed" in text

def test_zone_with_partial_metrics():
    """Зона с swing_metrics, но без shape_metrics."""
    zone = create_zone_with_features({
        'metadata': {
            'swing_metrics': {'num_swings': 5, ...},
            'shape_metrics': None
        }
    })

    text = visualizer._build_zone_annotation_text(zone, include_metrics=True)
    assert "Swing Metrics:" in text
    assert "Shape Metrics: Not available" in text

def test_backward_compatibility_old_call():
    """Старый вызов без новых параметров."""
    data = get_sample_data()
    zone = create_test_zone()

    # Старый вызов (без show_zone_metrics)
    fig = visualizer.plot_zone_detail(data, zone, show_zone_stats=True)

    # Должен работать идентично старой версии
    assert fig is not None
    # Проверить, что аннотация содержит только базовую инфо
    annotations = fig.layout.annotations
    assert len(annotations) > 0
    assert "Zone #" in annotations[0].text
    assert "Swing Metrics:" not in annotations[0].text  # НЕ показывать новые метрики

def test_combined_mode():
    """Объединённый режим: show_zone_stats=True + show_zone_metrics=True."""
    zone = create_zone_with_full_metrics()

    fig = visualizer.plot_zone_detail(
        data, zone,
        show_zone_stats=True,
        show_zone_metrics=True
    )

    annotations = fig.layout.annotations
    assert len(annotations) > 0
    text = annotations[0].text

    # Должен содержать ОБЕ части
    assert "Zone #" in text  # Базовая информация
    assert "Swing Metrics:" in text  # Новые метрики
    assert "─" in text  # Разделитель
```

##### 1.6. Документация и примеры (1.5 часа)

**Обновить** `examples/09_zone_metrics_visualization.py`:

```python
# Пример 1: Только базовая информация (BC)
fig = result.visualize('detail', zone_id=5, show_zone_stats=True)

# Пример 2: Только метрики
fig = result.visualize('detail', zone_id=5, show_zone_metrics=True)

# Пример 3: Объединённый режим
fig = result.visualize('detail', zone_id=5, show_zone_stats=True, show_zone_metrics=True)

# Пример 4: Диагностика отсутствующих метрик
# Зона без анализа свингов покажет "Calculation failed or not performed"
```

#### Визуальное представление

**Режим 1: show_zone_stats=True, show_zone_metrics=False (BC)**

```
┌─────────────────────────────────────┐
│ Zone #42 (bull) • 18 bars           │
│ Strength: 0.85                      │
└─────────────────────────────────────┘
```

**Режим 2: show_zone_stats=True, show_zone_metrics=True (объединённый)**

```
┌─────────────────────────────────────┐
│ Zone #42 (bull) • 18 bars           │
│ Strength: 0.85                      │
│ ────────────────────────────────    │
│ 📊 Swing Metrics:                   │
│   Swings: 4 (3↑ / 2↓)               │
│   Avg Rally: +1.2% (3.5 bars)       │
│   Avg Drop: -0.8% (2.1 bars)        │
│   Rally/Drop Ratio: 1.5x            │
│ ────────────────────────────────    │
│ 📈 Shape Metrics (MACD hist):       │
│   Skewness: +0.43 (right-tailed)    │
│   Kurtosis: 2.1 (platykurtic)       │
└─────────────────────────────────────┘
```

**Режим 3: Метрики отсутствуют**

```
┌─────────────────────────────────────┐
│ Zone #42 (bull) • 18 bars           │
│ Strength: 0.85                      │
│ ────────────────────────────────    │
│ 📊 Swing Metrics: Zone too short    │
│    (5 < 8 bars)                     │
│ 📈 Shape Metrics: Not available     │
└─────────────────────────────────────┘
```

#### Критерии успеха Этапа 1

- ✅ `plot_zone_detail()` принимает `show_zone_metrics=False` (default)
- ✅ Backward compatibility: старые вызовы работают идентично
- ✅ `_build_zone_annotation_text()` объединяет базовые статы и метрики
- ✅ `_format_swing_metrics()` диагностирует отсутствие данных с INFO-level логированием
- ✅ Метрики отображаются через `_add_annotation()` (Plotly и Matplotlib)
- ✅ Edge cases покрыты тестами (None metrics, partial metrics, короткие зоны)
- ✅ Regression tests проходят

---

### [x] 🎯 Этап 2: Агрегированные метрики в Overview (MVP)

**Приоритет**: СРЕДНИЙ
**Затраты**: 2-3 часа (упрощено до MVP)
**Цель**: Добавить минимальную статистику по зонам в overview режиме
**Зависимости**: ✅ Этап 0 завершён (Этап 1 опционален)

#### MVP Scope с гибкостью вывода

**Что ВКЛЮЧЕНО**:
- ✅ Агрегация по bull/bear зонам
- ✅ Режим `mean_std` (только он)
- ✅ Метрики: `avg_rally`, `avg_drop`, `rally_to_drop_ratio`, coverage %
- ✅ **Два режима вывода**: `'compact'` (по умолчанию, 4-6 строк) и `'full'` (расширенный, ~12-15 строк)

**Что ИСКЛЮЧЕНО** (перенесено в Future Work):
- ❌ Режимы агрегации `median`, `sum`
- ❌ Shape metrics в overview (оставляем только в detail до v1.1)

**Философия**: Компактный режим для быстрого обзора, полный — для детального анализа при необходимости.

#### Изменения в сигнатуре

```python
def plot_zones_on_price_chart(
    self,
    price_data: pd.DataFrame,
    zones_data: Union[List[Dict], pd.DataFrame],

    # === НОВЫЕ ПАРАМЕТРЫ ===
    show_aggregate_metrics: bool = False,        # NEW: По умолчанию выключено для BC
    aggregate_metrics_mode: str = 'compact',     # NEW: Режим вывода ('compact' | 'full')

    # === СУЩЕСТВУЮЩИЕ ===
    title: str = "Price Chart with Zones",
    show_indicators: bool = False,
    indicator_columns: Optional[List[str]] = None,
    indicator_chart_types: Optional[Dict[str, str]] = None,
    show_gap_lines: bool = False,
    xaxis_num_ticks: int = 16,
    time_axis_mode: str = 'dense',
    **kwargs
) -> Union[go.Figure, plt.Figure]:
    """
    Overview всех зон с опциональной агрегированной статистикой.

    NEW PARAMS (v1.0):
        show_aggregate_metrics: Отображать сводную статистику по всем зонам.
            MVP версия: только mean±std для swing metrics, раздельно для bull/bear.
            По умолчанию False для обратной совместимости.

        aggregate_metrics_mode: Режим отображения метрик (по умолчанию 'compact'):
            - 'compact': Компактный вывод (4-6 строк) — coverage, средние rally/drop, ratio
            - 'full': Полный вывод (~12-15 строк) — добавляет длительности свингов,
                      coverage-подразбиение и расширенную диагностику (shape metrics остаются только в detail)
    """
    # Валидация
    show_aggregate_metrics, kwargs = self._validate_and_get_config(
        'show_aggregate_metrics',
        show_aggregate_metrics,
        kwargs,
        default=False,
        allowed_kwargs=ALLOWED_OVERVIEW_KWARGS
    )

    aggregate_metrics_mode, kwargs = self._validate_and_get_config(
        'aggregate_metrics_mode',
        aggregate_metrics_mode,
        kwargs,
        default='compact',
        allowed_kwargs=ALLOWED_OVERVIEW_KWARGS
    )

    zones = self._prepare_zone_data(zones_data)

    # ... existing code (создание фигуры) ...

    # НОВОЕ: Агрегированные метрики (MVP)
    if show_aggregate_metrics and zones:
        aggregated = self._aggregate_zone_metrics_mvp(zones)

        if aggregated:
            annotation_text = self._format_aggregate_metrics_mvp(
                aggregated,
                mode=aggregate_metrics_mode
            )
            position = self.default_config.get('metrics_annotation_position', 'top-right')

            self._add_annotation(
                fig,
                text=annotation_text,
                position=position,
                row=1, col=1
            )

    return fig
```

#### Подзадачи

##### [x] 2.1. MVP агрегатор `_aggregate_zone_metrics_mvp()` (1 час)

```python
def _aggregate_zone_metrics_mvp(self, zones: List[Dict]) -> Optional[Dict[str, Any]]:
    """
    Агрегировать swing метрики по всем зонам (MVP версия).

    MVP Scope:
        - Только mean ± std (без median/sum)
        - Swing metrics (амплитуды + длительности) — без shape metrics
        - Раздельно для bull/bear

    Returns:
        {
            'bull': {
                'count': int,
                'with_swings': int,
                'avg_rally_mean': float, 'avg_rally_std': float,
                'avg_drop_mean': float, 'avg_drop_std': float,
                'ratio_mean': float,
                # Для full режима:
                'avg_rally_duration_mean': float, 'avg_rally_duration_std': float,
                'avg_drop_duration_mean': float, 'avg_drop_duration_std': float,
                'avg_duration_mean': float, 'avg_duration_std': float,
            },
            'bear': {...}
        }
        или None если нет данных
    """
    bull_zones = [z for z in zones if self._get_zone_type(z) == 'bull']
    bear_zones = [z for z in zones if self._get_zone_type(z) == 'bear']

    if not bull_zones and not bear_zones:
        self.logger.debug("No zones available for aggregation")
        return None

    result = {}

    for zone_type, zone_list in [('bull', bull_zones), ('bear', bear_zones)]:
        if not zone_list:
            continue

        # Извлечь swing metrics
        rallies = []
        drops = []
        ratios = []
        rally_durations = []
        drop_durations = []
        zones_with_swings = 0

        for zone in zone_list:
            metrics = self._extract_zone_metrics(zone)
            swing_metrics = metrics.get('swing_metrics')

            if swing_metrics and swing_metrics.get('num_swings', 0) > 0:
                zones_with_swings += 1

                # Базовые метрики (для compact)
                if 'avg_rally' in swing_metrics and swing_metrics['avg_rally'] is not None:
                    rallies.append(swing_metrics['avg_rally'])

                if 'avg_drop' in swing_metrics and swing_metrics['avg_drop'] is not None:
                    drops.append(swing_metrics['avg_drop'])

                if 'rally_to_drop_ratio' in swing_metrics and swing_metrics['rally_to_drop_ratio'] is not None:
                    ratios.append(swing_metrics['rally_to_drop_ratio'])

                # Дополнительные метрики (для full)
                if 'avg_rally_duration' in swing_metrics and swing_metrics['avg_rally_duration'] is not None:
                    rally_durations.append(swing_metrics['avg_rally_duration'])

                if 'avg_drop_duration' in swing_metrics and swing_metrics['avg_drop_duration'] is not None:
                    drop_durations.append(swing_metrics['avg_drop_duration'])

        # Вычислить статистику
        combined_durations = rally_durations + drop_durations
        result[zone_type] = {
            # Базовые (compact)
            'count': len(zone_list),
            'with_swings': zones_with_swings,
            'avg_rally_mean': np.mean(rallies) if rallies else None,
            'avg_rally_std': np.std(rallies) if rallies else None,
            'avg_drop_mean': np.mean(drops) if drops else None,
            'avg_drop_std': np.std(drops) if drops else None,
            'ratio_mean': np.mean(ratios) if ratios else None,

            # Дополнительные (full)
            'avg_rally_duration_mean': np.mean(rally_durations) if rally_durations else None,
            'avg_rally_duration_std': np.std(rally_durations) if rally_durations else None,
            'avg_drop_duration_mean': np.mean(drop_durations) if drop_durations else None,
            'avg_drop_duration_std': np.std(drop_durations) if drop_durations else None,
            'avg_duration_mean': np.mean(combined_durations) if combined_durations else None,
            'avg_duration_std': np.std(combined_durations) if combined_durations else None,
        }

    return result if result else None

def _get_zone_type(self, zone: Dict) -> str:
    """Извлечь тип зоны из dict."""
    return zone.get('type', 'unknown')
```

##### [x] 2.2. MVP форматирование с режимами `_format_aggregate_metrics_mvp()` (0.5-1 час)

```python
def _format_aggregate_metrics_mvp(
    self,
    aggregated: Dict[str, Any],
    mode: str = 'compact'
) -> str:
    """
    Форматирование агрегированных метрик с поддержкой режимов.

    Args:
        aggregated: Агрегированные данные
        mode: Режим вывода ('compact' | 'full')

    Returns:
        Форматированная строка с метриками
    """
    if mode not in ('compact', 'full'):
        self.logger.warning("Unknown aggregate_metrics_mode '%s', using 'compact'", mode)
        mode = 'compact'

    parts = []

    for zone_type in ['bull', 'bear']:
        if zone_type not in aggregated:
            continue

        stats = aggregated[zone_type]
        label = "📊 Bull Zones:" if zone_type == 'bull' else "📊 Bear Zones:"

        # Coverage (всегда показываем)
        coverage_pct = (stats['with_swings'] / stats['count'] * 100) if stats['count'] > 0 else 0
        parts.append(
            f"{label} {stats['with_swings']}/{stats['count']} with swings ({coverage_pct:.0f}%)"
        )

        # === COMPACT MODE: Только базовые метрики ===
        if mode == 'compact':
            # Rally/Drop (только mean ± std)
            if stats['avg_rally_mean'] is not None:
                parts.append(
                    f"  Rally: {stats['avg_rally_mean']:+.2%} ± {stats['avg_rally_std']:.2%}"
                )

            if stats['avg_drop_mean'] is not None:
                parts.append(
                    f"  Drop: {stats['avg_drop_mean']:+.2%} ± {stats['avg_drop_std']:.2%}"
                )

            # Ratio (только mean, без std для краткости)
            if stats['ratio_mean'] is not None:
                parts.append(f"  Ratio: {stats['ratio_mean']:.2f}x")

        # === FULL MODE: Расширенные метрики ===
        elif mode == 'full':
            # Rally с длительностью
            if stats['avg_rally_mean'] is not None:
                rally_text = f"  Rally: {stats['avg_rally_mean']:+.2%} ± {stats['avg_rally_std']:.2%}"
                if stats['avg_rally_duration_mean'] is not None:
                    rally_text += f" ({stats['avg_rally_duration_mean']:.1f} ± {stats['avg_rally_duration_std']:.1f} bars)"
                parts.append(rally_text)

            # Drop с длительностью
            if stats['avg_drop_mean'] is not None:
                drop_text = f"  Drop: {stats['avg_drop_mean']:+.2%} ± {stats['avg_drop_std']:.2%}"
                if stats['avg_drop_duration_mean'] is not None:
                    drop_text += f" ({stats['avg_drop_duration_mean']:.1f} ± {stats['avg_drop_duration_std']:.1f} bars)"
                parts.append(drop_text)

            # Ratio
            if stats['ratio_mean'] is not None:
                parts.append(f"  Ratio: {stats['ratio_mean']:.2f}x")

            if stats.get('avg_duration_mean') is not None:
                parts.append(
                    f"  Avg Swing Duration: {stats['avg_duration_mean']:.1f} ± {stats['avg_duration_std']:.1f} bars"
                    if stats.get('avg_duration_std') is not None
                    else f"  Avg Swing Duration: {stats['avg_duration_mean']:.1f} bars"
                )

    separator = '<br>' if self.backend == 'plotly' else '\n'
    return separator.join(parts)
```

##### [x] 2.3. Тестирование и примеры (0.5-1 час)

**Новые тесты** (`tests/visualization/test_zone_metrics_aggregation.py`):

```python
def test_aggregate_metrics_mvp():
    """Проверка MVP агрегации."""
    zones = create_mixed_zones(bull_count=5, bear_count=3)
    visualizer = ZoneVisualizer()

    aggregated = visualizer._aggregate_zone_metrics_mvp(zones)

    assert aggregated is not None
    assert 'bull' in aggregated
    assert 'bear' in aggregated
    assert aggregated['bull']['count'] == 5
    assert aggregated['bear']['count'] == 3

def test_aggregate_with_missing_metrics():
    """Зоны без метрик не ломают агрегацию."""
    zones = [
        create_zone_with_metrics({'num_swings': 5, ...}),
        create_zone_with_metrics(None),  # Нет метрик
        create_zone_with_metrics({'num_swings': 3, ...}),
    ]

    aggregated = visualizer._aggregate_zone_metrics_mvp(zones)

    # Должно работать, игнорируя зоны без метрик
    assert aggregated['bull']['with_swings'] == 2

def test_format_aggregate_compact_mode():
    """Проверка компактного режима форматирования."""
    aggregated = {
        'bull': {
            'count': 10,
            'with_swings': 8,
            'avg_rally_mean': 0.0118,
            'avg_rally_std': 0.0045,
            'avg_drop_mean': -0.0092,
            'avg_drop_std': 0.0038,
            'ratio_mean': 1.28
        }
    }

    text = visualizer._format_aggregate_metrics_mvp(aggregated, mode='compact')

    # Должен быть компактным
    lines = text.split('<br>')  # Для Plotly
    assert len(lines) <= 5  # Coverage + Rally + Drop + Ratio

    # Не должен содержать длительности
    assert 'bars' not in text
    # Не должен содержать shape metrics
    assert 'Skewness' not in text

def test_format_aggregate_full_mode():
    """Проверка полного режима форматирования."""
    aggregated = {
        'bull': {
            'count': 10,
            'with_swings': 8,
            'avg_rally_mean': 0.0118,
            'avg_rally_std': 0.0045,
            'avg_drop_mean': -0.0092,
            'avg_drop_std': 0.0038,
            'ratio_mean': 1.28,
            'avg_rally_duration_mean': 3.5,
            'avg_rally_duration_std': 1.2,
            'avg_drop_duration_mean': 2.1,
            'avg_drop_duration_std': 0.8,
            'avg_duration_mean': 6.4,
            'avg_duration_std': 1.9,
        }
    }

    text = visualizer._format_aggregate_metrics_mvp(aggregated, mode='full')

    # Должен содержать длительности
    assert 'bars' in text
    # Не должен содержать shape metrics
    assert 'Skewness' not in text
    assert 'Kurtosis' not in text
    # Должен содержать среднюю длительность
    assert 'Avg Swing Duration' in text

def test_format_aggregate_full_mode_missing_duration():
    """Полный режим с отсутствующими сводными длительностями."""
    aggregated = {
        'bull': {
            'count': 10,
            'with_swings': 8,
            'avg_rally_mean': 0.0118,
            'avg_rally_std': 0.0045,
            'avg_drop_mean': -0.0092,
            'avg_drop_std': 0.0038,
            'ratio_mean': 1.28,
            'avg_rally_duration_mean': 3.5,
            'avg_rally_duration_std': 1.2,
            'avg_drop_duration_mean': 2.1,
            'avg_drop_duration_std': 0.8,
            'avg_duration_mean': None,
            'avg_duration_std': None,
        }
    }

    # Не должно ломаться
    text = visualizer._format_aggregate_metrics_mvp(aggregated, mode='full')

    # Должен содержать длительности
    assert 'bars' in text
    # Не должен содержать среднюю длительность при её отсутствии
    assert 'Avg Swing Duration' not in text

def test_backward_compatibility_overview():
    """Старый вызов overview без новых параметров."""
    data = get_sample_data()
    zones = create_test_zones()

    fig = visualizer.plot_zones_on_price_chart(data, zones)

    # Должен работать без агрегированных метрик
    assert fig is not None
    # Проверить отсутствие дополнительных аннотаций
```

#### Визуальное представление

**Режим 'compact' (по умолчанию, 8 строк)**:

```
┌──────────────────────────────────────┐
│ 📊 Bull Zones: 23/37 with swings (62%)│
│   Rally: +1.18% ± 0.45%              │
│   Drop: -0.92% ± 0.38%               │
│   Ratio: 1.28x                       │
│ 📊 Bear Zones: 19/35 with swings (54%)│
│   Rally: +0.85% ± 0.32%              │
│   Drop: -1.05% ± 0.41%               │
│   Ratio: 0.81x                       │
└──────────────────────────────────────┘
```

**Режим 'full' (расширенный, ~16 строк)**:

```
┌───────────────────────────────────────────────────────┐
│ 📊 Bull Zones: 23/37 with swings (62%)                │
│   Rally: +1.18% ± 0.45% (3.5 ± 1.2 bars)              │
│   Drop: -0.92% ± 0.38% (2.1 ± 0.8 bars)               │
│   Ratio: 1.28x                                        │
│   Avg Swing Duration: 6.4 ± 1.9 bars                  │
│ 📊 Bear Zones: 19/35 with swings (54%)                │
│   Rally: +0.85% ± 0.32% (2.8 ± 0.9 bars)              │
│   Drop: -1.05% ± 0.41% (3.2 ± 1.1 bars)               │
│   Ratio: 0.81x                                        │
│   Avg Swing Duration: 6.9 ± 2.1 bars                  │
└───────────────────────────────────────────────────────┘
```

#### Критерии успеха Этапа 2 (MVP с гибкостью)

- ✅ `plot_zones_on_price_chart()` принимает `show_aggregate_metrics=False` (default)
- ✅ `plot_zones_on_price_chart()` принимает `aggregate_metrics_mode='compact'` (default)
- ✅ `_aggregate_zone_metrics_mvp()` работает только с `mean_std`
- ✅ Режим 'compact': вывод компактный (≤ 8 строк для bull + bear)
- ✅ Режим 'full': расширенный вывод (~12-16 строк) с длительностями и расширенной диагностикой без shape metrics
- ✅ Корректно обрабатывает зоны без метрик (skip_none=True)
- ✅ Graceful degradation: отсутствие swing metrics не ломает full режим (annotation fallback)
- ✅ Backward compatibility: старые вызовы работают
- ✅ Аннотация не загромождает график (особенно в compact)

---

### [x] 🎯 Этап 3: Визуализация свинг-точек (Plotly only)

**Приоритет**: ВЫСОКИЙ
**Затраты**: 5-7 часов (увеличено с учетом Plotly-only и защиты от edge cases)
**Цель**: Отображать свинг-точки из `SwingContext` на графиках (только Plotly в v1.0)
**Зависимости**: ✅ Этап 0 завершён

#### Изменения в сигнатуре

```python
def plot_zone_detail(
    self,
    price_data: pd.DataFrame,
    zone: Union[Dict, ZoneInfo],

    # === НОВЫЕ ПАРАМЕТРЫ ===
    show_swings: bool = False,           # NEW: Показать свинг-точки
    swing_marker_size: int = 10,         # NEW: Размер маркеров

    **kwargs
) -> Union[go.Figure, plt.Figure]:
    """
    Детальный просмотр зоны с опциональными свинг-точками.

    NEW PARAMS (v1.0):
        show_swings: Отображать свинг-точки из zone.swing_context.
            Только Plotly в v1.0, Matplotlib вызовет WARNING и пропустит.
        swing_marker_size: Размер маркеров свингов (default=10)

    LIMITATIONS (v1.0):
        - Matplotlib не поддерживается (см. Known Limitations)
        - При > 200 свингах выводится WARNING о производительности
    """
    # Валидация
    show_swings, kwargs = self._validate_and_get_config(
        'show_swings',
        show_swings,
        kwargs,
        default=False,
        allowed_kwargs=ALLOWED_DETAIL_KWARGS
    )

    # ... existing code ...

    # НОВОЕ: Добавить свинг-точки (только Plotly)
    if show_swings:
        if self.backend != 'plotly':
            self.logger.warning(
                "Swing overlay (show_swings=True) is only supported for Plotly backend. "
                "Matplotlib support will be added in v1.1. Skipping swing visualization."
            )
        else:
        swing_context = self._resolve_swing_context(zone)
        if swing_context:
                zone_swings = self._get_zone_swings_safe(zone, swing_context)

                # Защита от performance issues
                if len(zone_swings) > 200:
                    self.logger.warning(
                        "Zone has %d swing points. Rendering may be slow. "
                        "Consider filtering or increasing swing threshold.",
                        len(zone_swings)
                    )

            self._add_swing_overlay(
                fig,
                zone_swings,
                    row=1, col=1,
                marker_size=swing_marker_size
            )
            else:
                self.logger.debug(
                    "Zone %s has no swing_context. Ensure you called "
                    ".with_swing_scope('global') and .analyze()",
                    zone.get('zone_id') if isinstance(zone, dict) else zone.zone_id
                )

    return fig
```

#### Подзадачи

##### [x] 3.1. Resolver `_resolve_swing_context()` (0.5 часа)

```python
def _resolve_swing_context(self, zone: Union[Dict, ZoneInfo]) -> Optional[SwingContext]:
    """
    Извлечь SwingContext из зоны.

    Logic:
        1. Проверяем zone['swing_context'] (для normalized dict)
        2. Проверяем zone.swing_context (для ZoneInfo)
        3. Проверяем zone['original_zone'].swing_context
        4. Возвращаем None (НЕТ fallback на global)

    Returns:
        SwingContext или None
    """
    # Прямой доступ (normalized dict)
    if isinstance(zone, dict):
        swing_context = zone.get('swing_context')
        if swing_context:
            return swing_context

        # Попытка через original_zone
        original = zone.get('original_zone')
        if isinstance(original, ZoneInfo) and original.swing_context:
            return original.swing_context

        return None

    # ZoneInfo напрямую
    if isinstance(zone, ZoneInfo):
        return zone.swing_context

    return None

def _resolve_global_swing_context(self, zones: List[Dict]) -> Optional[SwingContext]:
    """
    Извлечь глобальный SwingContext из списка зон (для overview режима).

    Logic:
        Ищем первую зону с swing_context и предполагаем, что он глобальный.

    Returns:
        SwingContext или None
    """
    for zone in zones:
        swing_context = self._resolve_swing_context(zone)
        if swing_context:
            return swing_context

    return None

def _get_zone_swings_safe(
    self,
    zone: Union[Dict, ZoneInfo],
    swing_context: SwingContext
) -> List[SwingPoint]:
    """
    Безопасное извлечение свингов для зоны.

    Args:
        zone: Зона
        swing_context: Контекст свингов

    Returns:
        Список SwingPoint или []
    """
    try:
        # Для ZoneInfo используем метод
        if isinstance(zone, ZoneInfo):
            return zone.get_zone_swings()

        # Для dict пытаемся через original_zone
        original = zone.get('original_zone')
        if isinstance(original, ZoneInfo):
            return original.get_zone_swings()

        # Fallback: прямой вызов SwingContext.get_swings_for_zone
        # (требует ZoneInfo, создаём временный)
        temp_zone = ZoneInfo(
            zone_id=zone.get('zone_id', 0),
            type=zone.get('type', 'unknown'),
            start_idx=zone.get('start_idx', 0),
            end_idx=zone.get('end_idx', 0),
            start_time=zone.get('start_time'),
            end_time=zone.get('end_time'),
            duration=zone.get('duration', 0),
            data=zone.get('data', pd.DataFrame()),
            swing_context=swing_context
        )
        return temp_zone.get_zone_swings()

    except Exception as e:
        self.logger.warning("Failed to extract zone swings: %s", e)
        return []
```

##### [x] 3.2. Swing overlay `_add_swing_overlay()` (Plotly v1.0 + подготовка к Matplotlib, 2 часа)

```python
def _add_swing_overlay(
    self,
    fig: Union[go.Figure, plt.Figure],
    swing_points: List[SwingPoint],
    row: int = 1,
    col: int = 1,
    marker_size: int = 10
) -> None:
    """
    Добавить свинг-точки как scatter overlay.

    Args:
        fig: Plotly или Matplotlib figure
        swing_points: Список SwingPoint из SwingContext
        row, col: Позиция subplot (Plotly). Для Matplotlib используется axes[row - 1]
        marker_size: Размер маркеров

    Notes:
        - Plotly: добавляет два scatter trace (peaks, troughs)
        - Matplotlib: в v1.0 оставляем заглушку, реализация → Этап 4 (v1.1)
        - Цвета берутся из темы через `_get_theme_color()`
    """
    if not swing_points:
        self.logger.debug("No swing points provided for overlay")
        return

    peak_color = self._get_theme_color('swing_peak', '#d62728')
    trough_color = self._get_theme_color('swing_trough', '#2ca02c')

    peaks = [sp for sp in swing_points if sp.swing_type == 'peak']
    troughs = [sp for sp in swing_points if sp.swing_type == 'trough']

    if self.backend == 'plotly':
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
                    hovertemplate='<b>Peak</b><br>Price: %{y:.2f}<br>Time: %{x}<extra></extra>',
                    showlegend=True
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
                    hovertemplate='<b>Trough</b><br>Price: %{y:.2f}<br>Time: %{x}<extra></extra>',
                    showlegend=True
                ),
                row=row, col=col
            )

    elif self.backend == 'matplotlib':
        self.logger.warning(
            "Swing overlay for Matplotlib backend will be implemented in v1.1 (Этап 4). "
            "Current version skips overlay."
        )
        # Подготовительный код (структура axes, доступ к цветам) уже присутствует
        # Реализация: ax.scatter(...), маркеры '^'/'v', zorder=5

    else:
        self.logger.warning("Swing overlay not implemented for backend %s", self.backend)
```

##### [x] 3.3. Helper `_get_theme_color()` (0.5 часа)

```python
def _get_theme_color(self, role: str, default: str = '#000000') -> str:
    """
    Возвращает цвет для заданной роли из активной темы визуализатора.

    Args:
        role: идентификатор цвета (например, 'swing_peak', 'swing_trough')
        default: цвет по умолчанию, если тема не задаёт роль
    """
    colors = (self.theme or {}).get('colors', {})
    return colors.get(role, default)
```

- Использовать helper в `_add_swing_overlay()` и существующих зонах (`zone_colors`) для унификации цветов Plotly/Matplotlib.
- Подготовить кэш/передачу цвета в будущую ветку Matplotlib (см. Этап 4).

##### [x] 3.4. Overview режим (1 час)

```python
def plot_zones_on_price_chart(
    self,
    ...
    show_swings: bool = False,  # NEW
    swing_marker_size: int = 8,  # NEW: Меньше чем в detail
    ...
):
    """
    Overview всех зон с опциональными свинг-точками.

    NEW PARAMS (v1.0):
        show_swings: Отображать глобальные свинги из SwingContext.
            Только Plotly, показывает ВСЕ свинги в видимом диапазоне.
    """
    # ... existing code ...

    if show_swings and zones:
        if self.backend != 'plotly':
            self.logger.warning("Swing overlay only supported for Plotly (v1.0)")
        else:
        swing_context = self._resolve_global_swing_context(zones)
        if swing_context:
            # Фильтровать свинги по видимому диапазону
            visible_swings = [
                sp for sp in swing_context.swing_points
                    if price_data.index[0] <= sp.timestamp <= price_data.index[-1]
                ]

                if len(visible_swings) > 500:
                    self.logger.warning(
                        "Overview has %d swing points. Consider using detail view "
                        "or filtering data range.",
                        len(visible_swings)
                    )

                self._add_swing_overlay(
                    fig,
                    visible_swings,
                    row=1, col=1,
                    marker_size=swing_marker_size
                )

    return fig
```

##### 3.4. Тестирование и edge cases (1.5 часа)

**Новые тесты** (`tests/visualization/test_swing_overlay.py`):

```python
def test_swing_overlay_plotly():
    """Базовая проверка отображения свингов в Plotly."""
    visualizer = ZoneVisualizer(backend='plotly')
    zone = create_zone_with_swings(num_swings=10)

    fig = visualizer.plot_zone_detail(
        data, zone,
        show_swings=True
    )

    # Проверить наличие traces для peaks и troughs
    swing_traces = [t for t in fig.data if 'Swing' in t.name]
    assert len(swing_traces) == 2  # Peaks + Troughs

def test_swing_overlay_matplotlib_warning():
    """Matplotlib должен логировать WARNING и пропускать."""
    visualizer = ZoneVisualizer(backend='matplotlib')
    zone = create_zone_with_swings(num_swings=10)

    with pytest.warns(UserWarning, match="only supported for Plotly"):
        fig = visualizer.plot_zone_detail(
            data, zone,
            show_swings=True
        )

    # Фигура должна создаться, но без свингов
    assert fig is not None

def test_zone_without_swing_context():
    """Зона без swing_context не ломает визуализацию."""
    visualizer = ZoneVisualizer(backend='plotly')
    zone = ZoneInfo(..., swing_context=None)

    fig = visualizer.plot_zone_detail(
        data, zone,
        show_swings=True  # Запрошено, но недоступно
    )

    # Должно залогировать DEBUG и продолжить без свингов
    assert fig is not None

def test_performance_warning_many_swings():
    """Проверка WARNING при большом числе свингов."""
    zone = create_zone_with_swings(num_swings=250)

    with pytest.warns(UserWarning, match="Rendering may be slow"):
        fig = visualizer.plot_zone_detail(
            data, zone,
            show_swings=True
        )

def test_swing_colors_from_theme():
    """Проверка использования цветов из темы."""
    visualizer = ZoneVisualizer(theme='bquant_dark')
    zone = create_zone_with_swings(num_swings=5)

    fig = visualizer.plot_zone_detail(data, zone, show_swings=True)

    # Проверить, что цвета взяты из темы
    peak_trace = next(t for t in fig.data if 'Peak' in t.name)
    expected_color = visualizer.theme['colors']['swing_peak']
    assert peak_trace.marker.color == expected_color
```

##### 3.5. Документация и примеры (1 час)

**Обновить** `examples/zone_analysis_global_swings.py`:

```python
# Добавить визуализацию свингов
print("\n=== Визуализация зоны с глобальными свингами ===")

# Detail view с свингами
fig = global_result.visualize(
    'detail',
    zone_id=0,  # Первая бычья зона
    show_zone_metrics=True,
    show_swings=True,
    swing_marker_size=12
)
fig.show()

# Overview со всеми свингами
fig = global_result.visualize(
    'overview',
    show_aggregate_metrics=True,
    show_swings=True
)
fig.show()
```

#### Критерии успеха Этапа 3 (Plotly only)

- ✅ `_add_swing_overlay()` корректно отображает SwingPoint (только Plotly)
- ✅ Matplotlib вызывает WARNING и пропускает визуализацию
- ✅ Работает для `detail` и `overview` режимов
- ✅ Peaks/Troughs используют цвета из темы
- ✅ При > 200 свингах выводится WARNING о производительности
- ✅ Зоны без `swing_context` не ломают визуализацию (graceful degradation)
- ✅ Тесты покрывают edge cases

---

## Итоговая оценка трудозатрат

| Этап | Описание | Затраты | Приоритет | Зависимости |
|------|----------|---------|-----------|-------------|
| **0** | Infrastructure & Pre-requisites | 4-6 часов | КРИТИЧЕСКИЙ | ✅ Нет |
| **1** | Метрики в Detail | 6-8 часов | ВЫСОКИЙ | Этап 0 |
| **2** | Агрегированные метрики (MVP) | 2-3 часа | СРЕДНИЙ | Этап 0 |
| **3** | Визуализация свингов (Plotly only) | 5-7 часов | ВЫСОКИЙ | Этап 0 |
| **ИТОГО** | | **17-24 часа** | | |

**Сравнение с предыдущими оценками**:
- v6.0 (оптимистичная): 10-14 часов
- v7.0 (реалистичная): 17-24 часа
- **Изменение**: +7-10 часов на инфраструктуру, BC, edge cases, UX

---

## Последовательность реализации

### ✅ Рекомендуемый подход: Последовательная реализация

```
┌───────────────────────────────────────────┐
│ Этап 0 (4-6ч) → ОБЯЗАТЕЛЬНО ПЕРВЫМ       │
│    ↓                                      │
│ Этап 1 (6-8ч) или Этап 3 (5-7ч)         │
│    ↓                                      │
│ Этап 2 (2-3ч) — опционально              │
│                                           │
│ ИТОГО: 11-17 часов (минимум без Этапа 2) │
└───────────────────────────────────────────┘
```

**Обоснование последовательности**:
- Этап 0 **блокирует** все остальные (создаёт инфраструктуру)
- Этапы 1 и 3 **независимы** после Этапа 0 (можно выбрать приоритетный)
- Этап 2 (MVP) — **опционален** (nice-to-have для overview)

---

## Known Limitations (v1.0)

### 1. Matplotlib Support

**Ограничение**: Swing overlay (`show_swings=True`) **не поддерживается** в Matplotlib в v1.0.

**Workaround**:
- Используйте Plotly backend для визуализации свингов
- Matplotlib поддержка будет добавлена в **v1.1** (Этап 4)

**Поведение**:
```python
visualizer = ZoneVisualizer(backend='matplotlib')
fig = visualizer.plot_zone_detail(data, zone, show_swings=True)
# WARNING: Swing overlay (show_swings=True) is only supported for Plotly...
# Фигура создаётся без свингов
```

### 2. Performance для больших датасетов

**Ограничение**: При > 200 свингах рендеринг может замедляться.

**Mitigation**:
- Логируется WARNING при превышении порога
- Рекомендация пользователю: фильтровать данные или увеличивать swing threshold

**Будущее улучшение** (v1.2):
- Downsampling свингов для overview режима
- Опция `max_swings_to_display`

### 3. Aggregation Modes

**Ограничение**: В v1.0 поддерживается только режим агрегации `mean_std`, нет `median` и `sum`.

**Обоснование**: MVP scope для сокращения трудозатрат.

**Доступно**: Два режима **вывода** (`compact` и `full`), но без выбора метода агрегации.

**Будущее улучшение** (v1.2):
- Добавить параметр `aggregation_mode` с выбором методов ('mean_std', 'median', 'sum')
- Дополнительные методы агрегации

### 4. Fallback для SwingContext

**Ограничение**: Нет автоматического fallback на global context при отсутствии zone-level context.

**Обоснование**: Избежание неявного поведения, которое может запутать пользователя.

**Поведение**:
- Если `zone.swing_context is None` → методы возвращают `[]` или `None`
- Логируется DEBUG с подсказкой вызвать `.with_swing_scope('global')`

---

## Future Work

### [ ] Этап 4: Matplotlib Parity (v1.1)

**Затраты**: 3-5 часов
**Scope**:
- Реализация `_add_swing_overlay()` для Matplotlib
- Специфика: `ax.scatter()`, `zorder`, `transform=ax.transData`
- Тесты паритета Plotly vs Matplotlib
- Вынести получение цветов зон/свингов в `_get_theme_color(role)` (используется зонами и overlay) для единообразия бекендов
- Подготовить тестовую инфраструктуру (`pytest.mark.parametrize('backend', ...)`) для `test_swing_overlay`, чтобы Matplotlib добавился без рефакторинга

### [ ] Этап 5: Расширенная агрегация (v1.2)

**Затраты**: 2-3 часа
**Scope**:
- Режимы агрегации `median`, `sum` (дополнительно к `mean_std`)
- Опция `aggregation_mode` в API для выбора метода агрегации
- **Примечание**: Режимы вывода `compact`/`full` уже реализованы в v1.0

### [ ] Этап 6: Performance Optimizations (v1.2)

**Затраты**: 2-3 часа
**Scope**:
- Downsampling свингов при > 500 точек
- Опция `max_swings_to_display`
- Кэширование форматированных метрик

---

## Изменяемые файлы

### Основной модуль

**`bquant/visualization/zones.py`**:
- Этап 0: `_prepare_zone_data()`, `_normalize_zone()`, `_add_annotation()`, `__init__()`, `_validate_and_get_config()`
- Этап 1: `_extract_zone_metrics()`, `_build_zone_annotation_text()`, `_format_swing_metrics()`, `_format_shape_metrics()`, `_diagnose_missing_swing_metrics()`, обновление `plot_zone_detail()`
- Этап 2: `_aggregate_zone_metrics_mvp()`, `_format_aggregate_metrics_mvp()`, обновление `plot_zones_on_price_chart()`
- Этап 3: `_add_swing_overlay()`, `_resolve_swing_context()`, `_resolve_global_swing_context()`, `_get_zone_swings_safe()`

### Темы

**`bquant/visualization/themes.py`**:
- Добавить `swing_peak` и `swing_trough` в все темы

### Тесты

**Новые файлы**:
- `tests/visualization/test_infrastructure.py` — Этап 0
- `tests/visualization/test_zone_metrics_display.py` — Этап 1
- `tests/visualization/test_zone_metrics_aggregation.py` — Этап 2
- `tests/visualization/test_swing_overlay.py` — Этап 3

**Обновить**:
- `tests/visualization/test_zones_visualizer.py` — regression tests для BC

### Примеры

**Обновить**:
- `examples/09_zone_metrics_visualization.py` — Этапы 1, 2
- `examples/zone_analysis_global_swings.py` — Этап 3

### NotebookSimulator Smoke-Test (`04_zones_sample.py`)

- **Сценарий**: запускать `research/notebooks/04_zones_sample.py` после завершения каждого этапа (0→3) как дымовой/регрессионный тест визуализатора.
- **Запуск**: `python research/notebooks/04_zones_sample.py --no-trap` — флаг `--no-trap` отключает паузы `NotebookSimulator` и позволяет агенту прогонять весь скрипт автоматически.
- **Артефакты**: скрипт сохраняет графики на диск; разработчик/ИИ-ассистент обязан просмотреть полученные файлы и визуально подтвердить корректность.
- **Пошаговый режим**: основная логика в скрипте закомментирована блоками; допускается раскомментировать и выполнять только релевантные шаги для быстрого тестирования. Перед сдачей релиза рекомендуется прогонять все шаги целиком, несмотря на повышенное время выполнения.
- **Регрессия**: при любом изменении API параметров визуализатора обновлять скрипт, чтобы сохранённые примеры оставались валидными.

---

## Обновление документации

### 1. User Guide

**`docs/user_guide/zone_analysis.md`**:
- Новый раздел "Visualizing Zone Metrics" (Этапы 1, 2)
- Новый раздел "Swing Point Visualization" (Этап 3)
- Скриншоты графиков с метриками
- Migration guide для пользователей

### 2. API Documentation

**`docs/api/visualization/zones.md`**:
- Документировать новые параметры `plot_zone_detail()` и `plot_zones_on_price_chart()`
- Документировать внутренние методы (для расширения)
- Секция "Known Limitations (v1.0)"

### 3. Migration Guide

**Новый файл** `docs/migration/v1.0_zone_metrics.md`:

```markdown
# Migration Guide: Zone Metrics Visualization (v1.0)

## Breaking Changes

**None!** Все новые параметры опциональны с default=False.

## New Features

1. **Zone Metrics Display** (Этап 1)
2. **Aggregate Statistics** (Этап 2, MVP)
3. **Swing Point Overlay** (Этап 3, Plotly only)

## Usage Examples

### Before (v0.x)
...

### After (v1.0)
...

## Known Limitations

- Matplotlib swing overlay → v1.1
- Only mean_std aggregation → v1.2 for median/sum

## Troubleshooting

### "Swing Metrics: Not available"
...
```

---

## Критерии успеха (общие)

### Этап 0
- ✅ Вся инфраструктура создана и протестирована
- ✅ Нет breaking changes
- ✅ Regression tests проходят

### Этап 1
- ✅ Метрики отображаются корректно для зон с данными
- ✅ Graceful degradation для зон без метрик с понятной диагностикой
- ✅ Backward compatibility полная
- ✅ Edge cases покрыты тестами

### Этап 2
- ✅ MVP агрегация работает для bull/bear зон
- ✅ Компактный вывод (≤ 8 строк)
- ✅ Корректная обработка зон без метрик
- ✅ Backward compatibility

### Этап 3
- ✅ Swing overlay работает в Plotly
- ✅ Matplotlib логирует WARNING и пропускает
- ✅ Производительность: WARNING при > 200 свингах
- ✅ Graceful degradation для зон без swing_context

---

## Примеры использования

### Пример 1: Метрики в detail (Этап 1)

```python
result = (
    analyze_zones(df)
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_col='macd_hist')
    .with_strategies(swing='zigzag')
    .with_swing_scope('global')
    .analyze()
    .build()
)

# Объединённый режим
fig = result.visualize(
    'detail',
    zone_id=5,
    show_zone_stats=True,      # Базовая информация
    show_zone_metrics=True     # + Swing/Shape метрики
)
fig.show()
```

### Пример 2: Агрегированные метрики (Этап 2, MVP)

```python
# Overview с компактной статистикой (по умолчанию)
fig = result.visualize(
    'overview',
    show_aggregate_metrics=True  # Компактный режим (8 строк)
)
fig.show()

# Overview с полной статистикой (включая длительности и shape)
fig = result.visualize(
    'overview',
    show_aggregate_metrics=True,
    aggregate_metrics_mode='full'  # Полный режим (~16 строк)
)
fig.show()
```

### Пример 3: Свинг-точки (Этап 3, Plotly only)

```python
# Detail с метриками и свингами
fig = result.visualize(
    'detail',
    zone_id=5,
    show_zone_metrics=True,
    show_swings=True,           # Только Plotly в v1.0
    swing_marker_size=12
)
fig.show()

# Overview со всеми свингами
fig = result.visualize(
    'overview',
    show_aggregate_metrics=True,
    show_swings=True  # Глобальные свинги
)
fig.show()
```

### Пример 4: Backward Compatibility

```python
# Старый код работает без изменений
fig = result.visualize('detail', zone_id=5, show_zone_stats=True)
fig.show()
```

---

## Следующие шаги

### ✅ Завершено

1. ✅ **Утверждение упрощённого плана** (2025-11-08)
2. ✅ **Реализация gloswing.md** (2025-11-10)
3. ✅ **Архитектурная ревизия zomet.md** (2025-11-11, v7.0)

### 🚀 Готово к выполнению

4. **Реализация Этапа 0**: Infrastructure (4-6 часов) — **НАЧАТЬ ПЕРВЫМ**
5. **Реализация Этапа 1**: Метрики в detail (6-8 часов)
6. **Реализация Этапа 3**: Визуализация свингов (5-7 часов)
7. **Опционально Этап 2**: MVP агрегация (2-3 часа)

### ⏳ После реализации

8. **Тестирование**: Code review + интеграционные тесты (2-3 часа)
9. **Документация**: User guide + API docs + Migration guide (2-3 часа)
10. **Релиз v1.0**: Zone Metrics Visualization (Plotly-first)

### 🔮 Future Releases

11. **v1.1**: Matplotlib parity (Этап 4, 3-5 часов)
12. **v1.2**: Расширенная агрегация + Performance (Этапы 5-6, 4-6 часов)

---

**Автор**: Claude Code (ред. claude-sonnet-4.5)
**Версия документа**: 7.1 (добавлены режимы compact/full для агрегированных метрик)
**Дата обновления**: 2025-11-11

> **Критические изменения v7.0**:
>
> 1. ✅ Добавлен **Этап 0** (Infrastructure) как обязательный pre-requisite
> 2. ✅ Упрощён **Этап 2** до MVP (экономия 1-2 часа)
> 3. ✅ **Этап 3** теперь Plotly-only в v1.0 (Matplotlib в v1.1)
> 4. ✅ Добавлены секции **BC Strategy**, **Known Limitations**, **Future Work**
> 5. ✅ Реалистичная оценка трудозатрат: **17-24 часа** (вместо 10-14)
> 6. ✅ Полная спецификация **edge cases** и **graceful degradation**
> 7. ✅ UX improvements: диагностика отсутствующих метрик, понятные сообщения

> **Изменения v7.1** (2025-11-11):
>
> 1. ✅ Добавлен параметр `aggregate_metrics_mode` с режимами `'compact'` и `'full'`
> 2. ✅ Режим `'compact'` (по умолчанию): 8 строк — coverage, rally/drop, ratio
> 3. ✅ Режим `'full'`: ~16 строк — добавляет длительности свингов и сводную длительность без shape metrics
> 4. ✅ Расширен агрегатор для сбора дополнительных данных (амплитуды + длительности)
> 5. ✅ Graceful degradation: отсутствие swing metrics не ломает full режим
> 6. ✅ Без изменений трудозатрат (0.5 часа доп. на форматирование уже учтены)
