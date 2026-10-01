# Tasks

## 1. Safety net

- [x] 1.1 Add `tests/golden/` with a spec covering every current field type, shorthand and reference rule, record its CSV, JSON and JSON Lines output for a fixed seed from the unmodified code, and add a test comparing regenerated output byte for byte; verify the test passes and fails when one generator is deliberately perturbed
- [x] 1.2 Add `.github/workflows/ci.yml` running `ruff check`, `ruff format --check` and `pytest` on Python 3.11 to 3.13 on Linux and Windows, and verify the workflow file parses and its commands pass locally
- [x] 1.3 Run the million-row flat benchmark on the unmodified code and record throughput and peak memory in `design.md` as the baseline for task 7.1

## 2. Object model and validation

- [x] 2.1 Add `ObjectField` to `spec.py` with recursive field parsing and path-based problem locations, and verify with tests for an object with sub-fields, an object inside an object, an object without fields, the same field name at two levels, and a problem located at `entities.customer.fields.address.fields.postcode`
- [x] 2.2 Enforce the ten-level nesting limit with a depth counter, and verify with tests for ten levels accepted, eleven rejected with the path and the limit, and a YAML document whose `fields` mapping contains itself rejected with the same error and no other exception
- [x] 2.3 Add field shapes resolved in entity dependency order, with a helper returning an entity's leaf paths, and verify with tests for a flat entity, a nested entity, a two-level nesting and a reference to an object taking the target's shape
- [x] 2.4 Document the `object` type and the nesting limit in `docs/spec-reference.md` and verify with the docs test that the snippet loads

## 3. Generation

- [x] 3.1 Key random streams and generators by path and generate objects as nested dicts, skipping the children of a null object, with a fast path for flat entities; verify with tests for nested records in declared order, a null object, nulls inside an object, and the golden test still passing
- [x] 3.2 Verify stability with tests that adding, removing and reordering fields inside an object leaves the other nested values unchanged for the same seed, and that a flat spec is unaffected by an unrelated nested entity

## 4. Export and Python API

- [x] 4.1 Pass leaf paths to the CSV writer and read each leaf by walking the record, writing empty cells for a null object; verify with tests for the header `id,address.city,address.postcode,tier`, two-level paths, a null object written as `1,,,free`, and the golden test still passing
- [x] 4.2 Add `output.csv_separator` (`.` or `__`) with collision detection at validation, and verify with tests for the default, `address__city`, an unsupported separator, a collision naming both fields, and JSON output unaffected by the separator
- [x] 4.3 Verify JSON and JSON Lines with tests that an object is written nested and a null object as `null`
- [x] 4.4 Expose an entity's column paths on the simulation and verify with tests for a nested and a flat entity, and that the Python API yields nested dicts with `None` for a null object
- [x] 4.5 Update the Output section of `docs/spec-reference.md` with nested output in each format, the separator option and the null-object limitation of CSV, and verify the documented header against a generated file in a test

## 5. References to nested fields

- [x] 5.1 Accept dotted paths in the reference shorthand and in the long form's `field`, validated against the target's shape; verify with tests for `$customer.address.city`, the long form, an unknown nested field, a path through a non-object, a path through a copied object in each declaration order, and `$customer.`, `$customer..id` rejected
- [x] 5.2 Collect references declared inside objects for entity ordering, cycle detection and row picks, and verify with tests that a nested reference orders the entities correctly, takes part in cycle detection, and shares a row with the entity's other references to the same target
- [x] 5.3 Retain columns by path and read nested values from the chosen row, copying objects per record; verify with tests that `ship_city` is the city of the customer in `customer_id`, that a whole object is copied and equals the target's, that a null target address gives null, that reading through a copied object works, and that mutating one record's copied object leaves other records unchanged
- [x] 5.4 Verify export of copied objects with a test for the CSV columns `ship_to.city` and `ship_to.postcode`
- [x] 5.5 Document nested references in the References section of `docs/spec-reference.md` and verify with the docs test that the snippet loads and behaves as described

## 6. Examples

- [x] 6.1 Add an `address` object to the customer in `examples/shop.yaml` and `examples/shop.json` and a shipping city on the order read from `$customer.address.city`; verify with tests that both files load to the same spec, generate identical data, and that the shipping city matches the customer's
- [x] 6.2 Update `README.md` (field type table, a nested example) and verify that each documented command runs as written against `examples/shop.yaml` in all three formats

## 7. Wrap-up

- [x] 7.1 Re-run the flat benchmark and a nested one on the same machine, record both in `design.md`, and verify flat throughput is within 15% of the baseline from task 1.3 and that memory stays flat as the row count grows
- [x] 7.2 Verify `uv run pytest`, `uv run ruff check .` and `openspec validate add-nested-objects --strict` all pass
- [x] 7.3 Add entries under `[Unreleased]` in `CHANGELOG.md` for nested objects, nested references, CSV flattening with the separator option, and column paths in the Python API, and verify each item in the proposal is named
- [ ] 7.4 Archive the change with `/opsx:archive` and verify `openspec/specs/` contains the new and modified requirements
