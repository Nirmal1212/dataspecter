# dataspecter

Config-driven synthetic data simulator. Describe your entities, value ranges and probability distributions in a YAML or JSON spec, and get reproducible CSV, JSON or JSON Lines files.

```yaml
version: 1
seed: 42
entities:
  customer:
    count: 1000
    fields:
      id: {type: sequence, start: 1001}
      tier: {type: choice, values: [free || 70, pro || 25, enterprise || 5]}
      age: {type: integer, ranges: [18 to 35 || 0.7, 36 to 60 || 0.25, 61 to 90 || 0.05]}
  order:
    count: 5000
    fields:
      id: {type: uuid}
      customer_id: $customer.id
      customer_tier: $customer.tier
      total: {type: float, distribution: normal, mean: 40, stddev: 15, min: 5, precision: 2}
```

## Status

Early development, version 0.1.0, not yet released or published. Streaming to an HTTP endpoint is planned but not built.

## Install

dataspecter needs Python 3.11 or newer. From a checkout of this repository:

```bash
pip install .
```

## Quick start

Generate the example shop (customers, products, orders and order items) as CSV:

```bash
dataspecter generate examples/shop.yaml
```

```
Seed: 42
customer         1000 rows  output\shop\customer.csv
product            50 rows  output\shop\product.csv
order            5000 rows  output\shop\order.csv
order_item      12000 rows  output\shop\order_item.csv
```

The same spec and seed always produce the same files.

## Command line

```bash
dataspecter generate examples/shop.yaml --out out/run1 --format jsonl --seed 7
```

```bash
dataspecter validate examples/shop.yaml
```

| Command | What it does |
|---|---|
| `generate <spec>` | Validates the spec, generates every entity and writes one file per entity. |
| `validate <spec>` | Checks the spec and reports every problem with its location. Writes nothing. |

| Option of `generate` | Meaning | Default |
|---|---|---|
| `--out DIR` | Output directory | the spec's `output.dir`, else `output` |
| `--format csv\|json\|jsonl` | Output format | the spec's `output.format`, else `csv` |
| `--seed INTEGER` | Seed for the run | the spec's `seed`, else a random one that is printed |

Exit codes: `0` on success, `2` when the spec or the arguments are invalid or the spec file cannot be read, `1` for any other failure.

`python -m dataspecter` is equivalent to the `dataspecter` command, for environments that do not allow the installed script to run.

## Python API

```python
import dataspecter

spec = dataspecter.load_spec("examples/shop.yaml")  # or a dict of the same shape

simulation = dataspecter.generate(spec, seed=42)
for customer in simulation.records("customer"):
    print(customer["id"], customer["tier"], customer["age"])
    break

result = dataspecter.write(spec, out_dir="out/api", format="json", seed=42)
print(result.seed, [(entity.name, entity.rows) for entity in result.entities])
```

Records are plain dicts holding `int`, `float`, `bool`, `str`, `datetime.date`, `datetime.datetime` or `None`. An invalid spec raises `dataspecter.SpecError`, whose `problems` list every issue with its location; a file that cannot be written raises `dataspecter.ExportError`.

## Writing a spec

A spec lists entities; each entity has a row `count` and `fields`; each field has a `type`. [docs/spec-reference.md](docs/spec-reference.md) documents every option in full, and [examples/shop.yaml](examples/shop.yaml) with its JSON twin [examples/shop.json](examples/shop.json) shows them in use.

### Supported field types

| Type | Generates | Options |
|---|---|---|
| `integer` | Whole numbers | `min`, `max`, `distribution`, `mean`, `stddev`, or `ranges` |
| `float` | Decimal numbers | the same as `integer`, plus `precision` |
| `boolean` | `true` or `false` | `true_probability` (default 0.5) |
| `choice` | One of a list of values | `values`, `weights`, `value_type` |
| `date` | Calendar dates | `min`, `max` |
| `datetime` | Date-times | `min`, `max` |
| `sequence` | A counter: 1, 2, 3, ... | `start`, `step` |
| `uuid` | Unique identifiers | none |
| `constant` | The same value in every row | `value` |
| `reference` | A value taken from another entity's rows | `entity`, `field`, `link` |

Every type also accepts `null_probability`, the share of rows (0 to 1) that are null instead.

### Supported operations on values

