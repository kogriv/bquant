# Будущие оптимизации для Global Swing Calculation

**Статус**: TODO / Future Enhancements
**Приоритет**: LOW (не требуется для типичных use cases)
**Предварительные требования**: Завершение [gloswing.md](gloswing.md) + реальная потребность в больших датасетах

---

## Контекст

Текущая реализация global swing calculation использует стандартные Python dataclasses для хранения SwingPoint объектов в памяти. Это приемлемо для большинства real-world сценариев:

- **Датасеты <100k bars**: Никаких проблем (~130-260 KB)
- **Датасеты 100k-1M bars**: Приемлемо (~1.3-2.6 MB)
- **Датасеты >1M bars**: Потенциальная проблема (>3 MB)

Оптимизации, описанные ниже, потребуются **только если**:
1. Появятся пользователи с датасетами >5M bars
2. Будет измерено реальное impact на performance/memory
3. Будет обоснована необходимость (cost-benefit analysis)

**Рекомендация**: Реализовывать **после** получения обратной связи от пользователей о реальных проблемах.

---

## Оптимизация 1: Lazy Loading SwingPoint

### Проблема

При очень больших датасетах (>5M bars) загрузка всех SwingPoint объектов в память может быть дорогой:
- SwingContext с 50,000 точек ≈ 13 MB
- При десериализации из кэша - весь объём загружается сразу

### Решение

Загружать SwingPoint по требованию из disk cache.

```python
# В bquant/analysis/zones/models.py

from typing import Optional, Dict, Any
import pickle
from pathlib import Path

@dataclass
class SwingContext:
    """
    FUTURE: Поддержка lazy loading для очень больших датасетов
    """
    swing_points: Optional[List[SwingPoint]] = None  # None если lazy mode
    indices: np.ndarray  # Всегда в памяти (для bisect)
    full_data_length: int
    strategy_name: str
    strategy_params: Dict[str, Any]

    # Lazy loading fields
    _lazy: bool = False
    _cache_path: Optional[Path] = None
    _loaded_ranges: Dict[tuple, List[SwingPoint]] = None  # Cache loaded chunks

    def __init__(self, ..., lazy_load: bool = False, cache_path: Optional[Path] = None):
        """
        Args:
            lazy_load: Если True, SwingPoint загружаются по требованию
            cache_path: Путь к файлу кэша со SwingPoint (для lazy mode)
        """
        if lazy_load:
            if cache_path is None:
                raise ValueError("cache_path required for lazy_load=True")
            self._lazy = True
            self._cache_path = cache_path
            self._loaded_ranges = {}
            self.swing_points = None  # Не загружаем в память
        else:
            self._lazy = False
            # swing_points загружены при инициализации

    def slice(self, start_idx: int, end_idx: int) -> List[SwingPoint]:
        """
        Нарезка пивотов с lazy loading поддержкой.
        """
        if not self._lazy:
            # Стандартный режим (текущая реализация)
            return self._slice_eager(start_idx, end_idx)

        # Lazy режим: загрузить только нужный диапазон
        return self._slice_lazy(start_idx, end_idx)

    def _slice_eager(self, start_idx: int, end_idx: int) -> List[SwingPoint]:
        """Текущая реализация - все точки в памяти."""
        if len(self.swing_points) == 0:
            return []

        left = bisect_left(self.indices, start_idx)
        right = bisect_right(self.indices, end_idx)

        left_with_neighbor = max(0, left - 1)
        right_with_neighbor = min(len(self.swing_points), right + 1)

        return self.swing_points[left_with_neighbor:right_with_neighbor]

    def _slice_lazy(self, start_idx: int, end_idx: int) -> List[SwingPoint]:
        """
        Lazy режим: загрузить SwingPoint для нужного диапазона из disk cache.
        """
        # 1. Определить диапазон индексов для загрузки
        left = bisect_left(self.indices, start_idx)
        right = bisect_right(self.indices, end_idx)

        left_with_neighbor = max(0, left - 1)
        right_with_neighbor = min(len(self.indices), right + 1)

        # 2. Проверить кэш загруженных диапазонов
        cache_key = (left_with_neighbor, right_with_neighbor)
        if cache_key in self._loaded_ranges:
            return self._loaded_ranges[cache_key]

        # 3. Загрузить из disk cache
        swing_points = self._load_swing_points_from_disk(
            left_with_neighbor,
            right_with_neighbor
        )

        # 4. Закэшировать в памяти для повторного использования
        self._loaded_ranges[cache_key] = swing_points

        # 5. Ограничить размер in-memory cache (LRU eviction)
        if len(self._loaded_ranges) > 10:  # Max 10 ranges в памяти
            # Удалить самый старый
            oldest_key = next(iter(self._loaded_ranges))
            del self._loaded_ranges[oldest_key]

        return swing_points

    def _load_swing_points_from_disk(
        self,
        left_idx: int,
        right_idx: int
    ) -> List[SwingPoint]:
        """
        Загрузить SwingPoint из disk cache.

        Предполагается, что SwingPoint сохранены в файле построчно
        или используется специальный формат (HDF5, Parquet).
        """
        with open(self._cache_path, 'rb') as f:
            # Seek к нужной позиции (требует индекс offsets)
            # Или загрузить весь файл и отфильтровать (проще, но медленнее)
            all_points = pickle.load(f)
            return all_points[left_idx:right_idx]
```

