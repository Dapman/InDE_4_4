"""
InDE MVP v2.9 - Mention Handler
Detect and handle @mentions in text for notifications.

Features:
- Detect @mentions in comments and chat
- Send email notifications when mentioned
- Track mention notifications
"""

import re
from datetime import datetime
from typing import Dict, List, Optional

from config import COLLABORATION_CONFIG


class MentionHandler:
    """
    Handle @mentions in text and send notifications.

    Detects mentions of stakeholders by email or name and
    sends appropriate notifications.
    """

    def __init__(self, db):
        """
        Initialize the mention handler.

        Args:
            db: Database instance
        """
        self.db = db
        self.config = COLLABORATION_CONFIG
        self.mention_pattern = re.compile(
            self.config.get(
                "mention_pattern",
                r"@([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+|[A-Za-z][A-Za-z0-9_]*)"
            )
        )

    def detect_mentions(self, text: str) -> List[Dict]:
        """
        Find @mentions in text.

        Args:
            text: Text to search for mentions

        Returns:
            List of detected mentions with details
        """
        if not self.config.get("enable_mentions", True):
            return []

        mentions = []
        matches = self.mention_pattern.findall(text)

        for match in matches:
            mention = {
                "raw": match,
                "type": "email" if "@" in match and "." in match else "name",
                "value": match
            }
            mentions.append(mention)

        return mentions

    def resolve_mentions(self, mentions: List[Dict], pursuit_id: str) -> List[Dict]:
        """
        Resolve mention references to stakeholder records.

        Args:
            mentions: List of detected mentions
            pursuit_id: Pursuit ID for stakeholder lookup

        Returns:
            List of resolved mentions with stakeholder details
        """
        resolved = []

        # Get stakeholders for this pursuit
        stakeholders = self.db.get_stakeholder_feedback_by_pursuit(pursuit_id)

        for mention in mentions:
            resolved_mention = {
                **mention,
                "resolved": False,
                "stakeholder": None
            }

            if mention["type"] == "email":
                # Look for exact email match
                for sh in stakeholders:
                    if sh.get("email", "").lower() == mention["value"].lower():
                        resolved_mention["resolved"] = True
                        resolved_mention["stakeholder"] = {
                            "feedback_id": sh.get("feedback_id"),
                            "name": sh.get("stakeholder_name"),
                            "email": sh.get("email")
                        }
                        break

            elif mention["type"] == "name":
                # Look for name match (case-insensitive)
                for sh in stakeholders:
                    name = sh.get("stakeholder_name", "")
                    # Match if mention matches first name, last name, or full name
                    name_parts = name.lower().split()
                    if mention["value"].lower() in name_parts or mention["value"].lower() == name.lower().replace(" ", ""):
                        resolved_mention["resolved"] = True
                        resolved_mention["stakeholder"] = {
                            "feedback_id": sh.get("feedback_id"),
                            "name": name,
                            "email": sh.get("email")
                        }
                        break

            resolved.append(resolved_mention)

        return resolved

    def send_mention_notification(self, stakeholder_email: str,
                                  pursuit_id: str, context: str,
                                  mentioned_by: str = None) -> bool:
        """
        Email stakeholder when mentioned.

        Args:
            stakeholder_email: Email to notify
            pursuit_id: ID of the pursuit
            context: Text context where mention occurred
            mentioned_by: Name of person who made the mention

        Returns:
            True if notification sent
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return False

        # In production, would send actual email
        pursuit_title = pursuit.get("title", "an innovation pursuit")

        print(
            f"[Notification] Email to {stakeholder_email}: "
            f"You were mentioned in '{pursuit_title}' "
            f"by {mentioned_by or 'someone'}: {context[:100]}..."
        )

        # Log activity
        self.db.log_activity(
            pursuit_id=pursuit_id,
            activity_type="mention_notification",
            description=f"Notified {stakeholder_email} of mention",
            metadata={
                "stakeholder_email": stakeholder_email,
                "mentioned_by": mentioned_by
            }
        )

        return True

    def process_text_for_mentions(self, text: str, pursuit_id: str,
                                  author_name: str = None) -> Dict:
        """
        Full pipeline: detect, resolve, and notify mentions.

        Args:
            text: Text to process
            pursuit_id: Pursuit context
            author_name: Who wrote the text

        Returns:
            Dict with mentions found and notifications sent
        """
        result = {
            "mentions_found": 0,
            "mentions_resolved": 0,
            "notifications_sent": 0,
            "mentions": []
        }

        # Detect mentions
        mentions = self.detect_mentions(text)
        result["mentions_found"] = len(mentions)

        if not mentions:
            return result

        # Resolve to stakeholders
        resolved = self.resolve_mentions(mentions, pursuit_id)
        result["mentions_resolved"] = sum(1 for m in resolved if m.get("resolved"))
        result["mentions"] = resolved

        # Send notifications for resolved mentions
        for mention in resolved:
            if mention.get("resolved") and mention.get("stakeholder"):
                email = mention["stakeholder"].get("email")
                if email:
                    sent = self.send_mention_notification(
                        stakeholder_email=email,
                        pursuit_id=pursuit_id,
                        context=text,
                        mentioned_by=author_name
                    )
                    if sent:
                        result["notifications_sent"] += 1

        return result

    def get_mention_suggestions(self, partial: str, pursuit_id: str) -> List[Dict]:
        """
        Get autocomplete suggestions for @mentions.

        Args:
            partial: Partial mention text to match
            pursuit_id: Pursuit context for stakeholders

        Returns:
            List of matching stakeholder suggestions
        """
        stakeholders = self.db.get_stakeholder_feedback_by_pursuit(pursuit_id)

        suggestions = []
        partial_lower = partial.lower()

        for sh in stakeholders:
            name = sh.get("stakeholder_name", "")
            email = sh.get("email", "")

            # Match on name or email
            if (partial_lower in name.lower() or
                partial_lower in email.lower()):
                suggestions.append({
                    "name": name,
                    "email": email,
                    "role": sh.get("role", ""),
                    "mention_value": email if email else name.replace(" ", "")
                })

        return suggestions[:10]  # Limit to 10 suggestions

    def format_text_with_mentions(self, text: str, mentions: List[Dict]) -> str:
        """
        Format text with resolved mentions highlighted.

        Args:
            text: Original text
            mentions: Resolved mentions list

        Returns:
            Text with mentions formatted (e.g., for HTML display)
        """
        formatted = text

        for mention in mentions:
            raw = "@" + mention["raw"]
            if mention.get("resolved"):
                stakeholder = mention.get("stakeholder", {})
                name = stakeholder.get("name", mention["raw"])
                # Replace with styled mention
                replacement = f'**@{name}**'
            else:
                replacement = f'@{mention["raw"]}'

            formatted = formatted.replace(raw, replacement, 1)

        return formatted
