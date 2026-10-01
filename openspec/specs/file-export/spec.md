# file-export Specification

## Purpose

Defines how generated entities are written to disk as CSV, JSON or JSON Lines files, so that the data can be loaded into other tools without further conversion.

## Requirements

### Requirement: Output files
The system SHALL write one file per entity into the output directory, named `<entity>.<extension>`, where the extension is `csv`, `json` or `jsonl` according to the format. The output directory SHALL be created if it does not exist. An existing file with the same name SHALL be overwritten. All files SHALL be encoded as UTF-8.

#### Scenario: One file per entity
- **WHEN** a spec with entities `customer` and `order` is exported as CSV to `out/`
- **THEN** `out/customer.csv` and `out/order.csv` exist and no other files are written

#### Scenario: Directory is created
- **WHEN** the output directory `out/run1` does not exist
- **THEN** it is created, including missing parent directories, and the files are written into it

#### Scenario: Existing file is replaced
- **WHEN** `out/customer.csv` already exists from an earlier run
- **THEN** it is replaced by the new output and contains no rows from the earlier run

### Requirement: Output format selection
The output format SHALL be one of `csv`, `json` or `jsonl`, and SHALL default to `csv` when none is specified. The output directory SHALL default to `output` in the current working directory.

#### Scenario: Default format
- **WHEN** no format is specified in the spec or by the caller
- **THEN** the entities are written as CSV files

#### Scenario: Unsupported format
- **WHEN** the format `xml` is requested
- **THEN** the system rejects it with an error listing the supported formats, and writes nothing

### Requirement: CSV export
A CSV file SHALL begin with a header row of the entity's field names in declared order, followed by one line per generated row. Fields SHALL be quoted as needed following RFC 4180, so that values containing commas, quotes or line breaks survive a round trip. A null SHALL be written as an empty field. Booleans SHALL be written as `true` or `false`. Dates and date-times SHALL be written in ISO 8601 format.

#### Scenario: Header and rows
- **WHEN** an entity with fields `id`, `tier` and 100 rows is exported as CSV
- **THEN** the file has 101 lines, the first being `id,tier`

#### Scenario: Value containing a comma
- **WHEN** a `choice` value is `Smith, John`
- **THEN** it is written as `"Smith, John"` and reads back as a single field

#### Scenario: Null value
- **WHEN** a row has a null in its second of three fields
- **THEN** the line has an empty second field, such as `1,,true`

#### Scenario: Date value
- **WHEN** a `date` field has the value 5 March 2024
- **THEN** it is written as `2024-03-05`

### Requirement: JSON export
A JSON file SHALL contain a single array holding one object per generated row, each object's keys being the field names in declared order. Numbers and booleans SHALL be written as JSON numbers and booleans, nulls as `null`, and dates and date-times as ISO 8601 strings. The file SHALL be valid JSON.

#### Scenario: Array of objects
- **WHEN** an entity with 100 rows is exported as JSON
- **THEN** the file parses as an array of 100 objects

#### Scenario: Native value types
- **WHEN** a row has an integer `age` of 31, a boolean `active` of true and a null `email`
- **THEN** its object contains `"age": 31`, `"active": true` and `"email": null`

### Requirement: JSON Lines export
A JSON Lines file SHALL contain one JSON object per line, one line per generated row, using the same value representation as JSON export.

#### Scenario: One object per line
- **WHEN** an entity with 100 rows is exported as JSON Lines
- **THEN** the file has 100 lines, each of which parses as a JSON object on its own

### Requirement: Export failures
When a file cannot be written, the system SHALL report an error naming the path and the cause.

#### Scenario: Output path is not writable
- **WHEN** the output directory cannot be created or written to
- **THEN** the export fails with an error naming that path and the reason
