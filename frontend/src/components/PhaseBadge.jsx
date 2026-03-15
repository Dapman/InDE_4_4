import { cn } from '../lib/utils';

const phases = {
  VISION: {
    label: 'Vision',
    color: 'bg-phase-vision/10 text-phase-vision border-phase-vision/20',
  },
  PITCH: {
    label: 'Pitch',
    color: 'bg-phase-pitch/10 text-phase-pitch border-phase-pitch/20',
  },
  DE_RISK: {
    label: 'De-Risk',
    color: 'bg-phase-derisk/10 text-phase-derisk border-phase-derisk/20',
  },
  BUILD: {
    label: 'Build',
    color: 'bg-phase-build/10 text-phase-build border-phase-build/20',
  },
  DEPLOY: {
    label: 'Deploy',
    color: 'bg-phase-deploy/10 text-phase-deploy border-phase-deploy/20',
  },
};

export function PhaseBadge({ phase, className }) {
  const config = phases[phase] || {
    label: phase?.replace(/_/g, ' ') || 'Unknown',
    color: 'bg-zinc-500/10 text-zinc-500 border-zinc-500/20',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-badge text-caption font-medium border',
        config.color,
        className
      )}
    >
      {config.label}
    </span>
  );
}

export default PhaseBadge;
