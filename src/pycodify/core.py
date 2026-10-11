from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, ClassVar


@dataclass(frozen=True)
class SourceFragment:
    """Result of serializing a value to Python source."""

    code: str
    imports: frozenset[tuple[str, str]] = frozenset()

    def __add__(self, other: SourceFragment) -> SourceFragment:
        return SourceFragment(
            code=self.code + other.code,
            imports=self.imports | other.imports,
        )


class PathRendering:
    """How one render pass spells :class:`pathlib.Path` values.

    The base spells every path as its own constructor call. Subclasses in
    :mod:`pycodify.paths` record or substitute paths for document-level
    factoring.
    """

    def path_source(self, value: Path, context: FormatContext) -> SourceFragment:
        constructor = imported_name("pathlib", "Path", context)
        return SourceFragment(
            f"{constructor.code}({str(value)!r})",
            constructor.imports,
        )


@dataclass(frozen=True)
class FormatContext:
    """Context passed through serialization."""

    indent: int = 0
    clean_mode: bool = False
    name_mappings: Mapping[tuple[str, str], str] = field(
        default_factory=lambda: MappingProxyType({})
    )
    paths: PathRendering = field(default_factory=PathRendering)

    def indented(self) -> FormatContext:
        return replace(self, indent=self.indent + 1)

    @property
    def indent_str(self) -> str:
        return "    " * self.indent


def imported_name(module: str, qualname: str, context: FormatContext) -> SourceFragment:
    """Spell an importable object by its module and ``__qualname__``.

    The root of the qualified name is imported (under its collision alias, if
    any) and the rest is spelled as attribute access, so nested classes, enums
    and functions load back as themselves. Objects defined inside a function
    have no import path and are rejected.
    """

    if "<locals>" in qualname:
        raise TypeError(
            f"{module}.{qualname} is defined inside a function and cannot be "
            "imported by generated source."
        )
    root, dot, nested = qualname.partition(".")
    if module == "builtins":
        return SourceFragment(qualname)
    import_pair = (module, root)
    name = context.name_mappings.get(import_pair, root)
    return SourceFragment(f"{name}{dot}{nested}", frozenset({import_pair}))


class PythonSourceLiteral(ABC):
    """A value that spells its own Python source expression."""

    @abstractmethod
    def source_fragment(self, context: FormatContext) -> SourceFragment:
        """Return the expression that reconstructs this value, with its imports."""


@dataclass(frozen=True)
class Comment:
    text: str


@dataclass(frozen=True)
class BlankLine:
    pass


@dataclass(frozen=True)
class Assignment:
    name: str
    value: Any


@dataclass(frozen=True)
class CodeBlock:
    items: tuple[Any, ...]

    @classmethod
    def from_items(cls, items: Iterable[Any]) -> CodeBlock:
        return cls(tuple(items))


class SourceFormatter(ABC):
    """Formats a value to Python source code."""

    priority: int = 0

    _registry: ClassVar[list[SourceFormatter]] = []
    _sorted_registry: ClassVar[list[SourceFormatter]] = []
    _registry_dirty: ClassVar[bool] = False

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if getattr(cls, "__abstract__", False):
            return
        SourceFormatter._registry.append(cls())
        SourceFormatter._registry_dirty = True

    @abstractmethod
    def can_format(self, value: Any) -> bool:
        """Return True if this formatter handles this value type."""
        raise NotImplementedError

    @abstractmethod
    def format(self, value: Any, context: FormatContext) -> SourceFragment:
        """Format value to Python source, returning code and required imports."""
        raise NotImplementedError

    @classmethod
    def register(cls, formatter: SourceFormatter) -> None:
        cls._registry.append(formatter)
        cls._registry_dirty = True

    @classmethod
    def _iter_registry(cls) -> list[SourceFormatter]:
        if cls._registry_dirty:
            cls._sorted_registry = sorted(
                cls._registry,
                key=lambda fmt: fmt.priority,
                reverse=True,
            )
            cls._registry_dirty = False
        return cls._sorted_registry

    @classmethod
    def get_formatter(cls, value: Any) -> SourceFormatter:
        for formatter in cls._iter_registry():
            if formatter.can_format(value):
                return formatter
        raise TypeError(f"No formatter for {type(value)}")


def to_source(value: Any, ctx: FormatContext | None = None) -> SourceFragment:
    """Convert any value to Python source code."""
    if isinstance(value, SourceFragment):
        return value
    ctx = ctx or FormatContext()
    formatter = SourceFormatter.get_formatter(value)
    return formatter.format(value, ctx)


def generate_python_source(
    obj: Any,
    header: str = "",
    clean_mode: bool = False,
) -> str:
    """Generate complete Python source with imports.

    Absolute paths that share a root or repeat are bound once at the top of the
    document (see :mod:`pycodify.paths`).
    """
    from .imports import resolve_imports
    from .paths import PathCollector, PathFactoring

    ctx = FormatContext(clean_mode=clean_mode)
    collector = PathCollector()
    to_source(obj, replace(ctx, paths=collector))
    factoring = PathFactoring.from_occurrences(collector.values)
    body = factoring.document(obj)
    ctx = replace(ctx, paths=factoring)

    fragment = to_source(body, ctx)
    import_lines, name_mappings = resolve_imports(fragment.imports)
    ctx = replace(ctx, name_mappings=MappingProxyType(name_mappings))
    fragment = to_source(body, ctx)

    code_lines: list[str] = []
    if header:
        code_lines.extend(header.splitlines())
        code_lines.append("")
    if import_lines:
        code_lines.extend(import_lines)
        code_lines.append("")

    if fragment.code:
        code_lines.append(fragment.code)

    return "\n".join(code_lines)
