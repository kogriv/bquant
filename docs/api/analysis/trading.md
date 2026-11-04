# Сделки из зон — `bquant.analysis.trading`

Зоны, бары и (по желанию) сигналы по зонам вместе с правилами входа, выхода и стопа и моделью
издержек превращаются в **кадр сделок**, который читает [`evaluation`](evaluation.md). На каждую
зону получается одна сделка. Зоны, не давшие сделки, возвращаются отдельно, каждая с причиной.
Правила — объекты с параметрами, а не строки.

```python
from bquant.analysis.evaluation import CostModel
from bquant.analysis.trading import FixedAtrStop, TakeProfit, ZoneBarClose, zone_trades
from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze()
    .build()
)
got = zone_trades(
    result.data, result, point=0.01,
    entry=ZoneBarClose(k=1),                         # decide at the close of the zone's second bar
    exit=TakeProfit(level_atr=2.0),                  # target 2 ATR, otherwise leave at the zone change
    stop=FixedAtrStop(1.0),
    costs=CostModel(spread='fixed', fixed_spread_points=30.0),
)
trades = got.trades
print(len(trades), len(got.skipped), got.skipped['reason'].value_counts().to_dict())
print(trades['exit_reason'].value_counts().to_dict())
print(round(trades['net'].mean(), 3), round(trades['mfe'].mean(), 3), round(trades['mae'].mean(), 3))
print(trades[['entry_time', 'side', 'hold', 'exit_reason', 'net']].head(3).round(3).to_string(index=False))
# 66 11 {'zone_shorter_than_k': 10, 'exit_beyond_data': 1}
# {'stop': 44, 'take': 16, 'fallback': 6}
# -0.24 1.012 1.072
#                entry_time  side  hold exit_reason    net
# 2025-06-13 08:00:00+07:00     1     5        stop -1.023
# 2025-06-13 18:00:00+07:00    -1     1        stop -1.023
# 2025-06-13 22:00:00+07:00    -1     3        stop -1.023
```

**Как это читать.**
- 11 зон пропущены, и у каждой своя причина. 10 короче двух баров: у них нет бара возраста 1, на
  котором принимается решение. У последней зоны выход наступил бы за концом данных.
- `net` — исход после издержек в ATR бара решения. Стоп в 1 ATR при фиксированном спреде 30
  пунктов даёт ровно `-1.023`: сам стоп `−1` плюс спред.
- `mfe` и `mae` — наибольшее движение в пользу и против позиции в окне, которое сделка
  действительно прожила.

## Что возвращается

`zone_trades` возвращает `ZoneTrades` из двух кадров.
- `trades` — столбцы в порядке `TRADE_COLUMNS`:
  - `zone_id`, `k`, `side`;
  - `decision_time`, `entry_time`, `exit_time`;
  - `hold` (`x − j`), `mode`, `exit_reason`;
  - цены входа и выхода, `atr_points`;
  - `gross_points`, `cost_points`, `nights`, `net_points`;
  - `gross` и `net` в ATR, `mfe`, `mae`;
  - `dur` — длительность зоны с баром смены;
  - `stop_and_take_same_bar`.

  Этот кадр принимает `validate_trades`.
- `skipped` — `zone_id` и `reason`.

`describe(rule)` переводит правило в словарь — для записи того, что было запущено.

## Обозначения

`s`, `e` — первый и последний бар зоны, `d` — её сторона (+1 / −1). `j` — **бар решения**,
бар, на закрытии которого принимается решение; исход и все уровни измеряются в `atr[j]`. По
умолчанию это ATR Уайлдера с периодом 14, его можно передать своим `atr` (в цене). **Окно
сделки** — бары `j + 1 … x`, где `x` — бар выхода; сам бар решения в окно не входит. Все
времена в кадре — время открытия бара, по часам сервера.

## Вход

| правило | бар решения `j` | вход | «сделки нет» |
|---|---|---|---|
| `ZoneBarClose(k=0, side='zone')` | `s + k` | закрытие `j` | `zone_shorter_than_k`, `atr_nan_at_decision_bar` |
| `NextOpen(side='zone')` | `s` | открытие `j + 1` | `no_next_bar`, `atr_nan_at_decision_bar` |

`side`: `'zone'` — сторона зоны, `'against_zone'` — противоположная, `'signal'` — знак
столбца `side_column` (по умолчанию `signal_side`) в строке сигналов `(зона, k)`. При нуле
сделки нет, причина `no_side`. Для правил, не связанных с зонами, передайте по одной «зоне»
на каждый бар решения (`start_idx = end_idx = j`).

## Выход

| правило | бар выхода `x` | цена | причина |
|---|---|---|---|
| `ZoneChange()` | `e + 1` | закрытие | `zone_change` |
| `Horizon(h)` | `j + h` | закрытие | `horizon` |
| `Horizon(h, cap=ZoneChange())` | `j + h`, но не позже `e + 1` | закрытие | `horizon`; при пределе (и ровно на границе) — `zone_change` |
| `SignalThreshold(signal, thr, k_min=1, require={}, fallback=ZoneChange())` | первый возраст `k' ≥ k_min`, `k' > k`, где `signal ≥ thr` и выполнены все `require` | закрытие | `signal` |
| `TrailingAfterSignal(signal, thr, s_atr, …)` | с бара сигнала (включительно) — первый бар, где закрытие отдало `s_atr` от лучшего | закрытие | `trail` |
| `TakeProfit(level_atr=… \| share_of_forecast=…, forecast=…)` | первый бар окна, чей high (покупка) или low (продажа) достал цель | цель | `take` |

Если сигнала, отката или цели нет до бара `fallback` (`ZoneChange` или `Horizon`), сделка
выходит по нему с причиной `fallback`. У `Horizon` с пределом за концом данных должен лежать именно бар выхода, а не любой из двух. Если выход приходится за концом данных, сделки нет:
причина `exit_beyond_data`, а не укороченная сделка. В `mode` всегда стоит **имя правила
выхода**, одно на вызов: это метка для `random_entry_baseline`, и задаётся она решением, а не
исходом. Чем сделка закрылась на самом деле, показывает `exit_reason`.

## Стоп и издержки

`FixedAtrStop(v)` или `ColumnStop(column)` — расстояние в ATR, во втором случае из строки
сигналов на баре решения. Выражения вроде `K·mae_prev1` вызывающий считает в столбец сам:
строки пакет не исполняет. Стоп проверяется на каждом баре окна, включая бар выхода, и
**выигрывает свой бар** у тейка, сигнала и правила выхода, потому что порядок внутри бара
неизвестен. Валовой исход при стопе — ровно минус его расстояние. Флаг
`stop_and_take_same_bar` отмечает сделки, где на том же баре была достигнута и цель.

`costs` — [`CostModel`](evaluation.md#издержки-сделки) со спредом бара **входа**; `None` —
без издержек. Ночи считаются в любом случае, до конца бара выхода: это факт сделки, а не
модели издержек.

## Отказы

Пакет отказывает, а не подставляет молча:
- нет строки или столбца сигналов, нужного стопу, тейку или стороне;
- зона вне баров, `start > end`, повтор `zone_id`;
- у зоны тип без стороны (не `bull` / `bear`, когда зоны переданы объектами);
- модель со спредом бара, а в барах нет столбца `spread`;
- `fallback` со своим собственным `fallback`;
- строка вместо правила.
