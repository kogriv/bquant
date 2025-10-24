BQuant Documentation
===================

.. image:: _static/logo.png
   :alt: BQuant Logo
   :width: 200px
   :align: center

**Мощная библиотека для количественного анализа финансовых данных**

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   
   user_guide/quick_start
   user_guide/README

.. toctree::
   :maxdepth: 2
   :caption: API Reference
   
   api/analysis/pipeline
   api/analysis/strategies
   api/analysis/statistical
   api/indicators/README
   api/visualization/README

.. toctree::
   :maxdepth: 2
   :caption: Tutorials & Examples
   
   tutorials/README
   examples/README

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide
   
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

Первый пример - Universal Zone Analysis
----------------------------------------

.. code-block:: python

   import bquant as bq
   from bquant.data.samples import get_sample_data
   from bquant.analysis.zones import analyze_zones

   # Загружаем sample данные
   data = get_sample_data('tv_xauusd_1h')

   # Universal Pipeline - работает с любым индикатором
   result = (
       analyze_zones(data)
       .with_indicator('pandas_ta', 'rsi', length=14)
       .detect_zones('threshold', indicator_col='rsi', 
                     upper_threshold=70, lower_threshold=30)
       .analyze(clustering=True)
       .build()
   )

   # Выводим результаты
   print(f"Найдено зон: {len(result.zones)}")
   print(f"Статистика: {result.statistics}")

Legacy MACD Wrapper (Deprecated)
--------------------------------

.. code-block:: python

   # ⚠️ DEPRECATED: Используйте analyze_zones() вместо этого
   from bquant.indicators import MACDZoneAnalyzer
   
   analyzer = MACDZoneAnalyzer()  # Deprecated wrapper
   result = analyzer.analyze_complete(data)  # Delegates to analyze_zones()

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
