import client from './client';

export const systemApi = {
  // Health check
  healthCheck: () =>
    client.get('/system/health'),

  // Version info
  getVersion: () =>
    client.get('/system/version'),

  // Display labels
  getDisplayLabels: () =>
    client.get('/system/display-labels').then((res) => res.data),

  // Methodology archetypes
  getMethodologyArchetypes: () =>
    client.get('/system/archetypes'),

  // Configuration
  getConfig: () =>
    client.get('/system/config'),

  updateConfig: (preferences) =>
    client.patch('/system/config', { preferences }),

  // Database status (admin only)
  getDatabaseStatus: () =>
    client.get('/system/database'),

  // Event streams status
  getStreamsStatus: () =>
    client.get('/system/streams'),

  // LLM Provider preferences (v3.9)
  getUserProviders: () =>
    client.get('/system/llm/user-providers').then((res) => res.data),

  updateLlmPreference: (preference) =>
    // Backend merges with existing preferences
    client.patch('/system/config', { preferences: { llm_provider: preference } }),

  // Diagnostics (v3.14 - admin only)
  getDiagnostics: (params = {}) =>
    client.get('/system/diagnostics', { params }).then((res) => res.data),

  getOnboardingDiagnostics: (days = 30) =>
    client.get('/system/diagnostics/onboarding', { params: { days } }).then((res) => res.data),

  getErrorDiagnostics: (limit = 50, level = null) =>
    client.get('/system/diagnostics/errors', { params: { limit, level } }).then((res) => res.data),

  // User diagnostics (v3.16 - admin only)
  getUserDiagnostics: (onlineThresholdMinutes = 15) =>
    client.get('/system/diagnostics/users', { params: { online_threshold_minutes: onlineThresholdMinutes } }).then((res) => res.data),

  // Innovator Vitals (v4.4.1 - admin only)
  getInnovatorVitals: () =>
    client.get('/system/diagnostics/innovator-vitals').then((res) => res.data),
};
