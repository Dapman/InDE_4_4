"""
Global Benchmarking Engine - Anonymized Comparative Analytics

Retrieves anonymized benchmark data from the IKF and caches it
locally for dashboard display and coaching context injection.

Architecture:
1. Periodic sync: Benchmarks refresh on the federation sync interval
2. Local cache: MongoDB collection `ikf_benchmarks` stores latest data
3. Dashboard integration: Org Portfolio Dashboard queries local cache
4. Coaching integration: ODICM references cached benchmarks when relevant

Privacy guarantee: The IKF returns ONLY statistical aggregates.
No individual organization data is ever transmitted.

IKF Endpoints consumed:
- GET /benchmark/industry/{naicsCode}
- GET /benchmark/methodology/{archetypeId}
- POST /benchmark/compare
- GET /benchmark/trends
"""

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any

logger = logging.getLogger("inde.ikf.benchmark_engine")

BENCHMARK_SYNC_INTERVAL = int(os.environ.get("BENCHMARK_SYNC_INTERVAL", "3600"))  # Default 1 hour
BENCHMARK_STALE_THRESHOLD = int(os.environ.get("BENCHMARK_STALE_THRESHOLD", "86400"))  # 24 hours


class BenchmarkEngine:
    """
    Global Benchmarking Engine for anonymized comparative analytics.

    Retrieves benchmark data from IKF and caches locally for:
    - Org Portfolio Dashboard display
    - Coaching context injection
    - Enterprise leader analytics
    """

    def __init__(self, db, connection_manager, circuit_breaker,
                 http_client, config):
        """
        Initialize the Benchmark Engine.

        Args:
            db: MongoDB database instance
            connection_manager: Federation connection manager
            circuit_breaker: Circuit breaker for resilience
            http_client: HTTP client for IKF requests
            config: Configuration with IKF base URL, org_id, etc.
        """
        self._db = db
        self._conn_manager = connection_manager
        self._breaker = circuit_breaker
        self._http_client = http_client
        self._config = config
        self._sync_task: Optional[asyncio.Task] = None
        self._running = False

    def start_sync(self):
        """Start periodic benchmark sync. Only when federation_mode == LIVE."""
        if self._sync_task and not self._sync_task.done():
            return
        self._running = True
        self._sync_task = asyncio.create_task(self._sync_loop())
        logger.info("Benchmark sync started")

    def stop_sync(self):
        """Stop periodic benchmark sync."""
        self._running = False
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
        logger.info("Benchmark sync stopped")

    async def _sync_loop(self):
        """
        Periodically fetch benchmark data from IKF.

        Fetches:
        1. Industry benchmarks for org's NAICS codes
        2. Methodology benchmarks for org's active archetypes
        3. Org's percentile ranking (anonymized comparison)
        """
        while self._running:
            try:
                if self._conn_manager.is_connected:
                    await self._refresh_benchmarks()
                await asyncio.sleep(BENCHMARK_SYNC_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Benchmark sync error: {e}")
                await asyncio.sleep(BENCHMARK_SYNC_INTERVAL)

    async def _refresh_benchmarks(self):
        """
        Fetch all relevant benchmark data from IKF.

        Step 1: Get org's industry codes and active methodologies
        Step 2: Fetch industry benchmarks for each NAICS code
        Step 3: Fetch methodology benchmarks for each archetype
        Step 4: Submit anonymized org metrics for percentile comparison
        Step 5: Cache results in ikf_benchmarks collection
        """
        org_config = await self._get_org_federation_config()
        if not org_config:
            logger.warning("No org federation config found, skipping benchmark refresh")
            return

        # Industry benchmarks
        for naics_code in org_config.get("industry_codes", []):
            await self._fetch_industry_benchmark(naics_code)

        # Methodology benchmarks
        for archetype_id in await self._get_active_archetypes():
            await self._fetch_methodology_benchmark(archetype_id)

        # Percentile comparison (anonymized org metrics submitted)
        await self._fetch_percentile_ranking(org_config)

        # Trend data
        await self._fetch_trend_data(org_config)

        logger.info("Benchmark refresh complete")

    async def _get_org_federation_config(self) -> Optional[Dict]:
        """Get the organization's federation configuration."""
        fed_state = self._db.ikf_federation_state.find_one({"type": "registration"})
        if not fed_state:
            return None

        return {
            "org_id": fed_state.get("org_id"),
            "industry_codes": fed_state.get("industry_codes", []),
            "primary_naics": fed_state.get("primary_naics"),
            "size_tier": fed_state.get("size_tier", "MEDIUM")
        }

    async def _get_active_archetypes(self) -> List[str]:
        """Get list of methodology archetypes actively used by the org."""
        # Query distinct archetypes from active pursuits
        archetypes = self._db.pursuits.distinct(
            "methodology_archetype",
            {"is_practice": {"$ne": True}, "state.status": {"$nin": ["TERMINATED", "COMPLETED"]}}
        )
        return [a for a in archetypes if a]

    async def _fetch_industry_benchmark(self, naics_code: str):
        """
        GET /benchmark/industry/{naicsCode}

        Returns: industry average, median, std deviation for all
        benchmark metrics. Sample size and confidence interval.
        """
        try:
            ikf_base_url = self._get_ikf_base_url()
            response = await self._breaker.call(
                self._http_client.get,
                f"{ikf_base_url}/v1/benchmark/industry/{naics_code}",
                headers=self._create_outbound_headers()
            )
            if response.status_code == 200:
                data = response.json()
                await self._cache_benchmark("industry", naics_code, data)
                logger.debug(f"Industry benchmark cached for {naics_code}")
        except Exception as e:
            logger.warning(f"Industry benchmark fetch failed for {naics_code}: {e}")

    async def _fetch_methodology_benchmark(self, archetype_id: str):
        """
        GET /benchmark/methodology/{archetypeId}

        Returns: methodology effectiveness statistics across InDEVerse.
        Completion rates, average time-per-phase, success distributions.
        """
        try:
            ikf_base_url = self._get_ikf_base_url()
            response = await self._breaker.call(
                self._http_client.get,
                f"{ikf_base_url}/v1/benchmark/methodology/{archetype_id}",
                headers=self._create_outbound_headers()
            )
            if response.status_code == 200:
                data = response.json()
                await self._cache_benchmark("methodology", archetype_id, data)
                logger.debug(f"Methodology benchmark cached for {archetype_id}")
        except Exception as e:
            logger.warning(f"Methodology benchmark fetch failed for {archetype_id}: {e}")

    async def _fetch_percentile_ranking(self, org_config: dict):
        """
        POST /benchmark/compare

        Submits ANONYMIZED org metrics for comparison against global baselines.
        The IKF NEVER receives raw org data - only aggregated metrics
        that cannot identify the organization.

        Request: { metrics: {pursuitSuccessRate, timeToValidation, ...},
                   industryCode, organizationSize, timeframe }
        Response: { industryBaseline, globalBaseline, percentileRanking,
                    sampleSize, confidenceInterval }
        """
        try:
            # Compute anonymized org metrics
            org_metrics = await self._compute_org_metrics()
            if not org_metrics:
                logger.debug("No org metrics available for percentile ranking")
                return

            payload = {
                "metrics": org_metrics,
                "industryCode": org_config.get("primary_naics"),
                "organizationSize": org_config.get("size_tier", "MEDIUM"),
                "timeframe": "YEAR"
            }

            ikf_base_url = self._get_ikf_base_url()
            response = await self._breaker.call(
                self._http_client.post,
                f"{ikf_base_url}/v1/benchmark/compare",
                json=payload,
                headers=self._create_outbound_headers()
            )
            if response.status_code == 200:
                data = response.json()
                await self._cache_benchmark("comparison", "latest", data)
                logger.debug("Percentile ranking cached")
        except Exception as e:
            logger.warning(f"Percentile ranking fetch failed: {e}")

    async def _fetch_trend_data(self, org_config: dict):
        """
        GET /benchmark/trends

        Retrieves historical trend data for benchmark metrics.
        Shows how industry and global baselines have evolved.
        """
        try:
            params = {"industryCode": org_config.get("primary_naics")}
            ikf_base_url = self._get_ikf_base_url()
            response = await self._breaker.call(
                self._http_client.get,
                f"{ikf_base_url}/v1/benchmark/trends",
                params=params,
                headers=self._create_outbound_headers()
            )
            if response.status_code == 200:
                data = response.json()
                await self._cache_benchmark("trends", "latest", data)
                logger.debug("Trend data cached")
        except Exception as e:
            logger.warning(f"Trend data fetch failed: {e}")

    async def _compute_org_metrics(self) -> Optional[Dict[str, float]]:
        """
        Compute anonymized organization-level metrics for benchmarking.

        These metrics are aggregates that cannot identify individuals.
        They represent the organization's collective innovation performance.

        PRIVACY: No innovator names, IDs, or individual scores.
        Only statistical aggregates over the org's pursuit portfolio.
        """
        pursuits = list(self._db.pursuits.find({
            "is_practice": {"$ne": True}
        }))

        if not pursuits:
            return None

        total = len(pursuits)
        successful = sum(1 for p in pursuits
                        if p.get("state", {}).get("status") == "COMPLETED.SUCCESSFUL")
        pivoted = sum(1 for p in pursuits
                     if p.get("state", {}).get("status") == "TERMINATED.PIVOTED")

        # Compute aggregate metrics matching IKF benchmark metric names
        return {
            "pursuitSuccessRate": successful / total if total > 0 else 0,
            "pivotRate": pivoted / total if total > 0 else 0,
            "timeToValidation": await self._avg_time_to_validation(pursuits),
            "learningVelocity": await self._avg_learning_velocity(),
            "knowledgeUtilization": await self._avg_knowledge_utilization(pursuits),
            "repeatFailureRate": await self._compute_repeat_failure_rate(pursuits),
            "patternRecognitionLatency": await self._avg_pattern_recognition_latency(),
            "crossPollinationApplicationRate": await self._cross_pollination_rate()
        }

    async def _avg_time_to_validation(self, pursuits: List[dict]) -> float:
        """Average days to reach validation milestone."""
        times = []
        for p in pursuits:
            created = p.get("created_at")
            validated = p.get("validation_reached_at")
            if created and validated:
                delta = (validated - created).days
                times.append(delta)
        return sum(times) / len(times) if times else 0

    async def _avg_learning_velocity(self) -> float:
        """Average learning velocity across all pursuits."""
        # Query from pursuit health metrics if available
        metrics = list(self._db.pursuit_health_metrics.find(
            {"velocity": {"$exists": True}},
            {"velocity": 1}
        ).limit(100))
        velocities = [m.get("velocity", 0) for m in metrics]
        return sum(velocities) / len(velocities) if velocities else 0

    async def _avg_knowledge_utilization(self, pursuits: List[dict]) -> float:
        """Percentage of patterns that are applied vs received."""
        total_received = self._db.ikf_federation_patterns.count_documents({"status": "INTEGRATED"})
        total_applied = self._db.ikf_federation_patterns.count_documents({
            "status": "INTEGRATED",
            "application_count": {"$gt": 0}
        })
        return total_applied / total_received if total_received > 0 else 0

    async def _compute_repeat_failure_rate(self, pursuits: List[dict]) -> float:
        """Rate of pursuits failing for similar reasons to previous failures."""
        # Simplified: count pursuits with repeat failure markers
        repeat_failures = sum(1 for p in pursuits
                             if p.get("state", {}).get("repeat_failure_flag"))
        total_failed = sum(1 for p in pursuits
                          if "FAILED" in p.get("state", {}).get("status", ""))
        return repeat_failures / total_failed if total_failed > 0 else 0

    async def _avg_pattern_recognition_latency(self) -> float:
        """Average time from pattern availability to application."""
        # Query pattern application events
        events = list(self._db.ikf_federation_patterns.find(
            {"first_applied_at": {"$exists": True}},
            {"imported_at": 1, "first_applied_at": 1}
        ).limit(100))

        latencies = []
        for e in events:
            imported = e.get("imported_at")
            applied = e.get("first_applied_at")
            if imported and applied:
                delta = (applied - imported).days
                latencies.append(delta)
        return sum(latencies) / len(latencies) if latencies else 0

    async def _cross_pollination_rate(self) -> float:
        """Rate of cross-pollination events vs total pattern applications."""
        total_applications = self._db.ikf_federation_patterns.aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$application_count"}}}
        ])
        total_list = list(total_applications)
        total = total_list[0]["total"] if total_list else 0

        cross_pollination = self._db.ikf_cross_pollination_events.count_documents({"confirmed": True})
        return cross_pollination / total if total > 0 else 0

    async def _cache_benchmark(self, benchmark_type: str, key: str, data: dict):
        """Cache benchmark data locally in ikf_benchmarks collection."""
        self._db.ikf_benchmarks.update_one(
            {"type": benchmark_type, "key": key},
            {"$set": {
                "type": benchmark_type,
                "key": key,
                "data": data,
                "fetched_at": datetime.now(timezone.utc),
                "source": "ikf_federation"
            }},
            upsert=True
        )

    def _get_ikf_base_url(self) -> str:
        """Get the IKF base URL from config or environment."""
        if self._config and hasattr(self._config, 'ikf_base_url'):
            return self._config.ikf_base_url
        return os.environ.get("IKF_REMOTE_NODE_URL", "http://localhost:8081/ikf-hub")

    def _create_outbound_headers(self) -> dict:
        """Create headers for outbound IKF requests."""
        if self._config and hasattr(self._config, 'create_outbound_headers'):
            return self._config.create_outbound_headers()
        return {"Content-Type": "application/json"}

    # =========================================================================
    # Public Query Methods
    # =========================================================================

    async def get_industry_benchmark(self, naics_code: str) -> Optional[dict]:
        """Retrieve cached industry benchmark for dashboard display."""
        result = self._db.ikf_benchmarks.find_one(
            {"type": "industry", "key": naics_code}
        )
        return result.get("data") if result else None

    async def get_methodology_benchmark(self, archetype_id: str) -> Optional[dict]:
        """Retrieve cached methodology benchmark for dashboard display."""
        result = self._db.ikf_benchmarks.find_one(
            {"type": "methodology", "key": archetype_id}
        )
        return result.get("data") if result else None

    async def get_percentile_ranking(self) -> Optional[dict]:
        """Retrieve cached percentile ranking for dashboard display."""
        result = self._db.ikf_benchmarks.find_one(
            {"type": "comparison", "key": "latest"}
        )
        return result.get("data") if result else None

    async def get_trends(self) -> Optional[dict]:
        """Retrieve cached trend data for dashboard display."""
        result = self._db.ikf_benchmarks.find_one(
            {"type": "trends", "key": "latest"}
        )
        return result.get("data") if result else None

    async def get_all_benchmarks(self) -> dict:
        """Retrieve all cached benchmark data for full dashboard."""
        org_config = await self._get_org_federation_config()

        result = {
            "industry": None,
            "methodology": [],
            "comparison": None,
            "trends": None,
            "fetched_at": None,
            "stale": True,
            "federation_status": "DISCONNECTED"
        }

        if self._conn_manager.is_connected:
            result["federation_status"] = "CONNECTED"
        elif os.environ.get("IKF_FEDERATION_MODE") == "simulation":
            result["federation_status"] = "SIMULATION"

        # Industry benchmark
        if org_config and org_config.get("primary_naics"):
            industry = self._db.ikf_benchmarks.find_one(
                {"type": "industry", "key": org_config["primary_naics"]}
            )
            if industry:
                result["industry"] = industry.get("data")
                result["fetched_at"] = industry.get("fetched_at")

        # Methodology benchmarks
        archetypes = await self._get_active_archetypes()
        for arch in archetypes:
            meth = self._db.ikf_benchmarks.find_one(
                {"type": "methodology", "key": arch}
            )
            if meth:
                result["methodology"].append({
                    "archetype_id": arch,
                    "data": meth.get("data")
                })

        # Comparison
        comparison = self._db.ikf_benchmarks.find_one(
            {"type": "comparison", "key": "latest"}
        )
        if comparison:
            result["comparison"] = comparison.get("data")
            if not result["fetched_at"]:
                result["fetched_at"] = comparison.get("fetched_at")

        # Trends
        trends = self._db.ikf_benchmarks.find_one(
            {"type": "trends", "key": "latest"}
        )
        if trends:
            result["trends"] = trends.get("data")

        # Check staleness
        if result["fetched_at"]:
            age = (datetime.now(timezone.utc) - result["fetched_at"]).total_seconds()
            result["stale"] = age > BENCHMARK_STALE_THRESHOLD

        return result

    async def get_benchmark_for_coaching(self, industry_code: str,
                                          pursuit_metrics: dict) -> Optional[dict]:
        """
        Get benchmark context for coaching injection.

        Returns a compact summary suitable for the 500-token
        benchmarking budget in the coaching context.

        Example output:
        {
            "velocity_percentile": 72,
            "industry_median_velocity": 0.65,
            "success_rate_percentile": 58,
            "notable_comparisons": [
                "Your pursuit velocity is in the top quartile for healthcare",
                "Organizations in your sector typically spend 40% more time in de-risk"
            ]
        }
        """
        comparison = await self.get_percentile_ranking()
        industry = await self.get_industry_benchmark(industry_code)

        if not comparison and not industry:
            return None

        return self._format_coaching_context(comparison, industry, pursuit_metrics)

    def _format_coaching_context(self, comparison: Optional[dict],
                                  industry: Optional[dict],
                                  pursuit_metrics: dict) -> Optional[dict]:
        """Format benchmark data for coaching context injection."""
        context = {
            "notable_comparisons": [],
            "source": "InDEVerse Global Benchmarks"
        }

        if comparison and comparison.get("percentileRanking"):
            ranking = comparison["percentileRanking"]
            for metric, percentile in ranking.items():
                if percentile >= 75:
                    context["notable_comparisons"].append(
                        f"Top quartile in {self._metric_display_name(metric)}"
                    )
                elif percentile <= 25:
                    context["notable_comparisons"].append(
                        f"Below median in {self._metric_display_name(metric)} - "
                        f"opportunity for improvement"
                    )
            context["percentile_ranking"] = ranking

        if industry and industry.get("metrics"):
            context["industry_baselines"] = {
                k: {"median": v.get("median"), "stddev": v.get("stdDev")}
                for k, v in industry["metrics"].items()
            }
            context["sample_size"] = industry.get("sampleSize", 0)

        return context if context["notable_comparisons"] else None

    def is_benchmark_stale(self) -> bool:
        """Check if benchmark data is older than the stale threshold."""
        latest = self._db.ikf_benchmarks.find_one(
            {},
            sort=[("fetched_at", -1)]
        )
        if not latest or not latest.get("fetched_at"):
            return True

        age = (datetime.now(timezone.utc) - latest["fetched_at"]).total_seconds()
        return age > BENCHMARK_STALE_THRESHOLD

    @staticmethod
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
        return names.get(metric_key, metric_key)
