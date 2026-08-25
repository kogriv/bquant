"""Identity and roles for indicator columns (G8 stage C).

A column name used to carry two unrelated things at once — which indicator
instance produced the series, and what the series means — fused into one literal
with nothing owning the mapping. `macd_hist` is "MACD with some parameters" plus
"the histogram", glued together; every producer invented a string and every
consumer guessed one, and the moment the data entered a DataFrame the knowledge
was gone.

This stage separates the halves without renaming anything yet:

* `IndicatorId` — identity, a deterministic slug over normalized parameters;
* output roles — what a series means, from a closed vocabulary;
* `ColumnSchema` — the mapping, kept beside the frame so it survives the merge;
* `indicator_role=` — the caller addresses a series by role instead of by string.

Renaming the emitted columns to slug form is the next step, together with the
consumers. Splitting it that way keeps every stage verifiable against the
previous behaviour, which a combined step could not be.

Analysis: ``devref/gaps/columns/g8_column_contract_measurement_2026-08-23.md``
Design:   ``devref/gaps/columns/g8_column_contract_design_2026-08-23.md``
"""

import pytest

from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data
from bquant.indicators import IndicatorFactory
from bquant.indicators.schema import (
    ColumnSchema,
    IndicatorId,
    known_roles,
    parse_column,
    register_role,
    validate_role,
)


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


# --------------------------------------------------------------------------- #
# 1. Identity
# --------------------------------------------------------------------------- #
class TestIndicatorId:
    def test_slug_carries_the_parameters(self):
        """The defect being closed: `macd_hist` says nothing about 12/26/9."""
        macd = IndicatorId("custom", "macd",
                           {"fast_period": 12, "slow_period": 26, "signal_period": 9},
                           ("fast_period", "slow_period", "signal_period"))
        assert macd.slug == "macd_12_26_9"

    def test_two_instances_of_one_indicator_do_not_collide(self):
        """`macd` and `bbands` used to claim the same columns whatever the settings."""
        order = ("fast_period", "slow_period", "signal_period")
        a = IndicatorId("custom", "macd", {"fast_period": 12, "slow_period": 26,
                                           "signal_period": 9}, order)
        b = IndicatorId("custom", "macd", {"fast_period": 5, "slow_period": 35,
                                           "signal_period": 5}, order)
        assert a.slug != b.slug
        assert a.column("hist") != b.column("hist")

    def test_keyword_order_does_not_change_the_slug(self):
        """Order comes from the declaration, not from how the caller typed it."""
        order = ("fast_period", "slow_period", "signal_period")
        a = IndicatorId("custom", "macd", {"fast_period": 12, "slow_period": 26,
                                           "signal_period": 9}, order)
        b = IndicatorId("custom", "macd", {"signal_period": 9, "fast_period": 12,
                                           "slow_period": 26}, order)
        assert a.slug == b.slug

    def test_two_and_two_point_zero_are_one_value(self):
        """pandas-ta's own `BBL_5_2.0_2.0` shows where the inconsistency ends up."""
        order = ("period", "std_dev")
        assert (IndicatorId("custom", "bbands", {"period": 20, "std_dev": 2}, order).slug
                == IndicatorId("custom", "bbands", {"period": 20, "std_dev": 2.0}, order).slug)

    def test_a_fractional_parameter_survives(self):
        spec = IndicatorId("custom", "zigzag", {"deviation": 0.05}, ("deviation",))
        assert spec.slug == "zigzag_0.05"

    def test_undeclared_parameters_still_slug_deterministically(self):
        """An incomplete declaration must degrade to a stable slug, not a random one."""
        a = IndicatorId("custom", "x", {"b": 2, "a": 1})
        b = IndicatorId("custom", "x", {"a": 1, "b": 2})
        assert a.slug == b.slug == "x_1_2"

    def test_a_single_value_output_is_just_the_slug(self):
        rsi = IndicatorId("custom", "rsi", {"period": 14}, ("period",))
        assert rsi.column("value") == "rsi_14"

    def test_the_separator_is_doubled_so_the_parse_is_unambiguous(self):
        """Names and parameters contain single underscores; one would be ambiguous."""
        macd = IndicatorId("custom", "macd", {"fast_period": 12, "slow_period": 26,
                                              "signal_period": 9},
                           ("fast_period", "slow_period", "signal_period"))
        assert macd.column("hist") == "macd_12_26_9__hist"
        assert parse_column(macd.column("hist")) == ("macd_12_26_9", "hist")

    def test_the_id_is_hashable_and_immutable(self):
        params = {"period": 14}
        rsi = IndicatorId("custom", "rsi", params, ("period",))
        params["period"] = 21  # the caller mutates their own dict
        assert rsi.slug == "rsi_14", "the id copied the mapping instead of aliasing it"
        assert {rsi: "ok"}[rsi] == "ok"


