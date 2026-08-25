#!/usr/bin/env python3
"""
Демонстрация профилей логирования BQuant

Этот скрипт показывает, как работают различные предустановленные профили:
- research: скрывает технические детали data модулей
- clean: минимальный вывод (только ERROR+)
- debug: максимальная детализация
- verbose: DEBUG везде
- focused: DEBUG для core, INFO для остальных
- critical: только критические события
- audit: полное логирование в файл, минимум в консоль
"""

from bquant.core.logging_config import setup_logging
from bquant.core.nb import NotebookSimulator

def demo_profile(profile_name, description):
    """Демонстрация работы конкретного профиля"""
    print(f"\n{'='*60}")
    print(f"🎯 ПРОФИЛЬ: {profile_name.upper()}")
    print(f"📝 Описание: {description}")
    print(f"{'='*60}")
    
    # Настройка логирования с указанным профилем
    setup_logging(profile=profile_name)
    
    # Создаем NotebookSimulator для пользовательских сообщений
    nb = NotebookSimulator(f"Демо профиля {profile_name}")
    
    # Пользовательские сообщения (всегда видны)
    nb.info(f"Запуск демонстрации профиля '{profile_name}'")
    
    # Импортируем модули для демонстрации технических логов
    from bquant.data.loader import load_ohlcv_data
    # Модуль `indicators/macd.py` удалён вместе с MACDZoneAnalyzer (0.0.5);
    # функция живёт в `calculators`.
    from bquant.indicators.calculators import calculate_macd
    from bquant.analysis.zones import find_support_resistance
    
    # Демонстрация загрузки данных
    nb.step("Загрузка тестовых данных")
    try:
        # Попытка загрузить несуществующий файл для демонстрации WARNING/ERROR
        data = load_ohlcv_data('nonexistent_file.csv', 'XAUUSD', '1h')
        nb.success("Данные загружены успешно")
    except Exception as e:
        nb.warning(f"Предупреждение при загрузке: {e}")
    
    # Демонстрация расчета индикаторов
    nb.step("Расчет MACD")
    try:
        # Создаем тестовые данные
        import pandas as pd
        import numpy as np
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        test_data = pd.DataFrame({
            'close': np.random.randn(100).cumsum() + 100
        }, index=dates)
        
        macd_result = calculate_macd(test_data)
        nb.success("MACD рассчитан успешно")
    except Exception as e:
        nb.error(f"Ошибка расчета MACD: {e}")
    
    # Демонстрация анализа зон
    nb.step("Анализ зон")
    try:
        # Создаем тестовые OHLCV данные для анализа зон
        test_ohlcv = pd.DataFrame({
            'open': np.random.randn(100).cumsum() + 100,
            'high': np.random.randn(100).cumsum() + 101,
            'low': np.random.randn(100).cumsum() + 99,
            'close': np.random.randn(100).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
        
        zones_result = find_support_resistance(test_ohlcv)
        nb.success(f"Анализ зон завершен, найдено {len(zones_result)} зон")
    except Exception as e:
        nb.error(f"Ошибка анализа зон: {e}")
    
    nb.success(f"Демонстрация профиля '{profile_name}' завершена")
    print(f"✅ Профиль '{profile_name}' продемонстрирован")

def main():
    """Основная функция демонстрации"""
    print("🚀 ДЕМОНСТРАЦИЯ ПРОФИЛЕЙ ЛОГИРОВАНИЯ BQUANT")
    print("=" * 60)
    
    # Список профилей для демонстрации
    profiles = [
        ('research', 'Скрывает технические детали data модулей (WARNING+ в консоль)'),
        ('clean', 'Минимальный вывод (ERROR+ в консоль)'),
        ('debug', 'Отладочный режим (DEBUG+ везде)'),
        ('verbose', 'Максимальная детализация (DEBUG+ везде)'),
        ('focused', 'DEBUG для core, INFO для остальных'),
        ('critical', 'Только критические события (ERROR+)'),
        ('audit', 'Полное логирование в файл, минимум в консоль')
    ]
    
    # Демонстрация каждого профиля
    for profile_name, description in profiles:
        demo_profile(profile_name, description)
    
    print(f"\n{'='*60}")
    print("🎉 ДЕМОНСТРАЦИЯ ВСЕХ ПРОФИЛЕЙ ЗАВЕРШЕНА")
    print("=" * 60)
    print("💡 Теперь вы можете выбрать подходящий профиль для вашего сценария!")
    print("📚 Подробности в документации: docs/api/core/logging.md")

if __name__ == "__main__":
    main()
