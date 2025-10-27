# Импорт основных библиотек
pd = None
talib = None
ta = None

try:
    import pandas as pd  # type: ignore[assignment]
    print("Pandas импортирован успешно!")
except ImportError:
    print("Ошибка: Pandas не установлен!")

try:
    import talib  # type: ignore[assignment]
    print("TA-Lib импортирован успешно!")
    # Проверим доступные функции TA-Lib
    print(f"Доступные функции TA-Lib: {len(talib.get_functions())}")
except ImportError:
    talib = None
    print("Ошибка: TA-Lib не установлен!")

try:
    import pandas_ta as ta  # type: ignore[assignment]
    print("Pandas_TA импортирован успешно!")
except ImportError:
    ta = None
    print("Ошибка: Pandas_TA не установлен!")

# Пример создания тестового датафрейма
if pd is None:
    print("Пропускаем демонстрацию: Pandas недоступен")
else:
    # Создаем простой датафрейм с тестовыми данными
    data = {
        'open': [100, 101, 102, 103, 104],
        'high': [105, 106, 107, 108, 109],
        'low': [95, 96, 97, 98, 99],
        'close': [102, 103, 104, 105, 106],
        'volume': [1000, 1500, 2000, 2500, 3000]
    }
    df = pd.DataFrame(data)

    if talib is not None:
        df['SMA'] = talib.SMA(df['close'], timeperiod=3)
        print("\nТестовый датафрейм с SMA от TA-Lib:")
        print(df)
    else:
        print("\nTA-Lib недоступен: пропускаем демонстрацию SMA")

    if ta is not None:
        df_ta = df.ta.sma(length=3)
        print("\nРезультат работы pandas_ta:")
        print(df_ta)
    else:
        print("\nPandas_TA недоступен: пропускаем расчёт SMA")
