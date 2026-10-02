# simulation-spec Specification

## Purpose

Defines the simulation spec: the YAML or JSON document in which a user declares the entities, fields and value rules that dataspecter turns into synthetic data, and the validation applied to that document before any data is generated.

## Requirements

### Requirement: Spec file formats
The system SHALL load a simulation spec from a YAML file (`.yaml` or `.yml`) or a JSON file (`.json`), chosen by file extension. A YAML spec and a JSON spec with the same content SHALL be treated identically.

#### Scenario: YAML spec is loaded
- **WHEN** a valid spec is supplied as `customers.yaml`
- **THEN** the spec is loaded and accepted

#### Scenario: Equivalent JSON spec behaves the same
- **WHEN** the same spec content is supplied as `customers.json`
- **THEN** it is accepted and generates the same data as the YAML version for the same seed

#### Scenario: Unsupported file extension
- **WHEN** a spec is supplied as `customers.toml`
- **THEN** the system rejects it with an error naming the supported extensions

#### Scenario: Malformed file
- **WHEN** a spec file contains invalid YAML or JSON syntax
- **THEN** the system rejects it with an error that names the file and the position of the syntax error

#### Scenario: Missing file
- **WHEN** the supplied spec path does not exist
- **THEN** the system rejects it with an error naming the path

### Requirement: Spec structure
A spec SHALL contain `version` and `entities`, and MAY contain `seed`, `output` and `types`. `version` SHALL be `1`. `entities` SHALL be a mapping of at least one entity name to an entity definition. Each entity definition SHALL contain `count`, an integer of 1 or more, and `fields`, a mapping of at least one field name to a field definition. `seed`, when present, SHALL be a non-negative integer. `output`, when present, MAY contain `format`, `dir` and `csv_separator`; `csv_separator` SHALL be `.` or `__`. `types`, when present, SHALL be a mapping of type name to field definition. Entity and field names SHALL start with a letter or underscore and contain only letters, digits and underscores. Any key the format does not define SHALL be rejected.

#### Scenario: Minimal valid spec
- **WHEN** a spec has `version: 1` and one entity with `count: 10` and one field
- **THEN** the spec is accepted

#### Scenario: Unsupported version
- **WHEN** a spec declares `version: 2`
- **THEN** the system rejects it with an error stating that only version 1 is supported

#### Scenario: No entities
- **WHEN** a spec has an empty `entities` mapping
- **THEN** the system rejects it with an error stating that at least one entity is required

#### Scenario: Unknown key
- **WHEN** an entity definition contains the key `cout` instead of `count`
- **THEN** the system rejects it with an error naming the unknown key `cout`

#### Scenario: Invalid entity name
- **WHEN** an entity is named `my-orders`
- **THEN** the system rejects it with an error describing the allowed characters for names

#### Scenario: Unsupported column separator
- **WHEN** a spec declares `output.csv_separator: "/"`
- **THEN** the system rejects it with an error listing the supported separators

#### Scenario: Types that is not a mapping
- **WHEN** a spec declares `types` as a list
- **THEN** the system rejects it with an error stating that `types` must be a mapping of type name to definition

### Requirement: Field types
Every field definition SHALL be either a mapping that declares a `type`, or a reference shorthand string. `type` SHALL be one of the built-in types `integer`, `float`, `boolean`, `choice`, `date`, `datetime`, `sequence`, `uuid`, `constant`, `reference`, `object`, `pattern` or `template`, or the name of a custom type declared in the spec. Each type SHALL accept only the keys defined for it, together with the keys every field accepts: `null_probability`, `hidden`, and `unique` where the type supports it.

#### Scenario: Unknown field type
- **WHEN** a field declares `type: email` and the spec declares no custom type of that name
- **THEN** the system rejects it with an error that lists the built-in types and the declared custom types

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
A `reference` field SHALL declare `entity` and `field`, naming a field of another entity in the same spec, and MAY declare `link`, a name following the rules for entity and field names. `field` MAY be the path of a nested field, such as `address.city`, and MAY name an object, in which case the whole object is copied. A path MAY pass through a field of the target that is itself a reference to an object. References SHALL NOT form a cycle between entities, and an entity SHALL NOT reference itself.

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

#### Scenario: Nested target field
- **WHEN** `order.ship_city` declares `entity: customer`, `field: address.city`, and `customer.address` is an object with a field `city`
- **THEN** the field is accepted

#### Scenario: Path through a field that is not an object
- **WHEN** a reference declares `field: id.city` and `customer.id` is not an object
- **THEN** the system rejects it with an error stating that `customer.id` has no field `city`

#### Scenario: Path through a copied object
- **WHEN** `order.ship_to` is a reference to the object `customer.address`, and `invoice.city` declares `entity: order`, `field: ship_to.city`
- **THEN** the field is accepted, whatever order the three entities are declared in

