"""
InDE EMS v3.7.2 - Inference Data Preparation

Transforms raw process_observations documents into structured pursuit
sequences suitable for pattern inference algorithms.

Key responsibilities:
- Load observations for an innovator across multiple ad-hoc pursuits
- Filter by signal weight and external influence
- Build per-pursuit activity sequences (ordered lists of observation types)
- Calculate temporal features (inter-event gaps, phase durations)
- Normalize sequences for cross-pursuit comparison
"""

import logging
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from core.database import db

logger = logging.getLogger("inde.ems.inference_data_prep")


class InferenceDataPrep:
    """
    Prepares raw observation data for pattern inference.

    Transforms process_observations into structured sequences that
    the PatternInferenceEngine can analyze.
    """

    def __init__(self, process_observer=None):
        """
        Args:
            process_observer: Optional ProcessObserver instance for data access.
                             If None, uses database directly.
        """
        self.observer = process_observer

    def prepare_innovator_data(
        self,
        innovator_id: str,
        min_weight: float = 0.0,
        exclude_coaching: bool = True
    ) -> Dict[str, Any]:
        """
        Prepare all observation data for an innovator's ad-hoc pursuits.

        Args:
            innovator_id: The innovator whose data to prepare
            min_weight: Minimum signal weight threshold (0.0-1.0)
            exclude_coaching: If True, exclude COACHING_INTERACTION observations

        Returns:
            {
                "innovator_id": str,
                "pursuit_count": int,
                "pursuits": [
                    {
                        "pursuit_id": str,
                        "sequence": [str],           # Ordered observation types
                        "detailed_sequence": [dict], # Full observation details
                        "temporal_features": dict,   # Timing analysis
                        "outcome": str,              # Terminal state if completed
                        "duration_days": float,
                    }
                ],
                "global_stats": {
                    "total_observations": int,
                    "avg_observations_per_pursuit": float,
                    "observation_type_distribution": dict,
                    "avg_pursuit_duration_days": float,
                }
            }
        """
        # Get all completed ad-hoc pursuits for this innovator
        adhoc_pursuits = db.get_synthesis_eligible_pursuits(innovator_id)

        pursuits_data = []
        total_observations = 0
        type_distribution = Counter()
        total_duration = 0.0

        for pursuit in adhoc_pursuits:
            pursuit_id = pursuit.get("pursuit_id", str(pursuit.get("_id", "")))

            # Get observations for this pursuit
            observations = self._get_pursuit_observations(
                pursuit_id, min_weight, exclude_coaching
            )

            if not observations:
                continue

            # Build activity sequence
            sequence = self.build_activity_sequence(observations)
            detailed_sequence = self._build_detailed_sequence(observations)

            # Calculate temporal features
            temporal_features = self.calculate_temporal_features(observations)

            # Get outcome data
            outcome_data = self.get_outcome_data(pursuit_id)

            # Calculate duration
            duration_days = temporal_features.get("total_duration_days", 0)
            total_duration += duration_days

            # Update statistics
            total_observations += len(observations)
            for obs in observations:
                type_distribution[obs.get("observation_type", "UNKNOWN")] += 1

            pursuits_data.append({
                "pursuit_id": pursuit_id,
                "pursuit_name": pursuit.get("name", "Untitled"),
                "sequence": sequence,
                "detailed_sequence": detailed_sequence,
                "temporal_features": temporal_features,
                "outcome": outcome_data.get("terminal_state", "unknown"),
                "duration_days": duration_days,
                "observation_count": len(observations),
            })

        pursuit_count = len(pursuits_data)

        return {
            "innovator_id": innovator_id,
            "pursuit_count": pursuit_count,
            "pursuits": pursuits_data,
            "global_stats": {
                "total_observations": total_observations,
                "avg_observations_per_pursuit": round(
                    total_observations / pursuit_count, 1
                ) if pursuit_count > 0 else 0,
                "observation_type_distribution": dict(type_distribution),
                "avg_pursuit_duration_days": round(
                    total_duration / pursuit_count, 1
                ) if pursuit_count > 0 else 0,
            }
        }

    def _get_pursuit_observations(
        self,
        pursuit_id: str,
        min_weight: float,
        exclude_coaching: bool
    ) -> List[Dict]:
        """Get filtered observations for a pursuit."""
        try:
            # Query observations from database
            query = {"pursuit_id": pursuit_id}

            if min_weight > 0:
                query["signal_weight"] = {"$gte": min_weight}

            if exclude_coaching:
                query["observation_type"] = {"$ne": "COACHING_INTERACTION"}

            cursor = db.db.process_observations.find(
                query,
                sort=[("sequence_number", 1)]
            )

            observations = list(cursor)

            # Parse timestamps if they're strings
            for obs in observations:
                if isinstance(obs.get("timestamp"), str):
                    try:
                        obs["timestamp"] = datetime.fromisoformat(
                            obs["timestamp"].replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        obs["timestamp"] = datetime.now(timezone.utc)

            return observations

        except Exception as e:
            logger.warning(f"Error getting observations for {pursuit_id}: {e}")
            return []

    def build_activity_sequence(
        self,
        observations: List[Dict],
        enrich: bool = True
    ) -> List[str]:
        """
        Build an ordered sequence of observation types from raw observations.

        This is the primary input format for sequence mining algorithms.
        Each observation becomes a symbol in the sequence.

        Args:
            observations: List of observation documents
            enrich: If True, add detail context to symbols
                   e.g., "ARTIFACT_CREATED:vision" instead of "ARTIFACT_CREATED"

        Returns:
            Ordered list of activity symbols
        """
        sequence = []

        for obs in observations:
            obs_type = obs.get("observation_type", "UNKNOWN")

            if enrich:
                details = obs.get("details", {})

                # Enrich based on observation type
                if obs_type == "ARTIFACT_CREATED":
                    detail = details.get("artifact_type", "")
                    symbol = f"{obs_type}:{detail}" if detail else obs_type
                elif obs_type == "TOOL_INVOKED":
                    detail = details.get("tool_name", "")
                    symbol = f"{obs_type}:{detail}" if detail else obs_type
                elif obs_type == "DECISION_MADE":
                    detail = details.get("decision_type", "")
                    symbol = f"{obs_type}:{detail}" if detail else obs_type
                elif obs_type == "ELEMENT_CAPTURED":
                    detail = details.get("element_type", "")
                    symbol = f"{obs_type}:{detail}" if detail else obs_type
                elif obs_type == "RISK_VALIDATION":
                    detail = details.get("validation_type", "")
                    symbol = f"{obs_type}:{detail}" if detail else obs_type
                else:
                    symbol = obs_type
            else:
                symbol = obs_type

            sequence.append(symbol)

        return sequence

    def _build_detailed_sequence(self, observations: List[Dict]) -> List[Dict]:
        """Build a detailed sequence with full observation data."""
        detailed = []

        for obs in observations:
            detailed.append({
                "observation_type": obs.get("observation_type", "UNKNOWN"),
                "timestamp": obs.get("timestamp"),
                "sequence_number": obs.get("sequence_number", 0),
                "details": obs.get("details", {}),
                "context": obs.get("context", {}),
                "signal_weight": obs.get("signal_weight", 0.5),
                "is_external_influence": obs.get("is_external_influence", False),
            })

        return detailed

    def calculate_temporal_features(self, observations: List[Dict]) -> Dict:
        """
        Extract timing-related features from an observation sequence.

        Returns:
            {
                "total_duration_days": float,
                "phase_durations": {str: float},  # Time per Universal State
                "inter_event_gaps": [float],      # Hours between events
                "avg_gap_hours": float,
                "activity_bursts": [...],         # Periods of high activity
                "dormant_periods": [...],         # Gaps > 24 hours
            }
        """
        if not observations:
            return {
                "total_duration_days": 0,
                "phase_durations": {},
                "inter_event_gaps": [],
                "avg_gap_hours": 0,
                "activity_bursts": [],
                "dormant_periods": [],
            }

        # Sort by timestamp
        sorted_obs = sorted(
            observations,
            key=lambda x: x.get("timestamp") or datetime.min.replace(tzinfo=timezone.utc)
        )

        # Calculate total duration
        first_ts = sorted_obs[0].get("timestamp")
        last_ts = sorted_obs[-1].get("timestamp")

        if first_ts and last_ts:
            total_duration = (last_ts - first_ts).total_seconds() / 86400  # Days
        else:
            total_duration = 0

        # Calculate inter-event gaps
        inter_event_gaps = []
        dormant_periods = []

        for i in range(1, len(sorted_obs)):
            prev_ts = sorted_obs[i-1].get("timestamp")
            curr_ts = sorted_obs[i].get("timestamp")

            if prev_ts and curr_ts:
                gap_hours = (curr_ts - prev_ts).total_seconds() / 3600
                inter_event_gaps.append(gap_hours)

                if gap_hours > 24:
                    dormant_periods.append({
                        "start": prev_ts.isoformat() if prev_ts else "",
                        "end": curr_ts.isoformat() if curr_ts else "",
                        "duration_hours": round(gap_hours, 1),
                    })

        avg_gap = sum(inter_event_gaps) / len(inter_event_gaps) if inter_event_gaps else 0

        # Calculate phase durations (simplified - by context.pursuit_phase)
        phase_times = {}
        for obs in sorted_obs:
            phase = obs.get("context", {}).get("pursuit_phase", "UNKNOWN")
            if phase not in phase_times:
                phase_times[phase] = 0
            # Each observation counts as a unit of activity
            phase_times[phase] += 1

        # Normalize to fractions
        total_obs = len(sorted_obs)
        phase_durations = {
            phase: round(count / total_obs, 2)
            for phase, count in phase_times.items()
        }

        # Detect activity bursts (3+ events within 2 hours)
        activity_bursts = self._detect_activity_bursts(sorted_obs)

        return {
            "total_duration_days": round(total_duration, 1),
            "phase_durations": phase_durations,
            "inter_event_gaps": [round(g, 1) for g in inter_event_gaps],
            "avg_gap_hours": round(avg_gap, 1),
            "activity_bursts": activity_bursts,
            "dormant_periods": dormant_periods,
        }

    def _detect_activity_bursts(self, sorted_obs: List[Dict]) -> List[Dict]:
        """Detect periods of high activity (3+ events within 2 hours)."""
        bursts = []
        i = 0

        while i < len(sorted_obs):
            burst_start = sorted_obs[i].get("timestamp")
            if not burst_start:
                i += 1
                continue

            # Find all events within 2 hours of burst_start
            burst_events = [sorted_obs[i]]
            j = i + 1

            while j < len(sorted_obs):
                curr_ts = sorted_obs[j].get("timestamp")
                if not curr_ts:
                    j += 1
                    continue

                if (curr_ts - burst_start).total_seconds() <= 7200:  # 2 hours
                    burst_events.append(sorted_obs[j])
                    j += 1
                else:
                    break

            if len(burst_events) >= 3:
                bursts.append({
                    "start": burst_start.isoformat(),
                    "end": burst_events[-1].get("timestamp", burst_start).isoformat(),
                    "event_count": len(burst_events),
                })
                i = j  # Skip past this burst
            else:
                i += 1

        return bursts

    def get_outcome_data(self, pursuit_id: str) -> Dict:
        """
        Get the outcome of a completed pursuit for outcome correlation.

        Returns:
            {
                "terminal_state": str,
                "success": bool,
                "maturity_score": float,
                "duration_days": float,
            }
        """
        try:
            pursuit = db.get_pursuit(pursuit_id)
            if not pursuit:
                return {
                    "terminal_state": "unknown",
                    "success": False,
                    "maturity_score": 0.0,
                    "duration_days": 0.0,
                }

            status = pursuit.get("status", "unknown")
            adhoc_meta = pursuit.get("adhoc_metadata", {})

            # Determine success based on status
            success = "COMPLETED" in status.upper() or "SUCCESS" in status.upper()

            # Get maturity score if available
            maturity = pursuit.get("maturity_score", 0.0)

            # Calculate duration
            created = pursuit.get("created_at")
            completed = adhoc_meta.get("observation_ended_at") or pursuit.get("completed_at")

            if created and completed:
                if isinstance(created, str):
                    created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if isinstance(completed, str):
                    completed = datetime.fromisoformat(completed.replace("Z", "+00:00"))
                duration = (completed - created).total_seconds() / 86400
            else:
                duration = 0.0

            return {
                "terminal_state": status,
                "success": success,
                "maturity_score": maturity,
                "duration_days": round(duration, 1),
            }

        except Exception as e:
            logger.warning(f"Error getting outcome for {pursuit_id}: {e}")
            return {
                "terminal_state": "unknown",
                "success": False,
                "maturity_score": 0.0,
                "duration_days": 0.0,
            }

    def get_cross_pursuit_sequences(
        self,
        innovator_id: str,
        enrich: bool = True
    ) -> List[List[str]]:
        """
        Get activity sequences for all ad-hoc pursuits by an innovator.

        Convenience method for sequence mining algorithms.

        Returns:
            List of activity sequences (one per pursuit)
        """
        data = self.prepare_innovator_data(innovator_id)
        return [p["sequence"] for p in data["pursuits"]]


# Singleton instance for module-level access
_data_prep_instance = None


def get_inference_data_prep() -> InferenceDataPrep:
    """Get or create the InferenceDataPrep singleton."""
    global _data_prep_instance
    if _data_prep_instance is None:
        _data_prep_instance = InferenceDataPrep()
    return _data_prep_instance
