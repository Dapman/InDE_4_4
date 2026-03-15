import { cn } from '../../lib/utils';
import { HealthIndicator } from './HealthIndicator';
import { PhaseBadge } from '../PhaseBadge';
import { useDisplayLabel } from '../../hooks/useDisplayLabel';

const MODE_CONFIG = {
  coaching: null, // No indicator for default mode
  // v4.0: Labels use innovator-facing goal vocabulary
  vision: {
    icon: '📖',
    label: 'Telling Your Story',
    accent: 'bg-phase-vision/10 border-phase-vision/30',
  },
  fear: {
    icon: '🛡️',
    label: 'Protecting Your Idea',
    accent: 'bg-phase-pitch/10 border-phase-pitch/30',
  },
  retrospective: {
    icon: '💡',
    label: 'Capturing What You Learned',
    accent: 'bg-phase-build/10 border-phase-build/30',
  },
  ems_review: {
    icon: '✨',
    label: 'Discovering Your Approach',
    accent: 'bg-inde-500/10 border-inde-500/30',
  },
  crisis: {
    icon: '🆘',
    label: 'Support Mode',
    accent: 'bg-health-atrisk/10 border-health-atrisk/30 animate-pulse-gentle',
  },
};

export function ChatHeader({
  mode = 'coaching',
  healthScore,
  healthZone,
  healthTrend,
  phase,
  className,
}) {
  const modeConfig = MODE_CONFIG[mode];
  const { getLabel } = useDisplayLabel();

  return (
    <div
      className={cn(
        'flex items-center justify-between px-4 py-2.5 border-b border-surface-border',
        modeConfig?.accent,
        className
      )}
    >
      {/* Left: Mode indicator or phase */}
      <div className="flex items-center gap-3">
        {modeConfig ? (
          <div className="flex items-center gap-2">
            <span className="text-base">{modeConfig.icon}</span>
            <span className="text-body-sm text-zinc-300 font-medium">
              {modeConfig.label}
            </span>
          </div>
        ) : phase ? (
          <PhaseBadge phase={phase} size="small" />
        ) : (
          <span className="text-body-sm text-zinc-500">Coaching Session</span>
        )}
      </div>

      {/* Right: Health indicator */}
      {healthScore !== null && healthScore !== undefined && (
        <HealthIndicator
          score={healthScore}
          zone={healthZone}
          trend={healthTrend}
          size="default"
        />
      )}
    </div>
  );
}

export default ChatHeader;
