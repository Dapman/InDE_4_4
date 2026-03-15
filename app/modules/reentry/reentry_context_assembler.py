"""
Re-Entry Context Assembler

Gathers everything the ReentryGenerator needs to produce a personalized
opening turn:
  - The user's profile and display name
  - The active pursuit's core idea summary, domain, and primary persona
  - The last momentum snapshot (exit tier, artifact at exit)
  - The gap duration since the last session
  - The last artifact active at exit (translated to innovator vocabulary)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Artifact key → natural language description for use in opening turns
# Aligns with v4.0 Display Label Registry artifact_panel category
ARTIFACT_NATURAL_LANGUAGE = {
    "vision":      "your innovation story",
    "fear":        "the risks we were protecting against",
    "validation":  "the assumptions you were testing",
    "coaching":    "our conversation",
    "retrospective": "what you've learned",
}


def _gap_duration_tier(gap_hours: float) -> str:
    """Classify gap into one of four duration tiers."""
    if gap_hours < 4:
        return "SHORT"
    elif gap_hours < 48:
        return "MEDIUM"
    elif gap_hours < 168:   # 7 days
        return "LONG"
    else:
        return "EXTENDED"


def _gap_natural_language(gap_hours: float) -> str:
    """Convert gap hours to natural, conversational time description."""
    if gap_hours < 1:
        return "a little while"
    elif gap_hours < 4:
        return "a few hours"
    elif gap_hours < 24:
        return "since yesterday"
    elif gap_hours < 36:
        return "overnight"
    elif gap_hours < 72:
        return "a couple of days"
    elif gap_hours < 120:
        return "a few days"
    elif gap_hours < 192:
        return "about a week"
    elif gap_hours < 336:
        return "a week or two"
    elif gap_hours < 720:
        return "a few weeks"
    elif gap_hours < 1440:
        return "about a month"
    else:
        return "quite a while"


class ReentryContextAssembler:
    """
    Assembles the full re-entry context dict required by ReentryGenerator.

    Usage:
        assembler = ReentryContextAssembler(db)
        context = assembler.assemble(user_id, pursuit_id)
        opening = reentry_generator.generate(context)
    """

    def __init__(self, db):
        self.db = db

    def assemble(self, user_id: str, pursuit_id: str) -> dict:
        """
        Assemble re-entry context from user, pursuit, and momentum data.

        Returns a context dict ready for ReentryGenerator.generate().
        Never raises — returns a minimal safe context on any error.
        """
        try:
            return self._assemble_internal(user_id, pursuit_id)
        except Exception as e:
            logger.error(f"Re-entry context assembly failed: {e}")
            return self._safe_fallback(user_id, pursuit_id)

    def _assemble_internal(self, user_id: str, pursuit_id: str) -> dict:
        # Get raw database if wrapped
        raw_db = self.db.db if hasattr(self.db, 'db') else self.db

        # ── User profile ─────────────────────────────────────────────
        user = raw_db.users.find_one({"user_id": user_id}) or {}
        display_name = user.get("display_name", user.get("name", ""))
        user_name = display_name.split()[0] if display_name else ""
        experience_level = user.get("experience_level", "novice")

        # ── Pursuit data ─────────────────────────────────────────────
        pursuit = raw_db.pursuits.find_one({"pursuit_id": pursuit_id}) or {}
        idea_summary = (
            pursuit.get("idea_summary") or
            pursuit.get("spark_text") or
            pursuit.get("title") or
            "your idea"
        )
        idea_domain = pursuit.get("domain") or "this space"
        persona = pursuit.get("primary_persona") or "the people you're trying to help"

        # ── Last session timestamp ────────────────────────────────────
        # Find the most recent conversation turn for this pursuit
        last_turn = raw_db.conversation_history.find_one(
            {"pursuit_id": pursuit_id, "user_id": user_id},
            sort=[("timestamp", -1)]
        )
        last_active_at = last_turn.get("timestamp") if last_turn else None

        # Calculate gap
        now = datetime.now(timezone.utc)
        if last_active_at:
            if hasattr(last_active_at, 'replace'):
                # Make timezone-aware if naive
                if last_active_at.tzinfo is None:
                    last_active_at = last_active_at.replace(tzinfo=timezone.utc)
            gap_hours = (now - last_active_at).total_seconds() / 3600
        else:
            gap_hours = 0.0

        gap_tier = _gap_duration_tier(gap_hours)
        gap_natural = _gap_natural_language(gap_hours)

        # ── Momentum snapshot ─────────────────────────────────────────
        snapshot = raw_db.momentum_snapshots.find_one(
            {"pursuit_id": pursuit_id},
            sort=[("recorded_at", -1)]
        )

        if snapshot:
            momentum_tier = snapshot.get("momentum_tier", "MEDIUM")
            artifact_at_exit = snapshot.get("artifact_at_exit")
            composite_score = snapshot.get("composite_score", 0.5)
            bridge_delivered = snapshot.get("bridge_delivered", False)
            bridge_responded = snapshot.get("bridge_responded", False)
        else:
            momentum_tier = None   # Triggers _no_snapshot library entry
            artifact_at_exit = None
            composite_score = None
            bridge_delivered = False
            bridge_responded = False

        # Translate artifact key to natural language
        last_artifact_natural = ARTIFACT_NATURAL_LANGUAGE.get(
            artifact_at_exit or "", "our last conversation"
        )

        return {
            # User
            "user_id":           user_id,
            "user_name":         user_name,
            "experience_level":  experience_level,
            # Pursuit
            "pursuit_id":        pursuit_id,
            "idea_summary":      idea_summary[:120],   # Truncate for prompt safety
            "idea_domain":       idea_domain,
            "persona":           persona,
            # Gap
            "gap_hours":         gap_hours,
            "gap_tier":          gap_tier,
            "gap_natural":       gap_natural,
            # Momentum
            "momentum_tier":     momentum_tier,        # None if no snapshot
            "composite_score":   composite_score,
            "artifact_at_exit":  artifact_at_exit,
            "last_artifact":     last_artifact_natural,
            "bridge_delivered":  bridge_delivered,
            "bridge_responded":  bridge_responded,
        }

    def _safe_fallback(self, user_id: str, pursuit_id: str) -> dict:
        """Minimal safe context — used when assembly fails."""
        return {
            "user_id":           user_id,
            "user_name":         "",
            "experience_level":  "novice",
            "pursuit_id":        pursuit_id,
            "idea_summary":      "your idea",
            "idea_domain":       "this space",
            "persona":           "the people you're trying to help",
            "gap_hours":         0.0,
            "gap_tier":          "SHORT",
            "gap_natural":       "a little while",
            "momentum_tier":     None,
            "composite_score":   None,
            "artifact_at_exit":  None,
            "last_artifact":     "our last conversation",
            "bridge_delivered":  False,
            "bridge_responded":  False,
        }
