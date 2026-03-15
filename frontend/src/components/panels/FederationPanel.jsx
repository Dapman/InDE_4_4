import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { federationApi } from '../../api/federation';
import { cn } from '../../lib/utils';
import {
  Globe,
  Radio,
  Clock,
  TrendingUp,
  Shield,
  Users,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  AlertCircle,
  CheckCircle,
  Loader2,
} from 'lucide-react';

// Display labels for federation status
const STATUS_LABELS = {
  DISCONNECTED: 'Local Only',
  CONNECTING: 'Connecting...',
  CONNECTED: 'Connected to Innovation Network',
  HALF_OPEN: 'Reconnecting...',
  OFFLINE: 'Local Only',
};

// Display labels for pattern types
const PATTERN_TYPE_LABELS = {
  temporal_benchmark: 'Timing & Velocity',
  pattern_contribution: 'Innovation Pattern',
  risk_intelligence: 'Risk Methodology',
  effectiveness: 'Effectiveness Metrics',
  retrospective_wisdom: 'Retrospective Learning',
  innovation_pattern: 'Innovation Pattern',
  methodology_pattern: 'Methodology Pattern',
};

// Display labels for trust relationship types
const TRUST_TYPE_LABELS = {
  PARTNER: 'Partner Organization',
  CONSORTIUM: 'Consortium Member',
  TRUSTED: 'Trusted Partner',
  VERIFIED: 'Verified Organization',
};

// Display labels for sharing levels
const SHARING_LEVEL_LABELS = {
  maximum: 'Maximum Sharing',
  balanced: 'Balanced',
  selective: 'Selective',
  private: 'Private',
  MAXIMUM: 'Maximum Sharing',
  BALANCED: 'Balanced',
  SELECTIVE: 'Selective',
  PRIVATE: 'Private',
};

/**
 * ConnectionStatus - Shows federation connection state
 */
