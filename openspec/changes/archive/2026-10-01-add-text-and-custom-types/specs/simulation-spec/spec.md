# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

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
