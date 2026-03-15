import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../stores/authStore';
import { systemApi } from '../api/system';
import { Navigate } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Database,
  Users,
  Clock,
  TrendingUp,
  Shield,
  Server,
  BarChart2,
  Circle,
  Mail,
} from 'lucide-react';
import { cn } from '../lib/utils';

// =============================================================================
// DIAGNOSTICS SECTION
// =============================================================================

function DiagnosticsSection({ title, icon: Icon, children, status }) {
  const statusColors = {
    healthy: 'text-green-500',
    degraded: 'text-yellow-500',
    critical: 'text-red-500',
    unknown: 'text-zinc-500',
  };

  return (
    <div className="bg-surface-2 border border-surface-border rounded-lg p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {Icon && <Icon className="w-5 h-5 text-inde-400" />}
          <h2 className="text-body-md font-medium text-zinc-200">{title}</h2>
        </div>
        {status && (
          <span className={cn('text-caption', statusColors[status])}>
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </span>
        )}
      </div>
      <div>{children}</div>
    </div>
  );
}

// =============================================================================
// STAT CARD
// =============================================================================

function StatCard({ label, value, sublabel, icon: Icon, trend }) {
  return (
    <div className="bg-surface-3 border border-surface-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-caption text-zinc-500">{label}</span>
        {Icon && <Icon className="w-4 h-4 text-zinc-500" />}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-heading-lg text-zinc-100">{value}</span>
        {trend && (
          <span className={cn(
            'text-caption',
            trend > 0 ? 'text-green-500' : trend < 0 ? 'text-red-500' : 'text-zinc-500'
          )}>
            {trend > 0 ? '+' : ''}{trend}%
          </span>
        )}
      </div>
      {sublabel && <span className="text-caption text-zinc-600">{sublabel}</span>}
    </div>
  );
}

// =============================================================================
// ERROR TABLE
// =============================================================================

