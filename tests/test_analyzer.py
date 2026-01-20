"""Tests for analyzer modules."""

from pathlib import Path

import pytest

from doc_drift_guard.analyzer.imports import extract_symbols, normalize_import_path
from doc_drift_guard.analyzer.resolver import (
    find_symbol_in_directory,
    find_symbol_in_file,
    resolve_import,
)
from doc_drift_guard.parser.python import Import


class TestImportsAnalyzer:
    """Tests for imports analyzer."""

    def test_extract_symbols_simple(self):
        """Test extracting symbols from simple import."""
        imports = [Import(module="example", names=["hello_world"], aliases={})]
        symbols = extract_symbols(imports)
        assert len(symbols) == 1
        assert symbols[0].symbol == "hello_world"
        assert symbols[0].module == "example"

    def test_extract_symbols_multiple(self):
        """Test extracting multiple symbols."""
        imports = [
            Import(
                module="example",
                names=["hello_world", "another_function"],
                aliases={}
            )
        ]
        symbols = extract_symbols(imports)
        assert len(symbols) == 2
        names = [s.symbol for s in symbols]
        assert "hello_world" in names
        assert "another_function" in names

    def test_extract_symbols_with_alias(self):
        """Test extracting symbols with aliases."""
        imports = [
            Import(
                module="example",
                names=["hello_world"],
                aliases={"hw": "hello_world"}
            )
        ]
        symbols = extract_symbols(imports)
        assert len(symbols) == 1
        assert symbols[0].symbol == "hello_world"
        assert symbols[0].alias == "hw"

    def test_normalize_import_path(self):
        """Test normalizing import paths."""
        assert normalize_import_path("example", "hello_world") == "example.hello_world"
        assert normalize_import_path("", "hello_world") == "hello_world"

    def test_extract_symbols_star_import_filtered(self):
        """Test star imports are filtered out (BUG FIX)."""
        imports = [Import(module="example", names=["*"], aliases={})]
        symbols = extract_symbols(imports)
        # Star imports should be filtered out
        assert len(symbols) == 0

    def test_extract_symbols_star_mixed_with_regular(self):
        """Test star imports filtered but regular imports kept (BUG FIX)."""
        imports = [
            Import(module="example", names=["func1", "*", "func2"], aliases={})
        ]
        symbols = extract_symbols(imports)
        # Should have 2 symbols, star filtered out
        assert len(symbols) == 2
        names = [s.symbol for s in symbols]
        assert "func1" in names
        assert "func2" in names
        assert "*" not in names

    def test_extract_symbols_plain_import(self):
        """Test plain imports (import math) are extracted (P1-2 FIX)."""
        imports = [Import(module="math", names=[], aliases={})]
        symbols = extract_symbols(imports)
        # Should have 1 symbol - the module name itself
        assert len(symbols) == 1
        assert symbols[0].symbol == "math"
        assert symbols[0].module == "math"

    def test_extract_symbols_plain_import_with_alias(self):
        """Test plain imports with alias (import math as m) are extracted (P1-2 FIX)."""
        imports = [Import(module="math", names=[], aliases={"m": "math"})]
        symbols = extract_symbols(imports)
        # Should have 1 symbol - the module name itself
        assert len(symbols) == 1
        assert symbols[0].symbol == "math"
        assert symbols[0].module == "math"
        assert symbols[0].alias == "m"

    def test_extract_symbols_plain_import_dotted(self):
        """Test plain imports of dotted modules (import os.path) are extracted (P1-3 FIX)."""
        imports = [Import(module="os.path", names=[], aliases={})]
        symbols = extract_symbols(imports)
        # P1-3 FIX: Should verify the FULL module path "os.path", not just "os"
        assert len(symbols) == 1
        assert symbols[0].symbol == "os.path"
        assert symbols[0].module == "os.path"

    def test_extract_symbols_plain_import_no_crash_empty_aliases(self):
        """Test plain imports with empty aliases don't crash (P1-1 FIX)."""
        # This should not raise IndexError
        imports = [Import(module="math", names=[], aliases={})]
        symbols = extract_symbols(imports)
        assert len(symbols) == 1
        assert symbols[0].alias is None

    def test_extract_symbols_plain_import_no_crash_with_alias(self):
        """Test plain imports with alias don't crash (P1-1 FIX)."""
        # This should not raise IndexError
        imports = [Import(module="math", names=[], aliases={"m": "math"})]
        symbols = extract_symbols(imports)
        assert len(symbols) == 1
        assert symbols[0].symbol == "math"
        assert symbols[0].alias == "m"


