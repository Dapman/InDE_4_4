"""
Biomimicry pattern database models.

The biomimicry_patterns collection stores curated biological strategies
with functional metadata for coaching context matching. Each pattern
represents a biological organism's strategy that has known applications
in human innovation.

Three-Tier Intelligence Model:
- Tier 1: This database - structured detection (function extraction -> matching -> scoring)
- Tier 2: LLM deep knowledge - unbounded reasoning about biology (not stored here)
- Tier 3: IKF federation - patterns from other orgs (source = "ikf_federation")
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class BiomimicryCategory(str, Enum):
    """Categories of biological strategies."""
    THERMAL_REGULATION = "THERMAL_REGULATION"
    STRUCTURAL_STRENGTH = "STRUCTURAL_STRENGTH"
    WATER_MANAGEMENT = "WATER_MANAGEMENT"
    ENERGY_EFFICIENCY = "ENERGY_EFFICIENCY"
    SWARM_INTELLIGENCE = "SWARM_INTELLIGENCE"
    SELF_HEALING = "SELF_HEALING"
    COMMUNICATION = "COMMUNICATION"
    ADAPTATION = "ADAPTATION"


class BiomimicryFunction(str, Enum):
    """Standardized functional categories for matching."""
    THERMAL_REGULATION = "thermal_regulation"
    STRUCTURAL_OPTIMIZATION = "structural_optimization"
    WATER_MANAGEMENT = "water_management"
    ENERGY_EFFICIENCY = "energy_efficiency"
    SWARM_COORDINATION = "swarm_coordination"
    SELF_HEALING = "self_healing"
    COMMUNICATION_SIGNALING = "communication_signaling"
    ENVIRONMENTAL_ADAPTATION = "environmental_adaptation"
    SURFACE_ENGINEERING = "surface_engineering"
    PASSIVE_HARVESTING = "passive_harvesting"
    DRAG_REDUCTION = "drag_reduction"
    IMPACT_ABSORPTION = "impact_absorption"
    PATTERN_RECOGNITION = "pattern_recognition"
    DISTRIBUTED_DECISION = "distributed_decision"
    RESOURCE_OPTIMIZATION = "resource_optimization"
    REGENERATION = "regeneration"
    CAMOUFLAGE = "camouflage"
    ADHESION = "adhesion"


# List of valid functions for LLM prompt
VALID_FUNCTIONS = [f.value for f in BiomimicryFunction]


class KnownApplication(BaseModel):
    """A documented real-world application of a biological strategy."""
    name: str
    description: str
    impact: str
    domains: List[str]


class BiomimicryPattern(BaseModel):
    """A curated biological strategy with innovation application metadata."""
    pattern_id: str
    organism: str
    category: BiomimicryCategory
    strategy_name: str
    description: str                             # Human-readable description
    mechanism: str                               # Detailed biological mechanism
    functions: List[str]                         # Functional keywords for matching
    applicable_domains: List[str]                # Innovation domains
    known_applications: List[KnownApplication]   # Documented real-world applications
    innovation_principles: List[str]             # Abstracted principles
    triz_connections: List[str] = []             # Pre-wiring for v3.6.1 TRIZ synergy
    federation_eligible: bool = True
    match_count: int = 0
    acceptance_rate: float = 0.0
    feedback_scores: List[float] = []
    source: str = "curated"                      # curated | ikf_federation | org_contributed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BiomimicryMatch(BaseModel):
    """Records a pattern match event for analytics and feedback loop."""
    match_id: str
    pursuit_id: str
    pattern_id: str
    match_score: float                           # 0.0 - 1.0 relevance
    extracted_functions: List[str]               # Functions extracted from challenge
    challenge_context: str                       # Anonymized challenge summary
    innovator_response: str = "pending"          # pending | explored | accepted | deferred | dismissed
    feedback_rating: Optional[int] = None        # 1-5 post-guidance rating
    methodology: Optional[str] = None            # Active methodology at time of match
    coaching_session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    responded_at: Optional[datetime] = None


class BiomimicryMatchResult(BaseModel):
    """Result of pattern matching - passed to coaching context."""
    pattern_id: str
    organism: str
    strategy_name: str
    description: str
    mechanism: str
    innovation_principles: List[str]
    triz_connections: List[str]
    score: float
    reason: str  # LLM-generated relevance explanation
    known_applications: List[Dict[str, Any]]
    category: str = ""
    functions: List[str] = []


class InnovatorResponse(str, Enum):
    """Possible innovator responses to biomimicry insights."""
    PENDING = "pending"
    EXPLORED = "explored"
    ACCEPTED = "accepted"
    DEFERRED = "deferred"
    DISMISSED = "dismissed"
