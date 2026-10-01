# Design

## Context

See `proposal.md` for motivation. The relevant current state:

- `spec.py` validates a raw mapping into frozen dataclasses. A field definition must be a mapping; `ReferenceField` holds `entity` and `field`; `ChoiceField` holds `values` and optional `weights`; range items must be mappings.
- `generators.py` gives each field its own random stream, keyed by seed, entity and field name. A reference field draws `rng.choice(column)` from that stream, so two references to the same entity pick unrelated rows.
- `engine.py` keeps the values of every referenced field in memory (`_columns`) and can produce a referenced column on its own, without iterating the entity's rows, because each field's stream is independent.

The specs promise that a field's values do not change when other fields are added, and that the same seed reproduces the same data. Both have to survive this change.

## Goals / Non-Goals

**Goals:**

- The shorthands are pure notation: after validation the model is the same as for the long forms, so generators, engine and exporters have a single code path.
- Errors point at what the user wrote, in the form they wrote it.
- Sharing a row between references needs no new syntax in the common case.

**Non-Goals:**

- Nested paths in references (`$customer.address.city`). The grammar leaves room for them; they arrive with nested objects in the next change.
- Templates or expressions. `$entity.field` is a whole field definition, not something interpolated inside a string.
- Controlling how many children each parent gets. Row choice stays uniform.

## Decisions

### 1. Shorthands are parsed in place during validation

`_parse_field` accepts a string as well as a mapping; `_choice` and `_ranges` recognise their string forms. Each produces the same dataclass the long form produces.

*Alternative considered:* a pre-pass that rewrites the raw mapping into long form before validation. It would keep the validator untouched, but problems would then be reported against text the user never wrote (a `weights` list they did not declare, a `type: reference` they did not type). Parsing in place lets each message quote the original entry.

### 2. Reference grammar: `$entity.field`, whole value only

The string must match `$`, an entity name, a dot, a field name, with names following the existing name rule. Anything else that is not a mapping is rejected with the expected form shown.

- `$` has no meaning in YAML or JSON, so `customer_id: $customer.id` needs no quotes in YAML, and it reads as "not literal data".
- The shorthand is recognised only in the field-definition position. A `constant` value of `"$5.00"` or a `choice` value starting with `$` stays literal.
- More than one dot is rejected for now rather than ignored, so that nested paths can be added later without changing the meaning of any spec that is valid today.
- The shorthand carries no options. `null_probability` and `link` need the mapping form. Keeping the shorthand to one shape is what makes it readable.

*Alternatives considered:* `${customer.id}` suggests interpolation inside a larger string, which is not what this is. A `ref: customer.id` key is shorter than today's form but is still a mapping, so it does not remove the nesting.

### 3. One row pick per link, shared by every reference that uses it

`ReferenceField` gains `link: str | None`. For each entity, the engine collects the distinct `(target entity, link)` pairs among its reference fields. Each pair is a *pick*: once per row it draws an index into the target entity's rows, and every reference field belonging to that pick reads its own target column at that index.

- A pick draws from its own stream, keyed by seed, entity, target entity and link. The key includes a separator that cannot occur in a field name, so it cannot collide with a field's stream.
- Because the stream is keyed by target and link, not by field, adding or removing a reference field does not move the picks. This keeps the "stable values" requirement, including the new scenario for a second reference to the same entity.
- Producing a referenced column on its own still works: a reference field that is itself referenced (`order_item` reading `order.customer_id`) rebuilds its pick from the same key and gets the same sequence a full pass over the rows would.
- `null_probability` stays per field and is applied after the value is read, so one reference can be null while another from the same row is not.

This changes the values every reference field produces for a given seed, since they previously drew from the field's own stream. Reproducibility is only promised within a version and nothing is released, so the change is recorded in the changelog rather than migrated.

*Alternatives considered:*
- **Keep picks independent and add an opt-in to share.** The common case (id plus attributes of the same parent) would be the verbose one, and forgetting the opt-in produces data that looks plausible and is wrong.
- **An explicit binding block per entity** (`with: {p: product}`, then `$p.id`). Fully explicit, but every reference would need a binding even when there is only one target. Sharing by default with `link` as the exception covers the same cases with less to write.

### 4. `link` exists only in the mapping form

Independent picks from the same entity (sender and receiver, home and away team) are the less common case, and a named link needs a name. Putting it in the mapping form keeps the shorthand to a single shape. If it proves common, a spelling for it can be added to the shorthand later without affecting existing specs.

### 5. `value || weight` parsing rules

