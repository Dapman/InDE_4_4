"""
IKF Momentum Pattern Contribution

InDE MVP v4.4.0 — The Learning Engine

Packages momentum patterns for anonymized federation contribution.
Extends the IKF knowledge package schema with a MOMENTUM_PATTERN category.

Contribution rules:
  1. Only patterns with confidence_score >= IKF_CONTRIBUTION_CONFIDENCE_THRESHOLD
     are eligible (defined in momentum_pattern_persistence.py)
  2. All persistent identifiers are stripped — only structural context remains
  3. context_hash replaces pursuit_stage + artifact_type + momentum_tier fields
     (hash is non-reversible; originating node cannot be inferred)
  4. Contribution is gated through the existing IKF circuit-breaker / availability
     check — if federation endpoint is down, contribution is queued, not lost

Contribution Package Schema Extension:
  contribution_type:   "MOMENTUM_PATTERN"
  pattern_type:        MomentumPatternType value
  context_hash:        SHA-256 fingerprint (structural, no PII)
  bridge_question_id:  The bridge ID (generic — not node-specific if bridge
                       library is federated; node-local bridges are omitted)
  insight_category:    IML insight category string
  momentum_lift_delta: Observed average lift
  return_rate_7d:      7-day return rate
  confidence_score:    Composite confidence
  sample_count:        Number of observations (must be >= MIN_SAMPLE)
  contributing_node:   Anonymized node identifier (GII-region only, no hash)
  schema_version:      "4.4.0"

© 2026 Yul Williams | InDEVerse, Incorporated
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger("inde.ikf.momentum_contribution")

# Guarded import of momentum pattern persistence
try:
    from modules.iml.momentum_pattern_persistence import (
        get_contribution_eligible_patterns,
        IKF_CONTRIBUTION_CONFIDENCE_THRESHOLD,
    )
    MOMENTUM_PATTERNS_AVAILABLE = True
except ImportError:
    MOMENTUM_PATTERNS_AVAILABLE = False
    logger.warning("Momentum pattern module not available for IKF contribution")

CONTRIBUTION_TYPE = "MOMENTUM_PATTERN"

# Bridge questions that are node-local (not in shared bridge library) are
# excluded from contribution — their IDs have no meaning on other nodes.
NODE_LOCAL_BRIDGE_PREFIX = "local_"


class MomentumContributionPackager:
    """
    Packages eligible momentum patterns for IKF federation contribution.
    """

    def build_contribution_packages(self, node_region: str = "US") -> List[Dict[str, Any]]:
        """
        Build a list of contribution packages from eligible momentum patterns.
        Returns an empty list if no eligible patterns exist.
        """
        if not MOMENTUM_PATTERNS_AVAILABLE:
            return []

        eligible = get_contribution_eligible_patterns()
        if not eligible:
            return []

        packages = []
        for pattern in eligible:
            package = self._build_package(pattern, node_region)
            if package:
                packages.append(package)

        logger.info(
            f"Built {len(packages)} momentum contribution packages "
            f"from {len(eligible)} eligible patterns"
        )
        return packages

    def _build_package(self, pattern: Dict[str, Any], node_region: str) -> Optional[Dict[str, Any]]:
        """
        Serialize a single pattern into an anonymized contribution package.
        Returns None if the pattern is not suitable for contribution
        (e.g., node-local bridge ID).
        """
        bridge_id = pattern.get("bridge_question_id")
        if bridge_id and bridge_id.startswith(NODE_LOCAL_BRIDGE_PREFIX):
            return None  # Node-local bridge; not federable

        return {
            "contribution_type": CONTRIBUTION_TYPE,
            "schema_version": "4.4.0",
            "pattern_type": pattern.get("pattern_type"),
            "context_hash": pattern.get("context_hash"),
            "bridge_question_id": bridge_id,
            "insight_category": pattern.get("insight_category"),
            "momentum_lift_delta": round(pattern.get("momentum_lift_delta", 0.0), 4),
            "return_rate_7d": round(pattern.get("return_rate_7d", 0.0), 4),
            "confidence_score": round(pattern.get("confidence_score", 0.0), 4),
            "sample_count": pattern.get("sample_count", 0),
            "contributing_node": node_region,   # Region only — no node hash
            "packaged_at": datetime.now(timezone.utc).isoformat(),
        }
