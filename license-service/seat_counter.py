"""
InDE License Service - Seat Counter
Counts active innovator seats based on coaching interactions.

A "seat" is consumed when a user has at least one coaching interaction
in the trailing 30-day window. Admin-only users who don't pursue
innovation work do not consume seats.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from models import SeatCompliance
from config import config


class SeatCounter:
    """Counts active innovator seats from the InDE database."""

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        """
        Initialize the seat counter.

        Args:
            db: Optional MongoDB database instance. Connects using config if not provided.
        """
        self._db = db
        self._client: Optional[AsyncIOMotorClient] = None

    async def _get_db(self) -> AsyncIOMotorDatabase:
        """Get or create database connection."""
        if self._db is not None:
            return self._db

        if self._client is None:
            self._client = AsyncIOMotorClient(config.MONGODB_URL)

        return self._client[config.MONGODB_DATABASE]

    async def count_active_seats(self) -> int:
        """
        Count the number of active seats (users with coaching interactions).

        A seat is consumed when a user has at least one coaching interaction
        (message in a coaching session) in the trailing 30-day window.

        Returns:
            Number of active seats
        """
        try:
            db = await self._get_db()

            cutoff = datetime.now(timezone.utc) - timedelta(days=config.SEAT_WINDOW_DAYS)

            # Count distinct users with coaching messages in the window
            # Look in the messages collection for recent coaching activity
            pipeline = [
                {
                    "$match": {
                        "timestamp": {"$gte": cutoff},
                        "role": "user"  # Only count user messages (not coach responses)
                    }
                },
                {
                    "$group": {
                        "_id": "$user_id"
                    }
                },
                {
                    "$count": "active_seats"
                }
            ]

            result = await db.messages.aggregate(pipeline).to_list(1)

            if result and len(result) > 0:
                return result[0].get("active_seats", 0)
            return 0

        except Exception:
            # If database is unavailable, return 0 to avoid blocking
            return 0

    async def check_seat_compliance(self, seat_limit: int) -> SeatCompliance:
        """
        Check if current seat usage is within the license limit.

        Args:
            seat_limit: Maximum allowed seats from license

        Returns:
            SeatCompliance object with usage details
        """
        active_seats = await self.count_active_seats()

        if seat_limit <= 0:
            # Unlimited seats
            return SeatCompliance(
                active_seats=active_seats,
                seat_limit=seat_limit,
                compliant=True,
                overage_percentage=0.0,
                warning=False,
                violation=False
            )

        overage_amount = max(0, active_seats - seat_limit)
        overage_percentage = (overage_amount / seat_limit * 100) if seat_limit > 0 else 0

        # 10% tolerance before violation
        tolerance_limit = seat_limit * (1 + config.SEAT_OVERAGE_TOLERANCE)

        return SeatCompliance(
            active_seats=active_seats,
            seat_limit=seat_limit,
            compliant=active_seats <= tolerance_limit,
            overage_percentage=overage_percentage,
            warning=active_seats > seat_limit and active_seats <= tolerance_limit,
            violation=active_seats > tolerance_limit
        )

    async def get_seat_details(self, seat_limit: int) -> dict:
        """
        Get detailed seat usage information.

        Args:
            seat_limit: Maximum allowed seats from license

        Returns:
            Dictionary with seat usage details
        """
        compliance = await self.check_seat_compliance(seat_limit)

        return {
            "active_seats": compliance.active_seats,
            "seat_limit": compliance.seat_limit,
            "available_seats": max(0, compliance.seat_limit - compliance.active_seats),
            "usage_percentage": (
                (compliance.active_seats / compliance.seat_limit * 100)
                if compliance.seat_limit > 0 else 0
            ),
            "compliant": compliance.compliant,
            "warning": compliance.warning,
            "violation": compliance.violation,
            "window_days": config.SEAT_WINDOW_DAYS,
            "overage_tolerance": f"{config.SEAT_OVERAGE_TOLERANCE * 100:.0f}%"
        }

    async def close(self) -> None:
        """Close database connection."""
        if self._client is not None:
            self._client.close()
            self._client = None


# Module-level counter instance
_seat_counter: Optional[SeatCounter] = None


def get_seat_counter() -> SeatCounter:
    """Get the singleton seat counter instance."""
    global _seat_counter
    if _seat_counter is None:
        _seat_counter = SeatCounter()
    return _seat_counter
