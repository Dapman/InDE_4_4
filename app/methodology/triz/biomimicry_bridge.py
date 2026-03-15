"""
TRIZ-Biomimicry Cross-Reference Builder

At startup, reads the biomimicry_patterns collection's triz_connections
fields and builds a reverse index: inventive_principle -> [organisms].

This enables the flagship coaching moment:
"Principle 17 - Another Dimension - is exactly what the Namibian Desert
Beetle does with its shell surface."

The bridge is rebuilt on:
1. Application startup
2. When new biomimicry patterns arrive via federation (inbound)
3. Periodically (every 6 hours) to catch manual additions
"""

import re
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("inde.triz.bridge")


class TrizBiomimicryBridge:
    """
    Cross-reference between TRIZ inventive principles and biological strategies.

    Builds a reverse index from the biomimicry pattern database's triz_connections
    fields, enabling the coach to surface biological analogs when discussing
    inventive principles.
    """

    def __init__(self, db):
        """
        Initialize the bridge.

        Args:
            db: MongoDB database connection
        """
        self._db = db
        self._principle_to_organisms: Dict[int, List[Dict]] = {}
        self._last_built: Optional[datetime] = None
        self._pattern_count: int = 0

    async def build_index(self) -> int:
        """
        Scan all biomimicry patterns with triz_connections and build
        a reverse index from principle number -> biological strategies.

        Returns:
            Number of principles with biological analogs
        """
        try:
            # Query patterns with non-empty triz_connections
            cursor = self._db.biomimicry_patterns.find(
                {"triz_connections": {"$exists": True, "$ne": []}}
            )
            patterns = await cursor.to_list(200)

            self._principle_to_organisms = {}
            self._pattern_count = 0

            for pattern in patterns:
                self._pattern_count += 1
                for connection in pattern.get("triz_connections", []):
                    # Parse principle number from "Principle N: Name" format
                    principle_num = self._extract_principle_number(connection)
                    if principle_num:
                        if principle_num not in self._principle_to_organisms:
                            self._principle_to_organisms[principle_num] = []

                        self._principle_to_organisms[principle_num].append({
                            "organism": pattern.get("organism", "Unknown"),
                            "strategy_name": pattern.get("strategy_name", ""),
                            "mechanism_summary": pattern.get("description", "")[:150],
                            "pattern_id": pattern.get("pattern_id", ""),
                            "category": pattern.get("category", ""),
                            "triz_connection_text": connection,
                        })

            self._last_built = datetime.now(timezone.utc)
            logger.info(
                f"TRIZ-Biomimicry bridge built: {len(self._principle_to_organisms)} "
                f"principles mapped from {self._pattern_count} patterns"
            )

            return len(self._principle_to_organisms)

        except Exception as e:
            logger.error(f"Failed to build TRIZ-Biomimicry bridge: {e}")
            return 0

    def get_biological_analogs(self, principle_number: int) -> List[Dict]:
        """
        Return biological strategies that embody a given inventive principle.

        Used during TRIZ Principle Application phase to enrich coaching
        with nature-inspired examples of the principle in action.

        Args:
            principle_number: TRIZ principle number (1-40)

        Returns:
            List of biological analog dicts with organism, strategy, and mechanism
        """
        return self._principle_to_organisms.get(principle_number, [])

    def get_all_mapped_principles(self) -> List[int]:
        """
        Return all principle numbers that have biological analogs.

        Returns:
            Sorted list of principle numbers with mappings
        """
        return sorted(self._principle_to_organisms.keys())

    def get_coverage_stats(self) -> Dict:
        """
        Return statistics about TRIZ-Biomimicry coverage.

        Returns:
            Dict with coverage statistics
        """
        total_principles = 40
        mapped_count = len(self._principle_to_organisms)
        total_analogs = sum(len(v) for v in self._principle_to_organisms.values())

        return {
            "total_principles": total_principles,
            "principles_with_analogs": mapped_count,
            "coverage_percent": round((mapped_count / total_principles) * 100, 1),
            "total_biological_analogs": total_analogs,
            "patterns_scanned": self._pattern_count,
            "last_built": self._last_built.isoformat() if self._last_built else None,
        }

    def format_analog_for_coaching(
        self,
        principle_number: int,
        principle_name: str,
        max_analogs: int = 2
    ) -> Optional[str]:
        """
        Format biological analogs for injection into coaching context.

        Args:
            principle_number: TRIZ principle number
            principle_name: Human-readable principle name
            max_analogs: Maximum analogs to include

        Returns:
            Formatted coaching context string, or None if no analogs
        """
        analogs = self.get_biological_analogs(principle_number)
        if not analogs:
            return None

        lines = []
        for analog in analogs[:max_analogs]:
            organism = analog.get("organism", "Unknown organism")
            mechanism = analog.get("mechanism_summary", "")
            strategy = analog.get("strategy_name", "")

            lines.append(
                f"Nature's example of Principle {principle_number} ({principle_name}): "
                f"{organism}"
            )
            if strategy:
                lines.append(f"  Strategy: {strategy}")
            if mechanism:
                lines.append(f"  Mechanism: {mechanism}")

        return "\n".join(lines)

    def _extract_principle_number(self, connection_str: str) -> Optional[int]:
        """
        Parse principle number from TRIZ connection string.

        Handles formats like:
        - "Principle 17: Another Dimension"
        - "Principle 2 - Taking Out"
        - "17: Another Dimension"

        Args:
            connection_str: The triz_connections field value

        Returns:
            Principle number (1-40), or None if not parseable
        """
        # Try "Principle N" format first
        match = re.search(r'Principle\s+(\d+)', connection_str, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 40:
                return num

        # Try leading number format
        match = re.match(r'^(\d+)\s*[:\-]', connection_str)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 40:
                return num

        return None

    async def refresh_if_stale(self, max_age_hours: int = 6) -> bool:
        """
        Refresh the index if it's older than max_age_hours.

        Args:
            max_age_hours: Maximum age before refresh

        Returns:
            True if refreshed, False if still fresh
        """
        if not self._last_built:
            await self.build_index()
            return True

        age = datetime.now(timezone.utc) - self._last_built
        if age.total_seconds() > max_age_hours * 3600:
            await self.build_index()
            return True

        return False

    async def on_pattern_imported(self, pattern_id: str) -> int:
        """
        Called when a new biomimicry pattern is imported via federation.
        Rebuilds the index to include the new pattern.

        Args:
            pattern_id: The imported pattern's ID

        Returns:
            Updated count of mapped principles
        """
        logger.info(f"Rebuilding TRIZ-Biomimicry bridge after pattern import: {pattern_id}")
        return await self.build_index()


class TrizBiomimicryCoachingAssistant:
    """
    High-level assistant for TRIZ-Biomimicry coaching integration.

    Provides methods for the scaffolding engine to get biological
    insights during TRIZ coaching conversations.
    """

    def __init__(self, bridge: TrizBiomimicryBridge, principles_db):
        """
        Initialize the coaching assistant.

        Args:
            bridge: The TrizBiomimicryBridge instance
            principles_db: The inventive principles reference
        """
        self._bridge = bridge
        self._principles = principles_db

    async def get_biological_insight(
        self,
        principle_numbers: List[int],
        max_insights: int = 2
    ) -> Optional[str]:
        """
        Get biological insights for recommended inventive principles.

        Called during TRIZ Principle Application phase when the coach
        is helping the innovator explore inventive principles.

        Args:
            principle_numbers: List of recommended principle numbers
            max_insights: Maximum insights to return

        Returns:
            Coaching context string with biological insights, or None
        """
        insights = []

        for num in principle_numbers:
            if len(insights) >= max_insights:
                break

            analogs = self._bridge.get_biological_analogs(num)
            if analogs:
                # Get principle name from database
                principle_name = self._get_principle_name(num)

                analog = analogs[0]  # Best match (first in list)
                organism = analog.get("organism", "an organism")
                mechanism = analog.get("mechanism_summary", "")

                insight = (
                    f"Principle {num} ({principle_name}) is embodied in nature by "
                    f"{organism}: {mechanism}"
                )
                insights.append(insight)

        if insights:
            header = "[TRIZ_BIOMIMICRY_INSIGHT]"
            footer = (
                "\nExplain WHY the organism's strategy embodies this principle. "
                "Connect the biological mechanism to the innovator's contradiction."
            )
            return header + "\n" + "\n".join(insights) + footer

        return None

    def _get_principle_name(self, number: int) -> str:
        """Get the name of an inventive principle by number."""
        from .inventive_principles import get_principle
        principle = get_principle(number)
        return principle.get("name", f"Principle {number}") if principle else f"Principle {number}"