# --------------------------------------------------------------------------- #
# 2. Roles — the closed half
# --------------------------------------------------------------------------- #
class TestRoles:
    def test_core_vocabulary_covers_the_shipped_indicators(self):
        assert {"value", "line", "signal", "hist",
                "upper", "middle", "lower", "width", "percent"} <= set(known_roles())

    def test_a_free_string_is_refused(self):
        """Accepting one would reproduce the defect one level up."""
        with pytest.raises(ValueError, match="unknown output role"):
            validate_role("whatever")

    def test_the_extension_point_requires_a_description(self):
        """A new role has to say what it means; that text is all a reader has."""
        with pytest.raises(ValueError):
            register_role("my_role", "")

    def test_a_registered_role_becomes_usable(self):
        register_role("test_only_role", "used by the test suite")
        try:
            assert validate_role("test_only_role") == "test_only_role"
            assert "test_only_role" in known_roles()
        finally:
            from bquant.indicators import schema

            schema._EXTRA_ROLES.pop("test_only_role", None)

    def test_parse_returns_none_for_a_library_name(self):
        """pandas-ta names its own output, and we do not overwrite it."""
        assert parse_column("RSI_50") is None
        assert parse_column("macd_hist") is None


# --------------------------------------------------------------------------- #
# 3. The side-car
# --------------------------------------------------------------------------- #
class TestColumnSchema:
    @staticmethod
    def _macd():
        return IndicatorId("custom", "macd",
                           {"fast_period": 12, "slow_period": 26, "signal_period": 9},
                           ("fast_period", "slow_period", "signal_period"))

    def test_role_resolves_to_the_actual_column(self):
        schema = ColumnSchema()
        schema.register(self._macd(),
                        {"line": "macd", "signal": "macd_signal", "hist": "macd_hist"})
        assert schema.column("hist") == "macd_hist"

    def test_the_reverse_lookup_returns_identity_and_role(self):
        """This is the knowledge that used to vanish on merge into the frame."""
        schema = ColumnSchema()
        macd = self._macd()
        schema.register(macd, {"line": "macd", "signal": "macd_signal", "hist": "macd_hist"})
        indicator, role = schema.roles_of("macd_signal")
        assert role == "signal"
        assert indicator.slug == "macd_12_26_9"
        assert indicator.parameters["slow_period"] == 26

    def test_an_ambiguous_role_is_not_guessed(self):
        """Two indicators offering the same role: refuse rather than pick one."""
        schema = ColumnSchema()
        schema.register(IndicatorId("custom", "rsi", {"period": 14}, ("period",)),
                        {"value": "rsi_14"})
        schema.register(IndicatorId("custom", "sma", {"period": 20}, ("period",)),
                        {"value": "sma_20"})
        assert schema.column("value") is None
        assert schema.column("value", IndicatorId("custom", "rsi", {"period": 14},
                                                  ("period",))) == "rsi_14"

    def test_it_survives_a_round_trip(self):
        """The schema goes to disk with the result, so it has to come back."""
        schema = ColumnSchema()
        schema.register(self._macd(),
                        {"line": "macd", "signal": "macd_signal", "hist": "macd_hist"})
        restored = ColumnSchema.from_dict(schema.to_dict())
        assert restored.column("hist") == "macd_hist"
        assert restored.roles_of("macd")[0].slug == "macd_12_26_9"

    def test_an_unknown_role_cannot_be_registered(self):
        schema = ColumnSchema()
        with pytest.raises(ValueError, match="unknown output role"):
            schema.register(self._macd(), {"nonsense": "x"})


