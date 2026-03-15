"""
InDE MVP v3.4 - IDTFS Core (Innovator Discovery & Team Formation Service)
Six-pillar expertise assessment for intelligent team formation.

Pillars:
1. Behavioral Expertise (P1) - InDE-derived from maturity, contribution history
2. Professional Profile (P2) - External: career, domain tags, credentials
3. Vouching (P3) - Directional endorsements from peers
4. Availability (P4) - Binary filter (UNAVAILABLE = hard exclude)
5. Composition Patterns (P5) - IML/IKF team composition intelligence (Phase 9)
6. Expertise Type (P6) - Domain vs process capability matching

Core Components:
- InnovatorProfileManager: Manage profiles and availability
- VouchingService: Handle vouching records
- BehavioralExpertiseCalculator: Calculate P1 scores
- ExpertiseTypeMatcher: Match P6 capabilities
- DiscoveryQuery: Search interface
"""

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from core.config import IDTFS_CONFIG, AVAILABILITY_STATUSES
from core.database import db

logger = logging.getLogger("inde.discovery.idtfs")


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class AvailabilityStatus(str, Enum):
    """Availability status for team formation."""
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    LIMITED = "LIMITED"
    UNAVAILABLE = "UNAVAILABLE"


class VouchingType(str, Enum):
    """Types of vouching endorsements."""
    EXPERTISE = "EXPERTISE"
    CHARACTER = "CHARACTER"
    COLLABORATION = "COLLABORATION"
    DELIVERY = "DELIVERY"


class VouchStrength(str, Enum):
    """Strength of vouch."""
    STRONG = "STRONG"
    STANDARD = "STANDARD"
    QUALIFIED = "QUALIFIED"


class ExpertiseType(str, Enum):
    """Types of expertise for P6 matching."""
    DOMAIN = "DOMAIN"
    TECHNICAL = "TECHNICAL"
    CREATIVE = "CREATIVE"
    ANALYTICAL = "ANALYTICAL"
    CONNECTOR = "CONNECTOR"
    EXECUTOR = "EXECUTOR"
    MENTOR = "MENTOR"
    VISIONARY = "VISIONARY"


@dataclass
class InnovatorProfile:
    """
    IDTFS Innovator Profile (Pillars 2, 4).

    External profile information plus availability settings.
    """
    user_id: str
    org_id: str
    availability_status: AvailabilityStatus = AvailabilityStatus.PART_TIME
    availability_hours_per_week: float = 20.0
    availability_until: Optional[datetime] = None
    discovery_opt_in: bool = True
    declared_expertise_tags: List[str] = field(default_factory=list)
    inferred_expertise_tags: List[str] = field(default_factory=list)
    expertise_types: List[ExpertiseType] = field(default_factory=list)

    # Professional background (P2)
    domain_expertise_tags: List[str] = field(default_factory=list)
    career_summary: Optional[str] = None
    credential_indicators: List[str] = field(default_factory=list)
    corporate_directory_link: Optional[str] = None

    # Interest profile
    interest_areas: List[str] = field(default_factory=list)
    preferred_phases: List[str] = field(default_factory=list)
    team_size_preference: Optional[str] = None  # "small", "medium", "large"
    weekly_capacity_hours: Optional[int] = None

    # Metadata
    profile_completeness: float = 0.0
    last_availability_update: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "org_id": self.org_id,
            "availability_status": self.availability_status.value if isinstance(self.availability_status, Enum) else self.availability_status,
            "availability_hours_per_week": self.availability_hours_per_week,
            "availability_until": self.availability_until.isoformat() if self.availability_until else None,
            "discovery_opt_in": self.discovery_opt_in,
            "declared_expertise_tags": self.declared_expertise_tags,
            "inferred_expertise_tags": self.inferred_expertise_tags,
            "expertise_types": [et.value if isinstance(et, Enum) else et for et in self.expertise_types],
            "professional_background": {
                "domain_expertise_tags": self.domain_expertise_tags,
                "career_summary": self.career_summary,
                "credential_indicators": self.credential_indicators,
                "corporate_directory_link": self.corporate_directory_link
            },
            "interest_profile": {
                "domain_areas": self.interest_areas,
                "preferred_phases": self.preferred_phases,
                "team_size_preference": self.team_size_preference,
                "weekly_capacity_hours": self.weekly_capacity_hours
            },
            "profile_completeness": self.profile_completeness,
            "last_availability_update": self.last_availability_update.isoformat() if self.last_availability_update else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "InnovatorProfile":
        """Create from database document."""
        prof_bg = data.get("professional_background", {})
        interest = data.get("interest_profile", {})

        # Handle both old 'availability' and new 'availability_status' field names
        availability_val = data.get("availability_status", data.get("availability", "PART_TIME"))
        try:
            availability_status = AvailabilityStatus(availability_val)
        except ValueError:
            availability_status = AvailabilityStatus.PART_TIME

        profile = cls(
            user_id=data["user_id"],
            org_id=data["org_id"],
            availability_status=availability_status,
            availability_hours_per_week=data.get("availability_hours_per_week", 20.0),
            availability_until=datetime.fromisoformat(data["availability_until"]) if data.get("availability_until") else None,
            discovery_opt_in=data.get("discovery_opt_in", True),
            declared_expertise_tags=data.get("declared_expertise_tags", []),
            inferred_expertise_tags=data.get("inferred_expertise_tags", []),
            expertise_types=[ExpertiseType(et) for et in data.get("expertise_types", [])],
            domain_expertise_tags=prof_bg.get("domain_expertise_tags", []),
            career_summary=prof_bg.get("career_summary"),
            credential_indicators=prof_bg.get("credential_indicators", []),
            corporate_directory_link=prof_bg.get("corporate_directory_link"),
            interest_areas=interest.get("domain_areas", []),
            preferred_phases=interest.get("preferred_phases", []),
            team_size_preference=interest.get("team_size_preference"),
            weekly_capacity_hours=interest.get("weekly_capacity_hours"),
            profile_completeness=data.get("profile_completeness", 0.0)
        )

        if data.get("last_availability_update"):
            profile.last_availability_update = datetime.fromisoformat(data["last_availability_update"])

        return profile


