"""
InDE MVP v3.7.4 - User Interface Package

Note: Gradio UI was retired in v3.7.4.4 in favor of the React frontend.
This package now only contains shared visualization utilities used by
report generation modules.

For the main UI, see frontend/ directory (React 18 + Vite).
"""

from .analytics_visualizations import (
    create_health_badge,
    create_velocity_bar_chart,
    create_health_trend_chart,
    create_risk_horizon_map,
    create_rve_status_chart,
    create_prediction_gauge,
    create_learning_sparkline,
    create_portfolio_heatmap,
    create_timeline_journey_chart,
    create_velocity_curve_chart,
    get_zone_color,
    apply_inde_theme,
    fig_to_bytes,
)

__all__ = [
    # Visualization utilities (matplotlib-based)
    'create_health_badge',
    'create_velocity_bar_chart',
    'create_health_trend_chart',
    'create_risk_horizon_map',
    'create_rve_status_chart',
    'create_prediction_gauge',
    'create_learning_sparkline',
    'create_portfolio_heatmap',
    'create_timeline_journey_chart',
    'create_velocity_curve_chart',
    'get_zone_color',
    'apply_inde_theme',
    'fig_to_bytes',
]
