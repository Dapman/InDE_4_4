import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { federationApi } from '../../api/federation';
import { cn } from '../../lib/utils';
import { printContributions } from '../../lib/print';
import {
  Upload,
  CheckCircle,
  XCircle,
  Clock,
  Eye,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  FileText,
  AlertTriangle,
  Loader2,
  Printer,
} from 'lucide-react';

// Display labels for contribution status
const STATUS_LABELS = {
  DRAFT: 'Needs Your Review',
  REVIEWED: 'Approved',
  IKF_READY: 'Ready to Share',
  REJECTED: 'Declined',
  PENDING: 'Pending',
  SUBMITTED: 'Submitted',
};

// Status badge colors
const STATUS_COLORS = {
  DRAFT: 'bg-amber-500/10 text-amber-400',
  REVIEWED: 'bg-emerald-500/10 text-emerald-400',
  IKF_READY: 'bg-inde-500/10 text-inde-400',
  REJECTED: 'bg-rose-500/10 text-rose-400',
  PENDING: 'bg-zinc-500/10 text-zinc-400',
  SUBMITTED: 'bg-blue-500/10 text-blue-400',
};

// Display labels for package types
const PACKAGE_TYPE_LABELS = {
  temporal_benchmark: 'Timing & Velocity',
  pattern_contribution: 'Innovation Pattern',
  risk_intelligence: 'Risk Methodology',
  effectiveness: 'Effectiveness Metrics',
  retrospective_wisdom: 'Retrospective Learning',
};

/**
 * ContributionCard - Single contribution item
 */
function ContributionCard({ contribution, onReview }) {
  const statusLabel = STATUS_LABELS[contribution.status] || contribution.status || 'Unknown';
  const statusColor = STATUS_COLORS[contribution.status] || 'bg-zinc-500/10 text-zinc-400';
  const typeLabel = PACKAGE_TYPE_LABELS[contribution.package_type] || contribution.package_type || 'Contribution';

  const isDraft = contribution.status === 'DRAFT';

  return (
    <div className="bg-surface-4 rounded-lg p-3">
      <div className="flex items-start justify-between mb-2">
        <span className={cn('text-caption px-2 py-0.5 rounded', statusColor)}>
          {statusLabel}
        </span>
        <span className="text-caption text-zinc-600">
          {contribution.created_at ? new Date(contribution.created_at).toLocaleDateString() : ''}
        </span>
      </div>

      <div className="flex items-center gap-2 mb-2">
        <FileText className="w-4 h-4 text-zinc-500" />
        <span className="text-body-sm text-zinc-200">{typeLabel}</span>
      </div>

      {contribution.summary && (
        <p className="text-caption text-zinc-400 line-clamp-2 mb-3">
          {contribution.summary}
        </p>
      )}

      {isDraft && (
        <button
          onClick={() => onReview(contribution)}
          className="w-full flex items-center justify-center gap-2 py-2 bg-inde-500/10 hover:bg-inde-500/20 text-inde-400 rounded-lg text-body-sm transition-colors"
        >
          <Eye className="w-4 h-4" />
          <span>Review</span>
        </button>
      )}
    </div>
  );
}

/**
 * ReviewModal - Side-by-side contribution review
 */
