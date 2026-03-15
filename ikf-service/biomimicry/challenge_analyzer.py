"""
Biomimicry Challenge Analyzer

Detects functional parallels between innovation challenges and biological
strategies. Uses LLM-assisted function extraction (not keyword matching)
combined with database queries and LLM-assisted relevance ranking.

Architecture:
    Challenge Context -> Function Extraction (LLM) -> Database Query ->
    Relevance Ranking (LLM) -> Threshold Gate (>=0.60) -> Coaching Offer (max 2)

Three-Tier Intelligence:
    Tier 1: Curated database query (this module)
    Tier 2: LLM deep knowledge (invoked during coaching, not here)
    Tier 3: IKF federation patterns (included in database query via source filter)
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import uuid4

logger = logging.getLogger("inde.ikf.biomimicry.analyzer")

# Valid function categories from BiomimicryFunction enum
VALID_FUNCTIONS = [
    "thermal_regulation", "structural_optimization", "water_management",
    "energy_efficiency", "swarm_coordination", "self_healing",
    "communication_signaling", "environmental_adaptation", "surface_engineering",
    "passive_harvesting", "drag_reduction", "impact_absorption",
    "pattern_recognition", "distributed_decision", "resource_optimization",
    "regeneration", "camouflage", "adhesion"
]


class BiomimicryMatchResult:
    """Result of pattern matching - passed to coaching context."""

    def __init__(
        self,
        pattern_id: str,
        organism: str,
        strategy_name: str,
        description: str,
        mechanism: str,
        innovation_principles: List[str],
        triz_connections: List[str],
        score: float,
        reason: str,
        known_applications: List[Dict[str, Any]],
        category: str = "",
        functions: List[str] = None
    ):
        self.pattern_id = pattern_id
        self.organism = organism
        self.strategy_name = strategy_name
        self.description = description
        self.mechanism = mechanism
        self.innovation_principles = innovation_principles
        self.triz_connections = triz_connections
        self.score = score
        self.reason = reason
        self.known_applications = known_applications
        self.category = category
        self.functions = functions or []

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "organism": self.organism,
            "strategy_name": self.strategy_name,
            "description": self.description,
            "mechanism": self.mechanism,
            "innovation_principles": self.innovation_principles,
            "triz_connections": self.triz_connections,
            "score": self.score,
            "reason": self.reason,
            "known_applications": self.known_applications,
            "category": self.category,
            "functions": self.functions
        }


class BiomimicryAnalyzer:
    """
    LLM-assisted challenge analysis for biomimicry pattern matching.

    This is the core intelligence that detects when biological strategies
    are relevant to an innovator's challenge. It uses a three-stage process:

    1. Function Extraction: LLM analyzes challenge to identify functional
       requirements that might have biological analogs

    2. Database Query: Query biomimicry_patterns collection for candidates
       matching the extracted functions

    3. Relevance Ranking: LLM ranks candidates by how well the biological
       mechanism maps to the specific challenge context

    The threshold gate (>=0.60) ensures only high-confidence matches surface.
    Maximum 2 patterns offered per interaction to avoid overwhelming.
    """

    def __init__(self, db, llm_gateway, config=None):
        """
        Initialize the Biomimicry Analyzer.

        Args:
            db: MongoDB database instance
            llm_gateway: LLM gateway for function extraction and ranking
            config: Optional configuration object
        """
        self._db = db
        self._llm = llm_gateway
        self._config = config
        self._confidence_threshold = 0.60
        self._max_offers_per_interaction = 2
        self._max_candidates_for_ranking = 8

    async def analyze_challenge(
        self,
        challenge_context: str,
        pursuit_domain: Optional[str] = None,
        active_methodology: Optional[str] = None,
        pursuit_id: Optional[str] = None,
    ) -> List[BiomimicryMatchResult]:
        """
        Main entry point. Analyzes challenge for biomimicry opportunities.

        Returns 0-2 high-confidence pattern matches, or empty list if
        no biological parallels are relevant.

        CRITICAL: This method must return quickly (<2s) to avoid blocking
        the coaching turn. Database queries are fast; LLM calls are the
        bottleneck. Use concise prompts.

        Args:
            challenge_context: Text describing the innovation challenge
            pursuit_domain: Optional domain context (e.g., "architecture")
            active_methodology: Optional methodology (lean_startup, etc.)
            pursuit_id: Optional pursuit ID for tracking

        Returns:
            List of BiomimicryMatchResult objects (0-2 items)
        """
        logger.debug(f"Analyzing challenge for biomimicry: {challenge_context[:100]}...")

        # Step 1: LLM-assisted function extraction
        extracted_functions = await self._extract_functions(challenge_context)
        if not extracted_functions:
            logger.debug("No biological parallels detected - returning empty")
            return []  # No biological parallels detected

        logger.debug(f"Extracted functions: {extracted_functions}")

        # Step 2: Database query for candidate patterns
        candidates = await self._query_candidates(
            extracted_functions, pursuit_domain
        )
        if not candidates:
            logger.debug("No candidate patterns found")
            return []

        logger.debug(f"Found {len(candidates)} candidate patterns")

        # Step 3: LLM-assisted relevance ranking
        ranked = await self._rank_relevance(
            candidates, challenge_context, pursuit_domain, active_methodology
        )

        # Step 4: Threshold gate + limit
        results = [m for m in ranked if m.score >= self._confidence_threshold]
        final_results = results[:self._max_offers_per_interaction]

        logger.info(
            f"Biomimicry analysis: {len(extracted_functions)} functions, "
            f"{len(candidates)} candidates, {len(final_results)} results"
        )

        # Record matches for analytics
        if final_results and pursuit_id:
            await self._record_matches(
                final_results, extracted_functions, challenge_context, pursuit_id
            )

        return final_results

    async def _extract_functions(self, challenge_context: str) -> List[str]:
        """
        LLM-assisted function extraction.

        Prompt instructs the LLM to analyze the challenge for functional
        requirements that have biological analogs. Returns standardized
        function categories from BiomimicryFunction enum.

        CRITICAL: The prompt explicitly tells the LLM to return empty
        if no genuine biological parallels exist. We do NOT force
        biomimicry connections where none exist naturally.

        Args:
            challenge_context: The innovation challenge description

        Returns:
            List of function strings (0-3 items)
        """
        prompt = f"""Analyze this innovation challenge for functional requirements
