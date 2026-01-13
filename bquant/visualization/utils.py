"""
Утилиты для визуализации BQuant.

Содержит вспомогательные функции для работы с временными рядами,
форматирования меток осей и других задач визуализации.
"""
from typing import List, Tuple
import pandas as pd


def find_all_gaps(dt_index: pd.DatetimeIndex) -> list[list[str]]:
    """
    Анализирует DatetimeIndex, находит разрывы и возвращает их в формате,
    совместимом с Plotly rangebreaks.
    """
    if not isinstance(dt_index, pd.DatetimeIndex) or len(dt_index) < 2:
        return []

    # 1. Вычисляем разницу во времени между соседними точками
    time_diffs = dt_index.to_series().diff()

    # 2. Определяем нормальный интервал (медиана - для устойчивости к выбросам)
    #    и порог для определения "разрыва" (например, в 1.5 раза больше нормы)
    normal_interval = time_diffs.median()
    gap_threshold = normal_interval * 1.5

    # 3. Находим все точки, где начинается разрыв
    gaps = time_diffs[time_diffs > gap_threshold]

    if gaps.empty:
        return []

    # 4. Формируем список интервалов для Plotly
    #    Plotly ожидает список вида [ [start1, end1], [start2, end2], ... ]
    #    где start и end - строки в формате ISO (например, "2025-06-28T00:00:00")
    rangebreak_values = []
    for gap_end_time, duration in gaps.items():
        gap_start_time = gap_end_time - duration
        
        # Конвертируем Timestamp в строки ISO для Plotly
        # Plotly rangebreaks требует строки в формате ISO
        start_str = gap_start_time.isoformat() if hasattr(gap_start_time, 'isoformat') else str(gap_start_time)
        end_str = gap_end_time.isoformat() if hasattr(gap_end_time, 'isoformat') else str(gap_end_time)
        
        # Добавляем интервал в формате, который понимает Plotly
        rangebreak_values.append([start_str, end_str])
    
    return rangebreak_values


