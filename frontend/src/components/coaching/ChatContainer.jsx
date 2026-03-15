import { useEffect, useRef, useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useCoachingStore } from '../../stores/coachingStore';
import { useAuthStore } from '../../stores/authStore';
import { usePursuitStore } from '../../stores/pursuitStore';
import { CoachingWebSocket } from '../../api/websocket';
import { coachingApi } from '../../api/coaching';
import { pursuitsApi } from '../../api/pursuits';
import { queryClient } from '../../lib/queryClient';
import { CoachMessage } from './CoachMessage';
import { InnovatorMessage } from './InnovatorMessage';
import { StreamingMessage } from './StreamingMessage';
import { MomentNotification } from './MomentNotification';
import { ChatHeader } from './ChatHeader';
import { ChatInput } from './ChatInput';
import { LoadingSpinner } from '../LoadingSpinner';
import { cn } from '../../lib/utils';

// Mode-specific accent colors for the top border
const MODE_ACCENTS = {
  coaching: 'border-t-inde-500',
  vision: 'border-t-phase-vision',
  fear: 'border-t-phase-pitch',
  retrospective: 'border-t-phase-build',
  ems_review: 'border-t-inde-500',
  crisis: 'border-t-health-atrisk',
  non_directive: 'border-t-zinc-500',
};

