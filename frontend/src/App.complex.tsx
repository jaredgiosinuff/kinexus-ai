/**
 * Main App Component - Root component with routing and theme provider
 */

import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import { Provider } from 'react-redux';
import { useSelector, useDispatch } from 'react-redux';

import { store, AppDispatch } from '@/store';
import { selectTheme } from '@/store/slices/uiSlice';
import { selectIsAuthenticated, loadCurrentUser } from '@/store/slices/authSlice';
import MainLayout from '@/components/layout/MainLayout';
import LoginPage from '@/components/auth/LoginPage';
import ReviewDashboard from '@/components/ReviewDashboard';
import DiffViewer from '@/components/DiffViewer';
import NotificationsProvider from '@/components/NotificationsProvider';
import WebSocketProvider from '@/components/WebSocketProvider';

// Create theme based on mode
const createAppTheme = (mode: 'light' | 'dark') =>
  createTheme({
    palette: {
      mode,
      primary: {
        main: '#1976d2',
        light: '#42a5f5',
        dark: '#1565c0',
      },
      secondary: {
        main: '#dc004e',
        light: '#ff5983',
        dark: '#9a0036',
      },
      background: {
        default: mode === 'light' ? '#f5f5f5' : '#121212',
        paper: mode === 'light' ? '#ffffff' : '#1e1e1e',
      },
    },
    typography: {
      fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
      h4: {
        fontWeight: 600,
      },
      h5: {
        fontWeight: 600,
      },
      subtitle1: {
        fontWeight: 500,
      },
      subtitle2: {
        fontWeight: 500,
      },
    },
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: 'none',
            borderRadius: 8,
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 12,
            boxShadow: mode === 'light'
              ? '0 2px 8px rgba(0,0,0,0.1)'
              : '0 2px 8px rgba(0,0,0,0.3)',
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: 6,
          },
        },
      },
    },
  });

// Protected Route Component
interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const isAuthenticated = useSelector(selectIsAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// App Content Component (needs to be inside Redux provider)
const AppContent: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const theme = useSelector(selectTheme);
  const isAuthenticated = useSelector(selectIsAuthenticated);

  const appTheme = createAppTheme(theme);

  // Load current user on app start
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token && !isAuthenticated) {
      dispatch(loadCurrentUser());
    }
  }, [dispatch, isAuthenticated]);

  return (
    <ThemeProvider theme={appTheme}>
      <CssBaseline />
      <Router>
        <Routes>
          {/* Public Routes */}
          <Route
            path="/login"
            element={
              isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />
            }
          />

          {/* Protected Routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <WebSocketProvider>
                  <NotificationsProvider>
                    <MainLayout>
                      <ReviewDashboard />
                    </MainLayout>
                  </NotificationsProvider>
                </WebSocketProvider>
              </ProtectedRoute>
            }
          />

          <Route
            path="/reviews/:reviewId"
            element={
              <ProtectedRoute>
                <WebSocketProvider>
                  <NotificationsProvider>
                    <MainLayout>
                      <DiffViewer reviewId={window.location.pathname.split('/')[2]} />
                    </MainLayout>
                  </NotificationsProvider>
                </WebSocketProvider>
              </ProtectedRoute>
            }
          />

          {/* Catch all route - redirect to dashboard */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
};

// Main App Component
const App: React.FC = () => {
  return (
    <Provider store={store}>
      <AppContent />
    </Provider>
  );
};

export default App;