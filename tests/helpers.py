"""Shared helpers for building small specs in tests."""

from __future__ import annotations

from typing import Any

import pytest

from dataspecter.errors import Problem, SpecError
from dataspecter.spec import load_spec


def spec_of(field: dict[str, Any], count: int = 10, **top_level: Any) -> dict[str, Any]:
    """A spec with one entity, `thing`, holding one field, `value`."""
    return {
        "version": 1,
        "entities": {"thing": {"count": count, "fields": {"value": field}}},
        **top_level,
    }


def problems_of(source: Any) -> list[Problem]:
    with pytest.raises(SpecError) as caught:
        load_spec(source)
    return list(caught.value.problems)


def problem_text(source: Any) -> str:
    return "\n".join(str(problem) for problem in problems_of(source))
