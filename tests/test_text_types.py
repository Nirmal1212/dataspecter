"""Patterns, templates, hidden fields, unique fields and custom types."""

import copy
import json
import re
from datetime import date

import pytest

import dataspecter
from dataspecter.spec import PatternField, TemplateField, load_spec

from .helpers import problem_text, problems_of


def spec_of(fields: dict, count: int = 50, **top) -> dict:
    return {
        "version": 1,
        "seed": 3,
        "entities": {"person": {"count": count, "fields": fields}},
        **top,
    }


def rows(fields: dict, count: int = 50, **top) -> list[dict]:
    simulation = dataspecter.generate(load_spec(spec_of(fields, count, **top)))
    return list(simulation.records("person"))


def column(field: dict, count: int = 1000) -> list:
    return [row["value"] for row in rows({"value": field}, count)]


# --- patterns ---------------------------------------------------------------------------------


def test_pattern_is_compiled_into_segments():
    field = (
        load_spec(spec_of({"v": {"type": "pattern", "pattern": "A-#%?"}}))
        .entities["person"]
        .fields["v"]
    )

    assert isinstance(field, PatternField)
    assert field.segments == (("literal", "A-"), ("digit", ""), ("nonzero", ""), ("letter", ""))


def test_phone_like_pattern():
    values = column({"type": "pattern", "pattern": "+91-%#########"})

    assert all(re.fullmatch(r"\+91-[1-9]\d{9}", value) for value in values)


def test_letters_and_digits():
    values = column({"type": "pattern", "pattern": "SKU-??-####"})

    assert all(re.fullmatch(r"SKU-[A-Z]{2}-\d{4}", value) for value in values)


def test_bracketed_text_is_literal():
    values = column({"type": "pattern", "pattern": "Item [#]## at 50[%] [[]?]"}, count=50)

    assert all(re.fullmatch(r"Item #\d\d at 50% \[[A-Z]\]", value) for value in values)


def test_pattern_values_vary():
    assert len(set(column({"type": "pattern", "pattern": "######"}))) > 900


@pytest.mark.parametrize("definition", [{"type": "pattern"}, {"type": "pattern", "pattern": ""}])
def test_missing_or_empty_pattern(definition):
    text = problem_text(spec_of({"v": definition}))

    assert "pattern is required" in text or "a non-empty string" in text


def test_unclosed_bracket():
    [problem] = problems_of(spec_of({"v": {"type": "pattern", "pattern": "Item [#"}}))

    assert problem.path == "entities.person.fields.v.pattern"
    assert "is not closed" in problem.message


def test_pattern_reads_the_same_from_yaml_and_json(tmp_path):
    pattern = "Item [#]?## 50[%]"
    (tmp_path / "a.yaml").write_text(
        "version: 1\nseed: 1\nentities:\n  person:\n    count: 5\n    fields:\n"
        f'      v: {{type: pattern, pattern: "{pattern}"}}\n',
        encoding="utf-8",
    )
    (tmp_path / "a.json").write_text(
        json.dumps(spec_of({"v": {"type": "pattern", "pattern": pattern}}, count=5, seed=1)),
        encoding="utf-8",
    )

    assert load_spec(tmp_path / "a.yaml") == load_spec(tmp_path / "a.json")


# --- templates: validation --------------------------------------------------------------------

NAMES = {
    "first_name": {"type": "choice", "values": ["Asha", "O'Brien", "José", "De La Cruz"]},
    "last_name": {"type": "choice", "values": ["Rao", "Müller", "Smith"]},
}
EMAIL = {"type": "template", "template": "{first_name|slug}.{last_name|slug}@example.com"}


def test_template_over_sibling_fields():
    field = load_spec(spec_of({**NAMES, "email": EMAIL})).entities["person"].fields["email"]

    assert isinstance(field, TemplateField)
    assert [part.target for part in field.parts if not isinstance(part, str)] == [
        "first_name",
        "last_name",
    ]


