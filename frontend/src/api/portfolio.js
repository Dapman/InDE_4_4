import client from './client';

/**
 * Portfolio Dashboard API client
 * Personal and organization portfolio analytics
 */
export const portfolioApi = {
  // ========== Personal Portfolio ==========

  // Get all pursuits for current user
  getPursuits: (filters = {}) =>
    client.get('/portfolio/pursuits', { params: filters }),

  // Get aggregate portfolio metrics
  getMetrics: () =>
    client.get('/portfolio/metrics'),

  // Get historical trends
  getTrends: (timeRange = '90d') =>
    client.get('/portfolio/trends', { params: { range: timeRange } }),

  // Get methodology distribution
  getMethodologyDistribution: () =>
    client.get('/portfolio/methodology-distribution'),

  // Get success/failure rates over time
  getOutcomeTrends: () =>
    client.get('/portfolio/outcome-trends'),

  // Get cross-pursuit pattern insights
  getPatternInsights: () =>
    client.get('/portfolio/pattern-insights'),

  // ========== Organization Portfolio ==========

  // Get org-level aggregated metrics
  getOrgMetrics: () =>
    client.get('/org/portfolio/metrics'),

  // Get innovation pipeline data
  getOrgPipeline: () =>
    client.get('/org/portfolio/pipeline'),

  // Get methodology effectiveness comparison
  getMethodologyEffectiveness: () =>
    client.get('/org/portfolio/methodology-effectiveness'),

  // Get org learning velocity trends
  getOrgLearningVelocity: () =>
    client.get('/org/portfolio/learning-velocity'),

  // Get team-level breakdown
  getTeamBreakdown: () =>
    client.get('/org/portfolio/teams'),
};
