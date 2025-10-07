/**
 * Sidebar - Navigation sidebar component
 */

import React from 'react';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Box,
  Typography,
  Chip,
} from '@mui/material';
import {
  Dashboard,
  Assignment,
  Description,
  Analytics,
  Settings,
  Group,
  History,
  AutoAwesome,
} from '@mui/icons-material';
import { useLocation, useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';

import { selectUser } from '@/store/slices/authSlice';
import { selectReviews, selectMyReviews } from '@/store/slices/reviewsSlice';

interface SidebarProps {
  open: boolean;
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactElement;
  path: string;
  badge?: number;
  disabled?: boolean;
  roles?: string[];
}

const Sidebar: React.FC<SidebarProps> = ({ open }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const user = useSelector(selectUser);
  const reviews = useSelector(selectReviews);
  const myReviews = useSelector(selectMyReviews);

  const pendingReviews = reviews.filter(r => r.status === 'pending').length;
  const myPendingReviews = myReviews.filter(r =>
    r.status === 'pending' || r.status === 'in_review'
  ).length;

  const navItems: NavItem[] = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: <Dashboard />,
      path: '/',
      badge: pendingReviews,
    },
    {
      id: 'my-reviews',
      label: 'My Reviews',
      icon: <Assignment />,
      path: '/my-reviews',
      badge: myPendingReviews,
    },
    {
      id: 'documents',
      label: 'Documents',
      icon: <Description />,
      path: '/documents',
      disabled: true, // Will be implemented later
    },
    {
      id: 'ai-insights',
      label: 'AI Insights',
      icon: <AutoAwesome />,
      path: '/insights',
      disabled: true, // Will be implemented later
    },
  ];

  const adminItems: NavItem[] = [
    {
      id: 'analytics',
      label: 'Analytics',
      icon: <Analytics />,
      path: '/analytics',
      roles: ['admin', 'manager'],
      disabled: true, // Will be implemented later
    },
    {
      id: 'users',
      label: 'Users',
      icon: <Group />,
      path: '/users',
      roles: ['admin'],
      disabled: true, // Will be implemented later
    },
    {
      id: 'audit-log',
      label: 'Audit Log',
      icon: <History />,
      path: '/audit',
      roles: ['admin', 'manager'],
      disabled: true, // Will be implemented later
    },
    {
      id: 'settings',
      label: 'System Settings',
      icon: <Settings />,
      path: '/settings',
      roles: ['admin'],
      disabled: true, // Will be implemented later
    },
  ];

  const handleNavigation = (path: string) => {
    navigate(path);
  };

  const isItemActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  const canAccessItem = (item: NavItem) => {
    if (!item.roles || !user) {
      return true;
    }
    return item.roles.includes(user.role);
  };

  const renderNavItem = (item: NavItem) => {
    if (!canAccessItem(item)) {
      return null;
    }

    const isActive = isItemActive(item.path);

    return (
      <ListItem key={item.id} disablePadding>
        <ListItemButton
          onClick={() => !item.disabled && handleNavigation(item.path)}
          selected={isActive}
          disabled={item.disabled}
          sx={{
            minHeight: 48,
            px: 2.5,
            '&.Mui-selected': {
              backgroundColor: 'primary.main',
              color: 'primary.contrastText',
              '& .MuiListItemIcon-root': {
                color: 'primary.contrastText',
              },
              '&:hover': {
                backgroundColor: 'primary.dark',
              },
            },
          }}
        >
          <ListItemIcon
            sx={{
              minWidth: 0,
              mr: open ? 3 : 'auto',
              justifyContent: 'center',
              color: isActive ? 'inherit' : 'action.active',
            }}
          >
            {item.icon}
          </ListItemIcon>
          <ListItemText
            primary={item.label}
            sx={{ opacity: open ? 1 : 0 }}
          />
          {open && item.badge !== undefined && item.badge > 0 && (
            <Chip
              label={item.badge}
              size="small"
              color={isActive ? 'secondary' : 'primary'}
              sx={{
                height: 20,
                fontSize: '0.75rem',
                fontWeight: 'bold',
              }}
            />
          )}
        </ListItemButton>
      </ListItem>
    );
  };

  const drawerContent = (
    <Box sx={{ overflow: 'auto', height: '100%' }}>
      {/* App Title/Logo when collapsed */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: open ? 'flex-start' : 'center',
          px: open ? 2.5 : 1,
          py: 2,
          minHeight: 64,
        }}
      >
        {open && (
          <Typography variant="h6" noWrap component="div">
            Kinexus AI
          </Typography>
        )}
      </Box>

      <Divider />

      {/* Main Navigation */}
      <List>
        {navItems.map(renderNavItem)}
      </List>

      {/* Admin Section */}
      {adminItems.some(canAccessItem) && (
        <>
          <Divider sx={{ my: 1 }} />
          {open && (
            <Box sx={{ px: 2.5, py: 1 }}>
              <Typography variant="caption" color="textSecondary">
                ADMINISTRATION
              </Typography>
            </Box>
          )}
          <List>
            {adminItems.map(renderNavItem)}
          </List>
        </>
      )}

      {/* Status Section */}
      <Box sx={{ mt: 'auto', p: open ? 2 : 1 }}>
        <Divider sx={{ mb: 2 }} />
        {open && (
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="caption" color="textSecondary" display="block">
              Version 1.0.0-dev
            </Typography>
            <Typography variant="caption" color="textSecondary" display="block">
              Development Build
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );

  return (
    <Drawer
      variant="persistent"
      anchor="left"
      open={open}
      sx={{
        width: open ? 240 : 72,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: open ? 240 : 72,
          boxSizing: 'border-box',
          transition: (theme) =>
            theme.transitions.create('width', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
          overflowX: 'hidden',
          position: 'fixed',
          top: 64, // Account for app bar
          height: 'calc(100vh - 64px)',
        },
      }}
    >
      {drawerContent}
    </Drawer>
  );
};

export default Sidebar;