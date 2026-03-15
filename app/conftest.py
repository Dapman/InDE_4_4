"""
InDE v3.2 - Pytest Configuration
Sets up the Python path for imports.
"""

import sys
import os
import pytest

# Add app directory to Python path BEFORE any other imports
app_dir = os.path.dirname(os.path.abspath(__file__))


def pytest_configure(config):
    """Configure pytest before any tests run."""
    # Ensure app_dir is at the front of sys.path
    if app_dir in sys.path:
        sys.path.remove(app_dir)
    sys.path.insert(0, app_dir)

    # Also change working directory to app_dir for relative imports
    os.chdir(app_dir)


# Run path setup immediately when conftest is loaded
if app_dir in sys.path:
    sys.path.remove(app_dir)
sys.path.insert(0, app_dir)
os.chdir(app_dir)
