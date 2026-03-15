"""
InDE MVP v3.1 - Core Package
Platform Foundation & Innovator Maturity

Core services:
- config: Application configuration
- database: Database operations with MongoDB
- LLMInterface: LLM calls with maturity and crisis integration
"""

from core.llm_interface import LLMInterface
from core.database import Database

__all__ = ['LLMInterface', 'Database']
