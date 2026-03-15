import { cn } from '../lib/utils';

const zones = {
  THRIVING: {
    label: 'Thriving',
    className: 'bg-health-healthy/10 text-health-healthy border-health-healthy/20',
  },
  HEALTHY: {
    label: 'Healthy',
    className: 'bg-health-healthy/10 text-health-healthy border-health-healthy/20',
  },
  CAUTION: {
    label: 'Caution',
    className: 'bg-health-caution/10 text-health-caution border-health-caution/20',
  },
  AT_RISK: {
    label: 'At Risk',
    className: 'bg-health-atrisk/10 text-health-atrisk border-health-atrisk/20',
  },
  CRITICAL: {
    label: 'Critical',
    className: 'bg-health-atrisk/10 text-health-atrisk border-health-atrisk/20',
  },
};

export function HealthBadge({ zone, score, showScore = false, className }) {
  const config = zones[zone] || zones.HEALTHY;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-badge text-caption font-medium border',
        config.className,
        className
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      <span>{config.label}</span>
      {showScore && score !== undefined && (
        <span className="opacity-75">({score})</span>
      )}
    </span>
  );
}

export default HealthBadge;
