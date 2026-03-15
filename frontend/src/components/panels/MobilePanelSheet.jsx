import {
  ClipboardList,
  FileText,
  Heart,
  Clock,
  GitMerge,
  Users,
  X,
} from 'lucide-react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../ui/sheet';
import { useUIStore } from '../../stores/uiStore';
import { usePursuitStore } from '../../stores/pursuitStore';
import { useCoachingStore } from '../../stores/coachingStore';
import { cn } from '../../lib/utils';

// Panel components
import { ScaffoldingPanel } from './ScaffoldingPanel';
import { ArtifactsPanel } from './ArtifactsPanel';
import { HealthPanel } from './HealthPanel';
import { TimelinePanel } from './TimelinePanel';
import { ConvergencePanel } from './ConvergencePanel';
import { TeamPanel } from './TeamPanel';

// Mobile panel tabs
const MOBILE_TABS = [
  { id: 'scaffold', icon: ClipboardList, label: 'Scaffold' },
  { id: 'artifacts', icon: FileText, label: 'Artifacts' },
  { id: 'health', icon: Heart, label: 'Health' },
  { id: 'timeline', icon: Clock, label: 'Timeline' },
  { id: 'convergence', icon: GitMerge, label: 'Converge' },
  { id: 'team', icon: Users, label: 'Team' },
];

/**
 * MobilePanelSheet - Bottom sheet for panel access on mobile devices.
 */
export function MobilePanelSheet() {
  const mobilePanelOpen = useUIStore((s) => s.mobilePanelOpen);
  const mobilePanelTab = useUIStore((s) => s.mobilePanelTab);
  const closeMobilePanel = useUIStore((s) => s.closeMobilePanel);
  const openMobilePanel = useUIStore((s) => s.openMobilePanel);

  const pursuitList = usePursuitStore((s) => s.pursuitList);
  const activePursuitId = usePursuitStore((s) => s.activePursuitId);
  const pursuit = pursuitList.find((p) => p.id === activePursuitId);

  const handleTabClick = (tabId) => {
    openMobilePanel(tabId);
  };

  // Handler to send a message to the coaching chat
  const handleSendMessage = (message) => {
    useCoachingStore.getState().sendMessage(message);
    closeMobilePanel(); // Close panel after sending
  };

  const renderPanelContent = () => {
    if (!pursuit?.id) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center p-6">
          <p className="text-body-sm text-zinc-500">
            Select a pursuit to view panel
          </p>
        </div>
      );
    }

    switch (mobilePanelTab) {
      case 'scaffold':
        return <ScaffoldingPanel pursuitId={pursuit.id} onSendMessage={handleSendMessage} />;
      case 'artifacts':
        return <ArtifactsPanel pursuitId={pursuit.id} />;
      case 'health':
        return <HealthPanel pursuitId={pursuit.id} onSendMessage={handleSendMessage} />;
      case 'timeline':
        return <TimelinePanel pursuitId={pursuit.id} />;
      case 'convergence':
        return <ConvergencePanel pursuitId={pursuit.id} onSendMessage={handleSendMessage} />;
      case 'team':
        return <TeamPanel pursuitId={pursuit.id} onSendMessage={handleSendMessage} />;
      default:
        return <ScaffoldingPanel pursuitId={pursuit.id} onSendMessage={handleSendMessage} />;
    }
  };

  const activeTab = MOBILE_TABS.find((t) => t.id === mobilePanelTab) || MOBILE_TABS[0];

  return (
    <Sheet open={mobilePanelOpen} onOpenChange={(open) => !open && closeMobilePanel()}>
      <SheetContent side="bottom" className="h-[70vh] flex flex-col p-0">
        <SheetHeader className="flex-shrink-0 px-4 py-3 border-b border-surface-border">
          <div className="flex items-center justify-between">
            <SheetTitle className="flex items-center gap-2 text-body-sm font-medium text-zinc-300">
              <activeTab.icon className="h-4 w-4 text-inde-400" />
              {activeTab.label}
            </SheetTitle>
            <button
              onClick={closeMobilePanel}
              className="p-1.5 hover:bg-surface-3 rounded transition-colors"
            >
              <X className="h-4 w-4 text-zinc-500" />
            </button>
          </div>

          {/* Tab selector */}
          <div className="flex gap-1 mt-3 overflow-x-auto pb-1 -mx-4 px-4">
            {MOBILE_TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => handleTabClick(tab.id)}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-caption whitespace-nowrap transition-colors',
                  mobilePanelTab === tab.id
                    ? 'bg-inde-500/20 text-inde-400'
                    : 'bg-surface-3 text-zinc-500 hover:text-zinc-300'
                )}
              >
                <tab.icon className="h-3.5 w-3.5" />
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </SheetHeader>

        {/* Panel content */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {renderPanelContent()}
        </div>
      </SheetContent>
    </Sheet>
  );
}

export default MobilePanelSheet;
