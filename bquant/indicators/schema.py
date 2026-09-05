"""Identity and roles for indicator output columns (G8 stage C).

A column name used to carry two unrelated things at once — **identity** (which
indicator instance produced this series) and **role** (what the series means) —
fused into one literal, with nothing owning the mapping between them.
``macd_hist`` is "MACD with some parameters" plus "the histogram", glued
together; every producer invented a string and every consumer guessed one. The
moment the data entered a ``DataFrame``, the knowledge of what each column meant
was gone.

Three consequences followed (measured in
``devref/gaps/columns/g8_column_contract_measurement_2026-08-23.md``):

* three naming conventions across five shipped indicators, and where the period
  is absent from the name, two instances with different settings claim the same
  column and silently overwrite one another;
* a silent overwrite at the merge point;
* library columns labelled with the parameters of *registration* rather than of
  the call — the worst of the three, because it does not withhold information,
  it asserts something false.

This module separates the two halves:

* :class:`IndicatorId` — identity, as a deterministic slug over normalized
  parameters;
* :class:`OutputRole` — role, from a closed vocabulary with an explicit
  extension point;
* :class:`ColumnSchema` — the mapping ``(identity, role) -> column``, kept
  beside the frame so it survives the merge that destroys the objects.

The split of what is open and what is closed is deliberate, and mirrors the one
made for zone types (``ZoneType``/``ZoneVocabulary``):

    **Closed is what universal code discriminates on; open is what the domain
    invents.**

Column names stay open — pandas-ta calls its output ``RSI_50`` and that is its
right. Roles are closed, because they are what a consumer asks for.
"""

from __future__ import annotations

import re
from collections.abc import Mapping as _MappingABC
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from ..core.logging_config import get_logger

logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Roles
# --------------------------------------------------------------------------- #
#: Roles the package understands. Closed on purpose: a consumer asks for "the
#: histogram", and that request must mean the same thing everywhere. Custom
#: indicators that genuinely need something else register it through
#: :func:`register_role` rather than inventing a free string, so the vocabulary
#: stays enumerable.
_CORE_ROLES: Tuple[str, ...] = (
    "value",    # the single output of a one-series indicator (RSI, SMA, EMA)
    "line",     # the primary line of a multi-series indicator (MACD)
    "signal",   # its signal line
    "hist",     # their difference
    "upper",    # band edges (Bollinger, Keltner, ...)
    "middle",
    "lower",
    "width",    # derived band measures
    "percent",
)

_EXTRA_ROLES: Dict[str, str] = {}


def register_role(role: str, description: str) -> None:
    """Add a role to the vocabulary.

    The extension point exists so that a custom indicator with a genuinely new
    kind of output is not forced to smuggle it through a free-form string. It
    still has to say what the role means, because that description is what a
    reader of somebody else's indicator has to go on.
    """
    if not isinstance(role, str) or not role.strip():
        raise ValueError(f"role must be a non-empty string, got {role!r}")
    if role in _CORE_ROLES:
        raise ValueError(f"'{role}' is already a core role")
    if not description or not description.strip():
        raise ValueError(f"role '{role}' must be registered with a description")
    _EXTRA_ROLES[role] = description
    logger.debug("Registered output role '%s': %s", role, description)


def known_roles() -> Tuple[str, ...]:
    """Every role currently understood, core first."""
    return _CORE_ROLES + tuple(sorted(_EXTRA_ROLES))


def validate_role(role: str) -> str:
    """Return ``role`` if the vocabulary knows it; raise otherwise."""
    if role in _CORE_ROLES or role in _EXTRA_ROLES:
        return role
    raise ValueError(
        f"unknown output role {role!r}. Known roles: {list(known_roles())}. "
        "Register a new one with register_role(role, description) rather than "
        "passing a free string — the vocabulary of roles is closed so that "
        "universal code can discriminate on it."
    )


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #
#: Characters a rendered parameter may consist of. The slug becomes a column
#: name, so anything that is not addressable as a name is not admissible here:
#: no whitespace, no quotes, no brackets. ``.`` and ``-`` are kept because
#: numbers need them (``2.5``, ``-1``); ``_`` is kept because it is harmless
#: inside a token, but a **doubled** underscore is rejected separately — that is
#: the separator :meth:`IndicatorId.column` uses, and a value containing it
#: would make the reverse parse ambiguous.
_TOKEN_RE = re.compile(r"[A-Za-z0-9._+-]+")


class UnrenderableParameter(ValueError):
    """A parameter value cannot be rendered into an identity.

    Raised instead of falling back to ``str()``. The fallback is what produced
    ``macd_preloaded_['macd', 'signal']_12_close_26_9`` — a "name" carrying
    brackets, quotes and a space. It did not fail; it produced something
    unusable and said nothing, which is the failure mode this whole gap is
    about.
    """


