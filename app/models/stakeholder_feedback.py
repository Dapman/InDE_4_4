"""
InDE MVP v2.6 - Stakeholder Feedback Model

Lightweight, flexible data structure for capturing stakeholder feedback.
Supports multiple input formats (quick form, batch, conversational, freeform).

Only name, role, and support_level are required.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import uuid

# Import support levels from config
try:
    from config import SUPPORT_LEVELS
except ImportError:
    SUPPORT_LEVELS = ["supportive", "conditional", "neutral", "opposed", "unclear"]


class StakeholderFeedback:
    """
    Flexible, lightweight stakeholder feedback record.
    Only name, role, support_level are required.
    """

    def __init__(self, pursuit_id: str, stakeholder_name: str,
                 role: str, support_level: str, **kwargs):
        """
        Initialize a stakeholder feedback record.

        Args:
            pursuit_id: ID of the pursuit this feedback relates to
            stakeholder_name: Name of the stakeholder
            role: Role/title of the stakeholder
            support_level: One of SUPPORT_LEVELS
            **kwargs: Optional fields (organization, date, concerns, etc.)
        """
        self.feedback_id = kwargs.get('feedback_id', str(uuid.uuid4()))
        self.pursuit_id = pursuit_id
        self.stakeholder_name = stakeholder_name
        self.role = role
        self.support_level = support_level.lower() if support_level else "unclear"

        # Optional fields
        self.organization = kwargs.get('organization', '')
        self.date = kwargs.get('date', datetime.now(timezone.utc))
        self.concerns = kwargs.get('concerns', [])
        self.resources_offered = kwargs.get('resources_offered', '')
        self.conditions = kwargs.get('conditions', '')
        self.notes = kwargs.get('notes', '')
        self.capture_method = kwargs.get('capture_method', 'quick_form')
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
        self.updated_at = kwargs.get('updated_at', datetime.now(timezone.utc))

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate required fields only. Non-blocking.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if not self.stakeholder_name or len(self.stakeholder_name.strip()) < 2:
            errors.append("Stakeholder name required (minimum 2 characters)")

        if not self.role or len(self.role.strip()) < 1:
            errors.append("Role/title required")

        if self.support_level not in SUPPORT_LEVELS:
            errors.append(f"Support level must be one of: {', '.join(SUPPORT_LEVELS)}")

        return (len(errors) == 0, errors)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to database document."""
        return {
            "feedback_id": self.feedback_id,
            "pursuit_id": self.pursuit_id,
            "stakeholder_name": self.stakeholder_name,
            "role": self.role,
            "organization": self.organization,
            "date": self.date,
            "support_level": self.support_level,
            "concerns": self.concerns if isinstance(self.concerns, list) else [self.concerns] if self.concerns else [],
            "resources_offered": self.resources_offered,
            "conditions": self.conditions,
            "notes": self.notes,
            "capture_method": self.capture_method,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'StakeholderFeedback':
        """Create StakeholderFeedback from database document."""
        return cls(
            pursuit_id=data.get('pursuit_id', ''),
            stakeholder_name=data.get('stakeholder_name', ''),
            role=data.get('role', ''),
            support_level=data.get('support_level', 'unclear'),
            feedback_id=data.get('feedback_id', str(uuid.uuid4())),
            organization=data.get('organization', ''),
            date=data.get('date', datetime.now(timezone.utc)),
            concerns=data.get('concerns', []),
            resources_offered=data.get('resources_offered', ''),
            conditions=data.get('conditions', ''),
            notes=data.get('notes', ''),
            capture_method=data.get('capture_method', 'quick_form'),
            created_at=data.get('created_at', datetime.now(timezone.utc)),
            updated_at=data.get('updated_at', datetime.now(timezone.utc))
        )

    @classmethod
    def from_conversational(cls, pursuit_id: str, description: str,
                            llm_interface=None) -> Optional['StakeholderFeedback']:
        """
        Create StakeholderFeedback by extracting details from a conversational description.

        Args:
            pursuit_id: Pursuit ID
            description: Natural language description of stakeholder interaction
            llm_interface: Optional LLM interface for extraction

        Returns:
            StakeholderFeedback or None if extraction failed
        """
        # Simple keyword-based extraction as fallback
        # In production, this would use the LLM for better extraction

        # Try to extract name (look for patterns like "talked to X" or "met with X")
        import re

        name_patterns = [
            r"talked to (\w+ \w+)",
            r"met with (\w+ \w+)",
            r"spoke with (\w+ \w+)",
            r"discussed with (\w+ \w+)",
            r"(\w+ \w+) (said|told|mentioned|thinks)"
        ]

        stakeholder_name = ""
        for pattern in name_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                stakeholder_name = match.group(1).strip()
                break

        if not stakeholder_name:
            return None

        # Try to extract role
        role_patterns = [
            r"(CTO|CEO|CFO|COO|VP|Director|Manager|Lead|Head of \w+)",
            r"our (\w+)",
            r"the (\w+)"
        ]

        role = ""
        for pattern in role_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                role = match.group(1).strip()
                break

        if not role:
            role = "Unknown"

        # Extract support level
        support_level = "unclear"
        if any(word in description.lower() for word in ["supportive", "supports", "excited", "enthusiastic", "loves"]):
            support_level = "supportive"
        elif any(word in description.lower() for word in ["conditional", "if ", "only if", "depends", "contingent"]):
            support_level = "conditional"
        elif any(word in description.lower() for word in ["neutral", "undecided", "on the fence"]):
            support_level = "neutral"
        elif any(word in description.lower() for word in ["opposed", "against", "doesn't support", "negative"]):
            support_level = "opposed"

        # Extract concerns
        concerns = []
        concern_patterns = [
            r"worried about (\w+(?:\s+\w+){0,3})",
            r"concerned about (\w+(?:\s+\w+){0,3})",
            r"concern[s]?[:]? (\w+(?:\s+\w+){0,3})"
        ]
        for pattern in concern_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            concerns.extend(matches)

        return cls(
            pursuit_id=pursuit_id,
            stakeholder_name=stakeholder_name,
            role=role,
            support_level=support_level,
            concerns=concerns,
            capture_method='conversational',
            notes=description
        )


class StakeholderFeedbackRepository:
    """Database operations for stakeholder feedback."""

    def __init__(self, database):
        """
        Initialize repository.

        Args:
            database: Database instance with stakeholder_feedback collection
        """
        self.db = database

    def save(self, feedback: StakeholderFeedback) -> str:
        """
        Save feedback record.

        Args:
            feedback: StakeholderFeedback instance

        Returns:
            feedback_id of saved record
        """
        doc = feedback.to_dict()
        self.db.db.stakeholder_feedback.insert_one(doc)
        return feedback.feedback_id

    def get_by_pursuit(self, pursuit_id: str) -> List[Dict]:
        """
        Get all feedback for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            List of feedback documents
        """
        return list(self.db.db.stakeholder_feedback.find({"pursuit_id": pursuit_id}))

    def get_by_id(self, feedback_id: str) -> Optional[Dict]:
        """
        Get feedback by ID.

        Args:
            feedback_id: Feedback ID

        Returns:
            Feedback document or None
        """
        return self.db.db.stakeholder_feedback.find_one({"feedback_id": feedback_id})

    def get_by_stakeholder(self, pursuit_id: str, stakeholder_name: str) -> Optional[Dict]:
        """
        Get feedback for specific stakeholder in pursuit.

        Args:
            pursuit_id: Pursuit ID
            stakeholder_name: Stakeholder name

        Returns:
            Feedback document or None
        """
        return self.db.db.stakeholder_feedback.find_one({
            "pursuit_id": pursuit_id,
            "stakeholder_name": stakeholder_name
        })

    def update(self, feedback_id: str, updates: Dict) -> bool:
        """
        Update existing feedback.

        Args:
            feedback_id: Feedback ID
            updates: Dict of fields to update

        Returns:
            True if update succeeded
        """
        updates["updated_at"] = datetime.now(timezone.utc)
        result = self.db.db.stakeholder_feedback.update_one(
            {"feedback_id": feedback_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    def delete(self, feedback_id: str) -> bool:
        """
        Delete feedback record.

        Args:
            feedback_id: Feedback ID

        Returns:
            True if delete succeeded
        """
        # For in-memory DB, we need to manually remove
        feedback_list = list(self.db.db.stakeholder_feedback.find({"feedback_id": feedback_id}))
        if feedback_list:
            # Use a workaround for in-memory deletion
            all_docs = list(self.db.db.stakeholder_feedback.find({}))
            self.db.db.stakeholder_feedback._documents = [
                d for d in all_docs if d.get("feedback_id") != feedback_id
            ]
            return True
        return False

    def count_by_pursuit(self, pursuit_id: str) -> int:
        """
        Count feedback entries for pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Number of feedback entries
        """
        return len(list(self.db.db.stakeholder_feedback.find({"pursuit_id": pursuit_id})))

    def get_support_distribution(self, pursuit_id: str) -> Dict[str, int]:
        """
        Get distribution of support levels for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Dict mapping support levels to counts
        """
        distribution = {level: 0 for level in SUPPORT_LEVELS}
        feedback_list = self.get_by_pursuit(pursuit_id)

        for feedback in feedback_list:
            level = feedback.get("support_level", "unclear")
            if level in distribution:
                distribution[level] += 1

        return distribution

    def get_all_concerns(self, pursuit_id: str) -> List[str]:
        """
        Get all concerns raised across all stakeholders for a pursuit.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            List of all concerns (may have duplicates)
        """
        concerns = []
        feedback_list = self.get_by_pursuit(pursuit_id)

        for feedback in feedback_list:
            fb_concerns = feedback.get("concerns", [])
            if isinstance(fb_concerns, list):
                concerns.extend(fb_concerns)
            elif fb_concerns:
                concerns.append(fb_concerns)

        return concerns

    def batch_save(self, feedback_list: List[StakeholderFeedback]) -> List[str]:
        """
        Save multiple feedback records at once.

        Args:
            feedback_list: List of StakeholderFeedback instances

        Returns:
            List of saved feedback_ids
        """
        ids = []
        for feedback in feedback_list:
            feedback_id = self.save(feedback)
            ids.append(feedback_id)
        return ids
