"""What each field type produces (data-generation capability).

Statistical checks use a fixed seed, so they are deterministic; the tolerances come from the
spec and are about ten standard errors wide.
"""

import uuid
from collections import Counter
from datetime import date, datetime
from statistics import fmean

import pytest

from dataspecter.generators import RowPick, field_generator, stream
from dataspecter.spec import load_spec

from .helpers import spec_of

ROWS = 10_000


def draw(field: dict, rows: int = ROWS, seed: int = 1) -> list:
    model = load_spec(spec_of(field)).entities["thing"].fields["value"]
    generate = field_generator(model, seed, "thing", "value")
    return [generate() for _ in range(rows)]


def share(values: list, predicate) -> float:
    return sum(1 for value in values if predicate(value)) / len(values)


# --- random streams ---------------------------------------------------------------------------


def test_same_inputs_give_the_same_stream():
    first = [stream(42, "customer", "age").random() for _ in range(5)]
    second = [stream(42, "customer", "age").random() for _ in range(5)]

    assert first == second


def test_streams_differ_by_seed_entity_field_and_purpose():
    samples = {
        stream(42, "customer", "age").random(),
        stream(43, "customer", "age").random(),
        stream(42, "order", "age").random(),
        stream(42, "customer", "tier").random(),
        stream(42, "customer", "age", "null").random(),
    }

    assert len(samples) == 5


# --- numeric ----------------------------------------------------------------------------------


def test_integer_within_range_including_both_ends():
    values = draw({"type": "integer", "min": 18, "max": 90})

    assert all(type(value) is int for value in values)
    assert min(values) == 18
    assert max(values) == 90


def test_uniform_float_within_range():
    values = draw({"type": "float", "min": 0, "max": 100})

    assert all(type(value) is float and 0 <= value <= 100 for value in values)


def test_float_precision():
    values = draw({"type": "float", "min": 0, "max": 100, "precision": 2})

    assert all(round(value, 2) == value for value in values)
    assert all(0 <= value <= 100 for value in values)


def test_float_precision_keeps_values_inside_fractional_bounds():
    values = draw({"type": "float", "min": 0.123, "max": 0.987, "precision": 1})

    assert set(values) <= {0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9}


def test_normal_values_centre_on_the_mean():
    values = draw({"type": "float", "distribution": "normal", "mean": 40, "stddev": 12})

    assert abs(fmean(values) - 40) < 1.2


def test_normal_bounds_are_respected():
    field = {"type": "float", "distribution": "normal", "mean": 40, "stddev": 12}
    values = draw({**field, "min": 18, "max": 90})

    assert min(values) >= 18
    assert max(values) <= 90


def test_normal_integer_field_produces_whole_numbers():
    field = {"type": "integer", "distribution": "normal", "mean": 40, "stddev": 12}
    values = draw({**field, "min": 18, "max": 90})

    assert all(type(value) is int and 18 <= value <= 90 for value in values)


def test_normal_with_bounds_far_in_the_tail_still_terminates():
    field = {"type": "float", "distribution": "normal", "mean": 0, "stddev": 1}
    values = draw({**field, "min": 50, "max": 60}, rows=20)

    assert set(values) == {50.0}


AGE_RANGES = [(18, 35), (36, 60), (61, 90)]


def age_field(weights: list[float]) -> dict:
    ranges = [
        {"min": low, "max": high, "weight": weight}
        for (low, high), weight in zip(AGE_RANGES, weights, strict=True)
    ]
    return {"type": "integer", "ranges": ranges}


def test_weighted_range_proportions_follow_the_weights():
    values = draw(age_field([0.7, 0.25, 0.05]))

    assert all(18 <= value <= 90 for value in values)
    for (low, high), expected in zip(AGE_RANGES, [0.70, 0.25, 0.05], strict=True):
        assert abs(share(values, lambda v, a=low, b=high: a <= v <= b) - expected) < 0.03


def test_weights_are_relative():
    assert draw(age_field([70, 25, 5])) == draw(age_field([0.7, 0.25, 0.05]))


