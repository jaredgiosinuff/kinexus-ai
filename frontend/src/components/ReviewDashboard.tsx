/**
 * Review Dashboard - Main interface for managing document reviews
 */

import React, { useEffect, useState, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Stack,
  Alert,
  CircularProgress,
  Badge,
} from '@mui/material';
import {
  Assignment,
  CheckCircle,
  Cancel,
  Schedule,
  FilterList,
  Refresh,
  Visibility,
  Person,
  TrendingUp,
  Queue,
  Speed,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { format, formatDistanceToNow } from 'date-fns';

import {
  fetchReviews,
  fetchMyReviews,
  fetchReviewMetrics,
  assignReview,
  selectReviews,
  selectMyReviews,
  selectReviewMetrics,
  selectReviewsLoading,
  selectReviewsError,
  setFilters,
  selectReviewsFilters,
} from '@/store/slices/reviewsSlice';
import { selectUser } from '@/store/slices/authSlice';
import { addNotification } from '@/store/slices/notificationsSlice';
import { Review, ReviewStatus, REVIEW_STATUSES, USER_ROLES } from '@/types';
import { AppDispatch, RootState } from '@/store';

const ReviewDashboard: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>();
  const user = useSelector(selectUser);
  const reviews = useSelector(selectReviews);
  const myReviews = useSelector(selectMyReviews);
  const metrics = useSelector(selectReviewMetrics);
  const loading = useSelector(selectReviewsLoading);
  const error = useSelector(selectReviewsError);
  const filters = useSelector(selectReviewsFilters);

  const [selectedTab, setSelectedTab] = useState<'all' | 'mine'>('all');
  const [filterOpen, setFilterOpen] = useState(false);

  // Load data on component mount
  useEffect(() => {
    dispatch(fetchReviews(filters));
    dispatch(fetchMyReviews({ status: ['pending', 'in_review'] }));
    dispatch(fetchReviewMetrics(30));
  }, [dispatch, filters]);

  // Filter and sort reviews
  const filteredReviews = useMemo(() => {
    const targetReviews = selectedTab === 'mine' ? myReviews : reviews;

    return targetReviews
      .filter(review => {
        if (filters.status && filters.status.length > 0) {
          return filters.status.includes(review.status);
        }
        return true;
      })
      .sort((a, b) => {
        // Sort by priority (high to low), then by creation time (new to old)
        if (a.priority !== b.priority) {
          return b.priority - a.priority;
        }
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
  }, [reviews, myReviews, selectedTab, filters]);

  // Dashboard stats
  const dashboardStats = useMemo(() => {
    const pendingReviews = reviews.filter(r => r.status === 'pending').length;
    const myPendingReviews = myReviews.filter(r =>
      r.status === 'pending' || r.status === 'in_review'
    ).length;
    const completedToday = reviews.filter(r => {
      if (!r.reviewed_at) return false;
      const reviewDate = new Date(r.reviewed_at);
      const today = new Date();
      return reviewDate.toDateString() === today.toDateString();
    }).length;

    return {
      pendingReviews,
      myPendingReviews,
      completedToday,
      approvalRate: metrics?.approval_rate || 0,
      avgReviewTime: metrics?.avg_review_time_minutes || 0,
    };
  }, [reviews, myReviews, metrics]);

  const handleAssignToMe = async (reviewId: string) => {
    if (!user) return;

    try {
      await dispatch(assignReview({ id: reviewId, reviewerId: user.id })).unwrap();
      dispatch(addNotification({
        type: 'success',
        title: 'Review Assigned',
        message: 'Review has been assigned to you',
      }));
      // Refresh data
      dispatch(fetchReviews(filters));
      dispatch(fetchMyReviews({ status: ['pending', 'in_review'] }));
    } catch (error: any) {
      dispatch(addNotification({
        type: 'error',
        title: 'Assignment Failed',
        message: error.message || 'Failed to assign review',
      }));
    }
  };

  const handleFilterChange = (key: string, value: any) => {
    dispatch(setFilters({ ...filters, [key]: value }));
  };

  const handleRefresh = () => {
    dispatch(fetchReviews(filters));
    dispatch(fetchMyReviews({ status: ['pending', 'in_review'] }));
    dispatch(fetchReviewMetrics(30));
  };

  const getStatusColor = (status: ReviewStatus): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    switch (status) {
      case 'pending':
        return 'warning';
      case 'in_review':
        return 'info';
      case 'approved':
      case 'approved_with_changes':
      case 'auto_approved':
        return 'success';
      case 'rejected':
        return 'error';
      default:
        return 'default';
    }
  };

  const getPriorityColor = (priority: number): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    if (priority >= 8) return 'error';
    if (priority >= 6) return 'warning';
    if (priority >= 4) return 'info';
    return 'success';
  };

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Review Dashboard
        </Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={<FilterList />}
            onClick={() => setFilterOpen(!filterOpen)}
          >
            Filters
          </Button>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleRefresh}
            disabled={loading}
          >
            Refresh
          </Button>
        </Stack>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Queue sx={{ color: 'warning.main', mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Pending Reviews
                  </Typography>
                  <Typography variant="h5">
                    {dashboardStats.pendingReviews}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Person sx={{ color: 'info.main', mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    My Reviews
                  </Typography>
                  <Typography variant="h5">
                    {dashboardStats.myPendingReviews}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <CheckCircle sx={{ color: 'success.main', mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Completed Today
                  </Typography>
                  <Typography variant="h5">
                    {dashboardStats.completedToday}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <TrendingUp sx={{ color: 'success.main', mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Approval Rate
                  </Typography>
                  <Typography variant="h5">
                    {(dashboardStats.approvalRate * 100).toFixed(1)}%
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={2.4}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Speed sx={{ color: 'primary.main', mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Avg Review Time
                  </Typography>
                  <Typography variant="h5">
                    {dashboardStats.avgReviewTime.toFixed(0)}m
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters */}
      {filterOpen && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={4}>
                <FormControl fullWidth>
                  <InputLabel>Status</InputLabel>
                  <Select
                    multiple
                    value={filters.status || []}
                    onChange={(e) => handleFilterChange('status', e.target.value)}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {(selected as string[]).map((value) => (
                          <Chip key={value} label={REVIEW_STATUSES[value as ReviewStatus]} size="small" />
                        ))}
                      </Box>
                    )}
                  >
                    {Object.entries(REVIEW_STATUSES).map(([key, label]) => (
                      <MenuItem key={key} value={key}>
                        {label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  label="Minimum Priority"
                  type="number"
                  inputProps={{ min: 1, max: 10 }}
                  value={filters.priority_min || ''}
                  onChange={(e) => handleFilterChange('priority_min', e.target.value ? Number(e.target.value) : undefined)}
                />
              </Grid>

              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  label="Document Type"
                  value={filters.document_type || ''}
                  onChange={(e) => handleFilterChange('document_type', e.target.value || undefined)}
                />
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Tab Navigation */}
      <Box sx={{ mb: 2 }}>
        <Button
          variant={selectedTab === 'all' ? 'contained' : 'outlined'}
          onClick={() => setSelectedTab('all')}
          sx={{ mr: 1 }}
        >
          All Reviews ({reviews.length})
        </Button>
        <Button
          variant={selectedTab === 'mine' ? 'contained' : 'outlined'}
          onClick={() => setSelectedTab('mine')}
        >
          My Reviews ({myReviews.length})
        </Button>
      </Box>

      {/* Reviews Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Document</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Priority</TableCell>
              <TableCell>Impact</TableCell>
              <TableCell>Reviewer</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} sx={{ textAlign: 'center', py: 4 }}>
                  <CircularProgress />
                </TableCell>
              </TableRow>
            ) : filteredReviews.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} sx={{ textAlign: 'center', py: 4 }}>
                  <Typography color="textSecondary">
                    No reviews found
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              filteredReviews.map((review) => (
                <TableRow key={review.id} hover>
                  <TableCell>
                    <Box>
                      <Typography variant="subtitle2">
                        {review.document?.title || 'Unknown Document'}
                      </Typography>
                      <Typography variant="caption" color="textSecondary">
                        {review.document?.document_type} • {review.change_id}
                      </Typography>
                    </Box>
                  </TableCell>

                  <TableCell>
                    <Chip
                      label={REVIEW_STATUSES[review.status]}
                      color={getStatusColor(review.status)}
                      size="small"
                    />
                  </TableCell>

                  <TableCell>
                    <Chip
                      label={review.priority}
                      color={getPriorityColor(review.priority)}
                      size="small"
                    />
                  </TableCell>

                  <TableCell>
                    <Typography variant="body2">
                      {review.impact_score}/10
                    </Typography>
                  </TableCell>

                  <TableCell>
                    {review.reviewer ? (
                      <Typography variant="body2">
                        {review.reviewer.email}
                      </Typography>
                    ) : (
                      <Typography variant="body2" color="textSecondary">
                        Unassigned
                      </Typography>
                    )}
                  </TableCell>

                  <TableCell>
                    <Tooltip title={format(new Date(review.created_at), 'PPpp')}>
                      <Typography variant="body2">
                        {formatDistanceToNow(new Date(review.created_at), { addSuffix: true })}
                      </Typography>
                    </Tooltip>
                  </TableCell>

                  <TableCell>
                    <Stack direction="row" spacing={1}>
                      <Tooltip title="View Review">
                        <IconButton
                          size="small"
                          onClick={() => {
                            // Navigate to review detail
                            window.open(`/reviews/${review.id}`, '_blank');
                          }}
                        >
                          <Visibility />
                        </IconButton>
                      </Tooltip>

                      {!review.reviewer_id && user?.role !== 'viewer' && (
                        <Tooltip title="Assign to Me">
                          <IconButton
                            size="small"
                            onClick={() => handleAssignToMe(review.id)}
                          >
                            <Assignment />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default ReviewDashboard;