"""
InDE MVP v3.10 - Relative Date Recalculator

TD-005: Manages the lifecycle of milestones extracted from relative date expressions.

When a user says "next quarter", "in six weeks", or "end of year", this module:
1. Resolves the expression to an absolute date based on extraction timestamp
2. Stores the original expression and resolution method
3. Flags the milestone for confirmation (requires_recalculation=True)
4. After 7+ days without confirmation, prompts the user to verify

Confirmed dates graduate from date_precision="relative" to date_precision="exact"
"""

import logging
from calendar import monthrange
from datetime import datetime, date, timedelta, timezone
from typing import Optional, Tuple, List, Dict, Any

from config import (
    RELATIVE_DATE_PROMPT_THRESHOLD_DAYS,
    RELATIVE_RESOLUTION_QUARTER_END,
    RELATIVE_RESOLUTION_QUARTER_START,
    RELATIVE_RESOLUTION_MONTH_END,
    RELATIVE_RESOLUTION_WEEK_END,
    RELATIVE_RESOLUTION_ESTIMATED
)

logger = logging.getLogger(__name__)


class RelativeDateRecalculator:
    """
    Handles resolution and confirmation of relative date expressions.

    Common expressions:
    - "next quarter", "end of Q2" -> quarter_end
    - "end of month", "this month" -> month_end
    - "next week", "this week" -> week_end
    - "in six weeks", "about 3 months" -> estimated
    - "end of year" -> quarter_end (Dec 31)
    """

    # Text numbers for parsing expressions like "six weeks"
    TEXT_NUMBERS = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "fourteen": 14, "sixteen": 16,
        "eighteen": 18, "twenty": 20, "thirty": 30
    }

    def __init__(self):
        self.prompt_threshold_days = RELATIVE_DATE_PROMPT_THRESHOLD_DAYS

    def resolve_relative_expression(
        self,
        expression: str,
        extraction_timestamp: str
    ) -> Tuple[str, str, str]:
        """
        Resolve a relative date expression to an absolute date.

        Args:
            expression: e.g., "next quarter", "in six weeks", "end of year"
            extraction_timestamp: ISO timestamp of when the expression was captured

        Returns:
            Tuple of (resolved_date_str, resolution_method, date_precision)
            resolved_date_str: "YYYY-MM-DD"
            resolution_method: "quarter_end" | "quarter_start" | "month_end" | "week_end" | "estimated"
            date_precision: always "relative" (stays relative until confirmed)
        """
        ref_date = self._parse_timestamp(extraction_timestamp) or date.today()
        expression_lower = expression.lower().strip()

        resolved, method = self._resolve(expression_lower, ref_date)
        logger.info(
            f"[RelativeDateRecalculator] Resolved '{expression}' -> {resolved} ({method})"
        )

        return str(resolved), method, "relative"

    def _resolve(self, expr: str, ref: date) -> Tuple[date, str]:
        """Core resolution logic."""

        # Quarter-end patterns
        if any(p in expr for p in ["next quarter", "end of quarter", "end of q"]):
            return self._quarter_end(ref, offset=1), RELATIVE_RESOLUTION_QUARTER_END
        if any(p in expr for p in ["this quarter", "current quarter"]):
            return self._quarter_end(ref, offset=0), RELATIVE_RESOLUTION_QUARTER_END

        # Specific quarter patterns (Q1, Q2, Q3, Q4)
        for q in range(1, 5):
            if f"q{q}" in expr or f"quarter {q}" in expr:
                return self._specific_quarter_end(ref.year, q), RELATIVE_RESOLUTION_QUARTER_END

        # Month-end patterns
        if "end of next month" in expr:
            next_month = self._add_months(ref, 1)
            return self._month_end(next_month), RELATIVE_RESOLUTION_MONTH_END
        if "end of month" in expr or "this month" in expr:
            return self._month_end(ref), RELATIVE_RESOLUTION_MONTH_END

        # Week patterns
        if "next week" in expr:
            days_ahead = 7 - ref.weekday() + 4  # Next Friday
            return ref + timedelta(days=days_ahead), RELATIVE_RESOLUTION_WEEK_END
        if "this week" in expr or "end of week" in expr:
            days_until_friday = 4 - ref.weekday()
            if days_until_friday < 0:
                days_until_friday += 7
            return ref + timedelta(days=days_until_friday), RELATIVE_RESOLUTION_WEEK_END

        # Duration patterns: "in N weeks", "in N months", "about N weeks"
        weeks = self._extract_duration(expr, ["week", "weeks"])
        if weeks:
            return ref + timedelta(weeks=weeks), RELATIVE_RESOLUTION_ESTIMATED

        months = self._extract_duration(expr, ["month", "months"])
        if months:
            return self._add_months(ref, months), RELATIVE_RESOLUTION_ESTIMATED

        days = self._extract_duration(expr, ["day", "days"])
        if days:
            return ref + timedelta(days=days), RELATIVE_RESOLUTION_ESTIMATED

        # End of year
        if "end of year" in expr or "year end" in expr or "by end of year" in expr:
            return date(ref.year, 12, 31), RELATIVE_RESOLUTION_QUARTER_END

        # Year-specific patterns
        if "end of 20" in expr:
            # Try to extract year like "end of 2026"
            import re
            year_match = re.search(r"20\d{2}", expr)
            if year_match:
                year = int(year_match.group())
                return date(year, 12, 31), RELATIVE_RESOLUTION_QUARTER_END

        # Default: 30 days from extraction (reasonable "soon" proxy)
        logger.warning(
            f"[RelativeDateRecalculator] Could not resolve: '{expr}'. Defaulting to +30 days."
        )
        return ref + timedelta(days=30), RELATIVE_RESOLUTION_ESTIMATED

    def _extract_duration(self, expr: str, unit_words: list) -> Optional[int]:
        """Extract numeric duration from expressions like 'six weeks', 'about 3 months'."""
        words = expr.split()

        for i, word in enumerate(words):
            if any(u in word for u in unit_words):
                # Check preceding word for number
                if i > 0:
                    prev = words[i - 1].strip("~").replace("about", "").replace("around", "").strip()
                    if prev.isdigit():
                        return int(prev)
                    if prev in self.TEXT_NUMBERS:
                        return self.TEXT_NUMBERS[prev]
        return None

    def _quarter_end(self, ref: date, offset: int) -> date:
        """Return the last day of the current quarter + offset quarters."""
        current_quarter = (ref.month - 1) // 3
        target_quarter = current_quarter + offset
        year = ref.year + (target_quarter // 4)
        quarter = target_quarter % 4
        quarter_end_month = [3, 6, 9, 12][quarter]
        last_day = monthrange(year, quarter_end_month)[1]
        return date(year, quarter_end_month, last_day)

    def _specific_quarter_end(self, year: int, quarter: int) -> date:
        """Return the last day of a specific quarter."""
        quarter_end_months = {1: 3, 2: 6, 3: 9, 4: 12}
        month = quarter_end_months[quarter]
        last_day = monthrange(year, month)[1]
        return date(year, month, last_day)

    def _month_end(self, ref: date) -> date:
        """Return the last day of the given month."""
        last_day = monthrange(ref.year, ref.month)[1]
        return date(ref.year, ref.month, last_day)

    def _add_months(self, ref: date, months: int) -> date:
        """Add months to a date, handling month-end edge cases."""
        month = ref.month + months
        year = ref.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        day = min(ref.day, monthrange(year, month)[1])
        return date(year, month, day)

    def _parse_timestamp(self, ts: str) -> Optional[date]:
        """Parse ISO timestamp to date."""
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
        except (ValueError, TypeError):
            return None

    async def check_stale_relative_dates(self, pursuit_id: str, db) -> List[Dict[str, Any]]:
        """
        Find milestones with requires_recalculation=True that have not been
        confirmed in more than RECALCULATION_PROMPT_THRESHOLD_DAYS days.

        Args:
            pursuit_id: The pursuit to check
            db: Database connection

        Returns:
            List of milestones that should receive a confirmation prompt.
        """
        stale = []
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=self.prompt_threshold_days)
        ).isoformat() + "Z"

        candidates = list(db.db.pursuit_milestones.find({
            "pursuit_id": pursuit_id,
            "requires_recalculation": True,
            "is_superseded": {"$ne": True},
            "$or": [
                {"recalculation_prompted_at": None},
                {"recalculation_prompted_at": {"$lt": cutoff}}
            ]
        }))

        for m in candidates:
            stale.append({
                "milestone_id": m.get("milestone_id"),
                "title": m.get("title", "milestone"),
                "date_expression": m.get("date_expression", ""),
                "resolved_date": m.get("target_date", ""),
                "extraction_timestamp": m.get("extracted_at", ""),
                "prompt": self._build_confirmation_prompt(m)
            })

        if stale:
            logger.info(
                f"[RelativeDateRecalculator] Found {len(stale)} stale relative dates "
                f"for pursuit {pursuit_id}"
            )

        return stale

    def check_stale_relative_dates_sync(self, pursuit_id: str, db) -> List[Dict[str, Any]]:
        """Synchronous version of check_stale_relative_dates."""
        stale = []
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=self.prompt_threshold_days)
        ).isoformat() + "Z"

        candidates = list(db.db.pursuit_milestones.find({
            "pursuit_id": pursuit_id,
            "requires_recalculation": True,
            "is_superseded": {"$ne": True},
            "$or": [
                {"recalculation_prompted_at": None},
                {"recalculation_prompted_at": {"$lt": cutoff}}
            ]
        }))

        for m in candidates:
            stale.append({
                "milestone_id": m.get("milestone_id"),
                "title": m.get("title", "milestone"),
                "date_expression": m.get("date_expression", ""),
                "resolved_date": m.get("target_date", ""),
                "extraction_timestamp": m.get("extracted_at", ""),
                "prompt": self._build_confirmation_prompt(m)
            })

        return stale

    def _build_confirmation_prompt(self, milestone: Dict) -> str:
        """Build a coaching prompt for relative date confirmation."""
        expr = milestone.get("date_expression", "a future date")
        resolved = milestone.get("target_date", "")
        extracted_at = milestone.get("extracted_at", "")

        # Format dates for display
        resolved_display = self._format_date_for_display(resolved)
        extracted_display = self._format_extraction_date(extracted_at)

        return (
            f"When you mentioned '{expr}' {extracted_display}, "
            f"I interpreted that as {resolved_display}. "
            f"Does that still hold, or has your timeline shifted?"
        )

    def _format_date_for_display(self, date_str: str) -> str:
        """Format a date string for user-friendly display."""
        try:
            if "T" in date_str:
                date_str = date_str.split("T")[0]
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%B %d, %Y")
        except (ValueError, TypeError):
            return date_str

    def _format_extraction_date(self, ts: str) -> str:
        """Format extraction timestamp as 'on March 5' or 'recently'."""
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return f"on {dt.strftime('%B %-d')}"
        except (ValueError, TypeError, AttributeError):
            try:
                # Windows compatibility - no %-d
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return f"on {dt.strftime('%B')} {dt.day}"
            except:
                return "recently"

    async def confirm_relative_date(
        self, milestone_id: str, confirmed_date: Optional[str], db
    ) -> None:
        """
        Mark a relative milestone as confirmed.

        Args:
            milestone_id: The milestone to confirm
            confirmed_date: If None, the resolved date stands. If provided, update target_date.
            db: Database connection

        In both cases:
        - requires_recalculation is set to False
        - date_precision is upgraded to "exact"
        """
        now = datetime.now(timezone.utc).isoformat() + "Z"

        update = {
            "requires_recalculation": False,
            "date_precision": "exact",
            "updated_at": now
        }

        if confirmed_date:
            update["target_date"] = confirmed_date

        db.db.pursuit_milestones.update_one(
            {"milestone_id": milestone_id},
            {"$set": update}
        )

        logger.info(
            f"[RelativeDateRecalculator] Confirmed milestone {milestone_id} "
            f"with date: {confirmed_date or '(original)'}"
        )

    def confirm_relative_date_sync(
        self, milestone_id: str, confirmed_date: Optional[str], db
    ) -> None:
        """Synchronous version of confirm_relative_date."""
        now = datetime.now(timezone.utc).isoformat() + "Z"

        update = {
            "requires_recalculation": False,
            "date_precision": "exact",
            "updated_at": now
        }

        if confirmed_date:
            update["target_date"] = confirmed_date

        db.db.pursuit_milestones.update_one(
            {"milestone_id": milestone_id},
            {"$set": update}
        )

    def mark_prompted(self, milestone_id: str, db) -> None:
        """Mark that a confirmation prompt was shown for this milestone."""
        now = datetime.now(timezone.utc).isoformat() + "Z"
        db.db.pursuit_milestones.update_one(
            {"milestone_id": milestone_id},
            {"$set": {"recalculation_prompted_at": now}}
        )
