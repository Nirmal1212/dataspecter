"""The built-in realistic types, their options and locales (realistic-data capability)."""

import json
import re

import pytest

import dataspecter
from dataspecter.cli import main
from dataspecter.data import LOCALES, RESERVED_DOMAINS, en_in, en_us
from dataspecter.spec import load_spec

from .helpers import problem_text, problems_of


def spec_of(fields: dict, count: int = 200, **top) -> dict:
    return {
        "version": 1,
        "seed": 11,
        "entities": {"person": {"count": count, "fields": fields}},
        **top,
    }


def rows(fields: dict, count: int = 200, locale: str | None = None, **top) -> list[dict]:
    spec = load_spec(spec_of(fields, count, **top), locale=locale)
    return list(dataspecter.generate(spec).records("person"))


def column(field: dict, count: int = 1000, **top) -> list:
    return [row["v"] for row in rows({"v": field}, count, **top)]


# --- bundled data -----------------------------------------------------------------------------


@pytest.mark.parametrize("data", [en_in, en_us], ids=["en_IN", "en_US"])
def test_bundled_data_is_well_formed(data):
    assert len(data.GIVEN_NAMES) >= 100
    assert len(data.FAMILY_NAMES) >= 100
    assert len(data.CITIES) >= 50
    for values in (data.GIVEN_NAMES, data.FAMILY_NAMES, data.STREET_NAMES, data.STATES):
        assert len(set(values)) == len(values)
        assert all(value and value == value.strip() for value in values)
    cities = [city for city, _, _ in data.CITIES]
    assert len(set(cities)) == len(cities)
    for city, state, prefixes in data.CITIES:
        assert city and state in data.STATES
        assert prefixes and all(re.fullmatch(r"\d{3}", prefix) for prefix in prefixes)
    assert {state for _, state, _ in data.CITIES} == set(data.STATES)


def test_indian_pin_prefixes_do_not_start_with_zero():
    assert all(not prefix.startswith("0") for _, _, prefixes in en_in.CITIES for prefix in prefixes)


def test_every_bundled_list_has_a_recorded_source():
    sources = (en_in.__file__.rsplit("en_in.py", 1)[0]) + "SOURCES.md"
    text = open(sources, encoding="utf-8").read()

    for heading in ("Given names", "Family names", "Street names", "Cities", "Postcode prefixes"):
        assert heading in text
    assert "Written by hand" in text


# --- locale -----------------------------------------------------------------------------------


def test_default_locale_is_united_states():
    assert all(value.startswith("+1-") for value in column({"type": "phone"}, count=20))


def test_spec_wide_locale_and_per_field_override():
    fields = {"home": {"type": "phone"}, "office": {"type": "phone", "locale": "en_US"}}
    spec = load_spec(spec_of(fields, 20, locale="en_IN"))
    result = list(dataspecter.generate(spec).records("person"))

    assert all(row["home"].startswith("+91-") for row in result)
    assert all(row["office"].startswith("+1-") for row in result)


def test_caller_locale_overrides_the_spec_but_not_the_field():
    fields = {"home": {"type": "phone"}, "office": {"type": "phone", "locale": "en_US"}}
    spec = load_spec(spec_of(fields, 20, locale="en_US"), locale="en_IN")
    result = list(dataspecter.generate(spec).records("person"))

    assert spec.locale == "en_IN"
    assert all(row["home"].startswith("+91-") for row in result)
    assert all(row["office"].startswith("+1-") for row in result)


def test_malformed_locale():
    [problem] = problems_of(spec_of({"v": {"type": "uuid"}}, locale="india"))
    assert problem.path == "locale"
    assert "en_IN" in problem.message

    with pytest.raises(ValueError, match="locale must be"):
        load_spec(spec_of({"v": {"type": "uuid"}}), locale="india")


def test_built_in_field_with_a_locale_that_is_not_bundled():
    [problem] = problems_of(spec_of({"v": {"type": "full_name"}}, locale="de_DE"))
    assert problem.path == "entities.person.fields.v"
    assert "en_US, en_IN" in problem.message and "'faker'" in problem.message

    [problem] = problems_of(spec_of({"v": {"type": "full_name", "locale": "de_DE"}}))
    assert "is not bundled" in problem.message


def test_unbundled_spec_locale_is_fine_without_built_in_fields():
    load_spec(spec_of({"v": {"type": "uuid"}}, locale="de_DE"))


# --- names ------------------------------------------------------------------------------------


