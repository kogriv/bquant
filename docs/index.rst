BQuant Documentation
===================

.. image:: _static/logo.png
   :alt: BQuant Logo
   :width: 200px
   :align: center

**Мощная библиотека для количественного анализа финансовых данных**

.. toctree::
   :maxdepth: 2
   :caption: Содержание:

   README
   user_guide/README
   api/README
   tutorials/README
   examples/README
   developer_guide/README

.. raw:: html

   <div class="admonition note">
   <p class="admonition-title">Быстрый старт</p>
   <p>Начните с <a href="user_guide/quick_start.html">Quick Start Guide</a> для быстрого знакомства с BQuant.</p>
   </div>

Установка
---------

.. code-block:: bash

   pip install bquant

Первый пример
-------------

.. code-block:: python

   import bquant as bq
   from bquant.data.samples import get_sample_data
   from bquant.indicators import MACDZoneAnalyzer

   # Загружаем sample данные
   data = get_sample_data('tv_xauusd_1h')

   # Создаем анализатор MACD
   analyzer = MACDZoneAnalyzer()

   # Выполняем полный анализ
   result = analyzer.analyze_complete(data)

   # Выводим результаты
   print(f"Найдено зон: {len(result.zones)}")
   print(f"Статистика: {result.statistics}")

Основные возможности
-------------------

* **📊 Анализ данных** - Загрузка, обработка и валидация OHLCV данных
* **📈 Технические индикаторы** - MACD с анализом зон и расширяемая архитектура
* **🔬 Статистический анализ** - Гипотезное тестирование и анализ распределений
* **📊 Визуализация** - Финансовые графики с настраиваемыми темами
* **⚡ Производительность** - NumPy-оптимизированные алгоритмы и кэширование

Документация
------------

* :doc:`user_guide/README` - Руководство пользователя
* :doc:`api/README` - Справочник API
* :doc:`tutorials/README` - Обучающие материалы
* :doc:`examples/README` - Примеры использования
* :doc:`developer_guide/README` - Руководство разработчика

Поддержка
---------

* `GitHub Issues <https://github.com/your-username/bquant/issues>`_ - Сообщения об ошибках
* `GitHub Discussions <https://github.com/your-username/bquant/discussions>`_ - Обсуждения
* `PyPI Package <https://pypi.org/project/bquant/>`_ - Установка через pip

Лицензия
--------

BQuant распространяется под лицензией MIT. См. файл `LICENSE <https://github.com/your-username/bquant/blob/main/LICENSE>`_ для подробностей.

Индексы и таблицы
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