def generate_dense_axis_labels(
    timestamps: List[pd.Timestamp],
    positions: List[int],
    num_ticks_requested: int = 16
) -> Tuple[List[int], List[str]]:
    """
    Генерирует умные метки для оси X в режиме 'dense'.
    
    Создает двухэтажные метки с адаптивным форматированием на основе
    временного диапазона данных. Используется в визуализации зон для
    единообразного отображения временных меток на графиках.
    
    Логика форматирования:
    - < 24 часа: только время (%H:%M)
    - < 7 дней: дата и время (%d.%m + %H:%M) - двухэтажные метки
    - < 30 дней: дата, время опционально (если все времена одинаковые - только дата)
    - >= 30 дней: дата, год отдельно (%d.%m + жирный год) - двухэтажные метки
    
    Args:
        timestamps: Список временных меток (pd.Timestamp или совместимые типы).
                    Может быть получен из DataFrame.index
        positions: Список позиционных индексов (0..N-1) для оси X.
                   Должен соответствовать timestamps по длине
        num_ticks_requested: Желаемое количество меток (по умолчанию 16).
                            Автоматически корректируется на основе временного
                            диапазона для оптимальной читаемости
    
    Returns:
        Кортеж (tickvals, ticktext):
        - tickvals: List[int] - позиции на оси X для меток
        - ticktext: List[str] - текстовые метки (могут содержать HTML для двухэтажных меток)
    
    Example:
        >>> import pandas as pd
        >>> from bquant.visualization.utils import generate_dense_axis_labels
        >>> 
        >>> # Подготовка данных
        >>> timestamps = pd.date_range('2025-01-01', periods=100, freq='H')
        >>> positions = list(range(len(timestamps)))
        >>> 
        >>> # Генерация меток
        >>> tickvals, ticktext = generate_dense_axis_labels(timestamps, positions, num_ticks_requested=16)
        >>> 
        >>> # Использование в Plotly
        >>> fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)
    """
    # Проверяем входные данные (безопасная проверка для pandas объектов)
    if not timestamps or len(timestamps) == 0:
        return [], []
    if not positions or len(positions) == 0:
        return [], []
    
    # Преобразуем timestamps в список pd.Timestamp для единообразия
    # Обрабатываем разные типы входных данных (list, Index, Series)
    if hasattr(timestamps, '__iter__') and not isinstance(timestamps, str):
        x_dates = [pd.Timestamp(ts) if not isinstance(ts, pd.Timestamp) else ts for ts in timestamps]
    else:
        x_dates = [pd.Timestamp(timestamps)] if timestamps else []
    
    # Определяем количество тиков (умная логика на основе временного диапазона)
    data_points = len(positions)
    if data_points > 0 and len(x_dates) > 0:
        time_range = (x_dates[-1] - x_dates[0]).total_seconds()
        if time_range < 3600 * 24:
            # Меньше суток: больше тиков (30 точек на тик)
            ideal_ticks = max(8, min(20, data_points // 30))
        elif time_range < 3600 * 24 * 7:
            # Меньше недели: средняя плотность (6 точек на тик)
            ideal_ticks = max(8, min(20, data_points // 6))
        elif time_range < 3600 * 24 * 30:
            # Меньше месяца: меньше тиков (2 точки на тик)
            ideal_ticks = max(8, min(20, data_points // 2))
        else:
            # Больше месяца: минимальная плотность (10 точек на тик)
            ideal_ticks = max(8, min(20, data_points // 10))
        num_ticks = max(8, min(num_ticks_requested, ideal_ticks, data_points))
    else:
        num_ticks = max(8, min(num_ticks_requested, len(positions)))
    
    tick_step = max(1, len(positions) // num_ticks) if num_ticks > 0 else 1
    tick_positions = positions[::tick_step]
    
    # Умное форматирование даты/времени на основе временного диапазона
    show_date, show_time, show_year_separately = True, True, False
    if len(x_dates) > 0:
        time_range = (x_dates[-1] - x_dates[0]).total_seconds()
        if time_range < 3600 * 24:
            # Меньше суток: только время
            date_format, time_format, show_date = '%H:%M', '%H:%M', False
        elif time_range < 3600 * 24 * 7:
            # Меньше недели: дата и время
            date_format, time_format = '%d.%m', '%H:%M'
        elif time_range < 3600 * 24 * 30:
            # Меньше месяца: дата, время опционально
            date_format = '%d.%m'
            unique_times = set(dt.strftime('%H:%M') for dt in x_dates if hasattr(dt, 'strftime'))
            if len(unique_times) == 1:
                # Все времена одинаковые - показываем только дату
                time_format, show_time = '%d.%m', False
            else:
                time_format = '%H:%M'
        else:
            # Больше месяца: дата, год отдельно
            date_format, time_format, show_time, show_year_separately = '%d.%m', '%d.%m', False, True
    else:
        date_format, time_format = '%d.%m', '%H:%M'
    
    # Формируем двухэтажные метки
    tick_labels = []
    prev_year = None
    for i in range(0, len(positions), tick_step):
        if i < len(x_dates):
            date_obj = x_dates[i]
            current_year = date_obj.year if hasattr(date_obj, 'year') else None
            show_year = show_year_separately and (prev_year is None or current_year != prev_year)
            
            if hasattr(date_obj, 'strftime'):
                date_str = date_obj.strftime(date_format)
                time_str = date_obj.strftime(time_format)
            else:
                date_str = str(date_obj)
                time_str = str(date_obj)
            
            # Формируем метку с двухэтажным форматом (HTML для Plotly)
            if show_year and current_year is not None:
                label = f"{date_str}<br><b>{current_year}</b>"
            elif show_date and show_time and date_str != time_str:
                label = f"{date_str}<br>{time_str}"
            elif show_date:
                label = date_str
            else:
                label = time_str
            
            tick_labels.append(label)
            prev_year = current_year
        else:
            tick_labels.append('')
    
    # Гарантируем наличие последнего тика для полноты отображения
    if positions and positions[-1] not in tick_positions:
        last_idx = len(positions) - 1
        if last_idx < len(x_dates):
            date_obj = x_dates[last_idx]
            if hasattr(date_obj, 'strftime'):
                date_str = date_obj.strftime(date_format)
                time_str = date_obj.strftime(time_format)
            else:
                date_str = str(date_obj)
                time_str = str(date_obj)
            
            if show_date and show_time and date_str != time_str:
                label = f"{date_str}<br>{time_str}"
            elif show_date:
                label = date_str
            else:
                label = time_str
            
            tick_positions.append(positions[-1])
            tick_labels.append(label)
    
    return tick_positions, tick_labels
