# Design

## Context

See `proposal.md` for motivation. This change builds on `add-nested-objects`, which gives every field a path and a shape, a golden-output test and CI. The relevant state after that change:

- Fields form a tree; streams, retained columns and problem locations are keyed by path.
- Fields in a record are generated in declared order and never read each other.
- A field's definition always sits where the field is used.
- Memory is flat in the row count, except for retained reference columns.

This change breaks the second and third of those, and adds one deliberate exception to the fourth.

## Goals / Non-Goals

**Goals:**

- After validation no custom type remains: the model holds only concrete fields, so generation never resolves a name.
- A template's meaning can be read from the template and the fields beside it, and cannot be changed by an edit somewhere else in the spec.
- A spec is data. Nothing in it is ever evaluated.
- A spec that cannot satisfy `unique` fails at validation where that is knowable, not on row 900,000.

**Non-Goals:**

- Uniqueness across several fields together, or across entities.
- Parameterised types with declared arguments. Overrides at the point of use cover the common cases.
- Lower-case or custom character classes in patterns.
- Conditional text or arithmetic in templates.

## Decisions

### 1. Pattern literals use brackets, not backslashes

A backslash escape reads differently in every host syntax: `"\#"` is an error in a double-quoted YAML string, fine in a single-quoted one, and must be `"\\#"` in JSON. Doubling the placeholder is not available either, since `##` already means two digits. Square brackets have no special meaning inside a YAML or JSON string, so `"Item [#]##"` is written the same everywhere. A literal `[` is `[[]`; a `]` outside brackets is literal on its own.

A pattern compiles once to a list of literal strings and placeholder kinds. The same compiled form gives the number of possible values (10, 9 or 26 per placeholder, multiplied), which the uniqueness check uses.

### 2. Templates: a fixed grammar, no evaluation

A small scanner turns the template into literal segments and placeholders (`^` prefix, a dotted path of names, then zero or more `|filter`). Python's `str.format` is not used, because it accepts attribute and index access (`{a.__class__}`) and would let a config reach into objects. Anything that is not a name path is a syntax error at validation.

### 3. Template scope is explicit

A path starts at the object or entity that directly contains the template, and each leading `^` moves the start one level out. There is no outward search.

The earlier draft searched outward when a name was not found beside the template. That makes a template's meaning depend on fields far from it: adding a field `name` to an inner object would silently redirect every `{name}` inside that object. With explicit scope the same edit changes nothing, and a missing `^` produces an error that suggests the fix.

Explicit scope also settles how custom types are validated (decision 6): an object type whose templates use no `^` is closed, and can be checked completely where it is declared.

### 4. Generation order within a record

Templates make fields depend on each other, so each entity gets a generation order: a topological sort of its leaf fields by placeholder dependencies, computed once at validation. A cycle is reported with the fields involved. Records are still assembled in declared order.

If any input is null the result is null. `jane.@example.com` from a missing surname would be plausible-looking wrong data, which is worse than a visible null.

Entities with no templates keep the existing flat fast path, so the golden output and the throughput baseline are unaffected.

### 5. Hidden fields are removed when the record is assembled

A hidden field is generated like any other, in dependency order, and held in the working row that templates read. It is left out when the record handed to callers and exporters is assembled, and its path is left out of the entity's column paths. Retained columns for references are unaffected, so a hidden field can be a reference target.

Hiding does not touch the field's stream, so toggling `hidden` never changes any value.

### 6. Custom types are expanded during validation

`types` is parsed first. A field whose `type` is a custom name is replaced by a copy of the definition with the use-site keys laid over it, recursively, before field parsing continues. For object types, `fields` at the point of use is merged by name, so one sub-field can be swapped without restating the rest.

Because expansion happens before paths are assigned, two uses of a type get different paths, different streams and independent values, and a spec using a type is indistinguishable downstream from one with the definition written in place.

**Name precedence.** Type lookup checks custom types first, then built-ins. While a type's own definition is being expanded, its name is taken out of the custom set, so `integer: {type: integer, min: 0, max: 9}` wraps the built-in instead of referring to itself. This makes the set of built-in names safe to grow: a later built-in called `company` cannot break a spec that already declares its own `company`.

**What is validated where.** Every definition is parsed for structure on its own, so a mistake in an unused type is reported at `types.<name>`. A closed object type (no `^` in its templates) is fully checked there too. Anything that depends on the surroundings (a scalar template type, a `^` placeholder, a reference) is checked at each use and reported at the field, naming the type.

*Alternative considered:* declared parameters (`params: {currency: INR}` with substitution). More expressive, but it is a second templating language inside the spec. Overriding keys covers changing a range, a pattern, a weight list or one sub-field.

### 7. Uniqueness: checked early, guaranteed when possible

Each unique field keeps a set of the values it has produced and redraws on a repeat.

- **Capacity at validation.** Where the number of distinct values is computable (integer ranges, floats with `precision`, dates, date-times, choices with a positive weight, patterns), `count` above it is a validation error.
- **Guaranteed completion for finite fields.** Redrawing alone stalls near capacity: with 499 of 500 integers used, a thousand redraws still miss the last one about one time in seven. So after 100 failed draws a field with a known finite set of values takes the next unused value, scanning from the last drawn position. Any spec that passes the capacity check therefore completes.
- **Unbounded fields** (a float without precision, an unbounded normal integer) have no capacity to check. If 1,000 consecutive draws repeat, generation stops with an error naming the field.
- **Nulls** are not values and are not tracked.

Uniqueness is the one place memory grows with row count: the set lives for the whole run. A million unique ten-character strings is on the order of 100 MB. This is stated in the reference, and only fields that ask for it pay.

Types where uniqueness makes no sense or cannot be controlled (`boolean`, `constant`, `template`, `reference`, `object`) reject the key. A unique template can be had by making one of its inputs unique.

### 8. The format version stays at 1

Everything here is a new type or an optional key. No existing spec changes meaning.

## Risks / Trade-offs

- **Memory for unique fields grows with rows** → Opt-in, documented with a rough size, and measured in the benchmark task.
- **Near-capacity unique fields are slower** → The scan fallback bounds the cost; the benchmark includes a field at 100% of capacity.
- **Shadowing a built-in type name can confuse a reader** (`type: integer` that is not the built-in) → It is the price of forward compatibility, and the reference says so next to the rule.
- **`^` is an unfamiliar notation** → One rule, shown in the reference with the error message that suggests it.
- **An error inside a custom type is reported where the type is used** → The message names the type and the path inside it.
- **Template dependency ordering adds work per record** → The order is computed once; entities without templates keep the flat fast path.
- **Random letters in patterns can spell words** → Noted in the reference; patterns that matter can use digits or a `choice` prefix.
