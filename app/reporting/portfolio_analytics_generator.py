"""
InDE MVP v2.8 - Portfolio Analytics Report Generator

Generates cross-pursuit analytics and organizational learning reports.
Provides insights across multiple pursuits including:
- Learning velocity analysis
- Methodology effectiveness comparison
- Pattern trend analysis
- Terminal state distribution
- Fear materialization patterns
- Stakeholder engagement patterns

Key Features:
- Multi-pursuit analysis with filtering
- Visualization generation (charts)
- Multiple output formats (Markdown, PDF)
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from collections import Counter

from config import (
    TERMINAL_STATES,
    PORTFOLIO_ANALYTICS_CONFIG,
    VISUALIZATION_CONFIG
)


class PortfolioAnalyticsGenerator:
    """
    Generates Portfolio Analytics Reports for cross-pursuit insights.
    """

    def __init__(self, database):
        self.db = database

    def generate_analytics_report(
        self,
        scope: str,  # "individual" | "team" | "organization"
        scope_id: str,  # user_id, team_id, or org_id
        time_range: Dict = None,  # {"start": datetime, "end": datetime}
        filters: Dict = None,  # {"archetypes": [...], "outcomes": [...], "domains": [...]}
        analysis_type: str = "comprehensive",  # "learning_velocity" | "methodology_effectiveness" | "pattern_trends" | "comprehensive"
        formats: List[str] = None
    ) -> Dict:
        """
        Generate portfolio analytics report.

        Args:
            scope: Scope of analysis ("individual", "team", "organization")
            scope_id: ID for the scope (user_id, team_id, org_id)
            time_range: Optional date range filter
            filters: Optional filters for archetypes, outcomes, domains
            analysis_type: Type of analysis to run
            formats: Output formats (default: ["markdown"])

        Returns:
            {
                "report_id": str,
                "pursuits_analyzed": int,
                "analytics": dict,
                "visualizations": list,
                "formats": dict
            }
        """
        if formats is None:
            formats = ["markdown"]

        # Get pursuits matching scope and filters
        pursuits = self._get_pursuits_for_analysis(
            scope,
            scope_id,
            time_range,
            filters
        )

        # Validate minimum pursuits
        min_pursuits = PORTFOLIO_ANALYTICS_CONFIG.get("min_pursuits_for_analytics", 3)
        if len(pursuits) < min_pursuits:
            raise ValueError(
                f"Need at least {min_pursuits} pursuits for analytics. "
                f"Found {len(pursuits)}."
            )

        # Run analytics
        analytics = self._run_analytics(pursuits, analysis_type)

        # Generate visualizations
        visualizations = []
        if PORTFOLIO_ANALYTICS_CONFIG.get("enable_visualizations", True):
            visualizations = self._generate_visualizations(analytics, pursuits)

        # Generate report ID
        report_id = str(uuid.uuid4())

        # Render in requested formats
        rendered_formats = {}
        for fmt in formats:
            output_path = self._render_analytics_format(
                report_id,
                analytics,
                visualizations,
                pursuits,
                fmt
            )
            rendered_formats[fmt] = output_path

        # Store report record
        report_record = {
            "report_id": report_id,
            "report_type": "PORTFOLIO_ANALYTICS",
            "scope": scope,
            "scope_id": scope_id,
            "time_range": time_range,
            "filters": filters,
            "analysis_type": analysis_type,
            "pursuits_analyzed": [str(p.get("pursuit_id", p.get("_id"))) for p in pursuits],
            "analytics": analytics,
            "visualizations": visualizations,
            "formats": rendered_formats,
            "generated_at": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc)
        }

        self.db.create_portfolio_analytics_report(report_record)

        return {
            "report_id": report_id,
            "pursuits_analyzed": len(pursuits),
            "analytics": analytics,
            "visualizations": visualizations,
            "formats": rendered_formats
        }

    def _get_pursuits_for_analysis(
        self,
        scope: str,
        scope_id: str,
        time_range: Dict,
        filters: Dict
    ) -> List[Dict]:
        """Get pursuits matching criteria."""
        # Build query based on scope
        if scope == "individual":
            pursuits = self.db.get_user_pursuits(scope_id)
        elif scope == "team":
            pursuits = self.db.get_team_pursuits(scope_id) if hasattr(self.db, 'get_team_pursuits') else []
        elif scope == "organization":
            pursuits = self.db.get_org_pursuits(scope_id) if hasattr(self.db, 'get_org_pursuits') else []
        else:
            pursuits = []

        # Apply filters
        if time_range:
            start = time_range.get("start")
            end = time_range.get("end", datetime.now(timezone.utc))
            pursuits = [
                p for p in pursuits
                if self._in_time_range(p.get("created_at"), start, end)
            ]

        if filters:
            # Methodology/archetype filter
            if filters.get("archetypes") and filters["archetypes"] != "all":
                pursuits = [
                    p for p in pursuits
                    if p.get("methodology") in filters["archetypes"]
                ]

            # Outcome filter
            if filters.get("outcomes") and filters["outcomes"] != "all":
                pursuits = [
                    p for p in pursuits
                    if self._matches_outcome_filter(p.get("state", ""), filters["outcomes"])
                ]

            # Domain filter
            if filters.get("domains") and filters["domains"] != "all":
                pursuits = [
                    p for p in pursuits
                    if p.get("domain") in filters["domains"]
                ]

        return pursuits

    def _in_time_range(self, created_at, start, end) -> bool:
        """Check if date is within range."""
        if not created_at:
            return False
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                return False
        if start and created_at < start:
            return False
        if end and created_at > end:
            return False
        return True

    def _matches_outcome_filter(self, state: str, outcomes: List[str]) -> bool:
        """Check if state matches outcome filter."""
        for outcome in outcomes:
            if outcome == "COMPLETED" and state.startswith("COMPLETED"):
                return True
            if outcome == "TERMINATED" and state.startswith("TERMINATED"):
                return True
            if state == outcome:
                return True
        return False

    def _run_analytics(self, pursuits: List[Dict], analysis_type: str) -> Dict:
        """Run specified analytics on pursuits."""
        analytics = {
            "summary": {
                "total_pursuits": len(pursuits),
                "terminal_pursuits": len([p for p in pursuits if self._is_terminal(p.get("state", ""))]),
                "active_pursuits": len([p for p in pursuits if p.get("state") == "ACTIVE"]),
                "suspended_pursuits": len([p for p in pursuits if p.get("state") == "SUSPENDED"])
            }
        }

        if analysis_type in ["learning_velocity", "comprehensive"]:
            analytics["learning_velocity"] = self._analyze_learning_velocity(pursuits)

        if analysis_type in ["methodology_effectiveness", "comprehensive"]:
            analytics["methodology_effectiveness"] = self._analyze_methodology_effectiveness(pursuits)

        if analysis_type in ["pattern_trends", "comprehensive"]:
            analytics["pattern_trends"] = self._analyze_pattern_trends(pursuits)

        if analysis_type == "comprehensive":
            analytics["terminal_distribution"] = self._analyze_terminal_distribution(pursuits)
            analytics["fear_analysis"] = self._analyze_fear_patterns(pursuits)
            analytics["stakeholder_insights"] = self._analyze_stakeholder_patterns(pursuits)

        return analytics

    def _analyze_learning_velocity(self, pursuits: List[Dict]) -> Dict:
        """Analyze how quickly organization learns from pursuits."""
        terminal_pursuits = [p for p in pursuits if self._is_terminal(p.get("state", ""))]

        if not terminal_pursuits:
            return {"note": "No terminal pursuits to analyze"}

        # Patterns per pursuit
        patterns_total = 0
        for pursuit in terminal_pursuits:
            pursuit_id = pursuit.get("pursuit_id", str(pursuit.get("_id", "")))
            patterns = self.db.get_patterns_by_pursuit(pursuit_id) if hasattr(self.db, 'get_patterns_by_pursuit') else []
            patterns_total += len(patterns) if patterns else 0

        patterns_per_pursuit = patterns_total / len(terminal_pursuits) if terminal_pursuits else 0

        # Average time to decision
        durations = []
        for pursuit in terminal_pursuits:
            created_at = pursuit.get("created_at")
            terminal_info = pursuit.get("terminal_info", {})
            terminated_at = terminal_info.get("terminated_at") or pursuit.get("updated_at")

            if created_at and terminated_at:
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except:
                        continue
                if isinstance(terminated_at, str):
                    try:
                        terminated_at = datetime.fromisoformat(terminated_at.replace('Z', '+00:00'))
                    except:
                        continue
                # Ensure both datetimes are timezone-aware
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                if terminated_at.tzinfo is None:
                    terminated_at = terminated_at.replace(tzinfo=timezone.utc)
                duration = (terminated_at - created_at).days
                durations.append(duration)

        avg_duration = sum(durations) / len(durations) if durations else 0

        # Repeat failure rate
        invalidated = [p for p in terminal_pursuits if "INVALIDATED" in p.get("state", "")]
        repeat_failures = self._detect_repeat_failures(invalidated)
        repeat_failure_rate = len(repeat_failures) / len(invalidated) if invalidated else 0

        # Knowledge utilization (how often patterns are referenced)
        knowledge_utilization = self._calculate_knowledge_utilization(pursuits)

        return {
            "patterns_per_pursuit": round(patterns_per_pursuit, 2),
            "avg_time_to_decision_days": round(avg_duration, 1),
            "repeat_failure_rate": round(repeat_failure_rate, 3),
            "knowledge_utilization_score": round(knowledge_utilization, 3),
            "total_patterns_extracted": patterns_total,
            "terminal_pursuits_analyzed": len(terminal_pursuits)
        }

    def _analyze_methodology_effectiveness(self, pursuits: List[Dict]) -> Dict:
        """Analyze which methodologies work best."""
        terminal_pursuits = [p for p in pursuits if self._is_terminal(p.get("state", ""))]

        if not terminal_pursuits:
            return {"note": "No terminal pursuits to analyze"}

        # Group by methodology
        by_methodology = {}
        for pursuit in terminal_pursuits:
            methodology = pursuit.get("methodology", "unknown")
            if methodology not in by_methodology:
                by_methodology[methodology] = []
            by_methodology[methodology].append(pursuit)

        # Analyze each methodology
        effectiveness = {}
        for methodology, method_pursuits in by_methodology.items():
            completed = len([p for p in method_pursuits if p.get("state", "").startswith("COMPLETED")])
            terminated = len([p for p in method_pursuits if p.get("state", "").startswith("TERMINATED")])

            completion_rate = completed / len(method_pursuits) if method_pursuits else 0

            # Average duration
            durations = []
            for p in method_pursuits:
                created_at = p.get("created_at")
                terminal_info = p.get("terminal_info", {})
                terminated_at = terminal_info.get("terminated_at") or p.get("updated_at")

                if created_at and terminated_at:
                    if isinstance(created_at, str):
                        try:
                            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        except:
                            continue
                    if isinstance(terminated_at, str):
                        try:
                            terminated_at = datetime.fromisoformat(terminated_at.replace('Z', '+00:00'))
                        except:
                            continue
                    # Ensure both datetimes are timezone-aware
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    if terminated_at.tzinfo is None:
                        terminated_at = terminated_at.replace(tzinfo=timezone.utc)
                    duration = (terminated_at - created_at).days
                    durations.append(duration)

            avg_duration = sum(durations) / len(durations) if durations else 0

            # Success correlation
            success_correlation = completed / len(method_pursuits) if method_pursuits else 0

            effectiveness[methodology] = {
                "completion_rate": round(completion_rate, 3),
                "avg_duration_days": round(avg_duration, 1),
                "success_correlation": round(success_correlation, 3),
                "total_pursuits": len(method_pursuits),
                "completed_count": completed,
                "terminated_count": terminated
            }

        return effectiveness

    def _analyze_pattern_trends(self, pursuits: List[Dict]) -> Dict:
        """Analyze emerging vs. declining patterns."""
        # Get all patterns from pursuits
        all_patterns = []
        for pursuit in pursuits:
            pursuit_id = pursuit.get("pursuit_id", str(pursuit.get("_id", "")))
            patterns = self.db.get_patterns_by_pursuit(pursuit_id) if hasattr(self.db, 'get_patterns_by_pursuit') else []
            if patterns:
                all_patterns.extend(patterns)

        if not all_patterns:
            # Try getting all learning patterns
            all_patterns = list(self.db.learning_patterns.find()) if hasattr(self.db, 'learning_patterns') else []

        if not all_patterns:
            return {"note": "No pattern data available"}

        # Analyze application trends
        emerging = []
        declining = []
        stable = []

        for pattern in all_patterns:
            applications = pattern.get("applications", pattern.get("application_count", 1))
            pattern_type = pattern.get("pattern_type", "UNKNOWN")
            pattern_content = pattern.get("pattern_content", pattern.get("content", ""))

            # Simple trend detection based on applications count
            if applications >= 5:
                trend = "emerging"
            elif applications <= 1:
                trend = "declining"
            else:
                trend = "stable"

            pattern_info = {
                "pattern_id": str(pattern.get("pattern_id", pattern.get("_id", ""))),
                "pattern_type": pattern_type,
                "pattern_content": str(pattern_content)[:100] if pattern_content else "",
                "applications": applications,
                "trend": trend
            }

            if trend == "emerging":
                emerging.append(pattern_info)
            elif trend == "declining":
                declining.append(pattern_info)
            else:
                stable.append(pattern_info)

        # Sort by applications
        emerging.sort(key=lambda x: x["applications"], reverse=True)
        declining.sort(key=lambda x: x["applications"])

        return {
            "emerging_patterns": emerging[:5],  # Top 5
            "declining_patterns": declining[:5],
            "stable_patterns_count": len(stable),
            "total_patterns_analyzed": len(all_patterns)
        }

    def _analyze_terminal_distribution(self, pursuits: List[Dict]) -> Dict:
        """Analyze distribution of terminal states."""
        terminal_pursuits = [p for p in pursuits if self._is_terminal(p.get("state", ""))]

        distribution = {}
        for pursuit in terminal_pursuits:
            state = pursuit.get("state", "UNKNOWN")
            distribution[state] = distribution.get(state, 0) + 1

        return distribution

    def _analyze_fear_patterns(self, pursuits: List[Dict]) -> Dict:
        """Analyze which fears are most common and most likely to materialize."""
        # Get fear resolutions from retrospectives
        fear_resolutions = []
        for pursuit in pursuits:
            pursuit_id = pursuit.get("pursuit_id", str(pursuit.get("_id", "")))
            terminal_info = pursuit.get("terminal_info", {})
            retrospective_id = terminal_info.get("retrospective_id")

            if retrospective_id:
                resolutions = self.db.get_fear_resolutions(retrospective_id) if hasattr(self.db, 'get_fear_resolutions') else []
                if resolutions:
                    fear_resolutions.extend(resolutions)

        if not fear_resolutions:
            return {"note": "No fear resolution data available"}

        # Count materializations and mitigation effectiveness
        materialized_count = 0
        effective_mitigation_count = 0

        for resolution in fear_resolutions:
            if resolution.get("materialized") == True:
                materialized_count += 1
                if resolution.get("mitigation_effectiveness") == "EFFECTIVE":
                    effective_mitigation_count += 1

        total_fears = len(fear_resolutions)
        materialization_rate = materialized_count / total_fears if total_fears > 0 else 0
        effective_mitigation_rate = effective_mitigation_count / materialized_count if materialized_count > 0 else 0

        return {
            "total_fears_tracked": total_fears,
            "materialization_rate": round(materialization_rate, 3),
            "effective_mitigation_rate": round(effective_mitigation_rate, 3),
            "fears_materialized": materialized_count,
            "fears_effectively_mitigated": effective_mitigation_count
        }

    def _analyze_stakeholder_patterns(self, pursuits: List[Dict]) -> Dict:
        """Analyze stakeholder engagement patterns."""
        stakeholder_data = []
        for pursuit in pursuits:
            pursuit_id = pursuit.get("pursuit_id", str(pursuit.get("_id", "")))
            feedback = self.db.get_stakeholder_feedback_by_pursuit(pursuit_id) if hasattr(self.db, 'get_stakeholder_feedback_by_pursuit') else []
            if feedback:
                stakeholder_data.extend(feedback)

        if not stakeholder_data:
            return {"note": "No stakeholder data available"}

        # Analyze support level distribution
        support_levels = Counter(fb.get("support_level", "unknown") for fb in stakeholder_data)

        # Count by relationship type
        relationship_types = Counter(fb.get("relationship_type", "unknown") for fb in stakeholder_data)

        return {
            "stakeholders_engaged_total": len(stakeholder_data),
            "avg_stakeholders_per_pursuit": round(len(stakeholder_data) / len(pursuits), 2) if pursuits else 0,
            "support_distribution": dict(support_levels),
            "relationship_distribution": dict(relationship_types)
        }

    def _generate_visualizations(self, analytics: Dict, pursuits: List[Dict]) -> List[Dict]:
        """Generate charts and visualizations."""
        visualizations = []

        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt
        except ImportError:
            return [{"note": "matplotlib not installed - visualizations skipped"}]

        # Create output directory
        output_dir = os.path.join(os.path.dirname(__file__), "..", "outputs", "charts")
        os.makedirs(output_dir, exist_ok=True)

        # Learning velocity chart
        if "learning_velocity" in analytics and analytics["learning_velocity"].get("patterns_per_pursuit") is not None:
            chart_path = self._create_learning_velocity_chart(analytics["learning_velocity"], output_dir)
            if chart_path:
                visualizations.append({
                    "type": "learning_velocity_chart",
                    "data_url": chart_path
                })

        # Methodology comparison chart
        if "methodology_effectiveness" in analytics and isinstance(analytics["methodology_effectiveness"], dict):
            if "note" not in analytics["methodology_effectiveness"]:
                chart_path = self._create_methodology_comparison_chart(analytics["methodology_effectiveness"], output_dir)
                if chart_path:
                    visualizations.append({
                        "type": "methodology_comparison",
                        "data_url": chart_path
                    })

        # Terminal distribution pie chart
        if "terminal_distribution" in analytics and analytics["terminal_distribution"]:
            chart_path = self._create_terminal_distribution_chart(analytics["terminal_distribution"], output_dir)
            if chart_path:
                visualizations.append({
                    "type": "terminal_distribution",
                    "data_url": chart_path
                })

        return visualizations

    def _create_learning_velocity_chart(self, data: Dict, output_dir: str) -> Optional[str]:
        """Create learning velocity visualization."""
        try:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(10, 6))

            metrics = [
                "Patterns\nper Pursuit",
                "Avg Days\nto Decision",
                "Knowledge\nUtilization"
            ]
            values = [
                data.get("patterns_per_pursuit", 0),
                data.get("avg_time_to_decision_days", 0) / 10,  # Scale for visibility
                data.get("knowledge_utilization_score", 0) * 10  # Scale for visibility
            ]

            colors = ['#4CAF50', '#2196F3', '#FF9800']
            ax.bar(metrics, values, color=colors)
            ax.set_ylabel('Value (scaled)')
            ax.set_title('Learning Velocity Metrics')

            chart_id = str(uuid.uuid4())[:8]
            chart_path = os.path.join(output_dir, f"learning_velocity_{chart_id}.png")
            dpi = VISUALIZATION_CONFIG.get("default_dpi", 150)
            plt.savefig(chart_path, dpi=dpi, bbox_inches='tight')
            plt.close()

            return chart_path
        except Exception as e:
            print(f"Error creating learning velocity chart: {e}")
            return None

    def _create_methodology_comparison_chart(self, data: Dict, output_dir: str) -> Optional[str]:
        """Create methodology effectiveness comparison."""
        try:
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(12, 6))

            methodologies = list(data.keys())
            completion_rates = [data[m].get("completion_rate", 0) for m in methodologies]

            # Format methodology names
            labels = [m.replace('_', ' ').title() for m in methodologies]

            ax.bar(labels, completion_rates, color='#2196F3')
            ax.set_ylabel('Completion Rate')
            ax.set_title('Methodology Effectiveness Comparison')
            ax.set_ylim(0, 1)

            # Add value labels on bars
            for i, v in enumerate(completion_rates):
                ax.text(i, v + 0.02, f'{v:.1%}', ha='center')

            plt.xticks(rotation=45, ha='right')

            chart_id = str(uuid.uuid4())[:8]
            chart_path = os.path.join(output_dir, f"methodology_comparison_{chart_id}.png")
            dpi = VISUALIZATION_CONFIG.get("default_dpi", 150)
            plt.savefig(chart_path, dpi=dpi, bbox_inches='tight')
            plt.close()

            return chart_path
        except Exception as e:
            print(f"Error creating methodology comparison chart: {e}")
            return None

    def _create_terminal_distribution_chart(self, data: Dict, output_dir: str) -> Optional[str]:
        """Create terminal state distribution pie chart."""
        try:
            import matplotlib.pyplot as plt

            if not data:
                return None

            fig, ax = plt.subplots(figsize=(10, 8))

            # Format labels
            labels = [state.replace('.', '\n') for state in data.keys()]
            sizes = list(data.values())

            # Color scheme
            colors = ['#4CAF50', '#8BC34A', '#FFC107', '#FF9800', '#F44336', '#9C27B0']

            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors[:len(sizes)])
            ax.set_title('Terminal State Distribution')

            chart_id = str(uuid.uuid4())[:8]
            chart_path = os.path.join(output_dir, f"terminal_distribution_{chart_id}.png")
            dpi = VISUALIZATION_CONFIG.get("default_dpi", 150)
            plt.savefig(chart_path, dpi=dpi, bbox_inches='tight')
            plt.close()

            return chart_path
        except Exception as e:
            print(f"Error creating terminal distribution chart: {e}")
            return None

    def _render_analytics_format(
        self,
        report_id: str,
        analytics: Dict,
        visualizations: List[Dict],
        pursuits: List[Dict],
        format: str
    ) -> str:
        """Render analytics report in specified format."""
        if format == "markdown":
            return self._render_analytics_markdown(report_id, analytics, visualizations, pursuits)
        elif format == "pdf":
            return self._render_analytics_pdf(report_id, analytics, visualizations, pursuits)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _render_analytics_markdown(
        self,
        report_id: str,
        analytics: Dict,
        visualizations: List[Dict],
        pursuits: List[Dict]
    ) -> str:
        """Render as Markdown."""
        # Create output directory
        output_dir = os.path.join(os.path.dirname(__file__), "..", "outputs", "reports")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"portfolio_{report_id}.md")

        md = "# Portfolio Analytics Report\n\n"
        md += f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC\n\n"
        md += "---\n\n"

        # Summary
        if "summary" in analytics:
            summary = analytics["summary"]
            md += "## Portfolio Summary\n\n"
            md += f"- **Total Pursuits Analyzed:** {summary.get('total_pursuits', 0)}\n"
            md += f"- **Terminal Pursuits:** {summary.get('terminal_pursuits', 0)}\n"
            md += f"- **Active Pursuits:** {summary.get('active_pursuits', 0)}\n"
            md += f"- **Suspended Pursuits:** {summary.get('suspended_pursuits', 0)}\n\n"
            md += "---\n\n"

        # Learning Velocity
        if "learning_velocity" in analytics:
            lv = analytics["learning_velocity"]
            md += "## Learning Velocity\n\n"
            if "note" in lv:
                md += f"*{lv['note']}*\n\n"
            else:
                md += f"- **Patterns per Pursuit:** {lv.get('patterns_per_pursuit', 0):.2f}\n"
                md += f"- **Avg Time to Decision:** {lv.get('avg_time_to_decision_days', 0):.0f} days\n"
                md += f"- **Repeat Failure Rate:** {lv.get('repeat_failure_rate', 0):.1%}\n"
                md += f"- **Knowledge Utilization:** {lv.get('knowledge_utilization_score', 0):.1%}\n"
                md += f"- **Total Patterns Extracted:** {lv.get('total_patterns_extracted', 0)}\n\n"
            md += "---\n\n"

        # Methodology Effectiveness
        if "methodology_effectiveness" in analytics:
            me = analytics["methodology_effectiveness"]
            md += "## Methodology Effectiveness\n\n"
            if "note" in me:
                md += f"*{me['note']}*\n\n"
            else:
                for methodology, metrics in me.items():
                    md += f"### {methodology.replace('_', ' ').title()}\n\n"
                    md += f"- **Completion Rate:** {metrics.get('completion_rate', 0):.1%}\n"
                    md += f"- **Avg Duration:** {metrics.get('avg_duration_days', 0):.0f} days\n"
                    md += f"- **Success Correlation:** {metrics.get('success_correlation', 0):.1%}\n"
                    md += f"- **Total Pursuits:** {metrics.get('total_pursuits', 0)}\n"
                    md += f"- **Completed:** {metrics.get('completed_count', 0)} | **Terminated:** {metrics.get('terminated_count', 0)}\n\n"
            md += "---\n\n"

        # Pattern Trends
        if "pattern_trends" in analytics:
            pt = analytics["pattern_trends"]
            md += "## Pattern Trends\n\n"
            if "note" in pt:
                md += f"*{pt['note']}*\n\n"
            else:
                md += f"**Total Patterns Analyzed:** {pt.get('total_patterns_analyzed', 0)}\n\n"

                if pt.get("emerging_patterns"):
                    md += "### Emerging Patterns\n\n"
                    for pattern in pt["emerging_patterns"]:
                        content = pattern.get('pattern_content', '')[:80]
                        md += f"- **{pattern.get('pattern_type', 'UNKNOWN')}:** {content}... "
                        md += f"({pattern.get('applications', 0)} applications)\n"
                    md += "\n"

                if pt.get("declining_patterns"):
                    md += "### Declining Patterns\n\n"
                    for pattern in pt["declining_patterns"]:
                        content = pattern.get('pattern_content', '')[:80]
                        md += f"- **{pattern.get('pattern_type', 'UNKNOWN')}:** {content}... "
                        md += f"({pattern.get('applications', 0)} applications)\n"
                    md += "\n"

                md += f"**Stable Patterns:** {pt.get('stable_patterns_count', 0)}\n\n"
            md += "---\n\n"

        # Terminal Distribution
        if "terminal_distribution" in analytics and analytics["terminal_distribution"]:
            md += "## Terminal State Distribution\n\n"
            for state, count in analytics["terminal_distribution"].items():
                md += f"- **{state}:** {count}\n"
            md += "\n---\n\n"

        # Fear Analysis
        if "fear_analysis" in analytics:
            fa = analytics["fear_analysis"]
            md += "## Fear Analysis\n\n"
            if "note" in fa:
                md += f"*{fa['note']}*\n\n"
            else:
                md += f"- **Total Fears Tracked:** {fa.get('total_fears_tracked', 0)}\n"
                md += f"- **Materialization Rate:** {fa.get('materialization_rate', 0):.1%}\n"
                md += f"- **Effective Mitigation Rate:** {fa.get('effective_mitigation_rate', 0):.1%}\n\n"
            md += "---\n\n"

        # Stakeholder Insights
        if "stakeholder_insights" in analytics:
            si = analytics["stakeholder_insights"]
            md += "## Stakeholder Insights\n\n"
            if "note" in si:
                md += f"*{si['note']}*\n\n"
            else:
                md += f"- **Total Stakeholders Engaged:** {si.get('stakeholders_engaged_total', 0)}\n"
                md += f"- **Avg per Pursuit:** {si.get('avg_stakeholders_per_pursuit', 0):.1f}\n"
                if si.get("support_distribution"):
                    md += "\n**Support Distribution:**\n"
                    for level, count in si["support_distribution"].items():
                        md += f"- {level}: {count}\n"
                md += "\n"
            md += "---\n\n"

        # Visualizations
        if visualizations:
            md += "## Visualizations\n\n"
            for viz in visualizations:
                if "note" in viz:
                    md += f"*{viz['note']}*\n\n"
                else:
                    title = viz.get('type', 'chart').replace('_', ' ').title()
                    md += f"### {title}\n\n"
                    md += f"![{viz.get('type', 'chart')}]({viz.get('data_url', '')})\n\n"

        # Footer
        md += "---\n\n"
        md += "*Generated by InDE MVP v2.8 - Report Intelligence*\n"

        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md)

        return output_path

    def _render_analytics_pdf(
        self,
        report_id: str,
        analytics: Dict,
        visualizations: List[Dict],
        pursuits: List[Dict]
    ) -> str:
        """Render as PDF (generates markdown first, then notes PDF location)."""
        md_path = self._render_analytics_markdown(report_id, analytics, visualizations, pursuits)
        pdf_path = md_path.replace('.md', '.pdf')

        # In production, would use pandoc or weasyprint
        # For now, return markdown path as fallback
        return md_path

    # Helper methods
    def _is_terminal(self, state: str) -> bool:
        """Check if state is terminal."""
        if not state:
            return False
        return state in TERMINAL_STATES

    def _detect_repeat_failures(self, invalidated_pursuits: List[Dict]) -> List[Dict]:
        """Detect pursuits that failed for similar reasons."""
        # Simplified implementation - would need pattern matching on failure reasons
        # Look for similar vision/problem statements or fear patterns
        repeat_failures = []

        if len(invalidated_pursuits) < 2:
            return []

        # Compare domains and methodologies for simple repeat detection
        domain_counts = Counter(p.get("domain", "") for p in invalidated_pursuits)
        for domain, count in domain_counts.items():
            if count >= 2 and domain:
                failures_in_domain = [p for p in invalidated_pursuits if p.get("domain") == domain]
                repeat_failures.extend(failures_in_domain[1:])  # Exclude first occurrence

        return repeat_failures

    def _calculate_knowledge_utilization(self, pursuits: List[Dict]) -> float:
        """Calculate how often patterns are referenced/applied."""
        # Get total patterns and their application counts
        total_applications = 0
        total_patterns = 0

        for pursuit in pursuits:
            pursuit_id = pursuit.get("pursuit_id", str(pursuit.get("_id", "")))
            patterns = self.db.get_patterns_by_pursuit(pursuit_id) if hasattr(self.db, 'get_patterns_by_pursuit') else []
            if patterns:
                for pattern in patterns:
                    total_patterns += 1
                    total_applications += pattern.get("applications", pattern.get("application_count", 1))

        if total_patterns == 0:
            return 0.5  # Baseline

        # Utilization score based on average applications per pattern
        avg_applications = total_applications / total_patterns
        # Normalize to 0-1 scale (assume 5+ applications = full utilization)
        utilization = min(avg_applications / 5.0, 1.0)

        return utilization
