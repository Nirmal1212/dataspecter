"""Exceptions raised by dataspecter."""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Problem:
    """One thing wrong with a spec and where it is.

    `path` is a dotted location such as ``entities.order.fields.amount``; it is empty for
    problems with the document as a whole.
    """

    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}" if self.path else self.message


class DataspecterError(Exception):
    """Base class for the errors dataspecter raises deliberately."""


class SpecError(DataspecterError):
    """A spec could not be loaded or is not valid. `problems` holds every problem found."""

    def __init__(self, problems: Iterable[Problem]):
        self.problems: tuple[Problem, ...] = tuple(problems)
        super().__init__("\n".join(str(problem) for problem in self.problems))


class GenerationError(DataspecterError):
    """Generation had to stop, for example because a unique field ran out of unused values."""


class ExportError(DataspecterError):
    """An output file or directory could not be written."""

    def __init__(self, path: str | os.PathLike[str], reason: str):
        self.path = Path(path)
        self.reason = reason
        super().__init__(f"cannot write {self.path}: {reason}")
