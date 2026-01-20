"""Parse Python code using AST."""

import ast
from dataclasses import dataclass


@dataclass
class Import:
    """Represents an import statement."""

    module: str
    names: list[str]
    aliases: dict[str, str]
    level: int = 0  # P1-3 FIX: Relative import level (0=absolute, 1=., 2=.., etc)


@dataclass
class FunctionCall:
    """Represents a function call."""

    name: str
    line: int


def parse_imports(code: str) -> list[Import]:
    """Extract import statements from Python code.

    Args:
        code: Python source code

    Returns:
        List of Import objects

    Raises:
        SyntaxError: If code is not valid Python
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SyntaxError(f"Failed to parse Python code: {e}") from e

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # Plain imports (import foo) don't import specific symbols
            # We only need to verify the module exists
            for alias in node.names:
                imports.append(Import(
                    module=alias.name,
                    names=[],  # Empty - only check module existence
                    aliases={alias.asname: alias.name} if alias.asname else {}
                ))

        elif isinstance(node, ast.ImportFrom):
            # Handle both absolute and relative imports
            # For relative imports (level > 0), node.module may be None
            module = node.module or ""  # Use empty string for bare relative imports
            names = [alias.name for alias in node.names]
            aliases = {
                alias.asname: alias.name
                for alias in node.names
                if alias.asname
            }
            imports.append(Import(
                module=module,
                names=names,
                aliases=aliases,
                level=node.level  # P1-3 FIX: Preserve relative import level
            ))

    return imports


def parse_function_calls(code: str) -> list[FunctionCall]:
    """Extract function calls from Python code.

    Args:
        code: Python source code

    Returns:
        List of FunctionCall objects

    Raises:
        SyntaxError: If code is not valid Python
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SyntaxError(f"Failed to parse Python code: {e}") from e

    calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Handle simple function calls (name()) and attribute calls (obj.method())
            if isinstance(node.func, ast.Name):
                calls.append(FunctionCall(
                    name=node.func.id,
                    line=node.lineno
                ))
            elif isinstance(node.func, ast.Attribute):
                calls.append(FunctionCall(
                    name=node.func.attr,
                    line=node.lineno
                ))

    return calls


def get_referenced_symbols(code: str) -> set[str]:
    """Get all symbols referenced in Python code (imports + function calls).

    Args:
        code: Python source code

    Returns:
        Set of symbol names

    Raises:
        SyntaxError: If code is not valid Python
    """
    symbols = set()

    # Add imported names
    imports = parse_imports(code)
    for imp in imports:
        symbols.update(imp.names)

    # Add function calls
    calls = parse_function_calls(code)
    for call in calls:
        symbols.add(call.name)

    return symbols
