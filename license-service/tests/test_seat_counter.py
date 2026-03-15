"""
Tests for InDE License Seat Counter.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from seat_counter import SeatCounter
from models import SeatCompliance


class TestSeatCompliance:
    """Test seat compliance calculations."""

    @pytest.fixture
    def counter(self):
        """Create a seat counter with mocked database."""
        mock_db = MagicMock()
        return SeatCounter(db=mock_db)

    @pytest.mark.asyncio
    async def test_compliance_under_limit(self, counter):
        """Test compliance when under seat limit."""
        with patch.object(counter, 'count_active_seats', new_callable=AsyncMock) as mock:
            mock.return_value = 5

            result = await counter.check_seat_compliance(10)

            assert result.active_seats == 5
            assert result.seat_limit == 10
            assert result.compliant is True
            assert result.warning is False
            assert result.violation is False

    @pytest.mark.asyncio
    async def test_compliance_at_limit(self, counter):
        """Test compliance when at seat limit."""
        with patch.object(counter, 'count_active_seats', new_callable=AsyncMock) as mock:
            mock.return_value = 10

            result = await counter.check_seat_compliance(10)

            assert result.active_seats == 10
            assert result.compliant is True
            assert result.warning is False
            assert result.violation is False

    @pytest.mark.asyncio
    async def test_warning_within_tolerance(self, counter):
        """Test warning when slightly over limit but within tolerance."""
        with patch.object(counter, 'count_active_seats', new_callable=AsyncMock) as mock:
            mock.return_value = 11  # 10% over limit of 10

            result = await counter.check_seat_compliance(10)

            assert result.active_seats == 11
            assert result.compliant is True  # Within 10% tolerance
            assert result.warning is True
            assert result.violation is False

    @pytest.mark.asyncio
    async def test_violation_over_tolerance(self, counter):
        """Test violation when over tolerance limit."""
        with patch.object(counter, 'count_active_seats', new_callable=AsyncMock) as mock:
            mock.return_value = 12  # 20% over limit of 10

            result = await counter.check_seat_compliance(10)

            assert result.active_seats == 12
            assert result.compliant is False
            assert result.violation is True

    @pytest.mark.asyncio
    async def test_unlimited_seats(self, counter):
        """Test behavior with unlimited seats (limit <= 0)."""
        with patch.object(counter, 'count_active_seats', new_callable=AsyncMock) as mock:
            mock.return_value = 1000

            result = await counter.check_seat_compliance(0)

            assert result.compliant is True
            assert result.warning is False
            assert result.violation is False


class TestSeatDetails:
    """Test seat details retrieval."""

    @pytest.fixture
    def counter(self):
        """Create a seat counter with mocked database."""
        mock_db = MagicMock()
        return SeatCounter(db=mock_db)

    @pytest.mark.asyncio
    async def test_get_seat_details(self, counter):
        """Test getting detailed seat information."""
        with patch.object(counter, 'count_active_seats', new_callable=AsyncMock) as mock:
            mock.return_value = 7

            details = await counter.get_seat_details(10)

            assert details["active_seats"] == 7
            assert details["seat_limit"] == 10
            assert details["available_seats"] == 3
            assert details["usage_percentage"] == 70.0
            assert details["compliant"] is True
            assert "window_days" in details


class TestEmptyDatabase:
    """Test behavior with empty database."""

    @pytest.fixture
    def counter(self):
        """Create a seat counter with mocked database."""
        mock_db = MagicMock()
        return SeatCounter(db=mock_db)

    @pytest.mark.asyncio
    async def test_empty_database_returns_zero(self, counter):
        """Test that empty database returns zero seats."""
        # Mock the aggregation to return empty result
        mock_result = []
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=mock_result)

        mock_collection = MagicMock()
        mock_collection.aggregate = MagicMock(return_value=mock_cursor)

        mock_db = MagicMock()
        mock_db.messages = mock_collection

        counter._db = mock_db

        result = await counter.count_active_seats()
        assert result == 0
