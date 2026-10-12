---
title: 'pycodify: Python Source Code as a Serialization Format'
tags:
  - Python
  - serialization
  - code generation
  - reproducibility
  - configuration
authors:
  - name: Tristan Simas
    orcid: 0000-0002-6526-3149
    affiliation: 1
affiliations:
  - name: McGill University
    index: 1
date: 13 January 2026
bibliography: paper.bib
---

# Summary

`pycodify` writes Python objects as executable Python source. The output is a complete module: the imports it needs, with aliases where two imported names collide, then the code.

```python
# plates.py
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

class Mode(Enum):
    FAST = "fast"
    SLOW = "slow"

@dataclass
class Reader:
    root: Path = Path("data")
    mode: Mode = Mode.FAST
    workers: int = 1
```

```python
from pathlib import Path
from plates import Mode, Reader
from pycodify import Assignment, generate_python_source

reader = Reader(root=Path("/data/screen"), mode=Mode.SLOW)
print(generate_python_source(Assignment("reader", reader), clean_mode=True))
```

prints

```python
from pathlib import Path
from plates import (
    Mode,
    Reader,
)

reader = Reader(
    root=Path('/data/screen'),
    mode=Mode.SLOW
)
```

Executing that text rebuilds an equal object: the test suite checks this for 22 values across the supported types. Python source is the format and the interpreter is the loader.

# Statement of Need

| Format | Diffable | Inspectable | Editable | Type-preserving |
|--------|:--------:|:-----------:|:--------:|:---------------:|
| pickle | ✗ | ✗ | ✗ | ✓ |
| JSON/YAML | ✓ | ✓ | ✓ | ✗ |
| Python source | ✓ | ✓ | ✓ | for supported types |

Binary formats like `pickle` [@pickle] cannot be diffed or edited as text. JSON has no enum, path or callable values, so each must be encoded as a string and decoded by hand. Python source is text, and it names an enum member, a `Path`, a class or a function as itself.

`pycodify` formats `None`, builtin numbers, `bytes`, `str`, lists, tuples, named tuples, dicts, sets, `Path`, enum and flag members, classes, dataclass instances, and importable callables (module-level functions, builtins, class methods). A value with no formatter raises `TypeError`, as does anything defined inside a function. An instance of a subclass of a builtin number type or of `str` (`numpy.float64`, for example) is written as the builtin value it equals, so its type is not kept.

Generated source names classes and functions by import path, so it loads only where those names can be imported. Like any Python file, it must not be executed if it comes from an untrusted source.

# State of the Field

`pickle` [@pickle], `dill` [@dill], and `cloudpickle` [@cloudpickle] serialize to binary. `repr()` returns an expression without imports, and only for types whose `repr` is valid source. `ast.unparse` [@ast] turns a syntax tree into source; it does not take a live object. `pycodify` starts from the object and produces the module with its imports.

# Software Design

## Rendering Passes

A formatter returns a `SourceFragment(code, imports)`, where `imports` is a set of `(module, name)` pairs. Aliases are known only after every pair has been seen, so `generate_python_source` renders more than once:

1. **Path discovery**: render once to record every `pathlib.Path` in the value.
2. **Import collection**: render the body and take the union of the import pairs.
3. **Resolution**: `resolve_imports` finds names imported from more than one module and gives each an alias built from the name and its module.
4. **Final render**: render again with the resulting `name_mappings`.

For `Config` imported from `alpha.sources` and from `beta.sources`, together with `Pipeline`, the import block is

```python
from alpha.sources import (
    Config as Config_alpha_sources,
    Pipeline,
)
from beta.sources import Config as Config_beta_sources
```

and the body uses the aliases. Modules and names are sorted. A nested class or enum is imported by its outermost class and spelled as attribute access (`Outer.Mode.FAST`).

When several absolute paths share a directory below the filesystem root, that directory is bound once (`path_root = Path('/data/screen')`) and each path is written relative to it (`path_root / 'plate_A'`). Relative paths and strings are left alone.

## Formatter Registry

`SourceFormatter` is an abstract base class. Defining a concrete subclass registers an instance of it through `__init_subclass__`. To format a value, the registry asks each formatter's `can_format` in descending `priority` and uses the first that accepts. A library adds its own without changing `pycodify`:

```python
from fractions import Fraction
from pycodify import SourceFormatter, SourceFragment, imported_name

class FractionFormatter(SourceFormatter):
    priority = 65

    def can_format(self, value):
        return isinstance(value, Fraction)

    def format(self, value, context):
        name = imported_name("fractions", "Fraction", context)
        code = f"{name.code}({value.numerator}, {value.denominator})"
        return SourceFragment(code, name.imports)
```

`imported_name` returns the name to use (the alias, if any) and the import pair. A class can instead subclass `PythonSourceLiteral` and implement `source_fragment`; the value then owns its spelling and needs no formatter.

In **clean mode** a dataclass field equal to its default is omitted; otherwise every constructor field is written. A nested dataclass is omitted only if it also has the default's exact type, so a subclass instance is kept.

## Documents

`SourceDocument` is a mixin for a dataclass saved as one module. Each constructor field becomes one module-level assignment named after the field, and `from_source` executes a module and builds the dataclass from those names. The field declarations are the only place the names are written.

# Research Impact Statement

`pycodify` is the code serialization layer of OpenHCS [@openhcs]:

- **GUI editing as code**: a step, a step list and a configuration are each a `SourceDocument`. The GUI, built on `pyqt-reactive` [@pyqtreactor], shows them as Python; the user edits the code and it is loaded back.
- **Remote execution**: the ZMQ execution client sends the global configuration as generated source, and the server rebuilds it with `from_source`.
- **Reproducibility**: a saved pipeline is a Python file stating its parameters.

OpenHCS registers five formatters of its own: for functions, two function-pattern shapes, materialization specs and `FunctionStep`. Its function references subclass `PythonSourceLiteral`: a function owned by a registry is written as a `get_function('<registry>:<key>')` call, any other as a plain import.

# AI Usage Disclosure

Generative AI assisted with drafting documentation. All content was reviewed and tested by human developers.

# Acknowledgements

This work was supported in part by the Fournier lab at the Montreal Neurological Institute, McGill University.

# References
