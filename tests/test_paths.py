"""Document-level factoring of absolute paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pycodify import Assignment, CodeBlock, generate_python_source


@dataclass(frozen=True)
class PathBearing:
    path: Path
    lookalike: str


def _load(source: str) -> dict[str, object]:
    namespace: dict[str, object] = {}
    exec(source, namespace)
    return namespace


def test_factors_deepest_common_root_and_repeated_values() -> None:
    plate_a = Path("/media/alice/T7/screen/plate_A")
    plate_b = Path("/media/alice/T7/screen/plate_B")
    template = Path("/media/alice/T7/screen/templates/fiducial.png")
    source = generate_python_source(
        CodeBlock(
            (
                Assignment("plate_paths", [plate_a, plate_b]),
                Assignment("pipeline_data", {plate_a: template, plate_b: None}),
            )
        )
    )

    assert "path_root = Path('/media/alice/T7/screen')" in source
    assert "path_1 = path_root / 'plate_A'" in source
    assert "path_2 = path_root / 'plate_B'" in source
    assert "path_root / 'templates' / 'fiducial.png'" in source
    assert source.count("/media/alice/T7/screen") == 1
    namespace = _load(source)
    assert namespace["plate_paths"] == [plate_a, plate_b]
    assert namespace["pipeline_data"] == {plate_a: template, plate_b: None}


def test_relative_paths_and_strings_are_not_factored() -> None:
    source = generate_python_source(
        Assignment(
            "values",
            [Path("templates/fiducial.png"), "/data/screen/a", "/data/screen/a"],
        )
    )

    assert "path_" not in source
    assert "Path('templates/fiducial.png')" in source
    assert source.count("'/data/screen/a'") == 2


def test_unrelated_trees_stay_separate_and_roots_follow_first_occurrence() -> None:
    source = generate_python_source(
        Assignment(
            "values",
            [
                Path("/mnt/zeta/one"),
                Path("/mnt/zeta/two"),
                Path("/data/alpha/one"),
                Path("/data/alpha/two"),
                Path("/srv/lone"),
            ],
        )
    )

    assert source.index("path_root = Path('/mnt/zeta')") < source.index(
        "path_root_2 = Path('/data/alpha')"
    )
    assert "Path('/srv/lone')" in source


def test_one_repeated_path_is_bound_without_a_root() -> None:
    source = generate_python_source(
        Assignment("values", [Path("/opt/models/model.bin")] * 2)
    )

    assert "path_root" not in source
    assert "path_1 = Path('/opt/models/model.bin')" in source
    assert source.count("/opt/models/model.bin") == 1


def test_dataclass_paths_are_factored_but_string_lookalikes_are_not() -> None:
    absolute = Path("/data/screen/config/model.bin")
    value = [PathBearing(absolute, str(absolute))] * 2
    source = generate_python_source(Assignment("configs", value))

    assert source.count("/data/screen/config/model.bin") == 3
    assert "path_1 = Path('/data/screen/config/model.bin')" in source
    assert _load(source)["configs"] == value
