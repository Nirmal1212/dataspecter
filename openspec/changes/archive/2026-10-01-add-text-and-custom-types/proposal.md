# Proposal

## Why

dataspecter can produce numbers, choices and dates, but not the text that most records are made of: codes, phone-shaped strings, emails built from a name. A field definition used in five entities also has to be written five times. And nothing can be declared unique, so generated keys and codes repeat, which breaks any table with a unique index.

This is the second of three changes replacing the single `add-rich-field-types` draft. It depends on `add-nested-objects` and is followed by `add-realistic-data`.

## What Changes

- **Patterns.** A new `pattern` type builds text from a mask: `#` is a digit, `%` a non-zero digit, `?` an upper-case letter, and anything in square brackets is literal. `"+91-%#########"`, `"SKU-??-####"`, `"Item [#]##"`. No backslash escapes, so a pattern is written the same way in YAML and JSON.
- **Templates.** A new `template` type builds text from other fields of the same record: `"{first_name|slug}.{last_name|slug}@example.com"`. Filters: `lower`, `upper`, `title`, `ascii`, `slug`.
- **Explicit template scope.** A placeholder reads only the fields beside the template. A field further out is reached with one `^` per level (`{^home.city}`). There is no fallback search, so adding a field elsewhere can never change what an existing template reads.
- **Hidden fields.** Any field can declare `hidden: true`: it is generated and can be read by templates and references, but is left out of records and files. This lets a template use a value without that value becoming a column.
- **Unique fields.** `unique: true` guarantees no repeated value within an entity, for the types where that is meaningful. A spec that asks for more unique values than the field can produce is rejected before generation.
- **Reusable custom types.** A top-level `types` block names field definitions once, and any field uses one with `type: <name>`. Keys given at the point of use override the definition's, so one type can serve several variations.
- **Forward-compatible type names.** A custom type with the same name as a built-in takes precedence, so adding built-in types in later versions can never break an existing spec.

Nothing in a spec is ever evaluated as code: patterns and templates are parsed by fixed grammars.

Out of scope: built-in names, emails, phones, addresses and Faker (next change); sharing types across files; rules between fields beyond templates; lists inside a record.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `simulation-spec`: new top-level `types`; new field types `pattern` and `template`; custom type names usable as a `type`; new common keys `hidden` and `unique`.
- `data-generation`: how patterns, templates, unique fields and custom types produce values; hidden fields are left out of records; fields in a record are generated in dependency order.
- `file-export`: hidden fields are not exported.

## Impact

- **Prerequisite**: `add-nested-objects` merged and archived. The deltas here extend requirements as that change leaves them, and templates and hidden fields rely on field paths and shapes.
- **Code**: `spec.py` (pattern and template parsers, type expansion, hidden and unique validation, capacity checks), `generators.py` and `engine.py` (pattern and template generation, dependency order within a record, uniqueness), `exporters.py` and `api.py` (hidden fields excluded from column paths).
- **Memory**: a `unique` field keeps every value it has produced for the length of the run. This is the one place memory grows with row count, and only for fields that ask for it.
- **Compatibility**: additive. Existing specs keep their meaning and their golden output.
- **Dependencies**: none added.