def test_unknown_field_in_a_placeholder():
    [problem] = problems_of(spec_of({**NAMES, "e": {"type": "template", "template": "{surname}"}}))

    assert problem.path == "entities.person.fields.e.template"
    assert "'surname'" in problem.message


def in_contact(template: str) -> dict:
    return {
        "tier": {"type": "constant", "value": "pro"},
        "home": {"type": "object", "fields": {"city": {"type": "constant", "value": "Pune"}}},
        "contact": {
            "type": "object",
            "fields": {
                "phone": {"type": "constant", "value": "555"},
                "label": {"type": "template", "template": template},
            },
        },
    }


def test_outer_levels_are_not_searched():
    [problem] = problems_of(spec_of(in_contact("{tier}")))

    assert "'tier'" in problem.message
    assert "did you mean {^tier}?" in problem.message


def test_reaching_outward_explicitly():
    result = rows(in_contact("{phone} {^tier} {^home.city}"), count=3)

    assert all(row["contact"]["label"] == "555 pro Pune" for row in result)


def test_too_many_levels_outward():
    [problem] = problems_of(
        spec_of({**NAMES, "e": {"type": "template", "template": "{^first_name}"}})
    )

    assert "no enclosing level" in problem.message


def test_unknown_filter():
    template = {"type": "template", "template": "{first_name|reverse}"}

    [problem] = problems_of(spec_of({**NAMES, "e": template}))
    assert "unknown filter 'reverse'" in problem.message
    assert "lower, upper, title, ascii, slug" in problem.message


def test_placeholder_naming_an_object():
    fields = in_contact("{phone}")
    fields["where"] = {"type": "template", "template": "{home}"}

    assert "names an object" in problem_text(spec_of(fields))


@pytest.mark.parametrize("template", ["{first_name.__class__}", "{first_name[0]}", "{}", "{a b}"])
def test_nothing_in_a_template_is_evaluated(template):
    text = problem_text(spec_of({**NAMES, "e": {"type": "template", "template": template}}))

    assert "malformed placeholder" in text or "has no field" in text or "no field" in text


def test_templates_that_depend_on_each_other():
    fields = {
        "a": {"type": "template", "template": "{b}"},
        "b": {"type": "template", "template": "{a}"},
    }

    [problem] = problems_of(spec_of(fields))
    assert "templates depend on each other" in problem.message
    assert "a" in problem.message and "b" in problem.message


@pytest.mark.parametrize("template", ["{first_name", "first_name}"])
def test_unbalanced_braces(template):
    text = problem_text(spec_of({**NAMES, "e": {"type": "template", "template": template}}))

    assert "is not closed" in text or "no matching" in text


# --- templates: values ------------------------------------------------------------------------


def test_template_built_from_the_same_record():
    slugs = {"Asha": "asha", "O'Brien": "o-brien", "José": "jose", "De La Cruz": "de-la-cruz"}
    lasts = {"Rao": "rao", "Müller": "muller", "Smith": "smith"}

    for row in rows({**NAMES, "email": EMAIL}, count=200):
        expected = f"{slugs[row['first_name']]}.{lasts[row['last_name']]}@example.com"
        assert row["email"] == expected


def test_case_and_ascii_filters():
    fields = {
        "name": {"type": "constant", "value": "mcDonald zoë"},
        "upper": {"type": "template", "template": "{name|upper}"},
        "lower": {"type": "template", "template": "{name|lower}"},
        "title": {"type": "template", "template": "{name|title}"},
        "ascii": {"type": "template", "template": "{name|ascii}"},
        "chained": {"type": "template", "template": "{name|ascii|upper}"},
    }
    row = rows(fields, count=1)[0]

    assert row["upper"] == "MCDONALD ZOË"
    assert row["lower"] == "mcdonald zoë"
    assert row["title"] == "Mcdonald Zoë"
    assert row["ascii"] == "mcDonald zoe"
    assert row["chained"] == "MCDONALD ZOE"


