import { useState, useEffect, useCallback } from 'react';
import { userApi } from '../api/user';
import { useAuthStore } from '../stores/authStore';

/**
 * Context Detection Algorithm for Returning User Experience
 *
 * On successful authentication, determines which interface configuration
 * to present based on user state:
 *
 * 1. Onboarding incomplete → First Session Flow (redirect to /onboarding)
 * 2. Expert + skip_context_routing → Expert Minimal Workspace (blank canvas + ⌘K hint)
 * 3. Recent session (<24h) with active pursuit → Resume Pursuit (navigate to /pursuit/{id})
 * 4. No active pursuits → Welcome Screen (/welcome with "Start New Pursuit")
 * 5. Exactly 1 active pursuit → Single Pursuit Dashboard (/pursuit/{id})
 * 6. Multiple active pursuits → Portfolio Overview (/portfolio)
 *
 * @returns {{ destination: string, isLoading: boolean, context: object, toast: string|null }}
 */
export function useContextDetection() {
  const [isLoading, setIsLoading] = useState(true);
  const [destination, setDestination] = useState('/');
  const [context, setContext] = useState(null);
  const [toast, setToast] = useState(null);

  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const updateUser = useAuthStore((s) => s.updateUser);

  const detectContext = useCallback(async () => {
    if (!isAuthenticated || !user) {
      setDestination('/login');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);

    try {
      // Parallel API calls for speed
      const [profileRes, sessionRes, countRes] = await Promise.all([
        userApi.getProfile().catch(() => ({ data: user })),
        userApi.getSessionState().catch(() => ({ data: {} })),
        userApi.getActivePursuitCount().catch(() => ({ data: { count: 0 } })),
      ]);

      const profile = profileRes.data || user;
      const sessionState = sessionRes.data || {};
      const pursuitData = countRes.data || { count: 0 };
      const activePursuitCount = pursuitData.count || 0;
      const activePursuits = pursuitData.pursuits || [];

      // Update user profile in store if we got fresh data
      if (profileRes.data) {
        updateUser(profileRes.data);
      }

      const contextData = {
        profile,
        sessionState,
        activePursuitCount,
        activePursuits,
        maturityLevel: profile.maturity_level || profile.experience_level || 'COMPETENT',
        isExpert: ['EXPERT', 'PROFICIENT'].includes(profile.maturity_level || profile.experience_level),
        skipContextRouting: profile.preferences?.skip_context_routing || false,
        onboardingComplete: profile.onboarding_complete !== false,
      };

      setContext(contextData);

      // Decision tree
      let dest = '/';
      let toastMsg = null;

      // 1. Onboarding incomplete
      if (!contextData.onboardingComplete) {
        dest = '/onboarding';
      }
      // 2. Expert with skip_context_routing
      else if (contextData.isExpert && contextData.skipContextRouting) {
        dest = '/'; // Dashboard with minimal workspace
      }
      // 3. Recent session with active pursuit
      else if (sessionState.last_active_pursuit && isRecentSession(sessionState.last_active_timestamp)) {
        dest = `/pursuit/${sessionState.last_active_pursuit}`;
        const pursuitName = activePursuits.find(p =>
          p.id === sessionState.last_active_pursuit || p.pursuit_id === sessionState.last_active_pursuit
        )?.title || 'your pursuit';
        toastMsg = `Welcome back! Continuing where you left off on ${pursuitName}.`;
      }
      // 4. No active pursuits
      else if (activePursuitCount === 0) {
        dest = '/welcome';
      }
      // 5. Exactly 1 active pursuit
      else if (activePursuitCount === 1 && activePursuits.length > 0) {
        const singlePursuit = activePursuits[0];
        dest = `/pursuit/${singlePursuit.id || singlePursuit.pursuit_id}`;
      }
      // 6. Multiple active pursuits
      else {
        dest = '/portfolio';
      }

      setDestination(dest);
      setToast(toastMsg);
    } catch (error) {
      console.error('Context detection failed:', error);
      // Fallback to dashboard
      setDestination('/');
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, user, updateUser]);

  useEffect(() => {
    if (isAuthenticated && user) {
      detectContext();
    }
  }, [isAuthenticated, user, detectContext]);

  return { destination, isLoading, context, toast, refresh: detectContext };
}

/**
 * Check if the last session was within the recency window (default 24h)
 */
function isRecentSession(timestamp, windowHours = 24) {
  if (!timestamp) return false;

  const lastActive = new Date(timestamp);
  const now = new Date();
  const diffHours = (now - lastActive) / (1000 * 60 * 60);

  return diffHours < windowHours;
}

export default useContextDetection;
