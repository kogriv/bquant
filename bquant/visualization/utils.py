# Псевдокод функции поиска разрывов
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
