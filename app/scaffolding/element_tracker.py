"""
InDE MVP v2.5 - Element Tracker

Tracks 48 scaffolding elements across 3 tiers:
- Critical (20): Core vision, fears, hypothesis elements
- Important (20): v2.5 Enhanced elements for richer pattern matching
- Teleological (8): Goal-oriented dimensions for methodology inference

v2.5 Enhancements:
- Tracks new V25_IMPORTANT_ELEMENTS for pattern matching
- Provides context extraction for pattern engine
- Supports tiered extraction (critical first, then important)
- Tracks extraction method and update history

Elements are extracted invisibly as the user talks - they never see
progress bars, checklists, or methodology terminology.
"""

import json
import re
from typing import Dict, List, Optional
from datetime import datetime, timezone

from config import (
    CRITICAL_ELEMENTS, ELEMENT_EXTRACTION_PROMPT,
    IMPORTANT_ELEMENTS, TELEOLOGICAL_DIMENSIONS, TELEOLOGICAL_INDICATORS,
    V25_IMPORTANT_ELEMENTS, ELEMENT_TRACKING_CONFIG
)


class ElementTracker:
    """
    Tracks critical information elements from conversation.
    Elements are extracted invisibly as user talks.
    """

    def __init__(self, llm_interface, database):
        """
        Initialize ElementTracker.

        Args:
            llm_interface: LLMInterface instance for Claude API calls
            database: Database instance for persistence
        """
        self.llm = llm_interface
        self.db = database

    def extract_elements(self, conversation_turn: str, pursuit_id: str) -> Dict:
        """
        Extract any critical elements from this conversation turn.

        Args:
            conversation_turn: The user's message text
            pursuit_id: ID of the current pursuit

        Returns:
            {
                "vision": {"problem_statement": {"text": "...", "confidence": 0.8}, ...},
                "fears": {"capability_fears": {"text": "...", "confidence": 0.7}, ...},
                "hypothesis": {"assumption_statement": {"text": "...", "confidence": 0.9}, ...},
                "extracted_count": int
            }
        """
        print(f"[ElementTracker] Extracting elements from: {conversation_turn[:50]}...")
        print(f"[ElementTracker] Pursuit ID: {pursuit_id}")

        # Get current pursuit context
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            print(f"[ElementTracker] No pursuit found for ID: {pursuit_id}")
            return {"vision": {}, "fears": {}, "hypothesis": {}, "extracted_count": 0}

        print(f"[ElementTracker] Found pursuit: {pursuit.get('title')}")

        # Get existing elements to provide context
        existing = self._get_existing_elements_summary(pursuit_id)
        print(f"[ElementTracker] Existing elements: {existing}")

        # Use LLM to extract new elements
        try:
            extracted = self._llm_extract_elements(
                conversation_turn,
                pursuit.get("title", "Unknown"),
                existing
            )
            print(f"[ElementTracker] LLM extracted: {extracted}")
        except Exception as e:
            print(f"[ElementTracker] LLM extraction failed: {e}")
            extracted = {"vision": {}, "fears": {}, "hypothesis": {}}

        # Update database with extracted elements
        if extracted:
            has_elements = any(v for v in extracted.values() if v)
            if has_elements:
                result = self.db.update_scaffolding_elements_batch(pursuit_id, extracted)
                print(f"[ElementTracker] Database update result: {result}")

                # Verify update by reading back
                completeness = self.get_completeness(pursuit_id)
                print(f"[ElementTracker] Completeness after update: {completeness}")

        # Count total extracted
        extracted_count = sum(
            len(elements) for elements in extracted.values() if elements
        )
        extracted["extracted_count"] = extracted_count

        if extracted_count > 0:
            print(f"[ElementTracker] Extracted {extracted_count} elements from turn")
        else:
            print(f"[ElementTracker] No elements extracted from this turn")

        return extracted

    def get_completeness(self, pursuit_id: str) -> Dict[str, float]:
        """
        Calculate completeness for each artifact type.

        Returns:
            {
                "vision": 0.625,      # 5/8 elements present
                "fears": 0.5,         # 3/6 elements present
                "hypothesis": 0.333,  # 2/6 elements present
                "overall": 0.476      # 10/20 elements present
            }
        """
        return self.db.get_element_completeness(pursuit_id)

    def get_missing_critical(self, pursuit_id: str, artifact_type: str) -> List[str]:
        """
        Get list of missing critical elements for an artifact type.
        Used by MomentDetector to decide interventions.
        """
        return self.db.get_missing_elements(pursuit_id, artifact_type)

    def get_present_elements(self, pursuit_id: str, artifact_type: str) -> Dict[str, str]:
        """
        Get dict of present elements with their text.
        Used by ArtifactGenerator when generating artifacts.
        """
        return self.db.get_present_elements(pursuit_id, artifact_type)

    def get_most_critical_gap(self, pursuit_id: str) -> Optional[Dict]:
        """
        Get the most critical missing element across all artifact types.

        Returns:
            {
                "artifact_type": "vision",
                "element": "target_user",
                "suggestion": "I notice we haven't discussed who would use this..."
            }
            or None if all critical elements are present
        """
        # Priority order: vision first (foundation), then fears, then hypothesis
        priority_order = ["vision", "fears", "hypothesis"]

        # Critical elements that should be asked about first
        critical_first = {
            "vision": ["problem_statement", "target_user", "solution_concept"],
            "fears": ["capability_fears", "market_fears"],
            "hypothesis": ["assumption_statement", "testable_prediction"]
        }

        for artifact_type in priority_order:
            missing = self.get_missing_critical(pursuit_id, artifact_type)
            if not missing:
                continue

            # Check if any critical-first elements are missing
            for element in critical_first.get(artifact_type, []):
                if element in missing:
                    return {
                        "artifact_type": artifact_type,
                        "element": element,
                        "suggestion": self._get_gap_suggestion(artifact_type, element)
                    }

            # Otherwise return first missing element
            return {
                "artifact_type": artifact_type,
                "element": missing[0],
                "suggestion": self._get_gap_suggestion(artifact_type, missing[0])
            }

        return None

    def _get_existing_elements_summary(self, pursuit_id: str) -> str:
        """Get a summary of existing elements for context."""
        state = self.db.get_scaffolding_state(pursuit_id)
        if not state:
            return "No elements captured yet."

        summary_parts = []

        for element_type, field in [
            ("Vision", "vision_elements"),
            ("Fears", "fear_elements"),
            ("Hypothesis", "hypothesis_elements")
        ]:
            elements = state.get(field, {})
            present = [k for k, v in elements.items() if v and v.get("text")]
            if present:
                summary_parts.append(f"{element_type}: {', '.join(present)}")

        return "; ".join(summary_parts) if summary_parts else "No elements captured yet."

    def _llm_extract_elements(self, conversation_turn: str,
                              pursuit_title: str, existing_elements: str) -> Dict:
        """Use LLM to extract elements from the conversation turn."""
        prompt = ELEMENT_EXTRACTION_PROMPT.format(
            pursuit_title=pursuit_title,
            existing_elements=existing_elements,
            conversation_turn=conversation_turn
        )

        response = self.llm.call_llm(
            prompt=prompt,
            max_tokens=500,
            system="You are an element extractor. Respond only with valid JSON."
        )

        # Parse JSON response
        try:
            # Clean response - extract JSON if wrapped in markdown
            json_text = response.strip()
            if json_text.startswith("```"):
                json_text = re.sub(r"```json?\s*", "", json_text)
                json_text = re.sub(r"```\s*$", "", json_text)

            result = json.loads(json_text)

            # Validate structure
            extracted = {
                "vision": {},
                "fears": {},
                "hypothesis": {}
            }

            for element_type in ["vision", "fears", "hypothesis"]:
                if element_type in result and isinstance(result[element_type], dict):
                    # Validate each element
                    valid_elements = CRITICAL_ELEMENTS.get(element_type, [])
                    for elem_name, elem_data in result[element_type].items():
                        if elem_name in valid_elements and isinstance(elem_data, dict):
                            if elem_data.get("text") and elem_data.get("confidence", 0) > 0.5:
                                extracted[element_type][elem_name] = elem_data

            return extracted

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"[ElementTracker] Failed to parse LLM response: {e}")
            return {"vision": {}, "fears": {}, "hypothesis": {}}

    def _get_gap_suggestion(self, artifact_type: str, element: str) -> str:
        """Get a natural suggestion for filling a gap."""
        suggestions = {
            # Vision elements
            ("vision", "problem_statement"): "I'm curious - what's the core problem you're trying to solve?",
            ("vision", "target_user"): "Who do you see as the main users or customers for this?",
            ("vision", "current_situation"): "How do people handle this problem today?",
            ("vision", "pain_points"): "What's most painful about the current situation?",
            ("vision", "solution_concept"): "What's your idea for solving this?",
            ("vision", "value_proposition"): "Why would someone choose this over alternatives?",
            ("vision", "differentiation"): "What makes your approach unique?",
            ("vision", "success_criteria"): "How will you know if this is working?",

            # Fear elements
            ("fears", "capability_fears"): "What concerns do you have about being able to build this?",
            ("fears", "market_fears"): "Any worries about whether people will actually want this?",
            ("fears", "resource_fears"): "Do you have concerns about having the resources you need?",
            ("fears", "timing_fears"): "How do you feel about the timing - too early, too late, or just right?",
            ("fears", "competition_fears"): "What about competitors - anyone else working on this?",
            ("fears", "personal_fears"): "What worries you most personally about pursuing this?",

            # Hypothesis elements
            ("hypothesis", "assumption_statement"): "What's the key assumption you're making here?",
            ("hypothesis", "testable_prediction"): "What do you predict will happen if your assumption is right?",
            ("hypothesis", "test_method"): "How could you test this assumption?",
            ("hypothesis", "success_metric"): "What metric would tell you this is working?",
            ("hypothesis", "failure_criteria"): "At what point would you consider this approach failed?",
            ("hypothesis", "learning_plan"): "What will you do with what you learn from testing?",
        }

        return suggestions.get(
            (artifact_type, element),
            f"Tell me more about the {element.replace('_', ' ')}."
        )

    # =========================================================================
    # v2.3: TELEOLOGICAL ELEMENT EXTRACTION
    # =========================================================================

    def extract_teleological_profile(self, pursuit_id: str,
                                      conversation_history: List[Dict] = None) -> Dict:
        """
        Extract teleological dimensions from conversation using keyword matching.

        Teleological dimensions help determine coaching style without exposing
        methodology terminology to the user.

        Args:
            pursuit_id: The pursuit ID
            conversation_history: Optional conversation history (last 10 turns used)

        Returns:
            {
                "purpose_type": "problem_solving",
                "beneficiary": "end_users",
                "uncertainty_level": 0.7,
                "value_creation_mode": "safety",
                "resource_context": "time_constrained",
                "org_context": "startup",
                "innovation_type": "architectural",
                "maturity_state": "hypothesis",
                "confidence": 0.75,
                "last_assessed": timestamp
            }
        """
        print(f"[ElementTracker] Extracting teleological profile for pursuit: {pursuit_id}")

        # Get conversation history if not provided
        if conversation_history is None:
            conversation_history = self.db.get_conversation_history(pursuit_id, limit=10)

        # Combine recent conversation into full text
        if not conversation_history:
            return self._empty_teleological_profile()

        recent_conv = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        full_text = " ".join([
            msg.get("content", "") for msg in recent_conv
            if msg.get("role") == "user"  # Focus on user messages
        ]).lower()

        if not full_text.strip():
            return self._empty_teleological_profile()

        # Keyword-based detection for each dimension
        profile = {}
        dimension_confidences = []

        for dimension in TELEOLOGICAL_DIMENSIONS:
            if dimension == "uncertainty_level":
                # Special handling: calculate based on language patterns
                profile[dimension] = self._estimate_uncertainty_level(full_text)
                dimension_confidences.append(0.6)  # Moderate confidence for estimation
            elif dimension in TELEOLOGICAL_INDICATORS:
                indicator_map = TELEOLOGICAL_INDICATORS[dimension]
                scores = {}

                for value, keywords in indicator_map.items():
                    count = sum(1 for kw in keywords if kw.lower() in full_text)
                    scores[value] = count

                # Pick highest score if any matches
                max_score = max(scores.values()) if scores else 0
                if max_score > 0:
                    profile[dimension] = max(scores, key=scores.get)
                    # Confidence based on how many matches
                    dimension_confidences.append(min(0.9, 0.5 + (max_score * 0.1)))
                else:
                    profile[dimension] = None
                    dimension_confidences.append(0.0)
            else:
                profile[dimension] = None
                dimension_confidences.append(0.0)

        # Calculate overall confidence
        valid_dims = sum(1 for v in profile.values() if v is not None)
        overall_confidence = valid_dims / len(TELEOLOGICAL_DIMENSIONS)

        profile["confidence"] = overall_confidence
        profile["last_assessed"] = datetime.now(timezone.utc)

        print(f"[ElementTracker] Teleological profile extracted: {profile}")
        return profile

    def _estimate_uncertainty_level(self, text: str) -> float:
        """
        Estimate uncertainty level from language patterns.
        Higher value = more uncertainty (exploratory stage).
        Lower value = more certainty (validation/scaling stage).

        Returns: 0.0-1.0 score
        """
        # High uncertainty indicators
        high_uncertainty = [
            "maybe", "might", "not sure", "wondering", "could be",
            "what if", "thinking about", "exploring", "don't know",
            "uncertain", "possibly", "perhaps", "just an idea"
        ]

        # Low uncertainty indicators
        low_uncertainty = [
            "know that", "proven", "tested", "data shows", "customers said",
            "definitely", "certain", "validated", "works", "confirmed",
            "evidence", "results show", "we've seen"
        ]

        high_count = sum(1 for phrase in high_uncertainty if phrase in text)
        low_count = sum(1 for phrase in low_uncertainty if phrase in text)

        # Base uncertainty is 0.5 (neutral)
        total = high_count + low_count
        if total == 0:
            return 0.5

        # Calculate ratio: more high = higher uncertainty
        uncertainty = 0.5 + (0.4 * (high_count - low_count) / max(total, 1))
        return max(0.1, min(0.9, uncertainty))  # Clamp to 0.1-0.9

    def _empty_teleological_profile(self) -> Dict:
        """Return empty teleological profile."""
        profile = {dim: None for dim in TELEOLOGICAL_DIMENSIONS}
        profile["confidence"] = 0.0
        profile["last_assessed"] = datetime.now(timezone.utc)
        return profile

    def get_teleological_profile(self, pursuit_id: str) -> Dict:
        """
        Get cached teleological profile from database or extract if stale.

        Returns cached profile if less than 5 minutes old, otherwise re-extracts.
        """
        state = self.db.get_scaffolding_state(pursuit_id)
        if state and state.get("teleological_profile"):
            profile = state.get("teleological_profile", {})
            last_assessed = profile.get("last_assessed")

            # Check if profile is recent enough (within 5 minutes)
            if last_assessed:
                if isinstance(last_assessed, datetime):
                    # Ensure timezone-aware for comparison
                    if last_assessed.tzinfo is None:
                        last_assessed = last_assessed.replace(tzinfo=timezone.utc)
                    age = (datetime.now(timezone.utc) - last_assessed).total_seconds()
                    if age < 300:  # 5 minutes
                        return profile

        # Extract fresh profile
        profile = self.extract_teleological_profile(pursuit_id)

        # Cache it in database
        self.db.update_teleological_profile(pursuit_id, profile)

        return profile

    def get_48_element_completeness(self, pursuit_id: str) -> Dict:
        """
        Calculate completeness across all 48 elements (v2.3 enhanced).

        Returns:
            {
                "critical": 0.50,      # 10/20 critical elements
                "important": 0.25,     # 5/20 important elements
                "teleological": 0.625, # 5/8 teleological dimensions
                "overall": 0.42,       # weighted average
                "vision": 0.625,       # (v2.2 backward compat)
                "fears": 0.5,
                "hypothesis": 0.333
            }
        """
        # Get v2.2 completeness (critical elements)
        critical_completeness = self.get_completeness(pursuit_id)

        # Get teleological profile completeness
        tele_profile = self.get_teleological_profile(pursuit_id)
        tele_completeness = tele_profile.get("confidence", 0.0)

        # Important elements completeness (simplified - based on critical + teleological)
        # In full implementation, would track important elements separately
        important_completeness = min(1.0, (critical_completeness.get("overall", 0) + tele_completeness) / 2)

        # Weighted overall (critical most important)
        overall = (
            critical_completeness.get("overall", 0) * 0.5 +  # 50% weight
            important_completeness * 0.3 +                    # 30% weight
            tele_completeness * 0.2                           # 20% weight
        )

        return {
            "critical": critical_completeness.get("overall", 0),
            "important": important_completeness,
            "teleological": tele_completeness,
            "overall": overall,
            # v2.2 backward compatibility
            "vision": critical_completeness.get("vision", 0),
            "fears": critical_completeness.get("fears", 0),
            "hypothesis": critical_completeness.get("hypothesis", 0)
        }

    # =========================================================================
    # v2.5: ADVANCED ELEMENT TRACKING FOR PATTERN MATCHING
    # =========================================================================

    def extract_important_elements(self, conversation_turn: str,
                                    pursuit_id: str) -> Dict:
        """
        v2.5: Extract important (non-critical) elements from conversation.

        These elements enhance pattern matching quality but are not required
        for artifact generation.

        Args:
            conversation_turn: The user's message text
            pursuit_id: ID of the current pursuit

        Returns:
            Dict of extracted important elements with confidence scores
        """
        if not ELEMENT_TRACKING_CONFIG.get("track_important_elements", True):
            return {}

        extracted = {}
        turn_lower = conversation_turn.lower()

        # Keyword-based extraction for important elements
        element_keywords = {
            "competitive_landscape": ["competitor", "competition", "others doing", "similar"],
            "business_model": ["revenue", "monetize", "business model", "make money"],
            "cost_structure": ["cost", "expensive", "budget", "price"],
            "go_to_market": ["launch", "marketing", "distribution", "reach users"],
            "partnerships": ["partner", "collaborate", "alliance", "work with"],
            "regulatory_concerns": ["regulation", "compliance", "legal", "law", "policy"],
            "technical_feasibility": ["build", "technical", "engineering", "develop"],
            "resource_requirements": ["need", "resources", "team", "hire"],
            "team_capabilities": ["skills", "expertise", "experience", "capable"],
            "market_timing": ["timing", "now", "ready", "early", "late"],
            "adoption_barriers": ["barrier", "adopt", "change", "switch"],
            "network_effects": ["network", "viral", "more users", "grows"],
            "scalability_constraints": ["scale", "growth", "limit", "constraint"],
            "stakeholder_alignment": ["stakeholder", "support", "buy-in", "approve"],
            "risk_tolerance": ["risk", "uncertainty", "bet", "gamble"]
        }

        confidence_threshold = ELEMENT_TRACKING_CONFIG.get(
            "confidence_threshold_important", 0.50
        )

        for element, keywords in element_keywords.items():
            matches = sum(1 for kw in keywords if kw in turn_lower)
            if matches > 0:
                confidence = min(0.9, 0.4 + (matches * 0.15))
                if confidence >= confidence_threshold:
                    # Extract relevant text snippet
                    text = self._extract_relevant_snippet(conversation_turn, keywords)
                    if text:
                        extracted[element] = {
                            "text": text,
                            "confidence": confidence,
                            "extraction_method": "keyword"
                        }
                        # Persist to database
                        self.db.update_important_element(
                            pursuit_id, element, text, confidence, "keyword"
                        )

        return extracted

    def _extract_relevant_snippet(self, text: str, keywords: List[str]) -> Optional[str]:
        """
        Extract a relevant snippet of text containing the keywords.

        Returns first sentence containing any keyword, up to 200 chars.
        """
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            if any(kw.lower() in sentence.lower() for kw in keywords):
                snippet = sentence.strip()
                if len(snippet) > 200:
                    snippet = snippet[:197] + "..."
                return snippet
        return None

    def get_pursuit_context_for_patterns(self, pursuit_id: str) -> Dict:
        """
        v2.5: Get comprehensive pursuit context for pattern matching.

        Returns context suitable for pattern engine queries.

        Args:
            pursuit_id: Pursuit ID

        Returns:
            {
                "problem_statement": str,
                "solution_concept": str,
                "domain": str (inferred),
                "stage": str,
                "key_challenges": [str],
                "target_user": str,
                "fears": [str]
            }
        """
        state = self.db.get_scaffolding_state(pursuit_id)
        if not state:
            return {}

        vision = state.get("vision_elements", {})
        fears = state.get("fear_elements", {})
        hypothesis = state.get("hypothesis_elements", {})
        tele = state.get("teleological_profile", {})

        # Build context
        context = {
            "problem_statement": self._get_text(vision.get("problem_statement")),
            "solution_concept": self._get_text(vision.get("solution_concept")),
            "target_user": self._get_text(vision.get("target_user")),
            "value_proposition": self._get_text(vision.get("value_proposition")),
            "domain": self._infer_domain(state),
            "stage": self._determine_stage(state),
            "key_challenges": self._extract_challenges(fears),
            "fears": [
                self._get_text(fears.get(f))
                for f in ["capability_fears", "market_fears", "resource_fears"]
                if self._get_text(fears.get(f))
            ],
            "assumptions": self._get_text(hypothesis.get("assumption_statement")),
            "maturity_state": tele.get("maturity_state", "spark"),
            "org_context": tele.get("org_context")
        }

        return context

    def _get_text(self, element: Optional[Dict]) -> Optional[str]:
        """Extract text from element dict safely."""
        if element and isinstance(element, dict):
            return element.get("text")
        return None

    def _infer_domain(self, state: Dict) -> str:
        """
        Infer domain from captured elements.

        Returns best guess domain from: healthcare, consumer, enterprise,
        fintech, education, other
        """
        # Combine all text for analysis
        all_text = ""
        for field in ["vision_elements", "fear_elements"]:
            elements = state.get(field, {})
            for elem in elements.values():
                if elem and elem.get("text"):
                    all_text += " " + elem["text"]

        all_text = all_text.lower()

        # Domain keywords
        domain_keywords = {
            "healthcare": ["health", "medical", "patient", "doctor", "hospital", "care"],
            "consumer": ["consumer", "user", "customer", "people", "everyday", "app"],
            "enterprise": ["enterprise", "business", "company", "b2b", "corporate"],
            "fintech": ["financial", "payment", "bank", "money", "invest", "finance"],
            "education": ["education", "learning", "student", "teach", "school", "course"],
            "safety": ["safety", "secure", "protect", "hazard", "danger", "warning"]
        }

        best_domain = "other"
        best_score = 0

        for domain, keywords in domain_keywords.items():
            score = sum(1 for kw in keywords if kw in all_text)
            if score > best_score:
                best_score = score
                best_domain = domain

        return best_domain

    def _determine_stage(self, state: Dict) -> str:
        """
        Determine current innovation stage from completeness.

        Returns: "vision" | "fear" | "hypothesis" | "execute"
        """
        completeness = self.db.get_element_completeness(state.get("pursuit_id", ""))

        if completeness.get("vision", 0) < 0.5:
            return "vision"
        elif completeness.get("fears", 0) < 0.5:
            return "fear"
        elif completeness.get("hypothesis", 0) < 0.5:
            return "hypothesis"
        else:
            return "execute"

    def _extract_challenges(self, fears: Dict) -> List[str]:
        """Extract key challenges from fear elements."""
        challenges = []
        for fear_name, fear_data in fears.items():
            text = self._get_text(fear_data)
            if text:
                # Simplify fear name for context
                challenge = fear_name.replace("_fears", "").replace("_", " ")
                challenges.append(f"{challenge}: {text[:100]}")
        return challenges[:5]  # Top 5 challenges

    def get_all_elements_flat(self, pursuit_id: str) -> Dict[str, str]:
        """
        v2.5: Get all tracked elements as a flat dict for pattern comparison.

        Returns dict with element names as keys and text as values.
        Includes both critical and important elements.
        """
        state = self.db.get_scaffolding_state(pursuit_id)
        if not state:
            return {}

        elements = {}

        # Critical elements
        for field in ["vision_elements", "fear_elements", "hypothesis_elements"]:
            field_elements = state.get(field, {})
            for name, data in field_elements.items():
                text = self._get_text(data)
                if text:
                    elements[name] = text

        # Important elements (v2.5)
        important = state.get("important_elements", {})
        for name, data in important.items():
            text = self._get_text(data)
            if text:
                elements[name] = text

        return elements

    def get_40_element_completeness(self, pursuit_id: str) -> Dict:
        """
        v2.5: Calculate completeness across all 40 elements (20 critical + 20 important).

        Returns:
            {
                "critical": 0.50,      # 10/20 critical elements
                "important": 0.25,     # 5/20 important elements
                "overall": 0.375,      # weighted average (critical 70%, important 30%)
                "vision": 0.625,       # backward compat
                "fears": 0.5,
                "hypothesis": 0.333,
                "critical_count": 10,
                "important_count": 5,
                "total_count": 15
            }
        """
        state = self.db.get_scaffolding_state(pursuit_id)
        if not state:
            return {
                "critical": 0.0, "important": 0.0, "overall": 0.0,
                "vision": 0.0, "fears": 0.0, "hypothesis": 0.0,
                "critical_count": 0, "important_count": 0, "total_count": 0
            }

        # Count critical elements
        critical_count = 0
        for field in ["vision_elements", "fear_elements", "hypothesis_elements"]:
            field_elements = state.get(field, {})
            critical_count += sum(
                1 for v in field_elements.values()
                if v and v.get("text")
            )

        critical_total = 20  # 8 + 6 + 6

        # Count important elements
        important_elements = state.get("important_elements", {})
        important_count = sum(
            1 for v in important_elements.values()
            if v and v.get("text")
        )
        important_total = len(V25_IMPORTANT_ELEMENTS)

        # Get critical breakdown
        critical_completeness = self.get_completeness(pursuit_id)

        # Calculate weighted overall (critical more important)
        critical_pct = critical_count / critical_total if critical_total > 0 else 0
        important_pct = important_count / important_total if important_total > 0 else 0
        overall = (critical_pct * 0.70) + (important_pct * 0.30)

        return {
            "critical": critical_pct,
            "important": important_pct,
            "overall": overall,
            "vision": critical_completeness.get("vision", 0),
            "fears": critical_completeness.get("fears", 0),
            "hypothesis": critical_completeness.get("hypothesis", 0),
            "critical_count": critical_count,
            "important_count": important_count,
            "total_count": critical_count + important_count
        }
