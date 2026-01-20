"""CLI for doc-drift-guard."""

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from doc_drift_guard.analyzer.imports import extract_symbols
from doc_drift_guard.analyzer.resolver import resolve_import
from doc_drift_guard.parser.markdown import extract_python_blocks
from doc_drift_guard.parser.python import parse_imports

console = Console()


@click.group()
def cli():
    """Doc Drift Guard - Detect outdated code examples in documentation."""
    pass


@cli.command()
@click.argument("doc_file", type=click.Path(exists=True, path_type=Path))
@click.option("--src", type=click.Path(exists=True, path_type=Path), default=".",
              help="Source directory to search for symbols")
@click.option("--json", "json_output", is_flag=True, help="Output results as JSON")
@click.option("--package", "-p", "packages", multiple=True,
              help="Package prefixes to check (ignores stdlib/third-party)")
def check(doc_file: Path, src: Path, json_output: bool, packages: tuple[str, ...]):
    """Check a documentation file for drift.

    Scans code blocks in DOC_FILE and verifies that imported symbols exist in the codebase.

    Exit codes:
        0 - No drift detected
        1 - Drift detected
        2 - Error occurred
    """
    try:
        # Read the documentation file
        content = doc_file.read_text(encoding="utf-8")

        # Extract Python code blocks
        code_blocks = extract_python_blocks(content)

        if not code_blocks:
            if not json_output:
                console.print(f"[yellow]No Python code blocks found in {doc_file}[/yellow]")
            sys.exit(0)

        # Collect all drifts
        all_drifts = []

        # Check each code block
        for block in code_blocks:
            try:
                imports = parse_imports(block.code)
                symbols = extract_symbols(imports)

                # Filter by package prefixes if specified
                if packages:
                    symbols = [
                        s for s in symbols
                        # P2-2 FIX: Always include relative imports (level > 0)
                        # Also keep empty module and matching packages
                        if s.level > 0 or s.module == "" or any(
                            s.module == p or s.module.startswith(f"{p}.") for p in packages
                        )
                    ]

                # Resolve each symbol
                for sym in symbols:
                    resolution = resolve_import(sym.module, sym.symbol, src, sym.level)
                    if not resolution.exists:
                        all_drifts.append({
                            "symbol": sym.symbol,
                            "module": sym.module,
                            "line": block.line_start,
                            "doc_file": str(doc_file)
                        })

            except SyntaxError:
                # Skip code blocks with syntax errors
                continue

        # Output results
        if json_output:
            output = {
                "drift_detected": len(all_drifts) > 0,
                "drifts": all_drifts
            }
            print(json.dumps(output))
        else:
            if all_drifts:
                table = Table(title="Drift Detected")
                table.add_column("Symbol", style="red")
                table.add_column("Module", style="yellow")
                table.add_column("Line", style="cyan")

                for drift in all_drifts:
                    table.add_row(drift["symbol"], drift["module"], str(drift["line"]))

                console.print(table)
                count = len(all_drifts)
                console.print(
                    f"\n[red]Found {count} symbol(s) that don't exist in the codebase[/red]"
                )
            else:
                console.print(f"[green]✓ No drift detected in {doc_file}[/green]")

        # Exit with appropriate code
        sys.exit(1 if all_drifts else 0)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(2)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
