"""Датасет обязан нести тот период, который объявляет.

G40. У `mt_xauusd_m15` в реестре стоял период `2025-05-20 … 2025-05-30`, а данные
внутри — `2025-08-07 … 2025-08-22`. Расхождение в три месяца, и `validate_dataset()`
всё это время отвечало `is_valid: True`: проверялись число строк и набор колонок,
период — нет вовсе. Вердикт выносился о том, чего не смотрели.

Почему не поймал сьют: все проверки sample-данных, кроме одной строки про источник,
работают на `tv_xauusd_1h` — единственном датасете, у которого метаданные совпадали.

Форма та же, что у G34/G37/G39: отсутствие проверки неотличимо от пройденной проверки.
"""

from __future__ import annotations

import pandas as pd
import pytest

from bquant.data.samples import (
    get_dataset_info,
    list_dataset_names,
    load_embedded_data,
    validate_dataset,
)
from bquant.data.samples.utils import validate_data_integrity


@pytest.mark.parametrize("dataset_name", list_dataset_names())
def test_declared_period_equals_the_data(dataset_name: str):
    """Главное утверждение: объявленное совпадает с несомым, у каждого датасета."""

    info = get_dataset_info(dataset_name)
    data = load_embedded_data(dataset_name)["DATA"]

    time_column = sorted(c for c in data[0] if "time" in c.lower())[0]

    assert pd.to_datetime(info["period_start"]) == pd.to_datetime(data[0][time_column])
    assert pd.to_datetime(info["period_end"]) == pd.to_datetime(data[-1][time_column])


@pytest.mark.parametrize("dataset_name", list_dataset_names())
def test_validation_passes_for_every_dataset(dataset_name: str):
    """Раньше сьют спрашивал это только у `tv_xauusd_1h`."""

    result = validate_dataset(dataset_name)

    assert result["is_valid"] is True, result["errors"]
    assert result["errors"] == []


def test_a_drifted_period_is_refused_and_named():
    """Подменяем период — валидация обязана назвать обе стороны расхождения.

    Без этой проверки правка реестра ничего не гарантирует: она чинит один
    случай, а не делает следующий такой же видимым.
    """

    dataset_name = "mt_xauusd_m15"
    data = load_embedded_data(dataset_name)["DATA"]
    info = dict(get_dataset_info(dataset_name))
    info["period_start"] = "2025-05-20T02:00:00"  # то, что стояло в реестре до G40

    result = validate_data_integrity(data, info)

    assert result["is_valid"] is False
    message = " ".join(result["errors"])
    assert "2025-05-20T02:00:00" in message, "отказ обязан назвать объявленное"
    assert "2025.08.07 19:15" in message, "и то, что на самом деле в данных"


def test_an_undeclared_period_is_not_silently_accepted():
    """`None` в метаданных — это «неизвестно», а не «совпало».

    Именно в таком виде период лежит в сгенерированном `embedded/mt_xauusd_m15.py`:
    извлечение не смогло определить временную колонку и записало `None`.
    """

    data = load_embedded_data("tv_xauusd_1h")["DATA"]
    info = dict(get_dataset_info("tv_xauusd_1h"))
    info["period_start"] = None
    info["period_end"] = None

    result = validate_data_integrity(data, info)

    assert result["is_valid"] is False
    assert any("Declared period is missing" in e for e in result["errors"])


def test_the_period_is_reported_even_when_it_matches():
    """Совпадение тоже должно быть видно — иначе «проверено» неотличимо от «пропущено»."""

    result = validate_dataset("tv_xauusd_1h")

    period = result["stats"]["period"]
    assert period["declared"] == period["actual"]
