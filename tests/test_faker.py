"""The optional Faker integration and its trust boundary (realistic-data capability)."""

import importlib.util
import subprocess
import sys
from datetime import date, timedelta
from decimal import Decimal

import pytest

import dataspecter
from dataspecter import fakerbridge
from dataspecter.spec import load_spec

from .helpers import problems_of

FAKER_INSTALLED = importlib.util.find_spec("faker") is not None
needs_faker = pytest.mark.skipif(not FAKER_INSTALLED, reason="Faker is not installed")


def spec_of(field: dict, count: int = 100, **top) -> dict:
    return {
        "version": 1,
        "seed": 8,
        "entities": {"thing": {"count": count, "fields": {"v": field}}},
        **top,
    }


def column(field: dict, count: int = 100, **top) -> list:
    simulation = dataspecter.generate(load_spec(spec_of(field, count, **top)))
    return [row["v"] for row in simulation.records("thing")]


def problem_of(field: dict, **top) -> str:
    [problem] = problems_of(spec_of(field, **top))
    return f"{problem.path}: {problem.message}"


# --- with Faker installed ---------------------------------------------------------------------


@needs_faker
def test_calling_a_provider():
    values = column({"type": "faker", "provider": "company"})

    assert all(isinstance(value, str) and value for value in values)
    assert len(set(values)) > 50


@needs_faker
def test_locale_and_arguments():
    days = column(
        {
            "type": "faker",
            "provider": "date_between",
            "args": {"start_date": "-30d", "end_date": "today"},
        }
    )
    today = date.today()
    assert all(type(day) is date and today - timedelta(days=31) <= day <= today for day in days)

    german = column({"type": "faker", "provider": "city", "locale": "de_DE"}, count=20)
    spec_wide = column({"type": "faker", "provider": "city"}, count=20, locale="de_DE")
    assert german == spec_wide


@needs_faker
def test_list_arguments_are_allowed():
    field = {"type": "faker", "provider": "random_element", "args": {"elements": ["a", "b", "c"]}}

    assert set(column(field)) == {"a", "b", "c"}


@needs_faker
def test_faker_values_are_reproducible_and_independent_of_other_fields():
    field = {"type": "faker", "provider": "name"}
    assert column(field) == column(field)

    raw = spec_of(field)
    raw["entities"]["thing"]["fields"] = {
        "extra": {"type": "faker", "provider": "city"},
        "v": field,
    }
    simulation = dataspecter.generate(load_spec(raw))
    assert [row["v"] for row in simulation.records("thing")] == column(field)


@needs_faker
def test_decimal_results_become_floats():
    values = column(
        {"type": "faker", "provider": "pydecimal", "args": {"left_digits": 2, "right_digits": 2}}
    )

    assert all(type(value) is float for value in values)


@needs_faker
@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ({"provider": "not_a_provider"}, "Faker has no provider named 'not_a_provider'"),
        ({"provider": "_config"}, "'_config' is not a Faker provider"),
        ({"provider": "seed_instance"}, "'seed_instance' is not a Faker provider"),
        ({"provider": "add_provider"}, "'add_provider' is not a Faker provider"),
        ({"provider": "name", "locale": "xx_XX"}, "Faker does not support the locale 'xx_XX'"),
        ({"provider": "company", "args": {"no_such_argument": 1}}, "could not be called"),
        ({"provider": "profile"}, "does not return a single value (it returned a dict)"),
        ({"provider": "binary", "args": {"length": 4}}, "it returned a bytes"),
        ({"provider": "company", "args": {"x": {"a": 1}}}, "an argument may be text"),
        ({}, "missing required key(s): provider"),
        ({"provider": "company", "locale": "germany"}, "a locale code such as en_IN"),
        ({"provider": "company", "args": ["a"]}, "a mapping of argument name to value"),
    ],
)
def test_rejected_faker_fields(field, expected):
    message = problem_of({"type": "faker", **field})

    assert message.startswith("entities.thing.fields.v")
    assert expected in message


@needs_faker
def test_result_that_changes_kind_during_generation(monkeypatch):
    spec = load_spec(spec_of({"type": "faker", "provider": "company"}))
    real = fakerbridge._convert
    calls = {"count": 0}

    def flaky(value):
        calls["count"] += 1
        return (False, b"bytes") if calls["count"] > 3 else real(value)

    monkeypatch.setattr(fakerbridge, "_convert", flaky)
    with pytest.raises(dataspecter.GenerationError, match="thing.v: Faker provider 'company'"):
        list(dataspecter.generate(spec).records("thing"))


@needs_faker
def test_unique_faker_field_that_runs_out_stops_with_an_error():
    field = {
        "type": "faker",
        "provider": "random_element",
        "args": {"elements": ["a", "b", "c"]},
        "unique": True,
    }
    simulation = dataspecter.generate(load_spec(spec_of(field, count=10)))

    with pytest.raises(dataspecter.GenerationError, match="thing.v is unique"):
        list(simulation.records("thing"))


@needs_faker
def test_convert_accepts_only_single_values():
    assert fakerbridge._convert(Decimal("1.5")) == (True, 1.5)
    assert fakerbridge._convert("x") == (True, "x")
    assert fakerbridge._convert(date(2024, 1, 1))[0] is True
    assert fakerbridge._convert({"a": 1})[0] is False
    assert fakerbridge._convert(b"x")[0] is False
    assert fakerbridge._convert(None)[0] is False


# --- Faker is optional ------------------------------------------------------------------------


@pytest.fixture
def without_faker(monkeypatch):
    """Make the bridge behave as it does when Faker is absent. A no-op when it really is."""
    monkeypatch.setattr(fakerbridge, "_faker_class", lambda: None)


def test_faker_field_without_faker_explains_how_to_install(without_faker):
    message = problem_of({"type": "faker", "provider": "company"})

    assert "pip install faker" in message
    assert "not installed" in message


def test_specs_without_a_faker_field_work_without_faker(without_faker):
    raw = spec_of({"type": "full_name"})
    raw["entities"]["thing"]["fields"]["home"] = {"type": "address"}

    assert len(column({"type": "email"})) == 100
    assert len(list(dataspecter.generate(load_spec(raw)).records("thing"))) == 100


def test_faker_is_not_loaded_unless_a_spec_uses_it(tmp_path):
    script = (
        "import sys, dataspecter\n"
        "spec = dataspecter.load_spec({'version': 1, 'entities': {'t': {'count': 5, 'fields': {\n"
        "    'n': {'type': 'full_name'}, 'e': {'type': 'email'}, 'h': {'type': 'address'}}}}})\n"
        f"dataspecter.write(spec, out_dir=r'{tmp_path}')\n"
        "print('faker' in sys.modules)\n"
    )
    done = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)

    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "False"
