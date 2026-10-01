# Design

## Context

See `proposal.md` for motivation. This change builds on the two before it. The relevant state after them:

- Fields form a tree addressed by path; a field has a shape known at validation.
- `pattern` and `template` exist, with a pattern compiler that also reports how many values a pattern can produce.
- Any supported field can be `unique`, with a capacity check at validation.
- Custom types take precedence over built-ins of the same name.
- A golden-output test and CI guard existing behaviour.
- PyYAML is the only runtime dependency, and a new one has to be justified.

## Goals / Non-Goals

**Goals:**

- `type: full_name` works with no configuration and no extra install.
- Generated contact data cannot reach a real person where a reserved range exists, and the reference says plainly where one does not.
- An address is internally consistent to the level a reader would check by eye: city, state and the start of the postcode.
- Faker stays strictly optional and strictly bounded in what a spec can make it do.

**Non-Goals:**

- Locale coverage beyond `en_US` and `en_IN` in the built-ins.
- Name frequencies that match a population. Names are chosen uniformly.
- Street-level accuracy. A street is a house number and a bundled street name; it is not checked against the city.
- Correlation between separate built-in fields. A template covers an email that matches a name.

## Decisions

### 1. Built-in types are native generators over bundled data

Bundled data lives in Python modules, one per locale (`dataspecter/data/en_in.py`, `en_us.py`), as tuples: given names, family names, street names, and city records of `(city, state, postcode prefixes)`. Python modules need no file access at run time and no packaging configuration.

- `first_name`, `last_name`: a uniform choice from the locale's list.
- `full_name`: one of each, in the declared `format`.
- `email`: a slugged given and family name from the locale, joined by a dot, with a short number, at the domain. Slugging uses the `slug` filter from the previous change, so the result is always valid whatever the names contain.
- `phone`: the locale's format, or the field's own `pattern`, run through the pattern compiler.
- `address`: one generator returning an object. It draws a city record, so state and postcode prefix always belong to the city, completes the postcode with random digits, and builds a street.

`address` is a single generator because its fields are correlated. Its shape is fixed by the `fields` option and known at validation, which is all that templates, references and CSV need.

*Alternative considered:* ship the built-ins as a bundled `types` block written in the public field types. It would demonstrate the mechanism, but the public types cannot draw several correlated values from one record.

### 2. Postcodes are consistent to the prefix, and are text

