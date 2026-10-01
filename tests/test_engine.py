"""Row generation, references and reproducibility (data-generation capability)."""

import copy

import pytest

from dataspecter.engine import Simulation, generation_order, resolve_seed
from dataspecter.spec import load_spec

SHOP = {
    "version": 1,
    "entities": {
        # Children are declared before their parents on purpose.
        "order_item": {
            "count": 300,
            "fields": {
                "id": {"type": "sequence"},
                "order_id": {"type": "reference", "entity": "order", "field": "id"},
                "quantity": {"type": "integer", "min": 1, "max": 5},
            },
        },
        "order": {
            "count": 120,
            "fields": {
                "id": {"type": "uuid"},
                "customer_id": {"type": "reference", "entity": "customer", "field": "id"},
                "total": {"type": "float", "min": 5, "max": 500, "precision": 2},
            },
        },
        "customer": {
            "count": 40,
            "fields": {
                "id": {"type": "sequence", "start": 1001},
                "tier": {"type": "choice", "values": ["free", "pro"]},
                "age": {"type": "integer", "min": 18, "max": 90},
            },
        },
    },
}


def shop(**changes) -> dict:
    raw = copy.deepcopy(SHOP)
    raw.update(changes)
    return raw


def run(raw: dict, seed: int | None = 42) -> dict[str, list[dict]]:
    simulation = Simulation(load_spec(raw), seed)
    return {name: list(simulation.records(name)) for name in simulation.entities}


# --- seed resolution --------------------------------------------------------------------------


def test_explicit_seed_takes_precedence_over_the_spec():
    assert resolve_seed(load_spec(shop(seed=42)), 7) == 7


def test_spec_seed_is_used_when_none_is_given():
    assert resolve_seed(load_spec(shop(seed=42))) == 42


def test_a_seed_is_chosen_and_recorded_when_none_is_supplied():
    spec = load_spec(shop())
    simulation = Simulation(spec)

    assert isinstance(simulation.seed, int) and simulation.seed >= 0
    first = list(simulation.records("customer"))
    assert list(Simulation(spec, simulation.seed).records("customer")) == first


@pytest.mark.parametrize("seed", [-1, 1.5, "7", True])
def test_invalid_explicit_seed(seed):
    with pytest.raises(ValueError, match="non-negative integer"):
        resolve_seed(load_spec(shop()), seed)


# --- ordering ---------------------------------------------------------------------------------


def test_parents_are_ordered_before_children_in_a_chain():
    assert generation_order(load_spec(shop())) == ("customer", "order", "order_item")


def test_unrelated_entities_keep_their_declared_order():
    raw = shop()
    for entity in raw["entities"].values():
        entity["fields"] = {"id": {"type": "sequence"}}

    assert generation_order(load_spec(raw)) == ("order_item", "order", "customer")


# --- rows -------------------------------------------------------------------------------------


def test_row_count_is_honoured():
    data = run(SHOP)

    assert {name: len(rows) for name, rows in data.items()} == {
        "customer": 40,
        "order": 120,
        "order_item": 300,
    }


def test_field_order_is_preserved_in_every_row():
    rows = run(SHOP)["customer"]

    assert all(list(row) == ["id", "tier", "age"] for row in rows)


def test_rows_are_produced_lazily():
    simulation = Simulation(load_spec(shop()), 42)
    rows = simulation.records("customer")

    assert next(rows)["id"] == 1001
    assert next(rows)["id"] == 1002


def test_only_referenced_fields_are_retained():
    simulation = Simulation(load_spec(shop()), 42)
    for name in simulation.entities:
        for _ in simulation.records(name):
            pass

    assert set(simulation._columns) == {("customer", "id"), ("order", "id")}


def test_unknown_entity_is_rejected():
    with pytest.raises(KeyError, match="unknown entity 'invoice'"):
        Simulation(load_spec(shop()), 42).records("invoice")


# --- references -------------------------------------------------------------------------------


def test_every_reference_resolves():
    data = run(SHOP)
    customer_ids = {row["id"] for row in data["customer"]}

    assert all(row["customer_id"] in customer_ids for row in data["order"])


def test_chained_references_resolve():
    data = run(SHOP)
    order_ids = {row["id"] for row in data["order"]}

    assert all(row["order_id"] in order_ids for row in data["order_item"])


def test_a_child_can_be_generated_without_iterating_its_parents():
    expected = run(SHOP)["order_item"]
    simulation = Simulation(load_spec(shop()), 42)

    assert list(simulation.records("order_item")) == expected


def test_reference_to_a_reference_field():
    raw = shop()
    raw["entities"]["order_item"]["fields"]["customer_id"] = {
        "type": "reference",
        "entity": "order",
        "field": "customer_id",
    }
    data = run(raw)
    customer_ids = {row["id"] for row in data["customer"]}

    assert all(row["customer_id"] in customer_ids for row in data["order_item"])


# --- reproducibility --------------------------------------------------------------------------


def test_same_seed_gives_identical_data():
    assert run(SHOP, seed=42) == run(SHOP, seed=42)


def test_different_seeds_give_different_data():
    assert run(SHOP, seed=42) != run(SHOP, seed=43)


def test_override_matches_a_spec_declaring_that_seed():
    assert run(shop(seed=42), seed=7) == run(shop(seed=7), seed=None)


