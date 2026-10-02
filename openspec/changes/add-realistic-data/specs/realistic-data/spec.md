# Spec Delta

## Purpose

Defines the field types that produce realistic personal and contact data without the user supplying any lists: built-in names, email addresses, phone numbers and postal addresses for the bundled locales, and an optional bridge to the Faker library for everything else.

## ADDED Requirements

### Requirement: Locales
The built-in realistic types SHALL bundle data for the locales `en_US` and `en_IN`. The locale of a field SHALL be the field's own `locale` if it declares one, otherwise the locale given on the command line or by the caller, otherwise the spec's `locale`, otherwise `en_US`. A built-in realistic field whose locale is not bundled SHALL be rejected at that field.

#### Scenario: Default locale
- **WHEN** no locale is declared anywhere
- **THEN** built-in realistic fields produce United States data

#### Scenario: Locale for the whole spec
- **WHEN** the spec declares `locale: en_IN` and a field declares `type: phone`
- **THEN** the field produces Indian phone numbers

#### Scenario: Locale for one field
- **WHEN** the spec declares `locale: en_IN` and a field declares `type: phone`, `locale: en_US`
- **THEN** that field produces United States phone numbers while other fields stay Indian

#### Scenario: Built-in field with a locale that is not bundled
- **WHEN** the spec declares `locale: de_DE` and a field declares `type: full_name`
- **THEN** the system rejects it at that field with an error listing the bundled locales and pointing to the `faker` type

#### Scenario: Unbundled spec locale with only Faker fields
- **WHEN** the spec declares `locale: de_DE` and its only realistic fields are `faker` fields
- **THEN** the spec is accepted and those fields use `de_DE`

### Requirement: Name types
The types `first_name` and `last_name` SHALL produce a given name and a family name drawn from the names bundled for the field's locale. `full_name` SHALL produce a given name and a family name, as `Given Family` by default or as `Family, Given` when it declares `format: last_first`. Each locale SHALL bundle at least 100 given names and at least 100 family names. These types accept `locale`, `unique` and the keys every field accepts; `full_name` also accepts `format`.

#### Scenario: Names from the locale
- **WHEN** a field declares `type: first_name` with locale `en_IN` and 1,000 rows are generated
- **THEN** every value is one of the given names bundled for `en_IN`

#### Scenario: Name format
- **WHEN** a field declares `type: full_name`, `format: last_first`
- **THEN** every value is a family name, a comma and a space, and a given name

#### Scenario: Unique full names within capacity
- **WHEN** a field declares `type: full_name`, `unique: true` in an entity with `count: 5000`
- **THEN** the spec is accepted and all 5,000 names differ

#### Scenario: Unique names beyond capacity
- **WHEN** a field declares `type: first_name`, `unique: true` in an entity whose `count` exceeds the number of bundled given names
- **THEN** the system rejects it with an error stating both numbers

#### Scenario: Unknown key
- **WHEN** a field declares `type: full_name`, `gender: female`
- **THEN** the system rejects it with an error naming the key `gender`

### Requirement: Email type
The type `email` SHALL produce a syntactically valid email address in lower case, whose part before the `@` consists of ASCII letters, digits, dots and hyphens. By default the domain SHALL be one reserved for documentation (`example.com`, `example.org` or `example.net`), so that no generated address can belong to a real person. A field MAY declare `domain`, a valid host name used instead. The type accepts `locale`, `domain`, `unique` and the keys every field accepts.

#### Scenario: Shape
- **WHEN** a field declares `type: email` and 1,000 rows are generated
- **THEN** every value matches `local@domain`, is lower case, and has one of the three reserved domains

#### Scenario: Own domain
- **WHEN** a field declares `type: email`, `domain: acme.test`
- **THEN** every value ends with `@acme.test`

#### Scenario: Invalid domain
- **WHEN** a field declares `domain: "not a domain"`
- **THEN** the system rejects it with an error stating that `domain` must be a host name

#### Scenario: Unique emails
- **WHEN** a field declares `type: email`, `unique: true` and 100,000 rows are generated
- **THEN** all 100,000 addresses differ

