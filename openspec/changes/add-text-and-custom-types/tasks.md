# Tasks

## 1. Patterns

- [x] 1.1 Add `PatternField` with a compiler from the pattern string to literal and placeholder segments (`#`, `%`, `?`, bracketed literals, `[[]`), and verify with tests for a valid pattern, bracketed `#`, `%` and `?`, a literal `[`, a missing or empty pattern, an unclosed bracket, and that the same pattern loads identically from YAML and JSON files
- [x] 1.2 Generate pattern values from the segments and verify with fixed-seed tests for `+91-%#########`, `SKU-??-####`, `Item [#]##`, and more than 900 distinct values in 1,000 rows of `######`
- [ ] 1.3 Document the `pattern` type in `docs/spec-reference.md` and verify with the docs test that the snippets load

## 2. Templates

- [x] 2.1 Add `TemplateField` with a scanner for literals, `{path}`, `^` prefixes, `|filter` chains and doubled braces, without using `str.format`; verify with tests for a valid template, unbalanced braces, an unknown filter listing the supported ones, an empty placeholder, and `{a.__class__}` and `{a[0]}` rejected without evaluating anything
- [x] 2.2 Resolve each placeholder to an absolute path from its explicit starting point and require a scalar; verify with tests for sibling fields, a nested path, `^` and `^^`, a field one level out without `^` rejected with the suggestion, too many `^`, an unknown field, and a placeholder naming an object
- [x] 2.3 Compute each entity's generation order from template dependencies and reject cycles, keeping the flat fast path for entities without templates; verify with tests for a template declared before its inputs, a chain of two templates, a mutual dependency naming both fields, and the golden test still passing
- [x] 2.4 Implement the filters `lower`, `upper`, `title`, `ascii` and `slug` and verify with tests for `mcDonald`, `O'Brien`, `De La Cruz`, `José`, `Zoë Müller`, a chain of two filters, and a value that slugs to an empty string
- [x] 2.5 Generate template values with value formatting, null when any input is null; verify with tests for the email example, literal braces, numbers, booleans and dates as text, a null input, a nested field and a reference as inputs, and output still in declared order
- [ ] 2.6 Document the `template` type, its filters and the `^` scope rule in `docs/spec-reference.md`, and verify with the docs test that the snippets load and the email example matches its record

## 3. Hidden fields

- [x] 3.1 Add the common key `hidden` with validation that every entity and visible object keeps a visible field, and verify with tests for a hidden template input, a hidden reference target, everything hidden rejected, a hidden object, and a non-boolean value
- [x] 3.2 Leave hidden fields out of records and column paths while still generating them, and verify with tests that rows omit them, that CSV and JSON omit them, that a template and a reference still read them, and that toggling `hidden` changes no value for the same seed
- [ ] 3.3 Document `hidden` in `docs/spec-reference.md` with the email-from-hidden-names example and verify with the docs test that the snippet loads and its output has no name columns

## 4. Unique fields

- [x] 4.1 Add the common key `unique` with per-type support and capacity computation, and verify with tests for a unique pattern accepted, an integer range and a choice with too few values rejected stating both numbers, zero-weight choice values not counted, unsupported types rejected, `sequence` and `uuid` accepting it, and an unbounded float accepted
- [x] 4.2 Generate unique values with redraws and the scan fallback for finite fields, and verify with fixed-seed tests for 10,000 distinct pattern values, a field at 100% of capacity producing every value once, nulls repeating while values do not, identical values for the same seed, and an unbounded field that cannot find a new value stopping with an error naming it
- [x] 4.3 Verify with a test that a unique field used as a reference target lets each referencing row identify exactly one target row
- [ ] 4.4 Document `unique`, its supported types, the capacity check and the memory cost in `docs/spec-reference.md`, and verify with the docs test that the snippets load

## 5. Custom types

- [x] 5.1 Parse the top-level `types` block and validate each definition structurally, and verify with tests for a declared type, `types` that is not a mapping, an invalid type name, a definition that is not a mapping, and a problem in an unused type located at `types.<name>`
- [x] 5.2 Expand custom types at the point of use with use-site keys overriding and object `fields` merged by name, with cycle detection; verify with tests for a scalar type, an object type used in two entities, an overridden key, an overridden sub-field, a key the underlying type does not accept, a type built on another type, a two-type cycle naming both, and an unknown type name listing built-in and declared types
- [x] 5.3 Give custom types precedence over built-ins, with the name denoting the built-in inside its own definition, and verify with tests for a custom `integer` wrapping the built-in, its use in a field, and a custom type named after a type that only a later change adds still resolving to the custom definition
- [x] 5.4 Check closed object types fully at declaration and everything else at the point of use, naming the type; verify with tests for a `person` type with a bad placeholder located at `types.person.fields.email`, a `person` type used in two entities, and a scalar template type used where its field is missing
- [x] 5.5 Verify generation with tests that two fields using the same type follow it and differ in most records, and that a spec using a type generates the same values as one with the definition written in place
- [ ] 5.6 Document custom types, overrides and name precedence in `docs/spec-reference.md`, including a `person` example combining an object, a pattern and a template, and verify with the docs test that the snippets load

## 6. Examples

- [ ] 6.1 Extend `examples/shop.yaml` and `examples/shop.json` with a unique product code pattern, a custom `money` type, and a customer email built by template from hidden name parts; verify with tests that both files load to the same spec, generate identical data, that product codes are unique, and that no hidden field is exported
- [ ] 6.2 Update `README.md` (field type table, common keys, a pattern and template example) and verify that each documented command runs as written against `examples/shop.yaml` in all three formats

## 7. Wrap-up

- [ ] 7.1 Re-run the flat benchmark and one with a template, a pattern and a unique field at one million rows on the same machine as the baseline, record time and peak memory in `design.md`, and verify flat throughput is within 15% of the baseline
- [ ] 7.2 Verify `uv run pytest`, `uv run ruff check .` and `openspec validate add-text-and-custom-types --strict` all pass
- [ ] 7.3 Add entries under `[Unreleased]` in `CHANGELOG.md` for patterns, templates, hidden fields, unique fields and custom types, and verify each item in the proposal is named
- [ ] 7.4 Archive the change with `/opsx:archive` and verify `openspec/specs/` contains the new and modified requirements
