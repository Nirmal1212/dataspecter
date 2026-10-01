# Spec reference

A simulation spec is a YAML (`.yaml`, `.yml`) or JSON (`.json`) file. Both formats mean exactly the same thing; the examples here use YAML.

- [Document](#document)
- [Entities](#entities)
- [Field types](#field-types)
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
output:             # optional
  format: csv       # csv, json or jsonl
  dir: output/shop  # relative paths resolve against the current working directory
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

## Field types

Every field has a `type`. Each type accepts only its own keys, plus `null_probability`.

### `integer` and `float`

Describe the values in one of two ways.

**A single range**, with an optional distribution:

```yaml
age:    {type: integer, min: 18, max: 90}                                  # uniform
height: {type: float, distribution: normal, mean: 170, stddev: 10, min: 140, max: 210}
```

| Key | Meaning |
|---|---|
| `min`, `max` | Inclusive bounds. Required for `uniform`, optional for `normal`. |
| `distribution` | `uniform` (default) or `normal`. |
| `mean`, `stddev` | Required for `normal`. `stddev` must be greater than zero. |

A `normal` field with bounds never produces a value outside them.

**Weighted ranges**, where each range is picked with a probability proportional to its weight and the value is uniform within it:

```yaml
age:
  type: integer
  ranges:
    - {min: 18, max: 35, weight: 0.7}
    - {min: 36, max: 60, weight: 0.25}
    - {min: 61, max: 90, weight: 0.05}
```

Weights are relative: `70, 25, 5` means the same as `0.7, 0.25, 0.05`. They must be non-negative and sum to more than zero. A range with weight 0 is never used. `ranges` cannot be combined with `min`, `max`, `distribution`, `mean` or `stddev`.

`integer` fields require whole-number bounds. `float` fields also accept:

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

```yaml
tier: {type: choice, values: [free, pro, enterprise], weights: [70, 25, 5]}
```

| Key | Meaning |
|---|---|
| `values` | Required. A non-empty list of strings, numbers or booleans. |
| `weights` | Optional. One weight per value, following the same rules as range weights. Without it every value is equally likely. |

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

The same `value` (a string, number, boolean or null) in every row.

### `reference`

```yaml
customer_id: {type: reference, entity: customer, field: id}
```

See [References](#references).

## Nulls

Any field can be null some of the time:

```yaml
referral_code: {type: choice, values: [FRIEND10, LAUNCH25], null_probability: 0.8}
```

`null_probability` is a number from 0 to 1 and defaults to 0. The null decision is made first and independently for each row; the non-null rows then follow the field's own rules. In the example, 80% of rows are null and the remaining 20% are split evenly between the two codes, so each code appears in about 10% of rows.

## References

A `reference` field takes each of its values from the values generated for a field of another entity, every row of that entity being equally likely.

```yaml
entities:
  order:
    count: 5000
    fields:
      customer_id: {type: reference, entity: customer, field: id}
  customer:
    count: 1000
    fields:
      id: {type: sequence, start: 1001}
```

- Entities can be declared in any order; they are generated parents first.
- References can chain (`order_item` → `order` → `customer`).
- An entity cannot reference itself, and references cannot form a cycle.

## Reproducibility

The same spec and seed always produce the same data. The seed comes from `--seed` (or the `seed` argument in Python) if given, otherwise from the spec. With neither, a seed is chosen and reported so the run can be repeated.

Each field draws from its own random stream, so for a fixed seed, adding, removing or reordering other fields or entities does not change the values a field already had.

Reproducibility is guaranteed within one dataspecter version.

## Output

One file per entity, named `<entity>.<format>`, written to the output directory. The directory is created if needed and existing files are replaced. Files are UTF-8 with `\n` line endings on every platform.

| Format | Shape | Null | Boolean | Date and date-time |
|---|---|---|---|---|
| `csv` | Header row, then one line per row. Quoted as needed (RFC 4180). | empty field | `true` / `false` | ISO 8601 |
| `json` | One array of objects. | `null` | `true` / `false` | ISO 8601 string |
| `jsonl` | One object per line. | `null` | `true` / `false` | ISO 8601 string |

The format and directory come from the command line or function arguments if given, otherwise from the spec's `output` block, otherwise `csv` in `output`.

## Validation

A spec is validated completely before anything is generated. Every problem is reported, each with its location:

```
error: shop.yaml is not a valid spec (2 problem(s))
  entities.order.fields.amount: min must not exceed max
  entities.order.fields.customer_id: unknown entity 'client'; entities in this spec: order, customer
```

Values are not coerced: `min: "18"` is rejected for a number, and `true` is not accepted as `1`.

## Things to know about YAML

- Unquoted `yes`, `no`, `on` and `off` are booleans in YAML. In a `choice` list, quote them if you mean text: `values: ["NO", "SE", "DK"]`.
- Dates do not need quotes: `min: 2024-01-01` and `min: "2024-01-01"` are the same.

## Current limits

- Records are flat: a field cannot hold a nested object or list.
- A reference copies one field. Two references to the same entity pick their rows independently.
- Reference rows are chosen uniformly, so the number of children per parent cannot be controlled.
- There are no rules across fields (such as one date falling after another), and no built-in names, emails or addresses.
- The values of referenced fields are held in memory while their children are generated; everything else is streamed.