@dataclass
class VouchingRecord:
    """
    IDTFS Vouching Record (Pillar 3).

    Directional endorsement from one innovator to another.
    """
    vouch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    voucher_id: str = ""      # Who is vouching
    vouchee_id: str = ""      # Who is being vouched for
    org_id: str = ""
    vouch_type: VouchingType = VouchingType.EXPERTISE
    expertise_tags: List[str] = field(default_factory=list)  # What they're vouching for
    strength: str = "STANDARD"
    context: Optional[str] = None  # Optional context/story
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict:
        return {
            "vouch_id": self.vouch_id,
            "voucher_id": self.voucher_id,
            "vouchee_id": self.vouchee_id,
            "org_id": self.org_id,
            "vouch_type": self.vouch_type.value if isinstance(self.vouch_type, Enum) else self.vouch_type,
            "expertise_tags": self.expertise_tags,
            "strength": self.strength.value if isinstance(self.strength, Enum) else self.strength,
            "context": self.context,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ExpertiseScore:
    """Expertise score from behavioral analysis (Pillar 1)."""
    user_id: str
    org_id: str
    overall_score: float
    component_scores: Dict[str, float] = field(default_factory=dict)
    evidence_count: int = 0
    confidence: float = 0.5
    last_calculated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DiscoveryCandidate:
    """A candidate returned from discovery search."""
    user_id: str
    composite_score: float
    pillar_scores: Dict[str, float] = field(default_factory=dict)
    matched_tags: List[str] = field(default_factory=list)
    expertise_types: List[str] = field(default_factory=list)
    availability_status: str = "PART_TIME"
    vouch_count: int = 0
    display_name: str = ""
    match_reason: str = ""


# =============================================================================
# INNOVATOR PROFILE MANAGER
# =============================================================================

class InnovatorProfileManager:
    """
    Manages innovator profiles for IDTFS (Pillars 2, 4).

    Handles profile CRUD, availability updates, and completeness calculation.
    """

    def __init__(self, db_instance=None):
        self._db = db_instance or db

    def get_profile(self, user_id: str, org_id: str) -> Optional[InnovatorProfile]:
        """Get an innovator's profile."""
        data = self._db.get_innovator_profile(user_id, org_id)
        if data:
            return InnovatorProfile.from_dict(data)
        return None

    def create_profile(self, profile: InnovatorProfile) -> InnovatorProfile:
        """Create a new innovator profile."""
        profile.profile_completeness = self._calculate_completeness(profile)
        profile.created_at = datetime.now(timezone.utc)
        profile.updated_at = datetime.now(timezone.utc)

        self._db.create_innovator_profile(profile.to_dict())
        return profile

    def update_profile(self, user_id: str, org_id: str, updates: Dict) -> bool:
        """Update an innovator profile."""
        # Get existing profile
        profile = self.get_profile(user_id, org_id)
        if not profile:
            return False

        # Apply updates
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        # Recalculate completeness
        profile.profile_completeness = self._calculate_completeness(profile)
        profile.updated_at = datetime.now(timezone.utc)

        return self._db.update_innovator_profile(user_id, org_id, {
            **updates,
            "profile_completeness": profile.profile_completeness
        })

    def update_availability(self, user_id: str, org_id: str,
                            status: AvailabilityStatus) -> bool:
        """Update availability status."""
        return self._db.update_innovator_profile(user_id, org_id, {
            "availability_status": status.value,
            "last_availability_update": datetime.now(timezone.utc)
        })

    def _calculate_completeness(self, profile: InnovatorProfile) -> float:
        """
        Calculate profile completeness (0.0 - 1.0).

        Weights:
        - Domain expertise tags: 30%
        - Career summary: 20%
        - Interest areas: 20%
        - Preferred phases: 15%
        - Capacity hours: 15%
        """
        score = 0.0

        if len(profile.domain_expertise_tags) >= 2:
            score += 0.30
        elif len(profile.domain_expertise_tags) >= 1:
            score += 0.15

        if profile.career_summary and len(profile.career_summary) > 50:
            score += 0.20

        if len(profile.interest_areas) >= 2:
            score += 0.20
        elif len(profile.interest_areas) >= 1:
            score += 0.10

        if len(profile.preferred_phases) >= 1:
            score += 0.15

        if profile.weekly_capacity_hours is not None:
            score += 0.15

        return min(score, 1.0)

    def get_available_profiles(self, org_id: str,
                                exclude_unavailable: bool = True) -> List[InnovatorProfile]:
        """Get profiles that are available or selective."""
        statuses = ["AVAILABLE", "SELECTIVE"]
        if not exclude_unavailable:
            statuses.append("UNAVAILABLE")

        data = self._db.get_available_innovators(org_id, statuses)
        return [InnovatorProfile.from_dict(d) for d in data]


# =============================================================================
# VOUCHING SERVICE
# =============================================================================

class VouchingService:
    """
    Manages vouching records for IDTFS (Pillar 3).

    Handles creating, retrieving, and revoking vouches.
    """

    def __init__(self, db_instance=None):
        self._db = db_instance or db

    def create_vouch(self, voucher_id: str, vouchee_id: str, org_id: str,
                     expertise_tags: List[str], strength: VouchStrength,
                     vouch_type: VouchingType = VouchingType.EXPERTISE,
                     context: str = None) -> VouchingRecord:
        """
        Create a vouching record.

        Args:
            voucher_id: User ID of person vouching
            vouchee_id: User ID of person being vouched for
            org_id: Organization context
            expertise_tags: What expertise is being vouched for
            strength: Strength of vouch
            vouch_type: Type of vouch (EXPERTISE, CHARACTER, etc.)
            context: Optional context/story

        Returns:
            Created VouchingRecord
        """
        # Verify both users are in the org
        voucher_membership = self._db.get_user_membership_in_org(voucher_id, org_id)
        vouchee_membership = self._db.get_user_membership_in_org(vouchee_id, org_id)

        if not voucher_membership or voucher_membership.get("status") != "active":
            raise ValueError("Voucher is not an active member of the organization")
        if not vouchee_membership or vouchee_membership.get("status") != "active":
            raise ValueError("Vouchee is not an active member of the organization")

        # Can't vouch for yourself
        if voucher_id == vouchee_id:
            raise ValueError("Cannot vouch for yourself")

        # Create the record
        record = VouchingRecord(
            voucher_id=voucher_id,
            vouchee_id=vouchee_id,
            org_id=org_id,
            vouch_type=vouch_type,
            expertise_tags=expertise_tags,
            strength=strength.value if isinstance(strength, Enum) else strength,
            context=context
        )

        self._db.create_vouching_record(
            voucher_id=voucher_id,
            vouchee_id=vouchee_id,
            org_id=org_id,
            vouch_type=vouch_type.value,
            expertise_tags=expertise_tags,
            strength=strength.value if isinstance(strength, Enum) else strength,
            context=context
        )

        return record

    def get_vouches_for_user(self, user_id: str, org_id: str) -> List[VouchingRecord]:
        """Get all active vouches for a user."""
        data = self._db.get_vouches_for_user(user_id, org_id)
        records = []
        for d in data:
            records.append(VouchingRecord(
                vouch_id=d.get("vouch_id", str(uuid.uuid4())),
                voucher_id=d["voucher_id"],
                vouchee_id=d.get("vouchee_id", d.get("vouched_id", "")),
                org_id=d["org_id"],
                vouch_type=VouchingType(d.get("vouch_type", "EXPERTISE")),
                expertise_tags=d.get("expertise_tags", []),
                strength=d.get("strength", "STANDARD"),
                context=d.get("context"),
                is_active=d.get("is_active", True)
            ))
        return records

    def get_vouch_score(self, user_id: str, org_id: str) -> float:
        """
        Calculate vouch score for a user (0.0 - 1.0).

        Scoring:
        - Each strong vouch: 0.15
        - Each standard vouch: 0.10
        - Each qualified vouch: 0.05
        - Cap at 1.0
        """
        vouches = self.get_vouches_for_user(user_id, org_id)
        score = 0.0

        for vouch in vouches:
            strength_val = vouch.strength if isinstance(vouch.strength, str) else vouch.strength.value if hasattr(vouch.strength, 'value') else str(vouch.strength)
            if strength_val == "STRONG":
                score += 0.15
            elif strength_val == "STANDARD":
                score += 0.10
            else:  # QUALIFIED
                score += 0.05

        return min(score, 1.0)

    def revoke_vouch(self, voucher_id: str, vouchee_id: str, org_id: str) -> bool:
        """Revoke a vouching record."""
        return self._db.revoke_vouch(voucher_id, vouchee_id, org_id)


# =============================================================================
# BEHAVIORAL EXPERTISE CALCULATOR
# =============================================================================

class BehavioralExpertiseCalculator:
    """
    Calculates behavioral expertise from InDE data (Pillar 1).

    Derives expertise score from:
    - Maturity level and dimension scores
    - Pursuit completion history
    - IKF contributions
    - Pattern applications
    """

    def __init__(self, db_instance=None):
        self._db = db_instance or db
        self.evidence_weights = {
            "maturity_level": 0.40,
            "completion_rate": 0.35,
            "ikf_contributions": 0.25
        }

    def calculate_expertise_score(self, user_id: str, org_id: str) -> Dict[str, float]:
        """
        Calculate behavioral expertise score.

        Returns:
            Dict with overall score and component breakdown
        """
        scores = {
            "maturity_component": 0.0,
            "completion_component": 0.0,
            "contribution_component": 0.0,
            "overall": 0.0
        }

        # Get user's pursuits in this org
        user_pursuits = self._db.get_user_pursuits(user_id)
        org_pursuits = [p for p in user_pursuits if p.get("org_id") == org_id]

        # 1. Maturity component (40%)
        # Get latest maturity event
        maturity_events = list(self._db.db.maturity_events.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(1))

        if maturity_events:
            level = maturity_events[0].get("maturity_level", "NOVICE")
            level_scores = {"NOVICE": 0.25, "COMPETENT": 0.50, "PROFICIENT": 0.75, "EXPERT": 1.0}
            scores["maturity_component"] = level_scores.get(level, 0.25)

        # 2. Completion component (35%)
        completed = [p for p in org_pursuits if p.get("status", "").startswith("COMPLETED")]
        total = len(org_pursuits)
        if total > 0:
            completion_rate = len(completed) / total
            scores["completion_component"] = min(completion_rate * 1.5, 1.0)  # Scale up

        # 3. Contribution component (25%)
        ikf_contributions = list(self._db.db.ikf_contributions.find({
            "user_id": user_id,
            "status": {"$in": ["IKF_READY", "SUBMITTED"]}
        }))
        scores["contribution_component"] = min(len(ikf_contributions) * 0.15, 1.0)

        # Calculate overall
        scores["overall"] = (
            scores["maturity_component"] * 0.40 +
            scores["completion_component"] * 0.35 +
            scores["contribution_component"] * 0.25
        )

        return scores


# =============================================================================
# EXPERTISE TYPE MATCHER
# =============================================================================

class ExpertiseTypeMatcher:
    """
    Matches expertise types for team formation (Pillar 6).

    Classifies expertise as domain, process, or hybrid.
    """

    # Process-related tags
    PROCESS_TAGS = [
        "validation", "user_research", "prototyping", "testing",
        "agile", "lean", "design_thinking", "facilitation",
        "stakeholder_management", "project_management"
    ]

    # Domain indicators (everything else is assumed domain)

    def classify_expertise(self, tags: List[str]) -> ExpertiseType:
        """
        Classify expertise based on tags.

        Args:
            tags: List of expertise tags

        Returns:
            ExpertiseType (DOMAIN, PROCESS, or HYBRID)
        """
        if not tags:
            return ExpertiseType.DOMAIN

        process_count = sum(1 for tag in tags if tag.lower() in self.PROCESS_TAGS)
        domain_count = len(tags) - process_count

        if process_count > 0 and domain_count > 0:
            return ExpertiseType.HYBRID
        elif process_count > domain_count:
            return ExpertiseType.PROCESS
        else:
            return ExpertiseType.DOMAIN

    def calculate_match_score(self, candidate_tags: List[str],
                               required_tags: List[str],
                               required_type: ExpertiseType = None) -> float:
        """
        Calculate how well a candidate matches required expertise.

        Args:
            candidate_tags: Candidate's expertise tags
            required_tags: Tags needed for the gap
            required_type: Optional type requirement

        Returns:
            Match score (0.0 - 1.0)
        """
        if not required_tags:
            return 0.5  # No specific requirements

        # Tag overlap score
        candidate_set = set(t.lower() for t in candidate_tags)
        required_set = set(t.lower() for t in required_tags)

        if not required_set:
            return 0.5

        overlap = len(candidate_set & required_set)
        tag_score = overlap / len(required_set)

        # Type match bonus
        type_bonus = 0.0
        if required_type:
            candidate_type = self.classify_expertise(candidate_tags)
            if candidate_type == required_type:
                type_bonus = 0.2
            elif candidate_type == ExpertiseType.HYBRID:
                type_bonus = 0.1

        return min(tag_score + type_bonus, 1.0)


# =============================================================================
# DISCOVERY QUERY
# =============================================================================

class DiscoveryQuery:
    """
    Search interface for discovering team candidates.

    Combines all pillars for scoring and ranking.
    """

    def __init__(self, db_instance=None):
        self._db = db_instance or db
        self._profile_manager = InnovatorProfileManager(db_instance)
        self._vouching_service = VouchingService(db_instance)
        self._behavioral_calc = BehavioralExpertiseCalculator(db_instance)
        self._type_matcher = ExpertiseTypeMatcher()

        self._weights = IDTFS_CONFIG.get("pillar_weights", {
            "p1_behavioral_expertise": 0.20,
            "p2_professional_profile": 0.15,
            "p3_vouching": 0.15,
            "p4_availability": 0.0,  # Binary filter
            "p5_composition_patterns": 0.25,
            "p6_expertise_type": 0.25
        })

    def search(
        self,
        org_id: str,
        gap_description: str,
        required_tags: List[str] = None,
        required_type: ExpertiseType = None,
        preferred_phases: List[str] = None,
        exclude_user_ids: List[str] = None,
        max_candidates: int = None
    ) -> List[DiscoveryCandidate]:
        """
        Search for team formation candidates.

        Args:
            org_id: Organization to search within
            gap_description: Description of the expertise gap
            required_tags: Tags to match against
            required_type: Required expertise type
            preferred_phases: Preferred innovation phases
            exclude_user_ids: Users to exclude (e.g., current team)
            max_candidates: Maximum candidates to return

        Returns:
            List of DiscoveryCandidate sorted by composite score
        """
        max_candidates = max_candidates or IDTFS_CONFIG.get("max_candidates", 20)
        required_tags = required_tags or []
        exclude_user_ids = exclude_user_ids or []

        # Get all available profiles
        hard_exclude_unavailable = IDTFS_CONFIG.get("unavailable_hard_exclude", True)
        profiles = self._profile_manager.get_available_profiles(
            org_id, exclude_unavailable=hard_exclude_unavailable
        )

        candidates = []
        for profile in profiles:
            if profile.user_id in exclude_user_ids:
                continue

            # Skip completely unavailable if hard exclude
            if hard_exclude_unavailable and profile.availability_status == AvailabilityStatus.UNAVAILABLE:
                continue

            # Calculate pillar scores
            pillar_scores = self._calculate_pillar_scores(
                profile=profile,
                required_tags=required_tags,
                required_type=required_type,
                preferred_phases=preferred_phases
            )

            # Calculate composite score
            composite = self._calculate_composite_score(pillar_scores)

            # Get user info for display
            user = self._db.get_user(profile.user_id)
            display_name = user.get("name", profile.user_id) if user else profile.user_id

            # Get vouch count
            vouches = self._vouching_service.get_vouches_for_user(profile.user_id, org_id)

            candidates.append(DiscoveryCandidate(
                user_id=profile.user_id,
                display_name=display_name,
                composite_score=composite,
                pillar_scores=pillar_scores,
                matched_tags=profile.domain_expertise_tags,
                expertise_types=[et.value if isinstance(et, Enum) else et for et in profile.expertise_types],
                availability_status=profile.availability_status.value,
                vouch_count=len(vouches),
                match_reason=self._generate_match_reason(pillar_scores, required_tags)
            ))

        # Sort by composite score descending
        candidates.sort(key=lambda c: c.composite_score, reverse=True)

        return candidates[:max_candidates]

    def _calculate_pillar_scores(
        self,
        profile: InnovatorProfile,
        required_tags: List[str],
        required_type: ExpertiseType,
        preferred_phases: List[str]
    ) -> Dict[str, float]:
        """Calculate individual pillar scores."""
        scores = {}

        # P1: Behavioral Expertise
        behavioral = self._behavioral_calc.calculate_expertise_score(
            profile.user_id, profile.org_id
        )
        scores["p1_behavioral_expertise"] = behavioral["overall"]

        # P2: Professional Profile (completeness as proxy)
        scores["p2_professional_profile"] = profile.profile_completeness

        # P3: Vouching
        scores["p3_vouching"] = self._vouching_service.get_vouch_score(
            profile.user_id, profile.org_id
        )

        # P4: Availability (binary for scoring, already filtered if hard exclude)
        if profile.availability_status == AvailabilityStatus.FULL_TIME:
            scores["p4_availability"] = 1.0
        elif profile.availability_status == AvailabilityStatus.PART_TIME:
            scores["p4_availability"] = 0.8
        elif profile.availability_status == AvailabilityStatus.LIMITED:
            scores["p4_availability"] = 0.5
        else:
            scores["p4_availability"] = 0.0

        # P5: Composition Patterns (placeholder for Phase 9)
        scores["p5_composition_patterns"] = 0.5

        # P6: Expertise Type Match
        scores["p6_expertise_type"] = self._type_matcher.calculate_match_score(
            profile.domain_expertise_tags,
            required_tags,
            required_type
        )

        # Phase preference bonus
        if preferred_phases and profile.preferred_phases:
            overlap = set(preferred_phases) & set(profile.preferred_phases)
            if overlap:
                scores["p6_expertise_type"] = min(scores["p6_expertise_type"] + 0.1, 1.0)

        return scores

    def _calculate_composite_score(self, pillar_scores: Dict[str, float]) -> float:
        """Calculate weighted composite score."""
        composite = 0.0
        for pillar, weight in self._weights.items():
            score = pillar_scores.get(pillar, 0.0)
            composite += score * weight
        return min(composite, 1.0)

    def _generate_match_reason(self, pillar_scores: Dict[str, float],
                                required_tags: List[str]) -> str:
        """Generate human-readable match reason."""
        reasons = []

        if pillar_scores.get("p6_expertise_type", 0) > 0.7:
            reasons.append("Strong expertise match")
        if pillar_scores.get("p3_vouching", 0) > 0.5:
            reasons.append("Well vouched")
        if pillar_scores.get("p1_behavioral_expertise", 0) > 0.6:
            reasons.append("High behavioral expertise")

        return "; ".join(reasons) if reasons else "Potential match"


# Global instances
_profile_manager: Optional[InnovatorProfileManager] = None
_vouching_service: Optional[VouchingService] = None
_expertise_calculator: Optional[BehavioralExpertiseCalculator] = None
_expertise_matcher: Optional[ExpertiseTypeMatcher] = None
_discovery_query: Optional[DiscoveryQuery] = None


def get_profile_manager() -> InnovatorProfileManager:
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = InnovatorProfileManager()
    return _profile_manager


def get_vouching_service() -> VouchingService:
    global _vouching_service
    if _vouching_service is None:
        _vouching_service = VouchingService()
    return _vouching_service


def get_expertise_calculator() -> BehavioralExpertiseCalculator:
    global _expertise_calculator
    if _expertise_calculator is None:
        _expertise_calculator = BehavioralExpertiseCalculator()
    return _expertise_calculator


def get_expertise_matcher() -> ExpertiseTypeMatcher:
    global _expertise_matcher
    if _expertise_matcher is None:
        _expertise_matcher = ExpertiseTypeMatcher()
    return _expertise_matcher


def get_discovery_query() -> DiscoveryQuery:
    global _discovery_query
    if _discovery_query is None:
        _discovery_query = DiscoveryQuery()
    return _discovery_query
