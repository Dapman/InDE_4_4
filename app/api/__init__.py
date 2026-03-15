"""
InDE v3.1 - API Routes Module
All FastAPI route modules for the InDE API.
"""

from api import auth
from api import pursuits
from api import coaching
from api import artifacts
from api import analytics
from api import reports
from api import timeline
from api import health
from api import ikf
from api import crisis
from api import maturity
from api import system

__all__ = [
    "auth",
    "pursuits",
    "coaching",
    "artifacts",
    "analytics",
    "reports",
    "timeline",
    "health",
    "ikf",
    "crisis",
    "maturity",
    "system"
]
