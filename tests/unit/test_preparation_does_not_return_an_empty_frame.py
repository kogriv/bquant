"""Подготовка данных не имеет права вернуть пустой кадр как результат.

G41. `prepare_data_for_analysis()` заканчивался `dropna()` **по всему кадру** — включая
колонки, к анализу отношения не имеющие. Во встроенном сэмпле TradingView четыре колонки
маркеров дивергенций заполнены только на сигнальных барах, то есть в загруженном виде
пусты целиком. Одной такой колонки хватало, чтобы отсев унёс все 1000 строк, и функция
возвращала кадр `(0, 36)` — тридцать шесть колонок и ни одной строки — без единой ошибки.

Документированный путь `clean_ohlcv_data()` → `prepare_data_for_analysis()` на собственных
данных пакета давал пустоту, и пустота выглядела как подготовленные данные.
"""

from __future__ import annotations

import pandas as pd
import pytest

from bquant.core.exceptions import DataProcessingError
from bquant.data.processor import clean_ohlcv_data, prepare_data_for_analysis
from bquant.data.samples import get_sample_data


@pytest.fixture(scope="module")
def sample() -> pd.DataFrame:
    return clean_ohlcv_data(get_sample_data("tv_xauusd_1h"))


def test_the_package_own_sample_survives_preparation(sample):
    """Главная проверка: на своих же данных подготовка обязана что-то оставить."""

    prepared = prepare_data_for_analysis(sample)

    assert not prepared.empty, "подготовка вернула ноль строк"
    assert len(prepared) == 951, "отсеяны только строки прогрева самого длинного окна"


def test_rows_are_dropped_only_for_the_columns_that_matter(sample):
    """Отсев обязан объясняться прогревом окон, а не посторонней колонкой.

    `price_ma_50` требует 50 баров, поэтому первые 49 строк уходят — и это всё.
    """

    prepared = prepare_data_for_analysis(sample)

    assert prepared.index[0] == 49
    assert prepared.index[-1] == len(sample) - 1


def test_a_column_empty_in_every_row_is_not_a_feature(sample):
    """Колонка без единого значения не может ни быть признаком, ни отсеивать строки."""

    short = sample.head(30)  # короче окна price_ma_50 — колонка пуста целиком

    prepared = prepare_data_for_analysis(short)

    assert not prepared.empty
    assert "price_ma_50" in prepared.columns, "колонка остаётся в кадре, но не отсеивает"
    assert prepared["price_ma_50"].isna().all()


@pytest.mark.parametrize("rows", [10, 20, 25, 49, 50, 51, 60, 120, 1000])
def test_the_result_is_never_an_empty_frame(sample, rows):
    """Инвариант: либо непустой кадр, либо отказ — но не пустота, выданная за результат.

    Проверяется на длинах вокруг всех окон прогрева (`roc_5`, `roc_10`, `price_ma_20`,
    `price_ma_50`), потому что именно прогрев — единственная законная причина отсева.
    На дореформенном коде падает длина 1000: там возвращался кадр `(0, 36)`.
    """

    try:
        prepared = prepare_data_for_analysis(sample.head(rows))
    except DataProcessingError:
        return  # отказ — допустимый исход, пустой кадр — нет

    assert not prepared.empty, f"подготовка вернула ноль строк на {rows} входных"


def test_the_dropped_columns_are_named_in_the_log(sample, caplog):
    """Пакетные логгеры не всплывают: слушать надо именованный логгер."""

    import logging

    logger = logging.getLogger("bquant.data.processor")
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.WARNING, logger="bquant.data.processor"):
            prepare_data_for_analysis(sample.head(30))
    finally:
        logger.removeHandler(caplog.handler)

    assert "price_ma_50" in caplog.text
