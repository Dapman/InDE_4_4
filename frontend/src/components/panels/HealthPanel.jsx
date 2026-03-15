import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Heart,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  AlertCircle,
  Info,
  MessageSquare,
  Printer,
} from 'lucide-react';
import { pursuitsApi } from '../../api/pursuits';
import { useDisplayLabel } from '../../hooks/useDisplayLabel';
import { cn } from '../../lib/utils';
import { printHealth } from '../../lib/print';

// Zone color mapping
const ZONE_COLORS = {
  HEALTHY: {
    text: 'text-health-healthy',
    bg: 'bg-health-healthy',
    border: 'border-health-healthy',
    dot: 'bg-health-healthy',
  },
  CAUTION: {
    text: 'text-health-caution',
    bg: 'bg-health-caution',
    border: 'border-health-caution',
    dot: 'bg-health-caution',
  },
  AT_RISK: {
    text: 'text-health-atrisk',
    bg: 'bg-health-atrisk',
    border: 'border-health-atrisk',
    dot: 'bg-health-atrisk',
  },
};

// Get zone from score
function getZoneFromScore(score) {
  if (score >= 60) return 'HEALTHY';
  if (score >= 40) return 'CAUTION';
  return 'AT_RISK';
}

// Get color classes for a score
function getScoreColors(score) {
  const zone = getZoneFromScore(score);
  return ZONE_COLORS[zone] || ZONE_COLORS.CAUTION;
}

// CSS sparkline component using bars
function Sparkline({ data, className }) {
  if (!data || data.length === 0) {
    return (
      <div className={cn('flex items-end gap-0.5 h-6', className)}>
        {Array(14).fill(0).map((_, i) => (
          <div
            key={i}
            className="flex-1 bg-surface-3 rounded-sm"
            style={{ height: '4px' }}
          />
        ))}
      </div>
    );
  }

  // Normalize data to 0-100 range and get colors
  const maxVal = Math.max(...data.map(d => d.score || d), 100);
  const minHeight = 4;
  const maxHeight = 24;

  return (
    <div className={cn('flex items-end gap-0.5 h-6', className)}>
      {data.map((point, i) => {
        const score = point.score ?? point;
        const normalizedHeight = Math.max(
          minHeight,
          ((score / maxVal) * (maxHeight - minHeight)) + minHeight
        );
        const colors = getScoreColors(score);
        const isLast = i === data.length - 1;

        return (
          <div
            key={i}
            className={cn(
              'flex-1 rounded-sm transition-all',
              colors.bg,
              isLast && 'opacity-100',
              !isLast && 'opacity-60'
            )}
            style={{ height: `${normalizedHeight}px` }}
            title={`${Math.round(score)}`}
          />
        );
      })}
    </div>
  );
}

// Component progress bar
function ComponentBar({ label, score, className }) {
  const colors = getScoreColors(score);

  return (
    <div className={cn('space-y-1', className)}>
      <div className="flex items-center justify-between">
        <span className="text-caption text-zinc-400">{label}</span>
        <span className={cn('text-caption font-medium', colors.text)}>
          {Math.round(score)}
        </span>
      </div>
      <div className="h-1.5 bg-surface-3 rounded-full overflow-hidden">
        <div
          className={cn('h-full transition-all duration-500', colors.bg)}
          style={{ width: `${Math.min(100, score)}%` }}
        />
      </div>
    </div>
  );
}

