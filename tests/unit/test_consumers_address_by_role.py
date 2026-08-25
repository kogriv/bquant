"""Consumers ask for a role; nobody guesses a column name (G8 stage C2b-1).

The producer side of G8 was built in stages C1/C2a: identity, a closed role
vocabulary, and a schema that survives the merge into a DataFrame. This stage is
the other half — the consumers. Until now they wrote the string:

* `zone_features` decided whether a zone was "MACD-ish" with
  ``'macd' in primary_indicator.lower()`` and then read ``data['macd']``;
* both visualizers hardcoded ``['macd', 'macd_signal', 'macd_hist']``;
* the `analyze_macd_zones` preset kept its own copy of the output names;
* `IndicatorSchema` restated them a **third** time, and got them wrong: it
  declared RSI's column as ``rsi``, which the RSI indicator never produces —
  the embedded sample happens to carry a TradingView column of that name, which
  is what made the mistake invisible.

Guessing by substring is not merely inelegant. ``'macd' in name`` was silently
false for every non-MACD oscillator, so `macd_amplitude` stayed None across
every RSI zone — and that field is a default regression predictor, which is how
the regression came to have no observations at all (G23).

Column names are not renamed in this stage; that is C2b-2. What changes is that
nothing depends on them any more.
"""

import pandas as pd
import pytest

from bquant.analysis.zones import analyze_zones
from bquant.data.samples import get_sample_data
from bquant.indicators import IndicatorFactory
from bquant.indicators.schema import ColumnSchema, IndicatorId, resolve_role_columns


@pytest.fixture(scope="module")
def data():
    return get_sample_data("tv_xauusd_1h")


@pytest.fixture(scope="module")
def macd_result(data):
    return (
        analyze_zones(data)
        .with_indicator("custom", "macd", fast_period=12, slow_period=26, signal_period=9)
        .detect_zones("zero_crossing", indicator_role="hist")
        .build()
    )


# --------------------------------------------------------------------------- #
# The resolver
# --------------------------------------------------------------------------- #
class TestResolveRoleColumns:

    def _frame(self, *names):
        return pd.DataFrame({name: [1.0, 2.0] for name in names})

    def test_schema_is_the_intended_path(self):
        frame = self._frame("whatever_the_library_called_it", "other")
        indicator = IndicatorId("custom", "macd", {"fast": 12})
        schema = ColumnSchema()
        schema.register(indicator, {"hist": "whatever_the_library_called_it"})

        assert resolve_role_columns(frame, ("hist",), schema=schema) == {
            "hist": "whatever_the_library_called_it"
        }

    def test_override_wins_over_schema(self):
        frame = self._frame("a", "b")
        schema = ColumnSchema()
        schema.register(IndicatorId("custom", "macd"), {"hist": "a"})

        resolved = resolve_role_columns(
            frame, ("hist",), schema=schema, overrides={"hist": "b"}
        )
        assert resolved == {"hist": "b"}, "an explicit name must not be overruled"

    def test_canonical_names_parse_as_the_degraded_path(self):
        """For a frame whose schema was lost — saved to CSV and read back."""
        frame = self._frame("macd_12_26_9__line", "macd_12_26_9__hist")
        assert resolve_role_columns(frame, ("line", "hist")) == {
            "line": "macd_12_26_9__line",
            "hist": "macd_12_26_9__hist",
        }

    def test_ambiguous_parse_refuses_rather_than_picking(self):
        """Two indicators claiming one role is not a coin toss."""
        frame = self._frame("macd_12_26_9__hist", "macd_5_35_5__hist")
        with pytest.raises(ValueError, match="cannot locate"):
            resolve_role_columns(frame, ("hist",))

    def test_refusal_names_the_roles_and_the_remedy(self):
        frame = self._frame("close", "volume")
        with pytest.raises(ValueError) as exc:
            resolve_role_columns(frame, ("line", "hist"))
        message = str(exc.value)
        assert "'line'" in message and "'hist'" in message
        assert "column_schema" in message or "result.column_schema" in message

    def test_unknown_role_is_refused(self):
        with pytest.raises(ValueError, match="unknown output role"):
            resolve_role_columns(self._frame("a"), ("not_a_role",))