| Operation | How to write it |
|---|---|
| Uniform range | `{type: integer, min: 18, max: 90}` |
| Normal distribution, optionally bounded | `{type: float, distribution: normal, mean: 40, stddev: 15, min: 5, max: 200}` |
| Weighted ranges | `ranges` with a `weight` per range, or `18 to 35 \|\| 0.7` |
| Rounding | `precision: 2` on a `float` |
| Equal-chance choice | `{type: choice, values: [books, games, music]}` |
| Weighted choice | `values` with a matching `weights` list, or `free \|\| 70` |
| Nulls | `null_probability: 0.8` on any field, or a null entry in `values` |
| Link to another entity | `{type: reference, entity: customer, field: id}`, or `$customer.id` |
| Copy several values from one parent row | two references to the same entity |
| Two independent rows of one entity | references with different `link` names |
| Reproducible runs | `seed` in the spec, or `--seed` |

Weights are relative: `[70, 25, 5]` means the same as `[0.7, 0.25, 0.05]`.

### Long form and shorthand

Several things can be written two ways. The long form spells everything out as keys; the shorthand says the same in one string. They are interchangeable, can be mixed in one spec, and generate identical data.

Long form:

```yaml
version: 1
seed: 42
entities:
  customer:
    count: 1000
    fields:
      id: {type: sequence, start: 1001}
      tier:
        type: choice
        values: [free, pro, enterprise]
        weights: [70, 25, 5]
      age:
        type: integer
        ranges:
          - {min: 18, max: 35, weight: 0.7}
          - {min: 36, max: 60, weight: 0.25}
          - {min: 61, max: 90, weight: 0.05}
      referral_code:
        type: choice
        values: [FRIEND10, LAUNCH25, PARTNER, null]
        weights: [0.2, 0.2, 0.1, 0.5]
      visits:
        type: choice
        values: [1, 2, 5]
        weights: [60, 30, 10]
  order:
    count: 5000
    fields:
      id: {type: uuid}
      customer_id: {type: reference, entity: customer, field: id}
```

Shorthand:

```yaml
version: 1
seed: 42
entities:
  customer:
    count: 1000
    fields:
      id: {type: sequence, start: 1001}
      tier:
        type: choice
        values: [free || 70, pro || 25, enterprise || 5]
      age:
        type: integer
        ranges: [18 to 35 || 0.7, 36 to 60 || 0.25, 61 to 90 || 0.05]
      referral_code:
        type: choice
        values: [FRIEND10 || 0.2, LAUNCH25 || 0.2, PARTNER || 0.1, " || 0.5"]
      visits:
        type: choice
        value_type: integer
        values: [1 || 60, 2 || 30, 5 || 10]
  order:
    count: 5000
    fields:
      id: {type: uuid}
      customer_id: $customer.id
```

| Shorthand | Long form it replaces | Notes |
|---|---|---|
| `$customer.id` | `{type: reference, entity: customer, field: id}` | The whole field definition is the string. |
| `value \|\| weight` in `values` | separate `values` and `weights` lists | An empty value means null. Every entry carries a weight, or none does. |
| `value_type: integer` | typed entries in a `values` list | Inline values are text unless the field declares `integer`, `float` or `boolean`. |
| `min to max \|\| weight` in `ranges` | `{min: ..., max: ..., weight: ...}` | `to` needs a space on each side. |

In YAML, quote the null entry (`" || 0.5"`), because a leading `|` means something else there. In JSON every shorthand is an ordinary string.

### References and shared rows

All references from one entity to the same target read from the same row, so several values can be copied from one parent:

```yaml
version: 1
entities:
  product:
    count: 50
    fields:
      id: {type: sequence}
      price: {type: float, min: 5, max: 200, precision: 2}
  order_item:
    count: 12000
    fields:
      product_id: $product.id
      unit_price: $product.price
```

Each order item gets one product's id and that same product's price. To pick two unrelated rows of the same entity, such as a sender and a receiver, use the long form with different `link` names; see the [reference](docs/spec-reference.md#references).

## Development

```bash
uv sync --extra dev
```

```bash
uv run pytest
```

```bash
uv run ruff check .
```

This project is spec-driven: changes are proposed with [OpenSpec](https://github.com/Fission-AI/OpenSpec) before they are built, and move through Git Flow branches. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full process.

After cloning, enable the commit message hook:

```bash
git config core.hooksPath .githooks
```
