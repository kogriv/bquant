# Tutorial: Preloaded зоны (Пример 3 + Сценарий 9)

## 🎯 Цели
- Воспроизвести Пример 3: PRELOADED индикатор + зоны (см. документацию)
- Повторить модульный Сценарий 9: работа с PRELOADED зонами (внешние данные)
- Разобрать формат входного CSV и лучшие практики интеграции

## 🔧 Предварительные требования
- Готовый CSV/Excel с разметкой зон эксперта или внешней системы
- OHLCV-данные, синхронизированные по времени (используем sample `tv_xauusd_1h`)

## 📥 Формат входных данных
`PreloadedZonesDetection` ожидает минимум четыре колонки.

| Колонка | Тип | Описание |
|---------|-----|----------|
| `zone_id` | int | Уникальный идентификатор |
| `type` | str | Тип зоны (`bull`, `bear`, `support`, `resistance`, ...) |
| `start_time` | datetime | Начало зоны (ISO 8601) |
| `end_time` | datetime | Конец зоны (ISO 8601) |

Дополнительно можно добавить `indicator`, `comment` и любые метаданные — они попадут в `ZoneInfo.data` и `indicator_context`.

### Пример CSV
```csv
zone_id,type,start_time,end_time,indicator
0,bull,2025-01-01T00:00:00,2025-01-01T06:00:00,external_model
1,bear,2025-01-02T12:00:00,2025-01-02T18:00:00,manual_markup
```

## 🛠️ Шаг 1. Быстрый pipeline с preloaded зонами
Воспользуемся fluent builder: индикатор внутри pipeline не нужен, потому что зоны уже размечены.

```python
from bquant.data.samples import get_sample_data
from bquant.analysis.zones import analyze_zones

df = get_sample_data('tv_xauusd_1h')

preloaded_result = (
    analyze_zones(df)
    .detect_zones('preloaded', zones_data='expert_zones.csv', time_tolerance='5min', min_duration=2)
    .analyze(clustering=False)
    .build()
)

print(f"Loaded zones: {len(preloaded_result.zones)}")
print(preloaded_result.zones[0].indicator_context['source'])  # 'external'
```

## ♻️ Шаг 2. Модульный сценарий (zomodul #9)
Для повторного использования сохраним зоны в pickle и сравним с автоматической детекцией, как показано в `zomodul.md`.

```python
import pickle
from bquant.analysis.zones.detection import ZoneDetectionRegistry, ZoneDetectionConfig
from bquant.analysis.zones.detection.preloaded import load_preloaded_zones
from bquant.indicators import IndicatorFactory

# 1. Загрузка preloaded зон
zones = load_preloaded_zones('expert_zones.csv', df, time_tolerance='5min', min_duration=2)

with open('expert_zones.pkl', 'wb') as f:
    pickle.dump(zones, f)

# 2. Рассчитываем MACD для автоматической стратегии
indicator = IndicatorFactory.create('custom', 'macd', fast=12, slow=26, signal=9)
macd_result = indicator.calculate(df)
df_with_macd = df.join(macd_result.data)

# 3. Анализ эксперта vs автоматической детекции
from bquant.analysis.zones import UniversalZoneAnalyzer
analyzer = UniversalZoneAnalyzer()
expert_analysis = analyzer.analyze_zones(zones, df)

auto_detector = ZoneDetectionRegistry.get('zero_crossing')
auto_config = ZoneDetectionConfig(strategy_name='zero_crossing', rules={'indicator_col': 'macd_hist'}, min_duration=2)
auto_zones = auto_detector.detect_zones(df_with_macd, auto_config)
auto_analysis = analyzer.analyze_zones(auto_zones, df_with_macd)

comparison = {
    'expert': {'zones': len(zones), 'win_rate': expert_analysis.statistics.get('win_rate')},
    'automatic': {'zones': len(auto_zones), 'win_rate': auto_analysis.statistics.get('win_rate')}
}
print(comparison)
```

## 📊 Визуализация и контроль качества
```python
preloaded_result.visualize('overview', title='Expert Zones vs Price').show()
preloaded_result.visualize('statistics').show()
```

- Используйте `visualize('detail', zone_id=...)`, чтобы убедиться, что временные окна совпадают.
- Если зона не отображается, проверьте `time_tolerance` и наличие строк в `ZoneInfo.data`.

## ✅ Лучшие практики
1. **Валидируйте вход** — проверяйте `missing` колонки перед запуском (`ValueError` при отсутствии).
2. **Сохраняйте оригинал** — держите исходный CSV рядом с pickle, чтобы отслеживать ревизии разметки.
3. **Временной допуск** — увеличивайте `time_tolerance` для разреженных данных или нестандартных сессий.
4. **Метаданные** — добавляйте столбцы с параметрами модели, чтобы в `indicator_context` сохранить источник.
5. **Сравнение стратегий** — комбинируйте анализ эксперта с автоматическими зонами для контроля качества, как в коде выше.

## 🚀 Что дальше
- Автоматизируйте загрузку из S3/БД, передавая `pd.DataFrame` вместо пути.
- Используйте `ZoneFeaturesAnalyzer` для метрик качества preloaded зон.
- Создайте CI-проверку, сравнивающую win-rate экспертов и автоматических стратегий.