Each city record carries the leading digits that postcodes in that city start with (three digits for both India's PIN codes and United States ZIP codes); the rest is random. That makes "Pune, Maharashtra, 411xxx" hold together without bundling every valid postcode. A full postcode may still not be one in use; the reference says so.

Postcodes, like phone numbers, are text. A United States ZIP code can begin with 0, which a number would lose.

### 3. Phone numbers: fictional where a reserved range exists

North American numbers of the form `NXX-555-01XX` are reserved for fictional use, so `en_US` uses them. That limits the format to 80,000 distinct numbers (800 area codes times 100), which the uniqueness capacity check reports.

For India no reserved range is known to this project, so `en_IN` produces random numbers in the valid mobile format, some of which will be assigned to real subscribers. The spec states this, the reference repeats it with the advice never to send messages to generated numbers, and the `pattern` option lets a team substitute a prefix they know to be safe.

### 4. Options instead of new types

The review of the earlier draft found the built-ins could not be adjusted at all. Each now has the one option people reach for first: `format` on `full_name`, `domain` on `email`, `pattern` on `phone`, `fields` on `address`. Anything further is a custom type built with templates and patterns, which is why those came first.

All built-ins except `address` support `unique`, using the capacity machinery from the previous change: list sizes for names, their product for full names, the pattern count for phones. Emails gain capacity from their numeric suffix, which widens when uniqueness needs it.

### 5. Locale resolution

Precedence, highest first: the field's `locale`, then `--locale` or the `locale` argument of the Python API, then the spec's `locale`, then `en_US`.

The spec-level value is only checked for form (`ll_CC`). Whether a locale is *usable* is decided per field: a built-in field needs a bundled locale, a `faker` field needs one Faker supports. The earlier draft restricted the spec-level key to the two bundled locales, which made a German dataset repeat `locale` on every Faker field; checking per field removes that without weakening any error.

`--locale` joins `--seed`, `--format` and `--out` so that one spec can be run for several regions.

### 6. Faker is an optional extra behind one module

Justification for the dependency, as the project rules require: realistic data for arbitrary locales and domains is a large, maintained dataset that this project should not rebuild, and only users who ask for it need it. So it is an extra, never a requirement.

- `pyproject.toml` gains a `faker` extra, and Faker joins the `dev` extra.
- Only `fakerbridge.py` imports Faker, inside a function, and nothing imports that module unless a spec contains a `faker` field. A test asserts `faker` is absent from `sys.modules` after a run without such a field.
- Each `faker` field gets its own Faker instance, seeded from the field's stream. `Decimal` results become `float`.
- The error for a missing library says `pip install faker`. That is correct however dataspecter itself was installed; the extra is described in the README as the convenient form once the package is published.

**The minimum version is measured, not guessed.** The first Faker task runs the bridge's three touch points (provider lookup, `seed_instance`, calling a provider) against the currently released Faker, records the version, and sets the lower bound from what it verifies.

### 7. The trust boundary

A spec is data, and the `faker` type is the one place where a spec names something to call. The boundary is therefore explicit:

- **What can be called.** Only a name that one of Faker's providers defines as a public method. Underscore names and methods of the Faker object itself (`seed_instance`, `add_provider`) are refused, so a spec cannot reach Faker's own machinery.
- **What can be passed.** Text, numbers, booleans, null, and lists of those. No nested mappings, nothing that could be a callable or a path object.
- **What can come back.** Text, a number, a boolean, a date or a date-time. Bytes and structures are refused.
- **When it is checked.** Once at validation, by calling the provider with the declared arguments, which also catches wrong arguments at the field's location. And on every generated value, cheaply by type, because one sample does not prove a provider always returns the same kind.

This does not make Faker a sandbox: a provider runs whatever code Faker ships. It means a spec can only ask for Faker's documented data generators, with plain arguments.

### 8. Testing without Faker

Faker in the `dev` extra means the local suite always has it. A second CI job installs the project without the extra and runs the suite, in which Faker tests are skipped and the "not installed" tests run for real. Locally the same tests simulate absence by hiding the module.

### 9. Data provenance

Before any list is merged, `src/dataspecter/data/SOURCES.md` records for each one where it came from and under what licence. Lists that cannot be sourced under a licence compatible with redistribution are written by hand or dropped. Tests check structure (minimum sizes, no duplicates, every city's state in the locale's state list, prefixes of the right length); the city-to-state and city-to-prefix mappings themselves are reviewed by a person against the recorded source, as a checklist item in the pull request.

### 10. The format version stays at 1

New types and an optional key. A spec that already declared a custom type with one of the new built-in names keeps its own definition, by the precedence rule.

## Risks / Trade-offs

- **Indian phone numbers can be real** → Stated in the spec and reference; `pattern` offers an escape; never the default for `en_US`.
- **Bundled lists encode a narrow picture of two countries, with uniform frequencies** → A convenience, not a census. Plain tuples in two files, easy to review and extend; custom types and Faker replace them where they do not fit.
- **A source or licence for postcode prefixes may not be found** → Task 1.1 settles sources before any data is written. If prefixes cannot be sourced for a locale, that locale ships postcodes in format only, and the address requirement is amended before implementation continues.
- **Faker's API or data changes between releases** → The bridge has three touch points, verified by the first Faker task; reproducibility is promised per Faker version only.
- **Faker is slow, and each field builds its own instance** → Measured in the benchmark task and reported in the reference, so users can choose the built-ins where speed matters.
- **A provider probe at validation runs Faker code** → It runs only for specs that use the type, and only the named provider.
- **Package size grows** → A few hundred short strings per locale.

## Open Questions

- Whether a range of Indian mobile numbers is reserved for fictional or test use. If one is found, `en_IN` can switch to it in a later change; the spec text would change but nothing in this task breakdown would.
