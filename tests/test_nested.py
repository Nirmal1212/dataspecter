"""Nested objects: validation, generation, references into them, and export."""

import copy
import json

import pytest
import yaml

import dataspecter
from dataspecter.spec import MAX_DEPTH, ObjectField, leaf_paths, load_spec

from .helpers import problem_text, problems_of

ADDRESS = {
    "type": "object",
    "fields": {
        "city": {"type": "choice", "values": ["Pune", "Austin", "Leeds", "Kochi"]},
        "postcode": {"type": "integer", "min": 10000, "max": 99999},
    },
}

SHOP = {
    "version": 1,
    "seed": 5,
    "entities": {
        "invoice": {
            "count": 80,
            "fields": {
                "id": {"type": "sequence"},
                "city": "$order.ship_to.city",
                "order_id": "$order.id",
            },
        },
        "order": {
            "count": 200,
            "fields": {
                "id": {"type": "sequence", "start": 500},
                "customer_id": "$customer.id",
                "ship_city": "$customer.address.city",
                "ship_to": "$customer.address",
                "billing": {
                    "type": "object",
                    "fields": {
                        "customer_id": "$customer.id",
                        "geo_lat": "$customer.address.geo.lat",
                    },
                },
            },
        },
        "customer": {
            "count": 50,
            "fields": {
                "id": {"type": "sequence", "start": 1001},
                "address": {
                    "type": "object",
                    "null_probability": 0.2,
                    "fields": {
                        "city": {"type": "choice", "values": ["Pune", "Austin", "Leeds", "Kochi"]},
                        "postcode": {"type": "integer", "min": 10000, "max": 99999},
                        "geo": {
                            "type": "object",
                            "fields": {
                                "lat": {"type": "float", "min": -90, "max": 90, "precision": 3},
                                "lon": {"type": "float", "min": -180, "max": 180, "precision": 3},
                            },
                        },
                    },
                },
                "tier": {"type": "choice", "values": ["free", "pro"]},
            },
        },
    },
}


def shop() -> dict:
    return copy.deepcopy(SHOP)


def entity_of(fields: dict, **output) -> dict:
    raw = {"version": 1, "seed": 1, "entities": {"customer": {"count": 20, "fields": fields}}}
    if output:
        raw["output"] = output
    return raw


def run(raw: dict, seed: int | None = None) -> dict[str, list[dict]]:
    simulation = dataspecter.generate(load_spec(raw), seed)
    return {name: list(simulation.records(name)) for name in simulation.entities}


def nested(levels: int) -> dict:
    field: dict = {"type": "uuid"}
    for _ in range(levels):
        field = {"type": "object", "fields": {"inner": field}}
    return field


# --- validation -------------------------------------------------------------------------------


def test_object_with_sub_fields():
    field = load_spec(entity_of({"address": ADDRESS})).entities["customer"].fields["address"]

    assert isinstance(field, ObjectField)
    assert list(field.fields) == ["city", "postcode"]


def test_object_inside_an_object_has_dotted_paths():
    spec = load_spec(shop())

    assert leaf_paths(spec, "customer") == (
        "id",
        "address.city",
        "address.postcode",
        "address.geo.lat",
        "address.geo.lon",
        "tier",
    )


@pytest.mark.parametrize("definition", [{"type": "object"}, {"type": "object", "fields": {}}])
def test_object_without_fields(definition):
    assert "at least one field" in problem_text(entity_of({"address": definition}))


def test_same_field_name_at_two_levels():
    fields = {
        "name": {"type": "constant", "value": "outer"},
        "contact": {"type": "object", "fields": {"name": {"type": "constant", "value": "inner"}}},
    }
    row = run(entity_of(fields))["customer"][0]

    assert row == {"name": "outer", "contact": {"name": "inner"}}


def test_problem_inside_an_object_is_located_by_path():
    broken = copy.deepcopy(ADDRESS)
    broken["fields"]["postcode"]["colour"] = "red"

    [problem] = problems_of(entity_of({"address": broken}))
    assert problem.path == "entities.customer.fields.address.fields.postcode"
    assert "unknown key 'colour'" in problem.message


def test_nesting_within_the_limit():
    load_spec(entity_of({"deep": nested(MAX_DEPTH)}))


def test_nesting_beyond_the_limit():
    [problem] = problems_of(entity_of({"deep": nested(MAX_DEPTH + 1)}))

    assert problem.path.startswith("entities.customer.fields.deep.fields.inner")
    assert f"more than {MAX_DEPTH} levels deep" in problem.message


def test_document_that_contains_itself_is_rejected_cleanly():
    document = """
version: 1
entities:
  customer:
    count: 1
    fields:
      loop: &loop
        type: object
        fields:
          inner: *loop
"""
    raw = yaml.safe_load(document)
    assert raw["entities"]["customer"]["fields"]["loop"]["fields"]["inner"] is not None

    [problem] = problems_of(raw)
    assert f"more than {MAX_DEPTH} levels deep" in problem.message


