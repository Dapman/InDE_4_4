"""Code consolidation script - removes duplicate root directories."""
import shutil
import os
from pathlib import Path

base = Path('.')

# Directories to remove (duplicates of app/ subdirectories)
dirs_to_remove = [
    'scaffolding', 'portfolio', 'notifications', 'insights',
    'reporting', 'distribution', 'sharing', 'collaboration',
    'tim', 'rve', 'intelligence', 'analytics', 'ikf', 'ui',
    'reports', 'models', 'middleware', 'core'
]

# Files to remove (duplicates)
files_to_remove = ['database.py', 'config.py']

print('=== CODE CONSOLIDATION ===')
print()

# Remove duplicate directories
for d in dirs_to_remove:
    path = base / d
    if path.exists() and path.is_dir():
        shutil.rmtree(path)
        print(f'Removed directory: {d}/')

# Remove duplicate files
for f in files_to_remove:
    path = base / f
    if path.exists():
        path.unlink()
        print(f'Removed file: {f}')

print()
print('Consolidation complete!')

# Rerun inventory to verify
from pathlib import Path
from collections import defaultdict

counts = defaultdict(int)
for pyfile in base.rglob('*.py'):
    if 'venv' in str(pyfile) or '__pycache__' in str(pyfile):
        continue
    counts['total'] += 1
    parts = pyfile.parts
    if len(parts) > 1:
        counts[parts[0]] += 1
    else:
        counts['root'] += 1

print()
print('=== POST-CONSOLIDATION COUNTS ===')
print(f'Total Python files: {counts["total"]}')
print(f'  app/: {counts.get("app", 0)}')
print(f'  ikf-service/: {counts.get("ikf-service", 0)}')
print(f'  tests/: {counts.get("tests", 0)}')
print(f'  tools/: {counts.get("tools", 0)}')
print(f'  root level: {counts.get("root", 0)}')
