import { useAuthStore } from '../stores/authStore';
import { usePursuitStore } from '../stores/pursuitStore';
import { useCoachingStore } from '../stores/coachingStore';
import { useEmsStore } from '../stores/emsStore';
import { useIntelligenceStore } from '../stores/intelligenceStore';
import { authApi } from '../api/auth';
import { pursuitsApi } from '../api/pursuits';
import { queryClient } from '../lib/queryClient';

/**
 * Auth convenience hook with login/logout actions.
 */
export function useAuth() {
  const { user, token, isAuthenticated, isLoading, login, logout, setLoading } = useAuthStore();

  const handleLogin = async (email, password) => {
    setLoading(true);
    try {
      const response = await authApi.login(email, password);
      // Backend returns { access_token, refresh_token, token_type, expires_in }
      const { access_token, refresh_token } = response.data;

      // Store tokens first so subsequent API calls are authenticated
      login({ email }, access_token, refresh_token);

      // Fetch full user profile
      try {
        const profileResponse = await authApi.getProfile();
        // Map backend fields to frontend expected format
        const userData = {
          id: profileResponse.data.user_id,
          email: profileResponse.data.email,
          name: profileResponse.data.name,
          experienceLevel: profileResponse.data.experience_level,
          maturityLevel: profileResponse.data.maturity_level,
          role: profileResponse.data.role,  // v3.15: Include role for admin detection
        };
        login(userData, access_token, refresh_token);
      } catch (profileError) {
        // Profile fetch failed, but login succeeded - use email as fallback
        console.warn('Could not fetch user profile:', profileError);
      }

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Login failed',
      };
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      // Check if this is a demo user - if so, delete all their pursuits first
      const currentUser = useAuthStore.getState().user;
      const isDemoUser = currentUser?.email === 'demo@inde.dev';

      if (isDemoUser) {
        try {
          // Delete all pursuits for demo user to reset the environment
          await pursuitsApi.deleteAll();
        } catch (cleanupError) {
          console.warn('Failed to clean up demo account:', cleanupError);
        }
      }

      await authApi.logout();
    } catch (error) {
      // Ignore logout errors
    } finally {
      // Clear auth state
      logout();

      // Clear all other stores to prevent data leakage between users
      usePursuitStore.getState().reset();
      useCoachingStore.getState().reset();
      useEmsStore.getState().reset();
      useIntelligenceStore.getState().reset();

      // Clear React Query cache to remove previous user's data
      queryClient.clear();

      // Clear persisted localStorage data for EMS and Intelligence stores
      localStorage.removeItem('inde-ems-store');
      localStorage.removeItem('inde-intelligence-store');
    }
  };

  const handleRegister = async (name, email, password) => {
    setLoading(true);
    try {
      await authApi.register({ name, email, password });
      // After registration, log the user in
      return await handleLogin(email, password);
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Registration failed',
      };
    } finally {
      setLoading(false);
    }
  };

  const refreshProfile = async () => {
    if (!token) return;
    try {
      const response = await authApi.getProfile();
      login(response.data, token);
    } catch (error) {
      // Profile fetch failed, log out
      logout();
    }
  };

  return {
    user,
    token,
    isAuthenticated,
    isLoading,
    login: handleLogin,
    logout: handleLogout,
    register: handleRegister,
    refreshProfile,
  };
}