def test_literal_braces_and_value_formatting():
    fields = {
        "id": {"type": "constant", "value": 7},
        "ratio": {"type": "constant", "value": 2.5},
        "active": {"type": "constant", "value": True},
        "day": {"type": "date", "min": "2024-03-05", "max": "2024-03-05"},
        "text": {"type": "template", "template": "{{{id}}} {ratio} {active} {day}"},
    }

    assert rows(fields, count=1)[0]["text"] == "{7} 2.5 true 2024-03-05"


def test_null_input_gives_a_null_template():
    fields = {
        "nick": {"type": "choice", "values": ["Ace"], "null_probability": 0.5},
        "greeting": {"type": "template", "template": "Hi {nick}"},
    }
    result = rows(fields, count=400)

    assert all((row["greeting"] is None) == (row["nick"] is None) for row in result)
    assert any(row["greeting"] is None for row in result)
    assert any(row["greeting"] == "Hi Ace" for row in result)


def test_template_declared_before_its_inputs_and_chained():
    fields = {
        "label": {"type": "template", "template": "<{email}>"},
        "email": EMAIL,
        **NAMES,
    }
    result = rows(fields, count=20)

    assert all(list(row) == ["label", "email", "first_name", "last_name"] for row in result)
    assert all(row["label"] == f"<{row['email']}>" for row in result)


def test_template_reads_a_reference():
    raw = {
        "version": 1,
        "seed": 1,
        "entities": {
            "customer": {"count": 20, "fields": {"name": {"type": "uuid"}}},
            "order": {
                "count": 60,
                "fields": {
                    "customer_name": "$customer.name",
                    "title": {"type": "template", "template": "Order for {customer_name}"},
                },
            },
        },
    }
    simulation = dataspecter.generate(load_spec(raw))

    assert all(
        row["title"] == f"Order for {row['customer_name']}" for row in simulation.records("order")
    )


def test_template_inside_a_null_object_is_skipped():
    fields = in_contact("{phone}")
    fields["contact"]["null_probability"] = 1

    assert all(row["contact"] is None for row in rows(fields, count=5))


def test_template_null_probability():
    fields = {**NAMES, "email": {**EMAIL, "null_probability": 0.5}}
    result = rows(fields, count=600)

    share = sum(row["email"] is None for row in result) / len(result)
    assert 0.4 < share < 0.6


# --- hidden fields ----------------------------------------------------------------------------

HIDDEN_NAMES = {name: {**field, "hidden": True} for name, field in NAMES.items()}


def test_hidden_fields_are_generated_but_left_out():
    visible = rows({"id": {"type": "sequence"}, **NAMES, "email": EMAIL}, count=100)
    hidden = rows({"id": {"type": "sequence"}, **HIDDEN_NAMES, "email": EMAIL}, count=100)

    assert all(list(row) == ["id", "email"] for row in hidden)
    assert [row["email"] for row in hidden] == [row["email"] for row in visible]
    assert [row["id"] for row in hidden] == [row["id"] for row in visible]


def test_hidden_fields_are_not_exported(tmp_path):
    spec = load_spec(spec_of({"id": {"type": "sequence"}, **HIDDEN_NAMES, "email": EMAIL}))
    dataspecter.write(spec, out_dir=tmp_path, format="csv")
    dataspecter.write(spec, out_dir=tmp_path, format="json")

    assert (tmp_path / "person.csv").read_text(encoding="utf-8").splitlines()[0] == "id,email"
    records = json.loads((tmp_path / "person.json").read_text(encoding="utf-8"))
    assert all(set(record) == {"id", "email"} for record in records)
    assert dataspecter.generate(spec).columns("person") == ("id", "email")


