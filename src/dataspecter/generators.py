"""Value generators: one per field type, each drawing from a random stream of its own."""

from __future__ import annotations

import hashlib
import itertools
import random
import re
import unicodedata
import uuid
from collections.abc import Callable, Sequence
from datetime import date, timedelta
from typing import Any

from dataspecter.domains import domain
from dataspecter.errors import GenerationError
from dataspecter.paths import reader
from dataspecter.spec import (
    BooleanField,
    ChoiceField,
    ConstantField,
    DateField,
    DatetimeField,
    Field,
    FloatField,
    IntegerField,
    PatternField,
    Placeholder,
    ReferenceField,
    SequenceField,
    TemplateField,
    UuidField,
    precision_bounds,
)

Generator = Callable[[], Any]

_NORMAL_ATTEMPTS = 100


def stream(seed: int, entity: str, field: str, purpose: str = "") -> random.Random:
    """Return the random stream for one field.

    The stream depends only on the seed and the field's own names, never on which other fields
    or entities exist, so editing one part of a spec leaves the values of the rest unchanged.
    Python's built-in ``hash()`` is salted per process, hence the explicit digest.
    """
    key = f"{seed}:{entity}:{field}" + (f":{purpose}" if purpose else "")
    return random.Random(int.from_bytes(hashlib.sha256(key.encode()).digest(), "big"))


class RowPick:
    """The row of a target entity chosen for the current row of a referencing entity.

    One pick is shared by every reference on the same link, so their values come from the same
    target row. Its stream is keyed by the target and link, not by any field, so adding or
    removing a reference field never changes which rows are chosen.
    """

    def __init__(self, seed: int, entity: str, target: str, link: str | None, rows: int):
        # "->" cannot occur in a field name, so this never collides with a field's stream.
        self._rng = stream(seed, entity, f"->{target}", link or "")
        self._rows = rows
        self.index = 0

    def advance(self) -> None:
        """Choose the target row for the next row. Call once per generated row."""
        self.index = self._rng.randrange(self._rows)


def field_generator(
    field: Field, seed: int, entity: str, name: str, read_reference: Generator | None = None
) -> Generator:
    """Return a function producing the next value of `field` on each call.

    `read_reference` returns the target field's value in the currently picked row, and is
    required for a reference.
    """
    generate = _build(field, stream(seed, entity, name), read_reference)
    if field.unique and not isinstance(field, SequenceField | UuidField):
        generate = _unique(generate, field, f"{entity}.{name}")
    if field.null_probability <= 0:
        return generate

    # Nulls are decided on a second stream, and the value is drawn regardless, so changing
    # null_probability never shifts the values themselves.
    nulls = stream(seed, entity, name, "null")
    probability = field.null_probability

    def generate_or_null() -> Any:
        value = generate()
        return None if nulls.random() < probability else value

    return generate_or_null


def _build(field: Field, rng: random.Random, read_reference: Generator | None) -> Generator:
    match field:
        case IntegerField() | FloatField():
            return _numeric(field, rng)
        case BooleanField():
            probability = field.true_probability
            return lambda: rng.random() < probability
        case ChoiceField():
            return _weighted(field.values, field.weights, rng)
        case DateField():
            first, days = field.min, (field.max - field.min).days
            return lambda: first + timedelta(days=rng.randint(0, days))
        case DatetimeField():
            start, seconds = field.min, int((field.max - field.min).total_seconds())
            return lambda: start + timedelta(seconds=rng.randint(0, seconds))
        case SequenceField():
            return itertools.count(field.start, field.step).__next__
        case UuidField():
            return lambda: str(uuid.UUID(int=rng.getrandbits(128), version=4))
        case ConstantField():
            value = field.value
            return lambda: value
        case PatternField():
            return _pattern(field, rng)
        case ReferenceField():
            if read_reference is None:
                raise ValueError("a reference field needs a reader for its target field")
            return read_reference
    raise TypeError(f"unsupported field: {field!r}")


def _weighted(items: Sequence[Any], weights: Sequence[float] | None, rng: random.Random):
    if weights is None:
        return lambda: rng.choice(items)
    cumulative = list(itertools.accumulate(weights))
    return lambda: rng.choices(items, cum_weights=cumulative)[0]