# --------------------------------------------------------------------------- #
# zone_features
# --------------------------------------------------------------------------- #
class TestZoneFeaturesUsesRoles:

    def test_line_amplitude_comes_from_the_declared_line(self, macd_result):
        """`macd_amplitude` is the amplitude of the indicator's *line* role."""
        line_col = macd_result.column_schema.column("line")
        assert line_col, "MACD must declare a line role"

        zone = macd_result.zones[0]
        series = macd_result.data[line_col].iloc[zone.start_idx:zone.end_idx + 1]
        expected = float(series.max()) - float(series.min())

        assert zone.features["macd_amplitude"] == pytest.approx(expected)

    def test_dead_backward_compatibility_aliases_are_gone(self, macd_result):
        """The same four numbers under a second set of names, chosen by substring.

        `'ao' in name.lower()` is true for any column carrying those two letters,
        so the alias block was not only redundant but wrong. Nothing read them.
        """
        metadata = macd_result.zones[0].features["metadata"]
        for dead in ("hist_max", "hist_min", "hist_avg",
                     "rsi_max", "rsi_min", "rsi_avg", "rsi_std",
                     "ao_max", "ao_min", "ao_avg", "ao_std"):
            assert dead not in metadata, f"{dead} is a removed alias"

        # The universal statistics remain and say the same thing.
        for kept in ("oscillator_max", "oscillator_min",
                     "oscillator_avg", "oscillator_std"):
            assert kept in metadata

    def test_indicator_statistics_follow_roles_not_names(self, macd_result):
        """`max_macd` is the maximum of the *line* role, whatever it is called."""
        line_col = macd_result.column_schema.column("line")
        zone = macd_result.zones[0]
        series = macd_result.data[line_col].iloc[zone.start_idx:zone.end_idx + 1]
        assert zone.features["metadata"]["max_macd"] == pytest.approx(float(series.max()))


# --------------------------------------------------------------------------- #
# Preset
# --------------------------------------------------------------------------- #
class TestPresetAddressesByRole:

    def test_both_bases_resolve(self, data):
        from bquant.analysis.zones import analyze_macd_zones

        on_hist = analyze_macd_zones(data, zone_basis="histogram")
        on_line = analyze_macd_zones(data, zone_basis="line")

        assert len(on_hist.zones) > 0 and len(on_line.zones) > 0
        assert len(on_hist.zones) != len(on_line.zones), (
            "the two bases must actually address different series"
        )

    def test_unknown_basis_still_refused(self, data):
        from bquant.analysis.zones import analyze_macd_zones

        with pytest.raises(ValueError, match="zone_basis"):
            analyze_macd_zones(data, zone_basis="whatever")


# --------------------------------------------------------------------------- #
# IndicatorSchema
# --------------------------------------------------------------------------- #
class TestIndicatorSchemaDerivesFromTheIndicator:

    @pytest.mark.parametrize("schema_name, factory_name", [
        ("macd", "macd"),
        ("rsi", "rsi"),
        ("bollinger_bands", "bbands"),
    ])
    def test_required_fields_match_the_indicator(self, schema_name, factory_name):
        from bquant.data.schemas import IndicatorSchema

        declared = list(IndicatorSchema(schema_name).required_fields)
        produced = IndicatorFactory.create("custom", factory_name).get_output_columns()
        assert declared == produced, (
            "the schema must not keep its own copy of the output names"
        )

    def test_rsi_no_longer_declares_a_column_the_indicator_never_produces(self):
        """It used to require `rsi`; the indicator emits `rsi_14`.

        The embedded sample carries a TradingView column called `rsi`, which is
        the only reason the mistake looked correct.
        """
        from bquant.data.schemas import RSI_SCHEMA

        assert "rsi" not in RSI_SCHEMA.required_fields


# --------------------------------------------------------------------------- #
# Visualization
# --------------------------------------------------------------------------- #
class TestVisualizersAskForRoles:

    def test_plot_accepts_the_schema_from_the_result(self, macd_result):
        from bquant.visualization import FinancialCharts

        figure = FinancialCharts().plot_macd_with_zones(
            macd_result.data, macd_result.zones,
            column_schema=macd_result.column_schema,
        )
        assert figure is not None

    def test_canonical_names_alone_are_enough(self, macd_result):
        """Since C2b the emitted names carry the role, so the parse path works.

        This is the degraded path doing its job: a frame whose schema was lost
        still plots. It is not a licence to stop passing the schema — with two
        MACDs in one frame the parse is ambiguous and refuses, which the next
        test covers.
        """
        from bquant.visualization import FinancialCharts

        figure = FinancialCharts().plot_macd_with_zones(
            macd_result.data, macd_result.zones
        )
        assert figure is not None

    def test_plot_refuses_rather_than_guessing(self, macd_result):
        """With nothing to go on, it must not pick a column.

        Plotting the wrong column is how a chart comes to assert something
        nobody computed.
        """
        from bquant.visualization import FinancialCharts

        # Только исходные колонки сэмпла: ни схемы, ни канонических имён.
        raw = macd_result.data[["open", "high", "low", "close", "macd", "signal"]]
        with pytest.raises(ValueError, match="cannot locate"):
            FinancialCharts().plot_macd_with_zones(raw, macd_result.zones)

    def test_zone_visualizer_takes_the_same_route(self, macd_result):
        from bquant.visualization.zones import ZoneVisualizer

        figure = ZoneVisualizer().plot_macd_zones(
            macd_result.data, macd_result.zones,
            column_schema=macd_result.column_schema,
        )
        assert figure is not None
