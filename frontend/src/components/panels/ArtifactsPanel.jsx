import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ChevronDown,
  ChevronRight,
  FileText,
  FlaskConical,
  BarChart3,
  ClipboardList,
  Sparkles,
  ExternalLink,
  Clock,
  User,
  X,
  FileBarChart,
  Loader2,
  Printer,
} from 'lucide-react';
import { artifactsApi } from '../../api/artifacts';
import { reportsApi } from '../../api/reports';
import { useDisplayLabel } from '../../hooks/useDisplayLabel';
import { cn } from '../../lib/utils';
import { formatDistanceToNow } from '../../lib/dateUtils';
import { printArtifact } from '../../lib/print';

// v4.0: Labels use innovator-facing goal vocabulary
// Artifact type groupings with icons
const ARTIFACT_GROUPS = {
  vision: {
    label: 'Your Innovation Story',
    icon: FileText,
    types: ['vision', 'elevator_pitch', 'value_proposition', 'vision_statement'],
  },
  validation: {
    label: 'What You\'ve Tested',
    icon: FlaskConical,
    types: ['hypothesis', 'test_plan', 'experiment', 'scenario', 'validation_result'],
  },
  analysis: {
    label: 'Risks & Protections',
    icon: BarChart3,
    types: ['fear_register', 'risk_assessment', 'strategy_canvas', 'competitive_analysis'],
  },
  reports: {
    label: 'Reports & Summaries',
    icon: ClipboardList,
    types: ['silr_terminal', 'silr_living', 'silr_portfolio', 'status_report', 'summary'],
  },
  methodology: {
    label: 'Your Approach',
    icon: Sparkles,
    types: ['review_session', 'published_archetype', 'methodology_snapshot'],
  },
};

// Get group for an artifact type
function getArtifactGroup(type) {
  const normalizedType = type?.toLowerCase();
  for (const [groupId, group] of Object.entries(ARTIFACT_GROUPS)) {
    if (group.types.includes(normalizedType)) {
      return groupId;
    }
  }
  return 'other';
}

// Single artifact item component
function ArtifactItem({ artifact, onPreview }) {
  const displayLabel = useDisplayLabel('artifact_types', artifact.type || artifact.artifact_type);
  const version = artifact.version || 1;

  return (
    <button
      onClick={() => onPreview(artifact)}
      className="w-full flex items-start gap-2 px-3 py-2.5 hover:bg-surface-3 transition-colors text-left"
    >
      <FileText className="h-4 w-4 text-inde-400 mt-0.5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-caption text-zinc-300 truncate">
            {artifact.name || artifact.title || displayLabel.label}
          </span>
          <span className="text-caption text-zinc-600 flex-shrink-0">
            v{version}
          </span>
        </div>
        <div className="text-caption text-zinc-500">
          {formatDistanceToNow(artifact.updated_at || artifact.created_at)}
        </div>
      </div>
      <ExternalLink className="h-3.5 w-3.5 text-zinc-600 flex-shrink-0 mt-1" />
    </button>
  );
}

