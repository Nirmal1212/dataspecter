# Proposal

## Why

Writing the first real config showed that the version 1 format is correct but wordy, and that it cannot express one thing realistic data needs. A reference takes four keys to say "the customer's id", a weighted list needs two parallel arrays that are easy to misalign, and an order item's `unit_price` cannot be the price of the product named by its `product_id`, because every reference picks its own row.

## What Changes

- **Reference shorthand.** A field may be written as the string `$entity.field` instead of a `reference` mapping, so `customer_id: $customer.id` replaces `customer_id: {type: reference, entity: customer, field: id}`.
- **Copying values from the referenced row.** **BREAKING**: all references from one entity to the same target entity now read from the same target row. With `product_id: $product.id` and `unit_price: $product.price`, each order item gets one product's id and that same product's price. Today the two fields pick independent rows.
- **Named links for independent picks.** The mapping form of a reference gains an optional `link` name. References to the same entity with different links choose their rows independently, which keeps cases like a transfer's sender and receiver expressible.
- **Weighted value shorthand.** A `choice` value may carry its weight inline as `value || weight`, so `values: ["FRIEND10 || 0.2", "LAUNCH25 || 0.2", "PARTNER || 0.1", " || 0.5"]` replaces separate `values` and `weights` lists. An empty value, as in the last entry, means null.
- **Typed inline values.** Inline values are text unless the field declares `value_type` (`integer`, `float`, `boolean` or `string`), which converts every value in the list: `value_type: integer` with `values: ["1 || 60", "2 || 30"]` yields the numbers 1 and 2.
- **Null as a choice value.** `values` may contain a null entry in the list form too, giving nulls an explicit weight alongside the other values.
- **Weighted range shorthand.** A `ranges` item may be written as `min to max || weight`, so `"18 to 35 || 0.7"` replaces `{min: 18, max: 35, weight: 0.7}`.
- **Null probability, stated precisely.** The spec and reference now say how `null_probability` combines with a field's own values: nulls are decided first, and the remaining rows follow the field's rules, so with `null_probability: 0.8` and two equally likely values each value appears in 10% of rows.

Every existing form keeps working; the shorthands are alternatives, not replacements.

Out of scope, and planned as the next change: nested objects (including references into them), reusable custom field types, patterns and templates, built-in name, email, phone and address generators, and an optional Faker integration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `simulation-spec`: a field definition may be a `$entity.field` string; `reference` gains `link`; `choice` values accept the `value || weight` form, an optional `value_type` and null entries; `ranges` items accept the `min to max || weight` form.
- `data-generation`: references from one entity to the same target share a row per link; a null entry in `choice` values produces nulls in proportion to its weight; the interaction of `null_probability` with a field's own values is specified; adding a reference does not change the values of existing references.

## Impact

- **Code**: `spec.py` (parsing and validating the shorthands, the `link` key, null choice values), `generators.py` and `engine.py` (one row pick per link instead of one per reference field).
- **Compatibility**: one behaviour change. For a fixed seed, reference fields produce different values than before, and two references to the same entity are no longer independent unless given different links. Nothing has been released, so no published version is affected; the change is recorded in the changelog as breaking.
- **Docs and examples**: `docs/spec-reference.md` and `README.md` document the shorthands; `examples/shop.yaml` and `examples/shop.json` are rewritten to use them, and `order_item.unit_price` becomes the referenced product's price.
- **Dependencies**: none added.
