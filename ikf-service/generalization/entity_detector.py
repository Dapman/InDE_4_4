"""
InDE v3.2 - LLM-Assisted Entity Detector
Stage 1 generalization: Entity detection and abstraction.

LLM-assisted detection identifies entities requiring abstraction.
Fallback: regex-only detection if LLM unavailable.

Cost management: ONE LLM call per package (~$0.01).
"""

import json
import logging
import re
from typing import Tuple, List, Dict, Any

logger = logging.getLogger("inde.ikf.entity_detector")


class LLMEntityDetector:
    """
    LLM-assisted entity detection for Stage 1 generalization.

    Sends pursuit data to inde-llm-gateway with a specialized prompt
    that identifies entities requiring abstraction.

    Cost management: ONE LLM call per package (~$0.01).
    Fallback: regex-only detection if LLM unavailable.
    """

    # Regex patterns for common entity types
    PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone_us": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        "phone_intl": r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b',
        "url": r'https?://[^\s<>"{}|\\^`\[\]]+',
        "money": r'\$\d+(?:,\d{3})*(?:\.\d{2})?(?:\s*(?:million|billion|M|B|K))?',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "ip_address": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    }

    def __init__(self, llm_client=None):
        """
        Initialize entity detector.

        Args:
            llm_client: httpx AsyncClient for LLM gateway calls
        """
        self._llm = llm_client

    async def detect_and_abstract(self, data: dict, context: dict) -> Tuple[dict, List[str]]:
        """
        Detect entities and replace with abstractions.

        Args:
            data: Data to process
            context: Context with industry, etc.

        Returns: (abstracted_data, transformation_log)
        """
        log = []

        # Try LLM-assisted detection
        if self._llm:
            try:
                entities = await self._llm_detect(data)
                for entity in entities:
                    data, entry = self._apply_abstraction(data, entity)
                    if entry:
                        log.append(entry)
                logger.info(f"LLM entity detection found {len(entities)} entities")
                return data, log
            except Exception as e:
                logger.warning(f"LLM entity detection failed, using regex fallback: {e}")

        # Fallback: regex patterns (v3.0.3 behavior)
        data, regex_log = self._regex_detect(data)
        log.extend(regex_log)
        return data, log

    def regex_detect_sync(self, data: dict) -> Tuple[dict, List[str]]:
        """Synchronous regex-only detection for non-async contexts."""
        return self._regex_detect(data)

    async def _llm_detect(self, data: dict) -> List[dict]:
        """
        Call LLM gateway to identify entities.

        Prompt instructs the LLM to return structured JSON:
        [{"text": "Acme Corp", "category": "organization",
          "abstraction": "Mid-size Manufacturing Company", "confidence": 0.95}]
        """
        # Truncate data to avoid token limits
        data_str = json.dumps(data, default=str)[:3000]

        prompt = f"""Analyze the following innovation pursuit data and identify all entities
that should be abstracted for privacy-preserving knowledge sharing.

For each entity, provide:
- text: the exact text to replace
- category: person | organization | product | location | project | financial
- abstraction: a generic replacement that preserves context
- confidence: 0.0-1.0

Return ONLY valid JSON array. No explanation.

Data:
{data_str}"""

        response = await self._llm.post("/llm/chat", json={
            "messages": [{"role": "user", "content": prompt}],
            "system_prompt": "You are a data anonymization specialist. Return only valid JSON.",
            "max_tokens": 500,
            "temperature": 0.1,
            "stream": False
        })

        result = response.json()
        content = result.get("content", "[]")

        # Parse JSON, handle potential errors
        try:
            # Extract JSON array from response (handle markdown code blocks)
            if "```" in content:
                # Extract content between code blocks
                match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
                if match:
                    content = match.group(1)

            entities = json.loads(content)
            if not isinstance(entities, list):
                return []
            return entities
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM entity response: {content[:100]}")
            return []

    def _regex_detect(self, data: dict) -> Tuple[dict, List[str]]:
        """
        v3.0.3 regex-based entity detection (fallback).

        Returns: (processed_data, transformation_log)
        """
        log = []
        data_str = json.dumps(data, default=str)
        counts = {}

        # Apply each pattern
        for pii_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, data_str)
            if matches:
                counts[pii_type] = len(matches)
                if pii_type == "email":
                    data_str = re.sub(pattern, "[email redacted]", data_str)
                elif pii_type in ("phone_us", "phone_intl"):
                    data_str = re.sub(pattern, "[phone redacted]", data_str)
                elif pii_type == "url":
                    data_str = re.sub(pattern, "[url redacted]", data_str)
                elif pii_type == "money":
                    data_str = re.sub(pattern, "[amount]", data_str)
                elif pii_type == "ssn":
                    data_str = re.sub(pattern, "[SSN redacted]", data_str)
                elif pii_type == "ip_address":
                    data_str = re.sub(pattern, "[IP redacted]", data_str)

        # Detect capitalized names (potential person/company names)
        name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        name_matches = re.findall(name_pattern, data_str)
        for match in name_matches:
            words = match.split()
            if 2 <= len(words) <= 4:
                if self._looks_like_person_name(match):
                    data_str = data_str.replace(match, "[Person]")
                    counts["person"] = counts.get("person", 0) + 1
                elif self._looks_like_company_name(match):
                    data_str = data_str.replace(match, "[Organization]")
                    counts["organization"] = counts.get("organization", 0) + 1

        # Build log
        for entity_type, count in counts.items():
            log.append(f"Stage 1: Abstracted {count} {entity_type} entities (regex)")

        try:
            return json.loads(data_str), log
        except json.JSONDecodeError:
            # If JSON is malformed after replacements, return original with warning
            log.append("WARNING: JSON parsing failed after entity abstraction")
            return data, log

    def _apply_abstraction(self, data: dict, entity: dict) -> Tuple[dict, str]:
        """
        Replace entity text with abstraction throughout data.

        Args:
            data: Data structure to modify
            entity: Entity dict with text, category, abstraction, confidence

        Returns: (modified_data, log_entry)
        """
        try:
            text = json.dumps(data, default=str)
            original = entity.get("text", "")
            replacement = entity.get("abstraction", "[REDACTED]")

            if not original:
                return data, ""

            text = text.replace(original, replacement)
            log_entry = (
                f"Entity '{original[:30]}...' ({entity.get('category', 'unknown')}) → "
                f"'{replacement}' (confidence: {entity.get('confidence', 'N/A')})"
            )

            return json.loads(text), log_entry
        except Exception as e:
            logger.warning(f"Failed to apply abstraction: {e}")
            return data, ""

    def _looks_like_person_name(self, text: str) -> bool:
        """Heuristic: detect if text looks like a person name."""
        words = text.split()
        if len(words) == 2:
            # Two capitalized words, common name pattern
            return all(w[0].isupper() and len(w) > 1 and w[1:].islower() for w in words)
        return False

    def _looks_like_company_name(self, text: str) -> bool:
        """Heuristic: detect if text looks like a company name."""
        company_indicators = [
            "Inc", "Corp", "LLC", "Ltd", "Co", "Company", "Group",
            "Partners", "Technologies", "Solutions", "Systems", "Services"
        ]
        return any(ind in text for ind in company_indicators)
