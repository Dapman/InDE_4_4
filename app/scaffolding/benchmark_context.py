"""
Benchmark Coaching Context - Advisory Performance References

Budget: 500 tokens (within the 12,500 per-turn total)
Max comparisons per turn: 3

Benchmarking references are ADVISORY - they inform the innovator's
understanding but never prescribe action. Consistent with the
Abstract Sovereignty Principle.

Example coaching language:
- "Your pursuit velocity is in the top quartile for your industry"
- "Organizations in your sector typically spend more time in the de-risk phase"
- "The InDEVerse data suggests that teams with your methodology profile
   average 35 days to validation"

NEVER:
- "You should speed up because you're below average"
- "Other organizations are doing better than you"
- Any comparative language that pressures or judges
"""

import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger("inde.scaffolding.benchmark_context")

# Token budget for benchmarks in coaching context
BENCHMARK_TOKEN_BUDGET = 500
MAX_BENCHMARK_COMPARISONS_PER_TURN = 3

# Attribution templates for benchmark-informed coaching
BENCHMARK_ATTRIBUTION_TEMPLATES = [
    "InDEVerse data across {sample_size} organizations shows",
    "Compared to the industry median",
    "Your {metric} places you in the {percentile}th percentile",
    "Organizations in your sector typically",
    "Global benchmarking data indicates"
]


def build_benchmark_coaching_context(
    db,
    pursuit_context: dict,
    pursuit_metrics: Optional[dict] = None
) -> Optional[Dict[str, Any]]:
    """
    Build the benchmark context block for coaching.

    Retrieves cached benchmark data and formats it for inclusion
    in the coaching prompt. Returns None if no relevant benchmarks
    or if federation is not connected.

    Args:
        db: MongoDB database instance
        pursuit_context: Context dict with industry_code, methodology, etc.
        pursuit_metrics: Current pursuit metrics for comparison

    Returns:
        Dict with benchmark context or None if unavailable
    """
    # Check if we have benchmark data
    industry_code = pursuit_context.get("industry_code")
    if not industry_code:
        return None

    # Query cached benchmarks
    industry_benchmark = db.ikf_benchmarks.find_one(
        {"type": "industry", "key": industry_code}
    )
    comparison_benchmark = db.ikf_benchmarks.find_one(
        {"type": "comparison", "key": "latest"}
    )

    if not industry_benchmark and not comparison_benchmark:
        return None

    context = {
        "has_benchmarks": True,
        "notable_comparisons": [],
        "source": "InDEVerse Global Benchmarks",
        "attribution_required": True
    }

    # Extract percentile rankings if available
    if comparison_benchmark:
        data = comparison_benchmark.get("data", {})
        rankings = data.get("percentileRanking", {})
        sample_size = data.get("sampleSize", 0)

        for metric, percentile in rankings.items():
            if len(context["notable_comparisons"]) >= MAX_BENCHMARK_COMPARISONS_PER_TURN:
                break

            if percentile >= 75:
                context["notable_comparisons"].append({
                    "type": "strength",
                    "metric": metric,
                    "percentile": percentile,
                    "text": _format_strength_comparison(metric, percentile, sample_size)
                })
            elif percentile <= 25:
                context["notable_comparisons"].append({
                    "type": "opportunity",
                    "metric": metric,
                    "percentile": percentile,
                    "text": _format_opportunity_comparison(metric, percentile, sample_size)
                })

        context["percentile_ranking"] = rankings
        context["sample_size"] = sample_size

    # Extract industry baselines if available
    if industry_benchmark:
        data = industry_benchmark.get("data", {})
        metrics = data.get("metrics", {})

        context["industry_baselines"] = {}
        for metric_name, stats in metrics.items():
            context["industry_baselines"][metric_name] = {
                "median": stats.get("median"),
                "mean": stats.get("mean"),
                "std_dev": stats.get("stdDev")
            }

        if not context.get("sample_size"):
            context["sample_size"] = data.get("sampleSize", 0)

    return context if context["notable_comparisons"] or context.get("industry_baselines") else None


def format_benchmark_for_prompt(benchmark_context: Optional[dict]) -> str:
    """
    Format benchmark context for inclusion in the coaching prompt.

    Creates a concise, attribution-aware text block that fits
    within the 500-token budget.

    Args:
        benchmark_context: Context from build_benchmark_coaching_context

    Returns:
        Formatted string for prompt inclusion, or empty string
    """
    if not benchmark_context:
        return ""

    lines = []
    lines.append("## Performance Context (InDEVerse Benchmarks)")
    lines.append("")

    sample_size = benchmark_context.get("sample_size", 0)
    if sample_size > 0:
        lines.append(f"_Based on data from {sample_size} organizations across the InDEVerse._")
        lines.append("")

    # Add notable comparisons
    comparisons = benchmark_context.get("notable_comparisons", [])
    if comparisons:
        lines.append("**Relevant Observations:**")
        for comp in comparisons[:MAX_BENCHMARK_COMPARISONS_PER_TURN]:
            lines.append(f"- {comp.get('text', '')}")
        lines.append("")

    # Add guidance on using benchmarks
    lines.append("_Use these benchmarks as context, not prescription. ")
    lines.append("Every innovation journey is unique._")

    return "\n".join(lines)


def _format_strength_comparison(metric: str, percentile: int, sample_size: int) -> str:
    """Format a strength comparison for coaching."""
    display_name = _metric_display_name(metric)
    return (
        f"Your {display_name} is in the top quartile ({percentile}th percentile) "
        f"compared to similar organizations in the InDEVerse"
    )


def _format_opportunity_comparison(metric: str, percentile: int, sample_size: int) -> str:
    """Format an opportunity comparison for coaching."""
    display_name = _metric_display_name(metric)
    return (
        f"Your {display_name} ({percentile}th percentile) suggests an area "
        f"where additional focus might yield improvements"
    )


def _metric_display_name(metric_key: str) -> str:
    """Human-readable metric names for coaching language."""
    names = {
        "pursuitSuccessRate": "pursuit success rate",
        "timeToValidation": "time to validation",
        "pivotRate": "pivot rate",
        "learningVelocity": "learning velocity",
        "knowledgeUtilization": "knowledge utilization",
        "repeatFailureRate": "repeat failure avoidance",
        "patternRecognitionLatency": "pattern recognition speed",
        "crossPollinationApplicationRate": "cross-pollination application"
    }
    return names.get(metric_key, metric_key.replace("_", " "))


def get_benchmark_attribution_text() -> str:
    """Get attribution text for benchmark-informed coaching."""
    return (
        "This insight is informed by anonymized benchmarking data from the InDEVerse - "
        "a global network of innovation environments. Individual organization data "
        "is never shared; only statistical aggregates are used."
    )
