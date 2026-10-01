# Design

## Context

See `proposal.md` for motivation. The relevant current state:

- A record is a flat `dict` of field name to scalar. An entity's `fields` is a flat mapping of frozen dataclasses.
- Each field draws from a random stream keyed by seed, entity and field name. References read a retained column of the target entity at an index chosen once per row per link.
- `exporters.py` takes a list of field names and writes one value per name.
- The test suite checks properties (ranges, proportions, a run equal to itself). No test records what a given spec and seed actually produce, and there is no CI.

This change replaces "field name" with "field path" throughout the engine. That is a mechanical but wide refactor of the hot path, which is exactly where an unnoticed change of output would hide.

## Goals / Non-Goals

**Goals:**

- Prove, not assume, that existing specs keep their exact output.
- One place that knows a field's structure, computed once at validation.
- The validator ends in "accepted" or "problems" for any input at all.

**Non-Goals:**

- Lists inside records.
- Anything that makes one field of a record depend on another (templates, next change).
- Removing the CSV limitation that a null object and an object of nulls look the same.

## Decisions

### 1. A golden-output test and CI land before any engine change

`tests/golden/` holds a spec exercising every current field type, shorthand and reference rule, and the CSV, JSON and JSON Lines files it produces for a fixed seed. A test regenerates them and compares bytes. The files are recorded from the code as it stands *before* task group 2, in their own commit, so any later difference is a regression by construction.

`.gitattributes` already forces LF, and the exporters write LF on every platform, so the comparison is byte-exact on Windows and Linux alike.

CI is a single GitHub Actions workflow running `ruff check`, `ruff format --check` and `pytest` on Python 3.11 to 3.13, on Linux and Windows. It exists so that the golden test is enforced on every pull request, not only when someone remembers to run it.

*Alternative considered:* rely on the existing reproducibility tests. They compare a run to another run of the same code, so they pass even if every value changes.

### 2. Fields are addressed by path

`ObjectField` holds a mapping of name to field, so an entity's fields become a tree. Every field has a path from the entity down (`address.city`), and the path replaces the field name wherever a field is identified: random streams, retained columns, and problem locations (`entities.customer.fields.address.fields.city`).

A top-level field's path is its name, so its stream key, and therefore its values, are unchanged. This is the property the golden test guards.

### 3. A null object does not generate its children

When an object is null for a row, its fields are not generated. Generating and discarding them would keep the children's values independent of the object's `null_probability`, but an address that is null nine times in ten would pay full cost on every row.

The cost of this choice is that changing an object's `null_probability` shifts the values of the fields inside it, because their streams advance only on non-null rows. The stability requirement says so explicitly. Values still never depend on *other* fields.

### 4. A field's shape is computed at validation

Each field has a *shape*: scalar, or an ordered list of named sub-shapes. An object's shape comes from its fields; a reference takes the shape of its target. Shapes drive nested-path checks for references, the CSV header, and the column paths exposed to callers.

Because a reference's shape comes from another entity, shapes are resolved in entity dependency order, after cycle detection. That is what lets a path pass through a copied object (`$order.ship_to.city`) whatever order the entities are declared in.

### 5. One depth limit handles both deep nesting and self-containing documents

The object parser carries a depth counter and reports a problem at depth eleven instead of descending. PyYAML accepts a mapping that contains itself through an anchor; the same counter stops that case, so no separate cycle detection is needed and no input can exhaust the stack. A test feeds exactly such a document.

Ten levels is far beyond any realistic record and far below Python's recursion limit.

### 6. References read paths; row picks stay per entity

The reference grammar accepts a dotted path after the entity. Row picks are unchanged and still belong to the entity: a reference declared inside an object shares picks with the entity's other references under the existing link rules, and counts for entity ordering and cycle detection.

Reading a path walks the retained value; a null object anywhere along it yields null. Only referenced paths are retained, as today.

### 7. Copied objects are copied

A reference to an object returns a copy of the retained value for each record. Returning the retained dict itself would be faster, but a caller who edits one record would silently change the parent's retained value and every later record that copies it. Object values are small and contain only scalars and other such dicts, so the copy is a shallow rebuild per level, not a general deep copy.

### 8. CSV flattening and the separator

The API layer computes an entity's leaf paths once and passes them to the writer, which reads each leaf by walking the record; a null object yields empty cells. JSON and JSON Lines need no change.

With the default `.` separator a column name can never collide with a field name, since names cannot contain dots. `__` is offered because several SQL loaders reject or mangle dots in column names. Names may contain underscores, so with `__` a collision is possible and is checked at validation.

The separator is a spec setting only. A command-line flag can follow if it is asked for.

### 9. Performance is a pass or fail criterion

Before task group 2, the existing benchmark (one million rows of a five-field flat entity to CSV) is run and its throughput recorded. After the change it is run again on the same machine, and the change is not complete unless throughput is within 15% of the recorded figure. Path lookups and nested row assembly are on the hot path, so flat entities take a fast path that never touches the nested code.

## Risks / Trade-offs

- **The refactor changes generated values without anyone noticing** → The golden test, recorded before the refactor and enforced in CI.
- **CSV cannot tell a null object from an object of nulls** → Stated in the spec and the reference, which recommends JSON or JSON Lines where the difference matters.
- **Deeply nested entities produce many columns** → Inherent to flattening; the same recommendation applies.
- **Changing an object's `null_probability` shifts its children's values** → Stated in the stability requirement and the reference.
- **Copying objects costs time on reference-heavy specs** → Measured in the benchmark task with an entity that copies an object; the copy is shallow per level.
- **CI minutes and maintenance** → One small workflow on a public repository.

## Measurements

Run with `benchmarks/bench.py`, best of three, Python 3.12 on the development laptop (Windows).

| When | Scenario | Rows | Throughput | Peak traced memory |
|---|---|---|---|---|
| Baseline, before any engine change | flat | 1,000,000 | 121,191 rows/s | 0.22 MB (same at 200,000 rows) |
| After this change | flat | 1,000,000 | 120,011 rows/s (1% below baseline) | not re-measured; same code path |
| After this change | nested | 1,000,000 | 75,352 rows/s | 0.49 MB (same at 200,000 rows) |

The flat figure is within the 15% allowed. The nested scenario writes eleven columns per row from two objects, a copied object and a nested reference; its memory does not grow with the row count.

## Migration Plan

1. Merge `feature/add-spec-shorthands` into `develop`.
2. Recut this branch from `develop` and commit the proposal.
3. Record the golden files and the baseline throughput before touching the engine.

No user-facing migration: existing specs are unaffected.
