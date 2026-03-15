"""
InDE MVP v2.8 - Report Template Manager

Manages report templates for SILR (Standardized Innovation Lifecycle Report)
and other report types. Provides system templates and custom template support.

System Templates:
- silr-standard: Full SILR with all 12 sections
- silr-light: Executive summary version (6 sections)
- academic: Research-focused format
- commercial: Business/investor format
- internal: Organization internal format
- investor: Pitch deck companion
- grant: Grant application format
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from config import REPORT_TEMPLATES_CONFIG


class ReportTemplateManager:
    """
    Manages report templates for all report types.
    Provides system templates and custom template CRUD operations.
    """

    def __init__(self, database):
        self.db = database
        self._system_templates = {}
        self._initialize_system_templates()

    def _initialize_system_templates(self):
        """Initialize all system templates."""
        self._system_templates = {
            "silr-standard": self._create_silr_standard_template(),
            "silr-light": self._create_silr_light_template(),
            "academic": self._create_academic_template(),
            "commercial": self._create_commercial_template(),
            "internal": self._create_internal_template(),
            "investor": self._create_investor_template(),
            "grant": self._create_grant_template()
        }

    def get_template(self, template_id: str) -> Optional[Dict]:
        """
        Get a template by ID.
        Checks system templates first, then custom templates.
        """
        # Check system templates
        if template_id in self._system_templates:
            return self._system_templates[template_id]

        # Check custom templates in database
        return self.db.get_report_template(template_id)

    def get_all_system_templates(self) -> List[Dict]:
        """Get all system templates."""
        return list(self._system_templates.values())

    def get_template_list(self, user_id: str = None) -> List[Dict]:
        """Get list of available templates (system + user custom)."""
        templates = []

        # Add system templates
        for template in self._system_templates.values():
            templates.append({
                "template_id": template["template_id"],
                "name": template["name"],
                "description": template["description"],
                "is_system": True,
                "section_count": len(template["sections"])
            })

        # Add user custom templates if user_id provided
        if user_id:
            custom = self.db.get_user_templates(user_id)
            for template in custom:
                templates.append({
                    "template_id": template["template_id"],
                    "name": template["name"],
                    "description": template.get("description", ""),
                    "is_system": False,
                    "section_count": len(template.get("sections", []))
                })

        return templates

    def create_custom_template(
        self,
        user_id: str,
        name: str,
        sections: List[Dict],
        description: str = "",
        base_template: str = None
    ) -> str:
        """Create a custom template for a user."""
        # Check user template limit
        existing = self.db.get_user_templates(user_id)
        max_templates = REPORT_TEMPLATES_CONFIG.get("max_custom_templates_per_user", 10)
        if len(existing) >= max_templates:
            raise ValueError(f"Maximum custom templates ({max_templates}) reached")

        template_id = str(uuid.uuid4())

        template_record = {
            "template_id": template_id,
            "name": name,
            "description": description,
            "sections": sections,
            "created_by": user_id,
            "base_template": base_template,
            "is_system": False,
            "created_at": datetime.now(timezone.utc)
        }

        self.db.create_report_template(template_record)
        return template_id

    def _default_formatting(self) -> Dict:
        """Default formatting options for templates."""
        return {
            "include_toc": False,
            "include_executive_summary": False,
            "page_numbers": True,
            "confidentiality_footer": None,
            "header_logo": None,
            "color_scheme": "professional"
        }

    # =========================================================================
    # SYSTEM TEMPLATE DEFINITIONS
    # =========================================================================

    def _create_silr_standard_template(self) -> Dict:
        """Create the standard SILR template with all 12 sections."""
        return {
            "template_id": "silr-standard",
            "name": "SILR Standard",
            "description": "Full Standardized Innovation Lifecycle Report with all sections",
            "is_system": True,
            "sections": [
                {
                    "section_id": "project_identification",
                    "title": "Project Identification",
                    "included": True,
                    "order": 1,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "vision",
                    "title": "Vision Statement",
                    "included": True,
                    "order": 2,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "methodology",
                    "title": "Methodology",
                    "included": True,
                    "order": 3,
                    "auto_populate": True,
                    "required": False
                },
                {
                    "section_id": "journey_tracking",
                    "title": "Journey Tracking",
                    "included": True,
                    "order": 4,
                    "auto_populate": True,
                    "required": False
                },
                {
                    "section_id": "scaffolding_state",
                    "title": "Scaffolding State",
                    "included": True,
                    "order": 5,
                    "auto_populate": True,
                    "required": False
                },
                {
                    "section_id": "hypothesis_outcomes",
                    "title": "Hypothesis Outcomes",
                    "included": True,
                    "order": 6,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "outcomes",
                    "title": "Outcomes",
                    "included": True,
                    "order": 7,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "learnings",
                    "title": "Key Learnings",
                    "included": True,
                    "order": 8,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "risks",
                    "title": "Risks & Fears",
                    "included": True,
                    "order": 9,
                    "auto_populate": True,
                    "required": False
                },
                {
                    "section_id": "stakeholders",
                    "title": "Stakeholder Engagement",
                    "included": True,
                    "order": 10,
                    "auto_populate": True,
                    "required": False
                },
                {
                    "section_id": "patterns",
                    "title": "Patterns Extracted",
                    "included": True,
                    "order": 11,
                    "auto_populate": True,
                    "required": False
                },
                {
                    "section_id": "recommendations",
                    "title": "Recommendations",
                    "included": True,
                    "order": 12,
                    "auto_populate": False,
                    "required": False
                }
            ],
            "formatting": self._default_formatting(),
            "created_at": datetime.now(timezone.utc)
        }

    def _create_silr_light_template(self) -> Dict:
        """Create the light SILR template for executive summaries."""
        return {
            "template_id": "silr-light",
            "name": "SILR Light",
            "description": "Executive summary version with 6 key sections",
            "is_system": True,
            "sections": [
                {
                    "section_id": "project_identification",
                    "title": "Project Overview",
                    "included": True,
                    "order": 1,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "vision",
                    "title": "Vision",
                    "included": True,
                    "order": 2,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "outcomes",
                    "title": "Outcomes",
                    "included": True,
                    "order": 3,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "learnings",
                    "title": "Key Learnings",
                    "included": True,
                    "order": 4,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "stakeholders",
                    "title": "Stakeholder Summary",
                    "included": True,
                    "order": 5,
                    "auto_populate": True,
                    "required": False
                },
                {
                    "section_id": "recommendations",
                    "title": "Next Steps",
                    "included": True,
                    "order": 6,
                    "auto_populate": False,
                    "required": False
                }
            ],
            "formatting": {
                **self._default_formatting(),
                "include_executive_summary": True
            },
            "created_at": datetime.now(timezone.utc)
        }

    def _create_academic_template(self) -> Dict:
        """Create academic/research-focused template."""
        return {
            "template_id": "academic",
            "name": "Academic Research",
            "description": "Research-focused format with methodology emphasis",
            "is_system": True,
            "sections": [
                {
                    "section_id": "project_identification",
                    "title": "Research Project",
                    "included": True,
                    "order": 1,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "vision",
                    "title": "Research Question",
                    "included": True,
                    "order": 2,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "methodology",
                    "title": "Methodology",
                    "included": True,
                    "order": 3,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "hypothesis_outcomes",
                    "title": "Hypothesis & Findings",
                    "included": True,
                    "order": 4,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "learnings",
                    "title": "Conclusions",
                    "included": True,
                    "order": 5,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "patterns",
                    "title": "Implications",
                    "included": True,
                    "order": 6,
                    "auto_populate": True,
                    "required": False
                },
                {
                    "section_id": "recommendations",
                    "title": "Future Research",
                    "included": True,
                    "order": 7,
                    "auto_populate": False,
                    "required": False
                }
            ],
            "formatting": {
                **self._default_formatting(),
                "include_toc": True
            },
            "created_at": datetime.now(timezone.utc)
        }

    def _create_commercial_template(self) -> Dict:
        """Create commercial/business template."""
        return {
            "template_id": "commercial",
            "name": "Commercial",
            "description": "Business-focused format for stakeholders",
            "is_system": True,
            "sections": [
                {
                    "section_id": "project_identification",
                    "title": "Executive Summary",
                    "included": True,
                    "order": 1,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "vision",
                    "title": "Value Proposition",
                    "included": True,
                    "order": 2,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "outcomes",
                    "title": "Results & Metrics",
                    "included": True,
                    "order": 3,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "stakeholders",
                    "title": "Market Validation",
                    "included": True,
                    "order": 4,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "risks",
                    "title": "Risk Analysis",
                    "included": True,
                    "order": 5,
                    "auto_populate": True,
                    "required": False
                },
                {
                    "section_id": "recommendations",
                    "title": "Strategic Recommendations",
                    "included": True,
                    "order": 6,
                    "auto_populate": False,
                    "required": False
                }
            ],
            "formatting": {
                **self._default_formatting(),
                "include_executive_summary": True,
                "confidentiality_footer": "CONFIDENTIAL - For authorized recipients only"
            },
            "created_at": datetime.now(timezone.utc)
        }

    def _create_internal_template(self) -> Dict:
        """Create internal organization template."""
        return {
            "template_id": "internal",
            "name": "Internal Report",
            "description": "Internal organization format for knowledge sharing",
            "is_system": True,
            "sections": [
                {
                    "section_id": "project_identification",
                    "title": "Project Summary",
                    "included": True,
                    "order": 1,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "journey_tracking",
                    "title": "Project Timeline",
                    "included": True,
                    "order": 2,
                    "auto_populate": True,
                    "required": False
                },
                {
                    "section_id": "outcomes",
                    "title": "Outcomes",
                    "included": True,
                    "order": 3,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "learnings",
                    "title": "Lessons Learned",
                    "included": True,
                    "order": 4,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "patterns",
                    "title": "Reusable Patterns",
                    "included": True,
                    "order": 5,
                    "auto_populate": True,
                    "required": False
                },
                {
                    "section_id": "recommendations",
                    "title": "Recommendations",
                    "included": True,
                    "order": 6,
                    "auto_populate": False,
                    "required": False
                }
            ],
            "formatting": {
                **self._default_formatting(),
                "confidentiality_footer": "INTERNAL USE ONLY"
            },
            "created_at": datetime.now(timezone.utc)
        }

    def _create_investor_template(self) -> Dict:
        """Create investor pitch companion template."""
        return {
            "template_id": "investor",
            "name": "Investor Brief",
            "description": "Pitch deck companion for investor discussions",
            "is_system": True,
            "sections": [
                {
                    "section_id": "project_identification",
                    "title": "Opportunity Overview",
                    "included": True,
                    "order": 1,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "vision",
                    "title": "Problem & Solution",
                    "included": True,
                    "order": 2,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "stakeholders",
                    "title": "Market Validation",
                    "included": True,
                    "order": 3,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "hypothesis_outcomes",
                    "title": "Validation Status",
                    "included": True,
                    "order": 4,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "risks",
                    "title": "Risk Mitigation",
                    "included": True,
                    "order": 5,
                    "auto_populate": True,
                    "required": False
                },
                {
                    "section_id": "recommendations",
                    "title": "Investment Thesis",
                    "included": True,
                    "order": 6,
                    "auto_populate": False,
                    "required": False
                }
            ],
            "formatting": {
                **self._default_formatting(),
                "include_executive_summary": True,
                "confidentiality_footer": "CONFIDENTIAL - Investment Materials"
            },
            "created_at": datetime.now(timezone.utc)
        }

    def _create_grant_template(self) -> Dict:
        """Create grant application template."""
        return {
            "template_id": "grant",
            "name": "Grant Application",
            "description": "Grant application format with research focus",
            "is_system": True,
            "sections": [
                {
                    "section_id": "project_identification",
                    "title": "Project Description",
                    "included": True,
                    "order": 1,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "vision",
                    "title": "Problem Statement & Objectives",
                    "included": True,
                    "order": 2,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "methodology",
                    "title": "Approach & Methodology",
                    "included": True,
                    "order": 3,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "hypothesis_outcomes",
                    "title": "Expected Outcomes",
                    "included": True,
                    "order": 4,
                    "auto_populate": True,
                    "required": True
                },
                {
                    "section_id": "risks",
                    "title": "Risk Assessment",
                    "included": True,
                    "order": 5,
                    "auto_populate": True,
                    "required": False
                },
                {
                    "section_id": "stakeholders",
                    "title": "Stakeholder Impact",
                    "included": True,
                    "order": 6,
                    "auto_populate": True,
                    "required": False
                },
                {
                    "section_id": "learnings",
                    "title": "Broader Impacts",
                    "included": True,
                    "order": 7,
                    "auto_populate": True,
                    "required": False
                }
            ],
            "formatting": {
                **self._default_formatting(),
                "include_toc": True
            },
            "created_at": datetime.now(timezone.utc)
        }