#### Scenario: Reference declared inside an object
- **WHEN** `order.billing` is an object whose field `customer_id` references `customer.id`
- **THEN** the field is accepted, and the entity `order` counts as referencing `customer` for ordering and cycle detection

### Requirement: Null probability
Any field MAY declare `null_probability`, which SHALL be a number between 0 and 1 inclusive and SHALL default to 0 when omitted.

#### Scenario: Out-of-range probability
- **WHEN** a field declares `null_probability: 1.5`
- **THEN** the system rejects it with an error stating the allowed range

### Requirement: Validation reporting
Validation SHALL complete before any data is generated, SHALL report every problem found rather than only the first, and SHALL identify each problem by its location in the spec.

#### Scenario: Multiple problems reported together
- **WHEN** a spec has an invalid range in `entities.order.fields.amount` and an unknown reference in `entities.order.fields.customer_id`
- **THEN** both problems are reported in one validation result, each with its location path

#### Scenario: Invalid spec generates nothing
- **WHEN** a spec fails validation
- **THEN** no rows are generated and no output files are created

### Requirement: Reference shorthand
A field definition written as a string of the form `$<entity>.<field>`, where `<field>` is a field name or a dotted path of field names, SHALL be equivalent to a `reference` mapping with that `entity` and `field` and no other keys. The same validation SHALL apply as for the mapping form, with problems reported at the field's location. A string that is not of this form SHALL be rejected with an error showing the expected form.

#### Scenario: Shorthand is equivalent to the mapping form
- **WHEN** `order.customer_id` is written as `$customer.id`
- **THEN** the spec is accepted and generates the same data, for the same seed, as `{type: reference, entity: customer, field: id}`

#### Scenario: Unknown target in shorthand
- **WHEN** `order.customer_id` is written as `$client.id` and no entity `client` exists
- **THEN** the system rejects it with an error at `entities.order.fields.customer_id` naming the missing entity

#### Scenario: Malformed shorthand
- **WHEN** a field is written as `$customer`, `$customer.`, `$customer..id`, `customer.id` or `$ customer.id`
- **THEN** the system rejects it with an error stating that the expected form is `$entity.field`

#### Scenario: Dollar text elsewhere is literal
- **WHEN** a `constant` field declares `value: "$customer.id"`, or a `choice` field lists `"$5.00"` among its values
- **THEN** the text is kept as written and is not treated as a reference

#### Scenario: Nested path in shorthand
- **WHEN** `order.ship_city` is written as `$customer.address.city`
- **THEN** it is accepted as a reference to the field `address.city` of `customer`

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

### Requirement: Object field definitions
An `object` field SHALL declare `fields`, a mapping of at least one field name to a field definition, following the same rules as an entity's fields. A field inside an object is identified by its path, the field names from the entity down joined by dots, such as `address.city`.

#### Scenario: Object with sub-fields
- **WHEN** `customer.address` declares `type: object` with the fields `city` and `postcode`
- **THEN** the spec is accepted

#### Scenario: Object inside an object
- **WHEN** `customer.address` contains an `object` field `geo` with the fields `lat` and `lon`
- **THEN** the spec is accepted and the inner fields have the paths `address.geo.lat` and `address.geo.lon`

#### Scenario: Object without fields
- **WHEN** an `object` field declares an empty `fields` mapping, or none
- **THEN** the system rejects it with an error stating that at least one field is required

#### Scenario: Same field name at two levels
- **WHEN** an entity has a field `name` and an object `contact` that also has a field `name`
- **THEN** the spec is accepted, and the two fields are distinct with the paths `name` and `contact.name`

#### Scenario: Problem inside an object is located by path
- **WHEN** `customer.address.postcode` declares an unknown key
- **THEN** the error is reported at `entities.customer.fields.address.fields.postcode`

### Requirement: Nesting limit and robust validation
Objects SHALL NOT be nested more than ten levels below an entity. A spec that exceeds the limit SHALL be rejected with a validation problem naming the path at which the limit was exceeded. Validation SHALL always end with either an accepted spec or a list of problems, whatever the structure of the input, including a document in which a mapping contains itself.

#### Scenario: Within the limit
- **WHEN** objects are nested ten levels deep
- **THEN** the spec is accepted

#### Scenario: Beyond the limit
- **WHEN** objects are nested eleven levels deep
- **THEN** the system rejects the spec with an error naming the path and the limit of ten levels

#### Scenario: Document that contains itself
- **WHEN** a YAML spec uses an anchor so that an object's `fields` mapping contains that same mapping
- **THEN** the system rejects the spec with the nesting-limit error, and does not fail in any other way

