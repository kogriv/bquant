"""Контракты, которые раньше только подразумевались (G66, AQ-044…047, AQ-053).

Замер до правки (2026-09-06):

* `cache_key('abc', 1, x=2.5)` в двух процессах — два разных ключа (то же для
  `np.ndarray` и `pd.Series`; кадры были стабильны): `hash(str(arg))` солится на процесс,
  и дисковый кэш для таких аргументов не переживал перезапуск. Запись, поднятая с диска,
  получала новый `default_ttl` вместо своего срока;
* `ZoneInfo(start_idx=9, end_idx=0, duration=40, data=<3 строки>)` принимался молча;
  `SwingContext(indices=[5, 2])` отдавал `slice(0, 3) -> [5, 2]` — точку вне зоны;
* `ZoneAnalysisResult.visualize()` звал `bquant[viz]`, extra, которого нет в
  `pyproject.toml`; `README` — `.[full]`, которого тоже нет;
* `embedded/mt_xauusd_m15.py::DATASET_INFO` хранил колонки из первой строки CSV без
  заголовка и `period_start=None`; `tv_xauusd_1h` — сырые имена колонок CSV при
  нормализованных ключах `DATA`; реестр `datasets.py` держал свою копию тех же чисел.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import tomllib
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
KEY_SCRIPT = """
import numpy as np, pandas as pd
from bquant.core.cache import cache_key
df = pd.DataFrame({'a': [1.0, 2.0, 3.0]}, index=pd.date_range('2024-01-01', periods=3, freq='h'))
print(cache_key('abc', 1, x=2.5), cache_key(df), cache_key(np.array([1, 2, 3])), cache_key(pd.Series([1, 2], name='s')),
      cache_key({'b': 1, 'a': [1, (2, 3)]}))
