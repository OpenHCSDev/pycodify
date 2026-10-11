"""Generated source loads back as an equal value, for every value family."""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

import pytest

from pycodify import (
    Assignment,
    CodeBlock,
    FormatContext,
    PythonSourceLiteral,
    SourceFragment,
    generate_python_source,
    imported_name,
    to_source,
)


class Outer:
    class Mode(enum.Enum):
        FAST = "fast"
        SLOW = "slow"

    class Inner:
        pass

    @staticmethod
    def helper(value):
        return value

    @classmethod
    def build(cls):
        return cls()


class Permission(enum.Flag):
    READ = 1
    WRITE = 2


def module_function(value):
    return value


class Point(NamedTuple):
    x: int
    y: int


@dataclass(frozen=True)
class Leaf:
    size: int = 1


@dataclass(frozen=True)
class Owner:
    mode: Outer.Mode = Outer.Mode.FAST
    kind: type = int
    leaf: Leaf | None = None
    derived: int = field(default=0, init=False)


@dataclass(frozen=True)
class Twice(PythonSourceLiteral):
    value: int

    def source_fragment(self, context: FormatContext) -> SourceFragment:
        owner = imported_name(type(self).__module__, type(self).__qualname__, context)
        return SourceFragment(f"{owner.code}({self.value} * 1)", owner.imports)


VALUES = (
    Outer.Mode.SLOW,
    Permission.READ | Permission.WRITE,
    Outer.Inner,
    Outer.Mode,
    int,
    module_function,
    Outer.helper,
    Outer.build,
    len,
    math.sqrt,
    Point(1, 2),
    frozenset({"b", "a"}),
    {3, 1, 2},
    b"bytes",
    1 + 2j,
    float("inf"),
    -float("inf"),
    {"key": [Path("/data/screen/a"), Path("/data/screen/b"), Path("relative/c")]},
    (Path("/opt/model.bin"), Path("/opt/model.bin")),
    Owner(mode=Outer.Mode.SLOW, kind=Outer.Inner, leaf=None),
    Owner(leaf=Leaf(size=3)),
    Twice(4),
)


@pytest.mark.parametrize("clean_mode", (True, False))
@pytest.mark.parametrize("value", VALUES, ids=repr)
def test_generated_source_loads_back_equal(value, clean_mode):
    source = generate_python_source(Assignment("value", value), clean_mode=clean_mode)
    namespace: dict[str, object] = {}
    exec(source, namespace)
    assert namespace["value"] == value, source


def test_nan_loads_back_as_nan():
    namespace: dict[str, object] = {}
    exec(generate_python_source(Assignment("value", float("nan"))), namespace)
    assert math.isnan(namespace["value"])


def test_nested_enum_imports_its_outermost_class():
    source = generate_python_source(Assignment("value", Outer.Mode.FAST))
    assert f"from {__name__} import Outer" in source
    assert "value = Outer.Mode.FAST" in source


def test_qualified_names_use_collision_aliases():
    source = generate_python_source(
        CodeBlock((Assignment("a", Outer.Mode.FAST), Assignment("b", enum.Enum)))
    )
    assert "a = Outer.Mode.FAST" in source
    assert "b = Enum" in source


class Unformattable:
    pass


def test_values_without_a_formatter_fail_loudly():
    with pytest.raises(TypeError, match="No formatter"):
        to_source(Unformattable())


def test_function_local_objects_fail_loudly():
    class Local(enum.Enum):
        ONE = 1

    with pytest.raises(TypeError, match="defined inside a function"):
        to_source(Local.ONE)
