/*
 * IdeaRichnessPanel - v4.3 Dashboard depth summary
 *
 * Replaces the "pursuit progress" section with idea-richness language:
 *   - Overall depth narrative
 *   - Top strength dimension
 *   - Active frontier dimension
 *   - Artifact richness signals
 *
 * Props:
 *   pursuitId: string - current pursuit to display depth for
 *   compact:   bool   - use compact layout for small spaces
 */
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../../stores/authStore';
import { useExperienceMode } from '../../context/ExperienceContext';
import { PursuitDepthIndicator } from '../progress/PursuitDepthIndicator';
import { ArtifactRichnessSignal } from '../progress/ArtifactRichnessSignal';
import { cn } from '../../lib/utils';
import { Layers, TrendingUp, Zap } from 'lucide-react';

export function IdeaRichnessPanel({ pursuitId, compact = false }) {
  const { token } = useAuthStore();
  const { isExpert } = useExperienceMode();

  const { data: depthData, isLoading } = useQuery({
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
    staleTime: 30000,
  });

  const { data: artifacts } = useQuery({
    queryKey: ['artifacts', pursuitId],
    queryFn: async () => {
      const response = await fetch(`/api/artifacts?pursuit_id=${pursuitId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch artifacts');
      }
      return response.json();
    },
    enabled: !!pursuitId && !!token,
    staleTime: 60000,
  });

  if (isLoading) {
    return (
      <div className={cn('animate-pulse', compact ? 'p-3' : 'p-4')}>
        <div className="h-5 bg-surface-4 rounded w-2/3 mb-3" />
        <div className="h-4 bg-surface-4 rounded w-full mb-2" />
        <div className="h-4 bg-surface-4 rounded w-3/4" />
      </div>
    );
  }

  if (!depthData) {
    return (
      <div className={cn('text-center', compact ? 'p-3' : 'p-4')}>
        <p className="text-body-sm text-zinc-500">
          Start capturing your idea to see its depth grow.
        </p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', compact ? 'p-3' : 'p-4')}>
      {/* Header */}
      <div className="flex items-center gap-2">
        <Layers className="w-5 h-5 text-inde-400" />
        <h3 className="text-body-sm font-medium text-zinc-200">
          Idea Richness
        </h3>
        {isExpert && (
          <span className="ml-auto text-caption text-zinc-500 font-mono">
            {(depthData.overall_depth * 100).toFixed(0)}%
          </span>
        )}
      </div>

      {/* Depth narrative */}
      <p className="text-body-sm text-zinc-300 leading-relaxed">
        {depthData.depth_narrative}
      </p>

      {/* Strength and Frontier */}
      <div className="grid grid-cols-2 gap-3">
        {/* Top Strength */}
        <div className="bg-surface-3 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-caption text-zinc-500 mb-1">
            <TrendingUp className="w-3 h-3" />
            <span>Strongest</span>
          </div>
          <div className="text-body-sm text-zinc-200">
            {depthData.top_strength}
          </div>
        </div>

        {/* Active Frontier */}
        <div className="bg-surface-3 rounded-lg p-3 border-l-2 border-inde-500">
          <div className="flex items-center gap-1.5 text-caption text-zinc-500 mb-1">
            <Zap className="w-3 h-3" />
            <span>Working on</span>
          </div>
          <div className="text-body-sm text-inde-300">
            {depthData.active_frontier}
          </div>
        </div>
      </div>

      {/* Artifact richness signals (compact: show top 3) */}
      {artifacts?.artifacts?.length > 0 && (
        <div className="pt-2 border-t border-surface-border">
          <div className="text-caption text-zinc-500 mb-2">
            What you've built
          </div>
          <div className="space-y-1">
            {artifacts.artifacts
              .slice(0, compact ? 3 : 5)
              .map((artifact, idx) => (
                <ArtifactRichnessSignal
                  key={artifact.artifact_id || idx}
                  artifactType={artifact.type || 'vision'}
                  version={artifact.version || 1}
                  lastUpdated={artifact.updated_at}
                  richnessLabel={artifact.richness_label || 'Your work here'}
                  compact={compact}
                />
              ))}
          </div>
        </div>
      )}

      {/* Full depth breakdown (non-compact only) */}
      {!compact && (
        <div className="pt-3 border-t border-surface-border">
          <div className="text-caption text-zinc-500 mb-3">
            Depth by dimension
          </div>
          <PursuitDepthIndicator pursuitId={pursuitId} />
        </div>
      )}
    </div>
  );
}
