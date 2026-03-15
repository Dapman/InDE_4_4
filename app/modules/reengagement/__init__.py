"""
Re-Engagement Module — Async Coaching Outreach

InDE MVP v4.3.0 — The Depth Frame

Watches for innovators who have not returned within 48–72 hours
following a session that ended with low momentum or without a
responded-to bridge. Delivers a single, pursuit-specific coaching
question in the coach's voice — not a marketing email, not a
system notification, but a genuine coaching moment delivered
asynchronously.

Design rules:
  - Maximum 2 re-engagement attempts per inactivity gap
  - Minimum 48h between the triggering exit and first attempt
  - Re-engagement is ALWAYS a question about the specific idea
  - No methodology terminology — Innovator Test applies
  - Opt-in only: requires coaching_cadence preference enabled
  - Never sent to users who are already active (session in last 24h)

© 2026 Yul Williams | InDEVerse, Incorporated
"""

from .reengagement_generator import ReengagementGenerator
from .reengagement_scheduler import ReengagementScheduler
from .reengagement_delivery import ReengagementDeliveryService

__all__ = ["ReengagementGenerator", "ReengagementScheduler", "ReengagementDeliveryService"]
