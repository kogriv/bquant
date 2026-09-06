# BQuant Analysis Scripts

Скрипты для автоматизированного анализа финансовых данных с использованием BQuant.

## 📊 Доступные скрипты

### `run_macd_analysis.py`
Выполняет полный MACD анализ для указанного инструмента и таймфрейма.

**Использование:**
```bash
python run_macd_analysis.py XAUUSD 1h
python run_macd_analysis.py --symbol EURUSD --timeframe 15m --output results.json
```

**Функциональность:**
- Загрузка данных из sample data или внешних источников
- Расчет MACD и ATR индикаторов
- Идентификация MACD зон
- Анализ характеристик зон
- Генерация отчета в JSON/HTML формате

### `run_hypothesis_tests.py`
Запускает статистическое тестирование гипотез для MACD зон.

**Использование:**
```bash
python run_hypothesis_tests.py XAUUSD 1h
python run_hypothesis_tests.py --symbol EURUSD --timeframe 1h --tests duration,slope
```

**Функциональность:**
- Выполнение всех доступных статистических тестов
- Тест продолжительности зон
- Тест наклона гистограммы
- Тест асимметрии быка/медведя
- Тест последовательности паттернов
- Тест волатильности

### `batch_analysis.py`
Выполняет пакетный анализ для множества инструментов и таймфреймов.

**Использование:**
```bash
python batch_analysis.py --symbols XAUUSD,EURUSD --timeframes 1h,4h
python batch_analysis.py --config batch_config.yaml
```

**Функциональность:**
- Анализ множества символов параллельно
- Сравнительный анализ между инструментами
- Агрегированные отчеты
- Экспорт результатов в различных форматах

## 🔧 Конфигурация

### Переменные окружения
- `BQUANT_DATA_PATH` - путь к данным (опционально)
- `BQUANT_OUTPUT_PATH` - путь для сохранения результатов (по умолчанию: `./output`)

### Файлы конфигурации
- `analysis_config.yaml` - общие настройки анализа
- `batch_config.yaml` - конфигурация для пакетного анализа

## 📋 Примеры использования

### Быстрый анализ sample данных
```bash
# Анализ TradingView данных
python run_macd_analysis.py tv_xauusd_1h --sample-data

# Тестирование гипотез
python run_hypothesis_tests.py tv_xauusd_1h --sample-data
```

### Полный анализ с внешними данными
```bash
# Загрузка данных и анализ
python run_macd_analysis.py XAUUSD 1h --data-source tradingview --periods 1000

# Пакетный анализ золота на разных таймфреймах
python batch_analysis.py --symbols XAUUSD --timeframes 15m,1h,4h,1d
```

### Экспорт результатов
```bash
# JSON отчет
python run_macd_analysis.py XAUUSD 1h --output-format json --output-file analysis.json

# HTML отчет с графиками
python run_macd_analysis.py XAUUSD 1h --output-format html --include-charts
```

## 🧪 Тестирование

Для тестирования скриптов используйте sample данные:
```bash
# Тест основного функционала
python run_macd_analysis.py tv_xauusd_1h --sample-data --dry-run

# Тест всех статистических функций
python run_hypothesis_tests.py tv_xauusd_1h --sample-data --verbose
```

## 📖 Выходные форматы

### JSON
Структурированные данные для дальнейшей обработки:
```json
{
  "symbol": "XAUUSD",
  "timeframe": "1h",
  "analysis_date": "2025-08-25T18:46:00Z",
  "zones": [...],
  "statistics": {...},
  "performance": {...}
}
```

### HTML
Интерактивные отчеты с графиками и таблицами для презентации результатов.

### CSV
Табличные данные для анализа в Excel или других инструментах.

## 🛠️ Разработка

При добавлении новых скриптов анализа:
1. Используйте base класс `AnalysisScript` 
2. Реализуйте CLI интерфейс с argparse
3. Добавьте логирование и обработку ошибок
4. Создайте тесты в `tests/scripts/`
5. Обновите документацию

## 🔗 См. также

- [BQuant Core Documentation](../../bquant/README.md)
- [Sample Data Guide](../../bquant/data/samples/README.md)
- [Testing Guide](../../tests/README.md)
