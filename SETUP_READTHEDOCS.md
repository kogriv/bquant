# Полное руководство по документации BQuant

> ## ⚠️ Факт, проверенный 2026-08-24: RTD подключён к **GitLab**, а не к GitHub
>
> Этот документ ниже описывает **задуманную** схему с импортом проекта через GitHub.
> Действующая — другая. Публичный API RTD отвечает:
>
> ```
> repository: https://gitlab.com/kogriv/bquant.git | type: git
> ```
>
> Практические следствия, которые стоят потерянного релиза документации:
>
> - **У GitHub-репозитория нет ни одного вебхука** (`gh api repos/kogriv/bquant/hooks`
>   возвращает `[]`) — они и не нужны, RTD слушает не его.
> - **Пуш только в `github` документацию не пересобирает.** Именно это и случилось при
>   выпуске 0.0.6: пакет ушёл на PyPI, а readthedocs.io ещё сутки показывал 0.0.5 с
>   примерами, которые не работают. Проверяется одной командой:
>   ```bash
>   curl -sI https://bquant.readthedocs.io/en/latest/ | grep last-modified
>   ```
> - **`origin` пушит на оба зеркала сразу** (у него два push-URL), поэтому обычный
>   `git push origin main` документацию пересобирает, а избирательный
>   `git push github main` — нет.
> - На странице пакета на PyPI стоит ссылка `Documentation = https://bquant.readthedocs.io/`,
>   так что отставшие доки видит любой, кто пришёл с PyPI.
>
> **Если захочется убрать эту скрытую зависимость** — перецепить проект на RTD с GitLab на
> GitHub в панели RTD. Тогда написанное ниже станет правдой, и зеркала перестанут влиять
> на публикацию документации. Пока этого не сделано, читать раздел 5.2 как «войти через
> GitLab».


## 🚀 TL;DR (быстрое обновление)

1) Зависимости для доков (единый источник):
```bash
pip install -e .[docs]
```

2) Локальная сборка и просмотр:
```bash
python -m sphinx -b html docs docs/_build/html
# открыть docs/_build/html/index.html в браузере
```

3) Обновление API‑доков (ручные страницы):
- Обновите соответствующие файлы в `docs/api/` и навигацию в `docs/index.rst`.

4) Версионирование (при релизе):
- Обновите версии: `pyproject.toml` → `[project].version` и `bquant/__init__.py` →
  `__version__`; затем `uv lock` (лок хранит версию пакета третьим местом).
  **`docs/conf.py` руками не трогать** — с 0.0.5 он берёт версию из пакета
  (`from bquant import __version__ as release`). До этого он четыре релиза подряд
  молча стоял на `0.0.1`, потому что его надо было обновлять вручную.
- Создайте и запушьте тег:
```bash
git tag -a vX.Y.Z -m "..."
git push origin vX.Y.Z   # origin = оба зеркала; для пересборки доков нужен GitLab
```

5) Read the Docs:
- Для «latest» — `git push` в основную ветку, RTD пересоберёт автоматически.
- Логи и ручной Rebuild — в панели RTD → Builds.

## 📚 Обзор

Это руководство описывает полный процесс создания, настройки и публикации документации BQuant на Read the Docs, включая локальную разработку, автогенерацию API, версионирование и частые проблемы.

## 🎯 Что мы создаём

- **Автоматическую сборку документации** на Read the Docs
- **Локальную разработку** документации
- **Интеграцию с GitHub** для автоматических обновлений
- **Профессиональную документацию** с поиском, навигацией и мобильной версией

## 🛠️ Инструменты и технологии

### Основные инструменты:
- **Sphinx** - генератор документации
- **Read the Docs** - хостинг документации
- **GitHub** - хранение кода и автоматизация
- **Python** - среда выполнения

### Дополнительные инструменты:
- **sphinx-rtd-theme** - современная тема оформления
- **myst-parser** - поддержка Markdown
- **sphinx-copybutton** - кнопки копирования кода
- **sphinx-autodoc-typehints** - автоматическая документация типов

## 📁 Структура файлов в проекте

```
bquant_project/
├── docs/                          # Папка документации
│   ├── conf.py                    # Конфигурация Sphinx
│   ├── index.rst                  # Главная страница
│   ├── Makefile                   # Команды сборки
│   ├── _static/                   # Статические файлы (CSS, JS, изображения)
│   ├── _templates/                # Шаблоны
│   ├── api/                       # API документация
│   ├── user_guide/                # Руководство пользователя
│   ├── tutorials/                 # Обучающие материалы
│   ├── examples/                  # Примеры использования
│   └── developer_guide/           # Руководство разработчика
├── .readthedocs.yml              # Конфигурация Read the Docs (python 3.11, extras docs)
├── pyproject.toml                # Зависимости проекта (включая docs)
├── requirements.txt              # Основные зависимости
└── SETUP_READTHEDOCS.md          # Это руководство
```

