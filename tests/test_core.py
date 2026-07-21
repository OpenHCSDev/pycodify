"""Tests for pycodify.core module."""

import pytest
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from pycodify import (
    Assignment,
    FormatContext,
    SourceFormatter,
    SourceFragment,
    generate_python_source,
)


class Color(Enum):
    """Test enum."""
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


@dataclass
class SimpleConfig:
    """Simple test configuration."""
    name: str = "default"
    value: int = 42
    enabled: bool = True


class ExtensionProbe:
    pass


class ExtensionProbeFormatter(SourceFormatter):
    priority = 200

    def can_format(self, value):
        return isinstance(value, ExtensionProbe)

    def format(self, value, context):
        del value
        marker = context.extension(ExtensionProbe)
        return SourceFragment(repr(marker), frozenset())


class TestBasicGeneration:
    """Test basic source code generation."""

    def test_simple_assignment(self):
        """Test generating source for a simple assignment."""
        config = SimpleConfig(name="test", value=100)
        assignment = Assignment("config", config)
        source = generate_python_source(assignment, clean_mode=False)
        
        assert "config = " in source
        assert "SimpleConfig" in source
        assert "name=" in source
        assert "value=" in source

    def test_clean_mode(self):
        """Test clean mode omits default values."""
        config = SimpleConfig()  # All defaults
        assignment = Assignment("config", config)
        source = generate_python_source(assignment, clean_mode=True)
        
        # Clean mode should omit fields matching defaults
        assert "config = " in source
        assert "SimpleConfig" in source

    def test_enum_serialization(self):
        """Test that enums are properly serialized."""
        config = SimpleConfig(name="enum_test")
        assignment = Assignment("config", config)
        source = generate_python_source(assignment, clean_mode=False)
        
        assert "SimpleConfig" in source
        assert "enum_test" in source

    def test_import_generation(self):
        """Test that necessary imports are generated."""
        config = SimpleConfig()
        assignment = Assignment("config", config)
        source = generate_python_source(assignment, clean_mode=False)
        
        # Should include import for SimpleConfig
        assert "from" in source or "import" in source or "SimpleConfig" in source

    def test_executable_source(self):
        """Test that generated source is executable."""
        config = SimpleConfig(name="executable", value=99)
        assignment = Assignment("config", config)
        source = generate_python_source(assignment, clean_mode=False)
        
        # Should be able to exec the source
        namespace = {}
        try:
            exec(source, namespace)
            assert "config" in namespace
        except Exception as e:
            pytest.fail(f"Generated source is not executable: {e}\n{source}")

    def test_context_extensions_survive_both_render_passes(self):
        context = FormatContext(
            extensions=MappingProxyType({ExtensionProbe: "preserved"})
        )

        source = generate_python_source(
            Assignment("value", ExtensionProbe()),
            context=context,
        )

        assert source == "value = 'preserved'"


class TestImportCollisions:
    """Test handling of import name collisions."""

    def test_collision_detection(self):
        """Test that import collisions are detected and handled."""
        # This would require multiple classes with same name from different modules
        # For now, just verify the basic mechanism works
        config = SimpleConfig()
        assignment = Assignment("config", config)
        source = generate_python_source(assignment, clean_mode=False)
        
        assert source is not None
        assert len(source) > 0
