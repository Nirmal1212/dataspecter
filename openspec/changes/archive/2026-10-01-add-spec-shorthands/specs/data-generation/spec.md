# Spec Delta

## MODIFIED Requirements

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
