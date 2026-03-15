"""
API Response Transform Middleware
InDE MVP v3.7.0 - IKF UI Remediation & Display Label Registry

Intercepts responses from IKF and federation endpoints to ensure
internal identifiers never reach the innovator-facing UI.

Principles:
- Internal IDs remain in URLs for routing (contribution_id in the path)
- Response BODIES surface only human-readable identifiers
- The transform is applied in the proxy layer, not in individual endpoints
- Unknown fields pass through unchanged (future-safe)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from shared.display_labels import DisplayLabels

logger = logging.getLogger("inde.response_transform")


class ResponseTransformMiddleware:
    """
    Transforms IKF API responses for innovator-facing display.

    Applied to responses from:
    - /api/ikf/contributions/*
    - /api/ikf/federation/*
    - /api/ikf/patterns/*
    - /api/ikf/benchmarks/*
    - /api/ikf/activity/*
    """

    # Fields that should be REMOVED from responses entirely
    STRIP_FIELDS = [
        "contribution_id",       # IKF-UI-001: UUID never displayed
        "contributor_org_hash",  # IKF-UI-005: Federation plumbing field
        "instance_id",           # IKF-UI-008: Internal federation identifier
        "pattern_id",            # IKF-UI-009: Internal pattern identifier
        "ikf_pattern_id",        # IKF-UI-009: Alternate pattern ID field
        "connection_state",      # IKF-UI-008: Raw state machine value (handled specially)
        "_id",                   # MongoDB internal ID
    ]

    # Fields that should be TRANSLATED via DisplayLabels
    TRANSLATE_FIELDS = {
        "package_type": "package_type",              # IKF-UI-002
        "generalization_level": "generalization_level",  # IKF-UI-003
        "transmission_status": "transmission_status",    # IKF-UI-004
        "status": "contribution_status",                 # IKF-UI-011
        "methodology_archetype": "methodology_archetype",  # IKF-UI-012
        "sharing_level": "sharing_level",                # IKF-UI-010
        "trigger": "scenario_trigger",                   # IKF-UI-015
        "health_zone": "health_zone",
        "pursuit_status": "pursuit_status",
        "phase": "ikf_phase",
        "convergence_phase": "convergence_phase",
        "maturity_level": "maturity_level",
    }

    @classmethod
    def transform(cls, response_data: Union[Dict, List, Any], endpoint_context: str = None) -> Any:
        """
        Transform a single response object.

        1. Strip internal identifiers
        2. Translate enum/state fields to human-readable labels
        3. Add display-friendly computed fields where needed
        """
        if response_data is None:
            return response_data

        if isinstance(response_data, list):
            return [cls.transform(item, endpoint_context) for item in response_data]

        if not isinstance(response_data, dict):
            return response_data

        transformed = {}

        for key, value in response_data.items():
            # Strip internal fields
            if key in cls.STRIP_FIELDS:
                continue

            # Translate known enum/state fields
            if key in cls.TRANSLATE_FIELDS:
                category = cls.TRANSLATE_FIELDS[key]
                transformed[key] = DisplayLabels.get(category, value)
                icon = DisplayLabels.get(category, value, "icon")
                if icon and icon != str(value):
                    transformed[f"{key}_icon"] = icon
                # Keep raw value as _raw for any programmatic needs
                transformed[f"{key}_raw"] = value
                continue

            # Recursively transform nested dicts
            if isinstance(value, dict):
                transformed[key] = cls.transform(value, endpoint_context)
                continue

            # Recursively transform lists of dicts
            if isinstance(value, list):
                transformed[key] = [
                    cls.transform(item, endpoint_context)
                    if isinstance(item, dict) else item
                    for item in value
                ]
                continue

            # Pass through everything else
            transformed[key] = value

        return transformed

    @classmethod
    def transform_contribution_for_display(cls, contribution: dict) -> dict:
        """
        Specialized transform for contribution review panel (IKF-UI-001).

        Replaces contribution_id as primary identifier with:
        "package_type_label — pursuit_name — formatted_date"
        """
        transformed = cls.transform(contribution)

        # Build human-readable identifier (IKF-UI-001)
        pkg_label = transformed.get("package_type", "Contribution")
        pursuit_name = contribution.get("pursuit_name",
                       contribution.get("metadata", {}).get("pursuit_name", "Your Pursuit"))
        created = contribution.get("created_at", "")

        # Format date as human-readable
        formatted_date = cls._format_date(created)

        transformed["display_identifier"] = f"{pkg_label} — {pursuit_name} — {formatted_date}"

        return transformed

    @classmethod
    def transform_pii_results(cls, pii_data: dict) -> dict:
        """
        Specialized transform for PII scan results (IKF-UI-013).

        Replaces raw confidence floats with traffic light system:
        - Green: "No personal information detected"
        - Yellow: "Some information may need review" (expandable detail)
        - Red: "Personal information detected — review required"
        """
        if not pii_data:
            return {
                "pii_status": DisplayLabels.get("pii_confidence", "green"),
                "pii_status_icon": DisplayLabels.get("pii_confidence", "green", "icon"),
                "pii_level": "green",
                "detail_available": False,
                "details": []
            }

        confidence = pii_data.get("confidence", 0)
        level = DisplayLabels.pii_confidence_level(confidence)

        return {
            "pii_status": DisplayLabels.get("pii_confidence", level),
            "pii_status_icon": DisplayLabels.get("pii_confidence", level, "icon"),
            "pii_level": level,
            "detail_available": level != "green",
            # Only include field-level details if yellow or red AND user expands
            "details": pii_data.get("field_detections", []) if level != "green" else []
        }

    @classmethod
    def transform_federation_status(cls, status_data: dict) -> dict:
        """
        Specialized transform for federation status display (IKF-UI-007, 008).

        Strips instance_id and connection_state; surfaces only:
        - Connection status label with icon
        - Last sync time (human-readable)
        - Pending contribution count
        """
        state = status_data.get("connection_state",
                status_data.get("state", "OFFLINE"))

        return {
            "status": DisplayLabels.get_with_icon("federation_state", state),
            "status_label": DisplayLabels.get("federation_state", state),
            "status_description": DisplayLabels.get("federation_state", state, "description"),
            "last_sync": cls._format_relative_time(status_data.get("last_sync_at")),
            "pending_contributions": status_data.get("pending_count", 0),
            "is_connected": state == "CONNECTED"
        }

    @classmethod
    def transform_pattern_for_display(cls, pattern: dict) -> dict:
        """
        Specialized transform for pattern intelligence display (IKF-UI-009).

        Strips pattern_id and ikf_pattern_id; shows pattern name + source badge.
        """
        transformed = cls.transform(pattern)

        source = pattern.get("source", "local")
        if source in ("IKF_GLOBAL", "ikf", "IKF"):
            source_key = "ikf"
        else:
            source_key = "local"

        transformed["source_badge"] = DisplayLabels.get_with_icon("pattern_source", source_key)
        transformed["source_label"] = DisplayLabels.get("pattern_source", source_key)

        return transformed

    @classmethod
    def transform_biomimicry_feedback(cls, feedback: dict) -> dict:
        """
        Specialized transform for biomimicry feedback messages (IKF-UI-014).

        Replaces pattern_id reference with organism name + strategy name:
        "Your feedback on Namibian Beetle — Fog Harvesting has been recorded."
        """
        organism = feedback.get("organism_name", "the organism")
        strategy = feedback.get("strategy_name", "this strategy")

        transformed = cls.transform(feedback)
        transformed["confirmation_message"] = (
            f"Your feedback on {organism} — {strategy} has been recorded."
        )

        return transformed

    @classmethod
    def transform_activity_log_event(cls, event: dict) -> dict:
        """
        Specialized transform for IKF Activity Log events (IKF-UI-006).

        Translates raw event type codes into natural language descriptions.
        """
        EVENT_DESCRIPTIONS = {
            "ikf.package.prepared": "Contribution prepared for your review",
            "ikf.package.reviewed": "You approved a contribution",
            "ikf.package.rejected": "You declined a contribution",
            "ikf.package.transmitted": "Contribution shared with the Innovation Network",
            "ikf.package.acknowledged": "Innovation Network confirmed receipt",
            "ikf.pattern.received": "New insight received from the Innovation Network",
            "ikf.pattern.applied": "You applied an Innovation Network insight",
            "ikf.pattern.dismissed": "You dismissed an Innovation Network insight",
            "ikf.federation.connected": "Connected to Innovation Network",
            "ikf.federation.disconnected": "Disconnected from Innovation Network",
            "ikf.sync.completed": "Innovation Network sync completed",
            "pursuit.completed": "Pursuit completed — insights ready to contribute",
            "pursuit.retrospective.completed": "Retrospective completed — wisdom captured",
            "pursuit.created": "New pursuit started",
            "pursuit.updated": "Pursuit updated",
            "element.captured": "New insight captured",
            "artifact.generated": "Document created",
            "artifact.updated": "Document updated",
            "health.warning": "Health status changed",
            "coaching.intervention": "Coaching guidance provided",
        }

        event_type = event.get("event_type", event.get("type", ""))

        transformed = cls.transform(event)
        transformed["description"] = EVENT_DESCRIPTIONS.get(
            event_type,
            f"Activity: {event_type.replace('.', ' ').replace('_', ' ').title()}"
        )
        transformed["timestamp_display"] = cls._format_relative_time(
            event.get("timestamp", event.get("created_at"))
        )

        return transformed

    @classmethod
    def transform_scenario_artifact(cls, artifact: dict) -> dict:
        """
        Specialized transform for scenario artifacts (IKF-UI-015).

        Translates trigger codes into natural language descriptions.
        """
        transformed = cls.transform(artifact)

        trigger = artifact.get("trigger", artifact.get("detection_trigger", ""))
        if trigger:
            transformed["trigger_description"] = DisplayLabels.get_with_icon("scenario_trigger", trigger)

        return transformed

    @staticmethod
    def _format_date(iso_string: str) -> str:
        """Format ISO date string as human-readable: 'Feb 14, 2026'"""
        if not iso_string:
            return ""
        try:
            if isinstance(iso_string, datetime):
                dt = iso_string
            else:
                dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
            return dt.strftime("%b %d, %Y")
        except (ValueError, TypeError, AttributeError):
            return str(iso_string) if iso_string else ""

    @staticmethod
    def _format_relative_time(iso_string: str) -> str:
        """Format timestamp as relative: '3 minutes ago', '2 hours ago', etc."""
        if not iso_string:
            return "Never"
        try:
            if isinstance(iso_string, datetime):
                dt = iso_string
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))

            now = datetime.now(timezone.utc)
            delta = now - dt

            if delta.total_seconds() < 0:
                return "Just now"
            elif delta.total_seconds() < 60:
                return "Just now"
            elif delta.total_seconds() < 3600:
                mins = int(delta.total_seconds() / 60)
                return f"{mins} minute{'s' if mins != 1 else ''} ago"
            elif delta.total_seconds() < 86400:
                hours = int(delta.total_seconds() / 3600)
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            else:
                days = delta.days
                return f"{days} day{'s' if days != 1 else ''} ago"
        except (ValueError, TypeError, AttributeError):
            return str(iso_string) if iso_string else "Never"
