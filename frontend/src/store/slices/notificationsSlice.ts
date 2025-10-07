/**
 * Notifications Redux slice
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { WebSocketMessage } from '@/types';

interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  persistent?: boolean;
  data?: any;
}

interface NotificationsState {
  items: Notification[];
  unreadCount: number;
  connectionStatus: 'disconnected' | 'connecting' | 'connected';
  wsStats: {
    total_connections: number;
    unique_users: number;
    rooms: number;
    connections_by_role: Record<string, number>;
  } | null;
}

const initialState: NotificationsState = {
  items: [],
  unreadCount: 0,
  connectionStatus: 'disconnected',
  wsStats: null,
};

const notificationsSlice = createSlice({
  name: 'notifications',
  initialState,
  reducers: {
    addNotification: (state, action: PayloadAction<Omit<Notification, 'id' | 'timestamp' | 'read'>>) => {
      const notification: Notification = {
        ...action.payload,
        id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
        timestamp: new Date(),
        read: false,
      };

      state.items.unshift(notification);
      state.unreadCount += 1;

      // Limit to 100 notifications
      if (state.items.length > 100) {
        const removed = state.items.splice(100);
        // Adjust unread count for removed unread notifications
        const removedUnread = removed.filter(n => !n.read).length;
        state.unreadCount = Math.max(0, state.unreadCount - removedUnread);
      }
    },

    markAsRead: (state, action: PayloadAction<string>) => {
      const notification = state.items.find(n => n.id === action.payload);
      if (notification && !notification.read) {
        notification.read = true;
        state.unreadCount = Math.max(0, state.unreadCount - 1);
      }
    },

    markAllAsRead: (state) => {
      state.items.forEach(notification => {
        notification.read = true;
      });
      state.unreadCount = 0;
    },

    removeNotification: (state, action: PayloadAction<string>) => {
      const index = state.items.findIndex(n => n.id === action.payload);
      if (index !== -1) {
        const notification = state.items[index];
        if (!notification.read) {
          state.unreadCount = Math.max(0, state.unreadCount - 1);
        }
        state.items.splice(index, 1);
      }
    },

    clearAllNotifications: (state) => {
      state.items = [];
      state.unreadCount = 0;
    },

    setConnectionStatus: (state, action: PayloadAction<'disconnected' | 'connecting' | 'connected'>) => {
      state.connectionStatus = action.payload;
    },

    updateWebSocketStats: (state, action: PayloadAction<NotificationsState['wsStats']>) => {
      state.wsStats = action.payload;
    },

    handleWebSocketMessage: (state, action: PayloadAction<WebSocketMessage>) => {
      const message = action.payload;

      // Handle different message types
      switch (message.type) {
        case 'review_created':
          state.items.unshift({
            id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
            type: 'info',
            title: 'New Review Created',
            message: `Review created for ${message.data.document?.title || 'document'}`,
            timestamp: new Date(),
            read: false,
            data: message.data,
          });
          state.unreadCount += 1;
          break;

        case 'review_assigned':
          state.items.unshift({
            id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
            type: 'info',
            title: 'Review Assigned',
            message: `Review assigned to ${message.data.reviewer?.name || 'reviewer'}`,
            timestamp: new Date(),
            read: false,
            data: message.data,
          });
          state.unreadCount += 1;
          break;

        case 'review_completed':
          const isApproved = message.data.status === 'approved' || message.data.status === 'approved_with_changes';
          state.items.unshift({
            id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
            type: isApproved ? 'success' : 'warning',
            title: `Review ${isApproved ? 'Approved' : 'Rejected'}`,
            message: `${message.data.document_title || 'Document'} review ${message.data.decision}`,
            timestamp: new Date(),
            read: false,
            data: message.data,
          });
          state.unreadCount += 1;
          break;

        case 'queue_update':
          // Don't create notifications for queue updates, just update data
          break;

        case 'system_alert':
          state.items.unshift({
            id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
            type: 'warning',
            title: 'System Alert',
            message: message.data.message || 'System notification',
            timestamp: new Date(),
            read: false,
            persistent: true,
            data: message.data,
          });
          state.unreadCount += 1;
          break;

        case 'connection_stats':
          state.wsStats = message.data;
          break;

        default:
          // Log unknown message types for debugging
          console.log('Unknown WebSocket message type:', message.type);
      }

      // Limit notifications
      if (state.items.length > 100) {
        const removed = state.items.splice(100);
        const removedUnread = removed.filter(n => !n.read).length;
        state.unreadCount = Math.max(0, state.unreadCount - removedUnread);
      }
    },
  },
});

export const {
  addNotification,
  markAsRead,
  markAllAsRead,
  removeNotification,
  clearAllNotifications,
  setConnectionStatus,
  updateWebSocketStats,
  handleWebSocketMessage,
} = notificationsSlice.actions;

export default notificationsSlice.reducer;

// Selectors
export const selectNotifications = (state: { notifications: NotificationsState }) => state.notifications.items;
export const selectUnreadCount = (state: { notifications: NotificationsState }) => state.notifications.unreadCount;
export const selectConnectionStatus = (state: { notifications: NotificationsState }) => state.notifications.connectionStatus;
export const selectWebSocketStats = (state: { notifications: NotificationsState }) => state.notifications.wsStats;