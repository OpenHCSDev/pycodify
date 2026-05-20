from __future__ import annotations

import dataclasses
import typing
from dataclasses import is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Tuple

from .core import (
    Assignment,
    BlankLine,
    CodeBlock,
    Comment,
    FormatContext,
    SourceFormatter,
    SourceFragment,
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
        imports = set()
        for item in value.items:
            fragment = to_source(item, context)
            imports |= fragment.imports
            codes.append(fragment.code)
        return SourceFragment("\n".join(codes), frozenset(imports))


class EnumFormatter(SourceFormatter):
    priority = 70

    def can_format(self, value: Any) -> bool:
        return isinstance(value, Enum)

    def format(self, value: Enum, context: FormatContext) -> SourceFragment:
        cls = value.__class__
        import_pair = (cls.__module__, cls.__name__)
        name = context.name_mappings.get(import_pair, cls.__name__)
        return SourceFragment(f"{name}.{value.name}", frozenset([import_pair]))


class PathFormatter(SourceFormatter):
    priority = 70

    def can_format(self, value: Any) -> bool:
        return isinstance(value, Path)

    def format(self, value: Path, context: FormatContext) -> SourceFragment:
        import_pair = ("pathlib", "Path")
        name = context.name_mappings.get(import_pair, "Path")
        return SourceFragment(f"{name}({repr(str(value))})", frozenset([import_pair]))


class StrFormatter(SourceFormatter):
    priority = 60

    def can_format(self, value: Any) -> bool:
        return isinstance(value, str)

    def format(self, value: str, context: FormatContext) -> SourceFragment:
        return SourceFragment(repr(value), frozenset())


class LiteralFormatter(SourceFormatter):
    priority = 50

    def can_format(self, value: Any) -> bool:
        return value is None or isinstance(value, (bool, int, float))

    def format(self, value: Any, context: FormatContext) -> SourceFragment:
        return SourceFragment(repr(value), frozenset())


class CallableFormatter(SourceFormatter):
    priority = 40

    def can_format(self, value: Any) -> bool:
        return callable(value) and not isinstance(value, type)

    def format(self, value: Any, context: FormatContext) -> SourceFragment:
        import_pair = (value.__module__, value.__name__)
        name = context.name_mappings.get(import_pair, value.__name__)
        return SourceFragment(name, frozenset([import_pair]))


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
        imports = set()
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
    priority = 30

    def can_format(self, value: Any) -> bool:
        return isinstance(value, set)

    def format(self, value: set, context: FormatContext) -> SourceFragment:
        if not value:
            return SourceFragment("set()", frozenset())

        item_ctx = context.indented()
        item_frags = [to_source(item, item_ctx) for item in value]
        imports = frozenset().union(*(frag.imports for frag in item_frags))
        inner = f",\n{item_ctx.indent_str}".join(frag.code for frag in item_frags)
        code = f"{{\n{item_ctx.indent_str}{inner}\n{context.indent_str}}}"
        return SourceFragment(code, imports)


class DataclassFormatter(SourceFormatter):
    priority = 35

    def can_format(self, value: Any) -> bool:
        return is_dataclass(value) and not isinstance(value, type)

    def format(self, value: Any, context: FormatContext) -> SourceFragment:
        code, imports, _ = _format_dataclass_expression(value, context)
        return SourceFragment(code, frozenset(imports))


def _resolve_dataclass_class_from_type(field_type: Any) -> Any | None:
    if field_type is None:
        return None

    origin = typing.get_origin(field_type)
    if origin is typing.Union:
        for arg in typing.get_args(field_type):
            if arg is type(None):
                continue
            resolved = _resolve_dataclass_class_from_type(arg)
            if resolved:
                return resolved
        return None

    if isinstance(field_type, type) and dataclasses.is_dataclass(field_type):
        return field_type

    return None


def _create_placeholder_dataclass_instance(dataclass_cls: type) -> Any:
    instance = object.__new__(dataclass_cls)
    for dc_field in dataclasses.fields(dataclass_cls):
        object.__setattr__(instance, dc_field.name, None)

    if hasattr(dataclass_cls, "_is_lazy_dataclass"):
        object.__setattr__(instance, "_is_lazy_dataclass", True)

    return instance


def _create_default_instance(instance: Any) -> Any:
    if hasattr(instance, "_resolve_field_value"):
        default_instance = object.__new__(instance.__class__)
        for dc_field in dataclasses.fields(instance):
            object.__setattr__(default_instance, dc_field.name, None)
        if hasattr(instance.__class__, "_is_lazy_dataclass"):
            object.__setattr__(default_instance, "_is_lazy_dataclass", True)
        return default_instance

    try:
        return instance.__class__()
    except Exception:
        default_instance = object.__new__(instance.__class__)
        for dc_field in dataclasses.fields(instance):
            if dc_field.default is not dataclasses.MISSING:
                value = dc_field.default
            elif dc_field.default_factory is not dataclasses.MISSING:  # type: ignore
                value = dc_field.default_factory()  # type: ignore
            else:
                value = None
            object.__setattr__(default_instance, dc_field.name, value)
        return default_instance


def _format_dataclass_expression(
    instance: Any,
    context: FormatContext,
) -> Tuple[str, set[Tuple[str, str]], bool]:
    cls = instance.__class__
    import_pair = (cls.__module__, cls.__name__)
    class_name = context.name_mappings.get(import_pair, cls.__name__)
    imports: set[Tuple[str, str]] = {import_pair}

    default_instance = _create_default_instance(instance)

    try:
        type_hints = typing.get_type_hints(instance.__class__)
    except Exception:
        type_hints = {}

    lines: list[str] = []
    field_ctx = context.indented()

    for dc_field in dataclasses.fields(instance):
        field_name = dc_field.name

        if hasattr(instance, "_resolve_field_value"):
            current_value = object.__getattribute__(instance, field_name)
            default_value = object.__getattribute__(default_instance, field_name)
        else:
            current_value = getattr(instance, field_name)
            default_value = getattr(default_instance, field_name)

        if (not context.clean_mode) and current_value is None:
            field_type = type_hints.get(field_name, dc_field.type)
            dataclass_cls = _resolve_dataclass_class_from_type(field_type)
            if dataclass_cls is not None:
                current_value = _create_placeholder_dataclass_instance(dataclass_cls)

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
            if context.clean_mode and not nested_has_fields:
                continue
            imports |= nested_imports
            lines.append(f"{field_name}={nested_code}")
        else:
            frag = to_source(current_value, field_ctx)
            imports |= frag.imports
            lines.append(f"{field_name}={frag.code}")

    if not lines:
        return f"{class_name}()", imports, False

    inner = f",\n{field_ctx.indent_str}".join(lines)
    code = f"{class_name}(\n{field_ctx.indent_str}{inner}\n{context.indent_str})"
    return code, imports, True


class FallbackFormatter(SourceFormatter):
    priority = -100

    def can_format(self, value: Any) -> bool:
        return True

    def format(self, value: Any, context: FormatContext) -> SourceFragment:
        return SourceFragment(repr(value), frozenset())