### Преимущества

- ✅ Memory footprint снижен до размера indices array + небольшой LRU cache
- ✅ Для 50,000 points: ~13 MB → ~400 KB (только indices)
- ✅ Поддержка очень больших датасетов (>10M bars)

### Недостатки

- ⚠️ Сложность реализации (disk I/O, caching, serialization format)
- ⚠️ Первый доступ к зоне медленнее (disk read)
- ⚠️ Требует специального формата хранения (индекс offsets для seek)

### Когда реализовывать

- Датасеты >5M bars
- Измеренное memory pressure (OOM errors)
- Кэши становятся критичными (cloud storage, shared cache)

---

## Оптимизация 2: Chunking для экстремальных датасетов

### Проблема

Расчёт swing indicator (ZigZag, FindPeaks) на датасете >5M bars может быть медленным:
- pandas-ta ZigZag на 10M bars может занять минуты
- Весь расчёт блокирует execution (нет progress feedback)

### Решение

Разбить датасет на временные chunks, рассчитать свинги для каждого chunk, затем склеить результаты.

```python
# В bquant/analysis/zones/pipeline.py

class ZoneAnalysisPipeline:

    LARGE_DATASET_THRESHOLD = 5_000_000  # 5M bars
    CHUNK_SIZE = 1_000_000  # 1M bars per chunk

    def _calculate_global_swings(self, data: pd.DataFrame) -> SwingContext:
        """
        UPDATED: Поддержка chunking для больших датасетов
        """
        if len(data) < self.LARGE_DATASET_THRESHOLD:
            # Стандартный режим для обычных датасетов
            return self._swing_strategy.calculate_global(data)

        # Chunking режим для больших датасетов
        self.logger.warning(
            f"Large dataset ({len(data)} bars), using chunked calculation. "
            f"Estimated memory: {self._estimate_swing_memory(data)} MB"
        )

        return self._calculate_global_swings_chunked(data)

    def _calculate_global_swings_chunked(
        self,
        data: pd.DataFrame
    ) -> SwingContext:
        """
        Chunked calculation для больших датасетов.

        Algorithm:
        1. Разбить data на chunks по CHUNK_SIZE bars
        2. Для каждого chunk рассчитать свинги
        3. Склеить результаты с разрешением граничных конфликтов
        """
        chunks = []
        chunk_swings = []

        # 1. Разбиение на chunks
        for i in range(0, len(data), self.CHUNK_SIZE):
            chunk_end = min(i + self.CHUNK_SIZE, len(data))
            chunk = data.iloc[i:chunk_end]
            chunks.append((i, chunk))

        self.logger.info(f"Processing {len(chunks)} chunks...")

        # 2. Расчёт для каждого chunk
        for chunk_idx, (offset, chunk) in enumerate(chunks):
            self.logger.info(
                f"Processing chunk {chunk_idx + 1}/{len(chunks)} "
                f"({len(chunk)} bars)..."
            )

            # Рассчитать свинги для chunk
            chunk_context = self._swing_strategy.calculate_global(chunk)

            # Скорректировать indices (относительно полного датасета)
            for sp in chunk_context.swing_points:
                sp.index += offset

            chunk_swings.extend(chunk_context.swing_points)

        # 3. Разрешение граничных конфликтов
        # (соседние chunks могут иметь дублирующиеся пивоты на границах)
        merged_swings = self._merge_chunk_swings(chunk_swings, data)

        # 4. Создание финального SwingContext
        indices = np.array([sp.index for sp in merged_swings])

        return SwingContext(
            swing_points=merged_swings,
            indices=indices,
            full_data_length=len(data),
            strategy_name=self._swing_strategy.get_metadata()['name'],
            strategy_params=self._swing_strategy.config_hash()
        )

    def _merge_chunk_swings(
        self,
        chunk_swings: List[SwingPoint],
        full_data: pd.DataFrame
    ) -> List[SwingPoint]:
        """
        Склеить свинги из chunks с разрешением граничных дубликатов.

        Problem:
            Chunk 1: [..., pivot@999]
            Chunk 2: [pivot@1000, ...]

            Пивоты на границах chunks могут дублироваться или конфликтовать.

        Solution:
            1. Сортировать все свинги по index
            2. Удалить дубликаты (близкие по индексу и цене)
            3. Пересчитать amplitude_to_next и duration_to_next
        """
        if not chunk_swings:
            return []

        # 1. Сортировка по index
        sorted_swings = sorted(chunk_swings, key=lambda sp: sp.index)

        # 2. Удаление дубликатов
        merged = []
        for i, sp in enumerate(sorted_swings):
            if i == 0:
                merged.append(sp)
                continue

            prev_sp = merged[-1]

            # Дубликат если индексы близки (<10 bars) и цены совпадают (±0.1%)
            if (sp.index - prev_sp.index < 10 and
                abs(sp.price - prev_sp.price) / prev_sp.price < 0.001):
                # Skip duplicate
                continue

            merged.append(sp)

        # 3. Пересчёт amplitude и duration
        for i in range(len(merged) - 1):
            curr = merged[i]
            next_sp = merged[i + 1]

            curr.amplitude_to_next = (next_sp.price / curr.price - 1) * 100
            curr.duration_to_next = next_sp.index - curr.index

        # Последняя точка не имеет next
        merged[-1].amplitude_to_next = None
        merged[-1].duration_to_next = None

        return merged

    def _estimate_swing_memory(self, data: pd.DataFrame) -> float:
        """
        Оценка потребления памяти SwingContext.

        Returns:
            Estimated memory in MB
        """
        estimated_swings = len(data) * 0.01  # ~1% bars = swings (rough estimate)
        bytes_per_point = 264
        total_bytes = estimated_swings * bytes_per_point
        return total_bytes / (1024 * 1024)  # Convert to MB
```

