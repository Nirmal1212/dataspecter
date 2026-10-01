# Spec Delta

## Purpose

Defines the simulation spec: the YAML or JSON document in which a user declares the entities, fields and value rules that dataspecter turns into synthetic data, and the validation applied to that document before any data is generated.

## ADDED Requirements

### Requirement: Spec file formats
The system SHALL load a simulation spec from a YAML file (`.yaml` or `.yml`) or a JSON file (`.json`), chosen by file extension. A YAML spec and a JSON spec with the same content SHALL be treated identically.

#### Scenario: YAML spec is loaded
- **WHEN** a valid spec is supplied as `customers.yaml`
- **THEN** the spec is loaded and accepted

#### Scenario: Equivalent JSON spec behaves the same
- **WHEN** the same spec content is supplied as `customers.json`
- **THEN** it is accepted and generates the same data as the YAML version for the same seed

#### Scenario: Unsupported file extension
- **WHEN** a spec is supplied as `customers.toml`
- **THEN** the system rejects it with an error naming the supported extensions

#### Scenario: Malformed file
- **WHEN** a spec file contains invalid YAML or JSON syntax
- **THEN** the system rejects it with an error that names the file and the position of the syntax error

#### Scenario: Missing file
- **WHEN** the supplied spec path does not exist
- **THEN** the system rejects it with an error naming the path

### Requirement: Spec structure
A spec SHALL contain `version` and `entities`, and MAY contain `seed` and `output`. `version` SHALL be `1`. `entities` SHALL be a mapping of at least one entity name to an entity definition. Each entity definition SHALL contain `count`, an integer of 1 or more, and `fields`, a mapping of at least one field name to a field definition. `seed`, when present, SHALL be a non-negative integer. `output`, when present, MAY contain `format` and `dir`. Entity and field names SHALL start with a letter or underscore and contain only letters, digits and underscores. Any key the format does not define SHALL be rejected.

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

### Requirement: Field types
Every field definition SHALL declare a `type`, which SHALL be one of `integer`, `float`, `boolean`, `choice`, `date`, `datetime`, `sequence`, `uuid`, `constant` or `reference`. Each type SHALL accept only the keys defined for it.

#### Scenario: Unknown field type
- **WHEN** a field declares `type: email`
- **THEN** the system rejects it with an error that lists the supported types

#### Scenario: Key that does not belong to the type
- **WHEN** a `boolean` field also declares `min: 1`
- **THEN** the system rejects it with an error naming the key `min`

### Requirement: Numeric field definitions
An `integer` or `float` field SHALL define its values in exactly one of two ways: a single range (`min` and `max`, with an optional `distribution`), or a list of weighted `ranges`.

For a single range, `distribution` SHALL be `uniform` (the default) or `normal`. A `uniform` field SHALL declare both `min` and `max`. A `normal` field SHALL declare `mean` and `stddev`, where `stddev` is greater than zero, and MAY declare `min` and `max`. Wherever both are present, `min` SHALL NOT exceed `max`.

For weighted ranges, each item SHALL declare `min`, `max` and `weight`. Weights SHALL be non-negative with a sum greater than zero; they need not sum to 1.

A `float` field MAY declare `precision`, a non-negative integer number of decimal places.

#### Scenario: Uniform range
- **WHEN** a field declares `type: integer`, `min: 18`, `max: 90`
- **THEN** the field is accepted with a uniform distribution

#### Scenario: Minimum above maximum
- **WHEN** a field declares `min: 90` and `max: 18`
- **THEN** the system rejects it with an error stating that `min` must not exceed `max`

#### Scenario: Normal distribution without parameters
- **WHEN** a field declares `distribution: normal` without `mean` or `stddev`
- **THEN** the system rejects it with an error naming the missing keys

#### Scenario: Weighted ranges
- **WHEN** a field declares `ranges` with three items weighted 0.7, 0.25 and 0.05
- **THEN** the field is accepted

#### Scenario: Both forms used together
- **WHEN** a field declares both `min`/`max` and `ranges`
- **THEN** the system rejects it with an error stating that the two forms are mutually exclusive

#### Scenario: Weights that cannot be used
- **WHEN** every item in `ranges` has `weight: 0`, or any weight is negative
- **THEN** the system rejects it with an error describing the weight rules

### Requirement: Other field definitions
A `boolean` field MAY declare `true_probability` between 0 and 1 inclusive (default 0.5). A `choice` field SHALL declare a non-empty `values` list and MAY declare `weights`, a list of the same length following the weight rules for ranges. A `date` or `datetime` field SHALL declare `min` and `max` as ISO 8601 values, with `min` not after `max`. A `sequence` field MAY declare integer `start` (default 1) and non-zero integer `step` (default 1). A `constant` field SHALL declare `value`. A `uuid` field takes no further keys.

#### Scenario: Weighted choice
- **WHEN** a `choice` field declares `values: [free, pro, enterprise]` and `weights: [70, 25, 5]`
- **THEN** the field is accepted

#### Scenario: Weights of the wrong length
- **WHEN** a `choice` field declares three values and two weights
- **THEN** the system rejects it with an error stating that `weights` must match `values` in length

#### Scenario: Invalid date
- **WHEN** a `date` field declares `min: 2024-13-01`
- **THEN** the system rejects it with an error stating that the value is not a valid ISO 8601 date

#### Scenario: Zero step
- **WHEN** a `sequence` field declares `step: 0`
- **THEN** the system rejects it with an error stating that `step` must not be zero

### Requirement: Reference field definitions
A `reference` field SHALL declare `entity` and `field`, naming a field of another entity in the same spec. References SHALL NOT form a cycle between entities, and an entity SHALL NOT reference itself.

#### Scenario: Valid reference
- **WHEN** `order.customer_id` declares `type: reference`, `entity: customer`, `field: id`, and `customer.id` exists
- **THEN** the field is accepted, regardless of the order in which the two entities are declared

#### Scenario: Unknown target entity
- **WHEN** a reference names an entity that is not in the spec
- **THEN** the system rejects it with an error naming the missing entity

#### Scenario: Unknown target field
- **WHEN** a reference names a field that the target entity does not define
- **THEN** the system rejects it with an error naming the missing field

#### Scenario: Circular references
- **WHEN** entity `a` references entity `b` and entity `b` references entity `a`
- **THEN** the system rejects the spec with an error naming the entities in the cycle

### Requirement: Null probability
Any field MAY declare `null_probability`, which SHALL be a number between 0 and 1 inclusive and SHALL default to 0 when omitted.

#### Scenario: Out-of-range probability
- **WHEN** a field declares `null_probability: 1.5`
- **THEN** the system rejects it with an error stating the allowed range

### Requirement: Validation reporting
Validation SHALL complete before any data is generated, SHALL report every problem found rather than only the first, and SHALL identify each problem by its location in the spec.

#### Scenario: Multiple problems reported together
- **WHEN** a spec has an invalid range in `entities.order.fields.amount` and an unknown reference in `entities.order.fields.customer_id`
- **THEN** both problems are reported in one validation result, each with its location path

#### Scenario: Invalid spec generates nothing
- **WHEN** a spec fails validation
- **THEN** no rows are generated and no output files are created