function ConnectionStatus({ status, lastSync, syncHealth }) {
  const statusLabel = STATUS_LABELS[status] || status || 'Unknown';
  const isConnected = status === 'CONNECTED';
  const isConnecting = status === 'CONNECTING' || status === 'HALF_OPEN';

  return (
    <div className="bg-surface-4 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-body-sm font-medium text-zinc-300">Connection Status</h4>
        <div className={cn(
          'flex items-center gap-2 px-2.5 py-1 rounded-full text-caption',
          isConnected ? 'bg-emerald-500/10 text-emerald-400' :
          isConnecting ? 'bg-amber-500/10 text-amber-400' :
          'bg-zinc-500/10 text-zinc-400'
        )}>
          {isConnecting ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : isConnected ? (
            <CheckCircle className="w-3 h-3" />
          ) : (
            <AlertCircle className="w-3 h-3" />
          )}
          <span>{statusLabel}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-caption">
        <div>
          <p className="text-zinc-500">Last Sync</p>
          <p className="text-zinc-300">
            {lastSync ? new Date(lastSync).toLocaleTimeString() : 'Never'}
          </p>
        </div>
        <div>
          <p className="text-zinc-500">Sync Health</p>
          <div className="flex items-center gap-1.5">
            <span className={cn(
              'w-2 h-2 rounded-full',
              syncHealth === 'healthy' ? 'bg-emerald-500' :
              syncHealth === 'degraded' ? 'bg-amber-500' : 'bg-rose-500'
            )} />
            <span className="text-zinc-300 capitalize">{syncHealth || 'Unknown'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * PatternCard - Incoming pattern from federation
 */
function PatternCard({ pattern }) {
  const [expanded, setExpanded] = useState(false);
  const typeLabel = PATTERN_TYPE_LABELS[pattern.type] || pattern.type || 'Pattern';

  return (
    <div className="bg-surface-4 rounded-lg p-3">
      <div className="flex items-start justify-between mb-2">
        <span className="text-caption text-inde-400 bg-inde-500/10 px-2 py-0.5 rounded">
          {typeLabel}
        </span>
        <span className="text-caption text-zinc-600">
          {pattern.timestamp ? new Date(pattern.timestamp).toLocaleDateString() : ''}
        </span>
      </div>

      <p className="text-body-sm text-zinc-200 line-clamp-2">
        {pattern.summary || pattern.description}
      </p>

      <div className="flex items-center justify-between mt-2">
        <div className="flex items-center gap-2">
          {pattern.confidence && (
            <span className={cn(
              'text-caption px-1.5 py-0.5 rounded',
              pattern.confidence >= 0.8 ? 'bg-emerald-500/10 text-emerald-400' :
              pattern.confidence >= 0.5 ? 'bg-amber-500/10 text-amber-400' :
              'bg-zinc-500/10 text-zinc-400'
            )}>
              {Math.round(pattern.confidence * 100)}% confidence
            </span>
          )}
        </div>
        <span className="text-caption text-zinc-500">
          {pattern.source || 'Global Network'}
        </span>
      </div>

      {expanded && pattern.details && (
        <div className="mt-3 pt-3 border-t border-surface-border">
          <p className="text-caption text-zinc-400">{pattern.details}</p>
        </div>
      )}

      {pattern.details && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-caption text-inde-400 hover:text-inde-300 mt-2 flex items-center gap-1"
        >
          {expanded ? 'Show less' : 'View details'}
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
      )}
    </div>
  );
}

/**
 * BenchmarkCard - Global benchmark comparison
 */
function BenchmarkCard({ benchmark }) {
  const orgValue = benchmark.org_value || 0;
  const avgValue = benchmark.industry_avg || benchmark.avg_value || 50;
  const maxValue = Math.max(orgValue, avgValue, 100);
  const orgPercent = (orgValue / maxValue) * 100;
  const avgPercent = (avgValue / maxValue) * 100;

  return (
    <div className="bg-surface-4 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <h5 className="text-body-sm text-zinc-200">{benchmark.metric_name || benchmark.name}</h5>
        <span className="text-caption text-zinc-500">{benchmark.sample_size || 0} orgs</span>
      </div>

      <div className="space-y-2">
        {/* Your org */}
        <div className="flex items-center gap-2">
          <span className="text-caption text-zinc-500 w-12">You</span>
          <div className="flex-1 h-2 bg-surface-5 rounded-full overflow-hidden">
            <div
              className="h-full bg-inde-500 rounded-full transition-all"
              style={{ width: `${orgPercent}%` }}
            />
          </div>
          <span className="text-caption text-zinc-300 w-12 text-right">{orgValue}</span>
        </div>

        {/* Industry avg */}
        <div className="flex items-center gap-2">
          <span className="text-caption text-zinc-500 w-12">Avg</span>
          <div className="flex-1 h-2 bg-surface-5 rounded-full overflow-hidden">
            <div
              className="h-full bg-zinc-500 rounded-full transition-all"
              style={{ width: `${avgPercent}%` }}
            />
          </div>
          <span className="text-caption text-zinc-400 w-12 text-right">{avgValue}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * TrustRelationshipCard - Trust network relationship
 */
function TrustRelationshipCard({ relationship }) {
  const typeLabel = TRUST_TYPE_LABELS[relationship.type] || relationship.type || 'Partner';
  const sharingLabel = SHARING_LEVEL_LABELS[relationship.sharing_level] || relationship.sharing_level || 'Balanced';

  return (
    <div className="bg-surface-4 rounded-lg p-3 flex items-center gap-3">
      <div className="p-2 bg-surface-5 rounded-lg">
        <Users className="w-4 h-4 text-inde-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-body-sm text-zinc-200 truncate">
          {relationship.org_name || relationship.anonymous_name || 'Anonymous Partner'}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-caption text-zinc-500">{typeLabel}</span>
          <span className="text-zinc-700">·</span>
          <span className="text-caption text-zinc-500">{sharingLabel}</span>
        </div>
      </div>
      {relationship.reputation_score !== undefined && (
        <div className="flex items-center gap-1 text-caption text-emerald-400">
          <Shield className="w-3 h-3" />
          <span>{relationship.reputation_score}</span>
        </div>
      )}
    </div>
  );
}

/**
 * CollapsibleSection - Section with expand/collapse
 */
function CollapsibleSection({ title, icon: Icon, children, defaultOpen = true, count }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-surface-border pb-4 last:border-0">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between py-2"
      >
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-zinc-500" />
          <span className="text-body-sm font-medium text-zinc-300">{title}</span>
          {count !== undefined && (
            <span className="text-caption text-zinc-500">({count})</span>
          )}
        </div>
        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-zinc-500" />
        ) : (
          <ChevronDown className="w-4 h-4 text-zinc-500" />
        )}
      </button>
      {isOpen && <div className="space-y-3 mt-2">{children}</div>}
    </div>
  );
}

/**
 * FederationPanel - Right sidebar panel for federation status
 */
export function FederationPanel({ pursuitId, onDataChange }) {
  // Fetch federation status
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['federation-status'],
    queryFn: async () => {
      const response = await federationApi.getStatus();
      return response.data;
    },
    staleTime: 30 * 1000,
    refetchInterval: 30 * 1000,
  });

  // Fetch incoming patterns
  const { data: patterns, isLoading: patternsLoading } = useQuery({
    queryKey: ['federation-patterns'],
    queryFn: async () => {
      const response = await federationApi.getIncomingPatterns(10);
      return response.data?.patterns || response.data || [];
    },
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
  });

  // Fetch benchmarks
  const { data: benchmarks, isLoading: benchmarksLoading } = useQuery({
    queryKey: ['federation-benchmarks'],
    queryFn: async () => {
      const response = await federationApi.getBenchmarkComparison();
      return response.data?.benchmarks || response.data || [];
    },
    staleTime: 300 * 1000, // 5 min cache
  });

  // Fetch trust network
  const { data: trustNetwork, isLoading: trustLoading } = useQuery({
    queryKey: ['federation-trust'],
    queryFn: async () => {
      const response = await federationApi.getTrustNetwork();
      return response.data?.relationships || response.data || [];
    },
    staleTime: 300 * 1000,
  });

  const isLoading = statusLoading;

  if (isLoading) {
    return (
      <div className="p-4 space-y-4">
        <div className="h-24 bg-surface-4 rounded-lg animate-pulse" />
        <div className="h-32 bg-surface-4 rounded-lg animate-pulse" />
      </div>
    );
  }

  const isSimulation = status?.mode === 'simulation';

  return (
    <div className="p-4 space-y-4">
      {/* Simulation badge */}
      {isSimulation && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2 text-caption text-amber-400 flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          <span>Federation Simulation Mode</span>
        </div>
      )}

      {/* Connection Status */}
      <ConnectionStatus
        status={status?.state || status?.status}
        lastSync={status?.last_sync}
        syncHealth={status?.sync_health || 'healthy'}
      />

      {/* Incoming Patterns */}
      <CollapsibleSection
        title="Incoming Patterns"
        icon={Radio}
        count={patterns?.length || 0}
      >
        {!patternsLoading && patterns?.length > 0 ? (
          patterns.slice(0, 5).map((pattern, idx) => (
            <PatternCard key={pattern.id || idx} pattern={pattern} />
          ))
        ) : (
          <p className="text-caption text-zinc-500 py-2">
            No incoming patterns yet
          </p>
        )}
      </CollapsibleSection>

      {/* Global Benchmarks */}
      <CollapsibleSection
        title="Global Benchmarks"
        icon={TrendingUp}
        defaultOpen={false}
      >
        {!benchmarksLoading && benchmarks?.length > 0 ? (
          benchmarks.slice(0, 4).map((benchmark, idx) => (
            <BenchmarkCard key={benchmark.id || idx} benchmark={benchmark} />
          ))
        ) : (
          <p className="text-caption text-zinc-500 py-2">
            No benchmark data available
          </p>
        )}
      </CollapsibleSection>

      {/* Trust Network */}
      <CollapsibleSection
        title="Trust Network"
        icon={Shield}
        defaultOpen={false}
        count={trustNetwork?.length || 0}
      >
        {!trustLoading && trustNetwork?.length > 0 ? (
          trustNetwork.slice(0, 5).map((rel, idx) => (
            <TrustRelationshipCard key={rel.id || idx} relationship={rel} />
          ))
        ) : (
          <p className="text-caption text-zinc-500 py-2">
            No trust relationships established
          </p>
        )}
      </CollapsibleSection>
    </div>
  );
}

export default FederationPanel;
