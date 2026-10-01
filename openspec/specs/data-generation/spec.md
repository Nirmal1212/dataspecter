# data-generation Specification

## Purpose

Defines how dataspecter turns a valid simulation spec into rows of synthetic data: what each field type produces, how distributions and probabilities shape the values, how entities relate through references, and what makes a run reproducible.

## Requirements

### Requirement: Rows per entity
For each entity, the system SHALL generate exactly `count` rows. Every row SHALL contain every field the entity declares, in the order the fields are declared.

#### Scenario: Row count is honoured
- **WHEN** an entity declares `count: 250`
- **THEN** exactly 250 rows are generated for it

#### Scenario: Field order is preserved
- **WHEN** an entity declares the fields `id`, `name`, `age` in that order
- **THEN** every generated row presents the fields in the order `id`, `name`, `age`

### Requirement: Uniform numeric values
An `integer` or `float` field with a uniform distribution SHALL produce values between `min` and `max` inclusive, with every part of the range equally likely. `integer` fields SHALL produce whole numbers. A `float` field with `precision` SHALL produce values rounded to that many decimal places.

#### Scenario: Integer within range
- **WHEN** a field declares `type: integer`, `min: 18`, `max: 90` and 10,000 rows are generated
- **THEN** every value is a whole number from 18 to 90, and both 18 and 90 are possible values

#### Scenario: Float precision
- **WHEN** a field declares `type: float`, `min: 0`, `max: 100`, `precision: 2`
- **THEN** every value has at most two decimal places

### Requirement: Normally distributed values
A numeric field with `distribution: normal` SHALL produce values following a normal distribution with the declared `mean` and `stddev`. When `min` or `max` is declared, every value SHALL lie within those bounds.

#### Scenario: Values centre on the mean
- **WHEN** a field declares `distribution: normal`, `mean: 40`, `stddev: 12` and 10,000 rows are generated
- **THEN** the average of the values is within 1.2 of 40

#### Scenario: Bounds are respected
- **WHEN** the same field also declares `min: 18` and `max: 90`
- **THEN** no generated value is below 18 or above 90

### Requirement: Weighted ranges
A numeric field with `ranges` SHALL choose a range for each row with probability proportional to its `weight`, then produce a value uniformly within that range.

#### Scenario: Proportions follow the weights
- **WHEN** a field declares ranges 18 to 35 (weight 0.7), 36 to 60 (weight 0.25) and 61 to 90 (weight 0.05), and 10,000 rows are generated
- **THEN** the share of values in each range is within 3 percentage points of 70%, 25% and 5%

#### Scenario: Weights are relative
- **WHEN** the same ranges are declared with weights 70, 25 and 5
- **THEN** the proportions are the same as with 0.7, 0.25 and 0.05

#### Scenario: Zero-weight range
- **WHEN** one range has `weight: 0`
- **THEN** no generated value comes from that range

### Requirement: Choice values
A `choice` field SHALL produce only values from its `values` list. Without weights, every value SHALL be equally likely. With weights, whether declared in `weights` or inline, each value SHALL be chosen with probability proportional to its weight. A null entry SHALL produce a null and is chosen like any other value. Values written with inline weights SHALL be produced in the field's `value_type`.

#### Scenario: Only listed values appear
- **WHEN** a field declares `values: [free, pro, enterprise]`
- **THEN** every generated value is one of `free`, `pro` or `enterprise`

#### Scenario: Weighted choice proportions
- **WHEN** the field also declares `weights: [70, 25, 5]` and 10,000 rows are generated
- **THEN** the share of each value is within 3 percentage points of 70%, 25% and 5%

#### Scenario: Null entry with a weight
- **WHEN** a field declares `values: ["FRIEND10 || 0.2", "LAUNCH25 || 0.2", "PARTNER || 0.1", " || 0.5"]` and 10,000 rows are generated
- **THEN** the shares of `FRIEND10`, `LAUNCH25`, `PARTNER` and null are within 3 percentage points of 20%, 20%, 10% and 50%

