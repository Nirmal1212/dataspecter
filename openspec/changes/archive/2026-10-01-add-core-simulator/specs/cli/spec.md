# Spec Delta

## Purpose

Defines the `dataspecter` command-line interface: the commands a user runs to validate a simulation spec and generate data files from it, what the commands print, and the exit codes scripts can rely on.

## ADDED Requirements

### Requirement: Generate command
`dataspecter generate <spec>` SHALL validate the spec, generate every entity and write the output files. On success it SHALL print a summary to standard output containing the seed used and, for each entity, its row count and the path of the file written, and SHALL exit with code 0.

#### Scenario: Successful generation
- **WHEN** the user runs `dataspecter generate shop.yaml` with a valid spec
- **THEN** the output files are written, a summary listing each entity's row count and file path and the seed is printed, and the exit code is 0

#### Scenario: Seed is reported for unseeded runs
- **WHEN** the spec has no seed and none is given on the command line
- **THEN** the summary shows the seed that was chosen for the run

### Requirement: Generate options
`generate` SHALL accept `--out <dir>`, `--format <csv|json|jsonl>` and `--seed <integer>`. Each option, when given, SHALL take precedence over the corresponding setting in the spec.

#### Scenario: Output directory override
- **WHEN** the spec declares `output.dir: data` and the user passes `--out tmp/run1`
- **THEN** the files are written to `tmp/run1`

#### Scenario: Format override
- **WHEN** the spec declares `output.format: csv` and the user passes `--format jsonl`
- **THEN** the files are written as JSON Lines

#### Scenario: Seed override
- **WHEN** the spec declares `seed: 42` and the user passes `--seed 7`
- **THEN** the data is generated with seed 7 and the summary reports seed 7

#### Scenario: Invalid option value
- **WHEN** the user passes `--format xml`
- **THEN** the command prints an error listing the supported formats to standard error, writes nothing, and exits with code 2

### Requirement: Validate command
`dataspecter validate <spec>` SHALL check the spec without generating data or writing files. It SHALL exit with code 0 and print a confirmation when the spec is valid.

#### Scenario: Valid spec
- **WHEN** the user runs `dataspecter validate shop.yaml` with a valid spec
- **THEN** a confirmation is printed, no files are written, and the exit code is 0

#### Scenario: Invalid spec
- **WHEN** the user runs `dataspecter validate shop.yaml` with a spec that has two problems
- **THEN** both problems are printed to standard error with their locations, and the exit code is 2

### Requirement: Error reporting and exit codes
The command SHALL exit with code 0 on success, code 2 when the spec or the command-line arguments are invalid or the spec file cannot be read, and code 1 for any other failure. Error messages SHALL be written to standard error. A run that fails validation SHALL NOT write any output files.

#### Scenario: Invalid spec on generate
- **WHEN** the user runs `dataspecter generate` with a spec that fails validation
- **THEN** every validation problem is printed to standard error, no output files are created, and the exit code is 2

#### Scenario: Missing spec file
- **WHEN** the user runs `dataspecter generate missing.yaml` and the file does not exist
- **THEN** an error naming the path is printed to standard error and the exit code is 2

#### Scenario: Output cannot be written
- **WHEN** generation succeeds but an output file cannot be written
- **THEN** an error naming the path is printed to standard error and the exit code is 1

### Requirement: Help and version
`dataspecter --help` and `dataspecter <command> --help` SHALL print usage for the tool and for the command. `dataspecter --version` SHALL print the installed version. Each SHALL exit with code 0.

#### Scenario: Version
- **WHEN** the user runs `dataspecter --version`
- **THEN** the installed version number is printed and the exit code is 0

#### Scenario: Command help
- **WHEN** the user runs `dataspecter generate --help`
- **THEN** usage for `generate`, including the `--out`, `--format` and `--seed` options, is printed and the exit code is 0
