"""Document-level factoring of absolute paths.

The contract is on native ``Path`` values: an absolute path on this platform
(``/data`` on POSIX, ``C:\\data`` on Windows) is factored, a relative one is
not, and the generated source loads back as equal ``Path`` objects. Paths are
spelled as ``Path(str(path))`` with the platform's own separators.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pycodify import Assignment, CodeBlock, generate_python_source

ANCHOR = Path(Path.cwd().anchor)
"""The filesystem root of this platform (``/`` or ``C:\\``)."""


def spelled(path: Path) -> str:
    """How generated source spells one path constructor."""

    return f"Path({str(path)!r})"


@dataclass(frozen=True)
class PathBearing:
    path: Path
    lookalike: str


def _load(source: str) -> dict[str, object]:
    namespace: dict[str, object] = {}
    exec(source, namespace)
    return namespace


def test_factors_deepest_common_root_and_repeated_values() -> None:
    screen = ANCHOR / "media" / "alice" / "T7" / "screen"
    plate_a = screen / "plate_A"
    plate_b = screen / "plate_B"
    template = screen / "templates" / "fiducial.png"
    source = generate_python_source(
        CodeBlock(
            (
                Assignment("plate_paths", [plate_a, plate_b]),
                Assignment("pipeline_data", {plate_a: template, plate_b: None}),
            )
        )
    )

    assert f"path_root = {spelled(screen)}" in source
    assert "path_1 = path_root / 'plate_A'" in source
    assert "path_2 = path_root / 'plate_B'" in source
    assert "path_root / 'templates' / 'fiducial.png'" in source
    assert source.count(repr(str(screen))[1:-1]) == 1
    namespace = _load(source)
    assert namespace["plate_paths"] == [plate_a, plate_b]
    assert namespace["pipeline_data"] == {plate_a: template, plate_b: None}


def test_relative_paths_and_strings_are_not_factored() -> None:
    relative = Path("templates") / "fiducial.png"
    lookalike = str(ANCHOR / "data" / "screen" / "a")
    values = [relative, lookalike, lookalike]
    source = generate_python_source(Assignment("values", values))

    assert "path_" not in source
    assert spelled(relative) in source
    assert source.count(repr(lookalike)) == 2
    assert _load(source)["values"] == values


def test_unrelated_trees_stay_separate_and_roots_follow_first_occurrence() -> None:
    zeta = ANCHOR / "mnt" / "zeta"
    alpha = ANCHOR / "data" / "alpha"
    lone = ANCHOR / "srv" / "lone"
    values = [zeta / "one", zeta / "two", alpha / "one", alpha / "two", lone]
    source = generate_python_source(Assignment("values", values))

    assert source.index(f"path_root = {spelled(zeta)}") < source.index(
        f"path_root_2 = {spelled(alpha)}"
    )
    assert spelled(lone) in source
    assert _load(source)["values"] == values


def test_one_repeated_path_is_bound_without_a_root() -> None:
    model = ANCHOR / "opt" / "models" / "model.bin"
    source = generate_python_source(Assignment("values", [model, model]))

    assert "path_root" not in source
    assert f"path_1 = {spelled(model)}" in source
    assert source.count(repr(str(model))[1:-1]) == 1
    assert _load(source)["values"] == [model, model]


def test_dataclass_paths_are_factored_but_string_lookalikes_are_not() -> None:
    absolute = ANCHOR / "data" / "screen" / "config" / "model.bin"
    value = [PathBearing(absolute, str(absolute))] * 2
    source = generate_python_source(Assignment("configs", value))

    assert source.count(repr(str(absolute))[1:-1]) == 3
    assert f"path_1 = {spelled(absolute)}" in source
    assert _load(source)["configs"] == value


def test_temporary_directory_paths_load_back_equal(tmp_path: Path) -> None:
    """A real directory on this platform round-trips through factoring."""

    values = {tmp_path / "plate_A": [tmp_path / "plate_A" / "image.tif"], tmp_path / "plate_B": []}
    source = generate_python_source(Assignment("values", values))

    assert "path_root" in source
    assert _load(source)["values"] == values
