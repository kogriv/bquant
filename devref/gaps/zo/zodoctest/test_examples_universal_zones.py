import os
import re
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / "examples" / "02a_universal_zones.py"


@lru_cache(maxsize=1)
def _run_example():
    env = os.environ.copy()
    env.setdefault("NUMBA_DISABLE_JIT", "1")
    env.setdefault("PANDAS_TA_SUPPRESS_ERRORS", "1")
    env.setdefault("PANDAS_TA_LOG_LEVEL", "ERROR")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            check=False,
            capture_output=True,
            text=True,
            cwd=tmpdir,
            env=env,
        )

        results_dir = tmp_path / "results"
        artifacts = {}
        if results_dir.exists():
            for artifact_path in results_dir.iterdir():
                relative = artifact_path.relative_to(tmp_path).as_posix()
                artifacts[relative] = artifact_path.stat().st_size

    return proc.returncode, proc.stdout, proc.stderr, artifacts


def test_script_execution():
    code, stdout, stderr, _ = _run_example()

    assert code == 0, f"Unexpected return code: {code}\nSTDERR:\n{stderr}"
    assert "Traceback" not in stdout
    assert "Traceback" not in stderr
    assert "ERROR" not in stdout, stdout
    assert "ERROR" not in stderr, stderr


def test_sections_present():
    _, stdout, _, _ = _run_example()

    markers = [
        "1. MACD Zones - Zero Crossing Strategy",
        "2. RSI Zones - Threshold Strategy",
        "3. Awesome Oscillator Zones - Zero Crossing Strategy",
        "4. Moving Average Crossover - Line Crossing Strategy",
        "5. Stochastic %K/%D - Line Crossing (v2.1)",
        "6. Custom Indicator - Zero Code Changes Needed!",
        "7. Preloaded Zones - External Data",
        "8. Кэширование и персистентное хранение",
        "9. Модульное использование",
    ]

    missing = [marker for marker in markers if marker not in stdout]
    assert not missing, f"Missing sections: {missing}"


def test_zone_counts_positive():
    _, stdout, _, _ = _run_example()

    patterns = {
        "MACD": r"\[OK\] MACD - Анализ завершен:\s+Зон: (\d+)",
        "RSI": r"\[OK\] RSI - Анализ завершен:\s+Зон: (\d+)",
        "AO": r"\[OK\] AO - Анализ завершен:\s+Зон: (\d+)",
        "MA Crossover": r"\[OK\] MA Crossover - Анализ завершен:\s+Зон: (\d+)",
        "Stochastic": r"\[OK\] Stochastic K/D - Анализ завершен:\s+Зон: (\d+)",
        "Custom Momentum": r"\[OK\] Custom Momentum - Анализ завершен:\s+Зон: (\d+)",
        "Preloaded": r"\[OK\] Preloaded - Анализ завершен:\s+Зон: (\d+)",
    }

    for name, pattern in patterns.items():
        match = re.search(pattern, stdout)
        assert match, f"Count pattern not found for {name}"
        count = int(match.group(1))
        assert count > 0, f"Expected positive zone count for {name}, got {count}"


def test_results_artifacts_created():
    _, _, _, artifacts = _run_example()

    expected = {
        "results/macd_zones.pkl",
        "results/macd_zones.json",
        "results/macd_zones.parquet",
    }
    artifact_keys = set(artifacts.keys())
    missing = expected - artifact_keys
    assert not missing, f"Missing artifacts: {missing}"

    empty = {name for name in expected if artifacts.get(name, 0) == 0}
    assert not empty, f"Artifacts without data: {empty}"


def test_reference_paths_exist():
    targets = [
        PROJECT_ROOT / "docs" / "api" / "analysis" / "zones.md",
        PROJECT_ROOT / "devref" / "gaps" / "zo" / "zomodul.md",
        PROJECT_ROOT / "devref" / "gaps" / "zo" / "zonan.md",
    ]

    missing = [str(path) for path in targets if not path.exists()]
    assert not missing, f"Reference targets are missing: {missing}"


def test_dataset_marker():
    _, stdout, _, _ = _run_example()
    assert "mt_xauusd_m15" in stdout


def main() -> None:
    tests = [
        test_script_execution,
        test_sections_present,
        test_zone_counts_positive,
        test_results_artifacts_created,
        test_reference_paths_exist,
        test_dataset_marker,
    ]

    results = []
    for test in tests:
        try:
            test()
            print(f"✅ {test.__name__}")
            results.append(True)
        except AssertionError as exc:
            print(f"❌ {test.__name__}: {exc}")
            results.append(False)
        except Exception as exc:  # pragma: no cover - страховка
            print(f"❌ {test.__name__} failed with unexpected error: {exc}")
            results.append(False)

    passed = sum(1 for value in results if value)
    print(f"\n✅ Пройдено {passed}/{len(tests)} тестов")

    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
