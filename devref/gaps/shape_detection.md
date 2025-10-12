# Анализ форм зон MACD: Архитектура и методы кластеризации

**Дата:** 2025-10-12  
**Контекст:** Phase 3.2 - Shape стратегии

---

## Содержание

1. [Архитектурная простота добавления новых Shape стратегий](#1-архитектурная-простота-добавления-новых-shape-стратегий)
2. [Методы кластеризации для форм бугров](#2-методы-кластеризации-для-форм-бугров)
3. [Рекомендации по реализации](#3-рекомендации-по-реализации)

---

## 1. Архитектурная простота добавления новых Shape стратегий

### ✅ Очень легко добавить - 5 шагов:

#### Шаг 1: Создать новую стратегию (1 файл)
```
bquant/analysis/zones/strategies/shape/fourier.py
```

Необходимо:
- Наследовать dataclass
- Реализовать метод `calculate(zone_data) -> ShapeMetrics`
- Добавить декоратор `@StrategyRegistry.register_shape_strategy('fourier')`

**Сложность:** Низкая - шаблон уже есть в `statistical.py`

---

#### Шаг 2: Экспорт (1 строка)
```python
# bquant/analysis/zones/strategies/shape/__init__.py
from .fourier import FourierShapeStrategy
__all__ = ['StatisticalShapeStrategy', 'FourierShapeStrategy']
```

---

#### Шаг 3: Конфиг (опционально)
```python
# bquant/core/config.py
'shape_strategy': {
    'type': 'fourier',  # или оставить 'statistical' как default
    'params': {'n_components': 5}
}
```

---

#### Шаг 4: Использование (0 изменений в коде!)
```python
# Автоматически подхватывается из config
analyzer = ZoneFeaturesAnalyzer()

# Или явно
from bquant.analysis.zones.strategies.shape import FourierShapeStrategy
analyzer = ZoneFeaturesAnalyzer(
    shape_strategy=FourierShapeStrategy(n_components=5)
)
```

**ZoneFeaturesAnalyzer НЕ НУЖНО МЕНЯТЬ** - он уже поддерживает любые shape стратегии!

---

#### Шаг 5: Тесты
```
tests/unit/test_fourier_shape_strategy.py
```

**Итого:** ~3 новых файла, 0 изменений в существующем коде (кроме exports)

---

### 🎯 Почему архитектура отличная:

1. **Полная изоляция:**
   - Новая стратегия в отдельном файле
   - Не трогает другие стратегии
   - Не трогает ZoneFeaturesAnalyzer

2. **Strategy Pattern работает:**
   - Единый интерфейс `ShapeCalculationStrategy`
   - Автоматическая регистрация через декоратор
   - Фабрика в config.py

3. **Горячая замена:**
   ```python
   # В production
   analyzer.shape_strategy = FourierShapeStrategy()
   # Сразу работает!
   ```

4. **A/B тестирование:**
   ```python
   strategies = [
       StatisticalShapeStrategy(),
       FourierShapeStrategy(n_components=5),
       WaveletShapeStrategy(wavelet='db4')
   ]
   
   for strategy in strategies:
       analyzer.shape_strategy = strategy
       results = analyzer.extract_zone_features(zone)
       # Сравнить
   ```

---

## 2. Методы кластеризации для форм бугров

### Контекст задачи:

**Что кластеризуем:**
- Зоны MACD с разными формами гистограммы
- Признаки: skewness, kurtosis, smoothness, duration, amplitude...
- Цель: найти архетипы зон (Sharp Impulse, Smooth Trend, Late Wave...)

---

### 📊 Сравнение методов кластеризации

| Метод | Плюсы | Минусы | Подходит? |
|-------|-------|--------|-----------|
| **K-Means** | Быстрый, простой, хорошо масштабируется | Нужно знать K заранее, чувствителен к выбросам, только сферические кластеры | ✅ **ДА** (уже используется) |
| **DBSCAN** | Находит кластеры произвольной формы, находит выбросы автоматически | Сложно подобрать eps и min_samples, плохо с разной плотностью | ⚠️ **ВОЗМОЖНО** |
| **Hierarchical** | Не нужно знать K, дендрограмма для анализа | Медленный O(n³), чувствителен к шуму | ✅ **ДА** (для анализа) |
| **GMM** | Мягкая кластеризация (вероятности), эллипсоидные кластеры | Медленнее K-Means, может переобучиться | ✅ **ДА** (хорошая альтернатива) |
| **Agglomerative** | Иерархический, стабильный | Требует памяти O(n²) | ✅ **ДА** |
| **OPTICS** | Лучше DBSCAN для разной плотности | Сложнее интерпретировать | ⚠️ **ВОЗМОЖНО** |

---

### 🖼️ Computer Vision (CV) методы для форм

#### Почему CV методы релевантны:

**Формы "бугров" MACD гистограммы - это визуальные паттерны!**
- Каждая зона = визуальная форма графика
- Трейдеры визуально различают паттерны
- CV методы могут автоматизировать это

---

#### 5. **Contour Analysis & Shape Descriptors** ✅ (очень перспективно!)

**Идея:** Преобразовать временной ряд в контур и извлечь дескрипторы формы

**Методы:**

##### a) Hu Moments (инварианты моментов)
```python
import cv2
import numpy as np

def extract_hu_moments(zone_data):
    # 1. Нормализовать данные к изображению
    hist = zone_data['macd_hist'].values
    hist_normalized = ((hist - hist.min()) / (hist.max() - hist.min()) * 255).astype(np.uint8)
    
    # 2. Создать бинарное изображение
    img = np.zeros((100, len(hist)), dtype=np.uint8)
    for i, val in enumerate(hist_normalized):
        img[100-val:100, i] = 255
    
    # 3. Найти контур
    contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 4. Рассчитать Hu моменты (7 инвариантов)
    moments = cv2.moments(contours[0])
    hu_moments = cv2.HuMoments(moments).flatten()
    
    return hu_moments  # 7 чисел, инвариантных к масштабу, повороту, отражению
```

**Преимущества:**
- ✅ Инвариантны к масштабу (длина зоны не важна)
- ✅ Инвариантны к вертикальному сдвигу
- ✅ 7 компактных признаков
- ✅ Хорошо работают для сравнения форм

**Для форм бугров:** Отлично! Могут различать "острый пик" vs "плоская волна" независимо от размера.

---

##### b) Zernike Moments
```python
import mahotas

def extract_zernike_moments(zone_data, radius=8):
    # Преобразовать в изображение (аналогично выше)
    img = render_zone_as_image(zone_data)
    
    # Рассчитать Zernike моменты
    zernike = mahotas.features.zernike_moments(img, radius)
    
    return zernike  # 25+ признаков (зависит от radius)
```

**Преимущества:**
- ✅ Еще более мощные чем Hu Moments
- ✅ Ортогональные (независимые признаки)
- ✅ Хорошо восстанавливают форму

**Минусы:**
- ⚠️ Медленнее чем Hu Moments
- ⚠️ Требует библиотеку mahotas

---

#### 6. **Dynamic Time Warping (DTW)** ✅✅ (ОЧЕНЬ рекомендую!)

**Идея:** Измерить "расстояние" между двумя временными рядами, учитывая возможное растяжение по времени

```python
from dtaidistance import dtw

def cluster_zones_with_dtw(zones_list):
    # 1. Извлечь гистограммы
    histograms = [zone['macd_hist'].values for zone in zones_list]
    
    # 2. Построить матрицу расстояний DTW
    distance_matrix = dtw.distance_matrix_fast(histograms)
    
    # 3. Использовать с любым алгоритмом кластеризации
    from sklearn.cluster import AgglomerativeClustering
    clusterer = AgglomerativeClustering(
        n_clusters=4, 
        affinity='precomputed',
        linkage='average'
    )
    labels = clusterer.fit_predict(distance_matrix)
    
    return labels
```

**Преимущества для форм:**
- ✅✅ **ИДЕАЛЬНО для временных рядов разной длины**
- ✅ Находит похожие формы даже если растянуты/сжаты по времени
- ✅ Интуитивно понятно: "эти два бугра похожи по форме"
- ✅ Не нужна нормализация длины

**Пример:**
```
Zone 1: ___/\___  (20 баров)
Zone 2: ___/\___  (30 баров)
DTW: "Эти формы идентичны!" (несмотря на разную длину)
```

**Для кластеризации:** Сначала DTW distance matrix, потом Hierarchical clustering.

---

#### 7. **Template Matching** ✅ (для классификации известных паттернов)

**Идея:** Создать шаблоны эталонных форм и искать похожие

```python
import numpy as np
from scipy.spatial.distance import correlation

# Эталонные формы
templates = {
    'sharp_early': [0, 1, 5, 10, 8, 4, 2, 1, 0],  # Резкий ранний пик
    'smooth_trend': [0, 2, 4, 6, 8, 7, 5, 3, 1],  # Плавный тренд
    'late_wave': [0, 1, 2, 3, 5, 8, 10, 9, 5]     # Поздняя волна
}

def classify_zone_by_template(zone_hist):
    # Нормализовать длину зоны к длине шаблона
    normalized = np.interp(
        np.linspace(0, len(zone_hist), len(templates['sharp_early'])),
        np.arange(len(zone_hist)),
        zone_hist
    )
    
    # Найти наиболее похожий шаблон
    best_match = None
    best_score = float('inf')
    
    for name, template in templates.items():
        distance = correlation(normalized, template)
        if distance < best_score:
            best_score = distance
            best_match = name
    
    return best_match, best_score
```

**Преимущества:**
- ✅ Интерпретируемо: "Зона похожа на шаблон X с коэффициентом Y"
- ✅ Можно создавать шаблоны на основе экспертного знания
- ✅ Быстро

**Использование:** Не для кластеризации, а для классификации по известным паттернам.

---

#### 8. **Convolutional Neural Networks (CNN)** ⚠️ (если много данных)

**Идея:** Обучить нейросеть различать формы

```python
import tensorflow as tf

def create_shape_classifier():
    model = tf.keras.Sequential([
        # Вход: изображение зоны 64x64
        tf.keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(64, 64, 1)),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dense(4, activation='softmax')  # 4 класса форм
    ])
    
    return model

# Обучение
model = create_shape_classifier()
model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
model.fit(zone_images, zone_labels, epochs=50)
```

**Преимущества:**
- ✅ Может выучить сложные паттерны
- ✅ SOTA для image classification

**Минусы:**
- ❌ Нужно много данных (тысячи зон)
- ❌ Требует разметки (supervised learning)
- ❌ "Черный ящик"
- ❌ Избыточен для простых форм

**Вывод:** Использовать только если:
- Есть >10,000 размеченных зон
- Простые методы не дают результат
- Нужна высокая точность

---

#### 9. **Siamese Networks для Similarity Learning** ⚠️ (продвинуто)

**Идея:** Обучить сеть определять "похожесть" двух зон

```python
def create_siamese_network():
    # Базовая сеть для извлечения признаков
    base_network = tf.keras.Sequential([
        tf.keras.layers.Conv1D(64, 3, activation='relu', input_shape=(100, 1)),
        tf.keras.layers.MaxPooling1D(2),
        tf.keras.layers.Conv1D(128, 3, activation='relu'),
        tf.keras.layers.GlobalAveragePooling1D(),
        tf.keras.layers.Dense(64, activation='relu')
    ])
    
    # Siamese архитектура
    input_a = tf.keras.Input(shape=(100, 1))
    input_b = tf.keras.Input(shape=(100, 1))
    
    embedding_a = base_network(input_a)
    embedding_b = base_network(input_b)
    
    # Расстояние между эмбеддингами
    distance = tf.keras.layers.Lambda(
        lambda x: tf.abs(x[0] - x[1])
    )([embedding_a, embedding_b])
    
    output = tf.keras.layers.Dense(1, activation='sigmoid')(distance)
    
    model = tf.keras.Model(inputs=[input_a, input_b], outputs=output)
    
    return model
```

**Использование:**
1. Обучить на парах похожих/непохожих зон
2. Извлечь эмбеддинги для всех зон
3. Кластеризовать эмбеддинги (K-Means, Hierarchical)

**Преимущества:**
- ✅ Автоматически выучивает метрику похожести
- ✅ Эмбеддинги можно использовать для кластеризации

**Минусы:**
- ❌ Нужно много данных
- ❌ Сложность обучения

---

#### 10. **Image-based Features + Traditional ML** ✅ (hybrid подход)

**Идея:** Рендерить зону как изображение и извлекать признаки

```python
import matplotlib.pyplot as plt
from skimage import feature, io
import numpy as np

def extract_image_features(zone_data):
    # 1. Рендерить зону как изображение
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(zone_data['macd_hist'])
    ax.fill_between(range(len(zone_data)), zone_data['macd_hist'], alpha=0.3)
    ax.axis('off')
    
    # Сохранить в буфер
    fig.canvas.draw()
    img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    plt.close(fig)
    
    # 2. Извлечь признаки изображения
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # HOG (Histogram of Oriented Gradients)
    hog_features = feature.hog(gray, pixels_per_cell=(16, 16))
    
    # LBP (Local Binary Patterns)
    lbp = feature.local_binary_pattern(gray, P=8, R=1, method='uniform')
    lbp_hist, _ = np.histogram(lbp.ravel(), bins=59, range=(0, 59))
    lbp_hist = lbp_hist.astype(float) / lbp_hist.sum()
    
    # Объединить признаки
    features = np.concatenate([hog_features, lbp_hist])
    
    return features

# Затем кластеризовать эти признаки
```

**Преимущества:**
- ✅ Использует богатый арсенал CV методов
- ✅ HOG отлично для текстур и форм
- ✅ LBP для локальных паттернов

**Минусы:**
- ⚠️ Overhead рендеринга
- ⚠️ Зависит от размера/разрешения изображения

---

### 📊 Сравнительная таблица CV методов

| Метод | Сложность | Данных нужно | Интерпретируемость | Для форм бугров |
|-------|-----------|--------------|-------------------|-----------------|
| **Hu Moments** | Низкая | Мало | Средняя | ✅✅ Отлично |
| **Zernike Moments** | Средняя | Мало | Низкая | ✅ Хорошо |
| **DTW** | Низкая | Мало | Высокая | ✅✅✅ ИДЕАЛЬНО |
| **Template Matching** | Низкая | Мало (шаблоны) | Очень высокая | ✅ Хорошо для классификации |
| **CNN** | Высокая | Много (10k+) | Низкая | ⚠️ Избыточно |
| **Siamese Networks** | Высокая | Много | Низкая | ⚠️ Избыточно |
| **Image Features (HOG/LBP)** | Средняя | Средне | Средняя | ✅ Хорошо |

---

### 🎯 CV методы - рекомендации

#### Лучшие для форм бугров:

1. **Dynamic Time Warping (DTW)** ⭐⭐⭐
   - **САМЫЙ РЕКОМЕНДУЕМЫЙ**
   - Специально создан для временных рядов
   - Работает с разной длиной зон
   - Интуитивно понятно

2. **Hu Moments** ⭐⭐
   - Простой и эффективный
   - 7 компактных признаков
   - Инвариантность к масштабу
   - Легко добавить к существующим метрикам

3. **Template Matching** ⭐
   - Для классификации (не кластеризации)
   - Если есть известные паттерны
   - Очень интерпретируемо

#### Не рекомендуется (пока):

- **CNN / Siamese** - избыточны, нужно много данных
- **Image-based (HOG/LBP)** - overhead рендеринга

---

### 🔨 Практическая реализация

#### Шаг 1: Добавить DTW в существующую архитектуру

```python
# bquant/analysis/zones/strategies/shape/dtw_shape.py

from dtaidistance import dtw
import numpy as np
from dataclasses import dataclass

@StrategyRegistry.register_shape_strategy('dtw')
@dataclass
class DTWShapeStrategy:
    """Shape analysis using Dynamic Time Warping distance."""
    
    reference_templates: dict = None  # Эталонные формы
    
    def calculate(self, zone_data):
        hist = zone_data['macd_hist'].values
        
        # Вычислить DTW расстояния до эталонов
        distances = {}
        for name, template in self.reference_templates.items():
            dist = dtw.distance(hist, template)
            distances[f'dtw_to_{name}'] = dist
        
        # Найти ближайший эталон
        closest_template = min(distances, key=distances.get)
        closest_distance = distances[closest_template]
        
        # Вернуть как ShapeMetrics (расширить для DTW расстояний)
        return ShapeMetrics(
            hist_skewness=0.0,  # DTW не использует
            hist_kurtosis=0.0,   # DTW не использует
            hist_smoothness=None,
            strategy_name='dtw',
            strategy_params={
                'closest_template': closest_template,
                'closest_distance': closest_distance,
                **distances  # Все расстояния
            }
        )
```

#### Шаг 2: Использовать DTW для кластеризации

```python
# В ZoneSequenceAnalyzer или новом анализаторе

def cluster_zones_dtw(self, zones_list, n_clusters=4):
    """Cluster zones using DTW distance matrix."""
    from dtaidistance import dtw
    from sklearn.cluster import AgglomerativeClustering
    
    # 1. Извлечь гистограммы
    histograms = [z.metadata['hist_values'] for z in zones_list]
    
    # 2. Построить матрицу расстояний
    distance_matrix = dtw.distance_matrix_fast(histograms)
    
    # 3. Hierarchical clustering
    clusterer = AgglomerativeClustering(
        n_clusters=n_clusters,
        affinity='precomputed',
        linkage='average'
    )
    labels = clusterer.fit_predict(distance_matrix)
    
    return labels
```

---

### 🎯 Рекомендации для форм "бугров":

#### 1. **K-Means** (текущий) ✅
**Когда использовать:**
- Есть гипотеза о количестве архетипов (3-5)
- Нужна скорость
- Признаки нормализованы

**Для форм бугров:**
```python
features = [
    'hist_skewness',      # -2 до 2
    'hist_kurtosis',      # 1 до 10
    'hist_smoothness',    # 0 до 1
    'duration',           # 10 до 200 баров
    'max_price_change'    # %
]
# Нормализация обязательна!
# K = 3-5 оптимально
```

**Архетипы:**
- Кластер 1: Sharp Early Impulse (skew>0, kurt>5)
- Кластер 2: Smooth Trend (skew≈0, kurt<3)
- Кластер 3: Late Wave (skew<0)

---

#### 2. **Hierarchical Clustering** ✅ (рекомендую добавить)

**Преимущества для вашей задачи:**
- **Не нужно знать K заранее** - можно посмотреть дендрограмму
- **Исследовательский анализ** - понять естественную группировку
- **Стабильность** - детерминистичен (в отличие от K-Means с random init)

**Использование:**
```python
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.cluster import AgglomerativeClustering

# 1. Построить дендрограмму (анализ)
linkage_matrix = linkage(features, method='ward')
dendrogram(linkage_matrix)
# Визуально определить оптимальное K

# 2. Кластеризация с выбранным K
clusterer = AgglomerativeClustering(n_clusters=4, linkage='ward')
labels = clusterer.fit_predict(features)
```

**Для форм:** Очень хорошо показывает иерархию похожести:
- Уровень 1: Bull vs Bear
- Уровень 2: Early vs Late impulse
- Уровень 3: Sharp vs Smooth

---

#### 3. **GMM (Gaussian Mixture Models)** ✅

**Преимущества:**
- **Мягкая кластеризация** - каждая зона может принадлежать к нескольким кластерам с вероятностями
- **Эллипсоидные кластеры** - лучше для форм (не только сферы)
- **Model selection** - BIC/AIC для выбора количества компонент

**Использование:**
```python
from sklearn.mixture import GaussianMixture

# Подбор K через BIC
bic_scores = []
for k in range(2, 10):
    gmm = GaussianMixture(n_components=k, random_state=42)
    gmm.fit(features)
    bic_scores.append(gmm.bic(features))

optimal_k = np.argmin(bic_scores) + 2

# Кластеризация
gmm = GaussianMixture(n_components=optimal_k)
labels = gmm.fit_predict(features)
probabilities = gmm.predict_proba(features)  # Мягкие метки!
```

**Для форм:** Отлично - формы не всегда четко разделены, переходные случаи получат смешанные метки.

---

#### 4. **DBSCAN** ⚠️ (осторожно)

**Когда может помочь:**
- Есть **выбросы** (аномальные формы бугров)
- Кластеры **произвольной формы** (не эллипсы)
- Не знаем K

**Проблемы для форм:**
- Сложно подобрать `eps` (radius)
- Плохо работает если разная "плотность" архетипов
- Может все записать в шум

**Использование:**
```python
from sklearn.cluster import DBSCAN

# Сложно подобрать eps!
eps_values = np.linspace(0.5, 5.0, 20)
for eps in eps_values:
    clusterer = DBSCAN(eps=eps, min_samples=5)
    labels = clusterer.fit_predict(features)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    print(f"eps={eps:.2f}: {n_clusters} clusters")
```

**Вывод:** Для форм DBSCAN избыточен, сложен в настройке.

---

### 🔥 Multi-Strategy подход (рекомендуется)

#### Этап 1: Исследование (Hierarchical)
```python
# Понять естественную группировку
linkage_matrix = linkage(features, method='ward')
dendrogram(linkage_matrix)
# Результат: "Ага, видно 4 основных группы"
```

#### Этап 2: Production (K-Means или GMM)
```python
# K-Means для скорости и интерпретируемости
kmeans = KMeans(n_clusters=4, random_state=42)
labels = kmeans.fit_predict(features)

# ИЛИ GMM для мягкой кластеризации
gmm = GaussianMixture(n_components=4)
labels = gmm.fit_predict(features)
probabilities = gmm.predict_proba(features)
```

#### Этап 3: Детекция аномалий (опционально)
```python
# Isolation Forest для выбросов
from sklearn.ensemble import IsolationForest
iso = IsolationForest(contamination=0.05)
anomalies = iso.fit_predict(features)
# Результат: зоны с аномальной формой
```

---

## 3. Рекомендации по реализации

### 📐 Архитектура кластеризации

**Текущая реализация:**
```python
# ZoneSequenceAnalyzer.cluster_zones() - уже есть K-Means
```

**Как добавить другие методы:**

#### Вариант 1: Параметр method
```python
def cluster_zones(self, zones_data, n_clusters=3, method='kmeans'):
    if method == 'kmeans':
        clusterer = KMeans(n_clusters=n_clusters)
    elif method == 'gmm':
        clusterer = GaussianMixture(n_components=n_clusters)
    elif method == 'hierarchical':
        clusterer = AgglomerativeClustering(n_clusters=n_clusters)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    labels = clusterer.fit_predict(zones_data)
    return labels
```

#### Вариант 2: Strategy Pattern (лучше!)
```python
# bquant/analysis/zones/clustering_strategies.py

class ClusteringStrategy(Protocol):
    def fit_predict(self, data: np.ndarray) -> np.ndarray: ...

@dataclass
class KMeansClusteringStrategy:
    n_clusters: int = 3
    
    def fit_predict(self, data):
        clusterer = KMeans(n_clusters=self.n_clusters)
        return clusterer.fit_predict(data)

@dataclass
class GMMClusteringStrategy:
    n_components: int = 3
    
    def fit_predict(self, data):
        gmm = GaussianMixture(n_components=self.n_components)
        return gmm.fit_predict(data)

@dataclass
class HierarchicalClusteringStrategy:
    n_clusters: int = 3
    linkage: str = 'ward'
    
    def fit_predict(self, data):
        clusterer = AgglomerativeClustering(
            n_clusters=self.n_clusters,
            linkage=self.linkage
        )
        return clusterer.fit_predict(data)

# В ZoneSequenceAnalyzer:
def cluster_zones(self, zones_data, strategy: ClusteringStrategy = None):
    if strategy is None:
        strategy = KMeansClusteringStrategy(n_clusters=3)
    
    return strategy.fit_predict(zones_data)
```

**Сложность добавления:** 1 новый файл, 1 новый класс стратегии!

---

### 🎯 Итоговая рекомендация

#### Для форм "бугров" лучше всего:

#### Traditional ML методы:

1. **K-Means** (текущий) - для production
   - ✅ Быстро
   - ✅ Понятно
   - ✅ Работает

2. **Hierarchical** - добавить для анализа
   - ✅ Помогает найти оптимальное K
   - ✅ Дендрограмма наглядна
   - ✅ Детерминистичен

3. **GMM** - добавить как альтернатива
   - ✅ Мягкая кластеризация
   - ✅ Автоматический выбор K (BIC)
   - ✅ Лучше для переходных форм

4. **DBSCAN** - НЕ рекомендую
   - ❌ Сложен в настройке
   - ❌ Избыточен для задачи
   - ✅ Лучше использовать Isolation Forest для аномалий

#### Computer Vision методы:

1. **DTW (Dynamic Time Warping)** ⭐⭐⭐ - САМЫЙ РЕКОМЕНДУЕМЫЙ
   - ✅✅✅ Идеально для временных рядов
   - ✅ Работает с разной длиной зон
   - ✅ Интуитивно понятная метрика похожести
   - ✅ Использовать с Hierarchical clustering

2. **Hu Moments** ⭐⭐ - добавить как признаки
   - ✅ 7 компактных признаков формы
   - ✅ Инвариантность к масштабу
   - ✅ Дополнить существующие shape metrics

3. **Template Matching** ⭐ - для известных паттернов
   - ✅ Классификация (не кластеризация)
   - ✅ Очень интерпретируемо

4. **CNN/Deep Learning** - НЕ рекомендую сейчас
   - ❌ Нужно >10,000 размеченных зон
   - ❌ Избыточно для задачи
   - ⏰ Только если простые методы не дадут результат

---

### ✅ Архитектурные выводы

**Добавить новые методы кластеризации:** ОЧЕНЬ ЛЕГКО
- Strategy Pattern для clustering (аналогично shape strategies)
- 1 новый файл на метод
- 0 изменений в существующем коде

**Когда добавлять:**

#### Traditional ML:
- **Hierarchical** - сейчас (для исследования оптимального K)
- **GMM** - скоро (когда понадобится мягкая кластеризация)
- **DBSCAN** - только если появятся выбросы

#### Computer Vision:
- **DTW** - ПРИОРИТЕТ #1 (идеально для временных рядов)
- **Hu Moments** - приоритет #2 (добавить как дополнительные признаки к shape metrics)
- **Template Matching** - для классификации известных паттернов
- **CNN/Siamese** - только если >10k размеченных зон

---

## Приложение: Почему FourierShapeStrategy отложена

### Причины отложения Fourier анализа

#### 1. **Достаточность базовых метрик**

`StatisticalShapeStrategy` уже покрывает основные аспекты формы:
- **Skewness** → где пик (начало/конец)
- **Kurtosis** → насколько резкий пик
- **Smoothness** → насколько гладкая кривая

Этого достаточно для:
- Классификации зон по архетипам
- Улучшенной кластеризации (K-Means)
- Фильтрации качественных сигналов

---

#### 2. **Сложность интерпретации для трейдеров**

**Фурье-анализ** дает:
- Частотный спектр (доминантные частоты)
- Амплитуды гармоник
- Фазовые сдвиги

**Проблема:** Что означает "доминантная частота 0.3" для принятия торговых решений?

**Статистика** дает:
- Skewness = 0.7 → "ранний импульс" ✅ понятно
- Kurtosis = 6.5 → "резкий пик" ✅ понятно

---

#### 3. **Принцип YAGNI (You Aren't Gonna Need It)**

Стратегия:
1. ✅ Реализовать базовый необходимый функционал
2. ⏸️ Отложить продвинутый, пока не появится реальная потребность
3. ✅ Архитектура готова - легко добавить позже

Сейчас нет доказательств, что Фурье-метрики дадут значимое преимущество над статистическими.

---

#### 4. **Производительность**

**FFT (Fast Fourier Transform):**
- Сложность: O(n log n)
- Для коротких зон (20-50 баров) может быть избыточен
- Требует дополнительных зависимостей (numpy.fft или scipy.fft)

**Статистика (skew, kurtosis):**
- Сложность: O(n)
- Быстрее на малых данных
- Уже есть в scipy.stats

---

#### 5. **Специфика применения**

**Фурье подходит для:**
- Периодических сигналов
- Выделения циклов
- Фильтрации шума

**Зоны MACD:**
- Обычно **не периодичны** (одиночные импульсы)
- Короткие (20-100 баров)
- Форма важнее частотного содержания

**Вывод:** Для анализа формы "бугра" гистограммы статистические моменты подходят лучше.

---

#### 6. **Возможные метрики Fourier (если реализовывать)**

Что можно было бы получить:
- `dominant_frequency` - главная частота
- `frequency_concentration` - насколько энергия сконцентрирована
- `spectral_entropy` - мера хаотичности спектра

**НО:** Как это поможет классифицировать зоны? Неочевидно.

---

#### 7. **Альтернативы Fourier**

Если нужен более продвинутый анализ формы:

**WaveletShapeStrategy** (тоже отложена):
- Лучше для непериодических сигналов
- Локализация во времени и частоте одновременно
- Может выделить "всплески" на разных масштабах

Но тоже избыточна на данном этапе.

---

### Когда имеет смысл реализовать Fourier?

#### Сценарии:

1. **Если статистические метрики недостаточны:**
   - Кластеризация дает плохое разделение
   - Нужны дополнительные признаки для ML

2. **Для специфичных задач:**
   - Поиск циклических паттернов внутри зон
   - Выделение "музыкальных" (гармоничных) vs "хаотичных" зон

3. **Для исследовательских целей:**
   - Проверка гипотезы о периодичности
   - Сравнение частотного содержания bull vs bear зон

---

### Текущая стратегия

#### Фаза 3.2: ✅ Базовый анализ формы
- StatisticalShapeStrategy реализована
- Работает, протестирована, готова к использованию

#### Следующие приоритеты:
1. **Фаза 3.5: Volatility** (Bollinger/ATR) - более важно
2. **Фаза 3.4: Divergence** - более важно
3. **Фаза 3.6: Volume** - более важно

#### Fourier/Wavelet:
- Опциональные расширения
- Реализовать только если появится конкретная потребность
- Инфраструктура готова - добавить легко

---

### Итог

**Почему отложено:**
1. ✅ Базовых метрик достаточно
2. ✅ Фурье сложнее интерпретировать
3. ✅ Неочевидная польза для зон MACD
4. ✅ Другие фазы важнее
5. ✅ YAGNI - не реализовывать пока не нужно

**Архитектурное решение правильное:**
- Strategy Pattern позволяет легко добавить FourierShapeStrategy позже
- Можно провести эксперимент и сравнить с StatisticalShapeStrategy
- Если Fourier даст преимущество - добавим

**Рекомендация:**
Сначала использовать StatisticalShapeStrategy на реальных данных, оценить эффективность кластеризации. Если понадобятся дополнительные метрики формы - добавить Fourier тогда.

---

**Автор:** AI Assistant  
**Дата:** 2025-10-12  
**Статус:** Аналитический документ

