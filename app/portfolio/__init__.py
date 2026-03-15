"""
InDE MVP v3.4 - Portfolio Package
Portfolio management for innovation pursuits.
Includes Org-Level Portfolio Dashboard with 7-panel enterprise intelligence.
"""

from .portfolio_manager import PortfolioManager
from .dashboard import (
    PortfolioDashboard,
    DashboardPanel,
    PanelType,
    HealthLevel,
    get_portfolio_dashboard
)

__all__ = [
    'PortfolioManager',
    'PortfolioDashboard',
    'DashboardPanel',
    'PanelType',
    'HealthLevel',
    'get_portfolio_dashboard'
]
