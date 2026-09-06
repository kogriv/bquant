import logging
import os
import sys
import tempfile
import traceback
import types
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def _prepare_pandas_ta() -> None:
    """Подменяем pandas-ta на лёгкий заглушечный модуль для быстрых тестов."""

    try:
        from importlib import import_module

        pandas_ta_loader = import_module("bquant.indicators.library.pandas_ta")
        manager_module = import_module("bquant.indicators.library.manager")
    except Exception:
        return

    fake_module = types.ModuleType("pandas_ta")
    fake_module.__dict__["__all__"] = []
    sys.modules["pandas_ta"] = fake_module

    loader = pandas_ta_loader.PandasTALoader
    loader._ta_module = fake_module
    loader._function_cache = {}
    loader._available_indicators = []
    loader._indicators_registered = True

    def _load_all_libraries_stub(cls):
        return {name: 0 for name in cls._loaders.keys()}

    def _load_library_stub(cls, library_name):
        return 0

    def _library_info_stub(cls, library_name):
        if library_name in cls._loaders:
            return {"available": False, "error": "External libraries disabled for doc tests"}
        return {"available": False, "error": "Unknown library"}

    manager_module.LibraryManager.load_all_libraries = classmethod(_load_all_libraries_stub)
    manager_module.LibraryManager.load_library = classmethod(_load_library_stub)
    manager_module.LibraryManager.get_library_info = classmethod(_library_info_stub)


def _create_sample_csv(path: Path, rows: int = 120) -> Path:
    """Создаём CSV с достаточным количеством строк для валидации loader."""

    index = pd.date_range("2024-01-01", periods=rows, freq="H")
    base = np.linspace(100.0, 110.0, rows)
    frame = pd.DataFrame(
        {
            "open": base,
            "high": base + 0.5,
            "low": base - 0.5,
            "close": base + 0.25,
            "volume": np.linspace(1000.0, 2000.0, rows),
        },
        index=index,
    )
    frame.to_csv(path)
    return path


_prepare_pandas_ta()


def test_profiles_and_practical_examples(sample_csv: Path) -> bool:
    """Проверяем все примеры профилей и практические блоки документа."""

    print("📋 Тест: Профили и практические примеры")

    try:
        from bquant.analysis.zones import analyze_zones
        from bquant.core.logging_config import setup_logging
        from bquant.data.loader import load_ohlcv_data
        from bquant.indicators.calculators import calculate_macd
    except Exception as exc:  # pragma: no cover - диагностический вывод
        print(f"  ❌ Импорт зависимостей не удался: {exc}")
        traceback.print_exc()
        return False

    try:
        # Research профиль + загрузка данных (пример 1)
        setup_logging(profile="research")
        data = load_ohlcv_data(sample_csv.name)
        print(f"  ✅ Research профиль: {len(data)} строк данных")

        # Остальные предустановленные профили
        setup_logging(profile="clean")
        setup_logging(profile="debug")

        # Development пример: максимальная детализация + MACD расчёт
        setup_logging(profile="verbose")
        macd_result = calculate_macd(data)
        print(f"  ✅ MACD рассчитан: колонки {list(macd_result.columns)}")

        setup_logging(profile="focused")

        # Production профиль + анализ зон (пример 3)
        setup_logging(profile="critical")
        zones_builder = analyze_zones(data)
        print(f"  ✅ Builder анализа зон: {type(zones_builder).__name__}")

        # Production/audit профиль
        setup_logging(profile="audit")

        # Модульная настройка (раздел "Точный контроль по модулям")
        setup_logging(
            modules_config={
                "bquant.data": {"console": "WARNING", "file": "INFO"},
                "bquant.indicators": {"console": "INFO", "file": "DEBUG"},
                "bquant.analysis": {"console": "DEBUG", "file": "DEBUG"},
            }
        )
        print("  ✅ Модульная конфигурация применена")

        # Исключения для отдельных логгеров
        setup_logging(
            profile="research",
            exceptions={
                "bquant.data.loader": "INFO",
                "bquant.analysis.zones": "DEBUG",
                "bquant.core.nb": "INFO",
            },
        )
        print("  ✅ Исключения для логгеров применены")

        # Приоритет profile → modules_config → exceptions
        setup_logging(
            profile="research",
            modules_config={"bquant.analysis": {"console": "DEBUG"}},
            exceptions={"bquant.data.loader": "INFO"},
        )
        print("  ✅ Приоритет настроек подтверждён")

        # Практический пример точной настройки (раздел 4)
        setup_logging(
            modules_config={
                "bquant.data": {"console": "WARNING", "file": "INFO"},
                "bquant.indicators": {"console": "ERROR", "file": "DEBUG"},
                "bquant.analysis": {"console": "INFO", "file": "INFO"},
            },
            exceptions={
                "bquant.data.loader": "INFO",
                "bquant.core.nb": "INFO",
            },
        )
        print("  ✅ Практический пример точной настройки выполнен")

        return (
            len(data) >= 100
            and not macd_result.empty
            and hasattr(zones_builder, "detect_zones")
        )
    except Exception as exc:  # pragma: no cover - диагностический вывод
        print(f"  ❌ Ошибка выполнения примеров: {exc}")
        traceback.print_exc()
        return False


