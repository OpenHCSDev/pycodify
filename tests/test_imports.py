"""Tests for pycodify import rendering."""

from pycodify.imports import resolve_imports


def test_resolve_imports_groups_multiple_names_from_same_module():
    import_lines, name_mappings = resolve_imports(
        frozenset(
            {
                ("example.module", "Beta"),
                ("example.module", "Alpha"),
                ("other.module", "Gamma"),
            }
        )
    )

    assert import_lines == [
        "from example.module import (",
        "    Alpha,",
        "    Beta,",
        ")",
        "from other.module import Gamma",
    ]
    assert name_mappings == {
        ("example.module", "Alpha"): "Alpha",
        ("example.module", "Beta"): "Beta",
        ("other.module", "Gamma"): "Gamma",
    }


def test_resolve_imports_groups_alias_collisions_with_module_imports():
    import_lines, name_mappings = resolve_imports(
        frozenset(
            {
                ("alpha.sources", "Config"),
                ("beta.sources", "Config"),
                ("alpha.sources", "Pipeline"),
            }
        )
    )

    assert import_lines == [
        "from alpha.sources import (",
        "    Config as Config_alpha_sources,",
        "    Pipeline,",
        ")",
        "from beta.sources import Config as Config_beta_sources",
    ]
    assert name_mappings == {
        ("alpha.sources", "Config"): "Config_alpha_sources",
        ("alpha.sources", "Pipeline"): "Pipeline",
        ("beta.sources", "Config"): "Config_beta_sources",
    }
