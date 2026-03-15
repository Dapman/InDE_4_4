"""
InDE MVP v3.7.1 - Artifact Generator

Generates formal artifacts from tracked scaffolding elements.
Only generates when completeness >= 75% (threshold configurable).

Artifact Types:
- Vision: Problem, target user, solution concept, value proposition, etc.
- Fears: Capability, market, resource, timing, competition, personal concerns
- Hypothesis: Assumptions, predictions, test methods, success metrics
- Experiment: Data collection sheets, tracking forms for RVE experiments (v3.7.1)
"""

from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
import logging

from config import (
    READINESS_THRESHOLD, CRITICAL_ELEMENTS,
    VISION_TEMPLATE, FEARS_TEMPLATE, HYPOTHESIS_TEMPLATE,
    ARTIFACT_GENERATION_PROMPT
)
from api.user_discovery import update_checklist_item_sync

logger = logging.getLogger(__name__)


class ArtifactGenerator:
    """
    Generates formal artifacts from tracked scaffolding elements.
    Only generates when completeness >= 75% of critical elements present.
    """

    def __init__(self, llm_interface, database):
        """
        Initialize ArtifactGenerator.

        Args:
            llm_interface: LLMInterface instance for Claude API calls
            database: Database instance for persistence
        """
        self.llm = llm_interface
        self.db = database

    def can_generate(self, pursuit_id: str, artifact_type: str) -> Tuple[bool, float, List[str]]:
        """
        Check if artifact is ready to generate.

        Args:
            pursuit_id: Pursuit ID
            artifact_type: 'vision', 'fears', or 'hypothesis'

        Returns:
            (ready: bool, completeness: float, missing: list)
        """
        completeness = self.db.get_element_completeness(pursuit_id)

        # Map artifact_type to completeness key
        key = artifact_type if artifact_type != "fears" else "fears"
        comp_value = completeness.get(key, 0.0)

        missing = self.db.get_missing_elements(pursuit_id, artifact_type)

        ready = comp_value >= READINESS_THRESHOLD

        return ready, comp_value, missing

    def generate_artifact(self, pursuit_id: str, artifact_type: str,
                          method: str = "automatic") -> Optional[Dict]:
        """
        Generate formal artifact from scaffolding elements.

        Args:
            pursuit_id: Pursuit ID
            artifact_type: 'vision', 'fears', 'hypothesis', or 'experiment'
            method: 'automatic' or 'user_requested'

        Returns:
            {
                "artifact_id": "uuid",
                "type": "vision" | "fears" | "hypothesis" | "experiment",
                "content": "formatted artifact text",
                "metadata": {...}
            }
            or None if generation fails
        """
        # Get pursuit for title
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            print(f"[ArtifactGenerator] Pursuit not found: {pursuit_id}")
            return None

        title = pursuit.get("title", "Untitled Pursuit")

        # v3.7.1: Handle experiment artifact type specially
        if artifact_type == "experiment":
            return self._generate_experiment_artifact(pursuit_id, title, method)

        # Get present elements
        elements = self.db.get_present_elements(pursuit_id, artifact_type)

        if not elements:
            print(f"[ArtifactGenerator] No elements found for {artifact_type}")
            return None

        # Generate artifact content
        try:
            content = self._generate_content(artifact_type, title, elements)
        except Exception as e:
            print(f"[ArtifactGenerator] Generation failed: {e}")
            return None

        # Calculate completeness
        completeness = self.db.get_element_completeness(pursuit_id)
        comp_key = artifact_type if artifact_type != "fears" else "fears"
        comp_value = completeness.get(comp_key, 0.0)

        # Store artifact
        artifact = self.db.create_artifact(
            pursuit_id=pursuit_id,
            artifact_type=artifact_type,
            content=content,
            elements_used=list(elements.keys()),
            completeness=comp_value,
            generation_method=method
        )

        logger.info(f"Created {artifact_type} artifact: {artifact['artifact_id']}")

        # v3.16: Update Getting Started checklist
        try:
            user_id = pursuit.get("user_id")
            if user_id:
                if artifact_type == "vision":
                    update_checklist_item_sync(user_id, "vision_created")
                elif artifact_type == "fears":
                    update_checklist_item_sync(user_id, "fear_identified")
                # Any artifact counts as first artifact generated
                update_checklist_item_sync(user_id, "first_artifact_generated")
        except Exception as e:
            logger.warning(f"Discovery checklist update failed: {e}")

        return artifact

    def _generate_content(self, artifact_type: str, title: str,
                          elements: Dict[str, str]) -> str:
        """Generate artifact content using template and LLM polish."""

        # First, fill template with available elements
        template_content = self._fill_template(artifact_type, title, elements)

        # Use LLM to polish and make coherent
        template_map = {
            "vision": VISION_TEMPLATE,
            "fears": FEARS_TEMPLATE,
            "hypothesis": HYPOTHESIS_TEMPLATE
        }

        try:
            polished = self._llm_polish_artifact(
                artifact_type, template_content, elements
            )
            return polished
        except Exception as e:
            print(f"[ArtifactGenerator] LLM polish failed, using template: {e}")
            return template_content

    def _fill_template(self, artifact_type: str, title: str,
                       elements: Dict[str, str]) -> str:
        """Fill artifact template with available elements."""

        if artifact_type == "vision":
            return self._fill_vision_template(title, elements)
        elif artifact_type == "fears":
            return self._fill_fears_template(title, elements)
        elif artifact_type == "hypothesis":
            return self._fill_hypothesis_template(title, elements)
        else:
            return f"# {artifact_type.title()}: {title}\n\n" + "\n\n".join(
                f"## {k.replace('_', ' ').title()}\n{v}" for k, v in elements.items()
            )

    def _fill_vision_template(self, title: str, elements: Dict[str, str]) -> str:
        """Fill vision template."""
        return f"""# Vision: {title}

## Problem
{elements.get('problem_statement', '_Not yet defined_')}

## Target User
{elements.get('target_user', '_Not yet defined_')}

## Current Situation
{elements.get('current_situation', '_Not yet defined_')}

## Pain Points
{elements.get('pain_points', '_Not yet defined_')}

## Solution Concept
{elements.get('solution_concept', '_Not yet defined_')}

## Value Proposition
{elements.get('value_proposition', '_Not yet defined_')}

## Differentiation
{elements.get('differentiation', '_Not yet defined_')}

## Success Criteria
{elements.get('success_criteria', '_Not yet defined_')}"""

    def _fill_fears_template(self, title: str, elements: Dict[str, str]) -> str:
        """Fill fears template."""
        return f"""# Fears & Concerns: {title}

## Capability Concerns
{elements.get('capability_fears', '_None identified_')}

## Market Concerns
{elements.get('market_fears', '_None identified_')}

## Resource Concerns
{elements.get('resource_fears', '_None identified_')}

## Timing Concerns
{elements.get('timing_fears', '_None identified_')}

## Competition Concerns
{elements.get('competition_fears', '_None identified_')}

## Personal Concerns
{elements.get('personal_fears', '_None identified_')}"""

    def _fill_hypothesis_template(self, title: str, elements: Dict[str, str]) -> str:
        """Fill hypothesis template."""
        return f"""# Key Hypothesis: {title}

## Core Assumption
{elements.get('assumption_statement', '_Not yet defined_')}

## Testable Prediction
{elements.get('testable_prediction', '_Not yet defined_')}

## Test Method
{elements.get('test_method', '_Not yet defined_')}

## Success Metric
{elements.get('success_metric', '_Not yet defined_')}

## Failure Criteria
{elements.get('failure_criteria', '_Not yet defined_')}

## Learning Plan
{elements.get('learning_plan', '_Not yet defined_')}"""

    def _llm_polish_artifact(self, artifact_type: str,
                             template_content: str,
                             elements: Dict[str, str]) -> str:
        """Use LLM to polish and make artifact coherent."""

        # Build elements JSON for context
        elements_json = "\n".join(
            f"- {k.replace('_', ' ').title()}: {v}"
            for k, v in elements.items() if v
        )

        prompt = f"""Polish this {artifact_type} artifact to be clear, professional, and coherent.

Current content:
{template_content}

Available elements:
{elements_json}

Requirements:
1. Keep the markdown structure (headers, sections)
2. Make each section flow naturally
3. Replace any "_Not yet defined_" placeholders with brief, appropriate placeholder text
4. Ensure consistency in tone and style
5. Keep it concise - this is a working document, not a final presentation

Return only the polished artifact content in markdown format."""

        response = self.llm.call_llm(
            prompt=prompt,
            max_tokens=1000,
            system="You are a document editor. Return only the polished document."
        )

        return response.strip()

    def get_artifact_preview(self, pursuit_id: str, artifact_type: str) -> str:
        """
        Get a preview of what the artifact would look like.
        Useful for showing user before they confirm generation.
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        title = pursuit.get("title", "Untitled") if pursuit else "Untitled"

        elements = self.db.get_present_elements(pursuit_id, artifact_type)
        missing = self.db.get_missing_elements(pursuit_id, artifact_type)

        preview = self._fill_template(artifact_type, title, elements)

        if missing:
            preview += f"\n\n---\n_Missing elements: {', '.join(missing)}_"

        return preview

    # =========================================================================
    # v3.7.1: EXPERIMENT ARTIFACT GENERATION
    # =========================================================================

    def _generate_experiment_artifact(self, pursuit_id: str, title: str,
                                       method: str) -> Optional[Dict]:
        """
        v3.7.1: Generate a data collection sheet artifact for experiments.

        Pulls from validation_experiments collection and hypothesis elements
        to create a structured data collection form.

        Args:
            pursuit_id: Pursuit ID
            title: Pursuit title
            method: Generation method

        Returns:
            Artifact dict or None
        """
        # Get active/recent experiments for this pursuit
        experiments = self._get_pursuit_experiments(pursuit_id)

        # Get hypothesis elements for context
        hypothesis_elements = self.db.get_present_elements(pursuit_id, "hypothesis")

        # If no experiments, try to create from hypothesis
        if not experiments and not hypothesis_elements:
            print(f"[ArtifactGenerator] No experiments or hypotheses for experiment artifact")
            return None

        # Generate content
        try:
            content = self._generate_experiment_content(
                title, experiments, hypothesis_elements
            )
        except Exception as e:
            print(f"[ArtifactGenerator] Experiment artifact generation failed: {e}")
            return None

        # Store artifact
        artifact = self.db.create_artifact(
            pursuit_id=pursuit_id,
            artifact_type="experiment",
            content=content,
            elements_used=["experiment_design", "data_collection"],
            completeness=1.0,  # Experiment artifacts are always complete
            generation_method=method
        )

        print(f"[ArtifactGenerator] Created experiment artifact: {artifact['artifact_id']}")

        return artifact

    def _get_pursuit_experiments(self, pursuit_id: str) -> List[Dict]:
        """Get experiments from validation_experiments collection."""
        try:
            # Try to get from validation_experiments collection
            experiments = list(self.db.db.validation_experiments.find(
                {"pursuit_id": pursuit_id},
                sort=[("created_at", -1)],
                limit=5
            ))
            return experiments
        except Exception as e:
            print(f"[ArtifactGenerator] Error getting experiments: {e}")
            return []

    def _generate_experiment_content(self, title: str, experiments: List[Dict],
                                      hypothesis_elements: Dict[str, str]) -> str:
        """Generate data collection sheet content."""

        # Build experiment context
        experiment_context = ""
        if experiments:
            for i, exp in enumerate(experiments, 1):
                experiment_context += f"""
