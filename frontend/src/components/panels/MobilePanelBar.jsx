import {
  ClipboardList,
  FileText,
  Heart,
  LayoutGrid,
} from 'lucide-react';
import { useUIStore } from '../../stores/uiStore';
import { usePursuitStore } from '../../stores/pursuitStore';
import { cn } from '../../lib/utils';

// Quick access tabs for mobile bottom bar
const QUICK_TABS = [
  { id: 'scaffold', icon: ClipboardList, label: 'Scaffold' },
  { id: 'artifacts', icon: FileText, label: 'Artifacts' },
  { id: 'health', icon: Heart, label: 'Health' },
];

/**
 * MobilePanelBar - Bottom action bar for quick panel access on mobile.
 * Only visible on mobile when a pursuit is active.
 */
export function MobilePanelBar() {
  const openMobilePanel = useUIStore((s) => s.openMobilePanel);
  const panelNotifications = useUIStore((s) => s.panelNotifications);
  const activePursuitId = usePursuitStore((s) => s.activePursuitId);

  // Don't render if no active pursuit
  if (!activePursuitId) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 md:hidden z-40">
      <div className="bg-surface-2 border-t border-surface-border px-2 py-2 safe-area-inset-bottom">
        <div className="flex items-center justify-around max-w-md mx-auto">
          {QUICK_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => openMobilePanel(tab.id)}
              className="relative flex flex-col items-center gap-1 px-4 py-2 rounded-lg hover:bg-surface-3 transition-colors"
            >
              <tab.icon className="h-5 w-5 text-zinc-400" />
              <span className="text-caption text-zinc-500">{tab.label}</span>
              {/* Notification dot */}
              {panelNotifications[tab.id] && (
                <span className="absolute top-1 right-3 w-2 h-2 bg-inde-500 rounded-full" />
              )}
            </button>
          ))}
          {/* More button for additional panels */}
          <button
            onClick={() => openMobilePanel('scaffold')}
            className="flex flex-col items-center gap-1 px-4 py-2 rounded-lg hover:bg-surface-3 transition-colors"
          >
            <LayoutGrid className="h-5 w-5 text-zinc-400" />
            <span className="text-caption text-zinc-500">More</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default MobilePanelBar;
