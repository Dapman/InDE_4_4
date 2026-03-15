/*
 * PursuitDepthIndicator - Replaces the module-completion progress bar
 *
 * In novice mode: 5 depth dimension bars + depth narrative text
 * In intermediate mode: 5 depth dimension bars + optional milestone markers
 * In expert mode: full dimension bars + phase label + legacy milestone markers
 *
 * Data source: GET /api/v1/pursuits/{id}/depth
 * Polling: refresh on pursuit selection change, on session close, on demand
 */
import { useQuery } from '@tanstack/react-query';
import { useExperienceMode } from '../../context/ExperienceContext';
import { useAuthStore } from '../../stores/authStore';
import { DepthDimensionBar } from './DepthDimensionBar';
import { cn } from '../../lib/utils';

export function PursuitDepthIndicator({ pursuitId, className }) {
  const { experienceMode, isNovice, isExpert } = useExperienceMode();
  const { token } = useAuthStore();

  const { data: depthData, isLoading, error } = useQuery({
    queryKey: ['pursuit-depth', pursuitId],
    queryFn: async () => {
      const response = await fetch(`/api/v1/pursuits/${pursuitId}/depth`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch depth data');
      }
      return response.json();
    },
    enabled: !!pursuitId && !!token,
    staleTime: 30000, // 30 seconds
    refetchOnWindowFocus: false,
  });

  if (isLoading) {
    return (
      <div className={cn('animate-pulse', className)}>
        <div className="h-4 bg-surface-4 rounded w-3/4 mb-3" />
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="mb-3">
            <div className="h-3 bg-surface-4 rounded w-1/2 mb-1.5" />
            <div className="h-2 bg-surface-4 rounded w-full" />
          </div>
        ))}
      </div>
    );
  }

  if (error || !depthData) {
    return (
      <div className={cn('text-caption text-zinc-500', className)}>
        Start capturing your idea to see your depth grow.
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Depth narrative */}
      <div className="mb-4">
        <p className="text-body-sm text-zinc-300 leading-relaxed">
          {depthData.depth_narrative}
        </p>
      </div>

      {/* Overall depth indicator (expert mode only) */}
      {isExpert && (
        <div className="mb-4 p-2 bg-surface-3 rounded-lg">
          <div className="flex justify-between items-center text-caption">
            <span className="text-zinc-400">Overall Depth</span>
            <span className="text-zinc-300 font-mono">
              {(depthData.overall_depth * 100).toFixed(0)}%
            </span>
          </div>
          <div className="mt-1 h-1.5 bg-surface-4 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-inde-600 to-inde-400 rounded-full transition-all duration-500"
              style={{ width: `${depthData.overall_depth * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Dimension bars */}
      <div className="space-y-1">
        {depthData.dimensions?.map((dimension) => (
          <DepthDimensionBar
            key={dimension.dimension}
            label={dimension.display_label}
            score={dimension.score}
            richnessPhrase={dimension.richness_phrase}
            isActiveFrontier={
              dimension.display_label === depthData.active_frontier
            }
            showScore={isExpert}
          />
        ))}
      </div>

      {/* Active frontier callout (intermediate mode) */}
      {!isNovice && !isExpert && depthData.active_frontier && (
        <div className="mt-4 p-2 bg-surface-3 rounded-lg border-l-2 border-inde-500">
          <div className="text-caption text-zinc-400">Working on now</div>
          <div className="text-body-sm text-zinc-200">
            {depthData.active_frontier}
          </div>
        </div>
      )}
    </div>
  );
}
