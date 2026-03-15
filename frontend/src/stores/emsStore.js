import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * EMS Store
 * Manages EMS state including observation status, inferences,
 * active review sessions, and refinement history.
 */
export const useEmsStore = create(
  persist(
    (set, get) => ({
      // Observation state
      observationStatus: null,
      isObserving: false,

      // Inference state
      latestInference: null,
      hasNewInference: false,

      // Active review session
      activeReviewSession: null,
      refinedArchetype: null,

      // Refinement history (for undo support)
      refinementHistory: [],

      // Published archetypes cache
      publishedArchetypes: [],

      // Review session messages
      reviewMessages: [],

      // Actions - Observation
      setObservationStatus: (status) => set({ observationStatus: status }),

      startObserving: () => set({ isObserving: true }),

      stopObserving: () => set({ isObserving: false }),

      // Actions - Inference
      setLatestInference: (inference) => set({
        latestInference: inference,
        hasNewInference: true,
      }),

      clearInferenceFlag: () => set({ hasNewInference: false }),

      // Actions - Review Session
      startReview: (session) => set({
        activeReviewSession: session,
        refinedArchetype: session?.refined_archetype || null,
        refinementHistory: [],
        reviewMessages: session?.messages || [],
      }),

      updateRefinedArchetype: (archetype) => set({ refinedArchetype: archetype }),

      addReviewMessage: (message) => set((state) => ({
        reviewMessages: [...state.reviewMessages, message],
      })),

      setReviewMessages: (messages) => set({ reviewMessages: messages }),

      endReview: () => set({
        activeReviewSession: null,
        refinedArchetype: null,
        refinementHistory: [],
        reviewMessages: [],
      }),

      // Actions - Refinements
      applyRefinement: (refinement) => set((state) => ({
        refinementHistory: [...state.refinementHistory, {
          ...refinement,
          timestamp: new Date().toISOString(),
        }],
      })),

      undoLastRefinement: () => set((state) => {
        const newHistory = [...state.refinementHistory];
        const undone = newHistory.pop();
        return {
          refinementHistory: newHistory,
          // Note: Actual archetype state reversal would need backend support
        };
      }),

      clearRefinementHistory: () => set({ refinementHistory: [] }),

      // Actions - Published Archetypes
      setPublishedArchetypes: (archetypes) => set({ publishedArchetypes: archetypes }),

      addPublishedArchetype: (archetype) => set((state) => ({
        publishedArchetypes: [archetype, ...state.publishedArchetypes],
      })),

      updateArchetype: (id, updates) => set((state) => ({
        publishedArchetypes: state.publishedArchetypes.map((a) =>
          a.id === id ? { ...a, ...updates } : a
        ),
      })),

      // Computed getters
      isReviewActive: () => !!get().activeReviewSession,

      canUndo: () => get().refinementHistory.length > 0,

      getRefinementCount: () => get().refinementHistory.length,

      // Full reset
      reset: () => set({
        observationStatus: null,
        isObserving: false,
        latestInference: null,
        hasNewInference: false,
        activeReviewSession: null,
        refinedArchetype: null,
        refinementHistory: [],
        publishedArchetypes: [],
        reviewMessages: [],
      }),
    }),
    {
      name: 'inde-ems-store',
      partialize: (state) => ({
        // Only persist published archetypes and observation status
        publishedArchetypes: state.publishedArchetypes,
        observationStatus: state.observationStatus,
      }),
    }
  )
);

export default useEmsStore;
