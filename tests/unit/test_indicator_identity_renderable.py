"""The identity slug must be renderable as a name (G8 stage C2a).

Stage C1 introduced `IndicatorId`, whose slug is meant to become the column
name in stage C2b. It rendered any parameter it did not recognise through
`str()`, and `str()` never fails — it produces something. For the one indicator
in the registry that carries a list parameter, what it produced was:

    macd_preloaded_['macd', 'signal']_12_close_26_9_preloaded

A "name" with brackets, quotes, a comma and a space in it. Nothing raised;
nothing warned. Two more things were wrong in the same string: `source` appeared
as a parameter although the id already carries a `source` field — a duplicated
fact that can disagree with itself — and it appeared *twice* for that reason.

The defect was latent only because that indicator declared no roles, so no
column was ever built from the slug. On C2b every column name comes from a slug,
and a latent defect there stops being latent.

These tests pin three things:

* an unrenderable parameter is **refused at construction**, naming the parameter,
  rather than degrading into an unusable string;
* every indicator the factory can build produces a slug usable as a name — the
  sweep that found the defect, kept as a permanent check rather than a one-off;
* the roles an indicator declares and the columns it reports cannot drift,
  because the columns are now derived from the declaration instead of being
  written beside it as a second literal.

Design: ``devref/gaps/columns/g8_column_contract_design_2026-08-23.md`` §6, C2a.
"""

import re

import pytest

from bquant.indicators import IndicatorFactory
from bquant.indicators.schema import (
    IndicatorId,
    UnrenderableParameter,
    _canonical_value,
)

#: What a slug is allowed to consist of if it is to serve as a column name.
#: Deliberately stricter than "whatever pandas accepts as a label": pandas will
#: happily hold `"['macd', 'signal']"` as a column name, which is exactly how
#: the defect stayed invisible.
NAME_SAFE = re.compile(r"[A-Za-z0-9._+-]+")


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
class TestCanonicalValue:
    """Equal values must render identically; unrenderable ones must refuse."""

    @pytest.mark.parametrize(
        "value, expected",
        [
            (2, "2"),
            (2.0, "2"),          # the same period, so the same token
            (2.5, "2.5"),
            (-1, "-1"),
            (True, "true"),
            (False, "false"),
            (None, "none"),
            ("close", "close"),
        ],
    )
    def test_scalars(self, value, expected):
        assert _canonical_value(value) == expected

    def test_sequence_renders_element_wise(self):
        assert _canonical_value(["macd", "signal"]) == "macd-signal"
        assert _canonical_value(("macd",)) == "macd"

    def test_sequence_order_is_meaning(self):
        """Order must change the rendering.

        For `required_columns` the position says which output lives in which
        column, so two orders are two different indicators. Sorting here would
        merge them.
        """
        assert _canonical_value(["macd", "signal"]) != _canonical_value(["signal", "macd"])

    def test_empty_sequence_is_explicit(self):
        assert _canonical_value([]) == "empty"

    def test_nested_sequence(self):
        assert _canonical_value([[1, 2], [3]]) == "1-2-3"

    @pytest.mark.parametrize(
        "value",
        [
            {"a": 1},                      # mapping
            {1, 2},                        # set — iteration order is not identity
            object(),                      # anything with a junk repr
        ],
    )
    def test_unrenderable_refuses(self, value):
        with pytest.raises(UnrenderableParameter):
            _canonical_value(value)

    @pytest.mark.parametrize(
        "value",
        [
            "two words",       # whitespace
            "a,b",             # the separator that leaked from list repr
            "['macd']",        # the actual defect, as a string
            "a/b",
        ],
    )
    def test_strings_that_cannot_be_names_refuse(self, value):
        with pytest.raises(UnrenderableParameter):
            _canonical_value(value)

    def test_double_underscore_refused(self):
        """`__` separates slug from role, so a value carrying it is ambiguous."""
        with pytest.raises(UnrenderableParameter, match="double underscore"):
            _canonical_value("fast__slow")

    def test_single_underscore_allowed(self):
        assert _canonical_value("fast_slow") == "fast_slow"


# --------------------------------------------------------------------------- #
# Identity refuses early
# --------------------------------------------------------------------------- #
class TestIdentityValidation:

    def test_bad_parameter_refused_at_construction(self):
        """Not when someone later asks for `.slug` — at construction.

        A defect that only surfaces when a particular attribute is read is a
        defect that ships.
        """
        with pytest.raises(UnrenderableParameter) as exc:
            IndicatorId("custom", "x", {"columns": {"a": 1}})
        assert "columns" in str(exc.value), "the offending parameter must be named"
        assert "'x'" in str(exc.value), "the indicator must be named"

    def test_bad_name_refused(self):
        with pytest.raises(UnrenderableParameter):
            IndicatorId("custom", "my indicator")

    def test_list_parameter_now_renders(self):
        iid = IndicatorId(
            "preloaded", "macd_preloaded",
            {"required_columns": ["macd", "signal"], "fast": 12},
        )
        assert NAME_SAFE.fullmatch(iid.slug)
        assert "macd-signal" in iid.slug

    def test_slug_is_still_deterministic_over_kwargs_order(self):
        a = IndicatorId("custom", "macd", {"fast": 12, "slow": 26},
                        ("fast", "slow"))
        b = IndicatorId("custom", "macd", {"slow": 26, "fast": 12},
                        ("fast", "slow"))
        assert a.slug == b.slug == "macd_12_26"


