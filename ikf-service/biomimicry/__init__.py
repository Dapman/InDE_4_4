"""
Biomimicry Module - Nature-Inspired Innovation Intelligence

This module provides LLM-assisted detection of biological parallels to
innovation challenges and integrates nature-inspired insights into
conversational coaching.

Components:
- BiomimicryAnalyzer: LLM-assisted function extraction and pattern matching
- BiomimicryDetector: Determines when to invoke biomimicry analysis
- BiomimicryFeedback: Tracks innovator responses and pattern effectiveness

Three-Tier Intelligence Model:
- Tier 1: Curated database (40+ patterns) - structured detection
- Tier 2: LLM deep knowledge - unbounded biological reasoning
- Tier 3: IKF federation - patterns from other organizations
"""

from .challenge_analyzer import BiomimicryAnalyzer
from .detection import BiomimicryDetector
from .feedback import BiomimicryFeedback

__all__ = [
    "BiomimicryAnalyzer",
    "BiomimicryDetector",
    "BiomimicryFeedback"
]
