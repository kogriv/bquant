"""Zone-type vocabulary as a declared abstraction (G20, stage 1).

The defect being closed: every universal layer downstream discriminated on the
zone-type *string* (``if zone_type == 'bull'``), fusing three independent
assumptions into one comparison — exactly two types, mutually opposite, spelled
``bull``/``bear``. A threshold or regime detector produced zones correctly and
then lost its directional metrics, its Markov chain and its hypothesis tests.

What is pinned here is the split that makes the fix possible:

* **type names are an open vocabulary** — a strategy invents them freely;
* **type properties are a closed one** — polarity is one of four values, and
  that is what universal code is allowed to discriminate on.

Nothing consumes the vocabulary yet (that is stages 2-5); these tests pin the
declaration side so the consumers have a contract to be written against.

Analysis: ``devref/gaps/zone_types/g20_zone_type_vocabulary_2026-08-24.md``
Design:   ``devref/gaps/zone_types/g20_zone_type_abstraction_design_2026-08-24.md``
"""

import pytest

from bquant.analysis.zones import ZoneType, ZoneVocabulary
from bquant.analysis.zones.detection import ZoneDetectionRegistry


# --------------------------------------------------------------------------- #
# 1. The descriptor
# --------------------------------------------------------------------------- #
class TestZoneType:
    def test_name_is_an_open_vocabulary(self):
        """Any non-empty name is legal — that is the point."""
        for name in ("bull", "overbought", "regime_a", "высокая_волатильность"):
            assert ZoneType(name).name == name

    @pytest.mark.parametrize("bad", ["", "   ", None, 42])
    def test_empty_or_non_string_name_is_rejected(self, bad):
        with pytest.raises((ValueError, TypeError)):
            ZoneType(bad)

    @pytest.mark.parametrize("polarity", [None, -1, 0, 1])
    def test_polarity_vocabulary_is_closed_and_complete(self, polarity):
        assert ZoneType("x", polarity=polarity).polarity == polarity

    @pytest.mark.parametrize("bad", [2, -2, "up", 1.0, True])
    def test_polarity_outside_the_closed_vocabulary_is_rejected(self, bad):
        """Guards the half of the design that must stay closed.

        `True` is included deliberately: `True == 1` in Python, so an unguarded
        membership test would silently accept a boolean and let a truthiness bug
        masquerade as a declared polarity.
        """
        if bad is True:
            # bool is an int subclass; accepting it would be a type confusion.
            assert isinstance(bad, int)
        with pytest.raises(ValueError):
            ZoneType("x", polarity=bad)

    def test_directional_means_a_sign_not_merely_declared(self):
        assert ZoneType("bull", polarity=+1).is_directional
        assert ZoneType("bear", polarity=-1).is_directional
        assert not ZoneType("neutral", polarity=0).is_directional
        assert not ZoneType("custom").is_directional

    def test_display_label_falls_back_to_the_name(self):
        assert ZoneType("bull").display_label == "bull"
        assert ZoneType("bull", label="Bullish").display_label == "Bullish"

    def test_bare_string_is_lifted_without_inventing_properties(self):
        """A plain name must not acquire a guessed polarity.

        This is the degradation path: a third-party strategy that declares only
        names keeps working, and universal layers will report directional
        analyses as not applicable rather than assuming a direction.
        """
        lifted = ZoneType.coerce("bull")
        assert lifted == ZoneType("bull")
        assert lifted.polarity is None
        assert not lifted.is_directional

    def test_descriptor_passes_through_coerce(self):
        declared = ZoneType("bull", polarity=+1)
        assert ZoneType.coerce(declared) is declared


