# Evaluation — оценка списка сделок

`bquant.analysis.evaluation` отвечает на вопрос, на который одно число бэктеста ответить не
может: **состоятелен ли результат, или он сделан удачей и отбором.** Всё в модуле читает один
объект — кадр сделок — и ничего не знает про зоны, ряды и советники: число проверок, на
которое делается поправка, и функция исхода для случайного базиса приходят от вызывающего.

| часть | вопрос | имена |
|---|---|---|
| контракт | что такое сделка | `validate_trades`, `month_key`, `months_between`, `month_label` |
| блочный бутстреп | какова ширина результата при перекрывающихся сделках | `BlockBootstrap` |
| случайный базис | сколько дал бы тот же вход на случайном баре того же года | `random_entry_baseline`, `attach_random_baseline` |
| сводка и критерий | выживает ли преимущество после поправки на всё опробованное | `trial_stats`, `benjamini_hochberg`, `Rule`, `MinTrades`, `NetPositive`, `YearsStable`, `BeatsRandom`, `MinEffect`, `BeatsBase`, `Placebo`, `Holds`, `HoldsFolds`, `apply_rules`, `Criterion`, `default_criterion` |
| вариант против базы | лучше ли правило той же сделки без него | `paired_stats`, `contrast_stats`, `permutation_placebo`, `SignFlip`, `PermuteFlags`, `PermuteColumn` |
| процедура по окнам | лучше ли подбор, чем его отсутствие | `evaluate_procedure`, `ProcedureResult` |
| квартальная мерка | размазан ли результат по времени или сделан одним отрезком | `quarterly_summary`, `QuartersPositive`, `QuarterMedian`, `WorstQuarter`, `QuarterMeanOverStd`, `default_quarter_rules` |

Проект и замороженные определения: `devref/architecture/evaluation_module_2026-11.md`.

## Кадр сделок

Одна строка — одна сделка. Обязательные столбцы: `entry_time`, `exit_time` (datetime64,
выход не раньше входа), `side` (+1 покупка, −1 продажа), `net` — исход **после издержек в
единицах вызывающего** (ATR бара входа, процент цены, деньги — пакет ничего не
пересчитывает). Необязательные: `gross` (до издержек; `cost = gross − net`), `rand`
(ожидание случайного входа, см. базис; `NaN` — «у этой сделки базиса нет»), `hold`
(удержание в барах; нужно, чтобы прикрепить базис).

`validate_trades(trades)` возвращает кадр как есть или отказывает `ValueError` с именем
столбца и тем, что требуется; молчаливого приведения типов нет. Год и целый ключ месяца
(`year·12 + month − 1`, `month_key`) берутся из `entry_time`; квартал — из `exit_time` и
только квартальной меркой.

## Сводка, бутстреп и критерий

```python
import numpy as np
import pandas as pd

from bquant.analysis.evaluation import (
    BlockBootstrap, Criterion, MinTrades, NetPositive, YearsStable, BeatsRandom,
    months_between, trial_stats,
)

rng = np.random.default_rng(0)
n = 300
entry = pd.Timestamp('2021-01-04 09:00') + pd.to_timedelta(np.sort(rng.integers(0, 3 * 365 * 24 - 100, n)), 'h')
hold = rng.integers(2, 30, n)
trades = pd.DataFrame({
    'entry_time': entry,
    'exit_time': entry + pd.to_timedelta(hold, 'h'),
    'side': rng.choice([-1, 1], n),
    'net': rng.normal(0.08, 1.0, n),       # outcome after costs, in ATR of the entry bar
    'rand': rng.normal(0.0, 0.3, n),       # expectation of a random entry (see the baseline)
    'hold': hold,
})

boot = BlockBootstrap(months_between('2021-01-01', '2023-12-31'), B=2000, seed=1)
row = trial_stats(trades, boot)
print(row['n'], round(row['net_mean'], 3), round(row['net_lo'], 3), round(row['net_hi'], 3))
print(round(row['excess_mean'], 3), round(row['excess_se'], 3), round(row['p'], 3))
print(row['years_n'], row['years_net_pos'])

table = pd.DataFrame([{k: v for k, v in row.items() if k != 'years'}])
criterion = Criterion([MinTrades(100), NetPositive(), YearsStable(2 / 3), BeatsRandom(0.05)])
verdict = criterion.evaluate(table, m_total=40)     # forty variants were tried, this is one of them
print(round(verdict.loc[0, 'q'], 3), verdict.loc[0, 'ok_beats_random'], verdict.loc[0, 'pass'])
# 300 0.058 -0.065 0.177
# 0.089 0.067 0.092
# 3 3
# 1.0 False False
```

