# Импорт основных библиотек
try:
    import pandas as pd
    print("Pandas импортирован успешно!")
except ImportError:
    print("Ошибка: Pandas не установлен!")

try:
    import talib
    print("TA-Lib импортирован успешно!")
    # Проверим доступные функции TA-Lib
    print(f"Доступные функции TA-Lib: {len(talib.get_functions())}")
except ImportError:
    print("Ошибка: TA-Lib не установлен!")

try:
    import pandas_ta as ta
    print("Pandas_TA импортирован успешно!")
except ImportError:
    print("Ошибка: Pandas_TA не установлен!")

# Пример создания тестового датафрейма
try:
    # Создаем простой датафрейм с тестовыми данными
    data = {
        'open': [100, 101, 102, 103, 104],
        'high': [105, 106, 107, 108, 109],
        'low': [95, 96, 97, 98, 99],
        'close': [102, 103, 104, 105, 106],
        'volume': [1000, 1500, 2000, 2500, 3000]
    }
    df = pd.DataFrame(data)
    
    # Проверяем работу TA-Lib
    df['SMA'] = talib.SMA(df['close'], timeperiod=3)
    print("\nТестовый датафрейм с SMA:")
    print(df)
    
    # Проверяем работу pandas_ta
    df_ta = df.ta.sma(length=3)
    print("\nРезультат работы pandas_ta:")
    print(df_ta)
    
except Exception as e:
    print(f"Ошибка при работе с данными: {e}")
