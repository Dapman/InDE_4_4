import client from './client';

/**
 * IKF Federation Panel API client
 * Federation status, contributions, trust network
 * Note: Some endpoints have fallbacks for planned backend features.
 */
export const federationApi = {
  // ========== Federation Status ==========

  // Get federation connection status
  getStatus: async () => {
    try {
      return await client.get('/ikf/federation/status');
    } catch {
      return { data: { status: 'disconnected', node_count: 0 } };
    }
  },

  // Get sync health info
  getSyncHealth: async () => {
    try {
      return await client.get('/ikf/federation/sync-health');
    } catch {
      return { data: { healthy: false, last_sync: null } };
    }
  },

  // ========== Incoming Patterns ==========

  // Get incoming federated patterns (uses search endpoint)
  getIncomingPatterns: async (limit = 20) => {
    try {
      // Use the POST search endpoint that exists
      const response = await client.post('/ikf/federation/patterns/search', {
        limit,
        package_type: 'pattern_contribution',
      });
      return { data: { patterns: response.data?.patterns || [] } };
    } catch {
      return { data: { patterns: [] } };
    }
  },

  // Get pattern details
  getPatternDetails: async (patternId) => {
    try {
      return await client.get(`/ikf/federation/patterns/${patternId}`);
    } catch {
      return { data: null };
    }
  },

  // ========== Benchmarks ==========

  // Get global benchmarks by type
  getBenchmarks: async (type) => {
    try {
      return await client.post('/ikf/federation/benchmarks', { phase: type });
    } catch {
      return { data: { benchmarks: [] } };
    }
  },

  // Get benchmark comparison for current org
  getBenchmarkComparison: async () => {
    try {
      return await client.post('/ikf/federation/benchmarks', {});
    } catch {
      return { data: { comparisons: [] } };
    }
  },

  // ========== Trust Network ==========

  // Get trust relationships (not yet implemented)
  getTrustNetwork: async () => {
    return { data: { nodes: [], relationships: [] } };
  },

  // Get organization reputation score (not yet implemented)
  getReputation: async () => {
    return { data: { score: 0, level: 'unknown' } };
  },

  // ========== Contributions ==========

  // Get contributions with status filtering
  getContributions: async (status) => {
    try {
      return await client.get('/ikf/contributions', { params: { status } });
    } catch {
      return { data: { contributions: [] } };
    }
  },

  // Get contribution preview (use get contribution endpoint)
  getContributionPreview: async (id) => {
    try {
      return await client.get(`/ikf/contributions/${id}`);
    } catch {
      return { data: null };
    }
  },

  // Submit review decision (approve or reject)
  reviewContribution: async (id, decision) => {
    try {
      const action = decision.approved ? 'approve' : 'reject';
      return await client.post(`/ikf/contributions/${id}/${action}`, {
        reason: decision.reason,
      });
    } catch {
      return { data: { success: false } };
    }
  },

  // Get contribution history (use contributions endpoint)
  getContributionHistory: async (limit = 50) => {
    try {
      return await client.get('/ikf/contributions', { params: { limit } });
    } catch {
      return { data: { contributions: [] } };
    }
  },
};