#### Scenario: Independent of the record's name fields
- **WHEN** an entity declares both a `full_name` field and an `email` field
- **THEN** the email is generated independently and does not have to contain that record's name

### Requirement: Phone type
The type `phone` SHALL produce a phone number as text in the format of the field's locale.

For `en_US` the number SHALL be `+1-` followed by a three-digit area code beginning with a digit from 2 to 9, then `-555-01` and two further digits, which is the range reserved for fictional use.

For `en_IN` the number SHALL be `+91-` followed by ten digits beginning with 6, 7, 8 or 9. No range is reserved for fictional Indian numbers, so such a number may be assigned to a real subscriber.

A field MAY declare `pattern`, a pattern as defined for `pattern` fields, which SHALL replace the locale's format. The type accepts `locale`, `pattern`, `unique` and the keys every field accepts.

#### Scenario: United States number
- **WHEN** a field declares `type: phone` with locale `en_US`
- **THEN** every value matches `+1-NXX-555-01XX`, where `N` is a digit from 2 to 9 and each `X` any digit

#### Scenario: Indian number
- **WHEN** a field declares `type: phone` with locale `en_IN`
- **THEN** every value matches `+91-` followed by ten digits, the first being 6, 7, 8 or 9

#### Scenario: Own format
- **WHEN** a field declares `type: phone`, `pattern: "+91-99999-#####"`
- **THEN** every value is `+91-99999-` followed by five digits

#### Scenario: Unique beyond the fictional range
- **WHEN** a field declares `type: phone`, `unique: true` with locale `en_US` in an entity with `count: 100000`
- **THEN** the system rejects it with an error stating that the format can produce 80,000 distinct numbers

### Requirement: Address type
The type `address` SHALL produce an object with the fields `street`, `city`, `state`, `postcode` and `country`, in that order, all text. `city` SHALL be a city bundled for the locale and `state` the state that city is in. `postcode` SHALL begin with a prefix bundled for that city and SHALL follow the locale's format: six digits not beginning with 0 for `en_IN`, five digits for `en_US`. `country` SHALL be `India` or `United States`. Each locale SHALL bundle at least 50 cities.

A field MAY declare `fields`, a non-empty list of those five names, in which case the object SHALL hold only those fields, in the listed order. The fields of an address SHALL be usable wherever a nested field is: in templates, references and CSV columns. The type accepts `locale`, `fields` and the keys every field accepts except `unique`.

#### Scenario: Shape
- **WHEN** a field declares `type: address`
- **THEN** every value is an object with exactly the fields `street`, `city`, `state`, `postcode` and `country`, each a text value

#### Scenario: City and state agree
- **WHEN** 1,000 addresses are generated for `en_IN`
- **THEN** in every one, the `state` is the state bundled for that `city`

#### Scenario: Postcode belongs to the city
- **WHEN** 1,000 addresses are generated for each locale
- **THEN** every postcode has the locale's length and begins with a prefix bundled for its city

#### Scenario: Leading zero is kept
- **WHEN** an `en_US` address has a postcode beginning with 0 and is exported as JSON
- **THEN** the postcode is written as a five-character string

#### Scenario: Choosing fields
- **WHEN** a field declares `type: address`, `fields: [city, postcode]`
- **THEN** every value is an object with exactly `city` and `postcode`, in that order

#### Scenario: Unknown field name
- **WHEN** a field declares `fields: [city, zipcode]`
- **THEN** the system rejects it with an error naming `zipcode` and listing the five field names

#### Scenario: Used by path
- **WHEN** an entity has `home: {type: address}` and a template `"{home.city}, {home.state}"`
- **THEN** the template's value is that record's city and state

#### Scenario: Flattened in CSV
- **WHEN** an entity with `home: {type: address}` is exported as CSV
- **THEN** it has the columns `home.street`, `home.city`, `home.state`, `home.postcode` and `home.country`

### Requirement: Faker type
The type `faker` SHALL produce values by calling a provider of the Faker library. It SHALL declare `provider`, the name of a Faker provider method, and MAY declare `locale`, any locale Faker supports, and `args`, a mapping of keyword arguments passed to the provider. The provider's result SHALL be text, a number, a boolean, a date or a date-time. The type accepts `provider`, `locale`, `args`, `unique` and the keys every field accepts.