## 🚀 Пошаговая настройка

### Шаг 1: Подготовка проекта

#### 1.1 Создание структуры документации
```bash
# Создаем папку документации
mkdir docs
cd docs

# Инициализируем Sphinx
sphinx-quickstart
```

#### 1.2 Настройка конфигурации Sphinx (`docs/conf.py`)
```python
# Основные настройки
project = 'BQuant'
copyright = '2025, HorDa'
author = 'kogriv'
release = '0.0.1'

# Расширения
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'sphinx.ext.intersphinx',
    'sphinx.ext.mathjax',
    'sphinx_copybutton',
    'myst_parser',
]

# Тема
html_theme = 'sphinx_rtd_theme'
```

#### 1.3 Зависимости для документации (единый источник)
```toml
[project.optional-dependencies]
docs = [
    "sphinx>=7.0.0",
    "sphinx-rtd-theme>=2.0.0",
    "sphinx-copybutton>=0.5.0",
    "myst-parser>=2.0.0",
    "sphinx-autodoc-typehints>=1.25.0",
]
```
Устанавливайте так:
```bash
pip install -e .[docs]
```

### Шаг 2: Конфигурация Read the Docs

#### 2.1 Создание `.readthedocs.yml`
```yaml
version: 2

build:
  os: ubuntu-22.04
  tools:
    python: "3.11"

sphinx:
  configuration: docs/conf.py

python:
  install:
    - method: pip
      path: .
      extra_requirements:
        - docs
```

#### 2.2 Объяснение параметров:
- **`version: 2`** - версия конфигурации Read the Docs
- **`build.os`** - операционная система для сборки
- **`build.tools.python`** - версия Python
- **`sphinx.configuration`** - путь к конфигурации Sphinx
- **`python.install`** - способ установки зависимостей

### Шаг 3: Создание контента документации

#### 3.1 Главная страница (`docs/index.rst`)
```rst
BQuant Documentation
===================

Добро пожаловать в документацию BQuant!

.. toctree::
   :maxdepth: 2
   :caption: Содержание:

   user_guide/index
   api/index
   tutorials/index
   examples/index
   developer_guide/index

Индексы и таблицы
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
```

#### 3.2 Структура разделов:
- **`user_guide/`** - руководство пользователя
- **`api/`** - справочник API
- **`tutorials/`** - обучающие материалы
- **`examples/`** - примеры использования
- **`developer_guide/`** - руководство разработчика

### Шаг 4: Локальная разработка

#### 4.1 Установка зависимостей
```bash
pip install -e .[docs]
```

#### 4.2 Сборка документации локально
```bash
python -m sphinx -b html docs docs/_build/html

# Просмотр результата
# Открыть docs/_build/html/index.html в браузере
```

Если нет доступа к файлу. Возможна проблема с правами доступа или форматом пути.  
Вариант 1: HTTP сервер (рекомендуется)Ж
```bash
cd /data/pro/bquant/docs/_build/html
python3 -m http.server 8000
```
Затем откройте в браузере:  
http://localhost:8000/api/core/README.html  
http://localhost:8000/index.html


#### 4.3 Автоматическая пересборка при изменениях
```bash
# Установка sphinx-autobuild
pip install sphinx-autobuild

# Запуск с автоматической пересборкой
# sphinx-autobuild docs docs/_build/html --open-browser
sphinx-autobuild docs docs/_build/html --port 8000
```

Разница между опциями:
--port 8000 — указывает порт (по умолчанию 8000)
Без этой опции sphinx-autobuild использует порт 8000 по умолчанию
Можно указать другой порт: --port 9000
--open-browser — автоматически открывает браузер после сборки
Открывает http://localhost:PORT в браузере
Работает только если запущено в интерактивном режиме (не в фоне)
Они не взаимоисключающие — можно использовать вместе:
```bash
sphinx-autobuild docs docs/_build/html --port 8000 --open-browser
```
Что лучше использовать:
Для разработки (с автопересборкой):
```bash
sphinx-autobuild docs docs/_build/html --port 8000 --open-browser
```
Для простого просмотра (без автопересборки):
```bash
cd docs/_build/html && python3 -m http.server 8000
```

