"""Валидатор для examples/07_validation_demo.py."""

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
SCRIPT_PATH = PROJECT_ROOT / "examples" / "07_validation_demo.py"


@lru_cache(maxsize=1)
def _run_example() -> Tuple[int, str, str]:
    """Запускает демонстрацию валидации и кэширует результат."""

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


def test_script_executes_cleanly() -> None:
    code, stdout, stderr = _run_example()

    assert code == 0, f"Код завершения {code}, stderr: {stderr}"
    assert "Traceback" not in stdout
    assert "Traceback" not in stderr


def test_out_of_sample_metrics() -> None:
    output = _combined_output()
    match = re.search(
        r"Train R²: ([0-9.]+).*?Test R²: ([0-9.]+).*?Degradation: ([0-9.]+)%",
        output,
        re.S,
    )
    assert match, "Не удалось извлечь показатели out-of-sample"

    train_r2 = float(match.group(1))
    test_r2 = float(match.group(2))
    degradation = float(match.group(3))

    assert train_r2 >= 0.9
    assert test_r2 >= 0.9
    assert degradation < 20.0


def test_walk_forward_stability() -> None:
    output = _combined_output()
    match = re.search(r"Stability score: ([0-9.]+)", output)
    assert match, "Не найден показатель стабильности"
    assert float(match.group(1)) > 0.6


def test_indicator_scenarios_present() -> None:
    output = _combined_output()
    for label in [
        "MACD (12,26,9)",
        "EMA (20) vs Close",
        "SMA (50) vs Close",
    ]:
        position = output.find(label)
        assert position != -1, f"Не найден блок {label}"
        snippet = output[position: position + 80]
        match = re.search(r"зон=(\d+)", snippet)
        assert match, f"Не удалось извлечь количество зон для {label}"
        assert int(match.group(1)) > 0, f"{label} должен давать зоны"


def test_monte_carlo_significance() -> None:
    output = _combined_output()
    match = re.search(r"P-value: ([0-9.]+)", output)
    assert match, "Не найден P-value"
    assert float(match.group(1)) < 0.05


def test_resource_links_exist() -> None:
    output = _combined_output()
    resources = re.findall(r"- ✅ ([^\n]+)", output)
    assert resources, "Не найдены подтверждённые ссылки"

    for relative in resources:
        target = PROJECT_ROOT / relative
        assert target.exists(), f"Ссылка {relative} не существует"
