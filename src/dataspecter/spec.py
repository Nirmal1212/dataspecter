"""The simulation spec: its data model, loading from YAML or JSON, and validation."""

from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from pathlib import Path
from typing import Any, ClassVar

import yaml

from dataspecter.errors import Problem, SpecError

SUPPORTED_VERSION = 1
FORMATS = ("csv", "json", "jsonl")

_EXTENSIONS = (".yaml", ".yml", ".json")
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NAME_RULE = (
    "names must start with a letter or underscore and contain only letters, digits and underscores"
)
_WEIGHT_RULE = "weights must be non-negative numbers with a sum greater than zero"
_REFERENCE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)")
_BAD = object()  # a key that was present but invalid, and has already been reported


# --- data model -------------------------------------------------------------------------------


@dataclass(frozen=True)
class WeightedRange:
    min: float
    max: float
    weight: float


@dataclass(frozen=True, kw_only=True)
class _Field:
    null_probability: float = 0.0


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
        if not isinstance(item, Mapping):
            problems.append(Problem(item_path, "must be a mapping with min, max and weight"))
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
        lambda v: isinstance(v, list) and bool(v) and all(map(_is_scalar, v)),
        "a non-empty list of strings, numbers or booleans",
        path,
        problems,
    )
    weights = _read(
        raw, "weights", lambda v: isinstance(v, list), "a list of numbers", path, problems
    )
    if _usable(weights):
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


def _reference(raw, path, problems, common):
    _require(raw, ("entity", "field"), path, problems)
    entity = _read(raw, "entity", lambda v: isinstance(v, str), "an entity name", path, problems)
    field = _read(raw, "field", lambda v: isinstance(v, str), "a field name", path, problems)
    link = _read(raw, "link", _is_name, f"a link name ({_NAME_RULE})", path, problems)
    if not _usable(entity, field) or link is _BAD:
        return None
    return ReferenceField(entity=entity, field=field, link=link, **common)


_COMMON_KEYS = frozenset({"type", "null_probability"})
_NUMERIC_KEYS = frozenset({"min", "max", "distribution", "mean", "stddev", "ranges"})

# type name -> (keys the type accepts besides the common ones, parser)
_FIELD_TYPES: dict[str, tuple[frozenset[str], Callable[..., Any]]] = {
    "integer": (_NUMERIC_KEYS, _integer),
    "float": (_NUMERIC_KEYS | {"precision"}, _float),
    "boolean": (frozenset({"true_probability"}), _boolean),
    "choice": (frozenset({"values", "weights"}), _choice),
    "date": (frozenset({"min", "max"}), _date),
    "datetime": (frozenset({"min", "max"}), _datetime),
    "sequence": (frozenset({"start", "step"}), _sequence),
    "uuid": (frozenset(), _uuid),
    "constant": (frozenset({"value"}), _constant),
    "reference": (frozenset({"entity", "field", "link"}), _reference),
}


def _parse_field(raw: Any, path: str, problems: list[Problem]) -> Field | None:
    start = len(problems)
    supported = f"supported types: {', '.join(_FIELD_TYPES)}"
    if isinstance(raw, str):
        parts = _reference_parts(raw)
        if parts is None:
            message = f"{raw!r} is not a field definition; a reference is written '$entity.field'"
            problems.append(Problem(path, message))
            return None
        return ReferenceField(entity=parts[0], field=parts[1])
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
    common = {"null_probability": 0.0 if null_probability is _BAD else null_probability}
    field = parser(raw, path, problems, common)
    return field if len(problems) == start else None


# --- document parsers -------------------------------------------------------------------------


def _parse_entity(name: Any, raw: Any, path: str, problems: list[Problem]) -> Entity | None:
    start = len(problems)
    if not _is_name(name):
        problems.append(Problem(path, f"invalid entity name {name!r}; {_NAME_RULE}"))
    if not isinstance(raw, Mapping):
        problems.append(Problem(path, "must be a mapping with 'count' and 'fields'"))
        return None
    _unknown_keys(raw, frozenset({"count", "fields"}), path, problems)
    _require(raw, ("count", "fields"), path, problems)
    count = _read(
        raw, "count", lambda v: _is_int(v) and v >= 1, "an integer of 1 or more", path, problems
    )

    fields: dict[str, Field] = {}
    raw_fields = raw.get("fields")
    if "fields" in raw:
        fields_path = _at(path, "fields")
        if not isinstance(raw_fields, Mapping):
            problems.append(Problem(fields_path, "must be a mapping of field name to definition"))
        elif not raw_fields:
            problems.append(Problem(fields_path, "at least one field is required"))
        else:
            for field_name, raw_field in raw_fields.items():
                field_path = _at(fields_path, field_name)
                if not _is_name(field_name):
                    message = f"invalid field name {field_name!r}; {_NAME_RULE}"
                    problems.append(Problem(field_path, message))
                field = _parse_field(raw_field, field_path, problems)
                if field is not None:
                    fields[field_name] = field

    if len(problems) > start:
        return None
    return Entity(name=name, count=count, fields=fields)


