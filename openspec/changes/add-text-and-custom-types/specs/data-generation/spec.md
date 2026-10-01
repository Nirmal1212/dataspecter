# Spec Delta

## ADDED Requirements

### Requirement: Pattern values
A `pattern` field SHALL produce text in which each `#` is replaced by a random digit from 0 to 9, each `%` by a random digit from 1 to 9 and each `?` by a random upper-case letter, with literal characters and bracketed text kept as written, without the brackets.

#### Scenario: Digits and literals
- **WHEN** a field declares `pattern: "+91-%#########"` and 1,000 rows are generated
- **THEN** every value is `+91-` followed by ten digits, the first of which is not 0

#### Scenario: Letters
- **WHEN** a field declares `pattern: "SKU-??-####"`
- **THEN** every value is `SKU-`, two upper-case letters, a hyphen and four digits

#### Scenario: Bracketed literal
- **WHEN** a field declares `pattern: "Item [#]##"`
- **THEN** every value is `Item #` followed by two digits

#### Scenario: Values vary
- **WHEN** a field declares `pattern: "######"` and 1,000 rows are generated
- **THEN** more than 900 distinct values are produced

### Requirement: Template values
A `template` field SHALL produce its template text with each placeholder replaced by the value, in the same record, of the field it names, after applying the placeholder's filters in order. Numbers SHALL be written in their plain form, booleans as `true` or `false`, and dates and date-times in ISO 8601 format. If any field a template names is null, the template's value SHALL be null.

The filters SHALL behave as follows: `lower` and `upper` change case; `title` capitalises the first letter of each word and lower-cases the rest; `ascii` replaces accented letters with their unaccented form and removes any other character outside ASCII; `slug` applies `ascii` and `lower`, replaces each run of characters other than letters and digits with one hyphen, and removes hyphens from both ends.

#### Scenario: Built from the same record
- **WHEN** `email` declares `template: "{first_name|slug}.{last_name|slug}@example.com"`
- **THEN** in every record `email` is that record's two names, slugged, joined by a dot and followed by `@example.com`

#### Scenario: Case filters
- **WHEN** a field holds `mcDonald` and templates use `{name|upper}`, `{name|lower}` and `{name|title}`
- **THEN** the values are `MCDONALD`, `mcdonald` and `Mcdonald`

#### Scenario: Names that are not plain ASCII words
- **WHEN** a field holds `O'Brien`, `De La Cruz` or `José` and a template uses `{name|slug}`
- **THEN** the values are `o-brien`, `de-la-cruz` and `jose`

#### Scenario: Ascii filter
- **WHEN** a field holds `Zoë Müller` and a template uses `{name|ascii}`
- **THEN** the value is `Zoe Muller`

#### Scenario: Literal braces
- **WHEN** a template is `"{{{id}}}"` and `id` is 7
- **THEN** the value is `{7}`

#### Scenario: Null input
- **WHEN** a template names a field that is null in a record
- **THEN** the template's value in that record is null

#### Scenario: Declared before the fields it uses
- **WHEN** `email` is declared before `first_name` and `last_name` in the entity
- **THEN** generation succeeds, `email` is built from that record's names, and `email` is still the first field in the output

#### Scenario: Reading outward, a nested field and a reference
- **WHEN** a template inside the object `contact` uses `{^home.city}` and `{^customer_name}`, where `customer_name` is a reference on the entity
- **THEN** the value contains that record's city and the referenced customer's name

### Requirement: Unique values
A field with `unique: true` SHALL NOT produce the same non-null value twice within an entity. Nulls produced by `null_probability` are not values and MAY repeat. Unique values SHALL be reproducible for a fixed seed. If generation cannot find an unused value for a row, it SHALL stop with an error naming the field, and SHALL NOT write a repeated value.

#### Scenario: No repeats
- **WHEN** a field declares `type: pattern`, `pattern: "??-###"`, `unique: true` and 10,000 rows are generated
- **THEN** all 10,000 values are different

#### Scenario: Every value used
- **WHEN** a field declares `type: integer`, `min: 1`, `max: 500`, `unique: true` in an entity with `count: 500`
- **THEN** the 500 values are exactly the integers 1 to 500, each once

#### Scenario: Nulls may repeat
- **WHEN** a unique field also declares `null_probability: 0.3`
- **THEN** about 30% of rows are null and all the remaining values differ from each other

#### Scenario: Reproducible
- **WHEN** a spec with a unique field is generated twice with the same seed
- **THEN** the two runs produce identical values

#### Scenario: A unique field as a reference target
- **WHEN** `product.code` is a unique pattern and `order_item.product_code` is `$product.code`
- **THEN** each order item's code identifies exactly one product

### Requirement: Custom type values
A field that uses a custom type SHALL produce values exactly as a field with the type's definition, after overrides, would. Two fields that use the same custom type SHALL produce values independently of each other.

#### Scenario: Same definition, independent values
- **WHEN** `home_phone` and `work_phone` both declare `type: indian_mobile`
- **THEN** both follow the pattern, and they differ from each other in most records

#### Scenario: Equivalent to writing the definition in place
- **WHEN** one spec uses `type: indian_mobile` for a field and another spec writes the same pattern definition directly on that field
- **THEN** the two specs generate identical values for that field with the same seed

#### Scenario: Self-contained object type
- **WHEN** a type `person` is an object with `first_name`, `last_name` and an `email` template over them, and it is used in two entities
- **THEN** in every record of both entities the email is built from the names in that same object

## MODIFIED Requirements

### Requirement: Rows per entity
For each entity, the system SHALL generate exactly `count` rows. Every row SHALL contain every field the entity declares that is not hidden, in the order the fields are declared. Hidden fields SHALL be generated but SHALL NOT appear in the row.

#### Scenario: Row count is honoured
- **WHEN** an entity declares `count: 250`
- **THEN** exactly 250 rows are generated for it

#### Scenario: Field order is preserved
- **WHEN** an entity declares the fields `id`, `name`, `age` in that order
- **THEN** every generated row presents the fields in the order `id`, `name`, `age`

#### Scenario: Hidden fields are left out
- **WHEN** an entity declares `id`, a hidden `first_name`, a hidden `last_name` and an `email` template over the two names
- **THEN** every row contains only `id` and `email`, and each `email` is built from names that do not appear in the row

#### Scenario: Hiding a field does not change other values
- **WHEN** `hidden: true` is added to or removed from a field and the spec is generated again with the same seed
- **THEN** the values of every field, including that one where it is visible, are unchanged
