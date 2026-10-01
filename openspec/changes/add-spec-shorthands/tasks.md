# Tasks

## 1. Reference shorthand

- [x] 1.1 Accept a `$entity.field` string as a field definition in `spec.py`, producing the same `ReferenceField` as the mapping form, and reject any other non-mapping definition with an error showing the expected form; verify with tests for equality with the mapping form, `$customer`, `$customer.id.extra`, `customer.id`, `$ customer.id`, a number or list as the definition, and `$`-prefixed text staying literal in a `constant` value and in `choice` values
- [x] 1.2 Make the cross-entity pass read shorthand references as well as mappings, and verify with tests that an unknown entity, an unknown field, a self-reference and a cycle written in shorthand are each reported at the field's path
- [x] 1.3 Document the shorthand in the References section of `docs/spec-reference.md`, and verify with a test that the snippet shown there loads as a valid spec

## 2. Shared rows and links

- [x] 2.1 Add the optional `link` key to the `reference` mapping, validated as a name, and verify with tests for an accepted link, an invalid link name, and the default of no link
- [x] 2.2 Replace per-field row choice with one pick per `(entity, target entity, link)` drawing from its own stream, in `generators.py` and `engine.py`; verify with tests that `unit_price` equals the price of the product named by `product_id` in every row, that references sharing a link agree, that references with different links differ in most rows, that the same link name on two target entities gives unrelated picks, and that a reference without a link is independent of linked references to the same entity
- [x] 2.3 Verify the column-only path with tests that a child entity generated without iterating its parents equals the same entity from a full pass, including a reference to a field that is itself a reference
- [x] 2.4 Verify stability and null handling with tests that adding a second reference to the same entity leaves the first unchanged for the same seed, and that `null_probability` on one reference leaves the other intact and correct
- [x] 2.5 Rewrite the References section of `docs/spec-reference.md` (shared row, `link`, per-field nulls), replace the "pick their rows independently" entry in Current limits with a note that independent links can land on the same row, and verify with a test that the sender and receiver snippet loads and behaves as described

## 3. Weighted choice values

- [x] 3.1 Allow null entries in `values` in the list form, and verify with tests that `values: [FRIEND10, null]` with `weights: [1, 4]` is accepted, generates nulls in about 80% of rows, and exports as an empty CSV field and a JSON `null`
- [x] 3.2 Parse the `value || weight` form in `spec.py` (only without `weights`, split on the last `||`, trimmed, value as text, empty value as null, every entry or none); verify with tests for the four-entry referral example, a list mixing weighted and unweighted strings, a number among weighted entries, the weights `lots`, `20%`, empty and `-1`, weights summing to zero, a value containing `||`, `10 || 0.5` yielding text, literal entries when `weights` is declared, and the hint about `weights` when an unweighted list contains `||`
- [x] 3.3 Add `value_type` (`string`, `integer`, `float`, `boolean`) for fields with inline weights, converting strictly and without evaluating the text; verify with tests for integer, float and boolean lists, an empty value staying null under each type, `2.5` and `two` rejected for `integer` at their entry, an unknown type name, and `value_type` rejected on a list without inline weights
- [x] 3.4 Verify generation with fixed-seed tests that the referral example gives shares within 3 points of 20%, 20%, 10% and 50% null, that inline and listed weights generate identical values, that two values with `null_probability: 0.8` give about 80% nulls and 10% each, and that a null entry of weight 0.5 with `null_probability: 0.5` gives about 75% nulls, and that `value_type: integer` values are generated as integers and written to JSON as numbers
- [x] 3.5 Document the inline form, `value_type`, null entries and the null arithmetic in the `choice` and Nulls sections of `docs/spec-reference.md`, add the quoting note for entries starting with a space or `|` to the YAML section, and verify with a test that the documented snippets load

## 4. Weighted range shorthand

- [x] 4.1 Parse `min to max || weight` items in `ranges`, running the result through the existing range checks, and verify with tests for equality with the mapping form, negative and decimal bounds including `.9`, optional spaces around `||`, a list mixing strings and mappings, `18-35 || 0.7`, `18..35 || 0.7`, `18to35 || 0.7` and `18 to 35` rejected with the expected form, a decimal bound in an integer field, `min` above `max`, and each problem located at `ranges[i]`
- [x] 4.2 Document the shorthand in the `integer` and `float` section of `docs/spec-reference.md` and verify with a test that the documented snippet loads and generates the same data as its mapping form

## 5. Examples

- [x] 5.1 Rewrite `examples/shop.yaml` and `examples/shop.json` with the shorthands, taking `order_item.unit_price` from `$product.price` and giving `referral_code` an inline null weight; verify with tests that the two files load to the same spec, generate identical data, and that every order item's `unit_price` is its product's price
- [x] 5.2 Update the spec snippet and usage text in `README.md` to the shorthand forms and verify that each documented command runs as written against `examples/shop.yaml`

## 6. Wrap-up

- [ ] 6.1 Verify `uv run pytest`, `uv run ruff check .` and `openspec validate add-spec-shorthands --strict` all pass
- [ ] 6.2 Add entries under `[Unreleased]` in `CHANGELOG.md`: the shorthands, `link` and null choice values under Added, and the shared-row behaviour under Changed marked as breaking; verify the entry names each of the six items in the proposal
- [ ] 6.3 Archive the change with `/opsx:archive` and verify `openspec/specs/simulation-spec` and `openspec/specs/data-generation` contain the new and modified requirements
