"""
InDE MVP v3.0.3 - IKF Contribution Preparer
Produces IKF-compatible knowledge packages from generalized data.

5 Package Types:
1. Temporal Benchmark - Velocity metrics, phase durations
2. Pattern Contribution - IML patterns with temporal enrichment
3. Risk Intelligence - Anonymized risk detections, RVE methodologies
4. Effectiveness Metrics - Scorecard metrics at organizational level
5. Retrospective Wisdom - Learning patterns from completed retrospectives

CRITICAL: ALL packages require human review before IKF_READY status.
Packages stored locally — NOT transmitted until v3.2 IKF federation.

All timestamps use ISO 8601 format for IKF compatibility.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uuid

from config import IKF_PACKAGE_TYPES, IKF_CONTRIBUTION_STATUS

from .generalization_engine import GeneralizationEngine


class IKFContributionPreparer:
    """
    Produces IKF-compatible knowledge packages.
    ALL packages require human review before IKF_READY status.
    Packages stored locally — NOT transmitted until v3.2 IKF federation.
    """

    def __init__(self, db, generalization_engine: GeneralizationEngine = None):
        """
        Initialize IKF contribution preparer.

        Args:
            db: Database instance
            generalization_engine: Optional GeneralizationEngine instance
        """
        self.db = db
        self.generalization_engine = generalization_engine or GeneralizationEngine(db)
        self.package_types = IKF_PACKAGE_TYPES

    def prepare_contribution(self, pursuit_id: str, package_type: str,
                              user_id: str = None) -> Dict:
        """
        Generate a contribution package of the specified type.

        Workflow:
        1. Gather raw data from pursuit
        2. Run through GeneralizationEngine
        3. Format to IKF API contract schema
        4. Store as DRAFT in ikf_contributions collection
        5. Return preview for human review

        Args:
            pursuit_id: Pursuit ID (None for portfolio-level contributions)
            package_type: One of IKF_PACKAGE_TYPES
            user_id: User ID for portfolio-level contributions

        Returns:
            {
                'contribution_id': str,
                'package_type': str,
                'preview': {
                    'original_summary': str,
                    'generalized_summary': str,
                    'side_by_side': [{field, original, generalized}]
                },
                'warnings': [str],
                'status': 'DRAFT'
            }
        """
        if package_type not in self.package_types:
            return {"error": f"Invalid package type: {package_type}"}

        # Get user_id from pursuit if not provided
        if not user_id and pursuit_id:
            pursuit = self.db.get_pursuit(pursuit_id)
            if pursuit:
                user_id = pursuit.get("user_id")

        # Gather raw data based on package type
        raw_data = self._gather_raw_data(pursuit_id, package_type, user_id)

        if not raw_data:
            return {"error": "Insufficient data for contribution"}

        # Get context
        context = self._get_context(pursuit_id, user_id)

        # Run generalization
        generalization_result = self.generalization_engine.generalize(raw_data, context)

        # Format to IKF schema
        ikf_package = self._format_to_ikf_schema(
            generalization_result,
            package_type,
            pursuit_id,
            user_id,
            context
        )

        # Generate preview
        preview = self._generate_preview(raw_data, generalization_result)

        # Store as DRAFT
        contribution_id = self.db.create_ikf_contribution({
            "contribution_id": str(uuid.uuid4()),
            "user_id": user_id,
            "pursuit_id": pursuit_id,
            "package_type": package_type,
            "generalization_level": 3,  # Default level
            "original_data_ref": generalization_result["original_hash"],
            "generalized_content": ikf_package["content"],
            "metadata": ikf_package["metadata"]
        })

        return {
            "contribution_id": contribution_id,
            "package_type": package_type,
            "preview": preview,
            "warnings": generalization_result.get("warnings", []),
            "confidence": generalization_result.get("confidence", 0.8),
            "status": "DRAFT",
            "transformations_log": generalization_result.get("transformations_log", [])
        }

    def review_contribution(self, contribution_id: str, approved: bool,
                            reviewer_id: str, notes: str = None) -> Dict:
        """
        Process human review decision.

        If approved: status DRAFT → REVIEWED → IKF_READY
        If rejected: status → REJECTED with notes

        CRITICAL: No automatic approval. This method MUST be called by
        explicit user action through the UI or chat command.

        Args:
            contribution_id: Contribution ID
            approved: Whether contribution is approved
            reviewer_id: ID of reviewing user
            notes: Optional review notes

        Returns:
            {
                'contribution_id': str,
                'status': str,
                'reviewed_by': str,
                'reviewed_at': ISO 8601
            }
        """
        contribution = self.db.get_ikf_contribution(contribution_id)

        if not contribution:
            return {"error": "Contribution not found"}

        if contribution.get("status") not in ["DRAFT", "REVIEWED"]:
            return {"error": f"Cannot review contribution in {contribution.get('status')} status"}

        if approved:
            success = self.db.approve_ikf_contribution(
                contribution_id, reviewer_id, notes
            )
            new_status = "IKF_READY"
        else:
            success = self.db.reject_ikf_contribution(
                contribution_id, reviewer_id, notes or "No reason provided"
            )
            new_status = "REJECTED"

        if not success:
            return {"error": "Failed to update contribution status"}

        # Update pursuit IKF status if applicable
        pursuit_id = contribution.get("pursuit_id")
        if pursuit_id and approved:
            self.db.update_pursuit_ikf_status(pursuit_id, "CONTRIBUTED")

        return {
            "contribution_id": contribution_id,
            "status": new_status,
            "reviewed_by": reviewer_id,
            "reviewed_at": datetime.now(timezone.utc).isoformat() + 'Z'
        }

    def get_pending_reviews(self, user_id: str) -> List[Dict]:
        """Return all contributions in DRAFT status awaiting review."""
        return self.db.get_pending_ikf_reviews(user_id)

    def get_contribution_history(self, user_id: str) -> List[Dict]:
        """Return all contributions with their statuses."""
        return self.db.get_user_ikf_contributions(user_id)

    def get_contribution_preview(self, contribution_id: str) -> Dict:
        """Get detailed preview of a contribution for review."""
        contribution = self.db.get_ikf_contribution(contribution_id)

        if not contribution:
            return {"error": "Contribution not found"}

        return {
            "contribution_id": contribution_id,
            "package_type": contribution.get("package_type"),
            "status": contribution.get("status"),
            "created_at": contribution.get("created_at"),
            "metadata": contribution.get("metadata", {}),
            "generalized_content": contribution.get("generalized_content", {}),
            "review_status": {
                "reviewed_by": contribution.get("reviewed_by"),
                "approved_at": contribution.get("approved_at"),
                "review_notes": contribution.get("review_notes"),
                "rejection_reason": contribution.get("rejection_reason")
            }
        }

    # =========================================================================
    # DATA GATHERING METHODS
    # =========================================================================

    def _gather_raw_data(self, pursuit_id: str, package_type: str,
                          user_id: str) -> Optional[Dict]:
        """Gather raw data based on package type."""
        gatherers = {
            "temporal_benchmark": self._gather_temporal_benchmark,
            "pattern": self._gather_pattern_data,
            "risk_intelligence": self._gather_risk_intelligence,
            "effectiveness": self._gather_effectiveness_data,
            "retrospective": self._gather_retrospective_data
        }

        gatherer = gatherers.get(package_type)
        if not gatherer:
            return None

        return gatherer(pursuit_id, user_id)

    def _gather_temporal_benchmark(self, pursuit_id: str, user_id: str) -> Optional[Dict]:
        """Gather temporal benchmark data."""
        if not pursuit_id:
            return None

        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return None

        # Get velocity metrics
        velocity = self.db.db.velocity_metrics.find_one(
            {"pursuit_id": pursuit_id},
            sort=[("calculated_at", -1)]
        )

        # Get phase transitions
        transitions = list(
            self.db.db.phase_transitions.find({"pursuit_id": pursuit_id})
        )

        # Get time allocation
        allocation = self.db.db.time_allocations.find_one({"pursuit_id": pursuit_id})

        return {
            "pursuit_title": pursuit.get("title"),
            "methodology": pursuit.get("methodology", "LEAN_STARTUP"),
            "problem_context": pursuit.get("problem_context", {}),
            "velocity": {
                "elements_per_week": velocity.get("elements_per_week") if velocity else 0,
                "status": velocity.get("status") if velocity else "unknown"
            },
            "phase_transitions": [
                {
                    "from_phase": t.get("from_phase"),
                    "to_phase": t.get("to_phase"),
                    "days_in_phase": t.get("days_in_previous_phase", 0)
                }
                for t in transitions
            ],
            "allocation": {
                "total_duration_days": allocation.get("total_duration_days") if allocation else 90
            }
        }

    def _gather_pattern_data(self, pursuit_id: str, user_id: str) -> Optional[Dict]:
        """Gather pattern contribution data."""
        if not pursuit_id:
            return None

        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return None

        # Get patterns associated with pursuit
        patterns = list(
            self.db.db.patterns.find({"source_pursuit_id": pursuit_id}).limit(10)
        )

        # Get pattern effectiveness
        effectiveness = list(
            self.db.db.pattern_effectiveness.find({"pursuit_id": pursuit_id})
        )

        return {
            "pursuit_title": pursuit.get("title"),
            "methodology": pursuit.get("methodology"),
            "problem_context": pursuit.get("problem_context", {}),
            "patterns": [
                {
                    "pattern_type": p.get("pattern_type"),
                    "insight": p.get("insight", {}),
                    "context": p.get("context", {})
                }
                for p in patterns
            ],
            "effectiveness": [
                {
                    "was_applied": e.get("was_applied"),
                    "outcome": e.get("outcome")
                }
                for e in effectiveness
            ]
        }

    def _gather_risk_intelligence(self, pursuit_id: str, user_id: str) -> Optional[Dict]:
        """Gather risk intelligence data."""
        if not pursuit_id:
            return None

        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return None

        # Get risk detections
        detection = self.db.get_latest_risk_detection(pursuit_id)

        # Get risk definitions
        risks = list(
            self.db.db.risk_definitions.find({"pursuit_id": pursuit_id})
        )

        # Get experiments
        experiments = self.db.get_pursuit_experiments(pursuit_id)

        return {
            "pursuit_title": pursuit.get("title"),
            "methodology": pursuit.get("methodology"),
            "problem_context": pursuit.get("problem_context", {}),
            "risk_detection": {
                "overall_risk_level": detection.get("overall_risk_level") if detection else "UNKNOWN",
                "risk_count": detection.get("risk_count") if detection else 0
            },
            "risks": [
                {
                    "risk_type": r.get("risk_type"),
                    "severity": r.get("severity")
                }
                for r in risks
            ],
            "experiments": [
                {
                    "methodology_template": e.get("methodology_template"),
                    "status": e.get("status"),
                    "verdict": e.get("verdict")
                }
                for e in experiments
            ]
        }

    def _gather_effectiveness_data(self, pursuit_id: str, user_id: str) -> Optional[Dict]:
        """Gather effectiveness metrics data (portfolio-level)."""
        if not user_id:
            return None

        # Get portfolio analytics
        analytics = self.db.get_latest_portfolio_analytics(user_id)

        # Get completed pursuits for learning metrics
        completed = list(self.db.db.pursuits.find({
            "user_id": user_id,
            "status": {"$in": ["launched", "integrated", "documented"]}
        }))

        return {
            "portfolio_health": analytics.get("portfolio_health") if analytics else {},
            "velocity_distribution": analytics.get("velocity_distribution") if analytics else {},
            "completed_pursuit_count": len(completed),
            "methodologies_used": list(set(p.get("methodology", "LEAN_STARTUP") for p in completed))
        }

    def _gather_retrospective_data(self, pursuit_id: str, user_id: str) -> Optional[Dict]:
        """Gather retrospective wisdom data."""
        if not pursuit_id:
            return None

        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return None

        # Get retrospective
        retro = self.db.db.retrospectives.find_one({"pursuit_id": pursuit_id})

        if not retro:
            return None

        return {
            "pursuit_title": pursuit.get("title"),
            "terminal_state": pursuit.get("terminal_info", {}).get("terminal_state"),
            "methodology": pursuit.get("methodology"),
            "problem_context": pursuit.get("problem_context", {}),
            "retrospective": {
                "key_learnings": retro.get("key_learnings", []),
                "what_worked": retro.get("what_worked", []),
                "what_didnt_work": retro.get("what_didnt_work", []),
                "recommendations": retro.get("recommendations", [])
            }
        }

    def _get_context(self, pursuit_id: str, user_id: str) -> Dict:
        """Get context for generalization."""
        context = {}

        if pursuit_id:
            pursuit = self.db.get_pursuit(pursuit_id)
            if pursuit:
                context["methodology"] = pursuit.get("methodology", "LEAN_STARTUP")
                problem_context = pursuit.get("problem_context", {})
                context["domain"] = problem_context.get("domain")
                context["innovation_type"] = problem_context.get("innovation_type")

        return context

    def _format_to_ikf_schema(self, generalization_result: Dict,
                               package_type: str, pursuit_id: str,
                               user_id: str, context: Dict) -> Dict:
        """Format generalized data to IKF API contract schema."""
        generalized = generalization_result.get("generalized", {})

        # Extract or build metadata
        ikf_context = generalized.get("ikf_context", {})

        metadata = {
            "industry_naics": ikf_context.get("industry_naics", "99"),
            "methodology_archetype": ikf_context.get("methodology_archetype", context.get("methodology", "LEAN_STARTUP")),
            "innovation_type": ikf_context.get("innovation_type", "PRODUCT"),
            "market_maturity": ikf_context.get("market_maturity", "EMERGING"),
            "regulatory_complexity": ikf_context.get("regulatory_complexity", "STANDARD")
        }

        # Build content based on package type
        content = self._build_package_content(generalized, package_type)

        return {
            "metadata": metadata,
            "content": content
        }

    def _build_package_content(self, generalized: Dict, package_type: str) -> Dict:
        """Build package content based on type."""
        if package_type == "temporal_benchmark":
            return {
                "velocity_metrics": generalized.get("velocity", {}),
                "phase_durations": generalized.get("phase_transitions", []),
                "allocation_pattern": generalized.get("allocation", {})
            }

        elif package_type == "pattern":
            return {
                "patterns": generalized.get("patterns", []),
                "extracted_patterns": generalized.get("extracted_patterns", []),
                "effectiveness_data": generalized.get("effectiveness", [])
            }

        elif package_type == "risk_intelligence":
            return {
                "risk_profile": generalized.get("risk_detection", {}),
                "risk_types": generalized.get("risks", []),
                "validation_outcomes": generalized.get("experiments", [])
            }

        elif package_type == "effectiveness":
            return {
                "portfolio_metrics": generalized.get("portfolio_health", {}),
                "velocity_patterns": generalized.get("velocity_distribution", {}),
                "pursuit_count": generalized.get("completed_pursuit_count", 0)
            }

        elif package_type == "retrospective":
            return {
                "terminal_outcome": generalized.get("terminal_state"),
                "learnings": generalized.get("retrospective", {}),
                "extracted_patterns": generalized.get("extracted_patterns", [])
            }

        return {}

    def _generate_preview(self, raw_data: Dict,
                           generalization_result: Dict) -> Dict:
        """Generate side-by-side preview for human review."""
        generalized = generalization_result.get("generalized", {})

        # Build original summary
        original_summary = self._summarize_data(raw_data)
        generalized_summary = self._summarize_data(generalized)

        # Build side-by-side comparison
        side_by_side = []

        # Compare key fields
        for key in ["pursuit_title", "methodology", "problem_context"]:
            if key in raw_data or key in generalized:
                side_by_side.append({
                    "field": key,
                    "original": str(raw_data.get(key, "N/A"))[:100],
                    "generalized": str(generalized.get(key, "N/A"))[:100]
                })

        return {
            "original_summary": original_summary,
            "generalized_summary": generalized_summary,
            "side_by_side": side_by_side,
            "transformations_applied": len(generalization_result.get("transformations_log", []))
        }

    def _summarize_data(self, data: Dict) -> str:
        """Generate text summary of data."""
        parts = []

        if "pursuit_title" in data:
            parts.append(f"Title: {data['pursuit_title'][:50]}")
        if "methodology" in data:
            parts.append(f"Methodology: {data['methodology']}")
        if "terminal_state" in data:
            parts.append(f"Outcome: {data['terminal_state']}")

        return " | ".join(parts) if parts else "No summary available"

    def get_package_type_info(self, package_type: str) -> Dict:
        """Get information about a package type."""
        info = {
            "temporal_benchmark": {
                "name": "Temporal Benchmark",
                "description": "Velocity metrics, phase durations, and time allocations",
                "ikf_destination": "IKF Benchmarking Engine",
                "required_data": ["velocity_metrics", "phase_transitions", "time_allocation"]
            },
            "pattern": {
                "name": "Pattern Contribution",
                "description": "IML patterns with temporal enrichment and effectiveness data",
                "ikf_destination": "IKF Pattern Synthesis Engine",
                "required_data": ["patterns", "pattern_effectiveness"]
            },
            "risk_intelligence": {
                "name": "Risk Intelligence",
                "description": "Anonymized risk detections and RVE validation outcomes",
                "ikf_destination": "IKF Pattern Synthesis Engine",
                "required_data": ["risk_detections", "experiments"]
            },
            "effectiveness": {
                "name": "Effectiveness Metrics",
                "description": "Organizational-level innovation effectiveness scorecard",
                "ikf_destination": "IKF Benchmarking Engine",
                "required_data": ["portfolio_analytics", "completed_pursuits"]
            },
            "retrospective": {
                "name": "Retrospective Wisdom",
                "description": "Learning patterns from completed retrospectives",
                "ikf_destination": "IKF Pattern Synthesis Engine",
                "required_data": ["retrospective", "terminal_state"]
            }
        }

        return info.get(package_type, {"error": "Unknown package type"})
