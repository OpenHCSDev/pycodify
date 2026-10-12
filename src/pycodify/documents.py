"""A dataclass saved as one Python module of assignments."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import MISSING, Field, fields
from typing import Any, TypeVar

from .core import Assignment, BlankLine, CodeBlock, generate_python_source

DocumentT = TypeVar("DocumentT", bound="SourceDocument")


class SourceDocument:
    """A dataclass whose constructor fields are a module's public assignments.

    Each ``init=True`` field is written as one module-level assignment named
    after the field, in declaration order, and read back by that name. The
    field declaration is the only place the name is spelled. A field with a
    default may be absent from a loaded module; a field without one must be
    assigned. ``init=False`` fields are not part of the saved module.
    """

    __slots__ = ()

    @classmethod
    def assignment_fields(cls) -> tuple[Field[Any], ...]:
        """Return the fields saved as assignments, in declaration order."""
        return tuple(field for field in fields(cls) if field.init)  # type: ignore[arg-type]

    @classmethod
    def assignment_names(cls) -> tuple[str, ...]:
        """Return the names this document assigns at module level."""
        return tuple(field.name for field in cls.assignment_fields())

    @classmethod
    def from_namespace(cls: type[DocumentT], namespace: Mapping[str, object]) -> DocumentT:
        """Build the document from the names an executed module defines."""
        values: dict[str, object] = {}
        for field in cls.assignment_fields():
            if field.name in namespace:
                values[field.name] = namespace[field.name]
            elif field.default is MISSING and field.default_factory is MISSING:
                raise ValueError(f"{cls.__name__} source must define {field.name!r}.")
        return cls(**values)

    @classmethod
    def from_source(cls: type[DocumentT], source: str) -> DocumentT:
        """Execute Python source and build the document from its assignments."""
        namespace: dict[str, object] = {}
        exec(compile(source, f"<{cls.__name__}>", "exec"), namespace)  # noqa: S102
        return cls.from_namespace(namespace)

    def body(self) -> CodeBlock:
        """Return one assignment per saved field, separated by blank lines."""
        items: list[object] = []
        for name in self.assignment_names():
            if items:
                items.append(BlankLine())
            items.append(Assignment(name, getattr(self, name)))
        return CodeBlock.from_items(items)

    def to_source(self, *, header: str = "", clean_mode: bool = False) -> str:
        """Render the document as a complete Python module."""
        return generate_python_source(self.body(), header=header, clean_mode=clean_mode)
