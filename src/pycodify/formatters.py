from __future__ import annotations

import dataclasses
import inspect
import math
from dataclasses import is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .core import (
    Assignment,
    BlankLine,
    CodeBlock,
    Comment,
    FormatContext,
    PythonSourceLiteral,
    SourceFormatter,
    SourceFragment,
    imported_name,
    to_source,
)


class CommentFormatter(SourceFormatter):
    priority = 100

    def can_format(self, value: Any) -> bool:
        return isinstance(value, Comment)

    def format(self, value: Comment, context: FormatContext) -> SourceFragment:
        text = value.text.strip()
        if not text:
            code = "#"
        elif text.lstrip().startswith("#"):
            code = text
        else:
            code = f"# {text}"
        return SourceFragment(f"{context.indent_str}{code}", frozenset())


class BlankLineFormatter(SourceFormatter):
    priority = 100

    def can_format(self, value: Any) -> bool:
        return isinstance(value, BlankLine)

    def format(self, value: BlankLine, context: FormatContext) -> SourceFragment:
        return SourceFragment("", frozenset())


class AssignmentFormatter(SourceFormatter):
    priority = 90

    def can_format(self, value: Any) -> bool:
        return isinstance(value, Assignment)

    def format(self, value: Assignment, context: FormatContext) -> SourceFragment:
        fragment = to_source(value.value, context)
        code = f"{context.indent_str}{value.name} = {fragment.code}"
        return SourceFragment(code, fragment.imports)


class CodeBlockFormatter(SourceFormatter):
    priority = 80

    def can_format(self, value: Any) -> bool:
        return isinstance(value, CodeBlock)

    def format(self, value: CodeBlock, context: FormatContext) -> SourceFragment:
        codes = []
        imports: set[tuple[str, str]] = set()
        for item in value.items:
            fragment = to_source(item, context)
            imports |= fragment.imports
            codes.append(fragment.code)
        return SourceFragment("\n".join(codes), frozenset(imports))


class PythonSourceLiteralFormatter(SourceFormatter):
    priority = 120

    def can_format(self, value: Any) -> bool:
        return isinstance(value, PythonSourceLiteral)

    def format(self, value: PythonSourceLiteral, context: FormatContext) -> SourceFragment:
        return value.source_fragment(context)


class EnumFormatter(SourceFormatter):
    priority = 70

    def can_format(self, value: Any) -> bool:
        return isinstance(value, Enum)

    def format(self, value: Enum, context: FormatContext) -> SourceFragment:
        enum_type = imported_name(type(value).__module__, type(value).__qualname__, context)
        if type(value).__members__.get(value.name) is value:
            return SourceFragment(f"{enum_type.code}.{value.name}", enum_type.imports)
        member_value = to_source(value.value, context)
        return SourceFragment(
            f"{enum_type.code}({member_value.code})",
            enum_type.imports | member_value.imports,
        )


class TypeFormatter(SourceFormatter):
    priority = 70

    def can_format(self, value: Any) -> bool:
        return isinstance(value, type)

    def format(self, value: type, context: FormatContext) -> SourceFragment:
        return imported_name(value.__module__, value.__qualname__, context)


class PathFormatter(SourceFormatter):
    priority = 70

    def can_format(self, value: Any) -> bool:
        return isinstance(value, Path)

    def format(self, value: Path, context: FormatContext) -> SourceFragment:
        return context.paths.path_source(value, context)


class StrFormatter(SourceFormatter):
    priority = 60

    def can_format(self, value: Any) -> bool:
        return isinstance(value, str)

    def format(self, value: str, context: FormatContext) -> SourceFragment:
        return SourceFragment(repr(str(value)), frozenset())


