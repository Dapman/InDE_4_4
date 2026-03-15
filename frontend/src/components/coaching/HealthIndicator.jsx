import { cn } from '../../lib/utils';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const HEALTH_ZONES = {
  HEALTHY: {
    color: 'bg-health-healthy',
    textColor: 'text-health-healthy',
    label: 'Healthy',
  },
  CAUTION: {
    color: 'bg-health-caution',
    textColor: 'text-health-caution',
    label: 'Attention',
  },
  AT_RISK: {
    color: 'bg-health-atrisk',
    textColor: 'text-health-atrisk',
    label: 'Critical',
  },
};

export function HealthIndicator({
  score,
  zone,
  trend,
  showLabel = true,
  size = 'default',
  className,
}) {
  const config = HEALTH_ZONES[zone] || HEALTH_ZONES.HEALTHY;

  // Determine trend icon
  const TrendIcon = trend > 0 ? TrendingUp : trend < 0 ? TrendingDown : Minus;
  const trendColor =
    trend > 0
      ? 'text-emerald-500'
      : trend < 0
        ? 'text-rose-500'
        : 'text-zinc-500';

  const sizeClasses = {
    small: {
      dot: 'w-1.5 h-1.5',
      text: 'text-caption',
      icon: 'w-3 h-3',
      gap: 'gap-1',
    },
    default: {
      dot: 'w-2 h-2',
      text: 'text-body-sm',
      icon: 'w-3.5 h-3.5',
      gap: 'gap-1.5',
    },
    large: {
      dot: 'w-2.5 h-2.5',
      text: 'text-body-md',
      icon: 'w-4 h-4',
      gap: 'gap-2',
    },
  };

  const s = sizeClasses[size] || sizeClasses.default;

  return (
    <div className={cn('flex items-center', s.gap, className)}>
      {/* Health dot */}
      <div className={cn('rounded-full', s.dot, config.color)} />

      {/* Score */}
      {score !== null && score !== undefined && (
        <span className={cn('font-mono font-medium', s.text, config.textColor)}>
          {Math.round(score)}
        </span>
      )}

      {/* Zone label */}
      {showLabel && (
        <span className={cn('text-zinc-500', s.text)}>{config.label}</span>
      )}

      {/* Trend indicator */}
      {trend !== undefined && trend !== null && trend !== 0 && (
        <TrendIcon className={cn(s.icon, trendColor)} />
      )}
    </div>
  );
}

// Compact version for inline use
export function HealthDot({ zone, className }) {
  const config = HEALTH_ZONES[zone] || HEALTH_ZONES.HEALTHY;
  return (
    <div
      className={cn('w-2 h-2 rounded-full', config.color, className)}
      title={config.label}
    />
  );
}

export default HealthIndicator;
