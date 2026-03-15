"""
InDE MVP v3.3 - Teams Module
Team Innovation & Shared Pursuits

This module provides team collaboration capabilities:
- Shared Pursuit Engine: Multi-user pursuit management with roles
- Team Scaffolding Engine: Element attribution and gap analysis
- Activity Stream: Real-time collaboration events
- Notification Service: Mention handling and alerts
- Team Context Assembler: Multi-user context for coaching
"""

from teams.shared_pursuit_engine import SharedPursuitEngine
from teams.team_scaffolding import TeamScaffoldingEngine
from teams.activity_stream import ActivityStreamService
from teams.notification_service import NotificationService
from teams.team_context_assembler import TeamContextAssembler

__all__ = [
    "SharedPursuitEngine",
    "TeamScaffoldingEngine",
    "ActivityStreamService",
    "NotificationService",
    "TeamContextAssembler",
]
