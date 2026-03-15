#!/usr/bin/env python3
"""
InDE Build Harness — Interface Extraction Tool

Reads BUILD_MANIFEST.json and produces BUILD_CONTEXT.md:
- STABLE modules: class names, method signatures, docstrings (no bodies)
- EXTEND modules: full interface + marked extension points
- REWRITE modules: full file contents
- Estimates token count of generated context

Usage: python tools/extract_interfaces.py [--manifest tools/BUILD_MANIFEST.json] [--output BUILD_CONTEXT.md]
"""

import argparse
import ast
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional


def load_manifest(manifest_path: str) -> Dict:
    """Load and validate BUILD_MANIFEST.json."""
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    required_keys = ['manifest_version', 'inde_version', 'modules']
    for key in required_keys:
        if key not in manifest:
            raise ValueError(f"Missing required key in manifest: {key}")

    return manifest


def extract_signatures(file_path: str) -> str:
    """
    Extract class definitions, method signatures, and module-level constants.
    Skip method bodies, keeping only signatures and docstrings.
    """
    if not os.path.exists(file_path):
        return f"# File not found: {file_path}\n"

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        tree = ast.parse(content)
    except SyntaxError as e:
        return f"# Syntax error in {file_path}: {e}\n"
    except Exception as e:
        return f"# Error parsing {file_path}: {e}\n"

    lines = []

    # Extract module docstring
    if ast.get_docstring(tree):
        lines.append(f'"""{ast.get_docstring(tree)}"""')
        lines.append('')

    # Extract imports (first 20 lines of imports)
    import_count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if import_count < 20:
                lines.append(ast.unparse(node))
                import_count += 1

    if import_count > 0:
        lines.append('')

    # Extract module-level constants/assignments
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    # Module-level constant
                    try:
                        lines.append(f"{target.id} = ...")
                    except:
                        pass

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                try:
                    lines.append(ast.unparse(node))
                except:
                    pass

    # Extract class definitions
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            lines.append('')
            lines.extend(extract_class_signature(node))

    # Extract top-level functions
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            lines.append('')
            lines.extend(extract_function_signature(node))

    return '\n'.join(lines)


def extract_class_signature(node: ast.ClassDef) -> List[str]:
    """Extract class definition with method signatures."""
    lines = []

    # Class definition
    bases = ', '.join(ast.unparse(b) for b in node.bases)
    if bases:
        lines.append(f"class {node.name}({bases}):")
    else:
        lines.append(f"class {node.name}:")

    # Class docstring
    docstring = ast.get_docstring(node)
    if docstring:
        # Truncate long docstrings
        if len(docstring) > 300:
            docstring = docstring[:300] + "..."
        lines.append(f'    """{docstring}"""')

    # Extract methods
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sig_lines = extract_function_signature(item, indent=4)
            lines.extend(sig_lines)

    return lines


def extract_function_signature(node, indent: int = 0) -> List[str]:
    """Extract function/method signature with docstring."""
    lines = []
    prefix = ' ' * indent

    # Build function signature
    async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""

    # Get arguments
    args = []
    for arg in node.args.args:
        arg_str = arg.arg
        if arg.annotation:
            try:
                arg_str += f": {ast.unparse(arg.annotation)}"
            except:
                pass
        args.append(arg_str)

    # Handle *args, **kwargs
    if node.args.vararg:
        args.append(f"*{node.args.vararg.arg}")
    if node.args.kwarg:
        args.append(f"**{node.args.kwarg.arg}")

    args_str = ', '.join(args)

    # Return annotation
    returns = ""
    if node.returns:
        try:
            returns = f" -> {ast.unparse(node.returns)}"
        except:
            pass

    lines.append(f"{prefix}{async_prefix}def {node.name}({args_str}){returns}:")

    # Docstring
    docstring = ast.get_docstring(node)
    if docstring:
        # Truncate long docstrings
        if len(docstring) > 200:
            docstring = docstring[:200] + "..."
        lines.append(f'{prefix}    """{docstring}"""')

    lines.append(f"{prefix}    ...")

    return lines


def read_full_file(file_path: str) -> str:
    """Read full file contents."""
    if not os.path.exists(file_path):
        return f"# File not found: {file_path}\n"

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"# Error reading {file_path}: {e}\n"


def estimate_tokens(text: str) -> int:
    """Estimate token count (approximate: chars / 4)."""
    return len(text) // 4


