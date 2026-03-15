import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { emsApi } from '../api/ems';
import { useAuthStore } from '../stores/authStore';
import { cn } from '../lib/utils';
import {
  Sparkles,
  Eye,
  Brain,
  Play,
  CheckCircle,
  AlertCircle,
  Lock,
  Users,
  Building2,
  Globe,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  Loader2,
  Star,
} from 'lucide-react';

// Confidence tier configuration
const CONFIDENCE_CONFIG = {
  HIGH: { label: 'High', color: 'text-emerald-400', bg: 'bg-emerald-500/10', stars: 3 },
  MODERATE: { label: 'Moderate', color: 'text-amber-400', bg: 'bg-amber-500/10', stars: 2 },
  LOW: { label: 'Low', color: 'text-rose-400', bg: 'bg-rose-500/10', stars: 1 },
};

// Visibility configuration
const VISIBILITY_CONFIG = {
  personal: { label: 'Personal', icon: Lock, description: 'Only you can see' },
  team: { label: 'Team', icon: Users, description: 'Shared with team' },
  organization: { label: 'Organization', icon: Building2, description: 'Available org-wide' },
  indaverse: { label: 'InDEVerse', icon: Globe, description: 'Shared globally' },
};

/**
 * ConfidenceBadge - Displays confidence level with stars
 */
function ConfidenceBadge({ tier, confidence }) {
  const config = CONFIDENCE_CONFIG[tier] || CONFIDENCE_CONFIG.MODERATE;
  const percent = Math.round((confidence || 0.5) * 100);

  return (
    <div className={cn('flex items-center gap-2 px-2.5 py-1 rounded-lg', config.bg)}>
      <div className="flex">
        {[1, 2, 3].map((n) => (
          <Star
            key={n}
            className={cn(
              'w-3.5 h-3.5',
              n <= config.stars ? config.color : 'text-zinc-600'
            )}
            fill={n <= config.stars ? 'currentColor' : 'none'}
          />
        ))}
      </div>
      <span className={cn('text-caption', config.color)}>
        {config.label} ({percent}%)
      </span>
    </div>
  );
}

/**
 * PhaseCard - Displays a discovered phase (read-only preview)
 */
function PhaseCard({ phase, index }) {
  const [expanded, setExpanded] = useState(false);
  const config = CONFIDENCE_CONFIG[phase.confidence_tier] || CONFIDENCE_CONFIG.MODERATE;

  return (
    <div className="bg-surface-4 border border-surface-border rounded-xl p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-display-xs font-bold text-zinc-500">
            {index + 1}
          </span>
          <div>
            <h4 className="text-body-sm font-medium text-zinc-200">
              {phase.name || `Phase ${index + 1}`}
            </h4>
            {phase.occurrence_rate && (
              <p className="text-caption text-zinc-500">
                {phase.occurrence_rate}% of pursuits
              </p>
            )}
          </div>
        </div>
        <ConfidenceBadge tier={phase.confidence_tier} confidence={phase.confidence} />
      </div>

      {/* Activities */}
      {phase.activities && phase.activities.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {phase.activities.slice(0, expanded ? undefined : 5).map((activity, idx) => (
            <span
              key={idx}
              className={cn(
                'px-2.5 py-1 rounded-full text-caption',
                activity.optional
                  ? 'border border-zinc-600 text-zinc-400'
                  : 'bg-surface-5 text-zinc-300'
              )}
            >
              {activity.name || activity}
            </span>
          ))}
          {!expanded && phase.activities.length > 5 && (
            <span className="text-caption text-zinc-500 py-1">
              +{phase.activities.length - 5} more
            </span>
          )}
        </div>
      )}

      {/* Tools */}
      {phase.tools && phase.tools.length > 0 && (
        <div className="text-caption text-zinc-500">
          Tools: {phase.tools.join(', ')}
        </div>
      )}

      {phase.activities && phase.activities.length > 5 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-caption text-inde-400 hover:text-inde-300 mt-2 flex items-center gap-1"
        >
          {expanded ? 'Show less' : 'Show all activities'}
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
      )}
    </div>
  );
}

