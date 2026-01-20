"""End-to-end tests for doc-drift-guard."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from doc_drift_guard.cli import cli


class TestE2E:
    """End-to-end integration tests."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path."""
        return Path(__file__).parent / "fixtures"

    def test_valid_readme_no_drift(self, runner, fixtures_dir):
        """Test valid README with no drift."""
        readme = fixtures_dir / "valid_readme.md"
        src_dir = fixtures_dir / "sample_src"

        result = runner.invoke(cli, ["check", str(readme), "--src", str(src_dir)])

        assert result.exit_code == 0
        assert "No drift detected" in result.output

    def test_drift_readme_detects_drift(self, runner, fixtures_dir):
        """Test README with drift is detected."""
        readme = fixtures_dir / "drift_readme.md"
        src_dir = fixtures_dir / "sample_src"

        result = runner.invoke(cli, ["check", str(readme), "--src", str(src_dir)])

        assert result.exit_code == 1
        assert "non_existent_function" in result.output

    def test_json_output_valid(self, runner, fixtures_dir):
        """Test JSON output for valid file."""
        readme = fixtures_dir / "valid_readme.md"
        src_dir = fixtures_dir / "sample_src"

        result = runner.invoke(cli, ["check", str(readme), "--src", str(src_dir), "--json"])

        assert result.exit_code == 0
        assert '"drift_detected": false' in result.output

    def test_json_output_drift(self, runner, fixtures_dir):
        """Test JSON output for file with drift."""
        readme = fixtures_dir / "drift_readme.md"
        src_dir = fixtures_dir / "sample_src"

        result = runner.invoke(cli, ["check", str(readme), "--src", str(src_dir), "--json"])

        assert result.exit_code == 1
        assert '"drift_detected": true' in result.output
        assert '"symbol": "non_existent_function"' in result.output

    def test_no_code_blocks(self, runner, tmp_path):
        """Test file with no code blocks."""
        readme = tmp_path / "empty.md"
        readme.write_text("# Title\n\nJust text, no code.", encoding="utf-8")

        result = runner.invoke(cli, ["check", str(readme)])

        assert result.exit_code == 0
        assert "No Python code blocks" in result.output

    def test_nonexistent_file(self, runner):
        """Test error handling for nonexistent file."""
        result = runner.invoke(cli, ["check", "nonexistent.md"])

        assert result.exit_code != 0

    def test_package_filter_ignores_stdlib(self, runner, fixtures_dir):
        """Test that --package flag filters to only check specified packages."""
        readme = fixtures_dir / "mixed_imports.md"
        src_dir = fixtures_dir / "sample_src"

        # With --package example, should only check example imports
        # os, sys, json are stdlib and should be ignored
        result = runner.invoke(
            cli, ["check", str(readme), "--src", str(src_dir), "--package", "example"]
        )

        assert result.exit_code == 0
        assert "No drift detected" in result.output

    def test_package_filter_detects_drift_in_specified_package(self, runner, fixtures_dir):
        """Test that drift in specified package is detected while stdlib is ignored."""
        readme = fixtures_dir / "mixed_imports_drift.md"
        src_dir = fixtures_dir / "sample_src"

        # With --package example, should detect non_existent_function
        # but ignore nonexistent_json_func (from json)
        result = runner.invoke(
            cli, ["check", str(readme), "--src", str(src_dir), "--package", "example"]
        )

        assert result.exit_code == 1
        assert "non_existent_function" in result.output
        # Should NOT report json imports
        assert "nonexistent_json_func" not in result.output

    def test_multiple_package_filters(self, runner, fixtures_dir, tmp_path):
        """Test that multiple --package flags work correctly."""
        # Create a test file with imports from multiple packages
        readme = tmp_path / "multi_package.md"
        readme.write_text(
            """# Test
```python
from example import hello_world
from mylib import some_func
from stdlib import whatever
```
""",
            encoding="utf-8",
        )

        src_dir = fixtures_dir / "sample_src"

        # With --package example --package mylib, should check both but not stdlib
        # example.hello_world exists, mylib.some_func doesn't exist
        result = runner.invoke(
            cli,
            [
                "check",
                str(readme),
                "--src",
                str(src_dir),
                "--package",
                "example",
                "--package",
                "mylib",
            ],
        )

        assert result.exit_code == 1
        assert "some_func" in result.output
        # Should NOT report stdlib imports
        assert "whatever" not in result.output

    def test_package_filter_keeps_relative_imports(self, runner, fixtures_dir, tmp_path):
        """Test that relative imports are kept when using --package (BUG FIX)."""
        # Create a test file with relative imports
        readme = tmp_path / "relative_imports.md"
        readme.write_text(
            """# Test
```python
from .utils import process, helper_func
```
""",
            encoding="utf-8",
        )

        # Create corresponding source files
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "__init__.py").write_text("", encoding="utf-8")
        utils_dir = src_dir / "utils"
        utils_dir.mkdir()
        (utils_dir / "__init__.py").write_text(
            "def process(): pass\ndef helper_func(): pass", encoding="utf-8"
        )

        # With --package flag, relative imports should still be checked
        result = runner.invoke(
            cli, ["check", str(readme), "--src", str(src_dir), "--package", "mylib"]
        )

        # Should find the symbols (exit 0 if they exist)
        assert result.exit_code == 0