### Преимущества

- ✅ Поддержка датасетов любого размера
- ✅ Progress feedback (логирование по chunks)
- ✅ Возможность параллелизации (chunks независимы)

### Недостатки

- ⚠️ Сложность разрешения граничных конфликтов
- ⚠️ Потенциальная потеря точности на границах chunks
- ⚠️ Дополнительная логика merge

### Когда реализовывать

- Датасеты >5M bars регулярно используются
- Пользователи жалуются на медленный расчёт
- Измерено real performance impact

---

## Оптимизация 3: Numpy Structured Arrays

### Проблема

Python dataclasses имеют overhead:
- `SwingPoint` object ≈ 264 bytes
- Из них ~100 bytes - Python object overhead
- Для 50,000 точек → ~5 MB overhead

### Решение

Использовать numpy structured arrays вместо List[SwingPoint].

```python
# В bquant/analysis/zones/models.py

import numpy as np
from typing import NamedTuple

class SwingContext:
    """
    FUTURE: Memory-efficient альтернатива с numpy structured arrays
    """

    def __init__(self, swing_points: List[SwingPoint], ...):
        # Конвертировать в numpy structured array
        self._swing_array = self._to_numpy_array(swing_points)
        self.indices = self._swing_array['index']  # View, не копия
        # ... остальные поля

    def _to_numpy_array(self, swing_points: List[SwingPoint]) -> np.ndarray:
        """
        Конвертировать List[SwingPoint] в numpy structured array.
        """
        # Определить dtype
        swing_dtype = np.dtype([
            ('point_id', 'i4'),           # 4 bytes (vs 28 bytes Python int)
            ('index', 'i4'),              # 4 bytes
            ('price', 'f8'),              # 8 bytes (vs 24 bytes Python float)
            ('swing_type', 'U8'),         # 8 chars (vs 49+ bytes string)
            ('amplitude_to_next', 'f8'),  # 8 bytes
            ('duration_to_next', 'i4'),   # 4 bytes
            # timestamp и strategy_name/params хранить отдельно (они одинаковы для всех)
        ])
        # Итого: ~44 bytes per point (vs 264 bytes) → 83% экономия!

        # Создать array
        n = len(swing_points)
        arr = np.empty(n, dtype=swing_dtype)

        # Заполнить данными
        for i, sp in enumerate(swing_points):
            arr[i]['point_id'] = sp.point_id
            arr[i]['index'] = sp.index
            arr[i]['price'] = sp.price
            arr[i]['swing_type'] = sp.swing_type
            arr[i]['amplitude_to_next'] = sp.amplitude_to_next or 0.0
            arr[i]['duration_to_next'] = sp.duration_to_next or 0

        return arr

    def slice(self, start_idx: int, end_idx: int) -> List[SwingPoint]:
        """
        Нарезка с numpy array backend.
        """
        # Bisect на numpy array (быстрее чем на List)
        left = np.searchsorted(self.indices, start_idx, side='left')
        right = np.searchsorted(self.indices, end_idx, side='right')

        left_with_neighbor = max(0, left - 1)
        right_with_neighbor = min(len(self._swing_array), right + 1)

        # Получить slice numpy array
        slice_arr = self._swing_array[left_with_neighbor:right_with_neighbor]

        # Конвертировать обратно в List[SwingPoint] для API compatibility
        return self._from_numpy_array(slice_arr)

    def _from_numpy_array(self, arr: np.ndarray) -> List[SwingPoint]:
        """Конвертировать numpy array обратно в List[SwingPoint]."""
        swing_points = []
        for i in range(len(arr)):
            sp = SwingPoint(
                point_id=int(arr[i]['point_id']),
                timestamp=self._reconstruct_timestamp(arr[i]['index']),
                index=int(arr[i]['index']),
                price=float(arr[i]['price']),
                swing_type=str(arr[i]['swing_type']),
                amplitude_to_next=float(arr[i]['amplitude_to_next']) or None,
                duration_to_next=int(arr[i]['duration_to_next']) or None,
                strategy_name=self.strategy_name,
                strategy_params=self.strategy_params
            )
            swing_points.append(sp)
        return swing_points
```

