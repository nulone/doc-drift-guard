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


def _extract_names_from_target(target: ast.AST) -> list[str]:
    """Recursively extract variable names from assignment targets.

    Handles simple names, tuples, and lists for unpacking patterns like:
    - a = 1
    - a, b = 1, 2
    - [x, y] = [1, 2]
    - (a, (b, c)) = (1, (2, 3))

    Args:
        target: AST node representing assignment target

    Returns:
        List of variable names
    """
    if isinstance(target, ast.Name):
        return [target.id]
    elif isinstance(target, (ast.Tuple, ast.List)):
        names = []
        for elt in target.elts:
            names.extend(_extract_names_from_target(elt))
        return names
    elif isinstance(target, ast.Starred):
        # P2 FIX: Handle starred unpacking (a, *b = [1,2,3])
        return _extract_names_from_target(target.value)
    return []


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
    except UnicodeDecodeError:
        return Resolution(symbol=symbol, exists=False, confidence=0.0)
    except (SyntaxError, OSError):
        return Resolution(symbol=symbol, exists=False, confidence=0.0)

    # Check ONLY top-level definitions (P1-1 FIX: don't use ast.walk which traverses nested scopes)
    for node in tree.body:
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
            # P1-2 FIX: Handle tuple/list unpacking recursively
            for target in node.targets:
                names = _extract_names_from_target(target)
                if symbol in names:
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
        elif isinstance(node, ast.ImportFrom):
            # P2-2 FIX: Check re-exports (from .internal import func)
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                if name == symbol:
                    return Resolution(
                        symbol=symbol,
                        exists=True,
                        location=str(file_path),
                        confidence=1.0
                    )
        elif isinstance(node, ast.Import):
            # P2-2 FIX: Check import re-exports (import x as y)
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                if name == symbol:
                    return Resolution(
                        symbol=symbol,
                        exists=True,
                        location=str(file_path),
                        confidence=1.0
                    )

    # P2-1 FIX: Check inside If/Try/With/For blocks (one level deep)
    # This handles common patterns like `if TYPE_CHECKING:` or `try:` blocks
    def check_nested_body(body: list[ast.AST]) -> Resolution | None:
        for child in body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if child.name == symbol:
                    return Resolution(
                        symbol=symbol,
                        exists=True,
                        location=str(file_path),
                        confidence=1.0
                    )
            elif isinstance(child, ast.ClassDef):
                if child.name == symbol:
                    return Resolution(
                        symbol=symbol,
                        exists=True,
                        location=str(file_path),
                        confidence=1.0
                    )
            elif isinstance(child, ast.Assign):
                for target in child.targets:
                    names = _extract_names_from_target(target)
                    if symbol in names:
                        return Resolution(
                            symbol=symbol,
                            exists=True,
                            location=str(file_path),
                            confidence=1.0
                        )
            elif isinstance(child, ast.AnnAssign):
                if isinstance(child.target, ast.Name) and child.target.id == symbol:
                    return Resolution(
                        symbol=symbol,
                        exists=True,
                        location=str(file_path),
                        confidence=1.0
                    )
            elif isinstance(child, ast.ImportFrom):
                for alias in child.names:
                    name = alias.asname if alias.asname else alias.name
                    if name == symbol:
                        return Resolution(
                            symbol=symbol,
                            exists=True,
                            location=str(file_path),
                            confidence=1.0
                        )
            elif isinstance(child, ast.Import):
                for alias in child.names:
                    name = alias.asname if alias.asname else alias.name
                    if name == symbol:
                        return Resolution(
                            symbol=symbol,
                            exists=True,
                            location=str(file_path),
                            confidence=1.0
                        )
        return None

    for node in tree.body:
        if isinstance(node, ast.If):
            result = check_nested_body(node.body)
            if result:
                return result
            result = check_nested_body(node.orelse)
            if result:
                return result
        elif isinstance(node, ast.Try):
            result = check_nested_body(node.body)
            if result:
                return result
            result = check_nested_body(node.orelse)
            if result:
                return result
            result = check_nested_body(node.finalbody)
            if result:
                return result
            for handler in node.handlers:
                result = check_nested_body(handler.body)
                if result:
                    return result
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            result = check_nested_body(node.body)
            if result:
                return result
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            result = check_nested_body(node.body)
            if result:
                return result
            result = check_nested_body(node.orelse)
            if result:
                return result

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

    # Search all .py files (P3-1 FIX: skip symlinks to avoid infinite loops)
    for py_file in src_dir.rglob("*.py"):
        if py_file.is_symlink():
            continue
        result = find_symbol_in_file(symbol, py_file)
        if result.exists:
            return result

    return Resolution(symbol=symbol, exists=False, confidence=0.0)


