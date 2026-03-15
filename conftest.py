"""
InDE MVP v3.4 - Root Test Configuration
Sets up Python path for module imports.
"""

import sys
import os

# Add the app directory to the Python path
app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)
