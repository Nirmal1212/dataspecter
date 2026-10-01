# Spec Delta

## ADDED Requirements

### Requirement: Nested objects in export
In JSON and JSON Lines output, an object field SHALL be written as a nested object, and a null object as `null`.

In CSV output, an object field SHALL be flattened into one column for each field inside it that is not itself an object, at any depth. The column SHALL be named by the path from the object down, joined by the column separator, and columns SHALL appear in declared order, in the position of the object. When an object is null, every one of its columns SHALL be empty for that row. CSV therefore does not distinguish a null object from an object whose fields are all null; JSON and JSON Lines do.

#### Scenario: Nested in JSON
- **WHEN** a customer has `address` with `city: Pune` and `postcode: "411001"` and is exported as JSON
- **THEN** its object contains `"address": {"city": "Pune", "postcode": "411001"}`

#### Scenario: Null object in JSON
- **WHEN** a customer's `address` is null
- **THEN** its object contains `"address": null`

#### Scenario: Flattened in CSV
- **WHEN** an entity declares `id`, then `address` with `city` and `postcode`, then `tier`, and is exported as CSV
- **THEN** the header row is `id,address.city,address.postcode,tier`

#### Scenario: Deeper nesting in CSV
- **WHEN** `address` contains an object `geo` with `lat` and `lon`
- **THEN** the columns for it are `address.geo.lat` and `address.geo.lon`

#### Scenario: Null object in CSV
- **WHEN** a row's `address` is null, in an entity with the header `id,address.city,address.postcode,tier`
- **THEN** the line is written as `1,,,free`

#### Scenario: Copied object in CSV
- **WHEN** `order.ship_to` is a reference to the object `customer.address`
- **THEN** the order's CSV has the columns `ship_to.city` and `ship_to.postcode`

#### Scenario: Flat entities are unchanged
- **WHEN** an entity has no object fields
- **THEN** its CSV, JSON and JSON Lines output is byte-for-byte what it was before this capability existed

### Requirement: CSV column separator
The separator joining the parts of a flattened column name SHALL be `.` by default and MAY be set to `__` with `output.csv_separator`. A spec SHALL be rejected when, under the chosen separator, two columns of one entity would have the same name. The separator SHALL NOT affect JSON or JSON Lines output.

#### Scenario: Default separator
- **WHEN** no separator is configured
- **THEN** the nested column is named `address.city`

#### Scenario: Double underscore
- **WHEN** the spec declares `output.csv_separator: "__"`
- **THEN** the nested column is named `address__city`

#### Scenario: Colliding column names
- **WHEN** the separator is `__` and an entity has both a field `address__city` and an object `address` with a field `city`
- **THEN** the system rejects the spec with an error naming both fields and the column name they share
