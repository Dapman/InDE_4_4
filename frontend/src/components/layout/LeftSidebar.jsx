import { useState, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useUIStore } from '../../stores/uiStore';
import { usePursuitStore } from '../../stores/pursuitStore';
import { useAuthStore } from '../../stores/authStore';
import { pursuitsApi } from '../../api/pursuits';
import { discoveryApi } from '../../api/discovery';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';
import { HealthDot } from '../coaching/HealthIndicator';
import { GettingStartedChecklist } from '../discovery';
import {
  Home,
  Briefcase,
  Building2,
  BarChart3,
  Sparkles,
  Globe,
  Settings,
  Plus,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  Rocket,
  Shield,
  Hammer,
  Flag,
  Check,
  X,
  Activity,
} from 'lucide-react';
import { cn } from '../../lib/utils';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: Home, path: '/' },
  { id: 'portfolio', label: 'Portfolio', icon: Briefcase, path: '/portfolio' },
  { id: 'org-portfolio', label: 'Org Portfolio', icon: Building2, path: '/org/portfolio', requiresOrg: true },
  { id: 'analytics', label: 'Analytics', icon: BarChart3, path: '/analytics' },
  { id: 'ems', label: 'EMS', icon: Sparkles, path: '/ems' },
  { id: 'ikf', label: 'IKF', icon: Globe, path: '/ikf' },
  { id: 'settings', label: 'Settings', icon: Settings, path: '/settings' },
  // v3.14: Admin-only diagnostics
  { id: 'diagnostics', label: 'Diagnostics', icon: Activity, path: '/diagnostics', requiresAdmin: true },
];

const PHASE_CONFIG = {
  VISION: { icon: Lightbulb, color: 'bg-phase-vision', label: 'Vision' },
  PITCH: { icon: Rocket, color: 'bg-phase-pitch', label: 'Pitch' },
  DE_RISK: { icon: Shield, color: 'bg-phase-derisk', label: 'De-Risk' },
  BUILD: { icon: Hammer, color: 'bg-phase-build', label: 'Build' },
  DEPLOY: { icon: Flag, color: 'bg-phase-deploy', label: 'Deploy' },
};

const ARCHETYPE_EMOJIS = {
  lean_startup: '🔬',
  design_thinking: '🎨',
  stage_gate: '🏗️',
  triz: '🧩',
  blue_ocean: '🌊',
  freeform: '✨',
};

