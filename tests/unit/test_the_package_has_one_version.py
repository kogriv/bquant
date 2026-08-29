"""У пакета одна версия, а не девять (G33).

Откуда
======

Восемь подпакетов объявляли собственный ``__version__`` литералом. Четыре
застряли на ``"0.0.0"`` при пакете ``0.0.9``, четыре — на ``"0.1.0-stub"``.
Само по себе расхождение можно было бы считать косметикой, если бы число не
выходило наружу: ``get_visualization_info()`` отдавал ``version: "0.0.0"``
как факт о пакете, а заглушки клали свою версию в метаданные результата.

Форма — та же, что в G8 и G32: **второй литерал**, который обязан совпадать с
первым, и которого никто не сверяет. Первый уезжает при каждом релизе, второй
стоит на месте — и молчит.

Нашлось не поиском, а попыткой честно описать ``get_visualization_info()`` в
доке (G31): чтобы записать, что функция возвращает, надо было её запустить.

Разбор: ``devref/gaps/docs/g33_a_second_version_literal_2026-08.md``.
"""

from __future__ import annotations

import importlib
import os
import pkgutil

import pytest

os.environ.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
os.environ.setdefault("BQUANT_SKIP_TALIB", "1")

import bquant  # noqa: E402


def _modules_declaring_a_version():
    found = []
    for module in pkgutil.walk_packages(bquant.__path__, prefix="bquant."):
        try:
            loaded = importlib.import_module(module.name)
        except Exception:  # pragma: no cover — модуль с тяжёлой зависимостью
            continue
        version = getattr(loaded, "__version__", None)
        if version is not None:
            found.append((module.name, version))
    return found


DECLARED = _modules_declaring_a_version()


@pytest.mark.parametrize(
    "module_name, version",
    DECLARED,
    ids=[name for name, _ in DECLARED],
)
def test_a_submodule_version_equals_the_package_version(module_name, version):
    """Подпакет вправе объявлять версию — но ту же, что у пакета."""
    assert version == bquant.__version__, (
        f"{module_name}.__version__ = {version!r}, а у пакета {bquant.__version__!r}.\n"
        "Свой литерал версии разъезжается с пакетом молча: релиз двигает один, "
        "второй остаётся. Берите версию у пакета — `from bquant import __version__`."
    )


def test_the_scan_actually_looked_at_the_package():
    """Пустой обход дал бы зелёный отчёт ни о чём."""
    assert len(DECLARED) >= 5, (
        f"найдено {len(DECLARED)} модулей с `__version__` — обход пакета сломался"
    )