function ErrorTable({ errors }) {
  if (!errors || errors.length === 0) {
    return (
      <div className="text-center py-8 text-zinc-500">
        <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
        <p className="text-body-sm">No recent errors</p>
      </div>
    );
  }

  const levelColors = {
    ERROR: 'text-red-400 bg-red-500/10',
    WARNING: 'text-yellow-400 bg-yellow-500/10',
    CRITICAL: 'text-red-500 bg-red-600/20',
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-body-sm">
        <thead>
          <tr className="border-b border-surface-border">
            <th className="text-left py-2 px-3 text-zinc-500 font-medium">Time</th>
            <th className="text-left py-2 px-3 text-zinc-500 font-medium">Level</th>
            <th className="text-left py-2 px-3 text-zinc-500 font-medium">Module</th>
            <th className="text-left py-2 px-3 text-zinc-500 font-medium">Message</th>
          </tr>
        </thead>
        <tbody>
          {errors.map((error, idx) => (
            <tr key={idx} className="border-b border-surface-border/50 hover:bg-surface-3">
              <td className="py-2 px-3 text-zinc-400 whitespace-nowrap">
                {new Date(error.timestamp).toLocaleTimeString()}
              </td>
              <td className="py-2 px-3">
                <span className={cn(
                  'px-2 py-0.5 rounded text-caption',
                  levelColors[error.level] || 'text-zinc-400'
                )}>
                  {error.level}
                </span>
              </td>
              <td className="py-2 px-3 text-zinc-400">{error.module}</td>
              <td className="py-2 px-3 text-zinc-300 max-w-md truncate">
                {error.message}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// =============================================================================
// ONBOARDING FUNNEL
// =============================================================================

function OnboardingFunnel({ funnel }) {
  if (!funnel || funnel.status === 'unavailable') {
    return (
      <div className="text-center py-4 text-zinc-500">
        <p className="text-body-sm">Onboarding metrics unavailable</p>
      </div>
    );
  }

  const criteriaLabels = {
    vision_artifact_created: 'Vision Created',
    fear_identified: 'Fear Identified',
    methodology_selected: 'Methodology Selected',
    iml_pattern_engaged: 'IML Engaged',
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Sessions"
          value={funnel.total_sessions || 0}
          sublabel={`Last ${funnel.period_days} days`}
          icon={Users}
        />
        <StatCard
          label="Completed"
          value={funnel.completed_sessions || 0}
          sublabel={`${((funnel.completion_rate || 0) * 100).toFixed(1)}% rate`}
          icon={CheckCircle}
        />
        <StatCard
          label="Avg Duration"
          value={funnel.average_duration_seconds
            ? `${Math.round(funnel.average_duration_seconds / 60)}m`
            : 'N/A'
          }
          sublabel="Time to complete"
          icon={Clock}
        />
        <StatCard
          label="Completion Rate"
          value={`${((funnel.completion_rate || 0) * 100).toFixed(0)}%`}
          icon={TrendingUp}
        />
      </div>

      {funnel.criteria_rates && Object.keys(funnel.criteria_rates).length > 0 && (
        <div className="mt-6">
          <h3 className="text-body-sm text-zinc-400 mb-3">Criterion Completion Rates</h3>
          <div className="space-y-2">
            {Object.entries(funnel.criteria_rates).map(([criterion, rate]) => (
              <div key={criterion} className="flex items-center gap-3">
                <span className="text-caption text-zinc-500 w-40">
                  {criteriaLabels[criterion] || criterion}
                </span>
                <div className="flex-1 h-2 bg-surface-4 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-inde-500 rounded-full transition-all"
                    style={{ width: `${(rate || 0) * 100}%` }}
                  />
                </div>
                <span className="text-caption text-zinc-400 w-12 text-right">
                  {((rate || 0) * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {funnel.screen_drop_off && Object.keys(funnel.screen_drop_off).length > 0 && (
        <div className="mt-6">
          <h3 className="text-body-sm text-zinc-400 mb-3">Screen Drop-off</h3>
          <div className="flex gap-2">
            {Object.entries(funnel.screen_drop_off).map(([screen, count]) => (
              <div key={screen} className="flex-1 bg-surface-3 rounded p-2 text-center">
                <span className="text-heading-sm text-zinc-200">{count}</span>
                <span className="text-caption text-zinc-500 block">
                  {screen.replace('_', ' ')}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// SYSTEM HEALTH
// =============================================================================

function SystemHealth({ health }) {
  if (!health) {
    return <p className="text-zinc-500">Health data unavailable</p>;
  }

  const statusIcon = {
    healthy: <CheckCircle className="w-5 h-5 text-green-500" />,
    degraded: <AlertTriangle className="w-5 h-5 text-yellow-500" />,
    critical: <XCircle className="w-5 h-5 text-red-500" />,
    unknown: <AlertCircle className="w-5 h-5 text-zinc-500" />,
  };

  return (
    <div className="space-y-3">
      {Object.entries(health)
        .filter(([key]) => key !== 'overall')
        .map(([key, value]) => (
          <div
            key={key}
            className="flex items-center justify-between py-2 border-b border-surface-border/50"
          >
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-zinc-500" />
              <span className="text-body-sm text-zinc-300 capitalize">{key}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-caption text-zinc-500">
                {value?.message || value?.status || 'Unknown'}
              </span>
              {statusIcon[value?.status] || statusIcon.unknown}
            </div>
          </div>
        ))}
    </div>
  );
}

// =============================================================================
// ACTIVE USERS TABLE (v3.16)
// =============================================================================

function ActiveUsersTable({ users, onlineCount, totalCount }) {
  if (!users || users.length === 0) {
    return (
      <div className="text-center py-8 text-zinc-500">
        <Users className="w-8 h-8 mx-auto mb-2" />
        <p className="text-body-sm">No registered users</p>
      </div>
    );
  }

  const formatLastActive = (timestamp) => {
    if (!timestamp) return 'Never';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="flex items-center gap-4 text-body-sm">
        <div className="flex items-center gap-2">
          <Circle className="w-3 h-3 fill-green-500 text-green-500" />
          <span className="text-green-400">{onlineCount} online</span>
        </div>
        <div className="flex items-center gap-2">
          <Circle className="w-3 h-3 fill-red-500 text-red-500" />
          <span className="text-red-400">{totalCount - onlineCount} offline</span>
        </div>
        <span className="text-zinc-500">({totalCount} total)</span>
      </div>

      {/* Users table */}
      <div className="overflow-x-auto">
        <table className="w-full text-body-sm">
          <thead>
            <tr className="border-b border-surface-border">
              <th className="text-left py-2 px-3 text-zinc-500 font-medium">Status</th>
              <th className="text-left py-2 px-3 text-zinc-500 font-medium">Name</th>
              <th className="text-left py-2 px-3 text-zinc-500 font-medium">Email</th>
              <th className="text-left py-2 px-3 text-zinc-500 font-medium">Last Active</th>
              <th className="text-left py-2 px-3 text-zinc-500 font-medium">Role</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr
                key={u.user_id}
                className="border-b border-surface-border/50 hover:bg-surface-3"
              >
                <td className="py-2 px-3">
                  <Circle
                    className={cn(
                      'w-3 h-3',
                      u.is_online
                        ? 'fill-green-500 text-green-500'
                        : 'fill-red-500 text-red-500'
                    )}
                  />
                </td>
                <td className={cn(
                  'py-2 px-3 font-medium',
                  u.is_online ? 'text-green-400' : 'text-red-400'
                )}>
                  {u.name}
                </td>
                <td className={cn(
                  'py-2 px-3',
                  u.is_online ? 'text-green-400' : 'text-red-400'
                )}>
                  <div className="flex items-center gap-1.5">
                    <Mail className="w-3 h-3 opacity-50" />
                    {u.email}
                  </div>
                </td>
                <td className="py-2 px-3 text-zinc-400">
                  {formatLastActive(u.last_active)}
                </td>
                <td className="py-2 px-3">
                  <span className={cn(
                    'px-2 py-0.5 rounded text-caption',
                    u.role === 'admin'
                      ? 'bg-purple-500/20 text-purple-400'
                      : 'bg-zinc-500/20 text-zinc-400'
                  )}>
                    {u.role}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// =============================================================================
// MAIN DIAGNOSTICS PAGE
// =============================================================================

export default function DiagnosticsPage() {
  const user = useAuthStore((s) => s.user);

  // Check admin role
  if (!user || user.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  const {
    data: diagnostics,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['diagnostics'],
    queryFn: () => systemApi.getDiagnostics({ include_errors: true, error_limit: 20 }),
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 10000,
  });

  // v3.16: Fetch user diagnostics
  const {
    data: userDiagnostics,
    refetch: refetchUsers,
  } = useQuery({
    queryKey: ['diagnostics-users'],
    queryFn: () => systemApi.getUserDiagnostics(15),
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 10000,
  });

  if (isLoading) {
    return (
      <div className="p-6 max-w-6xl mx-auto">
        <div className="flex items-center gap-2 text-zinc-500">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span>Loading diagnostics...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-6xl mx-auto">
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-400">
            <AlertCircle className="w-5 h-5" />
            <span>Failed to load diagnostics</span>
          </div>
          <p className="text-caption text-red-400/80 mt-1">
            {error.response?.data?.detail || error.message}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto h-full overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-heading-md text-zinc-100 flex items-center gap-2">
            <Activity className="w-6 h-6 text-inde-400" />
            System Diagnostics
          </h1>
          <p className="text-caption text-zinc-500 mt-1">
            Operational health monitoring for administrators
          </p>
        </div>
        <button
          onClick={() => { refetch(); refetchUsers(); }}
          className="flex items-center gap-2 px-3 py-2 bg-surface-3 hover:bg-surface-4
                     border border-surface-border rounded-lg text-body-sm text-zinc-300
                     transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Last updated */}
      {diagnostics?.collected_at && (
        <p className="text-caption text-zinc-600 mb-4">
          Last updated: {new Date(diagnostics.collected_at).toLocaleString()}
        </p>
      )}

      {/* Error Counts Summary */}
      <DiagnosticsSection title="Error Summary" icon={AlertTriangle}>
        <div className="grid grid-cols-3 gap-4">
          <StatCard
            label="Errors"
            value={diagnostics?.error_counts?.ERROR || 0}
            icon={XCircle}
          />
          <StatCard
            label="Warnings"
            value={diagnostics?.error_counts?.WARNING || 0}
            icon={AlertTriangle}
          />
          <StatCard
            label="Critical"
            value={diagnostics?.error_counts?.CRITICAL || 0}
            icon={AlertCircle}
          />
        </div>
      </DiagnosticsSection>

      {/* Innovator Stats */}
      <DiagnosticsSection title="Active Innovators" icon={Users}>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard
            label="Total Registered"
            value={diagnostics?.innovator_stats?.total ?? '—'}
            icon={Users}
          />
          <StatCard
            label="Active (24h)"
            value={diagnostics?.innovator_stats?.active_24h ?? '—'}
            sublabel="Last 24 hours"
            icon={Activity}
          />
          <StatCard
            label="Active (7d)"
            value={diagnostics?.innovator_stats?.active_7d ?? '—'}
            sublabel="Last 7 days"
            icon={TrendingUp}
          />
          <StatCard
            label="Active (30d)"
            value={diagnostics?.innovator_stats?.active_30d ?? '—'}
            sublabel="Last 30 days"
            icon={Clock}
          />
          <StatCard
            label="New This Week"
            value={diagnostics?.innovator_stats?.new_this_week ?? '—'}
            sublabel="Registered in 7d"
            icon={Users}
          />
        </div>
      </DiagnosticsSection>

      {/* Active Users (v3.16) */}
      <DiagnosticsSection title="User Directory" icon={Users}>
        <ActiveUsersTable
          users={userDiagnostics?.users}
          onlineCount={userDiagnostics?.online_count}
          totalCount={userDiagnostics?.total_count}
        />
      </DiagnosticsSection>

      {/* Onboarding Funnel */}
      <DiagnosticsSection title="Onboarding Funnel" icon={BarChart2}>
        <OnboardingFunnel funnel={diagnostics?.onboarding_funnel} />
      </DiagnosticsSection>

      {/* System Health */}
      <DiagnosticsSection
        title="System Health"
        icon={Server}
        status={diagnostics?.system_health?.overall}
      >
        <SystemHealth health={diagnostics?.system_health} />
      </DiagnosticsSection>

      {/* Recent Errors */}
      <DiagnosticsSection title="Recent Errors" icon={AlertCircle}>
        <ErrorTable errors={diagnostics?.recent_errors} />
      </DiagnosticsSection>
    </div>
  );
}