export function LeftSidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { leftSidebarOpen, leftSidebarWidth, toggleLeftSidebarWidth } = useUIStore();
  const { activePursuitId, setActivePursuit, setPursuitList } = usePursuitStore();
  const user = useAuthStore((s) => s.user);
  const [completedExpanded, setCompletedExpanded] = useState(false);

  const isCollapsed = leftSidebarWidth === 'collapsed';

  // Check if user has org access
  const hasOrgAccess = user?.org_id && (user?.role === 'org_admin' || user?.role === 'org_member' || user?.is_enterprise);

  // Check if user is admin
  const isAdmin = user?.role === 'admin';

  // Filter nav items based on user permissions
  const visibleNavItems = useMemo(() => {
    return NAV_ITEMS.filter((item) => {
      if (item.requiresOrg && !hasOrgAccess) return false;
      if (item.requiresAdmin && !isAdmin) return false;
      return true;
    });
  }, [hasOrgAccess, isAdmin]);

  // Fetch pursuits with React Query
  const { data: pursuits = [] } = useQuery({
    queryKey: ['pursuits'],
    queryFn: async () => {
      const response = await pursuitsApi.list();
      const rawList = response.data.pursuits || response.data || [];
      // Map backend field names to frontend expected names
      const list = rawList.map((p) => ({
        id: p.pursuit_id || p.id,
        name: p.title || p.name,
        state: (p.status || p.state || 'active').toUpperCase(),
        phase: p.phase || 'VISION',
        archetype: p.archetype || p.methodology || 'freeform',
        health_zone: p.health_zone || p.healthZone,
        health_score: p.health_score || p.healthScore,
        spark_description: p.description || p.spark_description,
        updated_at: p.updated_at || p.updatedAt,
      }));
      setPursuitList(list);
      return list;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Get auth token to check if user is authenticated
  const token = useAuthStore((s) => s.token);

  // v3.15: Fetch user discovery state for Getting Started checklist
  const { data: discoveryState } = useQuery({
    queryKey: ['discovery-state', token],
    queryFn: async () => {
      try {
        const response = await discoveryApi.getState();
        return response.data;
      } catch (e) {
        // Return defaults if not authenticated or error
        console.warn('Discovery state fetch failed:', e);
        return { checklist_complete: false, dismissed_hints: [], checklist_items: {} };
      }
    },
    enabled: !!token, // Only fetch when authenticated
    refetchInterval: 60000, // Refresh every minute
    staleTime: 30000,
  });

  const activePursuits = pursuits.filter(
    (p) => p.state === 'ACTIVE' || p.state === 'PENDING'
  );
  const completedPursuits = pursuits.filter(
    (p) => p.state === 'COMPLETED' || p.state === 'ARCHIVED' || p.state === 'TERMINATED'
  );

  if (!leftSidebarOpen) {
    return null;
  }

  const handleNewPursuit = () => {
    navigate('/pursuit/new');
  };

  const handleSelectPursuit = (pursuit) => {
    setActivePursuit(pursuit.id);
    navigate(`/pursuit/${pursuit.id}`);
  };

  const NavButton = ({ item, isActive }) => {
    const Icon = item.icon;

    if (isCollapsed) {
      return (
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={() => navigate(item.path)}
                className={cn(
                  'w-10 h-10 flex items-center justify-center rounded-lg transition-colors',
                  isActive
                    ? 'bg-inde-500/10 text-inde-400'
                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-surface-4'
                )}
              >
                <Icon className="h-5 w-5" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="right">{item.label}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }

    return (
      <button
        onClick={() => navigate(item.path)}
        className={cn(
          'w-full h-9 flex items-center gap-3 px-3 rounded-lg transition-colors text-body-sm',
          isActive
            ? 'bg-inde-500/10 text-inde-400'
            : 'text-zinc-400 hover:text-zinc-200 hover:bg-surface-4'
        )}
      >
        <Icon className="h-4 w-4 flex-shrink-0" />
        <span className="truncate">{item.label}</span>
      </button>
    );
  };

  const PursuitItem = ({ pursuit, isActive }) => {
    const phaseConfig = PHASE_CONFIG[pursuit.phase] || PHASE_CONFIG.VISION;
    const emoji = ARCHETYPE_EMOJIS[pursuit.archetype] || '✨';
    const healthZone = pursuit.health_zone || pursuit.healthZone;

    if (isCollapsed) {
      return (
        <TooltipProvider key={pursuit.id} delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={() => handleSelectPursuit(pursuit)}
                className={cn(
                  'w-10 h-10 flex items-center justify-center rounded-lg transition-all mx-auto',
                  isActive
                    ? 'bg-surface-5 ring-2 ring-inde-500/50 shadow-glow-inde'
                    : 'hover:bg-surface-4'
                )}
              >
                <span className="text-lg">{emoji}</span>
              </button>
            </TooltipTrigger>
            <TooltipContent side="right">
              <div className="flex items-center gap-2">
                <span>{pursuit.name}</span>
                {healthZone && <HealthDot zone={healthZone} />}
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }

    return (
      <button
        onClick={() => handleSelectPursuit(pursuit)}
        className={cn(
          'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left group',
          isActive
            ? 'bg-surface-4 ring-1 ring-inde-500/30 shadow-glow-inde'
            : 'hover:bg-surface-4'
        )}
      >
        {/* Archetype emoji */}
        <span className="text-lg flex-shrink-0">{emoji}</span>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p
              className={cn(
                'text-body-sm truncate',
                isActive ? 'text-zinc-200 font-medium' : 'text-zinc-400'
              )}
            >
              {pursuit.name}
            </p>
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            {/* Phase */}
            <span className={cn('text-caption text-zinc-600')}>
              {phaseConfig.label}
            </span>
            {/* Health dot */}
            {healthZone && (
              <>
                <span className="text-zinc-700">·</span>
                <HealthDot zone={healthZone} />
                {pursuit.health_score !== undefined && (
                  <span className="text-caption text-zinc-600">
                    {Math.round(pursuit.health_score)}
                  </span>
                )}
              </>
            )}
          </div>
        </div>
      </button>
    );
  };

  const CompletedPursuitItem = ({ pursuit }) => {
    const isCompleted = pursuit.state === 'COMPLETED';
    const isTerminated = pursuit.state === 'TERMINATED';

    if (isCollapsed) {
      return (
        <TooltipProvider key={pursuit.id} delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={() => handleSelectPursuit(pursuit)}
                className="w-10 h-10 flex items-center justify-center rounded-lg transition-colors mx-auto text-zinc-600 hover:bg-surface-4"
              >
                {isCompleted ? (
                  <Check className="w-4 h-4 text-emerald-500" />
                ) : isTerminated ? (
                  <X className="w-4 h-4 text-rose-500" />
                ) : (
                  <span className="text-xs">A</span>
                )}
              </button>
            </TooltipTrigger>
            <TooltipContent side="right">{pursuit.name}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }

    return (
      <button
        onClick={() => handleSelectPursuit(pursuit)}
        className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg transition-colors text-left hover:bg-surface-4"
      >
        {isCompleted ? (
          <Check className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
        ) : isTerminated ? (
          <X className="w-3.5 h-3.5 text-rose-500 flex-shrink-0" />
        ) : (
          <span className="w-3.5 h-3.5 flex-shrink-0" />
        )}
        <span className="text-body-sm text-zinc-600 truncate">{pursuit.name}</span>
      </button>
    );
  };

  return (
    <aside
      className={cn(
        'h-full bg-surface-2 border-r border-surface-border flex flex-col transition-all duration-200 ease-out',
        'hidden sm:flex', // Hide on mobile, show on sm and up
        isCollapsed ? 'w-sidebar-collapsed' : 'w-sidebar-expanded'
      )}
    >
      {/* Pursuits Section */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {/* Header */}
        <div
          className={cn(
            'flex items-center justify-between border-b border-surface-border',
            isCollapsed ? 'p-2' : 'px-3 py-2'
          )}
        >
          {!isCollapsed && (
            <span className="text-overline text-zinc-500 uppercase">Pursuits</span>
          )}
          <TooltipProvider delayDuration={0}>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleNewPursuit}
                  className={cn(
                    'text-zinc-500 hover:text-inde-400 hover:bg-inde-500/10',
                    isCollapsed ? 'h-8 w-8' : 'h-6 w-6'
                  )}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side={isCollapsed ? 'right' : 'bottom'}>
                New Pursuit
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>

        <ScrollArea className="flex-1">
          <div className={cn('space-y-1', isCollapsed ? 'p-2' : 'p-2')}>
            {/* Active pursuits */}
            {activePursuits.map((pursuit) => (
              <PursuitItem
                key={pursuit.id}
                pursuit={pursuit}
                isActive={pursuit.id === activePursuitId}
              />
            ))}

            {/* Empty state */}
            {activePursuits.length === 0 && (
              <div
                className={cn(
                  'text-center py-4',
                  isCollapsed ? 'px-1' : 'px-3'
                )}
              >
                {!isCollapsed && (
                  <>
                    <p className="text-caption text-zinc-600 mb-2">
                      No active pursuits
                    </p>
                    <Button
                      size="sm"
                      onClick={handleNewPursuit}
                      className="w-full bg-inde-500/20 text-inde-400 hover:bg-inde-500/30"
                    >
                      <Plus className="w-3.5 h-3.5 mr-1" />
                      Start One
                    </Button>
                  </>
                )}
              </div>
            )}

            {/* Completed pursuits section */}
            {completedPursuits.length > 0 && (
              <div className="pt-2 mt-2 border-t border-surface-border">
                {!isCollapsed && (
                  <button
                    onClick={() => setCompletedExpanded(!completedExpanded)}
                    className="w-full flex items-center justify-between px-3 py-1.5 text-caption text-zinc-600 hover:text-zinc-400 transition-colors"
                  >
                    <span>Completed ({completedPursuits.length})</span>
                    {completedExpanded ? (
                      <ChevronUp className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5" />
                    )}
                  </button>
                )}

                {(completedExpanded || isCollapsed) && (
                  <div className="space-y-0.5 mt-1">
                    {completedPursuits.slice(0, isCollapsed ? 3 : undefined).map((pursuit) => (
                      <CompletedPursuitItem key={pursuit.id} pursuit={pursuit} />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </ScrollArea>

        {/* v3.15: Getting Started Checklist */}
        {/* v4.4.1 FIX: flex-shrink-0 ensures checklist is not hidden by Navigation Items */}
        {activePursuits.length > 0 && !discoveryState?.checklist_complete && (
          <div className="flex-shrink-0 overflow-y-auto max-h-[220px]">
            <GettingStartedChecklist
              discoveryState={discoveryState}
              isCollapsed={isCollapsed}
            />
          </div>
        )}
      </div>

      {/* Navigation Items */}
      <div className={cn('border-t border-surface-border', isCollapsed ? 'p-2' : 'p-2')}>
        <div className="space-y-1">
          {visibleNavItems.map((item) => (
            <NavButton
              key={item.id}
              item={item}
              isActive={
                item.path === '/'
                  ? location.pathname === '/'
                  : location.pathname.startsWith(item.path)
              }
            />
          ))}
        </div>
      </div>

      {/* Collapse Toggle */}
      <div className="p-2 border-t border-surface-border">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleLeftSidebarWidth}
          className="w-full h-8 text-zinc-500 hover:text-zinc-300"
        >
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>
    </aside>
  );
}

export default LeftSidebar;
