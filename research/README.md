# research/

Исследовательские скрипты пакета. Сверено с содержимым каталога 2026-09-05.

## Что здесь есть

| Каталог | Содержимое |
|---|---|
| `notebooks/` | **20 python-скриптов** в стиле ноутбука (`NotebookSimulator`: шаги, пауза, разбор аргументов CLI) и их логи `*_log.txt`. Нумерация по слою пакета: `00_logging*`, `01_data*` (загрузка, обработка, схемы, валидация), `02_ind_*` (индикаторы), `03_analysis_*` и `03_zones_universal` (анализ), `04_zones_*` (визуализация), `06_swing_strategy_comparison` (кейс-стади свингов) |
| `experiments/` | только `README.md` с описанием будущей структуры; экспериментов нет |
| `studies/` | только `README.md`; исследований нет |

Jupyter-ноутбуков (`.ipynb`) в репозитории нет — и не планируется: скрипт с
`NotebookSimulator` исполняется из командной строки, попадает в батарею перед релизом и не
хранит выводы в файле. Каталогов `methodology/` и `templates/` тоже нет.

## Запуск

```bash
python research/notebooks/03_zones_universal.py --no-trap
```

`--no-trap` отключает паузы между шагами (`nb.wait()` ждёт `Enter`); под ним скрипты
гоняются батареей перед релизом вместе с `examples/*.py`, обязательно с `MPLBACKEND=Agg` —
иначе `plt.show()` откроет окно и повиснет. Пакет должен быть установлен (`pip install -e .`);
`sys.path` править не нужно. Справочник по `NotebookSimulator` — `docs/api/core/nb.md`.

Типичный импорт:

```python
from bquant.analysis.zones import analyze_zones, analyze_macd_zones
from bquant.analysis.statistical import run_all_hypothesis_tests
from bquant.data.samples import get_sample_data
from bquant.visualization import FinancialCharts, set_default_theme
```

## Правила

- Данные — только встроенные сэмплы (`bquant.data.samples`) или файлы, которых нет в репозитории и путь к которым не захардкожен.
- Числа, которые скрипт печатает и которые попадают в доки, — из прогона, не переписанные.
- Скрипт, который что-то «проверяет», обязан уметь упасть: шаг, печатающий «OK» при нулевом результате, — не проверка (см. `changelogs/` за 2026-09-05, шаг 11.1 в `03_zones_universal.py`).
- Кейс-стади с выводами живут в `docs/analytics/`, а не здесь: `06_swing_strategy_comparison.py` — источник чисел для `docs/analytics/zones/swing_strategy_comparison_case_study.md`.

## Связанное

- [Документация](../docs/) · [Примеры](../examples/) · [Тесты](../tests/)
- Issues: <https://github.com/kogriv/bquant/issues>