**Блок — календарный месяц входа.** Сделки перекрываются во времени, и обычный бутстреп по
сделкам даёт слишком узкий интервал. `BlockBootstrap(months, B, seed)` на каждом повторе
выбирает `M` месяцев с возвращением из `M` месяцев отрезка и берёт все сделки выбранных
месяцев; зависимость внутри месяца сохраняется. Список месяцев подаёт вызывающий —
`months_between(start, end)` — и это **месяцы отрезка, включая пустые**: месяц без сделок
тоже блок, и если его выкинуть, каждый интервал сузится. Повтор, в котором не оказалось ни
одной сделки, отбрасывается, а не перетягивается. Один и тот же `seed`, список месяцев и
`B` дают те же повторы.

**Сводка `trial_stats`** — одна строка на кандидата: `n`, `net_mean` с интервалом
`net_lo/net_hi`, преимущество над случайным входом `excess_mean` с интервалом,
стандартной ошибкой `excess_se` и односторонним `p = norm.sf(excess_mean / excess_se)`
(нормальное приближение с бутстреповской ошибкой: у доли повторов, `p_boot`, разрешение
`1/(B+1)` — слишком грубо, когда поправка идёт на тысячи вариантов), `hit`, годы (`years`
по годам; `years_n` — годы с не меньше чем `min_year_trades` сделками, из них
`years_net_pos` с плюсом). Без столбца `rand` преимущество **не считается** — все его
ключи `NaN`, а не ноль. Пустой кадр — `{"n": 0}`.

**Поправка `benjamini_hochberg(p, m_total)`.** `m_total` — всё, что было опробовано: на
этом отрезке, в прошлых поисках, включая варианты, не дошедшие до таблицы из-за малого
числа сделок. Недостающие до `m` проверки считаются `p = 1`, так что поправка не слабеет от
того, что кандидатов отбросили по дороге; `m` не бывает меньше числа `p` в таблице.
В примере выше один кандидат из сорока опробованных: `p = 0.092` после поправки даёт
`q = 1.0`, и правило `BeatsRandom` не проходит.

**Правила** — объекты с порогом в полях: порог меняется новым объектом, а не правкой кода,
и `describe()` его записывает. `MinTrades(n)`: `n ≥ n_min`; `NetPositive(use_ci)`:
`net_mean > 0` (и `net_lo > 0`); `YearsStable(share, min_years)`: не меньше `share` лет с
плюсом среди `years_n`; `BeatsRandom(alpha, margin)`: `excess_lo > margin` и `q < alpha`;
`MinEffect(threshold)`: `excess_mean ≥ threshold`. Неравенства ровно такие, как записаны:
значение на строгом пороге его не прошло. `Criterion(rules).evaluate(table, m_total)`
добавляет к таблице `q`, `m_total`, `ok_<rule>` на каждое правило и `pass`; строка с числом
сделок ниже `MinTrades` получает `p = NaN` **до** поправки (её `p` стоит на бутстрепе по
нескольким месяцам и не ранжируется), но в `m_total` входит. `default_criterion()` — четыре
правила выше с порогами `100`, `2/3`, `0.05`.

### Гейты исследования

Исследование сравнивает вариант не со случайным входом, а со своей **базой**: та же сделка
без правила варианта. Строка его таблицы несёт парную разность `mean_diff`, её `p` и `q`,
плацебо и итог на проверке, присоединённый к строке подбора (`val_mean_diff`, `val_p`).
Четыре правила читают эти столбцы:
- `BeatsBase(alpha)` — `q < alpha`;
- `Placebo(alpha)` — `placebo_p < alpha`, а без `placebo_p` (одна перестановка) — запасная форма
  `placebo_mean_diff < mean_diff / 2`;
