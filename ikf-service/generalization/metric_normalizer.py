"""
InDE v3.2 - Metric Normalizer
Stage 2 generalization: Convert absolute values to relative/categorical representations.

Examples:
- "$47M revenue" → "$10M-$100M revenue range"
- "847 employees" → "500-1000 employees"
- "17 days in DE_RISK" → "Phase duration: below median"
"""

import json
import logging
from typing import Tuple, List, Dict, Any, Optional

logger = logging.getLogger("inde.ikf.metric_normalizer")


class MetricNormalizer:
    """
    Stage 2: Metric Normalization.

    Convert absolute values to relative or categorical representations
    to preserve patterns while removing specific identifiable metrics.
    """

    # Default metric ranges by type
    METRIC_RANGES = {
        "revenue": [
            (0, 1_000_000, "Under $1M revenue"),
            (1_000_000, 10_000_000, "$1M-$10M revenue range"),
            (10_000_000, 100_000_000, "$10M-$100M revenue range"),
            (100_000_000, 1_000_000_000, "$100M-$1B revenue range"),
            (1_000_000_000, float('inf'), "Over $1B revenue"),
        ],
        "employees": [
            (0, 10, "Micro (1-10 employees)"),
            (10, 50, "Small (10-50 employees)"),
            (50, 250, "Medium (50-250 employees)"),
            (250, 1000, "Large (250-1000 employees)"),
            (1000, 5000, "Enterprise (1000-5000 employees)"),
            (5000, float('inf'), "Large Enterprise (5000+ employees)"),
        ],
        "days": [
            (0, 7, "Short duration (< 1 week)"),
            (7, 30, "Medium duration (1-4 weeks)"),
            (30, 90, "Standard duration (1-3 months)"),
            (90, 180, "Extended duration (3-6 months)"),
            (180, float('inf'), "Long duration (6+ months)"),
        ],
        "percentage": [
            (0, 10, "Minimal (< 10%)"),
            (10, 25, "Low (10-25%)"),
            (25, 50, "Moderate (25-50%)"),
            (50, 75, "High (50-75%)"),
            (75, 100, "Very High (75%+)"),
        ],
        "count": [
            (0, 3, "Few (1-3)"),
            (3, 10, "Several (3-10)"),
            (10, 50, "Many (10-50)"),
            (50, 100, "Numerous (50-100)"),
            (100, float('inf'), "Extensive (100+)"),
        ],
    }

    # Keywords to infer metric type from field names
    METRIC_KEYWORDS = {
        "revenue": ["revenue", "sales", "income", "earnings", "budget", "funding", "cost", "price", "amount"],
        "employees": ["employee", "staff", "headcount", "team_size", "workforce", "personnel"],
        "days": ["days", "duration", "time", "period", "weeks", "months"],
        "percentage": ["percent", "rate", "ratio", "proportion", "share"],
        "count": ["count", "number", "total", "quantity"],
    }

    def __init__(self, custom_ranges: Dict = None):
        """
        Initialize normalizer.

        Args:
            custom_ranges: Optional custom range definitions
        """
        self._ranges = {**self.METRIC_RANGES}
        if custom_ranges:
            self._ranges.update(custom_ranges)

    def normalize(self, data: dict, context: dict) -> Tuple[dict, List[str]]:
        """
        Normalize metrics in data.

        Args:
            data: Data to process
            context: Context with industry info for industry-specific ranges

        Returns: (normalized_data, transformation_log)
        """
        log = []
        result = self._deep_copy(data)
        normalizations = 0

        # Apply industry-specific adjustments
        industry_ranges = self._get_industry_ranges(context)
        if industry_ranges:
            self._ranges.update(industry_ranges)

        # Process the data recursively
        result, normalizations = self._process_data(result)

        if normalizations > 0:
            log.append(f"Stage 2: Normalized {normalizations} metric values to ranges")

        return result, log

    def _process_data(self, data: Any, path: str = "") -> Tuple[Any, int]:
        """Recursively process data to normalize metrics."""
        normalizations = 0

        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    metric_type = self._infer_metric_type(key)
                    if metric_type:
                        result[key] = self._normalize_value(value, metric_type)
                        normalizations += 1
                    else:
                        result[key] = value
                else:
                    processed, count = self._process_data(value, f"{path}.{key}")
                    result[key] = processed
                    normalizations += count
            return result, normalizations

        elif isinstance(data, list):
            result = []
            for i, item in enumerate(data):
                processed, count = self._process_data(item, f"{path}[{i}]")
                result.append(processed)
                normalizations += count
            return result, normalizations

        else:
            return data, normalizations

    def _infer_metric_type(self, key: str) -> Optional[str]:
        """Infer metric type from key name."""
        key_lower = key.lower()

        for metric_type, keywords in self.METRIC_KEYWORDS.items():
            if any(kw in key_lower for kw in keywords):
                return metric_type

        return None

    def _normalize_value(self, value: float, metric_type: str) -> str:
        """Convert a numeric value to a range category."""
        ranges = self._ranges.get(metric_type, [])

        for min_val, max_val, label in ranges:
            if min_val <= value < max_val:
                return label

        return f"{metric_type}: {value}"  # Fallback

    def _get_industry_ranges(self, context: dict) -> Optional[Dict]:
        """
        Get industry-specific range adjustments.

        Different industries have different "typical" values.
        """
        industry = context.get("industry", "").lower()

        # Industry-specific adjustments
        if "tech" in industry or "software" in industry:
            return {
                "revenue": [
                    (0, 1_000_000, "Pre-revenue / Seed stage"),
                    (1_000_000, 10_000_000, "Series A range ($1M-$10M ARR)"),
                    (10_000_000, 100_000_000, "Growth stage ($10M-$100M ARR)"),
                    (100_000_000, float('inf'), "Scale-up ($100M+ ARR)"),
                ],
            }

        if "manufacturing" in industry:
            return {
                "employees": [
                    (0, 50, "Small shop (< 50 employees)"),
                    (50, 250, "Mid-size manufacturer (50-250)"),
                    (250, 1000, "Large manufacturer (250-1000)"),
                    (1000, float('inf'), "Enterprise manufacturer (1000+)"),
                ],
            }

        return None

    def _deep_copy(self, data: Any) -> Any:
        """Deep copy a data structure."""
        import copy
        return copy.deepcopy(data)
