import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { motion } from 'framer-motion';
import { Plus, Sparkles, ArrowRight, Archive, XCircle, Fingerprint } from 'lucide-react';
import { pursuitsApi } from '../api/pursuits';
import { useAuthStore } from '../stores/authStore';
import { Button } from '../components/ui/button';
import { HealthIndicator } from '../components/coaching/HealthIndicator';
import { PhaseBadge } from '../components/PhaseBadge';
import { cn } from '../lib/utils';

// v3.13: Import archive and export components
import ArchiveButton from '../components/pursuit/ArchiveButton';
import ExportButton from '../components/export/ExportButton';

const ARCHETYPE_EMOJIS = {
  lean_startup: '🔬',
  design_thinking: '🎨',
  stage_gate: '🏗️',
  triz: '🧩',
  blue_ocean: '🌊',
  freeform: '✨',
};

export default function DashboardPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();

  // Refresh pursuits list after archive/restore
  const handleArchived = () => {
    // Invalidate both the dashboard query and regular pursuits query
    queryClient.invalidateQueries({ queryKey: ['dashboard-pursuits'] });
    queryClient.invalidateQueries({ queryKey: ['pursuits'] });
  };

  // Fetch pursuits (include archived so they show in Archived section)
  // Use unique query key to avoid being overwritten by other components
  const { data: pursuits = [], isLoading, error } = useQuery({
    queryKey: ['dashboard-pursuits'],
    queryFn: async () => {
      console.log('[Dashboard] Fetching pursuits...');
      try {
        // v3.13: Force include_archived=true to show archived section
        console.log('[Dashboard] Calling API with include_archived=true');
        const response = await pursuitsApi.list({ include_archived: true });
        console.log('[Dashboard] Raw API response:', response);
        console.log('[Dashboard] Response data pursuits:', response.data?.pursuits);
        const rawList = response.data?.pursuits || response.data || [];
        console.log('[Dashboard] Extracted rawList:', rawList);
        // Handle case where response is not an array
        if (!Array.isArray(rawList)) {
          console.warn('[Dashboard] Pursuits API returned non-array:', rawList);
          return [];
        }
        // Map backend field names to frontend expected names
        const mapped = rawList.map((p) => ({
          id: p.pursuit_id || p.id,
          name: p.title || p.name,
          state: (p.status || p.state || 'active').toUpperCase(),
          phase: p.phase || 'VISION',
          archetype: p.archetype || p.methodology || 'freeform',
          health_zone: p.health_zone || p.healthZone,
          health_score: p.health_score || p.healthScore,
          spark_description: p.description || p.spark_description,
          updated_at: p.updated_at || p.updatedAt,
          is_archived: p.is_archived || false,
          gii_id: p.gii_id || null,  // v3.16: Global Innovator Identifier
        }));
        console.log('[Dashboard] Mapped pursuits:', mapped);
        return mapped;
      } catch (err) {
        console.error('[Dashboard] Error fetching pursuits:', err);
        throw err;
      }
    },
  });

  // v3.13: Filter considers both status-based states AND is_archived flag
  const activePursuits = pursuits.filter(
    (p) => !p.is_archived && (p.state === 'ACTIVE' || p.state === 'PENDING')
  );
  const completedPursuits = pursuits.filter(
    (p) => !p.is_archived && p.state === 'COMPLETED'
  );
  // Archived includes: is_archived flag OR status-based archived/abandoned/deleted
  const archivedPursuits = pursuits.filter(
    (p) => p.is_archived || p.state === 'ARCHIVED' || p.state === 'ABANDONED' || p.state === 'DELETED'
  );

  const userName = user?.name?.split(' ')[0] || user?.email?.split('@')[0] || 'Innovator';

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-pulse text-body-md text-zinc-500">
          Loading your portfolio...
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="w-16 h-16 rounded-2xl bg-red-500/10 flex items-center justify-center mb-4">
          <Sparkles className="w-8 h-8 text-red-400" />
        </div>
        <h2 className="text-display-sm text-zinc-300 mb-2">Something went wrong</h2>
        <p className="text-body-md text-zinc-500 mb-6 max-w-md">
          We couldn't load your pursuits. Please try refreshing the page.
        </p>
        <Button
          onClick={() => window.location.reload()}
          className="bg-inde-500 hover:bg-inde-600"
        >
          Refresh Page
        </Button>
      </div>
    );
  }

  // Empty state for new users
  if (pursuits.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
          className="w-24 h-24 rounded-3xl bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center mb-6 shadow-glow-inde"
        >
          <Sparkles className="w-12 h-12 text-white" />
        </motion.div>

        <h1 className="text-display-lg inde-gradient-text mb-4">
          Welcome to InDE
        </h1>
        <p className="text-body-lg text-zinc-400 mb-8 max-w-md">
          Your AI-powered innovation coach is ready to help you transform ideas
          into validated innovations. Start your first pursuit to begin.
        </p>

        <Button
          size="lg"
          onClick={() => navigate('/pursuit/new')}
          className="gap-2 bg-gradient-to-r from-blue-500 to-violet-500 hover:from-blue-600 hover:to-violet-600"
        >
          <Plus className="w-5 h-5" />
          Start Your First Pursuit
        </Button>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-display-lg text-zinc-200 mb-2">
            Welcome back, {userName}
          </h1>
          <p className="text-body-lg text-zinc-500">
            {activePursuits.length > 0
              ? `You have ${activePursuits.length} active pursuit${activePursuits.length > 1 ? 's' : ''}`
              : 'Ready to start something new?'}
          </p>
        </motion.div>

        {/* Quick stats */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-surface-2 border border-surface-border rounded-panel p-4"
          >
            <div className="text-display-md text-inde-400">{activePursuits.length}</div>
            <div className="text-caption text-zinc-500">Active</div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="bg-surface-2 border border-surface-border rounded-panel p-4"
          >
            <div className="text-display-md text-emerald-400">{completedPursuits.length}</div>
            <div className="text-caption text-zinc-500">Completed</div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-surface-2 border border-surface-border rounded-panel p-4"
          >
            <div className="text-display-md text-zinc-500">{archivedPursuits.length}</div>
            <div className="text-caption text-zinc-500">Archived</div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            className="bg-surface-2 border border-surface-border rounded-panel p-4"
          >
            <div className="text-display-md text-zinc-400">{pursuits.length}</div>
            <div className="text-caption text-zinc-500">Total</div>
          </motion.div>
        </div>

        {/* Active pursuits */}
        {activePursuits.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-display-sm text-zinc-300">Active Pursuits</h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/pursuit/new')}
                className="gap-1.5 text-inde-400"
              >
                <Plus className="w-4 h-4" />
                New Pursuit
              </Button>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              {activePursuits.map((pursuit, index) => (
                <PursuitCard key={pursuit.id} pursuit={pursuit} index={index} onArchived={handleArchived} />
              ))}
            </div>
          </div>
        )}

        {/* Archived/Abandoned pursuits */}
        {archivedPursuits.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <Archive className="w-4 h-4 text-zinc-500" />
              <h2 className="text-display-sm text-zinc-500">Archived Pursuits</h2>
              <span className="text-caption text-zinc-600">({archivedPursuits.length})</span>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {archivedPursuits.map((pursuit, index) => (
                <ArchivedPursuitCard key={pursuit.id} pursuit={pursuit} index={index} onRestored={handleArchived} />
              ))}
            </div>
          </div>
        )}

        {/* Start new pursuit CTA (when pursuits exist) */}
        {activePursuits.length === 0 && pursuits.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-surface-2 border border-surface-border rounded-panel p-6 text-center"
          >
            <h3 className="text-display-sm text-zinc-300 mb-2">
              Ready for your next pursuit?
            </h3>
            <p className="text-body-md text-zinc-500 mb-4">
              All your previous pursuits are complete. Start a new innovation journey.
            </p>
            <Button
              onClick={() => navigate('/pursuit/new')}
              className="gap-2 bg-inde-500 hover:bg-inde-600"
            >
              <Plus className="w-4 h-4" />
              Start New Pursuit
            </Button>
          </motion.div>
        )}
      </div>
    </div>
  );
}

