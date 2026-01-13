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

project = 'BQuant Zone Analysis'
copyright = '2025, BQuant Team'
author = 'BQuant Team'

# The full version, including alpha/beta/rc tags
release = '0.0.1'

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

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    '_build', 
    'Thumbs.db', 
    '.DS_Store',
    # ДИАГНОСТИКА: Исключаем все markdown файлы, кроме api/core/*.md
    # Явно перечисляем все markdown файлы для исключения (Sphinx не поддерживает отрицательные паттерны)
    # 'analytics/**',  # Разрешаем analytics/*.md
    # 'api/analysis/**',  # Разрешаем api/analysis/*.md
    # 'api/data/**',  # Разрешаем api/data/*.md
    # 'api/extension_guide.md',  # Разрешаем api/extension_guide.md
    # 'api/indicators/**',  # Разрешаем api/indicators/*.md
    # 'api/README.md',  # Разрешаем api/README.md
    # 'api/visualization/**',  # Разрешаем api/visualization/*.md
    'BUILD_ISSUES.md',
    # 'developer_guide/**',  # Разрешаем developer_guide/*.md
    # 'examples/**',  # Разрешаем examples/*.md
    # 'migration/**',  # Разрешаем migration/*.md
    # 'MIGRATION_v2.md',  # Перенесен в migration/
    'README.md',
    # 'tutorials/**',  # Разрешаем tutorials/*.md
    # 'user_guide/**',  # Разрешаем user_guide/*.md
    # api/core/*.md НЕ исключаем - они должны быть в сборке
]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

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
    # 'display_version': True,  # Временно отключено - не поддерживается в текущей версии темы
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
}

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = '_static/logo.png'

# The name of an image file (relative to this directory) to use as a favicon of
# the docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = '_static/favicon.ico'

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
epub_identifier = 'https://github.com/your-username/bquant'

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
