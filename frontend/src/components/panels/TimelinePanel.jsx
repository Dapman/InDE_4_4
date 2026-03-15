import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Clock,
  Calendar,
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle2,
  Circle,
  Play,
  Printer,
  Flag,
  AlertCircle,
  AlertTriangle,
  History,
  HelpCircle,
} from 'lucide-react';
import { pursuitsApi } from '../../api/pursuits';
import { useDisplayLabel } from '../../hooks/useDisplayLabel';
import { cn } from '../../lib/utils';
import { formatShortDate, daysUntil, formatDuration } from '../../lib/dateUtils';
import { printTimeline } from '../../lib/print';

// Phase color mapping
const PHASE_COLORS = {
  VISION: { bg: 'bg-phase-vision', text: 'text-phase-vision', border: 'border-phase-vision' },
  FEAR: { bg: 'bg-phase-pitch', text: 'text-phase-pitch', border: 'border-phase-pitch' },
  DERISK: { bg: 'bg-phase-build', text: 'text-phase-build', border: 'border-phase-build' },
  DE_RISK: { bg: 'bg-phase-build', text: 'text-phase-build', border: 'border-phase-build' },
  VALIDATE: { bg: 'bg-health-caution', text: 'text-health-caution', border: 'border-health-caution' },
  BUILD: { bg: 'bg-health-healthy', text: 'text-health-healthy', border: 'border-health-healthy' },
  LAUNCH: { bg: 'bg-inde-500', text: 'text-inde-400', border: 'border-inde-500' },
};

// Phase sequence for ordering
const PHASE_ORDER = ['VISION', 'FEAR', 'DERISK', 'DE_RISK', 'VALIDATE', 'BUILD', 'LAUNCH'];

// Get phase colors
function getPhaseColors(phase) {
  const normalized = phase?.toUpperCase()?.replace('-', '_');
  return PHASE_COLORS[normalized] || { bg: 'bg-zinc-500', text: 'text-zinc-400', border: 'border-zinc-500' };
}

// Get phase order index
function getPhaseIndex(phase) {
  const normalized = phase?.toUpperCase()?.replace('-', '_');
  const idx = PHASE_ORDER.indexOf(normalized);
  return idx >= 0 ? idx : 0;
}

// Phase bar segment component
function PhaseSegment({ phase, isCurrent, isCompleted, percentage, duration }) {
  const colors = getPhaseColors(phase.name || phase.phase);
  const displayLabel = useDisplayLabel('phases', phase.name || phase.phase);

  return (
    <div
      className="relative flex-1 min-w-0 group"
      title={`${displayLabel.label}: ${duration || 'N/A'} days`}
    >
      {/* Segment bar */}
      <div
        className={cn(
          'h-3 rounded-sm transition-all',
          isCompleted && colors.bg,
          isCurrent && 'relative overflow-hidden',
          !isCompleted && !isCurrent && 'bg-surface-3'
        )}
      >
        {/* Current phase partial fill */}
        {isCurrent && (
          <>
            <div className="absolute inset-0 bg-surface-3" />
            <div
              className={cn('absolute inset-y-0 left-0', colors.bg)}
              style={{ width: `${percentage || 0}%` }}
            />
          </>
        )}
      </div>

      {/* Current phase indicator */}
      {isCurrent && (
        <div
          className={cn(
            'absolute -top-1 left-1/2 -translate-x-1/2 w-0 h-0',
            'border-l-4 border-r-4 border-t-4 border-transparent',
            colors.border.replace('border-', 'border-t-')
          )}
        />
      )}

      {/* Hover tooltip */}
      <div className="opacity-0 group-hover:opacity-100 absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-surface-3 rounded text-caption text-zinc-300 whitespace-nowrap z-10 transition-opacity">
        {displayLabel.label}
      </div>
    </div>
  );
}

