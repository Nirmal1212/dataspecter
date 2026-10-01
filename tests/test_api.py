"""The importable interface (python-api capability)."""

import json
from datetime import date
from pathlib import Path

import pytest

import dataspecter

RAW = {
    "version": 1,
    "entities": {
        "customer": {
            "count": 100,
            "fields": {
                "id": {"type": "sequence"},
                "age": {"type": "integer", "min": 18, "max": 90},
                "signup": {"type": "date", "min": "2024-01-01", "max": "2024-12-31"},
                "email": {"type": "constant", "value": "x@example.com", "null_probability": 1},
            },
        },
        "order": {
            "count": 250,
            "fields": {
                "id": {"type": "uuid"},
                "customer_id": {"type": "reference", "entity": "customer", "field": "id"},
            },
        },
    },
}


def raw(**changes) -> dict:
    return {**RAW, **changes}


# --- generating -------------------------------------------------------------------------------


def test_iterating_an_entitys_records():
    simulation = dataspecter.generate(dataspecter.load_spec(RAW), seed=42)
    records = list(simulation.records("customer"))

    assert simulation.entities == ("customer", "order")
    assert len(records) == 100
    assert all(list(record) == ["id", "age", "signup", "email"] for record in records)


def test_records_use_native_python_types():
    simulation = dataspecter.generate(dataspecter.load_spec(RAW), seed=42)
    record = next(simulation.records("customer"))

    assert type(record["age"]) is int
    assert type(record["signup"]) is date
    assert record["email"] is None


def test_seed_is_exposed_and_reproduces_the_run():
    spec = dataspecter.load_spec(RAW)
    first = dataspecter.generate(spec)
    second = dataspecter.generate(spec, seed=first.seed)

    assert list(first.records("order")) == list(second.records("order"))


# --- writing ----------------------------------------------------------------------------------


def test_write_reports_seed_rows_and_paths(tmp_path):
    result = dataspecter.write(dataspecter.load_spec(RAW), out_dir=tmp_path, seed=42)

    assert result.seed == 42
    assert result.format == "csv"
    assert [(entity.name, entity.rows) for entity in result.entities] == [
        ("customer", 100),
        ("order", 250),
    ]
    assert [entity.path for entity in result.entities] == [
        tmp_path / "customer.csv",
        tmp_path / "order.csv",
    ]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["customer.csv", "order.csv"]


def test_defaults_are_csv_in_the_output_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = dataspecter.write(dataspecter.load_spec(RAW))

    assert result.directory == Path("output")
    assert (tmp_path / "output" / "customer.csv").is_file()


def test_spec_output_block_overrides_the_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec = dataspecter.load_spec(raw(output={"format": "jsonl", "dir": "data/run1"}))

    dataspecter.write(spec)

    assert (tmp_path / "data" / "run1" / "order.jsonl").is_file()


def test_arguments_override_the_spec_output_block(tmp_path):
    spec = dataspecter.load_spec(raw(seed=1, output={"format": "jsonl", "dir": "ignored"}))

    result = dataspecter.write(spec, out_dir=tmp_path / "chosen", format="json", seed=2)

    assert result.seed == 2
    assert len(json.loads((tmp_path / "chosen" / "customer.json").read_text("utf-8"))) == 100
    assert not Path("ignored").exists()


def test_unsupported_format_writes_nothing(tmp_path):
    target = tmp_path / "out"

    with pytest.raises(ValueError, match="supported formats: csv, json, jsonl"):
        dataspecter.write(dataspecter.load_spec(RAW), out_dir=target, format="xml")
    assert not target.exists()


def test_same_seed_writes_identical_files(tmp_path):
    spec = dataspecter.load_spec(RAW)
    dataspecter.write(spec, out_dir=tmp_path / "a", seed=42)
    dataspecter.write(spec, out_dir=tmp_path / "b", seed=42)

    for name in ("customer.csv", "order.csv"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()


def test_unwritable_output_raises_export_error(tmp_path):
    blocker = tmp_path / "out"
    blocker.write_text("not a directory", encoding="utf-8")

    with pytest.raises(dataspecter.ExportError):
        dataspecter.write(dataspecter.load_spec(RAW), out_dir=blocker)


# --- errors and side effects ------------------------------------------------------------------


def test_invalid_spec_raises_with_every_problem():
    broken = raw()
    broken["entities"] = {
        "customer": {
            "count": 0,
            "fields": {"age": {"type": "integer", "min": 90, "max": 18}},
        }
    }

    with pytest.raises(dataspecter.SpecError) as caught:
        dataspecter.load_spec(broken)
    paths = [problem.path for problem in caught.value.problems]
    assert paths == ["entities.customer.count", "entities.customer.fields.age"]


def test_nothing_is_printed(tmp_path, capsys):
    spec = dataspecter.load_spec(RAW)
    list(dataspecter.generate(spec, seed=1).records("order"))
    dataspecter.write(spec, out_dir=tmp_path, format="jsonl", seed=1)

    assert capsys.readouterr() == ("", "")


def test_public_names():
    assert set(dataspecter.__all__) == {
        "ExportError",
        "SpecError",
        "__version__",
        "generate",
        "load_spec",
        "write",
    }