// Artifact group section component
function ArtifactGroupSection({ groupId, group, artifacts, onPreview }) {
  const [isExpanded, setIsExpanded] = useState(true);
  const Icon = group?.icon || FileText;

  if (artifacts.length === 0) return null;

  return (
    <div className="border-b border-surface-border last:border-0">
      {/* Group header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-3 py-2.5 hover:bg-surface-3 transition-colors"
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-zinc-500" />
        ) : (
          <ChevronRight className="h-4 w-4 text-zinc-500" />
        )}
        <Icon className="h-4 w-4 text-inde-400" />
        <span className="text-body-sm font-medium text-zinc-300 flex-1 text-left">
          {group?.label || groupId}
        </span>
        <span className="text-caption text-zinc-500">
          ({artifacts.length})
        </span>
      </button>

      {/* Group artifacts */}
      {isExpanded && (
        <div className="bg-surface-1/50">
          {artifacts.map((artifact) => (
            <ArtifactItem
              key={artifact.id || artifact.artifact_id}
              artifact={artifact}
              onPreview={onPreview}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Artifact preview modal/overlay component
function ArtifactPreview({ artifact, onClose }) {
  const displayLabel = useDisplayLabel('artifact_types', artifact.type || artifact.artifact_type);

  // Format content for display
  const formatContent = (content) => {
    if (!content) return null;

    // If it's a string, display as-is
    if (typeof content === 'string') {
      return (
        <div className="text-caption text-zinc-400 whitespace-pre-wrap">
          {content}
        </div>
      );
    }

    // If it's an object, display as key-value pairs
    if (typeof content === 'object') {
      return (
        <div className="space-y-2">
          {Object.entries(content).map(([key, value]) => (
            <div key={key} className="border-b border-surface-border/50 pb-2 last:border-0">
              <div className="text-caption text-zinc-500 mb-0.5">
                {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              </div>
              <div className="text-caption text-zinc-300">
                {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
              </div>
            </div>
          ))}
        </div>
      );
    }

    return <div className="text-caption text-zinc-400">{String(content)}</div>;
  };

  // Handle print
  const handlePrint = () => {
    printArtifact(artifact);
  };

  return (
    <div className="absolute inset-0 bg-surface-2 z-10 flex flex-col">
      {/* Preview header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-surface-border">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-body-sm font-medium text-zinc-300 truncate">
              {artifact.name || artifact.title || displayLabel.label}
            </span>
            <span className="text-caption text-zinc-600 flex-shrink-0">
              v{artifact.version || 1}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handlePrint}
            className="p-1.5 hover:bg-surface-3 rounded transition-colors"
            title="Print artifact"
          >
            <Printer className="h-4 w-4 text-zinc-500 hover:text-zinc-300" />
          </button>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-surface-3 rounded transition-colors"
          >
            <X className="h-4 w-4 text-zinc-500" />
          </button>
        </div>
      </div>

      {/* Preview content */}
      <div className="flex-1 overflow-y-auto p-3">
        {formatContent(artifact.content || artifact.data)}

        {!artifact.content && !artifact.data && (
          <div className="text-center py-8">
            <p className="text-caption text-zinc-500">No content available</p>
          </div>
        )}
      </div>

      {/* Preview footer with metadata */}
      <div className="px-3 py-2 border-t border-surface-border bg-surface-1/50">
        <div className="flex flex-wrap items-center gap-3 text-caption text-zinc-500">
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>
              {artifact.updated_at
                ? `Updated ${formatDistanceToNow(artifact.updated_at)}`
                : artifact.created_at
                  ? `Created ${formatDistanceToNow(artifact.created_at)}`
                  : 'Unknown date'}
            </span>
          </div>
          {artifact.created_by && (
            <div className="flex items-center gap-1">
              <User className="h-3 w-3" />
              <span>{artifact.created_by}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * ArtifactsPanel - Shows artifacts grouped by type with preview capability.
 * Includes report generation buttons.
 */
export function ArtifactsPanel({ pursuitId, onDataChange }) {
  const [previewArtifact, setPreviewArtifact] = useState(null);
  const [generatingReport, setGeneratingReport] = useState(null);
  const [reportMessage, setReportMessage] = useState(null);
  const queryClient = useQueryClient();

  // Generate Living Snapshot report
  const generateLivingSnapshot = async () => {
    setGeneratingReport('living');
    setReportMessage(null);
    try {
      const response = await reportsApi.generateLivingSnapshot(pursuitId);
      if (response.data) {
        setReportMessage({ type: 'success', text: 'Living Snapshot report generated' });
        // Refresh artifacts list
        queryClient.invalidateQueries(['artifacts', pursuitId]);
      } else {
        setReportMessage({ type: 'error', text: response.error || 'Failed to generate report' });
      }
    } catch (error) {
      setReportMessage({ type: 'error', text: 'Failed to generate report' });
    } finally {
      setGeneratingReport(null);
    }
  };

  // Generate Terminal report
  const generateTerminalReport = async () => {
    setGeneratingReport('terminal');
    setReportMessage(null);
    try {
      const response = await reportsApi.generateTerminalReport(pursuitId);
      if (response.data) {
        setReportMessage({ type: 'success', text: 'Terminal report generated' });
        queryClient.invalidateQueries(['artifacts', pursuitId]);
      } else {
        setReportMessage({ type: 'error', text: response.error || 'Failed to generate report' });
      }
    } catch (error) {
      setReportMessage({ type: 'error', text: 'Failed to generate report' });
    } finally {
      setGeneratingReport(null);
    }
  };

  // Fetch artifacts
  const { data, isLoading, error } = useQuery({
    queryKey: ['artifacts', pursuitId],
    queryFn: async () => {
      const response = await artifactsApi.list(pursuitId);
      return response.data;
    },
    enabled: !!pursuitId,
    staleTime: 30000,
    refetchInterval: 30000,
  });

  // Group artifacts by type
  const groupedArtifacts = useMemo(() => {
    const artifacts = data?.artifacts || data || [];
    if (!Array.isArray(artifacts)) return {};

    const groups = {};

    // Initialize all groups
    Object.keys(ARTIFACT_GROUPS).forEach((groupId) => {
      groups[groupId] = [];
    });
    groups.other = [];

    // Sort artifacts into groups
    artifacts.forEach((artifact) => {
      const groupId = getArtifactGroup(artifact.type || artifact.artifact_type);
      if (!groups[groupId]) {
        groups[groupId] = [];
      }
      groups[groupId].push(artifact);
    });

    // Sort each group by updated_at descending
    Object.keys(groups).forEach((groupId) => {
      groups[groupId].sort((a, b) => {
        const dateA = new Date(a.updated_at || a.created_at || 0);
        const dateB = new Date(b.updated_at || b.created_at || 0);
        return dateB - dateA;
      });
    });

    return groups;
  }, [data]);

  // Calculate total count
  const totalCount = useMemo(() => {
    return Object.values(groupedArtifacts).reduce((sum, arr) => sum + arr.length, 0);
  }, [groupedArtifacts]);

  if (isLoading) {
    return (
      <div className="p-4 flex items-center justify-center h-48">
        <div className="w-6 h-6 border-2 border-inde-500/30 border-t-inde-500 rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center">
        <p className="text-caption text-health-atrisk mb-2">Failed to load artifacts</p>
        <p className="text-caption text-zinc-600">{error.message}</p>
      </div>
    );
  }

  return (
    <div className="relative flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-surface-border flex-shrink-0">
        <div className="flex items-center justify-between">
          <h3 className="text-body-sm font-medium text-zinc-300">
            Artifacts
          </h3>
          <span className="text-caption text-zinc-500">
            ({totalCount})
          </span>
        </div>
      </div>

      {/* Report Generation Section */}
      <div className="p-3 border-b border-surface-border flex-shrink-0">
        <div className="text-caption text-zinc-500 mb-2 flex items-center gap-1">
          <FileBarChart className="h-3.5 w-3.5" />
          Generate Reports
        </div>
        <div className="flex gap-2">
          <button
            onClick={generateLivingSnapshot}
            disabled={generatingReport !== null}
            className={cn(
              'flex-1 px-2 py-1.5 text-caption text-zinc-300 rounded-card border transition-colors',
              'border-surface-border hover:border-inde-500/50 hover:bg-inde-500/10 hover:text-zinc-200',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {generatingReport === 'living' ? (
              <span className="flex items-center justify-center gap-1 text-inde-400">
                <Loader2 className="h-3 w-3 animate-spin" />
                Generating...
              </span>
            ) : (
              'Living Snapshot'
            )}
          </button>
          <button
            onClick={generateTerminalReport}
            disabled={generatingReport !== null}
            className={cn(
              'flex-1 px-2 py-1.5 text-caption text-zinc-300 rounded-card border transition-colors',
              'border-surface-border hover:border-inde-500/50 hover:bg-inde-500/10 hover:text-zinc-200',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {generatingReport === 'terminal' ? (
              <span className="flex items-center justify-center gap-1 text-inde-400">
                <Loader2 className="h-3 w-3 animate-spin" />
                Generating...
              </span>
            ) : (
              'Terminal Report'
            )}
          </button>
        </div>
        {reportMessage && (
          <div className={cn(
            'mt-2 text-caption px-2 py-1 rounded',
            reportMessage.type === 'success' ? 'text-health-healthy bg-health-healthy/10' : 'text-health-atrisk bg-health-atrisk/10'
          )}>
            {reportMessage.text}
          </div>
        )}
      </div>

      {/* Artifact groups */}
      <div className="flex-1 overflow-y-auto">
        {totalCount === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center px-4">
            <FileText className="h-8 w-8 text-zinc-600 mb-3" />
            <p className="text-body-sm text-zinc-400 mb-1">No artifacts yet</p>
            <p className="text-caption text-zinc-600">
              Artifacts will be generated through your coaching conversations
            </p>
          </div>
        ) : (
          Object.entries(ARTIFACT_GROUPS).map(([groupId, group]) => (
            <ArtifactGroupSection
              key={groupId}
              groupId={groupId}
              group={group}
              artifacts={groupedArtifacts[groupId] || []}
              onPreview={setPreviewArtifact}
            />
          ))
        )}

        {/* Other artifacts (uncategorized) */}
        {groupedArtifacts.other?.length > 0 && (
          <ArtifactGroupSection
            groupId="other"
            group={{ label: 'Other', icon: FileText }}
            artifacts={groupedArtifacts.other}
            onPreview={setPreviewArtifact}
          />
        )}
      </div>

      {/* Preview overlay */}
      {previewArtifact && (
        <ArtifactPreview
          artifact={previewArtifact}
          onClose={() => setPreviewArtifact(null)}
        />
      )}
    </div>
  );
}

export default ArtifactsPanel;
