"""The simulation spec: its data model, loading from YAML or JSON, and validation."""

from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, replace
from dataclasses import field as dataclass_field
from datetime import date, datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from pathlib import Path
from typing import Any, ClassVar

import yaml

from dataspecter.errors import Problem, SpecError

SUPPORTED_VERSION = 1
FORMATS = ("csv", "json", "jsonl")
CSV_SEPARATORS = (".", "__")
MAX_DEPTH = 10  # levels of object nesting below an entity

_EXTENSIONS = (".yaml", ".yml", ".json")
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NAME_RULE = (
    "names must start with a letter or underscore and contain only letters, digits and underscores"
)
_WEIGHT_RULE = "weights must be non-negative numbers with a sum greater than zero"
_VALUE_TYPES = ("string", "integer", "float", "boolean")
_SEPARATOR = "||"
_NUMBER_PATTERN = r"-?(?:\d+(?:\.\d+)?|\.\d+)"  # plain decimal; ".9" allowed, "1e3" is not
_NUMBER = re.compile(_NUMBER_PATTERN)
_INTEGER = re.compile(r"-?\d+")
_RANGE = re.compile(
    rf"\s*({_NUMBER_PATTERN})\s+to\s+({_NUMBER_PATTERN})\s*\|\|\s*({_NUMBER_PATTERN})\s*"
)
_RANGE_FORM = "'min to max || weight', for example '18 to 35 || 0.7'"
_NAME_PATTERN = r"[A-Za-z_][A-Za-z0-9_]*"
_PATH_PATTERN = rf"{_NAME_PATTERN}(?:\.{_NAME_PATTERN})*"
_PATH = re.compile(_PATH_PATTERN)
_REFERENCE = re.compile(rf"\$({_NAME_PATTERN})\.({_PATH_PATTERN})")
_BAD = object()  # a key that was present but invalid, and has already been reported
FILTERS = ("lower", "upper", "title", "ascii", "slug")
_PATTERN_KINDS = {"#": "digit", "%": "nonzero", "?": "letter"}
_PLACEHOLDER = re.compile(rf"\s*(\^*)\s*({_PATH_PATTERN})\s*((?:\|\s*[A-Za-z_]+\s*)*)")


# --- data model -------------------------------------------------------------------------------


@dataclass(frozen=True)
class WeightedRange:
    min: float
    max: float
    weight: float


@dataclass(frozen=True, kw_only=True)
class _Field:
    null_probability: float = 0.0
    hidden: bool = False
    unique: bool = False


@dataclass(frozen=True, kw_only=True)
class _NumericField(_Field):
    min: float | None = None
    max: float | None = None
    distribution: str = "uniform"
    mean: float | None = None
    stddev: float | None = None
    ranges: tuple[WeightedRange, ...] | None = None


@dataclass(frozen=True, kw_only=True)
class IntegerField(_NumericField):
    type: ClassVar[str] = "integer"


@dataclass(frozen=True, kw_only=True)
class FloatField(_NumericField):
    type: ClassVar[str] = "float"
    precision: int | None = None


@dataclass(frozen=True, kw_only=True)
class BooleanField(_Field):
    type: ClassVar[str] = "boolean"
    true_probability: float = 0.5


@dataclass(frozen=True, kw_only=True)
class ChoiceField(_Field):
    type: ClassVar[str] = "choice"
    values: tuple[Any, ...]
    weights: tuple[float, ...] | None = None


@dataclass(frozen=True, kw_only=True)
class DateField(_Field):
    type: ClassVar[str] = "date"
    min: date
    max: date


@dataclass(frozen=True, kw_only=True)
class DatetimeField(_Field):
    type: ClassVar[str] = "datetime"
    min: datetime
    max: datetime


@dataclass(frozen=True, kw_only=True)
class SequenceField(_Field):
    type: ClassVar[str] = "sequence"
    start: int = 1
    step: int = 1


@dataclass(frozen=True, kw_only=True)
class UuidField(_Field):
    type: ClassVar[str] = "uuid"


@dataclass(frozen=True, kw_only=True)
class ConstantField(_Field):
    type: ClassVar[str] = "constant"
    value: Any


@dataclass(frozen=True, kw_only=True)
class ReferenceField(_Field):
    type: ClassVar[str] = "reference"
    entity: str
    field: str
    link: str | None = None


@dataclass(frozen=True, kw_only=True)
class ObjectField(_Field):
    type: ClassVar[str] = "object"
    fields: Mapping[str, Any]


@dataclass(frozen=True, kw_only=True)
class PatternField(_Field):
    type: ClassVar[str] = "pattern"
    pattern: str
    # (kind, text) pairs: kind is "literal", "digit", "nonzero" or "letter".
    segments: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Placeholder:
    """A ``{path|filter}`` in a template. `target` is the path from the entity down."""

    up: int
    path: str
    filters: tuple[str, ...]
    target: str | None


@dataclass(frozen=True, kw_only=True)
class TemplateField(_Field):
    type: ClassVar[str] = "template"
    template: str
    parts: tuple[str | Placeholder, ...]


Field = (
    IntegerField
    | FloatField
    | BooleanField
    | ChoiceField
    | DateField
    | DatetimeField
    | SequenceField
    | UuidField
    | ConstantField
    | ReferenceField
    | ObjectField
    | PatternField
    | TemplateField
)


@dataclass(frozen=True)
class Entity:
    name: str
    count: int
    fields: Mapping[str, Field]


@dataclass(frozen=True)
class Output:
    format: str | None = None
    dir: str | None = None
    csv_separator: str | None = None


@dataclass(frozen=True)
class Spec:
    """A validated simulation spec. Build one with `load_spec`."""

    version: int
    entities: Mapping[str, Entity]
    seed: int | None = None
    output: Output = Output()


# --- loading ----------------------------------------------------------------------------------


class _Loader(yaml.SafeLoader):
    """SafeLoader that leaves dates as strings.

    YAML would otherwise turn an unquoted ``2024-01-01`` into a date object, and raise on an
    impossible one such as ``2024-13-01``. Keeping them as strings makes YAML and JSON specs
    arrive in the same shape and lets the validator report bad dates with their location.
    """