#### Scenario: Inline and listed weights generate the same data
- **WHEN** one spec declares `values: ["free || 70", "pro || 30"]` and another declares `values: [free, pro]` with `weights: [70, 30]`
- **THEN** the two generate identical values for the same seed

#### Scenario: Typed inline values
- **WHEN** a field declares `value_type: integer` and `values: ["1 || 60", "2 || 30", "5 || 10"]`
- **THEN** every generated value is the integer 1, 2 or 5, and it is written to JSON as a number, not as text

### Requirement: Boolean values
A `boolean` field SHALL produce `true` with probability `true_probability` and `false` otherwise.

#### Scenario: Always true
- **WHEN** a field declares `true_probability: 1`
- **THEN** every generated value is `true`

#### Scenario: Proportion follows the probability
- **WHEN** a field declares `true_probability: 0.2` and 10,000 rows are generated
- **THEN** the share of `true` values is within 3 percentage points of 20%

### Requirement: Date and time values
A `date` field SHALL produce calendar dates, and a `datetime` field SHALL produce date-times, between `min` and `max` inclusive.

#### Scenario: Dates within range
- **WHEN** a `date` field declares `min: 2024-01-01` and `max: 2024-12-31`
- **THEN** every generated value is a date in 2024

#### Scenario: Date-times within range
- **WHEN** a `datetime` field declares `min: 2024-01-01T00:00:00` and `max: 2024-01-01T23:59:59`
- **THEN** every generated value falls on 1 January 2024

### Requirement: Identifier and constant values
A `sequence` field SHALL produce `start` for the first row and add `step` for each following row. A `uuid` field SHALL produce a valid UUID that is unique within the entity. A `constant` field SHALL produce its declared `value` in every row.

#### Scenario: Sequence with defaults
- **WHEN** a `sequence` field declares no options and 3 rows are generated
- **THEN** the values are 1, 2, 3

#### Scenario: Sequence with start and step
- **WHEN** a `sequence` field declares `start: 1000` and `step: 10` and 3 rows are generated
- **THEN** the values are 1000, 1010, 1020

#### Scenario: Unique identifiers
- **WHEN** a `uuid` field is generated for 10,000 rows
- **THEN** all 10,000 values are valid UUIDs and no two are equal

#### Scenario: Constant value
- **WHEN** a `constant` field declares `value: EUR`
- **THEN** every row has the value `EUR`

### Requirement: Null values
A field with `null_probability` SHALL produce a null in place of its value with that probability, independently for each row. The rows that are not made null SHALL follow the field's own rules, so each of the field's own proportions is scaled by one minus `null_probability`.

#### Scenario: Never null by default
- **WHEN** a field declares no `null_probability`
- **THEN** no generated value is null

#### Scenario: Always null
- **WHEN** a field declares `null_probability: 1`
- **THEN** every generated value is null

#### Scenario: Proportion of nulls
- **WHEN** a field declares `null_probability: 0.1` and 10,000 rows are generated
- **THEN** the share of null values is within 3 percentage points of 10%

#### Scenario: The remaining share follows the field's own rules
- **WHEN** a `choice` field declares two values without weights and `null_probability: 0.8`, and 10,000 rows are generated
- **THEN** the share of nulls is within 3 percentage points of 80% and the share of each value is within 3 percentage points of 10%

#### Scenario: Null probability combined with a null entry
- **WHEN** a `choice` field declares `values: ["yes || 0.5", " || 0.5"]` and `null_probability: 0.5`, and 10,000 rows are generated
- **THEN** the share of nulls is within 3 percentage points of 75%

