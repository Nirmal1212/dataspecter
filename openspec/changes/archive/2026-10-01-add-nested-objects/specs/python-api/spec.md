# Spec Delta

## ADDED Requirements

### Requirement: Column paths
The package SHALL let a caller obtain, for any entity of a generated spec, the ordered paths of its leaf fields, which are the columns CSV export writes.

#### Scenario: Paths of a nested entity
- **WHEN** an entity declares `id`, then `address` with `city` and `postcode`, then `tier`
- **THEN** its column paths are `id`, `address.city`, `address.postcode` and `tier`, in that order

#### Scenario: Paths of a flat entity
- **WHEN** an entity has no object fields
- **THEN** its column paths are its field names in declared order

## MODIFIED Requirements

### Requirement: Generating records
The package SHALL let a caller generate the data for a validated spec, optionally supplying a seed, and iterate over the records of each entity. Each record SHALL be a mapping of field name to value using native Python types: `int`, `float`, `bool`, `str`, `datetime.date`, `datetime.datetime`, `None` for nulls, and a nested mapping of the same kind for an object field. Every record SHALL be independent: changing a record, or an object inside it, SHALL NOT affect any other record. The seed used for the run SHALL be available to the caller.

#### Scenario: Iterating an entity's records
- **WHEN** a caller generates a spec whose `customer` entity has `count: 100`
- **THEN** iterating the `customer` records yields 100 mappings, each with the entity's fields

#### Scenario: Native types
- **WHEN** a record has an `integer` field, a `date` field and a null field
- **THEN** their values are an `int`, a `datetime.date` and `None`

#### Scenario: Seed is exposed
- **WHEN** a caller generates a spec without supplying a seed
- **THEN** the caller can read the seed that was used and pass it to a later run to reproduce the data

#### Scenario: Nested record
- **WHEN** a record has an object field `address` with a field `city`
- **THEN** `record["address"]["city"]` is the city, and `record["address"]` is `None` when the object is null

#### Scenario: Copied objects are independent
- **WHEN** two orders copy the same customer's `address`, and a caller changes the `city` inside the first order's copy
- **THEN** the second order's copy and every later record are unaffected
