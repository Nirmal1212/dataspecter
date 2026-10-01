"""Writing entities to CSV, JSON and JSON Lines files (file-export capability)."""

import csv
import json
from datetime import date, datetime

import pytest

from dataspecter.errors import ExportError
from dataspecter.exporters import (
    WRITERS,
    _csv_value,
    _json_line,
    check_format,
    export,
    prepare_directory,
)
from dataspecter.spec import FORMATS

FIELDS = ["id", "name", "active", "joined", "seen", "score"]
ROWS = [
    {
        "id": 1,
        "name": "Smith, John",
        "active": True,
        "joined": date(2024, 3, 5),
        "seen": datetime(2024, 3, 5, 14, 30, 0),
        "score": 31.5,
    },
    {
        "id": 2,
        "name": 'Ann "Ace" Lee',
        "active": False,
        "joined": None,
        "seen": None,
        "score": None,
    },
    {"id": 3, "name": "Zoë\nNewline", "active": None, "joined": None, "seen": None, "score": 7},
]


def write(tmp_path, fmt, rows=ROWS, fields=FIELDS):
    path, count = export(tmp_path, "customer", fmt, fields, iter(rows))
    return path, count


# --- registry and value serialisation ---------------------------------------------------------


def test_registry_covers_every_supported_format():
    assert tuple(WRITERS) == FORMATS


def test_unsupported_format_lists_the_supported_ones():
    with pytest.raises(ValueError, match="supported formats: csv, json, jsonl"):
        check_format("xml")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, ""),
        (True, "true"),
        (False, "false"),
        (date(2024, 3, 5), "2024-03-05"),
        (datetime(2024, 3, 5, 14, 30), "2024-03-05T14:30:00"),
        (31, 31),
        ("text", "text"),
    ],
)
def test_csv_value_serialisation(value, expected):
    assert _csv_value(value) == expected


def test_json_value_serialisation():
    line = _json_line({"age": 31, "active": True, "email": None, "day": date(2024, 3, 5)})

    assert line == '{"age": 31, "active": true, "email": null, "day": "2024-03-05"}'


# --- CSV --------------------------------------------------------------------------------------


def test_csv_header_and_rows(tmp_path):
    rows = [{"id": number, "tier": "free"} for number in range(1, 101)]
    path, count = write(tmp_path, "csv", rows, ["id", "tier"])

    lines = path.read_text(encoding="utf-8").splitlines()
    assert count == 100
    assert len(lines) == 101
    assert lines[0] == "id,tier"
    assert lines[1] == "1,free"


def test_csv_value_containing_a_comma_is_quoted(tmp_path):
    path, _ = write(tmp_path, "csv")

    assert '"Smith, John"' in path.read_text(encoding="utf-8")


def test_csv_null_is_an_empty_field(tmp_path):
    path, _ = write(
        tmp_path, "csv", [{"id": 1, "email": None, "active": True}], ["id", "email", "active"]
    )

    assert path.read_text(encoding="utf-8").splitlines()[1] == "1,,true"


def test_csv_round_trips_awkward_values(tmp_path):
    path, _ = write(tmp_path, "csv")

    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert [row["name"] for row in rows] == ["Smith, John", 'Ann "Ace" Lee', "Zoë\nNewline"]
    assert rows[0]["joined"] == "2024-03-05"
    assert rows[0]["seen"] == "2024-03-05T14:30:00"
    assert rows[1]["active"] == "false"


def test_csv_uses_lf_line_endings_on_every_platform(tmp_path):
    path, _ = write(tmp_path, "csv", [{"id": 1}, {"id": 2}], ["id"])

    assert path.read_bytes() == b"id\n1\n2\n"


# --- JSON and JSON Lines ----------------------------------------------------------------------


def test_json_is_an_array_of_objects_with_native_types(tmp_path):
    path, count = write(tmp_path, "json")

    data = json.loads(path.read_text(encoding="utf-8"))
    assert count == len(data) == 3
    assert list(data[0]) == FIELDS
    assert data[0] == {
        "id": 1,
        "name": "Smith, John",
        "active": True,
        "joined": "2024-03-05",
        "seen": "2024-03-05T14:30:00",
        "score": 31.5,
    }
    assert data[1]["joined"] is None
    assert data[2]["name"] == "Zoë\nNewline"


def test_json_with_one_hundred_rows(tmp_path):
    rows = ({"id": number} for number in range(100))
    path, _ = write(tmp_path, "json", rows, ["id"])

    assert len(json.loads(path.read_text(encoding="utf-8"))) == 100


def test_jsonl_has_one_object_per_line(tmp_path):
    rows = ({"id": number, "note": "a\nb"} for number in range(100))
    path, count = write(tmp_path, "jsonl", rows, ["id", "note"])

    lines = path.read_text(encoding="utf-8").splitlines()
    assert count == len(lines) == 100
    assert [json.loads(line)["id"] for line in lines] == list(range(100))


def test_non_ascii_text_is_written_as_utf8(tmp_path):
    path, _ = write(tmp_path, "jsonl")

    assert "Zoë".encode() in path.read_bytes()


# --- files and directories --------------------------------------------------------------------


@pytest.mark.parametrize("fmt", FORMATS)
def test_file_is_named_after_the_entity_and_format(tmp_path, fmt):
    path, _ = write(tmp_path, fmt)

    assert path == tmp_path / f"customer.{fmt}"
    assert [entry.name for entry in tmp_path.iterdir()] == [f"customer.{fmt}"]


def test_missing_directory_is_created_with_its_parents(tmp_path):
    directory = prepare_directory(tmp_path / "out" / "run1")

    assert directory.is_dir()
    assert prepare_directory(directory) == directory  # already existing is fine


def test_existing_file_is_replaced(tmp_path):
    write(tmp_path, "csv", [{"id": number} for number in range(50)], ["id"])
    path, _ = write(tmp_path, "csv", [{"id": 999}], ["id"])

    assert path.read_text(encoding="utf-8") == "id\n999\n"


def test_directory_that_cannot_be_created(tmp_path):
    blocker = tmp_path / "out"
    blocker.write_text("a file where the directory should be", encoding="utf-8")

    with pytest.raises(ExportError) as caught:
        prepare_directory(blocker / "run1")
    assert caught.value.path == blocker / "run1"
    assert caught.value.reason


def test_file_that_cannot_be_written(tmp_path):
    (tmp_path / "customer.csv").mkdir()  # a directory sits where the file should go

    with pytest.raises(ExportError) as caught:
        write(tmp_path, "csv")
    assert caught.value.path == tmp_path / "customer.csv"
    assert "customer.csv" in str(caught.value)