def _canonical_value(value: Any) -> str:
    """Render a parameter value so equal values render identically.

    ``2`` and ``2.0`` are the same period and must not produce two different
    slugs; pandas-ta's own ``BBL_5_2.0_2.0`` shows where the inconsistency ends
    up. Floats that are whole numbers collapse to the integer form.

    Sequences render element-wise joined by ``-`` and stay **order-sensitive**,
    because for a positional parameter (which column holds which output) order
    is meaning, not presentation.

    Anything that has no such rendering raises :class:`UnrenderableParameter`
    rather than degrading to ``str()``.
    """
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        rendered = repr(round(value, 10)).rstrip("0").rstrip(".")
        return _validated_token(rendered, value)
    if isinstance(value, str):
        return _validated_token(value, value)
    if isinstance(value, (list, tuple)):
        if not value:
            return "empty"
        return "-".join(_canonical_value(item) for item in value)
    raise UnrenderableParameter(
        f"cannot render {type(value).__name__} {value!r} into an indicator "
        "identity. Identity has to be reproducible and usable as a column "
        "name; pass a scalar or a sequence of scalars, or keep this out of the "
        "indicator's parameters."
    )


def _validated_token(rendered: str, original: Any) -> str:
    """Return ``rendered`` if it is usable inside a name; raise otherwise."""
    if not _TOKEN_RE.fullmatch(rendered):
        raise UnrenderableParameter(
            f"parameter value {original!r} renders as {rendered!r}, which "
            "cannot be part of a column name. Allowed characters: letters, "
            "digits, '.', '_', '+', '-'."
        )
    if "__" in rendered:
        raise UnrenderableParameter(
            f"parameter value {original!r} contains a double underscore, which "
            "IndicatorId.column() uses to separate the slug from the role; a "
            "value carrying it would make the reverse parse ambiguous."
        )
    return rendered


class FrozenParameters(_MappingABC):
    """An immutable, hashable, picklable mapping for :attr:`IndicatorId.parameters`.

    A frozen dataclass holding a plain ``dict`` was frozen in name only: the
    dict could be edited through the attribute, and with it the slug and the
    hash of an id already sitting in a set or a schema (G58).
    ``types.MappingProxyType`` would do the freezing but cannot be pickled, and
    the id travels inside cached and saved results.
    """

    __slots__ = ("_items",)

    def __init__(self, items: Mapping[str, Any]):
        self._items = tuple((str(k), v) for k, v in dict(items).items())

    def __getitem__(self, key: str) -> Any:
        for k, v in self._items:
            if k == key:
                return v
        raise KeyError(key)

    def __iter__(self):
        return (k for k, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __hash__(self) -> int:
        return hash(self._items)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, _MappingABC):
            return dict(self.items()) == dict(other.items())
        return NotImplemented

    def __repr__(self) -> str:
        return f"FrozenParameters({dict(self._items)!r})"

    def __reduce__(self):
        return (FrozenParameters, (dict(self._items),))


