# Spec Delta

## ADDED Requirements

### Requirement: Reference shorthand
A field definition written as a string of the form `$<entity>.<field>` SHALL be equivalent to a `reference` mapping with that `entity` and `field` and no other keys. The same validation SHALL apply as for the mapping form, with problems reported at the field's location. A string that is not of this form SHALL be rejected with an error showing the expected form.

#### Scenario: Shorthand is equivalent to the mapping form
- **WHEN** `order.customer_id` is written as `$customer.id`
- **THEN** the spec is accepted and generates the same data, for the same seed, as `{type: reference, entity: customer, field: id}`

#### Scenario: Unknown target in shorthand
- **WHEN** `order.customer_id` is written as `$client.id` and no entity `client` exists
- **THEN** the system rejects it with an error at `entities.order.fields.customer_id` naming the missing entity

#### Scenario: Malformed shorthand
- **WHEN** a field is written as `$customer`, `$customer.id.extra`, `customer.id` or `$ customer.id`
- **THEN** the system rejects it with an error stating that the expected form is `$entity.field`

#### Scenario: Dollar text elsewhere is literal
- **WHEN** a `constant` field declares `value: "$customer.id"`, or a `choice` field lists `"$5.00"` among its values
- **THEN** the text is kept as written and is not treated as a reference

### Requirement: Weighted value shorthand
When a `choice` field declares no `weights`, an entry of `values` that is a string containing `||` SHALL be read as a value and its weight: the text before the last `||`, with surrounding spaces removed, is the value, and the text after it SHALL be a non-negative number giving the weight. An empty value SHALL mean null. If any entry carries a weight, every entry SHALL carry one; an entry that is not a string carries none. The weights follow the same rules as `weights`. When `weights` is declared, every entry of `values` SHALL be taken literally.

A field whose values carry inline weights MAY declare `value_type`, one of `string` (the default), `integer`, `float` or `boolean`, and every non-empty value SHALL be converted to that type. A value that cannot be converted SHALL be rejected. `value_type` SHALL be rejected on a field whose values carry no inline weights, since values in the list form already have their types.

#### Scenario: Inline weights
- **WHEN** a field declares `values: ["FRIEND10 || 0.2", "LAUNCH25 || 0.2", "PARTNER || 0.1", " || 0.5"]`
- **THEN** it is accepted as the values `FRIEND10`, `LAUNCH25`, `PARTNER` and null with the weights 0.2, 0.2, 0.1 and 0.5

#### Scenario: Only some entries carry a weight
- **WHEN** a field declares `values: ["free || 0.7", "pro"]`
- **THEN** the system rejects it with an error stating that either every value carries a weight or none does

#### Scenario: A number among weighted entries
- **WHEN** a field declares `values: ["free || 0.7", 10]`
- **THEN** the system rejects it with the same error, because the number carries no weight

#### Scenario: Weight that is not a number
- **WHEN** an entry is written as `PARTNER || lots`, `PARTNER || 20%` or `PARTNER ||`
- **THEN** the system rejects it with an error naming that entry and stating that the weight must be a non-negative number

#### Scenario: Negative weight
- **WHEN** an entry is written as `PARTNER || -1`
- **THEN** the system rejects it with an error describing the weight rules

#### Scenario: Value containing the separator
- **WHEN** an entry is written as `a || b || 0.5`
- **THEN** its value is the text `a || b` and its weight is 0.5

#### Scenario: Literal text containing the separator, without weights
- **WHEN** a field declares `values: ["yes || no", "maybe"]` and no `weights`, meaning the first entry as plain text
- **THEN** the system rejects it, and the error states that declaring `weights` makes every entry literal

#### Scenario: Value is text by default
- **WHEN** an entry is written as `10 || 0.5` and the field declares no `value_type`
- **THEN** its value is the text `10`, not the number 10

#### Scenario: Integer values
- **WHEN** a field declares `value_type: integer` and `values: ["1 || 60", "2 || 30", "5 || 10", " || 5"]`
- **THEN** it is accepted with the integer values 1, 2 and 5 and a null

#### Scenario: Value that does not fit the declared type
- **WHEN** a field declares `value_type: integer` and an entry `2.5 || 1` or `two || 1`
- **THEN** the system rejects it with an error naming that entry and the expected type

