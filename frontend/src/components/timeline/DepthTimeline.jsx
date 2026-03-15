/*
 * DepthTimeline - v4.3 Depth-framed timeline display
 *
 * Shows TIM milestones as depth achievements rather than process steps:
 *   - "Your story first took shape" (instead of "Vision Phase Started")
 *   - "You started protecting your idea" (instead of "Fear Extraction Begin")
 *
 * Experience mode behavior:
 *   - novice: depth labels only
 *   - intermediate: depth labels with dates
 *   - expert: depth labels + internal keys + dates
 */
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../../stores/authStore';
import { useExperienceMode } from '../../context/ExperienceContext';
import { cn } from '../../lib/utils';
import { formatRelative } from '../../lib/dateUtils';
import {
  Lightbulb,
  Shield,
  Beaker,
  Sparkles,
  Rocket,
  Flag,
  Circle,
} from 'lucide-react';

// Milestone icon mapping
const MILESTONE_ICONS = {
  vision_first: Lightbulb,
  fear_surfaced: Shield,
  first_hypothesis: Beaker,
  first_evidence: Sparkles,
  idea_sharpened: Sparkles,
  ready_to_test: Beaker,
  idea_at_launch: Rocket,
};

export function DepthTimeline({ pursuitId, compact = false }) {
  const { token } = useAuthStore();
  const { isExpert, isNovice } = useExperienceMode();

  const { data: timelineData, isLoading } = useQuery({
    queryKey: ['timeline', pursuitId],
    queryFn: async () => {
      const response = await fetch(`/api/timeline/${pursuitId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch timeline');
      }
      return response.json();
    },
    enabled: !!pursuitId && !!token,
    staleTime: 60000,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-3">
            <div className="w-6 h-6 bg-surface-4 rounded-full" />
            <div className="flex-1">
              <div className="h-4 bg-surface-4 rounded w-3/4 mb-1" />
              <div className="h-3 bg-surface-4 rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  const milestones = timelineData?.milestones || [];

  if (milestones.length === 0) {
    return (
      <div className="text-center py-4">
        <p className="text-body-sm text-zinc-500">
          Your journey milestones will appear here as your idea grows.
        </p>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Timeline line */}
      <div className="absolute left-3 top-3 bottom-3 w-0.5 bg-surface-4" />

      <div className="space-y-4">
        {milestones.map((milestone, idx) => {
          const key = milestone.key || milestone.milestone_key || 'default';
          const Icon = MILESTONE_ICONS[key] || Circle;
          const displayLabel =
            milestone.display_label || milestone.label || key;
          const timestamp = milestone.timestamp || milestone.created_at;

          return (
            <div
              key={milestone.id || idx}
              className={cn(
                'relative flex gap-3',
                compact && 'gap-2'
              )}
            >
              {/* Icon */}
              <div
                className={cn(
                  'relative z-10 flex-shrink-0 rounded-full flex items-center justify-center bg-surface-3',
                  compact ? 'w-5 h-5' : 'w-6 h-6'
                )}
              >
                <Icon
                  className={cn(
                    'text-inde-400',
                    compact ? 'w-3 h-3' : 'w-4 h-4'
                  )}
                />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0 pt-0.5">
                {/* Depth label */}
                <div
                  className={cn(
                    'text-zinc-200',
                    compact ? 'text-caption' : 'text-body-sm'
                  )}
                >
                  {displayLabel}
                </div>

                {/* Timestamp (intermediate/expert) */}
                {!isNovice && timestamp && (
                  <div className="text-caption text-zinc-500 mt-0.5">
                    {formatRelative(timestamp)}
                  </div>
                )}

                {/* Internal key (expert only) */}
                {isExpert && (
                  <div className="text-caption text-zinc-600 font-mono mt-0.5">
                    {key}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