export function ChatContainer({ pursuitId, className, initialMessage }) {
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const [useRestFallback, setUseRestFallback] = useState(false);
  const [initialMessageSent, setInitialMessageSent] = useState(false);

  // Store selectors
  const messages = useCoachingStore((s) => s.messages);
  const isStreaming = useCoachingStore((s) => s.isStreaming);
  const mode = useCoachingStore((s) => s.mode);
  const healthScore = useCoachingStore((s) => s.healthScore);
  const healthZone = useCoachingStore((s) => s.healthZone);
  const streamBuffer = useCoachingStore((s) => s.streamBuffer);

  const token = useAuthStore((s) => s.token);
  const pursuitList = usePursuitStore((s) => s.pursuitList);
  const activePursuit = usePursuitStore((s) =>
    s.pursuitList.find((p) => p.id === pursuitId)
  );

  // Auto-scroll on new messages or streaming content
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamBuffer, isStreaming]);

  // Load conversation history
  useEffect(() => {
    const loadHistory = async () => {
      setIsLoadingHistory(true);
      try {
        const response = await coachingApi.getHistory(pursuitId);
        // Backend returns { history: [...] } or { messages: [...] }
        const historyMessages = response.data.history || response.data.messages || [];
        useCoachingStore.getState().loadHistory(
          historyMessages.map((msg) => ({
            role: msg.role === 'assistant' ? 'assistant' : 'user',
            content: msg.content || msg.message,
            timestamp: msg.timestamp || msg.created_at,
            mode: msg.mode,
          }))
        );
      } catch (error) {
        console.error('Failed to load chat history:', error);
        // Don't fail - just start with empty history
        useCoachingStore.getState().clearMessages();
      } finally {
        setIsLoadingHistory(false);
      }
    };

    loadHistory();
  }, [pursuitId]);

  // WebSocket connection lifecycle
  useEffect(() => {
    if (!token || !pursuitId) return;

    // Clear previous state
    useCoachingStore.getState().clearStreamBuffer();
    useCoachingStore.getState().setStreaming(false);

    const ws = new CoachingWebSocket(pursuitId, {
      onOpen: () => {
        setWsConnected(true);
        setUseRestFallback(false);
        useCoachingStore.getState().setConnected(true);
      },
      onChunk: (chunk) => {
        useCoachingStore.getState().setStreaming(true);
        useCoachingStore.getState().appendStreamChunk(chunk);
      },
      onComplete: () => {
        useCoachingStore.getState().finalizeStream();
      },
      onMoment: (moment) => {
        useCoachingStore.getState().addMessage({
          role: 'moment',
          type: moment.type,
          content: moment.description || moment.message,
          data: moment,
        });
      },
      onHealth: (data) => {
        useCoachingStore.getState().setHealth(data.score, data.zone);
      },
      onIntervention: (intervention) => {
        useCoachingStore.getState().setActiveIntervention(intervention);
      },
      onScaffoldUpdate: (data) => {
        // Could update pursuit store with new scaffold state
        if (data.mode) {
          useCoachingStore.getState().setMode(data.mode);
        }
      },
      onError: (error) => {
        console.error('WebSocket error:', error);
        useCoachingStore.getState().setError(error.message || 'Connection error');
      },
      onClose: (event) => {
        setWsConnected(false);
        useCoachingStore.getState().setConnected(false);

        // If streaming was in progress, finalize it
        if (useCoachingStore.getState().isStreaming) {
          useCoachingStore.getState().finalizeStream();
        }

        // If not a clean close and max reconnects reached, fallback to REST
        if (!event.wasClean) {
          setUseRestFallback(true);
        }
      },
    });

    ws.connect(token);
    wsRef.current = ws;

    return () => {
      ws.disconnect();
      wsRef.current = null;
    };
  }, [pursuitId, token]);

  // Handle EVAPORATE command
  const handleEvaporateCommand = useCallback(
    async (pursuitName) => {
      // Find the pursuit by name (case-insensitive)
      const targetPursuit = pursuitList.find(
        (p) => p.name?.toLowerCase() === pursuitName.toLowerCase()
      );

      if (!targetPursuit) {
        useCoachingStore.getState().addAssistantMessage(
          `Could not find a pursuit named "${pursuitName}". Please check the name and try again.`
        );
        return;
      }

      try {
        await pursuitsApi.evaporate(targetPursuit.id);

        // Remove from local store
        usePursuitStore.getState().removePursuit(targetPursuit.id);

        // Invalidate queries to refresh data
        queryClient.invalidateQueries({ queryKey: ['pursuits'] });

        // If we just evaporated the current pursuit, navigate to dashboard
        if (targetPursuit.id === pursuitId) {
          useCoachingStore.getState().addAssistantMessage(
            `Pursuit "${targetPursuit.name}" has been evaporated. Redirecting to dashboard...`
          );
          setTimeout(() => {
            navigate('/');
          }, 1500);
        } else {
          useCoachingStore.getState().addAssistantMessage(
            `Pursuit "${targetPursuit.name}" has been evaporated and removed from your portfolio.`
          );
        }
      } catch (error) {
        console.error('Failed to evaporate pursuit:', error);
        useCoachingStore.getState().addAssistantMessage(
          `Failed to evaporate pursuit "${pursuitName}". Please try again.`
        );
      }
    },
    [pursuitList, pursuitId, navigate]
  );

  // Send message handler
  const sendMessage = useCallback(
    async (text) => {
      if (!text.trim() || isStreaming) return;

      // Check for EVAPORATE command
      const evaporateMatch = text.trim().match(/^EVAPORATE\s+(.+)$/i);
      if (evaporateMatch) {
        const pursuitName = evaporateMatch[1].trim();
        useCoachingStore.getState().addUserMessage(text);
        await handleEvaporateCommand(pursuitName);
        return;
      }

      // Add innovator message to state
      useCoachingStore.getState().addUserMessage(text);

      if (useRestFallback || !wsConnected) {
        // REST fallback
        try {
          useCoachingStore.getState().setStreaming(true);
          const response = await coachingApi.sendMessage(pursuitId, text, mode);
          // API returns { response: "...", pursuit_id: "...", ... }
          useCoachingStore.getState().addAssistantMessage(
            response.data.response || response.data.content || response.data.message
          );
          // Update health if provided
          if (response.data.health_zone) {
            useCoachingStore.getState().setHealth(null, response.data.health_zone);
          }
        } catch (error) {
          console.error('Failed to send message:', error);
          useCoachingStore.getState().setError('Failed to send message');
          useCoachingStore.getState().addAssistantMessage(
            'Sorry, I encountered an issue. Please try again.'
          );
        } finally {
          useCoachingStore.getState().setStreaming(false);
        }
      } else {
        // WebSocket send - set streaming immediately to show "thinking" indicator
        useCoachingStore.getState().setStreaming(true);
        wsRef.current?.sendWithMode(text, mode);
      }
    },
    [isStreaming, pursuitId, mode, useRestFallback, wsConnected, handleEvaporateCommand]
  );

  // Auto-send initial message (from NewPursuitPage spark)
  useEffect(() => {
    // Only send if:
    // 1. We have an initial message
    // 2. History has loaded
    // 3. There are no existing messages (new conversation)
    // 4. We haven't already sent it
    // 5. Either WebSocket is connected or we're using REST fallback
    if (
      initialMessage &&
      !isLoadingHistory &&
      messages.length === 0 &&
      !initialMessageSent &&
      (wsConnected || useRestFallback)
    ) {
      setInitialMessageSent(true);
      // Small delay to ensure UI is ready
      setTimeout(() => {
        sendMessage(initialMessage);
      }, 100);
    }
  }, [initialMessage, isLoadingHistory, messages.length, initialMessageSent, wsConnected, useRestFallback, sendMessage]);

  // Register sendMessage handler for external components (sidebar panels)
  useEffect(() => {
    useCoachingStore.getState().registerSendHandler(sendMessage);
    return () => {
      useCoachingStore.getState().unregisterSendHandler();
    };
  }, [sendMessage]);

  // Handle moment click
  const handleMomentClick = (moment) => {
    // Could trigger a coaching discussion about the moment
    sendMessage(`Let's discuss this ${moment.type.toLowerCase().replace('_', ' ')}.`);
  };

  if (isLoadingHistory) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner />
      </div>
    );
  }

  // Get mode accent
  const modeAccent = MODE_ACCENTS[mode] || MODE_ACCENTS.coaching;

  return (
    <div className={cn('flex flex-col h-full min-h-0 border-t-2 transition-colors duration-300', modeAccent, className)}>
      {/* Chat header */}
      <ChatHeader
        mode={mode}
        healthScore={healthScore}
        healthZone={healthZone}
        phase={activePursuit?.phase}
      />

      {/* Connection status indicator */}
      {!wsConnected && !useRestFallback && (
        <div className="px-4 py-2 bg-amber-500/10 border-b border-amber-500/20 text-center">
          <span className="text-caption text-amber-400">
            Connecting to coaching service...
          </span>
        </div>
      )}

      {useRestFallback && (
        <div className="px-4 py-2 bg-surface-3 border-b border-surface-border text-center">
          <span className="text-caption text-zinc-500">
            Using standard messaging (streaming unavailable)
          </span>
        </div>
      )}

      {/* Message list */}
      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-6 space-y-4 scroll-smooth">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center mb-4 shadow-glow-inde">
              <span className="text-white text-2xl font-bold font-display">ID</span>
            </div>
            <h2 className="text-display-sm text-zinc-300 mb-2">
              Welcome to your coaching session
            </h2>
            <p className="text-body-md text-zinc-500 max-w-md">
              Share your thoughts, ideas, or questions. I'm here to help you
              navigate your innovation journey.
            </p>
          </div>
        )}

        {messages.map((msg, i) => {
          if (msg.role === 'user') {
            return <InnovatorMessage key={msg.id || i} message={msg} />;
          }
          if (msg.role === 'moment') {
            return (
              <MomentNotification
                key={msg.id || i}
                moment={msg}
                onClick={() => handleMomentClick(msg)}
              />
            );
          }
          return <CoachMessage key={msg.id || i} message={msg} />;
        })}

        {/* Streaming message */}
        <StreamingMessage />

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <ChatInput onSend={sendMessage} disabled={isStreaming} mode={mode} hasMessages={messages.length > 0} />
    </div>
  );
}

export default ChatContainer;
