/**
 * Notifications Provider - Manages toast notifications and notification panel
 */

import React, { useEffect } from 'react';
import { Snackbar, Alert, Slide, SlideProps } from '@mui/material';
import { useDispatch, useSelector } from 'react-redux';

import {
  selectNotifications,
  removeNotification,
  markAsRead,
} from '@/store/slices/notificationsSlice';
import { AppDispatch } from '@/store';

interface NotificationsProviderProps {
  children: React.ReactNode;
}

// Slide transition component
const SlideTransition = (props: SlideProps) => {
  return <Slide {...props} direction="down" />;
};

const NotificationsProvider: React.FC<NotificationsProviderProps> = ({ children }) => {
  const dispatch = useDispatch<AppDispatch>();
  const notifications = useSelector(selectNotifications);

  // Show toast notifications for new items
  const [currentToast, setCurrentToast] = React.useState<string | null>(null);

  // Find the most recent unread notification to show as toast
  const latestNotification = notifications.find(n => !n.read && !n.persistent);

  useEffect(() => {
    if (latestNotification && latestNotification.id !== currentToast) {
      setCurrentToast(latestNotification.id);

      // Auto-dismiss non-persistent notifications after 6 seconds
      const timer = setTimeout(() => {
        handleCloseToast();
      }, 6000);

      return () => clearTimeout(timer);
    }
  }, [latestNotification, currentToast]);

  const handleCloseToast = () => {
    if (currentToast) {
      // Mark as read when dismissed
      dispatch(markAsRead(currentToast));
      setCurrentToast(null);
    }
  };

  const getAlertSeverity = (type: string) => {
    switch (type) {
      case 'success':
        return 'success';
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
      default:
        return 'info';
    }
  };

  return (
    <>
      {children}

      {/* Toast Notification */}
      <Snackbar
        open={!!currentToast && !!latestNotification}
        autoHideDuration={6000}
        onClose={handleCloseToast}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
        TransitionComponent={SlideTransition}
        sx={{ mt: 8 }} // Account for app bar
      >
        {latestNotification && (
          <Alert
            onClose={handleCloseToast}
            severity={getAlertSeverity(latestNotification.type)}
            variant="filled"
            sx={{
              minWidth: '300px',
              maxWidth: '500px',
            }}
          >
            <strong>{latestNotification.title}</strong>
            {latestNotification.message && (
              <div style={{ marginTop: '4px' }}>
                {latestNotification.message}
              </div>
            )}
          </Alert>
        )}
      </Snackbar>
    </>
  );
};

export default NotificationsProvider;