- `Holds(threshold, alpha)` — `val_mean_diff ≥ threshold` и `val_p < alpha`;
- `HoldsFolds(k)` — ровно `k` фолдов, все выше нуля.

Два прежних правила читают в такой строке другие столбцы: `MinEffect(t, column='mean_diff')`
и `YearsStable(positive='years_pos')`. Без этих параметров они читают то же, что и раньше.

```python
import pandas as pd

from bquant.analysis.evaluation import (
    BeatsBase, Criterion, Holds, HoldsFolds, MinEffect, Placebo, YearsStable,
)

# one row per variant of a study: the paired difference against its base on the selection
# segment, its corrected q, the placebo, the years, and the validation result joined to it
table = pd.DataFrame({
    'variant':           ['a', 'b', 'c'],
    'mean_diff':         [0.25, 0.30, 0.08],
    'q':                 [0.01, 0.04, 0.02],
    'placebo_p':         [0.00, float('nan'), 0.30],
    'placebo_mean_diff': [0.02, 0.16, 0.05],
    'years_n':           [4, 3, 4],
    'years_pos':         [3, 2, 4],
    'val_mean_diff':     [0.18, 0.21, 0.12],
    'val_p':             [0.01, 0.03, 0.20],
})
gates = Criterion([
    BeatsBase(0.05), Placebo(0.05), MinEffect(0.1, column='mean_diff'),
    YearsStable(2 / 3, positive='years_pos'), Holds(threshold=0.1, alpha=0.05),
])
verdict = gates.evaluate(table, m_total=None)        # q is already corrected by the caller
print(verdict.filter(regex='variant|ok_|pass').to_string(index=False))
print(HoldsFolds(4).check({'fold_signs': [1, 1, -1, 1]}))
# variant  ok_beats_base  ok_placebo  ok_min_effect  ok_years_stable  ok_holds  pass
#       a           True        True           True             True      True  True
#       b           True       False           True             True      True False
#       c           True       False          False             True     False False
# False
```

`b` не прошёл плацебо по запасной форме: `0.16` не меньше половины `0.30`. `c` не прошёл
плацебо (`0.30`), минимальный эффект и проверку. `evaluate(table, m_total=None)` берёт `q` из
таблицы — для исследования, где поправку на всё опробованное (варианты плюс прежние проходы по
ряду) уже сделал вызывающий. Если столбца `q` нет — отказ. Если передан `m_total`, `q`
пересчитывается всегда, даже когда столбец есть: устаревший `q` молча не проходит. Ничьи и
`NaN` правила не проходят.

## Вариант против базы

> **Без заказчика с ноября 2026** — поддерживается, не расширяется (как и [`trading`](trading.md)).

Исследование спрашивает не «зарабатывает ли правило», а «лучше ли оно **той же сделки без
него**», единица за единицей (зона, бар):
- `paired_stats(variant, base, *, key, boot_months)` сопоставляет кадры по `key` (inner join;
  непарные отбрасываются и считаются в `n_variant`, `n_base`, `n`) и берёт `d = variant − base`;
  `boot_months` — **все** месяцы отрезка, включая пустые;
- `se` — по блочному бутстрепу по месяцам;
- `p` — одностороннее для `mean_diff > 0`: при `p_kind='boot_share'` это доля повторов со
  средним `≤ 0`, при `'normal'` — `1 − Φ(mean_diff / se)`. Без разброса (`se < 1e-12`) `p` —
  `NaN`;
- `years`, `years_n` и `years_pos` (годы, где не меньше `min_year_units` единиц) читает
  `YearsStable(positive='years_pos')`.