def resolve_import(module: str, symbol: str, src_dir: Path, level: int = 0) -> Resolution:
    """Resolve an imported symbol.

    Args:
        module: Module name (e.g., 'example')
        symbol: Symbol name (e.g., 'hello_world')
        src_dir: Source directory to search
        level: Relative import level (0=absolute, 1=., 2=.., etc)

    Returns:
        Resolution object
    """
    # Security: Resolve src_dir to prevent path traversal
    try:
        src_dir_resolved = src_dir.resolve()
    except (ValueError, OSError):
        return Resolution(symbol=symbol, exists=False, confidence=0.0)

    # P1-2 FIX: Handle relative imports (level > 0)
    # For `from . import x` (level=1, module=""), search src_dir for the symbol
    # For `from .utils import x` (level=1, module="utils"), search src_dir/utils.py
    # P1 FIX: Navigate up based on level
    # level=1 means "from . import" = current package (src_dir)
    # level=2 means "from .. import" = parent of src_dir
    # level=3 means "from ... import" = grandparent of src_dir
    if level > 0:
        base_path = src_dir_resolved
        if level > 1:
            for _ in range(level - 1):
                new_path = base_path.parent
                # Safety: don't escape src_dir
                if not new_path.is_relative_to(src_dir_resolved):
                    return Resolution(symbol=symbol, exists=False, confidence=0.0)
                base_path = new_path

        if module:
            # Relative import with module: from .submodule import func
            module_parts = module.split('.')
            try:
                module_path = base_path.joinpath(*module_parts).with_suffix('.py')
                module_path_resolved = module_path.resolve()
                if module_path_resolved.exists():
                    return find_symbol_in_file(symbol, module_path)

                # Try as package
                package_path = base_path.joinpath(*module_parts, "__init__.py")
                package_path_resolved = package_path.resolve()
                if package_path_resolved.exists():
                    return find_symbol_in_file(symbol, package_path)
            except (ValueError, OSError):
                pass
            return Resolution(symbol=symbol, exists=False, confidence=0.0)
        else:
            # Bare relative import: from . import helper
            # Search base_path directly for the symbol
            return find_symbol_in_directory(symbol, base_path)

    # For absolute imports, empty module means we cannot verify
    if not module:
        return Resolution(symbol=symbol, exists=False, confidence=0.0)

    # P1-2 FIX: Handle plain imports (import math)
    # When symbol == module, we're checking a plain import - just verify module exists
    if symbol == module:
        # For plain imports, only check if the module file/package exists
        module_parts = module.split('.')

        # Security: Verify path doesn't escape src_dir before constructing
        try:
            # Try as a module file first (e.g., math.py)
            module_path = src_dir.joinpath(*module_parts).with_suffix('.py')
            module_path_resolved = module_path.resolve()
            if module_path_resolved.is_relative_to(src_dir_resolved) and module_path.exists():
                return Resolution(
                    symbol=symbol,
                    exists=True,
                    location=str(module_path),
                    confidence=1.0
                )

            # Try as a package directory (e.g., math/__init__.py)
            package_path = src_dir.joinpath(*module_parts, "__init__.py")
            package_path_resolved = package_path.resolve()
            if package_path_resolved.is_relative_to(src_dir_resolved) and package_path.exists():
                return Resolution(
                    symbol=symbol,
                    exists=True,
                    location=str(package_path),
                    confidence=1.0
                )
        except (ValueError, OSError):
            pass  # Path traversal or other error - continue to return not found

        # Module file/package not found in src_dir
        return Resolution(symbol=symbol, exists=False, confidence=0.0)

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
            return find_symbol_in_file(symbol, package_path)
            # P1-1 FIX: Removed directory-wide fallback search.
            # If symbol not found in __init__.py, return not found immediately.
    except (ValueError, OSError):
        pass

    # Symbol not found in specified module - don't fall back to global search
    return Resolution(symbol=symbol, exists=False, confidence=0.0)
