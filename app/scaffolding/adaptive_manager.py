"""
InDE MVP v2.5 - Adaptive Intervention Manager

Adjusts intervention frequency based on real-time user engagement signals.

Key Behaviors:
- High engagement (responding to interventions, longer messages):
  → Intervene more frequently (multiply cooldowns by 0.6)
- Low engagement (ignoring interventions, short messages):
  → Intervene less frequently (multiply cooldowns by 1.5)
- Medium engagement:
  → Use base cooldowns (no modification)

This prevents overwhelming disengaged users and capitalizes on
engaged users' receptiveness to coaching.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from config import ADAPTIVE_CONFIG, COOLDOWNS, DEMO_USER_ID


class AdaptiveInterventionManager:
    """
    Adjusts intervention timing based on user engagement signals.
    """

    def __init__(self, database):
        """
        Initialize AdaptiveInterventionManager.

        Args:
            database: Database instance for engagement metrics
        """
        self.db = database
        self.config = ADAPTIVE_CONFIG
        self._engagement_cache = {}  # user_id:pursuit_id -> (timestamp, score, tier)

        print(f"[AdaptiveManager] Initialized with config: {self.config}")

    def get_adaptive_cooldown(self, moment_type: str, user_id: str,
                               pursuit_id: str) -> int:
        """
        Get adjusted cooldown for a moment type based on engagement.

        Args:
            moment_type: e.g., "CRITICAL_GAP", "PATTERN_RELEVANT"
            user_id: User ID
            pursuit_id: Current pursuit ID

        Returns:
            Adjusted cooldown in minutes
        """
        if not self.config.get("enable_adaptive_cooldowns", True):
            return COOLDOWNS.get(moment_type, 30)

        base_cooldown = COOLDOWNS.get(moment_type, 30)

        # Get engagement tier
        tier = self.get_engagement_tier(user_id, pursuit_id)

        # Apply multiplier based on tier
        if tier == "high":
            multiplier = self.config.get("high_engagement_multiplier", 0.6)
        elif tier == "low":
            multiplier = self.config.get("low_engagement_multiplier", 1.5)
        else:  # medium
            multiplier = 1.0

        adjusted = int(base_cooldown * multiplier)

        # Ensure minimum cooldown of 5 minutes
        adjusted = max(5, adjusted)

        print(f"[AdaptiveManager] Cooldown for {moment_type}: {base_cooldown} -> {adjusted} (tier: {tier})")

        return adjusted

    def get_engagement_tier(self, user_id: str, pursuit_id: str) -> str:
        """
        Get user's current engagement tier.

        Returns: "high" | "medium" | "low"
        """
        # Check cache first
        cache_key = f"{user_id}:{pursuit_id}"
        cached = self._engagement_cache.get(cache_key)

        if cached:
            timestamp, _, tier = cached
            age = (datetime.now(timezone.utc) - timestamp).total_seconds()
            if age < 120:  # Cache for 2 minutes
                return tier

        # Get from database
        metrics = self.db.get_engagement_metrics(user_id, pursuit_id)

        if not metrics:
            return "medium"  # Default

        tier = metrics.get("engagement_tier", "medium")
        score = metrics.get("engagement_score", 0.5)

        # Update cache
        self._engagement_cache[cache_key] = (datetime.now(timezone.utc), score, tier)

        return tier

    def get_engagement_score(self, user_id: str, pursuit_id: str) -> float:
        """
        Get user's current engagement score (0.0 - 1.0).
        """
        metrics = self.db.get_engagement_metrics(user_id, pursuit_id)

        if not metrics:
            return 0.5  # Default neutral

        return metrics.get("engagement_score", 0.5)

    def record_user_message(self, user_id: str, pursuit_id: str,
                            message: str) -> None:
        """
        Record user message for engagement tracking.

        Args:
            user_id: User ID
            pursuit_id: Pursuit ID
            message: User's message text
        """
        if not self.config.get("enable_adaptive_cooldowns", True):
            return

        message_length = len(message)

        self.db.update_engagement_metrics(
            user_id=user_id,
            pursuit_id=pursuit_id,
            message_length=message_length
        )

        # Invalidate cache
        cache_key = f"{user_id}:{pursuit_id}"
        if cache_key in self._engagement_cache:
            del self._engagement_cache[cache_key]

    def record_intervention(self, user_id: str, pursuit_id: str,
                           intervention_type: str) -> None:
        """
        Record that an intervention was shown to the user.

        Args:
            user_id: User ID
            pursuit_id: Pursuit ID
            intervention_type: Type of intervention shown
        """
        if not self.config.get("enable_adaptive_cooldowns", True):
            return

        self.db.update_engagement_metrics(
            user_id=user_id,
            pursuit_id=pursuit_id,
            intervention_shown=True
        )

    def record_intervention_response(self, user_id: str, pursuit_id: str,
                                      responded: bool) -> None:
        """
        Record whether user responded to an intervention.

        "Responded" means the user's next message acknowledged or engaged
        with the intervention (not ignored it).

        Args:
            user_id: User ID
            pursuit_id: Pursuit ID
            responded: True if user responded to intervention
        """
        if not self.config.get("enable_adaptive_cooldowns", True):
            return

        if responded:
            self.db.update_engagement_metrics(
                user_id=user_id,
                pursuit_id=pursuit_id,
                intervention_responded=True
            )

        # Invalidate cache
        cache_key = f"{user_id}:{pursuit_id}"
        if cache_key in self._engagement_cache:
            del self._engagement_cache[cache_key]

    def record_artifact_interaction(self, user_id: str, pursuit_id: str) -> None:
        """
        Record that user interacted with an artifact.

        Artifact interactions (viewing, accepting generation, regenerating)
        are positive engagement signals.
        """
        if not self.config.get("enable_adaptive_cooldowns", True):
            return

        self.db.update_engagement_metrics(
            user_id=user_id,
            pursuit_id=pursuit_id,
            artifact_interaction=True
        )

        # Invalidate cache
        cache_key = f"{user_id}:{pursuit_id}"
        if cache_key in self._engagement_cache:
            del self._engagement_cache[cache_key]

    def should_intervene(self, user_id: str, pursuit_id: str,
                         moment_type: str,
                         last_intervention_time: Optional[datetime]) -> bool:
        """
        Check if cooldown has elapsed for this intervention type.

        Args:
            user_id: User ID
            pursuit_id: Pursuit ID
            moment_type: Type of intervention
            last_intervention_time: When this type was last triggered

        Returns:
            True if enough time has passed to intervene again
        """
        if last_intervention_time is None:
            return True

        # Ensure timezone-aware for comparison
        if last_intervention_time.tzinfo is None:
            last_intervention_time = last_intervention_time.replace(tzinfo=timezone.utc)

        adaptive_cooldown = self.get_adaptive_cooldown(
            moment_type, user_id, pursuit_id
        )

        elapsed = (datetime.now(timezone.utc) - last_intervention_time).total_seconds() / 60.0

        return elapsed >= adaptive_cooldown

    def get_engagement_summary(self, user_id: str, pursuit_id: str) -> Dict:
        """
        Get engagement summary for debugging/logging.

        Returns:
            {
                "engagement_score": 0.75,
                "engagement_tier": "high",
                "message_count": 15,
                "avg_message_length": 120,
                "intervention_response_rate": 0.80,
                "artifact_interactions": 3,
                "cooldown_multiplier": 0.6
            }
        """
        metrics = self.db.get_engagement_metrics(user_id, pursuit_id)

        if not metrics:
            return {
                "engagement_score": 0.5,
                "engagement_tier": "medium",
                "message_count": 0,
                "avg_message_length": 0,
                "intervention_response_rate": 0.5,
                "artifact_interactions": 0,
                "cooldown_multiplier": 1.0
            }

        tier = metrics.get("engagement_tier", "medium")

        if tier == "high":
            multiplier = self.config.get("high_engagement_multiplier", 0.6)
        elif tier == "low":
            multiplier = self.config.get("low_engagement_multiplier", 1.5)
        else:
            multiplier = 1.0

        inner_metrics = metrics.get("metrics", {})

        return {
            "engagement_score": metrics.get("engagement_score", 0.5),
            "engagement_tier": tier,
            "message_count": inner_metrics.get("message_count", 0),
            "avg_message_length": inner_metrics.get("avg_message_length", 0),
            "intervention_response_rate": inner_metrics.get("intervention_response_rate", 0.5),
            "artifact_interactions": inner_metrics.get("artifact_interaction_count", 0),
            "cooldown_multiplier": multiplier
        }

    def detect_response_to_intervention(self, message: str,
                                          last_intervention: Optional[Dict]) -> bool:
        """
        Heuristically detect if a message is responding to an intervention.

        Looks for:
        - Affirmative responses ("yes", "sure", "ok")
        - Direct answers to questions
        - Acknowledgment phrases
        - Message length > 50 chars (thoughtful response)

        Args:
            message: User's message
            last_intervention: Last intervention dict (with type, suggestion)

        Returns:
            True if message appears to respond to intervention
        """
        if not last_intervention:
            return False

        msg_lower = message.lower().strip()

        # Check for affirmative responses
        affirmatives = [
            "yes", "yeah", "yep", "sure", "ok", "okay",
            "that's right", "good question", "let me think",
            "i think", "well", "actually", "good point"
        ]

        if any(msg_lower.startswith(aff) for aff in affirmatives):
            return True

        # Check for longer thoughtful responses
        if len(message) > 50:
            return True

        # Check for topic continuation
        intervention_type = last_intervention.get("type", "")
        suggestion = last_intervention.get("suggestion", "").lower()

        # Extract keywords from suggestion
        if suggestion:
            words = suggestion.split()
            key_words = [w for w in words if len(w) > 4][:5]
            if any(kw in msg_lower for kw in key_words):
                return True

        return False

    def calculate_session_engagement(self, user_id: str, pursuit_id: str,
                                      window_hours: float = None) -> float:
        """
        Calculate engagement score over a time window.

        Uses rolling window to adapt to changing engagement levels
        within a session.

        Args:
            user_id: User ID
            pursuit_id: Pursuit ID
            window_hours: Hours to look back (default from config)

        Returns:
            Engagement score 0.0 - 1.0
        """
        if window_hours is None:
            window_hours = self.config.get("engagement_calculation_window_hours", 2)

        # Get conversation history within window
        history = self.db.get_conversation_history(pursuit_id, limit=50)

        if not history:
            return 0.5

        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        # Filter to window (ensure timezone-aware comparison)
        recent = []
        for turn in history:
            ts = turn.get("timestamp")
            if ts:
                if isinstance(ts, datetime) and ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts > cutoff:
                    recent.append(turn)

        if len(recent) < self.config.get("min_messages_for_engagement", 3):
            return 0.5  # Not enough data

        # Calculate engagement factors
        user_messages = [t for t in recent if t.get("role") == "user"]

        if not user_messages:
            return 0.3  # No user messages = low engagement

        # Factor 1: Message frequency (messages per hour)
        first_timestamp = recent[0]["timestamp"]
        if isinstance(first_timestamp, datetime) and first_timestamp.tzinfo is None:
            first_timestamp = first_timestamp.replace(tzinfo=timezone.utc)
        span = (datetime.now(timezone.utc) - first_timestamp).total_seconds() / 3600
        if span > 0:
            frequency = len(user_messages) / span
            freq_score = min(1.0, frequency / 10)  # Cap at 10/hour
        else:
            freq_score = 0.5

        # Factor 2: Average message length
        avg_length = sum(len(m.get("content", "")) for m in user_messages) / len(user_messages)
        length_score = min(1.0, avg_length / 200)  # Cap at 200 chars

        # Factor 3: Intervention responses (from metadata)
        interventions_shown = sum(
            1 for t in recent
            if t.get("metadata", {}).get("intervention_made")
        )
        responses = sum(
            1 for t in user_messages
            if t.get("metadata", {}).get("responded_to_intervention")
        )

        if interventions_shown > 0:
            response_score = responses / interventions_shown
        else:
            response_score = 0.5  # No interventions = neutral

        # Weighted combination
        engagement = (
            freq_score * 0.30 +
            length_score * 0.30 +
            response_score * 0.40
        )

        return round(engagement, 3)

    def clear_cache(self) -> None:
        """Clear engagement cache."""
        self._engagement_cache = {}