### Преимущества

- ✅ ~83% экономия памяти (44 bytes vs 264 bytes per point)
- ✅ Faster bisect operations (numpy.searchsorted)
- ✅ Для 50,000 points: 13 MB → 2.2 MB

### Недостатки

- ⚠️ Сложность реализации (конвертация туда-обратно)
- ⚠️ Потеря type safety (numpy arrays не знают о SwingPoint type)
- ⚠️ API compatibility layer требует конвертации

### Когда реализовывать

- Memory profiling показал что SwingContext - bottleneck
- Датасеты >1M bars регулярно используются
- Measured real memory pressure

---

## Оптимизация 4: Graceful Fallback при MemoryError

### Проблема

На машинах с ограниченной памятью global расчёт может упасть с MemoryError.

### Решение

Автоматический откат на per_zone режим при нехватке памяти.

```python
# В bquant/analysis/zones/pipeline.py

def _calculate_global_swings(self, data: pd.DataFrame) -> Optional[SwingContext]:
    """
    UPDATED: Graceful fallback при MemoryError
    """
    try:
        # Попытка глобального расчёта
        swing_context = self._swing_strategy.calculate_global(data)
        return swing_context

    except MemoryError as e:
        self.logger.error(
            f"MemoryError during global swing calculation: {e}\n"
            f"Dataset size: {len(data)} bars\n"
            f"Estimated memory needed: {self._estimate_swing_memory(data):.1f} MB\n"
            f"Falling back to per_zone mode."
        )
        return None  # Fallback to per_zone

    except Exception as e:
        # Другие ошибки (уже есть в текущей версии)
        self.logger.warning(
            f"Global swing calculation failed: {e}. "
            f"Falling back to per_zone mode."
        )
        return None
```

### Преимущества

- ✅ Graceful degradation вместо crash
- ✅ Информативное сообщение об ошибке
- ✅ Автоматический выбор подходящего режима

### Недостатки

- ⚠️ Пользователь не знает заранее о проблеме (только после падения)
- ⚠️ Может скрывать реальные memory leaks

### Когда реализовывать

- После получения отчётов о MemoryError от пользователей
- При наличии telemetry/monitoring

---

## Рекомендации по приоритизации

Если появится реальная потребность в оптимизациях:

**Phase 1** (Quick wins):
1. ✅ Graceful MemoryError fallback (простая реализация, большая выгода)
2. ✅ Добавить `_estimate_swing_memory()` helper (для warning'ов)

**Phase 2** (Средняя сложность):
3. ⚠️ Chunking для >5M bars (если есть такие пользователи)

**Phase 3** (Сложные оптимизации):
4. ❌ Lazy Loading (только если disk cache становится критичным)
5. ❌ Numpy arrays (только если memory profiling показал bottleneck)

**Не делать preemptively** - дождаться реальных проблем от пользователей!

---

## Измерение эффективности

Перед реализацией любой оптимизации:

1. **Профилирование** текущей версии:
   ```python
   import memory_profiler

   @profile
   def test_current_implementation():
       result = analyze_zones(large_data).with_swing_scope('global').build()
   ```

2. **Benchmarking**:
   - Время выполнения на 1M, 5M, 10M bars
   - Memory peak usage
   - Disk I/O (если applicable)

3. **A/B Testing**:
   - Текущая версия vs оптимизированная
   - Измерить реальную разницу (не теоретическую)

4. **Cost-Benefit Analysis**:
   - Сколько пользователей получат выгоду?
   - Сколько времени на реализацию?
   - Какие риски/complexity добавляется?

**Только если benefit > cost** → реализовывать оптимизацию.

---

## Итог

Все описанные оптимизации - **идеи для будущего**, НЕ обязательства.

Текущая реализация (Python dataclasses, eager loading) **достаточна** для 99% use cases.

Реализовывать оптимизации **только при наличии реальной потребности** и **после измерения impact'а**.
