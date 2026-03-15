import { create } from 'zustand';
import { applyTheme, getSystemPreference } from '../lib/theme';

export const useUIStore = create((set, get) => ({
  // Theme
  theme: 'dark', // 'dark' | 'light'

  // Adaptive complexity tier
  // 'guided' | 'standard' | 'streamlined' | 'minimal'
  complexityTier: 'standard',
  complexityAutoDetect: true, // Whether to auto-detect from maturity level

  // Panel states
  leftSidebarOpen: true,
  rightSidebarOpen: true,
  leftSidebarWidth: 'expanded', // 'collapsed' | 'expanded'

  // Right sidebar panel state
  activePanelTab: 'scaffold', // Default to scaffold tab
  panelNotifications: {}, // { tabId: boolean } for notification dots

  // Command palette
  commandPaletteOpen: false,

  // Active view
  activeView: 'dashboard',

  // Mobile sheet states
  mobileNavOpen: false,
  mobilePanelOpen: false,
  mobilePanelTab: null,

  // Notifications
  notifications: [],
  unreadCount: 0,

  // Actions
  initializeTheme: () => {
    const theme = getSystemPreference();
    applyTheme(theme);
    set({ theme });
  },

  toggleTheme: () =>
    set((state) => {
      const newTheme = state.theme === 'dark' ? 'light' : 'dark';
      applyTheme(newTheme);
      return { theme: newTheme };
    }),

  setTheme: (theme) => {
    applyTheme(theme);
    set({ theme });
  },

  toggleLeftSidebar: () =>
    set((state) => ({ leftSidebarOpen: !state.leftSidebarOpen })),

  toggleRightSidebar: () =>
    set((state) => ({ rightSidebarOpen: !state.rightSidebarOpen })),

  setCommandPaletteOpen: (open) =>
    set({ commandPaletteOpen: open }),

  toggleCommandPalette: () =>
    set((state) => ({ commandPaletteOpen: !state.commandPaletteOpen })),

  setActiveView: (view) =>
    set({ activeView: view }),

  // Collapse sidebar to icon-only
  collapseLeftSidebar: () =>
    set({ leftSidebarWidth: 'collapsed' }),

  expandLeftSidebar: () =>
    set({ leftSidebarWidth: 'expanded' }),

  toggleLeftSidebarWidth: () =>
    set((state) => ({
      leftSidebarWidth: state.leftSidebarWidth === 'collapsed' ? 'expanded' : 'collapsed',
    })),

  // Mobile
  setMobileNavOpen: (open) =>
    set({ mobileNavOpen: open }),

  toggleMobileNav: () =>
    set((state) => ({ mobileNavOpen: !state.mobileNavOpen })),

  // Notifications
  addNotification: (notification) =>
    set((state) => ({
      notifications: [notification, ...state.notifications],
      unreadCount: state.unreadCount + 1,
    })),

  markNotificationRead: (id) =>
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      ),
      unreadCount: Math.max(0, state.unreadCount - 1),
    })),

  clearNotifications: () =>
    set({ notifications: [], unreadCount: 0 }),

  // Panel tab management
  setActivePanelTab: (tabId) =>
    set((state) => ({
      activePanelTab: tabId,
      // Clear notification for selected tab
      panelNotifications: { ...state.panelNotifications, [tabId]: false },
    })),

  addPanelNotification: (tabId) =>
    set((state) => {
      // Don't add notification if tab is already active
      if (state.activePanelTab === tabId) return state;
      return {
        panelNotifications: { ...state.panelNotifications, [tabId]: true },
      };
    }),

  clearPanelNotification: (tabId) =>
    set((state) => ({
      panelNotifications: { ...state.panelNotifications, [tabId]: false },
    })),

  clearAllPanelNotifications: () =>
    set({ panelNotifications: {} }),

  // Mobile panel sheet
  openMobilePanel: (tabId) =>
    set({ mobilePanelOpen: true, mobilePanelTab: tabId || 'scaffold' }),

  closeMobilePanel: () =>
    set({ mobilePanelOpen: false }),

  // Auto-open right sidebar for pursuit pages
  openRightSidebarForPursuit: () => {
    const isMobile = window.innerWidth < 768;
    if (!isMobile) {
      set({ rightSidebarOpen: true });
    }
  },

  // Computed
  isLeftSidebarCollapsed: () => get().leftSidebarWidth === 'collapsed',

  // Adaptive complexity management
  setComplexityTier: (tier) =>
    set({ complexityTier: tier, complexityAutoDetect: false }),

  setComplexityAutoDetect: (autoDetect) =>
    set({ complexityAutoDetect: autoDetect }),

  // Initialize complexity from user maturity level
  initializeComplexity: (maturityLevel) => {
    const tierMap = {
      'NOVICE': 'guided',
      'COMPETENT': 'standard',
      'PROFICIENT': 'streamlined',
      'EXPERT': 'minimal',
    };
    const tier = tierMap[maturityLevel] || 'standard';
    set((state) => ({
      complexityTier: state.complexityAutoDetect ? tier : state.complexityTier,
    }));
  },

  // Apply complexity tier effects on layout
  applyComplexityDefaults: () => {
    const tier = get().complexityTier;
    const isMobile = window.innerWidth < 768;

    if (isMobile) return; // Don't override mobile defaults

    switch (tier) {
      case 'guided':
        set({
          leftSidebarWidth: 'expanded',
          rightSidebarOpen: true,
          leftSidebarOpen: true,
        });
        break;
      case 'standard':
        set({
          leftSidebarWidth: 'expanded',
          rightSidebarOpen: true,
          leftSidebarOpen: true,
        });
        break;
      case 'streamlined':
        set({
          leftSidebarWidth: 'collapsed',
          rightSidebarOpen: false,
        });
        break;
      case 'minimal':
        set({
          leftSidebarWidth: 'collapsed',
          rightSidebarOpen: false,
          leftSidebarOpen: false,
        });
        break;
    }
  },

  // Check if feature should be visible based on complexity tier
  shouldShowForTier: (minTier, maxTier = 'minimal') => {
    const tiers = ['guided', 'standard', 'streamlined', 'minimal'];
    const current = get().complexityTier;
    const currentIdx = tiers.indexOf(current);
    const minIdx = tiers.indexOf(minTier);
    const maxIdx = tiers.indexOf(maxTier);
    return currentIdx >= minIdx && currentIdx <= maxIdx;
  },
}));
