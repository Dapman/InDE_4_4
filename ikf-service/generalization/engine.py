"""
InDE v3.2 - Enhanced Generalization Engine
Four-stage generalization pipeline with LLM-assisted intelligence for IKF contribution.

v3.2 enhancements over v3.0.3:
- Stage 1: LLM-assisted entity detection (replaces regex-only)
- Stage 2: Dynamic range calculation based on industry context
- Stage 3: LLM-generated context summaries
- Stage 4: LLM-assisted pattern articulation with deduplication
- Post-pipeline: Automated PII scanner validation gate

EVERY output must pass human review before IKF marking.
"""

import hashlib
import json
import logging
from typing import Optional, Dict, List, Any

from generalization.entity_detector import LLMEntityDetector
from generalization.metric_normalizer import MetricNormalizer
from generalization.context_preserver import ContextPreserver
from generalization.pattern_extractor import PatternExtractor
from generalization.pii_scanner import PIIScanner

logger = logging.getLogger("inde.ikf.generalization")


class GeneralizationEngine:
    """
    Enhanced four-stage generalization pipeline for IKF contribution.

    v3.2 enhancements over v3.0.3:
    - Stage 1: LLM-assisted entity detection (replaces regex-only)
    - Stage 2: Dynamic range calculation based on industry context
    - Stage 3: LLM-generated context summaries
    - Stage 4: LLM-assisted pattern articulation with deduplication
    - Post-pipeline: Automated PII scanner validation gate

    EVERY output must pass human review before IKF marking.
    """

    def __init__(self, llm_client=None, db=None):
        """
        Initialize generalization engine.

        Args:
            llm_client: httpx client to inde-llm-gateway for LLM calls
            db: Database instance for context lookups
        """
        self._llm = llm_client
        self._db = db
        self._entity_detector = LLMEntityDetector(llm_client)
        self._normalizer = MetricNormalizer()
        self._preserver = ContextPreserver(llm_client)
        self._extractor = PatternExtractor(llm_client)
        self._pii_scanner = PIIScanner()

    async def generalize(self, raw_data: dict, context: dict) -> dict:
        """
        Run all four stages + PII scan sequentially.

        Args:
            raw_data: Original pursuit/pattern data
            context: Additional context (industry, methodology, etc.)

        Returns: {
            'original_hash': str,
            'generalized': dict,
            'transformations_log': [str],
            'confidence': float,
            'pii_scan': {'passed': bool, 'warnings': [str], 'high_confidence_flags': [str]},
            'warnings': [str]
        }
        """
        result = self._deep_copy(raw_data)
        log = []

        logger.info("Starting generalization pipeline")

        # Stage 1: Entity Abstraction (LLM-enhanced)
        result, stage1_log = await self._entity_detector.detect_and_abstract(result, context)
        log.extend(stage1_log)
        logger.debug(f"Stage 1 complete: {len(stage1_log)} transformations")

        # Stage 2: Metric Normalization
        result, stage2_log = self._normalizer.normalize(result, context)
        log.extend(stage2_log)
        logger.debug(f"Stage 2 complete: {len(stage2_log)} normalizations")

        # Stage 3: Context Preservation
        result, stage3_log = await self._preserver.preserve(result, context)
        log.extend(stage3_log)
        logger.debug(f"Stage 3 complete: {len(stage3_log)} context fields")

        # Stage 4: Pattern Extraction
        result, stage4_log = await self._extractor.extract(result, context)
        log.extend(stage4_log)
        logger.debug(f"Stage 4 complete: {len(stage4_log)} patterns")

        # Post-pipeline: PII Scan
        pii_result = self._pii_scanner.scan(result)
        logger.debug(f"PII scan: passed={pii_result['passed']}")

        # Calculate overall confidence
        confidence = self._calculate_confidence(log, pii_result)

        return {
            'original_hash': self._hash_data(raw_data),
            'generalized': result,
            'transformations_log': log,
            'confidence': confidence,
            'pii_scan': pii_result,
            'warnings': [w for w in log if 'WARNING' in w.upper()]
        }

    def generalize_sync(self, raw_data: dict, context: dict) -> dict:
        """
        Synchronous version for non-async contexts.
        Uses regex-only entity detection (no LLM calls).
        """
        result = self._deep_copy(raw_data)
        log = []

        # Stage 1: Entity Abstraction (regex fallback)
        result, stage1_log = self._entity_detector.regex_detect_sync(result)
        log.extend(stage1_log)

        # Stage 2: Metric Normalization
        result, stage2_log = self._normalizer.normalize(result, context)
        log.extend(stage2_log)

        # Stage 3: Context Preservation (sync)
        result, stage3_log = self._preserver.preserve_sync(result, context)
        log.extend(stage3_log)

        # Stage 4: Pattern Extraction (sync)
        result, stage4_log = self._extractor.extract_sync(result, context)
        log.extend(stage4_log)

        # Post-pipeline: PII Scan
        pii_result = self._pii_scanner.scan(result)

        confidence = self._calculate_confidence(log, pii_result)

        return {
            'original_hash': self._hash_data(raw_data),
            'generalized': result,
            'transformations_log': log,
            'confidence': confidence,
            'pii_scan': pii_result,
            'warnings': [w for w in log if 'WARNING' in w.upper()]
        }

    def _calculate_confidence(self, log: List[str], pii_result: dict) -> float:
        """Calculate overall generalization confidence (0.0-1.0)."""
        base = 0.8

        # Reduce for PII flags
        if pii_result.get('high_confidence_flags'):
            base -= 0.3

        # Reduce for excessive warnings
        warning_count = len([w for w in log if 'WARNING' in w.upper()])
        if warning_count > 3:
            base -= 0.1

        # Reduce if minimal transformations occurred
        if len(log) < 3:
            base -= 0.1

        return max(0.0, min(1.0, base))

    def _hash_data(self, data: dict) -> str:
        """Create SHA256 hash of data for audit trail."""
        return hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode()
        ).hexdigest()

    def _deep_copy(self, data: Any) -> Any:
        """Deep copy a data structure."""
        import copy
        return copy.deepcopy(data)