class LiteralFormatter(SourceFormatter):
    """``None`` and builtin numbers, spelled by their builtin type's ``repr``.

    Subclass instances (for example NumPy scalars) are spelled as the builtin
    value they equal; non-finite floats as ``float('nan')``/``float('inf')``.
    """

    priority = 50
    builtin_types = (bool, int, float, complex, bytes)

    def can_format(self, value: Any) -> bool:
        return value is None or isinstance(value, self.builtin_types)

    def format(self, value: Any, context: FormatContext) -> SourceFragment:
        if value is None:
            return SourceFragment("None", frozenset())
        builtin_type = next(t for t in self.builtin_types if isinstance(value, t))
        builtin_value: Any = builtin_type(value)
        if builtin_type is float and not math.isfinite(builtin_value):
            return SourceFragment(f"float({str(builtin_value)!r})", frozenset())
        return SourceFragment(repr(builtin_value), frozenset())


class CallableFormatter(SourceFormatter):
    """Module-level functions, builtins and class-bound methods, by import."""

    priority = 40

    def can_format(self, value: Any) -> bool:
        if inspect.isfunction(value):
            return True
        if inspect.isbuiltin(value):
            return inspect.ismodule(value.__self__) or value.__self__ is None
        return inspect.ismethod(value) and isinstance(value.__self__, type)

    def format(self, value: Any, context: FormatContext) -> SourceFragment:
        return imported_name(value.__module__, value.__qualname__, context)


class NamedTupleFormatter(SourceFormatter):
    priority = 31

    def can_format(self, value: Any) -> bool:
        return isinstance(value, tuple) and hasattr(type(value), "_fields")

    def format(self, value: Any, context: FormatContext) -> SourceFragment:
        tuple_type = imported_name(type(value).__module__, type(value).__qualname__, context)
        field_ctx = context.indented()
        fragments = [(name, to_source(item, field_ctx)) for name, item in zip(value._fields, value)]
        imports = tuple_type.imports.union(*(frag.imports for _, frag in fragments))
        if not fragments:
            return SourceFragment(f"{tuple_type.code}()", imports)
        inner = f",\n{field_ctx.indent_str}".join(f"{name}={frag.code}" for name, frag in fragments)
        code = f"{tuple_type.code}(\n{field_ctx.indent_str}{inner}\n{context.indent_str})"
        return SourceFragment(code, imports)


class ListFormatter(SourceFormatter):
    priority = 30

    def can_format(self, value: Any) -> bool:
        return isinstance(value, list)

    def format(self, value: list, context: FormatContext) -> SourceFragment:
        if not value:
            return SourceFragment("[]", frozenset())

        item_ctx = context.indented()
        item_frags = [to_source(item, item_ctx) for item in value]
        imports = frozenset().union(*(frag.imports for frag in item_frags))
        inner = f",\n{item_ctx.indent_str}".join(frag.code for frag in item_frags)
        code = f"[\n{item_ctx.indent_str}{inner}\n{context.indent_str}]"
        return SourceFragment(code, imports)


class TupleFormatter(SourceFormatter):
    priority = 30

    def can_format(self, value: Any) -> bool:
        return isinstance(value, tuple)

    def format(self, value: tuple, context: FormatContext) -> SourceFragment:
        if not value:
            return SourceFragment("()", frozenset())

        item_ctx = context.indented()
        item_frags = [to_source(item, item_ctx) for item in value]
        imports = frozenset().union(*(frag.imports for frag in item_frags))
        inner = f",\n{item_ctx.indent_str}".join(frag.code for frag in item_frags)
        if len(value) == 1:
            inner = f"{inner},"
        code = f"(\n{item_ctx.indent_str}{inner}\n{context.indent_str})"
        return SourceFragment(code, imports)


class DictFormatter(SourceFormatter):
    priority = 30

    def can_format(self, value: Any) -> bool:
        return isinstance(value, dict)

    def format(self, value: dict, context: FormatContext) -> SourceFragment:
        if not value:
            return SourceFragment("{}", frozenset())

        item_ctx = context.indented()
        entries = []
        imports: set[tuple[str, str]] = set()
        for key, val in value.items():
            key_frag = to_source(key, item_ctx)
            val_frag = to_source(val, item_ctx)
            imports |= key_frag.imports
            imports |= val_frag.imports
            entries.append(f"{key_frag.code}: {val_frag.code}")

        inner = f",\n{item_ctx.indent_str}".join(entries)
        code = f"{{\n{item_ctx.indent_str}{inner}\n{context.indent_str}}}"
        return SourceFragment(code, frozenset(imports))


