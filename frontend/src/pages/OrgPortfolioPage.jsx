import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Navigate, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { portfolioApi } from '../api/portfolio';
import { cn } from '../lib/utils';
import {
  Briefcase,
  Target,
  TrendingUp,
  Activity,
  Users,
  ChevronRight,
  Lightbulb,
  Rocket,
  Shield,
  Hammer,
  Flag,
  Check,
  ArrowRight,
} from 'lucide-react';

// Display labels for methodology names
const METHODOLOGY_LABELS = {
  lean_startup: 'Lean Startup',
  design_thinking: 'Design Thinking',
  stage_gate: 'Stage-Gate',
  triz: 'TRIZ',
  blue_ocean: 'Blue Ocean Strategy',
  freeform: 'Freeform',
  emergent: 'Emergent',
};

// Methodology colors
const METHODOLOGY_COLORS = {
  lean_startup: '#3B82F6',     // blue
  design_thinking: '#22C55E',   // green
  stage_gate: '#A855F7',        // purple
  triz: '#F97316',              // orange
  blue_ocean: '#14B8A6',        // teal
  freeform: '#6B7280',          // gray
  emergent: '#EAB308',          // gold
};

// Phase configuration
const PHASE_CONFIG = {
  VISION: { icon: Lightbulb, label: 'Vision', stage: 'discovery' },
  PITCH: { icon: Rocket, label: 'Pitch', stage: 'discovery' },
  DE_RISK: { icon: Shield, label: 'De-Risk', stage: 'development' },
  BUILD: { icon: Hammer, label: 'Build', stage: 'development' },
  DEPLOY: { icon: Flag, label: 'Deploy', stage: 'validation' },
};

/**
 * MetricCard - Displays a single aggregate metric
 */
function MetricCard({ icon: Icon, label, value, subtext, trend, className }) {
  return (
    <div className={cn(
      'bg-surface-3 border border-surface-border rounded-xl p-5',
      className
    )}>
      <div className="flex items-start justify-between mb-3">
        <div className="p-2 bg-surface-4 rounded-lg">
          <Icon className="w-5 h-5 text-inde-400" />
        </div>
        {trend && (
          <span className={cn(
            'text-caption font-medium',
            trend > 0 ? 'text-emerald-400' : trend < 0 ? 'text-rose-400' : 'text-zinc-500'
          )}>
            {trend > 0 ? '+' : ''}{trend}%
          </span>
        )}
      </div>
      <p className="text-display-sm font-semibold text-zinc-100">{value}</p>
      <p className="text-caption text-zinc-500 mt-1">{label}</p>
      {subtext && (
        <p className="text-caption text-zinc-600 mt-0.5">{subtext}</p>
      )}
    </div>
  );
}

/**
 * PipelineBar - Horizontal stacked bar for innovation pipeline
 */
