import client from './client';

/**
 * Reports API client
 * Generate and manage SILR reports (Living Snapshot, Terminal, Portfolio).
 */
export const reportsApi = {
  // Generate a living snapshot report
  generateLivingSnapshot: async (pursuitId) => {
    try {
      return await client.post('/reports', {
        pursuit_id: pursuitId,
        report_type: 'living_snapshot',
      });
    } catch (error) {
      return { data: null, error: error.response?.data?.detail || 'Failed to generate report' };
    }
  },

  // Generate a terminal report
  generateTerminalReport: async (pursuitId) => {
    try {
      return await client.post('/reports', {
        pursuit_id: pursuitId,
        report_type: 'terminal',
      });
    } catch (error) {
      return { data: null, error: error.response?.data?.detail || 'Failed to generate report' };
    }
  },

  // Generate a portfolio report
  generatePortfolioReport: async () => {
    try {
      return await client.post('/reports', {
        report_type: 'portfolio',
      });
    } catch (error) {
      return { data: null, error: error.response?.data?.detail || 'Failed to generate report' };
    }
  },

  // Get a report by ID
  getReport: async (reportId) => {
    try {
      return await client.get(`/reports/${reportId}`);
    } catch {
      return { data: null };
    }
  },

  // List reports for a pursuit
  listReports: async (pursuitId) => {
    try {
      return await client.get(`/reports/pursuit/${pursuitId}`);
    } catch {
      return { data: { reports: [] } };
    }
  },
};
