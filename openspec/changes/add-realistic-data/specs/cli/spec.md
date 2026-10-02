# Spec Delta

## MODIFIED Requirements

### Requirement: Generate options
`generate` SHALL accept `--out <dir>`, `--format <csv|json|jsonl>`, `--seed <integer>` and `--locale <code>`. Each option, when given, SHALL take precedence over the corresponding setting in the spec. `--locale` replaces the spec's `locale`; a field that declares its own `locale` keeps it.

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

#### Scenario: Locale override
- **WHEN** the spec declares `locale: en_US` and the user passes `--locale en_IN`
- **THEN** built-in realistic fields without their own `locale` produce Indian data

#### Scenario: Locale override that a built-in field cannot honour
- **WHEN** the user passes `--locale de_DE` and the spec has a `full_name` field without its own `locale`
- **THEN** the command prints the problem at that field to standard error, writes nothing, and exits with code 2

#### Scenario: Malformed locale option
- **WHEN** the user passes `--locale india`
- **THEN** the command prints an error showing the expected form to standard error and exits with code 2
