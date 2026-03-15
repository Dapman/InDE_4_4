"""
InDE MVP v3.10 - Timeline Consistency Validator

TD-002: Detects and surfaces inconsistencies between time_allocations.target_end
and the latest release milestone target_date for a pursuit.

Runs in two modes:
1. On-demand: Triggered immediately after any release milestone is stored/updated
2. Scheduled: Runs once per session on pursuit load

When inconsistency is detected, surfaces a coaching prompt presenting
the user with a clear choice: which date governs?
"""

import logging
from dataclasses import dataclass
from datetime import datetime, date, timezone
from typing import Optional, Dict, Any

from config import TIMELINE_INCONSISTENCY_THRESHOLD_DAYS

logger = logging.getLogger(__name__)


@dataclass
class ConsistencyResult:
    """Result of consistency validation."""
    is_consistent: bool
    allocation_end: Optional[str]        # From time_allocations.target_end
    milestone_end: Optional[str]         # From latest release milestone
    day_difference: int
    coaching_prompt: Optional[str]


class TimelineConsistencyValidator:
    """
    Validates consistency between time_allocations and milestone dates.

    The timeline module should have a single source of truth for the
    project end date. This validator detects when time_allocations.target_end
    and the latest release milestone disagree beyond a threshold.
    """

    def __init__(self, db):
        """
        Initialize TimelineConsistencyValidator.

        Args:
            db: Database instance with access to time_allocations and milestones
        """
        self.db = db
        self.threshold_days = TIMELINE_INCONSISTENCY_THRESHOLD_DAYS

    async def validate(self, pursuit_id: str) -> ConsistencyResult:
        """
        Check consistency between time_allocations.target_end and
        the latest non-superseded release milestone.

        Args:
            pursuit_id: The pursuit to validate

        Returns:
            ConsistencyResult. If inconsistent, includes a coaching prompt.
        """
        # Get time allocation
        allocation = self.db.db.time_allocations.find_one(
            {"pursuit_id": pursuit_id}
        )

        # Get latest non-superseded release milestone
        latest_release = self.db.db.pursuit_milestones.find_one(
            {
                "pursuit_id": pursuit_id,
                "milestone_type": "release",
                "is_superseded": {"$ne": True}
            },
            sort=[("target_date", -1)]
        )

        alloc_end = allocation.get("target_end") if allocation else None
        milestone_end = latest_release.get("target_date") if latest_release else None

        # If either is missing, no inconsistency to report
        if not alloc_end or not milestone_end:
            return ConsistencyResult(
                is_consistent=True,
                allocation_end=alloc_end,
                milestone_end=milestone_end,
                day_difference=0,
                coaching_prompt=None
            )

        alloc_date = self._parse_date(alloc_end)
        milestone_date = self._parse_date(milestone_end)

        if not alloc_date or not milestone_date:
            return ConsistencyResult(
                is_consistent=True,
                allocation_end=alloc_end,
                milestone_end=milestone_end,
                day_difference=0,
                coaching_prompt=None
            )

        day_diff = abs((alloc_date - milestone_date).days)

        if day_diff <= self.threshold_days:
            logger.debug(f"[ConsistencyValidator] Within threshold ({day_diff} days)")
            return ConsistencyResult(
                is_consistent=True,
                allocation_end=alloc_end,
                milestone_end=milestone_end,
                day_difference=day_diff,
                coaching_prompt=None
            )

        # Build a clear, choice-presenting coaching prompt
        prompt = self._build_inconsistency_prompt(alloc_end, milestone_end, day_diff)
        logger.info(f"[ConsistencyValidator] Inconsistency detected: {day_diff} days difference")

        return ConsistencyResult(
            is_consistent=False,
            allocation_end=alloc_end,
            milestone_end=milestone_end,
            day_difference=day_diff,
            coaching_prompt=prompt
        )

    def validate_sync(self, pursuit_id: str) -> ConsistencyResult:
        """
        Synchronous version of validate for non-async contexts.
        """
        # Get time allocation
        allocation = self.db.db.time_allocations.find_one(
            {"pursuit_id": pursuit_id}
        )

        # Get latest non-superseded release milestone
        latest_release = self.db.db.pursuit_milestones.find_one(
            {
                "pursuit_id": pursuit_id,
                "milestone_type": "release",
                "is_superseded": {"$ne": True}
            },
            sort=[("target_date", -1)]
        )

        alloc_end = allocation.get("target_end") if allocation else None
        milestone_end = latest_release.get("target_date") if latest_release else None

        if not alloc_end or not milestone_end:
            return ConsistencyResult(
                is_consistent=True,
                allocation_end=alloc_end,
                milestone_end=milestone_end,
                day_difference=0,
                coaching_prompt=None
            )

        alloc_date = self._parse_date(alloc_end)
        milestone_date = self._parse_date(milestone_end)

        if not alloc_date or not milestone_date:
            return ConsistencyResult(
                is_consistent=True,
                allocation_end=alloc_end,
                milestone_end=milestone_end,
                day_difference=0,
                coaching_prompt=None
            )

        day_diff = abs((alloc_date - milestone_date).days)

        if day_diff <= self.threshold_days:
            return ConsistencyResult(
                is_consistent=True,
                allocation_end=alloc_end,
                milestone_end=milestone_end,
                day_difference=day_diff,
                coaching_prompt=None
            )

        prompt = self._build_inconsistency_prompt(alloc_end, milestone_end, day_diff)

        return ConsistencyResult(
            is_consistent=False,
            allocation_end=alloc_end,
            milestone_end=milestone_end,
            day_difference=day_diff,
            coaching_prompt=prompt
        )

    async def resolve(self, pursuit_id: str, source_of_truth: str, db) -> None:
        """
        Resolve inconsistency by designating one date as the canonical end date.

        Args:
            pursuit_id: The pursuit to resolve
            source_of_truth: "allocation" | "milestone"
            db: Database connection

        If "milestone": update time_allocations.target_end to match the release milestone,
                       mark time_allocations.is_computed = True
        If "allocation": update the latest release milestone to match time_allocations.target_end,
                        create a new milestone version
        """
        now = datetime.now(timezone.utc).isoformat() + "Z"

        if source_of_truth == "milestone":
            latest_release = db.db.pursuit_milestones.find_one(
                {
                    "pursuit_id": pursuit_id,
                    "milestone_type": "release",
                    "is_superseded": {"$ne": True}
                },
                sort=[("target_date", -1)]
            )

            if latest_release:
                db.db.time_allocations.update_one(
                    {"pursuit_id": pursuit_id},
                    {"$set": {
                        "target_end": latest_release["target_date"],
                        "is_computed": True,
                        "computed_source_milestone_id": latest_release.get("milestone_id"),
                        "updated_at": now
                    }},
                    upsert=True
                )
                logger.info(
                    f"[ConsistencyValidator] Updated allocation to match milestone: "
                    f"{latest_release['target_date']}"
                )

        elif source_of_truth == "allocation":
            allocation = db.db.time_allocations.find_one({"pursuit_id": pursuit_id})

            if allocation and allocation.get("target_end"):
                latest_release = db.db.pursuit_milestones.find_one(
                    {
                        "pursuit_id": pursuit_id,
                        "milestone_type": "release",
                        "is_superseded": {"$ne": True}
                    },
                    sort=[("target_date", -1)]
                )

                if latest_release:
                    import uuid

                    # Supersede the old milestone with the allocation-aligned date
                    db.db.pursuit_milestones.update_one(
                        {"milestone_id": latest_release["milestone_id"]},
                        {"$set": {
                            "is_superseded": True,
                            "updated_at": now
                        }}
                    )

                    # Create new milestone version with allocation date
                    new_m = {
                        "milestone_id": str(uuid.uuid4()),
                        "pursuit_id": pursuit_id,
                        "title": latest_release.get("title", "Product Release"),
                        "description": latest_release.get("description"),
                        "target_date": allocation["target_end"],
                        "date_expression": latest_release.get("date_expression"),
                        "date_precision": "exact",
                        "milestone_type": "release",
                        "phase": latest_release.get("phase"),
                        "confidence": 1.0,
                        "source": "consistency_resolution",
                        "extracted_at": now,
                        "status": latest_release.get("status", "pending"),
                        "created_at": now,
                        "updated_at": now,
                        "milestone_version": latest_release.get("milestone_version", 1) + 1,
                        "supersedes_milestone_id": latest_release.get("milestone_id"),
                        "is_superseded": False,
                        "conflict_resolution_strategy": "user_chose_allocation",
                        "relative_resolution_method": None,
                        "requires_recalculation": False,
                        "recalculation_prompted_at": None
                    }

                    db.db.pursuit_milestones.insert_one(new_m)
                    logger.info(
                        f"[ConsistencyValidator] Created milestone v{new_m['milestone_version']} "
                        f"with allocation date: {allocation['target_end']}"
                    )

    def resolve_sync(self, pursuit_id: str, source_of_truth: str) -> None:
        """
        Synchronous version of resolve for non-async contexts.
        """
        now = datetime.now(timezone.utc).isoformat() + "Z"

        if source_of_truth == "milestone":
            latest_release = self.db.db.pursuit_milestones.find_one(
                {
                    "pursuit_id": pursuit_id,
                    "milestone_type": "release",
                    "is_superseded": {"$ne": True}
                },
                sort=[("target_date", -1)]
            )

            if latest_release:
                self.db.db.time_allocations.update_one(
                    {"pursuit_id": pursuit_id},
                    {"$set": {
                        "target_end": latest_release["target_date"],
                        "is_computed": True,
                        "computed_source_milestone_id": latest_release.get("milestone_id"),
                        "updated_at": now
                    }},
                    upsert=True
                )

        elif source_of_truth == "allocation":
            allocation = self.db.db.time_allocations.find_one({"pursuit_id": pursuit_id})

            if allocation and allocation.get("target_end"):
                latest_release = self.db.db.pursuit_milestones.find_one(
                    {
                        "pursuit_id": pursuit_id,
                        "milestone_type": "release",
                        "is_superseded": {"$ne": True}
                    },
                    sort=[("target_date", -1)]
                )

                if latest_release:
                    import uuid

                    self.db.db.pursuit_milestones.update_one(
                        {"milestone_id": latest_release["milestone_id"]},
                        {"$set": {
                            "is_superseded": True,
                            "updated_at": now
                        }}
                    )

                    new_m = {
                        "milestone_id": str(uuid.uuid4()),
                        "pursuit_id": pursuit_id,
                        "title": latest_release.get("title", "Product Release"),
                        "description": latest_release.get("description"),
                        "target_date": allocation["target_end"],
                        "date_expression": latest_release.get("date_expression"),
                        "date_precision": "exact",
                        "milestone_type": "release",
                        "phase": latest_release.get("phase"),
                        "confidence": 1.0,
                        "source": "consistency_resolution",
                        "extracted_at": now,
                        "status": latest_release.get("status", "pending"),
                        "created_at": now,
                        "updated_at": now,
                        "milestone_version": latest_release.get("milestone_version", 1) + 1,
                        "supersedes_milestone_id": latest_release.get("milestone_id"),
                        "is_superseded": False,
                        "conflict_resolution_strategy": "user_chose_allocation",
                        "relative_resolution_method": None,
                        "requires_recalculation": False,
                        "recalculation_prompted_at": None
                    }

                    self.db.db.pursuit_milestones.insert_one(new_m)

    def _build_inconsistency_prompt(self, alloc_end: str, milestone_end: str,
                                     day_diff: int) -> str:
        """Build a coaching prompt for the inconsistency."""
        # Parse dates for display
        alloc_display = self._format_date_for_display(alloc_end)
        milestone_display = self._format_date_for_display(milestone_end)

        weeks = round(day_diff / 7)
        direction = "later" if milestone_end > alloc_end else "earlier"

        return (
            f"I want to make sure your timeline is consistent. "
            f"Your project window is set to end {alloc_display}, "
            f"but your release milestone is targeting {milestone_display} - "
            f"about {weeks} week{'s' if weeks != 1 else ''} {direction}. "
            f"Which date should govern your timeline?"
        )

    def _format_date_for_display(self, date_str: str) -> str:
        """Format a date string for user-friendly display."""
        try:
            if "T" in date_str:
                date_str = date_str.split("T")[0]
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%B %d, %Y")
        except (ValueError, TypeError):
            return date_str

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            if "T" in date_str:
                date_str = date_str.split("T")[0]
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None
