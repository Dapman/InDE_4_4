"""
InDE IKF Service v3.5.2 - Contribution Models

Defines the contribution lifecycle statuses including v3.5.2
post-approval federation submission states.
"""

from enum import Enum
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ContributionStatus(str, Enum):
    """
    Contribution lifecycle statuses.

    v3.2-v3.5.1: Pre-approval lifecycle
    - DRAFT: Prepared, awaiting human review
    - UNDER_REVIEW: Being reviewed
    - IKF_READY: Approved, ready for federation
    - REJECTED: Rejected by reviewer

    v3.5.2: Post-approval federation lifecycle
    - IKF_SUBMITTING: Outbox worker picked up, submission in progress
    - IKF_SUBMITTED: Remote IKF acknowledged receipt
    - IKF_ACCEPTED: IKF validated and accepted the contribution
    - IKF_REJECTED: IKF rejected (with reason)
    - IKF_RETRY: Submission failed, scheduled for retry
    - IKF_FAILED: Max retries exceeded, needs manual intervention
    - IKF_INTEGRATED: IKF adopted into global pattern library (eventual)
    """
    # Existing statuses (v3.2-v3.5.1)
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    IKF_READY = "IKF_READY"
    REJECTED = "REJECTED"

    # New statuses (v3.5.2) - post-approval lifecycle
    IKF_SUBMITTING = "IKF_SUBMITTING"     # Outbox worker picked up, submission in progress
    IKF_SUBMITTED = "IKF_SUBMITTED"       # Remote IKF acknowledged receipt
    IKF_ACCEPTED = "IKF_ACCEPTED"         # IKF validated and accepted the contribution
    IKF_REJECTED = "IKF_REJECTED"         # IKF rejected (with reason)
    IKF_RETRY = "IKF_RETRY"               # Submission failed, scheduled for retry
    IKF_FAILED = "IKF_FAILED"             # Max retries exceeded, needs manual intervention
    IKF_INTEGRATED = "IKF_INTEGRATED"     # IKF adopted into global pattern library


class OutboxStatus(str, Enum):
    """Outbox entry lifecycle status."""
    PENDING = "PENDING"       # Queued, waiting for submission
    RETRY = "RETRY"           # Failed, scheduled for retry
    DELIVERED = "DELIVERED"   # Successfully submitted to IKF
    FAILED = "FAILED"         # Max retries exceeded


class ContributionPackageType(str, Enum):
    """IKF contribution package types."""
    TEMPORAL_BENCHMARK = "temporal_benchmark"
    PATTERN_CONTRIBUTION = "pattern_contribution"
    RISK_INTELLIGENCE = "risk_intelligence"
    EFFECTIVENESS_METRICS = "effectiveness_metrics"
    RETROSPECTIVE_WISDOM = "retrospective_wisdom"


class SharingRights(str, Enum):
    """Data sharing rights for contributions."""
    PERSONAL = "PERSONAL"   # Never federates
    ORG = "ORG"             # Federate after generalization
    IKF = "IKF"             # Available to all InDEVerse


class ContributionBase(BaseModel):
    """Base contribution model."""
    contribution_id: str
    pursuit_id: Optional[str] = None
    user_id: str
    org_id: Optional[str] = None
    package_type: str
    status: ContributionStatus = ContributionStatus.DRAFT

    # Content
    original_summary: Optional[str] = None
    generalized_summary: Optional[str] = None
    original_data: Optional[Dict[str, Any]] = None
    generalized_data: Optional[Dict[str, Any]] = None
    generalized_content: Optional[Dict[str, Any]] = None

    # Generalization metadata
    generalization_level: int = 0
    min_generalization_level: int = 1
    transformations_log: List[Dict[str, Any]] = []

    # PII scan results
    pii_scan: Optional[Dict[str, Any]] = None

    # Sharing
    sharing_rights: SharingRights = SharingRights.ORG
    explicit_ikf_consent: bool = False

    # Timestamps
    created_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Federation metadata (v3.5.2)
    ikf_receipt_id: Optional[str] = None
    failure_reason: Optional[str] = None

    class Config:
        use_enum_values = True


class OutboxEntry(BaseModel):
    """Contribution outbox entry for guaranteed delivery."""
    contribution_id: str
    status: OutboxStatus = OutboxStatus.PENDING
    enqueued_at: datetime
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    next_attempt_after: datetime
    delivered_at: Optional[datetime] = None
    error: Optional[str] = None
