"""
InDE v3.1 - Innovator Maturity Model
6-dimension behavioral scoring with 4-level progression.

Dimensions:
1. Discovery Competence (20%): Element extraction quality, time-to-vision
2. Validation Rigor (25%): RVE experiments, hypothesis testing
3. Reflective Practice (15%): Retrospective completion, learning capture
4. Velocity Management (15%): Phase timing adherence, progress consistency
5. Risk Awareness (15%): Fear identification, risk validation
6. Knowledge Contribution (10%): IKF contributions

Levels (never regress):
- NOVICE: Score < 40 OR pursuits < 2
- COMPETENT: Score >= 40 AND pursuits >= 2
- PROFICIENT: Score >= 55 AND pursuits >= 5
- EXPERT: Score >= 70 AND pursuits >= 9
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any
import logging

from core.config import (
    MATURITY_LEVELS,
    MATURITY_LEVEL_THRESHOLDS,
    MATURITY_DIMENSION_WEIGHTS,
    MATURITY_COACHING_STYLES
)

logger = logging.getLogger("inde.maturity")


class MaturityCalculator:
    """
    Calculates innovator maturity scores across 6 dimensions.
    """

    def __init__(self, db):
        """
        Initialize calculator with database access.

        Args:
            db: Database instance
        """
        self.db = db

    def calculate_scores(self, user_id: str) -> Dict[str, float]:
        """
        Calculate all maturity dimension scores for a user.

        Args:
            user_id: User's unique identifier

        Returns:
            Dict with dimension scores and composite score
        """
        scores = {
            "discovery_competence": self._calc_discovery_competence(user_id),
            "validation_rigor": self._calc_validation_rigor(user_id),
            "reflective_practice": self._calc_reflective_practice(user_id),
            "velocity_management": self._calc_velocity_management(user_id),
            "risk_awareness": self._calc_risk_awareness(user_id),
            "knowledge_contribution": self._calc_knowledge_contribution(user_id)
        }

        # Calculate weighted composite
        composite = sum(
            scores[dim] * weight
            for dim, weight in MATURITY_DIMENSION_WEIGHTS.items()
        )
        scores["composite"] = round(composite, 1)

        return scores

    def _calc_discovery_competence(self, user_id: str) -> float:
        """
        Calculate discovery competence (20% weight).

        Factors:
        - Average element extraction rate
        - Time from pursuit creation to vision artifact
        - Element confidence scores
        """
        pursuits = list(self.db.db.pursuits.find({"user_id": user_id}))
        if not pursuits:
            return 0.0

        total_score = 0.0
        count = 0

        for pursuit in pursuits:
            pursuit_id = pursuit["pursuit_id"]

            # Get scaffolding state
            state = self.db.get_scaffolding_state(pursuit_id)
            if not state:
                continue

            # Calculate element fill rate
            vision_elements = state.get("vision_elements", {})
            filled = sum(1 for v in vision_elements.values() if v is not None)
            fill_rate = filled / len(vision_elements) if vision_elements else 0

            # Calculate average confidence
            confidences = [
                v.get("confidence", 0) for v in vision_elements.values()
                if v is not None and isinstance(v, dict)
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            # Score this pursuit (fill rate weighted + confidence)
            pursuit_score = (fill_rate * 60) + (avg_confidence * 40)
            total_score += pursuit_score
            count += 1

        return round(total_score / count, 1) if count > 0 else 0.0

    def _calc_validation_rigor(self, user_id: str) -> float:
        """
        Calculate validation rigor (25% weight).

        Factors:
        - Number of RVE experiments designed
        - Experiment completion rate
        - Evidence package quality
        """
        # Get user's experiments
        experiments = list(self.db.db.validation_experiments.find({
            "user_id": user_id
        }))

        if not experiments:
            # Check if they have risk definitions at least
            risks = self.db.db.risk_definitions.count_documents({"user_id": user_id})
            if risks > 0:
                return min(risks * 10, 30)  # Partial credit for identifying risks
            return 0.0

        # Calculate metrics
        total = len(experiments)
        completed = sum(1 for e in experiments if e.get("status") == "COMPLETE")
        completion_rate = completed / total if total > 0 else 0

        # Check evidence quality
        evidence_packages = list(self.db.db.evidence_packages.find({"user_id": user_id}))
        high_quality = sum(
            1 for e in evidence_packages
            if e.get("confidence_level") == "HIGH"
        )
        quality_rate = high_quality / len(evidence_packages) if evidence_packages else 0

        # Combined score
        score = (
            min(total * 5, 30) +  # Credit for experiment count
            (completion_rate * 40) +  # Completion rate
            (quality_rate * 30)  # Evidence quality
        )

        return round(min(score, 100), 1)

    def _calc_reflective_practice(self, user_id: str) -> float:
        """
        Calculate reflective practice (15% weight).

        Factors:
        - Retrospective completion rate
        - Quality of retrospective responses
        - Learning pattern extractions
        """
        # Get completed retrospectives
        retros = list(self.db.db.retrospectives.find({"user_id": user_id}))

        if not retros:
            return 0.0

        # Calculate completion rate
        completed = sum(1 for r in retros if r.get("status") == "completed")
        completion_rate = completed / len(retros) if retros else 0

        # Check learning patterns extracted
        patterns = self.db.db.learning_patterns.count_documents({"user_id": user_id})

        # Score
        score = (
            (completion_rate * 60) +
            min(patterns * 10, 40)  # Credit for patterns
        )

        return round(min(score, 100), 1)

    def _calc_velocity_management(self, user_id: str) -> float:
        """
        Calculate velocity management (15% weight).

        Factors:
        - Phase timing adherence
        - Consistent engagement
        - Progress velocity
        """
        pursuits = list(self.db.db.pursuits.find({
            "user_id": user_id,
            "status": "active"
        }))

        if not pursuits:
            return 0.0

        total_score = 0.0
        count = 0

        for pursuit in pursuits:
            pursuit_id = pursuit["pursuit_id"]

            # Get velocity metrics
            velocity = self.db.db.velocity_metrics.find_one(
                {"pursuit_id": pursuit_id},
                sort=[("calculated_at", -1)]
            )

            if velocity:
                # Check if on track
                status = velocity.get("status", "on_track")
                if status == "ahead":
                    total_score += 100
                elif status in ["on_track", "on_track_high", "on_track_low"]:
                    total_score += 80
                elif status == "behind":
                    total_score += 50
                else:
                    total_score += 30
                count += 1

        # Also factor in engagement consistency
        # Check conversation frequency
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_messages = self.db.db.conversation_history.count_documents({
            "user_id": user_id,
            "timestamp": {"$gte": thirty_days_ago}
        })

        engagement_bonus = min(recent_messages * 2, 20)

        base_score = total_score / count if count > 0 else 50
        return round(min(base_score + engagement_bonus, 100), 1)

    def _calc_risk_awareness(self, user_id: str) -> float:
        """
        Calculate risk awareness (15% weight).

        Factors:
        - Fear identification rate
        - Fear-to-risk conversion
        - Risk validation attempts
        """
        pursuits = list(self.db.db.pursuits.find({"user_id": user_id}))
        if not pursuits:
            return 0.0

        total_fears = 0
        fears_with_risks = 0

        for pursuit in pursuits:
            pursuit_id = pursuit["pursuit_id"]

            # Get scaffolding state
            state = self.db.get_scaffolding_state(pursuit_id)
            if not state:
                continue

            # Count fears identified
            fear_elements = state.get("fear_elements", {})
            identified = sum(1 for v in fear_elements.values() if v is not None)
            total_fears += identified

            # Check for risk definitions
            risks = self.db.db.risk_definitions.count_documents({
                "pursuit_id": pursuit_id
            })
            if risks > 0 and identified > 0:
                fears_with_risks += min(risks, identified)

        if total_fears == 0:
            return 0.0

        # Fear identification score
        identification_score = min(total_fears * 8, 50)

        # Conversion rate
        conversion_rate = fears_with_risks / total_fears if total_fears > 0 else 0
        conversion_score = conversion_rate * 50

        return round(min(identification_score + conversion_score, 100), 1)

    def _calc_knowledge_contribution(self, user_id: str) -> float:
        """
        Calculate knowledge contribution (10% weight).

        Factors:
        - IKF contributions prepared
        - Contributions approved
        - Contribution quality
        """
        contributions = list(self.db.db.ikf_contributions.find({
            "user_id": user_id
        }))

        if not contributions:
            return 0.0

        total = len(contributions)
        approved = sum(1 for c in contributions if c.get("status") == "IKF_READY")
        reviewed = sum(1 for c in contributions if c.get("status") in ["REVIEWED", "IKF_READY"])

        # Score
        score = (
            min(total * 10, 30) +  # Credit for preparing
            min(reviewed * 15, 35) +  # Credit for review
            min(approved * 20, 35)  # Credit for approval
        )

        return round(min(score, 100), 1)

    def determine_level(self, scores: Dict[str, float], user_id: str) -> str:
        """
        Determine maturity level from scores.

        Args:
            scores: Dimension scores including composite
            user_id: User's unique identifier

        Returns:
            Maturity level string
        """
        user = self.db.db.users.find_one({"user_id": user_id})
        pursuit_count = user.get("pursuit_count", 0) if user else 0
        composite = scores.get("composite", 0)

        # Check thresholds in descending order
        for level in ["EXPERT", "PROFICIENT", "COMPETENT"]:
            threshold = MATURITY_LEVEL_THRESHOLDS[level]
            if (composite >= threshold["min_score"] and
                    pursuit_count >= threshold["min_pursuits"]):
                return level

        return "NOVICE"

    def get_coaching_style(self, level: str) -> Dict[str, Any]:
        """
        Get coaching style for a maturity level.

        Args:
            level: Maturity level

        Returns:
            Coaching style configuration
        """
        return MATURITY_COACHING_STYLES.get(level, MATURITY_COACHING_STYLES["NOVICE"])


def update_user_maturity(db, user_id: str) -> Dict[str, Any]:
    """
    Recalculate and update user's maturity scores and level.

    Args:
        db: Database instance
        user_id: User's unique identifier

    Returns:
        Updated maturity data
    """
    calculator = MaturityCalculator(db)

    # Calculate new scores
    scores = calculator.calculate_scores(user_id)

    # Determine new level
    new_level = calculator.determine_level(scores, user_id)

    # Get current level (levels never regress)
    user = db.db.users.find_one({"user_id": user_id})
    current_level = user.get("maturity_level", "NOVICE") if user else "NOVICE"

    current_idx = MATURITY_LEVELS.index(current_level)
    new_idx = MATURITY_LEVELS.index(new_level)
    final_level = MATURITY_LEVELS[max(current_idx, new_idx)]

    # Update user
    db.db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "maturity_scores": scores,
            "maturity_level": final_level
        }}
    )

    return {
        "scores": scores,
        "previous_level": current_level,
        "new_level": final_level,
        "level_changed": final_level != current_level
    }