@dataclass(frozen=True)
class IndicatorId:
    """Which indicator instance produced a series.

    The slug is deterministic over *normalized* parameters, and normalization is
    the substance rather than a detail:

    * **order is fixed by the declaration**, not by the order of ``**kwargs`` —
      otherwise ``MACD(fast=12, slow=26)`` and ``MACD(slow=26, fast=12)`` would
      slug differently;
    * **defaults are made explicit** — ``rsi()`` and ``rsi(period=14)`` must
      agree;
    * **numbers are canonicalised** — ``2`` and ``2.0`` are one value.

    Attributes:
        source: ``'custom'`` | ``'preloaded'`` | ``'pandas_ta'`` | ``'talib'``.
        name: Indicator name as the factory knows it (``'macd'``, ``'bbands'``).
        parameters: Full parameter set, defaults included.
        parameter_order: Names in declaration order. Parameters absent from it
            are appended alphabetically, so an incomplete declaration degrades
            to a stable slug rather than an unstable one.
    """

    source: str
    name: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    parameter_order: Tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError(f"IndicatorId.name must be a non-empty string, got {self.name!r}")
        # Freeze the mapping for real: a copy protected against the caller's
        # reference, and immutable through the attribute as well.
        object.__setattr__(self, "parameters", FrozenParameters(self.parameters))
        object.__setattr__(self, "parameter_order", tuple(self.parameter_order))
        _validated_token(self.name, self.name)
        # Render every parameter now, so an identity that cannot be rendered
        # fails **here**, naming the offending parameter, instead of surfacing
        # much later as an unusable column name.
        for key, value in self.parameters.items():
            try:
                _canonical_value(value)
            except UnrenderableParameter as exc:
                raise UnrenderableParameter(
                    f"indicator '{self.name}': parameter '{key}' — {exc}"
                ) from None

    def _ordered_parameters(self) -> Tuple[Tuple[str, Any], ...]:
        declared = [p for p in self.parameter_order if p in self.parameters]
        remaining = sorted(set(self.parameters) - set(declared))
        return tuple((p, self.parameters[p]) for p in declared + remaining)

    @property
    def slug(self) -> str:
        """``'macd_12_26_9'``, ``'rsi_14'``, ``'bbands_20_2'`` — stable and reproducible."""
        parts = [self.name] + [
            _canonical_value(value) for _, value in self._ordered_parameters()
        ]
        return "_".join(parts)

    def column(self, role: str) -> str:
        """Canonical column name for one of this instance's outputs.

        ``{slug}__{role}``, except that a lone ``value`` output is just the slug:
        ``rsi_14`` reads better than ``rsi_14__value`` and stays unambiguous.

        The separator is a **double** underscore because indicator names and
        parameters contain single ones; with one underscore the reverse parse
        would be ambiguous.
        """
        validate_role(role)
        if role == "value":
            return self.slug
        return f"{self.slug}__{role}"

    def __hash__(self) -> int:
        # The slug renders the parameters canonically and equality compares the
        # same inputs, so hashing on it stays consistent with `__eq__`.
        return hash((self.source, self.name, self.slug, self.parameter_order))

    @property
    def key(self) -> str:
        """``'custom.macd_12_26_9'`` — identity **including the source**.

        The slug alone is not an identity: a custom RSI and a pandas-ta RSI with
        the same parameters share ``rsi_14`` and are two different series
        (until G58 the second overwrote the first in :class:`ColumnSchema`).
        """
        return f"{self.source}.{self.slug}"

    def __str__(self) -> str:
        return self.key


def parse_column(column: str) -> Optional[Tuple[str, str]]:
    """Recover ``(slug, role)`` from a canonical column name — **degraded path**.

    This is deliberately not the primary way to learn what a column means. The
    mapping lives in :class:`ColumnSchema`, beside the frame; parsing the string
    is the fallback for when the schema has been lost — the caller saved the
    frame to CSV and read it back.

    It returns a *guess*, and callers must treat it as one. If this ever becomes
    the main path, the string has silently become the source of truth again and
    G8 is back under a new number.

    Returns ``None`` when the name does not follow the convention, which is the
    common case for library columns (``RSI_50``) — those are the library's to
    name, and we do not overwrite them.
    """
    if "__" not in column:
        return None
    slug, _, role = column.rpartition("__")
    if not slug or role not in known_roles():
        return None
    return slug, role


