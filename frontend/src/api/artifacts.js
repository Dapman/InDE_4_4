import client from './client';

export const artifactsApi = {
  list: (pursuitId) =>
    client.get(`/artifacts/pursuit/${pursuitId}`),

  get: (id) =>
    client.get(`/artifacts/${id}`),

  create: (data) =>
    client.post('/artifacts', data),

  update: (id, data) =>
    client.put(`/artifacts/${id}`, data),

  delete: (id) =>
    client.delete(`/artifacts/${id}`),

  // Versioning
  getVersions: (id) =>
    client.get(`/artifacts/${id}/versions`),

  getVersion: (id, version) =>
    client.get(`/artifacts/${id}/versions/${version}`),

  revertToVersion: (id, version) =>
    client.post(`/artifacts/${id}/revert`, { version }),

  // Schema validation
  validate: (artifactType, content) =>
    client.post('/artifacts/validate', { artifact_type: artifactType, content }),

  // Artifact types
  getTypes: () =>
    client.get('/artifacts/types'),

  // Generate artifact
  generate: (pursuitId, artifactType, context) =>
    client.post('/artifacts/generate', {
      pursuit_id: pursuitId,
      artifact_type: artifactType,
      context,
    }),

  // Upload file as artifact
  upload: (pursuitId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('pursuit_id', pursuitId);
    return client.post('/artifacts/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
};
