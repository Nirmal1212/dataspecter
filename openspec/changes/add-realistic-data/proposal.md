# Proposal

## Why

With objects, patterns, templates and custom types in place, a user can build a realistic person or address, but has to supply every list of names and cities themselves. Most users want `type: full_name` to just work, in the region they care about, and want a way out to a larger library when the built-ins do not cover their case.

This is the third of three changes replacing the single `add-rich-field-types` draft. It depends on `add-nested-objects` and `add-text-and-custom-types`.

## What Changes

- **Built-in realistic types.** `first_name`, `last_name`, `full_name`, `email`, `phone` and `address`, backed by bundled data for India (`en_IN`) and the United States (`en_US`).
- **Options on the built-ins.** `full_name` takes a `format`; `email` takes a `domain`; `phone` takes a `pattern`; `address` takes a list of the `fields` to include. All support `unique`.
- **Safe by default.** Emails use domains reserved for documentation, so they cannot reach a mailbox. United States phone numbers use the range reserved for fiction. Indian phone numbers have no such reserved range, so they are random valid-format numbers, and this is stated wherever the type is documented.
- **Addresses that hold together.** The state is the one the city is in, and the postcode begins with a prefix that belongs to that city. Postcodes are text, so a leading zero survives.
- **Locale handling.** `locale` on the spec, `--locale` on the command line, and `locale` on a field, in increasing order of precedence. The spec-level value may be any locale code; a built-in field whose resolved locale is not bundled is rejected at that field.
- **Optional Faker integration.** A `faker` type calls a provider of the Faker library, for other locales and for data the built-ins do not cover. It is available only when Faker is installed.
- **A stated trust boundary for Faker.** Only genuine provider methods can be called, arguments are plain values, and every result is checked to be a single value, during validation and during generation.
- **CI without Faker.** A second CI job runs the suite with Faker absent, so "works without it" is tested, not simulated.

Out of scope: more bundled locales; name frequencies that match a real population; correlation between separate built-in fields (an email matching a name is done with a template); lists inside a record.

## Capabilities

### New Capabilities

- `realistic-data`: the built-in name, email, phone and address types, their options and locales, and the optional Faker integration with its trust boundary.

### Modified Capabilities

- `simulation-spec`: new top-level `locale`; the realistic types and `faker` join the built-in field types.
- `cli`: `generate` accepts `--locale`.

## Impact

- **Prerequisite**: `add-nested-objects` and `add-text-and-custom-types` merged and archived. `address` is an object, the built-ins support `unique`, and the name precedence rule from the second change is what lets these type names be added without breaking specs that already use them for custom types.
- **Code**: new modules for the built-in generators, the bundled data and the Faker bridge; `spec.py` for the new types and locale; `cli.py` for `--locale`.
- **Dependencies**: no new required dependency. Faker becomes an optional extra and a development dependency. Its minimum version is established by test in the first Faker task, not assumed.
- **Package size**: bundled lists for two locales, a few hundred entries each, as Python modules.
- **Data provenance**: every bundled list is recorded with its source and licence in the package before it is merged.
- **Compatibility**: additive. Existing specs keep their golden output. A spec that declared a custom type named `email`, `phone` or similar keeps using its own definition.
