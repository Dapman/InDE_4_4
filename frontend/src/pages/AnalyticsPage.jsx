import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Heart,
  Clock,
  Target,
  Sparkles,
  FileText,
  Download,
} from 'lucide-react';
import { pursuitsApi } from '../api/pursuits';
import { cn } from '../lib/utils';

// =============================================================================
// METRIC CARD
// =============================================================================

function MetricCard({ title, value, subtitle, icon: Icon, color = 'inde', description }) {
  const colorClasses = {
    inde: 'text-inde-400',
    green: 'text-health-healthy',
    amber: 'text-health-caution',
    red: 'text-health-atrisk',
    blue: 'text-blue-400',
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
      {description && (
        <p className="text-caption text-zinc-600 mt-2">{description}</p>
      )}
    </div>
  );
}

// =============================================================================
// PHASE DISTRIBUTION BAR
// =============================================================================

function PhaseDistributionBar({ phases }) {
  const colors = {
    VISION: 'bg-phase-vision',
    PITCH: 'bg-phase-pitch',
    DE_RISK: 'bg-phase-derisk',
    BUILD: 'bg-phase-build',
    DEPLOY: 'bg-phase-deploy',
  };

  const total = Object.values(phases).reduce((a, b) => a + b, 0);
  if (total === 0) return null;

  return (
    <div className="space-y-3">
      {Object.entries(phases).map(([phase, count]) => {
        const percentage = (count / total) * 100;
        return (
          <div key={phase} className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-caption text-zinc-400">{phase.replace('_', '-')}</span>
              <span className="text-caption text-zinc-500">{count} ({Math.round(percentage)}%)</span>
            </div>
            <div className="h-2 bg-surface-3 rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all', colors[phase] || 'bg-inde-500')}
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// =============================================================================
// HEALTH DISTRIBUTION
// =============================================================================

function HealthDistribution({ healthy, caution, atRisk }) {
  const total = healthy + caution + atRisk;
  if (total === 0) return <p className="text-caption text-zinc-500">No data yet</p>;

  return (
    <div className="space-y-3">
      <div className="flex h-4 rounded-full overflow-hidden bg-surface-3">
        {healthy > 0 && (
          <div
            className="bg-health-healthy"
            style={{ width: `${(healthy / total) * 100}%` }}
          />
        )}
        {caution > 0 && (
          <div
            className="bg-health-caution"
            style={{ width: `${(caution / total) * 100}%` }}
          />
        )}
        {atRisk > 0 && (
          <div
            className="bg-health-atrisk"
            style={{ width: `${(atRisk / total) * 100}%` }}
          />
        )}
      </div>
      <div className="flex items-center justify-between text-caption">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-health-healthy" />
          <span className="text-zinc-400">Healthy ({healthy})</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-health-caution" />
          <span className="text-zinc-400">Caution ({caution})</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-health-atrisk" />
          <span className="text-zinc-400">At Risk ({atRisk})</span>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// MAIN ANALYTICS PAGE
// =============================================================================

export default function AnalyticsPage() {
  // Fetch pursuits data to compute analytics
  const { data: pursuitsData, isLoading } = useQuery({
    queryKey: ['analytics-pursuits'],
    queryFn: async () => {
      const response = await pursuitsApi.list();
      return response.data;
    },
    staleTime: 30000,
  });

  // Compute analytics from pursuits data
  const analytics = useMemo(() => {
    const pursuits = pursuitsData?.pursuits || [];
    if (pursuits.length === 0) {
      return {
        totalPursuits: 0,
        activePursuits: 0,
        completedPursuits: 0,
        avgHealth: 0,
        avgCompletionTime: 0,
        phases: {},
        healthDistribution: { healthy: 0, caution: 0, atRisk: 0 },
        methodologyBreakdown: {},
      };
    }

    const active = pursuits.filter((p) => p.state === 'ACTIVE' || p.status === 'active');
    const completed = pursuits.filter((p) => p.state === 'COMPLETED' || p.status === 'completed');
    const terminated = pursuits.filter((p) => p.state === 'TERMINATED' || p.status === 'terminated');

    // Health scores
    const healthScores = pursuits
      .map((p) => p.health_score ?? p.health ?? 50)
      .filter((h) => h !== undefined);
    const avgHealth = healthScores.length > 0
      ? healthScores.reduce((a, b) => a + b, 0) / healthScores.length
      : 0;

    // Health distribution
    const healthy = pursuits.filter((p) => (p.health_score ?? p.health ?? 50) >= 60).length;
    const caution = pursuits.filter((p) => {
      const h = p.health_score ?? p.health ?? 50;
      return h >= 40 && h < 60;
    }).length;
    const atRisk = pursuits.filter((p) => (p.health_score ?? p.health ?? 50) < 40).length;

    // Phase distribution
    const phases = {};
    pursuits.forEach((p) => {
      const phase = p.phase || p.current_phase || 'VISION';
      phases[phase] = (phases[phase] || 0) + 1;
    });

    // Methodology breakdown
    const methodologyBreakdown = {};
    pursuits.forEach((p) => {
      const method = p.archetype || p.methodology || 'freeform';
      methodologyBreakdown[method] = (methodologyBreakdown[method] || 0) + 1;
    });

    return {
      totalPursuits: pursuits.length,
      activePursuits: active.length,
      completedPursuits: completed.length,
      terminatedPursuits: terminated.length,
      avgHealth: Math.round(avgHealth),
      phases,
      healthDistribution: { healthy, caution, atRisk },
      methodologyBreakdown,
      successRate: (completed.length + terminated.length) > 0
        ? Math.round((completed.length / (completed.length + terminated.length)) * 100)
        : 0,
    };
  }, [pursuitsData]);

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-inde-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-surface-1">
      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-zinc-100 mb-1">
            Portfolio Analytics
          </h1>
          <p className="text-body-sm text-zinc-500">
            Innovation portfolio intelligence and effectiveness metrics
          </p>
        </div>

        {/* Summary Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <MetricCard
            title="Total Pursuits"
            value={analytics.totalPursuits}
            icon={Sparkles}
            color="inde"
          />
          <MetricCard
            title="Active"
            value={analytics.activePursuits}
            icon={TrendingUp}
            color="green"
          />
          <MetricCard
            title="Completed"
            value={analytics.completedPursuits}
            icon={Target}
            color="blue"
          />
          <MetricCard
            title="Success Rate"
            value={`${analytics.successRate}%`}
            icon={BarChart3}
            color={analytics.successRate >= 50 ? 'green' : 'amber'}
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Health Distribution */}
          <div className="bg-surface-2 border border-surface-border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-4">
              <Heart className="h-5 w-5 text-health-healthy" />
              <h2 className="text-body-sm font-medium text-zinc-300">
                Portfolio Health Distribution
              </h2>
            </div>
            <HealthDistribution {...analytics.healthDistribution} />
            <div className="mt-4 pt-4 border-t border-surface-border">
              <div className="flex items-center justify-between">
                <span className="text-caption text-zinc-500">Average Health Score</span>
                <span className={cn(
                  'text-body-sm font-medium',
                  analytics.avgHealth >= 60 ? 'text-health-healthy' :
                  analytics.avgHealth >= 40 ? 'text-health-caution' : 'text-health-atrisk'
                )}>
                  {analytics.avgHealth}/100
                </span>
              </div>
            </div>
          </div>

          {/* Phase Distribution */}
          <div className="bg-surface-2 border border-surface-border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-4">
              <Clock className="h-5 w-5 text-inde-400" />
              <h2 className="text-body-sm font-medium text-zinc-300">
                Phase Distribution
              </h2>
            </div>
            {Object.keys(analytics.phases).length > 0 ? (
              <PhaseDistributionBar phases={analytics.phases} />
            ) : (
              <p className="text-caption text-zinc-500">No phase data yet</p>
            )}
          </div>
        </div>

        {/* Methodology Breakdown */}
        <div className="bg-surface-2 border border-surface-border rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="h-5 w-5 text-inde-400" />
            <h2 className="text-body-sm font-medium text-zinc-300">
              Methodology Usage
            </h2>
          </div>
          {Object.keys(analytics.methodologyBreakdown).length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {Object.entries(analytics.methodologyBreakdown).map(([method, count]) => (
                <div
                  key={method}
                  className="bg-surface-3 rounded-lg p-3 text-center"
                >
                  <div className="text-lg font-bold text-zinc-200">{count}</div>
                  <div className="text-caption text-zinc-500 capitalize">
                    {method.replace('_', ' ')}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-caption text-zinc-500">Start pursuits to see methodology breakdown</p>
          )}
        </div>

        {/* Empty State */}
        {analytics.totalPursuits === 0 && (
          <div className="bg-surface-2 border border-surface-border rounded-lg p-8 text-center">
            <BarChart3 className="h-12 w-12 text-zinc-600 mx-auto mb-4" />
            <h3 className="text-body-md font-medium text-zinc-300 mb-2">
              No Analytics Data Yet
            </h3>
            <p className="text-body-sm text-zinc-500 max-w-md mx-auto">
              Start innovation pursuits to generate analytics and track your portfolio performance over time.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
