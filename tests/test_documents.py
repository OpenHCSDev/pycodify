"""A SourceDocument dataclass is saved as, and loaded from, its field names."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from pycodify import SourceDocument


@dataclass(frozen=True)
class Recipe(SourceDocument):
    title: str
    steps: list[str] = field(default_factory=list)
    loaded_from: str | None = field(default=None, init=False, compare=False)


def test_assignment_names_are_the_constructor_fields() -> None:
    assert Recipe.assignment_names() == ("title", "steps")


def test_source_assigns_each_field_once_and_loads_back_equal() -> None:
    recipe = Recipe(title="tea", steps=["boil", "steep"])

    source = recipe.to_source(header="# Recipe")

    assert source.splitlines()[0] == "# Recipe"
    namespace: dict[str, object] = {}
    exec(source, namespace)
    assert {name for name in namespace if not name.startswith("__")} == {"title", "steps"}
    assert Recipe.from_source(source) == recipe


def test_absent_field_takes_its_declared_default() -> None:
    assert Recipe.from_namespace({"title": "tea"}) == Recipe(title="tea")


def test_absent_required_field_is_an_error() -> None:
    with pytest.raises(ValueError, match="Recipe source must define 'title'"):
        Recipe.from_namespace({"steps": []})


def test_names_outside_the_declaration_are_ignored() -> None:
    assert Recipe.from_namespace({"title": "tea", "other": 1}) == Recipe(title="tea")
