"""
InDE MVP v2.6 - Pitch Orchestrator

Provides stakeholder-informed pitch preparation including:
- Stakeholder-specific intelligence for targeting
- Objection preparation based on actual feedback
- Social proof from champions
- Emphasis areas based on support landscape
"""

from datetime import datetime
from typing import Dict, List, Optional


class PitchOrchestrator:
    """
    Orchestrates pitch preparation with stakeholder intelligence.
    """

    def __init__(self, database, support_analyzer=None, fear_extractor=None,
                 pattern_engine=None):
        """
        Initialize PitchOrchestrator.

        Args:
            database: Database instance
            support_analyzer: SupportLandscapeAnalyzer for support intelligence
            fear_extractor: FearExtractor for fear cross-validation
            pattern_engine: PatternEngine for similar pursuit patterns
        """
        self.db = database
        self.support_analyzer = support_analyzer
        self.fear_extractor = fear_extractor
        self.pattern_engine = pattern_engine

    def generate_pitch_preparation(self, pursuit_id: str,
                                   target_stakeholder: str = None) -> Dict:
        """
        Generate comprehensive pitch preparation package.

        Args:
            pursuit_id: Pursuit ID
            target_stakeholder: Optional name of target stakeholder

        Returns:
            {
                "pitch_structure": {...},
                "stakeholder_intelligence": {...},
                "objection_preparation": [...],
                "social_proof": {...},
                "emphasis_areas": [...],
                "key_messages": [...],
                "risk_warnings": [...]
            }
        """
        # Get pursuit info
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return self._empty_preparation()

        # Get support landscape
        analysis = None
        if self.support_analyzer:
            analysis = self.support_analyzer.analyze_pursuit_support(pursuit_id)
        else:
            analysis = self._get_basic_analysis(pursuit_id)

        # Get stakeholder-specific intelligence
        stakeholder_intel = self._get_stakeholder_intelligence(
            pursuit_id, target_stakeholder
        )

        # Prepare objections
        objections = self._prepare_objections(pursuit_id, stakeholder_intel, analysis)

        # Build social proof
        social_proof = self._build_social_proof(analysis)

        # Determine emphasis areas
        emphasis = self._determine_emphasis(stakeholder_intel, analysis)

        # Generate key messages
        key_messages = self._generate_key_messages(pursuit, analysis, stakeholder_intel)

        # Identify risk warnings
        risk_warnings = self._identify_risk_warnings(analysis)

        # Generate basic pitch structure
        pitch_structure = self._generate_pitch_structure(pursuit, stakeholder_intel)

        return {
            "pitch_structure": pitch_structure,
            "stakeholder_intelligence": stakeholder_intel,
            "objection_preparation": objections,
            "social_proof": social_proof,
            "emphasis_areas": emphasis,
            "key_messages": key_messages,
            "risk_warnings": risk_warnings,
            "support_context": {
                "total_engaged": analysis.get("total_engaged", 0) if analysis else 0,
                "support_percentage": analysis.get("support_percentage", 0) if analysis else 0,
                "consensus_readiness": analysis.get("consensus_readiness", 0) if analysis else 0
            }
        }

    def _get_stakeholder_intelligence(self, pursuit_id: str,
                                      target_stakeholder: str = None) -> Dict:
        """Get intelligence about target stakeholder."""
        intelligence = {
            "target_stakeholder": target_stakeholder,
            "previous_engagement": False,
            "known_concerns": [],
            "known_position": "unknown",
            "conditions": "",
            "resources_offered": ""
        }

        if not target_stakeholder:
            return intelligence

        # Check if target stakeholder already engaged
        feedback_list = self.db.get_stakeholder_feedback_by_pursuit(pursuit_id)

        for feedback in feedback_list:
            name = feedback.get("stakeholder_name", "").lower()
            if target_stakeholder.lower() in name or name in target_stakeholder.lower():
                intelligence["previous_engagement"] = True
                intelligence["known_concerns"] = feedback.get("concerns", [])
                intelligence["known_position"] = feedback.get("support_level", "unknown")
                intelligence["conditions"] = feedback.get("conditions", "")
                intelligence["resources_offered"] = feedback.get("resources_offered", "")
                intelligence["role"] = feedback.get("role", "")
                break

        return intelligence

    def _prepare_objections(self, pursuit_id: str, stakeholder_intel: Dict,
                           analysis: Dict) -> List[Dict]:
        """Prepare responses to likely objections."""
        objections = []

        # Address known concerns from target stakeholder first
        known_concerns = stakeholder_intel.get("known_concerns", [])
        for concern in known_concerns:
            objections.append({
                "objection": concern,
                "source": "your previous feedback",
                "priority": "high",
                "response_hint": f"Address '{concern}' directly - they raised this before"
            })

        # Address common concerns from all stakeholders
        if analysis:
            top_concerns = analysis.get("top_concerns", [])
            for concern_data in top_concerns:
                concern = concern_data.get("concern", "")
                if concern not in known_concerns:
                    objections.append({
                        "objection": concern,
                        "source": f"{concern_data.get('mentions', 1)} stakeholder(s)",
                        "priority": "medium",
                        "response_hint": f"Common concern - prepare clear mitigation"
                    })

        # Add fears from fear extractor
        if self.fear_extractor:
            fears = self.fear_extractor.get_prioritized_fears(pursuit_id)
            for fear in fears[:3]:  # Top 3 fears
                if fear.get("validation") == "confirmed":
                    fear_desc = fear.get("description", "")[:50]
                    if fear_desc not in str(objections):
                        objections.append({
                            "objection": fear_desc,
                            "source": "stakeholder-validated concern",
                            "priority": "high",
                            "response_hint": "Confirmed by stakeholders - address proactively"
                        })

        return objections[:7]  # Top 7 objections

    def _build_social_proof(self, analysis: Dict) -> Dict:
        """Build social proof from stakeholder support."""
        if not analysis:
            return {"available": False, "statement": ""}

        champions = analysis.get("champions", [])
        support_pct = analysis.get("support_percentage", 0)
        total = analysis.get("total_engaged", 0)

        proof = {
            "available": len(champions) > 0 or support_pct > 0.5,
            "champions": champions,
            "support_percentage": support_pct,
            "total_engaged": total,
            "statement": ""
        }

        if not proof["available"]:
            proof["statement"] = ""
            return proof

        # Generate statement
        if len(champions) == 1:
            c = champions[0]
            proof["statement"] = f"{c['name']} ({c['role']}) is supportive"
            if c.get("resources"):
                proof["statement"] += f" and has committed {c['resources']}"
        elif len(champions) >= 2:
            names = [c["name"] for c in champions[:2]]
            proof["statement"] = f"{names[0]} and {names[1]} are both supportive"
            if len(champions) > 2:
                proof["statement"] += f", along with {len(champions) - 2} other(s)"
        elif support_pct >= 0.5:
            proof["statement"] = f"{int(support_pct * 100)}% of {total} stakeholders engaged are supportive"

        return proof

    def _determine_emphasis(self, stakeholder_intel: Dict,
                           analysis: Dict) -> List[str]:
        """Determine what to emphasize based on stakeholder context."""
        emphasis = []

        # Check known position
        position = stakeholder_intel.get("known_position", "unknown")
        if position == "neutral":
            emphasis.append("value_proposition")
            emphasis.append("problem_severity")
        elif position == "conditional":
            emphasis.append("address_conditions")
            emphasis.append("risk_mitigation")
        elif position == "opposed":
            emphasis.append("listen_first")
            emphasis.append("address_concerns")

        # Check common concerns
        if analysis:
            concerns_text = str(analysis.get("top_concerns", [])).lower()

            if "timeline" in concerns_text or "time" in concerns_text:
                emphasis.append("realistic_timeline")
            if "cost" in concerns_text or "budget" in concerns_text:
                emphasis.append("budget_efficiency")
            if "technical" in concerns_text or "feasib" in concerns_text:
                emphasis.append("technical_feasibility")
            if "risk" in concerns_text:
                emphasis.append("risk_management")

        # Default emphasis if none determined
        if not emphasis:
            emphasis = ["value_proposition", "differentiation"]

        return list(set(emphasis))[:5]

    def _generate_key_messages(self, pursuit: Dict, analysis: Dict,
                              stakeholder_intel: Dict) -> List[str]:
        """Generate key messages for the pitch."""
        messages = []

        # Core value message
        title = pursuit.get("title", "the innovation")
        messages.append(f"Core: Why {title} matters now")

        # Support momentum message
        if analysis and analysis.get("support_percentage", 0) >= 0.5:
            pct = int(analysis["support_percentage"] * 100)
            messages.append(f"Momentum: {pct}% stakeholder support achieved")

        # Concerns addressed message
        if analysis and analysis.get("top_concerns"):
            top = analysis["top_concerns"][0]["concern"]
            messages.append(f"Proactive: How we're addressing {top}")

        # Resource efficiency message
        if analysis and analysis.get("resources_committed"):
            count = len(analysis["resources_committed"])
            messages.append(f"Resources: {count} stakeholder commitment(s) secured")

        # Personalized message for target
        if stakeholder_intel.get("previous_engagement"):
            messages.append(f"Personal: Building on our previous conversation")

        return messages[:5]

    def _identify_risk_warnings(self, analysis: Dict) -> List[str]:
        """Identify risks to flag before pitching."""
        warnings = []

        if not analysis:
            warnings.append("No stakeholder feedback captured - consider engaging first")
            return warnings

        # Low engagement warning
        if analysis.get("total_engaged", 0) < 3:
            warnings.append("Limited stakeholder engagement - feedback may not be representative")

        # Opposition warning
        blockers = analysis.get("blockers", [])
        if blockers:
            opposed = [b for b in blockers if b.get("type") == "opposed"]
            if opposed:
                warnings.append(f"{len(opposed)} stakeholder(s) actively opposed - address before pitch")

        # Low support warning
        if analysis.get("support_percentage", 0) < 0.5:
            warnings.append("Less than 50% support - consider building more consensus first")

        # Unaddressed concerns
        risks = analysis.get("risk_areas", [])
        high_risks = [r for r in risks if r.get("severity") == "high"]
        if high_risks:
            warnings.append(f"{len(high_risks)} high-priority risk(s) need attention")

        return warnings

    def _generate_pitch_structure(self, pursuit: Dict,
                                 stakeholder_intel: Dict) -> Dict:
        """Generate recommended pitch structure."""
        # Customize opening based on stakeholder relationship
        if stakeholder_intel.get("previous_engagement"):
            opening = "Acknowledge previous conversation and incorporate their feedback"
        else:
            opening = "Brief introduction and why you're meeting"

        structure = {
            "opening": opening,
            "sections": [
                {
                    "name": "Problem",
                    "duration": "2-3 min",
                    "key_point": "Establish urgency and relevance"
                },
                {
                    "name": "Solution",
                    "duration": "3-4 min",
                    "key_point": "How it addresses the problem uniquely"
                },
                {
                    "name": "Evidence",
                    "duration": "2-3 min",
                    "key_point": "Validation data and stakeholder support"
                },
                {
                    "name": "Ask",
                    "duration": "1-2 min",
                    "key_point": "Clear, specific request"
                },
                {
                    "name": "Discussion",
                    "duration": "5-10 min",
                    "key_point": "Listen and address concerns"
                }
            ],
            "closing": "Summarize key points and confirm next steps"
        }

        # Adjust for known concerns
        if stakeholder_intel.get("known_concerns"):
            structure["sections"].insert(3, {
                "name": "Addressing Concerns",
                "duration": "2-3 min",
                "key_point": f"Directly address: {', '.join(stakeholder_intel['known_concerns'][:2])}"
            })

        return structure

    def _get_basic_analysis(self, pursuit_id: str) -> Dict:
        """Get basic analysis when support_analyzer not available."""
        feedback_list = self.db.get_stakeholder_feedback_by_pursuit(pursuit_id)

        if not feedback_list:
            return {
                "total_engaged": 0,
                "support_percentage": 0,
                "consensus_readiness": 0,
                "top_concerns": [],
                "champions": [],
                "blockers": [],
                "resources_committed": [],
                "risk_areas": []
            }

        # Basic calculations
        total = len(feedback_list)
        supportive = sum(1 for f in feedback_list
                        if f.get("support_level") in ["supportive", "conditional"])

        return {
            "total_engaged": total,
            "support_percentage": supportive / total if total > 0 else 0,
            "consensus_readiness": 0.5,
            "top_concerns": [],
            "champions": [],
            "blockers": [],
            "resources_committed": [],
            "risk_areas": []
        }

    def _empty_preparation(self) -> Dict:
        """Return empty preparation structure."""
        return {
            "pitch_structure": {},
            "stakeholder_intelligence": {},
            "objection_preparation": [],
            "social_proof": {"available": False, "statement": ""},
            "emphasis_areas": [],
            "key_messages": [],
            "risk_warnings": ["Pursuit not found"],
            "support_context": {
                "total_engaged": 0,
                "support_percentage": 0,
                "consensus_readiness": 0
            }
        }

    def generate_pitch_summary(self, pursuit_id: str,
                              target_stakeholder: str = None) -> str:
        """
        Generate human-readable pitch preparation summary.

        Args:
            pursuit_id: Pursuit ID
            target_stakeholder: Optional target stakeholder name

        Returns:
            Summary text
        """
        prep = self.generate_pitch_preparation(pursuit_id, target_stakeholder)
        lines = []

        # Header
        if target_stakeholder:
            lines.append(f"**Pitch Preparation for {target_stakeholder}**\n")
        else:
            lines.append("**Pitch Preparation Summary**\n")

        # Support context
        ctx = prep["support_context"]
        if ctx["total_engaged"] > 0:
            lines.append(f"Support context: {ctx['total_engaged']} stakeholder(s), "
                        f"{int(ctx['support_percentage']*100)}% supportive\n")

        # Stakeholder intelligence
        intel = prep["stakeholder_intelligence"]
        if intel.get("previous_engagement"):
            lines.append(f"Previous engagement: {intel.get('known_position', 'unknown')} position")
            if intel.get("known_concerns"):
                lines.append(f"Known concerns: {', '.join(intel['known_concerns'][:3])}")

        # Key objections to prepare for
        objections = prep["objection_preparation"]
        if objections:
            lines.append("\n**Prepare for these objections:**")
            for obj in objections[:3]:
                lines.append(f"- {obj['objection']} ({obj['source']})")

        # Social proof
        proof = prep["social_proof"]
        if proof.get("available"):
            lines.append(f"\n**Social proof:** {proof['statement']}")

        # Emphasis areas
        emphasis = prep["emphasis_areas"]
        if emphasis:
            lines.append(f"\n**Emphasize:** {', '.join(emphasis[:3])}")

        # Warnings
        warnings = prep["risk_warnings"]
        if warnings:
            lines.append("\n**Warnings:**")
            for w in warnings[:2]:
                lines.append(f"- {w}")

        return "\n".join(lines)
