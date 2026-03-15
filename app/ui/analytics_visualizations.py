"""
InDE MVP v3.0.3 - Analytics Visualizations Engine
Shared visualization functions with InDE color theme.

Used by both portfolio_dashboard.py and silr_temporal_enrichment.py
for consistent styling across all visualizations.

8 Visualization Types:
1. Timeline Journey Chart - Horizontal Gantt-style
2. Velocity Curve - Line chart with confidence band
3. Health Score Trend - Area chart with zone colors
4. Risk Horizon Map - Grouped bar chart
5. RVE Outcomes Donut - PASS/GREY/FAIL distribution
6. Portfolio Health Heatmap - Grid by pursuit/time
7. Prediction Accuracy Gauge - Semi-circular gauge
8. Learning Velocity Sparkline - Compact inline chart
"""

import io
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

# Use Agg backend for non-interactive rendering
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Wedge, Circle
import numpy as np

from config import INDE_COLORS, SILR_ENRICHMENT_CONFIG

# =============================================================================
# SHARED COLOR CONSTANTS
# =============================================================================

def get_zone_color(zone: str) -> str:
    """Get color for a health zone."""
    return INDE_COLORS.get(zone, INDE_COLORS.get("HEALTHY", "#3B82F6"))


def apply_inde_theme(ax):
    """Apply consistent InDE styling to any matplotlib axes."""
    ax.set_facecolor(INDE_COLORS.get("GRID", "#F1F5F9"))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#94A3B8')
    ax.spines['bottom'].set_color('#94A3B8')
    ax.tick_params(colors='#64748B')
    ax.xaxis.label.set_color('#475569')
    ax.yaxis.label.set_color('#475569')


def fig_to_bytes(fig) -> bytes:
    """Convert matplotlib figure to PNG bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=SILR_ENRICHMENT_CONFIG.get("visualization_dpi", 100),
                bbox_inches='tight', facecolor='white', edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()


# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def create_health_badge(score: int, zone: str, size: str = 'large') -> bytes:
    """
    Generate a health score badge as matplotlib figure.

    Args:
        score: Health score 0-100
        zone: Health zone name
        size: 'large' or 'small'

    Returns:
        PNG image bytes
    """
    figsize = (3, 3) if size == 'large' else (1.5, 1.5)
    fig, ax = plt.subplots(figsize=figsize)

    color = get_zone_color(zone)

    # Draw circular badge
    circle = Circle((0.5, 0.5), 0.4, color=color, alpha=0.2)
    ax.add_patch(circle)

    circle_border = Circle((0.5, 0.5), 0.4, fill=False, color=color, linewidth=3)
    ax.add_patch(circle_border)

    # Add score text
    fontsize = 32 if size == 'large' else 16
    ax.text(0.5, 0.55, str(score), ha='center', va='center',
            fontsize=fontsize, fontweight='bold', color=color)

    # Add zone label
    if size == 'large':
        ax.text(0.5, 0.25, zone, ha='center', va='center',
                fontsize=10, color='#64748B')

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    return fig_to_bytes(fig)


def create_velocity_bar_chart(pursuit_data: List[Dict], portfolio_avg: float) -> bytes:
    """
    Bar chart comparing velocities with average line.

    Args:
        pursuit_data: List of {name, velocity}
        portfolio_avg: Portfolio average velocity

    Returns:
        PNG image bytes
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    apply_inde_theme(ax)

    if not pursuit_data:
        ax.text(0.5, 0.5, 'No velocity data', ha='center', va='center')
        return fig_to_bytes(fig)

    names = [p.get('name', 'Unknown')[:15] for p in pursuit_data]
    velocities = [p.get('velocity', 0) for p in pursuit_data]

    # Color bars by relative performance
    colors = []
    for v in velocities:
        if v >= portfolio_avg * 1.2:
            colors.append(INDE_COLORS['THRIVING'])
        elif v >= portfolio_avg * 0.8:
            colors.append(INDE_COLORS['HEALTHY'])
        else:
            colors.append(INDE_COLORS['ATTENTION'])

    bars = ax.bar(names, velocities, color=colors, alpha=0.8)

    # Add portfolio average line
    ax.axhline(y=portfolio_avg, color=INDE_COLORS['PORTFOLIO_AVG'],
               linestyle='--', linewidth=2, label=f'Portfolio Avg: {portfolio_avg:.1f}')

    ax.set_xlabel('Pursuit')
    ax.set_ylabel('Velocity (elements/week)')
    ax.set_title('Velocity Comparison')
    ax.legend()

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    return fig_to_bytes(fig)


