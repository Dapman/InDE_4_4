"""
Re-Engagement Scheduler

Background task that periodically scans for innovators who are
eligible for async re-engagement and triggers message generation
and delivery.

Trigger conditions (ALL must be true):
  1. User has coaching_cadence opt-in enabled in preferences
  2. User has an active pursuit (not all terminal)
  3. Last session ended more than 48 hours ago
  4. Last session did NOT end with a bridge that was responded to
     (bridge_responded=False in last snapshot)
  5. Fewer than 2 re-engagement attempts have been sent in this gap
     (gap = period since last session, reset by a new session)
  6. No active session in last 24 hours (user is genuinely inactive)
  7. Pursuit has at least one artifact (not empty/just created)

Scheduling: Runs every 6 hours. Checks are lightweight — primarily
index-covered MongoDB queries.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)

# Configuration — these become configurable env vars in v4.3+
REENGAGEMENT_DELAY_HOURS = 48       # Minimum gap before first attempt
REENGAGEMENT_MAX_ATTEMPTS = 2       # Max attempts per inactivity gap
REENGAGEMENT_CHECK_INTERVAL_HOURS = 6  # How often the scheduler runs
ACTIVE_SESSION_WINDOW_HOURS = 24    # User is "active" if session in this window


class ReengagementScheduler:
    """
    Identifies eligible users and dispatches re-engagement messages.

    Usage (register as background task on app startup):
        scheduler = ReengagementScheduler(db, delivery_service, generator)
        # In your scheduler/background task framework:
        # await scheduler.run_check()
    """

    def __init__(self, db, delivery_service, generator):
        self.db = db
        self.delivery = delivery_service
        self.generator = generator

    def run_check(self) -> dict:
        """
        Main scheduler entry point. Scans for eligible users and
        dispatches re-engagement messages.

        Returns summary dict for telemetry/logging.
        Never raises — errors are logged but don't halt the check.
        """
        summary = {
            "checked_users": 0,
            "eligible_users": 0,
            "messages_sent": 0,
            "errors": 0,
            "run_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # Get raw database if wrapped
            raw_db = self.db.db if hasattr(self.db, 'db') else self.db

            eligible = self._find_eligible_pursuits(raw_db)
            summary["checked_users"] = len(eligible)

            for candidate in eligible:
                try:
                    sent = self._process_candidate(raw_db, candidate)
                    if sent:
                        summary["eligible_users"] += 1
                        summary["messages_sent"] += 1
                except Exception as e:
                    logger.error(
                        f"Re-engagement processing failed for "
                        f"user={candidate.get('user_id')}: {e}"
                    )
                    summary["errors"] += 1

        except Exception as e:
            logger.error(f"Re-engagement scheduler check failed: {e}")
            summary["errors"] += 1

        logger.info(f"Re-engagement check complete: {summary}")
        return summary

    def _find_eligible_pursuits(self, db) -> List[dict]:
        """
        Find user+pursuit pairs eligible for re-engagement.

        Uses MongoDB queries to efficiently find candidates.
        Returns a list of candidate dicts with user_id, pursuit_id,
        last_session_at, attempt_count.
        """
        cutoff_48h = datetime.now(timezone.utc) - timedelta(hours=REENGAGEMENT_DELAY_HOURS)
        cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=ACTIVE_SESSION_WINDOW_HOURS)

        # Find users who have coaching_cadence enabled
        # Accept both 'gentle' and 'active' as opt-in
        opted_in_users = list(db.users.find(
            {"preferences.coaching_cadence": {"$in": ["gentle", "active"]}},
            {"user_id": 1, "email": 1, "display_name": 1, "name": 1}
        ))

        candidates = []
        for user in opted_in_users:
            user_id = user.get("user_id")
            if not user_id:
                continue

            # Find active pursuits for this user
            active_pursuits = list(db.pursuits.find(
                {
                    "user_id": user_id,
                    "state": {"$nin": [
                        "TERMINATED.ABANDONED", "TERMINATED.BLOCKED",
                        "TERMINATED.INFEASIBLE", "TERMINATED.SUPERSEDED",
                        "TERMINATED.PIVOT", "COMPLETED.SUCCESSFUL",
                        "COMPLETED.PARTIAL"
                    ]}
                },
                {"pursuit_id": 1, "idea_summary": 1, "domain": 1, "primary_persona": 1,
                 "spark_text": 1, "title": 1}
            ))

            for pursuit in active_pursuits:
                pursuit_id = pursuit.get("pursuit_id")
                if not pursuit_id:
                    continue

                # Check: no recent activity in last 24h
                recent_turn = db.conversation_history.find_one(
                    {
                        "user_id": user_id,
                        "pursuit_id": pursuit_id,
                        "timestamp": {"$gte": cutoff_24h}
                    }
                )
                if recent_turn:
                    continue  # User is active — skip

                # Check: last turn ended > 48h ago
                last_turn = db.conversation_history.find_one(
                    {"user_id": user_id, "pursuit_id": pursuit_id},
                    sort=[("timestamp", -1)]
                )
                if not last_turn:
                    continue  # No conversation yet — skip
                last_session_at = last_turn.get("timestamp")
                if not last_session_at:
                    continue
                if hasattr(last_session_at, 'tzinfo') and last_session_at.tzinfo is None:
                    last_session_at = last_session_at.replace(tzinfo=timezone.utc)
                if last_session_at >= cutoff_48h:
                    continue  # Too recent — skip

                # Check: last snapshot bridge was not responded to
                last_snapshot = db.momentum_snapshots.find_one(
                    {"pursuit_id": pursuit_id},
                    sort=[("recorded_at", -1)]
                )
                if last_snapshot and last_snapshot.get("bridge_responded", False):
                    continue  # Bridge was responded to — skip

                # Check: attempt count for this gap
                gap_start = last_session_at
                attempt_count = db.reengagement_events.count_documents({
                    "user_id": user_id,
                    "pursuit_id": pursuit_id,
                    "sent_at": {"$gte": gap_start}
                })
                if attempt_count >= REENGAGEMENT_MAX_ATTEMPTS:
                    continue  # Max attempts reached — skip

                candidates.append({
                    "user_id":        user_id,
                    "user_email":     user.get("email"),
                    "user_name":      (user.get("display_name") or user.get("name") or "").split()[0] if (user.get("display_name") or user.get("name")) else "",
                    "pursuit_id":     pursuit_id,
                    "pursuit":        pursuit,
                    "last_session_at": last_session_at,
                    "attempt_number": attempt_count + 1,
                    "last_snapshot":  last_snapshot,
                })

        return candidates

    def _process_candidate(self, db, candidate: dict) -> bool:
        """
        Generate and dispatch a re-engagement message for one candidate.
        Records the attempt in reengagement_events.
        Returns True if message was sent.
        """
        user_id    = candidate["user_id"]
        pursuit_id = candidate["pursuit_id"]
        pursuit    = candidate["pursuit"]
        snapshot   = candidate.get("last_snapshot")

        # Build pursuit context for generator
        idea_summary = (
            pursuit.get("idea_summary") or
            pursuit.get("spark_text") or
            pursuit.get("title") or
            "your idea"
        )
        pursuit_context = {
            "idea_summary": idea_summary[:120],
            "idea_domain":  pursuit.get("domain") or "this space",
            "persona":      pursuit.get("primary_persona") or "the people you're helping",
        }

        momentum_tier    = snapshot.get("momentum_tier") if snapshot else None
        artifact_at_exit = snapshot.get("artifact_at_exit") if snapshot else None
        attempt_number   = candidate["attempt_number"]

        # Generate message
        message = self.generator.generate(
            pursuit_context=pursuit_context,
            momentum_tier=momentum_tier,
            artifact_at_exit=artifact_at_exit,
            attempt_number=attempt_number,
        )

        # Deliver
        delivered = self.delivery.send(
            to_email=candidate["user_email"],
            to_name=candidate.get("user_name", ""),
            subject=message["subject"],
            body=message["body"],
            metadata={
                "type":           "reengagement",
                "user_id":        user_id,
                "pursuit_id":     pursuit_id,
                "attempt_number": attempt_number,
                "momentum_tier":  momentum_tier,
            }
        )

        if delivered:
            # Record the attempt
            db.reengagement_events.insert_one({
                "user_id":        user_id,
                "pursuit_id":     pursuit_id,
                "sent_at":        datetime.now(timezone.utc),
                "attempt_number": attempt_number,
                "momentum_tier":  momentum_tier,
                "artifact_at_exit": artifact_at_exit,
                "subject":        message["subject"],
                "opened":         False,
                "session_resumed": False,
            })

        return delivered
