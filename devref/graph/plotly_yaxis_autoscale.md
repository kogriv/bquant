# Plotly Y-Axis Autoscaling Issue with Annotations

**Date:** 2025-11-06
**Component:** `bquant.visualization.zones.ZoneVisualizer`
**Severity:** High (visual regression)

## Problem

При использовании `ZoneVisualizer` с параметрами `show_zone_labels=True` или кастомной конфигурацией графики "сплющивались" - ось Y начиналась с 0 вместо автоматического масштабирования по данным. Это делало свечи нечитаемыми (отображались как горизонтальные линии в верхней части графика).

### Условия воспроизведения

```python
# Ломает график
visualizer = ZoneVisualizer(
    backend='plotly',
    width=1400,
    height=800,
    show_zone_labels=True,  # ← Вызывает проблему
    show_zone_stats=True,
)
fig = visualizer.plot_zone_detail(data, zone, show_indicators=True, show_volume=True)
```

**Ожидаемо:** Ось Y автоматически масштабируется по диапазону цен (например, 3320-3460)
**Фактически:** Ось Y начинается с 0, график "сплющен" (0-3500)

### Визуальные симптомы

- Candlestick свечи отображаются как маленькие горизонтальные линии в верхней части графика
- Ось Y начинается с 0 вместо минимальной цены
- Зона-подсветка занимает всю высоту панели
- Multi-panel layout (price + indicators + volume) визуально деформирован

## Root Cause

Две проблемы в `bquant/visualization/zones.py`:

### 1. Конфликт `row`/`col` с `xref`/`yref` в аннотациях (строки 1379-1380)

```python
# НЕПРАВИЛЬНО - вызывает сброс domain настроек оси Y
fig.add_annotation(
    xref='x',
    yref='paper',
    x=zone_x,
    y=1.05,
    text=f"Zone {zone.get('zone_id', 'n/a')}",
    row=1,  # ← Конфликт!
    col=1,  # ← Конфликт!
)
```

Когда используются явные `xref`/`yref`, параметры `row`/`col` вызывают внутренний конфликт в Plotly. Это приводит к сбросу настройки `domain` оси Y, которая критична для multi-panel layout.

### 2. Перезапись yaxis настроек в update_layout (строка 1416)

```python
# НЕПРАВИЛЬНО - перезаписывает domain
fig.update_layout(
    title=title,
    width=self.default_config['width'],
    height=self.default_config['height'],
    yaxis=dict(rangemode='normal'),  # ← Удаляет domain!
)
```

Вызов `update_layout(yaxis=dict(...))` **полностью заменяет** конфигурацию `yaxis`, удаляя ранее установленные настройки, включая критический параметр `domain` (определяет границы панели в multi-panel layout).

## Solution

### Исправление 1: Удалить row/col из аннотаций

```python
# ПРАВИЛЬНО
fig.add_annotation(
    xref='x',
    yref='paper',
    x=zone_x,
    y=1.05,
    text=f"Zone {zone.get('zone_id', 'n/a')}",
    showarrow=False,
    font=dict(size=12, color='black'),
    bgcolor='rgba(255,255,255,0.8)',
    # row/col не используются с явными xref/yref
)
```

**Файл:** `bquant/visualization/zones.py:1370-1380`
**Изменение:** Удалены параметры `row=1, col=1`

### Исправление 2: Удалить yaxis из update_layout

```python
# ПРАВИЛЬНО
fig.update_layout(
    title=title,
    width=self.default_config['width'],
    height=self.default_config['height'],
    xaxis_rangeslider_visible=False,
    template='plotly_white',
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1.0),
    # yaxis=dict(rangemode='normal') - УДАЛЕНО
    # rangemode='normal' уже установлено через fig.update_yaxes() выше
)
```

**Файл:** `bquant/visualization/zones.py:1409-1418`
**Изменение:** Удалена строка `yaxis=dict(rangemode='normal')`
**Обоснование:** Параметр `rangemode='normal'` уже установлен ранее через `fig.update_yaxes(rangemode='normal', row=1, col=1)` (строки 1082, 1187)

## Verification

Проверка инкрементальным тестированием:

```python
# Test 1: Default - OK
vis1 = ZoneVisualizer(backend='plotly')
fig1 = vis1.plot_zone_detail(data, zone)  # ✅ Работает

# Test 2: + width/height - OK
vis2 = ZoneVisualizer(backend='plotly', width=1400, height=800)
fig2 = vis2.plot_zone_detail(data, zone)  # ✅ Работает

# Test 3: + show_zone_labels - БЫЛО: СЛОМАНО, СТАЛО: OK
vis3 = ZoneVisualizer(backend='plotly', width=1400, height=800,
                      show_zone_labels=True, show_zone_stats=True)
fig3 = vis3.plot_zone_detail(data, zone)  # ✅ Теперь работает!
```

## Key Learnings

1. **Plotly аннотации:** При использовании `xref`/`yref` НЕ использовать `row`/`col` - они конфликтуют
2. **update_layout vs update_yaxes:** `update_layout(yaxis=dict(...))` **заменяет** всю конфигурацию оси, используйте `update_yaxes()` для частичных обновлений
3. **Multi-panel layout:** Параметр `domain` критичен для корректного разделения панелей, любая его перезапись ломает layout
4. **Порядок имеет значение:** Настройки через `update_yaxes()` применяются ДО `update_layout()`, который может их перезаписать

## Related Files

- `bquant/visualization/zones.py` - основной файл с исправлениями
- `research/notebooks/04_zones_sample.py` - тестовый скрипт для воспроизведения
- `docs/api/visualization/zones.md` - документация API

## Status

✅ **Resolved** (2025-11-06)
