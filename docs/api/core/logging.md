# `bquant.core.logging_config` — логирование

Одна точка настройки, семь профилей и модульные уровни. Задача, ради которой всё это
есть: скрыть технические подробности пакета из консоли, не теряя их в файле.

## Настройка одной строкой

```python
from bquant.core.logging_config import LOGGING_PROFILES, setup_logging

print(sorted(LOGGING_PROFILES))
# ['audit', 'clean', 'critical', 'debug', 'focused', 'research', 'verbose']

setup_logging(profile='research')
```

| Профиль | Консоль | Файл | Для чего |
|---|---|---|---|
| `research` | WARNING+ | INFO+ | research-скрипты и демонстрации |
| `clean` | ERROR+ | INFO+ | минимум шума, детали остаются в файле |
| `debug` | DEBUG+ | DEBUG+ | отладка |
| `verbose` | DEBUG+ | DEBUG+ | то же, без модульных различий |
| `focused` | DEBUG для `bquant.core`, INFO для прочих | DEBUG+ | работа над ядром |
| `critical` | ERROR+ | ERROR+ | production |
| `audit` | ERROR+ | INFO+ | аудит: тихая консоль, полный файл |

Таблица проверяема: под `research` сообщение уровня INFO от `bquant.data.loader` в
консоль не попадает, а WARNING и ERROR попадают; под `debug` попадают все три.

## Параметры `setup_logging()`

| Параметр | Что задаёт |
|---|---|
| `level`, `console_level`, `file_level` | уровни общий, консольный, файловый |
| `log_to_file`, `log_file` | включить файл и указать путь |
| `use_colors`, `console_enabled` | ANSI-цвета, вывод в консоль |
| `reset_loggers` | сбросить ранее настроенные логгеры |
| `profile` | один из семи профилей выше |
| `modules_config` | уровни по модулям: `{'bquant.data': {'console': 'WARNING', 'file': 'INFO'}}` |
| `exceptions` | исключения для конкретных логгеров: `{'bquant.data.loader': 'INFO'}` |

Приоритет — `profile` → `modules_config` → `exceptions`: каждый следующий уточняет
предыдущий.

```python
from bquant.core.logging_config import setup_logging

setup_logging(
    profile='research',
    modules_config={'bquant.analysis': {'console': 'DEBUG', 'file': 'DEBUG'}},
    exceptions={'bquant.core.nb': 'INFO'},
)
```

Настройки наследуются вниз по дереву имён: `bquant.data` покрывает `bquant.data.loader`,
`bquant.data.processor` и всё остальное под ним.

## Логгер

```python
from bquant.core.logging_config import get_logger

logger = get_logger(__name__)
contextual = get_logger(__name__, context={'symbol': 'XAUUSD', 'timeframe': '1h'})

print(type(logger).__name__, type(contextual).__name__)
# Logger ContextualLogger
```

С `context` возвращается `ContextualLogger`: он дописывает `[symbol=XAUUSD,
timeframe=1h]` в каждую строку. Без контекста — обычный `logging.Logger`.

## Операция как единица лога

```python
from bquant.core import LoggingContext

with LoggingContext("загрузка данных", symbol="XAUUSD"):
    ...   # работа

# INFO  [symbol=XAUUSD] Начало операции: загрузка данных
# INFO  [symbol=XAUUSD] Операция 'загрузка данных' завершена успешно за 0.12 сек
```

Пишет начало, а на выходе — успех с длительностью либо ошибку. Именованные аргументы
становятся контекстом каждой строки внутри блока. Исключение логируется и
**пробрасывается дальше** — менеджер его не глотает.

## Два декоратора

```python
from bquant.core import log_function_call, log_performance


@log_function_call
def load_and_prepare(path):
    ...


@log_performance
def heavy_pass(data):
    ...
```

