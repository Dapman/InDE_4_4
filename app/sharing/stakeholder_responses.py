"""
InDE MVP v2.9 - Stakeholder Response Handler
Capture stakeholder feedback on shared pursuits and thread into conversation.

Features:
- Capture feedback from shared pursuit views
- Thread responses into innovator's conversation
- Notify innovator of new feedback
- Enable innovator replies
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from config import STAKEHOLDER_RESPONSE_CONFIG


class StakeholderResponseHandler:
    """
    Handle stakeholder feedback from shared pursuits.

    Captures responses, threads them into the innovator's conversation,
    and enables two-way communication.
    """

    def __init__(self, db):
        """
        Initialize the response handler.

        Args:
            db: Database instance
        """
        self.db = db
        self.config = STAKEHOLDER_RESPONSE_CONFIG

    def capture_response(self, pursuit_id: str, shared_pursuit_id: str,
                        stakeholder_email: str, stakeholder_name: str,
                        response_type: str, response_text: str,
                        category: str = "general") -> str:
        """
        Record stakeholder feedback from shared pursuit.

        Args:
            pursuit_id: ID of the pursuit
            shared_pursuit_id: ID of the shared pursuit record
            stakeholder_email: Email of the responding stakeholder
            stakeholder_name: Name of the stakeholder
            response_type: excitement, concern, or question
            response_text: The actual feedback text
            category: Category for questions (market, technical, etc.)

        Returns:
            response_id of saved response
        """
        if response_type not in self.config.get("response_types", []):
            raise ValueError(f"Invalid response type: {response_type}")

        response_record = {
            "pursuit_id": pursuit_id,
            "shared_pursuit_id": shared_pursuit_id,
            "stakeholder_email": stakeholder_email,
            "stakeholder_name": stakeholder_name,
            "response_type": response_type,
            "response_text": response_text,
            "category": category
        }

        response_id = self.db.create_stakeholder_response(response_record)

        # Log activity
        self.db.log_activity(
            pursuit_id=pursuit_id,
            activity_type="stakeholder_feedback",
            description=f"{stakeholder_name} shared {response_type}: {response_text[:50]}...",
            metadata={
                "response_id": response_id,
                "response_type": response_type,
                "stakeholder_email": stakeholder_email
            }
        )

        # Auto-thread if configured
        if self.config.get("thread_to_conversation", True):
            self.thread_to_conversation(response_id)

        # Notify innovator if configured
        if self.config.get("notify_innovator", True):
            self.notify_innovator(pursuit_id, response_id)

        return response_id

    def thread_to_conversation(self, response_id: str) -> bool:
        """
        Add stakeholder feedback to innovator's chat.

        Creates a system message in conversation_history so ODICM
        can reference this feedback in coaching.

        Args:
            response_id: ID of the stakeholder response

        Returns:
            True if threaded successfully
        """
        response = self.db.get_stakeholder_response(response_id)
        if not response:
            return False

        pursuit_id = response.get("pursuit_id")
        stakeholder_name = response.get("stakeholder_name", "A stakeholder")
        response_type = response.get("response_type", "feedback")
        response_text = response.get("response_text", "")

        # Create formatted message for conversation
        type_emoji = {
            "excitement": "thumbs up",
            "concern": "warning",
            "question": "question"
        }.get(response_type, "message")

        message_content = (
            f"[Stakeholder Feedback] {stakeholder_name} responded with {response_type}:\n\n"
            f'"{response_text}"\n\n'
            f"Consider addressing this in your conversation."
        )

        # Save as system message in conversation history
        self.db.save_conversation_turn(
            pursuit_id=pursuit_id,
            role="system",
            content=message_content,
            metadata={
                "type": "stakeholder_response",
                "response_id": response_id,
                "stakeholder_name": stakeholder_name,
                "response_type": response_type
            }
        )

        # Mark as threaded
        self.db.mark_response_threaded(response_id)

        return True

    def notify_innovator(self, pursuit_id: str, response_id: str) -> bool:
        """
        Alert innovator of new stakeholder feedback.

        Args:
            pursuit_id: ID of the pursuit
            response_id: ID of the new response

        Returns:
            True if notification sent
        """
        response = self.db.get_stakeholder_response(response_id)
        if not response:
            return False

        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return False

        # Get user email
        user_id = pursuit.get("user_id")
        user = self.db.get_user(user_id)
        if not user or not user.get("email"):
            # In demo mode, just log
            print(f"[Notification] New stakeholder feedback on {pursuit.get('title')}")
            return True

        # Would send email notification here
        # For now, log the notification
        stakeholder_name = response.get("stakeholder_name", "A stakeholder")
        response_type = response.get("response_type", "feedback")

        print(
            f"[Notification] Email to {user.get('email')}: "
            f"{stakeholder_name} left {response_type} on '{pursuit.get('title')}'"
        )

        return True

    def enable_innovator_reply(self, response_id: str, reply_text: str,
                               user_id: str) -> bool:
        """
        Innovator responds to stakeholder question/feedback.

        Args:
            response_id: ID of the stakeholder response
            reply_text: The innovator's reply
            user_id: ID of the innovator (for verification)

        Returns:
            True if reply saved successfully
        """
        if not self.config.get("enable_innovator_reply", True):
            return False

        response = self.db.get_stakeholder_response(response_id)
        if not response:
            return False

        # Verify innovator owns the pursuit
        pursuit_id = response.get("pursuit_id")
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit or pursuit.get("user_id") != user_id:
            raise ValueError("Cannot reply to feedback on pursuit you don't own")

        # Save reply
        self.db.update_stakeholder_response(response_id, {
            "innovator_response": reply_text,
            "responded_at": datetime.now(timezone.utc)
        })

        # Notify stakeholder (would send email)
        stakeholder_email = response.get("stakeholder_email")
        if stakeholder_email:
            print(
                f"[Notification] Email to {stakeholder_email}: "
                f"Innovator replied to your feedback"
            )

        # Log activity
        self.db.log_activity(
            pursuit_id=pursuit_id,
            activity_type="innovator_replied",
            description=f"Replied to {response.get('stakeholder_name')}'s feedback",
            metadata={"response_id": response_id}
        )

        return True

    def get_pending_responses(self, pursuit_id: str) -> List[Dict]:
        """
        Get unaddressed stakeholder responses.

        Args:
            pursuit_id: ID of the pursuit

        Returns:
            List of responses without innovator reply
        """
        responses = self.db.get_pursuit_stakeholder_responses(pursuit_id)

        # Filter to those without reply
        pending = [
            r for r in responses
            if not r.get("innovator_response")
        ]

        return pending

    def get_response_summary(self, pursuit_id: str) -> Dict:
        """
        Get summary of stakeholder responses for a pursuit.

        Args:
            pursuit_id: ID of the pursuit

        Returns:
            Dict with response statistics
        """
        responses = self.db.get_pursuit_stakeholder_responses(pursuit_id)

        summary = {
            "total": len(responses),
            "by_type": {
                "excitement": 0,
                "concern": 0,
                "question": 0
            },
            "pending_replies": 0,
            "recent_responses": []
        }

        for r in responses:
            response_type = r.get("response_type", "unknown")
            if response_type in summary["by_type"]:
                summary["by_type"][response_type] += 1

            if not r.get("innovator_response"):
                summary["pending_replies"] += 1

        # Get 5 most recent
        summary["recent_responses"] = [
            {
                "stakeholder_name": r.get("stakeholder_name"),
                "response_type": r.get("response_type"),
                "response_text": r.get("response_text", "")[:100],
                "submitted_at": r.get("submitted_at"),
                "has_reply": bool(r.get("innovator_response"))
            }
            for r in responses[:5]
        ]

        return summary

    def format_for_odicm(self, pursuit_id: str) -> str:
        """
        Format stakeholder responses for ODICM context.

        Provides a summary that can be included in ODICM's
        coaching context.

        Args:
            pursuit_id: ID of the pursuit

        Returns:
            Formatted string for ODICM context
        """
        summary = self.get_response_summary(pursuit_id)

        if summary["total"] == 0:
            return ""

        parts = ["**Stakeholder Responses:**"]

        # Summary counts
        parts.append(
            f"- {summary['by_type']['excitement']} expressions of excitement"
        )
        parts.append(
            f"- {summary['by_type']['concern']} concerns raised"
        )
        parts.append(
            f"- {summary['by_type']['question']} questions asked"
        )

        if summary["pending_replies"] > 0:
            parts.append(f"- {summary['pending_replies']} awaiting your response")

        # Recent specific items
        if summary["recent_responses"]:
            parts.append("\n**Recent Feedback:**")
            for r in summary["recent_responses"][:3]:
                name = r.get("stakeholder_name", "Someone")
                rtype = r.get("response_type", "shared")
                text = r.get("response_text", "")[:50]
                replied = " (replied)" if r.get("has_reply") else ""
                parts.append(f'- {name} ({rtype}): "{text}..."{replied}')

        return "\n".join(parts)