def _numeric(field: IntegerField | FloatField, rng: random.Random) -> Generator:
    precision = field.precision if isinstance(field, FloatField) else None
    if isinstance(field, IntegerField):
        shape, uniform = round, rng.randint
    elif precision is None:
        shape, uniform = float, rng.uniform
    else:

        def shape(value: float) -> float:
            return round(value, precision)

        def uniform(low: float, high: float) -> float:
            grid_low, grid_high = precision_bounds(low, high, precision)
            return min(max(shape(rng.uniform(low, high)), grid_low), grid_high)

    if field.ranges is not None:
        # Bind each range's bounds now; a bare lambda would see only the last range.
        samplers = [lambda low=item.min, high=item.max: uniform(low, high) for item in field.ranges]
        choose = _weighted(samplers, [item.weight for item in field.ranges], rng)
        return lambda: choose()()
    if field.distribution == "uniform":
        low, high = field.min, field.max
        return lambda: uniform(low, high)

    mean, stddev = field.mean, field.stddev
    low, high = precision_bounds(field.min, field.max, precision)

    def normal() -> float:
        # Redrawing keeps the bell shape near the bounds; clamping alone would pile values up
        # on them. The attempt limit guarantees an end when the bounds sit far out in a tail.
        for _ in range(_NORMAL_ATTEMPTS):
            value = shape(rng.gauss(mean, stddev))
            if (low is None or value >= low) and (high is None or value <= high):
                return value
        if low is not None and value < low:
            return shape(low)
        return shape(high)

    return normal


_DIGITS = "0123456789"
_PATTERN_ALPHABETS = {
    "digit": _DIGITS,
    "nonzero": _DIGITS[1:],
    "letter": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
}


def _pattern(field: PatternField, rng: random.Random) -> Generator:
    pieces = [(text, _PATTERN_ALPHABETS.get(kind)) for kind, text in field.segments]
    return lambda: "".join(
        text if alphabet is None else rng.choice(alphabet) for text, alphabet in pieces
    )


_REDRAWS = 100  # for a field whose values can be listed: after this many repeats, list them
_REDRAWS_UNBOUNDED = 1000  # for a field whose values cannot: after this many, give up


def _unique(generate: Generator, field: Field, label: str) -> Generator:
    """Wrap a generator so that it never returns the same value twice.

    Redrawing alone stalls when few values are left: with 499 of 500 used, a thousand draws
    still miss the last one about one time in seven. So a field whose values can be listed
    switches to taking the next unused one, which always finishes if there are enough values.
    """
    seen: set[Any] = set()
    values = domain(field)
    cursor = 0  # every listed value before this index has been used

    def generate_unique() -> Any:
        nonlocal cursor
        for _ in range(_REDRAWS if values else _REDRAWS_UNBOUNDED):
            value = generate()
            if value not in seen:
                seen.add(value)
                return value
        if values is None:
            raise GenerationError(
                f"{label} is unique, but {_REDRAWS_UNBOUNDED:,} draws in a row repeated earlier "
                "values; widen the field's range or drop 'unique'"
            )
        size, value_at = values
        while cursor < size:
            value = value_at(cursor)
            cursor += 1
            if value not in seen:
                seen.add(value)
                return value
        raise GenerationError(f"{label} is unique, and all {size:,} of its values are used")

    return generate_unique


# --- templates --------------------------------------------------------------------------------


def _ascii(text: str) -> str:
    """Replace accented letters with their plain form and drop anything else outside ASCII."""
    decomposed = unicodedata.normalize("NFKD", text)
    return decomposed.encode("ascii", "ignore").decode("ascii")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _ascii(text).lower()).strip("-")


def _title(text: str) -> str:
    return " ".join(word[:1].upper() + word[1:].lower() for word in text.split(" "))


_FILTERS: dict[str, Callable[[str], str]] = {
    "lower": str.lower,
    "upper": str.upper,
    "title": _title,
    "ascii": _ascii,
    "slug": _slug,
}


def _text(value: Any) -> str:
    """Write a value the way it would appear in a text file."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, date):  # covers datetime
        return value.isoformat()
    return str(value)


def template_renderer(
    field: TemplateField, seed: int, entity: str, name: str
) -> Callable[[dict[str, Any]], Any]:
    """Return a function building the template's value from a record that holds its inputs.

    The value is null when any input is null: "jane.@example.com" from a missing surname would
    be plausible-looking wrong data.
    """
    pieces: list[Any] = []
    for part in field.parts:
        if isinstance(part, Placeholder):
            filters = [_FILTERS[item] for item in part.filters]
            pieces.append((reader(part.target), filters))
        else:
            pieces.append(part)
    nulls = stream(seed, entity, name, "null") if field.null_probability > 0 else None
    probability = field.null_probability

    def render(record: dict[str, Any]) -> Any:
        made_null = nulls is not None and nulls.random() < probability
        out: list[str] = []
        for piece in pieces:
            if isinstance(piece, str):
                out.append(piece)
                continue
            read, filters = piece
            value = read(record)
            if value is None:
                return None
            text = _text(value)
            for apply in filters:
                text = apply(text)
            out.append(text)
        return None if made_null else "".join(out)

    return render
