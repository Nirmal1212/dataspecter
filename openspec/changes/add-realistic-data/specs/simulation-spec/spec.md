# Spec Delta

## MODIFIED Requirements

### Requirement: Spec structure
A spec SHALL contain `version` and `entities`, and MAY contain `seed`, `output`, `types` and `locale`. `version` SHALL be `1`. `entities` SHALL be a mapping of at least one entity name to an entity definition. Each entity definition SHALL contain `count`, an integer of 1 or more, and `fields`, a mapping of at least one field name to a field definition. `seed`, when present, SHALL be a non-negative integer. `output`, when present, MAY contain `format`, `dir` and `csv_separator`; `csv_separator` SHALL be `.` or `__`. `types`, when present, SHALL be a mapping of type name to field definition. `locale`, when present, SHALL be a locale code of the form `ll_CC`, such as `en_IN`. Entity and field names SHALL start with a letter or underscore and contain only letters, digits and underscores. Any key the format does not define SHALL be rejected.

#### Scenario: Minimal valid spec
- **WHEN** a spec has `version: 1` and one entity with `count: 10` and one field
- **THEN** the spec is accepted

#### Scenario: Unsupported version
- **WHEN** a spec declares `version: 2`
- **THEN** the system rejects it with an error stating that only version 1 is supported

#### Scenario: No entities
- **WHEN** a spec has an empty `entities` mapping
- **THEN** the system rejects it with an error stating that at least one entity is required

#### Scenario: Unknown key
- **WHEN** an entity definition contains the key `cout` instead of `count`
- **THEN** the system rejects it with an error naming the unknown key `cout`

#### Scenario: Invalid entity name
- **WHEN** an entity is named `my-orders`
- **THEN** the system rejects it with an error describing the allowed characters for names

#### Scenario: Unsupported column separator
- **WHEN** a spec declares `output.csv_separator: "/"`
- **THEN** the system rejects it with an error listing the supported separators

#### Scenario: Types that is not a mapping
- **WHEN** a spec declares `types` as a list
- **THEN** the system rejects it with an error stating that `types` must be a mapping of type name to definition

#### Scenario: Malformed locale
- **WHEN** a spec declares `locale: india`
- **THEN** the system rejects it with an error showing the expected form, such as `en_IN`

### Requirement: Field types
Every field definition SHALL be either a mapping that declares a `type`, or a reference shorthand string. `type` SHALL be one of the built-in types `integer`, `float`, `boolean`, `choice`, `date`, `datetime`, `sequence`, `uuid`, `constant`, `reference`, `object`, `pattern`, `template`, `first_name`, `last_name`, `full_name`, `email`, `phone`, `address` or `faker`, or the name of a custom type declared in the spec. Each type SHALL accept only the keys defined for it, together with the keys every field accepts: `null_probability`, `hidden`, and `unique` where the type supports it.

#### Scenario: Unknown field type
- **WHEN** a field declares `type: surname` and the spec declares no custom type of that name
- **THEN** the system rejects it with an error that lists the built-in types and the declared custom types

#### Scenario: Key that does not belong to the type
- **WHEN** a `boolean` field also declares `min: 1`
- **THEN** the system rejects it with an error naming the key `min`

#### Scenario: Definition that is neither a mapping nor a reference
- **WHEN** a field is defined as the number `42` or as a list
- **THEN** the system rejects it with an error stating that a field must be a mapping with a `type` or a `$entity.field` reference

#### Scenario: Custom type that predates a built-in of the same name
- **WHEN** a spec declares its own custom type named `email` and a field declares `type: email`
- **THEN** the field uses the spec's definition, not the built-in `email`