# --------------------------------------------------------------------------- #
# The sweep that found the defect
# --------------------------------------------------------------------------- #
def _buildable_indicators():
    """Every indicator the factory can build with its defaults."""
    built = []
    for name, source in IndicatorFactory.list_indicators().items():
        if source == "library":
            continue  # library indicators are named by the library, see §4.3
        try:
            built.append((name, IndicatorFactory.create(source, name)))
        except Exception:
            continue
    return built


@pytest.mark.parametrize("name, indicator", _buildable_indicators(),
                         ids=lambda v: v if isinstance(v, str) else "")
def test_every_indicator_has_a_name_safe_slug(name, indicator):
    """The one-off sweep, kept.

    Running it by hand found one bad slug out of 164 registered indicators. A
    check that only ever runs once is a check that stops being true.
    """
    slug = indicator.get_indicator_id().slug
    assert NAME_SAFE.fullmatch(slug), f"{name} slugs to an unusable name: {slug!r}"
    assert "__" not in slug, (
        f"{name} slugs to {slug!r}, which contains the slug/role separator"
    )


@pytest.mark.parametrize("name, indicator", _buildable_indicators(),
                         ids=lambda v: v if isinstance(v, str) else "")
def test_declared_roles_and_reported_columns_cannot_drift(name, indicator):
    """Columns are derived from the role declaration, not written beside it.

    Two literals are two places to disagree. Stage A of this plan had to add a
    pin for exactly that kind of drift between declaration and reality; here the
    drift is removed by construction, and this asserts it stays removed.
    """
    roles = indicator.get_output_roles()
    if not roles:
        pytest.skip(f"{name} declares no roles")
    assert list(roles.values()) == list(indicator.get_output_columns()), (
        f"{name}: roles say {list(roles.values())}, "
        f"columns say {indicator.get_output_columns()}"
    )


def test_source_is_not_also_a_parameter():
    """`source` is a field of the identity, so it must not be a parameter too.

    It was both on the preloaded MACD, which put `preloaded` into the slug twice
    and created a fact that could disagree with itself.
    """
    for name, indicator in _buildable_indicators():
        iid = indicator.get_indicator_id()
        assert "source" not in iid.parameters, (
            f"{name} carries 'source' as a parameter while the identity already "
            f"records source={iid.source!r}"
        )


# --------------------------------------------------------------------------- #
# Preloaded: the source owns its names
# --------------------------------------------------------------------------- #
class TestPreloadedRoles:
    """A reader does not rename what it reads.

    The sample frame calls its columns `macd` and `signal` because that is what
    the TradingView export calls them. The preloaded indicator computes nothing,
    so it has no claim on those names — but role addressing must still work.
    That is the whole point of separating identity from role.
    """

    def _make(self, columns=None):
        from bquant.indicators.preloaded.macd import MACDPreloadedIndicator
        return MACDPreloadedIndicator(required_columns=columns) if columns \
            else MACDPreloadedIndicator()

    def test_roles_point_at_the_sources_own_names(self):
        assert self._make().get_output_roles() == {"line": "macd", "signal": "signal"}

    def test_roles_follow_the_requested_columns(self):
        assert self._make(["m", "s", "h"]).get_output_roles() == {
            "line": "m", "signal": "s", "hist": "h",
        }

    def test_partial_column_set(self):
        assert self._make(["m"]).get_output_roles() == {"line": "m"}

    def test_contract_exhausted_is_an_honest_empty(self):
        """Beyond the documented roles, `{}` — not a guess about column four."""
        assert self._make(["a", "b", "c", "d"]).get_output_roles() == {}


# --------------------------------------------------------------------------- #
# What C2a buys the caller
# --------------------------------------------------------------------------- #
class TestRoleAddressingOverPreloadedData:
    """Role addressing now reaches data the project did not compute.

    Before C2a the preloaded indicator declared no roles, so `indicator_role=`
    could not be used with pre-calculated data at all — the caller was back to
    knowing that the TradingView export happens to call its column `macd`. The
    names are still the source's; what changed is that they are now *declared*.
    """

    @pytest.fixture(scope="class")
    def data(self):
        from bquant.data.samples import get_sample_data
        return get_sample_data("tv_xauusd_1h")

    def test_role_and_name_address_the_same_series(self, data):
        from bquant.analysis.zones import analyze_zones

        by_name = (analyze_zones(data)
                   .with_indicator("preloaded", "macd_preloaded")
                   .detect_zones("zero_crossing", indicator_col="macd")
                   .build())
        by_role = (analyze_zones(data)
                   .with_indicator("preloaded", "macd_preloaded")
                   .detect_zones("zero_crossing", indicator_role="line")
                   .build())

        assert len(by_role.zones) == len(by_name.zones) > 0

    def test_schema_records_the_sources_own_names(self, data):
        from bquant.analysis.zones import analyze_zones

        result = (analyze_zones(data)
                  .with_indicator("preloaded", "macd_preloaded")
                  .detect_zones("zero_crossing", indicator_col="macd")
                  .build())

        assert result.column_schema.column("line") == "macd", (
            "the reader must not rename what it read"
        )
        indicator, role = result.column_schema.roles_of("signal")
        assert role == "signal"
        # The parameters of the original calculation — which the bare column
        # name `signal` never carried.
        assert indicator.parameters["fast"] == 12
        assert indicator.parameters["slow"] == 26
