"""Оптимизированные индикаторы считают то, что называют.

G44. `OptimizedIndicators` рекламировались справочником ядра как «оптимизированные
реализации на NumPy». Две из пяти считали не то:

* `sma` строилась через `np.convolve(..., mode='same')` — окно **центрированное** и
  дополненное нулями с обоих концов. Индикатор заглядывал вперёд, а последние
  `period//2` значений усреднялись с нулями: на ряде около 2900 последнее значение
  равнялось 1597. `bollinger_bands` брала оттуда среднюю линию, поэтому ошибалась
  вместе с ней — при том что разброс в той же функции считался по **правильному**
  хвостовому окну. Среднее и отклонение мерились на разных множествах.
* `rsi` при отсутствии падений обнуляла RS, и строго растущий ряд получал **RSI 0** —
  отметку предельной перепроданности. Строго падающий ряд давал 0. Плоский ряд давал 0.
  Три противоположных состояния, одно число.

Эталон здесь — pandas: `rolling(period).mean()` и `ewm(span, adjust=False)`. Он не
«ещё одна реализация», а определение: скользящее среднее и есть среднее хвостового окна.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bquant.core.performance import OptimizedIndicators


@pytest.fixture(scope="module")
def prices() -> np.ndarray:
    rng = np.random.default_rng(0)
    return 3000 + np.cumsum(rng.normal(0, 2, 500))


def test_sma_is_the_mean_of_the_trailing_window(prices):
    """Главная проверка: совпадение с определением на всём ряде, включая хвост."""

    reference = pd.Series(prices).rolling(20).mean().to_numpy()

    assert np.allclose(OptimizedIndicators.sma(prices, 20), reference, equal_nan=True)


def test_sma_does_not_average_prices_with_padding(prices):
    """Отдельно про хвост: там ошибка была вдвое, и именно её никто не видел."""

    sma = OptimizedIndicators.sma(prices, 20)

    assert sma[-1] == pytest.approx(prices[-20:].mean())
    assert sma[-1] > prices.min(), "значение не может выпасть из диапазона цен"


def test_sma_warmup_is_absent_not_wrong(prices):
    """Первые period-1 значений отсутствуют, а не досчитываются по неполному окну."""

    sma = OptimizedIndicators.sma(prices, 20)

    assert np.isnan(sma[:19]).all()
    assert not np.isnan(sma[19:]).any()


def test_bollinger_middle_band_is_the_sma(prices):
    """Средняя линия и разброс обязаны считаться по одному и тому же окну."""

    upper, middle, lower = OptimizedIndicators.bollinger_bands(prices, 20, 2.0)
    reference = pd.Series(prices).rolling(20).mean().to_numpy()

    assert np.allclose(middle, reference, equal_nan=True)
    assert np.all(upper[19:] >= middle[19:])
    assert np.all(middle[19:] >= lower[19:])


def test_ema_matches_its_definition(prices):
    """EMA была верна и до правки — пин, чтобы осталась верной.

    С G58 первые `period - 1` значений не публикуются — тот же прогрев, что у
    custom-EMA; после него ряд совпадает с `ewm(adjust=False)` побитово.
    """

    reference = pd.Series(prices).ewm(span=20, adjust=False).mean().to_numpy()
    ema = OptimizedIndicators.ema(prices, 20)

    assert np.isnan(ema[:19]).all() and not np.isnan(ema[19:]).any()
    assert np.allclose(ema[19:], reference[19:])


def test_a_series_that_only_rises_is_not_oversold():
    """RSI строго растущего ряда — 100, а не 0."""

    rising = np.arange(100, 200, dtype=float)

    assert OptimizedIndicators.rsi(rising, 14)[-1] == 100.0


def test_a_series_that_only_falls_is_not_the_same_as_one_that_only_rises():
    """Два противоположных ряда обязаны давать разные числа."""

    rising = np.arange(100, 200, dtype=float)
    falling = np.arange(200, 100, -1, dtype=float)

    assert OptimizedIndicators.rsi(rising, 14)[-1] == 100.0
    assert OptimizedIndicators.rsi(falling, 14)[-1] == 0.0


def test_a_flat_series_has_no_rsi():
    """Ни роста, ни падения — величина не определена; ноль здесь был бы выдумкой."""

    flat = np.full(100, 150.0)

    assert np.isnan(OptimizedIndicators.rsi(flat, 14)[-1])


def test_rsi_stays_inside_its_scale(prices):
    rsi = OptimizedIndicators.rsi(prices, 14)

    assert np.nanmin(rsi) >= 0.0
    assert np.nanmax(rsi) <= 100.0


def test_the_cache_key_sees_the_package_version():
    """Иначе исправленная функция ещё час отдаёт прежние числа с диска (как в G36)."""

    from unittest import mock

    import bquant
    from bquant.core.cache import get_cache_manager

    memory_cache = get_cache_manager().memory_cache
    before = memory_cache._generate_key("f", (1,), {})
    with mock.patch.object(bquant, "__version__", "9.9.9"):
        after = memory_cache._generate_key("f", (1,), {})

    assert before != after
