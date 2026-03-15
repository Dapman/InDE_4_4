import client from './client';

export const emsApi = {
  // Process observation - matches backend /ems/pursuit/{pursuit_id}/*
  getObservations: (pursuitId) =>
    client.get(`/ems/pursuit/${pursuitId}/observations`),

  getObservationStatus: (pursuitId) =>
    client.get(`/ems/pursuit/${pursuitId}/status`),

  getObservationSummary: (pursuitId) =>
    client.get(`/ems/pursuit/${pursuitId}/summary`),

  pauseObservation: (pursuitId) =>
    client.post(`/ems/pursuit/${pursuitId}/pause`),

  resumeObservation: (pursuitId) =>
    client.post(`/ems/pursuit/${pursuitId}/resume`),

  // Pattern inference - matches backend /ems/innovator/{innovator_id}/*
  getInferredArchetypes: (innovatorId) =>
    client.get(`/ems/innovator/${innovatorId}/inference-result`),

  triggerInference: (innovatorId) =>
    client.post(`/ems/innovator/${innovatorId}/infer-patterns`),

  getSynthesisEligibility: (innovatorId) =>
    client.get(`/ems/innovator/${innovatorId}/synthesis-eligibility`),

  getAdhocPursuits: (innovatorId) =>
    client.get(`/ems/innovator/${innovatorId}/adhoc-pursuits`),

  generateArchetype: (innovatorId) =>
    client.post(`/ems/innovator/${innovatorId}/generate-archetype`),

  getArchetype: (innovatorId) =>
    client.get(`/ems/innovator/${innovatorId}/archetype`),

  // Review sessions - matches backend /ems/review/*
  startReview: (innovatorId, archetypeId) =>
    client.post(`/ems/review/start/${innovatorId}`, { inferred_archetype_id: archetypeId }),

  getReviewStatus: (sessionId) =>
    client.get(`/ems/review/${sessionId}/status`),

  sendReviewMessage: (sessionId, message) =>
    client.post(`/ems/review/${sessionId}/exchange`, { innovator_message: message }),

  setMethodologyName: (sessionId, name) =>
    client.post(`/ems/review/${sessionId}/name`, { name }),

  setVisibility: (sessionId, visibility) =>
    client.post(`/ems/review/${sessionId}/visibility`, { visibility }),

  approvePublication: (sessionId) =>
    client.post(`/ems/review/${sessionId}/approve`),

  rejectReview: (sessionId) =>
    client.post(`/ems/review/${sessionId}/reject`),

  getComparison: (sessionId) =>
    client.get(`/ems/review/${sessionId}/comparison`),

  // Published archetypes - matches backend /ems/archetypes/*
  getMyArchetypes: () =>
    client.get('/ems/archetypes/mine'),

  checkEvolution: (archetypeId) =>
    client.get(`/ems/archetypes/${archetypeId}/evolution-check`),

  evolveArchetype: (archetypeId) =>
    client.post(`/ems/archetypes/${archetypeId}/evolve`),

  // Note: updateArchetypeVisibility endpoint not in backend - use session visibility
  updateArchetypeVisibility: (archetypeId, visibility) =>
    client.post(`/ems/archetypes/${archetypeId}/evolve`, { visibility }),
};