### Requirement: Pattern field definitions
A `pattern` field SHALL declare `pattern`, a non-empty string in which `#` stands for a digit from 0 to 9, `%` for a digit from 1 to 9 and `?` for an upper-case letter from A to Z. Text between `[` and the next `]` SHALL be literal, which is how a literal `#`, `%` or `?` is written; a literal `[` is written `[[]`. Every other character is literal. A pattern is written identically in YAML and JSON and uses no backslash escapes.

#### Scenario: Phone-like pattern
- **WHEN** a field declares `type: pattern`, `pattern: "+91-%#########"`
- **THEN** the field is accepted

#### Scenario: Literal placeholder characters
- **WHEN** a field declares `pattern: "Item [#]?## at 50[%]"`
- **THEN** the field is accepted, with the `#` and `%` inside brackets treated as literal characters

#### Scenario: Missing or empty pattern
- **WHEN** a `pattern` field declares no `pattern`, or an empty one
- **THEN** the system rejects it with an error stating that a pattern is required

#### Scenario: Unclosed bracket
- **WHEN** a pattern is written as `"Item [#"`
- **THEN** the system rejects it with an error stating that the bracket is not closed

### Requirement: Template field definitions
A `template` field SHALL declare `template`, a non-empty string in which `{path}` is replaced by the value of another field of the same record. A placeholder MAY apply filters, written `{path|filter}` and applied left to right, each one of `lower`, `upper`, `title`, `ascii` or `slug`. A literal brace SHALL be written doubled, as `{{` or `}}`. A template SHALL be parsed by a fixed grammar and SHALL NOT evaluate any part of its text as code.

A placeholder's path SHALL be resolved among the fields of the object, or entity, that directly contains the template, and MAY descend into objects there (`{address.city}`). Each leading `^` SHALL move the starting point one level outward (`{^home.city}`). There SHALL be no other search: a path that does not resolve from its starting point is an error. The path SHALL name a field that is not an object. A template SHALL NOT depend on itself, directly or through other templates.

#### Scenario: Template over sibling fields
- **WHEN** an entity has the fields `first_name` and `last_name`, and `email` declares `template: "{first_name|slug}.{last_name|slug}@example.com"`
- **THEN** the spec is accepted

#### Scenario: Unknown field in a placeholder
- **WHEN** a template uses `{surname}` and no field of that name is beside it
- **THEN** the system rejects it with an error naming `surname`

#### Scenario: No search of outer levels
- **WHEN** a template inside the object `contact` uses `{tier}`, and `tier` is a field of the entity but not of `contact`
- **THEN** the system rejects it with an error naming `tier` and suggesting `{^tier}`

#### Scenario: Reaching outward explicitly
- **WHEN** a template inside the object `contact` uses `{^tier}` and `{^home.city}`, both defined on the entity
- **THEN** the spec is accepted

#### Scenario: Too many levels outward
- **WHEN** a template declared directly on an entity uses `{^tier}`
- **THEN** the system rejects it with an error stating that there is no enclosing level

#### Scenario: Unknown filter
- **WHEN** a template uses `{first_name|reverse}`
- **THEN** the system rejects it with an error naming the filter and listing the supported filters

#### Scenario: Placeholder naming an object
- **WHEN** a template uses `{address}` and `address` is an object
- **THEN** the system rejects it with an error stating that a placeholder must name a field inside the object, such as `{address.city}`

#### Scenario: Attribute access is not a path
- **WHEN** a template uses `{first_name.__class__}` or `{first_name[0]}`
- **THEN** the system rejects it as an unknown field or a malformed placeholder, and evaluates nothing

#### Scenario: Templates that depend on each other
- **WHEN** field `a` is a template using `{b}` and field `b` is a template using `{a}`
- **THEN** the system rejects the spec with an error naming both fields

#### Scenario: Unbalanced braces
- **WHEN** a template is written as `"{first_name"`
- **THEN** the system rejects it with an error stating that the brace is not closed

### Requirement: Hidden fields
Any field written as a mapping MAY declare `hidden: true`. A hidden field SHALL be generated and SHALL be readable by templates and by references, but SHALL NOT appear in records or exported files. Hiding an object hides everything inside it. Every entity, and every object that is not itself hidden, SHALL have at least one field that is not hidden.

#### Scenario: Hidden input of a template
- **WHEN** `first_name` and `last_name` declare `hidden: true` and `email` is a template over them
- **THEN** the spec is accepted

#### Scenario: Hidden field referenced from another entity
- **WHEN** `customer.internal_code` is hidden and `order.customer_code` is `$customer.internal_code`
- **THEN** the spec is accepted

#### Scenario: Everything hidden
- **WHEN** every field of an entity declares `hidden: true`
- **THEN** the system rejects it with an error stating that at least one field must be visible

#### Scenario: Value that is not a boolean
- **WHEN** a field declares `hidden: "yes"`
- **THEN** the system rejects it with an error stating that `hidden` must be true or false

