"""
InDE MVP v2.6 - Pattern Engine

Connects pursuit context to organizational memory (IML - Innovation Memory Layer).
Surfaces relevant historical patterns during conversation.

Key Capabilities:
- Real-time pattern matching using semantic similarity
- Cross-pursuit insight detection
- Proto-pattern extraction from completed pursuits
- Pattern effectiveness tracking
- v2.6: Stakeholder engagement pattern learning
- v4.4: Momentum-lift scoring integration in pattern ranking

This is the core differentiator - making InDE learn from every
innovation attempt and share that wisdom with future innovators.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from config import (
    PATTERN_ENGINE_CONFIG, PATTERN_MATCHING_PROMPT,
    CROSS_PURSUIT_PROMPT, PROTO_PATTERN_EXTRACTION_PROMPT
)

# v4.4: Momentum-lift scoring integration (guarded import)
try:
    from modules.iml.momentum_lift_scorer import MomentumLiftScorer
    _lift_scorer = MomentumLiftScorer()
    MOMENTUM_LIFT_AVAILABLE = True
except Exception:
    MOMENTUM_LIFT_AVAILABLE = False
    _lift_scorer = None

# v4.4: Momentum lift weight — 20% of final scoring
MOMENTUM_LIFT_WEIGHT = 0.20


class PatternEngine:
    """
    Connects pursuit context to organizational memory (IML).
    Surfaces relevant historical patterns during conversation.
    """

    def __init__(self, llm_interface, database):
        """
        Initialize PatternEngine.

        Args:
            llm_interface: LLMInterface instance for semantic matching
            database: Database instance for pattern storage
        """
        self.llm = llm_interface
        self.db = database
        self.config = PATTERN_ENGINE_CONFIG

        # Cache for pattern results (reduces API calls)
        self._pattern_cache = {}
        self._cache_ttl = self.config.get("pattern_cache_ttl_seconds", 300)

        print(f"[PatternEngine] Initialized with config: {self.config}")

    def find_relevant_patterns(self, pursuit_id: str, context: Dict) -> List[Dict]:
        """
        Find patterns relevant to current pursuit context.

        Process:
        1. Extract pursuit characteristics (domain, problem type, stage)
        2. Query patterns collection for similar contexts
        3. Score patterns by relevance + effectiveness
        4. Return top 3-5 patterns with explanations

        Args:
            pursuit_id: Current pursuit
            context: {
                "problem_statement": str,
                "solution_concept": str,
                "domain": str,
                "stage": "vision|fear|hypothesis|execute",
                "key_challenges": [str]
            }

        Returns:
            [
                {
                    "pattern_id": "uuid",
                    "pattern_name": "Resource Constraint Pivot",
                    "relevance_score": 0.87,
                    "effectiveness_score": 0.72,
                    "similar_pursuits": 3,
                    "outcome_distribution": {
                        "success": 2,
                        "pivot": 1,
                        "fail": 0
                    },
                    "key_insight": "Teams that faced similar constraints succeeded by...",
                    "suggested_action": "Consider validating assumptions before building..."
                }
            ]
        """
        if not self.config.get("enable_pattern_matching", True):
            return []

        # Check cache first
        cache_key = f"{pursuit_id}:{context.get('domain', '')}:{context.get('stage', '')}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        print(f"[PatternEngine] Finding patterns for pursuit: {pursuit_id}")
        print(f"[PatternEngine] Context: {context}")

        # Phase 1: Fast metadata filter
        candidate_patterns = self._filter_candidates(context)
        print(f"[PatternEngine] Found {len(candidate_patterns)} candidate patterns")

        if not candidate_patterns:
            return []

        # Phase 2: Score by relevance
        matching_mode = self.config.get("matching_mode", "semantic")

        if matching_mode == "semantic" and not self.llm.demo_mode:
            scored_patterns = self._semantic_scoring(candidate_patterns, context)
        else:
            scored_patterns = self._keyword_scoring(candidate_patterns, context)

        # Phase 3: Filter by thresholds
        relevance_threshold = self.config.get("relevance_threshold", 0.70)
        effectiveness_threshold = self.config.get("effectiveness_threshold", 0.50)

        filtered = [
            p for p in scored_patterns
            if p.get("relevance_score", 0) >= relevance_threshold
            and p.get("effectiveness_score", 0) >= effectiveness_threshold
        ]

        # Limit results
        max_patterns = self.config.get("max_patterns_per_turn", 3)
        results = filtered[:max_patterns]

        # Cache results
        self._add_to_cache(cache_key, results)

        # Record pattern applications
        for pattern in results:
            self.db.record_pattern_application(
                pattern["pattern_id"],
                pursuit_id,
                pattern.get("relevance_score", 0)
            )

        print(f"[PatternEngine] Returning {len(results)} relevant patterns")
        return results

    def _filter_candidates(self, context: Dict) -> List[Dict]:
        """
        Phase 1: Filter patterns by metadata match.

        Uses domain and effectiveness threshold for fast filtering.
        """
        domain = context.get("domain")
        effectiveness_threshold = self.config.get("effectiveness_threshold", 0.50)

        # Build query
        domains = [domain] if domain else None
        candidates = self.db.find_patterns_by_context(
            domains=domains,
            min_success_rate=effectiveness_threshold
        )

        return candidates

    def _keyword_scoring(self, patterns: List[Dict], context: Dict) -> List[Dict]:
        """
        Score patterns using keyword matching (fallback method).

        Used when LLM is unavailable or in demo mode.
        """
        scored = []

        # Build context keywords
        context_text = " ".join([
            str(context.get("problem_statement", "")),
            str(context.get("solution_concept", "")),
            " ".join(context.get("key_challenges", [])),
            str(context.get("target_user", ""))
        ]).lower()

        context_words = set(context_text.split())

        for pattern in patterns:
            # Get pattern text
            pattern_text = " ".join([
                str(pattern.get("pattern_name", "")),
                str(pattern.get("solution_approach", "")),
                str(pattern.get("key_insight", ""))
            ]).lower()

            pattern_words = set(pattern_text.split())

            # Calculate overlap score
            overlap = len(context_words & pattern_words)
            total = len(context_words | pattern_words)

            relevance = overlap / total if total > 0 else 0

            # Get effectiveness
            effectiveness = pattern.get("effectiveness", {})
            effectiveness_score = effectiveness.get("success_rate", 0.5)

            # v4.4: Add momentum_lift_score if available
            momentum_lift = 0.5  # Neutral default
            if MOMENTUM_LIFT_AVAILABLE and _lift_scorer:
                momentum_lift = _lift_scorer.score_insight(
                    insight_category=pattern.get("pattern_category", ""),
                    pursuit_stage=context.get("stage", "unknown"),
                    artifact_type=context.get("artifact_type", "unknown"),
                    momentum_tier=context.get("momentum_tier", "MEDIUM"),
                )

            scored.append({
                "pattern_id": pattern["pattern_id"],
                "pattern_name": pattern.get("pattern_name", "Unknown Pattern"),
                "relevance_score": round(relevance, 3),
                "effectiveness_score": effectiveness_score,
                "momentum_lift_score": momentum_lift,  # v4.4
                "similar_pursuits": effectiveness.get("total_applications", 0),
                "outcome_distribution": {
                    "success": effectiveness.get("success_count", 0),
                    "pivot": effectiveness.get("pivot_count", 0),
                    "fail": effectiveness.get("fail_count", 0)
                },
                "key_insight": pattern.get("key_insight", ""),
                "suggested_action": self._generate_action_suggestion(pattern, context)
            })

        # v4.4: Sort by weighted combination of relevance * effectiveness + momentum_lift
        # Existing factors get (1 - MOMENTUM_LIFT_WEIGHT) = 80%, momentum_lift gets 20%
        def compute_final_score(p):
            base_score = p["relevance_score"] * p["effectiveness_score"]
            lift_score = p.get("momentum_lift_score", 0.5)
            return (1 - MOMENTUM_LIFT_WEIGHT) * base_score + MOMENTUM_LIFT_WEIGHT * lift_score

        scored.sort(
            key=compute_final_score,
            reverse=True
        )

        return scored

    def _semantic_scoring(self, patterns: List[Dict], context: Dict) -> List[Dict]:
        """
        Score patterns using LLM semantic matching.

        More accurate but slower than keyword matching.
        """
        # Build patterns JSON for prompt
        patterns_for_prompt = []
        for p in patterns[:10]:  # Limit to 10 for token efficiency
            patterns_for_prompt.append({
                "pattern_id": p["pattern_id"],
                "pattern_name": p.get("pattern_name", ""),
                "problem_context": p.get("problem_context", {}),
                "solution_approach": p.get("solution_approach", ""),
                "key_insight": p.get("key_insight", ""),
                "success_rate": p.get("effectiveness", {}).get("success_rate", 0)
            })

        prompt = PATTERN_MATCHING_PROMPT.format(
            problem_statement=context.get("problem_statement", ""),
            solution_concept=context.get("solution_concept", ""),
            domain=context.get("domain", ""),
            stage=context.get("stage", ""),
            key_challenges=", ".join(context.get("key_challenges", [])),
            patterns_json=json.dumps(patterns_for_prompt, indent=2)
        )

        try:
            response = self.llm.call_llm(
                prompt=prompt,
                max_tokens=800,
                system="You are a pattern matcher. Respond only with valid JSON."
            )

            # Parse response
            result = self._parse_json_response(response)
            relevant = result.get("relevant_patterns", [])

            # Merge with pattern data
            scored = []
            pattern_map = {p["pattern_id"]: p for p in patterns}

            for match in relevant:
                pattern_id = match.get("pattern_id")
                if pattern_id in pattern_map:
                    pattern = pattern_map[pattern_id]
                    effectiveness = pattern.get("effectiveness", {})

                    scored.append({
                        "pattern_id": pattern_id,
                        "pattern_name": pattern.get("pattern_name", ""),
                        "relevance_score": match.get("relevance_score", 0.5),
                        "relevance_reason": match.get("relevance_reason", ""),
                        "effectiveness_score": effectiveness.get("success_rate", 0.5),
                        "similar_pursuits": effectiveness.get("total_applications", 0),
                        "outcome_distribution": {
                            "success": effectiveness.get("success_count", 0),
                            "pivot": effectiveness.get("pivot_count", 0),
                            "fail": effectiveness.get("fail_count", 0)
                        },
                        "key_insight": pattern.get("key_insight", ""),
                        "suggested_action": match.get("suggested_application", "")
                    })

            return scored

        except Exception as e:
            print(f"[PatternEngine] Semantic scoring failed: {e}")
            # Fall back to keyword scoring
            return self._keyword_scoring(patterns, context)

    def _generate_action_suggestion(self, pattern: Dict, context: Dict) -> str:
        """Generate action suggestion based on pattern and context."""
        stage = context.get("stage", "vision")
        approach = pattern.get("solution_approach", "")

        if stage == "vision":
            return f"Consider: {approach[:100]}..."
        elif stage == "fear":
            return f"Others who faced similar concerns found: {approach[:100]}..."
        else:
            return f"A proven approach: {approach[:100]}..."

    def detect_cross_pursuit_insights(self, user_id: str,
                                       current_pursuit_id: str) -> List[Dict]:
        """
        Find connections between user's own pursuits.

        Examples:
        - "Your CloudOps pursuit has similar assumptions to SmartMirror"
        - "You resolved timing concerns in SmartMirror, consider similar approach here"
        - "Three of your pursuits share capability fears around compliance"

        Args:
            user_id: User ID
            current_pursuit_id: Current pursuit ID

        Returns:
            List of insight dicts
        """
        if not self.config.get("enable_cross_pursuit_insights", True):
            return []

        print(f"[PatternEngine] Detecting cross-pursuit insights for user: {user_id}")

        # Get user's other pursuits
        all_pursuits = self.db.get_user_pursuits(user_id)
        other_pursuits = [
            p for p in all_pursuits
            if p["pursuit_id"] != current_pursuit_id
        ]

        if not other_pursuits:
            return []

        # Get current pursuit context
        current_state = self.db.get_scaffolding_state(current_pursuit_id)
        if not current_state:
            return []

        # Look for similar elements across pursuits
        insights = []

        # Get current pursuit elements
        current_elements = self._extract_key_elements(current_state)

        # Compare with other pursuits
        window_days = self.config.get("cross_pursuit_window_days", 180)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=window_days)

        for pursuit in other_pursuits:
            # Skip old pursuits
            created_at = pursuit.get("created_at")
            if isinstance(created_at, datetime):
                # Ensure timezone-aware for comparison
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                if created_at < cutoff_date:
                    continue

            other_state = self.db.get_scaffolding_state(pursuit["pursuit_id"])
            if not other_state:
                continue

            other_elements = self._extract_key_elements(other_state)

            # Find similarities
            similar_fears = self._find_similar_elements(
                current_elements.get("fears", {}),
                other_elements.get("fears", {})
            )

            similar_assumptions = self._find_similar_elements(
                current_elements.get("assumptions", {}),
                other_elements.get("assumptions", {})
            )

            if similar_fears:
                insights.append({
                    "insight_type": "shared_fear",
                    "related_pursuit_id": pursuit["pursuit_id"],
                    "related_pursuit_title": pursuit.get("title", ""),
                    "insight": f"Similar concern about {similar_fears[0]} as in {pursuit.get('title', 'another pursuit')}",
                    "suggested_action": "Review how you approached this concern previously",
                    "confidence": 0.75
                })

            if similar_assumptions:
                insights.append({
                    "insight_type": "similar_assumption",
                    "related_pursuit_id": pursuit["pursuit_id"],
                    "related_pursuit_title": pursuit.get("title", ""),
                    "insight": f"Related assumption to {pursuit.get('title', 'another pursuit')}",
                    "suggested_action": "Consider learnings from your previous validation",
                    "confidence": 0.70
                })

        # Limit insights
        return insights[:3]

    def _extract_key_elements(self, state: Dict) -> Dict:
        """Extract key elements for comparison."""
        fears = state.get("fear_elements", {}) or {}
        hypothesis = state.get("hypothesis_elements", {}) or {}

        # Safely get assumption text
        assumption_elem = hypothesis.get("assumption_statement")
        assumption_text = ""
        if assumption_elem and isinstance(assumption_elem, dict):
            assumption_text = assumption_elem.get("text", "")

        return {
            "fears": {
                k: v.get("text", "") for k, v in fears.items()
                if v and isinstance(v, dict) and v.get("text")
            },
            "assumptions": {
                "assumption": assumption_text
            }
        }

    def _find_similar_elements(self, elements1: Dict, elements2: Dict) -> List[str]:
        """Find similar elements between two sets using keyword overlap."""
        similar = []

        for name1, text1 in elements1.items():
            if not text1:
                continue
            words1 = set(text1.lower().split())

            for name2, text2 in elements2.items():
                if not text2:
                    continue
                words2 = set(text2.lower().split())

                # Calculate similarity
                overlap = len(words1 & words2)
                if overlap >= 3:  # At least 3 words in common
                    similar.append(name1)
                    break

        return similar

    def extract_proto_pattern(self, pursuit_id: str) -> Optional[Dict]:
        """
        Extract learnable pattern from completed pursuit.
        Called when pursuit reaches terminal state (success/fail/pivot).

        Creates "proto-pattern" that becomes full pattern after validation.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            Created pattern dict or None
        """
        print(f"[PatternEngine] Extracting proto-pattern from pursuit: {pursuit_id}")

        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return None

        state = self.db.get_scaffolding_state(pursuit_id)
        if not state:
            return None

        # Get pursuit details
        vision = state.get("vision_elements", {})
        hypothesis = state.get("hypothesis_elements", {})

        # Build extraction context
        context = {
            "title": pursuit.get("title", ""),
            "problem_statement": vision.get("problem_statement", {}).get("text", ""),
            "solution_concept": vision.get("solution_concept", {}).get("text", ""),
            "domain": self._infer_domain_from_state(state),
            "outcome": pursuit.get("status", "completed"),
            "learnings": hypothesis.get("learning_plan", {}).get("text", ""),
            "timeline": pursuit.get("updated_at", datetime.now(timezone.utc))
        }

        # Use LLM to extract pattern (or fallback)
        if not self.llm.demo_mode:
            pattern_data = self._llm_extract_pattern(context)
        else:
            pattern_data = self._basic_extract_pattern(context)

        if not pattern_data:
            return None

        # Create proto-pattern in database
        pattern = self.db.create_v25_pattern(
            pattern_name=pattern_data.get("pattern_name", f"Pattern from {pursuit.get('title', 'Unknown')}"),
            problem_context=pattern_data.get("problem_context", {
                "domain": [context["domain"]],
                "problem_type": [],
                "innovation_stage": ["vision"]
            }),
            solution_approach=pattern_data.get("solution_approach", context["solution_concept"]),
            key_insight=pattern_data.get("key_insight", ""),
            source_pursuits=[pursuit_id],
            pattern_type="proto-pattern"
        )

        print(f"[PatternEngine] Created proto-pattern: {pattern['pattern_id']}")
        return pattern

    def _llm_extract_pattern(self, context: Dict) -> Optional[Dict]:
        """Use LLM to extract pattern from pursuit context."""
        prompt = PROTO_PATTERN_EXTRACTION_PROMPT.format(
            title=context.get("title", ""),
            problem_statement=context.get("problem_statement", ""),
            solution_concept=context.get("solution_concept", ""),
            domain=context.get("domain", ""),
            outcome=context.get("outcome", ""),
            learnings=context.get("learnings", ""),
            timeline=str(context.get("timeline", ""))
        )

        try:
            response = self.llm.call_llm(
                prompt=prompt,
                max_tokens=600,
                system="You are a pattern extractor. Respond only with valid JSON."
            )

            return self._parse_json_response(response)

        except Exception as e:
            print(f"[PatternEngine] LLM pattern extraction failed: {e}")
            return None

    def _basic_extract_pattern(self, context: Dict) -> Dict:
        """Basic pattern extraction without LLM."""
        return {
            "pattern_name": f"Approach from {context.get('title', 'Unknown')}",
            "problem_context": {
                "domain": [context.get("domain", "other")],
                "problem_type": [],
                "innovation_stage": ["vision"]
            },
            "solution_approach": context.get("solution_concept", ""),
            "key_insight": context.get("learnings", "Pattern extracted from completed pursuit"),
            "success_factors": [],
            "failure_risks": [],
            "applicability_score": 0.5
        }

    def _infer_domain_from_state(self, state: Dict) -> str:
        """Infer domain from scaffolding state."""
        # Combine all text
        all_text = ""
        for field in ["vision_elements", "fear_elements"]:
            elements = state.get(field, {})
            for elem in elements.values():
                if elem and isinstance(elem, dict) and elem.get("text"):
                    all_text += " " + elem["text"]

        all_text = all_text.lower()

        # Domain keywords
        domains = {
            "healthcare": ["health", "medical", "patient"],
            "consumer": ["consumer", "user", "app"],
            "enterprise": ["enterprise", "business", "b2b"],
            "fintech": ["financial", "payment", "bank"],
            "education": ["education", "learning", "student"]
        }

        for domain, keywords in domains.items():
            if any(kw in all_text for kw in keywords):
                return domain

        return "other"

    def update_pattern_effectiveness(self, pattern_id: str, outcome: str) -> bool:
        """
        Update pattern success rate based on pursuit outcomes.
        Tracks: success_count, pivot_count, fail_count, contexts_applied

        Args:
            pattern_id: Pattern ID
            outcome: "success" | "pivot" | "fail"

        Returns:
            True if update succeeded
        """
        result = self.db.update_pattern_effectiveness(pattern_id, outcome)

        # Check if pattern should be promoted
        pattern = self.db.get_pattern(pattern_id)
        if pattern:
            effectiveness = pattern.get("effectiveness", {})
            total = effectiveness.get("total_applications", 0)
            success_rate = effectiveness.get("success_rate", 0)
            pattern_type = pattern.get("pattern_type", "proto-pattern")

            promotion_threshold = self.config.get("proto_pattern_promotion_threshold", 3)

            if (pattern_type == "proto-pattern" and
                total >= promotion_threshold and
                success_rate >= 0.5):
                self.db.promote_pattern_to_validated(pattern_id)
                print(f"[PatternEngine] Promoted pattern {pattern_id} to validated")

        return result

    def match_patterns_to_elements(self, elements: Dict) -> Dict:
        """
        Map tracked elements to relevant historical patterns.

        Returns element-specific pattern suggestions:
        {
            "target_user": [pattern_ids],
            "value_proposition": [pattern_ids],
            "capability_fears": [pattern_ids]
        }
        """
        # Simplified implementation - would be enhanced with embeddings
        element_patterns = {}

        # Get all patterns
        all_patterns = self.db.find_patterns_by_context(min_success_rate=0.5)

        for element_name, element_text in elements.items():
            if not element_text:
                continue

            matching = []
            words = set(element_text.lower().split())

            for pattern in all_patterns:
                insight = pattern.get("key_insight", "").lower()
                insight_words = set(insight.split())

                if len(words & insight_words) >= 2:
                    matching.append(pattern["pattern_id"])

            if matching:
                element_patterns[element_name] = matching[:3]

        return element_patterns

    # =========================================================================
    # Cache Management
    # =========================================================================

    def _get_from_cache(self, key: str) -> Optional[List]:
        """Get cached pattern results if not expired."""
        if key not in self._pattern_cache:
            return None

        cached_time, results = self._pattern_cache[key]
        age = (datetime.now(timezone.utc) - cached_time).total_seconds()

        if age < self._cache_ttl:
            return results

        # Expired
        del self._pattern_cache[key]
        return None

    def _add_to_cache(self, key: str, results: List) -> None:
        """Add pattern results to cache."""
        self._pattern_cache[key] = (datetime.now(timezone.utc), results)

        # Clean old entries (simple cleanup)
        if len(self._pattern_cache) > 100:
            oldest_key = min(
                self._pattern_cache.keys(),
                key=lambda k: self._pattern_cache[k][0]
            )
            del self._pattern_cache[oldest_key]

    def clear_cache(self) -> None:
        """Clear pattern cache."""
        self._pattern_cache = {}

    # =========================================================================
    # Utilities
    # =========================================================================

    def _parse_json_response(self, response: str) -> Dict:
        """Parse JSON from LLM response, handling markdown wrapping."""
        import re

        text = response.strip()

        # Remove markdown code blocks
        if text.startswith("```"):
            text = re.sub(r"```json?\s*", "", text)
            text = re.sub(r"```\s*$", "", text)

        return json.loads(text)

    def get_pattern_suggestions_natural(self, patterns: List[Dict]) -> str:
        """
        Generate natural language suggestion from pattern results.

        Used by LLM to phrase pattern insights conversationally.
        """
        if not patterns:
            return ""

        if len(patterns) == 1:
            p = patterns[0]
            return (
                f"I've noticed a similar situation before - {p['key_insight']} "
                f"{p.get('suggested_action', '')}"
            )
        else:
            insights = [p['key_insight'][:50] for p in patterns[:2]]
            return (
                f"This reminds me of patterns we've seen: {insights[0]}... "
                f"and {insights[1]}..."
            )

    # =========================================================================
    # v2.6: Stakeholder Engagement Pattern Methods
    # =========================================================================

    def extract_stakeholder_engagement_pattern(self, pursuit_id: str,
                                               outcome: str = None) -> Optional[Dict]:
        """
        v2.6: Extract stakeholder engagement pattern from pursuit.

        Learns from:
        - Stakeholder count and distribution
        - Timeline from first engagement to outcome
        - Common concerns and resolutions
        - Champion/blocker patterns

        Args:
            pursuit_id: Pursuit ID
            outcome: Optional pursuit outcome

        Returns:
            Stakeholder pattern dict or None
        """
        print(f"[PatternEngine] Extracting stakeholder pattern for: {pursuit_id}")

        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return None

        # Get stakeholder feedback
        feedback_list = self.db.get_stakeholder_feedback_by_pursuit(pursuit_id)
        if not feedback_list:
            return None

        # Calculate engagement metrics
        total_stakeholders = len(feedback_list)
        support_levels = [f.get("support_level", "unclear") for f in feedback_list]

        supportive = sum(1 for s in support_levels if s == "supportive")
        conditional = sum(1 for s in support_levels if s == "conditional")
        opposed = sum(1 for s in support_levels if s == "opposed")

        support_rate = (supportive + conditional) / total_stakeholders if total_stakeholders > 0 else 0

        # Extract common concerns
        all_concerns = []
        for f in feedback_list:
            concerns = f.get("concerns", [])
            if isinstance(concerns, list):
                all_concerns.extend(concerns)

        # Count concern frequencies
        concern_counts = {}
        for concern in all_concerns:
            normalized = concern.lower().strip()
            concern_counts[normalized] = concern_counts.get(normalized, 0) + 1

        top_concerns = sorted(concern_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # Build pattern
        pattern_data = {
            "pattern_type": "stakeholder_engagement",
            "pursuit_id": pursuit_id,
            "pursuit_domain": self._infer_domain_from_state(
                self.db.get_scaffolding_state(pursuit_id) or {}
            ),
            "metrics": {
                "total_stakeholders": total_stakeholders,
                "support_rate": support_rate,
                "supportive_count": supportive,
                "conditional_count": conditional,
                "opposed_count": opposed
            },
            "top_concerns": [c[0] for c in top_concerns],
            "concern_frequencies": dict(top_concerns),
            "outcome": outcome or pursuit.get("status", "unknown"),
            "timestamp": datetime.now(timezone.utc)
        }

        # Store pattern
        try:
            self.db.db.patterns.insert_one(pattern_data)
            print(f"[PatternEngine] Saved stakeholder pattern: {pattern_data}")
        except Exception as e:
            print(f"[PatternEngine] Failed to save stakeholder pattern: {e}")

        return pattern_data

    def find_similar_engagement_patterns(self, pursuit_id: str) -> List[Dict]:
        """
        v2.6: Find similar stakeholder engagement patterns.

        Args:
            pursuit_id: Current pursuit ID

        Returns:
            List of similar pursuit patterns
        """
        # Get current pursuit context
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return []

        state = self.db.get_scaffolding_state(pursuit_id)
        domain = self._infer_domain_from_state(state) if state else "other"

        # Find patterns from same domain
        try:
            patterns = list(self.db.db.patterns.find({
                "pattern_type": "stakeholder_engagement",
                "pursuit_domain": domain,
                "pursuit_id": {"$ne": pursuit_id}  # Exclude current
            }).limit(10))

            # Sort by support rate similarity
            current_feedback = self.db.get_stakeholder_feedback_by_pursuit(pursuit_id)
            current_count = len(current_feedback)

            if current_count > 0:
                current_support = sum(
                    1 for f in current_feedback
                    if f.get("support_level") in ["supportive", "conditional"]
                ) / current_count
            else:
                current_support = 0.5  # Default

            # Score by similarity
            for p in patterns:
                p_metrics = p.get("metrics", {})
                p_support = p_metrics.get("support_rate", 0.5)
                p["similarity_score"] = 1 - abs(current_support - p_support)

            # Sort by similarity
            patterns.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)

            return patterns[:5]

        except Exception as e:
            print(f"[PatternEngine] Failed to find engagement patterns: {e}")
            return []

    def get_engagement_benchmarks(self, pursuit_id: str) -> Dict:
        """
        v2.6: Get stakeholder engagement benchmarks from similar pursuits.

        Args:
            pursuit_id: Current pursuit ID

        Returns:
            Benchmark metrics
        """
        similar = self.find_similar_engagement_patterns(pursuit_id)

        if not similar:
            return {
                "available": False,
                "message": "No similar pursuits found for benchmarking"
            }

        # Calculate averages
        avg_stakeholders = sum(
            p.get("metrics", {}).get("total_stakeholders", 0)
            for p in similar
        ) / len(similar)

        avg_support = sum(
            p.get("metrics", {}).get("support_rate", 0)
            for p in similar
        ) / len(similar)

        # Get successful patterns
        successful = [p for p in similar if p.get("outcome") == "success"]
        success_avg_support = 0
        if successful:
            success_avg_support = sum(
                p.get("metrics", {}).get("support_rate", 0)
                for p in successful
            ) / len(successful)

        # Aggregate common concerns
        all_concerns = []
        for p in similar:
            all_concerns.extend(p.get("top_concerns", []))

        # Count concern frequencies
        concern_counts = {}
        for c in all_concerns:
            concern_counts[c] = concern_counts.get(c, 0) + 1

        common_concerns = sorted(concern_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "available": True,
            "sample_size": len(similar),
            "avg_stakeholders": round(avg_stakeholders, 1),
            "avg_support_rate": round(avg_support * 100),
            "success_avg_support_rate": round(success_avg_support * 100) if successful else None,
            "common_concerns_across_pursuits": [c[0] for c in common_concerns],
            "recommendation": self._generate_engagement_recommendation(
                avg_support, success_avg_support, common_concerns
            )
        }

    def _generate_engagement_recommendation(self, avg_support: float,
                                            success_avg: float,
                                            concerns: List) -> str:
        """Generate engagement recommendation based on benchmarks."""
        if success_avg and success_avg > avg_support:
            target_pct = int(success_avg * 100)
            return f"Successful similar pursuits averaged {target_pct}% support. Focus on addressing key concerns to reach this threshold."

        if concerns:
            top_concern = concerns[0][0] if concerns else "stakeholder alignment"
            return f"Common concern across similar pursuits: '{top_concern}'. Consider proactively addressing this."

        return "Engage stakeholders early and address concerns promptly for best outcomes."

    def learn_from_stakeholder_outcome(self, pursuit_id: str, outcome: str) -> None:
        """
        v2.6: Record stakeholder engagement outcome for pattern learning.

        Called when pursuit reaches terminal state.

        Args:
            pursuit_id: Pursuit ID
            outcome: success/fail/pivot
        """
        # Extract and save the pattern
        pattern = self.extract_stakeholder_engagement_pattern(pursuit_id, outcome)

        if pattern:
            print(f"[PatternEngine] Learned stakeholder pattern from {pursuit_id}: {outcome}")

            # Update effectiveness tracking
            summary = self.db.get_pursuit_stakeholder_summary(pursuit_id)
            if summary:
                # Record correlation between support level and outcome
                support_pct = summary.get("support_percentage", 0)

                # Store effectiveness data
                try:
                    self.db.db.pattern_effectiveness.insert_one({
                        "type": "stakeholder_engagement",
                        "pursuit_id": pursuit_id,
                        "support_percentage": support_pct,
                        "outcome": outcome,
                        "timestamp": datetime.now(timezone.utc)
                    })
                except Exception:
                    pass
