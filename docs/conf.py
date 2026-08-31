# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------

# Имя сайта совпадает с именем пакета. Прежнее — 'BQuant Zone Analysis' — осталось
# от времён, когда пакет был только про MACD-зоны; сейчас зоны это одна из областей,
# а `pyproject.toml` описывает пакет как quantitative research toolkit.
project = 'BQuant'
copyright = '2024–2026, BQuant'
author = 'BQuant'

# The full version, including alpha/beta/rc tags.
# Derived from the package rather than hardcoded: this was pinned at '0.0.1' through
# four releases because nothing tied it to the real version. `sys.path` already points
# at the repo root above, so this reads the working tree, not an installed copy.
from bquant import __version__ as release  # noqa: E402

# Язык контента. Объявлен явно: без него Sphinx считает сайт английским и подписывает
# навигацию по-английски поверх русского текста. Он же — точка входа для gettext, если
# дойдёт до второй языковой ветки (см. devref/architecture/docs_sequential_pass_2026-08.md).
language = 'ru'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
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

# Generate implicit anchors for headings up to level 4 so cross-document and
# in-page `file.md#heading-slug` links resolve (MyST slugifies heading text).
myst_heading_anchors = 4

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
    # `docs/README.md` — навигация по каталогу для того, кто читает репозиторий на
    # GitHub. На сайте её роль выполняют `index.rst` и боковое меню, поэтому в сборку
    # она не идёт.
    'README.md',
]

# Здесь стоял блок из двенадцати закомментированных строк под шапкой
# «ДИАГНОСТИКА: Исключаем все markdown файлы, кроме api/core/*.md». Фактически
# исключался один файл — всё остальное было закомментировано. Леса от давней
# диагностики убрали, шапку нет, и читатель конфига получал картину, обратную
# действительности. Ни одна из проверок доки этого не видела: они смотрят
# содержимое страниц, а не конфиг сборки.

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Своих статических файлов у сайта нет, поэтому `html_static_path` не объявляется.
# Здесь же стояли `html_logo = '_static/logo.png'` и `html_favicon = '_static/favicon.ico'`
# при том, что каталога `docs/_static/` не существует вовсе — сборка ругалась тремя
# предупреждениями на каждый прогон, а сайт всё это время был без логотипа. Вернуть,
# когда появятся сами файлы.

# -- Options for autodoc ----------------------------------------------------

# Automatically extract typehints when specified and place them in
# descriptions of the relevant function/method.
autodoc_typehints = "description"

# Don't show class signature with the class' name.
autodoc_class_signature = "separated"

# -- Options for napoleon ---------------------------------------------------

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None

# -- Options for intersphinx -------------------------------------------------

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/', None),
}

# -- Options for HTML output -------------------------------------------------

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    'navigation_depth': 4,
    'titles_only': False,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'logo_only': False,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
}

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    'papersize': 'a4paper',

    # The font size ('10pt', '11pt' or '12pt').
    'pointsize': '11pt',

    # Additional stuff for the LaTeX preamble.
    'preamble': r'''
        \usepackage{amsmath}
        \usepackage{amssymb}
    ''',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    ('index', 'BQuant.tex', 'BQuant Documentation',
     'BQuant Team', 'manual'),
]

# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bquant', 'BQuant Documentation',
     ['BQuant Team'], 1)
]

# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'BQuant', 'BQuant Documentation',
     'BQuant Team', 'BQuant', 'Quantitative analysis library for financial data.',
     'Miscellaneous'),
]

# -- Options for Epub output -------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
epub_identifier = 'https://github.com/kogriv/bquant'

# A unique identification for the text.
epub_uid = 'bquant-documentation'

# A list of files that should not be packed into the epub file.
epub_exclude_files = ['search.html']

# -- Extension configuration -------------------------------------------------

# Copy button configuration
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# -- Custom configuration ---------------------------------------------------

# Add any custom configuration here
def setup(app):
    app.add_css_file('custom.css')
