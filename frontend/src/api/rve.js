import client from './client';

/**
 * Risk Validation Engine API client
 * Provides access to risk assessment, validation, and experiment design.
 */
export const rveApi = {
  // Get all risks for a pursuit
  getRisks: async (pursuitId) => {
    try {
      return await client.get(`/pursuits/${pursuitId}/risks`);
    } catch {
      return { data: { risks: [] } };
    }
  },

  // Get risk details
  getRiskDetails: async (riskId) => {
    try {
      return await client.get(`/risks/${riskId}`);
    } catch {
      return { data: null };
    }
  },

  // Create a new risk from a fear
  createRiskFromFear: async (pursuitId, fearId) => {
    try {
      return await client.post(`/pursuits/${pursuitId}/risks/from-fear`, {
        fear_id: fearId,
      });
    } catch {
      return { data: { success: false } };
    }
  },

  // Add a manual risk
  addRisk: async (pursuitId, risk) => {
    try {
      return await client.post(`/pursuits/${pursuitId}/risks`, risk);
    } catch {
      return { data: { success: false } };
    }
  },

  // Update risk assessment
  updateRiskAssessment: async (riskId, assessment) => {
    try {
      return await client.put(`/risks/${riskId}/assessment`, assessment);
    } catch {
      return { data: { success: false } };
    }
  },

  // Get experiment suggestions for a risk
  getExperimentSuggestions: async (riskId) => {
    try {
      return await client.get(`/risks/${riskId}/experiments/suggest`);
    } catch {
      return { data: { suggestions: [] } };
    }
  },

  // Create an experiment for a risk
  createExperiment: async (riskId, experiment) => {
    try {
      return await client.post(`/risks/${riskId}/experiments`, experiment);
    } catch {
      return { data: { success: false } };
    }
  },

  // Get experiments for a risk
  getExperiments: async (riskId) => {
    try {
      return await client.get(`/risks/${riskId}/experiments`);
    } catch {
      return { data: { experiments: [] } };
    }
  },

  // Update experiment status
  updateExperiment: async (experimentId, data) => {
    try {
      return await client.put(`/experiments/${experimentId}`, data);
    } catch {
      return { data: { success: false } };
    }
  },

  // Get decision support for a risk
  getDecisionSupport: async (riskId) => {
    try {
      return await client.get(`/risks/${riskId}/decision-support`);
    } catch {
      return { data: { recommendation: null, confidence: 0 } };
    }
  },

  // Record a risk decision
  recordDecision: async (riskId, decision) => {
    try {
      return await client.post(`/risks/${riskId}/decision`, decision);
    } catch {
      return { data: { success: false } };
    }
  },

  // Get risk validation status
  getValidationStatus: async (riskId) => {
    try {
      return await client.get(`/risks/${riskId}/validation`);
    } catch {
      return { data: { status: 'unknown', evidence_count: 0 } };
    }
  },

  // Override a risk assessment (with justification)
  overrideAssessment: async (riskId, override) => {
    try {
      return await client.post(`/risks/${riskId}/override`, override);
    } catch {
      return { data: { success: false } };
    }
  },
};