def test_self_containing_document_from_a_file(tmp_path):
    path = tmp_path / "loop.yaml"
    path.write_text(
        "version: 1\nentities:\n  c:\n    count: 1\n    fields:\n      loop: &l\n"
        "        type: object\n        fields:\n          inner: *l\n",
        encoding="utf-8",
    )

    assert "levels deep" in problem_text(path)


# --- generation -------------------------------------------------------------------------------


def test_nested_record_in_declared_order():
    rows = run(entity_of({"id": {"type": "sequence"}, "address": ADDRESS}))["customer"]

    assert all(list(row) == ["id", "address"] for row in rows)
    assert all(list(row["address"]) == ["city", "postcode"] for row in rows)
    assert all(10000 <= row["address"]["postcode"] <= 99999 for row in rows)


def test_null_object_is_null_not_an_object_of_nulls():
    rows = run(entity_of({"address": {**ADDRESS, "null_probability": 1}}))["customer"]

    assert all(row["address"] is None for row in rows)


def test_nulls_inside_an_object():
    address = copy.deepcopy(ADDRESS)
    address["fields"]["postcode"]["null_probability"] = 1
    rows = run(entity_of({"address": address}))["customer"]

    assert all(row["address"]["postcode"] is None for row in rows)
    assert all(row["address"]["city"] is not None for row in rows)


def test_object_null_proportion():
    raw = entity_of({"address": {**ADDRESS, "null_probability": 0.3}})
    raw["entities"]["customer"]["count"] = 5000
    rows = run(raw)["customer"]

    share = sum(row["address"] is None for row in rows) / len(rows)
    assert abs(share - 0.3) < 0.03


def test_adding_removing_and_reordering_nested_fields_keeps_values():
    before = run(entity_of({"address": ADDRESS}))["customer"]

    grown = copy.deepcopy(ADDRESS)
    grown["fields"] = {"country": {"type": "constant", "value": "IN"}, **grown["fields"]}
    after = run(entity_of({"address": grown}))["customer"]
    for row in after:
        del row["address"]["country"]
    assert [row["address"] for row in after] == [row["address"] for row in before]

    shrunk = copy.deepcopy(ADDRESS)
    del shrunk["fields"]["city"]
    only_postcode = run(entity_of({"address": shrunk}))["customer"]
    assert [row["address"]["postcode"] for row in only_postcode] == [
        row["address"]["postcode"] for row in before
    ]


def test_a_flat_entity_is_unaffected_by_a_nested_one_beside_it():
    flat = {"id": {"type": "sequence"}, "age": {"type": "integer", "min": 1, "max": 99}}
    alone = {"version": 1, "seed": 9, "entities": {"person": {"count": 30, "fields": flat}}}
    together = copy.deepcopy(alone)
    together["entities"]["customer"] = {"count": 5, "fields": {"address": ADDRESS}}

    assert run(alone)["person"] == run(together)["person"]


# --- references into nested fields ------------------------------------------------------------


def test_nested_reference_in_both_forms():
    short = shop()
    long = shop()
    long["entities"]["order"]["fields"]["ship_city"] = {
        "type": "reference",
        "entity": "customer",
        "field": "address.city",
    }

    assert load_spec(short) == load_spec(long)


def test_unknown_nested_field():
    raw = shop()
    raw["entities"]["order"]["fields"]["ship_city"] = "$customer.address.town"

    [problem] = problems_of(raw)
    assert problem.path == "entities.order.fields.ship_city"
    assert "'customer.address' has no field 'town'" in problem.message


def test_path_through_a_field_that_is_not_an_object():
    raw = shop()
    raw["entities"]["order"]["fields"]["ship_city"] = "$customer.id.city"

    [problem] = problems_of(raw)
    assert "'customer.id' has no field 'city'" in problem.message


@pytest.mark.parametrize("text", ["$customer.", "$customer..id", "$customer.address."])
def test_malformed_nested_shorthand(text):
    raw = shop()
    raw["entities"]["order"]["fields"]["ship_city"] = text

    assert "'$entity.field'" in problem_text(raw)


def test_path_through_a_copied_object_in_any_declaration_order():
    forward = shop()
    backward = shop()
    backward["entities"] = dict(reversed(list(backward["entities"].items())))

    assert run(forward) == run(backward)


def test_reference_inside_an_object_counts_for_ordering_and_cycles():
    simulation = dataspecter.generate(load_spec(shop()))
    assert simulation.entities == ("customer", "order", "invoice")

    cyclic = shop()
    cyclic["entities"]["customer"]["fields"]["address"]["fields"]["last"] = "$order.id"
    assert "circular reference between entities" in problem_text(cyclic)


def test_nested_values_come_from_the_chosen_row():
    data = run(SHOP)
    customers = {row["id"]: row for row in data["customer"]}

    for order in data["order"]:
        address = customers[order["customer_id"]]["address"]
        assert order["ship_to"] == address
        assert order["ship_city"] == (address["city"] if address else None)
        assert order["billing"]["customer_id"] == order["customer_id"]
        assert order["billing"]["geo_lat"] == (address["geo"]["lat"] if address else None)
    assert any(order["ship_to"] is None for order in data["order"])
    assert any(order["ship_to"] is not None for order in data["order"])


