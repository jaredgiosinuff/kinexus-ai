/**
 * Redux store configuration for Kinexus AI frontend
 */

import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';
import reviewsReducer from './slices/reviewsSlice';
import notificationsReducer from './slices/notificationsSlice';
import uiReducer from './slices/uiSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    reviews: reviewsReducer,
    notifications: notificationsReducer,
    ui: uiReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['notifications/addNotification'],
        ignoredPaths: ['notifications.items.timestamp'],
      },
    }),
  devTools: import.meta.env.DEV,
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;