"""
Trust Relationship Models - Inter-Organizational Trust Network

Trust relationships are bilateral: both organizations must agree.
Trust levels unlock enhanced sharing capabilities.

Lifecycle: PROPOSED -> ACTIVE -> EXPIRED / REVOKED
Types: BILATERAL | CONSORTIUM | RESEARCH
Sharing levels: PARTNER | INDUSTRY

IKF-IML Spec Section 7 implementation.
"""

from enum import Enum
from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class TrustRelationshipStatus(str, Enum):
    """Status of a trust relationship."""
    PROPOSED = "PROPOSED"     # One party has requested
    ACTIVE = "ACTIVE"         # Both parties have accepted
    EXPIRED = "EXPIRED"       # Past expiration date
    REVOKED = "REVOKED"       # One party terminated


class TrustRelationshipType(str, Enum):
    """Type of trust relationship."""
    BILATERAL = "BILATERAL"   # Two organizations
    CONSORTIUM = "CONSORTIUM" # Industry group
    RESEARCH = "RESEARCH"     # Academic partnership


class TrustSharingLevel(str, Enum):
    """Level of sharing enabled by trust."""
    INDUSTRY = "INDUSTRY"     # Standard industry sharing
    PARTNER = "PARTNER"       # Enhanced sharing (richer patterns, cross-org IDTFS)


class ReputationComponent(str, Enum):
    """Components of organization reputation score."""
    CONTRIBUTION_VOLUME = "contributionVolume"      # 20% weight
    CONTRIBUTION_QUALITY = "contributionQuality"    # 30% weight
    PATTERN_VALIDATION = "patternValidation"        # 25% weight
    COMMUNITY_ENGAGEMENT = "communityEngagement"    # 15% weight
    COMPLIANCE_RECORD = "complianceRecord"           # 10% weight


# Weight constants for reputation calculation
REPUTATION_WEIGHTS = {
    ReputationComponent.CONTRIBUTION_VOLUME: 0.20,
    ReputationComponent.CONTRIBUTION_QUALITY: 0.30,
    ReputationComponent.PATTERN_VALIDATION: 0.25,
    ReputationComponent.COMMUNITY_ENGAGEMENT: 0.15,
    ReputationComponent.COMPLIANCE_RECORD: 0.10
}


class TrustRelationship(BaseModel):
    """A trust relationship between two organizations."""
    relationship_id: str
    partner_org_id: str
    partner_org_name: Optional[str] = None
    relationship_type: TrustRelationshipType
    sharing_level: TrustSharingLevel
    status: TrustRelationshipStatus
    established_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None
    terms: Optional[Dict[str, Any]] = None


class TrustRequest(BaseModel):
    """Request to establish a trust relationship."""
    target_org_id: str
    relationship_type: TrustRelationshipType
    sharing_level: TrustSharingLevel
    justification: Optional[str] = None
    expiration_date: Optional[str] = None


class TrustResponse(BaseModel):
    """Response to a trust relationship request."""
    relationship_id: str
    accept: bool
    terms: Optional[Dict[str, Any]] = None


class ReputationScore(BaseModel):
    """Organization reputation score from IKF."""
    org_id: str
    overall_score: int  # 0-100
    components: Dict[str, Dict[str, float]]  # Component -> {score, weight}
    trend: str  # "improving", "declining", "stable"
    last_updated: datetime


class ReputationFeedback(BaseModel):
    """Feedback on a contribution for reputation calculation."""
    contribution_id: str
    feedback_type: str  # "applied", "dismissed", "validated", "disputed"
    effectiveness_rating: Optional[int] = None  # 1-5
    comments: Optional[str] = None
