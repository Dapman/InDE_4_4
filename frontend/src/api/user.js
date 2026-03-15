import client from './client';

/**
 * User API module for context detection and preferences
 */
export const userApi = {
  // Get user profile with preferences and experience level
  getProfile: () => client.get('/auth/me'),

  // Get last session state (last active pursuit, timestamp)
  // Falls back to pursuits endpoint if dedicated session-state doesn't exist
  getSessionState: async () => {
    try {
      const response = await client.get('/auth/session-state');
      return response;
    } catch (error) {
      // Fallback: derive session state from pursuits list
      return { data: { last_active_pursuit: null, last_active_timestamp: null } };
    }
  },

  // Update user preferences (adaptive complexity level, skip_context_routing, etc.)
  updatePreferences: (prefs) => client.patch('/auth/preferences', prefs),

  // Get active pursuit count (lightweight, for routing decision)
  getActivePursuitCount: async () => {
    try {
      const response = await client.get('/pursuits/count?status=active');
      return response;
    } catch (error) {
      // Fallback: fetch full list and count
      const listResponse = await client.get('/pursuits');
      const pursuits = listResponse.data?.pursuits || listResponse.data || [];
      const active = pursuits.filter(
        (p) => p.status === 'active' || p.status === 'ACTIVE' || p.state === 'ACTIVE'
      );
      return { data: { count: active.length, pursuits: active } };
    }
  },
};

export default userApi;
