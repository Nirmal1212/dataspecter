# Tasks

## 1. Project scaffolding

- [x] 1.1 Add `pyproject.toml` (hatchling, Python >=3.11, version 0.1.0, pyyaml as the only runtime dependency, dev extra with pytest and ruff, `dataspecter` console script, ruff and pytest config) and verify `uv sync --extra dev` succeeds
- [x] 1.2 Create `src/dataspecter/__init__.py` with `__version__` and an empty `tests/` package, and verify `uv run python -c "import dataspecter; print(dataspecter.__version__)"` prints `0.1.0`
- [x] 1.3 Add a smoke test that imports the package and verify `uv run pytest` and `uv run ruff check .` both pass
- [x] 1.4 Record the tech stack and the build, test and lint commands in `CLAUDE.md` and in the `context` block of `openspec/config.yaml`, and verify `openspec validate --all --strict` still passes

## 2. Spec model and validation

- [x] 2.1 Add `errors.py` with `SpecError` (list of problems, each with a dotted location path and message) and `ExportError`, and verify with a unit test that a `SpecError` exposes its problems and renders them one per line
- [x] 2.2 Implement the frozen dataclasses in `spec.py` for the top-level spec, entities, `output` and each of the ten field types, and the validator that builds them from a raw mapping while collecting located problems, with a table of allowed keys per field type and strict type checks (no string-to-number coercion, booleans rejected as numbers); verify with tests for a minimal valid spec, unsupported version, empty entities, unknown key, invalid name and unknown field type
- [x] 2.3 Add the single-field rules (min not above max, uniform needs min and max, normal needs mean and positive stddev, `ranges` exclusive with min/max, weight rules, weights matching values, date ordering, non-zero step, probabilities in 0 to 1) and verify each with a test taken from the `simulation-spec` scenarios
- [x] 2.4 Add the cross-entity pass (reference target entity and field exist, no self-reference, no cycles) and verify with tests for a valid forward reference, unknown entity, unknown field and a two-entity cycle
- [x] 2.5 Implement `load_spec` for a path (`.yaml`, `.yml`, `.json`) and for a mapping, converting every failure into `SpecError`; verify with tests for YAML, JSON, mapping, unsupported extension, malformed syntax, missing file, and two problems reported together with their paths

## 3. Value generators

- [x] 3.1 Implement per-field random streams seeded from a SHA-256 digest of seed, entity and field, with a separate stream for null decisions; verify with a test that the same inputs give the same sequence and that different field names give different sequences
- [x] 3.2 Implement the numeric generators (uniform, normal with resampling then clamping, weighted ranges, float precision, integer rounding) and verify with fixed-seed tests for bounds, the mean of a normal field, and range proportions within the tolerances in the `data-generation` spec
- [x] 3.3 Implement the `boolean`, `choice`, `date`, `datetime`, `sequence`, `uuid` and `constant` generators and verify each against its scenarios, including weighted choice proportions and 10,000 unique valid UUIDs
- [x] 3.4 Apply `null_probability` uniformly across field types and verify with tests for probability 0, probability 1 and a 10% proportion

## 4. Generation engine

- [x] 4.1 Implement seed resolution (explicit seed, then spec seed, then a random seed that is recorded) and verify with tests for each of the three cases
- [x] 4.2 Implement topological ordering of entities by their references and verify with tests that a child declared before its parent, and a three-entity chain, are ordered parents first
- [x] 4.3 Implement row iteration that yields one dict per row in declared field order while retaining only referenced columns, and verify with tests for exact row counts, field order, and that an unreferenced field is not retained
- [x] 4.4 Implement reference resolution from the retained parent columns and verify with tests that every child value exists among the parent's values, for a single reference and for a chain
- [x] 4.5 Add reproducibility tests and verify that the same seed gives identical rows, different seeds differ, and adding a field or an entity leaves all existing values unchanged

## 5. File export

- [x] 5.1 Implement the exporter interface, the format registry and the shared value serialiser, and verify with unit tests that dates, date-times, booleans and nulls serialise as the `file-export` spec requires
- [x] 5.2 Implement the CSV exporter and verify with tests for the header row, line count, quoting of a value containing a comma, an empty field for null, and LF line endings
- [x] 5.3 Implement the JSON and JSON Lines exporters, writing incrementally, and verify with tests that the JSON file parses as an array of the right length with native types, and that each JSON Lines line parses on its own
- [x] 5.4 Implement output directory creation, per-entity file naming, overwrite, and `ExportError` on write failure; verify with tests for a nested directory that does not exist, replacement of an existing file, and an unwritable path

## 6. Python API

- [x] 6.1 Implement `generate(spec, seed=None)` returning a `Simulation` with `seed`, entity names and `records(entity)`, and verify with tests for iterating an entity, native Python value types, and reading back the chosen seed
- [x] 6.2 Implement `write(spec, out_dir=None, format=None, seed=None)` with arguments overriding the spec's `output` block overriding the defaults, returning the seed and per-entity row counts and paths; verify with tests for each level of precedence and for an unsupported format
- [x] 6.3 Export `load_spec`, `generate`, `write`, `SpecError` and `ExportError` from `dataspecter`, and verify with a test that using them writes nothing to stdout or stderr

## 7. Command line

- [x] 7.1 Implement `cli.py` with `argparse`: `generate` (with `--out`, `--format`, `--seed`), `validate`, `--version` and `--help`; verify with tests that call `main()` for a successful generate, each option override, a valid `validate`, `--version` and `generate --help`
- [x] 7.2 Map failures to exit codes and stderr (2 for an invalid spec, unreadable spec file or bad arguments; 1 otherwise) and verify with tests for an invalid spec on `generate` leaving no files, an invalid spec on `validate`, a missing file, `--format xml`, and an unwritable output path
- [x] 7.3 Add a test that the files written by the CLI and by `write()` for the same spec, seed and format are byte-for-byte identical

## 8. Examples and documentation

- [x] 8.1 Add `examples/shop.yaml` (customer, order and order_item with references, weighted ranges, a normal field, weighted choice and nulls) and its JSON equivalent, and verify with a test that both validate and produce identical data for the same seed
- [x] 8.2 Document installation, a quick start, the CLI and the Python API in `README.md`, add `docs/spec-reference.md` covering every field type and option, and verify that each documented command runs as written against `examples/shop.yaml`

## 9. Integration and wrap-up

- [ ] 9.1 Run the installed `dataspecter generate examples/shop.yaml` in all three formats and verify the files open correctly and every reference resolves
- [ ] 9.2 Generate one million rows of a five-field entity to CSV, record the time and peak memory in the pull request description, and verify memory stays flat as the row count grows
- [ ] 9.3 Verify `uv run pytest`, `uv run ruff check .` and `openspec validate add-core-simulator --strict` all pass
- [ ] 9.4 Add the entry for this change under `[Unreleased]` in `CHANGELOG.md` and verify it lists the spec format, generation, export formats, CLI and Python API
- [ ] 9.5 Archive the change with `/opsx:archive` and verify `openspec/specs/` contains the five new capability specs
