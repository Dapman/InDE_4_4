"""
InDE MVP v2.9 - Feedback Widgets
Simple reaction and comment widgets for shared pursuits.

Features:
- Three-button reactions (Excites/Concerns/Questions)
- Comment form with elaboration
- Question form with categories
"""

from typing import Dict, List, Optional

from config import FEEDBACK_WIDGET_LABELS, STAKEHOLDER_RESPONSE_CONFIG


class FeedbackWidgets:
    """
    UI widget configurations for stakeholder feedback on shared pursuits.

    Provides widget definitions and form structures for the
    public pursuit view interface.
    """

    def __init__(self):
        """Initialize the feedback widgets."""
        self.config = STAKEHOLDER_RESPONSE_CONFIG
        self.labels = FEEDBACK_WIDGET_LABELS

    def get_reaction_buttons(self) -> List[Dict]:
        """
        Get configuration for reaction buttons.

        Returns:
            List of button configurations
        """
        return [
            {
                "id": "excitement",
                "label": self.labels.get("excitement", "This excites me"),
                "icon": "thumbs_up",
                "color": "green",
                "prompt": "What specifically excites you about this innovation?"
            },
            {
                "id": "concern",
                "label": self.labels.get("concern", "This concerns me"),
                "icon": "warning",
                "color": "orange",
                "prompt": "What concerns do you have about this approach?"
            },
            {
                "id": "question",
                "label": self.labels.get("question", "I have questions"),
                "icon": "question",
                "color": "blue",
                "prompt": "What questions would you like the innovator to address?"
            }
        ]

    def get_comment_form(self, response_type: str = "general") -> Dict:
        """
        Get comment form configuration.

        Args:
            response_type: Type of response (excitement, concern, question)

        Returns:
            Form configuration dict
        """
        prompts = {
            "excitement": "Why does this excite you?",
            "concern": "What specifically concerns you?",
            "question": "What would you like to know?",
            "general": "Share your thoughts..."
        }

        return {
            "fields": [
                {
                    "name": "response_text",
                    "type": "textarea",
                    "label": prompts.get(response_type, prompts["general"]),
                    "required": True,
                    "maxlength": 1000,
                    "rows": 4
                },
                {
                    "name": "stakeholder_name",
                    "type": "text",
                    "label": "Your Name",
                    "required": False,
                    "placeholder": "Optional - helps the innovator follow up"
                },
                {
                    "name": "stakeholder_email",
                    "type": "email",
                    "label": "Email (for response notifications)",
                    "required": False,
                    "placeholder": "Optional - get notified of replies"
                }
            ],
            "submit_label": "Share Feedback"
        }

    def get_question_form(self) -> Dict:
        """
        Get structured question form configuration.

        Returns:
            Form configuration dict
        """
        categories = self.config.get("question_categories", [
            "market", "technical", "resource", "timing", "general"
        ])

        category_options = [
            {"value": "market", "label": "Market/Customer"},
            {"value": "technical", "label": "Technical/Feasibility"},
            {"value": "resource", "label": "Resources/Capabilities"},
            {"value": "timing", "label": "Timing/Strategy"},
            {"value": "general", "label": "General Question"}
        ]

        return {
            "fields": [
                {
                    "name": "response_text",
                    "type": "textarea",
                    "label": "Your Question",
                    "required": True,
                    "maxlength": 500,
                    "rows": 3,
                    "placeholder": "What would you like to know?"
                },
                {
                    "name": "category",
                    "type": "select",
                    "label": "Category",
                    "required": False,
                    "options": [c for c in category_options if c["value"] in categories],
                    "default": "general"
                },
                {
                    "name": "stakeholder_name",
                    "type": "text",
                    "label": "Your Name",
                    "required": False
                },
                {
                    "name": "stakeholder_email",
                    "type": "email",
                    "label": "Email (to receive answer)",
                    "required": False,
                    "placeholder": "We'll notify you when answered"
                }
            ],
            "submit_label": "Ask Question"
        }

    def get_full_widget_config(self) -> Dict:
        """
        Get complete widget configuration for public pursuit view.

        Returns:
            Dict with all widget configurations
        """
        return {
            "reaction_buttons": self.get_reaction_buttons(),
            "comment_form": self.get_comment_form(),
            "question_form": self.get_question_form(),
            "widget_settings": {
                "show_response_count": True,
                "require_email_for_notifications": True,
                "max_responses_displayed": 10,
                "show_innovator_replies": True,
                "collapse_after_submit": True
            }
        }

    def validate_response(self, response_data: Dict) -> Dict:
        """
        Validate a response submission.

        Args:
            response_data: Dict with form data

        Returns:
            Dict with is_valid and any errors
        """
        errors = []

        # Required fields
        if not response_data.get("response_text", "").strip():
            errors.append("Response text is required")

        if not response_data.get("response_type"):
            errors.append("Response type is required")

        # Validate response type
        valid_types = self.config.get("response_types", [
            "excitement", "concern", "question"
        ])
        if response_data.get("response_type") not in valid_types:
            errors.append(f"Invalid response type: {response_data.get('response_type')}")

        # Validate email format if provided
        email = response_data.get("stakeholder_email", "")
        if email and "@" not in email:
            errors.append("Invalid email format")

        # Length limits
        response_text = response_data.get("response_text", "")
        if len(response_text) > 1000:
            errors.append("Response text too long (max 1000 characters)")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }

    def format_response_display(self, response: Dict) -> Dict:
        """
        Format a response for display in the widget.

        Args:
            response: Response record from database

        Returns:
            Formatted response for display
        """
        response_type = response.get("response_type", "feedback")

        type_config = {
            "excitement": {"icon": "thumbs_up", "color": "green", "label": "Excited"},
            "concern": {"icon": "warning", "color": "orange", "label": "Concern"},
            "question": {"icon": "question", "color": "blue", "label": "Question"}
        }.get(response_type, {"icon": "message", "color": "gray", "label": "Feedback"})

        display = {
            "response_id": response.get("response_id"),
            "stakeholder_name": response.get("stakeholder_name", "Anonymous"),
            "response_type": response_type,
            "response_text": response.get("response_text", ""),
            "category": response.get("category"),
            "submitted_at": response.get("submitted_at"),
            "icon": type_config["icon"],
            "color": type_config["color"],
            "type_label": type_config["label"]
        }

        # Include reply if present
        if response.get("innovator_response"):
            display["innovator_reply"] = {
                "text": response.get("innovator_response"),
                "replied_at": response.get("responded_at")
            }

        return display