that may have biological analogs. Extract 0-3 core functions using ONLY
these standardized categories:

thermal_regulation, structural_optimization, water_management,
energy_efficiency, swarm_coordination, self_healing,
communication_signaling, environmental_adaptation, surface_engineering,
passive_harvesting, drag_reduction, impact_absorption,
pattern_recognition, distributed_decision, resource_optimization,
regeneration, camouflage, adhesion

Challenge context: {challenge_context}

IMPORTANT: Return EMPTY if no genuine functional parallel to biological
strategies exists. Do NOT force connections. Many innovation challenges
have no meaningful biomimicry analog - that's completely fine.

Return ONLY a JSON array of matching function names, e.g. ["thermal_regulation", "energy_efficiency"]
Return [] if no biological parallels exist."""

        try:
            response = await self._llm.complete(prompt, max_tokens=100)

            # Parse JSON array from response
            functions = self._parse_function_response(response)

            # Validate against known functions
            valid_functions = [f for f in functions if f in VALID_FUNCTIONS]

            # Limit to 3
            return valid_functions[:3]

        except Exception as e:
            logger.warning(f"Function extraction failed: {e}")
            return []

    def _parse_function_response(self, response: str) -> List[str]:
        """
        Parse LLM response to extract function array.

        Handles various response formats including:
        - Pure JSON array: ["func1", "func2"]
        - JSON in markdown: ```json ["func1"]```
        - Text with JSON: Here are the functions: ["func1"]
        """
        try:
            # Try direct JSON parse
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # Try to find JSON array in response
        array_match = re.search(r'\[([^\]]*)\]', response)
        if array_match:
            try:
                return json.loads(array_match.group(0))
            except json.JSONDecodeError:
                pass

        # Try to extract quoted strings
        quoted = re.findall(r'"([^"]+)"', response)
        if quoted:
            return [q for q in quoted if q in VALID_FUNCTIONS]

        return []

    async def _query_candidates(
        self, functions: List[str], domain: Optional[str] = None
    ) -> List[dict]:
        """
        Query biomimicry_patterns collection for candidates matching
        extracted functions.

        Query strategy:
        - Primary: patterns whose functions overlap with extracted functions
        - Secondary: patterns whose applicable_domains include pursuit domain
        - Both curated and IKF-federated patterns included (no source filter)
        - Sort by effectiveness (acceptance_rate desc, match_count desc)
        - Limit to 8 candidates for relevance ranking (keeps LLM prompt small)

        Args:
            functions: List of extracted function categories
            domain: Optional pursuit domain for boosting

        Returns:
            List of pattern documents from database
        """
        if domain:
            query = {
                "$or": [
                    {"functions": {"$in": functions}},
                    {
                        "functions": {"$in": functions},
                        "applicable_domains": domain
                    }
                ]
            }
        else:
            query = {"functions": {"$in": functions}}

        cursor = self._db.biomimicry_patterns.find(query).sort([
            ("acceptance_rate", -1),
            ("match_count", -1)
        ]).limit(self._max_candidates_for_ranking)

        candidates = list(cursor)
        return candidates

    async def _rank_relevance(
        self, candidates: List[dict], challenge_context: str,
        domain: Optional[str], methodology: Optional[str]
    ) -> List[BiomimicryMatchResult]:
        """
        LLM-assisted relevance ranking.

        Given candidate biological strategies and the specific challenge
        context, the LLM ranks by:
        1. How directly the biological mechanism maps to the challenge
        2. Whether the innovator's domain allows the principle to be applied
        3. Whether known applications exist in related domains
        4. The "insight distance" - the balance between surprising and actionable

        Args:
            candidates: List of candidate pattern documents
            challenge_context: The innovation challenge description
            domain: Optional pursuit domain
            methodology: Optional active methodology

        Returns:
            List of scored BiomimicryMatchResult objects
        """
        if not candidates:
            return []

        # Format candidates into concise summaries for the prompt
        candidate_summaries = self._format_candidates_for_ranking(candidates)

        prompt = f"""Given these biological strategies and the innovator's challenge,