// Phase list item component
function PhaseListItem({ phase, isCurrent, isCompleted, actual, planned }) {
  const colors = getPhaseColors(phase.name || phase.phase);
  const displayLabel = useDisplayLabel('phases', phase.name || phase.phase);

  const overUnder = actual && planned ? actual - planned : null;

  return (
    <div className={cn('flex items-center gap-2 py-2', isCurrent && 'bg-surface-3/50 -mx-4 px-4')}>
      {/* Status icon */}
      {isCompleted ? (
        <CheckCircle2 className={cn('h-4 w-4', colors.text)} />
      ) : isCurrent ? (
        <Play className={cn('h-4 w-4', colors.text)} />
      ) : (
        <Circle className="h-4 w-4 text-zinc-600" />
      )}

      {/* Phase name */}
      <span
        className={cn(
          'text-caption flex-1',
          isCompleted || isCurrent ? colors.text : 'text-zinc-500'
        )}
      >
        {displayLabel.label}
      </span>

      {/* Duration */}
      <div className="flex items-center gap-2 text-caption">
        {actual && (
          <span className={cn(isCurrent ? 'text-zinc-300' : 'text-zinc-500')}>
            {actual}d
          </span>
        )}
        {planned && !actual && (
          <span className="text-zinc-600">{planned}d</span>
        )}
        {overUnder !== null && overUnder !== 0 && (
          <span className={cn(overUnder > 0 ? 'text-health-atrisk' : 'text-health-healthy')}>
            {overUnder > 0 ? '+' : ''}{overUnder}d
          </span>
        )}
      </div>
    </div>
  );
}

// Velocity status badge component
function VelocityBadge({ ratio }) {
  if (ratio === null || ratio === undefined) return null;

  let color, label, Icon;
  if (ratio > 1.1) {
    color = 'text-health-healthy';
    label = 'Ahead';
    Icon = TrendingUp;
  } else if (ratio < 0.9) {
    color = 'text-health-atrisk';
    label = 'Behind';
    Icon = TrendingDown;
  } else {
    color = 'text-health-caution';
    label = 'On Track';
    Icon = Minus;
  }

  return (
    <div className={cn('flex items-center gap-1', color)}>
      <Icon className="h-4 w-4" />
      <span className="text-caption font-medium">{label}</span>
    </div>
  );
}