### Requirement: Unique fields
A field of type `integer`, `float`, `date`, `datetime`, `choice` or `pattern` MAY declare `unique: true`. `sequence` and `uuid` fields, whose values are always unique, SHALL accept the key with no effect. Every other type SHALL reject it. Where the number of distinct values a unique field can produce is known, a spec whose entity `count` exceeds that number SHALL be rejected, with the error stating both numbers.

#### Scenario: Unique pattern
- **WHEN** a field declares `type: pattern`, `pattern: "SKU-??-####"`, `unique: true` in an entity with `count: 1000`
- **THEN** the spec is accepted, since the pattern has 6,760,000 possible values

#### Scenario: More rows than values
- **WHEN** a field declares `type: integer`, `min: 1`, `max: 100`, `unique: true` in an entity with `count: 500`
- **THEN** the system rejects it with an error stating that the field can produce 100 distinct values and 500 are needed

#### Scenario: Unique choice
- **WHEN** a `choice` field with four distinct values declares `unique: true` in an entity with `count: 5`
- **THEN** the system rejects it with an error stating that the field can produce 4 distinct values

#### Scenario: Type that cannot be unique
- **WHEN** a `boolean`, `constant`, `template`, `reference` or `object` field declares `unique: true`
- **THEN** the system rejects it with an error stating that `unique` is not supported for that type

#### Scenario: Unbounded field
- **WHEN** a `float` field without `precision` declares `unique: true`
- **THEN** the spec is accepted without a capacity check

### Requirement: Custom types
A spec MAY declare `types`, a mapping of type name to field definition written as a mapping. A type name SHALL follow the rules for entity and field names. A field MAY use the name as its `type`, and SHALL behave as if the type's definition had been written in its place. Keys declared at the point of use SHALL replace the same keys of the definition and SHALL be valid for the definition's own type; for an object type, `fields` at the point of use SHALL replace or add sub-fields by name. A custom type MAY use other custom types, but SHALL NOT depend on itself.

A custom type whose name is also the name of a built-in type SHALL take precedence over the built-in throughout the spec; within its own definition, that name SHALL denote the built-in.

Every declared type SHALL be validated for structure whether or not a field uses it. A template inside an object type whose placeholders stay within that type SHALL also be checked at the declaration. Checks that depend on where a type is used SHALL be made at each point of use, with the type named in the error.

#### Scenario: Declaring and using a type
- **WHEN** a spec declares `types: {indian_mobile: {type: pattern, pattern: "+91-%#########"}}` and a field declares `type: indian_mobile`
- **THEN** the spec is accepted and the field behaves as that pattern field

#### Scenario: Object as a custom type
- **WHEN** a type `money` is declared as an object with the fields `amount` and `currency`, and two fields in different entities declare `type: money`
- **THEN** both fields are objects with those two sub-fields

#### Scenario: Overriding a key at the point of use
- **WHEN** a field declares `type: indian_mobile`, `unique: true`, `null_probability: 0.1`
- **THEN** it behaves as the pattern with those two keys applied

#### Scenario: Overriding a sub-field of an object type
- **WHEN** a field declares `type: money`, `fields: {currency: {type: constant, value: USD}}`
- **THEN** it is the `money` object with its `currency` replaced and its `amount` unchanged

#### Scenario: Key that the underlying type does not accept
- **WHEN** a field declares `type: indian_mobile` together with `min: 1`
- **THEN** the system rejects it with an error naming the key and the underlying type `pattern`

#### Scenario: Type built on another type
- **WHEN** type `contact` is an object whose field `mobile` declares `type: indian_mobile`
- **THEN** the spec is accepted

#### Scenario: Types that depend on each other
- **WHEN** type `a` uses type `b` and type `b` uses type `a`
- **THEN** the system rejects the spec with an error naming both types

#### Scenario: Custom type named like a built-in
- **WHEN** a spec declares a type `integer` as `{type: integer, min: 0, max: 9}` and a field declares `type: integer` with no other keys
- **THEN** the spec is accepted, the field takes the range 0 to 9, and the definition itself refers to the built-in `integer`

#### Scenario: Problem in an unused type
- **WHEN** a declared type has an unknown key and no field uses it
- **THEN** the system rejects the spec with the problem located at `types.<name>`

#### Scenario: Self-contained template in an object type
- **WHEN** type `person` is an object with `first_name` and an `email` template using `{surname}`, which the object does not define
- **THEN** the system rejects the spec with the problem located at `types.person.fields.email`

#### Scenario: Check that depends on the point of use
- **WHEN** type `greeting` is a template using `{first_name}` and a field uses it in an entity that has no `first_name`
- **THEN** the system rejects the spec at that field, with an error naming the type `greeting` and the missing field
