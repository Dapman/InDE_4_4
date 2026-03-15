/*
 * DepthDimensionBar - Single depth dimension display
 *
 * Props:
 *   label:          string  - dimension label (from Display Label Registry)
 *   score:          number  - 0.0-1.0
 *   richnessPhrase: string  - qualitative label (e.g., "Getting stronger")
 *   isActiveFrontier: bool  - true if this is where current momentum flows
 *   showScore:      bool    - show numeric score (expert mode only)
 *
 * Visual behavior:
 *   - Displays label + richness phrase (not a percentage)
 *   - Animated fill bar (width = score * 100%)
 *   - Active frontier: subtle pulse animation + accent color
 *   - No "X% complete" text ever appears in novice mode
 */
import { cn } from '../../lib/utils';

export function DepthDimensionBar({
  label,
  score = 0,
  richnessPhrase = '',
  isActiveFrontier = false,
  showScore = false,
}) {
  const widthPercent = Math.round(score * 100);

  return (
    <div className="mb-3">
      {/* Label and richness phrase */}
      <div className="flex justify-between items-baseline mb-1.5">
        <span className="text-body-sm text-zinc-300">{label}</span>
        {showScore && (
          <span className="text-caption text-zinc-500 font-mono">
            {(score * 100).toFixed(0)}%
          </span>
        )}
      </div>

      {/* Progress bar container */}
      <div className="relative">
        {/* Active frontier indicator */}
        {isActiveFrontier && (
          <div className="absolute -left-0.5 top-0 w-1 h-full bg-inde-400 rounded-full animate-pulse" />
        )}

        {/* Bar background */}
        <div
          className={cn(
            'h-2 rounded-full bg-surface-4 overflow-hidden',
            isActiveFrontier && 'ml-2'
          )}
        >
          {/* Fill bar */}
          <div
            className={cn(
              'h-full rounded-full transition-all duration-700 ease-out',
              isActiveFrontier
                ? 'bg-gradient-to-r from-inde-500 to-inde-400'
                : 'bg-gradient-to-r from-zinc-600 to-zinc-500'
            )}
            style={{ width: `${widthPercent}%` }}
          />
        </div>
      </div>

      {/* Richness phrase */}
      <div className="mt-1">
        <span
          className={cn(
            'text-caption',
            isActiveFrontier ? 'text-inde-300' : 'text-zinc-500'
          )}
        >
          {richnessPhrase}
        </span>
      </div>
    </div>
  );
}
