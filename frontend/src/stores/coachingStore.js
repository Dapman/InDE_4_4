import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { generateUUID } from '../lib/utils';

export const useCoachingStore = create(
  persist(
    (set, get) => ({
  messages: [],
  isStreaming: false,
  streamBuffer: '', // Accumulates streamed chunks
  mode: 'coaching', // 'coaching' | 'vision' | 'fear' | 'retrospective' | 'non_directive' | 'ems_review'
  healthScore: null,
  healthZone: null,
  activeIntervention: null,
  isConnected: false,
  error: null,

  // Draft message per pursuit (persisted to survive page reloads)
  draftMessages: {}, // { [pursuitId]: string }

  // External send handler - set by ChatContainer so panels can trigger sends
  _sendHandler: null,

  // Message management
  addMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          ...message,
          id: message.id || generateUUID(),
          timestamp: message.timestamp || new Date(),
        },
      ],
    })),

  addUserMessage: (content) =>
    get().addMessage({
      role: 'user',
      content,
      mode: get().mode,
    }),

  addAssistantMessage: (content, metadata = {}) =>
    get().addMessage({
      role: 'assistant',
      content,
      mode: get().mode,
      ...metadata,
    }),

  // Streaming
  setStreaming: (streaming) =>
    set({ isStreaming: streaming }),

  appendStreamChunk: (chunk) =>
    set((state) => ({
      streamBuffer: state.streamBuffer + chunk,
    })),

  finalizeStream: () =>
    set((state) => {
      const content = state.streamBuffer;
      if (!content) return { streamBuffer: '', isStreaming: false };

      return {
        messages: [
          ...state.messages,
          {
            id: generateUUID(),
            role: 'assistant',
            content,
            timestamp: new Date(),
            mode: state.mode,
          },
        ],
        streamBuffer: '',
        isStreaming: false,
      };
    }),

  clearStreamBuffer: () =>
    set({ streamBuffer: '' }),

  // Mode management
  setMode: (mode) =>
    set({ mode }),

  // Health
  setHealth: (score, zone) =>
    set({ healthScore: score, healthZone: zone }),

  // Intervention
  setActiveIntervention: (intervention) =>
    set({ activeIntervention: intervention }),

  clearIntervention: () =>
    set({ activeIntervention: null }),

  // Connection
  setConnected: (connected) =>
    set({ isConnected: connected }),

  // Error handling
  setError: (error) =>
    set({ error }),

  clearError: () =>
    set({ error: null }),

  // Clear all
  clearMessages: () =>
    set({
      messages: [],
      streamBuffer: '',
      isStreaming: false,
      error: null,
    }),

  // Load history
  loadHistory: (messages) =>
    set({
      messages: messages.map((m) => ({
        ...m,
        id: m.id || generateUUID(),
        timestamp: new Date(m.timestamp || m.created_at),
      })),
    }),

  // Computed
  getLastMessage: () => {
    const messages = get().messages;
    return messages[messages.length - 1] || null;
  },

  getMessageCount: () => get().messages.length,

  // Full reset for logout
  reset: () =>
    set({
      messages: [],
      isStreaming: false,
      streamBuffer: '',
      mode: 'coaching',
      healthScore: null,
      healthZone: null,
      activeIntervention: null,
      isConnected: false,
      error: null,
      _sendHandler: null,
    }),

  // Register send handler (called by ChatContainer)
  registerSendHandler: (handler) =>
    set({ _sendHandler: handler }),

  // Unregister send handler
  unregisterSendHandler: () =>
    set({ _sendHandler: null }),

  // Trigger a message send from external components (e.g., sidebar panels)
  sendMessage: (message) => {
    const handler = get()._sendHandler;
    if (handler && typeof handler === 'function') {
      handler(message);
    } else {
      // Fallback: just add to messages (won't get a response)
      console.warn('No send handler registered - message added but not sent to coach');
      get().addUserMessage(message);
    }
  },

  // Draft message management (persisted)
  setDraftMessage: (pursuitId, content) =>
    set((state) => ({
      draftMessages: {
        ...state.draftMessages,
        [pursuitId]: content,
      },
    })),

  getDraftMessage: (pursuitId) => get().draftMessages[pursuitId] || '',

  clearDraftMessage: (pursuitId) =>
    set((state) => {
      const { [pursuitId]: _, ...rest } = state.draftMessages;
      return { draftMessages: rest };
    }),
    }),
    {
      name: 'inde-coaching-store',
      // Only persist draft messages - other state is transient
      partialize: (state) => ({
        draftMessages: state.draftMessages,
      }),
    }
  )
);
