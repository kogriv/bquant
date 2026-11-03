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
| сводка и критерий | выживает ли преимущество после поправки на всё опробованное | `trial_stats`, `benjamini_hochberg`, `Rule`, `MinTrades`, `NetPositive`, `YearsStable`, `BeatsRandom`, `MinEffect`, `apply_rules`, `Criterion`, `default_criterion` |
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
#  2021     1     6      -0.1449  1979
#  2021    -1     6       0.0449  1979
#  side  hold  net    rand
#     1     6  0.4 -0.1449
#    -1    24 -0.2  0.3454
#     1     6  1.1 -0.1449
```

Покупка в год роста выигрывает в среднем при любом сигнале. Базис это снимает: для каждой
клетки (год, сторона, удержание) — **точное среднее** исхода по **всем** барам отрезка, у
которых окно удержания `e … e + H − 1` лежит внутри отрезка; не выборка. Функция исхода —
вызывающего: она получает позиции баров входа, удержание и сторону и возвращает исход в его
единицах (издержки и масштаб — внутри неё); разогрев индикатора выражается через `lo`.
`by_hour=True` добавляет в ключ час входа. `attach_random_baseline` подставляет
`rand` по ключу; сделка, для которой клетки нет, получает `NaN` — она остаётся в `n`, но
выпадает из преимущества.

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

## Чего модуль не делает

Не хранит реестр опробованных вариантов (`m_total` — от вызывающего), не знает про зоны,
ряды и советники, не разбирает отчёты тестеров — кадр сделок, таблицу проходов и кривую
баланса строит вызывающий.
