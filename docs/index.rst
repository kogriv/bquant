BQuant Documentation
====================

BQuant — инструментарий количественного исследования финансовых рынков.
Ядро — универсальный пайплайн анализа зон: он не привязан к конкретному
индикатору и работает с любым осциллятором.

.. toctree::
   :maxdepth: 2
   :caption: API Reference
   
   api/README
   api/core/README
   api/core/config
   api/core/nb
   api/core/performance
   api/core/logging
   api/core/exceptions
   api/core/utils
   api/data/README
   api/data/loader
   api/data/processor
   api/data/samples
   api/data/validator
   api/data/schemas
   api/indicators/README
   api/indicators/base
   api/indicators/custom
   api/indicators/factory
   api/indicators/library_manager
   api/indicators/macd
   api/indicators/preloaded
   api/visualization/README
   api/visualization/zones
   api/analysis/README
   api/analysis/base
   api/analysis/zones
   api/analysis/pipeline
   api/analysis/strategies
   api/analysis/statistical
   api/analysis/zones/global_swings_models
   api/analysis/zones/global_swings_pipeline
   api/analysis/zones/global_swings_strategies
   api/extension_guide

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   
   user_guide/README
   user_guide/quick_start
   user_guide/cli
   user_guide/core_concepts
   user_guide/zone_analysis
   user_guide/zone_analysis_result
   user_guide/caching
   user_guide/best_practices
   user_guide/swing_strategies

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

   from bquant.data.samples import get_sample_data
   from bquant.analysis.zones import analyze_zones

   data = get_sample_data('tv_xauusd_1h')

   # Пайплайн не привязан к индикатору: меняется вызов `.with_indicator()`,
   # остальное остаётся тем же.
   result = (
       analyze_zones(data)
       .with_indicator('pandas_ta', 'rsi', length=14)
       .detect_zones('threshold', indicator_role='value',
                     upper_threshold=70, lower_threshold=30)
       .analyze(clustering=True)
       .build()
   )

   print(f"Найдено зон: {len(result.zones)}")          # 64
   print(sorted({zone.type for zone in result.zones}))  # ['neutral', 'overbought', 'oversold']

Зона адресуется **ролью** (``indicator_role='value'``), а не именем колонки.
Имя колонки зависит от библиотеки и параметров вызова и меняется вместе с ними;
роль — нет.

MACD-зоны в одну строку
-----------------------

.. code-block:: python

   from bquant.analysis.zones import analyze_macd_zones

   result = analyze_macd_zones(data)  # пресет поверх того же пайплайна

.. note::

   Класс ``MACDZoneAnalyzer`` (и обёртки ``create_macd_analyzer`` /
   ``analyze_macd_zones`` из ``bquant.indicators.macd``) **удалён** в 0.0.5.
   Замена — пресет выше либо полный билдер ``analyze_zones()``.
   Сам индикатор MACD не менялся.

Основные возможности
--------------------

* **Анализ зон** — универсальный пайплайн ``analyze_zones()``: пять способов
  детекции, пять групп метрик, любой индикатор
* **Данные** — загрузка, обработка и валидация OHLCV; встроенные наборы для
  примеров и тестов
* **Индикаторы** — встроенные, а также из ``pandas-ta`` и TA-Lib через единую фабрику
* **Статистика** — проверка гипотез и анализ распределений
* **Визуализация** — финансовые графики с настраиваемыми темами
* **Производительность** — векторизованные вычисления и двухуровневый кэш

Документация
------------

* :doc:`user_guide/README` - Руководство пользователя
* :doc:`api/README` - Справочник API
* :doc:`tutorials/README` - Обучающие материалы
* :doc:`examples/README` - Примеры использования
* :doc:`developer_guide/README` - Руководство разработчика

Поддержка
---------

* `GitHub Issues <https://github.com/kogriv/bquant/issues>`_ - Сообщения об ошибках
* `GitHub Discussions <https://github.com/kogriv/bquant/discussions>`_ - Обсуждения
* `PyPI Package <https://pypi.org/project/bquant/>`_ - Установка через pip

Лицензия
--------

BQuant распространяется под лицензией MIT. См. файл `LICENSE <https://github.com/kogriv/bquant/blob/main/LICENSE>`_ для подробностей.

Индексы и таблицы
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
