# Документация BQuant — как собрать локально

Эта страница нужна тому, кто **правит доку**. Читателю самой документации она не
нужна: он открывает [bquant.readthedocs.io](https://bquant.readthedocs.io/) или
начинает с [user_guide/quick_start.md](user_guide/quick_start.md).

В сборку сайта эта страница не входит — навигацию там даёт `index.rst`.

## Структура

| Каталог | Что внутри |
|---|---|
| `user_guide/` | руководства для пользователя пакета |
| `api/` | справочник по модулям |
| `tutorials/` | пошаговые сценарии |
| `examples/` | разбор примеров из `examples/` в корне |
| `developer_guide/` | для тех, кто расширяет пакет |
| `analytics/` | разборы конкретных исследований |
| `migration/` | переходы между версиями API |

## Сборка

```bash
pip install -e .[docs]
python -m sphinx -b html docs docs/_build/html
```

Открыть `docs/_build/html/index.html`.

Живая пересборка при правке:

```bash
pip install sphinx-autobuild
sphinx-autobuild docs docs/_build/html --open-browser
```

## Сборка обязана быть без предупреждений

Предупреждения Sphinx — это не шум, а отдельный слой проверок, которого нет
в тестах. Автоматические проверки доки читают страницы как **текст** и не знают,
во что они собираются:

| Что ловит только сборка | Пример |
|---|---|
| ссылка на каталог, а не на файл | `[core](../core/)` — на GitHub работает, на сайте ведёт в никуда |
| ссылка за пределы дерева доки | ссылка из `docs/` на `devref/` или корневой `README.md` |
| разрыв уровней заголовков | H2 сразу на H4 — ломает оглавление страницы |
| неизвестный лексер подсветки | ` ```csv ` — блок отрендерится без подсветки |

Отсюда правило: **страницу правят до нуля предупреждений о ней**, а не до «текст
выглядит хорошо».

```bash
python -m sphinx -b html docs docs/_build/html -E -a 2>&1 | grep -i warning
```

Ключевые слова в логе: `toctree`, `orphan`, `xref_missing`,
`document isn't included in any toctree`.

Если страница открывается по прямой ссылке, но не появилась в левом меню, — как
правило, дело в инкрементальной сборке. Чистая пересборка:

```bash
python -m sphinx -M clean docs docs/_build
python -m sphinx -b html docs docs/_build/html -E -a
```

## Публикация

Сайт собирает Read the Docs по `.readthedocs.yml` (Python 3.12, extras `docs`).

**Пуш только в GitHub сайт не пересобирает** — RTD подключён к зеркалу на GitLab.
Это стоило одного релиза документации: пакет уехал на PyPI, а сайт сутки показывал
предыдущую версию. Подробности, признаки и проверка одной командой —
[SETUP_READTHEDOCS.md](../SETUP_READTHEDOCS.md).

Релизная версия сайта появляется от тега `vX.Y.Z`.

## Ссылки

- Сайт: <https://bquant.readthedocs.io/>
- Полное руководство по документации: [SETUP_READTHEDOCS.md](../SETUP_READTHEDOCS.md)
- Sphinx: <https://www.sphinx-doc.org/>
