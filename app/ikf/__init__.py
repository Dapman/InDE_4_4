"""
InDE MVP v3.2 - IKF Module
Innovation Knowledge Fabric contribution preparation and federation access.

Components:
- GeneralizationEngine: 4-stage privacy-preserving data generalization
- IKFContributionPreparer: 5 package types with human review gate
- IKFServiceClient: Communication with IKF service for federation

All packages require explicit human approval before IKF_READY status.
v3.2 adds full federation protocol support via ikf-service container.
"""

from .generalization_engine import GeneralizationEngine
from .contribution_preparer import IKFContributionPreparer
from .service_client import IKFServiceClient
from .insights_provider import IKFInsightsProvider

__all__ = [
    "GeneralizationEngine",
    "IKFContributionPreparer",
    "IKFServiceClient",
    "IKFInsightsProvider"
]
