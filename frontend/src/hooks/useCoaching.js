import { useEffect, useCallback, useRef } from 'react';
import { useCoachingStore } from '../stores/coachingStore';
import { useAuthStore } from '../stores/authStore';
import { coachingApi } from '../api/coaching';
import { CoachingWebSocket } from '../api/websocket';

/**
 * Hook for managing coaching session.
 */
export function useCoaching(pursuitId) {
  const socketRef = useRef(null);
  const { token } = useAuthStore();
  const {
    messages,
    isStreaming,
    streamBuffer,
    mode,
    healthScore,
    healthZone,
    activeIntervention,
    isConnected,
    error,
    addUserMessage,
    setStreaming,
    appendStreamChunk,
    finalizeStream,
    setHealth,
    setActiveIntervention,
    setConnected,
    setError,
    clearMessages,
    loadHistory,
    setMode,
  } = useCoachingStore();

  // Connect WebSocket
  useEffect(() => {
    if (!pursuitId || !token) return;

    const socket = new CoachingWebSocket(pursuitId, {
      onOpen: () => {
        setConnected(true);
      },
      onChunk: (chunk) => {
        setStreaming(true);
        appendStreamChunk(chunk);
      },
      onComplete: () => {
        finalizeStream();
      },
      onMoment: (moment) => {
        // Handle moment detection
        console.log('Moment detected:', moment);
      },
      onHealth: (data) => {
        setHealth(data.score, data.zone);
      },
      onIntervention: (intervention) => {
        setActiveIntervention(intervention);
      },
      onError: (err) => {
        setError(err.message || 'WebSocket error');
      },
      onClose: () => {
        setConnected(false);
      },
    });

    socket.connect(token);
    socketRef.current = socket;

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [pursuitId, token]);

  // Load conversation history
  useEffect(() => {
    if (!pursuitId) return;

    const fetchHistory = async () => {
      try {
        const response = await coachingApi.getHistory(pursuitId);
        loadHistory(response.data.messages || []);
      } catch (err) {
        console.error('Failed to load history:', err);
      }
    };

    fetchHistory();
  }, [pursuitId, loadHistory]);

  // Send message via WebSocket
  const sendMessage = useCallback(
    (content) => {
      if (!content.trim()) return;

      addUserMessage(content);

      if (socketRef.current?.isConnected()) {
        socketRef.current.sendWithMode(content, mode);
      } else {
        // Fallback to REST API
        setStreaming(true);
        coachingApi
          .sendMessage(pursuitId, content, mode)
          .then((response) => {
            appendStreamChunk(response.data.response);
            finalizeStream();
          })
          .catch((err) => {
            setError(err.message || 'Failed to send message');
            setStreaming(false);
          });
      }
    },
    [pursuitId, mode, addUserMessage, appendStreamChunk, finalizeStream, setStreaming, setError]
  );

  // Mode-specific actions
  const startVisionMode = useCallback(async () => {
    setMode('vision');
    try {
      await coachingApi.startVisionMode(pursuitId);
    } catch (err) {
      setError(err.message);
    }
  }, [pursuitId, setMode, setError]);

  const startFearMode = useCallback(async () => {
    setMode('fear');
    try {
      await coachingApi.startFearMode(pursuitId);
    } catch (err) {
      setError(err.message);
    }
  }, [pursuitId, setMode, setError]);

  const startRetrospective = useCallback(
    async (scope = 'recent') => {
      setMode('retrospective');
      try {
        await coachingApi.startRetrospective(pursuitId, scope);
      } catch (err) {
        setError(err.message);
      }
    },
    [pursuitId, setMode, setError]
  );

  const resetMode = useCallback(() => {
    setMode('coaching');
  }, [setMode]);

  return {
    messages,
    isStreaming,
    streamBuffer,
    mode,
    healthScore,
    healthZone,
    activeIntervention,
    isConnected,
    error,
    sendMessage,
    startVisionMode,
    startFearMode,
    startRetrospective,
    resetMode,
    clearMessages,
    setMode,
  };
}
