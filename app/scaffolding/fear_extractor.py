"""
InDE MVP v2.6 - Fear Extractor

Extracts fears from artifacts and cross-validates AI-predicted fears
with actual stakeholder concerns.

Key Features:
- Extract predicted fears from Fear artifacts
- Cross-validate with stakeholder feedback
- Identify validated fears, blind spots, and false alarms
- Update confidence scores based on validation
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re


class FearExtractor:
    """
    Extracts and validates fears using stakeholder feedback.
    """

    def __init__(self, database, llm_interface=None):
        """
        Initialize FearExtractor.

        Args:
            database: Database instance
            llm_interface: Optional LLM interface for semantic matching
        """
        self.db = database
        self.llm = llm_interface

    def get_predicted_fears(self, pursuit_id: str) -> List[Dict]:
        """
        Get predicted fears from the Fear artifact.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            List of fear dicts with id, description, category, confidence
        """
        # Get fear artifact
        artifacts = self.db.get_pursuit_artifacts(pursuit_id, "fears")

        if not artifacts:
            return []

        # Parse fears from artifact content
        fears = []
        artifact = artifacts[0]  # Most recent
        content = artifact.get("content", "")

        # Extract fears from structured artifact content
        # Look for sections like "## Capability Concerns", "## Market Concerns", etc.
        sections = {
            "capability": r"(?:Capability|Technical)\s*(?:Concerns?|Fears?)[:\s]*\n([^\n#]+(?:\n[^\n#]+)*)",
            "market": r"Market\s*(?:Concerns?|Fears?)[:\s]*\n([^\n#]+(?:\n[^\n#]+)*)",
            "resource": r"Resource\s*(?:Concerns?|Fears?)[:\s]*\n([^\n#]+(?:\n[^\n#]+)*)",
            "timing": r"Timing\s*(?:Concerns?|Fears?)[:\s]*\n([^\n#]+(?:\n[^\n#]+)*)",
            "competition": r"Competition\s*(?:Concerns?|Fears?)[:\s]*\n([^\n#]+(?:\n[^\n#]+)*)",
            "personal": r"Personal\s*(?:Concerns?|Fears?)[:\s]*\n([^\n#]+(?:\n[^\n#]+)*)"
        }

        fear_id = 0
        for category, pattern in sections.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                fear_text = match.group(1).strip()
                if fear_text and fear_text.lower() not in ["none", "n/a", "not specified"]:
                    fears.append({
                        "id": f"fear_{fear_id}",
                        "description": fear_text,
                        "category": category,
                        "confidence": 0.7,  # Default AI confidence
                        "source": "artifact"
                    })
                    fear_id += 1

        # Also check scaffolding state for fear elements
        state = self.db.get_scaffolding_state(pursuit_id)
        if state:
            fear_elements = state.get("fear_elements", {})
            for element_name, element_data in fear_elements.items():
                if element_data and element_data.get("text"):
                    fears.append({
                        "id": f"fear_{fear_id}",
                        "description": element_data["text"],
                        "category": element_name.replace("_fears", "").replace("_", " "),
                        "confidence": element_data.get("confidence", 0.6),
                        "source": "scaffolding"
                    })
                    fear_id += 1

        return fears

    def get_stakeholder_concerns(self, pursuit_id: str) -> List[str]:
        """
        Get all concerns raised by stakeholders.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            List of concern strings
        """
        feedback_list = self.db.get_stakeholder_feedback_by_pursuit(pursuit_id)
        concerns = []

        for feedback in feedback_list:
            fb_concerns = feedback.get("concerns", [])
            if isinstance(fb_concerns, list):
                concerns.extend(fb_concerns)
            elif fb_concerns:
                concerns.append(str(fb_concerns))

        return concerns

    def cross_validate_with_stakeholders(self, pursuit_id: str) -> Dict:
        """
        Compare predicted fears with actual stakeholder concerns.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            {
                "validated_fears": [...],    # Predicted AND confirmed
                "blind_spots": [...],        # Not predicted BUT stakeholders raised
                "false_alarms": [...],       # Predicted BUT no stakeholder concern
                "confidence_updates": {...}  # Adjusted fear confidence scores
                "validation_strength": float # Overall validation score
            }
        """
        predicted_fears = self.get_predicted_fears(pursuit_id)
        stakeholder_concerns = self.get_stakeholder_concerns(pursuit_id)

        if not predicted_fears and not stakeholder_concerns:
            return self._empty_validation()

        if not stakeholder_concerns:
            # No stakeholder feedback yet
            return {
                "validated_fears": [],
                "blind_spots": [],
                "false_alarms": [],  # Can't call them false alarms without feedback
                "unvalidated_fears": predicted_fears,
                "confidence_updates": {},
                "validation_strength": 0.0,
                "message": "No stakeholder feedback to validate against"
            }

        validated = []
        false_alarms = []
        matched_concerns = set()
        confidence_updates = {}

        # Match predicted fears to stakeholder concerns
        for fear in predicted_fears:
            fear_text = fear.get("description", "").lower()
            matches = self._find_matching_concerns(fear_text, stakeholder_concerns)

            if matches:
                validated.append({
                    "fear": fear,
                    "confirming_stakeholders": len(matches),
                    "evidence": matches[:3]  # First 3 examples
                })
                # Increase confidence for validated fears
                confidence_updates[fear["id"]] = min(1.0, fear.get("confidence", 0.5) + 0.2)
                matched_concerns.update(matches)
            else:
                false_alarms.append(fear)
                # Decrease confidence for unconfirmed fears
                confidence_updates[fear["id"]] = max(0.2, fear.get("confidence", 0.5) - 0.1)

        # Find blind spots (concerns not predicted)
        blind_spots = []
        predicted_text = " ".join([f.get("description", "") for f in predicted_fears])
        for concern in stakeholder_concerns:
            if concern not in matched_concerns:
                if not self._matches_predicted(concern, predicted_text):
                    blind_spots.append(concern)

        # Calculate validation strength
        total_predicted = len(predicted_fears)
        validation_strength = len(validated) / total_predicted if total_predicted > 0 else 0.0

        return {
            "validated_fears": validated,
            "blind_spots": list(set(blind_spots)),  # Deduplicate
            "false_alarms": false_alarms,
            "confidence_updates": confidence_updates,
            "validation_strength": validation_strength
        }

    def _find_matching_concerns(self, fear_text: str, concerns: List[str]) -> List[str]:
        """
        Find stakeholder concerns that match a predicted fear.

        Args:
            fear_text: Fear description text
            concerns: List of stakeholder concerns

        Returns:
            List of matching concerns
        """
        matches = []

        # Extract keywords from fear
        fear_keywords = self._extract_keywords(fear_text)

        for concern in concerns:
            concern_keywords = self._extract_keywords(concern)
            overlap = fear_keywords.intersection(concern_keywords)

            # Require at least 2 keyword overlap or significant substring match
            if len(overlap) >= 2:
                matches.append(concern)
            elif self._has_significant_overlap(fear_text, concern.lower()):
                matches.append(concern)

        return matches

    def _extract_keywords(self, text: str) -> set:
        """Extract significant keywords from text."""
        # Common stop words to ignore
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "can", "to", "of",
            "in", "for", "on", "with", "at", "by", "from", "as", "into",
            "about", "that", "this", "it", "we", "they", "i", "you", "our",
            "their", "my", "your", "what", "which", "who", "when", "where",
            "why", "how", "if", "then", "but", "and", "or", "not", "no"
        }

        words = set(re.findall(r'\b\w+\b', text.lower()))
        return words - stop_words

    def _has_significant_overlap(self, text1: str, text2: str) -> bool:
        """Check for significant substring overlap."""
        # Check if any word of 5+ characters appears in both
        words1 = [w for w in re.findall(r'\b\w{5,}\b', text1) if len(w) >= 5]
        for word in words1:
            if word in text2:
                return True
        return False

    def _matches_predicted(self, concern: str, predicted_text: str) -> bool:
        """Check if a concern was predicted."""
        concern_keywords = self._extract_keywords(concern)
        predicted_keywords = self._extract_keywords(predicted_text)

        overlap = concern_keywords.intersection(predicted_keywords)
        return len(overlap) >= 2

    def _empty_validation(self) -> Dict:
        """Return empty validation structure."""
        return {
            "validated_fears": [],
            "blind_spots": [],
            "false_alarms": [],
            "confidence_updates": {},
            "validation_strength": 0.0
        }

    def generate_validation_summary(self, pursuit_id: str) -> str:
        """
        Generate human-readable validation summary.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Summary text
        """
        validation = self.cross_validate_with_stakeholders(pursuit_id)

        if validation.get("message"):
            return validation["message"]

        if not validation["validated_fears"] and not validation["blind_spots"]:
            return ""

        lines = []

        if validation["validated_fears"]:
            count = len(validation["validated_fears"])
            lines.append(f"**{count} predicted fear(s) confirmed by stakeholders:**")
            for v in validation["validated_fears"][:3]:
                fear_desc = v["fear"]["description"][:80]
                mentions = v["confirming_stakeholders"]
                lines.append(f"- {fear_desc}... ({mentions} mention(s))")

        if validation["blind_spots"]:
            count = len(validation["blind_spots"])
            lines.append(f"\n**{count} stakeholder concern(s) not in your fear analysis:**")
            for bs in validation["blind_spots"][:3]:
                lines.append(f"- {bs[:80]}...")

        if validation["false_alarms"]:
            count = len(validation["false_alarms"])
            lines.append(f"\n**{count} predicted fear(s) not mentioned by stakeholders** (may be lower risk)")

        strength = validation["validation_strength"]
        if strength >= 0.7:
            lines.append(f"\nValidation strength: {strength*100:.0f}% (strong alignment)")
        elif strength >= 0.4:
            lines.append(f"\nValidation strength: {strength*100:.0f}% (moderate alignment)")
        else:
            lines.append(f"\nValidation strength: {strength*100:.0f}% (limited alignment)")

        return "\n".join(lines)

    def get_prioritized_fears(self, pursuit_id: str) -> List[Dict]:
        """
        Get fears prioritized by stakeholder validation.

        Fears confirmed by stakeholders are ranked higher.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            List of fears sorted by priority
        """
        validation = self.cross_validate_with_stakeholders(pursuit_id)
        prioritized = []

        # Validated fears first (high priority)
        for v in validation.get("validated_fears", []):
            fear = v["fear"].copy()
            fear["priority"] = "high"
            fear["validation"] = "confirmed"
            fear["stakeholder_mentions"] = v["confirming_stakeholders"]
            prioritized.append(fear)

        # Blind spots (high priority - unknown unknowns)
        for bs in validation.get("blind_spots", []):
            prioritized.append({
                "id": f"blindspot_{hash(bs) % 10000}",
                "description": bs,
                "category": "stakeholder_raised",
                "priority": "high",
                "validation": "stakeholder_only",
                "confidence": 0.9  # High confidence since stakeholder raised it
            })

        # False alarms last (lower priority)
        for fear in validation.get("false_alarms", []):
            fear_copy = fear.copy()
            fear_copy["priority"] = "medium"
            fear_copy["validation"] = "unconfirmed"
            prioritized.append(fear_copy)

        return prioritized

    def suggest_fear_mitigations(self, pursuit_id: str) -> List[Dict]:
        """
        Suggest mitigations for validated fears based on stakeholder context.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            List of mitigation suggestions
        """
        prioritized = self.get_prioritized_fears(pursuit_id)
        suggestions = []

        for fear in prioritized:
            if fear.get("priority") == "high":
                suggestions.append({
                    "fear": fear["description"][:100],
                    "priority": fear["priority"],
                    "suggestion": self._generate_mitigation_hint(fear)
                })

        return suggestions[:5]  # Top 5 suggestions

    def _generate_mitigation_hint(self, fear: Dict) -> str:
        """Generate basic mitigation hint for a fear."""
        category = fear.get("category", "").lower()
        validation = fear.get("validation", "")

        if validation == "stakeholder_only":
            return "Address this concern directly with stakeholders who raised it"

        if "technical" in category or "capability" in category:
            return "Consider proof-of-concept or technical spike to address"
        elif "market" in category:
            return "Validate with customer interviews or market research"
        elif "resource" in category:
            return "Identify champions who can help secure resources"
        elif "timing" in category:
            return "Create timeline with explicit milestones"
        elif "competition" in category:
            return "Clarify differentiation and unique value"
        else:
            return "Discuss mitigation approach with supportive stakeholders"