def test_reading_through_a_copied_object():
    data = run(SHOP)
    orders = {row["id"]: row for row in data["order"]}

    for invoice in data["invoice"]:
        ship_to = orders[invoice["order_id"]]["ship_to"]
        assert invoice["city"] == (ship_to["city"] if ship_to else None)


def test_copied_objects_are_independent():
    simulation = dataspecter.generate(load_spec(shop()))
    customers = list(simulation.records("customer"))
    orders = list(simulation.records("order"))

    first = next(order for order in orders if order["ship_to"] is not None)
    original_city = first["ship_to"]["city"]
    first["ship_to"]["city"] = "CHANGED"
    first["ship_to"]["geo"]["lat"] = 999

    others = [order for order in orders if order is not first and order["ship_to"]]
    assert all(order["ship_to"]["city"] != "CHANGED" for order in others)
    assert all(order["ship_to"]["geo"]["lat"] != 999 for order in others)
    assert all(row["address"]["city"] != "CHANGED" for row in customers if row["address"])
    invoices = list(simulation.records("invoice"))
    assert all(invoice["city"] != "CHANGED" for invoice in invoices)
    assert original_city != "CHANGED"


def test_child_generated_alone_equals_the_full_pass():
    expected = run(SHOP)["invoice"]
    simulation = dataspecter.generate(load_spec(shop()))

    assert list(simulation.records("invoice")) == expected


# --- export and the Python API ----------------------------------------------------------------


def test_column_paths():
    simulation = dataspecter.generate(load_spec(shop()))

    assert simulation.columns("invoice") == ("id", "city", "order_id")
    assert simulation.columns("order") == (
        "id",
        "customer_id",
        "ship_city",
        "ship_to.city",
        "ship_to.postcode",
        "ship_to.geo.lat",
        "ship_to.geo.lon",
        "billing.customer_id",
        "billing.geo_lat",
    )
    with pytest.raises(KeyError):
        simulation.columns("nope")


def test_csv_flattens_objects(tmp_path):
    fields = {
        "id": {"type": "sequence"},
        "address": ADDRESS,
        "tier": {"type": "constant", "value": "free"},
    }
    dataspecter.write(load_spec(entity_of(fields)), out_dir=tmp_path, format="csv")
    lines = (tmp_path / "customer.csv").read_text(encoding="utf-8").splitlines()

    assert lines[0] == "id,address.city,address.postcode,tier"
    assert len(lines[1].split(",")) == 4


def test_csv_null_object_is_empty_cells(tmp_path):
    fields = {
        "id": {"type": "sequence"},
        "address": {**ADDRESS, "null_probability": 1},
        "tier": {"type": "constant", "value": "free"},
    }
    dataspecter.write(load_spec(entity_of(fields)), out_dir=tmp_path, format="csv")

    assert (tmp_path / "customer.csv").read_text(encoding="utf-8").splitlines()[1] == "1,,,free"


def test_csv_columns_of_a_copied_object(tmp_path):
    dataspecter.write(load_spec(shop()), out_dir=tmp_path, format="csv")
    header = (tmp_path / "order.csv").read_text(encoding="utf-8").splitlines()[0]

    assert "ship_to.city,ship_to.postcode,ship_to.geo.lat,ship_to.geo.lon" in header


def test_json_and_jsonl_nest_objects(tmp_path):
    spec = load_spec(shop())
    dataspecter.write(spec, out_dir=tmp_path, format="json")
    dataspecter.write(spec, out_dir=tmp_path, format="jsonl")

    customers = json.loads((tmp_path / "customer.json").read_text(encoding="utf-8"))
    assert any(row["address"] is None for row in customers)
    full = next(row for row in customers if row["address"])
    assert set(full["address"]) == {"city", "postcode", "geo"}
    assert set(full["address"]["geo"]) == {"lat", "lon"}
    lines = (tmp_path / "customer.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == customers


def test_double_underscore_separator(tmp_path):
    spec = load_spec(entity_of({"address": ADDRESS}, csv_separator="__"))
    dataspecter.write(spec, out_dir=tmp_path, format="csv")
    dataspecter.write(spec, out_dir=tmp_path, format="json")

    assert (
        (tmp_path / "customer.csv")
        .read_text(encoding="utf-8")
        .startswith("address__city,address__postcode\n")
    )
    assert "address" in json.loads((tmp_path / "customer.json").read_text(encoding="utf-8"))[0]


def test_unsupported_separator():
    [problem] = problems_of(entity_of({"address": ADDRESS}, csv_separator="/"))

    assert problem.path == "output.csv_separator"
    assert "'.' or '__'" in problem.message


def test_colliding_column_names():
    fields = {"address__city": {"type": "uuid"}, "address": ADDRESS}

    [problem] = problems_of(entity_of(fields, csv_separator="__"))
    assert problem.path == "entities.customer"
    assert "'address__city'" in problem.message and "'address.city'" in problem.message

    load_spec(entity_of(fields))  # no collision with the default separator
