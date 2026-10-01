"""The shipped example specs stay valid and equivalent to each other."""

from pathlib import Path

import dataspecter

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_yaml_and_json_examples_are_the_same_spec():
    assert dataspecter.load_spec(EXAMPLES / "shop.yaml") == dataspecter.load_spec(
        EXAMPLES / "shop.json"
    )


def test_yaml_and_json_examples_produce_identical_data():
    from_yaml = dataspecter.generate(dataspecter.load_spec(EXAMPLES / "shop.yaml"), seed=7)
    from_json = dataspecter.generate(dataspecter.load_spec(EXAMPLES / "shop.json"), seed=7)

    assert from_yaml.entities == ("customer", "product", "order", "order_item")
    for entity in from_yaml.entities:
        assert list(from_yaml.records(entity)) == list(from_json.records(entity))


def test_every_reference_in_the_example_resolves():
    simulation = dataspecter.generate(dataspecter.load_spec(EXAMPLES / "shop.yaml"))
    data = {entity: list(simulation.records(entity)) for entity in simulation.entities}

    customers = {row["id"] for row in data["customer"]}
    orders = {row["id"] for row in data["order"]}
    products = {row["id"] for row in data["product"]}
    assert all(row["customer_id"] in customers for row in data["order"])
    assert all(row["order_id"] in orders for row in data["order_item"])
    assert all(row["product_id"] in products for row in data["order_item"])


def test_copied_values_in_the_example_come_from_the_same_parent_row():
    simulation = dataspecter.generate(dataspecter.load_spec(EXAMPLES / "shop.yaml"))
    data = {entity: list(simulation.records(entity)) for entity in simulation.entities}

    price_of = {row["id"]: row["price"] for row in data["product"]}
    tier_of = {row["id"]: row["tier"] for row in data["customer"]}
    assert all(row["unit_price"] == price_of[row["product_id"]] for row in data["order_item"])
    assert all(row["customer_tier"] == tier_of[row["customer_id"]] for row in data["order"])


def test_example_shorthands_produce_nulls_and_integers():
    simulation = dataspecter.generate(dataspecter.load_spec(EXAMPLES / "shop.yaml"))
    codes = [row["referral_code"] for row in simulation.records("customer")]
    levels = {row["gift_wrap_level"] for row in simulation.records("order_item")}

    assert 0.4 < codes.count(None) / len(codes) < 0.6
    assert levels == {0, 1, 2}


def test_example_shipping_city_is_read_from_the_customers_address():
    simulation = dataspecter.generate(dataspecter.load_spec(EXAMPLES / "shop.yaml"))
    customers = {row["id"]: row for row in simulation.records("customer")}
    orders = list(simulation.records("order"))

    for order in orders:
        address = customers[order["customer_id"]]["address"]
        assert order["ship_city"] == (address["city"] if address else None)
    assert any(order["ship_city"] is None for order in orders)
    assert simulation.columns("customer")[-2:] == ("address.city", "address.postcode")


def test_example_text_fields_types_and_hidden_fields():
    import re

    simulation = dataspecter.generate(dataspecter.load_spec(EXAMPLES / "shop.yaml"))
    customers = list(simulation.records("customer"))
    products = list(simulation.records("product"))

    assert all("first_name" not in row and "last_name" not in row for row in customers)
    assert all(re.fullmatch(r"[a-z-]+\.[a-z-]+@example\.com", row["email"]) for row in customers)
    assert "email" in simulation.columns("customer")
    codes = [row["code"] for row in products]
    assert len(set(codes)) == len(codes)
    assert all(re.fullmatch(r"SKU-[A-Z]{2}-\d{4}", code) for code in codes)
    assert all(row["list_price"]["currency"] == "USD" for row in products)
    assert simulation.columns("product")[1:4] == (
        "code",
        "list_price.amount",
        "list_price.currency",
    )
