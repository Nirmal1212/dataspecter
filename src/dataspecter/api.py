"""The public Python API, re-exported from the `dataspecter` package."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dataspecter.engine import Simulation
from dataspecter.exporters import check_format, export, prepare_directory
from dataspecter.spec import Spec

DEFAULT_FORMAT = "csv"
DEFAULT_DIR = "output"


@dataclass(frozen=True)
class EntityResult:
    name: str
    rows: int
    path: Path


@dataclass(frozen=True)
class WriteResult:
    seed: int
    format: str
    directory: Path
    entities: tuple[EntityResult, ...]


def generate(spec: Spec, seed: int | None = None) -> Simulation:
    """Start a run of `spec`.

    The returned simulation exposes the `seed` it uses, the `entities` in generation order, and
    ``records(entity)`` to iterate over an entity's rows. An explicit `seed` takes precedence
    over the spec's; with neither, one is chosen and can be read back from the simulation.
    """
    return Simulation(spec, seed)


def write(
    spec: Spec,
    out_dir: str | os.PathLike[str] | None = None,
    format: str | None = None,
    seed: int | None = None,
) -> WriteResult:
    """Generate every entity of `spec` and write one file per entity.

    Arguments override the spec's ``output`` block, which overrides the defaults (CSV files in
    ``./output``). Existing files of the same name are replaced. Raises `ValueError` for an
    unsupported format and `ExportError` if a file or directory cannot be written.
    """
    fmt = check_format(format or spec.output.format or DEFAULT_FORMAT)
    simulation = generate(spec, seed)
    directory = prepare_directory(out_dir or spec.output.dir or DEFAULT_DIR)

    results = []
    for name in simulation.entities:
        fields = list(spec.entities[name].fields)
        path, rows = export(directory, name, fmt, fields, simulation.records(name))
        results.append(EntityResult(name, rows, path))
    return WriteResult(simulation.seed, fmt, directory, tuple(results))
