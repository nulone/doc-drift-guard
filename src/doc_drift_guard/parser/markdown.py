"""Extract code blocks from markdown files."""

import re
from dataclasses import dataclass


@dataclass
class CodeBlock:
    """Represents a fenced code block in markdown."""

    language: str
    code: str
    line_start: int
    line_end: int


def extract_code_blocks(content: str) -> list[CodeBlock]:
    """Extract all fenced code blocks from markdown content.

    Args:
        content: Markdown file content

    Returns:
        List of CodeBlock objects
    """
    blocks = []
    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        # Match opening fence: ```language or ~~~language
        match = re.match(r'^(```|~~~)(\w+)?', line)
        if match:
            fence_type = match.group(1)  # ``` or ~~~
            language = match.group(2) or ""
            line_start = i + 1  # Content starts on next line
            code_lines = []
            i += 1

            # Collect lines until closing fence (must match opening fence type)
            while i < len(lines):
                if re.match(rf'^{re.escape(fence_type)}\s*$', lines[i]):
                    line_end = i
                    blocks.append(CodeBlock(
                        language=language,
                        code='\n'.join(code_lines),
                        line_start=line_start,
                        line_end=line_end
                    ))
                    break
                code_lines.append(lines[i])
                i += 1

        i += 1

    return blocks


def extract_python_blocks(content: str) -> list[CodeBlock]:
    """Extract only Python code blocks from markdown content.

    Args:
        content: Markdown file content

    Returns:
        List of CodeBlock objects with language='python', 'py', 'Python', etc.
    """
    all_blocks = extract_code_blocks(content)
    # Case-insensitive match, accept both 'python' and 'py'
    return [block for block in all_blocks if block.language.lower() in ('python', 'py')]
