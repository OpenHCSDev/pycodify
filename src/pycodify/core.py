from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, ClassVar, FrozenSet, Iterable, List, Tuple


@dataclass(frozen=True)
class SourceFragment:
    """Result of serializing a value to Python source."""

    code: str
    imports: FrozenSet[Tuple[str, str]] = frozenset()

    def __add__(self, other: "SourceFragment") -> "SourceFragment":
        return SourceFragment(
            code=self.code + other.code,
            imports=self.imports | other.imports,
        )


@dataclass(frozen=True)
class FormatContext:
    """Context passed through serialization."""

    indent: int = 0
    clean_mode: bool = False
    name_mappings: Mapping[Tuple[str, str], str] = field(
        default_factory=lambda: MappingProxyType({})
    )
    extensions: Mapping[type[object], object] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def indented(self) -> "FormatContext":
        return replace(self, indent=self.indent + 1)

    @property
    def indent_str(self) -> str:
        return "    " * self.indent

    def extension(self, extension_type: type[Any]) -> Any | None:
        """Return one caller-owned rendering extension by exact nominal type."""

        return self.extensions.get(extension_type)


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
    items: Tuple[Any, ...]

    @classmethod
    def from_items(cls, items: Iterable[Any]) -> "CodeBlock":
        return cls(tuple(items))


class SourceFormatter(ABC):
    """Formats a value to Python source code."""

    priority: int = 0

    _registry: ClassVar[List["SourceFormatter"]] = []
    _sorted_registry: ClassVar[List["SourceFormatter"]] = []
    _registry_dirty: ClassVar[bool] = False

    def __init_subclass__(cls, **kwargs):
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
    def register(cls, formatter: "SourceFormatter") -> None:
        cls._registry.append(formatter)
        cls._registry_dirty = True

    @classmethod
    def _iter_registry(cls) -> List["SourceFormatter"]:
        if cls._registry_dirty:
            cls._sorted_registry = sorted(
                cls._registry,
                key=lambda fmt: fmt.priority,
                reverse=True,
            )
            cls._registry_dirty = False
        return cls._sorted_registry

    @classmethod
    def get_formatter(cls, value: Any) -> "SourceFormatter":
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
    *,
    context: FormatContext | None = None,
) -> str:
    """Generate complete Python source with imports."""
    from .imports import resolve_imports

    ctx = context or FormatContext(clean_mode=clean_mode)
    fragment = to_source(obj, ctx)

    import_lines, name_mappings = resolve_imports(fragment.imports)

    ctx = replace(ctx, name_mappings=MappingProxyType(name_mappings))
    fragment = to_source(obj, ctx)

    code_lines: List[str] = []
    if header:
        code_lines.extend(header.splitlines())
        code_lines.append("")
    if import_lines:
        code_lines.extend(import_lines)
        code_lines.append("")

    if fragment.code:
        code_lines.append(fragment.code)

    return "\n".join(code_lines)
