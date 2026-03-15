import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Intelligence Store
 * Manages intelligence panel state including patterns, cross-pollination,
 * learning velocity, and dismissed patterns.
 */
export const useIntelligenceStore = create(
  persist(
    (set, get) => ({
      // Pattern data
      patterns: [],
      crossPollination: [],
      learningVelocity: null,

      // Dismissed patterns (excluded from display)
      dismissedPatternIds: [],

      // Notification state
      hasNewPatterns: false,
      lastPatternUpdate: null,

      // Actions
      setPatterns: (patterns) => set({
        patterns,
        hasNewPatterns: true,
        lastPatternUpdate: new Date().toISOString(),
      }),

      setCrossPollination: (crossPollination) => set({ crossPollination }),

      setLearningVelocity: (learningVelocity) => set({ learningVelocity }),

      dismissPattern: (patternId) => set((state) => ({
        dismissedPatternIds: [...state.dismissedPatternIds, patternId],
        patterns: state.patterns.filter((p) => p.id !== patternId),
      })),

      undoDismiss: (patternId) => set((state) => ({
        dismissedPatternIds: state.dismissedPatternIds.filter((id) => id !== patternId),
      })),

      clearNewFlag: () => set({ hasNewPatterns: false }),

      // Get patterns excluding dismissed ones
      getVisiblePatterns: () => {
        const state = get();
        return state.patterns.filter(
          (p) => !state.dismissedPatternIds.includes(p.id)
        );
      },

      // Reset for new pursuit context
      resetForPursuit: () => set({
        patterns: [],
        crossPollination: [],
        hasNewPatterns: false,
        // Keep dismissed patterns across pursuits
      }),

      // Full reset
      reset: () => set({
        patterns: [],
        crossPollination: [],
        learningVelocity: null,
        dismissedPatternIds: [],
        hasNewPatterns: false,
        lastPatternUpdate: null,
      }),
    }),
    {
      name: 'inde-intelligence-store',
      partialize: (state) => ({
        dismissedPatternIds: state.dismissedPatternIds,
        learningVelocity: state.learningVelocity,
      }),
    }
  )
);

export default useIntelligenceStore;