def create_risk_donut(risk_data: Dict) -> bytes:
    """
    Donut chart for risk distribution by severity.

    Args:
        risk_data: {high: int, medium: int, low: int}

    Returns:
        PNG image bytes
    """
    fig, ax = plt.subplots(figsize=(6, 6))

    sizes = [
        risk_data.get('high', 0),
        risk_data.get('medium', 0),
        risk_data.get('low', 0)
    ]

    # Filter out zeros
    labels = ['High', 'Medium', 'Low']
    colors = [INDE_COLORS['CRITICAL'], INDE_COLORS['ATTENTION'], INDE_COLORS['HEALTHY']]

    non_zero = [(s, l, c) for s, l, c in zip(sizes, labels, colors) if s > 0]

    if not non_zero:
        ax.text(0.5, 0.5, 'No risks identified', ha='center', va='center',
                fontsize=14, transform=ax.transAxes)
        ax.axis('off')
        return fig_to_bytes(fig)

    sizes, labels, colors = zip(*non_zero)

    # Create donut
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                       autopct='%1.0f%%', pctdistance=0.75,
                                       wedgeprops=dict(width=0.5))

    # Style
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')

    ax.set_title('Risk Distribution by Severity')

    return fig_to_bytes(fig)


def create_rve_status_chart(rve_data: Dict) -> bytes:
    """
    PASS/GREY/FAIL distribution chart.

    Args:
        rve_data: {PASS: int, GREY: int, FAIL: int}

    Returns:
        PNG image bytes
    """
    fig, ax = plt.subplots(figsize=(6, 6))

    sizes = [
        rve_data.get('PASS', 0),
        rve_data.get('GREY', 0),
        rve_data.get('FAIL', 0)
    ]

    labels = ['PASS', 'GREY', 'FAIL']
    colors = [INDE_COLORS['PASS'], INDE_COLORS['GREY'], INDE_COLORS['FAIL']]

    non_zero = [(s, l, c) for s, l, c in zip(sizes, labels, colors) if s > 0]

    if not non_zero:
        ax.text(0.5, 0.5, 'No experiments completed', ha='center', va='center',
                fontsize=14, transform=ax.transAxes)
        ax.axis('off')
        return fig_to_bytes(fig)

    sizes, labels, colors = zip(*non_zero)

    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                       autopct='%1.0f%%', pctdistance=0.75,
                                       wedgeprops=dict(width=0.5))

    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')

    ax.set_title('RVE Experiment Outcomes')

    return fig_to_bytes(fig)


def create_sparkline(data_points: List[float], color: str = None) -> bytes:
    """
    Compact inline sparkline chart.

    Args:
        data_points: List of values
        color: Optional line color

    Returns:
        PNG image bytes
    """
    fig, ax = plt.subplots(figsize=(3, 1))

    if not data_points:
        return fig_to_bytes(fig)

    color = color or INDE_COLORS['PRIMARY']

    x = range(len(data_points))
    ax.plot(x, data_points, color=color, linewidth=2)
    ax.fill_between(x, data_points, alpha=0.2, color=color)

    # Minimal styling for sparkline
    ax.axis('off')
    ax.set_xlim(0, len(data_points) - 1)

    return fig_to_bytes(fig)


