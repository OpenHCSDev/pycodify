Architecture
============

Two-Pass Algorithm
-------------------

Generating executable source requires knowing import aliases before emitting code. But aliases depend on detecting collisions, which requires visiting all types first. This creates a dependency: code generation requires alias resolution, but alias resolution requires traversing the object graph.

pycodify solves this with two passes:

1. **Collection pass**: Traverse the object, emit code fragments, and collect
   ``(module, name)`` import pairs.
2. **Resolution**: ``resolve_imports`` sorts the pairs, detects names exported by
   more than one module, and derives aliases from each module path.
3. **Regeneration pass**: Re-traverse with the resolved ``name_mappings`` and
   emit final code using those local names.

This is not an optimization—it is structurally necessary. A single-pass algorithm cannot know whether ``Config`` needs aliasing until it has seen all types that might also be named ``Config``.

Extensible Formatter Registry
------------------------------

Each type maps to a ``SourceFormatter`` that emits a ``SourceFragment(code, imports)``. Formatters register via ``__init_subclass__``—defining a formatter class automatically adds it to the registry:

.. code-block:: python

   class EnumFormatter(SourceFormatter):
       priority = 70

       def can_format(self, value: Any) -> bool:
           return isinstance(value, Enum)

       def format(self, value: Enum, context: FormatContext) -> SourceFragment:
           cls = value.__class__
           import_pair = (cls.__module__, cls.__name__)
           name = context.name_mappings.get(import_pair, cls.__name__)
           return SourceFragment(f"{name}.{value.name}", frozenset([import_pair]))

Priority-based dispatch selects the most specific formatter. Domain extensions add formatters without modifying core code.

Core Components
---------------

**SourceFormatter**
  Base class for all formatters. Subclasses implement ``can_format()`` and ``format()`` methods.

**SourceFragment**
  Represents a piece of generated code with its required imports.

**FormatContext**
  Carries indentation depth, ``clean_mode``, the ``(module, name)`` to
  local-name mapping, and caller-owned typed extensions. ``indented()`` returns
  a copied context and does not mutate its caller.

**resolve_imports**
  Detects collisions and returns import lines plus the name mapping used by the
  regeneration pass.

**generate_python_source**
  Orchestrates collection, resolution, and regeneration to produce a complete
  source string.

Immutable typed context extensions
----------------------------------

``FormatContext`` is frozen. Its default mappings are read-only mapping proxies,
and context evolution uses dataclass replacement rather than mutation. A host
may supply an ``extensions`` mapping keyed by the exact nominal type of each
rendering policy or state record. A formatter retrieves one value with
``context.extension(ExtensionType)``; pycodify does not search base classes,
string keys, or a fallback chain.

``generate_python_source(..., context=context)`` threads the caller's context
through collection and regeneration. Import resolution replaces only
``name_mappings`` for the second pass, so typed extensions and all other context
fields survive. When a context is supplied, its ``clean_mode`` is authoritative;
the separate ``clean_mode=`` argument is used only when pycodify constructs the
context.

Extensions provide formatting context, not formatter dispatch. New value
families still extend the ``SourceFormatter`` registry, while the exact extension
type allows that formatter to obtain host-owned rendering information without
adding host imports or fields to pycodify core.

Clean Mode
----------

Clean mode omits fields matching their default values. This requires:

1. Accessing the dataclass field defaults
2. Comparing current values to defaults
3. Omitting fields where ``current_value == default_value``

Explicit mode includes all fields for complete reproducibility.

Stability and trust boundary
----------------------------

Import ordering and collision aliases are deterministic for a fixed set of
``(module, name)`` pairs. The library does not promise that arbitrary object
graphs produce byte-identical text across runs: container iteration, object
``repr`` implementations, custom formatters, and dependency versions can all
affect output or replay.

The output is executable Python. pycodify owns formatting and import resolution,
not sandboxing or validation of generated programs. Hosts must restrict inputs
and custom formatters to trusted sources, review persisted code before running
it, and define their own compatibility policy for imported domain APIs.

Lazy Dataclass Integration
---------------------------

For dataclasses with ``__getattribute__`` interception (used for hierarchical config inheritance), formatters use ``object.__getattribute__`` to access raw field values without triggering lazy resolution:

.. code-block:: python

   # In DataclassFormatter
   if hasattr(instance, "_resolve_field_value"):
       # Bypass __getattribute__ to get raw None vs concrete value
       current_value = object.__getattribute__(instance, field_name)
   else:
       current_value = getattr(instance, field_name)

This distinguishes explicitly-set values from inherited ones during serialization.

Module Structure
----------------

- **core.py**: Main API (``Assignment``, ``generate_python_source``)
- **formatters.py**: Built-in formatters (dataclass, enum, primitive types)
- **imports.py**: Import resolution and collision handling