"""


# --- AQ-044 ---------------------------------------------------------------

def test_cache_keys_are_the_same_in_two_processes():
    runs = [
        subprocess.run([sys.executable, "-c", KEY_SCRIPT], capture_output=True, text=True, timeout=300)
        for _ in range(2)
    ]
    for run in runs:
        assert run.returncode == 0, run.stderr[-600:]
    assert runs[0].stdout.strip().splitlines()[-1] == runs[1].stdout.strip().splitlines()[-1]


def test_a_disk_entry_keeps_its_own_expiry_when_lifted_into_memory(tmp_path):
    from bquant.core.cache import CacheManager, DiskCache

    manager = CacheManager(memory_size=10, disk_cache=False)
    manager.disk_cache = DiskCache(cache_dir=tmp_path)
    manager.disk_cache.put("k", "v", ttl=120)
    disk_expiry = manager.disk_cache.get_entry("k").expiry

    assert manager.get("k") == "v"
    memory_expiry = manager.memory_cache._cache["k"].expiry
    assert memory_expiry == disk_expiry, (
        f"memory entry expires at {memory_expiry}, disk entry at {disk_expiry}"
    )
    assert memory_expiry < datetime.now() + timedelta(seconds=130)


# --- AQ-045 ---------------------------------------------------------------

@pytest.fixture
def frame():
    return pd.DataFrame({"close": np.arange(10.0)}, index=pd.date_range("2024-01-01", periods=10, freq="h"))


def _zone(frame, **overrides):
    from bquant.analysis.zones.models import ZoneInfo

    fields = dict(zone_id=1, type="bull", start_idx=2, end_idx=5, start_time=frame.index[2],
                  end_time=frame.index[5], duration=4, data=frame.iloc[2:6])
    fields.update(overrides)
    return ZoneInfo(**fields)


def test_a_consistent_zone_is_accepted_and_an_empty_frame_means_not_carried(frame):
    assert _zone(frame).duration == 4
    assert len(_zone(frame, data=pd.DataFrame()).data) == 0


@pytest.mark.parametrize("overrides, message", [
    ({"start_idx": 6}, "start_idx 6 > end_idx 5"),
    ({"duration": 40}, "duration 40 != end_idx - start_idx \\+ 1 = 4"),
    ({"data": None, "end_time": None}, None),  # tolerated: nothing to compare
])
def test_a_zone_that_contradicts_itself_is_refused(frame, overrides, message):
    if message is None:
        _zone(frame, **overrides)
        return
    with pytest.raises(ValueError, match=message):
        _zone(frame, **overrides)


def test_a_zone_with_reversed_time_or_foreign_frame_is_refused(frame):
    with pytest.raises(ValueError, match="start_time .* > end_time"):
        _zone(frame, start_time=frame.index[5], end_time=frame.index[2])
    with pytest.raises(ValueError, match="data carries 3 rows, duration is 4"):
        _zone(frame, data=frame.iloc[:3])


def test_an_unsorted_swing_context_is_refused(frame):
    from bquant.analysis.zones.models import SwingContext, SwingPoint

    def point(i, kind):
        return SwingPoint(point_id=i, timestamp=frame.index[i], index=i, price=1.0, swing_type=kind,
                          amplitude_to_next=None, duration_to_next=None, strategy_name="x", strategy_params={})

    with pytest.raises(ValueError, match="sorted ascending"):
        SwingContext(swing_points=[point(5, "peak"), point(2, "trough")], indices=np.array([5, 2]),
                     full_data_length=10, strategy_name="x", strategy_params={})
    with pytest.raises(ValueError, match=r"indices\[1\] = 7 but swing_points\[1\].index = 5"):
        SwingContext(swing_points=[point(2, "trough"), point(5, "peak")], indices=np.array([2, 7]),
                     full_data_length=10, strategy_name="x", strategy_params={})


# --- AQ-046 ---------------------------------------------------------------

def _declared_extras():
    return set(tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["optional-dependencies"])


def test_every_install_hint_names_an_extra_that_exists():
    extras = _declared_extras()
    hinted = {}
    for path in [*(ROOT / "bquant").rglob("*.py"), ROOT / "README.md", *(ROOT / "docs").rglob("*.md")]:
        if "_build" in path.parts:
            continue
        for match in re.finditer(r"bquant\[([a-z,]+)\]|\.\[([a-z,]+)\]", path.read_text(encoding="utf-8", errors="ignore")):
            for extra in (match.group(1) or match.group(2)).split(","):
                hinted.setdefault(extra, set()).add(str(path.relative_to(ROOT)))
    unknown = {extra: files for extra, files in hinted.items() if extra not in extras}
    assert not unknown, f"install hints name extras that do not exist: {unknown}"


def test_extras_do_not_repeat_base_dependencies():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    base = {re.split(r"[<>=!~ ]", dep)[0].lower() for dep in project["dependencies"]}
    repeated = {
        extra: sorted(name for name in (re.split(r"[<>=!~ ]", dep)[0].lower() for dep in deps) if name in base)
        for extra, deps in project["optional-dependencies"].items()
    }
    repeated = {k: v for k, v in repeated.items() if v}
    assert not repeated, f"extras repeat base dependencies: {repeated}"


# --- AQ-047 ---------------------------------------------------------------

def test_result_fields_are_the_types_they_are_annotated_with():
    from bquant.analysis.zones import analyze_zones
    from bquant.analysis.zones.models import ZoneAnalysisResult
    from bquant.data.samples import get_sample_data

    result = (analyze_zones(get_sample_data("tv_xauusd_1h"))
              .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
              .detect_zones("zero_crossing", indicator_role="hist")
              .with_cache(enable=False).analyze(clustering=False, regression=True).build())
    for name in ("statistics", "hypothesis_tests", "regression_results"):
        value = getattr(result, name)
        assert isinstance(value, dict), f"{name} is {type(value).__name__}, annotated Dict"
    import typing

    annotation = ZoneAnalysisResult.__dataclass_fields__["hypothesis_tests"].type
    assert typing.get_origin(annotation) is dict or annotation in ("Dict[str, Any]", dict), annotation


# --- AQ-053 ---------------------------------------------------------------

@pytest.mark.parametrize("name", ["tv_xauusd_1h", "mt_xauusd_m15"])
def test_sample_metadata_is_what_the_data_carries(name):
    from bquant.data.samples import get_dataset_info, validate_dataset
    from bquant.data.samples.datasets import AVAILABLE_DATASETS, MEASURED_FIELDS
    from bquant.data.samples.utils import load_embedded_data

    embedded = load_embedded_data(name)
    data, declared = embedded["DATA"], embedded["DATASET_INFO"]
    assert declared["columns"] == list(data[0].keys())
    assert declared["rows"] == len(data)
    assert pd.Timestamp(declared["period_start"]) == pd.Timestamp(data[0]["time"])
    assert pd.Timestamp(declared["period_end"]) == pd.Timestamp(data[-1]["time"])

    info = get_dataset_info(name)
    assert info["columns"] == declared["columns"] and info["rows"] == declared["rows"]
    assert pd.Timestamp(info["period_start"]) == pd.Timestamp(declared["period_start"])
    assert not (set(MEASURED_FIELDS) & set(AVAILABLE_DATASETS[name])), "registry keeps its own copy"
    verdict = validate_dataset(name)
    assert verdict["is_valid"], verdict["errors"]


def test_the_generator_refuses_a_period_it_cannot_determine():
    from bquant.data.samples.generator import SampleDataGenerator

    generator = SampleDataGenerator.__new__(SampleDataGenerator)
    generator.logger = __import__("logging").getLogger("test")
    config = {"name": "x", "description": "", "source": "", "symbol": "X", "timeframe": "1H",
              "license": "", "disclaimer": ""}
    with pytest.raises(ValueError, match="cannot determine the period"):
        generator._create_metadata(config, pd.DataFrame({"open": [1.0]}), "x", Path("x.csv"))
