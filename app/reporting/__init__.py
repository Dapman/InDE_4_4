"""
InDE MVP v2.8 - Report Intelligence Module

This module provides comprehensive reporting capabilities:
- Template Management: System and custom report templates
- Living Snapshot Reports: Progress reports for active pursuits
- Portfolio Analytics Reports: Cross-pursuit synthesis
- Report Review Workflow: Draft -> Review -> Edit -> Approve -> Finalize
"""

from .template_manager import ReportTemplateManager
from .living_snapshot_generator import LivingSnapshotGenerator
from .portfolio_analytics_generator import PortfolioAnalyticsGenerator
from .report_review_manager import ReportReviewManager

__all__ = [
    "ReportTemplateManager",
    "LivingSnapshotGenerator",
    "PortfolioAnalyticsGenerator",
    "ReportReviewManager"
]
