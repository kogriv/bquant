# Фикстура «сделки из зон»

Бары — те же 480 синтетических H1, что `../../evaluation/baseline/bars.csv`. Генератор и
эталонная реализация формул — на стороне запросившей лаборатории; поле `bars` в
`expected.json` называет путь в её репозитории. Данных и чисел чьих-либо исследований здесь нет.

- `zones.csv` — 10 зон кадром (`zone_id, start_idx, end_idx, side`): первая лежит в разогреве
  ATR, у последней выход за концом данных;
- `signals.csv` — строки `(zone_id, k)`: `p_pivot_formed`, `state_abstain`,
  `range_forecast_atr`, `stop_atr`, `signal_side`;
- `expected.json → variants` — 20 вариантов правил (вход, выход, стоп, издержки), `costs` —
  модели издержек;
- `trades.csv` — 160 ожидаемых сделок построчно, `skipped.csv` — 40 пропусков с причиной.

`tests/unit/test_trades_from_zones_reproduce_the_reference.py` воспроизводит каждый вариант:
времена, `hold`, `nights`, `mode`, `exit_reason` — точно, числа — до `1e-9`.