# --------------------------------------------------------------------------- #
# The side-car
# --------------------------------------------------------------------------- #
@dataclass
class ColumnSchema:
    """``(indicator, role) -> column name``, kept beside the frame.

    Once indicator output is merged into a ``DataFrame`` the objects are gone and
    only strings remain. That is precisely where the knowledge used to be lost,
    so the mapping has to survive the merge — hence a side-car rather than
    anything encoded in the names.

    A consumer asks "give me the histogram of the MACD this analysis used"
    instead of guessing ``'macd_hist'``.
    """

    #: ``(indicator key, role) -> column``; the key is :attr:`IndicatorId.key`,
    #: source included, so two sources with the same slug stay two entries.
    entries: Dict[Tuple[str, str], str] = field(default_factory=dict)
    indicators: Dict[str, IndicatorId] = field(default_factory=dict)

    def register(self, indicator: IndicatorId, columns: Mapping[str, str]) -> None:
        """Record where each role of ``indicator`` landed in the frame."""
        self.indicators[indicator.key] = indicator
        for role, column in columns.items():
            validate_role(role)
            self.entries[(indicator.key, role)] = column

    def column(self, role: str, indicator: Optional[IndicatorId] = None) -> Optional[str]:
        """Column holding ``role``; ``None`` if this schema does not know it.

        With a single indicator registered — the common case — the indicator may
        be omitted. With several, omitting it is ambiguous and returns ``None``
        rather than picking one, for the same reason
        ``ZoneVocabulary.counterpart_of`` refuses to guess.
        """
        validate_role(role)
        if indicator is not None:
            return self.entries.get((indicator.key, role))

        matches = [col for (_, r), col in self.entries.items() if r == role]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            logger.debug(
                "Role '%s' is provided by %d indicators; name one explicitly.",
                role, len(matches),
            )
        return None

    def roles_of(self, column: str) -> Optional[Tuple[IndicatorId, str]]:
        """Which indicator and role a column holds, from the schema itself."""
        for (key, role), name in self.entries.items():
            if name == column:
                return self.indicators[key], role
        return None

    def roles(self) -> Tuple[str, ...]:
        """Roles present in this schema, in vocabulary order."""
        present = {role for _, role in self.entries}
        return tuple(r for r in known_roles() if r in present)

    def to_dict(self) -> Dict[str, Any]:
        """Serializable form, for results that get written to disk."""
        return {
            "entries": {f"{key}|{role}": col for (key, role), col in self.entries.items()},
            "indicators": {
                key: {
                    "source": ind.source,
                    "name": ind.name,
                    "parameters": dict(ind.parameters),
                    "parameter_order": list(ind.parameter_order),
                }
                for key, ind in self.indicators.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Optional[Mapping[str, Any]]) -> "ColumnSchema":
        if not data:
            return cls()
        indicators = {}
        for key, spec in (data.get("indicators") or {}).items():
            indicator = IndicatorId(
                source=spec["source"],
                name=spec["name"],
                parameters=spec.get("parameters", {}),
                parameter_order=tuple(spec.get("parameter_order", ())),
            )
            if key != indicator.key:
                # Written before G58: keyed by slug, source dropped from the key.
                raise ValueError(
                    f"column schema entry {key!r} is keyed without its source "
                    f"(expected {indicator.key!r}); this artifact was written before "
                    "2026-09-05 and cannot tell two sources with one slug apart. "
                    "Recompute the analysis."
                )
            indicators[key] = indicator
        entries = {}
        for key, column in (data.get("entries") or {}).items():
            indicator_key, _, role = key.partition("|")
            if indicator_key not in indicators:
                raise ValueError(
                    f"column schema entry {key!r} names an indicator the schema does not "
                    f"describe; known: {sorted(indicators)}"
                )
            entries[(indicator_key, role)] = column
        return cls(entries=entries, indicators=indicators)

    def __bool__(self) -> bool:
        return bool(self.entries)


# --------------------------------------------------------------------------- #
# Resolving roles against a frame
# --------------------------------------------------------------------------- #
def resolve_role_columns(
    data: Any,
    roles: Iterable[str],
    schema: Optional["ColumnSchema"] = None,
    overrides: Optional[Mapping[str, str]] = None,
) -> Dict[str, str]:
    """Find the column holding each requested role in ``data``.

    A consumer that needs "the histogram" used to write ``data['macd_hist']``
    and be wrong the moment the indicator was configured differently, or came
    from a library, or was one of two MACDs in the same frame. This is what it
    writes instead.

    Resolution order, most authoritative first:

    1. **``overrides``** — the caller names the column outright. The escape
       hatch for frames that came from somewhere else entirely.
    2. **``schema``** — the mapping recorded when the indicator was computed.
       This is the intended path.
    3. **parsing the column names** — the degraded path (:func:`parse_column`).
       It is a guess, and it is here only for frames whose schema was lost, e.g.
       saved to CSV and read back.

    Raises:
        ValueError: naming the roles it could not place and how to supply them.
            Refusing is the point: silently plotting the wrong column is how a
            chart comes to assert something nobody computed.
    """
    roles = tuple(roles)
    for role in roles:
        validate_role(role)

    overrides = dict(overrides or {})
    columns = list(getattr(data, "columns", []))
    resolved: Dict[str, str] = {}
    missing = []

    # The degraded path, computed once: role -> columns whose *name* claims it.
    by_parsed_role: Dict[str, list] = {}
    for column in columns:
        parsed = parse_column(str(column))
        if parsed:
            by_parsed_role.setdefault(parsed[1], []).append(column)

    for role in roles:
        column = overrides.get(role)
        if column is None and schema is not None:
            column = schema.column(role)
        if column is None:
            candidates = by_parsed_role.get(role, [])
            if len(candidates) == 1:
                column = candidates[0]
            elif len(candidates) > 1:
                logger.debug(
                    "Role '%s' is claimed by %d column names (%s); name one "
                    "explicitly rather than letting the guess pick.",
                    role, len(candidates), candidates,
                )
        if column is not None and column in columns:
            resolved[role] = column
        else:
            missing.append(role)

    if missing:
        raise ValueError(
            f"cannot locate column(s) for role(s) {missing} in this frame. "
            f"Columns present: {columns}. Pass the schema recorded when the "
            f"indicator was computed (result.column_schema), or name the "
            f"columns directly."
        )
    return resolved


__all__ = [
    "IndicatorId",
    "FrozenParameters",
    "resolve_role_columns",
    "UnrenderableParameter",
    "ColumnSchema",
    "register_role",
    "known_roles",
    "validate_role",
    "parse_column",
]