// v3.9/v3.10/v3.11: Milestone card component with provisional date support and permission awareness
function MilestoneCard({ milestone, onConfirmRelativeDate, canEdit = true }) {
  const isOverdue = milestone.is_overdue;
  const isProvisional = milestone.requires_recalculation === true;
  const isSuperseded = milestone.is_superseded === true;

  const daysText = milestone.days_until !== undefined && milestone.days_until !== null
    ? (isOverdue
        ? `${Math.abs(milestone.days_until)} days overdue`
        : `${milestone.days_until} days`)
    : milestone.date_expression || 'TBD';

  // Format target date for display
  const targetDateDisplay = milestone.target_date
    ? formatShortDate(milestone.target_date)
    : milestone.date_expression || 'Date TBD';

  // v3.10: Determine card styling based on state
  const cardClasses = cn(
    'p-3 rounded-card border transition-all',
    isSuperseded
      ? 'border-zinc-700/30 bg-zinc-800/30 opacity-60 line-through'
      : isOverdue
        ? 'border-health-atrisk/30 bg-health-atrisk/5'
        : isProvisional
          ? 'border-dashed border-inde-400/30 bg-inde-500/5'
          : 'border-surface-border bg-surface-2'
  );

  return (
    <div className={cardClasses}>
      <div className="flex items-start gap-2">
        <Flag className={cn(
          'h-4 w-4 mt-0.5 flex-shrink-0',
          isSuperseded ? 'text-zinc-600' :
          isOverdue ? 'text-health-atrisk' :
          isProvisional ? 'text-inde-400/70' : 'text-inde-400'
        )} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className={cn(
              'text-caption font-medium truncate',
              isSuperseded ? 'text-zinc-500' : 'text-zinc-300'
            )}>
              {milestone.title}
            </span>
            {/* v3.10: Provisional date indicator */}
            {isProvisional && (
              <HelpCircle
                className="h-3 w-3 text-inde-400/70 flex-shrink-0"
                title={`Based on "${milestone.date_expression}" - confirm this is still accurate`}
              />
            )}
            {/* v3.10: Superseded indicator */}
            {isSuperseded && milestone.milestone_version > 1 && (
              <span className="text-[9px] text-zinc-600 bg-zinc-700/50 px-1 rounded">
                v{milestone.milestone_version - 1}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className={cn(
              'text-caption',
              isSuperseded ? 'text-zinc-600' :
              isOverdue ? 'text-health-atrisk' :
              isProvisional ? 'text-inde-400/70' : 'text-zinc-500'
            )}>
              {isProvisional && '~'}{targetDateDisplay}
            </span>
            <span className="text-caption text-zinc-600">
              ({daysText})
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            {milestone.milestone_type && milestone.milestone_type !== 'other' && (
              <span className="text-[10px] text-zinc-600 bg-surface-3 px-1.5 py-0.5 rounded">
                {milestone.milestone_type.replace('_', ' ')}
              </span>
            )}
            {/* v3.10/v3.11: Confirm date button for provisional milestones (permission-aware) */}
            {isProvisional && onConfirmRelativeDate && canEdit && (
              <button
                onClick={() => onConfirmRelativeDate(milestone)}
                className="text-[10px] text-inde-400 hover:text-inde-300 bg-inde-500/10 hover:bg-inde-500/20 px-1.5 py-0.5 rounded transition-colors"
              >
                Confirm date
              </button>
            )}
            {/* v3.11: Show locked indicator for non-editable milestones in team pursuits */}
            {isProvisional && !canEdit && (
              <span
                className="text-[10px] text-zinc-500 bg-zinc-700/50 px-1.5 py-0.5 rounded cursor-default"
                title="Only the pursuit creator can modify milestone dates"
              >
                Locked
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// v3.10/v3.11: Inconsistency warning banner (permission-aware)
function InconsistencyWarning({ allocationEnd, milestoneEnd, dayDifference, onResolve, canEdit = true }) {
  return (
    <div className="p-3 rounded-card border border-amber-500/30 bg-amber-500/10 mb-3">
      <div className="flex items-start gap-2">
        <AlertTriangle className="h-4 w-4 text-amber-400 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <div className="text-caption font-medium text-amber-300">
            Timeline Inconsistency
          </div>
          <p className="text-caption text-amber-200/70 mt-1">
            Project window ends {allocationEnd} but release milestone targets {milestoneEnd} ({dayDifference} days difference).
          </p>
          {/* v3.11: Only show resolution buttons if user can edit */}
          {canEdit ? (
            <div className="flex gap-2 mt-2">
              <button
                onClick={() => onResolve('milestone')}
                className="text-[10px] text-amber-300 bg-amber-500/20 hover:bg-amber-500/30 px-2 py-1 rounded transition-colors"
              >
                Use {milestoneEnd}
              </button>
              <button
                onClick={() => onResolve('allocation')}
                className="text-[10px] text-amber-300 bg-amber-500/20 hover:bg-amber-500/30 px-2 py-1 rounded transition-colors"
              >
                Use {allocationEnd}
              </button>
            </div>
          ) : (
            <div className="text-[10px] text-amber-200/50 mt-2">
              Only the pursuit creator can resolve this inconsistency.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * TimelinePanel - Shows phase progress bar, velocity metrics, and maturity score.
 * v3.10: Enhanced with timeline integrity features (conflict detection, consistency validation)
 */
export function TimelinePanel({ pursuitId, onDataChange }) {
  // v3.10: State for showing superseded milestones
  const [showHistory, setShowHistory] = useState(false);

  // Fetch timeline data
  const { data: timelineData, isLoading } = useQuery({
    queryKey: ['timeline', pursuitId],
    queryFn: async () => {
      const response = await pursuitsApi.getTimeline(pursuitId);
      return response.data;
    },
    enabled: !!pursuitId,
    staleTime: 30000,
    refetchInterval: 30000,
  });

  // v3.9: Fetch milestones data
  const { data: milestonesData, refetch: refetchMilestones } = useQuery({
    queryKey: ['milestones', pursuitId],
    queryFn: async () => {
      const response = await pursuitsApi.getMilestones(pursuitId);
      return response.data;
    },
    enabled: !!pursuitId,
    staleTime: 30000,
    refetchInterval: 30000,
  });

  // v3.10: Fetch consistency check data
  const { data: consistencyData } = useQuery({
    queryKey: ['timeline-consistency', pursuitId],
    queryFn: async () => {
      try {
        const response = await pursuitsApi.checkTimelineConsistency(pursuitId);
        return response.data;
      } catch (e) {
        // Endpoint may not exist yet - gracefully handle
        return { is_consistent: true };
      }
    },
    enabled: !!pursuitId,
    staleTime: 60000,
    refetchInterval: 60000,
  });

  // v3.11: Fetch milestone edit permissions (TD-014)
  const { data: permissionsData } = useQuery({
    queryKey: ['milestone-permissions', pursuitId],
    queryFn: async () => {
      try {
        const response = await pursuitsApi.getMilestonePermissions(pursuitId);
        return response.data;
      } catch (e) {
        // Endpoint may not exist yet - default to allowing edits
        return { can_edit: true, is_team_pursuit: false };
      }
    },
    enabled: !!pursuitId,
    staleTime: 60000,
  });

  const canEditMilestones = permissionsData?.can_edit ?? true;
  const isTeamPursuit = permissionsData?.is_team_pursuit ?? false;

  const allMilestones = milestonesData?.milestones || [];
  // v3.10: Filter milestones based on history toggle
  const milestones = showHistory
    ? allMilestones
    : allMilestones.filter(m => !m.is_superseded);

  const supersededCount = allMilestones.filter(m => m.is_superseded).length;
  const hasInconsistency = consistencyData && !consistencyData.is_consistent;

  // Parse timeline data
  const {
    startedAt,
    targetEnd,
    currentPhase,
    phases,
    elapsedPercentage,
    velocity,
    maturity,
  } = useMemo(() => {
    const data = timelineData || {};

    const start = data.started_at || data.start_date || data.created_at;
    const totalDays = data.total_days || 90;
    // Calculate target end from start + total_days
    let end = data.target_end || data.end_date;
    if (!end && start) {
      const startDate = new Date(start);
      startDate.setDate(startDate.getDate() + totalDays);
      end = startDate.toISOString();
    }
    const current = data.current_phase || data.phase || 'VISION';

    // Calculate elapsed percentage
    let elapsed = 0;
    if (start && end) {
      const startMs = new Date(start).getTime();
      const endMs = new Date(end).getTime();
      const nowMs = Date.now();
      elapsed = Math.min(100, Math.max(0, ((nowMs - startMs) / (endMs - startMs)) * 100));
    }

    // Parse phases - handle both array and object formats
    let phaseList = [];
    if (Array.isArray(data.phases)) {
      phaseList = data.phases;
    } else if (data.phases && typeof data.phases === 'object') {
      // Convert phases object to array (from allocation endpoint)
      phaseList = Object.entries(data.phases).map(([name, phaseData]) => ({
        name,
        phase: name,
        duration: phaseData.days,
        planned_days: phaseData.days,
        percent: phaseData.percent,
        status: phaseData.status,
      }));
    }

    // Parse velocity
    const vel = data.velocity || {};

    // Parse maturity
    const mat = data.maturity || {};

    return {
      startedAt: start,
      targetEnd: end,
      currentPhase: current,
      phases: phaseList,
      elapsedPercentage: elapsed,
      velocity: vel,
      maturity: mat,
    };
  }, [timelineData]);

  // Days remaining
  const daysRemaining = targetEnd ? daysUntil(targetEnd) : null;

  if (isLoading) {
    return (
      <div className="p-4 flex items-center justify-center h-48">
        <div className="w-6 h-6 border-2 border-inde-500/30 border-t-inde-500 rounded-full animate-spin" />
      </div>
    );
  }

  // Handle print
  const handlePrint = () => {
    printTimeline({
      started_at: startedAt,
      target_end: targetEnd,
      current_phase: currentPhase,
      phases,
      velocity,
      maturity,
    });
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header with dates */}
      <div className="p-4 border-b border-surface-border">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-body-sm font-medium text-zinc-300">Timeline</h3>
          <button
            onClick={handlePrint}
            className="p-1.5 hover:bg-surface-3 rounded transition-colors"
            title="Print timeline"
          >
            <Printer className="h-4 w-4 text-zinc-500 hover:text-zinc-300" />
          </button>
        </div>

        <div className="space-y-2 text-caption">
          <div className="flex items-center justify-between">
            <span className="text-zinc-500 flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              Started
            </span>
            <span className="text-zinc-300">
              {startedAt ? formatShortDate(startedAt) : 'Not started'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-zinc-500 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Target
            </span>
            <span className="text-zinc-300">
              {targetEnd ? (
                <>
                  {formatShortDate(targetEnd)}
                  {daysRemaining !== null && (
                    <span className={cn(
                      'ml-1',
                      daysRemaining < 0 ? 'text-health-atrisk' :
                      daysRemaining < 7 ? 'text-health-caution' : 'text-zinc-500'
                    )}>
                      ({daysRemaining} days)
                    </span>
                  )}
                </>
              ) : 'Not set'}
            </span>
          </div>
        </div>
      </div>

      {/* Phase progress bar */}
      <div className="p-4 border-b border-surface-border">
        <div className="text-caption text-zinc-500 mb-2">Phase Progress</div>

        {/* Overall progress bar */}
        <div className="h-2 bg-surface-3 rounded-full overflow-hidden mb-3">
          <div
            className="h-full bg-inde-500 transition-all duration-500"
            style={{ width: `${elapsedPercentage}%` }}
          />
        </div>
        <div className="text-caption text-zinc-500 text-center mb-4">
          {Math.round(elapsedPercentage)}% elapsed
        </div>

        {/* Phase segments */}
        {phases.length > 0 && (
          <div className="flex gap-1">
            {phases.map((phase, i) => {
              const phaseName = phase.name || phase.phase;
              const currentIndex = getPhaseIndex(currentPhase);
              const phaseIndex = getPhaseIndex(phaseName);
              const isCompleted = phaseIndex < currentIndex;
              const isCurrent = phaseName?.toUpperCase() === currentPhase?.toUpperCase();

              return (
                <PhaseSegment
                  key={i}
                  phase={phase}
                  isCurrent={isCurrent}
                  isCompleted={isCompleted}
                  percentage={phase.progress || 0}
                  duration={phase.duration || phase.planned_days}
                />
              );
            })}
          </div>
        )}
      </div>

      {/* Phase breakdown list */}
      <div className="p-4 border-b border-surface-border">
        <div className="text-caption text-zinc-500 mb-2">Phase Breakdown</div>

        <div className="divide-y divide-surface-border/50">
          {phases.length > 0 ? (
            phases.map((phase, i) => {
              const phaseName = phase.name || phase.phase;
              const currentIndex = getPhaseIndex(currentPhase);
              const phaseIndex = getPhaseIndex(phaseName);
              const isCompleted = phaseIndex < currentIndex;
              const isCurrent = phaseName?.toUpperCase() === currentPhase?.toUpperCase();

              return (
                <PhaseListItem
                  key={i}
                  phase={phase}
                  isCurrent={isCurrent}
                  isCompleted={isCompleted}
                  actual={phase.actual_days || (isCompleted ? phase.duration : null)}
                  planned={phase.planned_days || phase.duration}
                />
              );
            })
          ) : (
            <div className="py-4 text-center text-caption text-zinc-500">
              No phase data available
            </div>
          )}
        </div>
      </div>

      {/* v3.9/v3.10: Milestones section with timeline integrity features */}
      <div className="p-4 border-b border-surface-border">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-caption text-zinc-500">Milestones</span>
            {/* v3.10: Inconsistency indicator on header */}
            {hasInconsistency && (
              <AlertTriangle className="h-3 w-3 text-amber-400" title="Timeline inconsistency detected" />
            )}
          </div>
          <div className="flex items-center gap-2">
            {/* v3.10: History toggle */}
            {supersededCount > 0 && (
              <button
                onClick={() => setShowHistory(!showHistory)}
                className={cn(
                  'flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded transition-colors',
                  showHistory
                    ? 'text-inde-400 bg-inde-500/20'
                    : 'text-zinc-500 hover:text-zinc-400 bg-surface-3'
                )}
                title={showHistory ? 'Hide history' : 'Show superseded milestones'}
              >
                <History className="h-3 w-3" />
                {supersededCount}
              </button>
            )}
            {milestones.length > 0 && (
              <span className="text-caption text-zinc-600">({milestones.length})</span>
            )}
          </div>
        </div>

        {/* v3.10/v3.11: Inconsistency warning banner (permission-aware) */}
        {hasInconsistency && consistencyData && (
          <InconsistencyWarning
            allocationEnd={formatShortDate(consistencyData.allocation_end)}
            milestoneEnd={formatShortDate(consistencyData.milestone_end)}
            dayDifference={consistencyData.day_difference}
            canEdit={canEditMilestones}
            onResolve={async (source) => {
              try {
                await pursuitsApi.resolveTimelineInconsistency(pursuitId, { source_of_truth: source });
                refetchMilestones();
              } catch (e) {
                console.error('Failed to resolve inconsistency:', e);
              }
            }}
          />
        )}

        {milestones.length === 0 ? (
          <div className="text-center py-4">
            <Flag className="h-6 w-6 text-zinc-600 mx-auto mb-2" />
            <p className="text-caption text-zinc-500">No milestones detected yet</p>
            <p className="text-caption text-zinc-600 text-xs mt-1">
              Mention dates in the conversation to add milestones
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {milestones.slice(0, 5).map((milestone) => (
              <MilestoneCard
                key={milestone.milestone_id}
                milestone={milestone}
                canEdit={canEditMilestones}
                onConfirmRelativeDate={async (m) => {
                  try {
                    await pursuitsApi.confirmRelativeDate(pursuitId, {
                      milestone_id: m.milestone_id,
                      confirmed_date: null // Confirm original date
                    });
                    refetchMilestones();
                  } catch (e) {
                    console.error('Failed to confirm date:', e);
                  }
                }}
              />
            ))}
            {milestones.length > 5 && (
              <button className="w-full text-center text-caption text-inde-400 hover:text-inde-300 py-2">
                Show all {milestones.length} milestones
              </button>
            )}
          </div>
        )}
      </div>

      {/* Velocity section */}
      <div className="p-4 border-b border-surface-border">
        <div className="text-caption text-zinc-500 mb-3">Velocity</div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-caption">
            <span className="text-zinc-500">Current</span>
            <span className="text-zinc-300">
              {velocity.current?.toFixed(1) || '--'} elem/week
            </span>
          </div>
          <div className="flex items-center justify-between text-caption">
            <span className="text-zinc-500">Expected</span>
            <span className="text-zinc-300">
              {velocity.expected?.toFixed(1) || '--'} elem/week
            </span>
          </div>
          <div className="flex items-center justify-between text-caption">
            <span className="text-zinc-500">Status</span>
            <VelocityBadge ratio={velocity.ratio} />
          </div>
        </div>
      </div>

      {/* Maturity section */}
      <div className="p-4">
        <div className="text-caption text-zinc-500 mb-3">Maturity</div>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-caption">
            <span className="text-zinc-500">Score</span>
            <span className="text-zinc-300">
              {maturity.score || '--'} / 100
            </span>
          </div>
          <div className="flex items-center justify-between text-caption">
            <span className="text-zinc-500">Level</span>
            <span className="text-zinc-300 capitalize">
              {maturity.level || '--'}
            </span>
          </div>
        </div>

        {/* Maturity progress bar */}
        {maturity.score && (
          <div className="mt-3">
            <div className="h-1.5 bg-surface-3 rounded-full overflow-hidden">
              <div
                className="h-full bg-inde-500 transition-all duration-500"
                style={{ width: `${maturity.score}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default TimelinePanel;
