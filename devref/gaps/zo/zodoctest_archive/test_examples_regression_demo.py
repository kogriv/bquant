"""Валидатор для examples/06_regression_demo.py."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / "examples" / "06_regression_demo.py"


@lru_cache(maxsize=1)
def _run_example() -> Tuple[int, str, str]:
    """Запускает демо регрессии и кэширует результат."""

    env = os.environ.copy()
    env.setdefault("NUMBA_DISABLE_JIT", "1")
    env.setdefault("BQUANT_SKIP_PANDAS_TA", "1")
    env.setdefault("BQUANT_SKIP_TALIB", "1")
    env.setdefault("BQUANT_LOG_LEVEL", "ERROR")

    with tempfile.TemporaryDirectory() as tmpdir:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            check=False,
            capture_output=True,
            text=True,
            cwd=tmpdir,
            env=env,
        )

    return proc.returncode, proc.stdout, proc.stderr


def _combined_output() -> str:
    code, stdout, stderr = _run_example()
    return stdout + "\n" + stderr + f"\n[exit={code}]"


def test_script_execution() -> None:
    code, stdout, stderr = _run_example()

    assert code == 0, f"Код завершения {code}, stderr: {stderr}"
    assert "Traceback" not in stdout
    assert "Traceback" not in stderr


def test_duration_model_metrics() -> None:
    output = _combined_output()

    block = re.search(r"Model 1: Zone Duration(.*?)(?:\n\s*Model 2:)", output, re.S)
    assert block, "Не найден блок Model 1"

    r2_match = re.search(r"R²: ([0-9.]+)", block.group(1))
    assert r2_match, "Не найден коэффициент детерминации для модели длительности"
    assert float(r2_match.group(1)) > 0.9

    coeffs = re.findall(r"macd_amplitude\s+:\s+([\-0-9.]+)|hist_amplitude\s+:\s+([\-0-9.]+)", block.group(1))
    assert coeffs, "Не удалось извлечь коэффициенты модели"


def test_price_return_section() -> None:
    output = _combined_output()

    block = re.search(r"Model 2: Price Return(.*?)(?:\n\s*4\.)", output, re.S)
    assert block, "Не найден блок Model 2"

    r2_match = re.search(r"R²: ([0-9.]+)", block.group(1))
    assert r2_match, "Не найден коэффициент детерминации для модели доходности"


def test_alternative_indicator_blocks() -> None:
    output = _combined_output()

    ema_match = re.search(r"EMA zones: (\d+).*?EMA R²: ([0-9.]+)", output, re.S)
    assert ema_match, "Не найден блок EMA"
    assert int(ema_match.group(1)) > 0

    macd_match = re.search(r"MACD \(8,21,5\) zones: (\d+).*?MACD \(8,21,5\) R²: ([0-9.]+)", output, re.S)
    assert macd_match, "Не найден блок MACD (8,21,5)"
    assert int(macd_match.group(1)) > 0


def test_takeaways_present() -> None:
    output = _combined_output()
    for item in [
        "1. Universal Pipeline provides numeric features for regression",
        "2. Same regression workflow works with multiple indicators",
        "5. Coefficients highlight the most influential features",
    ]:
        assert item in output