function ReviewModal({ contribution, onClose, onApprove, onReject, isSubmitting }) {
  const [notes, setNotes] = useState('');

  // Fetch preview data
  const { data: preview, isLoading: previewLoading } = useQuery({
    queryKey: ['contribution-preview', contribution.id],
    queryFn: async () => {
      const response = await federationApi.getContributionPreview(contribution.id);
      return response.data;
    },
    enabled: !!contribution.id,
  });

  const typeLabel = PACKAGE_TYPE_LABELS[contribution.package_type] || contribution.package_type || 'Contribution';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60">
      <div className="bg-surface-3 border border-surface-border rounded-xl w-full max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between">
          <div>
            <h3 className="text-body-lg font-medium text-zinc-100">Review Contribution</h3>
            <p className="text-caption text-zinc-500 mt-0.5">{typeLabel}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-surface-4 rounded-lg text-zinc-500"
          >
            <XCircle className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {previewLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 text-inde-400 animate-spin" />
            </div>
          ) : (
            <>
              {/* Explanation */}
              <div className="bg-inde-500/5 border border-inde-500/20 rounded-lg px-4 py-3 mb-6">
                <p className="text-body-sm text-inde-300">
                  This is what will be shared with the Innovation Network. Personal and organizational details have been generalized.
                </p>
              </div>

              {/* Side-by-side comparison */}
              <div className="grid grid-cols-2 gap-6">
                {/* Original */}
                <div>
                  <h4 className="text-body-sm font-medium text-zinc-300 mb-3">Original</h4>
                  <div className="bg-surface-4 rounded-lg p-4 space-y-3">
                    {preview?.original ? (
                      Object.entries(preview.original).map(([key, value]) => (
                        <div key={key}>
                          <p className="text-caption text-zinc-500 capitalize">{key.replace(/_/g, ' ')}</p>
                          <p className="text-body-sm text-zinc-300 mt-0.5">
                            {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                          </p>
                        </div>
                      ))
                    ) : (
                      <p className="text-caption text-zinc-500">No original data available</p>
                    )}
                  </div>
                </div>

                {/* Generalized */}
                <div>
                  <h4 className="text-body-sm font-medium text-zinc-300 mb-3">Generalized (Shared)</h4>
                  <div className="bg-surface-4 rounded-lg p-4 space-y-3">
                    {preview?.generalized ? (
                      Object.entries(preview.generalized).map(([key, value]) => {
                        const isAnonymized = preview.anonymized_fields?.includes(key);
                        return (
                          <div key={key}>
                            <p className="text-caption text-zinc-500 capitalize flex items-center gap-1">
                              {key.replace(/_/g, ' ')}
                              {isAnonymized && (
                                <span className="text-emerald-400 text-[10px]">(anonymized)</span>
                              )}
                            </p>
                            <p className={cn(
                              'text-body-sm mt-0.5',
                              isAnonymized ? 'text-emerald-300' : 'text-zinc-300'
                            )}>
                              {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                            </p>
                          </div>
                        );
                      })
                    ) : (
                      <p className="text-caption text-zinc-500">No generalized data available</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Notes */}
              <div className="mt-6">
                <label className="text-body-sm text-zinc-300 block mb-2">Notes (optional)</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add any notes about your decision..."
                  className="w-full h-20 bg-surface-4 border border-surface-border rounded-lg px-3 py-2 text-body-sm text-zinc-200 placeholder:text-zinc-600 resize-none"
                />
              </div>
            </>
          )}
        </div>

        {/* Actions */}
        <div className="px-6 py-4 border-t border-surface-border flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 text-body-sm text-zinc-400 hover:text-zinc-300"
          >
            Cancel
          </button>
          <div className="flex items-center gap-3">
            <button
              onClick={() => onReject(notes)}
              disabled={isSubmitting}
              className="flex items-center gap-2 px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 rounded-lg text-body-sm transition-colors disabled:opacity-50"
            >
              <XCircle className="w-4 h-4" />
              <span>Decline</span>
            </button>
            <button
              onClick={() => onApprove(notes)}
              disabled={isSubmitting}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 rounded-lg text-body-sm transition-colors disabled:opacity-50"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <CheckCircle className="w-4 h-4" />
              )}
              <span>Approve</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * HistoryItem - Contribution history entry
 */
function HistoryItem({ contribution }) {
  const statusLabel = STATUS_LABELS[contribution.status] || contribution.status;
  const statusColor = STATUS_COLORS[contribution.status] || 'bg-zinc-500/10 text-zinc-400';
  const typeLabel = PACKAGE_TYPE_LABELS[contribution.package_type] || contribution.package_type;

  return (
    <div className="flex items-center gap-3 py-2">
      <div className={cn('p-1.5 rounded', statusColor)}>
        {contribution.status === 'REVIEWED' || contribution.status === 'IKF_READY' ? (
          <CheckCircle className="w-3.5 h-3.5" />
        ) : contribution.status === 'REJECTED' ? (
          <XCircle className="w-3.5 h-3.5" />
        ) : (
          <Clock className="w-3.5 h-3.5" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-body-sm text-zinc-300 truncate">{typeLabel}</p>
        <p className="text-caption text-zinc-500">{statusLabel}</p>
      </div>
      <span className="text-caption text-zinc-600">
        {contribution.updated_at ? new Date(contribution.updated_at).toLocaleDateString() : ''}
      </span>
    </div>
  );
}

/**
 * ContributionPanel - Right sidebar panel for contribution management
 */
export function ContributionPanel({ pursuitId, onDataChange }) {
  const queryClient = useQueryClient();
  const [reviewingContribution, setReviewingContribution] = useState(null);
  const [showHistory, setShowHistory] = useState(false);

  // Fetch draft contributions (need review)
  const { data: drafts, isLoading: draftsLoading } = useQuery({
    queryKey: ['contributions', 'DRAFT'],
    queryFn: async () => {
      const response = await federationApi.getContributions('DRAFT');
      return response.data?.contributions || response.data || [];
    },
    staleTime: 30 * 1000,
    refetchInterval: 30 * 1000,
  });

  // Fetch contribution history
  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['contributions-history'],
    queryFn: async () => {
      const response = await federationApi.getContributionHistory(20);
      return response.data?.contributions || response.data || [];
    },
    staleTime: 60 * 1000,
  });

  // Review mutation
  const reviewMutation = useMutation({
    mutationFn: async ({ id, decision }) => {
      return federationApi.reviewContribution(id, decision);
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['contributions']);
      queryClient.invalidateQueries(['contributions-history']);
      setReviewingContribution(null);
      onDataChange?.();
    },
  });

  const handleReview = useCallback((contribution) => {
    setReviewingContribution(contribution);
  }, []);

  const handleApprove = useCallback((notes) => {
    if (!reviewingContribution) return;
    reviewMutation.mutate({
      id: reviewingContribution.id,
      decision: { approved: true, notes },
    });
  }, [reviewingContribution, reviewMutation]);

  const handleReject = useCallback((notes) => {
    if (!reviewingContribution) return;
    reviewMutation.mutate({
      id: reviewingContribution.id,
      decision: { approved: false, notes },
    });
  }, [reviewingContribution, reviewMutation]);

  const pendingCount = drafts?.length || 0;

  // Handle print
  const handlePrint = () => {
    printContributions({
      drafts: drafts || [],
      history: history || [],
    });
  };

  return (
    <div className="p-4 space-y-4">
      {/* Pending review section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-body-sm font-medium text-zinc-300">Contribution Queue</h4>
          <div className="flex items-center gap-2">
            {pendingCount > 0 && (
              <span className="text-caption text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">
                {pendingCount} pending
              </span>
            )}
            <button
              onClick={handlePrint}
              className="p-1.5 hover:bg-surface-3 rounded transition-colors"
              title="Print contributions report"
            >
              <Printer className="h-4 w-4 text-zinc-500 hover:text-zinc-300" />
            </button>
          </div>
        </div>

        {draftsLoading ? (
          <div className="space-y-3">
            <div className="h-24 bg-surface-4 rounded-lg animate-pulse" />
            <div className="h-24 bg-surface-4 rounded-lg animate-pulse" />
          </div>
        ) : drafts && drafts.length > 0 ? (
          <div className="space-y-3">
            {drafts.map((contribution, idx) => (
              <ContributionCard
                key={contribution.id || idx}
                contribution={contribution}
                onReview={handleReview}
              />
            ))}
          </div>
        ) : (
          <div className="bg-surface-4 rounded-lg p-4 text-center">
            <CheckCircle className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
            <p className="text-body-sm text-zinc-300">All caught up!</p>
            <p className="text-caption text-zinc-500 mt-1">
              No contributions need your review
            </p>
          </div>
        )}
      </div>

      {/* History section */}
      <div className="border-t border-surface-border pt-4">
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="w-full flex items-center justify-between py-2"
        >
          <span className="text-body-sm font-medium text-zinc-300">Contribution History</span>
          {showHistory ? (
            <ChevronUp className="w-4 h-4 text-zinc-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-zinc-500" />
          )}
        </button>

        {showHistory && (
          <div className="mt-2">
            {historyLoading ? (
              <div className="h-32 bg-surface-4 rounded-lg animate-pulse" />
            ) : history && history.length > 0 ? (
              <div className="bg-surface-4 rounded-lg divide-y divide-surface-border">
                {history.slice(0, 10).map((contribution, idx) => (
                  <div key={contribution.id || idx} className="px-3">
                    <HistoryItem contribution={contribution} />
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-caption text-zinc-500 py-4 text-center">
                No contribution history yet
              </p>
            )}
          </div>
        )}
      </div>

      {/* Review Modal */}
      {reviewingContribution && (
        <ReviewModal
          contribution={reviewingContribution}
          onClose={() => setReviewingContribution(null)}
          onApprove={handleApprove}
          onReject={handleReject}
          isSubmitting={reviewMutation.isPending}
        />
      )}
    </div>
  );
}

export default ContributionPanel;
