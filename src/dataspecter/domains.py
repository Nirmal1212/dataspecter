"""The set of values a field can produce, where that set is finite and can be enumerated.

Used to reject a `unique` field that cannot fill its entity, and to finish a unique field that
is close to running out without drawing at random for ever.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Callable
from datetime import timedelta
from itertools import accumulate
from typing import Any

from dataspecter.spec import (
    ChoiceField,
    DateField,
    DatetimeField,
    Field,
    FloatField,
    IntegerField,
    NameField,
    PatternField,
    PhoneField,
    precision_bounds,
)

# (number of distinct values, function returning the value at an index)
Domain = tuple[int, Callable[[int], Any]]

_DIGITS = "0123456789"
_ALPHABETS = {
    "digit": _DIGITS,
    "nonzero": _DIGITS[1:],
    "letter": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "two_to_nine": _DIGITS[2:],
    "six_to_nine": _DIGITS[6:],
}


def domain(field: Field) -> Domain | None:
    """Return the field's values as a size and an index function, or None if unbounded."""
    match field:
        case IntegerField():
            return _spans(_bounds(field), lambda index: index)
        case FloatField() if field.precision is not None and field.precision <= 15:
            precision, scale = field.precision, 10**field.precision
            grid = []
            bounds = _bounds(field)
            if bounds is None:
                return None
            for low, high in bounds:
                grid_low, grid_high = precision_bounds(low, high, precision)
                grid.append((round(grid_low * scale), round(grid_high * scale)))
            return _spans(grid, lambda index: round(index / scale, precision))
        case DateField():
            first = field.min
            return (field.max - first).days + 1, lambda index: first + timedelta(days=index)
        case DatetimeField():
            start = field.min
            seconds = int((field.max - start).total_seconds())
            return seconds + 1, lambda index: start + timedelta(seconds=index)
        case ChoiceField():
            weights = field.weights or (1,) * len(field.values)
            values = list(
                dict.fromkeys(
                    value
                    for value, weight in zip(field.values, weights, strict=True)
                    if value is not None and weight > 0
                )
            )
            return len(values), values.__getitem__
        case PatternField() | PhoneField():
            return _pattern_domain(field)
        case NameField():
            from dataspecter.realistic import name_values  # realistic builds on this module

            return name_values(field)
    return None


def _bounds(field: IntegerField | FloatField) -> list[tuple[float, float]] | None:
    """The inclusive ranges a numeric field draws from, or None if it has an open end."""
    if field.ranges is not None:
        return [(item.min, item.max) for item in field.ranges if item.weight > 0]
    if field.min is None or field.max is None:
        return None
    return [(field.min, field.max)]


def _spans(bounds: list[tuple[int, int]] | None, convert: Callable[[int], Any]) -> Domain | None:
    """Build a domain from integer ranges, merging any that overlap."""
    if bounds is None:
        return None
    merged: list[list[int]] = []
    for low, high in sorted(bounds):
        if merged and low <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], high)
        else:
            merged.append([low, high])
    ends = list(accumulate(high - low + 1 for low, high in merged))  # running totals

    def value_at(index: int) -> Any:
        span = bisect_right(ends, index)
        before = ends[span - 1] if span else 0
        return convert(merged[span][0] + index - before)

    return (ends[-1] if ends else 0), value_at


def _pattern_domain(field: PatternField | PhoneField) -> Domain:
    alphabets = [_ALPHABETS[kind] for kind, _ in field.segments if kind != "literal"]
    size = 1
    for alphabet in alphabets:
        size *= len(alphabet)

    def value_at(index: int) -> str:
        chosen = []
        for alphabet in reversed(alphabets):
            index, position = divmod(index, len(alphabet))
            chosen.append(alphabet[position])
        chosen.reverse()
        characters = iter(chosen)
        return "".join(
            text if kind == "literal" else next(characters) for kind, text in field.segments
        )

    return size, value_at
