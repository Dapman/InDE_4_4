import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Globe,
  Wifi,
  WifiOff,
  Share2,
  Download,
  CheckCircle,
  Clock,
  AlertCircle,
  FileText,
  Users,
  TrendingUp,
  Lightbulb,
} from 'lucide-react';
import { ikfApi } from '../api/ikf';
import { cn } from '../lib/utils';

// =============================================================================
// STATUS BADGE
// =============================================================================

function StatusBadge({ status }) {
  const config = {
    connected: { icon: Wifi, color: 'text-health-healthy', bg: 'bg-health-healthy/10', label: 'Connected' },
    disconnected: { icon: WifiOff, color: 'text-health-atrisk', bg: 'bg-health-atrisk/10', label: 'Disconnected' },
    syncing: { icon: Clock, color: 'text-health-caution', bg: 'bg-health-caution/10', label: 'Syncing' },
  };

  const { icon: Icon, color, bg, label } = config[status] || config.disconnected;

  return (
    <div className={cn('inline-flex items-center gap-2 px-3 py-1.5 rounded-full', bg)}>
      <Icon className={cn('h-4 w-4', color)} />
      <span className={cn('text-caption font-medium', color)}>{label}</span>
    </div>
  );
}

// =============================================================================
// CONTRIBUTION CARD
// =============================================================================

function ContributionCard({ contribution }) {
  const statusConfig = {
    PENDING: { color: 'text-health-caution', bg: 'bg-health-caution/10', label: 'Pending Review' },
    REVIEWED: { color: 'text-inde-400', bg: 'bg-inde-500/10', label: 'Reviewed' },
    IKF_READY: { color: 'text-health-healthy', bg: 'bg-health-healthy/10', label: 'Ready to Share' },
    SHARED: { color: 'text-blue-400', bg: 'bg-blue-500/10', label: 'Shared' },
    REJECTED: { color: 'text-health-atrisk', bg: 'bg-health-atrisk/10', label: 'Rejected' },
  };

  const { color, bg, label } = statusConfig[contribution.status] || statusConfig.PENDING;

  return (
    <div className="bg-surface-2 border border-surface-border rounded-lg p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-inde-400" />
          <span className="text-body-sm font-medium text-zinc-200">
            {contribution.package_type || 'Pattern Contribution'}
          </span>
        </div>
        <span className={cn('px-2 py-0.5 rounded-full text-caption', bg, color)}>
          {label}
        </span>
      </div>
      <p className="text-caption text-zinc-400 mb-3 line-clamp-2">
        {contribution.description || contribution.title || 'Innovation pattern from your pursuit'}
      </p>
      <div className="flex items-center justify-between">
        <span className="text-caption text-zinc-600">
          {contribution.created_at ? new Date(contribution.created_at).toLocaleDateString() : 'Recently'}
        </span>
        <span className="text-caption text-zinc-500">
          Level {contribution.generalization_level || 1}
        </span>
      </div>
    </div>
  );
}

// =============================================================================
// PATTERN CARD
// =============================================================================

function PatternCard({ pattern }) {
  return (
    <div className="bg-surface-2 border border-surface-border rounded-lg p-4 hover:border-inde-500/50 transition-colors cursor-pointer">
      <div className="flex items-start gap-3 mb-3">
        <div className="w-10 h-10 rounded-lg bg-inde-500/10 flex items-center justify-center flex-shrink-0">
          <Lightbulb className="h-5 w-5 text-inde-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-body-sm font-medium text-zinc-200 truncate">
            {pattern.title || pattern.name || 'Innovation Pattern'}
          </h3>
          <span className="text-caption text-zinc-500">
            {pattern.methodology || pattern.archetype || 'General'}
          </span>
        </div>
      </div>
      <p className="text-caption text-zinc-400 mb-3 line-clamp-2">
        {pattern.description || pattern.summary || 'Pattern insight from the innovation network'}
      </p>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <Users className="h-3 w-3 text-zinc-600" />
          <span className="text-caption text-zinc-600">
            {pattern.usage_count || 0} uses
          </span>
        </div>
        <span className={cn(
          'text-caption',
          (pattern.confidence || 0) >= 0.7 ? 'text-health-healthy' : 'text-zinc-500'
        )}>
          {Math.round((pattern.confidence || 0) * 100)}% confidence
        </span>
      </div>
    </div>
  );
}

// =============================================================================
// MAIN IKF PAGE
// =============================================================================

