BQuant Documentation
===================

Версия документации по состоянию на 2026-01-12 чт.

.. toctree::
   :maxdepth: 2
   :caption: API Reference
   
   api/README
   api/core/README
   api/data/README
   api/indicators/README
   api/visualization/README
   api/analysis/README
   api/analysis/base
   api/extension_guide

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   
   user_guide/README
   user_guide/quick_start
   user_guide/core_concepts
   user_guide/zone_analysis
   user_guide/caching
   user_guide/best_practices
   user_guide/swing_strategies
   user_guide/swing_analysis_results

.. toctree::
   :maxdepth: 2
   :caption: Tutorials
   
   tutorials/README
   tutorials/macd_basic_pipeline
   tutorials/rsi_strategy_switching
   tutorials/preloaded_zones_workflow
   tutorials/combined_rules_detection

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide
   
   developer_guide/README
   developer_guide/zone_analyzer_deep_dive
   developer_guide/zone_detection_strategies
   developer_guide/statistical_analysis_workflow
   developer_guide/analytical_philosophy

.. toctree::
   :maxdepth: 2
   :caption: Examples
   
   examples/README

.. toctree::
   :maxdepth: 2
   :caption: Analytics
   
   analytics/zones/swing
   analytics/zones/macd_zone_consistency_case_study
   analytics/zones/swing_strategy_comparison_case_study

.. toctree::
   :maxdepth: 2
   :caption: Migration
   
   migration/MIGRATION_v2
   migration/global_swings_migration

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
