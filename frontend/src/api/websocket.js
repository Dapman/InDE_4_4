/**
 * WebSocket client for coaching streaming.
 *
 * Connects to ws://host:8000/ws/coaching/{pursuit_id}
 * Handles reconnection, auth, and message parsing.
 */
export class CoachingWebSocket {
  constructor(pursuitId, handlers) {
    this.pursuitId = pursuitId;
    this.handlers = handlers; // { onChunk, onMoment, onHealth, onIntervention, onError, onClose }
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
    this.connectionTimeout = null;
    this.connected = false;
  }

  connect(token) {
    // In production, derive WebSocket URL from current location
    // In development, use localhost
    const baseUrl = import.meta.env.VITE_WS_URL ?? (
      import.meta.env.DEV
        ? 'ws://localhost:8000'
        : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
    );
    const url = `${baseUrl}/ws/coaching/${this.pursuitId}?token=${token}`;

    this.ws = new WebSocket(url);

    // v4.0: Add connection timeout - fall back to REST if no connection in 5s
    this.connectionTimeout = setTimeout(() => {
      if (!this.connected) {
        console.warn('WebSocket connection timeout - falling back to REST');
        this.maxReconnectAttempts = 0; // Prevent reconnection
        this.ws?.close();
        // Trigger close handler with unclean close to enable REST fallback
        this.handlers.onClose?.({ wasClean: false, code: 1006, reason: 'Connection timeout' });
      }
    }, 5000);

    this.ws.onopen = () => {
      this.connected = true;
      clearTimeout(this.connectionTimeout);
      this.reconnectAttempts = 0;
      this.handlers.onOpen?.();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        switch (data.type) {
          case 'coach_response':
            this.handlers.onChunk?.(data.content);
            break;
          case 'coach_response_complete':
            this.handlers.onComplete?.(data);
            break;
          case 'moment_detected':
            this.handlers.onMoment?.(data.moment);
            break;
          case 'health_update':
            this.handlers.onHealth?.(data);
            break;
          case 'intervention':
            this.handlers.onIntervention?.(data.intervention);
            break;
          case 'scaffold_update':
            this.handlers.onScaffoldUpdate?.(data);
            break;
          case 'error':
            this.handlers.onError?.(new Error(data.message));
            break;
          default:
            break;
        }
      } catch (err) {
        this.handlers.onError?.(err);
      }
    };

    this.ws.onclose = (event) => {
      this.connected = false;
      clearTimeout(this.connectionTimeout);

      if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
        setTimeout(() => {
          this.reconnectAttempts++;
          this.connect(token);
        }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts));
      }
      this.handlers.onClose?.(event);
    };

    this.ws.onerror = (error) => {
      clearTimeout(this.connectionTimeout);
      this.handlers.onError?.(error);
    };
  }

  send(message) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'message', content: message }));
    }
  }

  sendWithMode(message, mode) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'message', content: message, mode }));
    }
  }

  disconnect() {
    this.maxReconnectAttempts = 0; // Prevent reconnection
    clearTimeout(this.connectionTimeout);
    this.ws?.close();
  }

  isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

/**
 * Create a WebSocket connection with automatic token injection.
 */
export function createCoachingSocket(pursuitId, handlers) {
  const socket = new CoachingWebSocket(pursuitId, handlers);
  return socket;
}
