# Spec Delta

## ADDED Requirements

### Requirement: Hidden fields are not exported
A hidden field SHALL NOT appear in any output file: it has no CSV column and no key in JSON or JSON Lines objects. A hidden object SHALL contribute no columns and no key. The column paths of an entity SHALL NOT include hidden fields.

#### Scenario: No column in CSV
- **WHEN** an entity declares `id`, a hidden `first_name` and `email`, and is exported as CSV
- **THEN** the header row is `id,email`

#### Scenario: No key in JSON
- **WHEN** the same entity is exported as JSON
- **THEN** each object has the keys `id` and `email` only

#### Scenario: Hidden object
- **WHEN** an object `internal` with three fields declares `hidden: true`
- **THEN** none of its fields appears in any output format