#### Scenario: Boolean and decimal values
- **WHEN** one field declares `value_type: boolean` with `values: ["true || 9", "false || 1"]` and another declares `value_type: float` with `values: ["0.5 || 1", "2 || 1"]`
- **THEN** the first has the boolean values true and false, and the second the decimal values 0.5 and 2.0

#### Scenario: Value type without inline weights
- **WHEN** a field declares `value_type: integer` with `values: [1, 2, 3]`
- **THEN** the system rejects it with an error stating that `value_type` applies only to values written with inline weights

#### Scenario: Entries are literal when weights are declared
- **WHEN** a field declares `values: ["a || b", "c"]` together with `weights: [1, 1]`
- **THEN** it is accepted and the first value is the text `a || b`

### Requirement: Weighted range shorthand
An item of `ranges` MAY be written as a string of the form `<min> to <max> || <weight>`, which SHALL be equivalent to the mapping with those `min`, `max` and `weight` values and subject to the same rules. The word `to` SHALL be surrounded by spaces; spaces around `||` are optional. A bound SHALL be a plain decimal number with an optional minus sign, and MAY omit the digit before the decimal point. String items and mapping items MAY be mixed in one list. A string that is not of this form SHALL be rejected with an error showing the expected form.

#### Scenario: Ranges written as strings
- **WHEN** an `integer` field declares `ranges: ["18 to 35 || 0.7", "36 to 60 || 0.25", "61 to 90 || 0.05"]`
- **THEN** it is accepted and generates the same data, for the same seed, as the three mappings with those bounds and weights

#### Scenario: Negative and decimal bounds
- **WHEN** a `float` field declares `ranges: ["-10.5 to -0.5 || 1", "0.4 to .9 || 3"]`
- **THEN** it is accepted with the ranges -10.5 to -0.5 and 0.4 to 0.9

#### Scenario: Spacing around the weight separator
- **WHEN** an item is written as `18 to 35||0.7` or `18  to  35  ||  0.7`
- **THEN** it is accepted as the range 18 to 35 with weight 0.7

#### Scenario: Malformed range
- **WHEN** an item is written as `18-35 || 0.7`, `18..35 || 0.7`, `18to35 || 0.7` or `18 to 35`
- **THEN** the system rejects it with an error at that item stating that the expected form is `min to max || weight`

#### Scenario: Decimal bound in an integer field
- **WHEN** an `integer` field declares the item `1.5 to 3 || 1`
- **THEN** the system rejects it with an error stating that the bounds must be integers

#### Scenario: Minimum above maximum
- **WHEN** the second item of `ranges` is written as `35 to 18 || 1`
- **THEN** the system rejects it with an error at that item stating that `min` must not exceed `max`

#### Scenario: Strings and mappings together
- **WHEN** a field declares `ranges: ["18 to 35 || 0.7", {min: 36, max: 90, weight: 0.3}]`
- **THEN** it is accepted with both ranges

## MODIFIED Requirements

### Requirement: Field types
Every field definition SHALL be either a mapping that declares a `type`, or a reference shorthand string. `type` SHALL be one of `integer`, `float`, `boolean`, `choice`, `date`, `datetime`, `sequence`, `uuid`, `constant` or `reference`. Each type SHALL accept only the keys defined for it.

#### Scenario: Unknown field type
- **WHEN** a field declares `type: email`
- **THEN** the system rejects it with an error that lists the supported types

#### Scenario: Key that does not belong to the type
- **WHEN** a `boolean` field also declares `min: 1`
- **THEN** the system rejects it with an error naming the key `min`

#### Scenario: Definition that is neither a mapping nor a reference
- **WHEN** a field is defined as the number `42` or as a list
- **THEN** the system rejects it with an error stating that a field must be a mapping with a `type` or a `$entity.field` reference

### Requirement: Numeric field definitions
An `integer` or `float` field SHALL define its values in exactly one of two ways: a single range (`min` and `max`, with an optional `distribution`), or a list of weighted `ranges`.

For a single range, `distribution` SHALL be `uniform` (the default) or `normal`. A `uniform` field SHALL declare both `min` and `max`. A `normal` field SHALL declare `mean` and `stddev`, where `stddev` is greater than zero, and MAY declare `min` and `max`. Wherever both are present, `min` SHALL NOT exceed `max`.

