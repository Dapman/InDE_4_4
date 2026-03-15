"""
InDE MVP v2.7 - Stakeholder Notifier

Sends terminal state notifications to tracked stakeholders.
Integrates with v2.6 stakeholder feedback system.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from config import TERMINAL_STATES


class StakeholderNotifier:
    """
    Sends terminal state notifications to stakeholders.
    """

    # Notification templates by terminal state
    NOTIFICATION_TEMPLATES = {
        "COMPLETED.SUCCESSFUL": {
            "subject": "Innovation Pursuit Successfully Completed",
            "tone": "celebratory",
            "action_request": "We'd appreciate your feedback on the outcome."
        },
        "COMPLETED.VALIDATED_NOT_PURSUED": {
            "subject": "Innovation Pursuit - Validated, Strategic Decision Not to Proceed",
            "tone": "professional",
            "action_request": "Your input on this strategic decision is valued."
        },
        "TERMINATED.INVALIDATED": {
            "subject": "Innovation Pursuit - Hypothesis Invalidated",
            "tone": "learning-focused",
            "action_request": "We learned valuable lessons from this pursuit."
        },
        "TERMINATED.PIVOTED": {
            "subject": "Innovation Pursuit - Pivoting to New Direction",
            "tone": "forward-looking",
            "action_request": "We'd like to keep you updated on our new direction."
        },
        "TERMINATED.ABANDONED": {
            "subject": "Innovation Pursuit - Project Discontinued",
            "tone": "professional",
            "action_request": "Thank you for your support during this pursuit."
        },
        "TERMINATED.OBE": {
            "subject": "Innovation Pursuit - Overtaken by Events",
            "tone": "informational",
            "action_request": "We appreciate your involvement in this pursuit."
        }
    }

    def __init__(self, database):
        """
        Initialize StakeholderNotifier.

        Args:
            database: Database instance
        """
        self.db = database

    def notify_stakeholders(self, pursuit_id: str,
                           retrospective_id: str = None,
                           report_id: str = None) -> Dict:
        """
        Send notifications to all tracked stakeholders.

        Args:
            pursuit_id: Pursuit ID
            retrospective_id: Optional retrospective ID
            report_id: Optional report ID

        Returns:
            {
                "notifications_sent": int,
                "notification_ids": [...],
                "errors": [...]
            }
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return {"error": "Pursuit not found", "notifications_sent": 0}

        terminal_state = pursuit.get("state")
        if terminal_state not in TERMINAL_STATES:
            return {"error": "Pursuit not in terminal state", "notifications_sent": 0}

        # Get stakeholders for this pursuit
        stakeholders = list(self.db.db.stakeholder_feedback.find({
            "pursuit_id": pursuit_id
        }))

        if not stakeholders:
            return {
                "notifications_sent": 0,
                "message": "No stakeholders to notify",
                "notification_ids": [],
                "errors": []
            }

        # Get template
        template = self.NOTIFICATION_TEMPLATES.get(
            terminal_state,
            {"subject": "Innovation Pursuit Update", "tone": "professional", "action_request": ""}
        )

        # Send notifications
        notification_ids = []
        errors = []

        for stakeholder in stakeholders:
            notification = self._create_notification(
                pursuit=pursuit,
                stakeholder=stakeholder,
                terminal_state=terminal_state,
                template=template,
                retrospective_id=retrospective_id,
                report_id=report_id
            )

            try:
                # Store notification (in production would also send email/etc)
                self.db.db.notifications.insert_one(notification)
                notification_ids.append(notification["notification_id"])
            except Exception as e:
                errors.append({
                    "stakeholder": stakeholder.get("stakeholder_name"),
                    "error": str(e)
                })

        # Update pursuit to mark stakeholders notified
        self.db.db.pursuits.update_one(
            {"pursuit_id": pursuit_id},
            {"$set": {
                "terminal_info.stakeholders_notified": True,
                "terminal_info.stakeholders_notified_at": datetime.now(timezone.utc),
                "terminal_info.notifications_count": len(notification_ids)
            }}
        )

        return {
            "notifications_sent": len(notification_ids),
            "notification_ids": notification_ids,
            "errors": errors
        }

    def _create_notification(self, pursuit: Dict, stakeholder: Dict,
                            terminal_state: str, template: Dict,
                            retrospective_id: str = None,
                            report_id: str = None) -> Dict:
        """Create notification record."""
        import uuid

        # Build notification content
        content = self._build_notification_content(
            pursuit=pursuit,
            stakeholder=stakeholder,
            terminal_state=terminal_state,
            template=template
        )

        return {
            "notification_id": str(uuid.uuid4()),
            "pursuit_id": pursuit.get("pursuit_id"),
            "stakeholder_id": stakeholder.get("feedback_id"),
            "stakeholder_name": stakeholder.get("stakeholder_name"),
            "stakeholder_email": stakeholder.get("email"),  # May not exist
            "notification_type": "TERMINAL_STATE",
            "terminal_state": terminal_state,
            "subject": template["subject"],
            "content": content,
            "attachments": {
                "retrospective_id": retrospective_id,
                "report_id": report_id
            },
            "status": "CREATED",  # In production: PENDING, SENT, FAILED
            "created_at": datetime.now(timezone.utc)
        }

    def _build_notification_content(self, pursuit: Dict, stakeholder: Dict,
                                   terminal_state: str, template: Dict) -> str:
        """Build notification content."""
        pursuit_name = pursuit.get("title", "Unknown Pursuit")
        stakeholder_name = stakeholder.get("stakeholder_name", "Stakeholder")

        # Get outcome description
        outcome_descriptions = {
            "COMPLETED.SUCCESSFUL": "has been successfully completed",
            "COMPLETED.VALIDATED_NOT_PURSUED": "was validated but we've made a strategic decision not to proceed",
            "TERMINATED.INVALIDATED": "has concluded after our hypothesis was invalidated through testing",
            "TERMINATED.PIVOTED": "is being pivoted in a new direction",
            "TERMINATED.ABANDONED": "has been discontinued due to external factors",
            "TERMINATED.OBE": "has been overtaken by external events"
        }

        outcome_text = outcome_descriptions.get(terminal_state, "has reached its conclusion")

        content = f"""Dear {stakeholder_name},

We wanted to inform you that the innovation pursuit "{pursuit_name}" {outcome_text}.

Your engagement and feedback throughout this pursuit has been valuable. As part of our commitment to continuous learning, we've conducted a retrospective to capture key insights.

{template['action_request']}

Thank you for your support.

Best regards,
The Innovation Team"""

        return content

    def get_notification_status(self, notification_id: str) -> Optional[Dict]:
        """Get notification status by ID."""
        return self.db.db.notifications.find_one({"notification_id": notification_id})

    def get_pursuit_notifications(self, pursuit_id: str) -> List[Dict]:
        """Get all notifications for a pursuit."""
        return list(self.db.db.notifications.find({"pursuit_id": pursuit_id}))

    def request_stakeholder_feedback(self, pursuit_id: str,
                                     stakeholder_id: str) -> Dict:
        """
        Request feedback from a specific stakeholder on outcome.

        Args:
            pursuit_id: Pursuit ID
            stakeholder_id: Stakeholder feedback ID

        Returns:
            Request record
        """
        import uuid

        request = {
            "request_id": str(uuid.uuid4()),
            "pursuit_id": pursuit_id,
            "stakeholder_id": stakeholder_id,
            "request_type": "OUTCOME_FEEDBACK",
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc)
        }

        self.db.db.feedback_requests.insert_one(request)

        return request
