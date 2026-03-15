import client from './client';

/**
 * Intelligence API client
 * Consumes IML Pattern Intelligence endpoints
 * Note: Backend intelligence endpoints are planned for future builds.
 * Currently returns fallback data to allow UI to function.
 */
export const intelligenceApi = {
  // Get pattern matches for active pursuit
  getPatterns: async (pursuitId) => {
    try {
      return await client.get(`/intelligence/patterns/${pursuitId}`);
    } catch {
      // Return empty patterns - backend not yet implemented
      return { data: { patterns: [] } };
    }
  },

  // Get cross-pollination suggestions
  getCrossPollination: async (pursuitId) => {
    try {
      return await client.get(`/intelligence/cross-pollination/${pursuitId}`);
    } catch {
      // Return empty insights - backend not yet implemented
      return { data: { insights: [] } };
    }
  },

  // Get learning velocity for user
  getLearningVelocity: async (userId) => {
    try {
      return await client.get(`/intelligence/learning-velocity/${userId}`);
    } catch {
      // Return default velocity - backend not yet implemented
      return { data: { velocity: 0, trend: 'stable', history: [] } };
    }
  },

  // Dismiss a pattern suggestion (no-op if backend unavailable)
  dismissPattern: async (patternId) => {
    try {
      return await client.post(`/intelligence/patterns/${patternId}/dismiss`);
    } catch {
      return { data: { success: true } };
    }
  },

  // Record pattern feedback (no-op if backend unavailable)
  recordFeedback: async (patternId, feedback, pursuitId) => {
    try {
      return await client.post(`/intelligence/patterns/${patternId}/feedback`, {
        type: feedback,
        pursuit_id: pursuitId,
      });
    } catch {
      return { data: { success: true } };
    }
  },

  // Get biomimicry insights (for TRIZ pursuits)
  getBiomimicryInsights: async (pursuitId) => {
    try {
      return await client.get(`/intelligence/biomimicry/${pursuitId}`);
    } catch {
      // Return empty insights - backend not yet implemented
      return { data: { insights: [] } };
    }
  },

  // Get all intelligence for a pursuit
  getIntelligenceSummary: async (pursuitId) => {
    try {
      return await client.get(`/intelligence/summary/${pursuitId}`);
    } catch {
      return { data: { patterns: [], cross_pollination: [], velocity: 0 } };
    }
  },
};
