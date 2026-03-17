"""
InDE v4.4.1 - Innovation Vitals Service
Aggregates per-user behavioral intelligence for beta testing analysis.

This module provides the backend aggregation for the Innovation Vitals
tab in the Admin Diagnostics panel. It reads from existing MongoDB
collections (users, pursuits, artifacts, coaching_sessions) and computes
engagement status classifications.

Zero writes. Read-only queries against existing data.

2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# =============================================================================
# ENGAGEMENT STATUS THRESHOLDS (hardcoded per spec)
# =============================================================================
NEW_USER_WINDOW_HOURS = 48
AT_RISK_DAYS = 7
DORMANT_DAYS = 14
ENGAGED_MIN_COACHING_SESSIONS = 3
ENGAGED_MIN_ARTIFACTS = 2


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class InnovatorVitalsRecord(BaseModel):
    """Per-user innovation vitals record."""
    user_id: str
    display_name: str
    email: str
    experience_level: Optional[str] = None  # None if not yet set
    pursuits_created: int
    highest_phase_reached: Optional[int] = None  # None if no pursuits
    artifacts_count: int
    coaching_sessions: int
    last_login: Optional[datetime] = None
    session_duration_last: Optional[int] = None  # minutes
    registered_at: Optional[datetime] = None
    status: str  # ENGAGED | EXPLORING | AT RISK | DORMANT | NEW


class InnovatorVitalsSummary(BaseModel):
    """Summary counts by status."""
    total: int
    engaged: int
    exploring: int
    at_risk: int
    dormant: int
    new: int


class InnovatorVitalsResponse(BaseModel):
    """Response envelope for innovator vitals endpoint."""
    users: List[InnovatorVitalsRecord]
    summary: InnovatorVitalsSummary
    generated_at: datetime
    warnings: List[str]


# =============================================================================
# INNOVATOR VITALS SERVICE
# =============================================================================

class InnovatorVitalsService:
    """
    Aggregates per-user innovation activity into a scannable view.

    Fetches data from:
    - users collection: identity, experience level, login times
    - pursuits collection: pursuit counts, highest phase
    - artifacts collection: artifact counts
    - coaching_sessions collection: session counts

    All queries use aggregation pipelines for efficiency (no N+1).
    """

    def __init__(self, db):
        """
        Initialize with database connection.

        Args:
            db: Database instance (with db.db attribute for raw MongoDB access)
        """
        self.db = db
        self.raw_db = db.db if hasattr(db, 'db') else db

    def get_all_vitals(self) -> InnovatorVitalsResponse:
        """
        Fetch innovation vitals for all users.

        Returns:
            InnovatorVitalsResponse with users array, summary, and any warnings
        """
        warnings = []
        now = datetime.now(timezone.utc)

        # 1. Fetch all users
        try:
            users_data = self._fetch_users()
        except Exception as e:
            logger.error(f"Failed to fetch users: {e}")
            warnings.append(f"Users fetch failed: {str(e)}")
            users_data = {}

        # 2. Aggregate pursuits by user
        try:
            pursuits_data = self._aggregate_pursuits()
        except Exception as e:
            logger.error(f"Failed to aggregate pursuits: {e}")
            warnings.append(f"Pursuits aggregation failed: {str(e)}")
            pursuits_data = {}

        # 3. Aggregate artifacts by user
        try:
            artifacts_data = self._aggregate_artifacts()
        except Exception as e:
            logger.error(f"Failed to aggregate artifacts: {e}")
            warnings.append(f"Artifacts aggregation failed: {str(e)}")
            artifacts_data = {}

        # 4. Aggregate coaching sessions by user
        try:
            sessions_data = self._aggregate_coaching_sessions()
        except Exception as e:
            logger.error(f"Failed to aggregate coaching sessions: {e}")
            warnings.append(f"Coaching sessions aggregation failed: {str(e)}")
            sessions_data = {}

        # 5. Join and compute status for each user
        records = []
        summary_counts = {
            "engaged": 0,
            "exploring": 0,
            "at_risk": 0,
            "dormant": 0,
            "new": 0
        }

        for user_id, user in users_data.items():
            pursuit_info = pursuits_data.get(user_id, {})
            artifact_count = artifacts_data.get(user_id, 0)
            session_count = sessions_data.get(user_id, 0)

            pursuits_created = pursuit_info.get("count", 0)
            highest_phase = pursuit_info.get("highest_phase")

            # Compute engagement status
            status = self._compute_status(
                pursuits_created=pursuits_created,
                artifacts_count=artifact_count,
                coaching_sessions=session_count,
                last_login=user.get("last_login"),
                registered_at=user.get("registered_at"),
                now=now
            )

            # Count by status
            status_key = status.lower().replace(" ", "_")
            if status_key in summary_counts:
                summary_counts[status_key] += 1

            # Build record
            record = InnovatorVitalsRecord(
                user_id=user_id,
                display_name=user.get("display_name") or user.get("name") or "Unknown",
                email=user.get("email") or "",
                experience_level=user.get("experience_level"),
                pursuits_created=pursuits_created,
                highest_phase_reached=highest_phase,
                artifacts_count=artifact_count,
                coaching_sessions=session_count,
                last_login=user.get("last_login"),
                session_duration_last=user.get("session_duration_last"),
                registered_at=user.get("registered_at"),
                status=status
            )
            records.append(record)

        # Sort by last_login descending (most recently active first)
        records.sort(
            key=lambda r: r.last_login or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )

        # Build response
        return InnovatorVitalsResponse(
            users=records,
            summary=InnovatorVitalsSummary(
                total=len(records),
                **summary_counts
            ),
            generated_at=now,
            warnings=warnings
        )

    def _fetch_users(self) -> dict:
        """
        Fetch all users (excluding system/legacy users).

        Returns:
            Dict mapping user_id to user data
        """
        users = {}

        cursor = self.raw_db.users.find(
            {"is_legacy": {"$ne": True}},
            {
                "user_id": 1,
                "name": 1,
                "display_name": 1,
                "email": 1,
                "experience_level": 1,
                "last_active": 1,
                "last_login": 1,
                "created_at": 1,
                "session_duration_last": 1
            }
        )

        for u in cursor:
            user_id = u.get("user_id")
            if not user_id:
                continue

            # Normalize datetime fields
            last_login = u.get("last_login") or u.get("last_active")
            if last_login and isinstance(last_login, str):
                try:
                    last_login = datetime.fromisoformat(last_login.replace("Z", "+00:00"))
                except:
                    last_login = None
            if last_login and last_login.tzinfo is None:
                last_login = last_login.replace(tzinfo=timezone.utc)

            registered_at = u.get("created_at")
            if registered_at and isinstance(registered_at, str):
                try:
                    registered_at = datetime.fromisoformat(registered_at.replace("Z", "+00:00"))
                except:
                    registered_at = None
            if registered_at and registered_at.tzinfo is None:
                registered_at = registered_at.replace(tzinfo=timezone.utc)

            users[user_id] = {
                "name": u.get("name"),
                "display_name": u.get("display_name"),
                "email": u.get("email"),
                "experience_level": u.get("experience_level"),
                "last_login": last_login,
                "registered_at": registered_at,
                "session_duration_last": u.get("session_duration_last")
            }

        return users

    def _aggregate_pursuits(self) -> dict:
        """
        Aggregate pursuit counts and highest phase per user.

        Returns:
            Dict mapping user_id to {count, highest_phase}
        """
        pipeline = [
            {"$group": {
                "_id": "$user_id",
                "count": {"$sum": 1},
                "highest_phase": {"$max": "$current_phase"}
            }}
        ]

        results = {}
        for doc in self.raw_db.pursuits.aggregate(pipeline):
            user_id = doc.get("_id")
            if user_id:
                # Convert phase string to number if needed
                phase = doc.get("highest_phase")
                phase_num = self._phase_to_number(phase) if phase else None

                results[user_id] = {
                    "count": doc.get("count", 0),
                    "highest_phase": phase_num
                }

        return results

    def _phase_to_number(self, phase) -> Optional[int]:
        """Convert phase identifier to number."""
        if isinstance(phase, int):
            return phase

        phase_map = {
            "VISION": 1, "vision": 1,
            "PITCH": 2, "pitch": 2,
            "DE_RISK": 3, "de_risk": 3, "derisk": 3,
            "BUILD": 4, "build": 4,
            "DEPLOY": 5, "deploy": 5
        }

        if isinstance(phase, str):
            return phase_map.get(phase.upper(), None)

        return None

    def _aggregate_artifacts(self) -> dict:
        """
        Aggregate artifact counts per user.

        Returns:
            Dict mapping user_id to artifact count
        """
        pipeline = [
            {"$group": {
                "_id": "$user_id",
                "count": {"$sum": 1}
            }}
        ]

        results = {}
        for doc in self.raw_db.artifacts.aggregate(pipeline):
            user_id = doc.get("_id")
            if user_id:
                results[user_id] = doc.get("count", 0)

        return results

    def _aggregate_coaching_sessions(self) -> dict:
        """
        Aggregate coaching session counts per user.

        Note: This counts from coaching_sessions or conversation_history
        depending on which collection exists.

        Returns:
            Dict mapping user_id to session count
        """
        # Try coaching_sessions collection first
        try:
            pipeline = [
                {"$group": {
                    "_id": "$user_id",
                    "count": {"$sum": 1}
                }}
            ]

            results = {}
            for doc in self.raw_db.coaching_sessions.aggregate(pipeline):
                user_id = doc.get("_id")
                if user_id:
                    results[user_id] = doc.get("count", 0)

            if results:
                return results
        except Exception:
            pass

        # Fallback: count unique sessions from conversation_history
        try:
            pipeline = [
                {"$group": {
                    "_id": {"user_id": "$user_id", "session_id": "$session_id"}
                }},
                {"$group": {
                    "_id": "$_id.user_id",
                    "count": {"$sum": 1}
                }}
            ]

            results = {}
            for doc in self.raw_db.conversation_history.aggregate(pipeline):
                user_id = doc.get("_id")
                if user_id:
                    results[user_id] = doc.get("count", 0)

            return results
        except Exception:
            pass

        return {}

    def _compute_status(
        self,
        pursuits_created: int,
        artifacts_count: int,
        coaching_sessions: int,
        last_login: Optional[datetime],
        registered_at: Optional[datetime],
        now: datetime
    ) -> str:
        """
        Compute engagement status classification.

        Evaluation order (per spec):
        1. NEW: registered_at within 48 hours (overrides all)
        2. AT RISK: last_login > 7 days AND pursuits >= 1
        3. ENGAGED: pursuits >= 1 AND sessions >= 3 AND artifacts >= 2
        4. EXPLORING: pursuits >= 1 AND (sessions < 3 OR artifacts < 2)
        5. DORMANT: pursuits = 0 OR last_login > 14 days

        Args:
            pursuits_created: Number of pursuits created
            artifacts_count: Number of artifacts created
            coaching_sessions: Number of coaching sessions
            last_login: Last login timestamp
            registered_at: Registration timestamp
            now: Current time for comparison

        Returns:
            Status string: ENGAGED, EXPLORING, AT RISK, DORMANT, or NEW
        """
        # 1. NEW: Check first (overrides all)
        if registered_at:
            hours_since_registration = (now - registered_at).total_seconds() / 3600
            if hours_since_registration <= NEW_USER_WINDOW_HOURS:
                return "NEW"

        # Calculate days since last login
        days_since_login = None
        if last_login:
            days_since_login = (now - last_login).days

        # 2. DORMANT (long absence): Check > 14 days first
        # This takes priority because very long absence = truly inactive
        if days_since_login is not None and days_since_login > DORMANT_DAYS:
            return "DORMANT"

        # 3. DORMANT (no pursuits): pursuits = 0 means never engaged
        if pursuits_created == 0:
            return "DORMANT"

        # 4. AT RISK: 7-14 day window with pursuits created
        # User has pursuits but is going quiet (potential churn)
        if days_since_login is not None and days_since_login > AT_RISK_DAYS:
            if pursuits_created >= 1:
                return "AT RISK"

        # 5. ENGAGED: pursuits >= 1 AND sessions >= 3 AND artifacts >= 2
        if (pursuits_created >= 1 and
            coaching_sessions >= ENGAGED_MIN_COACHING_SESSIONS and
            artifacts_count >= ENGAGED_MIN_ARTIFACTS):
            return "ENGAGED"

        # 6. EXPLORING: pursuits >= 1 AND (sessions < 3 OR artifacts < 2)
        if pursuits_created >= 1:
            return "EXPLORING"

        # Fallback to DORMANT
        return "DORMANT"


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTION
# =============================================================================

def get_innovator_vitals(db) -> InnovatorVitalsResponse:
    """
    Convenience function to get innovator vitals.

    Args:
        db: Database instance

    Returns:
        InnovatorVitalsResponse
    """
    service = InnovatorVitalsService(db)
    return service.get_all_vitals()
