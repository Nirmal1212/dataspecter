# Design

## Context

The repository contains only process scaffolding; this change introduces the first source code. See `proposal.md` for motivation and scope, and the five spec deltas for required behaviour.

Constraints that shape the approach:

- Python was chosen as the language.
- dataspecter is both a command-line tool and a library imported into other people's test suites and notebooks. Every runtime dependency it carries becomes a constraint on those projects, so each one has to earn its place.
- Streaming records to an HTTP endpoint is the planned next change. It is out of scope here, but the engine must not make it awkward.
- The specs promise two things that constrain the internals: identical output for the same spec and seed, and unchanged values for existing fields when other fields or entities are added.

## Goals / Non-Goals

**Goals:**

- A small core with clear seams: spec model, value generators, engine, exporters, with the CLI as a thin layer over a public API.
- Memory use that does not grow with row count, except for columns that other entities reference.
- New field types and new output targets can be added without touching the engine.

**Non-Goals:**

- Raw throughput. Pure-Python row generation is acceptable for this change; vectorised generation can come later behind the same generator interface.
- Statistical variety beyond uniform, normal and weighted ranges.
- A plugin system for third-party field types or exporters. The registries are internal for now.

## Decisions

### 1. One runtime dependency; layout and tooling kept minimal

Each dependency was evaluated against what this change actually needs:

| Dependency | Kind | Verdict | Reason |
|---|---|---|---|
| PyYAML | runtime | **Keep** | YAML specs are a requirement and the standard library has no YAML parser. Pure-Python fallback, no dependencies of its own. Only safe loading is used. |
| pydantic | runtime | **Drop** | See decision 2. It would bring a compiled core and three further packages to validate a format with ten field types, and would pin every host project to a pydantic major version. |
| NumPy | runtime | **Not added** | See decision 3. The standard library's `random` covers every distribution in scope. |
| Click / Typer | runtime | **Not added** | See decision 7. `argparse` covers two subcommands and three options. |
| hatchling | build only | **Keep** | A build backend is needed to make the package installable and to expose the `dataspecter` command. It is never installed for users of the package. |
| pytest | dev only | **Keep** | The specs translate into many small parametrised cases that need temporary directories and captured output; `parametrize`, `tmp_path` and `capsys` do this directly. |
| ruff | dev only | **Keep** | One tool for linting and formatting. |

So the installed footprint is dataspecter plus PyYAML. Everything else used at runtime is standard library: `random`, `hashlib`, `secrets`, `csv`, `json`, `datetime`, `uuid`, `argparse`, `dataclasses`.

`requires-python = ">=3.11"`, because from 3.11 `date.fromisoformat` and `datetime.fromisoformat` parse the general ISO 8601 forms, which removes any need for a date-parsing library.

The package lives at `src/dataspecter/` (the `src/` layout stops tests from accidentally importing the working tree instead of the installed package), with tests in `tests/` and example specs in `examples/`. Ruff runs with rules `E`, `F`, `I`, `UP`, `B` and a 100-character line. Commands are written for `uv` (`uv sync --extra dev`, `uv run pytest`), but nothing depends on it: `pip install -e ".[dev]"` works equally.

Modules:

| Module | Responsibility |
|---|---|
| `spec.py` | Dataclasses for the spec, file and mapping loading, validation |
| `errors.py` | `SpecError` (carries a list of located problems) and `ExportError` |
| `generators.py` | One value generator per field type, built from a field model and a random stream |
| `engine.py` | Seed handling, entity ordering, row iteration, reference resolution |
| `exporters.py` | CSV, JSON and JSON Lines writers behind one small interface |
| `api.py` | Public functions, re-exported from `dataspecter/__init__.py` |
| `cli.py` | `argparse` entry point that calls the public API |

*Alternatives considered for the build backend:* setuptools (works, but needs more configuration for a `src/` layout) and Poetry (brings its own lock and metadata format for no benefit at this size).

### 2. Hand-written spec validation over plain dataclasses