### Experiment {i}: {exp.get('name', 'Unnamed')}
- **Hypothesis**: {exp.get('hypothesis', 'Not specified')}
- **Method**: {exp.get('methodology', 'Not specified')}
- **Target Sample Size**: {exp.get('target_sample_size', 'Not specified')}
- **Success Criteria**: {exp.get('success_criteria', 'Not specified')}
"""

        # Build hypothesis context
        hypothesis_context = ""
        if hypothesis_elements:
            if hypothesis_elements.get('assumption_statement'):
                hypothesis_context += f"\n- **Core Assumption**: {hypothesis_elements['assumption_statement']}"
            if hypothesis_elements.get('testable_prediction'):
                hypothesis_context += f"\n- **Prediction**: {hypothesis_elements['testable_prediction']}"
            if hypothesis_elements.get('success_metric'):
                hypothesis_context += f"\n- **Success Metric**: {hypothesis_elements['success_metric']}"

        # Generate the data collection sheet using LLM
        prompt = f"""Create a professional data collection sheet for validating this innovation.

PURSUIT: {title}

EXPERIMENTS DESIGNED:
{experiment_context if experiment_context else "No formal experiments yet - create a general validation tracking sheet."}

HYPOTHESIS CONTEXT:
{hypothesis_context if hypothesis_context else "No formal hypothesis yet - create a flexible data collection form."}

