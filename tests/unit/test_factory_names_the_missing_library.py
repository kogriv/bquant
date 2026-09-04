"""A library indicator that is not registered fails by naming the library, not a class.

``IndicatorFactory.create('talib', 'rsi')`` without TA-Lib used to fall into a
"template" branch that imported ``TALibRSI`` from ``bquant.indicators.library.talib`` —
a class that module never defined. The reader got
``ImportError: cannot import name 'TALibRSI'`` and went looking for a broken package;
the actual state was "TA-Lib is not installed". The RSI tutorial prescribed exactly
that call.
"""

import pytest

from bquant.indicators.base import IndicatorFactory


@pytest.mark.parametrize("indicator", ["sma", "ema", "rsi", "macd", "bbands"])
def test_an_unregistered_talib_indicator_names_the_library(indicator):
    registered = f"talib_{indicator}" in IndicatorFactory._registry
    if registered:
        pytest.skip("TA-Lib is loaded in this environment; the branch under test is not reached")

    with pytest.raises(KeyError) as failure:
        IndicatorFactory.create('talib', indicator)

    message = str(failure.value)
    assert "not registered" in message and "not installed" in message, message
    assert "TALib" not in message, "the error must not name a class that does not exist"
