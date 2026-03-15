"""
InDE MVP v3.4 - Formation Flow & Composition Patterns
IDTFS Pillar 5: Composition Pattern Analysis + Formation Orchestration

This module provides:
- Composition Pattern Analysis: Historical team effectiveness patterns
- Formation Flow: Orchestrated team formation recommendations
- Gap Analysis: Identify missing expertise in current teams
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from enum import Enum
import uuid
import logging

from core.database import db
from core.config import IDTFS_CONFIG

logger = logging.getLogger("inde.discovery.formation")


# =============================================================================
# ENUMERATIONS
# =============================================================================

class FormationStatus(str, Enum):
    """Status of a formation recommendation."""
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class PatternType(str, Enum):
    """Types of composition patterns."""
    EXPERTISE_MIX = "EXPERTISE_MIX"
    ROLE_BALANCE = "ROLE_BALANCE"
    COGNITIVE_DIVERSITY = "COGNITIVE_DIVERSITY"
    EXPERIENCE_BLEND = "EXPERIENCE_BLEND"
    COLLABORATION_HISTORY = "COLLABORATION_HISTORY"


class GapSeverity(str, Enum):
    """Severity of expertise gaps."""
    CRITICAL = "CRITICAL"
    SIGNIFICANT = "SIGNIFICANT"
    MODERATE = "MODERATE"
    MINOR = "MINOR"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CompositionPattern:
    """A composition pattern learned from historical team data."""
    pattern_id: str
    pattern_type: PatternType
    org_id: str
    pattern_data: Dict[str, Any]
    effectiveness_score: float
    sample_size: int
    confidence: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type.value,
            "org_id": self.org_id,
            "pattern_data": self.pattern_data,
            "effectiveness_score": self.effectiveness_score,
            "sample_size": self.sample_size,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CompositionPattern":
        return cls(
            pattern_id=data["pattern_id"],
            pattern_type=PatternType(data["pattern_type"]),
            org_id=data["org_id"],
            pattern_data=data.get("pattern_data", {}),
            effectiveness_score=data.get("effectiveness_score", 0.0),
            sample_size=data.get("sample_size", 0),
            confidence=data.get("confidence", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.now(timezone.utc)),
            last_updated=datetime.fromisoformat(data["last_updated"]) if isinstance(data.get("last_updated"), str) else data.get("last_updated", datetime.now(timezone.utc))
        )


@dataclass
class ExpertiseGap:
    """An identified expertise gap in a team."""
    gap_id: str
    pursuit_id: str
    gap_description: str
    required_tags: List[str]
    required_expertise_types: List[str]
    severity: GapSeverity
    identified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolved_by: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "gap_id": self.gap_id,
            "pursuit_id": self.pursuit_id,
            "gap_description": self.gap_description,
            "required_tags": self.required_tags,
            "required_expertise_types": self.required_expertise_types,
            "severity": self.severity.value,
            "identified_at": self.identified_at.isoformat(),
            "resolved": self.resolved,
            "resolved_by": self.resolved_by
        }


@dataclass
class FormationRecommendation:
    """A team formation recommendation."""
    recommendation_id: str
    pursuit_id: str
    org_id: str
    gap_id: Optional[str]
    recommended_members: List[Dict[str, Any]]
    rationale: str
    composition_score: float
    pattern_matches: List[str]
    status: FormationStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    accepted_at: Optional[datetime] = None
    accepted_by: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "recommendation_id": self.recommendation_id,
            "pursuit_id": self.pursuit_id,
            "org_id": self.org_id,
            "gap_id": self.gap_id,
            "recommended_members": self.recommended_members,
            "rationale": self.rationale,
            "composition_score": self.composition_score,
            "pattern_matches": self.pattern_matches,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "accepted_by": self.accepted_by
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "FormationRecommendation":
        return cls(
            recommendation_id=data["recommendation_id"],
            pursuit_id=data["pursuit_id"],
            org_id=data["org_id"],
            gap_id=data.get("gap_id"),
            recommended_members=data.get("recommended_members", []),
            rationale=data.get("rationale", ""),
            composition_score=data.get("composition_score", 0.0),
            pattern_matches=data.get("pattern_matches", []),
            status=FormationStatus(data.get("status", "DRAFT")),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.now(timezone.utc)),
            created_by=data.get("created_by", ""),
            accepted_at=datetime.fromisoformat(data["accepted_at"]) if data.get("accepted_at") else None,
            accepted_by=data.get("accepted_by")
        )


# =============================================================================
# COMPOSITION PATTERN ANALYZER (PILLAR 5)
# =============================================================================

class CompositionPatternAnalyzer:
    """
    Analyzes historical team compositions to identify effectiveness patterns.

    Pillar 5 of IDTFS: Identifies patterns that correlate with successful
    innovation outcomes based on team composition data.
    """

    def __init__(self):
        self.pattern_weights = IDTFS_CONFIG.get("pattern_weights", {
            "expertise_mix": 0.25,
            "role_balance": 0.20,
            "cognitive_diversity": 0.20,
            "experience_blend": 0.15,
            "collaboration_history": 0.20
        })
        self.min_sample_size = 5  # Minimum teams to establish pattern

    def analyze_org_patterns(self, org_id: str) -> List[CompositionPattern]:
        """
        Analyze all team compositions in an organization to extract patterns.

        Returns list of identified composition patterns.
        """
        patterns = []

        # Get all pursuits with teams in org
        pursuits = db.get_pursuits_by_org(org_id) or []
        successful_pursuits = [p for p in pursuits if self._is_successful_pursuit(p)]

        if len(successful_pursuits) < self.min_sample_size:
            logger.info(f"Insufficient data for pattern analysis in org {org_id}")
            return patterns

        # Analyze expertise mix patterns
        expertise_pattern = self._analyze_expertise_mix(org_id, successful_pursuits)
        if expertise_pattern:
            patterns.append(expertise_pattern)

        # Analyze role balance patterns
        role_pattern = self._analyze_role_balance(org_id, successful_pursuits)
        if role_pattern:
            patterns.append(role_pattern)

        # Analyze cognitive diversity patterns
        diversity_pattern = self._analyze_cognitive_diversity(org_id, successful_pursuits)
        if diversity_pattern:
            patterns.append(diversity_pattern)

        # Analyze collaboration history patterns
        collab_pattern = self._analyze_collaboration_history(org_id, successful_pursuits)
        if collab_pattern:
            patterns.append(collab_pattern)

        # Store patterns
        for pattern in patterns:
            db.upsert_composition_pattern(pattern.to_dict())

        return patterns

    def _is_successful_pursuit(self, pursuit: Dict) -> bool:
        """Determine if a pursuit was successful based on metrics."""
        health_score = pursuit.get("health_score", 0)
        status = pursuit.get("status", "")
        maturity = pursuit.get("maturity_level", 0)

        # Success criteria: high health, completed or advanced, mature
        return (
            health_score >= 0.7 or
            status in ["completed", "launched", "scaling"] or
            maturity >= 3
        )

    def _analyze_expertise_mix(self, org_id: str, pursuits: List[Dict]) -> Optional[CompositionPattern]:
        """Analyze optimal expertise tag combinations."""
        expertise_counts = {}
        total_teams = 0

        for pursuit in pursuits:
            team_members = pursuit.get("sharing", {}).get("team_members", [])
            if not team_members:
                continue

            total_teams += 1
            team_tags = set()

            for member in team_members:
                profile = db.get_innovator_profile(member.get("user_id"), org_id)
                if profile:
                    team_tags.update(profile.get("declared_expertise_tags", []))
                    team_tags.update(profile.get("inferred_expertise_tags", []))

            # Count tag combinations
            for tag in team_tags:
                expertise_counts[tag] = expertise_counts.get(tag, 0) + 1

        if total_teams < self.min_sample_size:
            return None

        # Find most common expertise in successful teams
        sorted_expertise = sorted(expertise_counts.items(), key=lambda x: x[1], reverse=True)
        top_expertise = [tag for tag, count in sorted_expertise[:10] if count >= total_teams * 0.3]

        return CompositionPattern(
            pattern_id=str(uuid.uuid4()),
            pattern_type=PatternType.EXPERTISE_MIX,
            org_id=org_id,
            pattern_data={
                "recommended_tags": top_expertise,
                "tag_frequencies": dict(sorted_expertise[:20])
            },
            effectiveness_score=0.8,
            sample_size=total_teams,
            confidence=min(total_teams / 20, 1.0)
        )

    def _analyze_role_balance(self, org_id: str, pursuits: List[Dict]) -> Optional[CompositionPattern]:
        """Analyze optimal role distribution."""
        role_distributions = []

        for pursuit in pursuits:
            team_members = pursuit.get("sharing", {}).get("team_members", [])
            if not team_members:
                continue

            role_counts = {}
            for member in team_members:
                profile = db.get_innovator_profile(member.get("user_id"), org_id)
                if profile:
                    for et in profile.get("expertise_types", []):
                        role_counts[et] = role_counts.get(et, 0) + 1

            if role_counts:
                total = sum(role_counts.values())
                role_distributions.append({k: v/total for k, v in role_counts.items()})

        if len(role_distributions) < self.min_sample_size:
            return None

        # Calculate average role distribution
        avg_distribution = {}
        all_roles = set()
        for dist in role_distributions:
            all_roles.update(dist.keys())

        for role in all_roles:
            values = [d.get(role, 0) for d in role_distributions]
            avg_distribution[role] = sum(values) / len(values)

        return CompositionPattern(
            pattern_id=str(uuid.uuid4()),
            pattern_type=PatternType.ROLE_BALANCE,
            org_id=org_id,
            pattern_data={
                "optimal_distribution": avg_distribution,
                "recommended_team_size": {
                    "min": 3,
                    "optimal": 5,
                    "max": 8
                }
            },
            effectiveness_score=0.75,
            sample_size=len(role_distributions),
            confidence=min(len(role_distributions) / 20, 1.0)
        )

    def _analyze_cognitive_diversity(self, org_id: str, pursuits: List[Dict]) -> Optional[CompositionPattern]:
        """Analyze cognitive diversity patterns."""
        diversity_scores = []

        for pursuit in pursuits:
            team_members = pursuit.get("sharing", {}).get("team_members", [])
            if len(team_members) < 2:
                continue

            expertise_types = set()
            for member in team_members:
                profile = db.get_innovator_profile(member.get("user_id"), org_id)
                if profile:
                    expertise_types.update(profile.get("expertise_types", []))

            # Diversity = unique types / team size (capped at 1.0)
            diversity = min(len(expertise_types) / len(team_members), 1.0)
            diversity_scores.append(diversity)

        if len(diversity_scores) < self.min_sample_size:
            return None

        avg_diversity = sum(diversity_scores) / len(diversity_scores)

        return CompositionPattern(
            pattern_id=str(uuid.uuid4()),
            pattern_type=PatternType.COGNITIVE_DIVERSITY,
            org_id=org_id,
            pattern_data={
                "optimal_diversity_range": {
                    "min": max(0.6, avg_diversity - 0.15),
                    "optimal": avg_diversity,
                    "max": min(1.0, avg_diversity + 0.15)
                }
            },
            effectiveness_score=0.7,
            sample_size=len(diversity_scores),
            confidence=min(len(diversity_scores) / 20, 1.0)
        )

    def _analyze_collaboration_history(self, org_id: str, pursuits: List[Dict]) -> Optional[CompositionPattern]:
        """Analyze collaboration history patterns."""
        collaboration_pairs = {}

        for pursuit in pursuits:
            team_members = pursuit.get("sharing", {}).get("team_members", [])
            if len(team_members) < 2:
                continue

            # Count collaboration pairs
            member_ids = [m.get("user_id") for m in team_members]
            for i, m1 in enumerate(member_ids):
                for m2 in member_ids[i+1:]:
                    pair = tuple(sorted([m1, m2]))
                    collaboration_pairs[pair] = collaboration_pairs.get(pair, 0) + 1

        if not collaboration_pairs:
            return None

        # Find frequently successful collaborators
        strong_pairs = {pair: count for pair, count in collaboration_pairs.items() if count >= 2}

        return CompositionPattern(
            pattern_id=str(uuid.uuid4()),
            pattern_type=PatternType.COLLABORATION_HISTORY,
            org_id=org_id,
            pattern_data={
                "strong_collaborator_pairs": [
                    {"members": list(pair), "collaborations": count}
                    for pair, count in sorted(strong_pairs.items(), key=lambda x: x[1], reverse=True)[:20]
                ],
                "recommendation": "prior_success_weight",
                "weight": 0.15
            },
            effectiveness_score=0.65,
            sample_size=len(pursuits),
            confidence=min(len(strong_pairs) / 10, 1.0)
        )

    def get_org_patterns(self, org_id: str) -> List[CompositionPattern]:
        """Get existing patterns for an organization."""
        pattern_dicts = db.get_composition_patterns(org_id)
        return [CompositionPattern.from_dict(p) for p in pattern_dicts]

    def score_team_composition(
        self,
        org_id: str,
        member_ids: List[str],
        patterns: Optional[List[CompositionPattern]] = None
    ) -> Dict[str, Any]:
        """
        Score a proposed team composition against known patterns.

        Returns composite score and breakdown by pattern type.
        """
        if patterns is None:
            patterns = self.get_org_patterns(org_id)

        if not patterns:
            return {
                "composite_score": 0.5,
                "pattern_scores": {},
                "matches": [],
                "gaps": [],
                "message": "Insufficient pattern data for scoring"
            }

        scores = {}
        matches = []
        gaps = []

        # Get member profiles
        member_profiles = []
        for member_id in member_ids:
            profile = db.get_innovator_profile(member_id, org_id)
            if profile:
                member_profiles.append(profile)

        if not member_profiles:
            return {
                "composite_score": 0.3,
                "pattern_scores": {},
                "matches": [],
                "gaps": ["No member profiles found"],
                "message": "Unable to score team without member profiles"
            }

        # Score against each pattern
        for pattern in patterns:
            score, match_details = self._score_against_pattern(
                member_profiles, pattern
            )
            scores[pattern.pattern_type.value] = score

            if score >= 0.7:
                matches.append(f"Strong match: {pattern.pattern_type.value}")
            elif score < 0.4:
                gaps.append(f"Gap in {pattern.pattern_type.value}: score {score:.2f}")

        # Calculate weighted composite
        composite = 0.0
        total_weight = 0.0
        for pattern_type, score in scores.items():
            weight = self.pattern_weights.get(pattern_type.lower(), 0.2)
            composite += score * weight
            total_weight += weight

        if total_weight > 0:
            composite /= total_weight

        return {
            "composite_score": round(composite, 3),
            "pattern_scores": scores,
            "matches": matches,
            "gaps": gaps,
            "team_size": len(member_ids),
            "profiles_found": len(member_profiles)
        }

    def _score_against_pattern(
        self,
        profiles: List[Dict],
        pattern: CompositionPattern
    ) -> tuple:
        """Score profiles against a specific pattern."""
        score = 0.5  # Default neutral score
        details = {}

        if pattern.pattern_type == PatternType.EXPERTISE_MIX:
            recommended_tags = pattern.pattern_data.get("recommended_tags", [])
            team_tags = set()
            for profile in profiles:
                team_tags.update(profile.get("declared_expertise_tags", []))
                team_tags.update(profile.get("inferred_expertise_tags", []))

            if recommended_tags:
                matches = len(team_tags.intersection(set(recommended_tags)))
                score = min(matches / len(recommended_tags), 1.0)
                details["matched_tags"] = matches

        elif pattern.pattern_type == PatternType.ROLE_BALANCE:
            optimal_dist = pattern.pattern_data.get("optimal_distribution", {})
            team_types = {}
            for profile in profiles:
                for et in profile.get("expertise_types", []):
                    team_types[et] = team_types.get(et, 0) + 1

            if optimal_dist and team_types:
                total = sum(team_types.values())
                team_dist = {k: v/total for k, v in team_types.items()}

                # Calculate similarity to optimal
                diff_sum = 0
                for role, opt_pct in optimal_dist.items():
                    team_pct = team_dist.get(role, 0)
                    diff_sum += abs(opt_pct - team_pct)

                score = max(0, 1 - diff_sum / 2)
                details["distribution"] = team_dist

        elif pattern.pattern_type == PatternType.COGNITIVE_DIVERSITY:
            optimal_range = pattern.pattern_data.get("optimal_diversity_range", {})
            expertise_types = set()
            for profile in profiles:
                expertise_types.update(profile.get("expertise_types", []))

            diversity = len(expertise_types) / len(profiles) if profiles else 0

            opt_min = optimal_range.get("min", 0.5)
            opt_max = optimal_range.get("max", 1.0)

            if opt_min <= diversity <= opt_max:
                score = 1.0
            elif diversity < opt_min:
                score = max(0, diversity / opt_min)
            else:
                score = max(0, 1 - (diversity - opt_max) / 0.5)

            details["diversity"] = diversity

        return score, details


# =============================================================================
# GAP ANALYZER
# =============================================================================

class GapAnalyzer:
    """Identifies expertise gaps in teams."""

    def analyze_pursuit_gaps(self, pursuit_id: str, org_id: str) -> List[ExpertiseGap]:
        """
        Analyze a pursuit to identify expertise gaps.

        Uses pursuit requirements, current team composition, and
        organizational patterns to identify missing expertise.
        """
        pursuit = db.get_pursuit(pursuit_id)
        if not pursuit:
            return []

        gaps = []

        # Get current team composition
        team_members = pursuit.get("sharing", {}).get("team_members", [])
        current_expertise = set()
        current_types = set()

        for member in team_members:
            profile = db.get_innovator_profile(member.get("user_id"), org_id)
            if profile:
                current_expertise.update(profile.get("declared_expertise_tags", []))
                current_expertise.update(profile.get("inferred_expertise_tags", []))
                current_types.update(profile.get("expertise_types", []))

        # Get pursuit requirements (from artifacts, coaching insights)
        required_expertise = pursuit.get("required_expertise", [])
        pursuit_type = pursuit.get("pursuit_type", "general")

        # Default requirements based on pursuit type
        type_requirements = {
            "technical": ["engineering", "development", "architecture"],
            "product": ["product_management", "user_research", "design"],
            "business": ["market_analysis", "finance", "strategy"],
            "research": ["research", "analysis", "methodology"]
        }

        default_reqs = type_requirements.get(pursuit_type, [])
        all_requirements = set(required_expertise + default_reqs)

        # Identify gaps
        missing_expertise = all_requirements - current_expertise
        if missing_expertise:
            severity = GapSeverity.CRITICAL if len(missing_expertise) > 3 else \
                       GapSeverity.SIGNIFICANT if len(missing_expertise) > 1 else \
                       GapSeverity.MODERATE

            gaps.append(ExpertiseGap(
                gap_id=str(uuid.uuid4()),
                pursuit_id=pursuit_id,
                gap_description=f"Missing {len(missing_expertise)} required expertise areas",
                required_tags=list(missing_expertise),
                required_expertise_types=[],
                severity=severity
            ))

        # Check team size
        recommended_size = pursuit.get("recommended_team_size", 4)
        if len(team_members) < recommended_size:
            gaps.append(ExpertiseGap(
                gap_id=str(uuid.uuid4()),
                pursuit_id=pursuit_id,
                gap_description=f"Team size ({len(team_members)}) below recommended ({recommended_size})",
                required_tags=[],
                required_expertise_types=[],
                severity=GapSeverity.MODERATE
            ))

        return gaps


# =============================================================================
# FORMATION FLOW ORCHESTRATOR
# =============================================================================

class FormationFlowOrchestrator:
    """
    Orchestrates the team formation recommendation flow.

    Coordinates IDTFS pillars to generate optimal team recommendations.
    """

    def __init__(self):
        self.pattern_analyzer = CompositionPatternAnalyzer()
        self.gap_analyzer = GapAnalyzer()

    def generate_recommendations(
        self,
        pursuit_id: str,
        org_id: str,
        created_by: str,
        gap_id: Optional[str] = None,
        max_recommendations: int = 3
    ) -> List[FormationRecommendation]:
        """
        Generate team formation recommendations for a pursuit.

        Uses all IDTFS pillars to identify optimal candidates.
        """
        from .idtfs import get_discovery_query

        pursuit = db.get_pursuit(pursuit_id)
        if not pursuit:
            logger.warning(f"Pursuit {pursuit_id} not found")
            return []

        # Get existing gaps or analyze
        if gap_id:
            # Use specific gap
            gap_data = db.get_expertise_gap(gap_id)
            gaps = [ExpertiseGap(**gap_data)] if gap_data else []
        else:
            # Analyze all gaps
            gaps = self.gap_analyzer.analyze_pursuit_gaps(pursuit_id, org_id)

        if not gaps:
            logger.info(f"No gaps identified for pursuit {pursuit_id}")
            return []

        recommendations = []
        discovery = get_discovery_query()

        for gap in gaps[:max_recommendations]:
            # Search for candidates matching gap
            candidates = discovery.search(
                org_id=org_id,
                required_tags=gap.required_tags,
                preferred_expertise_types=gap.required_expertise_types,
                min_availability=0.3,
                max_results=10
            )

            if not candidates:
                continue

            # Get org patterns for scoring
            patterns = self.pattern_analyzer.get_org_patterns(org_id)

            # Generate recommendation
            recommended = self._select_optimal_combination(
                candidates=candidates,
                gap=gap,
                pursuit=pursuit,
                patterns=patterns,
                org_id=org_id
            )

            if recommended:
                recommendation = FormationRecommendation(
                    recommendation_id=str(uuid.uuid4()),
                    pursuit_id=pursuit_id,
                    org_id=org_id,
                    gap_id=gap.gap_id,
                    recommended_members=recommended["members"],
                    rationale=recommended["rationale"],
                    composition_score=recommended["score"],
                    pattern_matches=recommended.get("pattern_matches", []),
                    status=FormationStatus.PROPOSED,
                    created_by=created_by
                )

                # Store recommendation
                db.create_formation_recommendation(recommendation.to_dict())
                recommendations.append(recommendation)

        return recommendations

    def _select_optimal_combination(
        self,
        candidates: List,
        gap: ExpertiseGap,
        pursuit: Dict,
        patterns: List[CompositionPattern],
        org_id: str
    ) -> Optional[Dict]:
        """
        Select optimal candidate combination for the gap.

        Considers individual scores, team composition, and patterns.
        """
        if not candidates:
            return None

        # Get current team
        current_team = [
            m.get("user_id")
            for m in pursuit.get("sharing", {}).get("team_members", [])
        ]

        # Simple greedy selection for MVP
        # In production, would use optimization algorithm
        selected = []
        remaining_tags = set(gap.required_tags)

        for candidate in candidates:
            if len(selected) >= 3:
                break

            # Check if candidate fills any remaining gaps
            candidate_tags = set(candidate.matched_tags)
            fills_gap = candidate_tags.intersection(remaining_tags)

            if fills_gap or not remaining_tags:
                selected.append({
                    "user_id": candidate.user_id,
                    "composite_score": candidate.composite_score,
                    "matched_tags": candidate.matched_tags,
                    "expertise_types": candidate.expertise_types,
                    "availability_status": candidate.availability_status
                })
                remaining_tags -= fills_gap

        if not selected:
            # Take top candidates even if no specific match
            selected = [
                {
                    "user_id": c.user_id,
                    "composite_score": c.composite_score,
                    "matched_tags": c.matched_tags,
                    "expertise_types": c.expertise_types,
                    "availability_status": c.availability_status
                }
                for c in candidates[:2]
            ]

        # Score the proposed team
        proposed_team = current_team + [m["user_id"] for m in selected]
        composition_result = self.pattern_analyzer.score_team_composition(
            org_id=org_id,
            member_ids=proposed_team,
            patterns=patterns
        )

        # Build rationale
        rationale_parts = [f"Addresses gap: {gap.gap_description}"]
        if selected:
            rationale_parts.append(f"Recommending {len(selected)} candidate(s)")
        if composition_result.get("matches"):
            rationale_parts.extend(composition_result["matches"])

        return {
            "members": selected,
            "score": composition_result.get("composite_score", 0.5),
            "rationale": ". ".join(rationale_parts),
            "pattern_matches": composition_result.get("matches", [])
        }

    def accept_recommendation(
        self,
        recommendation_id: str,
        accepted_by: str
    ) -> Dict:
        """Accept a formation recommendation."""
        rec = db.get_formation_recommendation(recommendation_id)
        if not rec:
            return {"success": False, "error": "Recommendation not found"}

        if rec.get("status") != FormationStatus.PROPOSED.value:
            return {"success": False, "error": f"Cannot accept recommendation in {rec.get('status')} status"}

        # Update recommendation
        db.update_formation_recommendation(recommendation_id, {
            "status": FormationStatus.ACCEPTED.value,
            "accepted_at": datetime.now(timezone.utc).isoformat(),
            "accepted_by": accepted_by
        })

        # Add members to pursuit team
        pursuit_id = rec.get("pursuit_id")
        for member in rec.get("recommended_members", []):
            db.add_team_member(pursuit_id, {
                "user_id": member["user_id"],
                "role": "team_member",
                "added_via": "formation_recommendation",
                "recommendation_id": recommendation_id,
                "added_at": datetime.now(timezone.utc).isoformat(),
                "added_by": accepted_by
            })

        # Mark related gap as resolved
        if rec.get("gap_id"):
            db.resolve_expertise_gap(rec["gap_id"], accepted_by)

        logger.info(f"Formation recommendation {recommendation_id} accepted by {accepted_by}")

        return {
            "success": True,
            "members_added": len(rec.get("recommended_members", [])),
            "pursuit_id": pursuit_id
        }

    def reject_recommendation(
        self,
        recommendation_id: str,
        rejected_by: str,
        reason: Optional[str] = None
    ) -> Dict:
        """Reject a formation recommendation."""
        rec = db.get_formation_recommendation(recommendation_id)
        if not rec:
            return {"success": False, "error": "Recommendation not found"}

        db.update_formation_recommendation(recommendation_id, {
            "status": FormationStatus.REJECTED.value,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "rejected_by": rejected_by,
            "rejection_reason": reason
        })

        logger.info(f"Formation recommendation {recommendation_id} rejected by {rejected_by}")

        return {"success": True}


# =============================================================================
# SINGLETON ACCESSORS
# =============================================================================

_pattern_analyzer: Optional[CompositionPatternAnalyzer] = None
_gap_analyzer: Optional[GapAnalyzer] = None
_formation_orchestrator: Optional[FormationFlowOrchestrator] = None


def get_pattern_analyzer() -> CompositionPatternAnalyzer:
    """Get singleton CompositionPatternAnalyzer instance."""
    global _pattern_analyzer
    if _pattern_analyzer is None:
        _pattern_analyzer = CompositionPatternAnalyzer()
    return _pattern_analyzer


def get_gap_analyzer() -> GapAnalyzer:
    """Get singleton GapAnalyzer instance."""
    global _gap_analyzer
    if _gap_analyzer is None:
        _gap_analyzer = GapAnalyzer()
    return _gap_analyzer


def get_formation_orchestrator() -> FormationFlowOrchestrator:
    """Get singleton FormationFlowOrchestrator instance."""
    global _formation_orchestrator
    if _formation_orchestrator is None:
        _formation_orchestrator = FormationFlowOrchestrator()
    return _formation_orchestrator
