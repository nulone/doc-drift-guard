"""Tests for parser modules."""

import pytest

from doc_drift_guard.parser.markdown import extract_code_blocks, extract_python_blocks
from doc_drift_guard.parser.python import (
    get_referenced_symbols,
    parse_function_calls,
    parse_imports,
)


class TestMarkdownParser:
    """Tests for markdown parser."""

    def test_extract_single_code_block(self):
        """Test extracting a single code block."""
        content = """# Title

```python
print("hello")
```
"""
        blocks = extract_code_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].language == "python"
        assert blocks[0].code == 'print("hello")'

    def test_extract_multiple_code_blocks(self):
        """Test extracting multiple code blocks."""
        content = """# Title

```python
x = 1
```

Some text.

```javascript
console.log("hi");
```
"""
        blocks = extract_code_blocks(content)
        assert len(blocks) == 2
        assert blocks[0].language == "python"
        assert blocks[1].language == "javascript"

    def test_extract_python_blocks_only(self):
        """Test filtering for Python blocks only."""
        content = """# Title

```python
x = 1
```

```javascript
console.log("hi");
```

```python
y = 2
```
"""
        blocks = extract_python_blocks(content)
        assert len(blocks) == 2
        assert all(b.language == "python" for b in blocks)

    def test_code_block_with_no_language(self):
        """Test code block without language specification."""
        content = """# Title

```
generic code
```
"""
        blocks = extract_code_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].language == ""

    def test_multiline_code_block(self):
        """Test multiline code block."""
        content = """# Title

```python
def hello():
    print("world")
    return 42
```
"""
        blocks = extract_code_blocks(content)
        assert len(blocks) == 1
        assert "def hello():" in blocks[0].code
        assert 'print("world")' in blocks[0].code

    def test_tilde_fence(self):
        """Test tilde fence variant (BUG-5)."""
        content = """# Title

~~~python
print("hello")
~~~
"""
        blocks = extract_code_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].language == "python"
        assert blocks[0].code == 'print("hello")'

    def test_case_insensitive_python(self):
        """Test case-insensitive Python language (BUG-5)."""
        content1 = "```Python\nx = 1\n```"
        content2 = "```py\nx = 1\n```"
        content3 = "```PYTHON\nx = 1\n```"

        blocks1 = extract_python_blocks(content1)
        blocks2 = extract_python_blocks(content2)
        blocks3 = extract_python_blocks(content3)

        assert len(blocks1) == 1
        assert len(blocks2) == 1
        assert len(blocks3) == 1

    def test_indented_code_block_in_list(self):
        """Test indented code block inside a list (P2-1 FIX)."""
        content = """# Title

- Item 1
  ```python
  x = 1
  ```
- Item 2
"""
        blocks = extract_code_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].language == "python"
        assert "x = 1" in blocks[0].code

    def test_deeply_indented_code_block(self):
        """Test deeply indented code block (P2-1 FIX)."""
        content = """# Title

        ```python
        x = 1
        ```
"""
        blocks = extract_code_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].language == "python"
        assert "x = 1" in blocks[0].code

    def test_indented_code_block_mixed(self):
        """Test mixed indented and non-indented blocks (P2-1 FIX)."""
        content = """# Title

```python
top_level = True
```

1. Step one
   ```python
   indented = True
   ```
"""
        blocks = extract_code_blocks(content)
        assert len(blocks) == 2
        assert "top_level" in blocks[0].code
        assert "indented" in blocks[1].code


class TestPythonParser:
    """Tests for Python parser."""

    def test_parse_simple_import(self):
        """Test parsing simple import statement."""
        code = "import os"
        imports = parse_imports(code)
        assert len(imports) == 1
        assert imports[0].module == "os"

    def test_parse_from_import(self):
        """Test parsing from...import statement."""
        code = "from pathlib import Path"
        imports = parse_imports(code)
        assert len(imports) == 1
        assert imports[0].module == "pathlib"
        assert "Path" in imports[0].names

    def test_parse_multiple_imports(self):
        """Test parsing multiple imports from same module."""
        code = "from example import hello_world, another_function"
        imports = parse_imports(code)
        assert len(imports) == 1
        assert imports[0].module == "example"
        assert "hello_world" in imports[0].names
        assert "another_function" in imports[0].names

    def test_parse_import_with_alias(self):
        """Test parsing import with alias."""
        code = "from example import hello_world as hw"
        imports = parse_imports(code)
        assert len(imports) == 1
        assert "hw" in imports[0].aliases
        assert imports[0].aliases["hw"] == "hello_world"

    def test_parse_function_calls(self):
        """Test parsing function calls."""
        code = """
hello_world()
another_function()
print("test")
"""
        calls = parse_function_calls(code)
        assert len(calls) == 3
        names = [c.name for c in calls]
        assert "hello_world" in names
        assert "another_function" in names
        assert "print" in names

    def test_get_referenced_symbols(self):
        """Test getting all referenced symbols."""
        code = """
from example import hello_world, another_function

hello_world()
result = another_function()
"""
        symbols = get_referenced_symbols(code)
        assert "hello_world" in symbols
        assert "another_function" in symbols

    def test_syntax_error(self):
        """Test handling of syntax errors."""
        code = "def invalid syntax("
        with pytest.raises(SyntaxError):
            parse_imports(code)

    def test_plain_import_no_symbols(self):
        """Test plain import doesn't create symbols to check (BUG-2)."""
        code = "import os"
        imports = parse_imports(code)
        assert len(imports) == 1
        assert imports[0].module == "os"
        # Plain imports should have empty names list
        assert imports[0].names == []

    def test_relative_import(self):
        """Test relative imports are parsed (BUG-4)."""
        # Bare relative import
        code1 = "from . import helper"
        imports1 = parse_imports(code1)
        assert len(imports1) == 1
        assert "helper" in imports1[0].names

        # Relative import with module
        code2 = "from .submodule import func"
        imports2 = parse_imports(code2)
        assert len(imports2) == 1
        assert "func" in imports2[0].names

        # Parent relative import
        code3 = "from .. import parent_func"
        imports3 = parse_imports(code3)
        assert len(imports3) == 1
        assert "parent_func" in imports3[0].names

    def test_relative_import_level_preserved(self):
        """Test relative import level is preserved (P1-3 FIX)."""
        # Level 0 (absolute)
        code0 = "from pathlib import Path"
        imports0 = parse_imports(code0)
        assert imports0[0].level == 0

        # Level 1 (from . import)
        code1 = "from . import helper"
        imports1 = parse_imports(code1)
        assert imports1[0].level == 1
        assert imports1[0].module == ""

        # Level 1 with module (from .submodule import)
        code1m = "from .submodule import func"
        imports1m = parse_imports(code1m)
        assert imports1m[0].level == 1
        assert imports1m[0].module == "submodule"

        # Level 2 (from .. import)
        code2 = "from .. import parent_func"
        imports2 = parse_imports(code2)
        assert imports2[0].level == 2

        # Level 3 (from ... import)
        code3 = "from ...grandparent import func"
        imports3 = parse_imports(code3)
        assert imports3[0].level == 3
        assert imports3[0].module == "grandparent"
