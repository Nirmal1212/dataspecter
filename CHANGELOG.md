# Changelog

All notable changes to dataspecter are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Project scaffolding: OpenSpec, Git Flow process, Conventional Commits hook.
- Simulation spec format, version 1, written in YAML or JSON: named entities with a row count and typed fields, an optional seed and optional output settings. Specs are validated completely before anything is generated, and every problem is reported with its location.
- Data generation for the field types `integer`, `float`, `boolean`, `choice`, `date`, `datetime`, `sequence`, `uuid`, `constant` and `reference`, with uniform and normal distributions, weighted ranges, weighted choices and a per-field null probability.
- References between entities: a field can draw its values from another entity's generated rows, in any declaration order and through chains.
- Reproducible runs: the same spec and seed always produce the same data, and editing one part of a spec leaves the values of the rest unchanged.
- File export to CSV, JSON and JSON Lines, one file per entity.
- `dataspecter` command with `generate` (`--out`, `--format`, `--seed`) and `validate`, also runnable as `python -m dataspecter`.
- Python API: `load_spec`, `generate` and `write`, with `SpecError` and `ExportError`.
- Reference shorthand: a field can be written as `$entity.field` instead of a `reference` mapping.
- `link` on a `reference`, so that two references to the same entity can choose their rows independently.
- Weighted value shorthand for `choice`: `value || weight` entries in `values`, with an empty value meaning null.
- `value_type` (`string`, `integer`, `float`, `boolean`) to type the values written with inline weights.
- Null entries in `choice` values, in the list form as well as the shorthand.
- Weighted range shorthand: `min to max || weight` items in `ranges`.
- The spec reference documents every long form next to its shorthand, and states how `null_probability` combines with a field's own values.

### Changed

- **BREAKING:** all references from one entity to the same target entity now read from the same target row, so several values can be copied from one parent (`product_id: $product.id` with `unit_price: $product.price`). Previously each reference chose its own row. For a given seed, reference fields produce different values than before; use different `link` names where independent rows are wanted.
