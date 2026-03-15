"""
InDE v3.9 - LLM Gateway Test Configuration

pytest configuration and fixtures for LLM gateway tests.
"""

import pytest
import sys
import os

# Add parent directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_anthropic_key():
    """Provide a mock Anthropic API key for testing."""
    return "sk-ant-test-key-for-testing"


@pytest.fixture
def mock_ollama_url():
    """Provide a mock Ollama URL for testing."""
    return "http://localhost:11434"


@pytest.fixture
def sample_chat_messages():
    """Provide sample chat messages for testing."""
    return [
        {"role": "user", "content": "Hello, I have an idea for an innovation."},
        {"role": "assistant", "content": "That's exciting! Tell me more about it."},
        {"role": "user", "content": "I want to create a smart garden system."}
    ]


@pytest.fixture
def sample_system_prompt():
    """Provide a sample ODICM system prompt for testing."""
    return """You are an innovation coach helping the user explore their idea.

Your style:
- Be warm, supportive, and genuinely curious
- Ask probing questions that help them think deeper
- Never use jargon like "scaffolding" or "artifact"

Current context:
- Stage: Vision Exploration
- Archetype: Lean Startup
"""
