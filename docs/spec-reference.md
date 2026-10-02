# Spec reference

A simulation spec is a YAML (`.yaml`, `.yml`) or JSON (`.json`) file. Both formats mean exactly the same thing; the examples here use YAML.

Several things can be written two ways: a **long form**, where everything is spelled out as keys, and a **shorthand**, which says the same thing in one string. They are interchangeable and can be mixed freely in one spec. Where both exist, this page shows them next to each other.

- [Document](#document)
- [Entities](#entities)
- [Long form and shorthand at a glance](#long-form-and-shorthand-at-a-glance)
- [Field types](#field-types)
- [Realistic data](#realistic-data)
- [Locale](#locale)
- [Keys every field accepts](#keys-every-field-accepts)
- [Custom types](#custom-types)
- [Nulls](#nulls)
- [References](#references)
- [Reproducibility](#reproducibility)
- [Output](#output)
- [Validation](#validation)
- [Things to know about YAML](#things-to-know-about-yaml)
- [Current limits](#current-limits)

## Document

```yaml
version: 1          # required, must be 1
seed: 42            # optional, non-negative integer
locale: en_IN       # optional, for names, phones and addresses; see Locale
output:             # optional
  format: csv       # csv, json or jsonl
  dir: output/shop  # relative paths resolve against the current working directory
  csv_separator: .  # . or __ ; joins the parts of a nested column name in CSV
types:              # optional, reusable field definitions; see Custom types
  sku: {type: pattern, pattern: "SKU-??-####"}
entities:           # required, at least one
  customer:
    count: 1000
    fields:
      id: {type: sequence}
```

Any key not described on this page is rejected, so a typo such as `cout` for `count` is reported instead of ignored.

## Entities

| Key | Required | Meaning |
|---|---|---|
| `count` | yes | Number of rows to generate. An integer of 1 or more. |
| `fields` | yes | Field name to field definition. At least one. Fields appear in the output in this order. |

Entity and field names start with a letter or underscore and contain only letters, digits and underscores. The entity name becomes the output file name.

A field definition is either a mapping with a `type`, or a `$entity.field` reference string.

## Long form and shorthand at a glance

| What | Long form | Shorthand |
|---|---|---|
| Reference | `{type: reference, entity: customer, field: id}` | `$customer.id` |
| Weighted choice | `values: [free, pro]` with `weights: [70, 30]` | `values: [free \|\| 70, pro \|\| 30]` |
| Null as a weighted choice | `values: [A, null]` with `weights: [1, 4]` | `values: [A \|\| 1, " \|\| 4"]` |
| Typed weighted choice | `values: [0, 1, 2]` with `weights: [80, 15, 5]` | `value_type: integer` with `values: [0 \|\| 80, 1 \|\| 15, 2 \|\| 5]` |
| Weighted range | `{min: 18, max: 35, weight: 0.7}` | `18 to 35 \|\| 0.7` |

Everything else (`min` and `max`, distributions, dates, sequences, constants, objects, `null_probability`, `link`) has only the long form.

## Field types

Every mapping field has a `type`: one of the built-in types below, or the name of a [custom type](#custom-types). Each type accepts only its own keys, plus the [keys every field accepts](#keys-every-field-accepts).

### `integer` and `float`

Describe the values in one of two ways: a single range, or weighted ranges.

**A single range**, with an optional distribution:

```yaml
age:    {type: integer, min: 18, max: 90}
height: {type: float, distribution: normal, mean: 170, stddev: 10, min: 140, max: 210}
```

| Key | Meaning |
|---|---|
| `min`, `max` | Inclusive bounds. Required for `uniform`, optional for `normal`. |
| `distribution` | `uniform` (default) or `normal`. |
| `mean`, `stddev` | Required for `normal`. `stddev` must be greater than zero. |

A `normal` field with bounds never produces a value outside them.

**Weighted ranges**, where each range is picked with a probability proportional to its weight and the value is uniform within it.

Long form:

```yaml
age:
  type: integer
  ranges:
    - {min: 18, max: 35, weight: 0.7}
    - {min: 36, max: 60, weight: 0.25}
    - {min: 61, max: 90, weight: 0.05}
```

Shorthand:

```yaml
age:
  type: integer
  ranges: [18 to 35 || 0.7, 36 to 60 || 0.25, 61 to 90 || 0.05]
```

Rules for the shorthand, `min to max || weight`:

- `to` needs a space on each side. Spaces around `||` are optional.
- Bounds are plain decimal numbers with an optional minus sign: `-10.5 to -0.5 || 1`. A leading-dot decimal such as `.9` is accepted; exponents such as `1e3` are not.
- Strings and mappings can be mixed in one list.

Rules for both forms:

- Weights are relative: `70, 25, 5` means the same as `0.7, 0.25, 0.05`. They must be non-negative and sum to more than zero. A range with weight 0 is never used.
- `ranges` cannot be combined with `min`, `max`, `distribution`, `mean` or `stddev`.
- `integer` fields require whole-number bounds.

`float` fields also accept:

| Key | Meaning |
|---|---|
| `precision` | Number of decimal places to round to. A non-negative integer. |

### `boolean`

```yaml
opted_in: {type: boolean, true_probability: 0.3}
```

| Key | Meaning | Default |
|---|---|---|
| `true_probability` | Chance of `true`, from 0 to 1. | 0.5 |

### `choice`

Picks one of a list of values. Without weights every value is equally likely:

```yaml
country: {type: choice, values: [IN, US, GB, DE]}
```

**Weighted values.**

Long form, with a `weights` list matching `values` one to one:

```yaml
tier:
  type: choice
  values: [free, pro, enterprise]
  weights: [70, 25, 5]
```

Shorthand, with each weight written after its value:

```yaml
tier:
  type: choice
  values: [free || 70, pro || 25, enterprise || 5]
```

**Null as one of the values.** A null entry makes the field null for that share of rows.

Long form:

```yaml
referral_code:
  type: choice
  values: [FRIEND10, LAUNCH25, PARTNER, null]
  weights: [0.2, 0.2, 0.1, 0.5]
```

Shorthand, where an empty value means null:

```yaml
referral_code:
  type: choice
  values: [FRIEND10 || 0.2, LAUNCH25 || 0.2, PARTNER || 0.1, " || 0.5"]
```

**Typed values.** In the long form, values keep the type they are written with. In the shorthand a value is text unless the field declares `value_type`.

Long form:

```yaml
gift_wrap_level:
  type: choice
  values: [0, 1, 2]
  weights: [80, 15, 5]
```

Shorthand:

```yaml
gift_wrap_level:
  type: choice
  value_type: integer
  values: [0 || 80, 1 || 15, 2 || 5]
```

| Key | Meaning |
|---|---|
| `values` | Required. A non-empty list of strings, numbers, booleans or nulls, or of `value \|\| weight` strings. |
| `weights` | Optional, long form only. One weight per value. |
| `value_type` | Optional, shorthand only. `string` (default), `integer`, `float` or `boolean`. |

Rules for the shorthand, `value || weight`:

- Either every entry carries a weight, or none does.
- The entry is split on its last `||`, so `a || b || 0.5` is the value `a || b` with weight 0.5. Spaces around the value and the weight are ignored.
- The weight is a plain non-negative number. `20%` is not accepted.
- Without `value_type`, `10 || 0.5` is the text `10`, not the number 10. With `value_type`, every value must fit the type: `integer` takes digits with an optional minus sign, `float` a plain decimal number, `boolean` exactly `true` or `false`. An empty value is null under every type.
- Values are matched against fixed patterns and never evaluated as code.
- When `weights` is declared, every entry is taken literally. That is how to write values that really contain `||`:

```yaml
operator: {type: choice, values: ["a || b", "a && b"], weights: [1, 1]}
```

### `date` and `datetime`

```yaml
signup_date: {type: date, min: 2022-01-01, max: 2025-12-31}
placed_at:   {type: datetime, min: 2025-01-01T00:00:00, max: 2025-12-31T23:59:59}
```

`min` and `max` are required ISO 8601 values and are inclusive. Dates are spread evenly by day, date-times by second. If one bound of a `datetime` has a timezone offset, the other must too.

### `sequence`

```yaml
id: {type: sequence, start: 1001, step: 1}
```

| Key | Meaning | Default |
|---|---|---|
| `start` | Value of the first row. An integer. | 1 |
| `step` | Added for each following row. A non-zero integer. | 1 |

### `uuid`

```yaml
id: {type: uuid}
```

A version 4 UUID, unique within the entity and reproducible for a given seed. Takes no options.

### `constant`

```yaml
currency: {type: constant, value: EUR}
```

The same `value` (a string, number, boolean or null) in every row. A value starting with `$`, such as `"$5.00"`, is plain text here.

### `object`

Groups fields into a nested record. An object has its own `fields`, written exactly like an entity's, and objects can contain objects.

```yaml
address:
  type: object
  fields:
    city: {type: choice, values: [Pune, Austin, Leeds]}
    postcode: {type: integer, min: 10000, max: 99999}
    geo:
      type: object
      fields:
        lat: {type: float, min: -90, max: 90, precision: 4}
        lon: {type: float, min: -180, max: 180, precision: 4}
```

| Key | Required | Meaning |
|---|---|---|
| `fields` | yes | Field name to field definition. At least one. |

- A field inside an object is identified by its **path**: `address.city`, `address.geo.lat`. Paths are used in references, in CSV column names and in error locations.
- The same field name can be used at different levels; `name` and `contact.name` are different fields.
- `null_probability` on an object makes the whole object null. Its fields are then not generated at all.
- Objects can be nested up to ten levels deep.

### `pattern`

Builds text from a mask.

```yaml
mobile: {type: pattern, pattern: "+91-%#########"}
sku:    {type: pattern, pattern: "SKU-??-####"}
label:  {type: pattern, pattern: "Item [#]## at 50[%]"}
```

| In the pattern | Produces |
|---|---|
| `#` | a digit, 0 to 9 |
| `%` | a digit, 1 to 9 (for a position that must not be zero) |
| `?` | an upper-case letter, A to Z |
| `[text]` | `text` exactly as written, which is how a literal `#`, `%` or `?` is written |
| `[[]` | a literal `[` |
| anything else | itself |

There are no backslash escapes, so a pattern is written the same way in YAML and JSON. Random letters can spell words; use digits, or a `choice` for the letters, where that matters.

### `template`

Builds text from other fields of the same record.

```yaml
first_name: {type: choice, values: [Asha, Ravi, Meera]}
last_name:  {type: choice, values: [Rao, Nair, Smith]}
email:      {type: template, template: "{first_name|slug}.{last_name|slug}@example.com"}
```

A placeholder is `{field}`, optionally followed by filters, applied left to right:

| Filter | Effect | `José De La Cruz` becomes |
|---|---|---|
| `lower` | lower case | `josé de la cruz` |
| `upper` | upper case | `JOSÉ DE LA CRUZ` |
| `title` | first letter of each word in upper case | `José De La Cruz` |
| `ascii` | accents removed, other non-ASCII characters dropped | `Jose De La Cruz` |
| `slug` | `ascii`, lower case, and every run of other characters turned into one hyphen | `jose-de-la-cruz` |

Rules:

- **Scope is explicit.** A placeholder reads the fields beside the template: the other fields of the same entity or object. It can go down into an object beside it (`{address.city}`). To read a field one level further out, start with `^` (`{^tier}`); two levels, `^^`. Nothing else is searched, so adding a field elsewhere never changes what a template reads.
- A placeholder must name a single value, not an object.
- If any field a template reads is null, the template is null.
- Numbers are written plainly, booleans as `true` or `false`, dates in ISO 8601.
- A literal brace is written doubled: `{{` and `}}`.
- Templates can read other templates, in any declared order, but not in a circle.
- A template is plain text with placeholders. Nothing in it is evaluated.

Inside an object, with a field from the level above:

```yaml
tier: {type: choice, values: [free, pro]}
contact:
  type: object
  fields:
    phone: {type: pattern, pattern: "+91-%#########"}
    label: {type: template, template: "{phone} ({^tier})"}
```

### `reference`

See [References](#references).

## Realistic data

These types produce names, contact details and addresses without any lists from you. They come in two groups: built-in types backed by data bundled with dataspecter for India (`en_IN`) and the United States (`en_US`), and the optional `faker` type for everything else.

```yaml
name:   {type: full_name}
first:  {type: first_name}
last:   {type: last_name}
email:  {type: email}
mobile: {type: phone}
home:   {type: address}
```

| Type | Produces | Options | `unique` |
|---|---|---|---|
| `first_name` | a given name | `locale` | yes, up to the number of bundled names |
| `last_name` | a family name | `locale` | yes, up to the number of bundled names |
| `full_name` | a given and a family name | `locale`, `format` | yes, up to their product |
| `email` | an email address | `locale`, `domain` | yes |
| `phone` | a phone number, as text | `locale`, `pattern` | yes, up to what the format allows |
| `address` | an object: `street`, `city`, `state`, `postcode`, `country` | `locale`, `fields` | no |

### Names

```yaml
name:   {type: full_name}
formal: {type: full_name, format: last_first}
```

`format` is `first_last` (the default, `Asha Rao`) or `last_first` (`Rao, Asha`). Names are chosen uniformly from the bundled lists; they do not follow the frequencies of a real population.

### `email`

```yaml
email:      {type: email}
work_email: {type: email, domain: acme.test, unique: true}
```

By default the domain is `example.com`, `example.org` or `example.net`. Those domains are reserved for documentation, so a generated address can never reach a real mailbox. Set `domain` to use your own.

The address is generated on its own and does not match a name field beside it. For an email built from the record's own name, use a template; `slug` keeps it valid whatever the name contains:

```yaml
first_name: {type: first_name}
last_name:  {type: last_name}
email:      {type: template, template: "{first_name|slug}.{last_name|slug}@example.com"}
```

### `phone`

```yaml
mobile:      {type: phone}
test_mobile: {type: phone, pattern: "+91-99999-#####"}
```

| Locale | Format | Can it be a real number? |
|---|---|---|
| `en_US` | `+1-NXX-555-01XX` | No. 555-0100 to 555-0199 is reserved for fiction. This limits the format to 80,000 distinct numbers. |
| `en_IN` | `+91-` and ten digits starting 6 to 9 | **Yes.** India has no range reserved for test numbers, so some generated numbers belong to real people. |

Never send messages or place calls to generated numbers. If your team has a prefix it knows to be safe, set `pattern`, which takes the same syntax as the [`pattern`](#pattern) type and replaces the locale's format.

### `address`

```yaml
home:    {type: address}
billing: {type: address, fields: [city, postcode]}
```

An address is an object, so it behaves like any [`object`](#object): JSON nests it, CSV writes `home.street`, `home.city` and so on, a template can read `{home.city}`, and a reference can read `$customer.home.city` or copy `$customer.home` whole.

- `fields` selects which of the five fields to include, in the order listed.
- The state is the one the city is in, and the postcode starts with a prefix that belongs to the city. The remaining digits are random, so a full postcode may not be one in use.
- The street is a house number and a common street name; it is not a real address.
- Every field is text. A United States ZIP code beginning with 0 keeps its zero.

### `faker`

For other locales, and for data the built-ins do not cover (companies, job titles, and much else), the `faker` type calls a provider of the [Faker](https://faker.readthedocs.io) library.

```yaml
company: {type: faker, provider: company}
city:    {type: faker, provider: city, locale: de_DE}
joined:  {type: faker, provider: date_between, args: {start_date: "-30d", end_date: today}}
```

| Key | Required | Meaning |
|---|---|---|
| `provider` | yes | The name of a Faker provider method. |
| `locale` | no | Any locale Faker supports. Defaults to the locale in force. |
| `args` | no | Keyword arguments for the provider. |

Faker is optional. Install it with `pip install faker`, or as the extra `pip install "dataspecter[faker]"` once dataspecter is installed from a package index. Without it, a spec that uses the `faker` type is rejected with that instruction; every other spec works as before.

What a spec can and cannot do through this type:

- **Only providers can be called.** `provider` must be a method that one of Faker's providers defines. Names beginning with an underscore, and methods of the Faker object itself such as `seed_instance`, are refused.
- **Only plain arguments.** Each argument is text, a number, a boolean, null, or a list of those.
- **Only single values come back.** Text, numbers, booleans, dates and date-times. A provider that returns a structure or bytes, such as `profile`, is rejected.
- The provider is tried once when the spec is validated, so wrong arguments are reported before generation starts. Every generated value is checked as well.
- `unique: true` is supported; if the provider runs out of new values, generation stops with an error.

Faker values are reproducible for a given seed **and a given Faker version**: Faker's data changes between releases. Faker is also much slower than the built-in types.

## Locale

The locale decides which country's names, phone format and addresses the built-in types use, and is the default for `faker` fields. It is resolved per field, highest first:

1. `locale` on the field
2. `--locale` on the command line, or the `locale` argument of `load_spec`
3. `locale` at the top of the spec
4. `en_US`

```yaml
version: 1
locale: en_IN
entities:
  customer:
    count: 100
    fields:
      name: {type: full_name}
      mobile: {type: phone}
      us_office: {type: phone, locale: en_US}
```

The spec-level value can be any locale code of the form `ll_CC`. Whether it can be used is decided field by field: a built-in type needs `en_IN` or `en_US` and is rejected otherwise, with a pointer to `faker`; a `faker` field needs a locale Faker supports.

## Keys every field accepts

| Key | Meaning | Default |
|---|---|---|
| `null_probability` | Share of rows that are null. See [Nulls](#nulls). | 0 |
| `hidden` | Generate the field but leave it out of the output. | false |
| `unique` | Never repeat a value within the entity. Not every type supports it. | false |

These need the mapping form; a `$entity.field` shorthand takes no keys.

### `hidden`

A hidden field is generated, and templates and references can read it, but it does not appear in records or files. Use it for the ingredients of a template that should not be columns themselves:

```yaml
id:         {type: sequence}
first_name: {type: choice, values: [Asha, Ravi, Meera], hidden: true}
last_name:  {type: choice, values: [Rao, Nair, Smith], hidden: true}
email:      {type: template, template: "{first_name|slug}.{last_name|slug}@example.com"}
```

The output has two columns, `id` and `email`. Hiding an object hides everything inside it. Every entity, and every object that is not hidden, needs at least one visible field. Adding or removing `hidden` never changes any generated value.

### `unique`

```yaml
code: {type: pattern, pattern: "SKU-??-####", unique: true}
```

| Type | `unique` |
|---|---|
| `integer`, `float`, `date`, `datetime`, `choice`, `pattern` | supported |
| `sequence`, `uuid` | accepted, and has no effect: their values are always unique |
| `boolean`, `constant`, `template`, `reference`, `object` | rejected |

- Where the number of possible values is known, a spec is rejected before generation if the entity has more rows than the field has values. `{type: integer, min: 1, max: 100, unique: true}` in an entity with `count: 500` is an error stating both numbers.
- Fields with no fixed number of values (a `float` without `precision`, an unbounded `normal` integer) are accepted. If generation cannot find an unused value, it stops with an error naming the field; it never writes a repeat.
- Nulls from `null_probability` are not values and may repeat.
- To make a template unique, make one of the fields it reads unique.
- A unique field remembers every value it has produced until the run ends. This is the one place memory grows with the number of rows: roughly 100 MB for a million ten-character values.

## Custom types

A field definition used in several places can be named once in a top-level `types` block and then used as a `type`:

```yaml
version: 1
types:
  mobile: {type: pattern, pattern: "+91-%#########"}
  money:
    type: object
    fields:
      amount: {type: float, min: 5, max: 500, precision: 2}
      currency: {type: constant, value: INR}
  person:
    type: object
    fields:
      first_name: {type: choice, values: [Asha, Ravi, Meera]}
      last_name: {type: choice, values: [Rao, Nair, Smith]}
      email: {type: template, template: "{first_name|slug}.{last_name|slug}@example.com"}
      mobile: {type: mobile}
entities:
  customer:
    count: 1000
    fields:
      id: {type: sequence}
      contact: {type: person}
      backup_mobile: {type: mobile, null_probability: 0.7}
  product:
    count: 50
    fields:
      price: {type: money}
      price_usd:
        type: money
        fields:
          currency: {type: constant, value: USD}
```

- A field using a type behaves exactly as if the definition were written in its place. Two fields using the same type get independent values.
- A type can be any definition, including an object, and can use other types, but not in a circle.
- **Overrides.** Keys written beside `type` replace the same keys of the definition, as with `null_probability` on `backup_mobile`. They must be keys the underlying type accepts. For an object type, `fields` is merged by name, so `price_usd` replaces `currency` and keeps `amount`.
- **Templates in types.** A template inside an object type reads the fields of that object, so the type is self-contained and is checked where it is declared. A type that is itself a template, or one using `^`, is checked wherever it is used.
- **Name precedence.** If a custom type has the same name as a built-in type, the custom type wins everywhere in the spec, and inside its own definition the name means the built-in. So `integer: {type: integer, min: 0, max: 9}` narrows every `type: integer` in the spec. This rule exists so that built-in types added in later versions never break a spec that already uses the name; a `type: integer` that is not the built-in can surprise a reader, so shadow a built-in on purpose only.
- Every declared type is validated, whether or not a field uses it. A problem in a type is reported at `types.<name>`; a problem that depends on where it is used is reported at that field and names the type.

## Nulls

Any mapping field can be null some of the time:

```yaml
referral_code: {type: choice, values: [FRIEND10, LAUNCH25], null_probability: 0.8}
```

`null_probability` is a number from 0 to 1 and defaults to 0. The null decision is made first and independently for each row; the rows that are not null then follow the field's own rules. In the example, 80% of rows are null and the remaining 20% are split evenly between the two codes, so each code appears in about 10% of rows.

A `choice` field has a second way to produce nulls: a null entry with its own weight, shown [above](#choice). Use whichever reads better. If a field has both, they combine: with `null_probability: 0.5` and a null entry weighted at half the values, 75% of rows are null.

## References

A reference takes its value from a row of another entity.

Long form:

```yaml
version: 1
entities:
  customer:
    count: 1000
    fields:
      id: {type: sequence, start: 1001}
  order:
    count: 5000
    fields:
      customer_id: {type: reference, entity: customer, field: id}
```

Shorthand, where the whole field definition is `$entity.field`:

```yaml
version: 1
entities:
  customer:
    count: 1000
    fields:
      id: {type: sequence, start: 1001}
  order:
    count: 5000
    fields:
      customer_id: $customer.id
```

| Key (long form) | Required | Meaning |
|---|---|---|
| `entity` | yes | The entity to read from. |
| `field` | yes | The field of that entity to copy. |
| `link` | no | A name for the row choice. See below. |

The shorthand has no options. A reference that needs `null_probability` or `link` uses the long form.

### Copying several values from the same row

For each row, one row of the target entity is chosen, every target row being equally likely, and **every reference to that entity reads from that same row**. So an order item can carry a product's id and that same product's price:

```yaml
version: 1
entities:
  product:
    count: 50
    fields:
      id: {type: sequence}
      price: {type: float, min: 5, max: 200, precision: 2}
  order_item:
    count: 12000
    fields:
      product_id: $product.id
      unit_price: $product.price
```

`null_probability` still applies to each field on its own, so one copied value can be null while another from the same row is not.

### Choosing rows independently with `link`

When one entity needs two unrelated rows of the same target, give the references different `link` names. References with the same link share a row; references with different links, or with none, choose independently.

```yaml
version: 1
entities:
  account:
    count: 100
    fields:
      id: {type: sequence}
      name: {type: uuid}
  transfer:
    count: 1000
    fields:
      sender_id:   {type: reference, entity: account, field: id, link: sender}
      sender_name: {type: reference, entity: account, field: name, link: sender}
      receiver_id: {type: reference, entity: account, field: id, link: receiver}
```

Here `sender_id` and `sender_name` describe one account, and `receiver_id` another. A link name belongs to one target entity: the same name used on references to two different entities denotes two unrelated choices.

### Reading nested fields

A reference can name a path inside an object, or the object itself, which copies the whole object:

```yaml
version: 1
entities:
  customer:
    count: 1000
    fields:
      id: {type: sequence, start: 1001}
      address:
        type: object
        fields:
          city: {type: choice, values: [Pune, Austin, Leeds]}
          postcode: {type: integer, min: 10000, max: 99999}
  order:
    count: 5000
    fields:
      customer_id: $customer.id
      ship_city: $customer.address.city
      ship_to: $customer.address
```

All three order fields read from the same customer. In the long form the path goes in `field`: `{type: reference, entity: customer, field: address.city}`.

- If an object along the path is null in the chosen row, the reference is null.
- A path can pass through an object that was itself copied: with the spec above, another entity could use `$order.ship_to.city`.
- Each record gets its own copy of a copied object.
- A reference can be declared inside an object. It still shares its row with the entity's other references to the same target.

### Other rules

- Entities can be declared in any order; they are generated parents first.
- References can chain (`order_item` → `order` → `customer`), and a reference can copy a field that is itself a reference.
- An entity cannot reference itself, and references cannot form a cycle.

## Reproducibility

The same spec and seed always produce the same data. The seed comes from `--seed` (or the `seed` argument in Python) if given, otherwise from the spec. With neither, a seed is chosen and reported so the run can be repeated.

Each field draws from its own random stream, and each link has its own row choice, so for a fixed seed, adding, removing or reordering other fields or entities does not change the values a field already had. Adding a second reference to an entity leaves the first unchanged. The same holds for fields inside an object.

One exception: changing an object's `null_probability` changes the values of the fields inside it, because they are only generated for rows where the object is present.

The long form and the shorthand of the same spec generate identical data.

Reproducibility is guaranteed within one dataspecter version.

## Output

One file per entity, named `<entity>.<format>`, written to the output directory. The directory is created if needed and existing files are replaced. Files are UTF-8 with `\n` line endings on every platform.

| Format | Shape | Null | Boolean | Date and date-time |
|---|---|---|---|---|
| `csv` | Header row, then one line per row. Quoted as needed (RFC 4180). | empty field | `true` / `false` | ISO 8601 |
| `json` | One array of objects. | `null` | `true` / `false` | ISO 8601 string |
| `jsonl` | One object per line. | `null` | `true` / `false` | ISO 8601 string |

The format and directory come from the command line or function arguments if given, otherwise from the spec's `output` block, otherwise `csv` in `output`.

### Nested records

| Format | An object | A null object |
|---|---|---|
| `json`, `jsonl` | a nested object | `null` |
| `csv` | one column per field inside it, named by path | every one of its columns empty |

An entity with `id`, an `address` object holding `city` and `postcode`, and `tier` is written to CSV with this header:

```
id,address.city,address.postcode,tier
```

- CSV cannot tell a null object from an object whose fields are all null: both are empty cells. Use `json` or `jsonl` where the difference matters, or for deeply nested data.
- Some loaders reject dots in column names. `output.csv_separator: "__"` names the column `address__city` instead. A spec is rejected if two columns would then share a name.
- The separator does not affect JSON output.

## Validation

A spec is validated completely before anything is generated. Every problem is reported, each with its location:

```
error: shop.yaml is not a valid spec (2 problem(s))
  entities.order.fields.amount: min must not exceed max
  entities.order.fields.customer_id: unknown entity 'client'; entities in this spec: order, customer
```

Problems in a shorthand are reported against the entry as written, such as `entities.customer.fields.age.ranges[1]`.

Values are not coerced in the long form: `min: "18"` is rejected for a number, and `true` is not accepted as `1`.

## Things to know about YAML

- A shorthand entry that starts with a space or with `|` must be quoted, because YAML reads a leading `|` as the start of a text block. In practice that is the null entry: write `" || 0.5"`, not `|| 0.5`. Other entries need no quotes.
- `$customer.id` needs no quotes.
- Unquoted `yes`, `no`, `on` and `off` are booleans in YAML. In a `choice` list, quote them if you mean text: `values: ["NO", "SE", "DK"]`.
- Dates do not need quotes: `min: 2024-01-01` and `min: "2024-01-01"` are the same.
- In JSON every shorthand is an ordinary string: `"customer_id": "$customer.id"`, `"values": ["free || 70", "pro || 30"]`.

## Current limits

- A field cannot hold a list.
- References with different links choose independently, so they can land on the same row. With 100 accounts, about one transfer in 100 has the same sender and receiver.
- Reference rows are chosen uniformly, so the number of children per parent cannot be controlled.
- Apart from templates there are no rules across fields (such as one date falling after another).
- The built-in realistic types cover `en_IN` and `en_US` only, choose names uniformly, and do not correlate with each other: a phone's area code is unrelated to the address beside it.
- `unique` applies to one field within one entity; a combination of fields cannot be declared unique.
- Custom types cannot be shared between spec files.
- The values of referenced fields are held in memory while their children are generated; everything else is streamed.
