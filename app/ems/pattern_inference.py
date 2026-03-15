"""
InDE EMS v3.7.3 - Pattern Inference Engine

Discovers methodology patterns from observed innovator behavior using
four complementary algorithms, then scores confidence in discovered patterns.

Algorithms:
1. Sequence Mining - Find recurring activity patterns across pursuits
2. Phase Clustering - Group observations into methodology phases
3. Transition Inference - Discover phase transition triggers
4. Dependency Mapping - Map tool/artifact dependencies

Confidence Scoring:
- Sample size (n pursuits analyzed)
- Consistency (pattern frequency across pursuits)
- Outcome association (correlation with success)
- Distinctiveness (unique to this innovator vs. existing archetypes)

v3.7.3 Enhancement:
- True archetype-to-archetype similarity comparison (Audit I remediation)
- Multi-dimensional similarity: phase count, activity overlap, ordering, tools, transitions
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Set
from itertools import combinations

from ems.inference_data_prep import InferenceDataPrep, get_inference_data_prep

logger = logging.getLogger("inde.ems.pattern_inference")


class PatternInferenceEngine:
    """
    Discovers emergent methodology patterns from observed behavior.

    Uses multiple inference algorithms to identify recurring patterns,
    then combines results with confidence scoring.
    """

    # Minimum pursuits required for meaningful inference
    MIN_PURSUITS_FOR_INFERENCE = 3

    # Algorithm parameters
    MIN_SEQUENCE_LENGTH = 2
    MAX_SEQUENCE_LENGTH = 5
    MIN_PATTERN_FREQUENCY = 0.4  # Pattern must appear in 40% of pursuits
    MIN_PHASE_SIZE = 2  # Minimum observations per phase
    PHASE_GAP_THRESHOLD_HOURS = 4  # Gap suggesting phase boundary

    def __init__(self, data_prep: Optional[InferenceDataPrep] = None):
        """
        Args:
            data_prep: InferenceDataPrep instance for data access.
                      If None, uses singleton.
        """
        self.data_prep = data_prep or get_inference_data_prep()

    def infer_patterns(
        self,
        innovator_id: str,
        min_weight: float = 0.3
    ) -> Dict[str, Any]:
        """
        Run full pattern inference for an innovator.

        Args:
            innovator_id: The innovator to analyze
            min_weight: Minimum observation weight to include

        Returns:
            {
                "innovator_id": str,
                "inference_timestamp": str,
                "sufficient_data": bool,
                "pursuit_count": int,
                "patterns": {
                    "sequences": [...],      # Recurring activity sequences
                    "phases": [...],         # Identified methodology phases
                    "transitions": [...],    # Phase transition patterns
                    "dependencies": [...],   # Tool/artifact dependencies
                },
                "confidence": {
                    "overall": float,
                    "sample_size_score": float,
                    "consistency_score": float,
                    "outcome_association_score": float,
                    "distinctiveness_score": float,
                    "similar_archetypes": [...],  # v3.7.3: Top similar archetypes
                },
                "synthesis_ready": bool,
            }
        """
        logger.info(f"Starting pattern inference for innovator {innovator_id}")

        # Prepare data
        prepared_data = self.data_prep.prepare_innovator_data(
            innovator_id, min_weight=min_weight
        )

        pursuit_count = prepared_data["pursuit_count"]

        # Check if we have sufficient data
        if pursuit_count < self.MIN_PURSUITS_FOR_INFERENCE:
            logger.info(
                f"Insufficient data for inference: {pursuit_count} pursuits "
                f"(need {self.MIN_PURSUITS_FOR_INFERENCE})"
            )
            return {
                "innovator_id": innovator_id,
                "inference_timestamp": datetime.now(timezone.utc).isoformat(),
                "sufficient_data": False,
                "pursuit_count": pursuit_count,
                "patterns": {
                    "sequences": [],
                    "phases": [],
                    "transitions": [],
                    "dependencies": [],
                },
                "confidence": {
                    "overall": 0.0,
                    "sample_size_score": 0.0,
                    "consistency_score": 0.0,
                    "outcome_association_score": 0.0,
                    "distinctiveness_score": 0.0,
                    "similar_archetypes": [],  # v3.7.3
                },
                "synthesis_ready": False,
            }

        # Run inference algorithms
        sequences = self._mine_sequences(prepared_data)
        phases = self._cluster_into_phases(prepared_data)
        transitions = self._infer_transitions(prepared_data, phases)
        dependencies = self._map_tool_dependencies(prepared_data)

        # Calculate confidence scores
        confidence = self._calculate_confidence(
            prepared_data, sequences, phases, transitions, dependencies
        )

        # Determine if ready for ADL synthesis
        synthesis_ready = (
            confidence["overall"] >= 0.5 and
            len(sequences) >= 2 and
            len(phases) >= 2
        )

        result = {
            "innovator_id": innovator_id,
            "inference_timestamp": datetime.now(timezone.utc).isoformat(),
            "sufficient_data": True,
            "pursuit_count": pursuit_count,
            "patterns": {
                "sequences": sequences,
                "phases": phases,
                "transitions": transitions,
                "dependencies": dependencies,
            },
            "confidence": confidence,
            "synthesis_ready": synthesis_ready,
        }

        logger.info(
            f"Pattern inference complete for {innovator_id}: "
            f"{len(sequences)} sequences, {len(phases)} phases, "
            f"confidence={confidence['overall']:.2f}"
        )

        return result

    def _mine_sequences(self, prepared_data: Dict) -> List[Dict]:
        """
        Algorithm 1: Sequence Mining

        Find recurring activity patterns (n-grams) across pursuits.
        Uses a sliding window approach to extract subsequences,
        then identifies those appearing frequently across pursuits.

        Returns:
            [
                {
                    "sequence": [str],      # The activity sequence
                    "frequency": float,     # Fraction of pursuits containing it
                    "pursuit_count": int,   # Number of pursuits with sequence
                    "avg_position": float,  # Average position in pursuit (0-1)
                    "outcome_correlation": float,  # Correlation with success
                }
            ]
        """
        pursuits = prepared_data["pursuits"]
        if not pursuits:
            return []

        # Extract all n-grams from all pursuits
        ngram_occurrences: Dict[tuple, List[Dict]] = defaultdict(list)

        for pursuit in pursuits:
            sequence = pursuit["sequence"]
            pursuit_id = pursuit["pursuit_id"]
            outcome = pursuit["outcome"]
            success = "COMPLETE" in outcome.upper() or "SUCCESS" in outcome.upper()

            # Extract n-grams of various lengths
            for n in range(self.MIN_SEQUENCE_LENGTH, self.MAX_SEQUENCE_LENGTH + 1):
                for i in range(len(sequence) - n + 1):
                    ngram = tuple(sequence[i:i + n])
                    position = i / max(len(sequence) - 1, 1)  # Normalize to 0-1

                    ngram_occurrences[ngram].append({
                        "pursuit_id": pursuit_id,
                        "position": position,
                        "success": success,
                    })

        # Filter to frequent patterns
        pursuit_count = len(pursuits)
        min_occurrences = int(pursuit_count * self.MIN_PATTERN_FREQUENCY)

        frequent_patterns = []

        for ngram, occurrences in ngram_occurrences.items():
            # Count unique pursuits (not just occurrences)
            unique_pursuits = set(occ["pursuit_id"] for occ in occurrences)
            pattern_pursuit_count = len(unique_pursuits)

            if pattern_pursuit_count >= min_occurrences:
                # Calculate statistics
                avg_position = sum(occ["position"] for occ in occurrences) / len(occurrences)
                success_count = sum(1 for occ in occurrences if occ["success"])
                outcome_correlation = success_count / len(occurrences) if occurrences else 0

                frequent_patterns.append({
                    "sequence": list(ngram),
                    "frequency": round(pattern_pursuit_count / pursuit_count, 2),
                    "pursuit_count": pattern_pursuit_count,
                    "avg_position": round(avg_position, 2),
                    "outcome_correlation": round(outcome_correlation, 2),
                })

        # Sort by frequency * length (longer frequent patterns are more valuable)
        frequent_patterns.sort(
            key=lambda p: p["frequency"] * len(p["sequence"]),
            reverse=True
        )

        # Remove subsequences of more frequent patterns
        filtered_patterns = self._remove_redundant_subsequences(frequent_patterns)

        return filtered_patterns[:20]  # Return top 20

    def _remove_redundant_subsequences(self, patterns: List[Dict]) -> List[Dict]:
        """Remove patterns that are strict subsequences of more frequent patterns."""
        if not patterns:
            return []

        result = []
        seen_subsequences: Set[tuple] = set()

        for pattern in patterns:
            seq = tuple(pattern["sequence"])

            # Check if this is a subsequence of something we've seen
            is_redundant = False
            for seen in seen_subsequences:
                if self._is_subsequence(seq, seen):
                    is_redundant = True
                    break

            if not is_redundant:
                result.append(pattern)
                seen_subsequences.add(seq)

        return result

    def _is_subsequence(self, small: tuple, large: tuple) -> bool:
        """Check if small is a contiguous subsequence of large."""
        if len(small) >= len(large):
            return False

        small_str = "|||".join(small)
        large_str = "|||".join(large)
        return small_str in large_str

    def _cluster_into_phases(self, prepared_data: Dict) -> List[Dict]:
        """
        Algorithm 2: Phase Clustering

        Group observations into methodology phases based on:
        - Temporal gaps (pauses suggesting phase boundaries)
        - Activity type shifts (e.g., ideation -> validation)
        - Context changes (pursuit_phase field)

        Returns:
            [
                {
                    "phase_id": str,
                    "name": str,               # Inferred phase name
                    "typical_activities": [str],  # Common activities
                    "avg_duration_hours": float,
                    "position": str,           # "early", "middle", "late"
                    "frequency": float,        # How often this phase appears
                }
            ]
        """
        pursuits = prepared_data["pursuits"]
        if not pursuits:
            return []

        # Collect all phase boundaries across pursuits
        phase_clusters: Dict[str, List[Dict]] = defaultdict(list)

        for pursuit in pursuits:
            detailed_seq = pursuit["detailed_sequence"]
            temporal = pursuit["temporal_features"]

            # Use existing pursuit_phase context as primary clustering
            current_phase = None
            phase_activities: List[str] = []
            phase_start_idx = 0

            for i, obs in enumerate(detailed_seq):
                obs_phase = obs.get("context", {}).get("pursuit_phase", "UNKNOWN")
                activity = obs.get("observation_type", "UNKNOWN")

                if current_phase is None:
                    current_phase = obs_phase
                    phase_activities = [activity]
                    phase_start_idx = i
                elif obs_phase != current_phase:
                    # Phase boundary found
                    if len(phase_activities) >= self.MIN_PHASE_SIZE:
                        position = self._calculate_position(
                            phase_start_idx, i, len(detailed_seq)
                        )
                        phase_clusters[current_phase].append({
                            "activities": phase_activities,
                            "position": position,
                            "observation_count": len(phase_activities),
                        })

                    current_phase = obs_phase
                    phase_activities = [activity]
                    phase_start_idx = i
                else:
                    phase_activities.append(activity)

            # Handle last phase
            if phase_activities and len(phase_activities) >= self.MIN_PHASE_SIZE:
                position = self._calculate_position(
                    phase_start_idx, len(detailed_seq), len(detailed_seq)
                )
                phase_clusters[current_phase].append({
                    "activities": phase_activities,
                    "position": position,
                    "observation_count": len(phase_activities),
                })

        # Analyze clusters to create phase definitions
        pursuit_count = len(pursuits)
        phases = []

        for phase_name, instances in phase_clusters.items():
            if not instances:
                continue

            # Aggregate statistics
            all_activities = []
            positions = []
            total_obs = 0

            for instance in instances:
                all_activities.extend(instance["activities"])
                positions.append(instance["position"])
                total_obs += instance["observation_count"]

            # Find most common activities
            activity_counts = Counter(all_activities)
            typical_activities = [
                act for act, count in activity_counts.most_common(5)
            ]

            # Determine typical position
            avg_position = sum(p for p in positions) / len(positions) if positions else 0.5
            if avg_position < 0.33:
                position_label = "early"
            elif avg_position < 0.67:
                position_label = "middle"
            else:
                position_label = "late"

            phases.append({
                "phase_id": f"phase_{phase_name.lower()}",
                "name": phase_name,
                "typical_activities": typical_activities,
                "avg_observations": round(total_obs / len(instances), 1),
                "position": position_label,
                "frequency": round(len(instances) / pursuit_count, 2),
            })

        # Sort by typical position (early -> late)
        position_order = {"early": 0, "middle": 1, "late": 2}
        phases.sort(key=lambda p: position_order.get(p["position"], 1))

        return phases

    def _calculate_position(self, start: int, end: int, total: int) -> float:
        """Calculate normalized position (0-1) of a range within total."""
        if total <= 1:
            return 0.5
        midpoint = (start + end) / 2
        return midpoint / total

    def _infer_transitions(
        self,
        prepared_data: Dict,
        phases: List[Dict]
    ) -> List[Dict]:
        """
        Algorithm 3: Transition Inference

        Discover what triggers phase transitions:
        - Activity patterns that precede transitions
        - Temporal patterns (time in phase before transition)
        - Artifact completions that trigger moves

        Returns:
            [
                {
                    "from_phase": str,
                    "to_phase": str,
                    "trigger_activities": [str],  # Activities before transition
                    "trigger_artifacts": [str],   # Artifacts that trigger
                    "avg_phase_duration": float,  # Hours before transition
                    "frequency": float,           # How often this transition occurs
                }
            ]
        """
        pursuits = prepared_data["pursuits"]
        if not pursuits or len(phases) < 2:
            return []

        # Track all phase transitions
        transition_data: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)

        for pursuit in pursuits:
            detailed_seq = pursuit["detailed_sequence"]

            # Find phase transitions
            prev_phase = None
            phase_activities: List[str] = []

            for obs in detailed_seq:
                obs_phase = obs.get("context", {}).get("pursuit_phase", "UNKNOWN")
                activity = obs.get("observation_type", "UNKNOWN")

                if prev_phase is None:
                    prev_phase = obs_phase
                    phase_activities = [activity]
                elif obs_phase != prev_phase:
                    # Transition found
                    transition_key = (prev_phase, obs_phase)

                    # Get trigger activities (last 3 before transition)
                    trigger_acts = phase_activities[-3:] if phase_activities else []

                    # Check for artifact triggers
                    artifact_triggers = [
                        act for act in trigger_acts
                        if "ARTIFACT" in act
                    ]

                    transition_data[transition_key].append({
                        "trigger_activities": trigger_acts,
                        "trigger_artifacts": artifact_triggers,
                        "phase_activity_count": len(phase_activities),
                    })

                    prev_phase = obs_phase
                    phase_activities = [activity]
                else:
                    phase_activities.append(activity)

        # Aggregate transition patterns
        transitions = []
        pursuit_count = len(pursuits)

        for (from_phase, to_phase), instances in transition_data.items():
            if not instances:
                continue

            # Aggregate trigger activities
            all_triggers = []
            all_artifacts = []
            total_duration = 0

            for instance in instances:
                all_triggers.extend(instance["trigger_activities"])
                all_artifacts.extend(instance["trigger_artifacts"])
                total_duration += instance["phase_activity_count"]

            # Find most common triggers
            trigger_counts = Counter(all_triggers)
            top_triggers = [t for t, _ in trigger_counts.most_common(3)]

            artifact_counts = Counter(all_artifacts)
            top_artifacts = [a for a, _ in artifact_counts.most_common(2)]

            transitions.append({
                "from_phase": from_phase,
                "to_phase": to_phase,
                "trigger_activities": top_triggers,
                "trigger_artifacts": top_artifacts,
                "avg_activities_before_transition": round(
                    total_duration / len(instances), 1
                ),
                "frequency": round(len(instances) / pursuit_count, 2),
            })

        # Sort by frequency
        transitions.sort(key=lambda t: t["frequency"], reverse=True)

        return transitions

    def _map_tool_dependencies(self, prepared_data: Dict) -> List[Dict]:
        """
        Algorithm 4: Dependency Mapping

        Map dependencies between tools, artifacts, and activities:
        - Which tools are used before which artifacts
        - Which artifacts enable which activities
        - Which activities typically co-occur

        Returns:
            [
                {
                    "source": str,          # Activity/tool/artifact
                    "target": str,          # Dependent activity/artifact
                    "dependency_type": str, # "enables", "precedes", "co-occurs"
                    "strength": float,      # 0-1 strength of relationship
                    "lag": int,             # Typical sequence gap
                }
            ]
        """
        pursuits = prepared_data["pursuits"]
        if not pursuits:
            return []

        # Track co-occurrences and sequences
        pair_counts: Dict[Tuple[str, str], int] = Counter()
        precedence_counts: Dict[Tuple[str, str], List[int]] = defaultdict(list)
        activity_counts: Counter = Counter()

        for pursuit in pursuits:
            sequence = pursuit["sequence"]

            # Count individual activities
            for activity in sequence:
                activity_counts[activity] += 1

            # Count pairs (co-occurrence)
            unique_activities = set(sequence)
            for a1, a2 in combinations(sorted(unique_activities), 2):
                pair_counts[(a1, a2)] += 1

            # Track precedence (A before B with gap)
            for i, act1 in enumerate(sequence):
                for j in range(i + 1, min(i + 6, len(sequence))):  # Look ahead 5 steps
                    act2 = sequence[j]
                    if act1 != act2:
                        precedence_counts[(act1, act2)].append(j - i)

        # Build dependencies
        dependencies = []
        pursuit_count = len(pursuits)

        # Co-occurrence dependencies
        for (a1, a2), count in pair_counts.most_common(30):
            if count >= 2:  # At least 2 co-occurrences
                strength = count / pursuit_count
                if strength >= 0.3:  # Meaningful correlation
                    dependencies.append({
                        "source": a1,
                        "target": a2,
                        "dependency_type": "co-occurs",
                        "strength": round(strength, 2),
                        "lag": 0,
                    })

        # Precedence dependencies
        for (a1, a2), gaps in precedence_counts.items():
            if len(gaps) >= 2:  # At least 2 occurrences
                avg_gap = sum(gaps) / len(gaps)
                strength = len(gaps) / pursuit_count

                if strength >= 0.3:
                    # Determine dependency type
                    if "ARTIFACT" in a2 and "TOOL" in a1:
                        dep_type = "enables"
                    elif avg_gap <= 2:
                        dep_type = "immediately_precedes"
                    else:
                        dep_type = "precedes"

                    dependencies.append({
                        "source": a1,
                        "target": a2,
                        "dependency_type": dep_type,
                        "strength": round(strength, 2),
                        "lag": round(avg_gap, 1),
                    })

        # Remove duplicates and sort by strength
        seen = set()
        unique_deps = []
        for dep in dependencies:
            key = (dep["source"], dep["target"], dep["dependency_type"])
            if key not in seen:
                seen.add(key)
                unique_deps.append(dep)

        unique_deps.sort(key=lambda d: d["strength"], reverse=True)

        return unique_deps[:25]  # Top 25 dependencies

    def _calculate_confidence(
        self,
        prepared_data: Dict,
        sequences: List[Dict],
        phases: List[Dict],
        transitions: List[Dict],
        dependencies: List[Dict]
    ) -> Dict[str, float]:
        """
        Calculate confidence scores for discovered patterns.

        Four dimensions:
        1. Sample size - More pursuits = higher confidence
        2. Consistency - Patterns recurring across pursuits
        3. Outcome association - Patterns correlating with success
        4. Distinctiveness - v3.7.3: True archetype-to-archetype comparison

        Returns:
            {
                "overall": float,           # Weighted average (0-1)
                "sample_size_score": float,
                "consistency_score": float,
                "outcome_association_score": float,
                "distinctiveness_score": float,
                "similar_archetypes": List[Dict],  # v3.7.3: Top 3 similar archetypes
            }
        """
        pursuit_count = prepared_data["pursuit_count"]

        # 1. Sample size score (logarithmic scaling)
        # 3 pursuits = 0.3, 5 = 0.5, 10 = 0.7, 20+ = 0.9
        if pursuit_count < 3:
            sample_score = 0.0
        elif pursuit_count < 5:
            sample_score = 0.3
        elif pursuit_count < 10:
            sample_score = 0.5
        elif pursuit_count < 20:
            sample_score = 0.7
        else:
            sample_score = 0.9

        # 2. Consistency score (average frequency of discovered patterns)
        frequencies = []
        for seq in sequences:
            frequencies.append(seq.get("frequency", 0))
        for phase in phases:
            frequencies.append(phase.get("frequency", 0))
        for trans in transitions:
            frequencies.append(trans.get("frequency", 0))

        consistency_score = (
            sum(frequencies) / len(frequencies) if frequencies else 0.0
        )

        # 3. Outcome association score
        outcome_correlations = [
            seq.get("outcome_correlation", 0.5) for seq in sequences
        ]
        if outcome_correlations:
            # Score based on how much correlations deviate from 0.5 (random)
            avg_correlation = sum(outcome_correlations) / len(outcome_correlations)
            outcome_score = abs(avg_correlation - 0.5) * 2  # Scale to 0-1
        else:
            outcome_score = 0.0

        # 4. Distinctiveness score (v3.7.3: true archetype comparison)
        # Collect all activities for comparison
        inferred_activities = set()
        for seq in sequences:
            inferred_activities.update(seq.get("sequence", []))
        for phase in phases:
            inferred_activities.update(phase.get("typical_activities", []))

        # Collect tools from dependencies
        inferred_tools = set()
        for dep in dependencies:
            source = dep.get("source", "")
            target = dep.get("target", "")
            if "TOOL" in source:
                inferred_tools.add(source)
            if "TOOL" in target:
                inferred_tools.add(target)

        # Compare against existing archetypes
        similar_archetypes = self._compare_to_existing_archetypes(
            phases, transitions, inferred_activities, inferred_tools
        )

        # Distinctiveness = 1 - max_similarity (more distinct = less similar to existing)
        if similar_archetypes:
            max_similarity = similar_archetypes[0].get("similarity", 0)
            distinctiveness_score = 1.0 - max_similarity
        else:
            # No similar archetypes found = highly distinctive
            distinctiveness_score = 1.0

        # Calculate weighted overall score
        # Weights: sample=0.3, consistency=0.35, outcome=0.2, distinctiveness=0.15
        overall = (
            sample_score * 0.30 +
            consistency_score * 0.35 +
            outcome_score * 0.20 +
            distinctiveness_score * 0.15
        )

        return {
            "overall": round(overall, 2),
            "sample_size_score": round(sample_score, 2),
            "consistency_score": round(consistency_score, 2),
            "outcome_association_score": round(outcome_score, 2),
            "distinctiveness_score": round(distinctiveness_score, 2),
            "similar_archetypes": similar_archetypes,  # v3.7.3
        }

    def _compare_to_existing_archetypes(
        self,
        inferred_phases: List[Dict],
        inferred_transitions: List[Dict],
        inferred_activities: Set[str],
        inferred_tools: Set[str]
    ) -> List[Dict]:
        """
        v3.7.3: Compare inferred methodology against all existing archetypes.

        Returns top 3 archetypes with similarity > 0.3, sorted by similarity descending.
        """
        try:
            from coaching.methodology_archetypes import ARCHETYPE_REGISTRY
        except ImportError:
            logger.warning("Could not import ARCHETYPE_REGISTRY for comparison")
            return []

        similarities = []

        for archetype_name, archetype in ARCHETYPE_REGISTRY.items():
            # Skip ad_hoc/adhoc - it has no structure to compare
            if archetype_name in ("ad_hoc", "adhoc"):
                continue

            similarity = self._compute_archetype_similarity(
                inferred_phases=inferred_phases,
                inferred_transitions=inferred_transitions,
                inferred_activities=inferred_activities,
                inferred_tools=inferred_tools,
                existing_archetype=archetype
            )

            # Round first, then filter - ensures consistency
            rounded_similarity = round(similarity, 2)
            if rounded_similarity > 0.3:  # Only include meaningful similarities
                similarities.append({
                    "name": archetype_name,
                    "display_name": archetype.display_name,
                    "similarity": rounded_similarity,
                })

        # Sort by similarity descending, return top 3
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:3]

    def _compute_archetype_similarity(
        self,
        inferred_phases: List[Dict],
        inferred_transitions: List[Dict],
        inferred_activities: Set[str],
        inferred_tools: Set[str],
        existing_archetype
    ) -> float:
        """
        v3.7.3 Audit I Remediation: Compute multi-dimensional similarity.

        Dimensions and weights:
        1. Phase count similarity (0.15 weight)
        2. Activity overlap via Jaccard (0.35 weight)
        3. Phase ordering similarity via LCS (0.25 weight)
        4. Tool overlap (0.15 weight)
        5. Transition structure similarity (0.10 weight)
        """
        # 1. Phase count similarity (0.15 weight)
        inferred_count = len(inferred_phases)
        existing_count = len(existing_archetype.phases) if existing_archetype.phases else 0

        if existing_count == 0:
            phase_count_sim = 0.0
        else:
            diff = abs(inferred_count - existing_count)
            # Identical count = 1.0, each difference = -0.2
            phase_count_sim = max(1.0 - (diff * 0.2), 0.0)

        # 2. Activity overlap via Jaccard similarity (0.35 weight)
        existing_activities = set()
        for phase in existing_archetype.phases:
            # Use expected_artifacts as proxy for activities
            existing_activities.update(phase.expected_artifacts)
            # Also add normalized phase name activities
            existing_activities.add(phase.name.lower())

        # Normalize inferred activities for comparison
        normalized_inferred = set()
        for act in inferred_activities:
            # Extract meaningful keywords
            act_lower = act.lower()
            normalized_inferred.add(act_lower)
            # Add key activity types
            for keyword in ["vision", "hypothesis", "fear", "experiment", "validate",
                          "prototype", "test", "iterate", "empathy", "define", "ideate"]:
                if keyword in act_lower:
                    normalized_inferred.add(keyword)

        if not existing_activities and not normalized_inferred:
            activity_sim = 0.0
        elif not existing_activities or not normalized_inferred:
            activity_sim = 0.0
        else:
            intersection = existing_activities.intersection(normalized_inferred)
            union = existing_activities.union(normalized_inferred)
            activity_sim = len(intersection) / len(union) if union else 0.0

        # 3. Phase ordering similarity via Longest Common Subsequence (0.25 weight)
        # Map inferred phase positions to Universal States
        inferred_states = []
        for phase in inferred_phases:
            pos = phase.get("position", "middle")
            if pos == "early":
                inferred_states.append("DISCOVERY")
            elif pos == "late":
                inferred_states.append("IMPLEMENTATION")
            else:
                inferred_states.append("VALIDATION")

        existing_states = []
        # Map existing archetype phases (using coaching_focus as indicator)
        for phase in existing_archetype.phases:
            focus = phase.coaching_focus.lower()
            if "problem" in focus or "user" in focus or "empathy" in focus:
                existing_states.append("DISCOVERY")
            elif "execution" in focus or "launch" in focus:
                existing_states.append("IMPLEMENTATION")
            else:
                existing_states.append("VALIDATION")

        if not inferred_states or not existing_states:
            ordering_sim = 0.0
        else:
            lcs_len = self._longest_common_subsequence(inferred_states, existing_states)
            max_len = max(len(inferred_states), len(existing_states))
            ordering_sim = lcs_len / max_len if max_len > 0 else 0.0

        # 4. Tool overlap (0.15 weight)
        # For now, check if archetype mentions similar tool types
        existing_tools = set()
        for phase in existing_archetype.phases:
            # Success indicators often mention tools/artifacts
            for indicator in phase.success_indicators:
                indicator_lower = indicator.lower()
                for tool_type in ["mvp", "prototype", "test", "survey", "interview",
                                "experiment", "sketch", "canvas"]:
                    if tool_type in indicator_lower:
                        existing_tools.add(tool_type)

        normalized_tools = set()
        for tool in inferred_tools:
            tool_lower = tool.lower()
            for tool_type in ["mvp", "prototype", "test", "survey", "interview",
                            "experiment", "sketch", "canvas"]:
                if tool_type in tool_lower:
                    normalized_tools.add(tool_type)

        if not existing_tools and not normalized_tools:
            tool_sim = 0.5  # Neutral if no tools identified
        elif not existing_tools or not normalized_tools:
            tool_sim = 0.0
        else:
            intersection = existing_tools.intersection(normalized_tools)
            union = existing_tools.union(normalized_tools)
            tool_sim = len(intersection) / len(union) if union else 0.0

        # 5. Transition structure similarity (0.10 weight)
        inferred_transition_count = len(inferred_transitions)
        existing_transition_count = len(existing_archetype.transitions)

        # Check for backward transitions
        has_backward_inferred = any(
            t.get("from_phase", "") > t.get("to_phase", "")
            for t in inferred_transitions
        )
        allows_backward_existing = (
            existing_archetype.backward_iteration_philosophy and
            "pivot" in existing_archetype.backward_iteration_philosophy.lower()
        )

        # Transition count similarity
        if existing_transition_count == 0 and inferred_transition_count == 0:
            transition_count_sim = 1.0
        elif existing_transition_count == 0 or inferred_transition_count == 0:
            transition_count_sim = 0.0
        else:
            diff = abs(inferred_transition_count - existing_transition_count)
            transition_count_sim = max(1.0 - (diff * 0.15), 0.0)

        # Backward transition alignment
        backward_sim = 1.0 if has_backward_inferred == allows_backward_existing else 0.5

        transition_sim = (transition_count_sim * 0.6) + (backward_sim * 0.4)

        # Calculate weighted overall similarity
        similarity = (
            phase_count_sim * 0.15 +
            activity_sim * 0.35 +
            ordering_sim * 0.25 +
            tool_sim * 0.15 +
            transition_sim * 0.10
        )

        return similarity

    def _longest_common_subsequence(self, seq1: List[str], seq2: List[str]) -> int:
        """Calculate length of longest common subsequence."""
        if not seq1 or not seq2:
            return 0

        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i - 1] == seq2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        return dp[m][n]


# Singleton instance
_inference_engine_instance = None


def get_pattern_inference_engine() -> PatternInferenceEngine:
    """Get or create the PatternInferenceEngine singleton."""
    global _inference_engine_instance
    if _inference_engine_instance is None:
        _inference_engine_instance = PatternInferenceEngine()
    return _inference_engine_instance
