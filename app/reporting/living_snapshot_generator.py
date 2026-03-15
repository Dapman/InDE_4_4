"""
InDE MVP v2.8 - Living Snapshot Report Generator

Generates progress reports for active/suspended pursuits at any point
in their lifecycle. Shows COMPLETE, IN_PROGRESS, and PLANNED sections.

Key Features:
- Generate snapshot at any time during pursuit
- Sections show current status (COMPLETE, IN_PROGRESS, PLANNED)
- Include projections for planned sections
- Multiple output formats (Markdown, PDF)
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from config import TERMINAL_STATES, LIVING_SNAPSHOT_CONFIG


class LivingSnapshotGenerator:
    """
    Generates Living Snapshot Reports for active/suspended pursuits.
    """

    def __init__(self, database, template_manager):
        self.db = database
        self.template_manager = template_manager

    def generate_snapshot(
        self,
        pursuit_id: str,
        template_id: str = "silr-light",
        formats: List[str] = None,
        include_projections: bool = True
    ) -> Dict:
        """
        Generate living snapshot report for active pursuit.

        Args:
            pursuit_id: The pursuit to generate snapshot for
            template_id: Template to use (default: silr-light)
            formats: Output formats (default: ["markdown"])
            include_projections: Include planned sections with projections

        Returns:
            {
                "report_id": str,
                "formats": dict,
                "metadata": dict
            }
        """
        if formats is None:
            formats = LIVING_SNAPSHOT_CONFIG.get("formats", ["markdown"])

        # Get pursuit data
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            raise ValueError(f"Pursuit {pursuit_id} not found")

        # Validate pursuit is not terminal
        state = pursuit.get("state", "ACTIVE")
        if self._is_terminal(state):
            raise ValueError("Cannot generate snapshot for terminal pursuit. Use Terminal Report Generator.")

        # Get template
        template = self.template_manager.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Populate sections based on current state
        report_content = self._populate_snapshot_sections(
            template,
            pursuit,
            include_projections
        )

        # Calculate metadata
        metadata = self._calculate_snapshot_metadata(report_content, pursuit)

        # Generate report ID
        report_id = str(uuid.uuid4())

        # Render in requested formats
        rendered_formats = {}
        for fmt in formats:
            output_path = self._render_snapshot_format(
                report_id,
                report_content,
                template,
                pursuit,
                fmt
            )
            rendered_formats[fmt] = output_path

        # Store report record
        report_record = {
            "report_id": report_id,
            "pursuit_id": pursuit_id,
            "report_type": "LIVING_SNAPSHOT",
            "template_id": template_id,
            "generated_at": datetime.now(timezone.utc),
            "sections_included": [s["section_id"] for s in template["sections"] if s["included"]],
            "metadata": metadata,
            "content": report_content,
            "formats": rendered_formats
        }

        self.db.create_living_snapshot_report(report_record)

        return {
            "report_id": report_id,
            "formats": rendered_formats,
            "metadata": metadata,
            "content": report_content
        }

    def _populate_snapshot_sections(
        self,
        template: Dict,
        pursuit: Dict,
        include_projections: bool
    ) -> Dict:
        """Populate sections based on current pursuit state."""
        content = {}
        pursuit_id = pursuit.get("pursuit_id")

        for section in template["sections"]:
            if not section["included"]:
                continue

            section_id = section["section_id"]

            # Determine section status
            status = self._get_section_status(section_id, pursuit)

            if status == "COMPLETE":
                content[section_id] = self._populate_complete_section(
                    section,
                    pursuit
                )
            elif status == "IN_PROGRESS":
                content[section_id] = self._populate_in_progress_section(
                    section,
                    pursuit
                )
            elif status == "PLANNED" and include_projections:
                content[section_id] = self._populate_planned_section(
                    section,
                    pursuit
                )
            else:
                content[section_id] = {
                    "status": "NOT_STARTED",
                    "note": "This section will be available as the pursuit progresses"
                }

        return content

    def _get_section_status(self, section_id: str, pursuit: Dict) -> str:
        """Determine if section is COMPLETE, IN_PROGRESS, or PLANNED."""
        pursuit_id = pursuit.get("pursuit_id")

        # Project Identification - always complete if pursuit exists
        if section_id == "project_identification":
            return "COMPLETE"

        # Vision - complete if vision artifact exists
        if section_id == "vision":
            artifacts = self.db.get_pursuit_artifacts(pursuit_id, "vision")
            return "COMPLETE" if artifacts else "PLANNED"

        # Methodology - complete if methodology selected
        if section_id == "methodology":
            return "COMPLETE" if pursuit.get("methodology") else "PLANNED"

        # Journey tracking - in progress if there's conversation history
        if section_id == "journey_tracking":
            history = self.db.get_conversation_history(pursuit_id, limit=1)
            return "IN_PROGRESS" if history else "PLANNED"

        # Scaffolding state - in progress if any elements tracked
        if section_id == "scaffolding_state":
            state = self.db.get_scaffolding_state(pursuit_id)
            if state:
                completion = self._calculate_element_completion(state)
                if completion > 0.8:
                    return "COMPLETE"
                elif completion > 0:
                    return "IN_PROGRESS"
            return "PLANNED"

        # Hypothesis outcomes - complete if hypothesis artifact exists and validated
        if section_id == "hypothesis_outcomes":
            artifacts = self.db.get_pursuit_artifacts(pursuit_id, "hypothesis")
            if artifacts:
                latest = artifacts[0]
                if latest.get("validation_status"):
                    return "COMPLETE"
                return "IN_PROGRESS"
            return "PLANNED"

        # Outcomes - in progress for active pursuits
        if section_id == "outcomes":
            return "IN_PROGRESS"

        # Learnings - only complete if retrospective done (shouldn't be for active)
        if section_id == "learnings":
            return "PLANNED"

        # Risks - complete if fears identified
        if section_id == "risks":
            artifacts = self.db.get_pursuit_artifacts(pursuit_id, "fears")
            return "COMPLETE" if artifacts else "PLANNED"

        # Stakeholders - complete if stakeholder feedback exists
        if section_id == "stakeholders":
            feedback = self.db.get_stakeholder_feedback_by_pursuit(pursuit_id)
            return "COMPLETE" if feedback else "PLANNED"

        # Patterns - planned (generated at terminal)
        if section_id == "patterns":
            return "PLANNED"

        # Recommendations - always manual
        if section_id == "recommendations":
            return "PLANNED"

        return "PLANNED"

    def _populate_complete_section(self, section: Dict, pursuit: Dict) -> Dict:
        """Populate section with actual data."""
        section_id = section["section_id"]
        pursuit_id = pursuit.get("pursuit_id")

        if section_id == "project_identification":
            created_at = pursuit.get("created_at", datetime.now(timezone.utc))
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            # Ensure created_at is timezone-aware for subtraction
            if created_at and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            days_active = (datetime.now(timezone.utc) - created_at).days if created_at else 0

            return {
                "status": "COMPLETE",
                "data": {
                    "pursuit_name": pursuit.get("title", "Untitled"),
                    "innovator": pursuit.get("user_name", "Unknown"),
                    "organization": pursuit.get("organization", "Individual"),
                    "domain": pursuit.get("domain", "General"),
                    "start_date": created_at.strftime("%Y-%m-%d") if created_at else "Unknown",
                    "current_status": pursuit.get("state", "ACTIVE"),
                    "current_phase": pursuit.get("current_phase", "Active"),
                    "methodology": pursuit.get("methodology", "Not yet selected"),
                    "days_active": days_active
                }
            }

        elif section_id == "vision":
            artifacts = self.db.get_pursuit_artifacts(pursuit_id, "vision")
            if artifacts:
                vision = artifacts[0]
                return {
                    "status": "COMPLETE",
                    "data": {
                        "content": vision.get("content", ""),
                        "created_at": vision.get("created_at", "").isoformat() if isinstance(vision.get("created_at"), datetime) else str(vision.get("created_at", ""))
                    }
                }
            return {"status": "COMPLETE", "data": {}}

        elif section_id == "methodology":
            return {
                "status": "COMPLETE",
                "data": {
                    "methodology": pursuit.get("methodology", "Not specified"),
                    "phase": pursuit.get("current_phase", "Active")
                }
            }

        elif section_id == "scaffolding_state":
            state = self.db.get_scaffolding_state(pursuit_id)
            if state:
                completion = self._calculate_element_completion(state)
                return {
                    "status": "COMPLETE",
                    "data": {
                        "overall_completion": f"{completion:.0%}",
                        "vision_elements": len([k for k, v in state.get("vision_elements", {}).items() if v]),
                        "fear_elements": len([k for k, v in state.get("fear_elements", {}).items() if v]),
                        "hypothesis_elements": len([k for k, v in state.get("hypothesis_elements", {}).items() if v])
                    }
                }
            return {"status": "COMPLETE", "data": {}}

        elif section_id == "risks":
            artifacts = self.db.get_pursuit_artifacts(pursuit_id, "fears")
            if artifacts:
                fears = artifacts[0]
                return {
                    "status": "COMPLETE",
                    "data": {
                        "content": fears.get("content", ""),
                        "created_at": fears.get("created_at", "").isoformat() if isinstance(fears.get("created_at"), datetime) else str(fears.get("created_at", ""))
                    }
                }
            return {"status": "COMPLETE", "data": {}}

        elif section_id == "stakeholders":
            feedback = self.db.get_stakeholder_feedback_by_pursuit(pursuit_id)
            if feedback:
                support_dist = {"supportive": 0, "conditional": 0, "neutral": 0, "opposed": 0}
                for fb in feedback:
                    level = fb.get("support_level", "neutral")
                    if level in support_dist:
                        support_dist[level] += 1

                return {
                    "status": "COMPLETE",
                    "data": {
                        "total_stakeholders": len(feedback),
                        "support_distribution": support_dist,
                        "top_concerns": self._extract_top_concerns(feedback)
                    }
                }
            return {"status": "COMPLETE", "data": {}}

        return {"status": "COMPLETE", "data": {}}

    def _populate_in_progress_section(self, section: Dict, pursuit: Dict) -> Dict:
        """Populate partial data with IN_PROGRESS marker."""
        section_id = section["section_id"]
        pursuit_id = pursuit.get("pursuit_id")

        if section_id == "journey_tracking":
            history = self.db.get_conversation_history(pursuit_id, limit=100)
            return {
                "status": "IN_PROGRESS",
                "data": {
                    "interactions_count": len(history) if history else 0,
                    "note": "Journey tracking will be comprehensive at completion"
                }
            }

        elif section_id == "scaffolding_state":
            state = self.db.get_scaffolding_state(pursuit_id)
            if state:
                completion = self._calculate_element_completion(state)
                return {
                    "status": "IN_PROGRESS",
                    "data": {
                        "completion_percentage": f"{completion:.0%}",
                        "note": f"Scaffolding is {completion:.0%} complete"
                    }
                }
            return {"status": "IN_PROGRESS", "note": "Scaffolding in development"}

        elif section_id == "hypothesis_outcomes":
            artifacts = self.db.get_pursuit_artifacts(pursuit_id, "hypothesis")
            if artifacts:
                return {
                    "status": "IN_PROGRESS",
                    "data": {
                        "hypothesis_defined": True,
                        "note": "Hypothesis defined, awaiting validation"
                    }
                }
            return {"status": "IN_PROGRESS", "note": "Hypothesis in development"}

        elif section_id == "outcomes":
            return {
                "status": "IN_PROGRESS",
                "data": {
                    "note": "Outcomes will be finalized at pursuit completion"
                }
            }

        return {"status": "IN_PROGRESS", "note": "Section in development"}

    def _populate_planned_section(self, section: Dict, pursuit: Dict) -> Dict:
        """Show planned section with projection."""
        section_id = section["section_id"]
        methodology = pursuit.get("methodology", "lean_startup")

        if section_id == "hypothesis_outcomes":
            return {
                "status": "PLANNED",
                "projection": {
                    "note": "Hypothesis testing typically occurs in Assumption Testing phase",
                    "expected_phase": "ASSUMPTION_TESTING"
                }
            }

        elif section_id == "learnings":
            return {
                "status": "PLANNED",
                "projection": {
                    "note": "Key learnings will be captured through retrospective at pursuit completion",
                    "expected_timing": "At terminal state"
                }
            }

        elif section_id == "patterns":
            return {
                "status": "PLANNED",
                "projection": {
                    "note": "Patterns will be extracted from retrospective learnings",
                    "expected_timing": "After retrospective completion"
                }
            }

        elif section_id == "recommendations":
            return {
                "status": "PLANNED",
                "projection": {
                    "note": "Recommendations are typically added during report review",
                    "manual_entry": True
                }
            }

        return {"status": "PLANNED", "note": "This section is planned for later in the pursuit"}

    def _calculate_snapshot_metadata(self, content: Dict, pursuit: Dict) -> Dict:
        """Calculate metadata about snapshot completeness."""
        sections_complete = len([s for s in content.values() if s.get("status") == "COMPLETE"])
        sections_in_progress = len([s for s in content.values() if s.get("status") == "IN_PROGRESS"])
        sections_planned = len([s for s in content.values() if s.get("status") == "PLANNED"])
        sections_total = len(content)

        # Estimate pursuit completion based on scaffolding
        pursuit_id = pursuit.get("pursuit_id")
        state = self.db.get_scaffolding_state(pursuit_id)
        if state:
            pursuit_completion = self._calculate_element_completion(state)
        else:
            pursuit_completion = 0.1

        return {
            "pursuit_phase": pursuit.get("current_phase", "Active"),
            "pursuit_state": pursuit.get("state", "ACTIVE"),
            "completion_percentage": pursuit_completion,
            "sections_complete": sections_complete,
            "sections_in_progress": sections_in_progress,
            "sections_planned": sections_planned,
            "sections_total": sections_total,
            "report_type": "LIVING_SNAPSHOT",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    def _render_snapshot_format(
        self,
        report_id: str,
        content: Dict,
        template: Dict,
        pursuit: Dict,
        format: str
    ) -> str:
        """Render snapshot in specified format."""
        if format == "markdown":
            return self._render_snapshot_markdown(report_id, content, template, pursuit)
        elif format == "pdf":
            return self._render_snapshot_pdf(report_id, content, template, pursuit)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _render_snapshot_markdown(
        self,
        report_id: str,
        content: Dict,
        template: Dict,
        pursuit: Dict
    ) -> str:
        """Render as Markdown with status indicators."""
        # Create output directory if needed
        output_dir = os.path.join(os.path.dirname(__file__), "..", "outputs", "reports")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"snapshot_{report_id}.md")

        md = f"# Living Snapshot Report\n\n"
        md += f"**Pursuit:** {pursuit.get('title', 'Untitled')}\n\n"
        md += f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}\n\n"
        md += f"**Template:** {template.get('name', 'Unknown')}\n\n"
        md += "---\n\n"

        for section in template["sections"]:
            if not section["included"]:
                continue

            section_id = section["section_id"]
            if section_id not in content:
                continue

            section_content = content[section_id]
            status = section_content.get("status", "UNKNOWN")

            # Section header with status badge
            status_emoji = {
                "COMPLETE": "   ",
                "IN_PROGRESS": "   ",
                "PLANNED": "   ",
                "NOT_STARTED": "   "
            }

            md += f"## {section['title']} {status_emoji.get(status, '')}\n\n"

            if status == "COMPLETE":
                data = section_content.get("data", {})
                if "content" in data:
                    md += f"{data['content']}\n\n"
                else:
                    for key, value in data.items():
                        if isinstance(value, dict):
                            md += f"**{key.replace('_', ' ').title()}:**\n"
                            for k, v in value.items():
                                md += f"- {k}: {v}\n"
                            md += "\n"
                        elif isinstance(value, list):
                            md += f"**{key.replace('_', ' ').title()}:**\n"
                            for item in value:
                                md += f"- {item}\n"
                            md += "\n"
                        else:
                            md += f"**{key.replace('_', ' ').title()}:** {value}\n\n"

            elif status == "IN_PROGRESS":
                note = section_content.get("note", "In progress")
                md += f"*{note}*\n\n"
                if "data" in section_content:
                    for key, value in section_content["data"].items():
                        if key != "note":
                            md += f"- {key.replace('_', ' ').title()}: {value}\n"
                    md += "\n"

            elif status == "PLANNED":
                projection = section_content.get("projection", {})
                note = projection.get("note", section_content.get("note", "Planned for later"))
                md += f"*{note}*\n\n"

            md += "---\n\n"

        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md)

        return output_path

    def _render_snapshot_pdf(self, report_id: str, content: Dict, template: Dict, pursuit: Dict) -> str:
        """Render as PDF (generates markdown first, then converts)."""
        md_path = self._render_snapshot_markdown(report_id, content, template, pursuit)
        pdf_path = md_path.replace('.md', '.pdf')

        # In production, would use pandoc or weasyprint
        # For now, just note that markdown was generated
        return md_path  # Return markdown path as fallback

    def _is_terminal(self, state: str) -> bool:
        """Check if state is terminal."""
        return state in TERMINAL_STATES

    def _calculate_element_completion(self, state: Dict) -> float:
        """Calculate scaffolding element completion percentage."""
        if not state:
            return 0.0

        total = 0
        complete = 0

        for element_type in ["vision_elements", "fear_elements", "hypothesis_elements"]:
            elements = state.get(element_type, {})
            for key, value in elements.items():
                total += 1
                if value:
                    complete += 1

        return complete / total if total > 0 else 0.0

    def _extract_top_concerns(self, feedback: List[Dict], limit: int = 5) -> List[str]:
        """Extract top concerns from stakeholder feedback."""
        all_concerns = []
        for fb in feedback:
            concerns = fb.get("concerns", [])
            if isinstance(concerns, list):
                all_concerns.extend(concerns)
            elif isinstance(concerns, str):
                all_concerns.append(concerns)

        # Simple frequency count
        from collections import Counter
        concern_counts = Counter(all_concerns)
        return [concern for concern, _ in concern_counts.most_common(limit)]
