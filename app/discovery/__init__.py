"""
InDE MVP v3.4 - Discovery Module
Innovator Discovery & Team Formation Service (IDTFS).
"""

from .idtfs import (
    # Profile Management (Pillar 2, 4)
    InnovatorProfileManager,
    InnovatorProfile,
    AvailabilityStatus,

    # Vouching Service (Pillar 3)
    VouchingService,
    VouchingRecord,
    VouchingType,

    # Behavioral Expertise (Pillar 1)
    BehavioralExpertiseCalculator,
    ExpertiseScore,

    # Expertise Type Matching (Pillar 6)
    ExpertiseTypeMatcher,
    ExpertiseType,

    # Discovery Query
    DiscoveryQuery,
    DiscoveryCandidate,

    # Singleton accessors
    get_profile_manager,
    get_vouching_service,
    get_expertise_calculator,
    get_expertise_matcher,
    get_discovery_query
)

from .formation import (
    # Composition Patterns (Pillar 5)
    CompositionPatternAnalyzer,
    CompositionPattern,
    PatternType,

    # Gap Analysis
    GapAnalyzer,
    ExpertiseGap,
    GapSeverity,

    # Formation Flow
    FormationFlowOrchestrator,
    FormationRecommendation,
    FormationStatus,

    # Singleton accessors
    get_pattern_analyzer,
    get_gap_analyzer,
    get_formation_orchestrator
)

__all__ = [
    # Profile Management
    "InnovatorProfileManager",
    "InnovatorProfile",
    "AvailabilityStatus",

    # Vouching Service
    "VouchingService",
    "VouchingRecord",
    "VouchingType",

    # Behavioral Expertise
    "BehavioralExpertiseCalculator",
    "ExpertiseScore",

    # Expertise Type Matching
    "ExpertiseTypeMatcher",
    "ExpertiseType",

    # Discovery Query
    "DiscoveryQuery",
    "DiscoveryCandidate",

    # Composition Patterns (Pillar 5)
    "CompositionPatternAnalyzer",
    "CompositionPattern",
    "PatternType",

    # Gap Analysis
    "GapAnalyzer",
    "ExpertiseGap",
    "GapSeverity",

    # Formation Flow
    "FormationFlowOrchestrator",
    "FormationRecommendation",
    "FormationStatus",

    # Singleton accessors
    "get_profile_manager",
    "get_vouching_service",
    "get_expertise_calculator",
    "get_expertise_matcher",
    "get_discovery_query",
    "get_pattern_analyzer",
    "get_gap_analyzer",
    "get_formation_orchestrator"
]
