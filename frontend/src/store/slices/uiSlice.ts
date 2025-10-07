/**
 * UI state Redux slice
 */

import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark';
  notificationsPanelOpen: boolean;
  currentPage: string;
  loading: Record<string, boolean>;
  modals: Record<string, boolean>;
  preferences: {
    autoRefresh: boolean;
    refreshInterval: number; // seconds
    soundNotifications: boolean;
    desktopNotifications: boolean;
    compactView: boolean;
    timezone: string;
  };
}

const initialState: UIState = {
  sidebarOpen: true,
  theme: 'light',
  notificationsPanelOpen: false,
  currentPage: 'dashboard',
  loading: {},
  modals: {},
  preferences: {
    autoRefresh: true,
    refreshInterval: 30,
    soundNotifications: true,
    desktopNotifications: true,
    compactView: false,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  },
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebarOpen = action.payload;
    },

    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },

    setTheme: (state, action: PayloadAction<'light' | 'dark'>) => {
      state.theme = action.payload;
    },

    toggleTheme: (state) => {
      state.theme = state.theme === 'light' ? 'dark' : 'light';
    },

    setNotificationsPanelOpen: (state, action: PayloadAction<boolean>) => {
      state.notificationsPanelOpen = action.payload;
    },

    toggleNotificationsPanel: (state) => {
      state.notificationsPanelOpen = !state.notificationsPanelOpen;
    },

    setCurrentPage: (state, action: PayloadAction<string>) => {
      state.currentPage = action.payload;
    },

    setLoading: (state, action: PayloadAction<{ key: string; loading: boolean }>) => {
      state.loading[action.payload.key] = action.payload.loading;
    },

    clearLoading: (state, action: PayloadAction<string>) => {
      delete state.loading[action.payload];
    },

    setModal: (state, action: PayloadAction<{ key: string; open: boolean }>) => {
      state.modals[action.payload.key] = action.payload.open;
    },

    closeAllModals: (state) => {
      state.modals = {};
    },

    updatePreferences: (state, action: PayloadAction<Partial<UIState['preferences']>>) => {
      state.preferences = { ...state.preferences, ...action.payload };
    },

    resetPreferences: (state) => {
      state.preferences = initialState.preferences;
    },
  },
});

export const {
  setSidebarOpen,
  toggleSidebar,
  setTheme,
  toggleTheme,
  setNotificationsPanelOpen,
  toggleNotificationsPanel,
  setCurrentPage,
  setLoading,
  clearLoading,
  setModal,
  closeAllModals,
  updatePreferences,
  resetPreferences,
} = uiSlice.actions;

export default uiSlice.reducer;

// Selectors
export const selectSidebarOpen = (state: { ui: UIState }) => state.ui.sidebarOpen;
export const selectTheme = (state: { ui: UIState }) => state.ui.theme;
export const selectNotificationsPanelOpen = (state: { ui: UIState }) => state.ui.notificationsPanelOpen;
export const selectCurrentPage = (state: { ui: UIState }) => state.ui.currentPage;
export const selectLoading = (state: { ui: UIState }) => (key: string) => state.ui.loading[key] || false;
export const selectModal = (state: { ui: UIState }) => (key: string) => state.ui.modals[key] || false;
export const selectPreferences = (state: { ui: UIState }) => state.ui.preferences;