def test_hidden_field_as_a_reference_target_and_hidden_object():
    raw = {
        "version": 1,
        "seed": 2,
        "entities": {
            "customer": {
                "count": 30,
                "fields": {
                    "id": {"type": "sequence"},
                    "code": {"type": "pattern", "pattern": "C-####", "hidden": True},
                    "internal": {
                        "type": "object",
                        "hidden": True,
                        "fields": {"a": {"type": "uuid"}, "b": {"type": "uuid"}},
                    },
                    "profile": {
                        "type": "object",
                        "fields": {
                            "nick": {"type": "constant", "value": "x"},
                            "secret": {"type": "uuid", "hidden": True},
                        },
                    },
                },
            },
            "order": {
                "count": 90,
                "fields": {
                    "customer_code": "$customer.code",
                    "profile": "$customer.profile",
                },
            },
        },
    }
    simulation = dataspecter.generate(load_spec(raw))
    customers = list(simulation.records("customer"))
    orders = list(simulation.records("order"))

    assert all(list(row) == ["id", "profile"] for row in customers)
    assert all(row["profile"] == {"nick": "x"} for row in customers)
    assert all(re.fullmatch(r"C-\d{4}", row["customer_code"]) for row in orders)
    assert all(row["profile"] == {"nick": "x"} for row in orders)
    assert simulation.columns("order") == ("customer_code", "profile.nick")


def test_everything_hidden_is_rejected():
    [problem] = problems_of(spec_of(HIDDEN_NAMES))

    assert problem.path == "entities.person.fields"
    assert "at least one field must be visible" in problem.message


def test_hidden_must_be_a_boolean():
    [problem] = problems_of(spec_of({"v": {"type": "uuid", "hidden": "yes"}}))

    assert problem.path == "entities.person.fields.v.hidden"
    assert "true or false" in problem.message


# --- unique fields ----------------------------------------------------------------------------


def test_unique_pattern_values_never_repeat():
    values = column({"type": "pattern", "pattern": "??-###", "unique": True}, count=10_000)

    assert len(set(values)) == 10_000


def test_unique_field_at_full_capacity_uses_every_value():
    values = column({"type": "integer", "min": 1, "max": 500, "unique": True}, count=500)

    assert sorted(values) == list(range(1, 501))


def test_unique_values_with_nulls():
    field = {"type": "integer", "min": 1, "max": 5000, "unique": True, "null_probability": 0.3}
    values = column(field, count=2000)
    present = [value for value in values if value is not None]

    assert len(present) == len(set(present))
    assert 0.25 < values.count(None) / len(values) < 0.35


def test_unique_values_are_reproducible():
    field = {"type": "pattern", "pattern": "?##", "unique": True}

    assert column(field, count=2000) == column(field, count=2000)


@pytest.mark.parametrize(
    ("field", "capacity"),
    [
        ({"type": "integer", "min": 1, "max": 100}, "100"),
        ({"type": "choice", "values": ["a", "b", "c", "d", "a", None]}, "4"),
        ({"type": "choice", "values": ["a", "b", "c"], "weights": [1, 0, 1]}, "2"),
        ({"type": "pattern", "pattern": "X-##"}, "100"),
        ({"type": "float", "min": 0, "max": 1, "precision": 1}, "11"),
        ({"type": "date", "min": "2024-01-01", "max": "2024-01-10"}, "10"),
        ({"type": "integer", "ranges": ["1 to 5 || 1", "3 to 8 || 1", "20 to 21 || 0"]}, "8"),
    ],
)
def test_more_rows_than_unique_values(field, capacity):
    [problem] = problems_of(spec_of({"v": {**field, "unique": True}}, count=500))

    assert problem.path == "entities.person.fields.v"
    assert f"only {capacity} distinct values" in problem.message
    assert "needs 500" in problem.message


@pytest.mark.parametrize(
    "field",
    [
        {"type": "boolean"},
        {"type": "constant", "value": 1},
        {"type": "template", "template": "x"},
        {"type": "object", "fields": {"a": {"type": "uuid"}}},
    ],
)
def test_types_that_cannot_be_unique(field):
    [problem] = problems_of(spec_of({"v": {**field, "unique": True}}))

    assert problem.path == "entities.person.fields.v.unique"
    assert "'unique' is not supported" in problem.message


def test_sequence_and_uuid_accept_unique():
    result = rows(
        {"a": {"type": "sequence", "unique": True}, "b": {"type": "uuid", "unique": True}}, count=5
    )

    assert [row["a"] for row in result] == [1, 2, 3, 4, 5]