For weighted ranges, each item SHALL declare `min`, `max` and `weight`, either as a mapping or in the weighted range shorthand (`min to max || weight`). Weights SHALL be non-negative with a sum greater than zero; they need not sum to 1.

A `float` field MAY declare `precision`, a non-negative integer number of decimal places.

#### Scenario: Uniform range
- **WHEN** a field declares `type: integer`, `min: 18`, `max: 90`
- **THEN** the field is accepted with a uniform distribution

#### Scenario: Minimum above maximum
- **WHEN** a field declares `min: 90` and `max: 18`
- **THEN** the system rejects it with an error stating that `min` must not exceed `max`

#### Scenario: Normal distribution without parameters
- **WHEN** a field declares `distribution: normal` without `mean` or `stddev`
- **THEN** the system rejects it with an error naming the missing keys

#### Scenario: Weighted ranges
- **WHEN** a field declares `ranges` with three items weighted 0.7, 0.25 and 0.05
- **THEN** the field is accepted

#### Scenario: Both forms used together
- **WHEN** a field declares both `min`/`max` and `ranges`
- **THEN** the system rejects it with an error stating that the two forms are mutually exclusive

#### Scenario: Weights that cannot be used
- **WHEN** every item in `ranges` has `weight: 0`, or any weight is negative
- **THEN** the system rejects it with an error describing the weight rules

### Requirement: Other field definitions
A `boolean` field MAY declare `true_probability` between 0 and 1 inclusive (default 0.5). A `choice` field SHALL declare a non-empty `values` list, each entry being a string, number, boolean or null, and MAY declare `weights`, a list of the same length following the weight rules for ranges; alternatively its values MAY carry their weights inline in the weighted value shorthand, optionally with a `value_type`. A `date` or `datetime` field SHALL declare `min` and `max` as ISO 8601 values, with `min` not after `max`. A `sequence` field MAY declare integer `start` (default 1) and non-zero integer `step` (default 1). A `constant` field SHALL declare `value`. A `uuid` field takes no further keys.

#### Scenario: Weighted choice
- **WHEN** a `choice` field declares `values: [free, pro, enterprise]` and `weights: [70, 25, 5]`
- **THEN** the field is accepted

#### Scenario: Weights of the wrong length
- **WHEN** a `choice` field declares three values and two weights
- **THEN** the system rejects it with an error stating that `weights` must match `values` in length

#### Scenario: Null as a value
- **WHEN** a `choice` field declares `values: [FRIEND10, null]` and `weights: [1, 4]`
- **THEN** the field is accepted

#### Scenario: Invalid date
- **WHEN** a `date` field declares `min: 2024-13-01`
- **THEN** the system rejects it with an error stating that the value is not a valid ISO 8601 date

#### Scenario: Zero step
- **WHEN** a `sequence` field declares `step: 0`
- **THEN** the system rejects it with an error stating that `step` must not be zero

### Requirement: Reference field definitions
A `reference` field SHALL declare `entity` and `field`, naming a field of another entity in the same spec, and MAY declare `link`, a name following the rules for entity and field names. References SHALL NOT form a cycle between entities, and an entity SHALL NOT reference itself.

#### Scenario: Valid reference
- **WHEN** `order.customer_id` declares `type: reference`, `entity: customer`, `field: id`, and `customer.id` exists
- **THEN** the field is accepted, regardless of the order in which the two entities are declared

#### Scenario: Unknown target entity
- **WHEN** a reference names an entity that is not in the spec
- **THEN** the system rejects it with an error naming the missing entity

#### Scenario: Unknown target field
- **WHEN** a reference names a field that the target entity does not define
- **THEN** the system rejects it with an error naming the missing field

#### Scenario: Circular references
- **WHEN** entity `a` references entity `b` and entity `b` references entity `a`
- **THEN** the system rejects the spec with an error naming the entities in the cycle

#### Scenario: Named link
- **WHEN** `transfer.sender_id` declares `entity: account`, `field: id`, `link: sender`
- **THEN** the field is accepted

#### Scenario: Invalid link name
- **WHEN** a reference declares `link: "the sender"`
- **THEN** the system rejects it with an error describing the allowed characters for names
