Architecture
============

Two-Pass Algorithm
-------------------

Generating executable source requires knowing import aliases before emitting code. But aliases depend on detecting collisions, which requires visiting all types first. This creates a dependency: code generation requires alias resolution, but alias resolution requires traversing the object graph.

pycodify solves this with two passes, preceded by a path-discovery pass
(see *Path factoring* below):

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
           enum_type = imported_name(type(value).__module__, type(value).__qualname__, context)
           return SourceFragment(f"{enum_type.code}.{value.name}", enum_type.imports)

Priority-based dispatch selects the most specific formatter. Domain extensions add formatters without modifying core code. A value no formatter accepts raises ``TypeError``: pycodify never emits ``repr`` text it cannot load back.

Qualified names
---------------

``imported_name(module, qualname, context)`` is the one rule for spelling an
importable object. It imports the root of ``__qualname__`` and spells the rest as
attribute access, so ``Outer.Mode.FAST`` imports ``Outer``. Enum members,
classes, functions, class-bound methods, named tuples and dataclass constructors
all use it. Objects defined inside a function raise ``TypeError``.

Values that own their spelling
------------------------------

A value whose source is not its constructor subclasses ``PythonSourceLiteral``
and implements ``source_fragment(context)``, typically building on
``imported_name`` so collision aliases apply.

Core Components
---------------

**SourceFormatter**
  Base class for all formatters. Subclasses implement ``can_format()`` and ``format()`` methods.

**SourceFragment**
  Represents a piece of generated code with its required imports.

**FormatContext**
  Carries indentation depth, ``clean_mode``, the ``(module, name)`` to
  local-name mapping, and the pass's ``PathRendering``. ``indented()`` returns
  a copied context and does not mutate its caller.

**resolve_imports**
  Detects collisions and returns import lines plus the name mapping used by the
  regeneration pass.

**generate_python_source**
  Orchestrates collection, resolution, and regeneration to produce a complete
  source string.

Path factoring
--------------

``generate_python_source`` first renders the document with a ``PathCollector``
on ``FormatContext.paths`` to record every ``pathlib.Path`` value. A
``PathFactoring`` plan then binds each directory shared by two or more absolute
paths (``path_root = Path('/data/screen')``) and each repeated absolute path
(``path_1 = path_root / 'plate_A'``) once, at the top of the document, and the
two rendering passes spell those paths through the bindings. Relative paths and
strings are never factored. ``to_source`` alone uses the base ``PathRendering``,
which spells each path as ``Path('...')``.

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

Module Structure
----------------

- **core.py**: Main API (``Assignment``, ``generate_python_source``)
- **formatters.py**: Built-in formatters (dataclass, enum, class, callable, primitive types)
- **paths.py**: Document-level path factoring

Lazy configuration dataclasses (ObjectState) are formatted by
``objectstate.codegen``, which registers its own formatter.
- **imports.py**: Import resolution and collision handling