def create_timeline_journey_chart(phases: List[Dict], milestones: List[Dict] = None) -> bytes:
    """
    Horizontal Gantt-style chart with phase durations and milestones.

    Args:
        phases: List of {name, start, end, duration_days}
        milestones: Optional list of {name, date}

    Returns:
        PNG image bytes
    """
    fig, ax = plt.subplots(figsize=(12, 4))
    apply_inde_theme(ax)

    if not phases:
        ax.text(0.5, 0.5, 'No phase data', ha='center', va='center')
        return fig_to_bytes(fig)

    phase_colors = {
        'VISION': INDE_COLORS['HEALTHY'],
        'CONCEPT': INDE_COLORS['PRIMARY'],
        'DE_RISK': INDE_COLORS['ATTENTION'],
        'DEPLOY': INDE_COLORS['THRIVING']
    }

    y_pos = 0.5
    bar_height = 0.3

    for i, phase in enumerate(phases):
        start = phase.get('start_day', i * 30)
        duration = phase.get('duration_days', 30)
        name = phase.get('name', f'Phase {i+1}')
        color = phase_colors.get(name, INDE_COLORS['SECONDARY'])

        ax.barh(y_pos, duration, left=start, height=bar_height,
                color=color, alpha=0.8, edgecolor='white')

        # Add phase label
        ax.text(start + duration/2, y_pos, name, ha='center', va='center',
                fontsize=10, fontweight='bold', color='white')

    # Add milestones if provided
    if milestones:
        for milestone in milestones:
            day = milestone.get('day', 0)
            name = milestone.get('name', 'Milestone')
            ax.axvline(x=day, color='#EF4444', linestyle='--', linewidth=2)
            ax.text(day, y_pos + 0.25, name, ha='center', fontsize=8, color='#EF4444')

    ax.set_ylim(0, 1)
    ax.set_xlabel('Days')
    ax.set_title('Timeline Journey')
    ax.set_yticks([])

    return fig_to_bytes(fig)


def create_velocity_curve_chart(actual: List[float], expected: List[float] = None) -> bytes:
    """
    Expected vs. actual velocity line chart with confidence band.

    Args:
        actual: List of actual velocity values
        expected: Optional list of expected values

    Returns:
        PNG image bytes
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    apply_inde_theme(ax)

    if not actual:
        ax.text(0.5, 0.5, 'No velocity data', ha='center', va='center')
        return fig_to_bytes(fig)

    x = range(len(actual))

    # Plot actual
    ax.plot(x, actual, color=INDE_COLORS['PRIMARY'], linewidth=2,
            label='Actual', marker='o', markersize=4)

    # Plot expected with confidence band
    if expected and len(expected) == len(actual):
        ax.plot(x, expected, color=INDE_COLORS['PORTFOLIO_AVG'],
                linewidth=2, linestyle='--', label='Expected')

        # Confidence band (±20%)
        upper = [e * 1.2 for e in expected]
        lower = [e * 0.8 for e in expected]
        ax.fill_between(x, lower, upper, color=INDE_COLORS['CONFIDENCE_BAND'], alpha=0.3)

    ax.set_xlabel('Week')
    ax.set_ylabel('Elements/Week')
    ax.set_title('Velocity Curve')
    ax.legend()

    return fig_to_bytes(fig)


def create_health_trend_chart(health_history: List[Dict]) -> bytes:
    """
    Area chart with zone-colored bands (green/blue/amber/orange/red).

    Args:
        health_history: List of {health_score, zone, calculated_at}

    Returns:
        PNG image bytes
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    apply_inde_theme(ax)

    if not health_history:
        ax.text(0.5, 0.5, 'No health history', ha='center', va='center')
        return fig_to_bytes(fig)

    # Limit data points
    max_points = SILR_ENRICHMENT_CONFIG.get("max_data_points_per_chart", 50)
    history = health_history[:max_points]
    history.reverse()  # Oldest first

    scores = [h.get('health_score', 50) for h in history]
    x = range(len(scores))

    # Draw zone background bands
    ax.axhspan(80, 100, color=INDE_COLORS['THRIVING'], alpha=0.1)
    ax.axhspan(60, 80, color=INDE_COLORS['HEALTHY'], alpha=0.1)
    ax.axhspan(40, 60, color=INDE_COLORS['ATTENTION'], alpha=0.1)
    ax.axhspan(20, 40, color=INDE_COLORS['AT_RISK'], alpha=0.1)
    ax.axhspan(0, 20, color=INDE_COLORS['CRITICAL'], alpha=0.1)

    # Plot health score line
    ax.plot(x, scores, color=INDE_COLORS['PRIMARY'], linewidth=2)
    ax.fill_between(x, scores, alpha=0.3, color=INDE_COLORS['PRIMARY'])

    ax.set_ylim(0, 100)
    ax.set_xlabel('Time')
    ax.set_ylabel('Health Score')
    ax.set_title('Health Score Trend')

    # Zone labels on right
    ax.text(len(scores) + 0.5, 90, 'THRIVING', fontsize=8, color=INDE_COLORS['THRIVING'])
    ax.text(len(scores) + 0.5, 70, 'HEALTHY', fontsize=8, color=INDE_COLORS['HEALTHY'])
    ax.text(len(scores) + 0.5, 50, 'ATTENTION', fontsize=8, color=INDE_COLORS['ATTENTION'])
    ax.text(len(scores) + 0.5, 30, 'AT_RISK', fontsize=8, color=INDE_COLORS['AT_RISK'])
    ax.text(len(scores) + 0.5, 10, 'CRITICAL', fontsize=8, color=INDE_COLORS['CRITICAL'])

    return fig_to_bytes(fig)


