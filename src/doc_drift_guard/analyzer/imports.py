"""Analyze imports and extract symbols."""

from dataclasses import dataclass

from doc_drift_guard.parser.python import Import


@dataclass
class ImportedSymbol:
    """Represents a symbol imported from a module."""

    symbol: str
    module: str
    alias: str | None = None


def extract_symbols(imports: list[Import]) -> list[ImportedSymbol]:
    """Extract individual symbols from import statements.

    Args:
        imports: List of Import objects

    Returns:
        List of ImportedSymbol objects (star imports are excluded)
    """
    symbols = []

    for imp in imports:
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
                alias=alias
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