```python
import numpy as np
import pandas as pd

from bquant.analysis.evaluation import (
    SignFlip, months_between, month_key, paired_stats, permutation_placebo,
)

rng = np.random.default_rng(1)
n = 240
entry = pd.Timestamp('2023-01-02') + pd.to_timedelta(np.sort(rng.integers(0, 2 * 365, n)), 'D')
base = pd.DataFrame({'zone_id': np.arange(n), 'month': month_key(entry), 'net': rng.normal(0.0, 1.0, n)})
variant = base.assign(net=base['net'] + rng.normal(0.12, 0.5, n))   # the same zones with the variant's rule

boot = months_between('2023-01-01', '2024-12-31')
row = paired_stats(variant, base, key='zone_id', boot_months=boot, seed=1)
print(row['n'], round(row['mean_diff'], 4), round(row['se'], 4), round(row['p'], 4), row['years_n'], row['years_pos'])

d = (variant['net'] - base['net']).to_numpy()
placebo = permutation_placebo(row['mean_diff'], SignFlip(d), n_perm=200, seed=1)
print(round(placebo['placebo_mean_diff'], 4), placebo['placebo_p'])
# 240 0.1458 0.0294 0.0 2 2
# 0.0003 0.0
```

`contrast_stats(x, flag_a, flag_b, *, month, boot_months)` — разность средних двух групп тех же
единиц, через центрированные индикаторы на том же бутстрепе. Годы для неё считаются внутри
каждого года, а группа меньше `min_group_units` даёт `NaN`. Флаги групп и пороги квантилей
считает вызывающий: два расчёта одного порога разными библиотеками могут разойтись в последнем
бите и перенести единицу через порог.

`permutation_placebo(observed, statistic, *, n_perm, seed)` пересчитывает статистику на
перемешанных единицах: ровно один `rng.permutation(N)` на шаг, `placebo_p` — доля значений
`≥ observed`, без поправки `+1`. Статистики:
- `SignFlip(d)` — **сбалансированный** переворот знаков парных разностей: ровно `N // 2` плюсов
  на перестановку, не независимые ±1;
- `PermuteFlags(x, a, b)` — тасует флаги групп;
- `PermuteColumn(frame, column, statistic)` — общий случай для вызывающего, который
  пересобирает сделки по перемешанному сигналу.

Плацебо в примере держится около нуля, а наблюдаемая разность выше всех 200 перестановок.

