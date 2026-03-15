"""
InDE MVP v2.5 - Conversational Scaffolding Package

Components:
- IntentDetector: Detects innovation intent, auto-creates pursuits
- ElementTracker: Tracks 40 scaffolding elements (20 critical + 20 important)
- MomentDetector: Detects 8 intervention opportunities
- ArtifactGenerator: Generates artifacts when ready
- ScaffoldingEngine: Main orchestrator
- PatternEngine: v2.5 - IML pattern matching and cross-pursuit insights
- AdaptiveInterventionManager: v2.5 - Engagement-based cooldown adjustment
- ArtifactLifecycleManager: Artifact versioning and drift detection
- TeleologicalAssessor: Goal-oriented methodology inference
"""

from .intent_detector import IntentDetector
from .element_tracker import ElementTracker
from .moment_detector import MomentDetector
from .artifact_generator import ArtifactGenerator
from .engine import ScaffoldingEngine
from .pattern_engine import PatternEngine
from .adaptive_manager import AdaptiveInterventionManager
from .lifecycle_manager import ArtifactLifecycleManager
from .teleological_assessor import TeleologicalAssessor

__all__ = [
    'IntentDetector',
    'ElementTracker',
    'MomentDetector',
    'ArtifactGenerator',
    'ScaffoldingEngine',
    'PatternEngine',
    'AdaptiveInterventionManager',
    'ArtifactLifecycleManager',
    'TeleologicalAssessor'
]
