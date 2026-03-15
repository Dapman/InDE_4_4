import client from './client';

export const pursuitsApi = {
  list: (options = {}) => {
    console.log('[pursuitsApi.list] Called with options:', options);
    const params = new URLSearchParams();
    if (options.include_archived) params.append('include_archived', 'true');
    if (options.status) params.append('status', options.status);
    if (options.limit) params.append('limit', options.limit);
    if (options.offset) params.append('offset', options.offset);
    const queryString = params.toString();
    const url = `/pursuits${queryString ? `?${queryString}` : ''}`;
    console.log('[pursuitsApi.list] Requesting URL:', url);
    return client.get(url);
  },

  get: (id) =>
    client.get(`/pursuits/${id}`),

  create: (data) =>
    client.post('/pursuits', data),

  update: (id, data) =>
    client.put(`/pursuits/${id}`, data),

  archive: (id) =>
    client.post(`/pursuits/${id}/archive`),

  restore: (id) =>
    client.post(`/pursuits/${id}/restore`),

  delete: (id) =>
    client.delete(`/pursuits/${id}`),

  // EVAPORATE - immediate permanent deletion without retrospective
  evaporate: (id) =>
    client.post(`/pursuits/${id}/evaporate`),

  // Delete all pursuits for the user (used for demo account cleanup)
  deleteAll: () =>
    client.delete('/pursuits/user/all'),

  // State transitions
  transitionState: (id, newState, rationale) =>
    client.post(`/pursuits/${id}/transition`, { new_state: newState, rationale }),

  // Phase management
  transitionPhase: (id, targetPhase, rationale) =>
    client.post(`/pursuits/${id}/phase-transition`, { target_phase: targetPhase, rationale }),

  // Team management
  getTeam: (id) =>
    client.get(`/teams/pursuits/${id}/team`),

  addTeamMember: (id, userId, role) =>
    client.post(`/teams/pursuits/${id}/team`, { user_id: userId, role }),

  removeTeamMember: (id, userId) =>
    client.delete(`/teams/pursuits/${id}/team/${userId}`),

  updateTeamRole: (id, userId, role) =>
    client.patch(`/teams/pursuits/${id}/team/${userId}/role`, { role }),

  // Health & analytics
  getHealth: (id) =>
    client.get(`/health/${id}`),

  getTimeline: (id) =>
    client.get(`/timeline/${id}/allocation`),

  // v3.9: Milestones
  getMilestones: (id) =>
    client.get(`/timeline/${id}/milestones`),

  updateMilestone: (pursuitId, milestoneId, data) =>
    client.patch(`/timeline/${pursuitId}/milestones/${milestoneId}`, data),

  deleteMilestone: (pursuitId, milestoneId) =>
    client.delete(`/timeline/${pursuitId}/milestones/${milestoneId}`),

  // v3.10: Timeline Integrity endpoints
  checkTimelineConsistency: (id) =>
    client.get(`/timeline/${id}/consistency-check`),

  resolveTimelineInconsistency: (id, data) =>
    client.post(`/timeline/${id}/resolve-inconsistency`, data),

  resolveConflict: (id, data) =>
    client.post(`/timeline/${id}/resolve-conflict`, data),

  confirmRelativeDate: (id, data) =>
    client.post(`/timeline/${id}/confirm-relative-date`, data),

  getStaleRelativeDates: (id) =>
    client.get(`/timeline/${id}/stale-relative-dates`),

  getPendingConflicts: (id) =>
    client.get(`/timeline/${id}/pending-conflicts`),

  // v3.11: Milestone permissions (TD-014)
  getMilestonePermissions: (id) =>
    client.get(`/timeline/${id}/milestone-permissions`),

  getScaffold: (id) =>
    client.get(`/pursuits/${id}/scaffolding`),

  // Sharing
  getShareSettings: (id) =>
    client.get(`/pursuits/${id}/sharing`),

  updateShareSettings: (id, settings) =>
    client.put(`/pursuits/${id}/sharing`, settings),

  // Abandonment & Retrospective
  abandon: (id, reason) =>
    client.post(`/pursuits/${id}/abandon`, { reason }),

  completeRetrospective: (id, retrospectiveData) =>
    client.post(`/pursuits/${id}/retrospective`, retrospectiveData),

  getRetrospective: (id) =>
    client.get(`/pursuits/${id}/retrospective`),
};
