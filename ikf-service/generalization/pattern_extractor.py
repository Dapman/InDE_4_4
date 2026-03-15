"""
InDE v3.2 - Pattern Extractor
Stage 4 generalization: Extract actionable patterns from generalized data.

Produces patterns with:
- applicability_criteria: when this pattern is relevant
- success_indicators: what to look for
- risk_indicators: what to watch out for
- confidence_level: based on evidence strength
"""

import logging
import uuid
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger("inde.ikf.pattern_extractor")


class PatternExtractor:
    """
    Stage 4: Pattern Extraction.

    Extract actionable patterns from generalized data.
    Uses LLM for articulation and deduplication when available.
    """

    # Pattern type definitions
    PATTERN_TYPES = [
        "SUCCESS_PATTERN",
        "RISK_INDICATOR",
        "HEALTH_TRAJECTORY",
        "RETROSPECTIVE_LEARNING",
        "TEMPORAL_BENCHMARK",
        "EFFECTIVENESS_METRIC",
    ]

    def __init__(self, llm_client=None):
        """
        Initialize pattern extractor.

        Args:
            llm_client: httpx AsyncClient for LLM gateway calls
        """
        self._llm = llm_client

    async def extract(self, data: dict, context: dict) -> Tuple[dict, List[str]]:
        """
        Extract patterns from generalized data.

        Args:
            data: Generalized data
            context: Context information

        Returns: (data_with_patterns, transformation_log)
        """
        log = []
        result = self._deep_copy(data)
        extracted_patterns = []

        # Extract from different data types
        fear_patterns = self._extract_fear_patterns(data)
        extracted_patterns.extend(fear_patterns)

        health_pattern = self._extract_health_pattern(data)
        if health_pattern:
            extracted_patterns.append(health_pattern)

        retro_patterns = self._extract_retrospective_patterns(data)
        extracted_patterns.extend(retro_patterns)

        temporal_patterns = self._extract_temporal_patterns(data)
        extracted_patterns.extend(temporal_patterns)

        # LLM-enhanced pattern articulation
        if self._llm and extracted_patterns:
            try:
                extracted_patterns = await self._llm_articulate_patterns(extracted_patterns, context)
            except Exception as e:
                logger.warning(f"LLM pattern articulation failed: {e}")

        # Deduplicate
        extracted_patterns = self._deduplicate_patterns(extracted_patterns)

        result["extracted_patterns"] = extracted_patterns

        if extracted_patterns:
            log.append(f"Stage 4: Extracted {len(extracted_patterns)} actionable patterns")

        return result, log

    def extract_sync(self, data: dict, context: dict) -> Tuple[dict, List[str]]:
        """Synchronous version without LLM enhancement."""
        log = []
        result = self._deep_copy(data)
        extracted_patterns = []

        fear_patterns = self._extract_fear_patterns(data)
        extracted_patterns.extend(fear_patterns)

        health_pattern = self._extract_health_pattern(data)
        if health_pattern:
            extracted_patterns.append(health_pattern)

        retro_patterns = self._extract_retrospective_patterns(data)
        extracted_patterns.extend(retro_patterns)

        temporal_patterns = self._extract_temporal_patterns(data)
        extracted_patterns.extend(temporal_patterns)

        extracted_patterns = self._deduplicate_patterns(extracted_patterns)

        result["extracted_patterns"] = extracted_patterns

        if extracted_patterns:
            log.append(f"Stage 4: Extracted {len(extracted_patterns)} patterns (sync)")

        return result, log

    async def _llm_articulate_patterns(self, patterns: List[dict], context: dict) -> List[dict]:
        """
        Use LLM to improve pattern articulation.
        """
        import json

        prompt = f"""Review these innovation patterns and improve their articulation.
For each pattern:
1. Make the description more actionable and specific
2. Improve applicability_criteria to be measurable
3. Add concrete success_indicators and risk_indicators

Patterns:
{json.dumps(patterns[:5], default=str)[:2000]}

Return JSON array with improved patterns. Keep pattern_id intact."""

        response = await self._llm.post("/llm/chat", json={
            "messages": [{"role": "user", "content": prompt}],
            "system_prompt": "You are an innovation pattern analyst. Return only valid JSON array.",
            "max_tokens": 1000,
            "temperature": 0.3,
            "stream": False
        })

        result = response.json()
        content = result.get("content", "[]")

        try:
            improved = json.loads(content)
            if isinstance(improved, list):
                return improved
        except json.JSONDecodeError:
            pass

        return patterns  # Return original if LLM fails

    def _extract_fear_patterns(self, data: dict) -> List[dict]:
        """Extract patterns from fears/risks."""
        patterns = []
        fears = data.get("fears", [])

        if not isinstance(fears, list):
            fears = [fears] if fears else []

        for fear in fears[:5]:  # Max 5
            if isinstance(fear, str):
                fear_text = fear
            elif isinstance(fear, dict):
                fear_text = fear.get("description", "")
            else:
                continue

            if not fear_text or len(fear_text) < 10:
                continue

            patterns.append({
                "pattern_id": str(uuid.uuid4())[:8],
                "pattern_type": "RISK_INDICATOR",
                "title": f"Risk: {fear_text[:50]}...",
                "description": fear_text[:200],
                "applicability_criteria": "Similar problem domain and phase",
                "success_indicators": ["Risk acknowledged and addressed early"],
                "risk_indicators": [fear_text[:100]],
                "confidence_level": 0.6,
                "extracted_at": datetime.now(timezone.utc).isoformat()
            })

        return patterns

    def _extract_health_pattern(self, data: dict) -> Optional[dict]:
        """Extract pattern from health trajectory."""
        health_zone = data.get("health_zone")
        health_score = data.get("health_score")

        if not health_zone:
            return None

        description = f"Pursuit in {health_zone} zone"
        if health_score:
            description += f" (score: {health_score})"

        return {
            "pattern_id": str(uuid.uuid4())[:8],
            "pattern_type": "HEALTH_TRAJECTORY",
            "title": f"Health Pattern: {health_zone}",
            "description": description,
            "applicability_criteria": "Pursuits in similar health state",
            "success_indicators": ["Stable or improving health score", "Proactive issue addressing"],
            "risk_indicators": ["Declining health trend", "Multiple red flags"],
            "confidence_level": 0.5,
            "extracted_at": datetime.now(timezone.utc).isoformat()
        }

    def _extract_retrospective_patterns(self, data: dict) -> List[dict]:
        """Extract patterns from retrospective learnings."""
        patterns = []
        retrospective = data.get("retrospective", {})

        if not retrospective:
            return patterns

        learnings = retrospective.get("key_learnings", [])
        for learning in learnings[:3]:  # Max 3
            if isinstance(learning, str) and len(learning) > 20:
                patterns.append({
                    "pattern_id": str(uuid.uuid4())[:8],
                    "pattern_type": "RETROSPECTIVE_LEARNING",
                    "title": f"Learning: {learning[:40]}...",
                    "description": learning[:200],
                    "applicability_criteria": "Similar methodology and phase",
                    "success_indicators": ["Applied this learning early", "Team aware of pattern"],
                    "risk_indicators": ["Repeating same mistakes"],
                    "confidence_level": 0.7,
                    "extracted_at": datetime.now(timezone.utc).isoformat()
                })

        return patterns

    def _extract_temporal_patterns(self, data: dict) -> List[dict]:
        """Extract temporal/timing patterns."""
        patterns = []

        # Phase duration patterns
        phases = data.get("phase_history", [])
        for phase in phases:
            duration = phase.get("duration_days")
            phase_name = phase.get("phase")

            if duration and phase_name:
                pattern_type = "below_median" if duration < 30 else "above_median"
                patterns.append({
                    "pattern_id": str(uuid.uuid4())[:8],
                    "pattern_type": "TEMPORAL_BENCHMARK",
                    "title": f"Phase Duration: {phase_name}",
                    "description": f"Phase {phase_name} completed in {pattern_type} time",
                    "applicability_criteria": f"Pursuits entering {phase_name} phase",
                    "success_indicators": [f"Phase completed within typical duration"],
                    "risk_indicators": ["Extended phase duration"],
                    "confidence_level": 0.6,
                    "extracted_at": datetime.now(timezone.utc).isoformat()
                })

        return patterns[:3]  # Max 3

    def _deduplicate_patterns(self, patterns: List[dict]) -> List[dict]:
        """Remove duplicate or highly similar patterns."""
        if not patterns:
            return patterns

        unique = []
        seen_descriptions = set()

        for pattern in patterns:
            desc = pattern.get("description", "")[:50].lower()
            if desc not in seen_descriptions:
                seen_descriptions.add(desc)
                unique.append(pattern)

        return unique

    def _deep_copy(self, data: Any) -> Any:
        """Deep copy a data structure."""
        import copy
        return copy.deepcopy(data)