def generate_build_context(manifest: Dict, base_path: str) -> str:
    """Generate BUILD_CONTEXT.md from manifest."""

    lines = []
    lines.append("# InDE v3.5.x Build Context")
    lines.append(f"## Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"## Manifest Version: {manifest['manifest_version']}")
    lines.append(f"## InDE Version: {manifest['inde_version']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # STABLE modules - signatures only
    lines.append("## STABLE Module Interfaces (read-only reference)")
    lines.append("")
    lines.append("These modules are NOT modified in v3.5.x builds. Only signatures shown.")
    lines.append("")

    stable_modules = manifest['modules'].get('STABLE', [])
    for module in stable_modules:
        if module.endswith('.py'):
            file_path = os.path.join(base_path, module)
            lines.append(f"### {module}")
            lines.append("```python")
            lines.append(extract_signatures(file_path))
            lines.append("```")
            lines.append("")

    lines.append("---")
    lines.append("")

    # EXTEND modules - full content
    lines.append("## EXTEND Modules (modification targets)")
    lines.append("")
    lines.append("These modules ARE modified in v3.5.x builds. Full content included.")
    lines.append("")

    extend_modules = manifest['modules'].get('EXTEND', [])
    for module in extend_modules:
        if module.endswith('.py') or module.endswith('.yml'):
            file_path = os.path.join(base_path, module)
            lines.append(f"### {module}")
            lines.append("```python" if module.endswith('.py') else "```yaml")
            lines.append(read_full_file(file_path))
            lines.append("```")
            lines.append("")

    lines.append("---")
    lines.append("")

    # REWRITE modules - full content (new files)
    lines.append("## REWRITE Modules (new code)")
    lines.append("")

    rewrite_modules = manifest['modules'].get('REWRITE', [])
    if rewrite_modules:
        for module in rewrite_modules:
            file_path = os.path.join(base_path, module)
            lines.append(f"### {module}")
            lines.append("```python")
            lines.append(read_full_file(file_path))
            lines.append("```")
            lines.append("")
    else:
        lines.append("*No REWRITE modules in v3.5.0*")
        lines.append("")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Extract interfaces from InDE codebase')
    parser.add_argument('--manifest', default='tools/BUILD_MANIFEST.json',
                        help='Path to BUILD_MANIFEST.json')
    parser.add_argument('--output', default='BUILD_CONTEXT.md',
                        help='Output file path')
    parser.add_argument('--base-path', default='.',
                        help='Base path for resolving module paths')

    args = parser.parse_args()

    print("=" * 50)
    print("InDE Build Harness - Interface Extraction")
    print("=" * 50)
    print()

    # Load manifest
    print(f"Loading manifest: {args.manifest}")
    manifest = load_manifest(args.manifest)
    print(f"  Manifest version: {manifest['manifest_version']}")
    print(f"  InDE version: {manifest['inde_version']}")
    print()

    # Count modules
    stable_count = len([m for m in manifest['modules'].get('STABLE', []) if m.endswith('.py')])
    extend_count = len([m for m in manifest['modules'].get('EXTEND', []) if m.endswith('.py') or m.endswith('.yml')])
    rewrite_count = len(manifest['modules'].get('REWRITE', []))

    print(f"Modules to process:")
    print(f"  STABLE (signatures only): {stable_count}")
    print(f"  EXTEND (full content): {extend_count}")
    print(f"  REWRITE (full content): {rewrite_count}")
    print()

    # Generate context
    print("Generating build context...")
    context = generate_build_context(manifest, args.base_path)

    # Write output
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(context)

    # Calculate metrics
    context_chars = len(context)
    context_tokens = estimate_tokens(context)

    # Calculate full codebase size
    full_size = 0
    for category in ['STABLE', 'EXTEND', 'REWRITE']:
        for module in manifest['modules'].get(category, []):
            if module.endswith('.py'):
                file_path = os.path.join(args.base_path, module)
                if os.path.exists(file_path):
                    try:
                        full_size += os.path.getsize(file_path)
                    except:
                        pass

    full_tokens = full_size // 4

    print()
    print("=" * 50)
    print("Extraction Complete")
    print("=" * 50)
    print(f"Output: {args.output}")
    print(f"Context size: {context_chars:,} characters (~{context_tokens:,} tokens)")
    print(f"Full codebase: {full_size:,} characters (~{full_tokens:,} tokens)")
    print(f"Reduction: {100 - (context_chars / full_size * 100):.1f}%" if full_size > 0 else "N/A")
    print()

    # Verify target
    if full_size > 0 and context_chars < full_size * 0.5:
        print("[OK] Context is <50% of full codebase - TARGET MET")
    else:
        print("[WARN] Context is >=50% of full codebase - review STABLE classification")


if __name__ == '__main__':
    main()
