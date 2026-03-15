import { useMemo, useCallback } from 'react';
import {
  ClipboardList,
  FileText,
  Heart,
  Clock,
  GitMerge,
  Users,
  Brain,
  Globe,
  Upload,
  Eye,
  Shield,
} from 'lucide-react';
import { useUIStore } from '../../stores/uiStore';
import { cn } from '../../lib/utils';

// Panel components
import { ScaffoldingPanel } from './ScaffoldingPanel';
import { ArtifactsPanel } from './ArtifactsPanel';
import { HealthPanel } from './HealthPanel';
import { TimelinePanel } from './TimelinePanel';
import { ConvergencePanel } from './ConvergencePanel';
import { TeamPanel } from './TeamPanel';
import { IntelligencePanel } from './IntelligencePanel';
import { FederationPanel } from './FederationPanel';
import { ContributionPanel } from './ContributionPanel';
import { EMSPanel } from './EMSPanel';
import { RVEPanel } from './RVEPanel';

// Panel tab configuration with conditional visibility
const PANEL_TABS = [
  { id: 'scaffold', icon: ClipboardList, label: 'Scaffold', always: true },
  { id: 'artifacts', icon: FileText, label: 'Artifacts', always: true },
  { id: 'health', icon: Heart, label: 'Health', always: true },
  { id: 'rve', icon: Shield, label: 'RVE', always: true },
  { id: 'timeline', icon: Clock, label: 'Timeline', always: true },
  { id: 'convergence', icon: GitMerge, label: 'Converge', always: true },
  { id: 'team', icon: Users, label: 'Team', always: true },
  { id: 'intelligence', icon: Brain, label: 'Intel', always: true },
  { id: 'federation', icon: Globe, label: 'Federation', always: true },
  { id: 'contributions', icon: Upload, label: 'Contrib', always: true },
  { id: 'ems', icon: Eye, label: 'EMS', always: true },
];

/**
 * PanelContainer - Tabbed panel container for the right sidebar.
 * Renders different contextual panels based on active pursuit state.
 *
 * @param {Object} pursuit - Active pursuit data
 * @param {string} pursuit.id - Pursuit ID
 * @param {boolean} pursuit.tim_enabled - Whether TIM timeline is enabled
 * @param {boolean} pursuit.convergence_active - Whether convergence tracking is active
 * @param {Array} pursuit.team - Team members array (for team panel visibility)
 * @param {Function} onSendMessage - Callback to send message to chat
 */
export function PanelContainer({ pursuit, onSendMessage }) {
  // Use uiStore for persistent tab state
  const activeTab = useUIStore((s) => s.activePanelTab);
  const notifications = useUIStore((s) => s.panelNotifications);
  const setActiveTab = useUIStore((s) => s.setActivePanelTab);
  const addNotification = useUIStore((s) => s.addPanelNotification);

  // Filter visible tabs based on pursuit context
  const visibleTabs = useMemo(() => {
    return PANEL_TABS.filter(
      (tab) => tab.always || (tab.condition && tab.condition(pursuit))
    );
  }, [pursuit]);

  // Ensure active tab is visible; fallback to first tab if not
  const effectiveActiveTab = useMemo(() => {
    const isActiveTabVisible = visibleTabs.some((tab) => tab.id === activeTab);
    return isActiveTabVisible ? activeTab : visibleTabs[0]?.id || 'scaffold';
  }, [activeTab, visibleTabs]);

  // Handle tab change (notification clearing is handled by the store)
  const handleTabChange = useCallback((tabId) => {
    setActiveTab(tabId);
  }, [setActiveTab]);

  // Wrapper for panel notification callbacks
  const handleDataChange = useCallback((tabId) => {
    addNotification(tabId);
  }, [addNotification]);

  // Render panel content based on active tab
  const renderPanelContent = () => {
    if (!pursuit?.id) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center p-6">
          <p className="text-body-sm text-zinc-500">
            Select a pursuit to view contextual intelligence
          </p>
        </div>
      );
    }

    switch (effectiveActiveTab) {
      case 'scaffold':
        return (
          <ScaffoldingPanel
            pursuitId={pursuit.id}
            onSendMessage={onSendMessage}
            onDataChange={() => handleDataChange('scaffold')}
          />
        );
      case 'artifacts':
        return (
          <ArtifactsPanel
            pursuitId={pursuit.id}
            onDataChange={() => handleDataChange('artifacts')}
          />
        );
      case 'health':
        return (
          <HealthPanel
            pursuitId={pursuit.id}
            onSendMessage={onSendMessage}
            onDataChange={() => handleDataChange('health')}
          />
        );
      case 'rve':
        return (
          <RVEPanel
            pursuitId={pursuit.id}
            onSendMessage={onSendMessage}
            onDataChange={() => handleDataChange('rve')}
          />
        );
      case 'timeline':
        return (
          <TimelinePanel
            pursuitId={pursuit.id}
            onDataChange={() => handleDataChange('timeline')}
          />
        );
      case 'convergence':
        return (
          <ConvergencePanel
            pursuitId={pursuit.id}
            onSendMessage={onSendMessage}
            onDataChange={() => handleDataChange('convergence')}
          />
        );
      case 'team':
        return (
          <TeamPanel
            pursuitId={pursuit.id}
            onSendMessage={onSendMessage}
            onDataChange={() => handleDataChange('team')}
          />
        );
      case 'intelligence':
        return (
          <IntelligencePanel
            pursuitId={pursuit.id}
            onSendMessage={onSendMessage}
            onDataChange={() => handleDataChange('intelligence')}
          />
        );
      case 'federation':
        return (
          <FederationPanel
            pursuitId={pursuit.id}
            onDataChange={() => handleDataChange('federation')}
          />
        );
      case 'contributions':
        return (
          <ContributionPanel
            pursuitId={pursuit.id}
            onDataChange={() => handleDataChange('contributions')}
          />
        );
      case 'ems':
        return (
          <EMSPanel
            pursuitId={pursuit.id}
            onDataChange={() => handleDataChange('ems')}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex border-b border-surface-border overflow-x-auto scrollbar-none">
        {visibleTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={cn(
              'relative flex items-center gap-1.5 px-3 py-2.5 text-caption whitespace-nowrap transition-colors flex-shrink-0',
              effectiveActiveTab === tab.id
                ? 'text-inde-400 border-b-2 border-inde-500 -mb-px'
                : 'text-zinc-500 hover:text-zinc-300'
            )}
          >
            <tab.icon size={14} />
            <span>{tab.label}</span>
            {/* Notification dot */}
            {notifications[tab.id] && effectiveActiveTab !== tab.id && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-inde-500 rounded-full" />
            )}
          </button>
        ))}
      </div>

      {/* Panel content area */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {renderPanelContent()}
      </div>
    </div>
  );
}

export default PanelContainer;
