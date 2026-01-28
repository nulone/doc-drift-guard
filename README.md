# Doc Drift Guard 🛡️

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/nulone/doc-drift-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/nulone/doc-drift-guard/actions/workflows/ci.yml)

**Detect outdated code examples in documentation before they mislead your users.**

## The Problem

Documentation with broken code examples erodes trust. You refactor a function, rename a module, or update an API—and suddenly every tutorial, README, and guide shows outdated code that doesn't work anymore.

Manual verification doesn't scale. Copy-pasting examples into a REPL is tedious and error-prone. By the time users report issues, the damage is done.

## The Solution

Doc Drift Guard statically analyzes Markdown documentation to verify that Python code examples reference symbols that actually exist in your codebase.

- **AST-based parsing**: No brittle regex patterns
- **Real symbol resolution**: Validates imports against actual source code
- **Fast**: No code execution required
- **CI-friendly**: Exit codes and JSON output for automation

## Installation

```bash
pip install doc-drift-guard
```

## Quick Start

```bash
# Check single file
ddg check README.md --src ./src

# Check multiple files
ddg check docs/*.md --src ./src

# JSON output for CI integration
ddg check README.md --src ./src --json

# Check specific package imports
ddg check docs/*.md --src ./src --package mypackage
```

## CI Integration

### GitHub Actions

Add to `.github/workflows/docs.yml`:

```yaml
name: Documentation Check
on: [push, pull_request]

jobs:
  check-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - uses: ./.github/action.yml
        with:
          docs: 'README.md docs/**/*.md'
          src: './src'
          package: 'mypackage'
```

Or use it as a standalone action:

```yaml
- name: Check documentation drift
  run: |
    pip install doc-drift-guard
    ddg check README.md --src ./src
```

### Pre-commit Hook

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/yourusername/doc-drift-guard
    rev: v0.1.0
    hooks:
      - id: doc-drift-guard
        args: ['--src', './src', '--package', 'mypackage']
```

Then install:

```bash
pre-commit install
```

### GitLab CI

Add to `.gitlab-ci.yml`:

```yaml
docs:check:
  image: python:3.10
  script:
    - pip install doc-drift-guard
    - ddg check README.md docs/**/*.md --src ./src --json
  only:
    - merge_requests
    - main
```

## Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | Success | No drift detected, all symbols valid |
| `1` | Drift | Outdated code examples found |
| `2` | Error | Invalid arguments or runtime error |

## How It Works

1. **Extract code blocks**: Parses Markdown fenced code blocks tagged as Python
2. **Parse imports**: Uses Python AST to extract `import` and `from ... import` statements
3. **Resolve symbols**: Validates that imported symbols exist in the source directory
4. **Report drift**: Highlights missing symbols with file/line references

## Development

```bash
git clone https://github.com/yourusername/doc-drift-guard
cd doc-drift-guard
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT

---

**Built to keep documentation in sync with reality.**
