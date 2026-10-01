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