/**
 * InferenceOverview - Overview card for inference result
 */
function InferenceOverview({ inference, onStartReview, isStarting }) {
  return (
    <div className="bg-surface-3 border border-surface-border rounded-xl p-6">
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-inde-500/10 rounded-xl">
            <Brain className="w-8 h-8 text-inde-400" />
          </div>
          <div>
            <h2 className="text-display-sm font-semibold text-zinc-100">
              {inference.working_name || 'Discovered Methodology'}
            </h2>
            <p className="text-body-sm text-zinc-500 mt-1">
              {inference.phase_count || 0} phases discovered from {inference.pursuits_used || 0} pursuits
            </p>
          </div>
        </div>
        <ConfidenceBadge tier={inference.confidence_tier} confidence={inference.confidence} />
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-surface-4 rounded-lg p-4">
          <p className="text-display-xs font-semibold text-zinc-100">
            {inference.phase_count || 0}
          </p>
          <p className="text-caption text-zinc-500">Phases</p>
        </div>
        <div className="bg-surface-4 rounded-lg p-4">
          <p className="text-display-xs font-semibold text-zinc-100">
            {inference.activity_count || 0}
          </p>
          <p className="text-caption text-zinc-500">Activities</p>
        </div>
        <div className="bg-surface-4 rounded-lg p-4">
          <p className="text-display-xs font-semibold text-zinc-100">
            {inference.tool_count || 0}
          </p>
          <p className="text-caption text-zinc-500">Tools Used</p>
        </div>
      </div>

      <button
        onClick={onStartReview}
        disabled={isStarting}
        className="w-full flex items-center justify-center gap-2 py-3 bg-inde-500 hover:bg-inde-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
      >
        {isStarting ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : (
          <Play className="w-5 h-5" />
        )}
        <span>Start Review Session</span>
      </button>
    </div>
  );
}

/**
 * ComparisonPreview - Preview comparison with existing archetypes
 */