The validated spec is a tree of frozen dataclasses: `Spec`, `Entity`, `Output`, and one class per field type. A validator walks the raw mapping and builds that tree, appending to a shared list of problems instead of raising, so every problem is found in one run. Each problem holds a dotted location path (`entities.order.fields.amount`) and a message; if the list is non-empty at the end, it is raised as one `SpecError`.

The validator is table-driven where it can be. Each field type declares its allowed keys, so unknown keys are found by set difference and reported by name, and an unknown `type` is reported with the list of supported types. Rules that span several keys (`min` not above `max`, `ranges` exclusive with `min`/`max`, `weights` matching `values`) live in the function for that field type. Rules that span entities (reference targets exist, no self-reference, no cycles) run as a second pass, and only over entities that parsed cleanly, since they need well-formed entities to reason about.

Type checks are strict rather than coercing: the string `"18"` is not accepted for `min`, and a boolean is not accepted where a number is expected (in Python `True` is an `int`, so this needs an explicit check).

*Alternatives considered:*
- **pydantic.** It would supply unknown-key rejection, a union discriminated on `type`, error collection and error paths without custom code. Rejected because the cost falls on users: pydantic installs a compiled core plus three more packages, and a library that depends on it forces its major version onto every project that imports dataspecter. What it would save is modest, since the format is small (ten field types, about twenty-five keys), the cross-entity rules have to be hand-written regardless, and the specs call for specific error wording (naming the supported types, the allowed name characters, the mutually exclusive forms) that would mean overriding pydantic's messages anyway.
- **JSON Schema with the `jsonschema` package.** Good for editor completion, but weak at cross-key rules and at readable messages, and it is still a dependency. A schema file for editors can be published later without being used for validation.

### 3. Standard-library randomness, one stream per field

Values come from `random.Random` (Mersenne Twister), which provides everything needed: `uniform`, `gauss`, `choices`, `randrange`, `getrandbits`.

Each field gets its own `Random` instance, seeded from a SHA-256 digest of `"{seed}:{entity}:{field}"`. Null decisions use a second stream per field (`...:null`), so changing `null_probability` does not shift the values themselves. This is what delivers the "stable values when a spec is edited" requirement: no field's stream depends on which other fields or entities exist.

Python's built-in `hash()` is not used for seeding because it is salted per process.

When no seed is supplied, the engine draws one from `secrets.randbits(32)` and records it on the result, so the run can be reported and repeated.

*Alternatives considered:*
- **A single shared `Random`.** Simplest, but adding a field shifts every later value, which makes iterating on a spec frustrating and breaks the stability requirement.
- **NumPy generators.** Much faster in bulk, but a heavy dependency for a first version, and its natural unit is a whole column, which conflicts with row streaming (decision 4). The generator interface leaves room to add it later.

Reproducibility is guaranteed for the same dataspecter version. Python documents the Mersenne Twister sequence as stable across versions, but the guarantee is not extended across dataspecter releases, because adding a distribution may change how draws are consumed.

### 4. The engine streams rows; only referenced columns are kept

Generating an entity yields one row (a `dict` in field order) at a time. Exporters consume the iterator and write as they go, so a ten-million-row entity never sits in memory. The planned HTTP stream becomes another consumer of the same iterator.

References need the parent's values. Before generating, the engine works out which `(entity, field)` pairs are referenced, and while a parent entity is being produced it appends those fields' values to an in-memory list. A reference field then picks a uniformly random index into that list, using its own stream.

Entities are generated in topological order of their references, independent of declaration order. Because the files are written during generation, the engine drives the exporters entity by entity in that order. For API callers who want the records of one entity, the engine generates that entity's ancestors first, retaining only the referenced columns.

*Alternative considered:* generate everything into memory as columns, then export. Simpler reference handling, but memory grows with data size and it gives streaming output nothing to build on.

### 5. Bounded normal values by resampling

A normal field with `min` or `max` redraws until the value lands inside the bounds, up to 100 attempts, then clamps to the nearest bound. Resampling keeps the shape of the distribution near the edges; clamping alone would pile values up on the bounds. The attempt limit guarantees termination when the bounds sit far in a tail.

