import { useUIStore } from '../../stores/uiStore';
import { usePursuitStore } from '../../stores/pursuitStore';
import { useCoachingStore } from '../../stores/coachingStore';
import { Button } from '../ui/button';
import { X, Lightbulb, PanelRightClose } from 'lucide-react';
import { PanelContainer } from '../panels/PanelContainer';

/**
 * RightSidebar - Intelligence Panel with tabbed contextual panels.
 * Shows Scaffolding, Artifacts, Health, Timeline, Convergence, and Team panels.
 */
export function RightSidebar() {
  const { toggleRightSidebar } = useUIStore();
  const pursuitList = usePursuitStore((s) => s.pursuitList);
  const activePursuitId = usePursuitStore((s) => s.activePursuitId);

  // Get the active pursuit data
  const activePursuit = pursuitList.find((p) => p.id === activePursuitId);

  // Handler to send a message to the coaching chat
  const handleSendMessage = (message) => {
    // Use the store's sendMessage which triggers the actual send through ChatContainer
    useCoachingStore.getState().sendMessage(message);
  };

  return (
    <aside className="w-sidebar-wide h-full bg-surface-2 border-l border-surface-border flex flex-col animate-slide-in-right">
      {/* Header */}
      <div className="h-12 flex items-center justify-between px-4 border-b border-surface-border flex-shrink-0">
        <div className="flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-inde-400" />
          <span className="text-body-sm font-medium">Intelligence</span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleRightSidebar}
          className="h-7 w-7 text-zinc-500 hover:text-zinc-300"
          title="Close panel (⌘])"
        >
          <PanelRightClose className="h-4 w-4" />
        </Button>
      </div>

      {/* Panel content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <PanelContainer
          pursuit={activePursuit}
          onSendMessage={handleSendMessage}
        />
      </div>
    </aside>
  );
}

export default RightSidebar;
