/*
 * ArtifactRichnessSignal - Per-artifact qualitative strength indicator
 *
 * Props:
 *   artifactType: string  - e.g., 'vision', 'fear', 'hypothesis'
 *   version:      number  - artifact version count
 *   lastUpdated:  string  - ISO timestamp
 *   richnessLabel: string - from Display Label Registry 'artifact_richness_signals'
 *
 * Renders:
 *   [icon] Your story is taking shape    v3 - Updated 2 days ago
 *
 * Rules:
 *   - No "complete" or "done" language ever
 *   - Version number shown as signal of iteration, not completion
 *   - Richness label is always present (no empty state)
 */
import { FileText, Shield, Beaker, Target, Lightbulb, BarChart3 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { formatRelative } from '../../lib/dateUtils';

const ARTIFACT_ICONS = {
  vision: FileText,
  fear: Shield,
  hypothesis: Beaker,
  test_plan: Target,
  experiment: Lightbulb,
  value_prop: FileText,
  risk_assessment: Shield,
  silr: BarChart3,
};

export function ArtifactRichnessSignal({
  artifactType,
  version = 1,
  lastUpdated,
  richnessLabel = '',
  compact = false,
}) {
  const Icon = ARTIFACT_ICONS[artifactType] || FileText;
  const timeAgo = lastUpdated ? formatRelative(lastUpdated) : null;

  if (compact) {
    return (
      <div className="flex items-center gap-1.5 text-caption text-zinc-500">
        <Icon className="w-3 h-3" />
        <span>{richnessLabel}</span>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2 py-1.5">
      {/* Icon */}
      <div className="flex-shrink-0 mt-0.5">
        <Icon className="w-4 h-4 text-zinc-500" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Richness label */}
        <div className="text-body-sm text-zinc-300">{richnessLabel}</div>

        {/* Version and time */}
        <div className="flex items-center gap-2 mt-0.5">
          {version > 1 && (
            <span className="text-caption text-zinc-500">v{version}</span>
          )}
          {timeAgo && (
            <>
              {version > 1 && (
                <span className="text-caption text-zinc-600">-</span>
              )}
              <span className="text-caption text-zinc-500">
                Updated {timeAgo}
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