Integer fields round the drawn value to the nearest whole number before the bounds check.

### 6. Exporters share one interface and write incrementally

A writer is a function that takes an open file, the field names and an iterator of rows, writes each row as it arrives, and returns the row count. A registry maps `csv`, `json` and `jsonl` to their writer; the format name is also the file extension. One `export` function opens the file, calls the writer and turns any `OSError` into an `ExportError` naming the path.

- CSV uses the `csv` module with `lineterminator="\n"` and minimal quoting, which follows RFC 4180 quoting rules.
- JSON writes `[`, then comma-separated objects, then `]`, so the array is produced without holding the rows.
- Value conversion is one small function per target: CSV maps null to an empty field, booleans to `true`/`false` and dates to ISO 8601; JSON and JSON Lines share a function that only has to convert dates, since `json` handles the rest.

Files are opened with `encoding="utf-8"` and `newline=""`, so output is byte-identical on Windows, macOS and Linux. That matters both for reproducibility and for the requirement that the API and the CLI produce identical files.

Existing files are overwritten without prompting. Generation is reproducible and the tool will be used in scripts, where a prompt or a refusal is an obstacle.

### 7. The CLI is a thin `argparse` layer

`argparse` covers two subcommands and three options without adding a dependency. `cli.py` parses arguments, calls the public API, prints the summary, and maps `SpecError` and unreadable spec files to exit code 2, anything else to exit code 1. `argparse` already exits with 2 on bad arguments, which matches the spec.

*Alternative considered:* Typer or Click. Nicer help output, but not worth a dependency at this size.

### 8. Public API surface

Exported from `dataspecter`:

- `load_spec(source)` accepts a path or a mapping and returns a validated `Spec`; raises `SpecError`.
- `generate(spec, seed=None)` returns a `Simulation` exposing `seed`, the entity names in generation order, and `records(entity)` as an iterator of dicts.
- `write(spec, out_dir=None, format=None, seed=None)` generates and writes every entity, returning a result with the seed and, per entity, the row count and file path. The CLI's `generate` command is this function plus printing.
- `SpecError`, `ExportError`.

Arguments passed to `write` override the spec's `output` block; the `output` block overrides the defaults (`csv`, `./output`). Relative output directories resolve against the current working directory, in the API and the CLI alike.

## Risks / Trade-offs

- **Pure-Python generation is slow for very large runs** → Acceptable for this change. A throughput measurement is recorded in the tasks so the starting point is known, and decision 3 leaves room for vectorised generators.
- **Referenced columns are held in memory** → Only the referenced fields are kept, not whole rows; ten million integer keys is tens of megabytes. Documented as a known limit.
- **Statistical scenarios can fail by chance** → Tests use a fixed seed, so they are deterministic; the tolerances in the specs are roughly ten standard errors wide, so they hold for any reasonable seed.
- **Uniform reference selection is not realistic for many datasets** (most customers have few orders, a few have many) → Out of scope here and listed in the proposal as a follow-up; the reference field model can gain a distribution option without a breaking change.
- **Hand-written validation is more code to get right than a validation library** → Roughly 300 lines, covered scenario by scenario from the `simulation-spec` delta; the table of allowed keys per field type keeps the common mistakes (typos, misplaced keys) in one code path.
- **YAML parses unquoted dates into date objects, JSON keeps strings**, and YAML raises a bare error with no location on an impossible date such as `2024-13-01` → Specs are loaded with a `SafeLoader` subclass that has the timestamp resolver removed, so dates arrive as strings from both formats and the validator parses and reports them. Date objects are still accepted when a caller passes a mapping. A test confirms YAML and JSON specs load identically.
- **YAML 1.1 reads unquoted `yes`, `no`, `on` and `off` as booleans**, which can surprise in `choice` values (a country code `NO` becomes `false`) → Documented in the spec reference with the advice to quote such strings.
- **The name `dataspecter` has not been checked on PyPI** → Publishing is out of scope; check before the first release.
