==================== COMMIT DIVIDER ====================

## 2025-11-12: Добавлена функция plot_zigzag_verification для визуализации ZigZag индикатора

### Изменения в коде

**bquant/visualization/zones.py:**
- Добавлена функция `plot_zigzag_verification()` для построения графика ZigZag индикатора с swing-точками
- Функция создаёт однопанельный график: candlestick-график цены с маркерами swing points (peaks/troughs)
- Поддерживает использование `swing_context` для точного определения типов точек
- Добавлен параметр `show_rangeslider` (default=False) для опционального отображения ползунка навигации
- Экспортирована через `__all__`

**bquant/visualization/__init__.py:**
- Добавлен импорт `plot_zigzag_verification` из модуля `zones`
- Добавлена в `__all__` для публичного API

**research/notebooks/04_zones_sample.py:**
- Упрощён код в Step 2: заменён большой блок кода (~160 строк) на вызов функции `plot_zigzag_verification()` (~20 строк)
- Добавлен импорт `plot_zigzag_verification` из `bquant.visualization`

### Документация

**docs/api/visualization/zones.md:**
- Добавлен раздел "Визуализация ZigZag индикатора: `plot_zigzag_verification`" в секцию "Convenience-функции"
- Описаны параметры функции, возвращаемые значения и примеры использования
- Обновлён changelog: добавлена версия v1.1 с описанием новой функции

### Назначение

Функция позволяет визуально проверять параметры swing-стратегии (legs, deviation) и отлаживать настройки ZigZag индикатора. Полезно для:
- Верификации параметров стратегии после автоматической настройки (auto_swing_thresholds)
- Сравнения визуального результата ZigZag с результатами пайплайна
- Отладки и настройки параметров swing-детекции

### Использование

```python
from bquant.visualization import plot_zigzag_verification

# Простой вариант
fig = plot_zigzag_verification(price_data=df, legs=10, deviation=0.05)

# С swing_context для точных типов точек
fig = plot_zigzag_verification(
    price_data=result.data,
    legs=strategy_params['legs'],
    deviation=strategy_params['deviation'],
    swing_context=swing_context
)
```

