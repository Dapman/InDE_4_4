"""
Pursuit Export Service
Packages a pursuit's complete history as a downloadable ZIP.
Generated on-demand, streamed, never stored server-side.

v3.13: Innovator Experience Polish
"""

import io
import json
import logging
import zipfile
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import HTTPException

logger = logging.getLogger(__name__)


class PursuitExportService:
    """
    Generates complete pursuit export packages.

    Export format: ZIP file containing:
    - README.txt - Package overview
    - vision/ - Vision artifacts and persona documents
    - fears/ - Fear register from scaffolding state
    - milestones/ - Timeline with status
    - artifacts/ - All generated artifacts
    - conversations/ - Coaching sessions as readable Markdown
    - export_manifest.json - Machine-readable index
    """

    def __init__(self, db):
        """
        Initialize with database connection.

        Args:
            db: Database instance (expects db.db for raw pymongo access)
        """
        self.db = db.db if hasattr(db, 'db') else db

    def generate_export(self, pursuit_id: str, user_id: str) -> tuple:
        """
        Generate a complete pursuit export as a ZIP file in memory.

        Authorization: user must own the pursuit.

        Args:
            pursuit_id: The pursuit to export
            user_id: The user requesting export (must own pursuit)

        Returns:
            (zip_buffer: io.BytesIO, filename: str)
            The buffer is positioned at the start (seek(0) already called).

        Raises:
            HTTPException: 404 if pursuit not found, 403 if not authorized
        """
        # Verify ownership
        pursuit = self._get_authorized_pursuit(pursuit_id, user_id)

        # Gather all data
        export_data = self._collect_pursuit_data(pursuit)

        # Build ZIP in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            # README
            zf.writestr("README.txt", self._build_readme(pursuit, export_data))

            # Vision artifacts
            for artifact in export_data.get("vision_artifacts", []):
                title = artifact.get("title", "artifact")
                filename = f"vision/{self._safe_filename(title)}.md"
                zf.writestr(filename, self._format_artifact_as_markdown(artifact))

            # Fear register from scaffolding state
            if export_data.get("fear_elements"):
                zf.writestr("fears/fear_register.md", self._format_fears(export_data["fear_elements"]))

            # Milestones / timeline
            if export_data.get("milestones"):
                zf.writestr("milestones/timeline.md", self._format_milestones(export_data["milestones"]))

            # Other artifacts (retrospective, SILR, hypotheses, etc.)
            for artifact in export_data.get("other_artifacts", []):
                artifact_type = artifact.get("artifact_type", "artifact").lower().replace(".", "_")
                artifact_id = artifact.get("artifact_id", "unknown")[:8]
                filename = f"artifacts/{artifact_type}_{artifact_id}.md"
                zf.writestr(filename, self._format_artifact_as_markdown(artifact))

            # Coaching conversations (one Markdown file per session group)
            sessions = export_data.get("sessions", [])
            if sessions:
                for i, session in enumerate(sessions, 1):
                    session_date = str(session.get("date", "unknown"))[:10]
                    filename = f"conversations/session_{i:03d}_{session_date}.md"
                    zf.writestr(filename, self._format_session_as_markdown(session, i))

            # Machine-readable manifest
            zf.writestr("export_manifest.json", json.dumps(
                self._build_manifest(pursuit, export_data),
                indent=2,
                default=str
            ))

        zip_buffer.seek(0)

        # Generate filename: inde_export_{pursuit_title}_{date}.zip
        safe_title = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in pursuit.get("title", "pursuit")
        )[:40]
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        filename = f"inde_export_{safe_title}_{date_str}.zip"

        logger.info(f"Export generated for pursuit {pursuit_id} by user {user_id}. Filename: {filename}")

        return zip_buffer, filename

    def _collect_pursuit_data(self, pursuit: dict) -> dict:
        """Gather all related data for a pursuit."""
        pursuit_id = pursuit.get("pursuit_id")

        # Vision artifacts
        vision_artifacts = list(self.db.artifacts.find({
            "pursuit_id": pursuit_id,
            "artifact_type": {"$regex": "^vision", "$options": "i"}
        }))

        # Other artifacts
        other_artifacts = list(self.db.artifacts.find({
            "pursuit_id": pursuit_id,
            "artifact_type": {"$not": {"$regex": "^vision", "$options": "i"}}
        }).sort("created_at", -1))

        # Scaffolding state (contains fear_elements)
        scaffolding = self.db.scaffolding_states.find_one({"pursuit_id": pursuit_id})
        fear_elements = scaffolding.get("fear_elements", {}) if scaffolding else {}

        # Milestones (non-superseded)
        milestones = list(self.db.pursuit_milestones.find({
            "pursuit_id": pursuit_id,
            "is_superseded": {"$ne": True}
        }).sort("target_date", 1))

        # Conversation history
        sessions = self._collect_sessions(pursuit_id)

        # Retrospective if exists
        retrospective = self.db.retrospectives.find_one({"pursuit_id": pursuit_id})
        if retrospective:
            # Remove MongoDB _id
            retrospective.pop("_id", None)

        return {
            "pursuit": pursuit,
            "vision_artifacts": vision_artifacts,
            "fear_elements": fear_elements,
            "milestones": milestones,
            "other_artifacts": other_artifacts,
            "sessions": sessions,
            "retrospective": retrospective,
            "scaffolding": scaffolding
        }

    def _collect_sessions(self, pursuit_id: str) -> List[dict]:
        """
        Collect coaching conversations grouped by day.
        """
        turns = list(self.db.conversation_history.find(
            {"pursuit_id": pursuit_id}
        ).sort("timestamp", 1))

        if not turns:
            return []

        # Group by date
        sessions_map = {}
        for turn in turns:
            timestamp = turn.get("timestamp")
            if timestamp:
                date_key = str(timestamp)[:10]  # YYYY-MM-DD
            else:
                date_key = "unknown"

            if date_key not in sessions_map:
                sessions_map[date_key] = {
                    "date": date_key,
                    "turns": []
                }

            sessions_map[date_key]["turns"].append({
                "role": turn.get("role", ""),
                "content": turn.get("content", ""),
                "timestamp": str(turn.get("timestamp", ""))
            })

        return list(sessions_map.values())

    def _build_readme(self, pursuit: dict, export_data: dict) -> str:
        session_count = len(export_data.get("sessions", []))
        fear_elements = export_data.get("fear_elements", {})
        fear_count = sum(1 for v in fear_elements.values() if v)
        milestone_count = len(export_data.get("milestones", []))
        artifact_count = len(export_data.get("vision_artifacts", [])) + len(export_data.get("other_artifacts", []))
        export_date = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

        created_at = pursuit.get("created_at", "")
        if hasattr(created_at, 'strftime'):
            created_at = created_at.strftime("%Y-%m-%d")
        else:
            created_at = str(created_at)[:10]

        return f"""InDE Innovation Pursuit Export
==============================

Pursuit: {pursuit.get('title', 'Untitled')}
Description: {pursuit.get('description', 'No description')}
Status: {pursuit.get('status', 'Unknown')}
Created: {created_at}
Exported: {export_date}

Contents
--------
conversations/   {session_count} coaching session(s)
vision/          Vision and persona artifacts
fears/           Fear register ({fear_count} identified)
milestones/      Timeline ({milestone_count} milestones)
artifacts/       {artifact_count} generated artifact(s)
export_manifest.json   Machine-readable index

About This Export
-----------------
This package was exported from InDE (Innovation Development Environment),
an AI-powered innovation coaching platform by InDEVerse, Incorporated.

The conversations/ folder contains the complete coaching dialogue for this
pursuit, organized chronologically by date. Vision, fear, and milestone
documents capture the structured artifacts produced during coaching.

All content is the intellectual work of the innovator. InDE coaching
responses are included for context but the innovation itself belongs to you.

For more information: https://indeverse.com
"""

    def _format_fears(self, fear_elements: dict) -> str:
        lines = ["# Fear Register\n"]
        lines.append("Fears and concerns identified during coaching.\n")

        i = 0
        for key, value in fear_elements.items():
            if value:
                i += 1
                # Handle both string and dict values
                if isinstance(value, dict):
                    text = value.get("text", str(value))
                    status = value.get("status", "identified")
                else:
                    text = str(value)
                    status = "identified"

                status_icon = "resolved" if status == "resolved" else "open"
                lines.append(f"## {i}. {key.replace('_', ' ').title()} [{status_icon}]")
                lines.append(f"\n{text}\n")

        if i == 0:
            lines.append("No fears have been formally identified yet.\n")

        return "\n".join(lines)

    def _format_milestones(self, milestones: list) -> str:
        lines = ["# Innovation Timeline\n"]

        for m in milestones:
            status = m.get("status", "planned")
            status_icon = {"completed": "[x]", "in_progress": "[-]", "planned": "[ ]"}.get(status, "[ ]")

            lines.append(f"## {status_icon} {m.get('title', 'Untitled')}")
            lines.append(f"\n**Target Date:** {m.get('target_date', 'TBD')}")
            lines.append(f"\n**Type:** {m.get('milestone_type', 'milestone')}")
            lines.append(f"\n**Status:** {status}")

            if m.get("description"):
                lines.append(f"\n**Notes:** {m.get('description', '')}")

            lines.append("")

        if not milestones:
            lines.append("No milestones have been set yet.\n")

        return "\n".join(lines)

    def _format_session_as_markdown(self, session: dict, session_num: int) -> str:
        lines = [
            f"# Coaching Session {session_num}",
            f"\n**Date:** {session.get('date', 'Unknown')}\n",
            "---\n"
        ]

        for turn in session.get("turns", []):
            role = turn.get("role", "")
            content = turn.get("content", "")

            if role == "user":
                lines.append(f"**You:**\n\n{content}\n")
            else:
                lines.append(f"**InDE Coach:**\n\n{content}\n")

        return "\n".join(lines)

    def _format_artifact_as_markdown(self, artifact: dict) -> str:
        title = artifact.get("title", "Artifact")
        artifact_type = artifact.get("artifact_type", "")

        created_at = artifact.get("created_at", "")
        if hasattr(created_at, 'strftime'):
            created_at = created_at.strftime("%Y-%m-%d")
        else:
            created_at = str(created_at)[:10]

        lines = [
            f"# {title}",
            f"\n**Type:** {artifact_type}",
            f"\n**Created:** {created_at}\n",
            "---\n"
        ]

        content = artifact.get("content") or artifact.get("content_json") or ""
        if isinstance(content, dict):
            content = json.dumps(content, indent=2)

        lines.append(str(content))
        return "\n".join(lines)

    def _build_manifest(self, pursuit: dict, export_data: dict) -> dict:
        return {
            "export_format_version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "pursuit": {
                "id": pursuit.get("pursuit_id", ""),
                "title": pursuit.get("title", ""),
                "description": pursuit.get("description", ""),
                "status": pursuit.get("status", ""),
                "created_at": str(pursuit.get("created_at", "")),
            },
            "contents": {
                "coaching_sessions": len(export_data.get("sessions", [])),
                "vision_artifacts": len(export_data.get("vision_artifacts", [])),
                "fears_identified": sum(1 for v in export_data.get("fear_elements", {}).values() if v),
                "milestones": len(export_data.get("milestones", [])),
                "other_artifacts": len(export_data.get("other_artifacts", [])),
                "has_retrospective": export_data.get("retrospective") is not None
            },
            "generated_by": "InDE v4.3.0",
            "indeverse": "https://indeverse.com"
        }

    def _safe_filename(self, name: str) -> str:
        """Create a safe filename from a string."""
        return "".join(
            c if c.isalnum() or c in "-_ " else "_"
            for c in name
        )[:60].strip()

    def _get_authorized_pursuit(self, pursuit_id: str, user_id: str) -> dict:
        """
        Fetch pursuit and verify ownership.

        Raises:
            HTTPException: 404 if not found, 403 if not authorized
        """
        pursuit = self.db.pursuits.find_one({"pursuit_id": pursuit_id})

        if not pursuit:
            raise HTTPException(status_code=404, detail="Pursuit not found")

        if str(pursuit.get("user_id")) != str(user_id):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to export this pursuit"
            )

        return pursuit
