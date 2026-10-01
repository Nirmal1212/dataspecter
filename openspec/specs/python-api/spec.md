# python-api Specification

## Purpose

Defines the importable Python interface of dataspecter, so that tests, notebooks and other programs can load a simulation spec, generate records and write files without going through the command line.

## Requirements

### Requirement: Loading a spec
The `dataspecter` package SHALL let a caller obtain a validated spec either from a file path or from an in-memory mapping with the same structure as a spec file. Both routes SHALL apply the same validation.

#### Scenario: Load from a path
- **WHEN** a caller loads a spec from the path of a valid YAML or JSON file
- **THEN** a validated spec object is returned

#### Scenario: Load from a mapping
- **WHEN** a caller builds the spec as a Python dictionary and loads it
- **THEN** a validated spec object is returned, equivalent to loading the same content from a file

### Requirement: Generating records
The package SHALL let a caller generate the data for a validated spec, optionally supplying a seed, and iterate over the records of each entity. Each record SHALL be a mapping of field name to value using native Python types: `int`, `float`, `bool`, `str`, `datetime.date`, `datetime.datetime`, and `None` for nulls. The seed used for the run SHALL be available to the caller.

#### Scenario: Iterating an entity's records
- **WHEN** a caller generates a spec whose `customer` entity has `count: 100`
- **THEN** iterating the `customer` records yields 100 mappings, each with the entity's fields

#### Scenario: Native types
- **WHEN** a record has an `integer` field, a `date` field and a null field
- **THEN** their values are an `int`, a `datetime.date` and `None`

#### Scenario: Seed is exposed
- **WHEN** a caller generates a spec without supplying a seed
- **THEN** the caller can read the seed that was used and pass it to a later run to reproduce the data

### Requirement: Writing files
The package SHALL let a caller write the generated data for a spec to an output directory in any supported format, producing the same files as the command line does for the same spec, seed and format.

#### Scenario: Same output as the command line
- **WHEN** a caller writes a spec as CSV with seed 42, and the command line generates the same spec as CSV with seed 42
- **THEN** the files produced are byte-for-byte identical

### Requirement: Errors raised to callers
An invalid spec SHALL cause a single documented exception type to be raised, carrying every validation problem with its location. Importing the package and calling it SHALL NOT print to standard output or standard error, nor terminate the process.

#### Scenario: Invalid spec raises with all problems
- **WHEN** a caller loads a mapping that has two validation problems
- **THEN** the documented exception is raised, and it exposes both problems with their location paths

#### Scenario: No output on import or use
- **WHEN** a caller imports the package, loads a spec and generates records
- **THEN** nothing is written to standard output or standard error
