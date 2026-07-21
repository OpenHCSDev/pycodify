Usage Guide
===========

Basic Usage
-----------

The simplest way to use pycodify is to generate source code for an object:

.. code-block:: python

   from pycodify import Assignment, generate_python_source
   from dataclasses import dataclass

   @dataclass
   class ProcessingConfig:
       input_path: str = "/data/input"
       output_path: str = "/data/output"
       num_workers: int = 4

   config = ProcessingConfig(
       input_path="/data/production",
       num_workers=8
   )

   code = generate_python_source(
       Assignment("config", config),
       clean_mode=True
   )
   print(code)

Clean Mode vs Explicit Mode
----------------------------

**Clean mode** omits fields that match their default values and must be enabled
explicitly:

.. code-block:: python

   # Clean mode - concise
   code = generate_python_source(assignment, clean_mode=True)
   # Output: config = ProcessingConfig(input_path='/data/production', num_workers=8)

**Explicit mode** includes all fields for complete reproducibility and is the
default:

.. code-block:: python

   # Explicit mode - complete
   code = generate_python_source(assignment, clean_mode=False)
   # Output: config = ProcessingConfig(
   #     input_path='/data/production',
   #     output_path='/data/output',
   #     num_workers=8
   # )

Working with Enums
------------------

Enums are serialized with their full qualified names:

.. code-block:: python

   from enum import Enum

   class ImageFormat(Enum):
       JPEG = "jpeg"
       PNG = "png"
       TIFF = "tiff"

   @dataclass
   class ImageConfig:
       format: ImageFormat = ImageFormat.JPEG

   config = ImageConfig(format=ImageFormat.PNG)
   code = generate_python_source(Assignment("config", config))
   # Output includes: from __main__ import ImageFormat
   # config = ImageConfig(format=ImageFormat.PNG)

Handling Import Collisions
---------------------------

When multiple modules export the same name, pycodify aliases every colliding
import. Aliases are derived from the complete module path, with dots replaced
by underscores:

.. code-block:: python

   # pycodify generates:
   # from package.module_a import Config as Config_package_module_a
   # from package.module_b import Config as Config_package_module_b
   # left = Config_package_module_a(...)
   # right = Config_package_module_b(...)

``resolve_imports`` sorts modules and imported names before emitting them, so a
given set of import requirements has stable ordering and aliases. Whole-file
byte-for-byte stability additionally depends on value iteration order, ``repr``
implementations, and any custom formatters.

Formatting one value
--------------------

``to_source`` returns a ``SourceFragment`` rather than a complete file. Pass a
``FormatContext`` when indentation, clean mode, or already-resolved names must
be controlled explicitly:

.. code-block:: python

   from pycodify import FormatContext, to_source

   context = FormatContext(indent=1, clean_mode=True)
   fragment = to_source([1, 2], context)
   print(fragment.code)
   print(fragment.imports)

``FormatContext.indented()`` returns a copy with one additional indentation
level. ``name_mappings`` maps ``(module, imported_name)`` pairs to the local
names chosen by ``resolve_imports``; callers normally let
``generate_python_source`` populate it during the second pass.

Typed rendering extensions
--------------------------

A host can attach immutable rendering context without adding host-specific state
to pycodify. Keys are exact nominal types, and the same context reaches both
render passes:

.. code-block:: python

   from dataclasses import dataclass
   from types import MappingProxyType

   from pycodify import (
       Assignment,
       FormatContext,
       SourceFormatter,
       SourceFragment,
       generate_python_source,
   )

   @dataclass(frozen=True)
   class RenderPolicy:
       marker: str

   class PolicyValue:
       pass

   class PolicyValueFormatter(SourceFormatter):
       priority = 200

       def can_format(self, value):
           return isinstance(value, PolicyValue)

       def format(self, value, context):
           del value
           policy = context.extension(RenderPolicy)
           if policy is None:
               raise RuntimeError("RenderPolicy is required")
           return SourceFragment(repr(policy.marker))

   context = FormatContext(
       clean_mode=True,
       extensions=MappingProxyType(
           {RenderPolicy: RenderPolicy(marker="preserved")}
       ),
   )
   source = generate_python_source(
       Assignment("value", PolicyValue()),
       context=context,
   )
   assert source == "value = 'preserved'"

``extension(RenderPolicy)`` does not return a value stored under a base class or
string key. This exact-type lookup keeps extension ownership explicit. Treat the
extension mapping as immutable; use a new ``FormatContext`` when the host needs
different state.

Nested Dataclasses
-------------------

Nested dataclasses are properly serialized with all necessary imports:

.. code-block:: python

   from dataclasses import dataclass, field

   @dataclass
   class DatabaseConfig:
       host: str = "localhost"
       port: int = 5432

   @dataclass
   class AppConfig:
       database: DatabaseConfig = field(default_factory=DatabaseConfig)
       debug: bool = False

   config = AppConfig(
       database=DatabaseConfig(host="prod.db.internal"),
       debug=True
   )

   code = generate_python_source(Assignment("config", config))
   # Generates imports for both DatabaseConfig and AppConfig

Executing Generated Code
------------------------

The generated code is executable Python:

.. code-block:: python

   code = generate_python_source(assignment)
   namespace = {}
   exec(code, namespace)
   recreated_config = namespace["config"]
   assert recreated_config == original_config

.. warning::

   Generated output is executable Python, not a sandboxed data format. Execute
   it only when the input objects, custom formatters, header, and resulting file
   are trusted and have been reviewed. pycodify does not make ``exec`` safe for
   untrusted input.

Replay compatibility is owned jointly by the generated imports and the APIs
they call. Explicit mode records default-valued fields, but neither mode can
guarantee replay across incompatible module moves or constructor changes.
