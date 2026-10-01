"""Validation of the spec structure and of each field type (simulation-spec capability)."""

from datetime import date, datetime

import pytest

from dataspecter.spec import (
    ChoiceField,
    DateField,
    DatetimeField,
    FloatField,
    IntegerField,
    ReferenceField,
    SequenceField,
    load_spec,
)

from .helpers import problem_text, problems_of, spec_of

# --- spec structure ---------------------------------------------------------------------------


def test_minimal_valid_spec():
    spec = load_spec(spec_of({"type": "uuid"}))

    assert spec.version == 1
    assert spec.seed is None
    assert list(spec.entities) == ["thing"]
    assert spec.entities["thing"].count == 10
    assert list(spec.entities["thing"].fields) == ["value"]


def test_seed_and_output_are_read():
    raw = spec_of({"type": "uuid"}, seed=42, output={"format": "jsonl", "dir": "data"})
    spec = load_spec(raw)

    assert spec.seed == 42
    assert (spec.output.format, spec.output.dir) == ("jsonl", "data")


@pytest.mark.parametrize("version", [2, "1", 1.0, True, None])
def test_unsupported_version(version):
    raw = spec_of({"type": "uuid"})
    raw["version"] = version

    [problem] = problems_of(raw)
    assert problem.path == "version"
    assert "only version 1 is supported" in problem.message


def test_missing_version():
    raw = spec_of({"type": "uuid"})
    del raw["version"]

    assert "version: is required" in problem_text(raw)


def test_no_entities():
    [problem] = problems_of({"version": 1, "entities": {}})

    assert problem.path == "entities"
    assert "at least one entity is required" in problem.message


def test_unknown_key_is_named():
    raw = {"version": 1, "entities": {"thing": {"cout": 10, "fields": {"v": {"type": "uuid"}}}}}

    text = problem_text(raw)
    assert "entities.thing: unknown key 'cout'" in text
    assert "missing required key(s): count" in text


def test_unknown_top_level_key():
    assert "unknown key 'entitys'" in problem_text(spec_of({"type": "uuid"}, entitys={}))


@pytest.mark.parametrize("name", ["my-orders", "1st", "has space", ""])
def test_invalid_entity_name(name):
    raw = {"version": 1, "entities": {name: {"count": 1, "fields": {"v": {"type": "uuid"}}}}}

    text = problem_text(raw)
    assert "invalid entity name" in text
    assert "letters, digits and underscores" in text


def test_invalid_field_name():
    raw = {"version": 1, "entities": {"thing": {"count": 1, "fields": {"a.b": {"type": "uuid"}}}}}

    assert "invalid field name 'a.b'" in problem_text(raw)


@pytest.mark.parametrize("count", [0, -5, 2.5, "10", True])
def test_count_must_be_a_positive_integer(count):
    [problem] = problems_of(spec_of({"type": "uuid"}, count=count))

    assert problem.path == "entities.thing.count"
    assert "an integer of 1 or more" in problem.message


def test_entity_needs_at_least_one_field():
    raw = {"version": 1, "entities": {"thing": {"count": 1, "fields": {}}}}

    assert "at least one field is required" in problem_text(raw)


@pytest.mark.parametrize("seed", [-1, 1.5, "42"])
def test_seed_must_be_a_non_negative_integer(seed):
    [problem] = problems_of(spec_of({"type": "uuid"}, seed=seed))

    assert problem.path == "seed"


def test_unsupported_output_format():
    [problem] = problems_of(spec_of({"type": "uuid"}, output={"format": "xml"}))

    assert problem.path == "output.format"
    assert "supported formats: csv, json, jsonl" in problem.message


@pytest.mark.parametrize("source", [[], None, 42])
def test_spec_must_be_a_mapping(source):
    assert "the spec must be a mapping" in problem_text(source)


# --- field types ------------------------------------------------------------------------------


def test_unknown_field_type_lists_supported_types():
    [problem] = problems_of(spec_of({"type": "email"}))

    assert problem.path == "entities.thing.fields.value.type"
    assert "unknown field type 'email'" in problem.message
    for name in ("integer", "float", "boolean", "choice", "date", "datetime", "sequence"):
        assert name in problem.message
    for name in ("uuid", "constant", "reference"):
        assert name in problem.message


def test_missing_type():
    assert "missing required key 'type'" in problem_text(spec_of({"min": 1, "max": 2}))


def test_key_that_does_not_belong_to_the_type():
    [problem] = problems_of(spec_of({"type": "boolean", "min": 1}))

    assert problem.path == "entities.thing.fields.value"
    assert "unknown key 'min' for type 'boolean'" in problem.message


def test_uuid_takes_no_further_keys():
    assert "unknown key 'version'" in problem_text(spec_of({"type": "uuid", "version": 4}))


# --- numeric fields ---------------------------------------------------------------------------


def test_uniform_range_is_the_default():
    field = (
        load_spec(spec_of({"type": "integer", "min": 18, "max": 90}))
        .entities["thing"]
        .fields["value"]
    )

    assert isinstance(field, IntegerField)
    assert (field.min, field.max, field.distribution) == (18, 90, "uniform")