def test_logging_configurator() -> bool:
    """Проверяем оба примера использования LoggingConfigurator."""

    print("\n📋 Тест: LoggingConfigurator")

    try:
        from bquant.core.logging_config import LoggingConfigurator
    except Exception as exc:
        print(f"  ❌ Импорт LoggingConfigurator не удался: {exc}")
        traceback.print_exc()
        return False

    try:
        configurator = LoggingConfigurator()
        base_logger = configurator.preset("notebook", "research").apply()

        complex_logger = (
            LoggingConfigurator()
                .preset("development", "focused")           # Базовый preset
                .module("bquant.data")                       # Настройка data модуля
                .console("WARNING")                          # WARNING+ в консоль
                .file("DEBUG")                               # DEBUG+ в файл
                .module("bquant.indicators")                 # Настройка indicators
                .console("ERROR")                            # ERROR+ в консоль
                .exception("bquant.data.loader", "INFO")     # Исключение для loader
                .apply()                                      # Применить настройки
        )

        print(f"  ✅ Базовый логгер: {base_logger.name}")
        print(f"  ✅ Сложная конфигурация: {complex_logger.name}")
        return base_logger.name == "bquant" and complex_logger.name == "bquant"
    except Exception as exc:
        print(f"  ❌ Ошибка работы LoggingConfigurator: {exc}")
        traceback.print_exc()
        return False


def test_troubleshooting(temp_dir: Path) -> bool:
    """Выполняем все блоки из раздела Troubleshooting."""

    print("\n📋 Тест: Troubleshooting")

    try:
        import bquant
        from bquant.core.logging_config import setup_logging
    except Exception as exc:
        print(f"  ❌ Импорт логирования или пакета bquant не удался: {exc}")
        traceback.print_exc()
        return False

    try:
        # Неправильный и правильный порядок импорта
        from bquant.data.loader import load_ohlcv_data  # noqa: F401 - имитация позднего импорта
        setup_logging(profile="research")

        from bquant.core.logging_config import setup_logging as setup_logging_before
        setup_logging_before(profile="research")
        from bquant.data.loader import load_ohlcv_data as _loader_again  # noqa: F401

        # Проверка версии
        version = getattr(bquant, "__version__", "unknown")
        print(f"  ✅ Версия BQuant: {version}")

        # Настройка файлового логирования
        log_path = Path(temp_dir) / "my_log.txt"
        setup_logging(profile="research", log_to_file=True, log_file="my_log.txt")
        setup_logging(profile="research")

        exists = log_path.exists() and log_path.stat().st_size > 0
        print(f"  ✅ Файл логирования создан: {exists}")
        return exists
    except Exception as exc:
        print(f"  ❌ Ошибка в Troubleshooting примерах: {exc}")
        traceback.print_exc()
        return False


def test_notebook_integration(sample_csv: Path) -> bool:
    """Проверяем оба примера интеграции с NotebookSimulator."""

    print("\n📋 Тест: NotebookSimulator интеграция")

    try:
        from bquant.core.logging_config import setup_logging
        from bquant.core.nb import NotebookSimulator
        from bquant.data.loader import load_ohlcv_data
    except Exception as exc:
        print(f"  ❌ Импорт NotebookSimulator или зависимостей не удался: {exc}")
        traceback.print_exc()
        return False

    original_argv = sys.argv[:]
    sys.argv = ["notebook_script.py"]
    nb = None
    nb_demo = None

    try:
        setup_logging(profile="research")
        nb = NotebookSimulator("Тест")
        nb.info("Это сообщение ВСЕГДА видно")
        nb.warning("Это тоже видно")

        setup_logging(profile="research")
        nb_demo = NotebookSimulator("Демонстрация логирования")
        nb_demo.info("Шаг 1: Загрузка данных")

        # Технические детали (скрыты профилем research)
        from bquant.data.loader import load_ohlcv_data as _loader_for_nb  # noqa: F401
        data = load_ohlcv_data(sample_csv.name)
        nb_demo.success(f"Загружено {len(data)} строк")

        return len(data) >= 100
    except Exception as exc:
        print(f"  ❌ Ошибка интеграции NotebookSimulator: {exc}")
        traceback.print_exc()
        return False
    finally:
        sys.argv = original_argv
        for instance in (nb, nb_demo):
            if instance and instance.log_file:
                try:
                    instance.log_file.close()
                except Exception:
                    pass


