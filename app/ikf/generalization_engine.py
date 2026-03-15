"""
InDE MVP v3.0.3 - Generalization Engine
Four-stage data generalization pipeline for IKF contribution.

Stages:
1. Entity Abstraction - Replace identifiers with generic placeholders
2. Metric Normalization - Convert absolutes to ranges/categories
3. Context Preservation - Retain industry/methodology context
4. Pattern Extraction - Extract actionable patterns

EVERY output must pass human review before IKF marking.
All timestamps use ISO 8601 format for IKF compatibility.
"""

import re
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import uuid

from config import IKF_ENTITY_PATTERNS, IKF_METRIC_RANGES


class GeneralizationEngine:
    """
    Four-stage data generalization pipeline for IKF contribution.
    EVERY output must pass human review before IKF marking.
    """

    def __init__(self, db=None):
        """
        Initialize generalization engine.

        Args:
            db: Optional database instance for context lookups
        """
        self.db = db
        self.entity_patterns = IKF_ENTITY_PATTERNS
        self.metric_ranges = IKF_METRIC_RANGES

        # Replacement templates for entity abstraction
        self._company_templates = [
            "Mid-size {industry} Company",
            "Growing {industry} Organization",
            "Established {industry} Enterprise",
            "{industry} Business"
        ]

        self._person_templates = [
            "Innovation Lead",
            "Project Sponsor",
            "Team Member",
            "Stakeholder",
            "Department Head"
        ]

        self._location_templates = [
            "Major Metro Area",
            "Regional Center",
            "Suburban Location",
            "Urban Center"
        ]

    def generalize(self, raw_data: Dict, context: Dict) -> Dict:
        """
        Run all four stages sequentially.

        Args:
            raw_data: Original pursuit/pattern data
            context: Additional context (industry, methodology, etc.)

        Returns:
            {
                'original_hash': str,  # for audit trail
                'generalized': dict,   # transformed data
                'transformations_log': [str],  # what was changed
                'confidence': float,   # confidence in completeness
                'warnings': [str]      # potential PII needing review
            }
        """
        # Create hash of original for audit
        original_hash = self._hash_data(raw_data)

        transformations_log = []
        warnings = []

        # Stage 1: Entity Abstraction
        stage1_data, stage1_log, stage1_warnings = self._stage1_entity_abstraction(raw_data)
        transformations_log.extend(stage1_log)
        warnings.extend(stage1_warnings)

        # Stage 2: Metric Normalization
        stage2_data, stage2_log = self._stage2_metric_normalization(stage1_data)
        transformations_log.extend(stage2_log)

        # Stage 3: Context Preservation
        stage3_data, stage3_log = self._stage3_context_preservation(stage2_data, context)
        transformations_log.extend(stage3_log)

        # Stage 4: Pattern Extraction
        stage4_data, stage4_log = self._stage4_pattern_extraction(stage3_data)
        transformations_log.extend(stage4_log)

        # Calculate confidence
        confidence = self._calculate_confidence(raw_data, stage4_data, warnings)

        return {
            "original_hash": original_hash,
            "generalized": stage4_data,
            "transformations_log": transformations_log,
            "confidence": confidence,
            "warnings": warnings
        }

    def _stage1_entity_abstraction(self, data: Dict) -> Tuple[Dict, List[str], List[str]]:
        """
        Replace specific identifiers with generic placeholders.

        Examples:
        - "Acme Corp" → "Mid-size Manufacturing Company"
        - "Jane Smith" → "Innovation Lead"
        - "Chicago, IL" → "Major US Metro"
        - "Project Phoenix" → "Internal Transformation Initiative"
        """
        result = self._deep_copy(data)
        log = []
        warnings = []

        # Process all string values recursively
        result, entities_found = self._process_strings(result, self._abstract_entity)

        for entity_type, count in entities_found.items():
            if count > 0:
                log.append(f"Stage 1: Abstracted {count} {entity_type} entities")

        # Check for potential missed PII
        remaining_pii = self._scan_for_pii(result)
        if remaining_pii:
            for pii_type, locations in remaining_pii.items():
                warnings.append(f"Potential {pii_type} detected at: {', '.join(locations[:3])}")

        return result, log, warnings

    def _stage2_metric_normalization(self, data: Dict) -> Tuple[Dict, List[str]]:
        """
        Convert absolute values to relative or categorical representations.

        Examples:
        - "$47M revenue" → "$10M-$100M revenue range"
        - "847 employees" → "500-1000 employees"
        - "17 days in DE_RISK" → "Phase duration: below median"
        """
        result = self._deep_copy(data)
        log = []
        normalizations = 0

        # Process numeric values
        result, normalizations = self._process_metrics(result)

        if normalizations > 0:
            log.append(f"Stage 2: Normalized {normalizations} metric values to ranges")

        return result, log

    def _stage3_context_preservation(self, data: Dict, context: Dict) -> Tuple[Dict, List[str]]:
        """
        Retain industry, methodology, and regulatory context for applicability.

        Preserved fields:
        - NAICS code (industry classification)
        - Innovation type (product/process/business model/service)
        - Methodology archetype (Design Thinking/Lean Startup/etc.)
        - Market maturity stage
        - Regulatory complexity level
        """
        result = self._deep_copy(data)
        log = []

        # Extract or infer context
        preserved_context = {
            "industry_naics": context.get("naics_code") or self._infer_naics(data),
            "innovation_type": context.get("innovation_type") or self._infer_innovation_type(data),
            "methodology_archetype": context.get("methodology") or data.get("methodology", "LEAN_STARTUP"),
            "market_maturity": context.get("market_maturity") or self._infer_market_maturity(data),
            "regulatory_complexity": context.get("regulatory_complexity") or "STANDARD"
        }

        result["ikf_context"] = preserved_context

        preserved_fields = [k for k, v in preserved_context.items() if v]
        log.append(f"Stage 3: Preserved {len(preserved_fields)} context fields: {', '.join(preserved_fields)}")

        return result, log

    def _stage4_pattern_extraction(self, data: Dict) -> Tuple[Dict, List[str]]:
        """
        Extract actionable patterns from generalized data.

        Produces patterns with:
        - applicability_criteria: when this pattern is relevant
        - success_indicators: what to look for
        - risk_indicators: what to watch out for
        - confidence_level: based on evidence strength
        """
        result = self._deep_copy(data)
        log = []
        patterns_extracted = 0

        # Extract patterns from different data types
        extracted_patterns = []

        # From fears/risks
        fears = data.get("fears", [])
        if isinstance(fears, list):
            for fear in fears:
                pattern = self._extract_fear_pattern(fear)
                if pattern:
                    extracted_patterns.append(pattern)
                    patterns_extracted += 1

        # From velocity/health trajectories
        health_pattern = self._extract_health_pattern(data)
        if health_pattern:
            extracted_patterns.append(health_pattern)
            patterns_extracted += 1

        # From retrospective learnings
        retrospective = data.get("retrospective", {})
        if retrospective:
            retro_patterns = self._extract_retrospective_patterns(retrospective)
            extracted_patterns.extend(retro_patterns)
            patterns_extracted += len(retro_patterns)

        result["extracted_patterns"] = extracted_patterns

        if patterns_extracted > 0:
            log.append(f"Stage 4: Extracted {patterns_extracted} actionable patterns")

        return result, log

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _hash_data(self, data: Dict) -> str:
        """Create SHA256 hash of data for audit trail."""
        import json
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def _deep_copy(self, data: Any) -> Any:
        """Deep copy a data structure."""
        import copy
        return copy.deepcopy(data)

    def _process_strings(self, data: Any, processor) -> Tuple[Any, Dict[str, int]]:
        """Recursively process all strings in a data structure."""
        entities_found = {"emails": 0, "phones": 0, "urls": 0, "names": 0, "companies": 0}

        if isinstance(data, str):
            processed, found = processor(data)
            for k, v in found.items():
                entities_found[k] += v
            return processed, entities_found

        elif isinstance(data, dict):
            result = {}
            for key, value in data.items():
                processed, found = self._process_strings(value, processor)
                result[key] = processed
                for k, v in found.items():
                    entities_found[k] += v
            return result, entities_found

        elif isinstance(data, list):
            result = []
            for item in data:
                processed, found = self._process_strings(item, processor)
                result.append(processed)
                for k, v in found.items():
                    entities_found[k] += v
            return result, entities_found

        else:
            return data, entities_found

    def _abstract_entity(self, text: str) -> Tuple[str, Dict[str, int]]:
        """Abstract entities in a text string."""
        found = {"emails": 0, "phones": 0, "urls": 0, "names": 0, "companies": 0}
        result = text

        # Replace emails
        email_pattern = self.entity_patterns.get("email", "")
        if email_pattern:
            matches = re.findall(email_pattern, result)
            found["emails"] = len(matches)
            result = re.sub(email_pattern, "[email redacted]", result)

        # Replace phone numbers
        phone_pattern = self.entity_patterns.get("phone", "")
        if phone_pattern:
            matches = re.findall(phone_pattern, result)
            found["phones"] = len(matches)
            result = re.sub(phone_pattern, "[phone redacted]", result)

        # Replace URLs
        url_pattern = self.entity_patterns.get("url", "")
        if url_pattern:
            matches = re.findall(url_pattern, result)
            found["urls"] = len(matches)
            result = re.sub(url_pattern, "[url redacted]", result)

        # Replace money amounts
        money_pattern = self.entity_patterns.get("money", "")
        if money_pattern:
            result = re.sub(money_pattern, "[amount]", result)

        # Replace capitalized multi-word names (likely company/person names)
        name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        name_matches = re.findall(name_pattern, result)
        for match in name_matches:
            if len(match.split()) <= 4:  # Likely a name
                if self._looks_like_person_name(match):
                    result = result.replace(match, "[Person]")
                    found["names"] += 1
                elif self._looks_like_company_name(match):
                    result = result.replace(match, "[Organization]")
                    found["companies"] += 1

        return result, found

    def _looks_like_person_name(self, text: str) -> bool:
        """Heuristic: detect if text looks like a person name."""
        words = text.split()
        if len(words) == 2:
            # Two capitalized words, common name pattern
            return all(w[0].isupper() and w[1:].islower() for w in words)
        return False

    def _looks_like_company_name(self, text: str) -> bool:
        """Heuristic: detect if text looks like a company name."""
        company_indicators = ["Inc", "Corp", "LLC", "Ltd", "Co", "Company", "Group", "Partners"]
        return any(ind in text for ind in company_indicators)

    def _scan_for_pii(self, data: Any, path: str = "") -> Dict[str, List[str]]:
        """Scan for potential remaining PII."""
        findings = {}

        if isinstance(data, str):
            # Check for patterns that might be PII
            if re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', data):
                findings.setdefault("potential_names", []).append(path)
            if re.search(r'\d{3}[-.]?\d{3}[-.]?\d{4}', data):
                findings.setdefault("potential_phones", []).append(path)

        elif isinstance(data, dict):
            for key, value in data.items():
                sub_findings = self._scan_for_pii(value, f"{path}.{key}")
                for k, v in sub_findings.items():
                    findings.setdefault(k, []).extend(v)

        elif isinstance(data, list):
            for i, item in enumerate(data):
                sub_findings = self._scan_for_pii(item, f"{path}[{i}]")
                for k, v in sub_findings.items():
                    findings.setdefault(k, []).extend(v)

        return findings

    def _process_metrics(self, data: Any, path: str = "") -> Tuple[Any, int]:
        """Normalize numeric metrics to ranges."""
        normalizations = 0

        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    # Determine metric type from key name
                    metric_type = self._infer_metric_type(key)
                    if metric_type and metric_type in self.metric_ranges:
                        result[key] = self._normalize_to_range(value, metric_type)
                        normalizations += 1
                    else:
                        result[key] = value
                else:
                    processed, count = self._process_metrics(value, f"{path}.{key}")
                    result[key] = processed
                    normalizations += count
            return result, normalizations

        elif isinstance(data, list):
            result = []
            for i, item in enumerate(data):
                processed, count = self._process_metrics(item, f"{path}[{i}]")
                result.append(processed)
                normalizations += count
            return result, normalizations

        else:
            return data, normalizations

    def _infer_metric_type(self, key: str) -> Optional[str]:
        """Infer metric type from key name."""
        key_lower = key.lower()
        if any(k in key_lower for k in ["revenue", "amount", "budget", "cost", "price"]):
            return "revenue"
        if any(k in key_lower for k in ["employee", "team_size", "headcount", "staff"]):
            return "employees"
        if any(k in key_lower for k in ["days", "duration", "time"]):
            return "days"
        return None

    def _normalize_to_range(self, value: float, metric_type: str) -> str:
        """Convert a numeric value to a range category."""
        ranges = self.metric_ranges.get(metric_type, [])
        for min_val, max_val, label in ranges:
            if min_val <= value < max_val:
                return label
        return str(value)  # Fallback

    def _infer_naics(self, data: Dict) -> Optional[str]:
        """Infer NAICS code from data."""
        # Simplified - would use actual NAICS lookup in production
        problem_context = data.get("problem_context", {})
        domain = problem_context.get("domain", "").lower()

        naics_map = {
            "technology": "54",
            "healthcare": "62",
            "manufacturing": "31",
            "retail": "44",
            "finance": "52",
            "education": "61"
        }

        for key, code in naics_map.items():
            if key in domain:
                return code

        return "99"  # Unknown

    def _infer_innovation_type(self, data: Dict) -> str:
        """Infer innovation type from data."""
        title = data.get("title", "").lower()
        problem = str(data.get("problem_context", {}).get("problem_statement", "")).lower()

        if any(k in title + problem for k in ["product", "device", "tool", "app"]):
            return "PRODUCT"
        if any(k in title + problem for k in ["process", "workflow", "efficiency"]):
            return "PROCESS"
        if any(k in title + problem for k in ["business model", "revenue", "pricing"]):
            return "BUSINESS_MODEL"
        if any(k in title + problem for k in ["service", "support", "experience"]):
            return "SERVICE"

        return "PRODUCT"  # Default

    def _infer_market_maturity(self, data: Dict) -> str:
        """Infer market maturity stage."""
        # Simplified inference
        phase = data.get("current_phase", "VISION")
        if phase in ["VISION", "CONCEPT"]:
            return "EMERGING"
        elif phase == "DE_RISK":
            return "GROWING"
        else:
            return "MATURE"

    def _extract_fear_pattern(self, fear: Any) -> Optional[Dict]:
        """Extract pattern from a fear/risk."""
        if isinstance(fear, str):
            fear_text = fear
        elif isinstance(fear, dict):
            fear_text = fear.get("description", "")
        else:
            return None

        if not fear_text or len(fear_text) < 10:
            return None

        return {
            "pattern_type": "RISK_INDICATOR",
            "description": f"Risk pattern: {fear_text[:100]}",
            "applicability_criteria": "Similar problem domain and phase",
            "risk_indicators": [fear_text[:50]],
            "confidence_level": 0.6
        }

    def _extract_health_pattern(self, data: Dict) -> Optional[Dict]:
        """Extract pattern from health trajectory."""
        health_zone = data.get("health_zone")
        velocity_status = data.get("velocity_status")

        if not health_zone:
            return None

        return {
            "pattern_type": "HEALTH_TRAJECTORY",
            "description": f"Pursuit in {health_zone} zone",
            "success_indicators": ["Stable or improving health score"],
            "risk_indicators": ["Declining health trend"],
            "confidence_level": 0.5
        }

    def _extract_retrospective_patterns(self, retrospective: Dict) -> List[Dict]:
        """Extract patterns from retrospective learnings."""
        patterns = []

        learnings = retrospective.get("key_learnings", [])
        for learning in learnings[:3]:  # Max 3
            if isinstance(learning, str) and len(learning) > 20:
                patterns.append({
                    "pattern_type": "RETROSPECTIVE_LEARNING",
                    "description": learning[:100],
                    "applicability_criteria": "Similar methodology and phase",
                    "success_indicators": ["Applied this learning early"],
                    "confidence_level": 0.7
                })

        return patterns

    def _calculate_confidence(self, original: Dict, generalized: Dict,
                               warnings: List[str]) -> float:
        """Calculate confidence in generalization completeness."""
        base_confidence = 0.90

        # Reduce for each warning
        confidence = base_confidence - (len(warnings) * 0.05)

        # Reduce if large amounts of text remain
        original_text = str(original)
        generalized_text = str(generalized)

        if len(generalized_text) > len(original_text) * 0.9:
            confidence -= 0.05  # Not much was changed

        return max(0.3, min(1.0, confidence))
