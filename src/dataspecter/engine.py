"""The generation engine: seed handling, entity ordering, row iteration and references."""

from __future__ import annotations

import secrets
from collections.abc import Callable, Iterator, Mapping
from typing import Any

from dataspecter.generators import (
    Generator,
    RowPick,
    field_generator,
    stream,
    template_renderer,
)
from dataspecter.paths import copy_value, reader, remove
from dataspecter.spec import (
    Entity,
    Field,
    ObjectField,
    Placeholder,
    ReferenceField,
    Spec,
    TemplateField,
    follow,
    hidden_paths,
    iter_fields,
    leaf_paths,
)

# A step run on a record after its other fields exist: (path, function taking the record).
Finisher = tuple[str, Callable[[dict[str, Any]], None]]

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


def _references(entity: Entity) -> list[ReferenceField]:
    """Every reference field of an entity, including those inside objects."""
    return [field for _, field in iter_fields(entity.fields) if isinstance(field, ReferenceField)]


def generation_order(spec: Spec) -> tuple[str, ...]:
    """Order the entities so that each comes after every entity it references.

    Entities keep their declared order wherever references allow. The spec has already been
    checked for cycles.
    """
    order: list[str] = []

    def visit(name: str) -> None:
        if name in order:
            return
        for field in _references(spec.entities[name]):
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
            for field in _references(entity)
        }
        self._columns: dict[tuple[str, str], list[Any]] = {}

    def columns(self, entity: str) -> tuple[str, ...]:
        """Return the paths of the entity's single-valued fields: the columns CSV export writes."""
        self._check_entity(entity)
        return leaf_paths(self.spec, entity)

    def records(self, entity: str) -> Iterator[dict[str, Any]]:
        """Iterate over the rows of `entity`, each a dict of field name to value.

        An object field is a nested dict, or None when the object is null.
        """
        self._check_entity(entity)
        return self._rows(self.spec.entities[entity])

    def _check_entity(self, entity: str) -> None:
        if entity not in self.spec.entities:
            known = ", ".join(self.spec.entities)
            raise KeyError(f"unknown entity {entity!r}; entities in this spec: {known}")

    def _picks(self, entity: Entity) -> Picks:
        """Build one row pick per (target entity, link) the entity's references use.

        Every reference on the same link reads the row its pick chose, which is how several
        fields come to describe the same parent row.
        """
        picks: Picks = {}
        for field in _references(entity):
            if (field.entity, field.link) not in picks:
                rows = self.spec.entities[field.entity].count
                picks[field.entity, field.link] = RowPick(
                    self.seed, entity.name, field.entity, field.link, rows
                )
        return picks

    def _column(self, entity_name: str, path: str) -> list[Any]:
        """Return every value at a referenced path, generating the entity if no pass has yet."""
        key = (entity_name, path)
        if key not in self._columns:
            for _ in self._rows(self.spec.entities[entity_name]):
                pass  # a full pass collects every referenced path of the entity
        return self._columns[key]

    def _generator(self, entity: Entity, path: str, field: Field, picks: Picks) -> Generator:
        read = None
        if isinstance(field, ReferenceField):
            column = self._column(field.entity, field.field)
            pick = picks[field.entity, field.link]
            if isinstance(follow(self.spec, field), ObjectField):
                # Each record gets its own copy, so editing one never changes another.
                def read() -> Any:
                    return copy_value(column[pick.index])
            else:

                def read() -> Any:
                    return column[pick.index]

        return field_generator(field, self.seed, entity.name, path, read)

    def _builder(
        self,
        entity: Entity,
        fields: Mapping[str, Field],
        prefix: str,
        picks: Picks,
        templates: list[tuple[str, TemplateField]],
    ) -> Callable[[], dict[str, Any]]:
        """Return a function building one record, or one object inside it, per call.

        Templates are left as None and listed in `templates`; they are filled in once the
        fields they read exist.
        """
        steps: list[tuple[str, Generator]] = []
        for name, field in fields.items():
            path = f"{prefix}{name}"
            if isinstance(field, ObjectField):
                make = self._object(entity, path, field, picks, templates)
            elif isinstance(field, TemplateField):
                templates.append((path, field))
                make = _nothing
            else:
                make = self._generator(entity, path, field, picks)
            steps.append((name, make))
        return lambda: {name: make() for name, make in steps}

    def _object(
        self,
        entity: Entity,
        path: str,
        field: ObjectField,
        picks: Picks,
        templates: list[tuple[str, TemplateField]],
    ) -> Generator:
        build = self._builder(entity, field.fields, f"{path}.", picks, templates)
        if field.null_probability <= 0:
            return build
        nulls = stream(self.seed, entity.name, path, "null")
        probability = field.null_probability
        # A null object does not generate its fields: an address that is usually absent should
        # not cost a full address on every row.
        return lambda: None if nulls.random() < probability else build()

    def _finishers(self, entity: Entity, templates: list[tuple[str, TemplateField]]) -> list:
        """Return the steps that fill in templates, each after the templates it reads."""
        by_path = dict(templates)
        ordered: list[str] = []

        def visit(path: str) -> None:
            if path in ordered:
                return
            for part in by_path[path].parts:
                if isinstance(part, Placeholder) and part.target in by_path:
                    visit(part.target)
            ordered.append(path)

        for path in by_path:
            visit(path)

        steps = []
        for path in ordered:
            render = template_renderer(by_path[path], self.seed, entity.name, path)
            steps.append(_setter(path, render))
        return steps

    def _rows(self, entity: Entity) -> Iterator[dict[str, Any]]:
        picks = self._picks(entity)
        templates: list[tuple[str, TemplateField]] = []
        build = self._builder(entity, entity.fields, "", picks, templates)
        finishers = self._finishers(entity, templates)
        hidden = [path for path, field in iter_fields(entity.fields) if field.hidden]
        # Collect referenced paths in passing, so a later entity need not regenerate them.
        wanted = sorted(
            path
            for name, path in self._referenced
            if name == entity.name and (name, path) not in self._columns
        )
        collecting = [(path, self._collector(entity, path), []) for path in wanted]
        for _ in range(entity.count):
            for pick in picks.values():
                pick.advance()
            row = build()
            for finish in finishers:
                finish(row)
            for _, collect, column in collecting:
                column.append(collect(row))
            for path in hidden:
                remove(row, path)
            yield row
        for path, _, column in collecting:
            self._columns[entity.name, path] = column

    def _collector(self, entity: Entity, path: str) -> Callable[[dict[str, Any]], Any]:
        """Return a function reading the value other entities will copy from `path`.

        The value is copied, so that a caller editing the record cannot change what later
        records copy, and hidden fields inside a copied object are dropped.
        """
        read = reader(path)
        fields: Mapping[str, Field] = entity.fields
        field: Field | None = None
        for segment in path.split("."):
            field = fields[segment]
            target = follow(self.spec, field)
            fields = target.fields if isinstance(target, ObjectField) else {}
        inner_hidden = hidden_paths(self.spec, field)

        def collect(row: dict[str, Any]) -> Any:
            value = copy_value(read(row))
            if isinstance(value, dict):
                for hidden in inner_hidden:
                    remove(value, hidden)
            return value

        return collect


def _nothing() -> None:
    return None


def _setter(path: str, render: Callable[[dict[str, Any]], Any]) -> Callable[[dict[str, Any]], None]:
    """Return a function that renders a template and stores it at `path` in the record."""
    *parents, name = path.split(".")
    if not parents:

        def set_top(row: dict[str, Any]) -> None:
            row[name] = render(row)

        return set_top
    read_parent = reader(".".join(parents))

    def set_nested(row: dict[str, Any]) -> None:
        parent = read_parent(row)
        if parent is not None:  # the object holding the template is null for this record
            parent[name] = render(row)

    return set_nested
