/**
 * Main Layout - Primary application layout with navigation and content area
 */

import React, { useState } from 'react';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Badge,
  Tooltip,
  Button,
  Divider,
  ListItemIcon,
  ListItemText,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  Menu as MenuIcon,
  AccountCircle,
  Notifications,
  Logout,
  Settings,
  Person,
  DarkMode,
  LightMode,
  Science,
  Wifi,
  WifiOff,
  Circle,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';

import {
  selectUser,
  logoutUser,
} from '@/store/slices/authSlice';
import {
  selectTheme,
  toggleTheme,
  selectSidebarOpen,
  toggleSidebar,
} from '@/store/slices/uiSlice';
import {
  selectUnreadCount,
  selectConnectionStatus,
  selectNotifications,
  markAllAsRead,
  clearAllNotifications,
} from '@/store/slices/notificationsSlice';
import { useWebSocket } from '@/components/WebSocketProvider';
import NotificationsList from '@/components/layout/NotificationsList';
import Sidebar from '@/components/layout/Sidebar';
import { AppDispatch } from '@/store';

interface MainLayoutProps {
  children: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const dispatch = useDispatch<AppDispatch>();
  const navigate = useNavigate();

  const user = useSelector(selectUser);
  const theme = useSelector(selectTheme);
  const sidebarOpen = useSelector(selectSidebarOpen);
  const unreadCount = useSelector(selectUnreadCount);
  const connectionStatus = useSelector(selectConnectionStatus);
  const notifications = useSelector(selectNotifications);

  const { isConnected, reconnect } = useWebSocket();

  const [profileMenuAnchor, setProfileMenuAnchor] = useState<null | HTMLElement>(null);
  const [notificationsMenuAnchor, setNotificationsMenuAnchor] = useState<null | HTMLElement>(null);

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setProfileMenuAnchor(event.currentTarget);
  };

  const handleProfileMenuClose = () => {
    setProfileMenuAnchor(null);
  };

  const handleNotificationsMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setNotificationsMenuAnchor(event.currentTarget);
  };

  const handleNotificationsMenuClose = () => {
    setNotificationsMenuAnchor(null);
  };

  const handleLogout = async () => {
    try {
      await dispatch(logoutUser()).unwrap();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
      // Force navigation even if logout fails
      navigate('/login');
    }
    handleProfileMenuClose();
  };

  const handleThemeToggle = () => {
    dispatch(toggleTheme());
  };

  const handleMarkAllAsRead = () => {
    dispatch(markAllAsRead());
  };

  const handleClearAll = () => {
    dispatch(clearAllNotifications());
    handleNotificationsMenuClose();
  };

  const getConnectionIcon = () => {
    if (isConnected) {
      return <Wifi color="success" />;
    } else {
      return <WifiOff color="error" />;
    }
  };

  const getConnectionTooltip = () => {
    if (isConnected) {
      return 'Connected to real-time updates';
    } else {
      return `Disconnected - Click to reconnect (Status: ${connectionStatus})`;
    }
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
          backgroundColor: 'primary.main',
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="toggle sidebar"
            onClick={() => dispatch(toggleSidebar())}
            edge="start"
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>

          <Science sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Kinexus AI
          </Typography>

          {/* Connection Status */}
          <Tooltip title={getConnectionTooltip()}>
            <IconButton
              color="inherit"
              onClick={isConnected ? undefined : reconnect}
              sx={{ mr: 1 }}
            >
              {getConnectionIcon()}
            </IconButton>
          </Tooltip>

          {/* Theme Toggle */}
          <Tooltip title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>
            <IconButton color="inherit" onClick={handleThemeToggle} sx={{ mr: 1 }}>
              {theme === 'light' ? <DarkMode /> : <LightMode />}
            </IconButton>
          </Tooltip>

          {/* Notifications */}
          <Tooltip title="Notifications">
            <IconButton
              color="inherit"
              onClick={handleNotificationsMenuOpen}
              sx={{ mr: 1 }}
            >
              <Badge badgeContent={unreadCount} color="error">
                <Notifications />
              </Badge>
            </IconButton>
          </Tooltip>

          {/* Profile Menu */}
          <Tooltip title="Account">
            <IconButton
              color="inherit"
              onClick={handleProfileMenuOpen}
            >
              <Avatar sx={{ width: 32, height: 32, bgcolor: 'secondary.main' }}>
                {user?.email?.charAt(0).toUpperCase() || 'U'}
              </Avatar>
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      {/* Sidebar */}
      <Sidebar open={sidebarOpen} />

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 0,
          mt: 8, // Account for app bar
          ml: sidebarOpen ? '240px' : '0px',
          transition: (theme) =>
            theme.transitions.create(['margin'], {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
        }}
      >
        {children}
      </Box>

      {/* Profile Menu */}
      <Menu
        anchorEl={profileMenuAnchor}
        open={Boolean(profileMenuAnchor)}
        onClose={handleProfileMenuClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        <Box sx={{ p: 2, minWidth: 200 }}>
          <Typography variant="subtitle2" gutterBottom>
            {user?.email || 'Unknown User'}
          </Typography>
          <Typography variant="caption" color="textSecondary">
            Role: {user?.role || 'Unknown'}
          </Typography>
        </Box>
        <Divider />

        <MenuItem onClick={handleProfileMenuClose}>
          <ListItemIcon>
            <Person />
          </ListItemIcon>
          <ListItemText>Profile</ListItemText>
        </MenuItem>

        <MenuItem onClick={handleProfileMenuClose}>
          <ListItemIcon>
            <Settings />
          </ListItemIcon>
          <ListItemText>Settings</ListItemText>
        </MenuItem>

        <Box sx={{ px: 2, py: 1 }}>
          <FormControlLabel
            control={
              <Switch
                checked={theme === 'dark'}
                onChange={handleThemeToggle}
                size="small"
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {theme === 'dark' ? <DarkMode fontSize="small" /> : <LightMode fontSize="small" />}
                Dark Mode
              </Box>
            }
          />
        </Box>

        <Divider />

        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <Logout color="error" />
          </ListItemIcon>
          <ListItemText>Logout</ListItemText>
        </MenuItem>
      </Menu>

      {/* Notifications Menu */}
      <Menu
        anchorEl={notificationsMenuAnchor}
        open={Boolean(notificationsMenuAnchor)}
        onClose={handleNotificationsMenuClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        PaperProps={{
          sx: {
            maxWidth: 400,
            maxHeight: 500,
          },
        }}
      >
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="subtitle1">
            Notifications ({unreadCount})
          </Typography>
          <Box>
            {unreadCount > 0 && (
              <Button size="small" onClick={handleMarkAllAsRead} sx={{ mr: 1 }}>
                Mark All Read
              </Button>
            )}
            {notifications.length > 0 && (
              <Button size="small" color="error" onClick={handleClearAll}>
                Clear All
              </Button>
            )}
          </Box>
        </Box>
        <Divider />

        <NotificationsList
          notifications={notifications.slice(0, 10)} // Show latest 10
          onNotificationClick={handleNotificationsMenuClose}
        />

        {notifications.length === 0 && (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="textSecondary">
              No notifications
            </Typography>
          </Box>
        )}
      </Menu>
    </Box>
  );
};

export default MainLayout;