def test_float_field_with_precision():
    raw = spec_of({"type": "float", "min": 0, "max": 100, "precision": 2})
    field = load_spec(raw).entities["thing"].fields["value"]

    assert isinstance(field, FloatField)
    assert field.precision == 2


def test_minimum_above_maximum():
    [problem] = problems_of(spec_of({"type": "integer", "min": 90, "max": 18}))

    assert problem.path == "entities.thing.fields.value"
    assert "min must not exceed max" in problem.message


def test_uniform_needs_both_bounds():
    assert "missing required key(s): max" in problem_text(spec_of({"type": "integer", "min": 1}))


def test_normal_distribution_without_parameters():
    [problem] = problems_of(spec_of({"type": "float", "distribution": "normal"}))

    assert "missing required key(s): mean, stddev" in problem.message


def test_normal_distribution_bounds_are_optional():
    raw = spec_of({"type": "float", "distribution": "normal", "mean": 40, "stddev": 12})
    field = load_spec(raw).entities["thing"].fields["value"]

    assert (field.mean, field.stddev, field.min, field.max) == (40, 12, None, None)


@pytest.mark.parametrize("stddev", [0, -1])
def test_stddev_must_be_positive(stddev):
    raw = spec_of({"type": "float", "distribution": "normal", "mean": 1, "stddev": stddev})

    [problem] = problems_of(raw)
    assert problem.path == "entities.thing.fields.value.stddev"
    assert "greater than zero" in problem.message


def test_unknown_distribution():
    raw = spec_of({"type": "float", "min": 0, "max": 1, "distribution": "poisson"})

    assert "must be 'uniform' or 'normal'" in problem_text(raw)


def test_weighted_ranges():
    ranges = [
        {"min": 18, "max": 35, "weight": 0.7},
        {"min": 36, "max": 60, "weight": 0.25},
        {"min": 61, "max": 90, "weight": 0.05},
    ]
    field = (
        load_spec(spec_of({"type": "integer", "ranges": ranges})).entities["thing"].fields["value"]
    )

    assert [(r.min, r.max, r.weight) for r in field.ranges] == [
        (18, 35, 0.7),
        (36, 60, 0.25),
        (61, 90, 0.05),
    ]


def test_both_forms_used_together():
    ranges = [{"min": 1, "max": 2, "weight": 1}]
    [problem] = problems_of(spec_of({"type": "integer", "min": 1, "max": 9, "ranges": ranges}))

    assert "mutually exclusive" in problem.message


@pytest.mark.parametrize("weights", [[0, 0], [1, -1]])
def test_weights_that_cannot_be_used(weights):
    ranges = [{"min": 1, "max": 2, "weight": w} for w in weights]

    [problem] = problems_of(spec_of({"type": "integer", "ranges": ranges}))
    assert problem.path == "entities.thing.fields.value.ranges"
    assert "non-negative numbers with a sum greater than zero" in problem.message


def test_range_item_problems_are_located():
    ranges = [{"min": 1, "max": 2, "weight": 1}, {"min": 9, "max": 3, "weight": 1}]

    [problem] = problems_of(spec_of({"type": "integer", "ranges": ranges}))
    assert problem.path == "entities.thing.fields.value.ranges[1]"
    assert "min must not exceed max" in problem.message


@pytest.mark.parametrize("bound", ["18", True, 1.5])
def test_integer_bounds_are_not_coerced(bound):
    [problem] = problems_of(spec_of({"type": "integer", "min": bound, "max": 90}))

    assert problem.path == "entities.thing.fields.value.min"
    assert "must be an integer" in problem.message


def test_precision_too_coarse_for_the_range():
    raw = spec_of({"type": "float", "min": 0.12, "max": 0.13, "precision": 1})

    assert "no value with 1 decimal place(s) lies between min and max" in problem_text(raw)


# --- other fields -----------------------------------------------------------------------------


def test_weighted_choice():
    raw = spec_of(
        {"type": "choice", "values": ["free", "pro", "enterprise"], "weights": [70, 25, 5]}
    )
    field = load_spec(raw).entities["thing"].fields["value"]

    assert isinstance(field, ChoiceField)
    assert field.values == ("free", "pro", "enterprise")
    assert field.weights == (70, 25, 5)


def test_weights_of_the_wrong_length():
    raw = spec_of({"type": "choice", "values": ["a", "b", "c"], "weights": [1, 2]})

    [problem] = problems_of(raw)
    assert problem.path == "entities.thing.fields.value.weights"
    assert "weights must match values in length" in problem.message


@pytest.mark.parametrize("values", [[], "abc", [["nested"]], None])
def test_choice_values_must_be_a_non_empty_list_of_scalars(values):
    assert "a non-empty list" in problem_text(spec_of({"type": "choice", "values": values}))


def test_choice_weights_follow_the_weight_rules():
    raw = spec_of({"type": "choice", "values": ["a", "b"], "weights": [0, 0]})

    assert "sum greater than zero" in problem_text(raw)


