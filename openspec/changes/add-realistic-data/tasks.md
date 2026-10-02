# Tasks

## 1. Bundled data

- [x] 1.1 Decide the source and licence for each bundled list (given names, family names, street names, cities with states, postcode prefixes) for `en_IN` and `en_US`, record them in `src/dataspecter/data/SOURCES.md`, and verify every list has an entry with a licence that permits redistribution, or is marked as written by hand
- [x] 1.2 Add the data modules for both locales and verify with tests that each has at least 100 given names, 100 family names and 50 cities, no duplicates or empty entries, every city's state in the locale's state list, and every postcode prefix three digits long and valid for the locale's format
- [ ] 1.3 Add a review checklist for the city-to-state and city-to-prefix mappings to the pull request description and verify each mapping against its recorded source

## 2. Locale

- [x] 2.1 Add the spec-level `locale` key checked for form, per-field `locale`, and the resolution order field, caller, spec, `en_US`; verify with tests for the default, a spec-wide locale, a per-field override, a malformed code, and an unbundled locale rejected at a built-in field but accepted when only `faker` fields use it
- [x] 2.2 Add `--locale` to `generate` and a `locale` argument to the Python API's `load_spec`, where locales are validated, and verify with tests for the override, a field keeping its own locale, an unbundled override reported at the field with exit code 2, and a malformed option
- [x] 2.3 Document locale resolution in `docs/spec-reference.md` and `README.md` and verify with the docs test that the snippets load

## 3. Names and email

- [x] 3.1 Implement `first_name`, `last_name` and `full_name` with `format`, and verify with fixed-seed tests that values come from the locale's lists, both formats, more than 500 distinct full names in 1,000 rows, and an unknown key rejected
- [x] 3.2 Add `unique` support with capacities from the list sizes and verify with tests for 5,000 unique full names, a unique first name beyond capacity rejected stating both numbers, and identical values for the same seed
- [x] 3.3 Implement `email` with reserved default domains, the `domain` option and `unique`, and verify with tests for shape, lower case and ASCII, the three reserved domains, a custom domain, an invalid domain, 100,000 unique addresses, and independence from a `full_name` field beside it
- [x] 3.4 Document the name and email types and their options in `docs/spec-reference.md`, with the template recipe for an email that matches a name, and verify with the docs test that the snippets load and the recipe's emails match their records

## 4. Phone and address

- [x] 4.1 Implement `phone` with the `en_US` fictional format, the `en_IN` format, the `pattern` option and `unique`, and verify with tests for both formats, a custom pattern, the 80,000 capacity reported for unique `en_US` numbers, and values as text
- [x] 4.2 Implement `address` as an object generator with a shape set by `fields`, and verify with tests for the five text fields in order, city and state agreeing in 1,000 rows per locale, every postcode beginning with a prefix of its city, a leading-zero postcode kept in JSON and CSV, a subset of fields in the listed order, an unknown field name, and `unique` rejected
- [x] 4.3 Verify that address fields work by path with tests for a template over `home.city` and `home.state`, a reference to `$customer.home.city`, a reference copying the whole address, and the five CSV columns
- [x] 4.4 Verify reproducibility with tests that a spec using all built-in types generates identical records for the same seed, that adding a `phone` field leaves existing names unchanged, and that the golden test still passes
- [x] 4.5 Document `phone` and `address` in `docs/spec-reference.md`, including the statement that Indian numbers may be assigned and that postcodes are consistent to the prefix only, and verify with the docs test that the snippets load

## 5. Faker integration

- [x] 5.1 Add the `faker` extra and add Faker to the `dev` extra in `pyproject.toml`, run the bridge's three touch points (provider lookup, `seed_instance`, calling a provider) against the installed release, set the lower bound from what is verified, and record the version in `design.md`
- [x] 5.2 Add `fakerbridge.py`, the only module importing Faker, with provider lookup limited to public provider methods, argument checking and a validation-time probe; verify with tests for a valid provider, an unknown provider, `_config` and `seed_instance` rejected, an unknown Faker locale, a structured argument, invalid arguments reported at the field, and providers returning a dictionary and bytes rejected
- [x] 5.3 Generate values with one seeded Faker instance per field, checking each result's kind, and verify with tests for `company`, a `de_DE` city, `date_between` with arguments producing dates in range, identical values for the same seed, `Decimal` converted to `float`, a provider made to return an unsupported kind mid-run stopping with the field named, and `unique` with an exhausted provider stopping with an error
- [x] 5.4 Verify optionality with tests that hide the module: a `faker` field is rejected with the `pip install faker` message, a spec without one loads and generates, and `faker` is absent from `sys.modules` after a run without a `faker` field
- [x] 5.5 Add a CI job that installs the project without the `faker` extra and runs the suite, with Faker tests skipped and the not-installed tests running against real absence, and verify the workflow parses and both jobs' commands pass locally
- [x] 5.6 Document the `faker` type, its trust boundary, the install options and the per-version reproducibility in `docs/spec-reference.md` and `README.md`, and verify with the docs test that the snippets load

## 6. Examples

- [x] 6.1 Extend `examples/shop.yaml` and `examples/shop.json` with a named customer (built-in name, template email over hidden name parts, phone, address) and an order shipping city read from `$customer.home.city`; verify with tests that both files load to the same spec, generate identical data, and that each documented relationship holds
- [x] 6.2 Update `README.md` (field type table, a realistic example) and verify that each documented command runs as written against `examples/shop.yaml` in all three formats

## 7. Wrap-up

- [x] 7.1 Generate one million rows of an entity with a name, an email, a phone and an address, and 100,000 rows with a `faker` field, on the same machine as the baseline; record time and peak memory in `design.md` and verify flat throughput is within 15% of the baseline
- [x] 7.2 Verify `uv run pytest`, `uv run ruff check .` and `openspec validate add-realistic-data --strict` all pass
- [x] 7.3 Add entries under `[Unreleased]` in `CHANGELOG.md` for the built-in types and their options, locale handling with `--locale`, and the Faker type and extra, and verify each item in the proposal is named
- [ ] 7.4 Archive the change with `/opsx:archive` and verify `openspec/specs/` contains the new `realistic-data` spec and the updated `simulation-spec` and `cli`
