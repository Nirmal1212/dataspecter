from pathlib import Path

from dataspecter.errors import DataspecterError, ExportError, Problem, SpecError


def test_spec_error_exposes_its_problems():
    problems = [
        Problem("entities.order.fields.amount", "min must not exceed max"),
        Problem("entities.order.fields.customer_id", "unknown entity 'client'"),
    ]
    error = SpecError(problems)

    assert error.problems == tuple(problems)
    assert isinstance(error, DataspecterError)


def test_spec_error_renders_one_problem_per_line():
    error = SpecError([Problem("version", "is required"), Problem("", "file not found")])

    assert str(error).splitlines() == ["version: is required", "file not found"]


def test_export_error_names_the_path_and_reason():
    error = ExportError("out/customer.csv", "Permission denied")

    assert error.path == Path("out/customer.csv")
    assert "customer.csv" in str(error)
    assert "Permission denied" in str(error)