function ComparisonPreview({ comparison }) {
  if (!comparison || comparison.length === 0) {
    return null;
  }

  return (
    <div className="bg-surface-3 border border-surface-border rounded-xl p-6">
      <h3 className="text-body-lg font-medium text-zinc-200 mb-4">
        Similarity to Existing Methodologies
      </h3>
      <div className="space-y-3">
        {comparison.slice(0, 5).map((item, idx) => (
          <div key={idx} className="flex items-center gap-4">
            <span className="text-body-sm text-zinc-300 w-32 truncate">
              {item.archetype_name || item.name}
            </span>
            <div className="flex-1 h-3 bg-surface-4 rounded-full overflow-hidden">
              <div
                className="h-full bg-inde-500 rounded-full transition-all"
                style={{ width: `${(item.similarity || 0) * 100}%` }}
              />
            </div>
            <span className="text-caption text-zinc-500 w-12 text-right">
              {Math.round((item.similarity || 0) * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * PublishedArchetypeCard - Card for a published methodology
 */
function PublishedArchetypeCard({ archetype, onCheckEvolution, onChangeVisibility }) {
  const [showVisibility, setShowVisibility] = useState(false);
  const visibilityConfig = VISIBILITY_CONFIG[archetype.visibility] || VISIBILITY_CONFIG.personal;
  const VisIcon = visibilityConfig.icon;

  return (
    <div className="bg-surface-4 border border-surface-border rounded-xl p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h4 className="text-body-md font-medium text-zinc-200">
            {archetype.name || archetype.working_name}
          </h4>
          <p className="text-caption text-zinc-500 mt-0.5">
            v{archetype.version || '1.0'} • {archetype.phase_count || 0} phases
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn(
            'flex items-center gap-1.5 px-2 py-1 rounded text-caption',
            'bg-surface-5 text-zinc-400'
          )}>
            <VisIcon className="w-3 h-3" />
            {visibilityConfig.label}
          </span>
        </div>
      </div>

      {archetype.description && (
        <p className="text-body-sm text-zinc-400 mb-4 line-clamp-2">
          {archetype.description}
        </p>
      )}

      <div className="flex items-center justify-between pt-3 border-t border-surface-border">
        <div className="flex items-center gap-4 text-caption text-zinc-500">
          <span>{archetype.usage_count || 0} uses</span>
          <span>{archetype.created_at ? new Date(archetype.created_at).toLocaleDateString() : ''}</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowVisibility(!showVisibility)}
            className="text-caption text-zinc-400 hover:text-zinc-300"
          >
            Change visibility
          </button>
          <button
            onClick={() => onCheckEvolution(archetype.id)}
            className="flex items-center gap-1 text-caption text-inde-400 hover:text-inde-300"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Check for updates
          </button>
        </div>
      </div>

      {/* Visibility dropdown */}
      {showVisibility && (
        <div className="mt-3 pt-3 border-t border-surface-border">
          <p className="text-caption text-zinc-500 mb-2">Select visibility:</p>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(VISIBILITY_CONFIG).map(([key, config]) => {
              const Icon = config.icon;
              return (
                <button
                  key={key}
                  onClick={() => {
                    onChangeVisibility(archetype.id, key);
                    setShowVisibility(false);
                  }}
                  className={cn(
                    'flex items-center gap-2 p-2 rounded-lg text-left transition-colors',
                    archetype.visibility === key
                      ? 'bg-inde-500/10 text-inde-400'
                      : 'bg-surface-5 text-zinc-400 hover:bg-surface-3'
                  )}
                >
                  <Icon className="w-4 h-4" />
                  <div>
                    <p className="text-caption font-medium">{config.label}</p>
                    <p className="text-[10px] text-zinc-500">{config.description}</p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * EmptyState - Shows when no inference or archetypes
 */
function EmptyState({ hasObservations, observationCount, eligibleIn }) {
  const navigate = useNavigate();

  if (hasObservations) {
    return (
      <div className="bg-surface-3 border border-surface-border rounded-xl p-8 text-center">
        <Eye className="w-12 h-12 text-phase-vision mx-auto mb-4" />
        <h3 className="text-display-sm font-semibold text-zinc-100 mb-2">
          Observing Your Process
        </h3>
        <p className="text-body-sm text-zinc-400 mb-4 max-w-md mx-auto">
          EMS has captured {observationCount} observations so far.
          {eligibleIn > 0 && ` ${eligibleIn} more observations needed before synthesis can begin.`}
        </p>
        <div className="w-full max-w-xs mx-auto h-2 bg-surface-4 rounded-full overflow-hidden">
          <div
            className="h-full bg-phase-vision rounded-full transition-all"
            style={{ width: `${Math.min(100, (observationCount / (observationCount + eligibleIn)) * 100)}%` }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-surface-3 border border-surface-border rounded-xl p-8 text-center">
      <Sparkles className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
      <h3 className="text-display-sm font-semibold text-zinc-100 mb-2">
        No Methodology Discovered Yet
      </h3>
      <p className="text-body-sm text-zinc-400 mb-6 max-w-md mx-auto">
        Complete 3 or more freeform pursuits and InDE will discover the methodology hidden in your practice.
      </p>
      <button
        onClick={() => navigate('/pursuit/new?archetype=freeform')}
        className="inline-flex items-center gap-2 px-4 py-2 bg-inde-500/10 hover:bg-inde-500/20 text-inde-400 rounded-lg transition-colors"
      >
        <Play className="w-4 h-4" />
        Start a Freeform Pursuit
      </button>
    </div>
  );
}

/**
 * EMSPage - Full EMS dashboard
 */
export default function EMSPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  // Fetch observation status
  const { data: observationStatus } = useQuery({
    queryKey: ['ems-observation-status', user?.id],
    queryFn: async () => {
      const response = await emsApi.getSynthesisEligibility(user?.id);
      return response.data;
    },
    enabled: !!user?.id,
  });

  // Fetch latest inference
  const { data: latestInference, isLoading: inferenceLoading } = useQuery({
    queryKey: ['ems-inference', user?.id],
    queryFn: async () => {
      const response = await emsApi.getInferredArchetypes(user?.id);
      const data = response.data;
      if (Array.isArray(data)) {
        return data[0] || null;
      }
      return data?.latest || data || null;
    },
    enabled: !!user?.id,
  });

  // Fetch comparison data if inference exists
  const { data: comparison } = useQuery({
    queryKey: ['ems-comparison', latestInference?.id],
    queryFn: async () => {
      // This would use the comparison API - for now return mock structure
      return latestInference?.archetype_comparison || [];
    },
    enabled: !!latestInference?.id,
  });

  // Fetch published archetypes
  const { data: publishedArchetypes, isLoading: archetypesLoading } = useQuery({
    queryKey: ['ems-archetypes-mine'],
    queryFn: async () => {
      const response = await emsApi.getMyArchetypes();
      return response.data?.archetypes || response.data || [];
    },
  });

  // Start review mutation
  const startReviewMutation = useMutation({
    mutationFn: async () => {
      return emsApi.startReview(user?.id, latestInference?.id);
    },
    onSuccess: (response) => {
      const sessionId = response.data?.session_id || response.data?.id;
      navigate(`/ems/review/${sessionId}`);
    },
  });

  // Check evolution mutation
  const checkEvolutionMutation = useMutation({
    mutationFn: async (archetypeId) => {
      return emsApi.checkEvolution(archetypeId);
    },
  });

  // Change visibility mutation
  const changeVisibilityMutation = useMutation({
    mutationFn: async ({ id, visibility }) => {
      return emsApi.updateArchetypeVisibility(id, visibility);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['ems-archetypes-mine']);
    },
  });

  const handleStartReview = () => {
    startReviewMutation.mutate();
  };

  const handleCheckEvolution = (id) => {
    checkEvolutionMutation.mutate(id);
  };

  const handleChangeVisibility = (id, visibility) => {
    changeVisibilityMutation.mutate({ id, visibility });
  };

  const isLoading = inferenceLoading || archetypesLoading;
  const hasInference = latestInference && latestInference.phase_count > 0;
  const hasPublished = publishedArchetypes && publishedArchetypes.length > 0;

  if (isLoading) {
    return (
      <div className="flex-1 p-6 overflow-y-auto">
        <div className="max-w-4xl mx-auto animate-pulse space-y-6">
          <div className="h-8 w-64 bg-surface-4 rounded" />
          <div className="h-48 bg-surface-3 rounded-xl" />
          <div className="grid grid-cols-2 gap-4">
            <div className="h-32 bg-surface-3 rounded-xl" />
            <div className="h-32 bg-surface-3 rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-6 overflow-y-auto">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-display-md font-semibold text-zinc-100">
            Emergent Methodology Synthesizer
          </h1>
          <p className="text-body-sm text-zinc-500 mt-1">
            Discover and refine your unique innovation methodology
          </p>
        </div>

        {/* Main content */}
        {hasInference ? (
          <>
            {/* Inference Overview */}
            <InferenceOverview
              inference={latestInference}
              onStartReview={handleStartReview}
              isStarting={startReviewMutation.isPending}
            />

            {/* Phase Cards */}
            {latestInference.phases && latestInference.phases.length > 0 && (
              <div>
                <h3 className="text-body-lg font-medium text-zinc-200 mb-4">
                  Discovered Phases
                </h3>
                <div className="space-y-4">
                  {latestInference.phases.map((phase, idx) => (
                    <PhaseCard key={phase.id || idx} phase={phase} index={idx} />
                  ))}
                </div>
              </div>
            )}

            {/* Comparison Preview */}
            <ComparisonPreview comparison={comparison} />
          </>
        ) : (
          <EmptyState
            hasObservations={observationStatus?.observation_count > 0}
            observationCount={observationStatus?.observation_count || 0}
            eligibleIn={observationStatus?.observations_until_eligible || 0}
          />
        )}

        {/* Published Archetypes */}
        {hasPublished && (
          <div>
            <h3 className="text-body-lg font-medium text-zinc-200 mb-4">
              My Methodologies
            </h3>
            <div className="grid gap-4">
              {publishedArchetypes.map((archetype) => (
                <PublishedArchetypeCard
                  key={archetype.id}
                  archetype={archetype}
                  onCheckEvolution={handleCheckEvolution}
                  onChangeVisibility={handleChangeVisibility}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