def test_unbounded_unique_field_is_accepted_and_generates():
    values = column({"type": "float", "min": 0, "max": 1, "unique": True}, count=2000)

    assert len(set(values)) == 2000


def test_unbounded_field_that_cannot_find_a_new_value_stops():
    field = {
        "type": "integer",
        "distribution": "normal",
        "mean": 0,
        "stddev": 0.5,
        "unique": True,
    }
    simulation = dataspecter.generate(load_spec(spec_of({"value": field}, count=1000)))

    with pytest.raises(dataspecter.GenerationError, match="person.value is unique"):
        list(simulation.records("person"))


def test_unique_field_as_a_reference_target():
    raw = {
        "version": 1,
        "seed": 4,
        "entities": {
            "product": {
                "count": 300,
                "fields": {
                    "code": {"type": "pattern", "pattern": "P-###", "unique": True},
                    "price": {"type": "float", "min": 1, "max": 9, "precision": 2},
                },
            },
            "item": {
                "count": 900,
                "fields": {"product_code": "$product.code", "price": "$product.price"},
            },
        },
    }
    simulation = dataspecter.generate(load_spec(raw))
    price_of = {row["code"]: row["price"] for row in simulation.records("product")}

    assert len(price_of) == 300
    assert all(row["price"] == price_of[row["product_code"]] for row in simulation.records("item"))


# --- custom types -----------------------------------------------------------------------------

TYPES = {
    "indian_mobile": {"type": "pattern", "pattern": "+91-%#########"},
    "money": {
        "type": "object",
        "fields": {
            "amount": {"type": "float", "min": 5, "max": 500, "precision": 2},
            "currency": {"type": "constant", "value": "INR"},
        },
    },
    "person": {
        "type": "object",
        "fields": {
            "first_name": {"type": "choice", "values": ["Asha", "Ravi", "Meera"]},
            "last_name": {"type": "choice", "values": ["Rao", "Nair"]},
            "email": {"type": "template", "template": "{first_name|slug}.{last_name|slug}@x.test"},
            "mobile": {"type": "indian_mobile"},
        },
    },
}


def with_types(fields: dict, types: dict | None = None, count: int = 50) -> dict:
    return spec_of(fields, count, types=copy.deepcopy(TYPES if types is None else types))


def test_declaring_and_using_a_type():
    values = [row["m"] for row in rows({"m": {"type": "indian_mobile"}}, types=TYPES)]

    assert all(re.fullmatch(r"\+91-[1-9]\d{9}", value) for value in values)


def test_using_a_type_equals_writing_its_definition():
    used = load_spec(with_types({"m": {"type": "indian_mobile"}}))
    written = load_spec(spec_of({"m": TYPES["indian_mobile"]}))

    assert used.entities == written.entities


def test_object_type_used_in_two_entities_and_built_on_another_type():
    raw = with_types({"owner": {"type": "person"}, "price": {"type": "money"}})
    raw["entities"]["staff"] = {"count": 20, "fields": {"who": {"type": "person"}}}
    simulation = dataspecter.generate(load_spec(raw))

    for entity, key in (("person", "owner"), ("staff", "who")):
        for row in simulation.records(entity):
            who = row[key]
            assert who["email"] == f"{who['first_name'].lower()}.{who['last_name'].lower()}@x.test"
            assert re.fullmatch(r"\+91-[1-9]\d{9}", who["mobile"])


def test_two_fields_using_the_same_type_are_independent():
    fields = {"home": {"type": "indian_mobile"}, "work": {"type": "indian_mobile"}}
    result = rows(fields, count=200, types=TYPES)

    assert sum(row["home"] != row["work"] for row in result) > 190


def test_overriding_keys_at_the_point_of_use():
    field = {"type": "indian_mobile", "unique": True, "null_probability": 0.5}
    values = [row["m"] for row in rows({"m": field}, count=400, types=TYPES)]
    present = [value for value in values if value is not None]

    assert 0.4 < values.count(None) / len(values) < 0.6
    assert len(present) == len(set(present))


