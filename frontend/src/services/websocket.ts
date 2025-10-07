/**
 * WebSocket service for real-time notifications
 */

import { WebSocketMessage, NotificationMessage } from '@/types';
import { apiService } from './api';

type MessageHandler = (message: WebSocketMessage) => void;
type ConnectionHandler = (connected: boolean) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private messageHandlers: Map<string, MessageHandler[]> = new Map();
  private connectionHandlers: ConnectionHandler[] = [];
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 1000; // Start with 1 second
  private isConnecting = false;
  private shouldReconnect = true;

  private get wsUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_WS_HOST || window.location.host;
    const token = apiService.getToken();
    return `${protocol}//${host}/api/ws/notifications?token=${encodeURIComponent(token || '')}`;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      if (this.isConnecting) {
        reject(new Error('Already connecting'));
        return;
      }

      if (!apiService.isAuthenticated()) {
        reject(new Error('Not authenticated'));
        return;
      }

      this.isConnecting = true;
      this.shouldReconnect = true;

      try {
        this.ws = new WebSocket(this.wsUrl);

        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.reconnectInterval = 1000;
          this.notifyConnectionHandlers(true);
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason);
          this.isConnecting = false;
          this.ws = null;
          this.notifyConnectionHandlers(false);

          if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.isConnecting = false;

          if (this.ws?.readyState === WebSocket.CONNECTING) {
            reject(new Error('Failed to connect to WebSocket'));
          }
        };

      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  disconnect(): void {
    this.shouldReconnect = false;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    this.notifyConnectionHandlers(false);
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1), 30000);

    console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);

    this.reconnectTimer = setTimeout(() => {
      if (this.shouldReconnect) {
        this.connect().catch(() => {
          // Reconnect failed, will be scheduled again if attempts remain
        });
      }
    }, delay);
  }

  private handleMessage(message: WebSocketMessage): void {
    const handlers = this.messageHandlers.get(message.type) || [];
    const allHandlers = this.messageHandlers.get('*') || [];

    [...handlers, ...allHandlers].forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error('Error in message handler:', error);
      }
    });
  }

  private notifyConnectionHandlers(connected: boolean): void {
    this.connectionHandlers.forEach(handler => {
      try {
        handler(connected);
      } catch (error) {
        console.error('Error in connection handler:', error);
      }
    });
  }

  // Message subscription methods
  on(messageType: string, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, []);
    }

    this.messageHandlers.get(messageType)!.push(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.messageHandlers.get(messageType);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index > -1) {
          handlers.splice(index, 1);
        }
      }
    };
  }

  onConnection(handler: ConnectionHandler): () => void {
    this.connectionHandlers.push(handler);

    // Return unsubscribe function
    return () => {
      const index = this.connectionHandlers.indexOf(handler);
      if (index > -1) {
        this.connectionHandlers.splice(index, 1);
      }
    };
  }

  // Convenience methods for specific message types
  onReviewCreated(handler: (data: any) => void): () => void {
    return this.on('review_created', (message) => handler(message.data));
  }

  onReviewAssigned(handler: (data: any) => void): () => void {
    return this.on('review_assigned', (message) => handler(message.data));
  }

  onReviewCompleted(handler: (data: any) => void): () => void {
    return this.on('review_completed', (message) => handler(message.data));
  }

  onQueueUpdate(handler: (data: any) => void): () => void {
    return this.on('queue_update', (message) => handler(message.data));
  }

  onSystemAlert(handler: (data: any) => void): () => void {
    return this.on('system_alert', (message) => handler(message.data));
  }

  // Send messages to server
  send(message: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message:', message);
    }
  }

  ping(): void {
    this.send({
      type: 'ping',
      timestamp: new Date().toISOString(),
    });
  }

  subscribeToRoom(room: string): void {
    this.send({
      type: 'subscribe',
      room,
      timestamp: new Date().toISOString(),
    });
  }

  unsubscribeFromRoom(room: string): void {
    this.send({
      type: 'unsubscribe',
      room,
      timestamp: new Date().toISOString(),
    });
  }

  getStats(): void {
    this.send({
      type: 'get_stats',
      timestamp: new Date().toISOString(),
    });
  }

  // Status methods
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  isConnecting(): boolean {
    return this.isConnecting;
  }

  getConnectionState(): 'disconnected' | 'connecting' | 'connected' {
    if (this.isConnecting) return 'connecting';
    if (this.isConnected()) return 'connected';
    return 'disconnected';
  }
}

// Create singleton instance
export const webSocketService = new WebSocketService();

// Auto-connect when authenticated
apiService.client.interceptors.response.use((response) => {
  // If we just got a successful auth response, connect WebSocket
  if (response.config.url?.includes('/auth/login') && response.status === 200) {
    setTimeout(() => {
      webSocketService.connect().catch(console.error);
    }, 100);
  }
  return response;
});

// Auto-disconnect when logging out
const originalLogout = apiService.logout;
apiService.logout = async () => {
  webSocketService.disconnect();
  return originalLogout.call(apiService);
};