import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  BarChart3,
  TrendingUp,
  Heart,
  Clock,
  CheckCircle,
  XCircle,
  PauseCircle,
  LayoutGrid,
  List,
  Filter,
  Lightbulb,
  ArrowRight,
} from 'lucide-react';
import { pursuitsApi } from '../api/pursuits';
import { useDisplayLabel } from '../hooks/useDisplayLabel';
import { cn } from '../lib/utils';

// =============================================================================
// METRIC CARD
// =============================================================================

function MetricCard({ title, value, subtitle, icon: Icon, trend, color = 'inde' }) {
  const colorClasses = {
    inde: 'text-inde-400',
    green: 'text-health-healthy',
    amber: 'text-health-caution',
    red: 'text-health-atrisk',
  };

  return (
    <div className="bg-surface-2 border border-surface-border rounded-lg p-4">
      <div className="flex items-start justify-between mb-2">
        <span className="text-caption text-zinc-500">{title}</span>
        {Icon && <Icon className={cn('h-5 w-5', colorClasses[color])} />}
      </div>
      <div className="flex items-baseline gap-2">
        <span className={cn('text-2xl font-bold', colorClasses[color])}>
          {value}
        </span>
        {subtitle && (
          <span className="text-caption text-zinc-500">{subtitle}</span>
        )}
      </div>
      {trend !== undefined && (
        <div className="flex items-center gap-1 mt-2">
          <TrendingUp
            className={cn(
              'h-3 w-3',
              trend >= 0 ? 'text-health-healthy' : 'text-health-atrisk rotate-180'
            )}
          />
          <span
            className={cn(
              'text-caption',
              trend >= 0 ? 'text-health-healthy' : 'text-health-atrisk'
            )}
          >
            {trend >= 0 ? '+' : ''}{trend}% vs last period
          </span>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// PURSUIT CARD (Grid View)
// =============================================================================

function PursuitCard({ pursuit, onClick }) {
  const methodologyLabel = useDisplayLabel('methodologies', pursuit.archetype || pursuit.methodology);
  const phaseLabel = useDisplayLabel('phases', pursuit.current_phase || pursuit.phase);
  const statusLabel = useDisplayLabel('pursuit_states', pursuit.state || pursuit.status);

  // Health color
  const healthScore = pursuit.health_score ?? pursuit.health ?? 50;
  const healthColor =
    healthScore >= 60
      ? 'text-health-healthy'
      : healthScore >= 40
        ? 'text-health-caution'
        : 'text-health-atrisk';

  // Status badge colors
  const statusColors = {
    ACTIVE: 'bg-health-healthy/20 text-health-healthy',
    COMPLETED: 'bg-inde-500/20 text-inde-400',
    SUSPENDED: 'bg-health-caution/20 text-health-caution',
    TERMINATED: 'bg-health-atrisk/20 text-health-atrisk',
  };

  return (
    <div
      onClick={() => onClick?.(pursuit)}
      className="bg-surface-2 border border-surface-border rounded-lg p-4 cursor-pointer hover:border-inde-500/50 transition-colors"
    >
      {/* Title and methodology */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <h3 className="text-body-sm font-medium text-zinc-200 line-clamp-2">
          {pursuit.title || pursuit.name}
        </h3>
        <span
          className={cn(
            'px-2 py-0.5 rounded-full text-caption whitespace-nowrap',
            statusColors[pursuit.state] || statusColors.ACTIVE
          )}
        >
          {statusLabel.label || pursuit.state}
        </span>
      </div>

      {/* Methodology badge */}
      <div className="flex items-center gap-2 mb-3">
        <span className="px-2 py-0.5 bg-phase-vision/20 text-phase-vision rounded text-caption">
          {methodologyLabel.label || pursuit.archetype || 'Freeform'}
        </span>
      </div>

      {/* Phase progress */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-caption text-zinc-500">
            {phaseLabel.label || pursuit.current_phase || 'Vision'}
          </span>
          <span className="text-caption text-zinc-500">
            {pursuit.phase_progress || 0}%
          </span>
        </div>
        <div className="h-1.5 bg-surface-3 rounded-full overflow-hidden">
          <div
            className="h-full bg-inde-500 rounded-full transition-all"
            style={{ width: `${pursuit.phase_progress || 0}%` }}
          />
        </div>
      </div>

      {/* Health and maturity */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <Heart className={cn('h-4 w-4', healthColor)} />
          <span className={cn('text-caption', healthColor)}>
            {Math.round(healthScore)}
          </span>
        </div>
        {pursuit.maturity_level && (
          <span className="text-caption text-zinc-500">
            {pursuit.maturity_level}
          </span>
        )}
        {pursuit.last_activity && (
          <span className="text-caption text-zinc-600">
            {new Date(pursuit.last_activity).toLocaleDateString()}
          </span>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// PURSUIT ROW (List View)
// =============================================================================

function PursuitRow({ pursuit, onClick }) {
  const methodologyLabel = useDisplayLabel('methodologies', pursuit.archetype || pursuit.methodology);
  const phaseLabel = useDisplayLabel('phases', pursuit.current_phase || pursuit.phase);
  const statusLabel = useDisplayLabel('pursuit_states', pursuit.state || pursuit.status);

  const healthScore = pursuit.health_score ?? pursuit.health ?? 50;
  const healthColor =
    healthScore >= 60
      ? 'text-health-healthy'
      : healthScore >= 40
        ? 'text-health-caution'
        : 'text-health-atrisk';

  return (
    <tr
      onClick={() => onClick?.(pursuit)}
      className="border-b border-surface-border hover:bg-surface-3/50 cursor-pointer transition-colors"
    >
      <td className="py-3 px-4">
        <span className="text-body-sm text-zinc-200">
          {pursuit.title || pursuit.name}
        </span>
      </td>
      <td className="py-3 px-4">
        <span className="text-caption text-zinc-400">
          {methodologyLabel.label || pursuit.archetype}
        </span>
      </td>
      <td className="py-3 px-4">
        <span className="text-caption text-zinc-400">
          {phaseLabel.label || pursuit.current_phase}
        </span>
      </td>
      <td className="py-3 px-4">
        <span className={cn('text-caption', healthColor)}>
          {Math.round(healthScore)}
        </span>
      </td>
      <td className="py-3 px-4">
        <span className="text-caption text-zinc-400">
          {pursuit.maturity_level || '-'}
        </span>
      </td>
      <td className="py-3 px-4">
        <span className="text-caption text-zinc-400">
          {statusLabel.label || pursuit.state}
        </span>
      </td>
    </tr>
  );
}

// =============================================================================
// METHODOLOGY DONUT CHART (Simple CSS)
// =============================================================================

function MethodologyDonut({ data }) {
  if (!data || data.length === 0) return null;

  const total = data.reduce((sum, d) => sum + d.count, 0);
  const colors = {
    lean_startup: '#3b82f6', // blue
    design_thinking: '#22c55e', // green
    stage_gate: '#a855f7', // purple
    triz: '#f97316', // orange
    blue_ocean: '#14b8a6', // teal
    freeform: '#71717a', // gray
    emergent: '#eab308', // gold
  };

  // Calculate segments
  let currentAngle = 0;
  const segments = data.map((d) => {
    const angle = (d.count / total) * 360;
    const segment = {
      ...d,
      startAngle: currentAngle,
      endAngle: currentAngle + angle,
      color: colors[d.archetype] || '#71717a',
    };
    currentAngle += angle;
    return segment;
  });

  // Create conic gradient
  const gradientStops = segments
    .map((s) => `${s.color} ${s.startAngle}deg ${s.endAngle}deg`)
    .join(', ');

  return (
    <div className="flex items-center gap-4">
      {/* Donut */}
      <div
        className="w-24 h-24 rounded-full relative"
        style={{
          background: `conic-gradient(${gradientStops})`,
        }}
      >
        <div className="absolute inset-3 bg-surface-1 rounded-full flex items-center justify-center">
          <span className="text-body-sm font-medium text-zinc-300">{total}</span>
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-col gap-1">
        {segments.map((s) => (
          <div key={s.archetype} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: s.color }}
            />
            <span className="text-caption text-zinc-400">
              {s.label || s.archetype} ({s.count})
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// PATTERN INSIGHT CARD
// =============================================================================

function PatternInsightCard({ insight }) {
  return (
    <div className="bg-inde-500/10 border border-inde-500/20 rounded-lg p-3">
      <div className="flex items-start gap-2">
        <Lightbulb className="h-4 w-4 text-inde-400 mt-0.5 flex-shrink-0" />
        <p className="text-body-sm text-zinc-300">{insight.message || insight}</p>
      </div>
    </div>
  );
}

// =============================================================================
// MAIN PORTFOLIO PAGE
// =============================================================================

export function PortfolioPage() {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'
  const [statusFilter, setStatusFilter] = useState('all');
  const [methodologyFilter, setMethodologyFilter] = useState('all');

  // Fetch portfolio data - use existing pursuits API endpoint
  const { data: pursuitsData, isLoading: pursuitsLoading } = useQuery({
    queryKey: ['portfolio-pursuits'],
    queryFn: async () => {
      const response = await pursuitsApi.list();
      return response.data;
    },
    staleTime: 30000,
  });

  // Compute metrics locally from pursuits data
  const computedMetrics = useMemo(() => {
    const pursuits = pursuitsData?.pursuits || [];
    if (pursuits.length === 0) return { active_count: 0, success_rate: 0, average_health: 0, learning_velocity: 0 };

    const active = pursuits.filter((p) => p.state === 'ACTIVE' || p.status === 'active');
    const completed = pursuits.filter((p) => p.state === 'COMPLETED' || p.status === 'completed');
    const terminated = pursuits.filter((p) => p.state === 'TERMINATED' || p.status === 'terminated');

    const successRate = (completed.length + terminated.length) > 0
      ? (completed.length / (completed.length + terminated.length)) * 100
      : 0;

    const healthScores = pursuits
      .map((p) => p.health_score ?? p.health ?? 50)
      .filter((h) => h !== undefined);
    const avgHealth = healthScores.length > 0
      ? healthScores.reduce((a, b) => a + b, 0) / healthScores.length
      : 50;

    return {
      active_count: active.length,
      success_rate: successRate,
      average_health: avgHealth,
      learning_velocity: Math.min(100, pursuits.length * 10 + completed.length * 5),
    };
  }, [pursuitsData]);

  // Compute methodology distribution locally
  const computedMethodologyData = useMemo(() => {
    const pursuits = pursuitsData?.pursuits || [];
    const counts = {};
    const labels = {
      lean_startup: 'Lean Startup',
      design_thinking: 'Design Thinking',
      stage_gate: 'Stage-Gate',
      triz: 'TRIZ',
      blue_ocean: 'Blue Ocean',
      freeform: 'Freeform',
      emergent: 'Emergent',
    };

    pursuits.forEach((p) => {
      const arch = p.archetype || p.methodology || 'freeform';
      counts[arch] = (counts[arch] || 0) + 1;
    });

    return {
      distribution: Object.entries(counts).map(([archetype, count]) => ({
        archetype,
        label: labels[archetype] || archetype,
        count,
      })),
    };
  }, [pursuitsData]);

  // Generate insights locally based on pursuits patterns
  const computedInsights = useMemo(() => {
    const pursuits = pursuitsData?.pursuits || [];
    const insights = [];

    const active = pursuits.filter((p) => p.state === 'ACTIVE');
    const lowHealth = active.filter((p) => (p.health_score ?? p.health ?? 50) < 40);

    if (lowHealth.length > 0) {
      insights.push({
        message: `${lowHealth.length} pursuit${lowHealth.length > 1 ? 's' : ''} need${lowHealth.length === 1 ? 's' : ''} attention - health score below 40.`,
      });
    }

    const methodologies = [...new Set(pursuits.map((p) => p.archetype || p.methodology))];
    if (methodologies.length > 2) {
      insights.push({
        message: `You're exploring ${methodologies.length} different methodologies - great for finding what works!`,
      });
    }

    const completed = pursuits.filter((p) => p.state === 'COMPLETED');
    if (completed.length > 0) {
      insights.push({
        message: `${completed.length} completed pursuit${completed.length > 1 ? 's' : ''} - your experience is growing!`,
      });
    }

    if (insights.length === 0 && active.length > 0) {
      insights.push({
        message: `${active.length} active pursuit${active.length > 1 ? 's' : ''} in progress. Keep the momentum going!`,
      });
    }

    return { insights };
  }, [pursuitsData]);

  // Filter pursuits
  const filteredPursuits = useMemo(() => {
    let pursuits = pursuitsData?.pursuits || [];

    if (statusFilter !== 'all') {
      pursuits = pursuits.filter((p) => p.state === statusFilter);
    }

    if (methodologyFilter !== 'all') {
      pursuits = pursuits.filter(
        (p) => p.archetype === methodologyFilter || p.methodology === methodologyFilter
      );
    }

    return pursuits;
  }, [pursuitsData, statusFilter, methodologyFilter]);

  // Extract metrics from computed data
  const activePursuits = computedMetrics.active_count;
  const successRate = computedMetrics.success_rate;
  const avgHealth = computedMetrics.average_health;
  const learningVelocity = computedMetrics.learning_velocity;

  // Handle pursuit click
  const handlePursuitClick = (pursuit) => {
    navigate(`/pursuit/${pursuit.id}`);
  };

  return (
    <div className="h-full overflow-y-auto bg-surface-1">
      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-zinc-100 mb-1">
            Innovation Portfolio
          </h1>
          <p className="text-body-sm text-zinc-500">
            Your complete innovation landscape
          </p>
        </div>

        {/* Metrics overview */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <MetricCard
            title="Active Pursuits"
            value={activePursuits}
            icon={BarChart3}
            color="inde"
          />
          <MetricCard
            title="Success Rate"
            value={`${Math.round(successRate)}%`}
            icon={CheckCircle}
            color={successRate >= 50 ? 'green' : 'amber'}
          />
          <MetricCard
            title="Average Health"
            value={Math.round(avgHealth)}
            subtitle="/ 100"
            icon={Heart}
            color={avgHealth >= 60 ? 'green' : avgHealth >= 40 ? 'amber' : 'red'}
          />
          <MetricCard
            title="Learning Velocity"
            value={Math.round(learningVelocity)}
            icon={TrendingUp}
            color="inde"
          />
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Methodology distribution */}
          <div className="bg-surface-2 border border-surface-border rounded-lg p-4">
            <h2 className="text-body-sm font-medium text-zinc-300 mb-4">
              Methodology Distribution
            </h2>
            <MethodologyDonut data={computedMethodologyData?.distribution || []} />
          </div>

          {/* Pattern insights */}
          <div className="bg-surface-2 border border-surface-border rounded-lg p-4">
            <h2 className="text-body-sm font-medium text-zinc-300 mb-4">
              Portfolio Insights
            </h2>
            <div className="space-y-2">
              {(computedInsights?.insights || []).slice(0, 3).map((insight, i) => (
                <PatternInsightCard key={i} insight={insight} />
              ))}
              {(!computedInsights?.insights || computedInsights.insights.length === 0) && (
                <p className="text-caption text-zinc-500 italic">
                  Complete more pursuits to unlock portfolio insights.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Pursuits section */}
        <div className="bg-surface-2 border border-surface-border rounded-lg">
          {/* Toolbar */}
          <div className="flex items-center justify-between p-4 border-b border-surface-border">
            <h2 className="text-body-sm font-medium text-zinc-300">
              All Pursuits ({filteredPursuits.length})
            </h2>

            <div className="flex items-center gap-3">
              {/* Filters */}
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-2 py-1 text-caption bg-surface-3 border border-surface-border rounded text-zinc-300"
              >
                <option value="all">All Status</option>
                <option value="ACTIVE">Active</option>
                <option value="COMPLETED">Completed</option>
                <option value="SUSPENDED">Suspended</option>
                <option value="TERMINATED">Terminated</option>
              </select>

              <select
                value={methodologyFilter}
                onChange={(e) => setMethodologyFilter(e.target.value)}
                className="px-2 py-1 text-caption bg-surface-3 border border-surface-border rounded text-zinc-300"
              >
                <option value="all">All Methods</option>
                <option value="lean_startup">Lean Startup</option>
                <option value="design_thinking">Design Thinking</option>
                <option value="stage_gate">Stage-Gate</option>
                <option value="triz">TRIZ</option>
                <option value="blue_ocean">Blue Ocean</option>
                <option value="freeform">Freeform</option>
              </select>

              {/* View toggle */}
              <div className="flex items-center border border-surface-border rounded overflow-hidden">
                <button
                  onClick={() => setViewMode('grid')}
                  className={cn(
                    'p-1.5 transition-colors',
                    viewMode === 'grid'
                      ? 'bg-inde-500/20 text-inde-400'
                      : 'text-zinc-500 hover:text-zinc-300'
                  )}
                >
                  <LayoutGrid className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={cn(
                    'p-1.5 transition-colors',
                    viewMode === 'list'
                      ? 'bg-inde-500/20 text-inde-400'
                      : 'text-zinc-500 hover:text-zinc-300'
                  )}
                >
                  <List className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="p-4">
            {pursuitsLoading ? (
              <div className="animate-pulse space-y-4">
                <div className="h-32 bg-surface-3 rounded" />
                <div className="h-32 bg-surface-3 rounded" />
              </div>
            ) : filteredPursuits.length === 0 ? (
              <div className="text-center py-12">
                <BarChart3 className="h-12 w-12 text-zinc-600 mx-auto mb-4" />
                <p className="text-body-sm text-zinc-500 mb-2">
                  No pursuits found
                </p>
                <p className="text-caption text-zinc-600">
                  {statusFilter !== 'all' || methodologyFilter !== 'all'
                    ? 'Try adjusting your filters'
                    : 'Start a new pursuit to begin your innovation journey'}
                </p>
              </div>
            ) : viewMode === 'grid' ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredPursuits.map((pursuit) => (
                  <PursuitCard
                    key={pursuit.id}
                    pursuit={pursuit}
                    onClick={handlePursuitClick}
                  />
                ))}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-surface-border">
                      <th className="py-2 px-4 text-left text-caption font-medium text-zinc-500">
                        Title
                      </th>
                      <th className="py-2 px-4 text-left text-caption font-medium text-zinc-500">
                        Methodology
                      </th>
                      <th className="py-2 px-4 text-left text-caption font-medium text-zinc-500">
                        Phase
                      </th>
                      <th className="py-2 px-4 text-left text-caption font-medium text-zinc-500">
                        Health
                      </th>
                      <th className="py-2 px-4 text-left text-caption font-medium text-zinc-500">
                        Maturity
                      </th>
                      <th className="py-2 px-4 text-left text-caption font-medium text-zinc-500">
                        Status
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPursuits.map((pursuit) => (
                      <PursuitRow
                        key={pursuit.id}
                        pursuit={pursuit}
                        onClick={handlePursuitClick}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default PortfolioPage;
