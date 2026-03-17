import { usePursuitStore } from '../../stores/pursuitStore';
import { useCoachingStore } from '../../stores/coachingStore';
import { cn } from '../../lib/utils';
import { Wifi, WifiOff } from 'lucide-react';

// Version info - update these when releasing new versions
const VERSION_INFO = {
  product: 'InDE',
  version: '4.4.1',
  revision: '0',  // Increment for patches within a version
  company: 'InDEVerse, Inc.',
  year: new Date().getFullYear(),
};

const PHASE_LABELS = {
  VISION: 'Vision',
  PITCH: 'Pitch',
  DE_RISK: 'De-Risk',
  BUILD: 'Build',
  DEPLOY: 'Deploy',
};

/**
 * StatusBar - Bottom status bar showing connection, phase, and version.
 */
export function StatusBar() {
  const { pursuitList, activePursuitId } = usePursuitStore();
  const { isConnected } = useCoachingStore();

  const activePursuit = pursuitList.find((p) => p.id === activePursuitId);
  const phaseLabel = PHASE_LABELS[activePursuit?.phase] || '';
  const archetypeLabel = activePursuit?.methodology_archetype
    ?.replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase()) || '';

  return (
    <footer className="h-statusbar flex items-center px-4 border-t border-surface-border bg-surface-2/80 text-caption">
      {/* Left: Connection Status */}
      <div className="flex items-center gap-2">
        {isConnected ? (
          <>
            <Wifi className="h-3 w-3 text-health-healthy" />
            <span className="text-zinc-500">Connected</span>
          </>
        ) : (
          <>
            <WifiOff className="h-3 w-3 text-zinc-500" />
            <span className="text-zinc-600">Offline</span>
          </>
        )}
      </div>

      {/* Center: Active Pursuit Phase */}
      <div className="flex-1 flex items-center justify-center">
        {activePursuit && (
          <span className="text-zinc-500">
            {phaseLabel}
            {archetypeLabel && (
              <>
                <span className="mx-1.5 text-zinc-700">•</span>
                <span className="text-zinc-600">{archetypeLabel}</span>
              </>
            )}
          </span>
        )}
      </div>

      {/* Right: Company and Version */}
      <div className="flex items-center gap-2 text-zinc-600">
        <span className="text-zinc-500">{VERSION_INFO.company}</span>
        <span className="text-zinc-700">|</span>
        <span>
          {VERSION_INFO.product} v{VERSION_INFO.version}.{VERSION_INFO.revision}
        </span>
      </div>
    </footer>
  );
}

export default StatusBar;
