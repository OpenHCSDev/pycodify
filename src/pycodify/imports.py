from __future__ import annotations

from collections import defaultdict
from typing import Dict, FrozenSet, Iterable, List, Optional, Tuple


ImportSpec = Tuple[str, Optional[str]]


def _alias_for_collision(name: str, module: str) -> str:
    return f"{name}_{module.replace('.', '_')}"


def _format_import_target(name: str, alias: Optional[str]) -> str:
    if alias is None:
        return name
    return f"{name} as {alias}"


def _format_module_import(module: str, targets: List[ImportSpec]) -> List[str]:
    if len(targets) == 1:
        name, alias = targets[0]
        return [f"from {module} import {_format_import_target(name, alias)}"]

    lines = [f"from {module} import ("]
    lines.extend(
        f"    {_format_import_target(name, alias)},"
        for name, alias in targets
    )
    lines.append(")")
    return lines


def resolve_imports(
    imports: FrozenSet[Tuple[str, str]] | Iterable[Tuple[str, str]],
) -> Tuple[List[str], Dict[Tuple[str, str], str]]:
    """Resolve import collisions and generate import lines."""
    import_pairs = {pair for pair in imports if pair and pair[0] and pair[1]}

    # Filter out builtins and None modules
    filtered = [
        (module, name)
        for module, name in import_pairs
        if module not in (None, "builtins")
    ]

    name_to_modules = defaultdict(list)
    for module, name in filtered:
        name_to_modules[name].append(module)

    imports_by_module: Dict[str, List[ImportSpec]] = defaultdict(list)
    name_mappings: Dict[Tuple[str, str], str] = {}

    for module, name in sorted(filtered):
        if len(name_to_modules[name]) > 1:
            alias = _alias_for_collision(name, module)
            imports_by_module[module].append((name, alias))
            name_mappings[(module, name)] = alias
        else:
            imports_by_module[module].append((name, None))
            name_mappings[(module, name)] = name

    import_lines: List[str] = []
    for module in sorted(imports_by_module):
        import_lines.extend(
            _format_module_import(
                module,
                sorted(imports_by_module[module], key=lambda target: target[0]),
            )
        )

    return import_lines, name_mappings
