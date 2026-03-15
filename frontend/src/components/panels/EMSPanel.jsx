import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { emsApi } from '../../api/ems';
import { useAuthStore } from '../../stores/authStore';
import { usePursuitStore } from '../../stores/pursuitStore';
import { cn } from '../../lib/utils';
import {
  Eye,
  Brain,
  Sparkles,
  ChevronRight,
  AlertCircle,
  CheckCircle,
  Loader2,
} from 'lucide-react';

// Confidence tier labels
const CONFIDENCE_LABELS = {
  HIGH: { label: 'High', color: 'text-emerald-400' },
  MODERATE: { label: 'Moderate', color: 'text-amber-400' },
  LOW: { label: 'Low', color: 'text-rose-400' },
};

/**
 * ObservationStatus - Shows observation capture status
 */
function ObservationStatus({ observationCount, lastObservation, phasesDetected, eligibleIn }) {
  return (
    <div className="bg-surface-4 rounded-lg p-4">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-phase-vision/20 rounded-lg">
          <Eye className="w-5 h-5 text-phase-vision" />
        </div>
        <div>
          <h4 className="text-body-sm font-medium text-zinc-200">
            Observing Your Process
          </h4>
          <p className="text-caption text-zinc-500">
            {observationCount} observations captured
          </p>
        </div>
      </div>

      <div className="space-y-2 text-caption">
        <div className="flex items-center justify-between">
          <span className="text-zinc-500">Last observation</span>
          <span className="text-zinc-300">{lastObservation || 'Just now'}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-zinc-500">Phases detected</span>
          <span className="text-zinc-300">~{phasesDetected || 0}</span>
        </div>
        {eligibleIn > 0 && (
          <div className="flex items-center justify-between pt-2 border-t border-surface-border">
            <span className="text-zinc-500">Next milestone</span>
            <span className="text-inde-400">{eligibleIn} more for synthesis</span>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * InferenceReady - Shows when inference is available
 */
function InferenceReady({ inference, onReview }) {
  const confidenceConfig = CONFIDENCE_LABELS[inference.confidence_tier] || CONFIDENCE_LABELS.MODERATE;
  const confidencePercent = Math.round((inference.confidence || 0.5) * 100);

  return (
    <div className="bg-surface-4 rounded-lg p-4">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-inde-500/20 rounded-lg">
          <Brain className="w-5 h-5 text-inde-400" />
        </div>
        <div>
          <h4 className="text-body-sm font-medium text-zinc-200">
            Methodology Discovery
          </h4>
          <p className="text-caption text-zinc-500">
            {inference.phase_count || 0} phases discovered
          </p>
        </div>
      </div>

      <div className="space-y-2 text-caption mb-4">
        <div className="flex items-center justify-between">
          <span className="text-zinc-500">Confidence</span>
          <span className={confidenceConfig.color}>
            {confidenceConfig.label} ({confidencePercent}%)
          </span>
        </div>
        {inference.working_name && (
          <div className="flex items-center justify-between">
            <span className="text-zinc-500">Working name</span>
            <span className="text-zinc-300">{inference.working_name}</span>
          </div>
        )}
        {inference.pursuits_used > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-zinc-500">Based on</span>
            <span className="text-zinc-300">{inference.pursuits_used} pursuits</span>
          </div>
        )}
      </div>

      <button
        onClick={onReview}
        className="w-full flex items-center justify-center gap-2 py-2.5 bg-inde-500/10 hover:bg-inde-500/20 text-inde-400 rounded-lg text-body-sm transition-colors"
      >
        <span>Review Your Methodology</span>
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
}

/**
 * NoActiveObservation - Shows when no ad-hoc pursuit active
 */
function NoActiveObservation({ onStartPursuit }) {
  return (
    <div className="bg-surface-4 rounded-lg p-4 text-center">
      <Sparkles className="w-8 h-8 text-zinc-600 mx-auto mb-3" />
      <h4 className="text-body-sm text-zinc-300 mb-1">
        No Active Observation
      </h4>
      <p className="text-caption text-zinc-500 mb-4">
        Start a freeform pursuit to discover your methodology
      </p>
      <button
        onClick={onStartPursuit}
        className="text-caption text-inde-400 hover:text-inde-300"
      >
        Start a Freeform Pursuit →
      </button>
    </div>
  );
}

/**
 * PublishedArchetypesQuick - Quick view of published archetypes
 */
function PublishedArchetypesQuick({ archetypes, onViewAll }) {
  if (!archetypes || archetypes.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 pt-4 border-t border-surface-border">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-caption text-zinc-500">Your Methodologies</h4>
        <button
          onClick={onViewAll}
          className="text-caption text-inde-400 hover:text-inde-300"
        >
          View all
        </button>
      </div>
      <div className="space-y-2">
        {archetypes.slice(0, 3).map((arch) => (
          <div
            key={arch.id}
            className="flex items-center gap-2 bg-surface-5 rounded-lg px-3 py-2"
          >
            <CheckCircle className="w-4 h-4 text-emerald-500" />
            <span className="text-body-sm text-zinc-300 truncate flex-1">
              {arch.name || arch.working_name}
            </span>
            <span className="text-caption text-zinc-600">v{arch.version || '1.0'}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * EMSPanel - Right sidebar panel for EMS status
 */
export function EMSPanel({ pursuitId, onDataChange }) {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const activePursuit = usePursuitStore((s) => {
    const list = s.pursuitList || [];
    return list.find((p) => p.id === pursuitId);
  });

  // Check if active pursuit is ad-hoc/freeform
  const isAdHocPursuit = activePursuit?.archetype === 'freeform' || !activePursuit?.archetype;

  // Fetch observation status for ad-hoc pursuit
  const { data: observationStatus, isLoading: observationLoading } = useQuery({
    queryKey: ['ems-observations', pursuitId],
    queryFn: async () => {
      const response = await emsApi.getObservations(pursuitId);
      return response.data;
    },
    enabled: !!pursuitId && isAdHocPursuit,
    staleTime: 30 * 1000,
    refetchInterval: 30 * 1000,
  });

  // Fetch latest inference
  const { data: latestInference, isLoading: inferenceLoading } = useQuery({
    queryKey: ['ems-inference', user?.id],
    queryFn: async () => {
      const response = await emsApi.getInferredArchetypes(user?.id);
      const data = response.data;
      // Get the most recent inference
      if (Array.isArray(data)) {
        return data[0] || null;
      }
      return data?.latest || data || null;
    },
    enabled: !!user?.id,
    staleTime: 60 * 1000,
  });

  // Fetch published archetypes
  const { data: publishedArchetypes } = useQuery({
    queryKey: ['ems-archetypes-mine'],
    queryFn: async () => {
      const response = await emsApi.getMyArchetypes();
      return response.data?.archetypes || response.data || [];
    },
    staleTime: 300 * 1000,
  });

  const handleReview = () => {
    navigate('/ems');
  };

  const handleStartPursuit = () => {
    navigate('/pursuit/new?archetype=freeform');
  };

  const handleViewAll = () => {
    navigate('/ems');
  };

  const isLoading = observationLoading || inferenceLoading;

  if (isLoading) {
    return (
      <div className="p-4">
        <div className="h-32 bg-surface-4 rounded-lg animate-pulse" />
      </div>
    );
  }

  // Determine what to show
  const hasInference = latestInference && latestInference.phase_count > 0;
  const hasObservations = observationStatus && observationStatus.count > 0;

  return (
    <div className="p-4 space-y-4">
      {/* Show inference ready if available */}
      {hasInference && (
        <InferenceReady
          inference={latestInference}
          onReview={handleReview}
        />
      )}

      {/* Show observation status if ad-hoc pursuit */}
      {isAdHocPursuit && hasObservations && !hasInference && (
        <ObservationStatus
          observationCount={observationStatus.count || 0}
          lastObservation={observationStatus.last_observation_time}
          phasesDetected={observationStatus.phases_detected}
          eligibleIn={observationStatus.observations_until_eligible}
        />
      )}

      {/* Show no active observation if not ad-hoc */}
      {!isAdHocPursuit && !hasInference && (
        <NoActiveObservation onStartPursuit={handleStartPursuit} />
      )}

      {/* Quick view of published archetypes */}
      <PublishedArchetypesQuick
        archetypes={publishedArchetypes}
        onViewAll={handleViewAll}
      />

      {/* Link to full EMS page */}
      <div className="text-center pt-2">
        <button
          onClick={handleViewAll}
          className="text-caption text-zinc-500 hover:text-zinc-300"
        >
          Open EMS Dashboard →
        </button>
      </div>
    </div>
  );
}

export default EMSPanel;