Как останавливать серверы:
```bash
cat << 'EOF'
# Остановка sphinx-autobuild:
pkill -f sphinx-autobuild

# Или найти PID и убить:
ps aux | grep sphinx-autobuild | grep -v grep
kill <PID>

# Остановка простого HTTP-сервера Python:
pkill -f "python.*http.server"

# Или найти PID и убить:
ps aux | grep "http.server" | grep -v grep
kill <PID>

# Остановка всех процессов на порту 8000:
lsof -ti:8000 | xargs kill 2>/dev/null
# или
fuser -k 8000/tcp 2>/dev/null
EOF

ps aux | grep -E "(http.server|sphinx-autobuild)" | grep -v grep | awk '{print "PID:", $2, "| Команда:", $11, $12, $13, $14}'
# PID: 1094597 | Команда: /data/pro/bquant/venv_bquant/bin/python3 /data/pro/bquant/venv_bquant/bin/sphinx-autobuild docs docs/_build/html
```
Способы остановки:
1. Остановка sphinx-autobuild:
```bash
# Самый простой способ:
pkill -f sphinx-autobuild

# Или по PID (если знаете):
kill 1094597
```
2. Остановка простого HTTP-сервера Python:
```bash
# Остановить все процессы http.server:
pkill -f "python.*http.server"

# Или по порту:
lsof -ti:8000 | xargs kill
```
3. Универсальный способ (остановить все на порту):
```bash
# Найти и убить процесс на порту 8000:
fuser -k 8000/tcp

# Или через lsof:
lsof -ti:8000 | xargs kill -9
```
4. Если запущено в интерактивном режиме:
Нажмите Ctrl+C в терминале, где запущен сервер
Рекомендация:
Для разработки документации используйте:
```bash
sphinx-autobuild docs docs/_build/html --port 8000 --open-browser
```

### Шаг 5: Настройка на Read the Docs

#### 5.1 Подготовка репозитория
```bash
# Добавление файлов в Git
git add .
git commit -m "Add documentation configuration"
git push origin main
```

