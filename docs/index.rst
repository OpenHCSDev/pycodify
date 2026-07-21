pycodify
========

pycodify serializes Python objects to executable Python source while resolving
imports and name collisions.

Quick start
-----------

.. code-block:: python

   from dataclasses import dataclass
   from pycodify import Assignment, generate_python_source

   @dataclass
   class Config:
       name: str = "default"
       value: int = 42

   config = Config(name="production", value=100)
   code = generate_python_source(Assignment("config", config))

Explicit mode is the default (``clean_mode=False``) and includes default-valued
fields. Pass ``clean_mode=True`` only when default elision is desired.

.. toctree::
   :maxdepth: 2

   usage
   api
   architecture

Ownership
---------

pycodify owns source fragments, imports, formatter registration, collision
handling, and generic Python formatting. Host packages own their domain
formatters and round-trip policies.
