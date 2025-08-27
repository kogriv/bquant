"""
BQuant Integration Tests

Интеграционные тесты для проверки взаимодействия компонентов BQuant.

Содержит тесты для:
- Полного пайплайна MACD анализа
- Интеграции загрузки и обработки данных
- Интеграции визуализации
- Интеграции скриптов анализа
"""

# Integration test modules
from .test_full_pipeline import *
from .test_data_pipeline import *
from .test_visualization_pipeline import *
from .test_scripts_integration import *
