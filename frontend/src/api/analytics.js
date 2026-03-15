import client from './client';

export const analyticsApi = {
  // Portfolio analytics
  getPortfolioHealth: () =>
    client.get('/analytics/portfolio/health'),

  getPortfolioOverview: () =>
    client.get('/analytics/portfolio/overview'),

  getPortfolioTrends: (timeframe = '30d') =>
    client.get('/analytics/portfolio/trends', { params: { timeframe } }),

  // Cross-pursuit analysis
  comparePursuits: (pursuitIds) =>
    client.post('/analytics/compare', { pursuit_ids: pursuitIds }),

  getSharedPatterns: () =>
    client.get('/analytics/patterns/shared'),

  // Effectiveness metrics
  getEffectivenessScorecard: () =>
    client.get('/analytics/effectiveness'),

  getInnovatorProfile: (userId) =>
    client.get(`/analytics/innovator/${userId}`),

  // Reports
  generateLivingSnapshot: (pursuitId) =>
    client.post(`/reports/snapshot/${pursuitId}`),

  generateTerminalReport: (pursuitId) =>
    client.post(`/reports/terminal/${pursuitId}`),

  generatePortfolioReport: () =>
    client.post('/reports/portfolio'),

  getReport: (reportId) =>
    client.get(`/reports/${reportId}`),

  listReports: (pursuitId) =>
    client.get('/reports', { params: { pursuit_id: pursuitId } }),
};
