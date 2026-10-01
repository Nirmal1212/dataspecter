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
      tier: {type: choice, values: [free, pro, enterprise], weights: [70, 25, 5]}
      age:
        type: integer
        ranges:
          - {min: 18, max: 35, weight: 0.7}
          - {min: 36, max: 60, weight: 0.25}
          - {min: 61, max: 90, weight: 0.05}
  order:
    count: 5000
    fields:
      id: {type: uuid}
      customer_id: {type: reference, entity: customer, field: id}
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

[docs/spec-reference.md](docs/spec-reference.md) documents every field type and option. [examples/shop.yaml](examples/shop.yaml) and its JSON twin [examples/shop.json](examples/shop.json) show them in use.

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