def _parse_output(raw: Any, problems: list[Problem]) -> Output:
    path = "output"
    if not isinstance(raw, Mapping):
        problems.append(Problem(path, "must be a mapping with 'format' and/or 'dir'"))
        return Output()
    _unknown_keys(raw, frozenset({"format", "dir"}), path, problems)
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
    return Output(format=output_format, dir=None if directory is _BAD else directory)


def _parse_spec(raw: Any, problems: list[Problem]) -> Spec | None:
    if not isinstance(raw, Mapping):
        problems.append(Problem("", "the spec must be a mapping with 'version' and 'entities'"))
        return None
    _unknown_keys(raw, frozenset({"version", "seed", "entities", "output"}), "", problems)

    if "version" not in raw:
        problems.append(Problem("version", f"is required; use version: {SUPPORTED_VERSION}"))
    elif not _is_int(raw["version"]) or raw["version"] != SUPPORTED_VERSION:
        message = f"only version {SUPPORTED_VERSION} is supported, got {raw['version']!r}"
        problems.append(Problem("version", message))

    seed = _read(
        raw, "seed", lambda v: _is_int(v) and v >= 0, "a non-negative integer", "", problems
    )
    output = _parse_output(raw["output"], problems) if "output" in raw else Output()

    entities: dict[str, Entity] = {}
    raw_entities = raw.get("entities")
    if "entities" not in raw:
        problems.append(Problem("entities", "is required"))
    elif not isinstance(raw_entities, Mapping):
        problems.append(Problem("entities", "must be a mapping of entity name to definition"))
    elif not raw_entities:
        problems.append(Problem("entities", "at least one entity is required"))
    else:
        for name, raw_entity in raw_entities.items():
            entity = _parse_entity(name, raw_entity, _at("entities", name), problems)
            if entity is not None:
                entities[name] = entity
        _check_references(raw_entities, problems)

    if problems:
        return None
    return Spec(version=SUPPORTED_VERSION, entities=entities, seed=seed, output=output)


# --- rules that span entities -----------------------------------------------------------------


def _check_references(raw_entities: Mapping[Any, Any], problems: list[Problem]) -> None:
    """Check every reference's target exists and that references do not form a cycle.

    Works from the raw mapping rather than the parsed entities, so one unrelated problem in an
    entity does not hide a bad reference elsewhere.
    """
    declared: dict[Any, set[Any] | None] = {}
    for name, raw_entity in raw_entities.items():
        raw_fields = raw_entity.get("fields") if isinstance(raw_entity, Mapping) else None
        declared[name] = set(raw_fields) if isinstance(raw_fields, Mapping) else None

    edges: dict[str, list[str]] = {}
    for name, raw_entity in raw_entities.items():
        if declared[name] is None:
            continue
        for field_name, raw_field in raw_entity["fields"].items():
            reference = _raw_reference(raw_field)
            if reference is None:
                continue
            target, target_field = reference
            path = _at(_at(_at("entities", name), "fields"), field_name)
            if target == name:
                problems.append(Problem(path, "an entity cannot reference itself"))
            elif target not in declared:
                known = ", ".join(str(entity) for entity in declared)
                message = f"unknown entity {target!r}; entities in this spec: {known}"
                problems.append(Problem(path, message))
            else:
                target_fields = declared[target]
                if target_fields is not None and target_field not in target_fields:
                    message = f"entity {target!r} has no field {target_field!r}"
                    problems.append(Problem(path, message))
                edges.setdefault(name, []).append(target)

    cycle = _find_cycle(edges)
    if cycle:
        message = f"circular reference between entities: {' -> '.join(cycle)}"
        problems.append(Problem("entities", message))


def _raw_reference(raw_field: Any) -> tuple[str, str] | None:
    """Return the (entity, field) a raw field definition refers to, in either form, if any."""
    if isinstance(raw_field, str):
        return _reference_parts(raw_field)
    if isinstance(raw_field, Mapping) and raw_field.get("type") == "reference":
        target, target_field = raw_field.get("entity"), raw_field.get("field")
        if isinstance(target, str) and isinstance(target_field, str):
            return target, target_field
    return None  # not a reference, or malformed and already reported by the field parser


def _find_cycle(edges: Mapping[str, list[str]]) -> list[str] | None:
    """Return the entities along one cycle (first repeated at the end), or None."""
    done: set[str] = set()

    def visit(node: str, trail: list[str]) -> list[str] | None:
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
