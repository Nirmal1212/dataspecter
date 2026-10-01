"""Loading specs from YAML files, JSON files and mappings (simulation-spec capability)."""

import json

from dataspecter.spec import load_spec

from .helpers import problem_text, problems_of, spec_of

YAML_SPEC = """\
version: 1
seed: 7
entities:
  customer:
    count: 25
    fields:
      id: {type: sequence}
      signup: {type: date, min: 2024-01-01, max: 2024-12-31}
      tier:
        type: choice
        values: [free, pro]
        weights: [3, 1]
"""

JSON_SPEC = {
    "version": 1,
    "seed": 7,
    "entities": {
        "customer": {
            "count": 25,
            "fields": {
                "id": {"type": "sequence"},
                "signup": {"type": "date", "min": "2024-01-01", "max": "2024-12-31"},
                "tier": {"type": "choice", "values": ["free", "pro"], "weights": [3, 1]},
            },
        }
    },
}


def test_yaml_spec_is_loaded(tmp_path):
    path = tmp_path / "customers.yaml"
    path.write_text(YAML_SPEC, encoding="utf-8")

    spec = load_spec(path)

    assert spec.seed == 7
    assert list(spec.entities["customer"].fields) == ["id", "signup", "tier"]


def test_yml_extension_is_accepted(tmp_path):
    path = tmp_path / "customers.yml"
    path.write_text(YAML_SPEC, encoding="utf-8")

    assert load_spec(str(path)).entities["customer"].count == 25


def test_equivalent_json_spec_loads_identically(tmp_path):
    yaml_path = tmp_path / "customers.yaml"
    yaml_path.write_text(YAML_SPEC, encoding="utf-8")
    json_path = tmp_path / "customers.json"
    json_path.write_text(json.dumps(JSON_SPEC), encoding="utf-8")

    assert load_spec(yaml_path) == load_spec(json_path)


def test_mapping_loads_identically_to_a_file(tmp_path):
    path = tmp_path / "customers.json"
    path.write_text(json.dumps(JSON_SPEC), encoding="utf-8")

    assert load_spec(JSON_SPEC) == load_spec(path)


def test_unsupported_file_extension(tmp_path):
    path = tmp_path / "customers.toml"
    path.write_text("version = 1", encoding="utf-8")

    text = problem_text(path)
    assert "unsupported file extension '.toml'" in text
    assert ".yaml, .yml or .json" in text


def test_malformed_yaml_names_the_file_and_position(tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("version: 1\nentities: [unclosed\n", encoding="utf-8")

    text = problem_text(path)
    assert "broken.yaml" in text
    assert "invalid YAML at line" in text


def test_malformed_json_names_the_file_and_position(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text('{"version": 1,\n "entities": }', encoding="utf-8")

    text = problem_text(path)
    assert "broken.json" in text
    assert "invalid JSON at line 2, column" in text


def test_missing_file_names_the_path(tmp_path):
    path = tmp_path / "missing.yaml"

    text = problem_text(path)
    assert "missing.yaml" in text
    assert "file not found" in text


def test_empty_file_is_rejected(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")

    assert "the spec must be a mapping" in problem_text(path)


def test_invalid_yaml_date_is_reported_with_its_location(tmp_path):
    path = tmp_path / "dates.yaml"
    path.write_text(
        "version: 1\n"
        "entities:\n"
        "  thing:\n"
        "    count: 1\n"
        "    fields:\n"
        "      day: {type: date, min: 2024-13-01, max: 2024-12-31}\n",
        encoding="utf-8",
    )

    [problem] = problems_of(path)
    assert problem.path == "entities.thing.fields.day.min"
    assert "is not a valid ISO 8601 date" in problem.message


def test_two_problems_in_a_file_are_reported_together(tmp_path):
    raw = spec_of({"type": "integer", "min": 9, "max": 1})
    raw["entities"]["thing"]["fields"]["other"] = {"type": "surname"}
    path = tmp_path / "two.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    paths = [problem.path for problem in problems_of(path)]
    assert paths == ["entities.thing.fields.value", "entities.thing.fields.other.type"]
