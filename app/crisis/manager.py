"""
InDE v3.1 - Crisis Mode Manager
7 crisis types with 5-phase intervention protocol.

Crisis Types:
1. COMPETITOR_THREAT: Market competitive pressure
2. RESOURCE_EXHAUSTION: Running out of time/money/people
3. HYPOTHESIS_INVALIDATION: Core assumption disproven
4. SPONSOR_LOSS: Key stakeholder withdrawn
5. VELOCITY_COLLAPSE: Progress stalled
6. PATTERN_MATCH: Historical failure pattern detected
7. MANUAL: User-initiated crisis mode

Intervention Phases:
1. IMMEDIATE_TRIAGE (0-5 min): Assess scope, stabilize
2. DIAGNOSTIC_DEEP_DIVE (5-15 min): Understand root cause
3. OPTIONS_GENERATION (15-30 min): Generate response options
4. DECISION_SUPPORT (30-45 min): Help select action
5. POST_CRISIS_MONITORING (45-60 min): Track resolution
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uuid
import logging

from core.config import (
    CRISIS_TYPES,
    CRISIS_PHASES,
    CRISIS_URGENCY_LEVELS
)

logger = logging.getLogger("inde.crisis")


class CrisisManager:
    """
    Manages crisis mode sessions and interventions.
    """

    def __init__(self, db):
        """
        Initialize crisis manager with database access.

        Args:
            db: Database instance
        """
        self.db = db

    def detect_crisis(self, pursuit_id: str, user_id: str) -> Optional[Dict]:
        """
        Check if a pursuit should trigger crisis mode.

        Args:
            pursuit_id: Pursuit to check
            user_id: User who owns the pursuit

        Returns:
            Crisis detection result or None if no crisis detected
        """
        # Check for existing active crisis
        existing = self.db.db.crisis_sessions.find_one({
            "pursuit_id": pursuit_id,
            "resolved_at": None
        })
        if existing:
            return None  # Already in crisis mode

        # Get pursuit health
        health = self.db.db.health_scores.find_one(
            {"pursuit_id": pursuit_id},
            sort=[("calculated_at", -1)]
        )

        if health:
            # Auto-trigger on critical health
            if health.get("zone") == "CRITICAL":
                return {
                    "should_trigger": True,
                    "crisis_type": "VELOCITY_COLLAPSE",
                    "reason": f"Pursuit health critical ({health.get('score', 0)}/100)",
                    "urgency": "CRITICAL"
                }

            # Check for velocity collapse
            if health.get("components", {}).get("velocity_health", 100) < 20:
                return {
                    "should_trigger": True,
                    "crisis_type": "VELOCITY_COLLAPSE",
                    "reason": "Velocity has collapsed below sustainable level",
                    "urgency": "URGENT"
                }

        # Check for pattern-matched crisis
        pattern_crisis = self._check_pattern_match(pursuit_id)
        if pattern_crisis:
            return pattern_crisis

        return None

    def _check_pattern_match(self, pursuit_id: str) -> Optional[Dict]:
        """Check if pursuit matches known failure patterns."""
        # Check temporal antipatterns
        antipatterns = [
            "VISION_STALL",
            "VELOCITY_COLLAPSE",
            "PHASE_SKIP",
            "BUFFER_EXHAUSTION",
            "ELEMENT_DROUGHT"
        ]

        # Get pursuit's temporal events
        pursuit = self.db.db.pursuits.find_one({"pursuit_id": pursuit_id})
        if not pursuit:
            return None

        created_at = pursuit.get("created_at")
        if not created_at:
            return None

        # Check for element drought (no elements in 10+ days)
        ten_days_ago = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0
        )
        recent_elements = self.db.db.temporal_events.count_documents({
            "pursuit_id": pursuit_id,
            "event_type": "ELEMENT_CAPTURED",
            "timestamp": {"$gte": ten_days_ago}
        })

        if recent_elements == 0:
            # Check total pursuit age
            age_days = (datetime.now(timezone.utc) - created_at).days
            if age_days > 14:  # Only trigger if pursuit is old enough
                return {
                    "should_trigger": True,
                    "crisis_type": "PATTERN_MATCH",
                    "reason": "ELEMENT_DROUGHT: No new elements captured in 10+ days",
                    "urgency": "STANDARD"
                }

        return None

    def trigger_crisis(
        self,
        pursuit_id: str,
        user_id: str,
        crisis_type: str,
        trigger_reason: Optional[str] = None
    ) -> Dict:
        """
        Trigger crisis mode for a pursuit.

        Args:
            pursuit_id: Pursuit entering crisis mode
            user_id: User who owns the pursuit
            crisis_type: Type of crisis
            trigger_reason: Optional reason for triggering

        Returns:
            Created crisis session
        """
        if crisis_type not in CRISIS_TYPES:
            raise ValueError(f"Invalid crisis type: {crisis_type}")

        crisis_config = CRISIS_TYPES[crisis_type]
        session_id = str(uuid.uuid4())

        session = {
            "session_id": session_id,
            "pursuit_id": pursuit_id,
            "user_id": user_id,
            "crisis_type": crisis_type,
            "urgency": crisis_config["default_urgency"],
            "intervention_depth": crisis_config["intervention_depth"],
            "current_phase": CRISIS_PHASES[0],
            "phase_history": [{
                "phase": CRISIS_PHASES[0],
                "entered_at": datetime.now(timezone.utc).isoformat(),
                "notes": []
            }],
            "trigger_reason": trigger_reason,
            "started_at": datetime.now(timezone.utc),
            "resolved_at": None,
            "resolution": None,
            "actions_taken": [],
            "insights_captured": []
        }

        self.db.db.crisis_sessions.insert_one(session)

        # Update pursuit
        self.db.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {
                "$push": {"crisis_history": {
                    "session_id": session_id,
                    "crisis_type": crisis_type,
                    "started_at": datetime.now(timezone.utc).isoformat()
                }},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )

        logger.info(f"Crisis triggered: {crisis_type} for pursuit {pursuit_id}")

        return session

    def advance_phase(self, session_id: str, notes: Optional[str] = None) -> Dict:
        """
        Advance crisis session to next phase.

        Args:
            session_id: Crisis session ID
            notes: Optional notes for current phase

        Returns:
            Updated session
        """
        session = self.db.db.crisis_sessions.find_one({"session_id": session_id})
        if not session:
            raise ValueError("Crisis session not found")

        if session.get("resolved_at"):
            raise ValueError("Crisis session already resolved")

        current_idx = CRISIS_PHASES.index(session["current_phase"])
        if current_idx >= len(CRISIS_PHASES) - 1:
            raise ValueError("Already at final phase")

        next_phase = CRISIS_PHASES[current_idx + 1]

        # Update session
        update = {
            "current_phase": next_phase,
            "phase_history": session["phase_history"] + [{
                "phase": next_phase,
                "entered_at": datetime.now(timezone.utc).isoformat(),
                "notes": []
            }]
        }

        if notes:
            # Add notes to current phase
            update["phase_history"][-2]["notes"].append({
                "content": notes,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        self.db.db.crisis_sessions.update_one(
            {"session_id": session_id},
            {"$set": update}
        )

        return {
            "session_id": session_id,
            "previous_phase": session["current_phase"],
            "current_phase": next_phase
        }

    def resolve_crisis(
        self,
        session_id: str,
        resolution: str,
        insights: Optional[List[str]] = None
    ) -> Dict:
        """
        Resolve a crisis session.

        Args:
            session_id: Crisis session ID
            resolution: Resolution description
            insights: Optional insights captured

        Returns:
            Resolution summary
        """
        session = self.db.db.crisis_sessions.find_one({"session_id": session_id})
        if not session:
            raise ValueError("Crisis session not found")

        if session.get("resolved_at"):
            raise ValueError("Crisis session already resolved")

        resolved_at = datetime.now(timezone.utc)

        self.db.db.crisis_sessions.update_one(
            {"session_id": session_id},
            {"$set": {
                "resolved_at": resolved_at,
                "resolution": resolution,
                "insights_captured": insights or []
            }}
        )

        # Calculate crisis duration
        started_at = session["started_at"]
        duration_minutes = (resolved_at - started_at).total_seconds() / 60

        logger.info(
            f"Crisis resolved: {session_id} after {duration_minutes:.1f} minutes"
        )

        return {
            "session_id": session_id,
            "pursuit_id": session["pursuit_id"],
            "crisis_type": session["crisis_type"],
            "resolution": resolution,
            "duration_minutes": duration_minutes,
            "phases_completed": len(session.get("phase_history", [])),
            "insights_captured": insights or []
        }

    def get_phase_guidance(self, crisis_type: str, phase: str) -> Dict:
        """
        Get coaching guidance for current crisis phase.

        Args:
            crisis_type: Type of crisis
            phase: Current phase

        Returns:
            Phase guidance including questions and actions
        """
        guidance = {
            "IMMEDIATE_TRIAGE": {
                "duration_minutes": 5,
                "objective": "Stabilize and assess scope",
                "questions": [
                    "What triggered this situation?",
                    "Who else needs to know right now?",
                    "What's the immediate impact?"
                ],
                "actions": [
                    "Document current state",
                    "Identify key stakeholders to notify",
                    "Pause any automated processes"
                ]
            },
            "DIAGNOSTIC_DEEP_DIVE": {
                "duration_minutes": 10,
                "objective": "Understand root cause",
                "questions": [
                    "What assumptions led us here?",
                    "Were there warning signs we missed?",
                    "What's the underlying issue vs. the symptom?"
                ],
                "actions": [
                    "Review recent decisions",
                    "Analyze relevant data",
                    "Map cause-effect relationships"
                ]
            },
            "OPTIONS_GENERATION": {
                "duration_minutes": 15,
                "objective": "Generate response options",
                "questions": [
                    "What are our options?",
                    "What's the fastest path forward?",
                    "What would we do with unlimited resources?"
                ],
                "actions": [
                    "Brainstorm at least 3 options",
                    "Evaluate feasibility of each",
                    "Consider second-order effects"
                ]
            },
            "DECISION_SUPPORT": {
                "duration_minutes": 15,
                "objective": "Select and plan action",
                "questions": [
                    "Which option best addresses root cause?",
                    "What resources do we need?",
                    "How will we know if it's working?"
                ],
                "actions": [
                    "Select primary option",
                    "Define success criteria",
                    "Create action plan with owners"
                ]
            },
            "POST_CRISIS_MONITORING": {
                "duration_minutes": 15,
                "objective": "Track resolution and learn",
                "questions": [
                    "Is the action plan working?",
                    "What would we do differently next time?",
                    "What should we add to our early warning system?"
                ],
                "actions": [
                    "Monitor resolution progress",
                    "Capture lessons learned",
                    "Update risk definitions if needed"
                ]
            }
        }

        return guidance.get(phase, {
            "objective": "Unknown phase",
            "questions": [],
            "actions": []
        })