#### 5.2 Импорт проекта на Read the Docs
1. Перейти на [readthedocs.org](https://readthedocs.org)
2. Войти через GitLab (см. врезку в начале файла — проект импортирован оттуда)
3. Нажать "Import a Project"
4. Выбрать репозиторий `bquant`
5. Read the Docs автоматически обнаружит `.readthedocs.yml`

#### 5.3 Проверка настроек
- **Project name**: `bquant`
- **Documentation type**: `Sphinx`
- **Configuration file**: `.readthedocs.yml`
- **Python version**: `3.11`

### Шаг 6: Тестирование и отладка

#### 6.1 Проверка сборки
1. Перейти в проект на Read the Docs
2. Проверить логи сборки в разделе "Builds"
3. Исправить ошибки, если есть

#### 6.2 Частые проблемы и решения:

**Проблема**: "Config validation error"
```yaml
# Решение: упростить конфигурацию
version: 2
sphinx:
  configuration: docs/conf.py
python:
  install:
    - method: pip
      path: .
      extra_requirements:
        - docs
```

**Проблема**: "Python version conflict"
```toml
# В pyproject.toml
requires-python = ">=3.11"
```

**Проблема**: "Missing dependencies"
```toml
# Добавить в [project.optional-dependencies]
docs = [
    "sphinx>=7.0.0",
    "sphinx-rtd-theme>=2.0.0",
    # ... другие зависимости
]
```

## 📝 Работа с документацией

### Добавление новых страниц

#### 1. Создание файла
```bash
# Создать новый файл
touch docs/user_guide/new_feature.md
```

#### 2. Добавление в навигацию
```rst
# В docs/user_guide/index.rst
.. toctree::
   :maxdepth: 2

   quick_start
   new_feature
```

#### 3. Написание контента
```markdown
# Новый функционал

Описание нового функционала...

## Использование

```python
from bquant import new_feature
result = new_feature.do_something()
```
```

### Обновление API документации (ручной подход)

1. Обновляйте страницы в `docs/api/` вручную: поддерживайте актуальные списки модулей, классов и функций, примеры кода, ссылки.
2. При необходимости можно встраивать `autodoc` фрагменты точечно в Markdown через MyST:
```md
:::{eval-rst}
.. automodule:: bquant.core.utils
   :members:
   :undoc-members:
:::
```
3. После правок соберите и проверьте локально.

> Примечание: автоматическая генерация целого раздела API отключена по умолчанию, см. раздел ниже как опцию.

### Добавление примеров кода

#### 1. Создание файла примера
```python
# docs/examples/basic_usage.py
import bquant as bq

# Пример использования
data = bq.data.load_sample_data()
result = bq.analysis.macd_analysis(data)
print(result)
```

#### 2. Включение в документацию
```rst
.. literalinclude:: examples/basic_usage.py
   :language: python
   :caption: Базовый пример использования
```

## 🔄 Обновление документации

### Автоматическое обновление (latest)
1. Внести изменения в документацию
2. Закоммитить и запушить в GitHub
3. Read the Docs автоматически пересоберет документацию

### Ручное обновление / Rebuild
1. Перейти в проект на Read the Docs
2. Нажать "Build Version"
3. Выбрать ветку или тег

### Версионирование документации
```bash
# Создание тега для версии
git tag v0.0.1
git push origin v0.0.1

# Read the Docs автоматически создаст версию документации
```
Где менять версии перед релизом:
- `pyproject.toml` → `[project].version = "X.Y.Z"`
- `docs/conf.py` → `release = "X.Y.Z"`
- `bquant/__init__.py` → `__version__ = "X.Y.Z"`

## 🎨 Кастомизация

### Изменение темы
```python
# В docs/conf.py
html_theme = 'sphinx_rtd_theme'

html_theme_options = {
    'navigation_depth': 4,
    'titles_only': False,
    'collapse_navigation': False,
    'sticky_navigation': True,
}
```

### Добавление CSS
```css
/* docs/_static/custom.css */
.wy-nav-content {
    max-width: 1200px;
}
```

```python
# В docs/conf.py
def setup(app):
    app.add_css_file('custom.css')
```

### Настройка поиска
```python
# В docs/conf.py
html_use_index = True
html_split_index = False
html_search_language = 'en'
```

## 📊 Мониторинг и аналитика

### Статистика использования
- Read the Docs предоставляет статистику просмотров
- Можно подключить Google Analytics
- Отслеживание поисковых запросов

### Уведомления
- Email уведомления о неудачных сборках
- Интеграция с Slack/Discord
- Webhook уведомления

## 🔧 Продвинутые настройки

### (Опционально) Автогенерация API раздела

Автогенерация полезна, если нужно быстро покрыть много модулей без ручного описания.

Преимущества:
- Быстрое покрытие всего дерева модулей;
- Меньше ручной рутины при изменениях структуры;
- Единый стиль для всех страниц.

Сложности:
- Меньше контроля над качеством текста (docstring ≠ документация);
- Нужно избегать перетирания ручных страниц;
- Возможна необходимость коммитить сгенерированные файлы или настраивать генерацию на билде RTD.

Быстрый старт (если решите включить):
```bash
sphinx-apidoc -o docs/api/autogen bquant --force
```
Добавьте в навигацию, например, в `docs/index.rst`:
```rst
.. toctree::
   :maxdepth: 2

   api/README
   api/autogen/index
```
Альтернатива — генерировать на лету на RTD (добавив команду генерации перед сборкой) и не коммитить `autogen` в репозиторий.

### Интеграция с CI/CD
```yaml
# .github/workflows/docs.yml
name: Build Documentation
on: [push, pull_request]
jobs:
  build-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build docs
        run: |
          pip install -e .[docs]
          cd docs && make html
```

### Автоматическая проверка ссылок (локально)
```bash
# Установка linkchecker
pip install linkchecker

# Проверка ссылок
sphinx-build -b linkcheck docs docs/_build/linkcheck
```

## 🎉 Результат

После успешной настройки вы получите:

- ✅ **Профессиональную документацию** на `https://bquant.readthedocs.io/`
- ✅ **Автоматическую сборку** при каждом коммите
- ✅ **Версионирование** документации
- ✅ **Поиск** по всей документации
- ✅ **Мобильную версию**
- ✅ **Интеграцию с GitHub**

## 🔗 Полезные ссылки

- [Read the Docs Documentation](https://docs.readthedocs.io/)
- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [sphinx-rtd-theme](https://sphinx-rtd-theme.readthedocs.io/)
- [MyST Parser](https://myst-parser.readthedocs.io/)
- [GitHub Repository](https://github.com/kogriv/bquant)
- [Live Documentation](https://bquant.readthedocs.io/)

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи сборки на Read the Docs
2. Убедитесь в корректности конфигурации
3. Проверьте совместимость версий
4. Обратитесь к документации инструментов
5. Создайте issue в репозитории проекта
