"""Analyze imports and extract symbols."""

from dataclasses import dataclass

from doc_drift_guard.parser.python import Import


@dataclass
class ImportedSymbol:
    """Represents a symbol imported from a module."""

    symbol: str
    module: str
    alias: str | None = None
    level: int = 0  # P1-2 FIX: Relative import level (0=absolute, 1=., 2=.., etc)


def extract_symbols(imports: list[Import]) -> list[ImportedSymbol]:
    """Extract individual symbols from import statements.

    Args:
        imports: List of Import objects

    Returns:
        List of ImportedSymbol objects (star imports are excluded)
    """
    symbols = []

    for imp in imports:
        # Handle plain imports (import math, import os.path) - verify the module itself exists
        if not imp.names:
            # P1-3 FIX: Use FULL module path, not just top-level
            # For "import os.path", verify os.path exists, not just os
            alias = None
            if imp.aliases and len(imp.aliases) > 0:
                alias = list(imp.aliases.keys())[0]
            # Use the full module path for verification
            symbols.append(ImportedSymbol(
                symbol=imp.module,
                module=imp.module,
                alias=alias,
                level=imp.level  # P1-2 FIX: Pass level through
            ))
            continue

        for name in imp.names:
            # Skip star imports - they can't be checked for drift
            if name == "*":
                continue

            alias = None
            # Check if this name has an alias
            for alias_name, original in imp.aliases.items():
                if original == name:
                    alias = alias_name
                    break

            symbols.append(ImportedSymbol(
                symbol=name,
                module=imp.module,
                alias=alias,
                level=imp.level  # P1-2 FIX: Pass level through
            ))

    return symbols


def normalize_import_path(module: str, symbol: str) -> str:
    """Normalize import path to a searchable form.

    Args:
        module: Module name (e.g., 'example')
        symbol: Symbol name (e.g., 'hello_world')

    Returns:
        Normalized path (e.g., 'example.hello_world')
    """
    if not module:
        return symbol
    return f"{module}.{symbol}"
