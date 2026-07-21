API orientation
===============

``Assignment`` and ``CodeBlock``
   Structured top-level source items.

``generate_python_source(obj, header="", clean_mode=False, *, context=None)``
   Generate complete executable source and required imports. A caller-supplied
   ``FormatContext`` is retained across both render passes and owns clean mode.

``to_source(value, context=None)``
   Format one value into a ``SourceFragment``.

``SourceFormatter``
   Nominal extension point. Subclasses implement ``can_format`` and ``format``;
   application-specific formatters register without changing pycodify core.

``resolve_imports``
   Resolve import requirements and aliases for colliding names.

``FormatContext`` and ``SourceFragment``
   Immutable typed formatting state and output records. ``FormatContext`` may
   carry exact-type ``extensions`` and exposes them through ``extension(type)``.

The canonical import surface is ``pycodify.__all__``.

Public API
----------

.. automodule:: pycodify
   :members:
   :member-order: bysource