class SetFormatter(SourceFormatter):
    """Sets and frozensets; members are sorted by their source for stable output."""

    priority = 30

    def can_format(self, value: Any) -> bool:
        return isinstance(value, (set, frozenset))

    def format(self, value: set | frozenset, context: FormatContext) -> SourceFragment:
        constructor = "frozenset" if isinstance(value, frozenset) else "set"
        if not value:
            return SourceFragment(f"{constructor}()", frozenset())

        item_ctx = context.indented()
        item_frags = sorted(
            (to_source(item, item_ctx) for item in value),
            key=lambda frag: frag.code,
        )
        imports = frozenset().union(*(frag.imports for frag in item_frags))
        inner = f",\n{item_ctx.indent_str}".join(frag.code for frag in item_frags)
        code = f"{{\n{item_ctx.indent_str}{inner}\n{context.indent_str}}}"
        if constructor == "frozenset":
            code = f"frozenset({code})"
        return SourceFragment(code, imports)


class DataclassFormatter(SourceFormatter):
    priority = 35

    def can_format(self, value: Any) -> bool:
        return is_dataclass(value) and not isinstance(value, type)

    def format(self, value: Any, context: FormatContext) -> SourceFragment:
        code, imports, _ = _format_dataclass_expression(value, context)
        return SourceFragment(code, frozenset(imports))


def _create_default_instance(instance: Any) -> Any:
    try:
        return instance.__class__()
    except (TypeError, ValueError):
        default_instance = object.__new__(instance.__class__)
        for dc_field in dataclasses.fields(instance):
            if dc_field.default is not dataclasses.MISSING:
                value = dc_field.default
            elif dc_field.default_factory is not dataclasses.MISSING:  # type: ignore
                value = dc_field.default_factory()  # type: ignore
            else:
                value = dataclasses.MISSING
            object.__setattr__(default_instance, dc_field.name, value)
        return default_instance


def _format_dataclass_expression(
    instance: Any,
    context: FormatContext,
) -> tuple[str, set[tuple[str, str]], bool]:
    cls = instance.__class__
    class_ref = imported_name(cls.__module__, cls.__qualname__, context)
    imports: set[tuple[str, str]] = set(class_ref.imports)

    default_instance = _create_default_instance(instance)

    lines: list[str] = []
    field_ctx = context.indented()

    for dc_field in dataclasses.fields(instance):
        if not dc_field.init:
            continue
        field_name = dc_field.name
        current_value = getattr(instance, field_name)
        default_value = getattr(default_instance, field_name)

        if context.clean_mode and current_value == default_value:
            continue

        if dataclasses.is_dataclass(current_value) and not isinstance(current_value, type):
            formatter = SourceFormatter.get_formatter(current_value)
            if not isinstance(formatter, DataclassFormatter):
                frag = formatter.format(current_value, field_ctx)
                imports |= frag.imports
                lines.append(f"{field_name}={frag.code}")
                continue

            nested_code, nested_imports, nested_has_fields = _format_dataclass_expression(
                current_value,
                field_ctx,
            )
            if (
                context.clean_mode
                and not nested_has_fields
                and type(current_value) is type(default_value)
            ):
                continue
            imports |= nested_imports
            lines.append(f"{field_name}={nested_code}")
        else:
            frag = to_source(current_value, field_ctx)
            imports |= frag.imports
            lines.append(f"{field_name}={frag.code}")

    if not lines:
        return f"{class_ref.code}()", imports, False

    inner = f",\n{field_ctx.indent_str}".join(lines)
    code = f"{class_ref.code}(\n{field_ctx.indent_str}{inner}\n{context.indent_str})"
    return code, imports, True
