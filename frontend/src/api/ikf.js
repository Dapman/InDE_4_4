import client from './client';

export const ikfApi = {
  // Federation status
  getFederationStatus: () =>
    client.get('/ikf/status'),

  // Contributions
  getContributions: () =>
    client.get('/ikf/contributions'),

  getPendingReviews: () =>
    client.get('/ikf/contributions/pending'),

  prepareContribution: (pursuitId, packageType) =>
    client.post('/ikf/contributions/prepare', { pursuit_id: pursuitId, package_type: packageType }),

  reviewContribution: (contributionId, action, rationale) =>
    client.post(`/ikf/contributions/${contributionId}/review`, { action, rationale }),

  submitContribution: (contributionId) =>
    client.post(`/ikf/contributions/${contributionId}/submit`),

  // Patterns from federation
  getFederatedPatterns: (filters) =>
    client.get('/ikf/patterns', { params: filters }),

  getPatternDetails: (patternId) =>
    client.get(`/ikf/patterns/${patternId}`),

  // Benchmarks
  getBenchmarks: (industry, phase) =>
    client.get('/ikf/benchmarks', { params: { industry, phase } }),

  compareToBenchmark: (pursuitId) =>
    client.get(`/ikf/benchmarks/compare/${pursuitId}`),

  // Knowledge import
  importPattern: (patternId) =>
    client.post(`/ikf/patterns/${patternId}/import`),

  // Organization federation
  getOrgFederationSettings: () =>
    client.get('/ikf/org/settings'),

  updateOrgFederationSettings: (settings) =>
    client.put('/ikf/org/settings', settings),
};