# --------------------------------------------------------------------------- #
# 4. Indicators declare their identity and roles
# --------------------------------------------------------------------------- #
class TestIndicatorsDeclare:
    @pytest.mark.parametrize(
        "name, params, expected_slug",
        [
            ("macd", {"fast_period": 12, "slow_period": 26, "signal_period": 9}, "macd_12_26_9"),
            ("macd", {"fast_period": 5, "slow_period": 35, "signal_period": 5}, "macd_5_35_5"),
            ("rsi", {"period": 21}, "rsi_21"),
            ("sma", {"period": 30}, "sma_30"),
        ],
    )
    def test_identity_comes_from_the_actual_parameters(self, name, params, expected_slug):
        indicator = IndicatorFactory.create("custom", name, **params)
        assert indicator.get_indicator_id().slug == expected_slug

    def test_multi_output_indicators_declare_every_role(self):
        macd = IndicatorFactory.create("custom", "macd", fast_period=12,
                                       slow_period=26, signal_period=9)
        assert macd.get_output_roles() == {
            "line": "macd_12_26_9__line",
            "signal": "macd_12_26_9__signal",
            "hist": "macd_12_26_9__hist",
        }
        bbands = IndicatorFactory.create("custom", "bbands", period=20)
        assert set(bbands.get_output_roles()) == {
            "upper", "middle", "lower", "width", "percent",
        }

    def test_single_output_indicators_get_the_default(self):
        rsi = IndicatorFactory.create("custom", "rsi", period=14)
        assert rsi.get_output_roles() == {"value": "rsi_14"}

    def test_declared_roles_point_at_columns_that_are_actually_emitted(self, data):
        """The declaration must describe reality, not intention."""
        for name, params in (
            ("macd", {"fast_period": 12, "slow_period": 26, "signal_period": 9}),
            ("bbands", {"period": 20}),
            ("rsi", {"period": 14}),
        ):
            indicator = IndicatorFactory.create("custom", name, **params)
            emitted = set(indicator.calculate(data).data.columns)
            declared = set(indicator.get_output_roles().values())
            assert declared <= emitted, (
                f"custom.{name}: declares {declared - emitted} which it does not emit"
            )


# --------------------------------------------------------------------------- #
# 5. Addressing by role, end to end
# --------------------------------------------------------------------------- #
class TestRoleAddressing:
    def test_role_and_column_name_select_the_same_series(self, data):
        by_role = (
            analyze_zones(data)
            .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
            .detect_zones("zero_crossing", indicator_role="hist")
            .with_cache(False)
            .build()
        )
        # То же самое, но адресуясь именем колонки. Имя берётся у индикатора, а
        # не пишется литералом: литерал в тесте протухает ровно так же, как
        # протухали литералы в коде.
        hist_column = IndicatorFactory.create(
            "custom", "macd", fast_period=12, slow_period=26, signal_period=9
        ).get_output_roles()["hist"]
        by_name = (
            analyze_zones(data)
            .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
            .detect_zones("zero_crossing", indicator_col=hist_column)
            .with_cache(False)
            .build()
        )
        assert by_role.zones, "role addressing produced no zones"
        assert len(by_role.zones) == len(by_name.zones)
        assert [z.type for z in by_role.zones] == [z.type for z in by_name.zones]

    def test_the_result_carries_the_schema(self, data):
        result = (
            analyze_zones(data)
            .with_indicator("custom", "macd", fast_period=5, slow_period=35, signal_period=5)
            .detect_zones("zero_crossing", indicator_role="hist")
            .with_cache(False)
            .build()
        )
        assert result.column_schema
        # Имя колонки теперь **несёт параметры**, с которыми ряд посчитан: до
        # C2b и `macd(12,26,9)`, и `macd(5,35,5)` претендовали на одну строку
        # `macd_hist`, то есть имя не различало то, что различается.
        assert result.column_schema.column("hist") == "macd_5_35_5__hist"
        indicator, role = result.column_schema.roles_of("macd_5_35_5__signal")
        assert (indicator.slug, role) == ("macd_5_35_5", "signal")

    def test_a_role_the_indicator_does_not_provide_is_refused_clearly(self, data):
        with pytest.raises(ValueError) as excinfo:
            (
                analyze_zones(data)
                .with_indicator("custom", "macd", fast_period=12, slow_period=26,
                                signal_period=9)
                .detect_zones("zero_crossing", indicator_role="upper")
                .with_cache(False)
                .build()
            )
        message = str(excinfo.value)
        assert "indicator_role='upper'" in message
        assert "line" in message and "hist" in message, (
            f"the message must say what is available: {message}"
        )

    def test_role_and_column_together_are_rejected(self, data):
        with pytest.raises(ValueError, match="not both"):
            analyze_zones(data).detect_zones(
                "zero_crossing", indicator_role="hist", indicator_col="macd_hist"
            )

    def test_no_indicator_means_no_schema(self, data):
        """Columns supplied by the caller declare nothing, and we do not pretend.

        Uses the sample's own `macd` column, which arrived with the TradingView
        export: nothing states what it means, so there is no schema to offer.
        """
        assert "macd" in data.columns
        result = (
            analyze_zones(data)
            .detect_zones("zero_crossing", indicator_col="macd")
            .with_cache(False)
            .build()
        )
        assert result.zones
        assert not result.column_schema