- **When it applies:** only when the field has no `weights` key and at least one entry of `values` is a string containing `||`. With `weights` present, entries are literal, which gives values that really contain `||` a way to be written.
- **Splitting:** on the last `||`, so the value part may itself contain `||`. Both parts are stripped of surrounding spaces.
- **Weight:** must parse as a finite, non-negative number. The usual weight rules then apply to the list (sum greater than zero; relative, so they need not sum to 1).
- **Value:** text by default, so `"10 || 0.5"` yields the string `10`. A field-level `value_type` (`string`, `integer`, `float`, `boolean`) converts every non-empty value in the list. The type is declared, never guessed from the text, so `"007 || 1"` stays `007` and `"true || 1"` stays text unless the field says otherwise. Conversion is strict: `integer` accepts an optional minus and digits only, `float` a plain decimal number, `boolean` exactly `true` or `false`. A value that does not fit is reported at its entry.
- **No evaluation of config text.** Running the value through Python's `eval` would let a config file execute code, and even a restricted literal parser would bring Python syntax (`True`, `None`) into a YAML and JSON format. Conversion is a fixed set of patterns.
- **`value_type` only with inline weights.** In the list form the values already carry their types from YAML or JSON, so the key would be redundant there and is rejected to avoid two ways of saying the same thing.
- **Empty value:** null, whatever the `value_type`. This is what "50% empty" means in practice and matches how nulls are exported (an empty CSV field, `null` in JSON).
- **All or none:** if one entry carries a weight, every entry must. A list where some entries are weighted and others are not has no obvious meaning, so it is rejected instead of guessed at. A non-string entry (a number, a boolean, a null) in such a list counts as carrying no weight.

`ChoiceField` is unchanged in shape: conversion happens during validation, so it holds the already-typed values, which may now include `None` (the list form accepts null too). Generation needs no change beyond that: a `None` value is chosen like any other.

When an unweighted list contains `||` in what was meant as plain text, the entry fails as a malformed weight. That message says how to make entries literal (declare `weights`), since the cause is otherwise not obvious.

### 6. Range shorthand: `min to max || weight`

The bounds are separated by the word `to`, with spaces on both sides. The item is matched as a whole; a bound written without a decimal point becomes an integer, otherwise a float, and the result goes through exactly the checks a mapping item gets (integer fields reject decimal bounds, `min` must not exceed `max`, the precision check). A bound is an optional minus sign and a plain decimal number; a leading-dot form such as `.9` is accepted, exponents and thousands separators are not. String and mapping items can be mixed, since each item is validated on its own.

*Alternatives considered:*
- **`min..max`.** Compact, but dots next to decimal points are hard to read and easy to get wrong: `0.4..0.9` is valid while `0.4...9` and `1...5` look plausible and are not, or mean something unexpected if leading-dot decimals are allowed.
- **A hyphen** (`18-35`). Ambiguous with negative bounds (`-10--5`).

### 8. The format version stays at 1

Every addition is an alternative spelling or an optional key, and every spec that is valid today keeps its structure. The one behaviour change (shared rows) alters generated values, not what a spec may contain. No version of dataspecter has been released, so there is no installed base that would misread a newer spec, and bumping `version` would only force every existing file to change.

### 7. Stating the null rule

`null_probability` behaviour does not change. The requirement now states it, and the reference documents the arithmetic: nulls first, then the field's own proportions scaled by what is left. With a null entry in `values` as well, the two combine as independent events.

## Risks / Trade-offs

- **Reference values change for every existing spec and seed, and same-entity references stop being independent** → Marked BREAKING in the proposal and changelog. No release exists yet. `link` restores independence where it is wanted, and the reference documents it next to the shorthand.
- **A value that legitimately contains `||`** → Taken literally whenever `weights` is declared. Documented with an example.
- **In YAML, an entry that starts with a space or `|` must be quoted** (`" || 0.5"`), or YAML reads `|` as a block marker → Documented in the YAML notes; the resulting YAML error already names the line.
- **Inline values are text unless `value_type` says otherwise** (`"10 || 0.5"` alone is not a number) → Stated in the spec with its own scenario; the reference shows the `value_type` example next to the shorthand.
- **Independent links can land on the same row** (a transfer whose sender is also its receiver, roughly one in every N for N accounts) → Stated in the spec. Guaranteeing distinct rows is not in this change; it is noted in the reference under Current limits.
- **More columns held in memory**, since copying attributes means more fields are referenced → Still one list per referenced field, not whole rows. Documented under the existing memory note.
- **Sharing by default may surprise someone who expects two independent picks** → The reference states the rule in the first sentence of the section and shows `link` directly beneath it.

## Open Questions

- Whether the shorthand should gain a spelling for links. It does not affect anything in this change and can be decided once real configs show how often links are needed.
