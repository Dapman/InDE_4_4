"""
Benchmark Data Models - Anonymized Performance Comparisons

All benchmarking data represents anonymized aggregates across
the InDEVerse. Individual organization identification is
architecturally impossible - the IKF computes these statistics
across all participants and returns only distributions.

Available metrics (from IKF-IML Spec Section 6.4):
- pursuitSuccessRate
- timeToValidation
- pivotRate
- learningVelocity
- knowledgeUtilization
- repeatFailureRate
- patternRecognitionLatency
- crossPollinationApplicationRate
"""

from enum import Enum
from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class BenchmarkTimeframe(str, Enum):
    """Timeframe for benchmark comparisons."""
    QUARTER = "QUARTER"
    YEAR = "YEAR"
    ALL_TIME = "ALL_TIME"


class OrganizationSize(str, Enum):
    """Organization size tiers for benchmark segmentation."""
    SMALL = "SMALL"          # < 50 innovators
    MEDIUM = "MEDIUM"        # 50-200 innovators
    LARGE = "LARGE"          # 200-1000 innovators
    ENTERPRISE = "ENTERPRISE"  # 1000+ innovators


class BenchmarkMetricType(str, Enum):
    """Types of benchmark metrics available from IKF."""
    PURSUIT_SUCCESS_RATE = "pursuitSuccessRate"
    TIME_TO_VALIDATION = "timeToValidation"
    PIVOT_RATE = "pivotRate"
    LEARNING_VELOCITY = "learningVelocity"
    KNOWLEDGE_UTILIZATION = "knowledgeUtilization"
    REPEAT_FAILURE_RATE = "repeatFailureRate"
    PATTERN_RECOGNITION_LATENCY = "patternRecognitionLatency"
    CROSS_POLLINATION_APPLICATION_RATE = "crossPollinationApplicationRate"


class MetricStatistics(BaseModel):
    """Statistical summary for a single metric."""
    mean: float
    median: float
    std_dev: float = Field(alias="stdDev")
    percentile_25: float = Field(alias="p25")
    percentile_75: float = Field(alias="p75")
    min_value: Optional[float] = Field(None, alias="min")
    max_value: Optional[float] = Field(None, alias="max")

    class Config:
        populate_by_name = True


class IndustryBenchmark(BaseModel):
    """Benchmark data for a specific industry (NAICS code)."""
    naics_code: str
    industry_name: str
    metrics: Dict[str, MetricStatistics]
    sample_size: int
    confidence_interval: float = 0.95
    timeframe: BenchmarkTimeframe
    last_updated: datetime


class MethodologyBenchmark(BaseModel):
    """Benchmark data for a specific innovation methodology."""
    archetype_id: str
    archetype_name: str
    completion_rate: float
    avg_time_per_phase: Dict[str, float]  # Phase name -> days
    success_distribution: Dict[str, float]  # Outcome -> percentage
    sample_size: int
    timeframe: BenchmarkTimeframe
    last_updated: datetime


class PercentileRanking(BaseModel):
    """Organization's percentile ranking across metrics."""
    metrics: Dict[str, int]  # Metric name -> percentile (0-100)
    industry_code: str
    organization_size: OrganizationSize
    compared_to_industry: bool = True
    compared_to_global: bool = True
    sample_size: int
    calculated_at: datetime


class BenchmarkTrend(BaseModel):
    """Historical trend data for benchmark metrics."""
    metric_name: str
    data_points: List[Dict[str, Any]]  # [{timestamp, value}, ...]
    trend_direction: str  # "improving", "declining", "stable"
    change_percentage: float


class BenchmarkComparisonRequest(BaseModel):
    """Request payload for benchmark comparison."""
    metrics: Dict[str, float]
    industry_code: str = Field(alias="industryCode")
    organization_size: str = Field(alias="organizationSize")
    timeframe: str = "YEAR"

    class Config:
        populate_by_name = True


class BenchmarkComparisonResponse(BaseModel):
    """Response from benchmark comparison API."""
    industry_baseline: Dict[str, MetricStatistics] = Field(alias="industryBaseline")
    global_baseline: Dict[str, MetricStatistics] = Field(alias="globalBaseline")
    percentile_ranking: Dict[str, int] = Field(alias="percentileRanking")
    sample_size: int = Field(alias="sampleSize")
    confidence_interval: float = Field(alias="confidenceInterval")

    class Config:
        populate_by_name = True