function PursuitCard({ pursuit, index, onArchived }) {
  const navigate = useNavigate();
  const emoji = ARCHETYPE_EMOJIS[pursuit.archetype] || '✨';
  const healthZone = pursuit.health_zone || pursuit.healthZone;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 + index * 0.05 }}
      className="w-full bg-surface-2 border border-surface-border rounded-panel p-5 text-left hover:border-inde-500/30 hover:bg-surface-3 transition-all group"
    >
      <div className="flex items-start gap-4">
        {/* Archetype icon */}
        <button
          onClick={() => navigate(`/pursuit/${pursuit.id}`)}
          className="text-3xl flex-shrink-0 hover:scale-110 transition-transform"
        >
          {emoji}
        </button>

        {/* Content */}
        <div
          className="flex-1 min-w-0 cursor-pointer"
          onClick={() => navigate(`/pursuit/${pursuit.id}`)}
        >
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-body-lg font-medium text-zinc-200 truncate">
              {pursuit.name}
            </h3>
            <ArrowRight className="w-4 h-4 text-zinc-600 opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>

          {/* Phase and health */}
          <div className="flex items-center gap-3 mb-2">
            <PhaseBadge phase={pursuit.phase} size="small" />
            {healthZone && (
              <HealthIndicator
                score={pursuit.health_score}
                zone={healthZone}
                size="small"
              />
            )}
          </div>

          {/* v3.16: GII identifier */}
          {pursuit.gii_id && (
            <div className="flex items-center gap-1.5 mb-3">
              <Fingerprint className="w-3 h-3 text-zinc-500" />
              <span className="text-caption text-zinc-500 font-mono">{pursuit.gii_id}</span>
            </div>
          )}

          {/* Spark description */}
          {pursuit.spark_description && (
            <p className="text-body-sm text-zinc-500 line-clamp-2 mb-3">
              {pursuit.spark_description}
            </p>
          )}

          {/* Last activity */}
          {pursuit.updated_at && (
            <p className="text-caption text-zinc-600">
              Last activity{' '}
              {formatDistanceToNow(new Date(pursuit.updated_at), { addSuffix: true })}
            </p>
          )}
        </div>

        {/* v3.13: Action buttons */}
        <div className="flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <ExportButton
            pursuitId={pursuit.id}
            pursuitTitle={pursuit.name}
            variant="ghost"
            size="icon"
            showLabel={false}
          />
          <ArchiveButton
            pursuitId={pursuit.id}
            isArchived={false}
            onArchive={onArchived}
          />
        </div>
      </div>
    </motion.div>
  );
}

