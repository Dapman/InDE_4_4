"""
InDE MVP v4.4.0 - Portfolio Dashboard
Org-Level Portfolio Dashboard with 8-panel enterprise intelligence.

Eight Panels:
1. Portfolio Health Summary - Aggregate health across all pursuits
2. Stage Distribution - Pursuits by methodology stage
3. Resource Allocation - Team capacity and allocation metrics
4. Innovation Pipeline - Pipeline flow and velocity metrics
5. Risk Radar - Aggregated risk signals across portfolio
6. Convergence Insights - Coaching convergence patterns
7. Talent & Formation - IDTFS insights and formation activity
8. Momentum Health - Org-level momentum analytics (v4.4)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

from core.database import db
from core.config import METHODOLOGY_ARCHETYPES

logger = logging.getLogger("inde.portfolio.dashboard")


# =============================================================================
# ENUMERATIONS
# =============================================================================

class PanelType(str, Enum):
    """Types of dashboard panels."""
    PORTFOLIO_HEALTH = "portfolio_health"
    STAGE_DISTRIBUTION = "stage_distribution"
    RESOURCE_ALLOCATION = "resource_allocation"
    INNOVATION_PIPELINE = "innovation_pipeline"
    RISK_RADAR = "risk_radar"
    CONVERGENCE_INSIGHTS = "convergence_insights"
    TALENT_FORMATION = "talent_formation"
    MOMENTUM_HEALTH = "momentum_health"  # v4.4: Org-level momentum analytics


class HealthLevel(str, Enum):
    """Health level categories."""
    EXCELLENT = "excellent"
    GOOD = "good"
    AT_RISK = "at_risk"
    CRITICAL = "critical"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DashboardPanel:
    """A dashboard panel with computed data."""
    panel_type: PanelType
    title: str
    data: Dict[str, Any]
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cache_duration_seconds: int = 300  # 5 minute cache

    def to_dict(self) -> Dict:
        return {
            "panel_type": self.panel_type.value,
            "title": self.title,
            "data": self.data,
            "updated_at": self.updated_at.isoformat(),
            "cache_duration_seconds": self.cache_duration_seconds
        }


@dataclass
class PortfolioHealthMetrics:
    """Aggregate portfolio health metrics."""
    total_pursuits: int
    active_pursuits: int
    average_health_score: float
    health_distribution: Dict[str, int]
    trending_up: int
    trending_down: int
    stalled_pursuits: int

    def to_dict(self) -> Dict:
        return {
            "total_pursuits": self.total_pursuits,
            "active_pursuits": self.active_pursuits,
            "average_health_score": round(self.average_health_score, 3),
            "health_distribution": self.health_distribution,
            "trending_up": self.trending_up,
            "trending_down": self.trending_down,
            "stalled_pursuits": self.stalled_pursuits
        }


# =============================================================================
# PORTFOLIO DASHBOARD
# =============================================================================

class PortfolioDashboard:
    """
    Generates org-level portfolio dashboard with 7 intelligence panels.

    Provides enterprise visibility into innovation health, pipeline flow,
    risk signals, and team formation activity.
    """

    def __init__(self):
        self._cache: Dict[str, DashboardPanel] = {}
        self._cache_timestamps: Dict[str, datetime] = {}

    def get_full_dashboard(self, org_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get complete dashboard with all 7 panels.

        Returns cached data if available and not expired.
        """
        panels = {}

        # Generate each panel
        panel_generators = [
            (PanelType.PORTFOLIO_HEALTH, self._generate_portfolio_health),
            (PanelType.STAGE_DISTRIBUTION, self._generate_stage_distribution),
            (PanelType.RESOURCE_ALLOCATION, self._generate_resource_allocation),
            (PanelType.INNOVATION_PIPELINE, self._generate_innovation_pipeline),
            (PanelType.RISK_RADAR, self._generate_risk_radar),
            (PanelType.CONVERGENCE_INSIGHTS, self._generate_convergence_insights),
            (PanelType.TALENT_FORMATION, self._generate_talent_formation),
            (PanelType.MOMENTUM_HEALTH, self._generate_momentum_health),  # v4.4
        ]

        for panel_type, generator in panel_generators:
            cache_key = f"{org_id}:{panel_type.value}"

            # Check cache
            if not force_refresh and self._is_cache_valid(cache_key):
                panels[panel_type.value] = self._cache[cache_key].to_dict()
            else:
                panel = generator(org_id)
                self._cache[cache_key] = panel
                self._cache_timestamps[cache_key] = datetime.now(timezone.utc)
                panels[panel_type.value] = panel.to_dict()

        return {
            "org_id": org_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "panels": panels
        }

    def get_panel(self, org_id: str, panel_type: PanelType, force_refresh: bool = False) -> DashboardPanel:
        """Get a specific dashboard panel."""
        cache_key = f"{org_id}:{panel_type.value}"

        if not force_refresh and self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        generators = {
            PanelType.PORTFOLIO_HEALTH: self._generate_portfolio_health,
            PanelType.STAGE_DISTRIBUTION: self._generate_stage_distribution,
            PanelType.RESOURCE_ALLOCATION: self._generate_resource_allocation,
            PanelType.INNOVATION_PIPELINE: self._generate_innovation_pipeline,
            PanelType.RISK_RADAR: self._generate_risk_radar,
            PanelType.CONVERGENCE_INSIGHTS: self._generate_convergence_insights,
            PanelType.TALENT_FORMATION: self._generate_talent_formation,
            PanelType.MOMENTUM_HEALTH: self._generate_momentum_health,  # v4.4
        }

        generator = generators.get(panel_type)
        if not generator:
            raise ValueError(f"Unknown panel type: {panel_type}")

        panel = generator(org_id)
        self._cache[cache_key] = panel
        self._cache_timestamps[cache_key] = datetime.now(timezone.utc)

        return panel

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached panel is still valid."""
        if cache_key not in self._cache:
            return False

        timestamp = self._cache_timestamps.get(cache_key)
        if not timestamp:
            return False

        panel = self._cache[cache_key]
        expiry = timestamp + timedelta(seconds=panel.cache_duration_seconds)

        return datetime.now(timezone.utc) < expiry

    # =========================================================================
    # PANEL 1: PORTFOLIO HEALTH SUMMARY
    # =========================================================================

    def _generate_portfolio_health(self, org_id: str) -> DashboardPanel:
        """
        Generate Portfolio Health Summary panel.

        Aggregates health scores across all pursuits in the organization.
        """
        pursuits = db.get_pursuits_by_org(org_id) or []

        if not pursuits:
            return DashboardPanel(
                panel_type=PanelType.PORTFOLIO_HEALTH,
                title="Portfolio Health Summary",
                data={
                    "metrics": PortfolioHealthMetrics(
                        total_pursuits=0,
                        active_pursuits=0,
                        average_health_score=0.0,
                        health_distribution={},
                        trending_up=0,
                        trending_down=0,
                        stalled_pursuits=0
                    ).to_dict(),
                    "top_performers": [],
                    "needs_attention": []
                }
            )

        # Calculate metrics
        health_scores = []
        health_dist = {"excellent": 0, "good": 0, "at_risk": 0, "critical": 0}
        active_count = 0
        trending_up = 0
        trending_down = 0
        stalled = 0

        top_performers = []
        needs_attention = []

        for pursuit in pursuits:
            status = pursuit.get("status", "")
            health = pursuit.get("health_score", 0.5)
            health_scores.append(health)

            # Count active
            if status in ["active", "in_progress", "planning"]:
                active_count += 1

            # Categorize health
            if health >= 0.8:
                health_dist["excellent"] += 1
                top_performers.append({
                    "pursuit_id": pursuit.get("pursuit_id"),
                    "name": pursuit.get("name", "Unnamed"),
                    "health_score": health
                })
            elif health >= 0.6:
                health_dist["good"] += 1
            elif health >= 0.4:
                health_dist["at_risk"] += 1
                needs_attention.append({
                    "pursuit_id": pursuit.get("pursuit_id"),
                    "name": pursuit.get("name", "Unnamed"),
                    "health_score": health,
                    "reason": "Below optimal health"
                })
            else:
                health_dist["critical"] += 1
                needs_attention.append({
                    "pursuit_id": pursuit.get("pursuit_id"),
                    "name": pursuit.get("name", "Unnamed"),
                    "health_score": health,
                    "reason": "Critical health level"
                })

            # Check trends (simplified - compare to threshold)
            trend = pursuit.get("health_trend", "stable")
            if trend == "improving":
                trending_up += 1
            elif trend == "declining":
                trending_down += 1

            # Check for stalled pursuits (no activity in 14 days)
            last_activity = pursuit.get("last_activity_at")
            if last_activity:
                try:
                    if isinstance(last_activity, str):
                        last_dt = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
                    else:
                        last_dt = last_activity
                    # Ensure timezone-aware comparison
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) - last_dt > timedelta(days=14):
                        stalled += 1
                except (ValueError, AttributeError):
                    pass

        avg_health = sum(health_scores) / len(health_scores) if health_scores else 0.0

        metrics = PortfolioHealthMetrics(
            total_pursuits=len(pursuits),
            active_pursuits=active_count,
            average_health_score=avg_health,
            health_distribution=health_dist,
            trending_up=trending_up,
            trending_down=trending_down,
            stalled_pursuits=stalled
        )

        return DashboardPanel(
            panel_type=PanelType.PORTFOLIO_HEALTH,
            title="Portfolio Health Summary",
            data={
                "metrics": metrics.to_dict(),
                "top_performers": sorted(top_performers, key=lambda x: x["health_score"], reverse=True)[:5],
                "needs_attention": sorted(needs_attention, key=lambda x: x["health_score"])[:5]
            }
        )

    # =========================================================================
    # PANEL 2: STAGE DISTRIBUTION
    # =========================================================================

    def _generate_stage_distribution(self, org_id: str) -> DashboardPanel:
        """
        Generate Stage Distribution panel.

        Shows pursuits distributed across methodology stages.
        """
        pursuits = db.get_pursuits_by_org(org_id) or []

        # Distribution by methodology archetype
        archetype_distribution = {}
        stage_distribution = {}

        for pursuit in pursuits:
            archetype = pursuit.get("methodology_archetype", "lean_startup")
            current_stage = pursuit.get("current_stage", "unknown")

            # Count by archetype
            if archetype not in archetype_distribution:
                archetype_distribution[archetype] = {"count": 0, "stages": {}}
            archetype_distribution[archetype]["count"] += 1

            # Count by stage within archetype
            if current_stage not in archetype_distribution[archetype]["stages"]:
                archetype_distribution[archetype]["stages"][current_stage] = 0
            archetype_distribution[archetype]["stages"][current_stage] += 1

            # Global stage distribution
            if current_stage not in stage_distribution:
                stage_distribution[current_stage] = 0
            stage_distribution[current_stage] += 1

        # Calculate stage progression metrics
        early_stage = sum(stage_distribution.get(s, 0) for s in ["VISION", "EMPATHIZE", "DISCOVERY", "IDEATE"])
        mid_stage = sum(stage_distribution.get(s, 0) for s in ["DE_RISK", "DEFINE", "PROTOTYPE", "SCOPING", "BUILD_CASE"])
        late_stage = sum(stage_distribution.get(s, 0) for s in ["SCALE", "TEST", "DEVELOPMENT", "LAUNCH"])

        return DashboardPanel(
            panel_type=PanelType.STAGE_DISTRIBUTION,
            title="Stage Distribution",
            data={
                "by_archetype": archetype_distribution,
                "global_distribution": stage_distribution,
                "stage_summary": {
                    "early_stage": early_stage,
                    "mid_stage": mid_stage,
                    "late_stage": late_stage
                },
                "total_pursuits": len(pursuits)
            }
        )

    # =========================================================================
    # PANEL 3: RESOURCE ALLOCATION
    # =========================================================================

    def _generate_resource_allocation(self, org_id: str) -> DashboardPanel:
        """
        Generate Resource Allocation panel.

        Shows team capacity and allocation across pursuits.
        """
        pursuits = db.get_pursuits_by_org(org_id) or []

        # Get all team members across pursuits
        all_members = set()
        pursuit_allocations = []
        member_workload = {}

        for pursuit in pursuits:
            team = pursuit.get("sharing", {}).get("team_members", [])
            team_size = len(team)

            for member in team:
                user_id = member.get("user_id")
                if user_id:
                    all_members.add(user_id)
                    if user_id not in member_workload:
                        member_workload[user_id] = 0
                    member_workload[user_id] += 1

            pursuit_allocations.append({
                "pursuit_id": pursuit.get("pursuit_id"),
                "name": pursuit.get("name", "Unnamed"),
                "team_size": team_size,
                "status": pursuit.get("status", "unknown")
            })

        # Calculate capacity metrics
        overloaded_members = [uid for uid, count in member_workload.items() if count > 3]
        underutilized_members = [uid for uid, count in member_workload.items() if count == 1]

        # Get org members for capacity calculation
        org_members = db.get_org_members(org_id) or []
        total_capacity = len(org_members)
        allocated = len(all_members)
        unallocated = total_capacity - allocated

        return DashboardPanel(
            panel_type=PanelType.RESOURCE_ALLOCATION,
            title="Resource Allocation",
            data={
                "capacity_summary": {
                    "total_members": total_capacity,
                    "allocated_members": allocated,
                    "unallocated_members": max(0, unallocated),
                    "allocation_rate": round(allocated / total_capacity, 3) if total_capacity > 0 else 0
                },
                "workload_distribution": {
                    "overloaded_count": len(overloaded_members),
                    "balanced_count": len(member_workload) - len(overloaded_members) - len(underutilized_members),
                    "underutilized_count": len(underutilized_members)
                },
                "top_allocations": sorted(pursuit_allocations, key=lambda x: x["team_size"], reverse=True)[:10],
                "avg_team_size": round(sum(p["team_size"] for p in pursuit_allocations) / len(pursuit_allocations), 2) if pursuit_allocations else 0
            }
        )

    # =========================================================================
    # PANEL 4: INNOVATION PIPELINE
    # =========================================================================

    def _generate_innovation_pipeline(self, org_id: str) -> DashboardPanel:
        """
        Generate Innovation Pipeline panel.

        Shows pipeline flow, velocity, and throughput metrics.
        """
        pursuits = db.get_pursuits_by_org(org_id) or []

        # Pipeline stages (simplified)
        pipeline = {
            "ideation": [],
            "validation": [],
            "development": [],
            "scaling": [],
            "completed": [],
            "archived": []
        }

        # Categorize pursuits
        for pursuit in pursuits:
            status = pursuit.get("status", "").lower()
            stage = pursuit.get("current_stage", "").upper()

            pursuit_summary = {
                "pursuit_id": pursuit.get("pursuit_id"),
                "name": pursuit.get("name", "Unnamed"),
                "created_at": pursuit.get("created_at"),
                "health_score": pursuit.get("health_score", 0.5)
            }

            if status in ["completed", "launched"]:
                pipeline["completed"].append(pursuit_summary)
            elif status in ["archived", "cancelled"]:
                pipeline["archived"].append(pursuit_summary)
            elif stage in ["VISION", "EMPATHIZE", "IDEATE", "DISCOVERY"]:
                pipeline["ideation"].append(pursuit_summary)
            elif stage in ["DE_RISK", "DEFINE", "PROTOTYPE", "SCOPING"]:
                pipeline["validation"].append(pursuit_summary)
            elif stage in ["SCALE", "TEST", "DEVELOPMENT", "BUILD_CASE"]:
                pipeline["development"].append(pursuit_summary)
            else:
                pipeline["scaling"].append(pursuit_summary)

        # Calculate velocity metrics
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        new_this_month = 0
        completed_this_month = 0

        for pursuit in pursuits:
            created = pursuit.get("created_at")
            if created:
                try:
                    if isinstance(created, str):
                        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    else:
                        created_dt = created
                    # Ensure timezone-aware comparison
                    if created_dt.tzinfo is None:
                        created_dt = created_dt.replace(tzinfo=timezone.utc)
                    if created_dt > thirty_days_ago:
                        new_this_month += 1
                except (ValueError, AttributeError):
                    pass

            # Check completion date
            completed_at = pursuit.get("completed_at")
            if completed_at:
                try:
                    if isinstance(completed_at, str):
                        completed_dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                    else:
                        completed_dt = completed_at
                    # Ensure timezone-aware comparison
                    if completed_dt.tzinfo is None:
                        completed_dt = completed_dt.replace(tzinfo=timezone.utc)
                    if completed_dt > thirty_days_ago:
                        completed_this_month += 1
                except (ValueError, AttributeError):
                    pass

        return DashboardPanel(
            panel_type=PanelType.INNOVATION_PIPELINE,
            title="Innovation Pipeline",
            data={
                "pipeline_stages": {
                    stage: len(items) for stage, items in pipeline.items()
                },
                "pipeline_details": {
                    stage: items[:5] for stage, items in pipeline.items()
                },
                "velocity_metrics": {
                    "new_pursuits_30d": new_this_month,
                    "completed_30d": completed_this_month,
                    "net_change_30d": new_this_month - completed_this_month
                },
                "funnel_conversion": self._calculate_funnel_conversion(pipeline)
            }
        )

    def _calculate_funnel_conversion(self, pipeline: Dict) -> Dict:
        """Calculate conversion rates between pipeline stages."""
        ideation = len(pipeline.get("ideation", []))
        validation = len(pipeline.get("validation", []))
        development = len(pipeline.get("development", []))
        scaling = len(pipeline.get("scaling", []))
        completed = len(pipeline.get("completed", []))

        total_active = ideation + validation + development + scaling

        return {
            "ideation_to_validation": round(validation / ideation, 2) if ideation > 0 else 0,
            "validation_to_development": round(development / validation, 2) if validation > 0 else 0,
            "development_to_scaling": round(scaling / development, 2) if development > 0 else 0,
            "overall_success_rate": round(completed / (total_active + completed), 2) if (total_active + completed) > 0 else 0
        }

    # =========================================================================
    # PANEL 5: RISK RADAR
    # =========================================================================

    def _generate_risk_radar(self, org_id: str) -> DashboardPanel:
        """
        Generate Risk Radar panel.

        Aggregates risk signals across the portfolio.
        """
        pursuits = db.get_pursuits_by_org(org_id) or []

        risk_summary = {
            "high_risk_pursuits": [],
            "risk_categories": {
                "execution": 0,
                "market": 0,
                "technical": 0,
                "resource": 0,
                "stakeholder": 0
            },
            "emerging_risks": [],
            "risk_trends": []
        }

        for pursuit in pursuits:
            pursuit_id = pursuit.get("pursuit_id")
            pursuit_name = pursuit.get("name", "Unnamed")
            health = pursuit.get("health_score", 0.5)

            # Get risk indicators
            risks = pursuit.get("risk_indicators", [])

            if health < 0.4:
                risk_summary["high_risk_pursuits"].append({
                    "pursuit_id": pursuit_id,
                    "name": pursuit_name,
                    "health_score": health,
                    "risk_count": len(risks)
                })

            # Categorize risks
            for risk in risks:
                category = risk.get("category", "execution").lower()
                if category in risk_summary["risk_categories"]:
                    risk_summary["risk_categories"][category] += 1

                # Check for emerging risks (recent)
                identified_at = risk.get("identified_at")
                if identified_at:
                    try:
                        if isinstance(identified_at, str):
                            risk_dt = datetime.fromisoformat(identified_at.replace("Z", "+00:00"))
                        else:
                            risk_dt = identified_at
                        # Ensure timezone-aware comparison
                        if risk_dt.tzinfo is None:
                            risk_dt = risk_dt.replace(tzinfo=timezone.utc)
                        if datetime.now(timezone.utc) - risk_dt < timedelta(days=7):
                            risk_summary["emerging_risks"].append({
                                "pursuit_id": pursuit_id,
                                "pursuit_name": pursuit_name,
                                "risk_description": risk.get("description", ""),
                                "category": category,
                                "identified_at": identified_at
                            })
                    except (ValueError, AttributeError):
                        pass

        # Calculate risk score
        total_risks = sum(risk_summary["risk_categories"].values())
        high_risk_count = len(risk_summary["high_risk_pursuits"])
        risk_score = 1.0 - (high_risk_count / len(pursuits)) if pursuits else 1.0

        return DashboardPanel(
            panel_type=PanelType.RISK_RADAR,
            title="Risk Radar",
            data={
                "portfolio_risk_score": round(risk_score, 3),
                "high_risk_pursuits": risk_summary["high_risk_pursuits"][:5],
                "risk_by_category": risk_summary["risk_categories"],
                "total_active_risks": total_risks,
                "emerging_risks": risk_summary["emerging_risks"][:5]
            }
        )

    # =========================================================================
    # PANEL 6: CONVERGENCE INSIGHTS
    # =========================================================================

    def _generate_convergence_insights(self, org_id: str) -> DashboardPanel:
        """
        Generate Convergence Insights panel.

        Shows coaching convergence patterns and outcomes.
        """
        # Get convergence sessions for org pursuits
        pursuits = db.get_pursuits_by_org(org_id) or []
        pursuit_ids = [p.get("pursuit_id") for p in pursuits]

        total_sessions = 0
        total_outcomes = 0
        outcome_types = {"DECISION": 0, "INSIGHT": 0, "HYPOTHESIS": 0, "COMMITMENT": 0, "REFINEMENT": 0}
        phase_distribution = {"EXPLORING": 0, "CONSOLIDATING": 0, "COMMITTED": 0, "HANDED_OFF": 0}
        avg_outcomes_per_session = 0
        recent_convergences = []

        for pursuit_id in pursuit_ids[:50]:  # Limit to prevent timeout
            sessions = db.get_pursuit_convergence_sessions(pursuit_id, limit=10) or []

            for session in sessions:
                total_sessions += 1
                outcomes = session.get("outcomes_captured", [])
                total_outcomes += len(outcomes)

                # Count outcome types
                for outcome in outcomes:
                    otype = outcome.get("outcome_type", "")
                    if otype in outcome_types:
                        outcome_types[otype] += 1

                # Count phases
                phase = session.get("current_phase", "EXPLORING")
                if phase in phase_distribution:
                    phase_distribution[phase] += 1

                # Track recent completed convergences
                if session.get("current_phase") == "HANDED_OFF":
                    recent_convergences.append({
                        "session_id": session.get("session_id"),
                        "pursuit_id": pursuit_id,
                        "outcomes_count": len(outcomes),
                        "completed_at": session.get("completed_at")
                    })

        if total_sessions > 0:
            avg_outcomes_per_session = round(total_outcomes / total_sessions, 2)

        return DashboardPanel(
            panel_type=PanelType.CONVERGENCE_INSIGHTS,
            title="Convergence Insights",
            data={
                "summary": {
                    "total_sessions": total_sessions,
                    "total_outcomes": total_outcomes,
                    "avg_outcomes_per_session": avg_outcomes_per_session,
                    "handoff_rate": round(phase_distribution["HANDED_OFF"] / total_sessions, 2) if total_sessions > 0 else 0
                },
                "outcome_distribution": outcome_types,
                "phase_distribution": phase_distribution,
                "recent_convergences": sorted(
                    recent_convergences,
                    key=lambda x: x.get("completed_at", ""),
                    reverse=True
                )[:5]
            }
        )

    # =========================================================================
    # PANEL 7: TALENT & FORMATION
    # =========================================================================

    def _generate_talent_formation(self, org_id: str) -> DashboardPanel:
        """
        Generate Talent & Formation panel.

        Shows IDTFS insights and formation activity.
        """
        # Get innovator profiles
        profiles = db.get_org_innovator_profiles(org_id) or []

        # Profile metrics
        total_profiles = len(profiles)
        opted_in = len([p for p in profiles if p.get("discovery_opt_in", False)])
        avg_completeness = 0
        if profiles:
            completeness_scores = [p.get("profile_completeness", 0) for p in profiles]
            avg_completeness = sum(completeness_scores) / len(completeness_scores)

        # Availability distribution
        availability = {"FULL_TIME": 0, "PART_TIME": 0, "LIMITED": 0, "UNAVAILABLE": 0}
        for profile in profiles:
            status = profile.get("availability_status", "UNAVAILABLE")
            if status in availability:
                availability[status] += 1

        # Expertise distribution
        expertise_tags = {}
        expertise_types = {}
        for profile in profiles:
            for tag in profile.get("declared_expertise_tags", []):
                expertise_tags[tag] = expertise_tags.get(tag, 0) + 1
            for etype in profile.get("expertise_types", []):
                expertise_types[etype] = expertise_types.get(etype, 0) + 1

        # Get vouching activity
        vouching_records = db.get_org_vouching_records(org_id, limit=100) or []
        vouching_last_30d = len([v for v in vouching_records if self._is_within_days(v.get("created_at"), 30)])

        # Get formation recommendations
        recommendations = db.get_org_formation_recommendations(org_id, limit=50) or []
        pending_recs = len([r for r in recommendations if r.get("status") == "PROPOSED"])
        accepted_recs = len([r for r in recommendations if r.get("status") == "ACCEPTED"])

        return DashboardPanel(
            panel_type=PanelType.TALENT_FORMATION,
            title="Talent & Formation",
            data={
                "profile_metrics": {
                    "total_profiles": total_profiles,
                    "discovery_opted_in": opted_in,
                    "opt_in_rate": round(opted_in / total_profiles, 2) if total_profiles > 0 else 0,
                    "avg_profile_completeness": round(avg_completeness, 2)
                },
                "availability_distribution": availability,
                "top_expertise_tags": dict(sorted(expertise_tags.items(), key=lambda x: x[1], reverse=True)[:10]),
                "expertise_type_distribution": expertise_types,
                "vouching_activity": {
                    "total_vouches": len(vouching_records),
                    "vouches_last_30d": vouching_last_30d
                },
                "formation_activity": {
                    "pending_recommendations": pending_recs,
                    "accepted_recommendations": accepted_recs,
                    "acceptance_rate": round(accepted_recs / (pending_recs + accepted_recs), 2) if (pending_recs + accepted_recs) > 0 else 0
                }
            }
        )

    def _is_within_days(self, date_value: Any, days: int) -> bool:
        """Check if a date is within the specified number of days."""
        if not date_value:
            return False
        try:
            if isinstance(date_value, str):
                dt = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            else:
                dt = date_value
            # Ensure timezone-aware comparison
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) - dt < timedelta(days=days)
        except (ValueError, AttributeError):
            return False

    # =========================================================================
    # PANEL 8: MOMENTUM HEALTH (v4.4)
    # =========================================================================

    def _generate_momentum_health(self, org_id: str) -> DashboardPanel:
        """
        Generate Momentum Health panel (v4.4).

        Shows org-level momentum analytics including:
        - Aggregate momentum tier distribution
        - IML pattern learning metrics
        - Bridge effectiveness rates
        - Momentum trajectory trends
        """
        pursuits = db.get_pursuits_by_org(org_id) or []
        pursuit_ids = [p.get("pursuit_id") for p in pursuits if p.get("pursuit_id")]

        # Initialize metrics
        tier_distribution = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "CRITICAL": 0}
        total_snapshots = 0
        total_bridges_delivered = 0
        total_bridges_responded = 0
        trajectory_directions = {"rising": 0, "declining": 0, "stable": 0, "mixed": 0}
        recent_sessions = []
        avg_composite_scores = []

        # Aggregate momentum snapshots across pursuits
        for pursuit_id in pursuit_ids[:100]:  # Limit to prevent timeout
            try:
                snapshots = list(db.db.momentum_snapshots.find(
                    {"pursuit_id": pursuit_id},
                    sort=[("recorded_at", -1)],
                    limit=10
                ))

                for snapshot in snapshots:
                    total_snapshots += 1
                    tier = snapshot.get("momentum_tier", "MEDIUM")
                    if tier in tier_distribution:
                        tier_distribution[tier] += 1

                    score = snapshot.get("composite_score", 0.5)
                    avg_composite_scores.append(score)

                    if snapshot.get("bridge_delivered"):
                        total_bridges_delivered += 1
                        if snapshot.get("bridge_responded"):
                            total_bridges_responded += 1

                    # Track recent sessions
                    if self._is_within_days(snapshot.get("recorded_at"), 7):
                        recent_sessions.append({
                            "pursuit_id": pursuit_id,
                            "tier": tier,
                            "score": score,
                            "recorded_at": snapshot.get("recorded_at")
                        })
            except Exception as e:
                logger.warning(f"Failed to get momentum snapshots for {pursuit_id}: {e}")

        # Get IML pattern metrics
        iml_metrics = self._get_iml_pattern_metrics(org_id)

        # Calculate averages
        avg_score = sum(avg_composite_scores) / len(avg_composite_scores) if avg_composite_scores else 0.5
        bridge_response_rate = (
            total_bridges_responded / total_bridges_delivered
            if total_bridges_delivered > 0 else 0
        )

        # Determine org-level momentum health
        high_energy_rate = tier_distribution["HIGH"] / total_snapshots if total_snapshots > 0 else 0
        low_energy_rate = (tier_distribution["LOW"] + tier_distribution["CRITICAL"]) / total_snapshots if total_snapshots > 0 else 0

        if high_energy_rate > 0.4:
            org_momentum_health = "excellent"
        elif high_energy_rate > 0.25 and low_energy_rate < 0.2:
            org_momentum_health = "good"
        elif low_energy_rate > 0.35:
            org_momentum_health = "at_risk"
        else:
            org_momentum_health = "stable"

        return DashboardPanel(
            panel_type=PanelType.MOMENTUM_HEALTH,
            title="Momentum Health",
            data={
                "summary": {
                    "total_sessions_tracked": total_snapshots,
                    "avg_momentum_score": round(avg_score, 3),
                    "org_momentum_health": org_momentum_health,
                    "pursuits_analyzed": len(pursuit_ids)
                },
                "tier_distribution": tier_distribution,
                "bridge_effectiveness": {
                    "bridges_delivered": total_bridges_delivered,
                    "bridges_responded": total_bridges_responded,
                    "response_rate": round(bridge_response_rate, 3)
                },
                "iml_learning": iml_metrics,
                "recent_sessions": sorted(
                    recent_sessions,
                    key=lambda x: x.get("recorded_at", ""),
                    reverse=True
                )[:10]
            },
            cache_duration_seconds=600  # 10 minute cache for momentum data
        )

    def _get_iml_pattern_metrics(self, org_id: str) -> Dict[str, Any]:
        """
        Get IML momentum pattern learning metrics (v4.4).

        Returns metrics about how well the system is learning
        from momentum patterns across the organization.
        """
        try:
            # Count patterns by type
            pattern_counts = {}
            pattern_types = ["BRIDGE_LIFT", "BRIDGE_STALL", "INSIGHT_LIFT", "INSIGHT_STALL"]

            for ptype in pattern_types:
                count = db.db.momentum_patterns.count_documents({"pattern_type": ptype})
                pattern_counts[ptype] = count

            total_patterns = sum(pattern_counts.values())

            # Get high-confidence patterns
            high_confidence = db.db.momentum_patterns.count_documents({
                "confidence": {"$gte": 0.7}
            })

            # Get patterns contributed to IKF
            ikf_eligible = db.db.momentum_patterns.count_documents({
                "confidence": {"$gte": 0.7},
                "sample_size": {"$gte": 5}
            })

            # Calculate learning velocity (patterns created in last 7 days)
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
            recent_patterns = db.db.momentum_patterns.count_documents({
                "created_at": {"$gte": seven_days_ago}
            })

            return {
                "total_patterns": total_patterns,
                "patterns_by_type": pattern_counts,
                "high_confidence_patterns": high_confidence,
                "ikf_contribution_eligible": ikf_eligible,
                "learning_velocity_7d": recent_patterns,
                "confidence_rate": round(high_confidence / total_patterns, 3) if total_patterns > 0 else 0
            }
        except Exception as e:
            logger.warning(f"Failed to get IML pattern metrics: {e}")
            return {
                "total_patterns": 0,
                "patterns_by_type": {},
                "high_confidence_patterns": 0,
                "ikf_contribution_eligible": 0,
                "learning_velocity_7d": 0,
                "confidence_rate": 0,
                "error": str(e)
            }


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_dashboard: Optional[PortfolioDashboard] = None


def get_portfolio_dashboard() -> PortfolioDashboard:
    """Get singleton PortfolioDashboard instance."""
    global _dashboard
    if _dashboard is None:
        _dashboard = PortfolioDashboard()
    return _dashboard
