import client from './client';

export const coachingApi = {
  // Send a message and get response
  sendMessage: (pursuitId, message, mode = 'coaching') =>
    client.post(`/coaching/${pursuitId}/message`, { message, mode }),

  // Get conversation history
  getHistory: (pursuitId, limit = 50) =>
    client.get(`/coaching/${pursuitId}/history`, { params: { limit } }),

  // Get coaching context
  getContext: (pursuitId) =>
    client.get(`/coaching/${pursuitId}/context`),

  // Mode-specific endpoints
  startVisionMode: (pursuitId) =>
    client.post(`/coaching/${pursuitId}/vision/start`),

  submitVision: (pursuitId, vision) =>
    client.post(`/coaching/${pursuitId}/vision/submit`, { vision }),

  startFearMode: (pursuitId) =>
    client.post(`/coaching/${pursuitId}/fear/start`),

  extractFears: (pursuitId) =>
    client.post(`/coaching/${pursuitId}/fear/extract`),

  startRetrospective: (pursuitId, scope) =>
    client.post(`/coaching/${pursuitId}/retrospective/start`, { scope }),

  // Interventions
  getActiveIntervention: (pursuitId) =>
    client.get(`/coaching/${pursuitId}/intervention`),

  acknowledgeIntervention: (pursuitId, interventionId) =>
    client.post(`/coaching/${pursuitId}/intervention/${interventionId}/acknowledge`),

  // RVE integration
  getRiskContext: (pursuitId) =>
    client.get(`/coaching/${pursuitId}/risks`),

  suggestExperiment: (pursuitId, riskId) =>
    client.post(`/coaching/${pursuitId}/experiment/suggest`, { risk_id: riskId }),
};
