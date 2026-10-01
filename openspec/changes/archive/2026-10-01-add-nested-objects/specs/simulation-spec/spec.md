# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Spec structure
A spec SHALL contain `version` and `entities`, and MAY contain `seed` and `output`. `version` SHALL be `1`. `entities` SHALL be a mapping of at least one entity name to an entity definition. Each entity definition SHALL contain `count`, an integer of 1 or more, and `fields`, a mapping of at least one field name to a field definition. `seed`, when present, SHALL be a non-negative integer. `output`, when present, MAY contain `format`, `dir` and `csv_separator`; `csv_separator` SHALL be `.` or `__`. Entity and field names SHALL start with a letter or underscore and contain only letters, digits and underscores. Any key the format does not define SHALL be rejected.

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

### Requirement: Field types
Every field definition SHALL be either a mapping that declares a `type`, or a reference shorthand string. `type` SHALL be one of `integer`, `float`, `boolean`, `choice`, `date`, `datetime`, `sequence`, `uuid`, `constant`, `reference` or `object`. Each type SHALL accept only the keys defined for it.

#### Scenario: Unknown field type
- **WHEN** a field declares `type: email`
- **THEN** the system rejects it with an error that lists the supported types

#### Scenario: Key that does not belong to the type
- **WHEN** a `boolean` field also declares `min: 1`
- **THEN** the system rejects it with an error naming the key `min`

#### Scenario: Definition that is neither a mapping nor a reference
- **WHEN** a field is defined as the number `42` or as a list
- **THEN** the system rejects it with an error stating that a field must be a mapping with a `type` or a `$entity.field` reference

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
