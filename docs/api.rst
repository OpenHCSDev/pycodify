API orientation
===============

``Assignment`` and ``CodeBlock``
   Structured top-level source items.

``generate_python_source(obj, header="", clean_mode=False)``
   Generate complete executable source and required imports, with shared and
   repeated absolute paths bound once at the top.

``to_source(value, context=None)``
   Format one value into a ``SourceFragment``.

``SourceFormatter``
   Nominal extension point. Subclasses implement ``can_format`` and ``format``;
   application-specific formatters register without changing pycodify core.

``resolve_imports``
   Resolve import requirements and aliases for colliding names.

``FormatContext`` and ``SourceFragment``
   Immutable formatting state and output records.

``imported_name(module, qualname, context)``
   Spell an importable object by its qualified name, honouring collision aliases.

``PythonSourceLiteral``
   Base for values that spell their own source through ``source_fragment``.

``PathRendering``, ``PathCollector``, ``PathFactoring``, ``PathConstructor``
   How a render pass spells paths: plainly, while recording, or through the
   document's path bindings.

The canonical import surface is ``pycodify.__all__``.

Public API
----------

.. automodule:: pycodify
   :members:
   :member-order: bysource