export default function IKFPage() {
  const [activeTab, setActiveTab] = useState('overview');

  // Fetch federation status
  const { data: statusData } = useQuery({
    queryKey: ['ikf-status'],
    queryFn: async () => {
      try {
        const response = await ikfApi.getFederationStatus();
        return response.data;
      } catch {
        return { status: 'disconnected', node_count: 0, patterns_available: 0 };
      }
    },
    staleTime: 60000,
    retry: false,
  });

  // Fetch contributions
  const { data: contributionsData } = useQuery({
    queryKey: ['ikf-contributions'],
    queryFn: async () => {
      try {
        const response = await ikfApi.getContributions();
        return response.data;
      } catch {
        return { contributions: [] };
      }
    },
    staleTime: 30000,
    retry: false,
  });

  // Fetch federated patterns
  const { data: patternsData } = useQuery({
    queryKey: ['ikf-patterns'],
    queryFn: async () => {
      try {
        const response = await ikfApi.getFederatedPatterns({});
        return response.data;
      } catch {
        return { patterns: [] };
      }
    },
    staleTime: 60000,
    retry: false,
  });

  const federationStatus = statusData?.status || statusData?.connection_status || 'disconnected';
  const contributions = contributionsData?.contributions || [];
  const patterns = patternsData?.patterns || [];

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'contributions', label: `Contributions (${contributions.length})` },
    { id: 'patterns', label: `Patterns (${patterns.length})` },
  ];

  return (
    <div className="h-full overflow-y-auto bg-surface-1">
      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-xl font-semibold text-zinc-100 mb-1">
              Innovation Knowledge Federation
            </h1>
            <p className="text-body-sm text-zinc-500">
              Connect to the federated innovation intelligence network
            </p>
          </div>
          <StatusBadge status={federationStatus} />
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-surface-2 border border-surface-border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Globe className="h-5 w-5 text-inde-400" />
              <span className="text-caption text-zinc-500">Network Nodes</span>
            </div>
            <span className="text-2xl font-bold text-zinc-200">
              {statusData?.node_count || statusData?.active_nodes || 0}
            </span>
          </div>
          <div className="bg-surface-2 border border-surface-border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Lightbulb className="h-5 w-5 text-health-healthy" />
              <span className="text-caption text-zinc-500">Available Patterns</span>
            </div>
            <span className="text-2xl font-bold text-zinc-200">
              {statusData?.patterns_available || patterns.length}
            </span>
          </div>
          <div className="bg-surface-2 border border-surface-border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Share2 className="h-5 w-5 text-blue-400" />
              <span className="text-caption text-zinc-500">Your Contributions</span>
            </div>
            <span className="text-2xl font-bold text-zinc-200">
              {contributions.length}
            </span>
          </div>
          <div className="bg-surface-2 border border-surface-border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Download className="h-5 w-5 text-phase-pitch" />
              <span className="text-caption text-zinc-500">Patterns Applied</span>
            </div>
            <span className="text-2xl font-bold text-zinc-200">
              {statusData?.patterns_applied || 0}
            </span>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-1 border-b border-surface-border mb-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'px-4 py-2 text-body-sm font-medium transition-colors border-b-2 -mb-px',
                activeTab === tab.id
                  ? 'text-inde-400 border-inde-500'
                  : 'text-zinc-500 border-transparent hover:text-zinc-300'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* How IKF Works */}
            <div className="bg-surface-2 border border-surface-border rounded-lg p-6">
              <h2 className="text-body-md font-medium text-zinc-200 mb-4">
                How the Innovation Knowledge Federation Works
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center p-4">
                  <div className="w-12 h-12 rounded-full bg-inde-500/10 flex items-center justify-center mx-auto mb-3">
                    <Share2 className="h-6 w-6 text-inde-400" />
                  </div>
                  <h3 className="text-body-sm font-medium text-zinc-300 mb-2">Contribute</h3>
                  <p className="text-caption text-zinc-500">
                    Share anonymized patterns and learnings from your innovation pursuits
                  </p>
                </div>
                <div className="text-center p-4">
                  <div className="w-12 h-12 rounded-full bg-health-healthy/10 flex items-center justify-center mx-auto mb-3">
                    <Globe className="h-6 w-6 text-health-healthy" />
                  </div>
                  <h3 className="text-body-sm font-medium text-zinc-300 mb-2">Connect</h3>
                  <p className="text-caption text-zinc-500">
                    Join a network of innovators sharing collective wisdom
                  </p>
                </div>
                <div className="text-center p-4">
                  <div className="w-12 h-12 rounded-full bg-phase-pitch/10 flex items-center justify-center mx-auto mb-3">
                    <TrendingUp className="h-6 w-6 text-phase-pitch" />
                  </div>
                  <h3 className="text-body-sm font-medium text-zinc-300 mb-2">Learn</h3>
                  <p className="text-caption text-zinc-500">
                    Apply proven patterns and benchmarks to accelerate your pursuits
                  </p>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            {(contributions.length > 0 || patterns.length > 0) && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {contributions.length > 0 && (
                  <div>
                    <h3 className="text-body-sm font-medium text-zinc-300 mb-3">
                      Recent Contributions
                    </h3>
                    <div className="space-y-3">
                      {contributions.slice(0, 3).map((c, i) => (
                        <ContributionCard key={c.contribution_id || i} contribution={c} />
                      ))}
                    </div>
                  </div>
                )}
                {patterns.length > 0 && (
                  <div>
                    <h3 className="text-body-sm font-medium text-zinc-300 mb-3">
                      Trending Patterns
                    </h3>
                    <div className="space-y-3">
                      {patterns.slice(0, 3).map((p, i) => (
                        <PatternCard key={p.pattern_id || i} pattern={p} />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'contributions' && (
          <div>
            {contributions.length === 0 ? (
              <div className="bg-surface-2 border border-surface-border rounded-lg p-8 text-center">
                <Share2 className="h-12 w-12 text-zinc-600 mx-auto mb-4" />
                <h3 className="text-body-md font-medium text-zinc-300 mb-2">
                  No Contributions Yet
                </h3>
                <p className="text-body-sm text-zinc-500 max-w-md mx-auto">
                  Complete innovation pursuits to contribute anonymized patterns to the network.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {contributions.map((c, i) => (
                  <ContributionCard key={c.contribution_id || i} contribution={c} />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'patterns' && (
          <div>
            {patterns.length === 0 ? (
              <div className="bg-surface-2 border border-surface-border rounded-lg p-8 text-center">
                <Lightbulb className="h-12 w-12 text-zinc-600 mx-auto mb-4" />
                <h3 className="text-body-md font-medium text-zinc-300 mb-2">
                  No Patterns Available
                </h3>
                <p className="text-body-sm text-zinc-500 max-w-md mx-auto">
                  {federationStatus === 'connected'
                    ? 'No patterns match your current pursuits yet.'
                    : 'Connect to the federation to access shared patterns.'}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {patterns.map((p, i) => (
                  <PatternCard key={p.pattern_id || i} pattern={p} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