@pytest.mark.parametrize("probability", [-0.1, 1.5, "0.5", True])
def test_true_probability_range(probability):
    raw = spec_of({"type": "boolean", "true_probability": probability})

    assert "a number between 0 and 1" in problem_text(raw)


def test_date_field():
    raw = spec_of({"type": "date", "min": "2024-01-01", "max": "2024-12-31"})
    field = load_spec(raw).entities["thing"].fields["value"]

    assert isinstance(field, DateField)
    assert (field.min, field.max) == (date(2024, 1, 1), date(2024, 12, 31))


def test_date_objects_are_accepted_in_a_mapping():
    raw = spec_of({"type": "date", "min": date(2024, 1, 1), "max": date(2024, 12, 31)})

    assert load_spec(raw).entities["thing"].fields["value"].min == date(2024, 1, 1)


def test_datetime_field():
    raw = spec_of({"type": "datetime", "min": "2024-01-01T00:00:00", "max": "2024-01-01T23:59:59"})
    field = load_spec(raw).entities["thing"].fields["value"]

    assert isinstance(field, DatetimeField)
    assert field.max == datetime(2024, 1, 1, 23, 59, 59)


def test_invalid_date():
    [problem] = problems_of(spec_of({"type": "date", "min": "2024-13-01", "max": "2024-12-31"}))

    assert problem.path == "entities.thing.fields.value.min"
    assert "is not a valid ISO 8601 date" in problem.message


def test_date_minimum_after_maximum():
    raw = spec_of({"type": "date", "min": "2024-12-31", "max": "2024-01-01"})

    assert "min must not be after max" in problem_text(raw)


def test_datetime_bounds_must_agree_on_timezone():
    raw = spec_of(
        {"type": "datetime", "min": "2024-01-01T00:00:00+00:00", "max": "2024-01-02T00:00:00"}
    )

    assert "timezone offset" in problem_text(raw)


def test_sequence_defaults():
    field = load_spec(spec_of({"type": "sequence"})).entities["thing"].fields["value"]

    assert isinstance(field, SequenceField)
    assert (field.start, field.step) == (1, 1)


def test_zero_step():
    [problem] = problems_of(spec_of({"type": "sequence", "step": 0}))

    assert problem.path == "entities.thing.fields.value.step"
    assert "must not be zero" in problem.message


def test_constant_needs_a_value():
    assert "missing required key(s): value" in problem_text(spec_of({"type": "constant"}))


# --- null probability -------------------------------------------------------------------------


def test_null_probability_defaults_to_zero():
    field = load_spec(spec_of({"type": "uuid"})).entities["thing"].fields["value"]

    assert field.null_probability == 0


@pytest.mark.parametrize("probability", [1.5, -0.01, "0.1"])
def test_out_of_range_null_probability(probability):
    [problem] = problems_of(spec_of({"type": "uuid", "null_probability": probability}))

    assert problem.path == "entities.thing.fields.value.null_probability"
    assert "a number between 0 and 1" in problem.message


# --- references -------------------------------------------------------------------------------


def shop(order_fields: dict, customer_fields: dict | None = None) -> dict:
    """`order` is declared before `customer`, so every reference here is a forward one."""
    return {
        "version": 1,
        "entities": {
            "order": {"count": 5, "fields": order_fields},
            "customer": {"count": 3, "fields": customer_fields or {"id": {"type": "sequence"}}},
        },
    }


def test_valid_forward_reference():
    raw = shop({"customer_id": {"type": "reference", "entity": "customer", "field": "id"}})
    field = load_spec(raw).entities["order"].fields["customer_id"]

    assert isinstance(field, ReferenceField)
    assert (field.entity, field.field) == ("customer", "id")


def test_unknown_target_entity():
    raw = shop({"customer_id": {"type": "reference", "entity": "client", "field": "id"}})

    [problem] = problems_of(raw)
    assert problem.path == "entities.order.fields.customer_id"
    assert "unknown entity 'client'" in problem.message


def test_unknown_target_field():
    raw = shop({"customer_id": {"type": "reference", "entity": "customer", "field": "uid"}})

    [problem] = problems_of(raw)
    assert problem.path == "entities.order.fields.customer_id"
    assert "entity 'customer' has no field 'uid'" in problem.message


def test_self_reference():
    raw = shop({"parent": {"type": "reference", "entity": "order", "field": "parent"}})

    assert "an entity cannot reference itself" in problem_text(raw)


def test_circular_references_name_the_entities():
    raw = shop(
        {"customer_id": {"type": "reference", "entity": "customer", "field": "last_order"}},
        {"last_order": {"type": "reference", "entity": "order", "field": "customer_id"}},
    )

    [problem] = problems_of(raw)
    assert "circular reference between entities" in problem.message
    assert "order" in problem.message and "customer" in problem.message


# --- reporting --------------------------------------------------------------------------------


def test_multiple_problems_are_reported_together_with_their_paths():
    raw = shop(
        {
            "amount": {"type": "float", "min": 500, "max": 5},
            "customer_id": {"type": "reference", "entity": "client", "field": "id"},
        }
    )

    paths = {problem.path for problem in problems_of(raw)}
    assert paths == {"entities.order.fields.amount", "entities.order.fields.customer_id"}
