import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      // Context detection state (not persisted - transient)
      contextDetection: null, // { destination, context, toast }
      contextDetectionComplete: false,

      login: (user, token, refreshToken = null) =>
        set((state) => ({
          user,
          token,
          // Keep existing refresh token if not provided (e.g., during profile refresh)
          refreshToken: refreshToken ?? state.refreshToken,
          isAuthenticated: true,
          isLoading: false,
          contextDetectionComplete: false, // Reset on new login
        })),

      logout: () =>
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false,
          contextDetection: null,
          contextDetectionComplete: false,
        }),

      // Context detection actions
      setContextDetection: (detection) =>
        set({
          contextDetection: detection,
          contextDetectionComplete: true,
        }),

      clearContextDetection: () =>
        set({
          contextDetection: null,
          contextDetectionComplete: false,
        }),

      updateUser: (updates) =>
        set((state) => ({
          user: { ...state.user, ...updates },
        })),

      setLoading: (isLoading) =>
        set({ isLoading }),

      // Computed getters
      getUserId: () => get().user?.id,
      getUserName: () => get().user?.name || get().user?.email?.split('@')[0] || 'User',
      getUserInitials: () => {
        const name = get().user?.name || get().user?.email || 'U';
        return name
          .split(' ')
          .map((n) => n[0])
          .join('')
          .toUpperCase()
          .slice(0, 2);
      },
    }),
    {
      name: 'inde-auth-store',
      // Only persist authentication-critical fields
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
