"""
InDE MVP v3.4 - ODICM Extensions
On-Demand Innovation Coaching Module with Convergence Awareness.

This module extends the core ODICM with:
- Convergence-aware coaching responses
- Methodology-specific coaching language
- Org intelligence integration
- Portfolio context awareness
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import logging

from core.database import db
from coaching.convergence import (
    get_convergence_orchestrator, ConvergencePhase, ConvergenceSignalDetector
)
from coaching.methodology_archetypes import (
    get_archetype, CoachingLanguageAdapter, get_coaching_style
)
from portfolio.dashboard import get_portfolio_dashboard, PanelType
from core.config import CONVERGENCE_CONFIG

logger = logging.getLogger("inde.coaching.odicm_extensions")


# =============================================================================
# ENUMERATIONS
# =============================================================================

class CoachingMode(str, Enum):
    """Coaching interaction modes."""
    EXPLORATORY = "exploratory"
    CONVERGENT = "convergent"
    DIRECTIVE = "directive"
    REFLECTIVE = "reflective"
    NON_DIRECTIVE = "non_directive"  # v3.7.1: Ad-hoc pursuits


class ContextSource(str, Enum):
    """Sources of coaching context."""
    PURSUIT = "pursuit"
    CONVERSATION = "conversation"
    PORTFOLIO = "portfolio"
    ORGANIZATION = "organization"
    METHODOLOGY = "methodology"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CoachingContext:
    """Rich coaching context combining multiple sources."""
    pursuit_id: str
    user_id: str
    org_id: str
    methodology_archetype: str
    current_phase: ConvergencePhase
    coaching_mode: CoachingMode
    convergence_signals: List[Dict]
    portfolio_context: Dict[str, Any]
    methodology_guidance: Dict[str, Any]
    recent_outcomes: List[Dict]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict:
        return {
            "pursuit_id": self.pursuit_id,
            "user_id": self.user_id,
            "org_id": self.org_id,
            "methodology_archetype": self.methodology_archetype,
            "current_phase": self.current_phase.value,
            "coaching_mode": self.coaching_mode.value,
            "convergence_signals": self.convergence_signals,
            "portfolio_context": self.portfolio_context,
            "methodology_guidance": self.methodology_guidance,
            "recent_outcomes": self.recent_outcomes,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class EnhancedCoachingResponse:
    """Enhanced coaching response with convergence awareness."""
    message: str
    coaching_mode: CoachingMode
    convergence_phase: ConvergencePhase
    suggested_actions: List[str]
    methodology_hints: List[str]
    convergence_prompt: Optional[str]
    portfolio_insights: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "message": self.message,
            "coaching_mode": self.coaching_mode.value,
            "convergence_phase": self.convergence_phase.value,
            "suggested_actions": self.suggested_actions,
            "methodology_hints": self.methodology_hints,
            "convergence_prompt": self.convergence_prompt,
            "portfolio_insights": self.portfolio_insights,
            "metadata": self.metadata
        }


# =============================================================================
# CONVERGENCE-AWARE COACH
# =============================================================================

class ConvergenceAwareCoach:
    """
    Enhanced coaching layer with convergence awareness.

    Integrates signal detection, methodology adaptation, and
    portfolio context into coaching interactions.
    """

    def __init__(self):
        self.signal_detector = ConvergenceSignalDetector()
        self.convergence_threshold = CONVERGENCE_CONFIG.get("threshold", 0.7)

    def build_coaching_context(
        self,
        pursuit_id: str,
        session_id: str,
        user_id: str,
        conversation_history: List[Dict]
    ) -> CoachingContext:
        """
        Build comprehensive coaching context from multiple sources.

        Combines pursuit, conversation, portfolio, and methodology context.
        v3.7.1: Now handles ad-hoc pursuits with non-directive mode.
        """
        # Get pursuit details
        pursuit = db.get_pursuit(pursuit_id) or {}
        org_id = pursuit.get("org_id", "")
        methodology = pursuit.get("methodology_archetype", "lean_startup")

        # v3.7.1: Check for ad-hoc pursuit
        is_adhoc = methodology == "ad_hoc"

        # Get convergence state (skip for ad-hoc)
        if is_adhoc:
            # Ad-hoc pursuits don't have convergence tracking
            current_phase = ConvergencePhase.EXPLORING  # Default state
            signals = []
            coaching_mode = CoachingMode.NON_DIRECTIVE
        else:
            orchestrator = get_convergence_orchestrator()
            convergence_context = orchestrator.get_convergence_context(session_id)
            current_phase = ConvergencePhase(convergence_context.get("current_phase", "EXPLORING"))

            # Detect current signals
            latest_message = conversation_history[-1]["content"] if conversation_history else ""
            session_start = convergence_context.get("session_start", datetime.now(timezone.utc))

            signals = self.signal_detector.detect_signals(
                message=latest_message,
                conversation_history=conversation_history,
                session_start_time=session_start
            )

            # Determine coaching mode based on phase and signals
            coaching_mode = self._determine_coaching_mode(current_phase, signals)

        # Get portfolio context (limited for performance)
        portfolio_context = self._get_portfolio_context(org_id, pursuit_id)

        # Get methodology guidance (minimal for ad-hoc)
        methodology_guidance = self._get_methodology_guidance(methodology, pursuit)

        # Get recent outcomes
        if is_adhoc:
            recent_outcomes = []
        else:
            orchestrator = get_convergence_orchestrator()
            convergence_context = orchestrator.get_convergence_context(session_id)
            recent_outcomes = convergence_context.get("outcomes_captured", [])[-5:]

        return CoachingContext(
            pursuit_id=pursuit_id,
            user_id=user_id,
            org_id=org_id,
            methodology_archetype=methodology,
            current_phase=current_phase,
            coaching_mode=coaching_mode,
            convergence_signals=[s.to_dict() for s in signals] if signals else [],
            portfolio_context=portfolio_context,
            methodology_guidance=methodology_guidance,
            recent_outcomes=recent_outcomes
        )

    def _determine_coaching_mode(
        self,
        phase: ConvergencePhase,
        signals: List
    ) -> CoachingMode:
        """Determine appropriate coaching mode based on context."""
        # Calculate composite signal score
        if signals:
            signal_score = sum(s.score for s in signals) / len(signals)
        else:
            signal_score = 0.0

        # Phase-based mode selection
        if phase == ConvergencePhase.EXPLORING:
            if signal_score > 0.5:
                return CoachingMode.CONVERGENT  # Signals detected, start converging
            return CoachingMode.EXPLORATORY  # Still exploring

        elif phase == ConvergencePhase.CONSOLIDATING:
            return CoachingMode.CONVERGENT  # Focus on convergence

        elif phase == ConvergencePhase.COMMITTED:
            return CoachingMode.DIRECTIVE  # Guide toward outcomes

        else:  # HANDED_OFF
            return CoachingMode.REFLECTIVE  # Reflect on outcomes

    def _get_portfolio_context(self, org_id: str, pursuit_id: str) -> Dict:
        """Get relevant portfolio context for coaching."""
        if not org_id:
            return {}

        try:
            dashboard = get_portfolio_dashboard()

            # Get health summary
            health_panel = dashboard.get_panel(org_id, PanelType.PORTFOLIO_HEALTH)
            health_data = health_panel.data.get("metrics", {})

            # Find this pursuit in top performers or needs attention
            pursuit_status = "average"
            for p in health_panel.data.get("top_performers", []):
                if p.get("pursuit_id") == pursuit_id:
                    pursuit_status = "top_performer"
                    break
            for p in health_panel.data.get("needs_attention", []):
                if p.get("pursuit_id") == pursuit_id:
                    pursuit_status = "needs_attention"
                    break

            return {
                "portfolio_avg_health": health_data.get("average_health_score", 0.5),
                "pursuit_status_in_portfolio": pursuit_status,
                "active_pursuits_count": health_data.get("active_pursuits", 0)
            }
        except Exception as e:
            logger.warning(f"Error fetching portfolio context: {e}")
            return {}

    def _get_methodology_guidance(self, methodology: str, pursuit: Dict) -> Dict:
        """
        Get methodology-specific guidance.
        v3.7.1: Returns minimal guidance for ad-hoc pursuits.
        """
        # v3.7.1: Handle ad-hoc pursuits
        if methodology == "ad_hoc":
            return {
                "archetype_name": "Freeform",
                "coaching_style": "non_directive",
                "enforcement": "none",
                "current_stage": pursuit.get("current_state", "active"),
                "stage_guidance": "",  # No proactive guidance
                "available_transitions": [],  # Innovator controls flow
                "is_adhoc": True
            }

        archetype = get_archetype(methodology)
        if not archetype:
            return {}

        current_stage = pursuit.get("current_stage", "")
        coaching_style = get_coaching_style(methodology)

        # Get stage-specific guidance
        stage_guidance = ""
        for phase in archetype.phases:
            if phase.name == current_stage:
                stage_guidance = f"Focus on {phase.name}: {phase.description}"
                break

        return {
            "archetype_name": archetype.name,
            "coaching_style": coaching_style,
            "enforcement": archetype.enforcement,
            "current_stage": current_stage,
            "stage_guidance": stage_guidance,
            "available_transitions": [
                t.to_phase for t in archetype.phase_transitions
                if t.from_phase == current_stage
            ],
            "is_adhoc": False
        }

    def enhance_response(
        self,
        base_response: str,
        context: CoachingContext,
        include_portfolio_insights: bool = True
    ) -> EnhancedCoachingResponse:
        """
        Enhance a base coaching response with convergence awareness.

        Adds methodology-specific language, convergence prompts, and
        portfolio insights.
        """
        # Get language adapter
        adapter = CoachingLanguageAdapter(context.methodology_archetype)

        # Adapt base message to methodology
        enhanced_message = base_response

        # Add methodology-specific hints
        methodology_hints = []
        guidance = context.methodology_guidance
        if guidance.get("stage_guidance"):
            methodology_hints.append(guidance["stage_guidance"])

        # Generate convergence prompt based on phase
        convergence_prompt = self._generate_convergence_prompt(context)

        # Generate suggested actions
        suggested_actions = self._generate_suggested_actions(context)

        # Generate portfolio insights if requested
        portfolio_insights = None
        if include_portfolio_insights and context.portfolio_context:
            portfolio_insights = self._generate_portfolio_insights(context)

        return EnhancedCoachingResponse(
            message=enhanced_message,
            coaching_mode=context.coaching_mode,
            convergence_phase=context.current_phase,
            suggested_actions=suggested_actions,
            methodology_hints=methodology_hints,
            convergence_prompt=convergence_prompt,
            portfolio_insights=portfolio_insights,
            metadata={
                "signal_count": len(context.convergence_signals),
                "outcomes_captured": len(context.recent_outcomes)
            }
        )

    def _generate_convergence_prompt(self, context: CoachingContext) -> Optional[str]:
        """
        Generate phase-appropriate convergence prompt.
        v3.7.1: Returns None for non-directive mode.
        """
        # v3.7.1: No convergence prompts in non-directive mode
        if context.coaching_mode == CoachingMode.NON_DIRECTIVE:
            return None

        phase = context.current_phase
        adapter = CoachingLanguageAdapter(context.methodology_archetype)

        if phase == ConvergencePhase.EXPLORING:
            # Check if signals suggest readiness for convergence
            high_signals = [s for s in context.convergence_signals if s.get("score", 0) > 0.6]
            if high_signals:
                return adapter.adapt_transition_prompt(
                    "I notice you might be ready to consolidate your thinking. "
                    "Would you like to capture what you've discovered so far?"
                )
            return None

        elif phase == ConvergencePhase.CONSOLIDATING:
            return adapter.adapt_transition_prompt(
                "Let's work on crystallizing your insights. "
                "What are the key takeaways from our discussion?"
            )

        elif phase == ConvergencePhase.COMMITTED:
            return "You've captured valuable outcomes. Is there anything else "
            "you'd like to add before we complete this session?"

        return None

    def _generate_suggested_actions(self, context: CoachingContext) -> List[str]:
        """
        Generate suggested actions based on context.
        v3.7.1: Returns empty list for non-directive mode.
        """
        # v3.7.1: No suggested actions in non-directive mode
        if context.coaching_mode == CoachingMode.NON_DIRECTIVE:
            return []  # Innovator leads; no suggestions

        actions = []

        phase = context.current_phase

        if phase == ConvergencePhase.EXPLORING:
            actions.extend([
                "Continue exploring the problem space",
                "Ask clarifying questions",
                "Consider alternative perspectives"
            ])

        elif phase == ConvergencePhase.CONSOLIDATING:
            actions.extend([
                "Summarize key insights",
                "Identify decisions to be made",
                "Capture hypotheses to test"
            ])

        elif phase == ConvergencePhase.COMMITTED:
            actions.extend([
                "Review captured outcomes",
                "Plan next steps",
                "Complete handoff"
            ])

        # Add methodology-specific actions
        guidance = context.methodology_guidance
        if guidance.get("available_transitions"):
            for transition in guidance["available_transitions"][:2]:
                actions.append(f"Consider transitioning to {transition} phase")

        return actions[:5]  # Limit to 5 actions

    def _generate_portfolio_insights(self, context: CoachingContext) -> str:
        """Generate portfolio-aware insights."""
        portfolio = context.portfolio_context

        if portfolio.get("pursuit_status_in_portfolio") == "top_performer":
            return (
                "This pursuit is performing well compared to others in your portfolio. "
                "Consider what practices are working and how they might apply elsewhere."
            )

        elif portfolio.get("pursuit_status_in_portfolio") == "needs_attention":
            return (
                "This pursuit could benefit from focused attention. "
                "Consider what obstacles might be slowing progress."
            )

        avg_health = portfolio.get("portfolio_avg_health", 0.5)
        if avg_health < 0.5:
            return (
                "Your portfolio overall is showing some stress. "
                "It might be worth reviewing priorities and resource allocation."
            )

        return ""


# =============================================================================
# ORG INTELLIGENCE INTEGRATION
# =============================================================================

class OrgIntelligenceProvider:
    """
    Provides organization-level intelligence for coaching.

    Aggregates patterns, best practices, and learnings from
    across the organization.
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_duration = timedelta(minutes=15)

    def get_org_best_practices(self, org_id: str, pursuit_type: str = None) -> List[Dict]:
        """
        Get organization best practices relevant to current context.

        Returns practices learned from successful pursuits.
        """
        cache_key = f"best_practices:{org_id}:{pursuit_type or 'all'}"

        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        practices = []

        # Get successful pursuits
        pursuits = db.get_pursuits_by_org(org_id) or []
        successful = [
            p for p in pursuits
            if p.get("health_score", 0) >= 0.8 or
               p.get("status") in ["completed", "launched"]
        ]

        # Extract practices from successful pursuits
        for pursuit in successful[:10]:
            # Get coaching outcomes
            sessions = db.get_pursuit_convergence_sessions(pursuit.get("pursuit_id"), limit=5) or []
            for session in sessions:
                for outcome in session.get("outcomes_captured", []):
                    if outcome.get("outcome_type") == "INSIGHT":
                        practices.append({
                            "source_pursuit_id": pursuit.get("pursuit_id"),
                            "source_pursuit_name": pursuit.get("name"),
                            "insight": outcome.get("summary"),
                            "methodology": pursuit.get("methodology_archetype"),
                            "stage": pursuit.get("current_stage")
                        })

        # Limit and cache
        practices = practices[:20]
        self._cache[cache_key] = practices
        self._cache_expiry[cache_key] = datetime.now(timezone.utc)

        return practices

    def get_similar_pursuits(self, org_id: str, pursuit_id: str) -> List[Dict]:
        """
        Find similar pursuits in the organization.

        Useful for learning from comparable initiatives.
        """
        target_pursuit = db.get_pursuit(pursuit_id) or {}
        target_tags = target_pursuit.get("tags", [])
        target_type = target_pursuit.get("pursuit_type", "")

        pursuits = db.get_pursuits_by_org(org_id) or []

        similar = []
        for pursuit in pursuits:
            if pursuit.get("pursuit_id") == pursuit_id:
                continue

            # Calculate similarity based on tags and type
            pursuit_tags = pursuit.get("tags", [])
            tag_overlap = len(set(target_tags) & set(pursuit_tags))
            type_match = pursuit.get("pursuit_type") == target_type

            if tag_overlap > 0 or type_match:
                similar.append({
                    "pursuit_id": pursuit.get("pursuit_id"),
                    "name": pursuit.get("name"),
                    "status": pursuit.get("status"),
                    "health_score": pursuit.get("health_score", 0.5),
                    "tag_overlap": tag_overlap,
                    "type_match": type_match,
                    "similarity_score": (tag_overlap * 0.3 + (1 if type_match else 0) * 0.7)
                })

        # Sort by similarity and return top 5
        similar.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similar[:5]

    def get_org_coaching_patterns(self, org_id: str) -> Dict:
        """
        Get organization-wide coaching patterns.

        Identifies common themes, successful strategies, and areas
        for improvement.
        """
        cache_key = f"coaching_patterns:{org_id}"

        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        patterns = {
            "common_outcome_types": {},
            "avg_session_duration": 0,
            "avg_outcomes_per_session": 0,
            "successful_methodologies": [],
            "challenging_stages": []
        }

        # Analyze convergence sessions
        pursuits = db.get_pursuits_by_org(org_id) or []

        total_sessions = 0
        total_outcomes = 0
        methodology_success = {}
        stage_health = {}

        for pursuit in pursuits[:50]:  # Limit for performance
            sessions = db.get_pursuit_convergence_sessions(pursuit.get("pursuit_id"), limit=10) or []

            for session in sessions:
                total_sessions += 1
                outcomes = session.get("outcomes_captured", [])
                total_outcomes += len(outcomes)

                for outcome in outcomes:
                    otype = outcome.get("outcome_type", "")
                    patterns["common_outcome_types"][otype] = \
                        patterns["common_outcome_types"].get(otype, 0) + 1

            # Track methodology success
            methodology = pursuit.get("methodology_archetype", "lean_startup")
            health = pursuit.get("health_score", 0.5)
            if methodology not in methodology_success:
                methodology_success[methodology] = []
            methodology_success[methodology].append(health)

            # Track stage health
            stage = pursuit.get("current_stage", "unknown")
            if stage not in stage_health:
                stage_health[stage] = []
            stage_health[stage].append(health)

        # Calculate averages
        if total_sessions > 0:
            patterns["avg_outcomes_per_session"] = round(total_outcomes / total_sessions, 2)

        # Find successful methodologies
        for methodology, scores in methodology_success.items():
            avg = sum(scores) / len(scores) if scores else 0
            if avg >= 0.7:
                patterns["successful_methodologies"].append({
                    "methodology": methodology,
                    "avg_health": round(avg, 2),
                    "sample_size": len(scores)
                })

        # Find challenging stages
        for stage, scores in stage_health.items():
            avg = sum(scores) / len(scores) if scores else 0
            if avg < 0.5:
                patterns["challenging_stages"].append({
                    "stage": stage,
                    "avg_health": round(avg, 2),
                    "sample_size": len(scores)
                })

        self._cache[cache_key] = patterns
        self._cache_expiry[cache_key] = datetime.now(timezone.utc)

        return patterns

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid."""
        if key not in self._cache:
            return False
        expiry = self._cache_expiry.get(key)
        if not expiry:
            return False
        return datetime.now(timezone.utc) < expiry + self._cache_duration


# =============================================================================
# SINGLETON ACCESSORS
# =============================================================================

_convergence_coach: Optional[ConvergenceAwareCoach] = None
_org_intelligence: Optional[OrgIntelligenceProvider] = None


def get_convergence_coach() -> ConvergenceAwareCoach:
    """Get singleton ConvergenceAwareCoach instance."""
    global _convergence_coach
    if _convergence_coach is None:
        _convergence_coach = ConvergenceAwareCoach()
    return _convergence_coach


def get_org_intelligence() -> OrgIntelligenceProvider:
    """Get singleton OrgIntelligenceProvider instance."""
    global _org_intelligence
    if _org_intelligence is None:
        _org_intelligence = OrgIntelligenceProvider()
    return _org_intelligence
