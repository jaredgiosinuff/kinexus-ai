/**
 * Notifications List - Component for displaying notification items
 */

import React from 'react';
import {
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Box,
  IconButton,
  Chip,
  Tooltip,
} from '@mui/material';
import {
  Assignment,
  CheckCircle,
  Cancel,
  Warning,
  Info,
  Close,
  Circle,
  Person,
  Notifications,
} from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import { formatDistanceToNow } from 'date-fns';

import {
  markAsRead,
  removeNotification,
} from '@/store/slices/notificationsSlice';
import { AppDispatch } from '@/store';

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

interface NotificationsListProps {
  notifications: Notification[];
  onNotificationClick?: () => void;
}

const NotificationsList: React.FC<NotificationsListProps> = ({
  notifications,
  onNotificationClick,
}) => {
  const dispatch = useDispatch<AppDispatch>();

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle color="success" />;
      case 'error':
        return <Cancel color="error" />;
      case 'warning':
        return <Warning color="warning" />;
      case 'info':
      default:
        return <Info color="info" />;
    }
  };

  const getTypeIcon = (notification: Notification) => {
    // Special icons based on notification content
    if (notification.title.includes('Review')) {
      return <Assignment color="primary" />;
    }
    if (notification.title.includes('User') || notification.title.includes('Assigned')) {
      return <Person color="primary" />;
    }
    return getNotificationIcon(notification.type);
  };

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.read) {
      dispatch(markAsRead(notification.id));
    }

    // Handle navigation based on notification data
    if (notification.data?.reviewId) {
      window.open(`/reviews/${notification.data.reviewId}`, '_blank');
    }

    onNotificationClick?.();
  };

  const handleRemoveNotification = (e: React.MouseEvent, notificationId: string) => {
    e.stopPropagation();
    dispatch(removeNotification(notificationId));
  };

  const formatTimestamp = (timestamp: Date) => {
    try {
      return formatDistanceToNow(new Date(timestamp), { addSuffix: true });
    } catch (error) {
      return 'Unknown time';
    }
  };

  if (notifications.length === 0) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Notifications color="disabled" sx={{ fontSize: 48, mb: 1 }} />
        <Typography variant="body2" color="textSecondary">
          No notifications yet
        </Typography>
      </Box>
    );
  }

  return (
    <List sx={{ py: 0, maxHeight: 400, overflow: 'auto' }}>
      {notifications.map((notification) => (
        <ListItem
          key={notification.id}
          disablePadding
          secondaryAction={
            <IconButton
              edge="end"
              aria-label="dismiss"
              size="small"
              onClick={(e) => handleRemoveNotification(e, notification.id)}
            >
              <Close fontSize="small" />
            </IconButton>
          }
        >
          <ListItemButton
            onClick={() => handleNotificationClick(notification)}
            sx={{
              alignItems: 'flex-start',
              py: 1.5,
              pr: 6, // Make room for close button
              backgroundColor: notification.read ? 'transparent' : 'action.hover',
              '&:hover': {
                backgroundColor: 'action.selected',
              },
            }}
          >
            <ListItemIcon sx={{ mt: 0.5 }}>
              <Box sx={{ position: 'relative' }}>
                {getTypeIcon(notification)}
                {!notification.read && (
                  <Circle
                    sx={{
                      position: 'absolute',
                      top: -2,
                      right: -2,
                      fontSize: 8,
                      color: 'primary.main',
                    }}
                  />
                )}
              </Box>
            </ListItemIcon>

            <ListItemText
              primary={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                  <Typography
                    variant="subtitle2"
                    sx={{
                      fontWeight: notification.read ? 'normal' : 'bold',
                      flex: 1,
                    }}
                  >
                    {notification.title}
                  </Typography>
                  {notification.persistent && (
                    <Chip
                      label="Important"
                      size="small"
                      color="warning"
                      sx={{ height: 16, fontSize: '0.65rem' }}
                    />
                  )}
                </Box>
              }
              secondary={
                <Box>
                  <Typography
                    variant="body2"
                    color="textSecondary"
                    sx={{
                      mb: 0.5,
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {notification.message}
                  </Typography>
                  <Typography variant="caption" color="textSecondary">
                    {formatTimestamp(notification.timestamp)}
                  </Typography>
                </Box>
              }
            />
          </ListItemButton>
        </ListItem>
      ))}
    </List>
  );
};

export default NotificationsList;