def test_overriding_a_sub_field_of_an_object_type():
    field = {"type": "money", "fields": {"currency": {"type": "constant", "value": "USD"}}}
    result = rows({"price": field}, types=TYPES)

    assert all(list(row["price"]) == ["amount", "currency"] for row in result)
    assert all(row["price"]["currency"] == "USD" for row in result)


def test_key_the_underlying_type_does_not_accept():
    [problem] = problems_of(with_types({"m": {"type": "indian_mobile", "min": 1}}))

    assert problem.path == "entities.person.fields.m"
    assert "unknown key 'min' for type 'pattern'" in problem.message
    assert "(in custom type 'indian_mobile')" in problem.message


def test_types_that_depend_on_each_other():
    types = {"a": {"type": "b"}, "b": {"type": "a"}}

    [problem] = problems_of(with_types({"v": {"type": "a"}}, types))
    assert problem.path == "types"
    assert "a -> b -> a" in problem.message or "b -> a -> b" in problem.message


def test_custom_type_named_like_a_built_in_takes_precedence():
    types = {"integer": {"type": "integer", "min": 0, "max": 9}}
    values = [row["v"] for row in rows({"v": {"type": "integer"}}, count=300, types=types)]

    assert set(values) == set(range(10))


def test_custom_type_named_after_a_type_added_later_still_wins():
    types = {"full_name": {"type": "constant", "value": "mine"}}

    assert all(row["v"] == "mine" for row in rows({"v": {"type": "full_name"}}, types=types))


def test_problem_in_an_unused_type():
    types = {"broken": {"type": "boolean", "min": 1}}

    [problem] = problems_of(with_types({"v": {"type": "uuid"}}, types))
    assert problem.path == "types.broken"


def test_broken_type_is_reported_once_even_when_used():
    types = {"broken": {"type": "boolean", "min": 1}, "wrapper": {"type": "broken"}}
    fields = {"a": {"type": "broken"}, "b": {"type": "wrapper"}}

    [problem] = problems_of(with_types(fields, types))
    assert problem.path == "types.broken"


def test_closed_object_type_is_checked_where_it_is_declared():
    types = copy.deepcopy(TYPES)
    types["person"]["fields"]["email"]["template"] = "{surname}@x.test"

    [problem] = problems_of(with_types({"v": {"type": "uuid"}}, types))
    assert problem.path == "types.person.fields.email.template"
    assert "'surname'" in problem.message


def test_check_that_depends_on_the_point_of_use():
    types = {"greeting": {"type": "template", "template": "Hi {first_name}"}}
    good = rows(
        {"first_name": {"type": "constant", "value": "Asha"}, "g": {"type": "greeting"}},
        types=types,
    )
    assert all(row["g"] == "Hi Asha" for row in good)

    [problem] = problems_of(with_types({"g": {"type": "greeting"}}, types))
    assert problem.path == "entities.person.fields.g.template"
    assert "'first_name'" in problem.message
    assert "(in custom type 'greeting')" in problem.message


def test_unknown_type_lists_built_in_and_custom_types():
    [problem] = problems_of(with_types({"v": {"type": "surname"}}))

    assert "unknown field type 'surname'" in problem.message
    assert "pattern" in problem.message and "template" in problem.message
    assert "custom types in this spec: indian_mobile, money, person" in problem.message


@pytest.mark.parametrize("types", [["a"], {"bad-name": {"type": "uuid"}}, {"a": "uuid"}])
def test_malformed_types_block(types):
    paths = [problem.path for problem in problems_of(with_types({"v": {"type": "uuid"}}, types))]

    assert all(path.startswith("types") for path in paths)


def test_values_are_native_types_in_objects_from_types():
    row = rows(
        {
            "price": {"type": "money"},
            "day": {"type": "date", "min": "2024-01-01", "max": "2024-01-02"},
        },
        types=TYPES,
    )[0]

    assert type(row["price"]["amount"]) is float
    assert type(row["day"]) is date