function PipelineBar({ data }) {
  const total = data.discovery + data.development + data.validation + data.complete;
  if (total === 0) return null;

  const segments = [
    { key: 'discovery', label: 'Discovery', count: data.discovery, color: 'bg-phase-vision' },
    { key: 'development', label: 'Development', count: data.development, color: 'bg-phase-derisk' },
    { key: 'validation', label: 'Validation', count: data.validation, color: 'bg-phase-deploy' },
    { key: 'complete', label: 'Complete', count: data.complete, color: 'bg-emerald-500' },
  ];

  return (
    <div className="space-y-3">
      <div className="flex h-8 rounded-lg overflow-hidden bg-surface-4">
        {segments.map((seg) => (
          seg.count > 0 && (
            <div
              key={seg.key}
              className={cn('h-full transition-all', seg.color)}
              style={{ width: `${(seg.count / total) * 100}%` }}
            />
          )
        ))}
      </div>
      <div className="flex flex-wrap gap-4">
        {segments.map((seg) => (
          <div key={seg.key} className="flex items-center gap-2">
            <div className={cn('w-3 h-3 rounded', seg.color)} />
            <span className="text-caption text-zinc-400">
              {seg.label}: {seg.count}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * MethodologyEffectivenessChart - Grouped bar chart comparing methodologies
 */
function MethodologyEffectivenessChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-zinc-500 text-body-sm">
        No methodology data available yet
      </div>
    );
  }

  const maxSuccessRate = Math.max(...data.map(d => d.success_rate || 0), 100);
  const maxDuration = Math.max(...data.map(d => d.avg_duration || 0), 30);
  const maxHealth = Math.max(...data.map(d => d.avg_health || 0), 100);

  return (
    <div className="space-y-4">
      {data.map((item) => {
        const label = METHODOLOGY_LABELS[item.methodology] || item.methodology;
        const color = METHODOLOGY_COLORS[item.methodology] || '#6B7280';

        return (
          <div key={item.methodology} className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-body-sm text-zinc-300">{label}</span>
              <span className="text-caption text-zinc-500">{item.pursuit_count || 0} pursuits</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {/* Success Rate */}
              <div className="space-y-1">
                <div className="h-6 bg-surface-4 rounded overflow-hidden">
                  <div
                    className="h-full rounded transition-all"
                    style={{
                      width: `${((item.success_rate || 0) / maxSuccessRate) * 100}%`,
                      backgroundColor: color,
                    }}
                  />
                </div>
                <p className="text-caption text-zinc-500">Success: {item.success_rate || 0}%</p>
              </div>
              {/* Duration */}
              <div className="space-y-1">
                <div className="h-6 bg-surface-4 rounded overflow-hidden">
                  <div
                    className="h-full rounded transition-all opacity-70"
                    style={{
                      width: `${((item.avg_duration || 0) / maxDuration) * 100}%`,
                      backgroundColor: color,
                    }}
                  />
                </div>
                <p className="text-caption text-zinc-500">Avg Days: {item.avg_duration || 0}</p>
              </div>
              {/* Health */}
              <div className="space-y-1">
                <div className="h-6 bg-surface-4 rounded overflow-hidden">
                  <div
                    className="h-full rounded transition-all opacity-50"
                    style={{
                      width: `${((item.avg_health || 0) / maxHealth) * 100}%`,
                      backgroundColor: color,
                    }}
                  />
                </div>
                <p className="text-caption text-zinc-500">Health: {item.avg_health || 0}</p>
              </div>
            </div>
          </div>
        );
      })}
      <div className="flex gap-6 mt-4 pt-4 border-t border-surface-border">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded bg-inde-500" />
          <span className="text-caption text-zinc-500">Success Rate</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded bg-inde-500 opacity-70" />
          <span className="text-caption text-zinc-500">Avg Duration</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded bg-inde-500 opacity-50" />
          <span className="text-caption text-zinc-500">Avg Health</span>
        </div>
      </div>
    </div>
  );
}

/**
 * PipelineKanban - Kanban-style visualization of pursuits in pipeline stages
 */
function PipelineKanban({ pursuits, onPursuitClick }) {
  const stages = useMemo(() => {
    const discovery = [];
    const development = [];
    const validation = [];
    const complete = [];

    pursuits.forEach((p) => {
      const phase = p.phase || 'VISION';
      const stage = PHASE_CONFIG[phase]?.stage || 'discovery';
      const state = (p.state || p.status || 'ACTIVE').toUpperCase();

      if (state === 'COMPLETED' || state === 'ARCHIVED' || state === 'TERMINATED') {
        complete.push(p);
      } else if (stage === 'discovery') {
        discovery.push(p);
      } else if (stage === 'development') {
        development.push(p);
      } else {
        validation.push(p);
      }
    });

    return { discovery, development, validation, complete };
  }, [pursuits]);

  const columns = [
    { key: 'discovery', label: 'Discovery', items: stages.discovery, color: 'border-phase-vision' },
    { key: 'development', label: 'Development', items: stages.development, color: 'border-phase-derisk' },
    { key: 'validation', label: 'Validation', items: stages.validation, color: 'border-phase-deploy' },
    { key: 'complete', label: 'Complete', items: stages.complete, color: 'border-emerald-500' },
  ];

  return (
    <div className="grid grid-cols-4 gap-4">
      {columns.map((col) => (
        <div key={col.key} className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-body-sm font-medium text-zinc-300">{col.label}</h4>
            <span className="text-caption text-zinc-500">{col.items.length}</span>
          </div>
          <div className={cn('border-t-2 pt-3 space-y-2', col.color)}>
            {col.items.length === 0 ? (
              <p className="text-caption text-zinc-600 py-4 text-center">No pursuits</p>
            ) : (
              col.items.slice(0, 5).map((p) => (
                <button
                  key={p.id || p.pursuit_id}
                  onClick={() => onPursuitClick?.(p)}
                  className="w-full text-left bg-surface-4 hover:bg-surface-5 rounded-lg p-3 transition-colors"
                >
                  <p className="text-body-sm text-zinc-200 truncate">{p.title || p.name}</p>
                  <div className="flex items-center justify-between mt-1.5">
                    <span className="text-caption text-zinc-500">{p.owner_name || 'Unknown'}</span>
                    {p.health_zone && (
                      <span className={cn(
                        'w-2 h-2 rounded-full',
                        p.health_zone === 'green' ? 'bg-emerald-500' :
                        p.health_zone === 'amber' ? 'bg-amber-500' : 'bg-rose-500'
                      )} />
                    )}
                  </div>
                </button>
              ))
            )}
            {col.items.length > 5 && (
              <p className="text-caption text-zinc-500 text-center py-2">
                +{col.items.length - 5} more
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * LearningVelocityChart - Multi-line trend chart
 */
function LearningVelocityChart({ data }) {
  if (!data || !data.trends || data.trends.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-zinc-500 text-body-sm">
        No velocity data available yet
      </div>
    );
  }

  const maxValue = Math.max(
    ...data.trends.map(d => d.org_velocity || 0),
    ...data.trends.map(d => d.benchmark || 0),
    100
  );

  // Simple SVG line chart
  const width = 400;
  const height = 160;
  const padding = 30;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;

  const xScale = (i) => padding + (i / (data.trends.length - 1)) * chartWidth;
  const yScale = (v) => height - padding - (v / maxValue) * chartHeight;

  const orgLine = data.trends.map((d, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(d.org_velocity || 0)}`).join(' ');
  const benchmarkLine = data.trends.map((d, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(d.benchmark || 50)}`).join(' ');

  return (
    <div className="space-y-3">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-48">
        {/* Grid lines */}
        {[0, 25, 50, 75, 100].map((v) => (
          <g key={v}>
            <line
              x1={padding}
              y1={yScale(v)}
              x2={width - padding}
              y2={yScale(v)}
              stroke="rgb(63 63 70)"
              strokeDasharray="4"
            />
            <text
              x={padding - 8}
              y={yScale(v) + 4}
              className="fill-zinc-600 text-[10px]"
              textAnchor="end"
            >
              {v}
            </text>
          </g>
        ))}

        {/* Benchmark line */}
        <path
          d={benchmarkLine}
          fill="none"
          stroke="rgb(113 113 122)"
          strokeWidth="2"
          strokeDasharray="6"
        />

        {/* Org velocity line */}
        <path
          d={orgLine}
          fill="none"
          stroke="rgb(99 102 241)"
          strokeWidth="2.5"
        />

        {/* Data points */}
        {data.trends.map((d, i) => (
          <circle
            key={i}
            cx={xScale(i)}
            cy={yScale(d.org_velocity || 0)}
            r="4"
            fill="rgb(99 102 241)"
          />
        ))}

        {/* Month labels */}
        {data.trends.map((d, i) => (
          <text
            key={i}
            x={xScale(i)}
            y={height - 8}
            className="fill-zinc-500 text-[10px]"
            textAnchor="middle"
          >
            {d.month || `M${i + 1}`}
          </text>
        ))}
      </svg>

      <div className="flex gap-6 justify-center">
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-indigo-500" />
          <span className="text-caption text-zinc-400">Organization</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-zinc-500 border-dashed" />
          <span className="text-caption text-zinc-400">Industry Benchmark</span>
        </div>
      </div>
    </div>
  );
}

/**
 * OrgPortfolioPage - Organization-wide portfolio analytics (Enterprise only)
 */
export default function OrgPortfolioPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);

  // Check if user has org access
  const hasOrgAccess = user?.org_id && (user?.role === 'org_admin' || user?.role === 'org_member' || user?.is_enterprise);

  // Fetch org metrics
  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['org-portfolio-metrics'],
    queryFn: async () => {
      const response = await portfolioApi.getOrgMetrics();
      return response.data;
    },
    enabled: hasOrgAccess,
    staleTime: 60 * 1000,
  });

  // Fetch pipeline data
  const { data: pipeline, isLoading: pipelineLoading } = useQuery({
    queryKey: ['org-portfolio-pipeline'],
    queryFn: async () => {
      const response = await portfolioApi.getOrgPipeline();
      return response.data;
    },
    enabled: hasOrgAccess,
    staleTime: 60 * 1000,
  });

  // Fetch methodology effectiveness
  const { data: effectiveness, isLoading: effectivenessLoading } = useQuery({
    queryKey: ['org-methodology-effectiveness'],
    queryFn: async () => {
      const response = await portfolioApi.getMethodologyEffectiveness();
      return response.data;
    },
    enabled: hasOrgAccess,
    staleTime: 60 * 1000,
  });

  // Fetch learning velocity trends
  const { data: velocity, isLoading: velocityLoading } = useQuery({
    queryKey: ['org-learning-velocity'],
    queryFn: async () => {
      const response = await portfolioApi.getOrgLearningVelocity();
      return response.data;
    },
    enabled: hasOrgAccess,
    staleTime: 60 * 1000,
  });

  // Redirect non-enterprise users
  if (!hasOrgAccess) {
    return <Navigate to="/portfolio" replace />;
  }

  const handlePursuitClick = (pursuit) => {
    const id = pursuit.id || pursuit.pursuit_id;
    if (id) {
      navigate(`/pursuit/${id}`);
    }
  };

  const isLoading = metricsLoading || pipelineLoading;

  if (isLoading) {
    return (
      <div className="flex-1 p-6 overflow-y-auto">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 w-64 bg-surface-4 rounded" />
            <div className="grid grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-32 bg-surface-3 rounded-xl" />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 overflow-y-auto">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-display-md font-semibold text-zinc-100">
            Organization Portfolio
          </h1>
          <p className="text-body-sm text-zinc-500 mt-1">
            Innovation analytics across your organization
          </p>
        </div>

        {/* Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            icon={Briefcase}
            label="Active Pursuits"
            value={metrics?.total_active || 0}
            subtext={`${metrics?.total_innovators || 0} innovators`}
          />
          <MetricCard
            icon={Target}
            label="Success Rate"
            value={`${metrics?.success_rate || 0}%`}
            trend={metrics?.success_rate_trend}
          />
          <MetricCard
            icon={Activity}
            label="Avg Health Score"
            value={metrics?.avg_health || 0}
            subtext={metrics?.health_zone || 'Healthy'}
          />
          <MetricCard
            icon={TrendingUp}
            label="Learning Velocity"
            value={metrics?.learning_velocity || 0}
            trend={metrics?.velocity_trend}
          />
        </div>

        {/* Innovation Pipeline Bar */}
        <div className="bg-surface-3 border border-surface-border rounded-xl p-6">
          <h2 className="text-body-lg font-medium text-zinc-200 mb-4">
            Innovation Pipeline
          </h2>
          <PipelineBar
            data={{
              discovery: pipeline?.stages?.discovery || metrics?.pipeline_discovery || 0,
              development: pipeline?.stages?.development || metrics?.pipeline_development || 0,
              validation: pipeline?.stages?.validation || metrics?.pipeline_validation || 0,
              complete: pipeline?.stages?.complete || metrics?.pipeline_complete || 0,
            }}
          />
        </div>

        {/* Two-column layout for charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Methodology Effectiveness */}
          <div className="bg-surface-3 border border-surface-border rounded-xl p-6">
            <h2 className="text-body-lg font-medium text-zinc-200 mb-4">
              Methodology Effectiveness
            </h2>
            <MethodologyEffectivenessChart
              data={effectiveness?.methodologies || []}
            />
          </div>

          {/* Learning Velocity Trends */}
          <div className="bg-surface-3 border border-surface-border rounded-xl p-6">
            <h2 className="text-body-lg font-medium text-zinc-200 mb-4">
              Learning Velocity Trend
            </h2>
            <LearningVelocityChart data={velocity} />
          </div>
        </div>

        {/* Pipeline Kanban */}
        <div className="bg-surface-3 border border-surface-border rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-body-lg font-medium text-zinc-200">
              Pursuits by Stage
            </h2>
            <button
              onClick={() => navigate('/portfolio')}
              className="flex items-center gap-1 text-caption text-inde-400 hover:text-inde-300"
            >
              View all pursuits
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          <PipelineKanban
            pursuits={pipeline?.pursuits || []}
            onPursuitClick={handlePursuitClick}
          />
        </div>

        {/* Team Breakdown (if available) */}
        {metrics?.teams && metrics.teams.length > 0 && (
          <div className="bg-surface-3 border border-surface-border rounded-xl p-6">
            <h2 className="text-body-lg font-medium text-zinc-200 mb-4">
              Team Performance
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {metrics.teams.map((team) => (
                <div
                  key={team.id || team.name}
                  className="bg-surface-4 rounded-lg p-4"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-surface-5 rounded-lg">
                      <Users className="w-4 h-4 text-inde-400" />
                    </div>
                    <div>
                      <p className="text-body-sm font-medium text-zinc-200">
                        {team.name}
                      </p>
                      <p className="text-caption text-zinc-500">
                        {team.member_count || 0} members
                      </p>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 mt-4">
                    <div>
                      <p className="text-display-xs font-semibold text-zinc-100">
                        {team.active_pursuits || 0}
                      </p>
                      <p className="text-caption text-zinc-600">Active</p>
                    </div>
                    <div>
                      <p className="text-display-xs font-semibold text-zinc-100">
                        {team.success_rate || 0}%
                      </p>
                      <p className="text-caption text-zinc-600">Success</p>
                    </div>
                    <div>
                      <p className="text-display-xs font-semibold text-zinc-100">
                        {team.avg_health || 0}
                      </p>
                      <p className="text-caption text-zinc-600">Health</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
