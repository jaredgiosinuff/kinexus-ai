/**
 * WebSocket Provider - Manages WebSocket connection and real-time updates
 */

import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';

import { selectUser } from '@/store/slices/authSlice';
import {
  setConnectionStatus,
  handleWebSocketMessage,
  updateWebSocketStats,
} from '@/store/slices/notificationsSlice';
import {
  updateReviewInList,
  addReviewToList,
  removeReviewFromList,
} from '@/store/slices/reviewsSlice';
import { addNotification } from '@/store/slices/notificationsSlice';
import { WebSocketMessage } from '@/types';
import { AppDispatch } from '@/store';

interface WebSocketContextType {
  isConnected: boolean;
  reconnect: () => void;
  disconnect: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

interface WebSocketProviderProps {
  children: React.ReactNode;
}

const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const dispatch = useDispatch<AppDispatch>();
  const user = useSelector(selectUser);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const maxReconnectAttempts = 5;
  const reconnectDelay = 5000; // 5 seconds
  const heartbeatInterval = 30000; // 30 seconds

  const getWebSocketUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NODE_ENV === 'development'
      ? 'localhost:8000'
      : window.location.host;
    return `${protocol}//${host}/api/ws`;
  };

  const sendHeartbeat = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'ping' }));
    }
  };

  const handleMessage = (event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);

      // Handle pong responses
      if (message.type === 'pong') {
        return;
      }

      // Dispatch to notifications slice for general handling
      dispatch(handleWebSocketMessage(message));

      // Handle specific message types for reviews
      switch (message.type) {
        case 'review_created':
          if (message.data) {
            dispatch(addReviewToList(message.data));
          }
          break;

        case 'review_assigned':
        case 'review_completed':
          if (message.data) {
            dispatch(updateReviewInList(message.data));
          }
          break;

        case 'review_deleted':
          if (message.data?.id) {
            dispatch(removeReviewFromList(message.data.id));
          }
          break;

        case 'system_alert':
          // System alerts are handled by the notifications slice
          break;

        case 'connection_stats':
          if (message.data) {
            dispatch(updateWebSocketStats(message.data));
          }
          break;

        default:
          console.log('Unhandled WebSocket message type:', message.type);
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  };

  const connect = () => {
    if (!user) {
      return;
    }

    try {
      dispatch(setConnectionStatus('connecting'));
      setIsConnected(false);

      const token = localStorage.getItem('token');
      const wsUrl = `${getWebSocketUrl()}?token=${encodeURIComponent(token || '')}`;

      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setReconnectAttempts(0);
        dispatch(setConnectionStatus('connected'));

        // Start heartbeat
        heartbeatIntervalRef.current = setInterval(sendHeartbeat, heartbeatInterval);

        // Join user room for personal notifications
        wsRef.current?.send(JSON.stringify({
          type: 'join_room',
          room: `user_${user.id}`,
        }));

        // Join reviews room for review updates
        wsRef.current?.send(JSON.stringify({
          type: 'join_room',
          room: 'reviews',
        }));
      };

      wsRef.current.onmessage = handleMessage;

      wsRef.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        dispatch(setConnectionStatus('disconnected'));

        // Clear heartbeat
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }

        // Attempt to reconnect if not manually closed
        if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
          const delay = reconnectDelay * Math.pow(2, reconnectAttempts); // Exponential backoff
          console.log(`Attempting to reconnect in ${delay / 1000} seconds...`);

          reconnectTimeoutRef.current = setTimeout(() => {
            setReconnectAttempts(prev => prev + 1);
            connect();
          }, delay);
        } else if (reconnectAttempts >= maxReconnectAttempts) {
          console.error('Max reconnection attempts reached');
          dispatch(addNotification({
            type: 'error',
            title: 'Connection Lost',
            message: 'Unable to reconnect to server. Please refresh the page.',
            persistent: true,
          }));
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        dispatch(setConnectionStatus('disconnected'));
      };

    } catch (error) {
      console.error('Error connecting to WebSocket:', error);
      dispatch(setConnectionStatus('disconnected'));
    }
  };

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }

    setIsConnected(false);
    setReconnectAttempts(0);
    dispatch(setConnectionStatus('disconnected'));
  };

  const reconnect = () => {
    disconnect();
    setReconnectAttempts(0);
    setTimeout(() => connect(), 1000);
  };

  // Connect when user is available
  useEffect(() => {
    if (user) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [user]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, []);

  // Handle visibility change to reconnect when tab becomes active
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && user && !isConnected) {
        console.log('Tab became active, attempting to reconnect...');
        reconnect();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [user, isConnected]);

  const contextValue: WebSocketContextType = {
    isConnected,
    reconnect,
    disconnect,
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

export default WebSocketProvider;