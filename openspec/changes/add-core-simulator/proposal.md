# Proposal

## Why

Realistic test data is tedious to hand-write and risky to copy from production. dataspecter exists to produce it from a declarative spec, but the repository currently holds only scaffolding: there is no spec format, no generator and no output. This change delivers the first usable slice, so that a single YAML or JSON file can describe related entities and yield reproducible data files.

## What Changes

- Define the simulation spec format (version 1), written in YAML or JSON: named entities, a row count per entity, typed fields, an optional seed and optional output settings.
- Validate specs strictly and report every problem with its location in the file, before anything is generated.
- Generate data for these field types: `integer`, `float`, `boolean`, `choice`, `date`, `datetime`, `sequence`, `uuid`, `constant` and `reference`.
- Support realistic value shaping: uniform and normal distributions within bounds, weighted ranges ("70% between 18 and 35, 25% between 36 and 60, 5% between 61 and 90"), weighted choices, and a per-field null probability.
- Support multiple entities in one spec, with `reference` fields that draw their values from another entity's generated rows (for example `order.customer_id` from `customer.id`).
- Make generation reproducible: the same spec and seed always produce the same data.
- Export each entity to a file in CSV, JSON (array) or JSON Lines format.
- Provide a `dataspecter` command (`generate`, `validate`) and an importable Python API that the command is built on.

Out of scope for this change, each a candidate for its own follow-up: streaming records to an HTTP endpoint, realistic text providers (names, emails, addresses), derived or templated fields, uniqueness constraints on arbitrary fields, per-parent cardinality for references, and publishing to PyPI.

## Capabilities

### New Capabilities

- `simulation-spec`: the spec file format, how it is loaded from YAML or JSON, and the validation rules and error reporting applied to it.
- `data-generation`: how rows are produced from a valid spec, covering field types, distributions, weighted ranges, nulls, references between entities, and reproducibility.
- `file-export`: writing generated entities to CSV, JSON and JSON Lines files, including file naming, value serialisation and overwrite behaviour.
- `cli`: the `dataspecter` command, its subcommands and options, its output, and its exit codes.
- `python-api`: the importable interface for loading a spec, generating records and writing files from Python code.

### Modified Capabilities

None. There are no existing specs.

## Impact

- **Code**: introduces the first source tree, a Python package under `src/dataspecter/` with tests under `tests/` and example specs under `examples/`.
- **Tooling**: adds `pyproject.toml` (Python 3.11+, hatchling as build backend, pytest and ruff for development).
- **Dependencies**: one runtime dependency, `pyyaml`, for loading YAML specs. Everything else at runtime is the Python standard library.
- **Docs**: `README.md` gains installation and usage; `CLAUDE.md` and `openspec/config.yaml` record the chosen tech stack and the build, test and lint commands.
- **Compatibility**: nothing is released yet, so there is nothing to break. The spec format carries `version: 1` so later changes can evolve it deliberately.
