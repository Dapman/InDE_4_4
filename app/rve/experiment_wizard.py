"""
InDE MVP v3.0.2 - Experiment Design Wizard
ODICM-guided experiment design with methodology templates.

Features:
- Methodology-specific experiment templates
- Guided experiment design through conversation
- Success criteria definition
- Timeline and resource estimation
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

from config import (
    RVE_CONFIG, RVE_EXPERIMENT_TEMPLATES,
    EXPERIMENT_STATUS
)


class ExperimentDesignWizard:
    """
    Guide innovators through designing validation experiments.

    Provides methodology-specific templates and conversational
    guidance for experiment design.
    """

    # Template definitions for each experiment type
    EXPERIMENT_TEMPLATES = {
        # LEAN_STARTUP templates
        "landing_page_test": {
            "title": "Landing Page Test",
            "description": "Test demand by creating a landing page and measuring conversion",
            "methodology": "landing_page_test",
            "typical_duration_days": 14,
            "min_sample_size": 100,
            "suggested_metrics": ["conversion_rate", "signup_rate", "bounce_rate"],
            "resources_needed": ["landing page builder", "analytics tool", "traffic source"],
            "steps": [
                "Define value proposition",
                "Create landing page with clear CTA",
                "Set up conversion tracking",
                "Drive traffic (ads, social, email)",
                "Collect and analyze results"
            ]
        },
        "concierge_mvp": {
            "title": "Concierge MVP",
            "description": "Manually deliver the service to validate the core value proposition",
            "methodology": "concierge_mvp",
            "typical_duration_days": 30,
            "min_sample_size": 5,
            "suggested_metrics": ["retention_rate", "satisfaction_score", "willingness_to_pay"],
            "resources_needed": ["direct customer access", "time commitment"],
            "steps": [
                "Identify early adopter customers",
                "Manually deliver the proposed service",
                "Track customer feedback and behavior",
                "Measure value delivered",
                "Document learnings"
            ]
        },
        "smoke_test": {
            "title": "Smoke Test",
            "description": "Gauge interest before building - measure intent without product",
            "methodology": "smoke_test",
            "typical_duration_days": 7,
            "min_sample_size": 50,
            "suggested_metrics": ["intent_rate", "email_signups", "preorder_count"],
            "resources_needed": ["marketing channel", "landing page"],
            "steps": [
                "Create marketing message",
                "Set up capture mechanism (email, preorder)",
                "Launch to target audience",
                "Measure interest signals",
                "Analyze results"
            ]
        },
        "wizard_of_oz": {
            "title": "Wizard of Oz Test",
            "description": "Simulate automated functionality manually behind the scenes",
            "methodology": "wizard_of_oz",
            "typical_duration_days": 21,
            "min_sample_size": 10,
            "suggested_metrics": ["task_completion", "user_satisfaction", "feasibility_score"],
            "resources_needed": ["backend operator", "frontend interface"],
            "steps": [
                "Build user-facing interface",
                "Set up manual backend process",
                "Recruit test users",
                "Deliver experience manually",
                "Measure user perception and satisfaction"
            ]
        },
        "split_test": {
            "title": "A/B Split Test",
            "description": "Compare two variants to determine which performs better",
            "methodology": "split_test",
            "typical_duration_days": 14,
            "min_sample_size": 200,
            "suggested_metrics": ["conversion_rate", "engagement_rate", "click_through_rate"],
            "resources_needed": ["A/B testing tool", "traffic source"],
            "steps": [
                "Define hypothesis",
                "Create variant A and B",
                "Split traffic equally",
                "Run test until statistical significance",
                "Declare winner"
            ]
        },

        # DESIGN_THINKING templates
        "user_interview_series": {
            "title": "User Interview Series",
            "description": "Conduct structured interviews to understand user needs",
            "methodology": "user_interviews",
            "typical_duration_days": 14,
            "min_sample_size": 8,
            "suggested_metrics": ["pain_point_frequency", "needs_validation", "quote_themes"],
            "resources_needed": ["interview guide", "recording setup", "participant recruitment"],
            "steps": [
                "Develop interview guide",
                "Recruit target participants",
                "Conduct interviews",
                "Transcribe and code responses",
                "Synthesize findings"
            ]
        },
        "prototype_test": {
            "title": "Prototype Test",
            "description": "Test a prototype with users to validate usability and value",
            "methodology": "prototype_test",
            "typical_duration_days": 10,
            "min_sample_size": 5,
            "suggested_metrics": ["task_success", "time_on_task", "satisfaction", "errors"],
            "resources_needed": ["prototype", "test script", "participants"],
            "steps": [
                "Create clickable prototype",
                "Develop test scenarios",
                "Recruit participants",
                "Run moderated tests",
                "Document findings"
            ]
        },
        "observation_study": {
            "title": "Observation Study",
            "description": "Observe users in their natural context to understand behavior",
            "methodology": "observation_study",
            "typical_duration_days": 7,
            "min_sample_size": 5,
            "suggested_metrics": ["behavior_patterns", "pain_points_observed", "workarounds"],
            "resources_needed": ["observation protocol", "note-taking system"],
            "steps": [
                "Define observation goals",
                "Get access to context",
                "Observe without interfering",
                "Document behaviors",
                "Analyze patterns"
            ]
        },
        "co_creation_session": {
            "title": "Co-Creation Session",
            "description": "Collaborate with users to design solutions together",
            "methodology": "co_creation_session",
            "typical_duration_days": 3,
            "min_sample_size": 6,
            "suggested_metrics": ["ideas_generated", "feasibility_scores", "user_enthusiasm"],
            "resources_needed": ["facilitation skills", "workshop materials", "participants"],
            "steps": [
                "Define session objectives",
                "Prepare materials and activities",
                "Facilitate session",
                "Capture outputs",
                "Synthesize into insights"
            ]
        },
        "diary_study": {
            "title": "Diary Study",
            "description": "Have users log their experiences over time",
            "methodology": "diary_study",
            "typical_duration_days": 14,
            "min_sample_size": 10,
            "suggested_metrics": ["frequency_of_issue", "context_patterns", "emotional_response"],
            "resources_needed": ["diary template", "reminder system", "participants"],
            "steps": [
                "Design diary format",
                "Brief participants",
                "Collect entries over study period",
                "Conduct follow-up interviews",
                "Analyze longitudinal data"
            ]
        },

        # STAGE_GATE templates
        "technical_feasibility": {
            "title": "Technical Feasibility Study",
            "description": "Assess whether the technical solution can be built",
            "methodology": "technical_feasibility",
            "typical_duration_days": 21,
            "min_sample_size": 1,
            "suggested_metrics": ["feasibility_score", "technical_risks", "resource_estimate"],
            "resources_needed": ["technical team", "research access"],
            "steps": [
                "Define technical requirements",
                "Research available technologies",
                "Build proof of concept if needed",
                "Assess risks and gaps",
                "Document feasibility conclusion"
            ]
        },
        "market_assessment": {
            "title": "Market Assessment",
            "description": "Analyze market size, trends, and competitive landscape",
            "methodology": "market_assessment",
            "typical_duration_days": 14,
            "min_sample_size": 10,
            "suggested_metrics": ["market_size", "growth_rate", "competitive_intensity"],
            "resources_needed": ["market research tools", "industry reports"],
            "steps": [
                "Define market boundaries",
                "Gather market size data",
                "Analyze competitive landscape",
                "Identify trends and drivers",
                "Synthesize into assessment"
            ]
        },
        "financial_analysis": {
            "title": "Financial Analysis",
            "description": "Model the financial viability of the pursuit",
            "methodology": "financial_analysis",
            "typical_duration_days": 7,
            "min_sample_size": 1,
            "suggested_metrics": ["unit_economics", "payback_period", "roi_potential"],
            "resources_needed": ["financial modeling skills", "market data"],
            "steps": [
                "Define revenue model",
                "Estimate costs",
                "Build financial model",
                "Run scenarios",
                "Determine viability thresholds"
            ]
        },
        "competitive_scan": {
            "title": "Competitive Scan",
            "description": "Map and analyze competitive alternatives",
            "methodology": "competitive_scan",
            "typical_duration_days": 7,
            "min_sample_size": 5,
            "suggested_metrics": ["competitor_count", "differentiation_score", "threat_level"],
            "resources_needed": ["research tools", "competitor access"],
            "steps": [
                "Identify competitors",
                "Analyze their offerings",
                "Map positioning",
                "Identify differentiation opportunities",
                "Assess competitive threats"
            ]
        },
        "regulatory_review": {
            "title": "Regulatory Review",
            "description": "Assess regulatory requirements and compliance needs",
            "methodology": "regulatory_review",
            "typical_duration_days": 14,
            "min_sample_size": 1,
            "suggested_metrics": ["compliance_requirements", "regulatory_risk", "timeline_impact"],
            "resources_needed": ["legal/regulatory expertise", "regulatory documents"],
            "steps": [
                "Identify applicable regulations",
                "Map compliance requirements",
                "Assess current compliance status",
                "Identify gaps and risks",
                "Develop compliance plan"
            ]
        }
    }

    def __init__(self, db, llm=None):
        """
        Initialize the experiment wizard.

        Args:
            db: Database instance
            llm: Optional LLM interface for guided design
        """
        self.db = db
        self.llm = llm
        self.config = RVE_CONFIG

    def get_available_templates(self, methodology: str = None) -> List[Dict]:
        """
        Get available experiment templates.

        Args:
            methodology: Optional filter by methodology (LEAN_STARTUP, DESIGN_THINKING, STAGE_GATE)

        Returns:
            List of template summaries
        """
        templates = []

        for template_key, template in self.EXPERIMENT_TEMPLATES.items():
            # Filter by methodology if specified
            if methodology:
                method_templates = RVE_EXPERIMENT_TEMPLATES.get(methodology, [])
                if template_key not in method_templates:
                    continue

            templates.append({
                "key": template_key,
                "title": template.get("title"),
                "description": template.get("description"),
                "typical_duration_days": template.get("typical_duration_days"),
                "min_sample_size": template.get("min_sample_size")
            })

        return templates

    def get_template(self, template_key: str) -> Optional[Dict]:
        """Get full template details."""
        return self.EXPERIMENT_TEMPLATES.get(template_key)

    def suggest_experiment_for_risk(self, risk_id: str,
                                     methodology: str = None) -> Dict:
        """
        Suggest an experiment type based on risk characteristics.

        Args:
            risk_id: Risk ID to suggest experiment for
            methodology: Optional methodology preference

        Returns:
            Dict with suggested template and rationale
        """
        risk = self.db.get_risk_definition(risk_id)
        if not risk:
            raise ValueError(f"Risk not found: {risk_id}")

        category = risk.get("risk_category", "MARKET")
        priority = risk.get("validation_priority", "MEDIUM")

        # Suggestion logic based on risk category
        category_suggestions = {
            "MARKET": ["landing_page_test", "user_interview_series", "smoke_test"],
            "TECHNICAL": ["technical_feasibility", "prototype_test", "wizard_of_oz"],
            "RESOURCE": ["financial_analysis", "concierge_mvp"],
            "REGULATORY": ["regulatory_review"],
            "TIMING": ["market_assessment", "competitive_scan"]
        }

        # Get suggested templates
        suggested_keys = category_suggestions.get(category, ["user_interview_series"])

        # If methodology specified, filter to matching templates
        if methodology:
            method_templates = RVE_EXPERIMENT_TEMPLATES.get(methodology, [])
            suggested_keys = [k for k in suggested_keys if k in method_templates] or suggested_keys

        # Get first suggestion
        primary_key = suggested_keys[0] if suggested_keys else "user_interview_series"
        primary_template = self.EXPERIMENT_TEMPLATES.get(primary_key, {})

        return {
            "primary_suggestion": {
                "key": primary_key,
                "template": primary_template
            },
            "alternatives": [
                {"key": k, "template": self.EXPERIMENT_TEMPLATES.get(k)}
                for k in suggested_keys[1:3]  # Up to 2 alternatives
            ],
            "rationale": f"Based on {category} risk category, {primary_template.get('title')} is recommended.",
            "risk_category": category,
            "risk_priority": priority
        }

    def design_experiment(self, risk_id: str, pursuit_id: str,
                          template_key: str,
                          customizations: Dict = None) -> str:
        """
        Create a designed experiment from a template.

        Args:
            risk_id: Risk this experiment validates
            pursuit_id: Pursuit ID
            template_key: Template to use
            customizations: Optional customizations to template defaults

        Returns:
            experiment_id of created experiment
        """
        if not self.config.get("enable_experiment_wizard", True):
            raise ValueError("Experiment wizard is disabled")

        risk = self.db.get_risk_definition(risk_id)
        if not risk:
            raise ValueError(f"Risk not found: {risk_id}")

        template = self.EXPERIMENT_TEMPLATES.get(template_key)
        if not template:
            raise ValueError(f"Template not found: {template_key}")

        customizations = customizations or {}

        # Build experiment record
        start_date = datetime.now(timezone.utc)
        duration = customizations.get("duration_days", template.get("typical_duration_days", 14))
        target_end = start_date + timedelta(days=duration)

        experiment_record = {
            "pursuit_id": pursuit_id,
            "risk_id": risk_id,
            "template_key": template_key,
            "title": customizations.get("title", template.get("title")),
            "description": customizations.get("description", template.get("description")),
            "methodology": template.get("methodology"),
            "methodology_template": template_key,
            "status": "DESIGNED",

            # Design details
            "target_sample_size": customizations.get("sample_size", template.get("min_sample_size")),
            "success_criteria": customizations.get("success_criteria", []),
            "metrics_to_track": customizations.get("metrics", template.get("suggested_metrics", [])),
            "resources_needed": customizations.get("resources", template.get("resources_needed", [])),
            "steps": customizations.get("steps", template.get("steps", [])),

            # Timeline
            "planned_duration_days": duration,
            "planned_start": start_date.isoformat() + 'Z',
            "planned_end": target_end.isoformat() + 'Z',
            "start_date": None,
            "completion_date": None,

            # Results tracking
            "results": None,
            "evidence_id": None,
            "has_evidence": False
        }

        experiment_id = self.db.create_validation_experiment(experiment_record)

        # Link experiment to risk
        self.db.update_risk_definition(risk_id, {
            "experiment_ids": risk.get("experiment_ids", []) + [experiment_id]
        })

        # Update pursuit RVE status
        rve_status = self.db.get_pursuit_rve_status(pursuit_id)
        if rve_status:
            pending = rve_status.get("pending_experiments", [])
            pending.append(experiment_id)
            rve_status["pending_experiments"] = pending
            self.db.update_pursuit_rve_status(pursuit_id, rve_status)

        # Log activity
        self.db.log_activity(
            pursuit_id=pursuit_id,
            activity_type="experiment_designed",
            description=f"Designed experiment: {experiment_record.get('title')}",
            metadata={
                "experiment_id": experiment_id,
                "risk_id": risk_id,
                "template": template_key
            }
        )

        return experiment_id

    def start_experiment(self, experiment_id: str) -> bool:
        """
        Mark an experiment as started.

        Args:
            experiment_id: Experiment to start

        Returns:
            True if successful
        """
        experiment = self.db.get_validation_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment not found: {experiment_id}")

        success = self.db.start_experiment(experiment_id)

        if success:
            # Move from pending to active
            pursuit_id = experiment.get("pursuit_id")
            rve_status = self.db.get_pursuit_rve_status(pursuit_id)
            if rve_status:
                pending = rve_status.get("pending_experiments", [])
                active = rve_status.get("active_experiments", [])
                if experiment_id in pending:
                    pending.remove(experiment_id)
                if experiment_id not in active:
                    active.append(experiment_id)
                rve_status["pending_experiments"] = pending
                rve_status["active_experiments"] = active
                self.db.update_pursuit_rve_status(pursuit_id, rve_status)

            # Log activity
            self.db.log_activity(
                pursuit_id=pursuit_id,
                activity_type="experiment_started",
                description=f"Started experiment: {experiment.get('title')}",
                metadata={"experiment_id": experiment_id}
            )

        return success

    def complete_experiment(self, experiment_id: str, results: Dict) -> Dict:
        """
        Mark an experiment as complete with results.

        Args:
            experiment_id: Experiment to complete
            results: Results data

        Returns:
            Dict with completion details
        """
        experiment = self.db.get_validation_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment not found: {experiment_id}")

        success = self.db.complete_experiment(experiment_id, results)

        if success:
            # Move from active to completed
            pursuit_id = experiment.get("pursuit_id")
            rve_status = self.db.get_pursuit_rve_status(pursuit_id)
            if rve_status:
                active = rve_status.get("active_experiments", [])
                completed = rve_status.get("completed_experiments", [])
                if experiment_id in active:
                    active.remove(experiment_id)
                if experiment_id not in completed:
                    completed.append(experiment_id)
                rve_status["active_experiments"] = active
                rve_status["completed_experiments"] = completed
                self.db.update_pursuit_rve_status(pursuit_id, rve_status)

            # Log activity
            self.db.log_activity(
                pursuit_id=pursuit_id,
                activity_type="experiment_completed",
                description=f"Completed experiment: {experiment.get('title')}",
                metadata={
                    "experiment_id": experiment_id,
                    "results_summary": str(results)[:100]
                }
            )

        return {
            "success": success,
            "experiment_id": experiment_id,
            "ready_for_assessment": True,
            "message": "Experiment completed. Results ready for three-zone assessment."
        }

    def get_experiment_status(self, experiment_id: str) -> Dict:
        """Get current status of an experiment."""
        experiment = self.db.get_validation_experiment(experiment_id)
        if not experiment:
            return {"error": "Experiment not found"}

        return {
            "experiment_id": experiment_id,
            "title": experiment.get("title"),
            "status": experiment.get("status"),
            "template": experiment.get("template_key"),
            "target_sample": experiment.get("target_sample_size"),
            "metrics": experiment.get("metrics_to_track"),
            "has_evidence": experiment.get("has_evidence", False),
            "started": experiment.get("start_date") is not None,
            "completed": experiment.get("status") == "COMPLETE"
        }

    def get_pursuit_experiments(self, pursuit_id: str) -> Dict:
        """Get all experiments for a pursuit with status summary."""
        experiments = self.db.get_pursuit_experiments(pursuit_id)

        by_status = {"DESIGNED": [], "IN_PROGRESS": [], "COMPLETE": [], "ABANDONED": []}
        for exp in experiments:
            status = exp.get("status", "DESIGNED")
            by_status[status].append({
                "experiment_id": exp.get("experiment_id"),
                "title": exp.get("title"),
                "risk_id": exp.get("risk_id"),
                "has_evidence": exp.get("has_evidence", False)
            })

        return {
            "total": len(experiments),
            "by_status": by_status,
            "needs_attention": [
                exp for exp in experiments
                if exp.get("status") == "COMPLETE" and not exp.get("has_evidence")
            ]
        }

    def generate_design_prompt(self, risk: Dict, template: Dict) -> str:
        """
        Generate a coaching prompt to guide experiment design.

        Args:
            risk: Risk being validated
            template: Template being used

        Returns:
            Coaching prompt for ODICM
        """
        return f"""Let's design a validation experiment for this risk.

**Risk:** {risk.get('risk_parameter', 'Unknown')}
**Template:** {template.get('title')}

I'll help you customize this experiment. Let's start with:

1. **Success Criteria:** What specific outcome would tell you this risk is mitigated?
   (e.g., "At least 30% conversion rate" or "8 out of 10 users complete the task")

2. **Sample Size:** How many participants or data points do you need?
   (Recommended minimum: {template.get('min_sample_size')})

3. **Timeline:** How long do you need to run this?
   (Typical duration: {template.get('typical_duration_days')} days)

What success criteria would you like to define?"""
