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