### Requirement: References between entities
For each row of an entity, the system SHALL choose one row of each target entity that the entity references, each target row being equally likely, and every `reference` field pointing at that target SHALL take its value from the chosen row. References that declare different `link` names SHALL choose their rows independently of one another, so they may by chance choose the same row; references with the same `link`, or with none, SHALL share a row. A link name applies to one target entity: the same name used for two different target entities denotes two unrelated choices. Entities SHALL be generated correctly whatever order they are declared in.

#### Scenario: Every reference resolves
- **WHEN** `order.customer_id` references `customer.id`, with 100 customers and 500 orders
- **THEN** every `order.customer_id` equals the `id` of one of the 100 generated customers

#### Scenario: Declaration order does not matter
- **WHEN** `order` is declared before `customer` in the spec
- **THEN** generation succeeds and every reference still resolves

#### Scenario: Chained references
- **WHEN** `order_item` references `order`, and `order` references `customer`
- **THEN** all three entities are generated and every reference resolves

#### Scenario: Values are copied from the same row
- **WHEN** `order_item` declares `product_id: $product.id` and `unit_price: $product.price`
- **THEN** in every order item, `unit_price` equals the `price` of the product whose `id` is that item's `product_id`

#### Scenario: Different links choose independently
- **WHEN** `transfer` declares `sender_id` and `sender_name` referencing `account` with `link: sender`, and `receiver_id` referencing `account` with `link: receiver`, and 1,000 transfers are generated over 100 accounts
- **THEN** in every transfer `sender_name` is the name of the account whose `id` is `sender_id`, and `receiver_id` differs from `sender_id` in most transfers

#### Scenario: The same link name on different target entities
- **WHEN** `shipment` declares `from_city: {entity: city, field: name, link: origin}` and `from_depot: {entity: depot, field: code, link: origin}`
- **THEN** the city row and the depot row are chosen independently of each other

#### Scenario: A reference without a link next to linked ones
- **WHEN** `transfer` declares `owner_id: $account.id` together with references to `account` using `link: sender` and `link: receiver`
- **THEN** `owner_id` is chosen independently of both the sender and the receiver

#### Scenario: A null in one reference leaves the others intact
- **WHEN** `order_item.unit_price` references `product.price` with `null_probability: 0.5` and `order_item.product_id` references `product.id`
- **THEN** `product_id` is never null, and wherever `unit_price` is not null it is the price of that product

### Requirement: Reproducible generation
The same spec generated with the same seed SHALL produce identical data on every run. The seed SHALL be taken from an explicit override when one is given, otherwise from the spec's `seed`. When neither is given, the system SHALL choose a seed and make the chosen value available to the caller, so the run can be repeated.

#### Scenario: Same seed, same data
- **WHEN** a spec with `seed: 42` is generated twice
- **THEN** the two runs produce identical rows for every entity

#### Scenario: Different seeds, different data
- **WHEN** the same spec is generated with seed 42 and with seed 43
- **THEN** the generated data differs between the two runs

#### Scenario: Override takes precedence
- **WHEN** a spec declares `seed: 42` and a run supplies the seed 7
- **THEN** the data is identical to a run of the same spec declaring `seed: 7`

#### Scenario: No seed supplied
- **WHEN** a spec has no `seed` and none is supplied
- **THEN** the run reports the seed it used, and generating again with that seed reproduces the same data

### Requirement: Stable values when a spec is edited
For a fixed seed, the values generated for a field SHALL NOT change when other fields are added to, removed from or reordered within the spec.

#### Scenario: Adding a field
- **WHEN** a field `loyalty_points` is added to the `customer` entity and the spec is generated again with the same seed
- **THEN** the values of every previously existing field are unchanged

#### Scenario: Adding an entity
- **WHEN** a new entity is added to the spec and it is generated again with the same seed
- **THEN** the rows of every previously existing entity are unchanged

#### Scenario: Adding a second reference to the same entity
- **WHEN** `order_item` already declares `product_id: $product.id`, and `unit_price: $product.price` is added and the spec is generated again with the same seed
- **THEN** the values of `product_id` are unchanged