class TestResolver:
    """Tests for resolver."""

    @pytest.fixture
    def sample_file(self, tmp_path):
        """Create a sample Python file for testing."""
        file_path = tmp_path / "test.py"
        file_path.write_text("""
def hello_world():
    pass

class MyClass:
    pass
""", encoding="utf-8")
        return file_path

    def test_find_symbol_in_file_function(self, sample_file):
        """Test finding a function symbol in a file."""
        result = find_symbol_in_file("hello_world", sample_file)
        assert result.exists
        assert result.symbol == "hello_world"
        assert str(sample_file) in result.location

    def test_find_symbol_in_file_class(self, sample_file):
        """Test finding a class symbol in a file."""
        result = find_symbol_in_file("MyClass", sample_file)
        assert result.exists
        assert result.symbol == "MyClass"

    def test_find_symbol_in_file_not_found(self, sample_file):
        """Test symbol not found in file."""
        result = find_symbol_in_file("non_existent", sample_file)
        assert not result.exists
        assert result.symbol == "non_existent"

    def test_find_symbol_in_directory(self, tmp_path):
        """Test finding symbol in directory."""
        # Create test files
        file1 = tmp_path / "file1.py"
        file1.write_text("def func1(): pass", encoding="utf-8")

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        file2 = subdir / "file2.py"
        file2.write_text("def target_func(): pass", encoding="utf-8")

        result = find_symbol_in_directory("target_func", tmp_path)
        assert result.exists
        assert result.symbol == "target_func"

    def test_resolve_import_direct_module(self):
        """Test resolving import from direct module file."""
        # Use the fixtures directory
        fixtures_dir = Path(__file__).parent / "fixtures" / "sample_src"
        result = resolve_import("example", "hello_world", fixtures_dir)
        assert result.exists
        assert result.symbol == "hello_world"

    def test_resolve_import_not_found(self, tmp_path):
        """Test resolving non-existent import."""
        result = resolve_import("nonexistent", "func", tmp_path)
        assert not result.exists

    def test_resolve_dotted_module(self, tmp_path):
        """Test resolving import from dotted module (BUG-1)."""
        # Create pkg/sub.py with a function
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
        sub_file = pkg_dir / "sub.py"
        sub_file.write_text("def dotted_func(): pass", encoding="utf-8")

        result = resolve_import("pkg.sub", "dotted_func", tmp_path)
        assert result.exists
        assert result.symbol == "dotted_func"

    def test_path_traversal_security(self, tmp_path):
        """Test path traversal attack is prevented (BUG-3)."""
        # Try to escape src_dir with ../../../
        result = resolve_import("../../../etc/passwd", "root", tmp_path)
        assert not result.exists

        # Try another variant
        result = resolve_import("../..", "somefunc", tmp_path)
        assert not result.exists

    def test_find_async_function(self, tmp_path):
        """Test finding async function symbols (BUG FIX)."""
        file_path = tmp_path / "async_test.py"
        file_path.write_text("""
async def async_func():
    pass

async def another_async():
    return 42
""", encoding="utf-8")
        result = find_symbol_in_file("async_func", file_path)
        assert result.exists
        assert result.symbol == "async_func"

        result2 = find_symbol_in_file("another_async", file_path)
        assert result2.exists

    def test_find_module_variable(self, tmp_path):
        """Test finding module-level variables (BUG FIX)."""
        file_path = tmp_path / "vars_test.py"
        file_path.write_text("""
VERSION = "1.0.0"
CONFIG = {"key": "value"}
DEBUG = True
""", encoding="utf-8")
        result = find_symbol_in_file("VERSION", file_path)
        assert result.exists
        assert result.symbol == "VERSION"

        result2 = find_symbol_in_file("CONFIG", file_path)
        assert result2.exists

    def test_find_annotated_variable(self, tmp_path):
        """Test finding annotated variables (BUG FIX)."""
        file_path = tmp_path / "annotated_test.py"
        file_path.write_text("""
API_KEY: str = "secret"
MAX_RETRIES: int = 3
""", encoding="utf-8")
        result = find_symbol_in_file("API_KEY", file_path)
        assert result.exists
        assert result.symbol == "API_KEY"

        result2 = find_symbol_in_file("MAX_RETRIES", file_path)
        assert result2.exists

    def test_resolve_import_no_global_fallback(self, tmp_path):
        """Test that resolve_import doesn't fall back to global search (P1-1 FIX).

        If a symbol is imported from a specific module but doesn't exist there,
        it should return exists=False even if the symbol exists elsewhere.
        """
        # Create module_a.py with target_func
        module_a = tmp_path / "module_a.py"
        module_a.write_text("def target_func(): pass", encoding="utf-8")

        # Create module_b.py without target_func
        module_b = tmp_path / "module_b.py"
        module_b.write_text("def other_func(): pass", encoding="utf-8")

        # Try to import target_func from module_b (where it doesn't exist)
        # It should return exists=False, not find it in module_a
        result = resolve_import("module_b", "target_func", tmp_path)
        assert not result.exists
        assert result.symbol == "target_func"

    def test_resolve_import_package_no_global_fallback(self, tmp_path):
        """Test package import doesn't fall back to global search (P1-1 FIX)."""
        # Create pkg1/func.py with target_func
        pkg1 = tmp_path / "pkg1"
        pkg1.mkdir()
        (pkg1 / "__init__.py").write_text("", encoding="utf-8")
        (pkg1 / "module.py").write_text("def target_func(): pass", encoding="utf-8")

        # Create pkg2/ without target_func
        pkg2 = tmp_path / "pkg2"
        pkg2.mkdir()
        (pkg2 / "__init__.py").write_text("", encoding="utf-8")
        (pkg2 / "module.py").write_text("def other_func(): pass", encoding="utf-8")

        # Try to import target_func from pkg2 (where it doesn't exist)
        result = resolve_import("pkg2", "target_func", tmp_path)
        assert not result.exists
        assert result.symbol == "target_func"

    def test_resolve_plain_import_module_file_exists(self, tmp_path):
        """Test plain import succeeds when module file exists (P1-2 FIX)."""
        # Create mymodule.py with some content
        mymodule = tmp_path / "mymodule.py"
        mymodule.write_text("def some_func(): pass\nVERSION = '1.0'", encoding="utf-8")

        # Plain import: import mymodule
        # symbol == module, so we only check if mymodule.py exists
        result = resolve_import("mymodule", "mymodule", tmp_path)
        assert result.exists
        assert result.symbol == "mymodule"
        assert str(tmp_path / "mymodule.py") in result.location

    def test_resolve_plain_import_package_exists(self, tmp_path):
        """Test plain import succeeds when package exists (P1-2 FIX)."""
        # Create mypkg/__init__.py
        mypkg = tmp_path / "mypkg"
        mypkg.mkdir()
        (mypkg / "__init__.py").write_text("def pkg_func(): pass", encoding="utf-8")

        # Plain import: import mypkg
        # symbol == module, so we only check if mypkg/__init__.py exists
        result = resolve_import("mypkg", "mypkg", tmp_path)
        assert result.exists
        assert result.symbol == "mypkg"

    def test_resolve_plain_import_module_not_exists(self, tmp_path):
        """Test plain import fails when module doesn't exist (P1-2 FIX)."""
        # No module file created
        # Plain import: import nonexistent
        result = resolve_import("nonexistent", "nonexistent", tmp_path)
        assert not result.exists
        assert result.symbol == "nonexistent"

    def test_resolve_empty_module_no_global_fallback(self, tmp_path):
        """Test empty module doesn't fall back to global search (P1-3 FIX)."""
        # Create a module with a function
        (tmp_path / "module.py").write_text("def my_func(): pass", encoding="utf-8")

        # Try to resolve with empty module (relative import without context)
        # This should return drift, not search the entire directory
        result = resolve_import("", "my_func", tmp_path)
        assert not result.exists
        assert result.symbol == "my_func"

    def test_find_symbol_tuple_unpacking(self, tmp_path):
        """Test finding symbols from tuple unpacking (P1-2 FIX)."""
        file_path = tmp_path / "tuple_test.py"
        file_path.write_text("""
# Tuple unpacking
A, B = 1, 2
X, Y, Z = (10, 20, 30)

# List unpacking
[M, N] = [100, 200]

# Nested unpacking
(P, (Q, R)) = (1, (2, 3))
""", encoding="utf-8")
        # Should find A from tuple unpacking
        result = find_symbol_in_file("A", file_path)
        assert result.exists
        assert result.symbol == "A"

        # Should find B
        result = find_symbol_in_file("B", file_path)
        assert result.exists

        # Should find from list unpacking
        result = find_symbol_in_file("M", file_path)
        assert result.exists

        # Should find from nested unpacking
        result = find_symbol_in_file("Q", file_path)
        assert result.exists

    def test_find_symbol_scope_blindness_fix(self, tmp_path):
        """Test that local variables inside functions are NOT found at module level (P1-1 FIX)."""
        file_path = tmp_path / "scope_test.py"
        file_path.write_text("""
# Module-level variable
MODULE_VAR = "visible"

def some_function():
    # Local variable - should NOT be found as module-level
    SECRET = "hidden"
    LOCAL_VAR = 123

class MyClass:
    # Class attribute - should NOT be found as module-level
    CLASS_ATTR = "class_level"

    def method(self):
        METHOD_VAR = "method_local"
""", encoding="utf-8")
        # Module-level variable SHOULD be found
        result = find_symbol_in_file("MODULE_VAR", file_path)
        assert result.exists

        # Local variable inside function should NOT be found
        result = find_symbol_in_file("SECRET", file_path)
        assert not result.exists, "SECRET is a local variable, should not be found at module level"

        result = find_symbol_in_file("LOCAL_VAR", file_path)
        assert not result.exists, "LOCAL_VAR is local, not module-level"

        # Class attribute should NOT be found as module-level
        result = find_symbol_in_file("CLASS_ATTR", file_path)
        assert not result.exists, "CLASS_ATTR is a class attribute, not module-level"

        # Method local should NOT be found
        result = find_symbol_in_file("METHOD_VAR", file_path)
        assert not result.exists, "METHOD_VAR is a method local, not module-level"

    def test_find_symbol_starred_unpacking(self, tmp_path):
        """Test finding symbols from starred unpacking (P2 FIX)."""
        file_path = tmp_path / "starred_test.py"
        file_path.write_text("""
# Starred unpacking
first, *rest = [1, 2, 3, 4]
a, *middle, z = range(10)
*head, last = "hello"
""", encoding="utf-8")
        # Should find all variables including starred ones
        result = find_symbol_in_file("first", file_path)
        assert result.exists

        result = find_symbol_in_file("rest", file_path)
        assert result.exists, "Starred variable 'rest' should be found"

        result = find_symbol_in_file("middle", file_path)
        assert result.exists, "Starred variable 'middle' should be found"

        result = find_symbol_in_file("head", file_path)
        assert result.exists, "Starred variable 'head' should be found"

    def test_resolve_relative_import_bare(self, tmp_path):
        """Test relative import with bare from . import (P1-2 FIX)."""
        # Create helper.py with a function
        (tmp_path / "helper.py").write_text("def helper_func(): pass", encoding="utf-8")

        # from . import helper_func (level=1, module="")
        result = resolve_import("", "helper_func", tmp_path, level=1)
        assert result.exists, "Bare relative import should find symbol in src_dir"

    def test_resolve_relative_import_with_module(self, tmp_path):
        """Test relative import with module from .utils import func (P1-2 FIX)."""
        # Create utils.py with a function
        (tmp_path / "utils.py").write_text("def util_func(): pass", encoding="utf-8")

        # from .utils import util_func (level=1, module="utils")
        result = resolve_import("utils", "util_func", tmp_path, level=1)
        assert result.exists, "Relative import with module should find symbol"

    def test_resolve_relative_import_not_found(self, tmp_path):
        """Test relative import returns not found when symbol doesn't exist (P1-2 FIX)."""
        # Create empty module
        (tmp_path / "utils.py").write_text("def other_func(): pass", encoding="utf-8")

        # from .utils import nonexistent (level=1, module="utils")
        result = resolve_import("utils", "nonexistent", tmp_path, level=1)
        assert not result.exists

    def test_resolve_absolute_import_empty_module_fails(self, tmp_path):
        """Test absolute import with empty module fails (not relative) (P1-2 FIX)."""
        # Create helper.py
        (tmp_path / "helper.py").write_text("def helper_func(): pass", encoding="utf-8")

        # Absolute import with empty module should fail (level=0)
        result = resolve_import("", "helper_func", tmp_path, level=0)
        assert not result.exists, "Absolute import with empty module should not search globally"

    def test_resolve_relative_import_level_2_blocked_by_stricter_security(self, tmp_path):
        """Test from ..module is blocked by stricter path traversal security (P1-2 FIX).

        With stricter security, relative imports cannot escape src_dir at all.
        level=2 from subpkg would traverse to tmp_path (parent), which is now blocked.
        """
        # Create structure:
        # tmp_path/
        #   utils.py (with target_func)
        #   subpkg/
        #     __init__.py (we're "in" here, src_dir=subpkg)

        # Create utils.py at tmp_path level
        (tmp_path / "utils.py").write_text("def target_func(): pass", encoding="utf-8")

        # Create subpkg directory
        subpkg = tmp_path / "subpkg"
        subpkg.mkdir()
        (subpkg / "__init__.py").write_text("", encoding="utf-8")

        # from ..utils import target_func (level=2, module="utils")
        # Starting from subpkg, level=2 would go up 1 directory - now blocked
        result = resolve_import("utils", "target_func", subpkg, level=2)
        assert not result.exists, "level=2 should be blocked by stricter path traversal security"

    def test_resolve_relative_import_level_3_blocked_by_security(self, tmp_path):
        """Test from ...module is blocked by path traversal security (P1-1 FIX).

        P1-1 security fix limits relative imports to one parent level above src_dir.
        level=3 from sub2 would traverse 2 levels up, which is now blocked.
        """
        # Create structure:
        # tmp_path/
        #   common.py (with shared_func)
        #   sub1/
        #     sub2/
        #       __init__.py (we're "in" here, src_dir=sub2)

        # Create common.py at root level
        (tmp_path / "common.py").write_text("def shared_func(): pass", encoding="utf-8")

        # Create nested structure
        sub1 = tmp_path / "sub1"
        sub1.mkdir()
        (sub1 / "__init__.py").write_text("", encoding="utf-8")
        sub2 = sub1 / "sub2"
        sub2.mkdir()
        (sub2 / "__init__.py").write_text("", encoding="utf-8")

        # from ...common import shared_func (level=3, module="common")
        # P1-1 FIX: This is now blocked because it would escape src_dir.parent (sub1)
        result = resolve_import("common", "shared_func", sub2, level=3)
        assert not result.exists, "level=3 should be blocked by path traversal security"

    def test_resolve_relative_import_level_2_not_found(self, tmp_path):
        """Test level=2 returns not found when module doesn't exist at parent (P1 FIX)."""
        # Create structure without target module
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        subpkg = pkg / "subpkg"
        subpkg.mkdir()
        (subpkg / "__init__.py").write_text("", encoding="utf-8")

        # from ..nonexistent import func (level=2, module="nonexistent")
        result = resolve_import("nonexistent", "func", subpkg, level=2)
        assert not result.exists

    def test_path_traversal_relative_import_escapes_src_dir(self, tmp_path):
        """Test that relative imports cannot escape src_dir (P1-1 FIX)."""
        # Create deeply nested structure
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")

        # Try from ....x import y (level=4 from pkg, would escape tmp_path)
        result = resolve_import("secret", "data", pkg, level=10)
        assert not result.exists

    def test_non_utf8_file_handling(self, tmp_path):
        """Test that non-UTF-8 files don't crash (P1-2 FIX)."""
        # Create a file with latin-1 encoding
        file_path = tmp_path / "latin1.py"
        file_path.write_bytes(b"# -*- coding: latin-1 -*-\nVAR = '\xe9'\n")

        # Should not crash, should return not found
        result = find_symbol_in_file("VAR", file_path)
        assert not result.exists

    def test_reexport_from_init(self, tmp_path):
        """Test that re-exports in __init__.py are detected (P2-2 FIX)."""
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        # Create __init__.py with re-export
        (pkg / "__init__.py").write_text(
            "from .internal import helper_func\nfrom .other import OtherClass as Alias",
            encoding="utf-8"
        )

        # Should find re-exported symbol
        result = find_symbol_in_file("helper_func", pkg / "__init__.py")
        assert result.exists

        # Should find aliased re-export
        result = find_symbol_in_file("Alias", pkg / "__init__.py")
        assert result.exists

    def test_import_reexport(self, tmp_path):
        """Test that import re-exports are detected (P2-2 FIX)."""
        file_path = tmp_path / "reexports.py"
        file_path.write_text("import os\nimport json as j", encoding="utf-8")

        result = find_symbol_in_file("os", file_path)
        assert result.exists

        result = find_symbol_in_file("j", file_path)
        assert result.exists

    def test_symlink_skipped(self, tmp_path):
        """Test that symlinks are skipped to avoid infinite loops (P3-1 FIX)."""
        # Create a directory with a real file
        (tmp_path / "real.py").write_text("def real_func(): pass", encoding="utf-8")

        # Create a symlink that points back to parent (would cause infinite loop)
        link_path = tmp_path / "subdir"
        try:
            link_path.symlink_to(tmp_path, target_is_directory=True)
        except OSError:
            pytest.skip("Cannot create symlinks on this system")

        # Should find real_func but not crash on symlink
        result = find_symbol_in_directory("real_func", tmp_path)
        assert result.exists

    def test_find_symbol_in_if_type_checking_block(self, tmp_path):
        """Test finding symbols inside if TYPE_CHECKING block (P2-1 FIX)."""
        file_path = tmp_path / "typed.py"
        file_path.write_text("""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    MyTypeAlias = dict[str, int]

    class TypeOnlyClass:
        pass

    def type_only_func():
        pass
""", encoding="utf-8")
        # Should find symbols inside if TYPE_CHECKING block
        result = find_symbol_in_file("Callable", file_path)
        assert result.exists, "Should find re-exported Callable in if TYPE_CHECKING"

        result = find_symbol_in_file("MyTypeAlias", file_path)
        assert result.exists, "Should find type alias in if TYPE_CHECKING"

        result = find_symbol_in_file("TypeOnlyClass", file_path)
        assert result.exists, "Should find class in if TYPE_CHECKING"

        result = find_symbol_in_file("type_only_func", file_path)
        assert result.exists, "Should find function in if TYPE_CHECKING"

    def test_find_symbol_in_try_block(self, tmp_path):
        """Test finding symbols inside try/except blocks (P2-1 FIX)."""
        file_path = tmp_path / "compat.py"
        file_path.write_text("""
try:
    from fast_lib import FastClass
    HAS_FAST = True
except ImportError:
    from slow_lib import SlowClass as FastClass
    HAS_FAST = False
""", encoding="utf-8")
        # Should find symbols in try block
        result = find_symbol_in_file("FastClass", file_path)
        assert result.exists, "Should find FastClass in try block"

        result = find_symbol_in_file("HAS_FAST", file_path)
        assert result.exists, "Should find HAS_FAST in try block"

    def test_find_symbol_in_with_block(self, tmp_path):
        """Test finding symbols inside with blocks (P2-1 FIX)."""
        file_path = tmp_path / "with_block.py"
        file_path.write_text("""
import contextlib

with contextlib.suppress(ImportError):
    from optional_dep import OptionalClass
    OPTIONAL_AVAILABLE = True
""", encoding="utf-8")
        # Should find symbols in with block
        result = find_symbol_in_file("OptionalClass", file_path)
        assert result.exists, "Should find OptionalClass in with block"

        result = find_symbol_in_file("OPTIONAL_AVAILABLE", file_path)
        assert result.exists, "Should find OPTIONAL_AVAILABLE in with block"

    def test_find_symbol_in_if_else_block(self, tmp_path):
        """Test finding symbols in if/else branches (P2-1 FIX)."""
        file_path = tmp_path / "conditional.py"
        file_path.write_text("""
import sys

if sys.version_info >= (3, 11):
    from tomllib import load as toml_load
else:
    from tomli import load as toml_load
""", encoding="utf-8")
        # Should find symbol in if branch
        result = find_symbol_in_file("toml_load", file_path)
        assert result.exists, "Should find toml_load in conditional block"
