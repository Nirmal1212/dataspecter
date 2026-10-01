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
