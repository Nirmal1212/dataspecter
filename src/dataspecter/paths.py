"""Reading values by path from nested records."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


def reader(path: str) -> Callable[[Mapping[str, Any]], Any]:
    """Return a function that reads `path` (such as ``address.city``) from a record.

    A null object anywhere along the path yields None.
    """
    parts = path.split(".")
    if len(parts) == 1:
        name = parts[0]
        return lambda record: record[name]

    def read(record: Mapping[str, Any]) -> Any:
        value: Any = record
        for part in parts:
            if value is None:
                return None
            value = value[part]
        return value

    return read


def copy_value(value: Any) -> Any:
    """Copy a record value. Objects are rebuilt level by level; everything else is immutable."""
    if isinstance(value, dict):
        return {name: copy_value(item) for name, item in value.items()}
    return value


def remove(record: dict[str, Any], path: str) -> None:
    """Delete the value at `path` from a record, if the objects leading to it are present."""
    *parents, name = path.split(".")
    value: Any = record
    for part in parents:
        value = value.get(part) if isinstance(value, dict) else None
        if value is None:
            return
    if isinstance(value, dict):
        value.pop(name, None)
