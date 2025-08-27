# Полное руководство по настройке документации BQuant

## 📚 Обзор

Это руководство описывает полный процесс создания, настройки и публикации документации для проекта BQuant на Read the Docs.

## 🎯 Что мы создаем

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
├── .readthedocs.yml              # Конфигурация Read the Docs
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

#### 1.3 Настройка зависимостей в `pyproject.toml`
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
# Установка зависимостей документации
pip install -e .[docs]

# Или установка из requirements.txt
pip install -r requirements.txt
```

#### 4.2 Сборка документации локально
```bash
cd docs

# Сборка HTML
make html

# Или через sphinx-build
sphinx-build -b html . _build/html

# Просмотр результата
# Открыть docs/_build/html/index.html в браузере
```

#### 4.3 Автоматическая пересборка при изменениях
```bash
# Установка sphinx-autobuild
pip install sphinx-autobuild

# Запуск с автоматической пересборкой
sphinx-autobuild docs docs/_build/html --open-browser
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
2. Войти через GitHub
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

### Обновление API документации

#### 1. Автоматическая генерация
```bash
# Генерация API документации
sphinx-apidoc -o docs/api bquant/
```

#### 2. Ручное добавление
```rst
# В docs/api/index.rst
.. automodule:: bquant.core
   :members:
   :undoc-members:
   :show-inheritance:
```

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

### Автоматическое обновление
1. Внести изменения в документацию
2. Закоммитить и запушить в GitHub
3. Read the Docs автоматически пересоберет документацию

### Ручное обновление
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

### Многоязычная документация
```yaml
# В .readthedocs.yml
sphinx:
  configuration: docs/conf.py
  fail_on_warning: false

formats:
  - pdf
  - epub
```

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

### Автоматическая проверка ссылок
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
- ✅ **Экспорт в PDF и ePub**
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