def test_zero_weight_range_is_never_used():
    values = draw(age_field([1, 0, 1]))

    assert not any(36 <= value <= 60 for value in values)


def test_weighted_float_ranges_honour_precision():
    ranges = [{"min": 0, "max": 1, "weight": 1}, {"min": 10, "max": 20, "weight": 1}]
    values = draw({"type": "float", "ranges": ranges, "precision": 1})

    assert all(round(value, 1) == value for value in values)
    assert all(0 <= value <= 1 or 10 <= value <= 20 for value in values)


# --- choice and boolean -----------------------------------------------------------------------


def test_only_listed_choice_values_appear_and_are_equally_likely():
    values = draw({"type": "choice", "values": ["free", "pro", "enterprise"]})

    counts = Counter(values)
    assert set(counts) == {"free", "pro", "enterprise"}
    assert all(abs(count / ROWS - 1 / 3) < 0.03 for count in counts.values())


def test_weighted_choice_proportions():
    field = {"type": "choice", "values": ["free", "pro", "enterprise"], "weights": [70, 25, 5]}
    counts = Counter(draw(field))

    for value, expected in (("free", 0.70), ("pro", 0.25), ("enterprise", 0.05)):
        assert abs(counts[value] / ROWS - expected) < 0.03


def test_choice_values_keep_their_types():
    values = draw({"type": "choice", "values": [1, 2.5, True, "x"]}, rows=200)

    assert {type(value) for value in values} == {int, float, bool, str}


def test_boolean_always_true():
    assert set(draw({"type": "boolean", "true_probability": 1})) == {True}


def test_boolean_proportion_follows_the_probability():
    values = draw({"type": "boolean", "true_probability": 0.2})

    assert abs(share(values, lambda v: v is True) - 0.2) < 0.03


# --- dates ------------------------------------------------------------------------------------


def test_dates_within_range():
    values = draw({"type": "date", "min": "2024-01-01", "max": "2024-12-31"})

    assert all(type(value) is date and value.year == 2024 for value in values)
    assert min(values) == date(2024, 1, 1)
    assert max(values) == date(2024, 12, 31)


def test_datetimes_within_range():
    field = {"type": "datetime", "min": "2024-01-01T00:00:00", "max": "2024-01-01T23:59:59"}
    values = draw(field)

    assert all(type(value) is datetime and value.date() == date(2024, 1, 1) for value in values)


# --- identifiers and constants ----------------------------------------------------------------


def test_sequence_with_defaults():
    assert draw({"type": "sequence"}, rows=3) == [1, 2, 3]


def test_sequence_with_start_and_step():
    assert draw({"type": "sequence", "start": 1000, "step": 10}, rows=3) == [1000, 1010, 1020]


def test_unique_valid_uuids():
    values = draw({"type": "uuid"})

    assert len(set(values)) == ROWS
    assert all(type(value) is str and uuid.UUID(value).version == 4 for value in values)


def test_constant_value():
    assert set(draw({"type": "constant", "value": "EUR"}, rows=50)) == {"EUR"}


def test_reference_reads_the_row_its_pick_chose():
    spec = load_spec(
        {
            "version": 1,
            "entities": {
                "thing": {"count": 3, "fields": {"value": {"type": "sequence"}}},
                "other": {"count": 1, "fields": {"value": "$thing.value"}},
            },
        }
    )
    column = [10, 20, 30]
    pick = RowPick(1, "other", "thing", None, rows=3)
    model = spec.entities["other"].fields["value"]
    generate = field_generator(model, 1, "other", "value", lambda: column[pick.index])

    seen = set()
    for _ in range(200):
        pick.advance()
        value = generate()
        assert value == column[pick.index]
        seen.add(value)
    assert seen == {10, 20, 30}


def test_row_picks_differ_by_link_and_target():
    def indexes(target, link):
        pick = RowPick(1, "transfer", target, link, rows=1000)
        chosen = []
        for _ in range(20):
            pick.advance()
            chosen.append(pick.index)
        return chosen

    assert indexes("account", "sender") == indexes("account", "sender")
    assert indexes("account", "sender") != indexes("account", "receiver")
    assert indexes("account", "sender") != indexes("account", None)
    assert indexes("account", "origin") != indexes("depot", "origin")


