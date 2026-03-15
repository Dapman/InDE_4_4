"""
InDE v3.2 - Context Preserver
Stage 3 generalization: Retain industry, methodology, and regulatory context.

Preserved fields:
- NAICS code (industry classification)
- Innovation type (product/process/business model/service)
- Methodology archetype (Design Thinking/Lean Startup/etc.)
- Market maturity stage
- Regulatory complexity level
"""

import logging
from typing import Tuple, List, Dict, Any, Optional

logger = logging.getLogger("inde.ikf.context_preserver")


class ContextPreserver:
    """
    Stage 3: Context Preservation.

    Retain industry, methodology, and regulatory context for applicability.
    Uses LLM to generate context summaries when available.
    """

    # NAICS code mapping for common domains
    NAICS_MAP = {
        "technology": "54",
        "software": "5112",
        "healthcare": "62",
        "manufacturing": "31",
        "retail": "44",
        "finance": "52",
        "banking": "522",
        "insurance": "524",
        "education": "61",
        "construction": "23",
        "real_estate": "531",
        "transportation": "48",
        "hospitality": "72",
        "media": "51",
        "telecom": "517",
        "energy": "22",
        "agriculture": "11",
    }

    # Innovation type indicators
    INNOVATION_INDICATORS = {
        "PRODUCT": ["product", "device", "tool", "app", "platform", "hardware", "widget"],
        "PROCESS": ["process", "workflow", "efficiency", "automation", "procedure", "method"],
        "BUSINESS_MODEL": ["business model", "revenue", "pricing", "subscription", "monetization"],
        "SERVICE": ["service", "support", "experience", "consulting", "delivery"],
    }

    # Methodology archetypes
    METHODOLOGIES = [
        "LEAN_STARTUP",
        "DESIGN_THINKING",
        "AGILE",
        "STAGE_GATE",
        "OPEN_INNOVATION",
        "BLUE_OCEAN",
        "JOBS_TO_BE_DONE",
    ]

    def __init__(self, llm_client=None):
        """
        Initialize context preserver.

        Args:
            llm_client: httpx AsyncClient for LLM gateway calls
        """
        self._llm = llm_client

    async def preserve(self, data: dict, context: dict) -> Tuple[dict, List[str]]:
        """
        Preserve and enrich context information.

        Args:
            data: Data being processed
            context: Additional context from caller

        Returns: (data_with_context, transformation_log)
        """
        log = []
        result = self._deep_copy(data)

        # Extract or infer context
        preserved_context = {
            "industry_naics": context.get("naics_code") or self._infer_naics(data, context),
            "innovation_type": context.get("innovation_type") or self._infer_innovation_type(data),
            "methodology_archetype": context.get("methodology") or self._infer_methodology(data),
            "market_maturity": context.get("market_maturity") or self._infer_market_maturity(data),
            "regulatory_complexity": context.get("regulatory_complexity") or self._infer_regulatory(data, context),
        }

        # Try LLM-enhanced context summary if available
        if self._llm:
            try:
                enhanced = await self._llm_enhance_context(data, preserved_context)
                preserved_context["context_summary"] = enhanced.get("summary", "")
                preserved_context["applicability_tags"] = enhanced.get("tags", [])
            except Exception as e:
                logger.warning(f"LLM context enhancement failed: {e}")

        result["ikf_context"] = preserved_context

        preserved_fields = [k for k, v in preserved_context.items() if v]
        log.append(f"Stage 3: Preserved {len(preserved_fields)} context fields: {', '.join(preserved_fields)}")

        return result, log

    def preserve_sync(self, data: dict, context: dict) -> Tuple[dict, List[str]]:
        """Synchronous version without LLM enhancement."""
        log = []
        result = self._deep_copy(data)

        preserved_context = {
            "industry_naics": context.get("naics_code") or self._infer_naics(data, context),
            "innovation_type": context.get("innovation_type") or self._infer_innovation_type(data),
            "methodology_archetype": context.get("methodology") or self._infer_methodology(data),
            "market_maturity": context.get("market_maturity") or self._infer_market_maturity(data),
            "regulatory_complexity": context.get("regulatory_complexity") or self._infer_regulatory(data, context),
        }

        result["ikf_context"] = preserved_context

        preserved_fields = [k for k, v in preserved_context.items() if v]
        log.append(f"Stage 3: Preserved {len(preserved_fields)} context fields")

        return result, log

    async def _llm_enhance_context(self, data: dict, context: dict) -> dict:
        """
        Use LLM to generate context summary and applicability tags.
        """
        import json

        prompt = f"""Analyze this innovation pursuit context and provide:
1. A brief (1-2 sentence) summary of when these patterns would apply
2. 3-5 applicability tags (e.g., "early-stage", "b2b", "regulated-industry")

Context:
- Industry: {context.get('industry_naics', 'Unknown')}
- Innovation Type: {context.get('innovation_type', 'Unknown')}
- Methodology: {context.get('methodology_archetype', 'Unknown')}

Return JSON: {{"summary": "...", "tags": ["..."]}}"""

        response = await self._llm.post("/llm/chat", json={
            "messages": [{"role": "user", "content": prompt}],
            "system_prompt": "You are an innovation pattern analyst. Return only valid JSON.",
            "max_tokens": 200,
            "temperature": 0.3,
            "stream": False
        })

        result = response.json()
        content = result.get("content", "{}")

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"summary": "", "tags": []}

    def _infer_naics(self, data: dict, context: dict) -> str:
        """Infer NAICS code from data and context."""
        # Check explicit context
        industry = context.get("industry", "").lower()
        domain = str(data.get("problem_context", {}).get("domain", "")).lower()
        combined = f"{industry} {domain}"

        for key, code in self.NAICS_MAP.items():
            if key in combined:
                return code

        return "99"  # Unknown

    def _infer_innovation_type(self, data: dict) -> str:
        """Infer innovation type from data."""
        title = str(data.get("title", "")).lower()
        problem = str(data.get("problem_context", {}).get("problem_statement", "")).lower()
        combined = f"{title} {problem}"

        for innovation_type, indicators in self.INNOVATION_INDICATORS.items():
            if any(ind in combined for ind in indicators):
                return innovation_type

        return "PRODUCT"  # Default

    def _infer_methodology(self, data: dict) -> str:
        """Infer methodology archetype from data."""
        methodology = data.get("methodology", "")
        if methodology in self.METHODOLOGIES:
            return methodology

        # Check for keywords
        text = str(data).lower()
        if "lean" in text or "mvp" in text or "experiment" in text:
            return "LEAN_STARTUP"
        if "design thinking" in text or "empathy" in text or "prototype" in text:
            return "DESIGN_THINKING"
        if "agile" in text or "sprint" in text or "scrum" in text:
            return "AGILE"
        if "stage gate" in text or "phase gate" in text:
            return "STAGE_GATE"

        return "LEAN_STARTUP"  # Default

    def _infer_market_maturity(self, data: dict) -> str:
        """Infer market maturity stage."""
        phase = data.get("current_phase", "VISION")

        if phase in ["VISION", "CONCEPT"]:
            return "EMERGING"
        elif phase == "DE_RISK":
            return "GROWING"
        elif phase in ["SCALE", "SUSTAIN"]:
            return "MATURE"

        return "EMERGING"  # Default

    def _infer_regulatory(self, data: dict, context: dict) -> str:
        """Infer regulatory complexity level."""
        industry = context.get("industry", "").lower()

        # High regulatory industries
        high_reg = ["healthcare", "finance", "banking", "insurance", "pharma", "medical", "legal"]
        if any(ind in industry for ind in high_reg):
            return "HIGH"

        # Medium regulatory
        med_reg = ["education", "food", "energy", "construction", "transportation"]
        if any(ind in industry for ind in med_reg):
            return "MEDIUM"

        return "STANDARD"

    def _deep_copy(self, data: Any) -> Any:
        """Deep copy a data structure."""
        import copy
        return copy.deepcopy(data)
