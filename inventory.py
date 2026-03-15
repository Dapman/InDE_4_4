"""Codebase inventory script for v3.5.0 build."""
import os
from pathlib import Path
from collections import defaultdict

base = Path('.')
counts = defaultdict(int)
file_lines = []

for pyfile in base.rglob('*.py'):
    if 'venv' in str(pyfile) or '__pycache__' in str(pyfile):
        continue
    counts['total'] += 1

    # Count by top-level dir
    parts = pyfile.parts
    if len(parts) > 1:
        counts[parts[0]] += 1
    else:
        counts['root'] += 1

    # Count lines
    try:
        lines = len(open(pyfile, encoding='utf-8', errors='ignore').readlines())
        file_lines.append((lines, str(pyfile)))
    except:
        pass

# Count test files
test_count = sum(1 for p in base.rglob('test_*.py') if 'venv' not in str(p))

# Count total lines
total_lines = sum(l for l, _ in file_lines)

print('=' * 50)
print('INDE v3.5.0 CODEBASE INVENTORY')
print('=' * 50)
print()
print('PYTHON FILE COUNTS:')
print(f'  Total Python files: {counts["total"]}')
print(f'  - app/: {counts.get("app", 0)}')
print(f'  - ikf-service/: {counts.get("ikf-service", 0)}')
print(f'  - tests/: {counts.get("tests", 0)}')
print(f'  - root level: {counts.get("root", 0)}')
print(f'  - other dirs: {counts["total"] - counts.get("app", 0) - counts.get("ikf-service", 0) - counts.get("tests", 0) - counts.get("root", 0)}')
print()
print(f'TEST FILES: {test_count}')
print(f'TOTAL LINES OF CODE: {total_lines:,}')
print()
print('TOP 15 LARGEST FILES:')
for lines, path in sorted(file_lines, reverse=True)[:15]:
    print(f'  {lines:5d} lines: {path}')
print()

# Find duplicates between root and app
root_files = set()
app_files = set()
for f in base.glob('*.py'):
    root_files.add(f.name)
for f in (base / 'app').rglob('*.py'):
    app_files.add(f.name)

duplicates = root_files & app_files
if duplicates:
    print('DUPLICATE FILES (root vs app/):')
    for d in sorted(duplicates):
        print(f'  {d}')
else:
    print('NO DUPLICATES between root and app/')