# --------------------------------------------------------------------------- #
# 2. The vocabulary
# --------------------------------------------------------------------------- #
class TestZoneVocabulary:
    def test_names_preserve_declaration_order(self):
        vocab = ZoneVocabulary.coerce(["overbought", "neutral", "oversold"])
        assert vocab.names() == ["overbought", "neutral", "oversold"]

    def test_duplicate_names_are_rejected(self):
        with pytest.raises(ValueError, match="duplicate"):
            ZoneVocabulary.coerce([ZoneType("bull"), ZoneType("bull", polarity=+1)])

    def test_empty_means_runtime_determined_not_no_zones(self):
        """`is_declared` is the flag consumers read; emptiness alone is ambiguous.

        Treating an empty vocabulary as an empty allow-list would reproduce G19 —
        a filter that silently discards everything.
        """
        empty = ZoneVocabulary.coerce(None)
        assert empty.names() == []
        assert empty.is_declared is False
        assert ZoneVocabulary.coerce(["bull"]).is_declared is True

    def test_polarity_lookup_of_an_unknown_name_is_none(self):
        vocab = ZoneVocabulary.coerce([ZoneType("bull", polarity=+1)])
        assert vocab.polarity_of("bull") == 1
        assert vocab.polarity_of("bear") is None

    def test_declared_counterpart_wins(self):
        vocab = ZoneVocabulary.coerce([
            ZoneType("bull", polarity=+1, counterpart="bear"),
            ZoneType("bear", polarity=-1, counterpart="bull"),
        ])
        assert vocab.counterpart_of("bull") == "bear"
        assert vocab.contrast_pairs() == [("bear", "bull")]

    def test_counterpart_is_derived_when_the_opposite_sign_is_unique(self):
        vocab = ZoneVocabulary.coerce([
            ZoneType("bull", polarity=+1),
            ZoneType("bear", polarity=-1),
        ])
        assert vocab.counterpart_of("bull") == "bear"
        assert vocab.contrast_pairs() == [("bear", "bull")]

    def test_derivation_refuses_to_guess_when_a_sign_is_shared(self):
        """The case the abstraction exists for: more than two types.

        With `strong_bull` and `weak_bull` both at +1 there is no single answer,
        so derivation must return nothing rather than pick one.
        """
        vocab = ZoneVocabulary.coerce([
            ZoneType("strong_bull", polarity=+1),
            ZoneType("weak_bull", polarity=+1),
            ZoneType("bear", polarity=-1),
        ])
        assert vocab.counterpart_of("bear") is None
        assert vocab.contrast_pairs() == []

    def test_declaration_still_works_where_derivation_cannot(self):
        """Explicit declaration is the primary path precisely for this case."""
        vocab = ZoneVocabulary.coerce([
            ZoneType("strong_bull", polarity=+1, counterpart="bear"),
            ZoneType("weak_bull", polarity=+1),
            ZoneType("bear", polarity=-1, counterpart="strong_bull"),
        ])
        assert vocab.contrast_pairs() == [("bear", "strong_bull")]

    def test_neutral_has_no_counterpart(self):
        vocab = ZoneVocabulary.coerce([
            ZoneType("overbought", polarity=+1, counterpart="oversold"),
            ZoneType("neutral", polarity=0),
            ZoneType("oversold", polarity=-1, counterpart="overbought"),
        ])
        assert vocab.counterpart_of("neutral") is None
        assert vocab.contrast_pairs() == [("overbought", "oversold")]

    def test_bare_names_yield_no_pairs(self):
        """Undeclared properties must not be back-filled by convention.

        'bull' and 'bear' look like an obvious pair to a human. Pairing them
        without a declaration would be exactly the hardcode being removed.
        """
        assert ZoneVocabulary.coerce(["bull", "bear"]).contrast_pairs() == []


# --------------------------------------------------------------------------- #
# 3. What the shipped strategies declare
# --------------------------------------------------------------------------- #
class TestShippedStrategyDeclarations:
    def test_every_strategy_is_reachable_through_the_registry(self):
        expected = {"zero_crossing", "threshold", "line_crossing", "preloaded", "combined"}
        assert expected <= set(ZoneDetectionRegistry.list_strategies())

    @pytest.mark.parametrize("strategy", ["zero_crossing", "line_crossing"])
    def test_two_line_strategies_declare_an_opposed_pair(self, strategy):
        vocab = ZoneDetectionRegistry.get_vocabulary(strategy)
        assert vocab.names() == ["bull", "bear"]
        assert vocab.polarity_of("bull") == 1
        assert vocab.polarity_of("bear") == -1
        assert vocab.contrast_pairs() == [("bear", "bull")]

    def test_threshold_declares_three_types_with_one_contrast_pair(self):
        vocab = ZoneDetectionRegistry.get_vocabulary("threshold")
        assert vocab.names() == ["overbought", "neutral", "oversold"]
        assert vocab.polarity_of("neutral") == 0
        assert vocab.contrast_pairs() == [("overbought", "oversold")]

    @pytest.mark.parametrize("strategy", ["preloaded", "combined"])
    def test_runtime_determined_strategies_declare_nothing_statically(self, strategy):
        """`preloaded` reads types from data, `combined` from the caller's rules.

        Previously they declared the placeholders `['any']` and `['custom']` —
        names no zone is ever actually labelled with.
        """
        vocab = ZoneDetectionRegistry.get_vocabulary(strategy)
        assert vocab.is_declared is False
        assert vocab.names() == []

    def test_metadata_names_are_derived_from_the_vocabulary(self):
        """One source of truth: the displayed list must not drift from the descriptors."""
        for name in ZoneDetectionRegistry.list_strategies():
            info = ZoneDetectionRegistry.get_info(name)
            assert info["supported_zones"] == ZoneDetectionRegistry.get_vocabulary(name).names()

    def test_unknown_strategy_is_an_error_not_an_empty_vocabulary(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            ZoneDetectionRegistry.get_vocabulary("nonexistent")


# --------------------------------------------------------------------------- #
# 4. Nothing consumes it yet — stage 1 must not change behaviour
# --------------------------------------------------------------------------- #
def test_unset_zone_types_means_no_filter():
    """`None` no longer becomes `['bull', 'bear']` (G19).

    The old default silenced two of the five shipped strategies: `threshold` emits
    `overbought`/`neutral`/`oversold` and `combined` emits whatever the caller's
    rules say, so the intersection with `['bull','bear']` was empty and both
    returned a successful, empty result.
    """
    from bquant.analysis.zones.detection import ZoneDetectionConfig

    config = ZoneDetectionConfig()
    assert config.zone_types is None
    for zone_type in ("bull", "bear", "overbought", "neutral", "regime_a"):
        assert config.accepts(zone_type)


def test_explicit_zone_types_still_filter():
    from bquant.analysis.zones.detection import ZoneDetectionConfig

    config = ZoneDetectionConfig(zone_types=["overbought", "oversold"])
    assert config.accepts("overbought")
    assert not config.accepts("neutral")
