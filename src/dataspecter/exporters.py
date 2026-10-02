"""File export: CSV, JSON and JSON Lines writers behind one small interface."""

from __future__ import annotations

import csv
import json
import os
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any, TextIO

from dataspecter.errors import ExportError
from dataspecter.paths import reader

Rows = Iterable[Mapping[str, Any]]
# A writer consumes rows one at a time, writes each as it arrives, and returns how many it wrote.
# It is given the entity's column paths and the separator CSV uses to name nested columns.
Writer = Callable[[TextIO, Sequence[str], Rows, str], int]


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, date):  # covers datetime, which is a date subclass
        return value.isoformat()
    return value


def _json_default(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"cannot write {value!r} as JSON")


def _json_line(row: Mapping[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False, default=_json_default)


def _write_csv(file: TextIO, columns: Sequence[str], rows: Rows, separator: str) -> int:
    writer = csv.writer(file, lineterminator="\n")
    writer.writerow([column.replace(".", separator) for column in columns])
    count = 0
    if not any("." in column for column in columns):
        for row in rows:
            writer.writerow([_csv_value(row[name]) for name in columns])
            count += 1
        return count
    # Nested records are flattened: one column per path, empty where an object is null.
    readers = [reader(column) for column in columns]
    for row in rows:
        writer.writerow([_csv_value(read(row)) for read in readers])
        count += 1
    return count


def _write_json(file: TextIO, columns: Sequence[str], rows: Rows, separator: str) -> int:
    # The array is written piece by piece, so the rows never have to be held together.
    count = 0
    file.write("[")
    for row in rows:
        file.write(",\n" if count else "\n")
        file.write(_json_line(row))
        count += 1
    file.write("\n]\n")
    return count


def _write_jsonl(file: TextIO, columns: Sequence[str], rows: Rows, separator: str) -> int:
    count = 0
    for row in rows:
        file.write(_json_line(row))
        file.write("\n")
        count += 1
    return count


# Format name -> writer. The name is also the file extension.
WRITERS: dict[str, Writer] = {"csv": _write_csv, "json": _write_json, "jsonl": _write_jsonl}


def check_format(name: str) -> str:
    if name not in WRITERS:
        raise ValueError(f"unsupported format {name!r}; supported formats: {', '.join(WRITERS)}")
    return name


def prepare_directory(directory: str | os.PathLike[str]) -> Path:
    """Create the output directory, with any missing parents, if it does not exist."""
    path = Path(directory)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ExportError(path, exc.strerror or str(exc)) from exc
    return path


def export(
    directory: Path,
    entity: str,
    fmt: str,
    columns: Sequence[str],
    rows: Rows,
    separator: str = ".",
) -> tuple[Path, int]:
    """Write one entity to ``<directory>/<entity>.<fmt>``, replacing any existing file.

    `columns` are the paths of the entity's single-valued fields, such as ``address.city``.
    Returns the path written and the number of rows.
    """
    path = directory / f"{entity}.{fmt}"
    try:
        # newline="" stops Windows turning "\n" into "\r\n", so output is identical everywhere.
        with path.open("w", encoding="utf-8", newline="") as file:
            return path, WRITERS[fmt](file, columns, rows, separator)
    except OSError as exc:
        raise ExportError(path, exc.strerror or str(exc)) from exc