Generate a markdown data collection sheet that includes:

1. **Header Section**
   - Title: "Data Collection Sheet: [pursuit name]"
   - Date field
   - Collector name field
   - Session/Participant ID field

2. **Experiment Details**
   - Which hypothesis being tested
   - Expected outcome

3. **Data Collection Table**
   - Numbered rows for recording observations
   - Columns appropriate for the experiment type (e.g., Observation #, Date/Time, Response/Measurement, Notes)

4. **Qualitative Notes Section**
   - Open text area for observations
   - Unexpected findings

5. **Summary Section**
   - Total responses/observations
   - Preliminary assessment (supports/challenges/inconclusive)
   - Next steps

Make it practical and ready to use. Use markdown table format for the data collection area.
Return only the markdown content."""

        response = self.llm.call_llm(
            prompt=prompt,
            max_tokens=1500,
            system="You are a research methods specialist. Create clear, practical data collection forms."
        )

        return response.strip()

    def generate_experiment_artifact_from_context(self, pursuit_id: str,
                                                    context: Dict) -> Optional[Dict]:
        """
        v3.7.1: Generate experiment artifact from conversation context.

        This is called when the coaching layer has already designed an
        experiment and described it in conversation.

        Args:
            pursuit_id: Pursuit ID
            context: Dict with experiment details from conversation

        Returns:
            Artifact dict or None
        """
        pursuit = self.db.get_pursuit(pursuit_id)
        if not pursuit:
            return None

        title = pursuit.get("title", "Untitled Pursuit")

        # Build content from context
        content = self._fill_experiment_template_from_context(title, context)

        # Store artifact
        artifact = self.db.create_artifact(
            pursuit_id=pursuit_id,
            artifact_type="experiment",
            content=content,
            elements_used=["experiment_design", "data_collection"],
            completeness=1.0,
            generation_method="context_based"
        )

        return artifact

    def _fill_experiment_template_from_context(self, title: str,
                                                 context: Dict) -> str:
        """Fill experiment template from conversation context."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        return f"""# Data Collection Sheet: {title}

## Session Information
- **Date**: {now}
- **Collector Name**: _______________
- **Session/Participant ID**: _______________

## Experiment Details
- **Hypothesis Being Tested**: {context.get('hypothesis', 'To be validated')}
- **Method**: {context.get('method', 'As designed')}
- **Expected Outcome**: {context.get('expected_outcome', 'TBD')}

## Data Collection

| # | Date/Time | Observation/Response | Measurement | Notes |
|---|-----------|---------------------|-------------|-------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |
| 6 | | | | |
| 7 | | | | |
| 8 | | | | |
| 9 | | | | |
| 10 | | | | |

## Qualitative Notes

### Observations
_Record any patterns, unexpected findings, or contextual factors..._




### Participant Quotes/Feedback
_Notable quotes or direct feedback..._




## Summary

- **Total Observations**: ___
- **Preliminary Assessment**: [ ] Supports hypothesis  [ ] Challenges hypothesis  [ ] Inconclusive
- **Confidence Level**: [ ] High  [ ] Medium  [ ] Low
- **Recommended Next Steps**:




---
_Generated by InDE v3.7.1 | Data collection artifact for validation tracking_
"""
