"""The generation engine: seed handling, entity ordering, row iteration and references."""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from typing import Any

from dataspecter.generators import Generator, RowPick, field_generator
from dataspecter.spec import Entity, ReferenceField, Spec

# The picks of one entity, keyed by (target entity, link).
Picks = dict[tuple[str, str | None], RowPick]


def resolve_seed(spec: Spec, seed: int | None = None) -> int:
    """Pick the seed for a run: the explicit one, else the spec's, else a fresh random one."""
    if seed is not None:
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ValueError(f"seed must be a non-negative integer, got {seed!r}")
        return seed
    if spec.seed is not None:
        return spec.seed
    return secrets.randbits(32)


def generation_order(spec: Spec) -> tuple[str, ...]:
    """Order the entities so that each comes after every entity it references.

    Entities keep their declared order wherever references allow. The spec has already been
    checked for cycles.
    """
    order: list[str] = []

    def visit(name: str) -> None:
        if name in order:
            return
        for field in spec.entities[name].fields.values():
            if isinstance(field, ReferenceField):
                visit(field.entity)
        order.append(name)

    for name in spec.entities:
        visit(name)
    return tuple(order)


class Simulation:
    """One run of a spec with a fixed seed.

    Rows are produced lazily, one at a time, so memory does not grow with the row count. The
    exception is fields that other entities reference: their values are kept so that the
    referencing fields can read from them.
    """

    def __init__(self, spec: Spec, seed: int | None = None):
        self.spec = spec
        self.seed = resolve_seed(spec, seed)
        self.entities = generation_order(spec)
        self._referenced = {
            (field.entity, field.field)
            for entity in spec.entities.values()
            for field in entity.fields.values()
            if isinstance(field, ReferenceField)
        }
        self._columns: dict[tuple[str, str], list[Any]] = {}

    def records(self, entity: str) -> Iterator[dict[str, Any]]:
        """Iterate over the rows of `entity`, each a dict of field name to value."""
        if entity not in self.spec.entities:
            known = ", ".join(self.spec.entities)
            raise KeyError(f"unknown entity {entity!r}; entities in this spec: {known}")
        return self._rows(self.spec.entities[entity])

    def _picks(self, entity: Entity, names: list[str]) -> Picks:
        """Build one row pick per (target entity, link) used by the named fields.

        Every reference on the same link reads the row its pick chose, which is how several
        fields come to describe the same parent row.
        """
        picks: Picks = {}
        for name in names:
            field = entity.fields[name]
            if isinstance(field, ReferenceField) and (field.entity, field.link) not in picks:
                rows = self.spec.entities[field.entity].count
                picks[field.entity, field.link] = RowPick(
                    self.seed, entity.name, field.entity, field.link, rows
                )
        return picks

    def _generator(self, entity: Entity, name: str, picks: Picks) -> Generator:
        field = entity.fields[name]
        read = None
        if isinstance(field, ReferenceField):
            column = self._column(field.entity, field.field)
            pick = picks[field.entity, field.link]

            def read() -> Any:
                return column[pick.index]

        return field_generator(field, self.seed, entity.name, name, read)

    def _column(self, entity_name: str, field_name: str) -> list[Any]:
        """Return every value of a referenced field, generating them if no pass has yet.

        A field's values depend only on its own stream and, for a reference, on its link's
        pick, so producing the column on its own gives exactly the values a full pass over the
        entity's rows gives.
        """
        key = (entity_name, field_name)
        if key not in self._columns:
            entity = self.spec.entities[entity_name]
            picks = self._picks(entity, [field_name])
            generate = self._generator(entity, field_name, picks)
            column = []
            for _ in range(entity.count):
                for pick in picks.values():
                    pick.advance()
                column.append(generate())
            self._columns[key] = column
        return self._columns[key]

    def _rows(self, entity: Entity) -> Iterator[dict[str, Any]]:
        picks = self._picks(entity, list(entity.fields))
        generators = {name: self._generator(entity, name, picks) for name in entity.fields}
        # Collect referenced fields in passing, so a later entity need not regenerate them.
        collecting: dict[str, list[Any]] = {
            name: []
            for name in entity.fields
            if (entity.name, name) in self._referenced and (entity.name, name) not in self._columns
        }
        for _ in range(entity.count):
            for pick in picks.values():
                pick.advance()
            row = {name: generate() for name, generate in generators.items()}
            for name, column in collecting.items():
                column.append(row[name])
            yield row
        for name, column in collecting.items():
            self._columns[(entity.name, name)] = column
