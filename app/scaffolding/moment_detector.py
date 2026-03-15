"""
InDE MVP v3.0.3 - Moment Detector "Analytics & Synthesis"

Detects 10 critical moments when natural interventions would add value.
Interventions are suggestions made conversationally, not system prompts.

The 10 Moment Types:
1. CRITICAL_GAP - Missing essential information that blocks progress
2. READY_TO_FORMALIZE - Enough info to create formal artifact (75%+)
3. FEAR_OPPORTUNITY - User expressed worry/concern worth capturing
4. NATURAL_TRANSITION - Natural point to shift focus (e.g., vision done, move to fears)
5. ARTIFACT_DRIFT - Artifact is stale due to evolved scaffolding elements

v2.5 Types:
6. PATTERN_RELEVANT - Historical pattern matches current context
7. CROSS_PURSUIT_INSIGHT - Connection between user's own pursuits detected
8. METHODOLOGY_GUIDANCE - Natural phase transition point detected

v2.6 Type:
9. STAKEHOLDER_ENGAGEMENT_PROMPT - Prompt to capture stakeholder feedback at transitions

v3.0.3 Type:
10. PORTFOLIO_INSIGHT - Portfolio-level insight ready to surface (cooldown: 120s, priority: MEDIUM)
    - Triggers on portfolio health changes, cross-pursuit patterns, velocity anomalies
    - Surfaces portfolio analytics insights naturally in conversation
    - Never judgmental - always informational
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from config import MOMENT_TYPES, COOLDOWNS, READINESS_THRESHOLD, STAKEHOLDER_PROMPT_TRIGGERS, PORTFOLIO_MOMENT_TYPE


class MomentDetector:
    """
    Detects 10 types of intervention moments (v3.0.3: added portfolio insight).
    Interventions are suggestions made conversationally, not system prompts.
    """

    # Keywords that suggest fear/concern expression
    FEAR_KEYWORDS = [
        r"\bworried\b", r"\bconcerned\b", r"\bafraid\b", r"\bfear\b",
        r"\bscared\b", r"\bnervous\b", r"\banxious\b", r"\bworry\b",
        r"\bwhat if\b", r"\bwhat about\b", r"\brisks?\b", r"\bproblems?\b",
        r"\bchallenges?\b", r"\bdifficult\b", r"\bhard\b", r"\btricky\b",
        r"\bi don't know (if|how|whether)\b", r"\bnot sure\b",
        r"\bmight (fail|not work)\b", r"\bcould go wrong\b"
    ]

    # v2.6: Keywords that suggest pitching/presenting
    PITCH_KEYWORDS = [
        r"\bpitch\b", r"\bpresent\b", r"\bpresentation\b", r"\bmeeting\b",
        r"\bproposal\b", r"\bpropose\b", r"\bdemonstrate\b", r"\bdemo\b",
        r"\bshow\b", r"\bstakeholder\b", r"\binvestor\b", r"\bboard\b"
    ]

    def __init__(self, element_tracker, database, lifecycle_manager=None,
                 pattern_engine=None, adaptive_manager=None, portfolio_intelligence=None):
        """
        Initialize MomentDetector.

        Args:
            element_tracker: ElementTracker instance for completeness checks
            database: Database instance for intervention history
            lifecycle_manager: v2.4 - ArtifactLifecycleManager for drift detection (optional)
            pattern_engine: v2.5 - PatternEngine for pattern-based interventions (optional)
            adaptive_manager: v2.5 - AdaptiveInterventionManager for cooldowns (optional)
            portfolio_intelligence: v3.0.3 - PortfolioIntelligenceEngine for portfolio insights (optional)
        """
        self.tracker = element_tracker
        self.db = database
        self.lifecycle_manager = lifecycle_manager  # v2.4: for ARTIFACT_DRIFT
        self.pattern_engine = pattern_engine        # v2.5: for PATTERN_RELEVANT
        self.adaptive_manager = adaptive_manager    # v2.5: for adaptive cooldowns
        self.portfolio_intelligence = portfolio_intelligence  # v3.0.3: for PORTFOLIO_INSIGHT
        self._fear_patterns = [re.compile(p, re.IGNORECASE) for p in self.FEAR_KEYWORDS]
        self._pitch_patterns = [re.compile(p, re.IGNORECASE) for p in self.PITCH_KEYWORDS]  # v2.6
        self._current_user_id = None  # Track for cross-pursuit detection
        self._stakeholder_prompted_pursuits = set()  # v2.6: Track which pursuits have been prompted
        self._last_portfolio_health = {}  # v3.0.3: Track portfolio health for change detection

    def detect_moments(self, pursuit_id: str, recent_message: str,
                       user_id: str = None) -> List[Dict]:
        """
        Detect intervention moments for this turn.

        Args:
            pursuit_id: Current pursuit ID
            recent_message: The user's most recent message
            user_id: v2.5 - User ID for cross-pursuit detection

        Returns:
            List of moments, sorted by priority (highest first), e.g.:
            [
                {
                    "type": "READY_TO_FORMALIZE",
                    "priority": 2,
                    "suggestion": "We've covered a lot about the problem and solution...",
                    "artifact_type": "vision",
                    "completeness": 0.875
                }
            ]
        """
        moments = []
        self._current_user_id = user_id  # Store for cross-pursuit checks

        # Get current completeness
        completeness = self.tracker.get_completeness(pursuit_id)

        # 1. Check for READY_TO_FORMALIZE
        ready_moment = self._check_ready_to_formalize(pursuit_id, completeness)
        if ready_moment:
            moments.append(ready_moment)

        # 2. Check for FEAR_OPPORTUNITY
        fear_moment = self._check_fear_opportunity(pursuit_id, recent_message, completeness)
        if fear_moment:
            moments.append(fear_moment)

        # 3. Check for CRITICAL_GAP (only if not ready to formalize)
        if not ready_moment:
            gap_moment = self._check_critical_gap(pursuit_id, completeness)
            if gap_moment:
                moments.append(gap_moment)

        # 4. Check for NATURAL_TRANSITION
        transition_moment = self._check_natural_transition(pursuit_id, completeness)
        if transition_moment:
            moments.append(transition_moment)

        # 5. v2.4: Check for ARTIFACT_DRIFT (stale artifacts due to evolved elements)
        if self.lifecycle_manager:
            drift_moment = self._check_artifact_drift(pursuit_id)
            if drift_moment:
                moments.append(drift_moment)

        # 6. v2.5: Check for PATTERN_RELEVANT (historical pattern matches)
        if self.pattern_engine:
            pattern_moment = self._check_pattern_relevant(pursuit_id)
            if pattern_moment:
                moments.append(pattern_moment)

        # 7. v2.5: Check for CROSS_PURSUIT_INSIGHT (connections to user's other pursuits)
        if self.pattern_engine and user_id:
            cross_moment = self._check_cross_pursuit_insight(pursuit_id, user_id)
            if cross_moment:
                moments.append(cross_moment)

        # 8. v2.5: Check for METHODOLOGY_GUIDANCE (phase transition guidance)
        methodology_moment = self._check_methodology_guidance(pursuit_id, completeness)
        if methodology_moment:
            moments.append(methodology_moment)

        # 9. v2.6: Check for STAKEHOLDER_ENGAGEMENT_PROMPT
        stakeholder_moment = self._check_stakeholder_engagement_prompt(
            pursuit_id, recent_message, completeness
        )
        if stakeholder_moment:
            moments.append(stakeholder_moment)

        # 10. v3.0.3: Check for PORTFOLIO_INSIGHT
        if self.portfolio_intelligence and user_id:
            portfolio_moment = self._check_portfolio_insight(pursuit_id, user_id)
            if portfolio_moment:
                moments.append(portfolio_moment)

        # Sort by priority (lower number = higher priority)
        moments.sort(key=lambda m: m["priority"])

        return moments

    def should_intervene(self, pursuit_id: str, moment_type: str) -> bool:
        """
        Check if enough time has passed since last intervention of this type.

        Args:
            pursuit_id: Pursuit ID
            moment_type: Type of moment to check

        Returns:
            True if intervention is allowed, False if still in cooldown
        """
        last_intervention = self.db.get_last_intervention(pursuit_id, moment_type)

        if not last_intervention:
            return True

        cooldown_minutes = COOLDOWNS.get(moment_type, 15)
        cooldown_delta = timedelta(minutes=cooldown_minutes)
        last_time = last_intervention.get("timestamp", datetime.min.replace(tzinfo=timezone.utc))

        # Handle both datetime objects and strings
        if isinstance(last_time, str):
            try:
                last_time = datetime.fromisoformat(last_time)
            except (ValueError, TypeError):
                last_time = datetime.min.replace(tzinfo=timezone.utc)

        # Ensure timezone-aware for comparison
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)

        return datetime.now(timezone.utc) - last_time > cooldown_delta

    def record_intervention(self, pursuit_id: str, moment_type: str,
                            suggestion: str) -> None:
        """Record that an intervention was made."""
        self.db.record_intervention(pursuit_id, moment_type, suggestion)

    def _check_ready_to_formalize(self, pursuit_id: str,
                                   completeness: Dict[str, float]) -> Optional[Dict]:
        """Check if any artifact type is ready to formalize (75%+ complete)."""

        # Check in priority order: vision first, then fears, then hypothesis
        for artifact_type in ["vision", "fears", "hypothesis"]:
            type_key = artifact_type if artifact_type != "fears" else "fears"
            comp = completeness.get(type_key, 0.0)

            print(f"[MomentDetector] Checking {artifact_type}: comp={comp:.2f}, threshold={READINESS_THRESHOLD}")

            if comp >= READINESS_THRESHOLD:
                can_intervene = self.should_intervene(pursuit_id, "READY_TO_FORMALIZE")
                print(f"[MomentDetector] {artifact_type} >= threshold, can_intervene={can_intervene}")

                if can_intervene:
                    # Check if artifact already exists
                    existing = self.db.get_pursuit_artifacts(pursuit_id, artifact_type)
                    print(f"[MomentDetector] Existing artifacts for {artifact_type}: {len(existing)}")

                    if existing:
                        continue  # Skip if already generated

                    print(f"[MomentDetector] READY_TO_FORMALIZE triggered for {artifact_type}!")
                    return {
                        "type": "READY_TO_FORMALIZE",
                        "priority": MOMENT_TYPES["READY_TO_FORMALIZE"]["priority"],
                        "suggestion": self._get_formalize_suggestion(artifact_type, comp),
                        "artifact_type": artifact_type,
                        "completeness": comp
                    }

        return None

    def _check_fear_opportunity(self, pursuit_id: str, message: str,
                                 completeness: Dict[str, float]) -> Optional[Dict]:
        """Check if user expressed a fear/concern worth capturing."""

        # Only look for fears if we have some vision foundation
        if completeness.get("vision", 0.0) < 0.25:
            return None

        # Check for fear keywords
        has_fear_signal = any(p.search(message) for p in self._fear_patterns)

        if has_fear_signal and self.should_intervene(pursuit_id, "FEAR_OPPORTUNITY"):
            return {
                "type": "FEAR_OPPORTUNITY",
                "priority": MOMENT_TYPES["FEAR_OPPORTUNITY"]["priority"],
                "suggestion": "That sounds like an important concern. Want to explore that worry a bit more?",
                "artifact_type": "fears",
                "completeness": completeness.get("fears", 0.0)
            }

        return None

    def _check_critical_gap(self, pursuit_id: str,
                            completeness: Dict[str, float]) -> Optional[Dict]:
        """Check for critical missing elements that block progress."""

        # Only suggest gaps if we have some progress but not enough
        vision_comp = completeness.get("vision", 0.0)

        # If vision is very early, let conversation flow naturally
        if vision_comp < 0.125:  # Less than 1 element
            return None

        # If vision is close to ready, don't interrupt
        if vision_comp >= READINESS_THRESHOLD - 0.125:
            return None

        if self.should_intervene(pursuit_id, "CRITICAL_GAP"):
            gap = self.tracker.get_most_critical_gap(pursuit_id)
            if gap:
                return {
                    "type": "CRITICAL_GAP",
                    "priority": MOMENT_TYPES["CRITICAL_GAP"]["priority"],
                    "suggestion": gap["suggestion"],
                    "artifact_type": gap["artifact_type"],
                    "missing_element": gap["element"]
                }

        return None

    def _check_natural_transition(self, pursuit_id: str,
                                   completeness: Dict[str, float]) -> Optional[Dict]:
        """Check if it's a natural point to shift focus."""

        # Check if vision is complete but fears haven't started
        vision_comp = completeness.get("vision", 0.0)
        fears_comp = completeness.get("fears", 0.0)

        if vision_comp >= READINESS_THRESHOLD and fears_comp < 0.167:  # Vision done, fears not started
            # Check if vision artifact exists
            vision_artifacts = self.db.get_pursuit_artifacts(pursuit_id, "vision")
            if vision_artifacts and self.should_intervene(pursuit_id, "NATURAL_TRANSITION"):
                return {
                    "type": "NATURAL_TRANSITION",
                    "priority": MOMENT_TYPES["NATURAL_TRANSITION"]["priority"],
                    "suggestion": "Now that we've captured your vision, what about concerns? What worries you most about making this real?",
                    "from_artifact": "vision",
                    "to_artifact": "fears"
                }

        # Check if fears complete but hypothesis hasn't started
        hypothesis_comp = completeness.get("hypothesis", 0.0)

        if fears_comp >= READINESS_THRESHOLD and hypothesis_comp < 0.167:
            fears_artifacts = self.db.get_pursuit_artifacts(pursuit_id, "fears")
            if fears_artifacts and self.should_intervene(pursuit_id, "NATURAL_TRANSITION"):
                return {
                    "type": "NATURAL_TRANSITION",
                    "priority": MOMENT_TYPES["NATURAL_TRANSITION"]["priority"],
                    "suggestion": "With those concerns documented, let's think about testing your assumptions. What's the riskiest assumption you're making?",
                    "from_artifact": "fears",
                    "to_artifact": "hypothesis"
                }

        return None

    def _get_formalize_suggestion(self, artifact_type: str, completeness: float) -> str:
        """Get a natural suggestion for formalizing an artifact."""

        pct = int(completeness * 100)

        suggestions = {
            "vision": f"We've covered a lot of ground - the problem, who it's for, your solution. Want me to draft a vision statement that captures everything? ({pct}% of key elements covered)",
            "fears": f"You've shared several important concerns. Shall I organize these into a formal risk document you can reference? ({pct}% of key concerns captured)",
            "hypothesis": f"We have a good sense of your assumptions and how to test them. Want me to formalize this into a testable hypothesis? ({pct}% complete)"
        }

        return suggestions.get(
            artifact_type,
            f"We've covered enough to create a formal {artifact_type} document. Shall I draft one?"
        )

    def _check_artifact_drift(self, pursuit_id: str) -> Optional[Dict]:
        """
        v2.4: Check if any artifacts need regeneration due to evolved elements.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            ARTIFACT_DRIFT moment or None
        """
        if not self.lifecycle_manager:
            return None

        if not self.should_intervene(pursuit_id, "ARTIFACT_DRIFT"):
            return None

        # Detect drift in all artifacts
        drifts = self.lifecycle_manager.detect_artifact_drift(pursuit_id)

        if not drifts:
            return None

        # Find highest severity drift that should suggest regeneration
        for drift in sorted(drifts, key=lambda d: {"MAJOR": 0, "MODERATE": 1, "MINOR": 2}.get(d.get("change_severity", "MINOR"), 2)):
            if drift.get("should_suggest_regen"):
                # Map severity to priority
                priority_map = {
                    "MAJOR": 2,      # High priority - pivot detected
                    "MODERATE": 3,   # Medium priority
                    "MINOR": 5       # Low priority
                }

                suggestion = self.lifecycle_manager.generate_drift_suggestion(drift)

                return {
                    "type": "ARTIFACT_DRIFT",
                    "priority": priority_map.get(drift["change_severity"], 4),
                    "suggestion": suggestion,
                    "artifact_id": drift["artifact_id"],
                    "artifact_type": drift["artifact_type"],
                    "change_severity": drift["change_severity"],
                    "changed_elements": drift.get("changed_elements", []),
                    "metadata": drift
                }

        return None

    # =========================================================================
    # v2.5: NEW INTERVENTION TYPES
    # =========================================================================

    def _check_pattern_relevant(self, pursuit_id: str) -> Optional[Dict]:
        """
        v2.5: Check if relevant historical patterns exist.

        Uses PatternEngine to find patterns that match current context.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            PATTERN_RELEVANT moment or None
        """
        if not self.pattern_engine:
            return None

        if not self.should_intervene(pursuit_id, "PATTERN_RELEVANT"):
            return None

        # Get pursuit context for pattern matching
        context = self.tracker.get_pursuit_context_for_patterns(pursuit_id)

        if not context.get("problem_statement"):
            return None  # Need at least problem to match patterns

        # Find relevant patterns
        patterns = self.pattern_engine.find_relevant_patterns(pursuit_id, context)

        if not patterns:
            return None

        # Get highest relevance pattern
        top_pattern = patterns[0]

        # Only surface if highly relevant
        if top_pattern.get("relevance_score", 0) < 0.70:
            return None

        # Generate natural suggestion
        suggestion = self._generate_pattern_suggestion(top_pattern)

        return {
            "type": "PATTERN_RELEVANT",
            "priority": MOMENT_TYPES["PATTERN_RELEVANT"]["priority"],
            "suggestion": suggestion,
            "pattern_id": top_pattern["pattern_id"],
            "pattern_name": top_pattern.get("pattern_name", ""),
            "relevance_score": top_pattern.get("relevance_score", 0),
            "key_insight": top_pattern.get("key_insight", ""),
            "all_patterns": patterns  # Include all for context
        }

    def _generate_pattern_suggestion(self, pattern: Dict) -> str:
        """Generate natural language suggestion from pattern."""
        insight = pattern.get("key_insight", "")
        action = pattern.get("suggested_action", "")

        if insight and action:
            return f"I've seen similar situations before. {insight[:100]}... {action[:100]}"
        elif insight:
            return f"This reminds me of a pattern we've seen: {insight[:150]}..."
        else:
            return f"There's a relevant insight from similar pursuits that might help here."

    def _check_cross_pursuit_insight(self, pursuit_id: str,
                                      user_id: str) -> Optional[Dict]:
        """
        v2.5: Check for connections to user's other pursuits.

        Args:
            pursuit_id: Current pursuit ID
            user_id: User ID

        Returns:
            CROSS_PURSUIT_INSIGHT moment or None
        """
        if not self.pattern_engine or not user_id:
            return None

        if not self.should_intervene(pursuit_id, "CROSS_PURSUIT_INSIGHT"):
            return None

        # Detect cross-pursuit insights
        insights = self.pattern_engine.detect_cross_pursuit_insights(
            user_id, pursuit_id
        )

        if not insights:
            return None

        # Get highest confidence insight
        top_insight = max(insights, key=lambda i: i.get("confidence", 0))

        if top_insight.get("confidence", 0) < 0.65:
            return None

        # Generate suggestion
        suggestion = self._generate_cross_pursuit_suggestion(top_insight)

        return {
            "type": "CROSS_PURSUIT_INSIGHT",
            "priority": MOMENT_TYPES["CROSS_PURSUIT_INSIGHT"]["priority"],
            "suggestion": suggestion,
            "insight_type": top_insight.get("insight_type", ""),
            "related_pursuit_id": top_insight.get("related_pursuit_id", ""),
            "related_pursuit_title": top_insight.get("related_pursuit_title", ""),
            "confidence": top_insight.get("confidence", 0),
            "all_insights": insights
        }

    def _generate_cross_pursuit_suggestion(self, insight: Dict) -> str:
        """Generate natural suggestion from cross-pursuit insight."""
        insight_type = insight.get("insight_type", "")
        related_title = insight.get("related_pursuit_title", "another project")
        action = insight.get("suggested_action", "")

        if insight_type == "shared_fear":
            return f"I notice a similar concern came up in your {related_title} work. {action}"
        elif insight_type == "similar_assumption":
            return f"This relates to assumptions you explored in {related_title}. {action}"
        elif insight_type == "applicable_learning":
            return f"Your experience with {related_title} might be relevant here. {action}"
        else:
            return f"There might be connections to your {related_title} pursuit worth exploring."

    def _check_methodology_guidance(self, pursuit_id: str,
                                     completeness: Dict[str, float]) -> Optional[Dict]:
        """
        v2.5: Check for natural phase transition guidance opportunities.

        Provides methodology-informed guidance without exposing terminology.
        Different from NATURAL_TRANSITION - this is about process guidance,
        not just prompting for the next artifact.

        Args:
            pursuit_id: Pursuit ID
            completeness: Current completeness scores

        Returns:
            METHODOLOGY_GUIDANCE moment or None
        """
        if not self.should_intervene(pursuit_id, "METHODOLOGY_GUIDANCE"):
            return None

        vision_comp = completeness.get("vision", 0.0)
        fears_comp = completeness.get("fears", 0.0)
        hypothesis_comp = completeness.get("hypothesis", 0.0)

        # Check for methodology guidance opportunities

        # 1. Vision exploration guidance (early stage)
        if vision_comp < 0.4 and vision_comp > 0.1:
            # User has started but not fully explored
            return {
                "type": "METHODOLOGY_GUIDANCE",
                "priority": MOMENT_TYPES["METHODOLOGY_GUIDANCE"]["priority"],
                "suggestion": "Before we go deeper on the solution, let's make sure we fully understand the problem. Who else experiences this pain?",
                "guidance_phase": "vision_exploration",
                "current_completeness": vision_comp
            }

        # 2. Fear exploration prompt (after good vision)
        if vision_comp >= 0.6 and fears_comp < 0.2:
            # Strong vision but no fear exploration
            return {
                "type": "METHODOLOGY_GUIDANCE",
                "priority": MOMENT_TYPES["METHODOLOGY_GUIDANCE"]["priority"],
                "suggestion": "Your vision is coming together nicely. Now, what's the thing that could most derail this? What keeps you up at night?",
                "guidance_phase": "fear_exploration",
                "current_completeness": fears_comp
            }

        # 3. Hypothesis formation prompt (after fears addressed)
        if fears_comp >= 0.5 and hypothesis_comp < 0.2:
            return {
                "type": "METHODOLOGY_GUIDANCE",
                "priority": MOMENT_TYPES["METHODOLOGY_GUIDANCE"]["priority"],
                "suggestion": "You've identified key concerns. What's your riskiest assumption? What would have to be true for this to work?",
                "guidance_phase": "hypothesis_formation",
                "current_completeness": hypothesis_comp
            }

        # 4. Validation readiness (all basics covered)
        if vision_comp >= 0.75 and fears_comp >= 0.5 and hypothesis_comp >= 0.5:
            return {
                "type": "METHODOLOGY_GUIDANCE",
                "priority": MOMENT_TYPES["METHODOLOGY_GUIDANCE"]["priority"],
                "suggestion": "You've done solid groundwork. What's the smallest, fastest way you could test your core assumption?",
                "guidance_phase": "validation_readiness",
                "current_completeness": (vision_comp + fears_comp + hypothesis_comp) / 3
            }

        return None

    def _check_stakeholder_engagement_prompt(self, pursuit_id: str,
                                              message: str,
                                              completeness: Dict[str, float]) -> Optional[Dict]:
        """
        v2.6: Check if stakeholder engagement prompt should be offered.

        Triggers:
        - State transitions (vision complete -> solution, solution -> building)
        - Before pitch mentions
        - Only if no stakeholder feedback captured yet
        - Respects advisory enforcement mode (never blocks)

        Args:
            pursuit_id: Pursuit ID
            message: Current user message
            completeness: Current completeness scores

        Returns:
            STAKEHOLDER_ENGAGEMENT_PROMPT moment or None
        """
        # Check if already prompted for this pursuit
        if pursuit_id in self._stakeholder_prompted_pursuits:
            return None

        # Check if stakeholder feedback already exists
        existing_count = self.db.count_stakeholder_feedback(pursuit_id)
        if existing_count > 0:
            # Already have feedback, don't prompt
            return None

        # Check for pitch-related keywords in message
        has_pitch_signal = any(p.search(message) for p in self._pitch_patterns)

        if has_pitch_signal:
            # Mark as prompted
            self._stakeholder_prompted_pursuits.add(pursuit_id)

            return {
                "type": "STAKEHOLDER_ENGAGEMENT_PROMPT",
                "priority": MOMENT_TYPES["STAKEHOLDER_ENGAGEMENT_PROMPT"]["priority"],
                "suggestion": self._generate_stakeholder_prompt_message("before_pitch"),
                "trigger": "before_pitch",
                "dismissible": True
            }

        # Check for phase transitions
        vision_comp = completeness.get("vision", 0.0)
        fears_comp = completeness.get("fears", 0.0)
        hypothesis_comp = completeness.get("hypothesis", 0.0)

        # Trigger at vision complete (PROBLEM_VALIDATION -> SOLUTION_REFINEMENT)
        if vision_comp >= 0.75 and fears_comp < 0.25:
            # Check if vision artifact exists (indicates transition point)
            vision_artifacts = self.db.get_pursuit_artifacts(pursuit_id, "vision")
            if vision_artifacts:
                # Mark as prompted
                self._stakeholder_prompted_pursuits.add(pursuit_id)

                return {
                    "type": "STAKEHOLDER_ENGAGEMENT_PROMPT",
                    "priority": MOMENT_TYPES["STAKEHOLDER_ENGAGEMENT_PROMPT"]["priority"],
                    "suggestion": self._generate_stakeholder_prompt_message("vision_complete"),
                    "trigger": "vision_complete",
                    "dismissible": True
                }

        # Trigger when ready to build (SOLUTION_REFINEMENT -> BUILDING)
        if vision_comp >= 0.75 and fears_comp >= 0.5 and hypothesis_comp >= 0.5:
            # Mark as prompted
            self._stakeholder_prompted_pursuits.add(pursuit_id)

            return {
                "type": "STAKEHOLDER_ENGAGEMENT_PROMPT",
                "priority": MOMENT_TYPES["STAKEHOLDER_ENGAGEMENT_PROMPT"]["priority"],
                "suggestion": self._generate_stakeholder_prompt_message("ready_to_build"),
                "trigger": "ready_to_build",
                "dismissible": True
            }

        return None

    def _generate_stakeholder_prompt_message(self, trigger: str) -> str:
        """
        v2.6: Generate contextual prompt message for stakeholder engagement.

        Args:
            trigger: Type of trigger (vision_complete, ready_to_build, before_pitch)

        Returns:
            Prompt message string
        """
        messages = {
            "vision_complete": (
                "You've made great progress defining your vision. Before we explore solutions, "
                "have you engaged any stakeholders about this pursuit? (managers, potential users, "
                "resource holders, etc.) Their input can help validate your direction."
            ),
            "ready_to_build": (
                "You're nearing the point of building. Have you gathered feedback from "
                "stakeholders who will need to support implementation? Understanding their "
                "concerns now can save time later."
            ),
            "before_pitch": (
                "Before pitching, capturing stakeholder feedback can strengthen your "
                "presentation. Have you engaged any key decision-makers? Their perspectives "
                "can help you anticipate questions and objections."
            )
        }

        return messages.get(trigger,
            "Have you engaged any stakeholders about this pursuit? Their feedback "
            "can provide valuable perspective."
        )

    def clear_stakeholder_prompt_for_pursuit(self, pursuit_id: str):
        """
        v2.6: Clear stakeholder prompt tracking for a pursuit.

        Call this if you want to re-enable prompting (e.g., after user declines
        and significant time has passed).

        Args:
            pursuit_id: Pursuit ID
        """
        self._stakeholder_prompted_pursuits.discard(pursuit_id)

    def should_intervene_adaptive(self, pursuit_id: str, moment_type: str,
                                   user_id: str = None) -> bool:
        """
        v2.5: Check if intervention is allowed using adaptive cooldowns.

        Falls back to standard cooldowns if adaptive manager not available.

        Args:
            pursuit_id: Pursuit ID
            moment_type: Type of moment
            user_id: User ID for engagement calculation

        Returns:
            True if intervention is allowed
        """
        last_intervention = self.db.get_last_intervention(pursuit_id, moment_type)
        last_time = None

        if last_intervention:
            last_time = last_intervention.get("timestamp")
            if isinstance(last_time, str):
                try:
                    last_time = datetime.fromisoformat(last_time)
                except (ValueError, TypeError):
                    last_time = None

        # Use adaptive manager if available
        if self.adaptive_manager and user_id:
            return self.adaptive_manager.should_intervene(
                user_id, pursuit_id, moment_type, last_time
            )

        # Fall back to standard cooldown check
        return self.should_intervene(pursuit_id, moment_type)

    # =========================================================================
    # v3.0.3: PORTFOLIO INSIGHT DETECTION
    # =========================================================================

    def _check_portfolio_insight(self, pursuit_id: str, user_id: str) -> Optional[Dict]:
        """
        v3.0.3: Check for portfolio-level insights to surface.

        Triggers:
        - Portfolio health changed significantly
        - Cross-pursuit pattern detected
        - Velocity anomaly detected
        - IKF contribution ready for review

        Args:
            pursuit_id: Current pursuit ID
            user_id: User ID

        Returns:
            PORTFOLIO_INSIGHT moment or None
        """
        if not self.portfolio_intelligence:
            return None

        # Check cooldown (120 seconds)
        cooldown_minutes = PORTFOLIO_MOMENT_TYPE.get("cooldown_minutes", 2)
        last_intervention = self.db.get_last_intervention(pursuit_id, "PORTFOLIO_INSIGHT")
        if last_intervention:
            last_time = last_intervention.get("timestamp")
            if isinstance(last_time, str):
                try:
                    last_time = datetime.fromisoformat(last_time)
                except (ValueError, TypeError):
                    last_time = None

            # Ensure timezone-aware for comparison
            if last_time and last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)

            if last_time and (datetime.now(timezone.utc) - last_time).total_seconds() < cooldown_minutes * 60:
                return None

        # Get portfolio health
        try:
            portfolio_health = self.portfolio_intelligence.calculate_portfolio_health(user_id)
        except Exception:
            return None

        pursuit_count = portfolio_health.get("pursuit_count", 0)
        if pursuit_count < 2:
            return None  # Need multi-pursuit context

        # Check for portfolio health change
        current_score = portfolio_health.get("health_score", 50)
        current_zone = portfolio_health.get("zone", "HEALTHY")
        previous_score = self._last_portfolio_health.get(user_id, {}).get("score", current_score)
        previous_zone = self._last_portfolio_health.get(user_id, {}).get("zone", current_zone)

        # Update tracking
        self._last_portfolio_health[user_id] = {"score": current_score, "zone": current_zone}

        insight = None
        trigger = None

        # 1. Zone change detection
        if current_zone != previous_zone:
            if current_zone in ["CRITICAL", "AT_RISK"] and previous_zone not in ["CRITICAL", "AT_RISK"]:
                insight = self._generate_health_decline_insight(current_zone, portfolio_health)
                trigger = "portfolio_health_declined"
            elif current_zone in ["THRIVING", "HEALTHY"] and previous_zone in ["CRITICAL", "AT_RISK"]:
                insight = self._generate_health_improvement_insight(current_zone, portfolio_health)
                trigger = "portfolio_health_improved"

        # 2. Check for cross-pursuit patterns
        if not insight:
            try:
                patterns = self.portfolio_intelligence.detect_portfolio_patterns(user_id)
                if patterns:
                    top_pattern = patterns[0]
                    if top_pattern.get("confidence", 0) >= 0.7:
                        insight = self._generate_portfolio_pattern_insight(top_pattern)
                        trigger = "cross_pursuit_pattern_detected"
            except Exception:
                pass

        # 3. Check for velocity recommendations
        if not insight:
            try:
                recommendations = self.portfolio_intelligence.generate_portfolio_recommendations(user_id)
                if recommendations:
                    # Only surface high-priority recommendations
                    high_priority = [r for r in recommendations if r.get("priority") == "HIGH"]
                    if high_priority:
                        insight = self._generate_recommendation_insight(high_priority[0])
                        trigger = "portfolio_recommendation"
            except Exception:
                pass

        if insight:
            return {
                "type": "PORTFOLIO_INSIGHT",
                "priority": PORTFOLIO_MOMENT_TYPE.get("priority", 4),
                "suggestion": insight,
                "trigger": trigger,
                "portfolio_health": current_score,
                "portfolio_zone": current_zone,
                "pursuit_count": pursuit_count
            }

        return None

    def _generate_health_decline_insight(self, zone: str, health_data: Dict) -> str:
        """Generate insight for portfolio health decline."""
        breakdown = health_data.get("breakdown", {})
        at_risk_count = breakdown.get("AT_RISK", 0) + breakdown.get("CRITICAL", 0)

        if at_risk_count > 0:
            return (
                f"I notice your portfolio has some pursuits that might need attention. "
                f"Would you like to take a look at what's happening with them?"
            )
        else:
            return (
                "Your portfolio overall seems to be slowing down a bit. "
                "Is there anything blocking progress that we could talk through?"
            )

    def _generate_health_improvement_insight(self, zone: str, health_data: Dict) -> str:
        """Generate insight for portfolio health improvement."""
        return (
            "Your portfolio is looking healthier! "
            "You've made good progress. Shall we capitalize on this momentum?"
        )

    def _generate_portfolio_pattern_insight(self, pattern: Dict) -> str:
        """Generate insight for detected cross-pursuit pattern."""
        pattern_type = pattern.get("pattern_type", "")
        description = pattern.get("description", "")

        if pattern_type == "SHARED_RISK":
            return (
                f"I noticed a common concern across some of your pursuits. "
                f"{description[:100]}... Would you like to explore this?"
            )
        elif pattern_type == "COMMON_BLOCKER":
            return (
                f"Several of your pursuits seem to be facing a similar challenge. "
                f"Addressing it once might help multiple projects."
            )
        elif pattern_type == "SYNERGY":
            return (
                f"There might be an opportunity to connect some of your pursuits. "
                f"{description[:100]}..."
            )
        else:
            return f"I've noticed something interesting across your pursuits: {description[:100]}..."

    def _generate_recommendation_insight(self, recommendation: Dict) -> str:
        """Generate insight from portfolio recommendation."""
        recommendation_text = recommendation.get("recommendation", "")
        return f"Based on how your pursuits are progressing, {recommendation_text[:150]}"
