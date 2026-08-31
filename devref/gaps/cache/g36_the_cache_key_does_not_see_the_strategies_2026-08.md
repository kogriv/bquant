# G36 — Кэш-ключ не видит четыре стратегии из пяти и молча отдаёт чужой результат

**Заведён:** 2026-08-31 при последовательном проходе по докам (волна 2,
`zone_analysis_result.md`).
**Статус:** 🔴 открыт — правка кода, решение владельца.
**Серьёзность:** выше, чем у остальных гэпов прохода: результат **неверен и молчит**.

---

## 1. Как нашли

Не поиском дефекта. Пример из `zone_analysis_result.md` включал все пять стратегий
метрик; правило прохода — исполнить и посмотреть на вывод. В выводе оказалось
`volatility_metrics: None` у всех 83 зон, а в логе — строка
`Zone analysis result loaded from cache`.

## 2. Замер

```
tv_xauusd_1h, MACD по линии, 32 зоны, стратегия volatility='combined'

кэш выключен, volatility включена:   29/32 зон с volatility_metrics
кэш выключен, volatility выключена:   0/32
кэш ВКЛЮЧЁН,  volatility включена:    0/32     ← отдан результат прошлого прогона
```

Кэш включён **по умолчанию**. То есть строка `.with_strategies(volatility='combined')`
при обычном использовании не даёт ничего, если раньше в этом же окружении считался тот
же индикатор с той же детекцией без неё.

Прямая проверка ключей:

```python
p1 = ZoneAnalysisPipeline(cfg, zone_analyzer=UniversalZoneAnalyzer(volatility_strategy=None))
p2 = ZoneAnalysisPipeline(cfg, zone_analyzer=UniversalZoneAnalyzer(volatility_strategy='combined'))
p1._generate_cache_key(data) == p2._generate_cache_key(data)   # True
```

Ключ совпадает и для конфигурации с тремя другими стратегиями
(`divergence='classic', volume='standard', shape='statistical'`).

## 3. Причина

`bquant/analysis/zones/pipeline.py:470` — ключ собирается из трёх частей:

```python
data_hash        = ZoneAnalysisCache.compute_data_hash(df)
config_signature = self.config.to_cache_key()
swing_signature  = ZoneAnalysisCache.swing_signature({...})
```

`ZoneAnalysisConfig` (там же, строка 106) полей для стратегий метрик **не имеет** —
в `to_cache_key()` уходят индикатор, детекция, кластеризация, регрессия, валидация,
`swing_scope` и `min_duration`. Стратегии приходят другим путём: билдер собирает
`UniversalZoneAnalyzer(shape_strategy=..., divergence_strategy=..., volatility_strategy=...,
volume_strategy=...)` и передаёт его в пайплайн как `zone_analyzer=`, мимо конфигурации.

Свинги — единственные, кого ключ видит: для них есть отдельная `swing_signature`.
То есть механизм «подпись стратегии в ключе» в файле **уже существует** и применён к
одному семейству из пяти. Это тот же силуэт, что G32: правильный образец рядом,
но не распространён.

## 4. Радиус

| Что | Влияние |
|---|---|
| `shape`, `divergence`, `volatility`, `volume` | смена стратегии не меняет ключ → отдаётся чужой результат |
| `swing`, `swing_scope` | в ключе есть, работают корректно |
| Дисковый кэш `~/.cache/bquant`, TTL 3600 с | дефект переживает перезапуск процесса в пределах часа |
| Флагманский пример в `AGENTS.md` | использует только `swing=` — не затронут |
| `docs/user_guide/zone_analysis_result.md`, `zone_analysis.md` | примеры со стратегиями метрик — задокументирован обход |

Пользователь, сравнивающий две стратегии формы «до/после», получит **одинаковые числа**
и заключит, что выбор стратегии ни на что не влияет.

## 5. Починка

Одна по существу: подпись анализатора в ключе — по образцу `swing_signature`.

```python
analyzer_signature = {
    'shape': self.zone_analyzer.shape_strategy_name,
    'divergence': ...,
    'volatility': ...,
    'volume': ...,
}
```

плюс поднять `CACHE_SCHEMA_VERSION` — старые записи ключей не различают то, что новые
различают, и должны быть признаны негодными. Механизм версии схемы в проекте для этого
и заведён (последний раз двигался в G15).

Отдельным вопросом — **обход на сегодня**: `.with_cache(enable=False)` при сравнении
стратегий. Он записан в доке.

## 6. Почему решение за владельцем

Правка меняет ключи всем: первый прогон после релиза пересчитает то, что раньше
приходило из кэша. Это не смена контракта, но это заметная разовая цена у внешнего
потребителя, а по правилам проекта такие вещи идут через него.
