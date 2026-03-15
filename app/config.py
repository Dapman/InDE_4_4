"""
InDE v3.1 - Configuration Compatibility Shim

This file re-exports all configuration from core.config for backward
compatibility with modules that import from 'config' directly.
"""

# Re-export everything from core.config
from core.config import *
