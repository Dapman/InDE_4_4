import { cn } from '../lib/utils';

const tiers = {
  HIGH: {
    label: 'Strong',
    icon: '🎯',
    className: 'bg-confidence-high/10 text-confidence-high border-confidence-high/20',
  },
  MODERATE: {
    label: 'Emerging',
    icon: '🌱',
    className: 'bg-confidence-moderate/10 text-confidence-moderate border-confidence-moderate/20',
  },
  LOW: {
    label: 'Tentative',
    icon: '🔮',
    className: 'bg-confidence-low/10 text-confidence-low border-confidence-low/20',
  },
  INSUFFICIENT: {
    label: 'Insufficient',
    icon: '❓',
    className: 'bg-zinc-500/10 text-zinc-500 border-zinc-500/20',
  },
};

export function ConfidenceBadge({ tier, showIcon = true, showLabel = true, className }) {
  const config = tiers[tier] || tiers.INSUFFICIENT;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-badge text-caption font-medium border',
        config.className,
        className
      )}
    >
      {showIcon && <span>{config.icon}</span>}
      {showLabel && <span>{config.label}</span>}
    </span>
  );
}

export default ConfidenceBadge;
