"""
InDE MVP v2.7 - Survey Data Processor

Handles ingestion of survey data from various formats (CSV, Excel, text).
Integrates results into:
1. Stakeholder feedback entries
2. Scaffolding element updates (vision validations, fears)
3. Evidence artifacts for traceability

Supports both structured (CSV/Excel) and unstructured (text/notes) input.
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import uuid

from config import SURVEY_CONFIG, SURVEY_INSIGHT_PROMPT


class SurveyProcessor:
    """
    Processes survey data files and integrates results into the pursuit context.
    """

    def __init__(self, llm_interface, database):
        """
        Initialize SurveyProcessor.

        Args:
            llm_interface: LLMInterface for insight extraction
            database: Database instance for storage
        """
        self.llm = llm_interface
        self.db = database
        self.config = SURVEY_CONFIG

    def process_file(self, file_path: str, pursuit_id: str,
                     user_id: str) -> Dict:
        """
        Main entry point - process uploaded survey file.

        Args:
            file_path: Path to uploaded file
            pursuit_id: Pursuit to associate data with
            user_id: User who uploaded

        Returns:
            {
                "success": bool,
                "response_count": int,
                "stakeholder_entries_created": int,
                "insights": {...},
                "evidence_artifact_id": str,
                "summary": str
            }
        """
        if not os.path.exists(file_path):
            return {"success": False, "error": "File not found"}

        # Get file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if ext not in self.config["supported_formats"]:
            return {
                "success": False,
                "error": f"Unsupported file format: {ext}. Supported: {self.config['supported_formats']}"
            }

        # Check file size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > self.config["max_file_size_mb"]:
            return {
                "success": False,
                "error": f"File too large ({file_size_mb:.1f}MB). Max: {self.config['max_file_size_mb']}MB"
            }

        # Parse based on file type
        if ext in [".csv", ".xlsx", ".xls"]:
            try:
                parsed_data, raw_text = self._parse_structured(file_path, ext)
            except ImportError as e:
                return {"success": False, "error": str(e)}
            is_structured = True
        else:
            parsed_data = None
            raw_text = self._parse_text(file_path)
            is_structured = False

        # Get pursuit context for insight extraction
        pursuit = self.db.get_pursuit(pursuit_id)
        pursuit_title = pursuit.get("title", "Unknown") if pursuit else "Unknown"

        # Get vision summary for context
        vision_summary = self._get_vision_summary(pursuit_id)

        # Extract insights via LLM
        insights = self._extract_insights(
            raw_text if not is_structured else self._data_to_text(parsed_data),
            pursuit_title,
            vision_summary
        )

        # Create stakeholder feedback entries
        stakeholder_count = 0
        if is_structured and parsed_data:
            stakeholder_count = self._create_stakeholder_entries(
                parsed_data, pursuit_id
            )
        elif not is_structured and raw_text:
            # For text files, try to extract stakeholder info via LLM
            stakeholder_count = self._extract_stakeholders_from_text(
                raw_text, pursuit_id, os.path.basename(file_path)
            )

        # Update scaffolding elements based on insights
        self._update_scaffolding_from_insights(pursuit_id, insights)

        # Create evidence artifact
        evidence_id = self._create_evidence_artifact(
            pursuit_id=pursuit_id,
            raw_data=parsed_data if is_structured else raw_text,
            insights=insights,
            source_filename=os.path.basename(file_path),
            response_count=len(parsed_data) if parsed_data else 0
        )

        # Build summary response
        summary = self._build_summary(
            response_count=len(parsed_data) if parsed_data else 0,
            stakeholder_count=stakeholder_count,
            insights=insights,
            is_structured=is_structured
        )

        return {
            "success": True,
            "response_count": len(parsed_data) if parsed_data else 0,
            "stakeholder_entries_created": stakeholder_count,
            "insights": insights,
            "evidence_artifact_id": evidence_id,
            "summary": summary
        }

    def _parse_structured(self, file_path: str, ext: str) -> Tuple[List[Dict], str]:
        """
        Parse CSV or Excel file into list of response dicts.

        Returns:
            (list of response dicts, raw text representation)
        """
        try:
            import pandas as pd

            if ext == ".csv":
                df = pd.read_csv(file_path)
            else:
                # Excel files require openpyxl
                try:
                    df = pd.read_excel(file_path, engine='openpyxl')
                except ImportError as e:
                    raise ImportError(
                        f"Excel file support requires 'openpyxl'. "
                        f"Install it with: pip install openpyxl"
                    ) from e

            # Normalize column names
            df.columns = [str(c).lower().strip() for c in df.columns]

            # Map columns to standard names
            column_map = self._detect_column_mapping(df.columns.tolist())

            # Convert to list of dicts with standardized keys
            responses = []
            for _, row in df.iterrows():
                response = {}
                for std_name, col_name in column_map.items():
                    if col_name and col_name in df.columns:
                        value = row[col_name]
                        # Handle NaN values
                        if pd.isna(value):
                            value = None
                        elif isinstance(value, (int, float)):
                            value = str(value) if std_name != "support" else value
                        else:
                            value = str(value).strip()
                        response[std_name] = value

                # Include any unmapped columns as additional data
                for col in df.columns:
                    if col not in column_map.values() and col not in response:
                        value = row[col]
                        if not pd.isna(value):
                            response[col] = str(value).strip()

                responses.append(response)

            # Create text representation for LLM analysis
            raw_text = df.to_string()

            return responses, raw_text

        except ImportError as e:
            # Check if it's an openpyxl error (for Excel files)
            if "openpyxl" in str(e):
                print(f"[SurveyProcessor] {e}")
                raise  # Re-raise to give user a clear error message
            # Otherwise it's pandas missing, fall back to CSV parsing
            print("[SurveyProcessor] pandas not available, falling back to basic CSV parsing")
            if ext == ".csv":
                return self._parse_csv_basic(file_path)
            else:
                # Can't parse Excel without pandas
                raise ImportError(
                    f"Excel file support requires 'pandas' and 'openpyxl'. "
                    f"Install with: pip install pandas openpyxl"
                )
        except Exception as e:
            print(f"[SurveyProcessor] Error parsing structured file: {e}")
            return [], ""

    def _parse_csv_basic(self, file_path: str) -> Tuple[List[Dict], str]:
        """Basic CSV parsing without pandas."""
        import csv

        responses = []
        raw_lines = []

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize keys
                normalized = {k.lower().strip(): v.strip() if v else None
                              for k, v in row.items()}
                responses.append(normalized)
                raw_lines.append(str(row))

        return responses, "\n".join(raw_lines)

    def _parse_text(self, file_path: str) -> str:
        """Parse text/markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"[SurveyProcessor] Error reading text file: {e}")
            return ""

    def _detect_column_mapping(self, columns: List[str]) -> Dict[str, str]:
        """
        Detect which columns map to standard field names.

        Returns:
            {standard_name: actual_column_name}
        """
        mappings = self.config["column_mappings"]
        result = {}

        for std_name, variations in mappings.items():
            for col in columns:
                if col in variations or any(v in col for v in variations):
                    result[std_name] = col
                    break

        return result

    def _data_to_text(self, data: List[Dict]) -> str:
        """Convert structured data to text for LLM analysis."""
        if not data:
            return ""

        lines = []
        for i, row in enumerate(data, 1):
            parts = [f"Response {i}:"]
            for key, value in row.items():
                if value:
                    parts.append(f"  {key}: {value}")
            lines.append("\n".join(parts))

        return "\n\n".join(lines)

    def _get_vision_summary(self, pursuit_id: str) -> str:
        """Get brief vision summary for context."""
        state = self.db.get_scaffolding_state(pursuit_id)
        if not state:
            return "Not yet defined"

        vision = state.get("vision_elements", {})
        parts = []

        if vision.get("problem_statement", {}).get("text"):
            parts.append(f"Problem: {vision['problem_statement']['text'][:100]}")
        if vision.get("solution_concept", {}).get("text"):
            parts.append(f"Solution: {vision['solution_concept']['text'][:100]}")

        return " | ".join(parts) if parts else "Vision in development"

    def _extract_insights(self, survey_text: str, pursuit_title: str,
                          vision_summary: str) -> Dict:
        """Use LLM to extract insights from survey data."""
        if not survey_text.strip():
            return {
                "themes": [],
                "vision_validations": [],
                "fears_insights": [],
                "hypothesis_refinements": [],
                "support_summary": {}
            }

        prompt = SURVEY_INSIGHT_PROMPT.format(
            pursuit_title=pursuit_title,
            vision_summary=vision_summary,
            survey_data=survey_text[:4000]  # Limit to avoid token overflow
        )

        try:
            response = self.llm.call_llm(
                prompt=prompt,
                max_tokens=1000,
                system="You are a survey analysis expert. Respond only with valid JSON."
            )

            # Parse JSON response
            text = response.strip()
            if text.startswith("```"):
                text = re.sub(r"```json?\s*", "", text)
                text = re.sub(r"```\s*$", "", text)

            return json.loads(text)

        except Exception as e:
            print(f"[SurveyProcessor] Insight extraction failed: {e}")
            return {
                "themes": [],
                "vision_validations": [],
                "fears_insights": [],
                "hypothesis_refinements": [],
                "support_summary": {},
                "error": str(e)
            }

    def _create_stakeholder_entries(self, data: List[Dict],
                                     pursuit_id: str) -> int:
        """Create stakeholder feedback entries from structured data."""
        created = 0

        for row in data:
            # Need at least a name to create entry
            name = row.get("name")
            if not name:
                continue

            # Map support level
            support_raw = row.get("support")
            support_level = self._map_support_level(support_raw)

            # Parse concerns (might be semicolon or comma separated)
            concerns_raw = row.get("concerns", "")
            concerns = []
            if concerns_raw:
                # Split by semicolon or comma
                concerns = [c.strip() for c in re.split(r'[;,]', concerns_raw)
                            if c.strip()]

            # Create feedback entry
            feedback = {
                "feedback_id": str(uuid.uuid4()),
                "pursuit_id": pursuit_id,
                "stakeholder_name": name,
                "role": row.get("role", "Survey Respondent"),
                "organization": row.get("organization"),
                "support_level": support_level,
                "concerns": concerns,
                "capture_method": "survey_import",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

            # Add any additional fields from the row
            for key, value in row.items():
                if key not in ["name", "role", "organization", "support", "concerns"]:
                    if value and key not in feedback:
                        feedback[f"survey_{key}"] = value

            try:
                self.db.db.stakeholder_feedback.insert_one(feedback)
                created += 1
            except Exception as e:
                print(f"[SurveyProcessor] Failed to create stakeholder entry: {e}")

        return created

    def _extract_stakeholders_from_text(self, text: str, pursuit_id: str,
                                         source_filename: str) -> int:
        """
        Extract stakeholder information from unstructured text via LLM.

        Args:
            text: Raw text content
            pursuit_id: Pursuit to associate with
            source_filename: Source file name for tracking

        Returns:
            Number of stakeholder entries created
        """
        if not text.strip():
            return 0

        prompt = """Analyze this document and extract any stakeholder feedback or positions mentioned.

DOCUMENT:
{text}

For each person or role mentioned with a position/feedback on the topic, extract:
- name: The person's name (or role if name not given)
- role: Their role/title
- organization: Their organization (if mentioned)
- support_level: supportive, conditional, neutral, opposed, or unclear
- concerns: Any concerns or objections they raised
- conditions: Any conditions for their support

Respond in JSON only:
{{
    "stakeholders": [
        {{
            "name": "Name or Role",
            "role": "Title/Position",
            "organization": "Org name or empty string",
            "support_level": "supportive|conditional|neutral|opposed|unclear",
            "concerns": ["concern1", "concern2"],
            "conditions": "conditions text or empty string"
        }}
    ]
}}

If no stakeholders are identifiable, return: {{"stakeholders": []}}
""".format(text=text[:3000])  # Limit to avoid token overflow

        try:
            response = self.llm.call_llm(
                prompt=prompt,
                max_tokens=1000,
                system="You are an expert at extracting stakeholder information from documents. Respond only with valid JSON."
            )

            # Parse JSON response
            response_text = response.strip()
            if response_text.startswith("```"):
                response_text = re.sub(r"```json?\s*", "", response_text)
                response_text = re.sub(r"```\s*$", "", response_text)

            result = json.loads(response_text)
            stakeholders = result.get("stakeholders", [])

            created = 0
            for sh in stakeholders:
                name = sh.get("name", "").strip()
                if not name:
                    continue

                concerns = sh.get("concerns", [])
                if isinstance(concerns, str):
                    concerns = [concerns] if concerns else []

                feedback = {
                    "feedback_id": str(uuid.uuid4()),
                    "pursuit_id": pursuit_id,
                    "stakeholder_name": name,
                    "role": sh.get("role", "Unknown"),
                    "organization": sh.get("organization", ""),
                    "support_level": sh.get("support_level", "unclear").lower(),
                    "concerns": concerns,
                    "conditions": sh.get("conditions", ""),
                    "capture_method": "document_extraction",
                    "source_document": source_filename,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }

                try:
                    self.db.db.stakeholder_feedback.insert_one(feedback)
                    created += 1
                except Exception as e:
                    print(f"[SurveyProcessor] Failed to create stakeholder entry: {e}")

            print(f"[SurveyProcessor] Extracted {created} stakeholders from text")
            return created

        except Exception as e:
            print(f"[SurveyProcessor] Stakeholder extraction from text failed: {e}")
            return 0

    def _map_support_level(self, value) -> str:
        """Map raw support value to standard support level."""
        if value is None:
            return "unclear"

        # Handle numeric
        if isinstance(value, (int, float)):
            mapping = self.config["support_level_mapping"]
            rounded = round(value)
            return mapping.get(rounded, "neutral")

        # Handle text
        value_lower = str(value).lower().strip()
        text_mapping = self.config["text_support_mapping"]

        for text, level in text_mapping.items():
            if text in value_lower:
                return level

        # Check for direct level names
        if value_lower in ["supportive", "conditional", "neutral", "opposed", "unclear"]:
            return value_lower

        return "unclear"

    def _update_scaffolding_from_insights(self, pursuit_id: str,
                                           insights: Dict) -> None:
        """Update scaffolding elements based on extracted insights."""
        # Update fears from insights
        fears_insights = insights.get("fears_insights", [])
        if fears_insights:
            # Combine into market_fears element
            fear_text = "\n".join([
                f"- {f.get('concern', '')} (frequency: {f.get('frequency', 'N/A')}, severity: {f.get('severity', 'unknown')})"
                for f in fears_insights[:5]  # Limit to top 5
            ])

            if fear_text:
                self.db.update_scaffolding_element(
                    pursuit_id, "fears", "market_fears",
                    f"From survey data:\n{fear_text}",
                    confidence=0.7
                )

        # Update vision validation signals (as early_validation important element)
        validations = insights.get("vision_validations", [])
        if validations:
            validation_text = "\n".join([
                f"- {v.get('signal', '')} (strength: {v.get('strength', 'unknown')}, n={v.get('source_count', '?')})"
                for v in validations[:5]
            ])

            if validation_text:
                # Store as important element
                self.db.update_important_element(
                    pursuit_id, "early_validation",
                    f"Survey validation signals:\n{validation_text}",
                    confidence=0.75,
                    extraction_method="survey"
                )

    def _create_evidence_artifact(self, pursuit_id: str, raw_data,
                                   insights: Dict, source_filename: str,
                                   response_count: int) -> str:
        """Create evidence artifact with survey data and insights."""
        artifact_id = str(uuid.uuid4())

        artifact = {
            "artifact_id": artifact_id,
            "pursuit_id": pursuit_id,
            "type": "evidence",
            "evidence_type": "survey_results",
            "source_filename": source_filename,
            "response_count": response_count,
            "raw_data": raw_data if isinstance(raw_data, str) else json.dumps(raw_data, default=str),
            "processed_insights": insights,
            "created_at": datetime.now(timezone.utc),
            # Add standard artifact fields for consistency
            "version": 1,
            "status": "CURRENT"
        }

        try:
            self.db.db.artifacts.insert_one(artifact)
            # Also add to pursuit's artifact_ids
            self.db.add_artifact_to_pursuit(pursuit_id, artifact_id)
            print(f"[SurveyProcessor] Created evidence artifact: {artifact_id}")
        except Exception as e:
            print(f"[SurveyProcessor] Failed to create evidence artifact: {e}")
            return None

        return artifact_id

    def _build_summary(self, response_count: int, stakeholder_count: int,
                       insights: Dict, is_structured: bool) -> str:
        """Build human-readable summary of processing results."""
        parts = []

        if is_structured:
            parts.append(f"I've processed your survey data with **{response_count} responses**.")
            if stakeholder_count > 0:
                parts.append(f"Created **{stakeholder_count} stakeholder feedback entries**.")
        else:
            parts.append("I've analyzed your survey notes.")

        # Themes
        themes = insights.get("themes", [])
        if themes:
            parts.append(f"\n**Key Themes:** {', '.join(themes[:3])}")

        # Support summary
        support = insights.get("support_summary", {})
        if support:
            sentiment = support.get("overall_sentiment", "mixed")
            supportive = support.get("supportive_count", 0)
            opposed = support.get("opposed_count", 0)
            parts.append(f"\n**Support Distribution:** {supportive} supportive, {opposed} opposed (overall: {sentiment})")

            conditions = support.get("key_conditions", [])
            if conditions:
                parts.append(f"Key conditions: {', '.join(conditions[:2])}")

        # Fears
        fears = insights.get("fears_insights", [])
        if fears:
            top_concern = fears[0].get("concern", "") if fears else ""
            if top_concern:
                parts.append(f"\n**Top Concern:** {top_concern}")

        # Validation signals
        validations = insights.get("vision_validations", [])
        if validations:
            strong = [v for v in validations if v.get("strength") == "strong"]
            if strong:
                parts.append(f"\n**Strong Validation:** {strong[0].get('signal', '')}")

        parts.append("\nThis data has been saved as evidence and integrated into your pursuit context.")

        return "\n".join(parts)