@pytest.mark.parametrize("locale", sorted(LOCALES))
def test_names_come_from_the_locale(locale):
    data = LOCALES[locale]
    fields = {
        "first": {"type": "first_name"},
        "last": {"type": "last_name"},
        "full": {"type": "full_name"},
        "formal": {"type": "full_name", "format": "last_first"},
    }
    result = rows(fields, count=1000, locale=locale)

    assert all(row["first"] in data.GIVEN_NAMES for row in result)
    assert all(row["last"] in data.FAMILY_NAMES for row in result)
    for row in result:
        given, family = row["full"].split(" ", 1)
        assert given in data.GIVEN_NAMES and family in data.FAMILY_NAMES
        family, given = row["formal"].split(", ")
        assert given in data.GIVEN_NAMES and family in data.FAMILY_NAMES
    assert len({row["full"] for row in result}) > 500


def test_unique_names_within_and_beyond_capacity():
    values = column({"type": "full_name", "unique": True}, count=5000)
    assert len(set(values)) == 5000

    [problem] = problems_of(spec_of({"v": {"type": "first_name", "unique": True}}, count=500))
    assert f"only {len(en_us.GIVEN_NAMES)} distinct values" in problem.message
    assert "needs 500" in problem.message


def test_unknown_key_and_format_on_a_name():
    assert "unknown key 'gender'" in problem_text(
        spec_of({"v": {"type": "full_name", "gender": "female"}})
    )
    assert "'first_last' or 'last_first'" in problem_text(
        spec_of({"v": {"type": "full_name", "format": "initials"}})
    )


# --- email ------------------------------------------------------------------------------------

EMAIL = re.compile(r"[a-z0-9.-]+@[a-z0-9.-]+")


def test_email_shape_and_reserved_domains():
    values = column({"type": "email"})

    assert all(EMAIL.fullmatch(value) for value in values)
    assert {value.split("@")[1] for value in values} == set(RESERVED_DOMAINS)
    assert len(set(values)) > 900


def test_email_own_domain_and_invalid_domain():
    assert all(
        value.endswith("@acme.test")
        for value in column({"type": "email", "domain": "acme.test"}, 50)
    )

    [problem] = problems_of(spec_of({"v": {"type": "email", "domain": "not a domain"}}))
    assert problem.path == "entities.person.fields.v.domain"
    assert "a host name" in problem.message


def test_unique_emails():
    values = column({"type": "email", "unique": True}, count=100_000)

    assert len(set(values)) == 100_000


def test_email_is_independent_of_a_name_beside_it():
    result = rows({"name": {"type": "full_name"}, "email": {"type": "email"}}, count=300)
    matching = sum(row["name"].split(" ")[0].lower() in row["email"] for row in result)

    assert matching < 30


# --- phone ------------------------------------------------------------------------------------


def test_phone_formats():
    us = column({"type": "phone"}, count=500)
    india = column({"type": "phone", "locale": "en_IN"}, count=500)

    assert all(re.fullmatch(r"\+1-[2-9]\d\d-555-01\d\d", value) for value in us)
    assert all(re.fullmatch(r"\+91-[6-9]\d{9}", value) for value in india)
    assert all(type(value) is str for value in us + india)


def test_phone_own_pattern():
    values = column({"type": "phone", "pattern": "+91-99999-#####"}, count=50)

    assert all(re.fullmatch(r"\+91-99999-\d{5}", value) for value in values)


def test_unique_phone_capacity():
    [problem] = problems_of(spec_of({"v": {"type": "phone", "unique": True}}, count=100_000))
    assert "only 80,000 distinct values" in problem.message

    values = column({"type": "phone", "unique": True}, count=20_000)
    assert len(set(values)) == 20_000


# --- address ----------------------------------------------------------------------------------


@pytest.mark.parametrize("locale", sorted(LOCALES))
def test_address_shape_and_consistency(locale):
    data = LOCALES[locale]
    state_of = {city: state for city, state, _ in data.CITIES}
    prefixes_of = {city: prefixes for city, _, prefixes in data.CITIES}
    values = column({"type": "address", "locale": locale})

    for value in values:
        assert list(value) == ["street", "city", "state", "postcode", "country"]
        assert all(type(item) is str for item in value.values())
        assert value["state"] == state_of[value["city"]]
        assert len(value["postcode"]) == data.POSTCODE_LENGTH and value["postcode"].isdigit()
        assert value["postcode"].startswith(prefixes_of[value["city"]])
        assert value["country"] == data.COUNTRY
        assert re.fullmatch(r"\d{1,3} .+", value["street"])
    assert len({value["city"] for value in values}) > 40


def test_indian_postcodes_never_start_with_zero_and_us_ones_keep_theirs(tmp_path):
    india = column({"type": "address", "locale": "en_IN"})
    assert all(value["postcode"][0] != "0" for value in india)

    spec = load_spec(spec_of({"home": {"type": "address"}}, count=2000))
    dataspecter.write(spec, out_dir=tmp_path, format="json")
    dataspecter.write(spec, out_dir=tmp_path, format="csv")
    records = json.loads((tmp_path / "person.json").read_text(encoding="utf-8"))
    leading_zero = [r["home"]["postcode"] for r in records if r["home"]["postcode"][0] == "0"]
    assert leading_zero and all(len(code) == 5 for code in leading_zero)
    assert f",{leading_zero[0]}," in (tmp_path / "person.csv").read_text(encoding="utf-8")


