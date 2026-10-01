"""Every YAML example in the docs loads, and each long form equals its shorthand."""

import re
from pathlib import Path

import pytest
import yaml

import dataspecter
from dataspecter.spec import _Loader

ROOT = Path(__file__).parent.parent
REFERENCE = (ROOT / "docs" / "spec-reference.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")

YAML_BLOCK = re.compile(r"```yaml\n(.*?)```", re.S)
PAIR = re.compile(
    r"Long form[^\n]*\n\n```yaml\n(.*?)```\n\nShorthand[^\n]*\n\n```yaml\n(.*?)```", re.S
)


def as_spec(block: str) -> dict:
    """Return a block as a full spec; a block of bare fields is wrapped in one entity."""
    raw = yaml.load(block, Loader=_Loader)
    if "version" in raw:
        return raw
    return {"version": 1, "entities": {"example": {"count": 5, "fields": raw}}}


def blocks(text: str) -> list[str]:
    return YAML_BLOCK.findall(text)


@pytest.mark.parametrize("block", blocks(REFERENCE) + blocks(README))
def test_every_yaml_example_is_a_valid_spec(block):
    spec = dataspecter.load_spec(as_spec(block))
    simulation = dataspecter.generate(spec, seed=1)

    for entity in simulation.entities:
        assert next(simulation.records(entity))


PAIRS = PAIR.findall(REFERENCE) + PAIR.findall(README)


def test_the_docs_show_long_and_shorthand_pairs():
    assert len(PAIR.findall(REFERENCE)) == 5
    assert len(PAIR.findall(README)) >= 1


@pytest.mark.parametrize(("long", "short"), PAIRS)
def test_long_form_and_shorthand_are_the_same_spec(long, short):
    long_spec = dataspecter.load_spec(as_spec(long))
    short_spec = dataspecter.load_spec(as_spec(short))

    assert long_spec == short_spec
    for entity in long_spec.entities:
        assert list(dataspecter.generate(long_spec, seed=7).records(entity)) == list(
            dataspecter.generate(short_spec, seed=7).records(entity)
        )


def test_sender_and_receiver_example_behaves_as_described():
    block = next(b for b in blocks(REFERENCE) if "link: sender" in b)
    simulation = dataspecter.generate(dataspecter.load_spec(as_spec(block)), seed=1)
    name_of = {row["id"]: row["name"] for row in simulation.records("account")}
    transfers = list(simulation.records("transfer"))

    assert all(row["sender_name"] == name_of[row["sender_id"]] for row in transfers)
    assert sum(row["sender_id"] != row["receiver_id"] for row in transfers) > 900


def test_copied_price_example_behaves_as_described():
    block = next(b for b in blocks(REFERENCE) if "unit_price: $product.price" in b)
    simulation = dataspecter.generate(dataspecter.load_spec(as_spec(block)), seed=1)
    price_of = {row["id"]: row["price"] for row in simulation.records("product")}

    assert all(
        row["unit_price"] == price_of[row["product_id"]] for row in simulation.records("order_item")
    )