#### Scenario: Calling a provider
- **WHEN** a field declares `type: faker`, `provider: company` and Faker is installed
- **THEN** every value is a company name produced by Faker

#### Scenario: Locale and arguments
- **WHEN** a field declares `provider: date_between`, `args: {start_date: "-30d", end_date: "today"}` and another declares `provider: city`, `locale: de_DE`
- **THEN** the first produces dates in the last 30 days and the second produces German city names

#### Scenario: Unknown provider
- **WHEN** a field declares `provider: not_a_provider`
- **THEN** the system rejects it with an error stating that Faker has no such provider

#### Scenario: Unknown Faker locale
- **WHEN** a field declares `type: faker`, `provider: name`, `locale: xx_XX`
- **THEN** the system rejects it with an error stating that Faker does not support that locale

#### Scenario: Invalid arguments
- **WHEN** a field declares `provider: company`, `args: {no_such_argument: 1}`
- **THEN** the system rejects it with an error at that field carrying the provider's message

#### Scenario: Unique Faker values
- **WHEN** a field declares `type: faker`, `provider: company`, `unique: true` and generation cannot find an unused value
- **THEN** generation stops with an error naming the field, and writes no repeated value

### Requirement: Faker trust boundary
A spec SHALL be able to call Faker providers and nothing else. `provider` SHALL be accepted only if it is a public method contributed by one of Faker's providers; names beginning with an underscore and methods of the Faker object itself SHALL be rejected. Each value in `args` SHALL be text, a number, a boolean, null, or a list of those. A result that is not a single value of a supported kind SHALL be rejected: during validation, when the provider is tried once, and during generation, where the run SHALL stop with an error naming the field.

#### Scenario: Private or non-provider name
- **WHEN** a field declares `provider: _config` or `provider: seed_instance`
- **THEN** the system rejects it with an error stating that the name is not a provider

#### Scenario: Structured argument
- **WHEN** a field declares `args: {elements: {a: 1}}`
- **THEN** the system rejects it with an error stating which kinds of argument are allowed

#### Scenario: Provider returning a structure
- **WHEN** a field declares `provider: profile`, which returns a dictionary
- **THEN** the system rejects it with an error stating that the provider does not return a single value

#### Scenario: Provider returning bytes
- **WHEN** a field declares `provider: binary`
- **THEN** the system rejects it with the same error

#### Scenario: Result that changes kind during generation
- **WHEN** a provider passes the check at validation but later returns a value that is not of a supported kind
- **THEN** generation stops with an error naming the field and the kind of value returned

### Requirement: Faker is optional
The `faker` type SHALL be available only when the Faker library is installed. When it is not, a spec that uses the `faker` type SHALL be rejected with an error that states how to install it. Specs that do not use the type SHALL work without Faker, and loading the package SHALL NOT load Faker.

#### Scenario: Faker not installed
- **WHEN** a field declares `type: faker` and the Faker library is not installed
- **THEN** the system rejects the spec with an error containing `pip install faker`

#### Scenario: No Faker needed otherwise
- **WHEN** a spec uses the built-in types but not `faker`, and the Faker library is not installed
- **THEN** the spec is accepted and generates data

#### Scenario: Not loaded unless used
- **WHEN** a program imports the package and runs a spec with no `faker` field, with Faker installed
- **THEN** the Faker library has not been loaded

### Requirement: Reproducible realistic data
For a fixed seed, every realistic-data type SHALL produce the same values on every run, and the values of one such field SHALL NOT change when other fields are added, removed or reordered. For the `faker` type this holds for a given version of the Faker library.

#### Scenario: Same seed, same names
- **WHEN** a spec with `full_name`, `email`, `phone` and `address` fields is generated twice with the same seed
- **THEN** the two runs produce identical records

#### Scenario: Faker values repeat
- **WHEN** a spec with a `faker` field is generated twice with the same seed and the same Faker version
- **THEN** the two runs produce identical values

#### Scenario: Unaffected by other fields
- **WHEN** a `phone` field is added next to an existing `full_name` field and the spec is generated again with the same seed
- **THEN** the full names are unchanged