def test_choosing_address_fields():
    values = column({"type": "address", "fields": ["postcode", "city"]}, count=50)
    assert all(list(value) == ["postcode", "city"] for value in values)

    full = column({"type": "address"}, count=50)
    assert [value["city"] for value in values] == [value["city"] for value in full]


def test_invalid_address_options():
    assert "unknown address field 'zipcode'" in problem_text(
        spec_of({"v": {"type": "address", "fields": ["city", "zipcode"]}})
    )
    assert "non-empty list" in problem_text(spec_of({"v": {"type": "address", "fields": []}}))
    assert "'unique' is not supported for type 'address'" in problem_text(
        spec_of({"v": {"type": "address", "unique": True}})
    )


def test_address_fields_by_path_in_templates_references_and_csv(tmp_path):
    raw = {
        "version": 1,
        "seed": 6,
        "locale": "en_IN",
        "entities": {
            "customer": {
                "count": 80,
                "fields": {
                    "id": {"type": "sequence"},
                    "home": {"type": "address", "null_probability": 0.2},
                    "where": {"type": "template", "template": "{home.city}, {home.state}"},
                },
            },
            "order": {
                "count": 200,
                "fields": {
                    "customer_id": "$customer.id",
                    "ship_city": "$customer.home.city",
                    "ship_to": "$customer.home",
                },
            },
        },
    }
    spec = load_spec(raw)
    simulation = dataspecter.generate(spec)
    customers = {row["id"]: row for row in simulation.records("customer")}

    for row in customers.values():
        expected = f"{row['home']['city']}, {row['home']['state']}" if row["home"] else None
        assert row["where"] == expected
    for order in simulation.records("order"):
        home = customers[order["customer_id"]]["home"]
        assert order["ship_to"] == home
        assert order["ship_city"] == (home["city"] if home else None)

    dataspecter.write(spec, out_dir=tmp_path, format="csv")
    header = (tmp_path / "customer.csv").read_text(encoding="utf-8").splitlines()[0]
    assert header == "id,home.street,home.city,home.state,home.postcode,home.country,where"
    assert "placeholder {home} names an object" in problem_text(
        {
            **raw,
            "entities": {
                "customer": {
                    "count": 1,
                    "fields": {
                        "home": {"type": "address"},
                        "w": {"type": "template", "template": "{home}"},
                    },
                }
            },
        }
    )


# --- reproducibility and precedence -----------------------------------------------------------

ALL_TYPES = {
    "name": {"type": "full_name"},
    "email": {"type": "email"},
    "phone": {"type": "phone"},
    "home": {"type": "address"},
}


def test_same_seed_same_realistic_data():
    assert rows(ALL_TYPES) == rows(ALL_TYPES)


def test_adding_a_field_leaves_existing_names_unchanged():
    without = {key: value for key, value in ALL_TYPES.items() if key != "phone"}

    assert [row["name"] for row in rows(without)] == [row["name"] for row in rows(ALL_TYPES)]


def test_a_custom_type_named_like_a_built_in_wins():
    types = {"email": {"type": "constant", "value": "mine@corp.test"}}

    assert set(column({"type": "email"}, count=20, types=types)) == {"mine@corp.test"}


# --- command line -----------------------------------------------------------------------------


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def spec_file(workdir, fields: dict, **top) -> str:
    path = workdir / "people.json"
    path.write_text(json.dumps(spec_of(fields, 20, **top)), encoding="utf-8")
    return str(path)


def test_locale_option_overrides_the_spec(workdir):
    path = spec_file(workdir, {"p": {"type": "phone"}, "o": {"type": "phone", "locale": "en_US"}})

    assert main(["generate", path, "--locale", "en_IN", "--format", "jsonl", "--out", "out"]) == 0
    records = [
        json.loads(line)
        for line in (workdir / "out" / "person.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert all(record["p"].startswith("+91-") for record in records)
    assert all(record["o"].startswith("+1-") for record in records)


def test_locale_option_a_built_in_field_cannot_honour(workdir, capsys):
    path = spec_file(workdir, {"name": {"type": "full_name"}})

    assert main(["generate", path, "--locale", "de_DE", "--out", "out"]) == 2
    error = capsys.readouterr().err
    assert "entities.person.fields.name" in error and "is not bundled" in error
    assert not (workdir / "out").exists()


def test_malformed_locale_option(workdir, capsys):
    path = spec_file(workdir, {"name": {"type": "full_name"}})

    with pytest.raises(SystemExit) as caught:
        main(["generate", path, "--locale", "india"])
    assert caught.value.code == 2
    assert "en_IN" in capsys.readouterr().err
