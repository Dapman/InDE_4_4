"""
Re-Entry Module — Momentum-Aware Session Opening

InDE MVP v4.4.0 — The Learning Engine

Generates personalized coach opening turns for every returning user
session. The opening is written specifically for this innovator, about
their specific idea, reflecting the momentum state at their last exit
and the time elapsed since then.

Design principles:
  - The opening must feel like a coach who remembers — not a system
    that restarted
  - Gap duration shapes the tone: short gaps get continuity,
    long gaps get re-grounding
  - Momentum tier at exit shapes the energy: high exits get advancement,
    low exits get reconnection
  - The opening is ALWAYS a question — not a summary, not a status report
  - Methodology vocabulary is NEVER used — Innovator Test applies

© 2026 Yul Williams | InDEVerse, Incorporated
"""

from .reentry_generator import ReentryGenerator
from .reentry_context_assembler import ReentryContextAssembler

__all__ = ["ReentryGenerator", "ReentryContextAssembler"]
