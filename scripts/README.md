# scripts/

Служебные скрипты. Сверено с каталогом 2026-09-05; флаги — из `argparse` самих скриптов.

| Каталог | Содержимое |
|---|---|
| `analysis/` | `run_macd_analysis.py`, `test_hypotheses.py`, `batch_analysis.py` + `README.md` |
| `data/` | `extract_samples.py`, `generate_samples.py`, `data_loader.py` |
| `publishing/` | `cleanup.sh`, `cleanup.ps1` — чистка дерева перед публикацией, `README.md` |
| `data_processing/`, `deployment/` | пусто; заведены под будущее |
| `cloud_setup.sh` | bootstrap окружения для облачной сессии Claude Code: Python 3.12 + зависимости строго из `uv.lock` |

## Анализ

```bash
python scripts/analysis/run_macd_analysis.py XAUUSD 1h --sample-data --output-format json
python scripts/analysis/test_hypotheses.py XAUUSD 1h --sample-data --all-tests --alpha 0.05
python scripts/analysis/batch_analysis.py --all-datasets --include-macd --include-hypotheses
```

Позиционные `symbol timeframe`; `--sample-data` берёт встроенный сэмпл вместо файла из
`data/`; у всех троих есть `--dry-run` и `--verbose`. `batch_analysis.py` принимает
`--symbols`/`--timeframes` списками, `--parallel --max-workers N`, `--config`.

## Данные

```bash
python scripts/data/extract_samples.py --extract-all
python scripts/data/extract_samples.py --dataset tv_xauusd_1h
python scripts/data/extract_samples.py --validate-sources
```

Извлекает встроенные сэмплы из исходных CSV (`--source` — каталог с ними). Исходные файлы
в репозитории **отсутствуют** и не нужны для работы пакета: сэмплы уже встроены в
`bquant.data.samples`.

## Требования

- Python **≥ 3.12**, пакет установлен (`pip install -e .`).
- Скрипт с CLI обязан: разбирать аргументы `argparse`, логировать через
  `bquant.core.logging_config`, не глотать исключения и иметь `--dry-run`, если что-то пишет.
