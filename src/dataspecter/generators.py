"""Value generators: one per field type, each drawing from a random stream of its own."""

from __future__ import annotations

import hashlib
import itertools
import random
import uuid
from collections.abc import Callable, Sequence
from datetime import timedelta
from typing import Any

from dataspecter.spec import (
    BooleanField,
    ChoiceField,
    ConstantField,
    DateField,
    DatetimeField,
    Field,
    FloatField,
    IntegerField,
    ReferenceField,
    SequenceField,
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


def field_generator(
    field: Field, seed: int, entity: str, name: str, referenced: Sequence[Any] | None = None
) -> Generator:
    """Return a function producing the next value of `field` on each call.

    `referenced` holds the target field's generated values, and is required for a reference.
    """
    generate = _build(field, stream(seed, entity, name), referenced)
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


def _build(field: Field, rng: random.Random, referenced: Sequence[Any] | None) -> Generator:
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
        case ReferenceField():
            if referenced is None:
                raise ValueError("a reference field needs the values of its target field")
            return lambda: rng.choice(referenced)
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
