"""Resolve symbols in the codebase."""

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Resolution:
    """Result of symbol resolution."""

    symbol: str
    exists: bool
    location: str | None = None
    confidence: float = 1.0


def find_symbol_in_file(symbol: str, file_path: Path) -> Resolution:
    """Check if a symbol exists in a Python file.

    Args:
        symbol: Symbol name to search for
        file_path: Path to Python file

    Returns:
        Resolution object
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except (SyntaxError, OSError):
        return Resolution(symbol=symbol, exists=False, confidence=0.0)

    # Check for function definitions, class definitions, and module-level variables
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
            return Resolution(
                symbol=symbol,
                exists=True,
                location=str(file_path),
                confidence=1.0
            )
        elif isinstance(node, ast.ClassDef) and node.name == symbol:
            return Resolution(
                symbol=symbol,
                exists=True,
                location=str(file_path),
                confidence=1.0
            )
        elif isinstance(node, ast.Assign):
            # Check module-level assignments: VAR = value
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == symbol:
                    return Resolution(
                        symbol=symbol,
                        exists=True,
                        location=str(file_path),
                        confidence=1.0
                    )
        elif isinstance(node, ast.AnnAssign):
            # Check annotated assignments: VAR: type = value
            if isinstance(node.target, ast.Name) and node.target.id == symbol:
                return Resolution(
                    symbol=symbol,
                    exists=True,
                    location=str(file_path),
                    confidence=1.0
                )

    return Resolution(symbol=symbol, exists=False, confidence=0.0)


def find_symbol_in_directory(symbol: str, src_dir: Path) -> Resolution:
    """Search for a symbol in all Python files in a directory.

    Args:
        symbol: Symbol name to search for
        src_dir: Directory to search

    Returns:
        Resolution object
    """
    if not src_dir.exists() or not src_dir.is_dir():
        return Resolution(symbol=symbol, exists=False, confidence=0.0)

    # Search all .py files
    for py_file in src_dir.rglob("*.py"):
        result = find_symbol_in_file(symbol, py_file)
        if result.exists:
            return result

    return Resolution(symbol=symbol, exists=False, confidence=0.0)


def resolve_import(module: str, symbol: str, src_dir: Path) -> Resolution:
    """Resolve an imported symbol.

    Args:
        module: Module name (e.g., 'example')
        symbol: Symbol name (e.g., 'hello_world')
        src_dir: Source directory to search

    Returns:
        Resolution object
    """
    # Security: Resolve src_dir to prevent path traversal
    try:
        src_dir_resolved = src_dir.resolve()
    except (ValueError, OSError):
        return Resolution(symbol=symbol, exists=False, confidence=0.0)

    # Handle empty module (relative imports) - search entire src_dir
    if not module:
        return find_symbol_in_directory(symbol, src_dir)

    # Try to find the module file
    # Handle dotted module names: pkg.sub → pkg/sub.py
    module_parts = module.split('.')

    # Security: Verify path doesn't escape src_dir before constructing
    try:
        module_path = src_dir.joinpath(*module_parts).with_suffix('.py')
        module_path_resolved = module_path.resolve()
        if module_path_resolved.is_relative_to(src_dir_resolved) and module_path.exists():
            return find_symbol_in_file(symbol, module_path)
    except (ValueError, OSError):
        pass  # Continue to try other paths (handles invalid paths, root paths, etc.)

    # Try as a package
    package_path = src_dir.joinpath(*module_parts, "__init__.py")

    # Security: Verify path doesn't escape src_dir
    try:
        package_path_resolved = package_path.resolve()
        if package_path_resolved.is_relative_to(src_dir_resolved) and package_path.exists():
            result = find_symbol_in_file(symbol, package_path)
            if result.exists:
                return result

            # Search the whole package directory
            package_dir = src_dir.joinpath(*module_parts)
            package_dir_resolved = package_dir.resolve()
            if package_dir_resolved.is_relative_to(src_dir_resolved):
                return find_symbol_in_directory(symbol, package_dir)
    except (ValueError, OSError):
        pass  # Continue to fallback

    # Fall back to searching the entire source directory
    return find_symbol_in_directory(symbol, src_dir)
