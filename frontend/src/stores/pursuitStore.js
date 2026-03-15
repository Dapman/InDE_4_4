import { create } from 'zustand';

export const usePursuitStore = create((set, get) => ({
  activePursuitId: null,
  pursuitCache: {}, // { [id]: pursuit_data }
  pursuitList: [],
  isLoading: false,
  error: null,

  setActivePursuit: (id) =>
    set({ activePursuitId: id }),

  setPursuitList: (list) =>
    set({ pursuitList: list }),

  cachePursuit: (id, data) =>
    set((state) => ({
      pursuitCache: { ...state.pursuitCache, [id]: data },
    })),

  updateCachedPursuit: (id, updates) =>
    set((state) => ({
      pursuitCache: {
        ...state.pursuitCache,
        [id]: { ...state.pursuitCache[id], ...updates },
      },
    })),

  removePursuit: (id) =>
    set((state) => {
      const { [id]: removed, ...rest } = state.pursuitCache;
      return {
        pursuitCache: rest,
        pursuitList: state.pursuitList.filter((p) => p.id !== id),
        activePursuitId: state.activePursuitId === id ? null : state.activePursuitId,
      };
    }),

  setLoading: (isLoading) =>
    set({ isLoading }),

  setError: (error) =>
    set({ error }),

  clearError: () =>
    set({ error: null }),

  // Computed getters
  getActivePursuit: () => {
    const state = get();
    return state.pursuitCache[state.activePursuitId] || null;
  },

  getPursuitById: (id) => get().pursuitCache[id] || null,

  getActivePursuits: () =>
    get().pursuitList.filter((p) => p.state === 'ACTIVE'),

  getArchivedPursuits: () =>
    get().pursuitList.filter((p) => p.state === 'ARCHIVED'),

  // Full reset for logout
  reset: () =>
    set({
      activePursuitId: null,
      pursuitCache: {},
      pursuitList: [],
      isLoading: false,
      error: null,
    }),
}));
