# `bquant.data.validator` — валидация данных

Пять проверок разной глубины. Ни одна не меняет кадр — каждая возвращает словарь с
вердиктом, перечнем находок и рекомендациями.

| Функция | Отвечает на вопрос | Ключ вердикта |
|---|---|---|
| `validate_ohlcv_data(df, strict=True)` | пригодны ли данные в целом | `is_valid` |
| `validate_data_completeness(df, required_columns=None, min_rows=None)` | всё ли на месте | `is_complete` |
| `validate_price_consistency(df)` | не противоречат ли цены друг другу | `is_consistent` |
| `validate_time_series_continuity(df, expected_frequency=None)` | нет ли дыр во времени | `is_continuous` |
| `validate_statistical_properties(df)` | как распределены значения | — |

## Общая проверка

```python
from bquant.data.samples import get_sample_data
from bquant.data.validator import validate_ohlcv_data

report = validate_ohlcv_data(get_sample_data('tv_xauusd_1h'))

print(report['is_valid'], report['issues'])
print(report['warnings'])
print(sorted(report['stats'].keys()))
# True []
# ['High missing data ratio: 26.67%']
# ['date_range', 'missing_data_summary', 'total_columns', 'total_rows']
```

**Предупреждение настоящее и объяснимое.** Четыре колонки из пятнадцати —
`regular_bullish`, `regular_bullish_label`, `regular_bearish`,
`regular_bearish_label` — маркеры дивергенций TradingView: они заполнены только на
сигнальных барах, а в выгрузке пусты целиком. Четыре пустых колонки из пятнадцати и
дают 26.67%. К ценам это отношения не имеет, поэтому `issues` пуст, а `is_valid` — `True`.

Эти же четыре колонки однажды обнулили `prepare_data_for_analysis()`
(`devref/gaps/data/g41_…`). Пустая колонка безобидна ровно до тех пор, пока кто-нибудь
не начнёт по ней отсеивать строки.

## Полнота

```python
from bquant.data.samples import get_sample_data
from bquant.data.validator import validate_data_completeness

report = validate_data_completeness(get_sample_data('tv_xauusd_1h'))

print(report['is_complete'], report['missing_columns'], report['insufficient_rows'])
print({k: float(v) for k, v in report['missing_data_ratio'].items() if v > 0})
# False [] False
# {'regular_bullish': 1.0, 'regular_bullish_label': 1.0, 'regular_bearish': 1.0, 'regular_bearish_label': 1.0}
```

`is_complete` здесь `False`, и это верно: доля пропусков в четырёх колонках равна
единице. Обязательные колонки при этом на месте, строк достаточно — то есть «неполно»
не значит «непригодно». Смотреть надо не на флаг, а на `missing_data_ratio`.

## Логика цен

```python
from bquant.data.samples import get_sample_data
from bquant.data.validator import validate_price_consistency

report = validate_price_consistency(get_sample_data('tv_xauusd_1h'))

print(report['is_consistent'])
print(report['price_issues'], report['logical_errors'], report['extreme_values'])
# True
# [] [] []
```

Проверяется то, что обязано выполняться по определению свечи: `high >= low`,
`high >= max(open, close)`, `low <= min(open, close)`, неотрицательность, отсутствие
скачков неправдоподобного размера.

## Непрерывность ряда

Функции нужен `DatetimeIndex` — время должно стоять в индексе:

```python
from bquant.data.processor import resolve_time_index
from bquant.data.samples import get_sample_data
from bquant.data.validator import validate_time_series_continuity

data = resolve_time_index(get_sample_data('tv_xauusd_1h'))
report = validate_time_series_continuity(data, expected_frequency='1h')

print(report['is_continuous'], report['detected_frequency'])
print(len(report['gaps']), report['duplicates'])
print(report['recommendations'])
# False None
# 482 []
# ['Fill 482 missing timestamps']
```

**`is_continuous: False` здесь — правильный ответ, а не находка.** Рынок золота стоит
по выходным: в `gaps` 482 записи, и каждая — часовая метка, которой нет, потому что
сессия была закрыта. Функция сообщает факт, а решать, дыра это или календарь, должен
читатель. Заполнять такие пропуски — почти всегда ошибка: она рисует торговлю там, где
её не было.

`detected_frequency` при этом `None` — именно из-за неравномерности; переданный
`expected_frequency` на определение не влияет, он используется для сверки.

## Статистика

```python
from bquant.data.samples import get_sample_data
from bquant.data.validator import validate_statistical_properties

report = validate_statistical_properties(get_sample_data('tv_xauusd_1h'))

close = report['statistics']['close']
print(round(close['mean'], 2), round(close['std'], 2))
print(round(close['skewness'], 3), round(close['kurtosis'], 3))
# 3350.64 35.59
# 0.154 -0.23
```

Возвращает `statistics` по каждой числовой колонке, `outliers`, `distribution_issues` и
`recommendations`. Вердикта одним флагом здесь нет намеренно: «распределение не такое»
— не то, что решается за пользователя.

## Как читать результат

* `issues` — то, что делает данные непригодными; `warnings` — то, о чём стоит знать.
* Флаг (`is_valid`, `is_complete`, `is_consistent`, `is_continuous`) — сводка, а не
  приговор: у каждого из них есть законные `False`, как показано выше.
* `recommendations` — подсказки, а не команды; на рыночных данных «заполните пропуски»
  часто означает «нарисуйте выходные».

## Дальше

| | |
|---|---|
| [Схемы](schemas.md) | проверка по объявленным полям и правилам |
| [Обработка](processor.md) | что делать с найденным |
| [Sample-данные](samples.md) | `validate_dataset()` — целостность встроенных наборов |
