import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Brain,
  Lightbulb,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  X,
  Sparkles,
  Leaf,
  ArrowRight,
  Check,
  Printer,
} from 'lucide-react';
import { intelligenceApi } from '../../api/intelligence';
import { useDisplayLabel } from '../../hooks/useDisplayLabel';
import { useAuthStore } from '../../stores/authStore';
import { usePursuitStore } from '../../stores/pursuitStore';
import { cn } from '../../lib/utils';
import { printIntelligence } from '../../lib/print';

// =============================================================================
// PATTERN SUGGESTION CARD
// =============================================================================

function PatternCard({ pattern, onApply, onDismiss, onExpand }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const patternTypeLabel = useDisplayLabel('pattern_types', pattern.type);
  const outcomeLabel = useDisplayLabel('pattern_outcomes', pattern.outcome);

  // Determine outcome indicator
  const outcomeConfig = {
    successful: { icon: '🟢', color: 'text-health-healthy' },
    failed: { icon: '🔴', color: 'text-health-atrisk' },
    pivoted: { icon: '🟡', color: 'text-health-caution' },
  };
  const outcome = outcomeConfig[pattern.outcome] || outcomeConfig.pivoted;

  // Similarity badge color intensity
  const getSimilarityColor = (similarity) => {
    if (similarity >= 80) return 'bg-inde-500 text-white';
    if (similarity >= 60) return 'bg-inde-400 text-white';
    if (similarity >= 40) return 'bg-inde-300 text-zinc-900';
    return 'bg-zinc-600 text-zinc-200';
  };

  const handleApply = () => {
    onApply?.(pattern);
  };

  const handleDismiss = (e) => {
    e.stopPropagation();
    onDismiss?.(pattern.id);
  };

  return (
    <div className="bg-surface-2 border border-surface-border rounded-lg p-3 mb-2">
      {/* Header row */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span
            className={cn(
              'px-2 py-0.5 rounded-full text-caption font-medium',
              getSimilarityColor(pattern.similarity)
            )}
          >
            {pattern.similarity}% Match
          </span>
          <span className={cn('text-caption', outcome.color)}>
            {outcome.icon}
          </span>
        </div>
        <button
          onClick={handleDismiss}
          className="p-1 text-zinc-500 hover:text-zinc-300 transition-colors"
          title="Dismiss"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Summary */}
      <p className="text-body-sm text-zinc-300 mb-2 line-clamp-2">
        {pattern.summary}
      </p>

      {/* Attribution */}
      <p className="text-caption text-zinc-500 italic mb-2">
        Innovators across the InDEVerse have found that...
      </p>

      {/* Key insight */}
      {pattern.key_insight && (
        <div className="bg-inde-500/10 border border-inde-500/20 rounded px-2 py-1.5 mb-2">
          <p className="text-caption text-inde-300">
            <Lightbulb className="h-3 w-3 inline mr-1" />
            {pattern.key_insight}
          </p>
        </div>
      )}

      {/* Expandable detail */}
      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-surface-border/50">
          <p className="text-body-sm text-zinc-400 mb-2">{pattern.detail}</p>
          {pattern.context && (
            <p className="text-caption text-zinc-500">
              Context: {pattern.context}
            </p>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 mt-2">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="px-2 py-1 text-caption text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          {isExpanded ? (
            <>
              <ChevronUp className="h-3 w-3 inline mr-1" />
              Less
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3 inline mr-1" />
              Explore
            </>
          )}
        </button>
        <button
          onClick={handleApply}
          className="px-2 py-1 text-caption bg-inde-500/20 text-inde-400 rounded hover:bg-inde-500/30 transition-colors"
        >
          <ArrowRight className="h-3 w-3 inline mr-1" />
          Apply
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// CROSS-POLLINATION CARD
// =============================================================================

function CrossPollinationCard({ insight, onApply }) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Domain distance indicator
  const getDistanceLabel = (distance) => {
    if (distance <= 1) return { label: 'Adjacent', color: 'text-health-healthy' };
    if (distance <= 2) return { label: 'Moderate', color: 'text-health-caution' };
    return { label: 'Distant', color: 'text-phase-vision' };
  };

  const distanceInfo = getDistanceLabel(insight.domain_distance);

  return (
    <div className="bg-phase-vision/10 border border-phase-vision/20 rounded-lg p-3 mb-2">
      {/* Source domain badge */}
      <div className="flex items-center gap-2 mb-2">
        <span className="px-2 py-0.5 bg-phase-vision/20 text-phase-vision rounded-full text-caption">
          From: {insight.source_domain}
        </span>
        <span className={cn('text-caption', distanceInfo.color)}>
          {distanceInfo.label}
        </span>
        {insight.transfer_probability && (
          <span className="text-caption text-zinc-500">
            {Math.round(insight.transfer_probability * 100)}% transfer
          </span>
        )}
      </div>

      {/* Bridge description */}
      <p className="text-body-sm text-zinc-300 mb-2">
        {insight.bridge_description}
      </p>

      {/* Expandable detail */}
      {isExpanded && insight.detail && (
        <div className="mt-2 pt-2 border-t border-phase-vision/20">
          <p className="text-caption text-zinc-400">{insight.detail}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 mt-2">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="px-2 py-1 text-caption text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          {isExpanded ? 'Less' : 'Details'}
        </button>
        <button
          onClick={() => onApply?.(insight)}
          className="px-2 py-1 text-caption bg-phase-vision/20 text-phase-vision rounded hover:bg-phase-vision/30 transition-colors"
        >
          Explore Transfer
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// LEARNING VELOCITY DISPLAY
// =============================================================================

function LearningVelocityDisplay({ data }) {
  if (!data) return null;

  const getTrendIcon = (trend) => {
    if (trend > 0) return <TrendingUp className="h-4 w-4 text-health-healthy" />;
    if (trend < 0) return <TrendingDown className="h-4 w-4 text-health-atrisk" />;
    return <Minus className="h-4 w-4 text-zinc-500" />;
  };

  // Mini sparkline using CSS
  const maxVal = Math.max(...(data.history || []).map((d) => d.value || d), 100);

  return (
    <div className="bg-surface-2 border border-surface-border rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-body-sm text-zinc-300">Learning Velocity</span>
        {getTrendIcon(data.trend)}
      </div>

      <div className="flex items-baseline gap-2 mb-3">
        <span className="text-2xl font-bold text-inde-400">
          {Math.round(data.score || 0)}
        </span>
        <span className="text-caption text-zinc-500">/ 100</span>
      </div>

      {/* Mini sparkline */}
      {data.history && data.history.length > 0 && (
        <div className="flex items-end gap-0.5 h-8 mb-2">
          {data.history.slice(-10).map((point, i) => {
            const value = point.value ?? point;
            const height = Math.max(4, (value / maxVal) * 32);
            return (
              <div
                key={i}
                className="flex-1 bg-inde-500/40 rounded-t"
                style={{ height: `${height}px` }}
              />
            );
          })}
        </div>
      )}

      {/* Conversion rate */}
      {data.conversion_rate !== undefined && (
        <p className="text-caption text-zinc-500">
          {Math.round(data.conversion_rate * 100)}% pursuit-to-insight conversion
        </p>
      )}

      {/* Org comparison */}
      {data.org_average !== undefined && (
        <p className="text-caption text-zinc-500 mt-1">
          Org avg: {Math.round(data.org_average)}
          {data.score > data.org_average ? (
            <span className="text-health-healthy ml-1">↑ Above</span>
          ) : (
            <span className="text-zinc-500 ml-1">↓ Below</span>
          )}
        </p>
      )}
    </div>
  );
}

// =============================================================================
// BIOMIMICRY INSIGHTS (TRIZ only)
// =============================================================================

function BiomimicrySection({ pursuitId }) {
  const { data, isLoading } = useQuery({
    queryKey: ['biomimicry', pursuitId],
    queryFn: async () => {
      const response = await intelligenceApi.getBiomimicryInsights(pursuitId);
      return response.data;
    },
    enabled: !!pursuitId,
    staleTime: 60000,
  });

  if (isLoading || !data?.insights?.length) return null;

  return (
    <div className="mt-4">
      <div className="flex items-center gap-2 mb-2">
        <Leaf className="h-4 w-4 text-green-500" />
        <span className="text-body-sm font-medium text-zinc-300">
          Nature's Solutions
        </span>
      </div>

      {data.insights.slice(0, 3).map((insight, i) => (
        <div
          key={i}
          className="bg-green-500/10 border border-green-500/20 rounded-lg p-2 mb-2"
        >
          <p className="text-caption font-medium text-green-400 mb-1">
            {insight.nature_analog}
          </p>
          <p className="text-caption text-zinc-400">{insight.description}</p>
          {insight.triz_contradiction && (
            <p className="text-caption text-zinc-500 mt-1">
              TRIZ: {insight.triz_contradiction}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// COLLAPSIBLE SECTION
// =============================================================================

function CollapsibleSection({ title, icon: Icon, children, defaultOpen = true, count }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="mb-4">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between py-2 text-body-sm font-medium text-zinc-300 hover:text-zinc-100 transition-colors"
      >
        <span className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-inde-400" />
          {title}
          {count !== undefined && (
            <span className="text-caption text-zinc-500">({count})</span>
          )}
        </span>
        {isOpen ? (
          <ChevronUp className="h-4 w-4 text-zinc-500" />
        ) : (
          <ChevronDown className="h-4 w-4 text-zinc-500" />
        )}
      </button>
      {isOpen && <div className="mt-2">{children}</div>}
    </div>
  );
}

// =============================================================================
// MAIN INTELLIGENCE PANEL
// =============================================================================

export function IntelligencePanel({ pursuitId, onSendMessage, onDataChange }) {
  const user = useAuthStore((s) => s.user);
  const pursuitList = usePursuitStore((s) => s.pursuitList);
  const pursuit = pursuitList.find((p) => p.id === pursuitId);

  // Fetch patterns
  const {
    data: patternsData,
    isLoading: patternsLoading,
    error: patternsError,
  } = useQuery({
    queryKey: ['intelligence-patterns', pursuitId],
    queryFn: async () => {
      const response = await intelligenceApi.getPatterns(pursuitId);
      return response.data;
    },
    enabled: !!pursuitId,
    staleTime: 60000,
    refetchInterval: 60000,
  });

  // Fetch cross-pollination
  const { data: crossPollinationData } = useQuery({
    queryKey: ['cross-pollination', pursuitId],
    queryFn: async () => {
      const response = await intelligenceApi.getCrossPollination(pursuitId);
      return response.data;
    },
    enabled: !!pursuitId,
    staleTime: 60000,
    refetchInterval: 60000,
  });

  // Fetch learning velocity
  const { data: velocityData } = useQuery({
    queryKey: ['learning-velocity', user?.id],
    queryFn: async () => {
      const response = await intelligenceApi.getLearningVelocity(user.id);
      return response.data;
    },
    enabled: !!user?.id,
    staleTime: 120000,
  });

  // State for dismissed patterns
  const [dismissedIds, setDismissedIds] = useState(new Set());

  // Filter out dismissed patterns
  const patterns = useMemo(() => {
    const allPatterns = patternsData?.patterns || [];
    return allPatterns.filter((p) => !dismissedIds.has(p.id));
  }, [patternsData, dismissedIds]);

  const crossPollination = crossPollinationData?.insights || [];

  // Check if pursuit uses TRIZ (for biomimicry section)
  const isTriz =
    pursuit?.archetype === 'triz' ||
    pursuit?.methodology?.toLowerCase().includes('triz');

  // Handlers
  const handleApplyPattern = (pattern) => {
    if (onSendMessage) {
      onSendMessage(
        `I'd like to discuss a pattern the system found: "${pattern.summary}" - How might this apply to my pursuit?`
      );
    }
    // Record feedback
    intelligenceApi.recordFeedback(pattern.id, 'applied', pursuitId).catch(() => {});
  };

  const handleDismissPattern = (patternId) => {
    setDismissedIds((prev) => new Set([...prev, patternId]));
    intelligenceApi.dismissPattern(patternId).catch(() => {});
  };

  const handleApplyCrossPollination = (insight) => {
    if (onSendMessage) {
      onSendMessage(
        `I found a cross-pollination insight from ${insight.source_domain}: "${insight.bridge_description}" - Can we explore how this might apply?`
      );
    }
  };

  // Handle print
  const handlePrint = () => {
    printIntelligence({
      patterns,
      crossPollination,
      velocity: velocityData,
    });
  };

  // No pursuit selected
  if (!pursuitId) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-6">
        <Brain className="h-8 w-8 text-zinc-600 mb-2" />
        <p className="text-body-sm text-zinc-500">
          Select a pursuit to see intelligence insights
        </p>
      </div>
    );
  }

  // Loading state
  if (patternsLoading) {
    return (
      <div className="p-4">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-surface-3 rounded w-1/3" />
          <div className="h-20 bg-surface-3 rounded" />
          <div className="h-20 bg-surface-3 rounded" />
        </div>
      </div>
    );
  }

  // Error state
  if (patternsError) {
    return (
      <div className="p-4 text-center">
        <p className="text-caption text-health-atrisk mb-2">
          Failed to load intelligence data
        </p>
        <p className="text-caption text-zinc-600">{patternsError.message}</p>
      </div>
    );
  }

  return (
    <div className="p-4 overflow-y-auto">
      {/* Print button */}
      <div className="flex justify-end mb-3">
        <button
          onClick={handlePrint}
          className="p-1.5 hover:bg-surface-3 rounded transition-colors"
          title="Print intelligence report"
        >
          <Printer className="h-4 w-4 text-zinc-500 hover:text-zinc-300" />
        </button>
      </div>

      {/* Pattern Suggestions */}
      <CollapsibleSection
        title="Pattern Suggestions"
        icon={Sparkles}
        count={patterns.length}
        defaultOpen={true}
      >
        {patterns.length > 0 ? (
          patterns.slice(0, 5).map((pattern) => (
            <PatternCard
              key={pattern.id}
              pattern={pattern}
              onApply={handleApplyPattern}
              onDismiss={handleDismissPattern}
            />
          ))
        ) : (
          <p className="text-caption text-zinc-500 italic">
            No pattern suggestions available yet. Keep working on your pursuit!
          </p>
        )}
      </CollapsibleSection>

      {/* Cross-Pollination Insights */}
      <CollapsibleSection
        title="Cross-Pollination"
        icon={ExternalLink}
        count={crossPollination.length}
        defaultOpen={crossPollination.length > 0}
      >
        {crossPollination.length > 0 ? (
          crossPollination.slice(0, 3).map((insight, i) => (
            <CrossPollinationCard
              key={i}
              insight={insight}
              onApply={handleApplyCrossPollination}
            />
          ))
        ) : (
          <p className="text-caption text-zinc-500 italic">
            No cross-domain insights available yet.
          </p>
        )}
      </CollapsibleSection>

      {/* Learning Velocity */}
      <CollapsibleSection
        title="Learning Velocity"
        icon={TrendingUp}
        defaultOpen={true}
      >
        <LearningVelocityDisplay data={velocityData} />
      </CollapsibleSection>

      {/* Biomimicry (TRIZ only) */}
      {isTriz && <BiomimicrySection pursuitId={pursuitId} />}
    </div>
  );
}

export default IntelligencePanel;