rank each by relevance. Score 0.0-1.0.

Challenge: {challenge_context}
Domain: {domain or 'unspecified'}

Candidates:
{candidate_summaries}

Rank by:
1. How directly the biological mechanism maps to the challenge
2. Whether the domain allows the principle to be applied
3. Whether known applications exist in related domains
4. Insight distance - prefer patterns that would genuinely surprise the innovator

Return JSON array: [{{"pattern_id": "...", "score": 0.XX, "reason": "brief reason"}}]
Order by score descending. Include all candidates."""

        try:
            response = await self._llm.complete(prompt, max_tokens=500)
            rankings = self._parse_ranking_response(response)

            # Build result objects with full pattern data
            results = []
            pattern_map = {c["pattern_id"]: c for c in candidates}

            for ranking in rankings:
                pattern_id = ranking.get("pattern_id")
                if pattern_id not in pattern_map:
                    continue

                pattern = pattern_map[pattern_id]
                result = BiomimicryMatchResult(
                    pattern_id=pattern_id,
                    organism=pattern.get("organism", ""),
                    strategy_name=pattern.get("strategy_name", ""),
                    description=pattern.get("description", ""),
                    mechanism=pattern.get("mechanism", ""),
                    innovation_principles=pattern.get("innovation_principles", []),
                    triz_connections=pattern.get("triz_connections", []),
                    score=float(ranking.get("score", 0.5)),
                    reason=ranking.get("reason", ""),
                    known_applications=pattern.get("known_applications", []),
                    category=pattern.get("category", ""),
                    functions=pattern.get("functions", [])
                )
                results.append(result)

            # Sort by score descending
            results.sort(key=lambda x: x.score, reverse=True)
            return results

        except Exception as e:
            logger.warning(f"Relevance ranking failed: {e}")
            # Fallback: return candidates with default scores
            results = []
            for pattern in candidates[:self._max_offers_per_interaction]:
                result = BiomimicryMatchResult(
                    pattern_id=pattern.get("pattern_id", ""),
                    organism=pattern.get("organism", ""),
                    strategy_name=pattern.get("strategy_name", ""),
                    description=pattern.get("description", ""),
                    mechanism=pattern.get("mechanism", ""),
                    innovation_principles=pattern.get("innovation_principles", []),
                    triz_connections=pattern.get("triz_connections", []),
                    score=0.65,  # Default medium-high score
                    reason="Database match",
                    known_applications=pattern.get("known_applications", []),
                    category=pattern.get("category", ""),
                    functions=pattern.get("functions", [])
                )
                results.append(result)
            return results

    def _format_candidates_for_ranking(self, candidates: List[dict]) -> str:
        """Format candidate patterns into concise summaries for the ranking prompt."""
        summaries = []
        for i, c in enumerate(candidates, 1):
            summary = (
                f"{i}. {c.get('pattern_id')}: {c.get('organism')} - {c.get('strategy_name')}\n"
                f"   Mechanism: {c.get('mechanism', '')[:150]}...\n"
                f"   Functions: {', '.join(c.get('functions', []))}"
            )
            if c.get("known_applications"):
                app = c["known_applications"][0]
                summary += f"\n   Known app: {app.get('name', '')} ({app.get('impact', '')})"
            summaries.append(summary)
        return "\n\n".join(summaries)

    def _parse_ranking_response(self, response: str) -> List[dict]:
        """Parse LLM ranking response into list of {pattern_id, score, reason}."""
        try:
            # Try direct JSON parse
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # Try to find JSON array in response
        array_match = re.search(r'\[[\s\S]*\]', response)
        if array_match:
            try:
                return json.loads(array_match.group(0))
            except json.JSONDecodeError:
                pass

        return []

    async def _record_matches(
        self, results: List[BiomimicryMatchResult],
        extracted_functions: List[str],
        challenge_context: str,
        pursuit_id: str
    ):
        """Record match events for analytics and feedback loop."""
        for result in results:
            match_doc = {
                "match_id": f"bm_{uuid4().hex[:12]}",
                "pursuit_id": pursuit_id,
                "pattern_id": result.pattern_id,
                "match_score": result.score,
                "extracted_functions": extracted_functions,
                "challenge_context": challenge_context[:200],  # Truncate for privacy
                "innovator_response": "pending",
                "feedback_rating": None,
                "methodology": None,
                "coaching_session_id": None,
                "created_at": datetime.now(timezone.utc)
            }

            try:
                self._db.biomimicry_matches.insert_one(match_doc)
            except Exception as e:
                logger.warning(f"Failed to record match: {e}")

    async def get_pattern_by_id(self, pattern_id: str) -> Optional[dict]:
        """Retrieve a specific pattern by ID."""
        return self._db.biomimicry_patterns.find_one({"pattern_id": pattern_id})

    async def get_patterns_by_category(
        self, category: str, limit: int = 10
    ) -> List[dict]:
        """Retrieve patterns by category."""
        return list(
            self._db.biomimicry_patterns.find({"category": category})
            .sort([("acceptance_rate", -1)])
            .limit(limit)
        )

    async def get_pattern_stats(self) -> dict:
        """Get overall pattern database statistics."""
        total = self._db.biomimicry_patterns.count_documents({})

        by_category = {}
        for cat in ["THERMAL_REGULATION", "STRUCTURAL_STRENGTH", "WATER_MANAGEMENT",
                    "ENERGY_EFFICIENCY", "SWARM_INTELLIGENCE", "SELF_HEALING",
                    "COMMUNICATION", "ADAPTATION"]:
            by_category[cat] = self._db.biomimicry_patterns.count_documents(
                {"category": cat}
            )

        by_source = {
            "curated": self._db.biomimicry_patterns.count_documents({"source": "curated"}),
            "ikf_federation": self._db.biomimicry_patterns.count_documents({"source": "ikf_federation"}),
            "org_contributed": self._db.biomimicry_patterns.count_documents({"source": "org_contributed"})
        }

        with_triz = self._db.biomimicry_patterns.count_documents(
            {"triz_connections": {"$ne": []}}
        )

        return {
            "total": total,
            "by_category": by_category,
            "by_source": by_source,
            "triz_coverage": f"{(with_triz / total * 100) if total > 0 else 0:.1f}%"
        }
