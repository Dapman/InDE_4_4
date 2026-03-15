/**
 * Discovery API - User discovery state endpoints.
 * v3.15 "First User Ready"
 */

import client from './client';

export const discoveryApi = {
  /**
   * Get the current user's discovery state
   */
  getState: () => client.get('/v1/user/discovery'),

  /**
   * Dismiss a hint
   * @param {string} hintId - The hint ID to dismiss
   */
  dismissHint: (hintId) =>
    client.post('/v1/user/discovery/dismiss', { hint_id: hintId }),

  /**
   * Reset all dismissed hints
   */
  resetHints: () => client.post('/v1/user/discovery/reset'),

  /**
   * Mark a checklist item as complete
   * @param {string} itemKey - The checklist item key
   */
  completeChecklistItem: (itemKey) =>
    client.post(`/v1/user/discovery/checklist/${itemKey}/complete`),
};

export default discoveryApi;