// Risk card component
function RiskCard({ risk, onDiscuss }) {
  const displayLabel = useDisplayLabel('risk_types', risk.type);

  // Severity icons and colors
  const severityConfig = {
    high: { icon: AlertCircle, color: 'text-health-atrisk', bg: 'bg-health-atrisk/10' },
    medium: { icon: AlertTriangle, color: 'text-health-caution', bg: 'bg-health-caution/10' },
    low: { icon: Info, color: 'text-zinc-400', bg: 'bg-zinc-500/10' },
  };

  const config = severityConfig[risk.severity?.toLowerCase()] || severityConfig.medium;
  const Icon = config.icon;

  return (
    <div className={cn('p-3 rounded-card', config.bg)}>
      <div className="flex items-start gap-2">
        <Icon className={cn('h-4 w-4 mt-0.5 flex-shrink-0', config.color)} />
        <div className="flex-1 min-w-0">
          <div className="text-caption font-medium text-zinc-300">
            {displayLabel.label || risk.type}
          </div>
          {risk.description && (
            <p className="text-caption text-zinc-500 mt-0.5 line-clamp-2">
              {risk.description}
            </p>
          )}
          <div className="flex items-center gap-2 mt-2">
            <span className={cn('text-caption capitalize', config.color)}>
              {risk.severity} severity
            </span>
            {onDiscuss && (
              <button
                onClick={() => onDiscuss(risk)}
                className="text-caption text-inde-400 hover:text-inde-300 flex items-center gap-1"
              >
                <MessageSquare className="h-3 w-3" />
                Discuss
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * HealthPanel - Shows health score gauge, trend sparkline, component bars, and risk cards.
 */
export function HealthPanel({ pursuitId, onSendMessage, onDataChange }) {
  // Fetch health data
  const { data: healthData, isLoading: healthLoading } = useQuery({
    queryKey: ['health', pursuitId],
    queryFn: async () => {
      const response = await pursuitsApi.getHealth(pursuitId);
      return response.data;
    },
    enabled: !!pursuitId,
    staleTime: 30000,
    refetchInterval: 30000,
  });

  // Calculate derived values
  const { score, zone, components, history, risks } = useMemo(() => {
    const data = healthData || {};
    const scoreVal = data.score ?? data.health_score ?? 50;
    const zoneVal = data.zone || data.health_zone || getZoneFromScore(scoreVal);

    // Extract component scores (map backend names to frontend names)
    const rawComps = data.components || data.component_scores || {};
    const comps = {
      velocity: rawComps.velocity ?? rawComps.velocity_health ?? scoreVal,
      completeness: rawComps.completeness ?? rawComps.element_coverage ?? scoreVal,
      engagement: rawComps.engagement ?? rawComps.engagement_rhythm ?? scoreVal,
      risk_balance: rawComps.risk_balance ?? rawComps.risk_posture ?? scoreVal,
      time_health: rawComps.time_health ?? rawComps.phase_timing ?? scoreVal,
    };

    // Extract history for sparkline
    const hist = data.history || data.trend || [];

    // Extract risks
    const riskList = data.risks || data.active_risks || [];

    return {
      score: scoreVal,
      zone: zoneVal.toUpperCase(),
      components: comps,
      history: hist,
      risks: riskList,
    };
  }, [healthData]);

  // Get zone display label
  const zoneLabel = useDisplayLabel('health_zones', zone);
  const colors = ZONE_COLORS[zone] || ZONE_COLORS.CAUTION;

  // Trend calculation
  const trend = useMemo(() => {
    if (!history || history.length < 2) return 'steady';
    const recent = history.slice(-3);
    const first = recent[0]?.score ?? recent[0] ?? 0;
    const last = recent[recent.length - 1]?.score ?? recent[recent.length - 1] ?? 0;
    const diff = last - first;
    if (diff > 3) return 'up';
    if (diff < -3) return 'down';
    return 'steady';
  }, [history]);

  // Handle discuss risk action
  const handleDiscussRisk = (risk) => {
    if (onSendMessage) {
      const riskLabel = risk.type?.replace(/_/g, ' ').toLowerCase() || 'this risk';
      onSendMessage(`I'd like to discuss the ${riskLabel} risk you've identified.`);
    }
  };

  // Handle print
  const handlePrint = () => {
    printHealth({
      score,
      zone,
      components,
      history,
      risks,
    });
  };

  if (healthLoading) {
    return (
      <div className="p-4 flex items-center justify-center h-48">
        <div className="w-6 h-6 border-2 border-inde-500/30 border-t-inde-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Score gauge section */}
      <div className="p-4 text-center border-b border-surface-border">
        <div className="flex items-center justify-between mb-2">
          <div className="flex-1" />
          <div className="text-caption text-zinc-500">Health Score</div>
          <div className="flex-1 flex justify-end">
            <button
              onClick={handlePrint}
              className="p-1.5 hover:bg-surface-3 rounded transition-colors"
              title="Print health report"
            >
              <Printer className="h-4 w-4 text-zinc-500 hover:text-zinc-300" />
            </button>
          </div>
        </div>

        {/* Large score display */}
        <div className="relative inline-flex items-center justify-center mb-2">
          {/* Circular progress ring */}
          <svg className="w-24 h-24 -rotate-90">
            <circle
              cx="48"
              cy="48"
              r="42"
              fill="none"
              stroke="currentColor"
              strokeWidth="6"
              className="text-surface-3"
            />
            <circle
              cx="48"
              cy="48"
              r="42"
              fill="none"
              stroke="currentColor"
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={`${(score / 100) * 264} 264`}
              className={colors.text}
            />
          </svg>
          {/* Score number */}
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={cn('text-display-lg font-bold', colors.text)}>
              {Math.round(score)}
            </span>
          </div>
        </div>

        {/* Zone badge */}
        <div className="flex items-center justify-center gap-2">
          <span className={cn('w-2 h-2 rounded-full', colors.bg)} />
          <span className={cn('text-body-sm font-medium', colors.text)}>
            {zoneLabel.label || zone}
          </span>
          {trend === 'up' && <TrendingUp className="h-4 w-4 text-health-healthy" />}
          {trend === 'down' && <TrendingDown className="h-4 w-4 text-health-atrisk" />}
          {trend === 'steady' && <Minus className="h-4 w-4 text-zinc-500" />}
        </div>
      </div>

      {/* Sparkline trend section */}
      <div className="p-4 border-b border-surface-border">
        <div className="text-caption text-zinc-500 mb-2">Score Trend (7 days)</div>
        <Sparkline data={history} />
      </div>

      {/* Component breakdown section */}
      <div className="p-4 border-b border-surface-border">
        <div className="text-caption text-zinc-500 mb-3">Health Components</div>
        <div className="space-y-3">
          <ComponentBar label="Velocity" score={components.velocity ?? 50} />
          <ComponentBar label="Completeness" score={components.completeness ?? 50} />
          <ComponentBar label="Engagement" score={components.engagement ?? 50} />
          <ComponentBar label="Risk Balance" score={components.risk_balance ?? 50} />
          <ComponentBar label="Time Health" score={components.time_health ?? 50} />
        </div>
      </div>

      {/* Active risks section */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-caption text-zinc-500">Active Risks</span>
          {risks.length > 0 && (
            <span className="text-caption text-zinc-600">({risks.length})</span>
          )}
        </div>

        {risks.length === 0 ? (
          <div className="text-center py-4">
            <Heart className="h-6 w-6 text-health-healthy mx-auto mb-2" />
            <p className="text-caption text-zinc-500">No active risks detected</p>
          </div>
        ) : (
          <div className="space-y-2">
            {risks.map((risk, i) => (
              <RiskCard
                key={risk.id || i}
                risk={risk}
                onDiscuss={handleDiscussRisk}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default HealthPanel;
