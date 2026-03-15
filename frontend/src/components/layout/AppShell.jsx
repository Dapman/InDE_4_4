import { useEffect, useMemo } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { useUIStore } from '../../stores/uiStore';
import { usePursuitStore } from '../../stores/pursuitStore';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcut';
import { TopBar } from './TopBar';
import { LeftSidebar } from './LeftSidebar';
import { RightSidebar } from './RightSidebar';
import { StatusBar } from './StatusBar';
import { CommandPalette } from '../CommandPalette';
import { MobilePanelSheet, MobilePanelBar } from '../panels';
import { cn } from '../../lib/utils';

/**
 * AppShell - The 5-zone layout container.
 *
 * ┌──────────────────────────────────────────────────────────┐
 * │                    TOP BAR (Zone 1)                       │
 * ├───────────┬──────────────────────────────────┬───────────────┤
 * │   LEFT    │     WORK CANVAS              │    RIGHT      │
 * │  SIDEBAR  │       (Zone 3)               │   SIDEBAR     │
 * │  (Zone 2) │                              │   (Zone 4)    │
 * │           │    <Outlet /> renders        │               │
 * │           │    active page here          │               │
 * ├───────────┴──────────────────────────────┴───────────────┤
 * │                  STATUS BAR (Zone 5)                      │
 * └──────────────────────────────────────────────────────────┘
 */
export function AppShell() {
  const navigate = useNavigate();
  const {
    leftSidebarOpen,
    rightSidebarOpen,
    leftSidebarWidth,
    commandPaletteOpen,
    toggleLeftSidebar,
    toggleRightSidebar,
    toggleCommandPalette,
    setCommandPaletteOpen,
    initializeTheme,
  } = useUIStore();

  const { pursuitList, setActivePursuit } = usePursuitStore();

  // Get active pursuits for shortcuts
  const activePursuits = useMemo(
    () => pursuitList.filter((p) => p.state === 'ACTIVE' || p.state === 'PENDING'),
    [pursuitList]
  );

  // Initialize theme on mount
  useEffect(() => {
    initializeTheme();
  }, [initializeTheme]);

  // Auto-collapse sidebar on smaller screens
  useEffect(() => {
    const handleResize = () => {
      const isMobile = window.innerWidth < 768;
      const isTablet = window.innerWidth >= 768 && window.innerWidth < 1024;

      if (isMobile) {
        // Hide sidebars on mobile
        useUIStore.getState().leftSidebarWidth = 'collapsed';
      } else if (isTablet) {
        // Collapse to icons on tablet
        useUIStore.getState().leftSidebarWidth = 'collapsed';
      }
    };

    // Check on mount
    handleResize();

    // Listen for resize
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Build dynamic shortcuts for pursuit switching
  const shortcuts = useMemo(() => {
    const baseShortcuts = [
      { key: 'k', modifiers: { meta: true }, callback: toggleCommandPalette },
      { key: '\\', modifiers: { meta: true }, callback: toggleLeftSidebar },
      { key: ']', modifiers: { meta: true }, callback: toggleRightSidebar },
      { key: 'Escape', callback: () => setCommandPaletteOpen(false) },
      // New pursuit shortcut
      {
        key: 'n',
        modifiers: { meta: true },
        callback: () => navigate('/pursuit/new'),
      },
    ];

    // Add pursuit switching shortcuts (⌘1-9)
    const pursuitShortcuts = activePursuits.slice(0, 9).map((pursuit, index) => ({
      key: String(index + 1),
      modifiers: { meta: true },
      callback: () => {
        setActivePursuit(pursuit.id);
        navigate(`/pursuit/${pursuit.id}`);
      },
    }));

    return [...baseShortcuts, ...pursuitShortcuts];
  }, [
    toggleCommandPalette,
    toggleLeftSidebar,
    toggleRightSidebar,
    setCommandPaletteOpen,
    navigate,
    activePursuits,
    setActivePursuit,
  ]);

  // Register keyboard shortcuts
  useKeyboardShortcuts(shortcuts);

  return (
    <div className="h-screen flex flex-col bg-surface-1 overflow-hidden">
      {/* Zone 1: Top Bar */}
      <TopBar />

      {/* Main content area: Zones 2, 3, 4 */}
      <div className="flex-1 flex overflow-hidden">
        {/* Zone 2: Left Sidebar */}
        <LeftSidebar />

        {/* Zone 3: Work Canvas */}
        <main
          className={cn(
            'flex-1 min-h-0 overflow-y-auto transition-all duration-200 ease-out',
            'bg-surface-1'
          )}
        >
          <Outlet />
        </main>

        {/* Zone 4: Right Sidebar */}
        {rightSidebarOpen && <RightSidebar />}
      </div>

      {/* Zone 5: Status Bar */}
      <StatusBar />

      {/* Command Palette Modal */}
      <CommandPalette
        open={commandPaletteOpen}
        onOpenChange={setCommandPaletteOpen}
      />

      {/* Mobile Panel Sheet */}
      <MobilePanelSheet />

      {/* Mobile Panel Bar - bottom action bar for mobile */}
      <MobilePanelBar />
    </div>
  );
}

export default AppShell;