# --- nulls ------------------------------------------------------------------------------------

EVERY_TYPE = [
    {"type": "integer", "min": 1, "max": 9},
    {"type": "float", "min": 1, "max": 9},
    {"type": "boolean"},
    {"type": "choice", "values": ["a", "b"]},
    {"type": "date", "min": "2024-01-01", "max": "2024-12-31"},
    {"type": "datetime", "min": "2024-01-01T00:00:00", "max": "2024-12-31T00:00:00"},
    {"type": "sequence"},
    {"type": "uuid"},
    {"type": "constant", "value": "x"},
]


@pytest.mark.parametrize("field", EVERY_TYPE, ids=lambda field: field["type"])
def test_never_null_by_default(field):
    assert None not in draw(field, rows=500)


@pytest.mark.parametrize("field", EVERY_TYPE, ids=lambda field: field["type"])
def test_always_null(field):
    assert set(draw({**field, "null_probability": 1}, rows=500)) == {None}


@pytest.mark.parametrize("field", EVERY_TYPE, ids=lambda field: field["type"])
def test_proportion_of_nulls(field):
    values = draw({**field, "null_probability": 0.1})

    assert abs(share(values, lambda v: v is None) - 0.1) < 0.03


def test_changing_null_probability_does_not_shift_the_values():
    field = {"type": "integer", "min": 1, "max": 1_000_000}
    without_nulls = draw(field, rows=500)
    with_nulls = draw({**field, "null_probability": 0.5}, rows=500)

    kept = [(a, b) for a, b in zip(without_nulls, with_nulls, strict=True) if b is not None]
    assert kept and all(a == b for a, b in kept)


# --- weighted values with nulls and types -----------------------------------------------------


def test_listed_null_value_is_chosen_by_its_weight():
    values = draw({"type": "choice", "values": ["FRIEND10", None], "weights": [1, 4]})

    assert abs(share(values, lambda v: v is None) - 0.8) < 0.03


def test_null_entry_with_an_inline_weight():
    values = draw(
        {
            "type": "choice",
            "values": ["FRIEND10 || 0.2", "LAUNCH25 || 0.2", "PARTNER || 0.1", " || 0.5"],
        }
    )
    counts = Counter(values)

    for value, expected in (("FRIEND10", 0.2), ("LAUNCH25", 0.2), ("PARTNER", 0.1), (None, 0.5)):
        assert abs(counts[value] / ROWS - expected) < 0.03


def test_inline_and_listed_weights_generate_the_same_data():
    inline = draw({"type": "choice", "values": ["free || 70", "pro || 30"]})
    listed = draw({"type": "choice", "values": ["free", "pro"], "weights": [70, 30]})

    assert inline == listed


def test_the_remaining_share_follows_the_fields_own_rules():
    values = draw({"type": "choice", "values": ["a", "b"], "null_probability": 0.8})
    counts = Counter(values)

    assert abs(counts[None] / ROWS - 0.8) < 0.03
    assert abs(counts["a"] / ROWS - 0.1) < 0.03
    assert abs(counts["b"] / ROWS - 0.1) < 0.03


def test_null_probability_combined_with_a_null_entry():
    field = {"type": "choice", "values": ["yes || 0.5", " || 0.5"], "null_probability": 0.5}

    assert abs(share(draw(field), lambda v: v is None) - 0.75) < 0.03


def test_typed_inline_values_are_generated_in_their_type():
    field = {"type": "choice", "value_type": "integer", "values": ["1 || 60", "2 || 30", "5 || 10"]}
    values = draw(field)

    assert set(values) == {1, 2, 5}
    assert all(type(value) is int for value in values)


def test_range_shorthand_generates_the_same_data_as_mappings():
    short = draw({"type": "integer", "ranges": ["18 to 35 || 0.7", "36 to 90 || 0.3"]})
    long = draw(
        {
            "type": "integer",
            "ranges": [
                {"min": 18, "max": 35, "weight": 0.7},
                {"min": 36, "max": 90, "weight": 0.3},
            ],
        }
    )

    assert short == long