def create_risk_horizon_map(risks_by_horizon: Dict) -> bytes:
    """
    Three-column grouped bar chart by horizon.

    Args:
        risks_by_horizon: {short: int, medium: int, long: int}

    Returns:
        PNG image bytes
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    apply_inde_theme(ax)

    horizons = ['Short-term\n(0-14 days)', 'Medium-term\n(14-60 days)', 'Long-term\n(60+ days)']
    counts = [
        risks_by_horizon.get('short', 0),
        risks_by_horizon.get('medium', 0),
        risks_by_horizon.get('long', 0)
    ]

    colors = [INDE_COLORS['CRITICAL'], INDE_COLORS['ATTENTION'], INDE_COLORS['HEALTHY']]

    bars = ax.bar(horizons, counts, color=colors, alpha=0.8)

    # Add count labels on bars
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(count)}',
                ha='center', va='bottom', fontweight='bold')

    ax.set_ylabel('Number of Risks')
    ax.set_title('Risks by Time Horizon')

    return fig_to_bytes(fig)


def create_portfolio_heatmap(pursuit_health_data: List[Dict]) -> bytes:
    """
    Grid heatmap: rows=pursuits, columns=time periods.

    Args:
        pursuit_health_data: List of {name, health_history: [scores]}

    Returns:
        PNG image bytes
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    if not pursuit_health_data:
        ax.text(0.5, 0.5, 'No portfolio data', ha='center', va='center')
        ax.axis('off')
        return fig_to_bytes(fig)

    # Build matrix
    max_periods = 10
    pursuit_names = [p.get('name', 'Unknown')[:20] for p in pursuit_health_data]

    matrix = []
    for pursuit in pursuit_health_data:
        history = pursuit.get('health_history', [50])[:max_periods]
        # Pad with last value if needed
        while len(history) < max_periods:
            history.append(history[-1] if history else 50)
        matrix.append(history)

    matrix = np.array(matrix)

    # Create custom colormap for health zones
    from matplotlib.colors import LinearSegmentedColormap
    colors_list = [
        INDE_COLORS['CRITICAL'],
        INDE_COLORS['AT_RISK'],
        INDE_COLORS['ATTENTION'],
        INDE_COLORS['HEALTHY'],
        INDE_COLORS['THRIVING']
    ]
    cmap = LinearSegmentedColormap.from_list('health', colors_list, N=100)

    im = ax.imshow(matrix, cmap=cmap, aspect='auto', vmin=0, vmax=100)

    ax.set_yticks(range(len(pursuit_names)))
    ax.set_yticklabels(pursuit_names)
    ax.set_xlabel('Time Period')
    ax.set_title('Portfolio Health Heatmap')

    # Colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Health Score')

    return fig_to_bytes(fig)


