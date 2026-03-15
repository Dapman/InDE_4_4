"""
InDE MVP v3.10 - Temporal Conflict Resolver

TD-001: Detects and manages conflicts between newly extracted milestones
and existing stored milestones for the same pursuit.

Called by TimelineExtractor BEFORE storing a new milestone.

Conflict Detection:
1. Direct date conflict: Same milestone type with target_date differing >14 days
2. Project end date shift: Release milestone differs from current project end
3. Retrograde milestone: Past date mentioned - treat as completed milestone

Versioning:
- When a conflict is resolved, old milestone is marked is_superseded=True
- New milestone gets milestone_version = old_version + 1
- supersedes_milestone_id links to the old milestone
"""

import logging
from dataclasses import dataclass
from datetime import datetime, date, timezone
from enum import Enum
from typing import Optional, Dict, List, Any

from config import (
    TIMELINE_CONFLICT_THRESHOLD_DAYS,
    CONFLICT_SEVERITY_NONE,
    CONFLICT_SEVERITY_MINOR,
    CONFLICT_SEVERITY_MAJOR,
    CONFLICT_SEVERITY_RETROGRADE,
    RESOLUTION_USER_CONFIRMED,
    RESOLUTION_AUTO_MINOR_UPDATE
)

logger = logging.getLogger(__name__)


class ConflictSeverity(str, Enum):
    """Conflict severity levels."""
    NONE = CONFLICT_SEVERITY_NONE           # No conflict - safe to store
    MINOR = CONFLICT_SEVERITY_MINOR         # <14 day shift - store but note in coaching
    MAJOR = CONFLICT_SEVERITY_MAJOR         # >14 day shift - hold pending user confirmation
    RETROGRADE = CONFLICT_SEVERITY_RETROGRADE  # Past date - treat as completed milestone


@dataclass
class ConflictResult:
    """Result of conflict detection check."""
    severity: ConflictSeverity
    existing_milestone_id: Optional[str]
    existing_date: Optional[str]
    proposed_date: Optional[str]
    day_difference: int
    coaching_prompt: Optional[str]  # Natural language prompt for the coaching engine
    can_store_immediately: bool     # False when severity == MAJOR (requires user confirmation)


