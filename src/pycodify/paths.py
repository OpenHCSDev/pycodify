"""Document-level factoring of absolute paths.

A document that names several paths under one directory binds that directory
once (``path_root = Path('/data/screen')``) and spells each path below it as
``path_root / 'plate_A'``; a path that occurs more than once is bound to its
own name (``path_1``). Relative paths and strings are never factored.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .core import (
    Assignment,
    BlankLine,
    CodeBlock,
    FormatContext,
    PathRendering,
    PythonSourceLiteral,
    SourceFragment,
)


@dataclass(frozen=True)
class PathConstructor(PythonSourceLiteral):
    """A path spelled as its own constructor call, never substituted."""

    value: Path

    def source_fragment(self, context: FormatContext) -> SourceFragment:
        return PathRendering().path_source(self.value, context)


@dataclass
class PathCollector(PathRendering):
    """Discovery pass: records every path it renders, in order."""

    values: list[Path] = field(default_factory=list)

    def path_source(self, value: Path, context: FormatContext) -> SourceFragment:
        self.values.append(value)
        return super().path_source(value, context)


@dataclass(frozen=True)
class PathFactoring(PathRendering):
    """Path bindings for one document and the expressions that replace paths."""

    bindings: tuple[Assignment, ...] = ()
    expressions: Mapping[Path, SourceFragment] = field(default_factory=lambda: MappingProxyType({}))

    @classmethod
    def from_occurrences(cls, occurrences: Iterable[Path]) -> PathFactoring:
        normalized = tuple(
            _lexically_normalized(path) for path in occurrences if path.is_absolute()
        )
        counts = Counter(normalized)
        ordered_values = tuple(dict.fromkeys(normalized))
        partitions: dict[tuple[str, str], list[Path]] = {}
        for value in ordered_values:
            first_component = value.parts[1] if len(value.parts) > 1 else ""
            partitions.setdefault((value.anchor, first_component), []).append(value)

        bindings: list[Assignment] = []
        root_by_value: dict[Path, tuple[str, Path]] = {}
        for values in partitions.values():
            if len(values) < 2:
                continue
            root = _common_ancestor(values)
            if root is None or root == Path(root.anchor):
                continue
            root_name = "path_root" if not bindings else f"path_root_{len(bindings) + 1}"
            bindings.append(Assignment(root_name, PathConstructor(root)))
            for value in values:
                root_by_value[value] = (root_name, root)

        expressions: dict[Path, SourceFragment] = {}
        path_index = 0
        for value in ordered_values:
            root_binding = root_by_value.get(value)
            below_root = (
                None
                if root_binding is None
                else _descendant_expression(root_binding[0], root_binding[1], value)
            )
            is_root = root_binding is not None and value == root_binding[1]
            if counts[value] > 1 and not is_root:
                path_index += 1
                path_name = f"path_{path_index}"
                bindings.append(Assignment(path_name, below_root or PathConstructor(value)))
                expressions[value] = SourceFragment(path_name)
                continue
            if below_root is not None:
                expressions[value] = below_root

        return cls(tuple(bindings), MappingProxyType(expressions))

    def path_source(self, value: Path, context: FormatContext) -> SourceFragment:
        if value.is_absolute():
            expression = self.expressions.get(_lexically_normalized(value))
            if expression is not None:
                return expression
        return super().path_source(value, context)

    def document(self, body: Any) -> Any:
        """Return ``body`` preceded by this factoring's bindings."""

        if not self.bindings:
            return body
        items = body.items if isinstance(body, CodeBlock) else (body,)
        return CodeBlock((*self.bindings, BlankLine(), *items))


def _lexically_normalized(value: Path) -> Path:
    components: list[str] = []
    for component in value.parts[1:]:
        if component in ("", "."):
            continue
        if component == "..":
            if components:
                components.pop()
            continue
        components.append(component)
    return Path(value.anchor, *components)


def _common_ancestor(values: list[Path]) -> Path | None:
    first_parts = values[0].parts
    common_count = 0
    for components in zip(*(value.parts for value in values)):
        if len(set(components)) != 1:
            break
        common_count += 1
    if common_count == 0:
        return None
    return Path(first_parts[0], *first_parts[1:common_count])


def _descendant_expression(root_name: str, root: Path, value: Path) -> SourceFragment:
    code = root_name
    for part in value.parts[len(root.parts) :]:
        code = f"{code} / {part!r}"
    return SourceFragment(code)