def create_prediction_gauge(accuracy: float) -> bytes:
    """
    Semi-circular gauge chart for prediction accuracy.

    Args:
        accuracy: Accuracy percentage (0-100)

    Returns:
        PNG image bytes
    """
    fig, ax = plt.subplots(figsize=(6, 4))

    # Gauge parameters
    accuracy = max(0, min(100, accuracy))  # Clamp
    angle = 180 * (accuracy / 100)

    # Background arc
    bg_wedge = Wedge((0.5, 0.1), 0.4, 0, 180, width=0.15,
                     facecolor='#E2E8F0', edgecolor='none')
    ax.add_patch(bg_wedge)

    # Accuracy arc with color based on value
    if accuracy >= 70:
        color = INDE_COLORS['THRIVING']
    elif accuracy >= 50:
        color = INDE_COLORS['HEALTHY']
    elif accuracy >= 30:
        color = INDE_COLORS['ATTENTION']
    else:
        color = INDE_COLORS['CRITICAL']

    value_wedge = Wedge((0.5, 0.1), 0.4, 0, angle, width=0.15,
                        facecolor=color, edgecolor='none')
    ax.add_patch(value_wedge)

    # Center text
    ax.text(0.5, 0.15, f'{accuracy:.0f}%', ha='center', va='center',
            fontsize=24, fontweight='bold', color=color)
    ax.text(0.5, 0.0, 'Prediction Accuracy', ha='center', va='center',
            fontsize=10, color='#64748B')

    ax.set_xlim(0, 1)
    ax.set_ylim(-0.1, 0.6)
    ax.axis('off')

    return fig_to_bytes(fig)


def create_learning_sparkline(learning_data: List[float]) -> bytes:
    """
    Compact line chart for inline display of learning velocity.

    Args:
        learning_data: List of learning velocity values

    Returns:
        PNG image bytes
    """
    return create_sparkline(learning_data, color=INDE_COLORS['SECONDARY'])


def create_effectiveness_summary_chart(metrics: Dict) -> bytes:
    """
    Summary chart showing all 7 effectiveness metrics.

    Args:
        metrics: Dict of metric name -> {value, trend, interpretation}

    Returns:
        PNG image bytes
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    apply_inde_theme(ax)

    metric_names = [
        'Learning Velocity',
        'Prediction Accuracy',
        'Risk Validation ROI',
        'Pattern Success',
        'Fear Resolution',
        'Retro Completeness',
        'Time to Decision'
    ]

    metric_keys = [
        'learning_velocity_trend',
        'prediction_accuracy',
        'risk_validation_roi',
        'pattern_application_success',
        'fear_resolution_rate',
        'retrospective_completeness',
        'time_to_decision'
    ]

    values = []
    colors = []

    for key in metric_keys:
        m = metrics.get(key, {})
        val = m.get('value')
        if val is None:
            values.append(0)
            colors.append('#CBD5E1')  # Gray for no data
        else:
            # Normalize to 0-100 scale
            if key == 'learning_velocity_trend':
                # Ratio: 0.5=excellent, 1.5=poor -> invert and scale
                val = max(0, min(100, (1.5 - val) * 100))
            elif key == 'time_to_decision':
                # Lower is better, cap at 30 days
                val = max(0, 100 - (val / 30 * 100))

            values.append(val)

            if val >= 70:
                colors.append(INDE_COLORS['THRIVING'])
            elif val >= 50:
                colors.append(INDE_COLORS['HEALTHY'])
            elif val >= 30:
                colors.append(INDE_COLORS['ATTENTION'])
            else:
                colors.append(INDE_COLORS['AT_RISK'])

    y_pos = range(len(metric_names))
    bars = ax.barh(y_pos, values, color=colors, alpha=0.8)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(metric_names)
    ax.set_xlim(0, 100)
    ax.set_xlabel('Score')
    ax.set_title('Innovation Effectiveness Scorecard')

    # Add value labels
    for bar, val, color in zip(bars, values, colors):
        if color != '#CBD5E1':  # Not gray
            ax.text(val + 2, bar.get_y() + bar.get_height()/2,
                    f'{val:.0f}', va='center', fontsize=9)
        else:
            ax.text(5, bar.get_y() + bar.get_height()/2,
                    'No data', va='center', fontsize=9, color='#94A3B8')

    plt.tight_layout()
    return fig_to_bytes(fig)
