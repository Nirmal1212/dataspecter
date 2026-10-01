"""Generated output is compared byte for byte with files recorded from an earlier version.

The property tests elsewhere would still pass if every generated value changed. This one does
not: it fails on any difference, so a refactor cannot alter what a spec and seed produce
without someone deciding it should.
"""

from pathlib import Path

import pytest

import dataspecter
from dataspecter import generators

GOLDEN = Path(__file__).parent / "golden"
FORMATS = ("csv", "json", "jsonl")
SPECS = sorted(path.stem for path in GOLDEN.glob("*.yaml"))


def generated(spec_name: str, fmt: str, out_dir: Path) -> dict[str, bytes]:
    spec = dataspecter.load_spec(GOLDEN / f"{spec_name}.yaml")
    result = dataspecter.write(spec, out_dir=out_dir, format=fmt)
    return {entity.path.name: entity.path.read_bytes() for entity in result.entities}


def recorded(spec_name: str, fmt: str) -> dict[str, bytes]:
    directory = GOLDEN / "expected" / spec_name / fmt
    return {path.name: path.read_bytes() for path in sorted(directory.iterdir())}


@pytest.mark.parametrize("spec_name", SPECS)
@pytest.mark.parametrize("fmt", FORMATS)
def test_output_matches_the_recorded_files(spec_name, fmt, tmp_path):
    actual = generated(spec_name, fmt, tmp_path)
    expected = recorded(spec_name, fmt)

    assert sorted(actual) == sorted(expected)
    for name in expected:
        assert actual[name] == expected[name], f"{spec_name}/{fmt}/{name} differs from golden"


def test_the_comparison_notices_a_changed_generator(tmp_path, monkeypatch):
    original = generators.stream

    def shifted(seed, entity, field, purpose=""):
        return original(seed + 1, entity, field, purpose)

    monkeypatch.setattr(generators, "stream", shifted)

    assert generated("spec", "csv", tmp_path) != recorded("spec", "csv")
