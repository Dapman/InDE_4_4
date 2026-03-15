import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  GitMerge,
  Search,
  RefreshCw,
  CheckCircle2,
  Circle,
  ChevronRight,
  Pin,
  AlertTriangle,
  Printer,
} from 'lucide-react';
import { pursuitsApi } from '../../api/pursuits';
import { useDisplayLabel } from '../../hooks/useDisplayLabel';
import { cn } from '../../lib/utils';
import { formatDistanceToNow } from '../../lib/dateUtils';
import { printConvergence } from '../../lib/print';

// Convergence phase configurations
const PHASE_CONFIG = {
  EXPLORING: {
    icon: Search,
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    description: 'Gathering information and exploring options. Take your time to understand the landscape.',
  },
  CONSOLIDATING: {
    icon: RefreshCw,
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    description: 'Patterns are emerging. Begin narrowing your focus toward key decisions.',
  },
  COMMITTED: {
    icon: CheckCircle2,
    color: 'text-health-healthy',
    bg: 'bg-health-healthy/10',
    border: 'border-health-healthy/30',
    description: 'Decision made. Moving forward with confidence on the chosen direction.',
  },
};

// Criterion item component
function CriterionItem({ criterion, satisfied }) {
  const displayLabel = useDisplayLabel('convergence_criteria', criterion.name || criterion.type);

  return (
    <div className="flex items-start gap-2 py-2">
      {satisfied ? (
        <CheckCircle2 className="h-4 w-4 text-health-healthy mt-0.5 flex-shrink-0" />
      ) : (
        <Circle className="h-4 w-4 text-zinc-600 mt-0.5 flex-shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <span
          className={cn(
            'text-caption',
            satisfied ? 'text-zinc-300' : 'text-zinc-500'
          )}
        >
          {criterion.description || displayLabel.label || criterion.name}
        </span>
      </div>
    </div>
  );
}

// Captured outcome card component
function OutcomeCard({ outcome }) {
  const displayLabel = useDisplayLabel('phases', outcome.phase);

  return (
    <div className="p-3 bg-surface-3/50 rounded-card">
      <div className="flex items-start gap-2">
        <Pin className="h-4 w-4 text-inde-400 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-caption text-zinc-300 line-clamp-3">
            "{outcome.content || outcome.decision}"
          </p>
          <div className="mt-1.5 flex items-center gap-2 text-caption text-zinc-500">
            <span>{displayLabel.label || outcome.phase}</span>
            {outcome.captured_at && (
              <>
                <span>•</span>
                <span>{formatDistanceToNow(outcome.captured_at)}</span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * ConvergencePanel - Shows convergence phase, transition criteria, and action buttons.
 */
export function ConvergencePanel({ pursuitId, onSendMessage, onDataChange }) {
  const queryClient = useQueryClient();
  const [showConfirmation, setShowConfirmation] = useState(false);

  // Fetch convergence data
  const { data: convergenceData, isLoading, error } = useQuery({
    queryKey: ['convergence', pursuitId],
    queryFn: async () => {
      // Try the dedicated convergence endpoint first, fall back to pursuit data
      try {
        const response = await pursuitsApi.get(pursuitId);
        return response.data?.convergence || response.data || {};
      } catch (err) {
        console.warn('Convergence data fetch failed:', err);
        return {};
      }
    },
    enabled: !!pursuitId,
    staleTime: 30000,
    refetchInterval: 30000,
  });

  // Mutation for advancing convergence
  const advanceMutation = useMutation({
    mutationFn: async () => {
      // This would call the convergence advance endpoint
      const response = await pursuitsApi.transitionPhase(pursuitId, 'advance_convergence', 'User initiated convergence advancement');
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['convergence', pursuitId]);
      queryClient.invalidateQueries(['pursuit', pursuitId]);
      setShowConfirmation(false);
    },
  });

  // Parse convergence data
  const { phase, criteria, outcomes, satisfiedCount, totalCount, canAdvance } = useMemo(() => {
    const data = convergenceData || {};

    const currentPhase = (data.phase || data.convergence_phase || 'EXPLORING').toUpperCase();
    const criteriaList = data.criteria || data.transition_criteria || [];
    const outcomeList = data.outcomes || data.captured_outcomes || [];

    // Count satisfied criteria
    let satisfied = 0;
    let total = criteriaList.length;
    criteriaList.forEach((c) => {
      if (c.satisfied || c.met || c.complete) {
        satisfied++;
      }
    });

    const advance = satisfied >= total && total > 0;

    return {
      phase: currentPhase,
      criteria: criteriaList,
      outcomes: outcomeList,
      satisfiedCount: satisfied,
      totalCount: total,
      canAdvance: advance,
    };
  }, [convergenceData]);

  // Get phase configuration
  const phaseConfig = PHASE_CONFIG[phase] || PHASE_CONFIG.EXPLORING;
  const PhaseIcon = phaseConfig.icon;
  const phaseLabel = useDisplayLabel('convergence_phases', phase);

  // Handle "Ready to Move On" click
  const handleAdvanceClick = () => {
    if (canAdvance) {
      setShowConfirmation(true);
    } else if (onSendMessage) {
      onSendMessage("I'd like to discuss what I need to do to advance my convergence phase.");
    }
  };

  // Handle confirm advance
  const handleConfirmAdvance = () => {
    advanceMutation.mutate();
    if (onSendMessage) {
      onSendMessage("I'm ready to move on to the next phase. Let's discuss what that means.");
    }
  };

  // Handle print
  const handlePrint = () => {
    printConvergence({
      phase,
      criteria,
      outcomes,
    });
  };

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
        <p className="text-caption text-health-atrisk mb-2">Failed to load convergence data</p>
        <p className="text-caption text-zinc-600">{error.message}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Phase display */}
      <div className={cn('p-4 border-b', phaseConfig.border, phaseConfig.bg)}>
        <div className="flex items-center gap-3 mb-3">
          <div className={cn('p-2 rounded-card', phaseConfig.bg)}>
            <PhaseIcon className={cn('h-5 w-5', phaseConfig.color)} />
          </div>
          <div className="flex-1">
            <div className="text-caption text-zinc-500">Convergence Phase</div>
            <div className={cn('text-body-sm font-medium', phaseConfig.color)}>
              {phaseLabel.label || phase}
            </div>
          </div>
          <button
            onClick={handlePrint}
            className="p-1.5 hover:bg-surface-3 rounded transition-colors"
            title="Print convergence report"
          >
            <Printer className="h-4 w-4 text-zinc-500 hover:text-zinc-300" />
          </button>
        </div>
        <p className="text-caption text-zinc-400 leading-relaxed">
          {phaseConfig.description}
        </p>
      </div>

      {/* Transition criteria */}
      <div className="p-4 border-b border-surface-border">
        <div className="flex items-center justify-between mb-3">
          <span className="text-caption text-zinc-500">Transition Criteria</span>
          {criteria.length > 0 && (
            <span className="text-caption text-zinc-600">
              {satisfiedCount} of {totalCount} met
            </span>
          )}
        </div>

        {criteria.length > 0 ? (
          <div className="divide-y divide-surface-border/50">
            {criteria.map((criterion, i) => (
              <CriterionItem
                key={criterion.id || i}
                criterion={criterion}
                satisfied={criterion.satisfied || criterion.met || criterion.complete}
              />
            ))}
          </div>
        ) : (
          <div className="py-4 text-center">
            <GitMerge className="h-6 w-6 text-zinc-600 mx-auto mb-2" />
            <p className="text-caption text-zinc-500">
              No transition criteria defined yet
            </p>
          </div>
        )}
      </div>

      {/* Ready to Move On button */}
      <div className="p-4 border-b border-surface-border">
        {showConfirmation ? (
          <div className="p-3 bg-surface-3/50 rounded-card">
            <div className="flex items-start gap-2 mb-3">
              <AlertTriangle className="h-4 w-4 text-health-caution mt-0.5" />
              <div>
                <p className="text-caption text-zinc-300">
                  Are you sure you want to advance?
                </p>
                <p className="text-caption text-zinc-500 mt-1">
                  This will trigger a coaching conversation about your transition.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleConfirmAdvance}
                disabled={advanceMutation.isPending}
                className="flex-1 px-3 py-2 bg-inde-500 hover:bg-inde-600 text-white text-caption font-medium rounded-card transition-colors disabled:opacity-50"
              >
                {advanceMutation.isPending ? 'Advancing...' : 'Yes, advance'}
              </button>
              <button
                onClick={() => setShowConfirmation(false)}
                className="flex-1 px-3 py-2 bg-surface-3 hover:bg-surface-4 text-zinc-300 text-caption font-medium rounded-card transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={handleAdvanceClick}
            disabled={phase === 'COMMITTED'}
            className={cn(
              'w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-card transition-colors text-caption font-medium',
              canAdvance
                ? 'bg-inde-500 hover:bg-inde-600 text-white shadow-glow-inde'
                : 'bg-surface-3 text-zinc-500 cursor-not-allowed',
              phase === 'COMMITTED' && 'opacity-50'
            )}
            title={
              !canAdvance
                ? 'Complete remaining criteria first'
                : phase === 'COMMITTED'
                  ? 'Already at final convergence phase'
                  : 'Click to advance to next phase'
            }
          >
            <span>
              {phase === 'COMMITTED'
                ? 'Fully Converged'
                : canAdvance
                  ? 'Ready to Move On'
                  : 'Complete Criteria to Continue'}
            </span>
            {canAdvance && phase !== 'COMMITTED' && (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        )}
      </div>

      {/* Captured outcomes */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-caption text-zinc-500">Captured Outcomes</span>
          {outcomes.length > 0 && (
            <span className="text-caption text-zinc-600">({outcomes.length})</span>
          )}
        </div>

        {outcomes.length > 0 ? (
          <div className="space-y-2">
            {outcomes.map((outcome, i) => (
              <OutcomeCard key={outcome.id || i} outcome={outcome} />
            ))}
          </div>
        ) : (
          <div className="py-4 text-center">
            <Pin className="h-6 w-6 text-zinc-600 mx-auto mb-2" />
            <p className="text-caption text-zinc-500">
              Outcomes will be captured as you converge on decisions
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default ConvergencePanel;
