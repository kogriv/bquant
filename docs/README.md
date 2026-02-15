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

Если новая страница открывается по прямой ссылке, но не появляется в левой панели (toctree), обычно это эффект инкрементальной сборки.

```bash
# Остановить sphinx-autobuild
Ctrl+C

# Очистить артефакты и пересобрать с "чистой" средой
python -m sphinx -M clean docs docs/_build
sphinx-autobuild docs docs/_build/html -a -E --open-browser
```

После перезапуска сделайте hard refresh в браузере (`Ctrl+Shift+R`).

### Лог сборки и что проверять

Если проблема осталась, сохраните полный лог сборки в файл и проверьте предупреждения:

```bash
# Одноразовая полная сборка с записью лога
python -m sphinx -b html docs docs/_build/html -E -a -n -T 2>&1 | tee docs/_build/sphinx-build.log
```

Где смотреть:

- Файл лога: `docs/_build/sphinx-build.log`
- Ключевые паттерны: `toctree`, `orphan`, `WARNING`, `document isn't included in any toctree`
- Частый кейс: документ собирается, но отсутствует в меню, если не попал в `toctree` или помечен `:orphan:`

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