function ArchivedPursuitCard({ pursuit, index, onRestored }) {
  const navigate = useNavigate();
  const emoji = ARCHETYPE_EMOJIS[pursuit.archetype] || '✨';

  // Determine status badge
  const statusConfig = {
    ARCHIVED: { label: 'Archived', color: 'text-zinc-500 bg-zinc-500/10' },
    ABANDONED: { label: 'Abandoned', color: 'text-amber-500 bg-amber-500/10' },
    DELETED: { label: 'Deleted', color: 'text-red-500 bg-red-500/10' },
  };
  const status = statusConfig[pursuit.state] || statusConfig.ARCHIVED;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 + index * 0.05 }}
      className="w-full bg-surface-2/50 border border-surface-border/50 rounded-panel p-4 text-left hover:border-zinc-600 hover:bg-surface-2 transition-all group opacity-75 hover:opacity-100"
    >
      <div className="flex items-start gap-3">
        {/* Archetype icon */}
        <button
          onClick={() => navigate(`/pursuit/${pursuit.id}`)}
          className="text-2xl flex-shrink-0 grayscale hover:grayscale-0 transition-all"
        >
          {emoji}
        </button>

        {/* Content */}
        <div
          className="flex-1 min-w-0 cursor-pointer"
          onClick={() => navigate(`/pursuit/${pursuit.id}`)}
        >
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-body-md font-medium text-zinc-400 truncate">
              {pursuit.name}
            </h3>
            <span className={cn('text-caption px-1.5 py-0.5 rounded', status.color)}>
              {status.label}
            </span>
          </div>

          {/* Last activity */}
          {pursuit.updated_at && (
            <p className="text-caption text-zinc-600">
              {formatDistanceToNow(new Date(pursuit.updated_at), { addSuffix: true })}
            </p>
          )}
        </div>

        {/* v3.13: Action buttons */}
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <ExportButton
            pursuitId={pursuit.id}
            pursuitTitle={pursuit.name}
            variant="ghost"
            size="icon"
            showLabel={false}
          />
          <ArchiveButton
            pursuitId={pursuit.id}
            isArchived={true}
            onRestore={onRestored}
          />
        </div>
      </div>
    </motion.div>
  );
}
