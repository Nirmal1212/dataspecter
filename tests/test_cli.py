"""The `dataspecter` command (cli capability)."""

import json

import pytest

import dataspecter
from dataspecter.cli import main

RAW = {
    "version": 1,
    "seed": 42,
    "output": {"format": "csv", "dir": "data"},
    "entities": {
        "customer": {
            "count": 20,
            "fields": {
                "id": {"type": "sequence"},
                "age": {"type": "integer", "min": 18, "max": 90},
            },
        },
        "order": {
            "count": 50,
            "fields": {
                "id": {"type": "uuid"},
                "customer_id": {"type": "reference", "entity": "customer", "field": "id"},
            },
        },
    },
}


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """Run each test in an empty directory, since relative output paths resolve against it."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def spec_file(workdir, raw=RAW, name="shop.json"):
    path = workdir / name
    path.write_text(json.dumps(raw), encoding="utf-8")
    return str(path)


def written(workdir):
    return sorted(
        str(path.relative_to(workdir)).replace("\\", "/") for path in workdir.rglob("*.*")
    )


# --- generate ---------------------------------------------------------------------------------


def test_successful_generation(workdir, capsys):
    code = main(["generate", spec_file(workdir)])

    out, err = capsys.readouterr()
    assert code == 0
    assert err == ""
    assert "Seed: 42" in out
    customer_line = next(line for line in out.splitlines() if line.startswith("customer"))
    assert "20 rows" in customer_line and "customer.csv" in customer_line
    order_line = next(line for line in out.splitlines() if line.startswith("order"))
    assert "50 rows" in order_line and "order.csv" in order_line
    assert written(workdir) == ["data/customer.csv", "data/order.csv", "shop.json"]


def test_seed_is_reported_for_unseeded_runs(workdir, capsys):
    unseeded = {key: value for key, value in RAW.items() if key != "seed"}
    path = spec_file(workdir, unseeded)

    assert main(["generate", path, "--out", "first"]) == 0
    seed = capsys.readouterr().out.splitlines()[0].removeprefix("Seed: ")
    assert seed.isdigit()

    assert main(["generate", path, "--out", "again", "--seed", seed]) == 0
    assert (workdir / "first" / "order.csv").read_bytes() == (
        workdir / "again" / "order.csv"
    ).read_bytes()


def test_output_directory_override(workdir):
    assert main(["generate", spec_file(workdir), "--out", "tmp/run1"]) == 0

    assert written(workdir) == ["shop.json", "tmp/run1/customer.csv", "tmp/run1/order.csv"]


def test_format_override(workdir):
    assert main(["generate", spec_file(workdir), "--format", "jsonl"]) == 0

    lines = (workdir / "data" / "customer.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 20
    assert json.loads(lines[0])["id"] == 1


def test_seed_override(workdir, capsys):
    path = spec_file(workdir)

    assert main(["generate", path, "--seed", "7", "--out", "seven"]) == 0
    assert "Seed: 7" in capsys.readouterr().out
    main(["generate", path, "--out", "default"])
    assert (workdir / "seven" / "customer.csv").read_bytes() != (
        workdir / "default" / "customer.csv"
    ).read_bytes()


# --- validate ---------------------------------------------------------------------------------


def test_validate_a_valid_spec(workdir, capsys):
    code = main(["validate", spec_file(workdir)])

    out, err = capsys.readouterr()
    assert code == 0
    assert "is valid" in out
    assert err == ""
    assert written(workdir) == ["shop.json"]


def broken_spec():
    raw = json.loads(json.dumps(RAW))
    raw["entities"]["customer"]["fields"]["age"] = {"type": "integer", "min": 90, "max": 18}
    raw["entities"]["order"]["fields"]["customer_id"]["entity"] = "client"
    return raw


def test_validate_an_invalid_spec(workdir, capsys):
    code = main(["validate", spec_file(workdir, broken_spec())])

    out, err = capsys.readouterr()
    assert code == 2
    assert out == ""
    assert "entities.customer.fields.age: min must not exceed max" in err
    assert "entities.order.fields.customer_id: unknown entity 'client'" in err


# --- errors and exit codes --------------------------------------------------------------------


def test_invalid_spec_on_generate_writes_nothing(workdir, capsys):
    code = main(["generate", spec_file(workdir, broken_spec())])

    out, err = capsys.readouterr()
    assert code == 2
    assert out == ""
    assert "2 problem(s)" in err
    assert "min must not exceed max" in err and "unknown entity 'client'" in err
    assert written(workdir) == ["shop.json"]


def test_missing_spec_file(workdir, capsys):
    code = main(["generate", "missing.yaml"])

    err = capsys.readouterr().err
    assert code == 2
    assert "missing.yaml" in err and "file not found" in err


def test_unsupported_format_option(workdir, capsys):
    with pytest.raises(SystemExit) as caught:
        main(["generate", spec_file(workdir), "--format", "xml"])

    err = capsys.readouterr().err
    assert caught.value.code == 2
    assert "csv" in err and "json" in err and "jsonl" in err
    assert written(workdir) == ["shop.json"]


@pytest.mark.parametrize("seed", ["-1", "abc", "1.5"])
def test_invalid_seed_option(workdir, capsys, seed):
    with pytest.raises(SystemExit) as caught:
        main(["generate", spec_file(workdir), "--seed", seed])

    assert caught.value.code == 2
    assert "non-negative integer" in capsys.readouterr().err


def test_output_that_cannot_be_written(workdir, capsys):
    (workdir / "blocked").write_text("a file, not a directory", encoding="utf-8")

    code = main(["generate", spec_file(workdir), "--out", "blocked/run1"])

    err = capsys.readouterr().err
    assert code == 1
    assert "blocked" in err


def test_no_command_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as caught:
        main([])

    assert caught.value.code == 2
    assert "usage: dataspecter" in capsys.readouterr().err


# --- help and version -------------------------------------------------------------------------


def test_version(capsys):
    with pytest.raises(SystemExit) as caught:
        main(["--version"])

    assert caught.value.code == 0
    assert capsys.readouterr().out.strip() == f"dataspecter {dataspecter.__version__}"


def test_top_level_help(capsys):
    with pytest.raises(SystemExit) as caught:
        main(["--help"])

    out = capsys.readouterr().out
    assert caught.value.code == 0
    assert "generate" in out and "validate" in out


def test_generate_help_lists_its_options(capsys):
    with pytest.raises(SystemExit) as caught:
        main(["generate", "--help"])

    out = capsys.readouterr().out
    assert caught.value.code == 0
    assert "--out" in out and "--format" in out and "--seed" in out


# --- parity with the API ----------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["csv", "json", "jsonl"])
def test_cli_and_api_write_identical_files(workdir, fmt):
    path = spec_file(workdir)
    main(["generate", path, "--out", "from_cli", "--format", fmt, "--seed", "42"])
    dataspecter.write(dataspecter.load_spec(path), out_dir="from_api", format=fmt, seed=42)

    for entity in ("customer", "order"):
        name = f"{entity}.{fmt}"
        assert (workdir / "from_cli" / name).read_bytes() == (
            workdir / "from_api" / name
        ).read_bytes()


# --- entry points -----------------------------------------------------------------------------


def test_console_script_points_at_main():
    from importlib.metadata import entry_points

    [script] = [
        entry for entry in entry_points(group="console_scripts") if entry.name == "dataspecter"
    ]
    assert script.load() is main


def test_module_can_be_run_with_python_m(workdir):
    import subprocess
    import sys

    path = spec_file(workdir)
    done = subprocess.run(
        [sys.executable, "-m", "dataspecter", "generate", path, "--out", "out"],
        capture_output=True,
        text=True,
    )

    assert done.returncode == 0
    assert "Seed: 42" in done.stdout
    assert (workdir / "out" / "customer.csv").is_file()