class TemporalConflictResolver:
    """
    Detects and manages conflicts between newly extracted milestones
    and existing stored milestones.

    Call chain:
    Message received -> ScaffoldingEngine -> TimelineExtractor.extract()
        -> TimelineExtractor._candidate_milestone(milestone)
        -> TemporalConflictResolver.check(milestone, pursuit_id)
            -> if conflict detected: return ConflictResult (do NOT store yet)
            -> if no conflict: return ClearResult (safe to store)
        -> If conflict: ScaffoldingEngine queues conflict prompt for next response
        -> If clear: TimelineExtractor._store_milestone(milestone)
    """

    def __init__(self, db):
        """
        Initialize TemporalConflictResolver.

        Args:
            db: Database instance with access to pursuit_milestones collection
        """
        self.db = db
        self.conflict_threshold = TIMELINE_CONFLICT_THRESHOLD_DAYS

    def check(self, candidate: Dict, pursuit_id: str) -> ConflictResult:
        """
        Evaluate a candidate milestone against existing stored milestones.
        Returns a ConflictResult indicating whether storage can proceed.

        Args:
            candidate: The proposed milestone dict (not yet stored)
            pursuit_id: The pursuit this milestone belongs to

        Returns:
            ConflictResult with severity and coaching prompt if applicable
        """
        candidate_date = self._parse_date(candidate.get("target_date"))

        if not candidate_date:
            # Can't resolve - store as-is
            return ConflictResult(
                severity=ConflictSeverity.NONE,
                existing_milestone_id=None,
                existing_date=None,
                proposed_date=candidate.get("target_date"),
                day_difference=0,
                coaching_prompt=None,
                can_store_immediately=True
            )

        # Retrograde check: date is in the past relative to extraction time
        today = date.today()
        if candidate_date < today:
            logger.info(f"[ConflictResolver] Retrograde date detected: {candidate_date}")
            return ConflictResult(
                severity=ConflictSeverity.RETROGRADE,
                existing_milestone_id=None,
                existing_date=None,
                proposed_date=str(candidate_date),
                day_difference=(today - candidate_date).days,
                coaching_prompt=None,  # Caller marks this as completed, not flagged
                can_store_immediately=True
            )

        # Fetch existing non-superseded milestones for this pursuit
        existing = self._get_existing_milestones(pursuit_id)

        # Find the most relevant existing milestone to compare against
        conflict_target = self._find_conflict_target(candidate, existing)

        if not conflict_target:
            return ConflictResult(
                severity=ConflictSeverity.NONE,
                existing_milestone_id=None,
                existing_date=None,
                proposed_date=str(candidate_date),
                day_difference=0,
                coaching_prompt=None,
                can_store_immediately=True
            )

        existing_date = self._parse_date(conflict_target.get("target_date"))
        if not existing_date:
            return ConflictResult(
                severity=ConflictSeverity.NONE,
                existing_milestone_id=conflict_target.get("milestone_id"),
                existing_date=conflict_target.get("target_date"),
                proposed_date=str(candidate_date),
                day_difference=0,
                coaching_prompt=None,
                can_store_immediately=True
            )

        day_diff = abs((candidate_date - existing_date).days)

        if day_diff <= 3:
            # Within noise threshold - treat as the same date, no conflict
            logger.debug(f"[ConflictResolver] Within noise threshold ({day_diff} days)")
            return ConflictResult(
                severity=ConflictSeverity.NONE,
                existing_milestone_id=conflict_target.get("milestone_id"),
                existing_date=str(existing_date),
                proposed_date=str(candidate_date),
                day_difference=day_diff,
                coaching_prompt=None,
                can_store_immediately=True
            )
        elif day_diff <= self.conflict_threshold:
            # Minor shift - note it but allow storage
            logger.info(f"[ConflictResolver] Minor conflict: {day_diff} days difference")
            return ConflictResult(
                severity=ConflictSeverity.MINOR,
                existing_milestone_id=conflict_target.get("milestone_id"),
                existing_date=str(existing_date),
                proposed_date=str(candidate_date),
                day_difference=day_diff,
                coaching_prompt=self._build_minor_prompt(
                    conflict_target, str(existing_date), str(candidate_date), day_diff
                ),
                can_store_immediately=True
            )
        else:
            # Major shift - require explicit confirmation
            logger.info(f"[ConflictResolver] Major conflict: {day_diff} days difference")
            return ConflictResult(
                severity=ConflictSeverity.MAJOR,
                existing_milestone_id=conflict_target.get("milestone_id"),
                existing_date=str(existing_date),
                proposed_date=str(candidate_date),
                day_difference=day_diff,
                coaching_prompt=self._build_major_prompt(
                    conflict_target, str(existing_date), str(candidate_date), day_diff
                ),
                can_store_immediately=False
            )

    def _get_existing_milestones(self, pursuit_id: str) -> List[Dict]:
        """Fetch non-superseded milestones for the pursuit."""
        try:
            milestones = list(self.db.db.pursuit_milestones.find({
                "pursuit_id": pursuit_id,
                "is_superseded": {"$ne": True}
            }))
            return milestones
        except Exception as e:
            logger.error(f"[ConflictResolver] Error fetching milestones: {e}")
            return []

    def _find_conflict_target(self, candidate: Dict, existing: List[Dict]) -> Optional[Dict]:
        """
        Find the most relevant existing milestone to compare the candidate against.

        Strategy:
        1. If candidate is "release" type and there's an existing release milestone -> that's the target
        2. If candidate title fuzzy-matches an existing milestone title -> that's the target
        3. Otherwise -> no conflict target (new, distinct milestone)
        """
        candidate_type = candidate.get("milestone_type", "")
        candidate_title = candidate.get("title", "").lower()

        for m in existing:
            # Same type: release-vs-release is always a conflict check
            if m.get("milestone_type") == candidate_type == "release":
                return m
            # Fuzzy title match
            existing_title = m.get("title", "").lower()
            if self._title_similarity(candidate_title, existing_title) > 0.7:
                return m

        return None

    def _title_similarity(self, a: str, b: str) -> float:
        """Simple token overlap similarity for milestone title matching."""
        tokens_a = set(a.split())
        tokens_b = set(b.split())
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union)

    def _build_minor_prompt(self, existing_m: Dict, old_date: str,
                            new_date: str, day_diff: int) -> str:
        """Build coaching prompt for minor conflict (informational)."""
        title = existing_m.get("title", "your target milestone")
        direction = "earlier" if new_date < old_date else "later"
        return (
            f"I noticed you mentioned {new_date} - that's about {day_diff} days "
            f"{direction} than the {title} date we had ({old_date}). "
            f"I'll update the timeline to reflect that."
        )

    def _build_major_prompt(self, existing_m: Dict, old_date: str,
                            new_date: str, day_diff: int) -> str:
        """Build coaching prompt for major conflict (requires confirmation)."""
        title = existing_m.get("title", "your target milestone")
        direction = "earlier" if new_date < old_date else "later"
        weeks = round(day_diff / 7)
        return (
            f"I want to make sure I've got your timeline right. Earlier we had {title} "
            f"set for {old_date}, but you just mentioned {new_date} - "
            f"that's about {weeks} week{'s' if weeks != 1 else ''} {direction}. "
            f"Should I update your timeline to {new_date}, or was that a different milestone?"
        )

    def supersede_milestone(self, old_id: str, new_milestone_doc: Dict,
                            resolution_strategy: str) -> Dict:
        """
        Mark the old milestone as superseded and store the new one as version N+1.

        Args:
            old_id: milestone_id of the milestone being superseded
            new_milestone_doc: The new milestone document to insert
            resolution_strategy: "user_confirmed" or "auto_minor_update"

        Returns:
            The inserted new milestone document with its new milestone_id
        """
        import uuid
        now = datetime.now(timezone.utc).isoformat() + "Z"

        # Get the old milestone to determine version number
        old_m = self.db.db.pursuit_milestones.find_one({"milestone_id": old_id})
        old_version = old_m.get("milestone_version", 1) if old_m else 1

        # Mark old as superseded
        self.db.db.pursuit_milestones.update_one(
            {"milestone_id": old_id},
            {"$set": {
                "is_superseded": True,
                "updated_at": now
            }}
        )
        logger.info(f"[ConflictResolver] Marked milestone {old_id} as superseded")

        # Assign version to new milestone
        new_milestone_doc["milestone_id"] = str(uuid.uuid4())
        new_milestone_doc["milestone_version"] = old_version + 1
        new_milestone_doc["supersedes_milestone_id"] = old_id
        new_milestone_doc["conflict_resolution_strategy"] = resolution_strategy
        new_milestone_doc["is_superseded"] = False
        new_milestone_doc["created_at"] = now
        new_milestone_doc["updated_at"] = now

        # Insert new milestone
        self.db.db.pursuit_milestones.insert_one(new_milestone_doc)
        logger.info(
            f"[ConflictResolver] Created milestone v{new_milestone_doc['milestone_version']}: "
            f"{new_milestone_doc['milestone_id']}"
        )

        return new_milestone_doc

    def resolve_conflict(self, pursuit_id: str, choice: str,
                         pending_milestone: Dict, existing_milestone_id: str) -> Dict:
        """
        Resolve a pending conflict based on user's choice.

        Args:
            pursuit_id: The pursuit ID
            choice: "accept_new" | "keep_existing" | "keep_both"
            pending_milestone: The milestone that was held pending resolution
            existing_milestone_id: The ID of the conflicting existing milestone

        Returns:
            Resolution result dict
        """
        now = datetime.now(timezone.utc).isoformat() + "Z"

        if choice == "accept_new":
            # Supersede old milestone with new one
            new_doc = self.supersede_milestone(
                old_id=existing_milestone_id,
                new_milestone_doc=pending_milestone,
                resolution_strategy=RESOLUTION_USER_CONFIRMED
            )
            return {
                "action": "superseded",
                "old_milestone_id": existing_milestone_id,
                "new_milestone_id": new_doc["milestone_id"],
                "resolved_at": now
            }

        elif choice == "keep_existing":
            # Discard the pending milestone
            return {
                "action": "discarded",
                "discarded_title": pending_milestone.get("title"),
                "kept_milestone_id": existing_milestone_id,
                "resolved_at": now
            }

        elif choice == "keep_both":
            # Store pending milestone without superseding old one
            import uuid
            pending_milestone["milestone_id"] = str(uuid.uuid4())
            pending_milestone["milestone_version"] = 1
            pending_milestone["is_superseded"] = False
            pending_milestone["conflict_resolution_strategy"] = RESOLUTION_USER_CONFIRMED
            pending_milestone["created_at"] = now
            pending_milestone["updated_at"] = now

            self.db.db.pursuit_milestones.insert_one(pending_milestone)

            return {
                "action": "both_kept",
                "existing_milestone_id": existing_milestone_id,
                "new_milestone_id": pending_milestone["milestone_id"],
                "resolved_at": now
            }

        else:
            raise ValueError(f"Invalid resolution choice: {choice}")

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            # Handle ISO format with time component
            if "T" in date_str:
                date_str = date_str.split("T")[0]
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None