`batched=True` передаёт статистике все перестановки одной матрицей. Так считают статистику,
которая обрабатывает все перестановки за один векторный проход
([`trades_at_exit`](trading.md#много-наборов-баров-выхода)); итог побитно тот же.

## Случайный базис

```python
import numpy as np
import pandas as pd

from bquant.analysis.evaluation import attach_random_baseline, random_entry_baseline

rng = np.random.default_rng(1)
index = pd.date_range('2021-01-01', periods=2000, freq='h')
close = 1800 + np.cumsum(rng.normal(0, 1.0, len(index)))
atr = pd.Series(close).diff().abs().rolling(14).mean().to_numpy()


def outcome(entries, hold, side):
    # net outcome of entering at bar e and leaving hold bars later, in ATR of the bar before entry
    return side * (close[entries + hold - 1] - close[entries]) / atr[entries - 1] - 0.05


table = random_entry_baseline(index, outcome, holds=[6, 24], lo=14)
print(table.shape, list(table.columns))
print(table[table['hold'] == 6].round(4).to_string(index=False))

trades = pd.DataFrame({
    'entry_time': index[[100, 500, 900]],
    'exit_time': index[[106, 524, 906]],
    'side': [1, -1, 1],
    'net': [0.4, -0.2, 1.1],
    'hold': [6, 24, 6],
})
print(attach_random_baseline(trades, table)[['side', 'hold', 'net', 'rand']].round(4).to_string(index=False))
#  year  side  hold  expectation  bars
# (4, 5) ['year', 'side', 'hold', 'expectation', 'bars']
#  year  side  hold  expectation  bars
#  2021     1     6      -0.1443  1980
#  2021    -1     6       0.0443  1980
#  side  hold  net    rand
#     1     6  0.4 -0.1443
#    -1    24 -0.2  0.3446
#     1     6  1.1 -0.1443
```

Покупка в год роста выигрывает в среднем при любом сигнале. Базис это снимает: для каждой
клетки (год, сторона, удержание) — **точное среднее** исхода по **всем** барам отрезка, у
которых окно удержания `e … e + H − 1` лежит внутри отрезка; не выборка. Функция исхода —
вызывающего: она получает позиции баров входа, удержание и сторону и возвращает исход в его
единицах (издержки и масштаб — внутри неё); разогрев индикатора выражается через `lo`.
`by_hour=True` добавляет в ключ час входа. `attach_random_baseline` подставляет
`rand` по ключу; сделка, для которой клетки нет, получает `NaN` — она остаётся в `n`, но
выпадает из преимущества.

### Режим выхода

Две стратегии с одним и тем же удержанием `H` могут выходить по-разному: одна на закрытии
бара `e + H − 1`, другая на открытии следующего. Исходы у них разные, и сравнивать вторую с
базисом первой — значит приписать входу то, что сделал выход. `modes` называет каждый способ
выхода и число баров, которое ему нужно сверх `e + H − 1` (*хвост*):

```python
import numpy as np
import pandas as pd

from bquant.analysis.evaluation import attach_random_baseline, random_entry_baseline

rng = np.random.default_rng(1)
index = pd.date_range('2021-01-01', periods=2000, freq='h')
open_ = 1800 + np.cumsum(rng.normal(0, 1.0, len(index)))
close = open_ + rng.normal(0, 0.5, len(index))
atr = pd.Series(close).diff().abs().rolling(14).mean().to_numpy()


def outcome(entries, hold, side, mode):
    # enter at the open of bar e; mode 'close' leaves at the close of bar e + hold - 1,
    # mode 'next_open' at the open of the bar after it
    exit_price = close[entries + hold - 1] if mode == 'close' else open_[entries + hold]
    return side * (exit_price - open_[entries]) / atr[entries - 1] - 0.05


table = random_entry_baseline(index, outcome, holds=[6], modes={'close': 0, 'next_open': 1}, lo=14)
print(table.round(4).to_string(index=False))

trades = pd.DataFrame({
    'entry_time': index[[100, 500]],
    'exit_time': index[[106, 506]],
    'side': [1, 1],
    'net': [0.4, 0.4],
    'hold': [6, 6],
    'mode': ['close', 'next_open'],
})
print(attach_random_baseline(trades, table)[['hold', 'mode', 'rand']].round(4).to_string(index=False))
# year  side  hold      mode  expectation  bars
# 2021     1     6     close      -0.1172  1980
# 2021    -1     6     close       0.0172  1980
# 2021     1     6 next_open      -0.1260  1979
# 2021    -1     6 next_open       0.0260  1979
# hold      mode    rand
#    6     close -0.1172
#    6 next_open -0.1260
```

С `modes` функция исхода получает четвёртый аргумент — метку режима, допустимый вход —
только тот, чьё окно вместе с хвостом лежит внутри отрезка (у `next_open` на один бар
меньше: 1979 против 1980), а в таблице и в ключе подстановки появляется столбец `mode`.
Сделкам тогда нужен свой столбец `mode`; без него `attach_random_baseline` отказывает, а не
считает все сделки первым режимом — иначе сделка с выходом на открытии молча получила бы
ожидание выхода на закрытии. Без `modes` всё как раньше: три аргумента, столбца `mode` нет.

## Процедура по окнам

```python
import numpy as np
import pandas as pd

from bquant.analysis.evaluation import evaluate_procedure

rng = np.random.default_rng(2)
rows = []
for window in range(1, 9):
    back, forward = rng.normal(100, 40, 6), rng.normal(20, 60, 6)
    for run in range(6):
        rows.append({'window': window, 'pass': run + 1, 'stop': [1, 2, 3][run % 3], 'size': [1, 2][run // 3],
                     'back': round(back[run], 2), 'forward': round(forward[run], 2)})
runs = pd.DataFrame(rows)

result = evaluate_procedure(runs, defaults={'stop': 2, 'size': 2})
print(result.per_window[['window', 'chosen', 'defaults', 'grid_mean', 'percentile', 'oracle']].round(2).to_string(index=False))
print(result.series[['sum', 'share_pos']].round(2).to_string())
print(result.paired.round(2).to_string())
#  window  chosen  defaults  grid_mean  percentile  oracle
#       1   78.65     78.65      28.43        0.83   78.65
#       2   39.83     39.83      30.05        0.50   70.49
#       3   84.70     32.63      52.66        0.83   84.70
#       4   99.46      5.90      16.52        0.83   99.46
#       5  -26.26      3.18      46.85        0.00  162.49
#       6  110.61    110.61       8.10        0.83  110.61
#       7   13.72     73.50      25.91        0.33   73.50
#       8    6.67      6.67      19.03        0.33  105.71
#               sum  share_pos
# variant
# chosen     407.38       0.88
# defaults   350.97       1.00
# grid_mean  227.55       1.00
# oracle     785.61       1.00
#                      mean_diff     t  share_pos    n
# comparison
# chosen_vs_grid_mean      22.48  1.12       0.62  8.0
# chosen_vs_defaults        7.05  0.42       0.25  8.0
```

Вход — по строке на (окно, проход) с результатом на окне подбора `back`, на форвардном
окне `forward` и параметрами прохода. Выбранный проход — `argmax back`, при равенстве —
меньший номер прохода. Против него три варианта, которые ничего не подбирают: проход с
параметрами **умолчаний** (ровно одна строка должна совпасть по всем `defaults`, иначе
`NaN`), **среднее по сетке** (проход, взятый наугад) и **оракул** (лучший форвард — верхняя
граница, которой никто не достигает). `percentile` — доля форвардов **строго ниже**
выбранного: 0.5 — как случайный выбор. По серии — сумма, медиана, доля окон в плюсе,
минимум и максимум каждого варианта; `t` парной разности «выбранный − базис» считается при
`n > 2` и ненулевом разбросе, иначе `NaN`. В примере восемь окон случайных чисел: подбор
дал `t = 1.12` против сетки и `0.42` против умолчаний — ничего, что отличалось бы от шума.

## Квартальная мерка

```python
import numpy as np
import pandas as pd

from bquant.analysis.evaluation import apply_rules, default_quarter_rules, quarterly_summary

rng = np.random.default_rng(3)
exits = pd.Timestamp('2021-01-05') + pd.to_timedelta(np.sort(rng.integers(0, 3 * 365 * 24, 400)), 'h')
balance = pd.Series(10_000 + np.cumsum(rng.normal(25, 250, 400)), index=exits)

summary = quarterly_summary(balance, initial=10_000)
print(summary['q_n'], summary['q_pos'], round(summary['q_median'], 4), round(summary['q_worst'], 4))
print(round(summary['max_dd'], 4), summary['longest_underwater_days'], summary['underwater_tail_days'])
print(round(summary['top_k_share'], 3))
print(apply_rules(summary, default_quarter_rules()))
# 13 11 0.0635 -0.1203
# -0.1835 153 13
# 0.575
# {'ok_quarters_positive': True, 'ok_quarter_median': True, 'ok_worst_quarter': True, 'ok_quarter_mean_over_std': True, 'pass': True}
```

Вход — баланс после каждой сделки, индекс — время выхода. Квартал календарный;
доходность квартала — баланс на его конец к балансу на конец предыдущего квартала (для
первого — депозит) минус один. Ключи: `q_n`, `q_pos`, `q_median`, `q_worst`, `q_mean`,
`q_std`, `q_mean_over_std`, `max_dd` (`min(balance / cummax − 1)` по сделкам),
`longest_underwater_days`, `underwater_tail_days`, `top_k_share`, `final`, `q_returns`.

Два решения, которые эталонная реализация оставляла неявными, здесь названы:
**квартал без сделок — квартал**: баланс переносится, доходность 0, квартал считается (плоский
квартал не положительный); и **хвост под водой виден**: `longest_underwater_days` — самый
длинный промежуток между соседними новыми максимумами — не видит отрезка от последнего
максимума до конца ряда, того самого, что открыт в живом прогоне; его несёт
`underwater_tail_days`. `top_k_share` — доля итоговой прибыли, сделанная `top_k` лучшими
кварталами (`NaN`, если итог не положителен).

Правила над сводкой — те же объекты, что и над кандидатами: `QuartersPositive(share)`,
`QuarterMedian(threshold)`, `WorstQuarter(threshold)`, `QuarterMeanOverStd(threshold)`;
`default_quarter_rules()` — пороги `2/3`, `0.02`, `−0.25`, `0.4`, предложенные запросившей
стороной и подлежащие пересмотру новым объектом. `apply_rules(summary, rules)` даёт флаги и
`pass`.

## Издержки сделки

> **Без заказчика с ноября 2026** — поддерживается, не расширяется (как и [`trading`](trading.md)).

Издержки круга сделки — в **пунктах** символа, положительное — расход; делить на ATR или на что
угодно ещё — дело вызывающего. Обычно они живут в функции исхода, которую усредняет случайный базис.

`rollover_nights(entry_time, exit_time, *, triple_weekday=2)` считает ночи свопа по календарю
сервера брокера. Полночь `m`, где `вход < m ≤ выход`, начисляется, если день, который она
завершает, — пн…пт: ночи после субботы и воскресенья не начисляются. Полночь после дня
`triple_weekday` (0 — понедельник; у большинства брокеров 2, ночь на четверг) идёт за три,
поэтому неделя — это 7 ночей. Время выхода — момент закрытия позиции: закрытие последнего бара
(его время плюс бар) или открытие следующего. Время с поясом читается по его собственным часам,
поэтому сначала переведите его в пояс сервера.

`CostModel` считает `спред + комиссия − своп(сторона) · ночи`:

```python
import numpy as np
import pandas as pd

from bquant.analysis.evaluation import CostModel, rollover_nights

entry = pd.to_datetime(['2022-01-04 10:00', '2022-01-05 15:00', '2022-01-07 12:00'])   # Tue, Wed, Fri
exit_ = pd.to_datetime(['2022-01-04 18:00', '2022-01-06 09:00', '2022-01-10 08:00'])   # same day, Thu, Mon
nights = rollover_nights(entry, exit_, triple_weekday=2)     # the Wednesday night counts three
print(nights.tolist())

spec = {'swap_mode': 1, 'swap_long': -3.2, 'swap_short': 1.1, 'swap_rollover3day': 3}   # MT5: Sunday = 0
model = CostModel.from_symbol_spec(spec, spread='bar', min_spread_points=15.0, commission_points=7.0)
spread = np.array([12.0, 25.0, np.nan])          # the spread of each entry bar; a missing one counts as 0
cost = model.round_trip(spread, entry_idx=[0, 1, 2], side=[1, 1, -1], nights=nights)
print(model.triple_weekday, cost.round(2).tolist())
# [0, 3, 1]
# 2 [22.0, 41.6, 20.9]
```

Бары MetaTrader — это цены bid, поэтому за круг платится **один** спред. В режиме `spread='bar'`
это спред бара входа: не меньше `min_spread_points`, пустой считается нулём. Режим `'fixed'` берёт
`fixed_spread_points`, это стресс-вариант. Своп указан со знаком MetaTrader: отрицательный
платится и прибавляется к издержкам. `from_symbol_spec` читает своп из спецификации символа,
где день недели считается от воскресенья: `triple_weekday = (swap_rollover3day − 1) % 7`.

Отказы, а не подмены:
- модели со свопом нужны `nights`; без них своп выпал бы из издержек без следа;
- `swap_mode ≠ 1` (своп не в пунктах) и спецификация без `swap_rollover3day` отклоняются;
- `triple_weekday` вне 0…4 отклоняется: тройная ночь в выходной никогда бы не начислилась;
- выход раньше входа и `side` не ±1 тоже отклоняются.

## От зон к оценке — пример стыковки

Пакет не превращает зоны в сделки: правила входа и выхода — решение торговой системы, а не
методологии, и одна зашитая связка читалась бы как ответ на вопрос «торгуются ли зоны», хотя
отвечала бы за один произвольный набор правил. Ниже правило — **самого примера**: вход на
открытии бара после первого бара зоны, выход на закрытии первого бара следующей зоны, бычья
зона — покупка, медвежья — продажа, издержки 0.05 ATR.

```python
import numpy as np
import pandas as pd

from bquant.analysis.evaluation import (
    BlockBootstrap, attach_random_baseline, default_criterion, months_between,
    random_entry_baseline, trial_stats,
)
from bquant.analysis.zones import analyze_zones
from bquant.data import calculate_atr
from bquant.data.samples import get_sample_data

result = (
    analyze_zones(get_sample_data('tv_xauusd_1h'))
    .with_indicator('custom', 'macd', fast_period=12, slow_period=26, signal_period=9)
    .detect_zones('zero_crossing', indicator_role='hist')
    .analyze()
    .build()
)
bars = result.data
open_, close = bars['open'].to_numpy(), bars['close'].to_numpy()
atr = calculate_atr(bars, period=14).to_numpy()
COST = 0.05          # round-trip costs, in ATR of the bar before entry


def outcome(entries, hold, side):
    exits = entries + hold - 1
    return side * (close[exits] - open_[entries]) / atr[entries - 1] - COST


# The rule is the example's, not the package's: the zone is known at the close of its
# first bar, so enter on the next open; its end is known at the close of the first bar
# of the next zone, so exit there. Bull zone -> buy, bear zone -> sell.
rows = []
for zone in result.zones:
    entry, exit_ = zone.start_idx + 1, zone.end_idx + 1
    if exit_ >= len(bars) or np.isnan(atr[entry - 1]):
        continue                      # the last zone is still open; the first has no ATR yet
    side = 1 if zone.type == 'bull' else -1
    rows.append({
        'entry_time': bars.index[entry], 'exit_time': bars.index[exit_],
        'side': side, 'hold': exit_ - entry + 1,
        'net': float(outcome(np.array([entry]), exit_ - entry + 1, side)[0]),
    })
trades = pd.DataFrame(rows)

baseline = random_entry_baseline(bars.index, outcome, holds=trades['hold'].unique(), lo=15)
trades = attach_random_baseline(trades, baseline)

boot = BlockBootstrap(months_between(bars.index[0], bars.index[-1]), B=2000, seed=1)
row = trial_stats(trades, boot)
print(row['n'], round(row['net_mean'], 3), round(row['net_lo'], 3), round(row['net_hi'], 3))
print(round(row['excess_mean'], 3), round(row['excess_lo'], 3), round(row['p'], 3))
print(len(boot.months), row['years_n'])

verdict = default_criterion().evaluate(pd.DataFrame([{k: v for k, v in row.items() if k != 'years'}]), m_total=1)
print({k: bool(v) for k, v in verdict.iloc[0].items() if k.startswith('ok_') or k == 'pass'})
# 76 -0.069 -0.352 0.15
# -0.019 -0.306 0.558
# 3 1
# {'ok_min_trades': False, 'ok_net_positive': False, 'ok_years_stable': False, 'ok_beats_random': False, 'pass': False}
```

**Как это читать.** 76 сделок, средний итог −0.069 ATR, интервал от −0.352 до 0.15 —
ноль внутри; преимущество над случайным входом того же года, стороны и удержания — −0.019 при `p = 0.558`. Ни одно из четырёх правил не пройдено, и важно,
*почему*: образец — 1000 часовых баров, около двух месяцев, это **три** блока бутстрепа и
**один** год. На таком отрезке метод не имеет права сказать «состоятельно», даже будь среднее
положительным: `MinTrades` требует 100 сделок, `YearsStable` — два года. Это и есть рабочий
результат — отказ с названной причиной, а не число, которое хочется прочитать как сигнал.

Функция исхода одна и для сделок, и для базиса: так случайный вход оценивается ровно теми же
издержками и в том же масштабе. `lo=15` — разогрев ATR: бар входа должен иметь ATR
предыдущего бара. Последняя зона ещё не закрыта и в сделки не идёт.

## Чего модуль не делает

Не хранит реестр опробованных вариантов (`m_total` — от вызывающего), не знает про зоны,
ряды и советники, не разбирает отчёты тестеров — кадр сделок, таблицу проходов и кривую
баланса строит вызывающий.
