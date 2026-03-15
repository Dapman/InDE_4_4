"""
InDE MVP v3.4 - Test Configuration
Sets up Python path for module imports.
"""

import sys
import os

# Add the app directory to the Python path FIRST
_app_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

import pytest

def pytest_configure(config):
    """Early hook to ensure path is set before collection."""
    app_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