`log_function_call` пишет вход и успешный выход **на уровне DEBUG**, ошибку — на ERROR.
При обычном `INFO` в логе не появится ничего, пока функция не упадёт; это устройство, а
не поломка. Чтобы увидеть трассировку — `setup_logging(profile='debug')`.

`log_performance` пишет строку **только если вызов занял больше секунды**. Быстрый вызов
не логируется вовсе: молчание здесь означает «быстро», а не «не сработало». Порог зашит и
не настраивается. Полноценный замер — со счётчиками, историей и экспортом — это
[`bquant.core.performance`](performance.md), а не эти декораторы.

## Fluent API

```python
from bquant.core.logging_config import LoggingConfigurator

(LoggingConfigurator()
    .preset('development', 'focused')
    .module('bquant.data')
        .console('WARNING')
        .file('DEBUG')
    .module('bquant.indicators')
        .console('ERROR')
    .exception('bquant.data.loader', 'INFO')
    .apply())
```

`preset(env_type, profile)` принимает первым аргументом тип окружения (`'notebook'`,
`'development'`, `'production'`, `'quiet'`), и **он ни на что не влияет**: конфигурацию
определяет только второй аргумент — профиль. `.preset('notebook', 'research')` и
`.preset('development', 'research')` дают побайтно одно и то же. Параметр оставлен под
будущие различия окружений; пока это единственная его роль.

## Тихая инициализация

Массовые регистрации при импорте свёрнуты в одну строку каждая, а болтовня сторонних
библиотек подавлена:

```
INFO - Zone detection strategies registered: combined, line_crossing, preloaded, threshold, zero_crossing
INFO - External indicators registered: pandas_ta=158, talib=0
```

Детали по каждой стратегии и каждому индикатору доступны на уровне DEBUG. Предупреждение
об отсутствующей TA-Lib остаётся WARNING — библиотека требует системной части и в
зависимости пакета не входит.

## Если INFO всё равно видно

Проверять стоит в таком порядке:

1. **Профиль вообще применён?** `setup_logging()` без аргументов ничего не меняет —
   нужен `profile=` или явные уровни.
2. **Логгер под деревом `bquant`?** Модульные настройки адресуются по имени, и
   `get_logger('my_script')` под них не попадает. Для своего кода задавайте
   уровень отдельно.
3. **Не перекрыт ли профиль позже?** Последний вызов `setup_logging()` побеждает.

Чего проверять **не** надо:

* **Порядок настройки и импортов.** `setup_logging(profile='research')` действует
  одинаково, вызван он до импорта `bquant.data.loader` или после — уровни
  устанавливаются на дерево имён, а не на конкретные объекты логгеров. Единственное
  настоящее следствие порядка: строки, напечатанные **во время** импорта, печатаются по
  тем настройкам, что действовали в тот момент. Задним числом их не убрать.
* **Откуда импортирован `setup_logging`.** `from bquant.core import setup_logging` и
  `from bquant.core.logging_config import setup_logging` — это один и тот же объект.

До 2026-09-01 раздел утверждал обратное по обоим пунктам: «Слишком поздно!» про порядок
и `from bquant.core import setup_logging  # ❌` про импорт.

## С NotebookSimulator

Сообщения `NotebookSimulator` печатаются напрямую и профилями не подавляются: `nb.info()`
и `nb.success()` видны при любом. Профиль управляет техническими логгерами пакета —
ровно то разделение, ради которого он и нужен:

```python
from bquant.core.logging_config import setup_logging
from bquant.core.nb import NotebookSimulator

setup_logging(profile='research')     # технические детали — в файл

nb = NotebookSimulator("Демонстрация")
nb.info("Шаг 1: загрузка данных")     # видно всегда
```

## Дальше

| | |
|---|---|
| [Notebook-скрипты](nb.md) | `NotebookSimulator` целиком |
| [Производительность](performance.md) | настоящий замер вместо `log_performance` |
| [Ядро](README.md) | остальные модули |
