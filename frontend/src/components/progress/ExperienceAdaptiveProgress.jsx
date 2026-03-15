/*
 * ExperienceAdaptiveProgress - Adaptive wrapper for progress display
 *
 * Routes to:
 *   - PursuitDepthIndicator for novice/intermediate modes
 *   - Legacy milestone view for expert mode (preserves existing behavior)
 *
 * This component is used where the old progress bar appeared.
 */
import { useExperienceMode } from '../../context/ExperienceContext';
import { PursuitDepthIndicator } from './PursuitDepthIndicator';
import { cn } from '../../lib/utils';

export function ExperienceAdaptiveProgress({
  pursuitId,
  phase,
  progress,
  className,
}) {
  const { isExpert } = useExperienceMode();

  // For expert mode with explicit legacy props, show traditional view
  if (isExpert && phase && progress !== undefined) {
    return (
      <div className={cn('space-y-2', className)}>
        {/* Phase badge */}
        <div className="flex items-center gap-2">
          <span className="text-caption text-zinc-400">Phase</span>
          <span className="px-2 py-0.5 bg-surface-4 rounded text-caption text-zinc-300">
            {phase}
          </span>
        </div>

        {/* Progress bar */}
        <div>
          <div className="flex justify-between text-caption mb-1">
            <span className="text-zinc-400">Progress</span>
            <span className="text-zinc-300">{progress}%</span>
          </div>
          <div className="h-2 bg-surface-4 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-inde-600 to-inde-400 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Also show depth for expert mode */}
        <div className="mt-4 pt-4 border-t border-surface-border">
          <PursuitDepthIndicator pursuitId={pursuitId} />
        </div>
      </div>
    );
  }

  // Default: depth-framed view for novice/intermediate
  return <PursuitDepthIndicator pursuitId={pursuitId} className={className} />;
}