_Loader.yaml_implicit_resolvers = {
    first_char: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for first_char, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_spec(source: str | os.PathLike[str] | Mapping[str, Any]) -> Spec:
    """Load and validate a spec from a YAML or JSON file, or from a mapping of the same shape.

    Raises `SpecError`, listing every problem found, if the file cannot be read or the spec
    is not valid.
    """
    raw = _read_file(Path(source)) if isinstance(source, str | os.PathLike) else source
    problems: list[Problem] = []
    spec = _parse_spec(raw, problems)
    if problems or spec is None:
        raise SpecError(problems)
    return spec


def _read_file(path: Path) -> Any:
    suffix = path.suffix.lower()
    if suffix not in _EXTENSIONS:
        raise _file_error(path, f"unsupported file extension {suffix!r}; use .yaml, .yml or .json")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise _file_error(path, "file not found") from None
    except UnicodeDecodeError:
        raise _file_error(path, "file is not valid UTF-8") from None
    except OSError as exc:
        raise _file_error(path, f"cannot read file: {exc.strerror or exc}") from None

    if suffix == ".json":
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            where = f"line {exc.lineno}, column {exc.colno}"
            raise _file_error(path, f"invalid JSON at {where}: {exc.msg}") from None
    try:
        return yaml.load(text, Loader=_Loader)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        detail = getattr(exc, "problem", None) or "could not be parsed"
        raise _file_error(path, f"invalid YAML{where}: {detail}") from None


def _file_error(path: Path, message: str) -> SpecError:
    return SpecError([Problem("", f"{path}: {message}")])


# --- validation helpers -----------------------------------------------------------------------


def _at(path: str, key: object) -> str:
    return f"{path}.{key}" if path else str(key)


def _is_int(value: Any) -> bool:
    # bool is a subclass of int, so `true` would otherwise pass as 1.
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def _is_probability(value: Any) -> bool:
    return _is_number(value) and 0 <= value <= 1


def _is_scalar(value: Any) -> bool:
    return isinstance(value, str | bool) or _is_number(value)


def _is_name(value: Any) -> bool:
    return isinstance(value, str) and _NAME.fullmatch(value) is not None


def _reference_parts(raw: Any) -> tuple[str, str] | None:
    """Split a ``$entity.field`` shorthand into its two names; None if `raw` is not one."""
    match = _REFERENCE.fullmatch(raw) if isinstance(raw, str) else None
    return (match[1], match[2]) if match else None


def _number(text: str) -> int | float:
    """Read a number matched by `_NUMBER`: an integer unless it has a decimal point."""
    return float(text) if "." in text else int(text)


def _listed(items: Any) -> str:
    return ", ".join(sorted(items))


def _read(
    raw: Mapping[Any, Any],
    key: str,
    valid: Callable[[Any], bool],
    expected: str,
    path: str,
    problems: list[Problem],
    default: Any = None,
) -> Any:
    """Return ``raw[key]`` if valid and `default` if absent; report and return `_BAD` otherwise."""
    if key not in raw:
        return default
    value = raw[key]
    if not valid(value):
        problems.append(Problem(_at(path, key), f"must be {expected}, got {value!r}"))
        return _BAD
    return value


def _require(raw: Mapping[Any, Any], keys: tuple[str, ...], path: str, problems: list[Problem]):
    missing = [key for key in keys if key not in raw]
    if missing:
        problems.append(Problem(path, f"missing required key(s): {', '.join(missing)}"))


def _unknown_keys(
    raw: Mapping[Any, Any],
    allowed: frozenset[str],
    path: str,
    problems: list[Problem],
    where: str = "",
) -> None:
    for key in raw:
        if key not in allowed:
            message = f"unknown key {key!r}{where}; allowed keys: {_listed(allowed)}"
            problems.append(Problem(path, message))


def _usable(*values: Any) -> bool:
    return all(value is not None and value is not _BAD for value in values)


def _check_weights(weights: list[Any], path: str, problems: list[Problem]) -> None:
    if not _usable(*weights):
        return  # an individual weight was already reported
    if any(weight < 0 for weight in weights) or sum(weights) <= 0:
        problems.append(Problem(path, _WEIGHT_RULE))


def precision_bounds(
    low: float | None, high: float | None, precision: int | None
) -> tuple[float | None, float | None]:
    """Narrow ``[low, high]`` to the values representable with `precision` decimal places.

    Rounding a value near a bound can push it outside the range (0.123 rounds to 0.1, below a
    minimum of 0.123); clamping to these bounds instead keeps it inside. If no representable
    value lies in the range, the returned low is greater than the returned high.
    """
    if precision is None or precision > 15:  # beyond a float's precision rounding is a no-op
        return low, high
    quantum = Decimal(1).scaleb(-precision)

    def snap(value: float | None, rounding: str) -> float | None:
        if value is None:
            return None
        return float(Decimal(repr(float(value))).quantize(quantum, rounding=rounding))

    return snap(low, ROUND_CEILING), snap(high, ROUND_FLOOR)


# --- field parsers ----------------------------------------------------------------------------
# Each parser reports problems as it goes and returns a field, or None if it reported any.


def _numeric(kind: str, raw: Mapping[Any, Any], path: str, problems: list[Problem], common: dict):
    start = len(problems)
    is_bound, bound = (_is_int, "an integer") if kind == "integer" else (_is_number, "a number")
    precision = None
    if kind == "float":
        precision = _read(
            raw,
            "precision",
            lambda v: _is_int(v) and v >= 0,
            "a non-negative integer",
            path,
            problems,
        )
    pairs: list[tuple[Any, Any, str]] = []  # (min, max, where) of every range, for shared checks
    values: dict[str, Any] = {}

    if "ranges" in raw:
        clash = [key for key in ("min", "max", "distribution", "mean", "stddev") if key in raw]
        if clash:
            message = (
                f"'ranges' and {_quoted(clash)} are mutually exclusive: use either a single "
                "range (min and max) or weighted ranges"
            )
            problems.append(Problem(path, message))
        ranges_path = _at(path, "ranges")
        indexed = _ranges(raw["ranges"], is_bound, bound, ranges_path, problems)
        values["ranges"] = tuple(item for _, item in indexed)
        pairs = [(item.min, item.max, f"{ranges_path}[{index}]") for index, item in indexed]
    else:
        distribution = _read(
            raw,
            "distribution",
            lambda v: v in ("uniform", "normal"),
            "'uniform' or 'normal'",
            path,
            problems,
            default="uniform",
        )
        low = _read(raw, "min", is_bound, bound, path, problems)
        high = _read(raw, "max", is_bound, bound, path, problems)
        mean = _read(raw, "mean", _is_number, "a number", path, problems)
        stddev = _read(raw, "stddev", _is_number, "a number", path, problems)
        if distribution == "uniform":
            _require(raw, ("min", "max"), path, problems)
            unused = [key for key in ("mean", "stddev") if key in raw]
            if unused:
                message = f"{_quoted(unused)} only apply when distribution is 'normal'"
                problems.append(Problem(path, message))
        elif distribution == "normal":
            _require(raw, ("mean", "stddev"), path, problems)
            if _usable(stddev) and stddev <= 0:
                problems.append(Problem(_at(path, "stddev"), "must be greater than zero"))
        pairs = [(low, high, path)]
        values.update(distribution=distribution, min=low, max=high, mean=mean, stddev=stddev)

    for low, high, where in pairs:
        if not _usable(low, high):
            continue
        if low > high:
            problems.append(Problem(where, "min must not exceed max"))
        elif _usable(precision):
            grid_low, grid_high = precision_bounds(low, high, precision)
            if grid_low > grid_high:
                message = f"no value with {precision} decimal place(s) lies between min and max"
                problems.append(Problem(where, message))

    if len(problems) > start:
        return None
    if kind == "integer":
        return IntegerField(**values, **common)
    return FloatField(**values, precision=precision, **common)


def _quoted(keys: list[str]) -> str:
    return ", ".join(f"'{key}'" for key in keys)


def _ranges(
    raw: Any, is_bound: Callable[[Any], bool], bound: str, path: str, problems: list[Problem]
) -> list[tuple[int, WeightedRange]]:
    if not isinstance(raw, list) or not raw:
        problems.append(Problem(path, "must be a non-empty list of items with min, max and weight"))
        return []
    ranges: list[tuple[int, WeightedRange]] = []
    weights: list[Any] = []
    for index, item in enumerate(raw):
        item_path = f"{path}[{index}]"
        if isinstance(item, str):
            match = _RANGE.fullmatch(item)
            if match is None:
                message = f"{item!r} is not a range; the expected form is {_RANGE_FORM}"
                problems.append(Problem(item_path, message))
                weights.append(_BAD)
                continue
            low, high, weight = (_number(part) for part in match.groups())
            item = {"min": low, "max": high, "weight": weight}
        if not isinstance(item, Mapping):
            message = f"must be a mapping with min, max and weight, or a string {_RANGE_FORM}"
            problems.append(Problem(item_path, message))
            weights.append(_BAD)
            continue
        _unknown_keys(item, frozenset({"min", "max", "weight"}), item_path, problems)
        _require(item, ("min", "max", "weight"), item_path, problems)
        low = _read(item, "min", is_bound, bound, item_path, problems)
        high = _read(item, "max", is_bound, bound, item_path, problems)
        weight = _read(item, "weight", _is_number, "a number", item_path, problems)
        weights.append(weight)
        ranges.append((index, WeightedRange(low, high, weight)))
    _check_weights(weights, path, problems)
    return ranges


def _integer(raw, path, problems, common):
    return _numeric("integer", raw, path, problems, common)


def _float(raw, path, problems, common):
    return _numeric("float", raw, path, problems, common)


def _boolean(raw, path, problems, common):
    probability = _read(
        raw,
        "true_probability",
        _is_probability,
        "a number between 0 and 1",
        path,
        problems,
        default=0.5,
    )
    if probability is _BAD:
        return None
    return BooleanField(true_probability=probability, **common)


def _choice(raw, path, problems, common):
    start = len(problems)
    _require(raw, ("values",), path, problems)
    values = _read(
        raw,
        "values",
        lambda v: isinstance(v, list) and bool(v) and all(x is None or _is_scalar(x) for x in v),
        "a non-empty list of strings, numbers, booleans or nulls",
        path,
        problems,
    )
    weights = _read(
        raw, "weights", lambda v: isinstance(v, list), "a list of numbers", path, problems
    )
    value_type = _read(
        raw,
        "value_type",
        lambda v: isinstance(v, str) and v in _VALUE_TYPES,
        f"one of {', '.join(_VALUE_TYPES)}",
        path,
        problems,
        default="string",
    )

    # With `weights` declared every entry is literal, which is how text containing "||" is written.
    inline = (
        "weights" not in raw
        and _usable(values)
        and any(isinstance(entry, str) and _SEPARATOR in entry for entry in values)
    )
    if inline:
        if value_type is not _BAD:
            values, weights = _inline_weights(values, value_type, _at(path, "values"), problems)
    elif "value_type" in raw and value_type is not _BAD:
        message = (
            "applies only to values written with inline weights ('value || weight'); "
            "values in a plain list already have their types"
        )
        problems.append(Problem(_at(path, "value_type"), message))
    elif _usable(weights):
        weights_path = _at(path, "weights")
        if _usable(values) and len(weights) != len(values):
            message = (
                f"weights must match values in length "
                f"({len(values)} values, {len(weights)} weights)"
            )
            problems.append(Problem(weights_path, message))
        if not all(map(_is_number, weights)):
            problems.append(Problem(weights_path, "must be a list of numbers"))
        else:
            _check_weights(weights, weights_path, problems)
    if len(problems) > start:
        return None
    return ChoiceField(
        values=tuple(values), weights=tuple(weights) if weights is not None else None, **common
    )


def _inline_weights(
    entries: list[Any], value_type: str, path: str, problems: list[Problem]
) -> tuple[list[Any], list[Any]]:
    """Split ``value || weight`` entries into values, converted to `value_type`, and weights."""
    literal_hint = "to use '||' as plain text, declare 'weights' so every value is taken literally"
    if not all(isinstance(entry, str) and _SEPARATOR in entry for entry in entries):
        message = (
            f"either every value carries a weight ('value || weight') or none does; {literal_hint}"
        )
        problems.append(Problem(path, message))
        return [], []

    values: list[Any] = []
    weights: list[Any] = []
    for index, entry in enumerate(entries):
        entry_path = f"{path}[{index}]"
        text, _, weight_text = (part.strip() for part in entry.rpartition(_SEPARATOR))
        if _NUMBER.fullmatch(weight_text):
            weights.append(_number(weight_text))
        else:
            message = (
                f"{entry!r}: the weight after '||' must be a non-negative number, "
                f"got {weight_text!r}; {literal_hint}"
            )
            problems.append(Problem(entry_path, message))
            weights.append(_BAD)
        values.append(_convert(text, value_type, entry_path, problems))
    _check_weights(weights, path, problems)
    return values, weights


def _convert(text: str, value_type: str, path: str, problems: list[Problem]) -> Any:
    """Convert the text of an inline value to its declared type. An empty value is null.

    The text is matched against fixed patterns and never evaluated, so a spec cannot run code.
    """
    if text == "":
        return None
    if value_type == "string":
        return text
    if value_type == "integer" and _INTEGER.fullmatch(text):
        return int(text)
    if value_type == "float" and _NUMBER.fullmatch(text):
        return float(text)
    if value_type == "boolean" and text in ("true", "false"):
        return text == "true"
    expected = "true or false" if value_type == "boolean" else f"a valid {value_type}"
    message = f"{text!r} is not {expected} (the field declares value_type: {value_type})"
    problems.append(Problem(path, message))
    return _BAD


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _temporal(raw, path, problems, common, parse, noun, field_type):
    start = len(problems)
    _require(raw, ("min", "max"), path, problems)
    bounds = {}
    for key in ("min", "max"):
        if key in raw:
            bounds[key] = parse(raw[key])
            if bounds[key] is None:
                message = f"{raw[key]!r} is not a valid ISO 8601 {noun}"
                problems.append(Problem(_at(path, key), message))
    if len(problems) > start:
        return None
    low, high = bounds["min"], bounds["max"]
    if isinstance(low, datetime) and (low.tzinfo is None) != (high.tzinfo is None):
        message = "min and max must both have a timezone offset, or neither"
        problems.append(Problem(path, message))
        return None
    if low > high:
        problems.append(Problem(path, "min must not be after max"))
        return None
    return field_type(min=low, max=high, **common)


def _date(raw, path, problems, common):
    return _temporal(raw, path, problems, common, _parse_date, "date", DateField)


def _datetime(raw, path, problems, common):
    return _temporal(raw, path, problems, common, _parse_datetime, "date-time", DatetimeField)


def _sequence(raw, path, problems, common):
    start = _read(raw, "start", _is_int, "an integer", path, problems, default=1)
    step = _read(raw, "step", _is_int, "an integer", path, problems, default=1)
    if step == 0:
        problems.append(Problem(_at(path, "step"), "must not be zero"))
        step = _BAD
    if not _usable(start, step):
        return None
    return SequenceField(start=start, step=step, **common)


def _uuid(raw, path, problems, common):
    return UuidField(**common)


def _constant(raw, path, problems, common):
    if "value" not in raw:
        _require(raw, ("value",), path, problems)
        return None
    value = raw["value"]
    if value is not None and not _is_scalar(value):
        message = f"must be a string, number, boolean or null, got {value!r}"
        problems.append(Problem(_at(path, "value"), message))
        return None
    return ConstantField(value=value, **common)


def _is_path(value: Any) -> bool:
    return isinstance(value, str) and _PATH.fullmatch(value) is not None


def _reference(raw, path, problems, common):
    _require(raw, ("entity", "field"), path, problems)
    entity = _read(raw, "entity", lambda v: isinstance(v, str), "an entity name", path, problems)
    field = _read(
        raw,
        "field",
        _is_path,
        "a field name, or a dotted path such as address.city",
        path,
        problems,
    )
    link = _read(raw, "link", _is_name, f"a link name ({_NAME_RULE})", path, problems)
    if not _usable(entity, field) or link is _BAD:
        return None
    return ReferenceField(entity=entity, field=field, link=link, **common)


def compile_pattern(pattern: str) -> tuple[tuple[tuple[str, str], ...] | None, str | None]:
    """Compile a pattern into (kind, text) segments, or return None and what is wrong with it.

    Text in square brackets is literal. Brackets are used instead of backslash escapes because
    a backslash is read differently by YAML single quotes, YAML double quotes and JSON.
    """
    segments: list[tuple[str, str]] = []
    literal: list[str] = []

    def flush() -> None:
        if literal:
            segments.append(("literal", "".join(literal)))
            literal.clear()

    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "[":
            end = pattern.find("]", index + 1)
            if end == -1:
                return None, "a '[' is not closed; write a literal '[' as '[[]'"
            literal.append(pattern[index + 1 : end])
            index = end + 1
            continue
        if char in _PATTERN_KINDS:
            flush()
            segments.append((_PATTERN_KINDS[char], ""))
        else:
            literal.append(char)
        index += 1
    flush()
    return tuple(segments), None


def _pattern(raw, path, problems, common):
    pattern = _read(
        raw,
        "pattern",
        lambda v: isinstance(v, str) and v != "",
        "a non-empty string",
        path,
        problems,
    )
    if "pattern" not in raw:
        problems.append(Problem(path, "a pattern is required, for example pattern: 'SKU-??-####'"))
        return None
    if pattern is _BAD:
        return None
    segments, error = compile_pattern(pattern)
    if error:
        problems.append(Problem(_at(path, "pattern"), error))
        return None
    return PatternField(pattern=pattern, segments=segments, **common)


@dataclass
class _Context:
    """What the field parsers need to know about where they are."""

    entity: Any
    # Every reference found, as (entity, problem path, field, note), for the cross-entity pass.
    # The note names the custom type the field came from, if any, for use in messages.
    references: list[tuple[Any, str, ReferenceField, str]] = dataclass_field(default_factory=list)
    # Every template found, as (entity, problem path, path in the entity, field, note).
    templates: list[tuple[Any, str, str, TemplateField, str]] = dataclass_field(
        default_factory=list
    )
    types: Mapping[str, Any] = dataclass_field(default_factory=dict)  # usable raw definitions
    broken: set[str] = dataclass_field(default_factory=set)  # types reported at their declaration
    expanding: tuple[str, ...] = ()  # custom types being expanded, outermost first
    declaring: str | None = None  # the custom type being validated on its own, if any


def _via(ctx: _Context) -> str:
    """Text naming the custom type a field is being expanded from, to append to a message."""
    return f" (in custom type {ctx.expanding[0]!r})" if ctx.expanding else ""


def _scan_template(text: str) -> tuple[list[Any] | None, str | None]:
    """Split a template into literal text and (ups, path, filters) placeholders.

    The grammar is fixed: a placeholder is a path of names with optional filters. Nothing is
    evaluated, and `str.format` is not used because it allows attribute and index access.
    """
    parts: list[Any] = []
    literal: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if text.startswith(("{{", "}}"), index):
            literal.append(char)
            index += 2
        elif char == "}":
            return None, "a '}' has no matching '{'; write a literal brace as '}}'"
        elif char == "{":
            end = text.find("}", index + 1)
            if end == -1:
                return None, "a '{' is not closed; write a literal brace as '{{'"
            inner = text[index + 1 : end]
            match = _PLACEHOLDER.fullmatch(inner)
            if match is None:
                message = (
                    f"malformed placeholder {{{inner}}}; expected {{field}}, {{object.field}}, "
                    "{^outer_field} or {field|filter}"
                )
                return None, message
            filters = tuple(name.strip() for name in match[3].split("|")[1:])
            unknown = [name for name in filters if name not in FILTERS]
            if unknown:
                supported = ", ".join(FILTERS)
                return None, f"unknown filter {unknown[0]!r}; supported filters: {supported}"
            if literal:
                parts.append("".join(literal))
                literal.clear()
            parts.append((len(match[1]), match[2], filters))
            index = end + 1
        else:
            literal.append(char)
            index += 1
    if literal:
        parts.append("".join(literal))
    return parts, None


def _template(raw, path, problems, common, ctx: _Context, depth: int, data_path: str):
    template = _read(
        raw,
        "template",
        lambda v: isinstance(v, str) and v != "",
        "a non-empty string",
        path,
        problems,
    )
    if "template" not in raw:
        problems.append(
            Problem(path, "a template is required, for example template: '{id}-{tier}'")
        )
        return None
    if template is _BAD:
        return None
    scanned, error = _scan_template(template)
    if error:
        problems.append(Problem(_at(path, "template"), error))
        return None

    scope = data_path.split(".")[:-1]  # the object, or entity, that contains this template
    parts: list[str | Placeholder] = []
    for part in scanned:
        if isinstance(part, str):
            parts.append(part)
            continue
        ups, name, filters = part
        target: str | None
        if ups > len(scope):
            # A custom type is validated before it is placed, so what lies outside it is unknown.
            if ctx.declaring is None:
                shown = "{" + "^" * ups + name + "}"
                message = f"placeholder {shown}: there is no enclosing level to reach"
                problems.append(Problem(_at(path, "template"), message))
                return None
            target = None
        else:
            target = ".".join([*scope[: len(scope) - ups], name])
            if ctx.declaring is not None and not target.startswith(f"{ctx.declaring}."):
                target = None  # leaves the type; checked where the type is used
        parts.append(Placeholder(up=ups, path=name, filters=filters, target=target))
    field = TemplateField(template=template, parts=tuple(parts), **common)
    ctx.templates.append((ctx.entity, path, data_path, field, _via(ctx)))
    return field


def _object(raw, path, problems, common, ctx: _Context, depth: int, data_path: str):
    # The depth check also ends a document that contains itself through a YAML anchor, so no
    # input can recurse without bound.
    if depth + 1 > MAX_DEPTH:
        problems.append(Problem(path, f"objects are nested more than {MAX_DEPTH} levels deep"))
        return None
    if "fields" not in raw:
        problems.append(Problem(path, "an object needs 'fields' with at least one field"))
        return None
    fields = _parse_fields(
        raw["fields"],
        _at(path, "fields"),
        problems,
        ctx,
        depth + 1,
        f"{data_path}.",
        need_visible=not common["hidden"],
    )
    if fields is None or any(field is None for field in fields.values()):
        return None
    return ObjectField(fields=fields, **common)


_COMMON_KEYS = frozenset({"type", "null_probability", "hidden", "unique"})
_NUMERIC_KEYS = frozenset({"min", "max", "distribution", "mean", "stddev", "ranges"})
_UNIQUE_TYPES = frozenset(
    {"integer", "float", "date", "datetime", "choice", "pattern", "sequence", "uuid"}
)
_CONTEXTUAL = (_object, _template)  # parsers that need to know where the field is

# type name -> (keys the type accepts besides the common ones, parser)
_FIELD_TYPES: dict[str, tuple[frozenset[str], Callable[..., Any]]] = {
    "integer": (_NUMERIC_KEYS, _integer),
    "float": (_NUMERIC_KEYS | {"precision"}, _float),
    "boolean": (frozenset({"true_probability"}), _boolean),
    "choice": (frozenset({"values", "weights", "value_type"}), _choice),
    "date": (frozenset({"min", "max"}), _date),
    "datetime": (frozenset({"min", "max"}), _datetime),
    "sequence": (frozenset({"start", "step"}), _sequence),
    "uuid": (frozenset(), _uuid),
    "constant": (frozenset({"value"}), _constant),
    "reference": (frozenset({"entity", "field", "link"}), _reference),
    "object": (frozenset({"fields"}), _object),
    "pattern": (frozenset({"pattern"}), _pattern),
    "template": (frozenset({"template"}), _template),
}


def _expand(type_name, raw, path, problems, ctx: _Context, depth: int, data_path: str):
    """Parse a field that uses a custom type, as if the definition were written in its place.

    Keys at the point of use replace the definition's. For an object type, `fields` is merged
    by name, so one sub-field can be swapped without restating the rest.
    """
    if type_name in ctx.broken:
        return None  # already reported where the type is declared
    merged = dict(ctx.types[type_name])
    for key, value in raw.items():
        if key == "type":
            continue
        if key == "fields" and isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    start = len(problems)
    inner = replace(ctx, expanding=(*ctx.expanding, type_name))
    field = _parse_field(merged, path, problems, inner, depth, data_path)
    for index in range(start, len(problems)):
        problem = problems[index]
        if "(in custom type" not in problem.message:
            message = f"{problem.message} (in custom type {type_name!r})"
            problems[index] = Problem(problem.path, message)
    return field


def _parse_field(
    raw: Any, path: str, problems: list[Problem], ctx: _Context, depth: int, data_path: str
) -> Field | None:
    """Parse one field definition.

    `depth` is the number of objects the field is nested inside, and `data_path` its path from
    the entity down, such as ``address.city``.
    """
    start = len(problems)
    supported = f"supported types: {', '.join(_FIELD_TYPES)}"
    if ctx.types:
        supported += f"; custom types in this spec: {', '.join(ctx.types)}"
    if isinstance(raw, str):
        parts = _reference_parts(raw)
        if parts is None:
            message = f"{raw!r} is not a field definition; a reference is written '$entity.field'"
            problems.append(Problem(path, message))
            return None
        field = ReferenceField(entity=parts[0], field=parts[1])
        ctx.references.append((ctx.entity, path, field, _via(ctx)))
        return field
    if not isinstance(raw, Mapping):
        message = (
            f"a field must be a mapping with a 'type' or a '$entity.field' reference; {supported}"
        )
        problems.append(Problem(path, message))
        return None
    if "type" not in raw:
        problems.append(Problem(path, f"missing required key 'type'; {supported}"))
        return None
    type_name = raw["type"]
    if isinstance(type_name, str) and type_name in ctx.types:
        # A custom type takes precedence over a built-in of the same name, except inside its
        # own definition, where the name means the built-in. That keeps later built-in types
        # from ever breaking a spec that already uses the name.
        if type_name not in ctx.expanding:
            return _expand(type_name, raw, path, problems, ctx, depth, data_path)
        if type_name not in _FIELD_TYPES:
            return None  # a cycle, reported once where the types are declared
    if not isinstance(type_name, str) or type_name not in _FIELD_TYPES:
        problems.append(
            Problem(_at(path, "type"), f"unknown field type {type_name!r}; {supported}")
        )
        return None

    keys, parser = _FIELD_TYPES[type_name]
    _unknown_keys(raw, keys | _COMMON_KEYS, path, problems, where=f" for type '{type_name}'")
    null_probability = _read(
        raw,
        "null_probability",
        _is_probability,
        "a number between 0 and 1",
        path,
        problems,
        default=0.0,
    )
    is_bool = lambda v: isinstance(v, bool)  # noqa: E731
    hidden = _read(raw, "hidden", is_bool, "true or false", path, problems, default=False)
    unique = _read(raw, "unique", is_bool, "true or false", path, problems, default=False)
    if unique is True and type_name not in _UNIQUE_TYPES:
        message = f"'unique' is not supported for type {type_name!r}"
        problems.append(Problem(_at(path, "unique"), message))
    common = {
        "null_probability": 0.0 if null_probability is _BAD else null_probability,
        "hidden": hidden is True,
        "unique": unique is True,
    }
    if parser in _CONTEXTUAL:
        field = parser(raw, path, problems, common, ctx, depth, data_path)
    else:
        field = parser(raw, path, problems, common)
    if isinstance(field, ReferenceField):
        ctx.references.append((ctx.entity, path, field, _via(ctx)))
    return field if len(problems) == start else None


def _parse_fields(
    raw: Any,
    path: str,
    problems: list[Problem],
    ctx: _Context,
    depth: int,
    prefix: str = "",
    need_visible: bool = True,
) -> dict[Any, Field | None] | None:
    """Parse the `fields` mapping of an entity or object.

    A field that fails to parse is kept as None, so that later checks can tell "this name is
    declared but broken" from "no such field".
    """
    if not isinstance(raw, Mapping):
        problems.append(Problem(path, "must be a mapping of field name to definition"))
        return None
    if not raw:
        problems.append(Problem(path, "at least one field is required"))
        return None
    fields: dict[Any, Field | None] = {}
    for name, raw_field in raw.items():
        field_path = _at(path, name)
        if not _is_name(name):
            problems.append(Problem(field_path, f"invalid field name {name!r}; {_NAME_RULE}"))
        fields[name] = _parse_field(raw_field, field_path, problems, ctx, depth, f"{prefix}{name}")
    if need_visible and all(field is not None and field.hidden for field in fields.values()):
        problems.append(Problem(path, "at least one field must be visible; every field is hidden"))
    return fields


# --- custom types -----------------------------------------------------------------------------


def _type_uses(definition: Any, names: Mapping[str, Any], own: str, depth: int = 0) -> set[str]:
    """Return the custom types a raw definition uses, directly or inside its objects."""
    found: set[str] = set()
    if not isinstance(definition, Mapping) or depth > MAX_DEPTH:
        return found
    used = definition.get("type")
    if isinstance(used, str) and used in names and not (used == own and used in _FIELD_TYPES):
        found.add(used)
    inner = definition.get("fields")
    if isinstance(inner, Mapping):
        for item in inner.values():
            found |= _type_uses(item, names, own, depth + 1)
    return found


def _parse_types(raw: Any, problems: list[Problem]) -> tuple[dict[str, Any], set[str]]:
    """Validate the `types` block. Return the usable definitions and the names that are broken."""
    if not isinstance(raw, Mapping):
        problems.append(Problem("types", "must be a mapping of type name to definition"))
        return {}, set()
    types: dict[str, Any] = {}
    for name, definition in raw.items():
        path = _at("types", name)
        if not _is_name(name):
            problems.append(Problem(path, f"invalid type name {name!r}; {_NAME_RULE}"))
        elif not isinstance(definition, Mapping):
            problems.append(Problem(path, "a type definition must be a mapping with a 'type'"))
        else:
            types[name] = definition

    uses = {name: _type_uses(definition, types, name) for name, definition in types.items()}
    broken: set[str] = set()
    cycle = _find_cycle({name: sorted(used) for name, used in uses.items()})
    while cycle:
        problems.append(
            Problem("types", f"custom types depend on each other: {' -> '.join(cycle)}")
        )
        broken.update(cycle)
        remaining = {
            name: sorted(used - broken) for name, used in uses.items() if name not in broken
        }
        cycle = _find_cycle(remaining)

    # Validate each type on its own, dependencies first, so that a type built on a broken one
    # is not reported a second time.
    done: list[str] = []

    def visit(name: str) -> None:
        if name in done or name in broken:
            return
        for used in sorted(uses[name]):
            visit(used)
        done.append(name)

    for name in types:
        visit(name)
    for name in done:
        if uses[name] & broken:
            broken.add(name)
            continue
        ctx = _Context(entity=None, types=types, broken=broken, declaring=name)
        start = len(problems)
        field = _parse_field(types[name], _at("types", name), problems, ctx, 0, name)
        if field is not None:
            _check_templates(ctx.templates, {None: {name: field}}, problems)
        if len(problems) > start:
            broken.add(name)
    return types, broken


# --- document parsers -------------------------------------------------------------------------


def _draft_fields(
    fields: Mapping[Any, Field | None], path: str, prefix: str = ""
) -> Iterator[tuple[str, str, Field]]:
    """Yield (problem path, path in the entity, field) for every field that parsed."""
    for name, field in fields.items():
        if field is None:
            continue
        yield _at(path, name), f"{prefix}{name}", field
        if isinstance(field, ObjectField):
            yield from _draft_fields(
                field.fields, _at(_at(path, name), "fields"), f"{prefix}{name}."
            )


def _check_unique(fields: Mapping[Any, Field | None], path: str, count: int, problems) -> None:
    from dataspecter.domains import domain  # imported here: domains builds on this module

    for problem_path, _, field in _draft_fields(fields, path):
        if not field.unique:
            continue
        values = domain(field)
        if values is not None and values[0] < count:
            message = (
                f"the field is unique but can produce only {values[0]:,} distinct values, and "
                f"the entity needs {count:,}"
            )
            problems.append(Problem(problem_path, message))


def _parse_entity(
    name: Any, raw: Any, path: str, problems: list[Problem], ctx: _Context
) -> tuple[Entity | None, dict[Any, Field | None] | None]:
    """Return the entity, or None if it has problems, and its fields as far as they parsed."""
    start = len(problems)
    if not _is_name(name):
        problems.append(Problem(path, f"invalid entity name {name!r}; {_NAME_RULE}"))
    if not isinstance(raw, Mapping):
        problems.append(Problem(path, "must be a mapping with 'count' and 'fields'"))
        return None, None
    _unknown_keys(raw, frozenset({"count", "fields"}), path, problems)
    _require(raw, ("count", "fields"), path, problems)
    count = _read(
        raw, "count", lambda v: _is_int(v) and v >= 1, "an integer of 1 or more", path, problems
    )
    fields = None
    if "fields" in raw:
        fields_path = _at(path, "fields")
        fields = _parse_fields(raw["fields"], fields_path, problems, ctx, depth=0)
        if fields is not None and _usable(count):
            _check_unique(fields, fields_path, count, problems)

    if len(problems) > start:
        return None, fields
    return Entity(name=name, count=count, fields=fields), fields


def _parse_output(raw: Any, problems: list[Problem]) -> Output:
    path = "output"
    if not isinstance(raw, Mapping):
        problems.append(Problem(path, "must be a mapping with 'format', 'dir' or 'csv_separator'"))
        return Output()
    _unknown_keys(raw, frozenset({"format", "dir", "csv_separator"}), path, problems)
    output_format = raw.get("format")
    if "format" in raw and output_format not in FORMATS:
        message = f"unsupported format {output_format!r}; supported formats: {', '.join(FORMATS)}"
        problems.append(Problem(_at(path, "format"), message))
    directory = _read(
        raw,
        "dir",
        lambda v: isinstance(v, str) and bool(v.strip()),
        "a directory path",
        path,
        problems,
    )
    separator = raw.get("csv_separator")
    if "csv_separator" in raw and separator not in CSV_SEPARATORS:
        supported = " or ".join(repr(item) for item in CSV_SEPARATORS)
        message = f"unsupported separator {separator!r}; supported separators: {supported}"
        problems.append(Problem(_at(path, "csv_separator"), message))
    return Output(
        format=output_format,
        dir=None if directory is _BAD else directory,
        csv_separator=separator,
    )


def _parse_spec(raw: Any, problems: list[Problem]) -> Spec | None:
    if not isinstance(raw, Mapping):
        problems.append(Problem("", "the spec must be a mapping with 'version' and 'entities'"))
        return None
    allowed = frozenset({"version", "seed", "entities", "output", "types"})
    _unknown_keys(raw, allowed, "", problems)

    if "version" not in raw:
        problems.append(Problem("version", f"is required; use version: {SUPPORTED_VERSION}"))
    elif not _is_int(raw["version"]) or raw["version"] != SUPPORTED_VERSION:
        message = f"only version {SUPPORTED_VERSION} is supported, got {raw['version']!r}"
        problems.append(Problem("version", message))

    seed = _read(
        raw, "seed", lambda v: _is_int(v) and v >= 0, "a non-negative integer", "", problems
    )
    output = _parse_output(raw["output"], problems) if "output" in raw else Output()
    types, broken = _parse_types(raw["types"], problems) if "types" in raw else ({}, set())

    entities: dict[str, Entity] = {}
    raw_entities = raw.get("entities")
    if "entities" not in raw:
        problems.append(Problem("entities", "is required"))
    elif not isinstance(raw_entities, Mapping):
        problems.append(Problem("entities", "must be a mapping of entity name to definition"))
    elif not raw_entities:
        problems.append(Problem("entities", "at least one entity is required"))
    else:
        drafts: dict[Any, dict[Any, Field | None] | None] = {}
        shared = _Context(entity=None, types=types, broken=broken)
        for name, raw_entity in raw_entities.items():
            ctx = replace(shared, entity=name)
            entity, drafts[name] = _parse_entity(
                name, raw_entity, _at("entities", name), problems, ctx
            )
            if entity is not None:
                entities[name] = entity
        _check_references(shared.references, drafts, problems)
        _check_templates(shared.templates, drafts, problems)

    if problems:
        return None
    spec = Spec(version=SUPPORTED_VERSION, entities=entities, seed=seed, output=output)
    _check_columns(spec, problems)
    return None if problems else spec


# --- rules that span fields and entities ------------------------------------------------------


def _check_references(
    references: list[tuple[Any, str, ReferenceField, str]],
    drafts: Mapping[Any, dict[Any, Field | None] | None],
    problems: list[Problem],
) -> None:
    """Check every reference's target exists and that references do not form a cycle.

    Works on fields as far as they parsed, so one unrelated problem in an entity does not hide
    a bad reference elsewhere.
    """
    edges: dict[Any, list[Any]] = {}
    for entity, path, field, note in references:
        if field.entity == entity:
            problems.append(Problem(path, f"an entity cannot reference itself{note}"))
        elif field.entity not in drafts:
            known = ", ".join(str(name) for name in drafts)
            message = f"unknown entity {field.entity!r}; entities in this spec: {known}{note}"
            problems.append(Problem(path, message))
        else:
            edges.setdefault(entity, []).append(field.entity)
            _, error = _lookup(drafts, field.entity, field.field, visiting=set())
            if error:
                problems.append(Problem(path, f"{error}{note}"))

    cycle = _find_cycle(edges)
    if cycle:
        message = f"circular reference between entities: {' -> '.join(map(str, cycle))}"
        problems.append(Problem("entities", message))


def _lookup(
    drafts: Mapping[Any, dict[Any, Field | None] | None],
    entity: Any,
    path: str,
    visiting: set[tuple[Any, str]],
) -> tuple[Field | None, str | None]:
    """Find the field at `path` in `entity`, passing through references to objects.

    Returns the field and no error; or None and an error message; or None and no message when
    the answer is unknown because of a problem that is reported elsewhere.
    """
    if (entity, path) in visiting:  # a cycle, reported once by the caller
        return None, None
    visiting = visiting | {(entity, path)}
    fields = drafts.get(entity)
    walked = str(entity)
    field: Field | None = None
    for index, segment in enumerate(path.split(".")):
        if fields is None:
            return None, None
        if segment not in fields:
            if index == 0:
                return None, f"entity {entity!r} has no field {segment!r}"
            return None, f"'{walked}' has no field {segment!r}"
        field = fields[segment]
        walked = f"{walked}.{segment}"
        target = _resolve(drafts, field, visiting)
        if target is None:
            return None, None
        fields = target.fields if isinstance(target, ObjectField) else {}
    return field, None


def _resolve(drafts, field: Field | None, visiting: set[tuple[Any, str]]) -> Field | None:
    """Follow references to the field they copy; None if that cannot be determined."""
    while isinstance(field, ReferenceField):
        field, _ = _lookup(drafts, field.entity, field.field, visiting)
    return field


def _check_templates(
    templates: list[tuple[Any, str, str, TemplateField, str]],
    drafts: Mapping[Any, dict[Any, Field | None] | None],
    problems: list[Problem],
) -> None:
    """Check that every placeholder names a single-valued field, and that none is circular."""
    edges: dict[tuple[Any, str], list[tuple[Any, str]]] = {}
    template_paths = {(entity, data_path) for entity, _, data_path, _, _ in templates}
    for entity, problem_path, data_path, field, note in templates:
        where = _at(problem_path, "template")
        for part in field.parts:
            if isinstance(part, str) or part.target is None:
                continue
            shown = "{" + "^" * part.up + part.path + "}"
            found, error = _lookup(drafts, entity, part.target, visiting=set())
            if error:
                hint = _outward_hint(drafts, entity, data_path, part)
                message = f"placeholder {shown}: there is no field {part.path!r} at that level"
                problems.append(Problem(where, message + hint + note))
            elif isinstance(_resolve(drafts, found, set()), ObjectField):
                message = (
                    f"placeholder {shown} names an object; a placeholder must name a field "
                    f"inside the object, such as {{{part.path}.city}}"
                )
                problems.append(Problem(where, message + note))
            elif (entity, part.target) in template_paths:
                edges.setdefault((entity, data_path), []).append((entity, part.target))

    cycle = _find_cycle(edges)
    if cycle:
        names = " -> ".join(path for _, path in cycle)
        owner = _at("entities", cycle[0][0]) if cycle[0][0] is not None else "types"
        problems.append(Problem(owner, f"templates depend on each other: {names}"))


def _outward_hint(drafts, entity: Any, data_path: str, part: Placeholder) -> str:
    """Suggest the `^` form when the field exists one or more levels further out."""
    scope = data_path.split(".")[:-1]
    for extra in range(1, len(scope) - part.up + 1):
        base = scope[: len(scope) - part.up - extra]
        found, error = _lookup(drafts, entity, ".".join([*base, part.path]), visiting=set())
        if found is not None and error is None:
            return f"; did you mean {{{'^' * (part.up + extra)}{part.path}}}?"
    return ""


def _find_cycle(edges: Mapping[Any, list[Any]]) -> list[Any] | None:
    """Return the nodes along one cycle (first repeated at the end), or None."""
    done: set[Any] = set()

    def visit(node: Any, trail: list[Any]) -> list[Any] | None:
        if node in trail:
            return trail[trail.index(node) :] + [node]
        if node in done:
            return None
        trail.append(node)
        for target in edges.get(node, ()):
            cycle = visit(target, trail)
            if cycle:
                return cycle
        trail.pop()
        done.add(node)
        return None

    for node in edges:
        cycle = visit(node, [])
        if cycle:
            return cycle
    return None


def _check_columns(spec: Spec, problems: list[Problem]) -> None:
    """Reject a spec in which two fields of an entity would share a CSV column name."""
    separator = spec.output.csv_separator or "."
    if separator == ".":
        return  # names cannot contain dots, so path-named columns cannot collide
    for name in spec.entities:
        seen: dict[str, str] = {}
        for path in leaf_paths(spec, name):
            column = path.replace(".", separator)
            if column in seen:
                message = (
                    f"fields {seen[column]!r} and {path!r} would both be written to the CSV "
                    f"column {column!r}; rename one, or use the default separator '.'"
                )
                problems.append(Problem(_at("entities", name), message))
            seen[column] = path


# --- reading the structure of a validated spec ------------------------------------------------


def iter_fields(fields: Mapping[str, Field], prefix: str = "") -> Iterator[tuple[str, Field]]:
    """Yield every field under `fields` with its path, objects before the fields inside them."""
    for name, field in fields.items():
        path = f"{prefix}{name}"
        yield path, field
        if isinstance(field, ObjectField):
            yield from iter_fields(field.fields, f"{path}.")


def follow(spec: Spec, field: Field) -> Field:
    """Return the field a reference ultimately copies; any other field is returned unchanged."""
    while isinstance(field, ReferenceField):
        field = field_at(spec, field.entity, field.field)
    return field


def field_at(spec: Spec, entity: str, path: str) -> Field:
    """Return the field at `path` in `entity`, passing through references to objects."""
    fields: Mapping[str, Field] = spec.entities[entity].fields
    field: Field | None = None
    for segment in path.split("."):
        field = fields[segment]
        target = follow(spec, field)
        fields = target.fields if isinstance(target, ObjectField) else {}
    return field


def hidden_paths(spec: Spec, field: Field, prefix: str = "") -> tuple[str, ...]:
    """Return the paths, relative to `field`, of the hidden fields inside the object it holds."""
    target = follow(spec, field)
    if not isinstance(target, ObjectField):
        return ()
    found: list[str] = []
    for name, inner in target.fields.items():
        if inner.hidden:
            found.append(f"{prefix}{name}")
        else:
            found.extend(hidden_paths(spec, inner, f"{prefix}{name}."))
    return tuple(found)


def leaf_paths(spec: Spec, entity: str) -> tuple[str, ...]:
    """Return the paths of an entity's visible fields that hold a single value, in declared order.

    These are the columns CSV export writes. An object contributes one path per field inside
    it, and so does a reference that copies an object. Hidden fields are left out.
    """

    def walk(fields: Mapping[str, Field], prefix: str) -> Iterator[str]:
        for name, field in fields.items():
            if field.hidden:
                continue
            target = follow(spec, field)
            if isinstance(target, ObjectField):
                yield from walk(target.fields, f"{prefix}{name}.")
            else:
                yield f"{prefix}{name}"

    return tuple(walk(spec.entities[entity].fields, ""))