def test_adding_a_field_leaves_existing_values_unchanged():
    before = run(SHOP)
    raw = shop()
    fields = raw["entities"]["customer"]["fields"]
    # Insert the new field first, so it also changes the position of every existing field.
    raw["entities"]["customer"]["fields"] = {
        "loyalty_points": {"type": "integer", "min": 0, "max": 5000},
        **fields,
    }
    after = run(raw)

    for row in after["customer"]:
        del row["loyalty_points"]
    assert after == before


def test_adding_an_entity_leaves_existing_rows_unchanged():
    before = run(SHOP)
    raw = shop()
    raw["entities"] = {
        "product": {"count": 10, "fields": {"id": {"type": "sequence"}}},
        **raw["entities"],
    }
    after = run(raw)

    del after["product"]
    assert after == before


# --- shared rows and links --------------------------------------------------------------------

LINKED = {
    "version": 1,
    "entities": {
        "order_item": {
            "count": 400,
            "fields": {
                "id": {"type": "sequence"},
                "product_id": "$product.id",
                "unit_price": "$product.price",
                "order_id": "$order.id",
                "buyer": "$order.customer_name",
            },
        },
        "order": {
            "count": 150,
            "fields": {
                "id": {"type": "uuid"},
                "customer_id": "$customer.id",
                "customer_name": "$customer.name",
            },
        },
        "product": {
            "count": 30,
            "fields": {
                "id": {"type": "sequence"},
                "price": {"type": "float", "min": 1, "max": 500, "precision": 2},
            },
        },
        "customer": {
            "count": 40,
            "fields": {
                "id": {"type": "sequence", "start": 1001},
                "name": {"type": "uuid"},
            },
        },
    },
}


def linked(**fields) -> dict:
    raw = copy.deepcopy(LINKED)
    raw["entities"]["order_item"]["fields"].update(fields)
    return raw


def test_values_are_copied_from_the_same_row():
    data = run(LINKED)
    price_of = {row["id"]: row["price"] for row in data["product"]}

    assert all(row["unit_price"] == price_of[row["product_id"]] for row in data["order_item"])
    assert len({row["product_id"] for row in data["order_item"]}) > 20


def test_shared_row_through_a_chain():
    data = run(LINKED)
    name_of = {row["id"]: row["name"] for row in data["customer"]}
    buyer_of = {row["id"]: name_of[row["customer_id"]] for row in data["order"]}

    assert all(row["buyer"] == buyer_of[row["order_id"]] for row in data["order_item"])


def account_reference(field: str, link: str) -> dict:
    return {"type": "reference", "entity": "account", "field": field, "link": link}


TRANSFER = {
    "version": 1,
    "entities": {
        "account": {
            "count": 100,
            "fields": {"id": {"type": "sequence"}, "name": {"type": "uuid"}},
        },
        "depot": {"count": 100, "fields": {"code": {"type": "sequence"}}},
        "transfer": {
            "count": 1000,
            "fields": {
                "sender_id": account_reference("id", "a"),
                "sender_name": account_reference("name", "a"),
                "receiver_id": account_reference("id", "b"),
                "owner_id": "$account.id",
                "depot_code": {
                    "type": "reference",
                    "entity": "depot",
                    "field": "code",
                    "link": "a",
                },
            },
        },
    },
}


def differing(rows, first, second) -> float:
    return sum(1 for row in rows if row[first] != row[second]) / len(rows)


def test_same_link_agrees_and_different_links_choose_independently():
    data = run(TRANSFER)
    name_of = {row["id"]: row["name"] for row in data["account"]}
    transfers = data["transfer"]

    assert all(row["sender_name"] == name_of[row["sender_id"]] for row in transfers)
    assert differing(transfers, "sender_id", "receiver_id") > 0.9


def test_a_reference_without_a_link_is_independent_of_linked_ones():
    transfers = run(TRANSFER)["transfer"]

    assert differing(transfers, "owner_id", "sender_id") > 0.9
    assert differing(transfers, "owner_id", "receiver_id") > 0.9


def test_the_same_link_name_on_two_entities_gives_unrelated_picks():
    transfers = run(TRANSFER)["transfer"]

    # Both entities count 1..100, so equal values would mean the same row index was chosen.
    assert differing(transfers, "sender_id", "depot_code") > 0.9


def test_child_generated_alone_equals_the_full_pass_including_copied_references():
    expected = run(LINKED)["order_item"]
    simulation = Simulation(load_spec(copy.deepcopy(LINKED)), 42)

    assert list(simulation.records("order_item")) == expected


def test_adding_a_second_reference_to_the_same_entity_leaves_the_first_unchanged():
    without = copy.deepcopy(LINKED)
    del without["entities"]["order_item"]["fields"]["unit_price"]

    before = [row["product_id"] for row in run(without)["order_item"]]
    after = [row["product_id"] for row in run(LINKED)["order_item"]]
    assert before == after


def test_a_null_in_one_reference_leaves_the_other_intact():
    price = {"type": "reference", "entity": "product", "field": "price", "null_probability": 0.5}
    data = run(linked(unit_price=price))
    price_of = {row["id"]: row["price"] for row in data["product"]}
    items = data["order_item"]

    assert all(row["product_id"] is not None for row in items)
    nulls = sum(1 for row in items if row["unit_price"] is None)
    assert 0.35 < nulls / len(items) < 0.65
    assert all(
        row["unit_price"] == price_of[row["product_id"]]
        for row in items
        if row["unit_price"] is not None
    )
