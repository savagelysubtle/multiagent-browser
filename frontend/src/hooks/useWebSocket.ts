import { useEffect, useRef, useCallback } from 'react';
import { useAppStore } from '../stores/useAppStore';
import { authService } from '../services/authService';
import { WebSocketMessage, Task } from '../types';

interface UseWebSocketOptions {
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
    heartbeatInterval = 30000,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const heartbeatTimerRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);

  const {
    user,
    connectionStatus,
    setConnectionStatus,
    updateTask,
    addTask,
  } = useAppStore();

  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

  const cleanup = useCallback(() => {
    if (heartbeatTimerRef.current) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);

      switch (message.type) {
        case 'task_created':
          console.log('Task created:', message);
          // Task will be added when we get the full task data
          break;

        case 'task_update':
          if (message.task_id && message.data) {
            const taskUpdate: Partial<Task> = {
              status: message.data.status,
              result: message.data.result,
              error: message.data.error,
              progress: message.data.progress,
            };

            if (message.data.status === 'completed' || message.data.status === 'failed') {
              taskUpdate.completed_at = new Date().toISOString();
            }

            updateTask(message.task_id, taskUpdate);
          }
          break;

        case 'ping':
          // Respond to ping with pong
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'pong' }));
          }
          break;

        case 'queued_message':
          // Handle queued messages from when we were offline
          if (message.data) {
            handleMessage({ data: JSON.stringify(message.data) } as MessageEvent);
          }
          break;

        case 'notification':
          // Handle general notifications
          console.log('Notification:', message.data);
          break;

        default:
          console.log('Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }, [updateTask]);

  const connect = useCallback(() => {
    // Temporarily disable WebSocket to debug the blank dashboard issue
    console.warn('WebSocket connection temporarily disabled for debugging');
    return;

    if (!user || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const token = authService.getToken();
    if (!token) {
      console.error('No auth token available for WebSocket connection');
      return;
    }

    try {
      setConnectionStatus('reconnecting');

      const ws = new WebSocket(`${wsUrl}?token=${encodeURIComponent(token)}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setConnectionStatus('connected');
        reconnectAttemptsRef.current = 0;

        // Start heartbeat
        heartbeatTimerRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, heartbeatInterval);
      };

      ws.onmessage = handleMessage;

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setConnectionStatus('disconnected');
        cleanup();

        // Don't reconnect if authentication failed
        if (event.code === 4001) {
          console.error('WebSocket authentication failed');
          return;
        }

        // Attempt to reconnect if not a normal closure and we haven't exceeded max attempts
        if (
          event.code !== 1000 &&
          reconnectAttemptsRef.current < maxReconnectAttempts &&
          user
        ) {
          reconnectAttemptsRef.current++;
          console.log(`Attempting to reconnect (${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`);

          reconnectTimerRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval * Math.pow(2, reconnectAttemptsRef.current - 1)); // Exponential backoff
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          console.error('Max reconnection attempts reached');
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('disconnected');
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionStatus('disconnected');
    }
  }, [user, wsUrl, handleMessage, setConnectionStatus, cleanup, reconnectInterval, maxReconnectAttempts, heartbeatInterval]);

  const disconnect = useCallback(() => {
    cleanup();
    if (wsRef.current) {
      wsRef.current.close(1000, 'User initiated disconnect');
      wsRef.current = null;
    }
    setConnectionStatus('disconnected');
  }, [cleanup, setConnectionStatus]);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    console.warn('WebSocket not connected, message not sent:', message);
    return false;
  }, []);

  // Connect when user is available
  useEffect(() => {
    if (user && connectionStatus === 'disconnected') {
      connect();
    } else if (!user && wsRef.current) {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [user, connect, disconnect, connectionStatus]);

  return {
    connectionStatus,
    connect,
    disconnect,
    sendMessage,
    isConnected: connectionStatus === 'connected',
  };
}