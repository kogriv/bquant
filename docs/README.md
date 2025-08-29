# BQuant Docs — Quick Start

Краткие инструкции для локальной сборки и просмотра документации. За подробным руководством (настройка RTD, автогенерация API, версии, CI) см. «Полное руководство»: `SETUP_READTHEDOCS.md`.

## Структура

- `api/` — API документация
- `user_guide/` — Руководства и гайды
- `developer_guide/` — Для разработчиков
- `tutorials/` — Туториалы
- `examples/` — Примеры кода
- `_static/`, `_templates/` — статика и шаблоны

## Установка зависимостей (единый источник)

```bash
pip install -e .[docs]
```

## Сборка

```bash
# Из корня проекта
python -m sphinx -b html docs docs/_build/html

# Либо из каталога docs
cd docs
sphinx-build -b html . _build/html
```

## Просмотр

Откройте в браузере: `docs/_build/html/index.html`.

## Live‑режим (по желанию)

```bash
pip install sphinx-autobuild
sphinx-autobuild docs docs/_build/html --open-browser
```

## Read the Docs (сборка в облаке)

- Конфиг: `.readthedocs.yml` (Python 3.11, Sphinx, extras `docs`).
- Для обновления «latest» — достаточно `git push` в основную ветку.
- Для релизной версии — создайте тег `vX.Y.Z` и запушьте.

Подробнее: см. `SETUP_READTHEDOCS.md`.

## Полезные ссылки

- Live: https://bquant.readthedocs.io/
- RTD: https://readthedocs.org/
- Sphinx: https://www.sphinx-doc.org/
- Repo: https://github.com/kogriv/bquant
