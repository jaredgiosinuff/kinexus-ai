/**
 * Reviews Redux slice
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Review, ReviewAction, ReviewMetrics, FilterOptions } from '@/types';
import { apiService } from '@/services/api';

interface ReviewsState {
  items: Review[];
  myReviews: Review[];
  currentReview: Review | null;
  metrics: ReviewMetrics | null;
  filters: FilterOptions;
  loading: boolean;
  error: string | null;
  lastUpdated: string | null;
}

const initialState: ReviewsState = {
  items: [],
  myReviews: [],
  currentReview: null,
  metrics: null,
  filters: {},
  loading: false,
  error: null,
  lastUpdated: null,
};

// Async thunks
export const fetchReviews = createAsyncThunk<
  Review[],
  FilterOptions | undefined,
  { rejectValue: string }
>(
  'reviews/fetchReviews',
  async (filters = {}, { rejectWithValue }) => {
    try {
      const reviews = await apiService.getReviews(filters);
      return reviews;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to fetch reviews');
    }
  }
);

export const fetchMyReviews = createAsyncThunk<
  Review[],
  { status?: string[]; limit?: number; offset?: number } | undefined,
  { rejectValue: string }
>(
  'reviews/fetchMyReviews',
  async (params = {}, { rejectWithValue }) => {
    try {
      const reviews = await apiService.getMyReviews(params);
      return reviews;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to fetch my reviews');
    }
  }
);

export const fetchReview = createAsyncThunk<
  Review,
  string,
  { rejectValue: string }
>(
  'reviews/fetchReview',
  async (id, { rejectWithValue }) => {
    try {
      const review = await apiService.getReview(id);
      return review;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to fetch review');
    }
  }
);

export const assignReview = createAsyncThunk<
  Review,
  { id: string; reviewerId: string },
  { rejectValue: string }
>(
  'reviews/assignReview',
  async ({ id, reviewerId }, { rejectWithValue }) => {
    try {
      const review = await apiService.assignReview(id, reviewerId);
      return review;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to assign review');
    }
  }
);

export const approveReview = createAsyncThunk<
  Review,
  { id: string; action: ReviewAction },
  { rejectValue: string }
>(
  'reviews/approveReview',
  async ({ id, action }, { rejectWithValue }) => {
    try {
      const review = await apiService.approveReview(id, action);
      return review;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to approve review');
    }
  }
);

export const rejectReview = createAsyncThunk<
  Review,
  { id: string; feedback: string },
  { rejectValue: string }
>(
  'reviews/rejectReview',
  async ({ id, feedback }, { rejectWithValue }) => {
    try {
      const review = await apiService.rejectReview(id, feedback);
      return review;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to reject review');
    }
  }
);

export const fetchReviewMetrics = createAsyncThunk<
  ReviewMetrics,
  number | undefined,
  { rejectValue: string }
>(
  'reviews/fetchMetrics',
  async (days = 30, { rejectWithValue }) => {
    try {
      const metrics = await apiService.getReviewMetrics(days);
      return metrics;
    } catch (error: any) {
      return rejectWithValue(error.message || 'Failed to fetch metrics');
    }
  }
);

const reviewsSlice = createSlice({
  name: 'reviews',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setFilters: (state, action: PayloadAction<FilterOptions>) => {
      state.filters = action.payload;
    },
    clearCurrentReview: (state) => {
      state.currentReview = null;
    },
    updateReviewInList: (state, action: PayloadAction<Review>) => {
      const updatedReview = action.payload;

      // Update in main list
      const index = state.items.findIndex(r => r.id === updatedReview.id);
      if (index !== -1) {
        state.items[index] = updatedReview;
      }

      // Update in my reviews list
      const myIndex = state.myReviews.findIndex(r => r.id === updatedReview.id);
      if (myIndex !== -1) {
        state.myReviews[myIndex] = updatedReview;
      }

      // Update current review if it matches
      if (state.currentReview?.id === updatedReview.id) {
        state.currentReview = updatedReview;
      }

      state.lastUpdated = new Date().toISOString();
    },
    addReviewToList: (state, action: PayloadAction<Review>) => {
      const newReview = action.payload;

      // Add to main list if not already present
      if (!state.items.find(r => r.id === newReview.id)) {
        state.items.unshift(newReview);
      }

      state.lastUpdated = new Date().toISOString();
    },
    removeReviewFromList: (state, action: PayloadAction<string>) => {
      const reviewId = action.payload;

      state.items = state.items.filter(r => r.id !== reviewId);
      state.myReviews = state.myReviews.filter(r => r.id !== reviewId);

      if (state.currentReview?.id === reviewId) {
        state.currentReview = null;
      }

      state.lastUpdated = new Date().toISOString();
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch reviews
      .addCase(fetchReviews.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchReviews.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload;
        state.lastUpdated = new Date().toISOString();
      })
      .addCase(fetchReviews.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Failed to fetch reviews';
      })

      // Fetch my reviews
      .addCase(fetchMyReviews.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchMyReviews.fulfilled, (state, action) => {
        state.loading = false;
        state.myReviews = action.payload;
        state.lastUpdated = new Date().toISOString();
      })
      .addCase(fetchMyReviews.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Failed to fetch my reviews';
      })

      // Fetch single review
      .addCase(fetchReview.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchReview.fulfilled, (state, action) => {
        state.loading = false;
        state.currentReview = action.payload;
      })
      .addCase(fetchReview.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || 'Failed to fetch review';
      })

      // Assign review
      .addCase(assignReview.fulfilled, (state, action) => {
        const updatedReview = action.payload;

        // Update in lists
        const index = state.items.findIndex(r => r.id === updatedReview.id);
        if (index !== -1) {
          state.items[index] = updatedReview;
        }

        if (state.currentReview?.id === updatedReview.id) {
          state.currentReview = updatedReview;
        }

        state.lastUpdated = new Date().toISOString();
      })
      .addCase(assignReview.rejected, (state, action) => {
        state.error = action.payload || 'Failed to assign review';
      })

      // Approve review
      .addCase(approveReview.fulfilled, (state, action) => {
        const updatedReview = action.payload;

        // Update in lists
        const index = state.items.findIndex(r => r.id === updatedReview.id);
        if (index !== -1) {
          state.items[index] = updatedReview;
        }

        const myIndex = state.myReviews.findIndex(r => r.id === updatedReview.id);
        if (myIndex !== -1) {
          state.myReviews[myIndex] = updatedReview;
        }

        if (state.currentReview?.id === updatedReview.id) {
          state.currentReview = updatedReview;
        }

        state.lastUpdated = new Date().toISOString();
      })
      .addCase(approveReview.rejected, (state, action) => {
        state.error = action.payload || 'Failed to approve review';
      })

      // Reject review
      .addCase(rejectReview.fulfilled, (state, action) => {
        const updatedReview = action.payload;

        // Update in lists
        const index = state.items.findIndex(r => r.id === updatedReview.id);
        if (index !== -1) {
          state.items[index] = updatedReview;
        }

        const myIndex = state.myReviews.findIndex(r => r.id === updatedReview.id);
        if (myIndex !== -1) {
          state.myReviews[myIndex] = updatedReview;
        }

        if (state.currentReview?.id === updatedReview.id) {
          state.currentReview = updatedReview;
        }

        state.lastUpdated = new Date().toISOString();
      })
      .addCase(rejectReview.rejected, (state, action) => {
        state.error = action.payload || 'Failed to reject review';
      })

      // Fetch metrics
      .addCase(fetchReviewMetrics.fulfilled, (state, action) => {
        state.metrics = action.payload;
      })
      .addCase(fetchReviewMetrics.rejected, (state, action) => {
        state.error = action.payload || 'Failed to fetch metrics';
      });
  },
});

export const {
  clearError,
  setFilters,
  clearCurrentReview,
  updateReviewInList,
  addReviewToList,
  removeReviewFromList,
} = reviewsSlice.actions;

export default reviewsSlice.reducer;

// Selectors
export const selectReviews = (state: { reviews: ReviewsState }) => state.reviews.items;
export const selectMyReviews = (state: { reviews: ReviewsState }) => state.reviews.myReviews;
export const selectCurrentReview = (state: { reviews: ReviewsState }) => state.reviews.currentReview;
export const selectReviewMetrics = (state: { reviews: ReviewsState }) => state.reviews.metrics;
export const selectReviewsLoading = (state: { reviews: ReviewsState }) => state.reviews.loading;
export const selectReviewsError = (state: { reviews: ReviewsState }) => state.reviews.error;
export const selectReviewsFilters = (state: { reviews: ReviewsState }) => state.reviews.filters;
export const selectReviewsLastUpdated = (state: { reviews: ReviewsState }) => state.reviews.lastUpdated;