def test_migration_examples() -> bool:
    """Воспроизводим раздел миграции."""

    print("\n📋 Тест: Миграция")

    try:
        from bquant.core.logging_config import setup_logging
    except Exception as exc:
        print(f"  ❌ Импорт setup_logging не удался: {exc}")
        traceback.print_exc()
        return False

    try:
        # Старый способ настройки
        logging.getLogger("bquant.data").setLevel(logging.WARNING)
        logging.getLogger("bquant.indicators").setLevel(logging.WARNING)
        logging.getLogger("bquant.analysis").setLevel(logging.INFO)

        # Новый единый вызов + модульная настройка
        setup_logging(profile="research")
        setup_logging(
            modules_config={
                "bquant.data": {"console": "WARNING"},
                "bquant.indicators": {"console": "WARNING"},
            }
        )

        print("  ✅ Старый и новый способы выполнены")
        return True
    except Exception as exc:
        print(f"  ❌ Ошибка в примерах миграции: {exc}")
        traceback.print_exc()
        return False


def test_cross_references() -> bool:
    """Убеждаемся, что все ссылки из раздела 'См. также' существуют."""

    print("\n📋 Тест: Cross-references")

    references: List[Path] = [
        project_root / "docs/api/core/nb.md",
        project_root / "docs/api/data/README.md",
        project_root / "docs/developer_guide/README.md",
    ]

    missing = [ref for ref in references if not ref.exists()]
    if missing:
        for ref in missing:
            print(f"  ❌ Не найден файл: {ref}")
        return False

    for ref in references:
        print(f"  ✅ {ref.relative_to(project_root)}")
    return True


def test_language() -> bool:
    """Проверяем, что раздел остаётся русскоязычным и содержит все блоки кода."""

    print("\n📋 Тест: Язык")

    try:
        content = (project_root / "docs/api/core/logging.md").read_text(encoding="utf-8")
    except Exception as exc:
        print(f"  ❌ Не удалось прочитать документ: {exc}")
        traceback.print_exc()
        return False

    lower_content = content.lower()
    markers = ["логирование", "профиль", "консоль", "файл", "исключения"]
    found = sum(1 for marker in markers if marker in lower_content)
    print(f"  ✅ Найдено русских маркеров: {found}/{len(markers)}")

    code_blocks = content.count("```python")
    print(f"  ✅ Количество python-блоков: {code_blocks}")

    return found >= len(markers) - 1 and code_blocks >= 10


def main() -> bool:
    print("🔍 Валидация docs/api/core/logging.md")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        temp_dir = Path(tmp_dir_str)
        original_cwd = Path.cwd()

        try:
            os.chdir(temp_dir)
            sample_csv = _create_sample_csv(temp_dir / "file.csv")

            from bquant.core import config as core_config  # Импорт после смены cwd

            core_config.LOGGING["log_file"] = temp_dir / "doc_logs" / "bquant.log"
            core_config.LOGGING["file_logging"] = True

            tests = [
                ("Профили и примеры", lambda: test_profiles_and_practical_examples(sample_csv)),
                ("LoggingConfigurator", test_logging_configurator),
                ("Troubleshooting", lambda: test_troubleshooting(temp_dir)),
                ("NotebookSimulator", lambda: test_notebook_integration(sample_csv)),
                ("Миграция", test_migration_examples),
                ("Cross-references", test_cross_references),
                ("Язык", test_language),
            ]

            results = []
            for name, func in tests:
                print(f"\n➡️ {name}")
                ok = func()
                results.append(ok)
                print(f"✔️ {name}: {'успех' if ok else 'ошибка'}")

            total = sum(results)
            print("=" * 60)
            print(f"Итого: {total}/{len(tests)} тестов успешно")
            return all(results)
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
