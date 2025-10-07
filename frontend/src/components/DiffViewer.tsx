/**
 * Diff Viewer - Component for displaying document changes with approval actions
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Stack,
  Alert,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Paper,
  Divider,
  IconButton,
  Tooltip,
  Grid,
  CircularProgress,
  Tab,
  Tabs,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  CheckCircle,
  Cancel,
  Schedule,
  Visibility,
  Person,
  Assignment,
  ExpandMore,
  Download,
  History,
  Code,
  Description,
  Link,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { format, formatDistanceToNow } from 'date-fns';

import {
  approveReview,
  rejectReview,
  assignReview,
  selectCurrentReview,
  selectReviewsLoading,
  selectReviewsError,
} from '@/store/slices/reviewsSlice';
import { selectUser } from '@/store/slices/authSlice';
import { addNotification } from '@/store/slices/notificationsSlice';
import { Review, ReviewAction, REVIEW_STATUSES, ReviewStatus } from '@/types';
import { AppDispatch } from '@/store';
import { documentService, ParsedDiff } from '@/services/documentService';

interface DiffViewerProps {
  reviewId: string;
  onClose?: () => void;
}


interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel = ({ children, value, index, ...other }: TabPanelProps) => (
  <div
    role="tabpanel"
    hidden={value !== index}
    id={`diff-tabpanel-${index}`}
    aria-labelledby={`diff-tab-${index}`}
    {...other}
  >
    {value === index && <Box sx={{ py: 2 }}>{children}</Box>}
  </div>
);

const DiffViewer: React.FC<DiffViewerProps> = ({ reviewId, onClose }) => {
  const dispatch = useDispatch<AppDispatch>();
  const user = useSelector(selectUser);
  const review = useSelector(selectCurrentReview);
  const loading = useSelector(selectReviewsLoading);
  const error = useSelector(selectReviewsError);

  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);
  const [rejectionDialogOpen, setRejectionDialogOpen] = useState(false);
  const [approvalAction, setApprovalAction] = useState<ReviewAction>('approve');
  const [rejectionFeedback, setRejectionFeedback] = useState('');
  const [activeTab, setActiveTab] = useState(0);
  const [parsedDiff, setParsedDiff] = useState<ParsedDiff | null>(null);

  // Parse diff content using document service
  useEffect(() => {
    if (review?.diff_content) {
      try {
        const parsed = documentService.parseDiff(review.diff_content);
        setParsedDiff(parsed);
      } catch (error) {
        console.error('Error parsing diff content:', error);
        setParsedDiff(null);
      }
    } else {
      setParsedDiff(null);
    }
  }, [review?.diff_content]);

  const handleApprove = async () => {
    if (!review) return;

    try {
      await dispatch(approveReview({ id: review.id, action: approvalAction })).unwrap();
      dispatch(addNotification({
        type: 'success',
        title: 'Review Approved',
        message: `Review has been ${approvalAction.replace('_', ' ')}`,
      }));
      setApprovalDialogOpen(false);
      onClose?.();
    } catch (error: any) {
      dispatch(addNotification({
        type: 'error',
        title: 'Approval Failed',
        message: error.message || 'Failed to approve review',
      }));
    }
  };

  const handleReject = async () => {
    if (!review || !rejectionFeedback.trim()) return;

    try {
      await dispatch(rejectReview({ id: review.id, feedback: rejectionFeedback })).unwrap();
      dispatch(addNotification({
        type: 'success',
        title: 'Review Rejected',
        message: 'Review has been rejected with feedback',
      }));
      setRejectionDialogOpen(false);
      setRejectionFeedback('');
      onClose?.();
    } catch (error: any) {
      dispatch(addNotification({
        type: 'error',
        title: 'Rejection Failed',
        message: error.message || 'Failed to reject review',
      }));
    }
  };

  const handleAssignToMe = async () => {
    if (!review || !user) return;

    try {
      await dispatch(assignReview({ id: review.id, reviewerId: user.id })).unwrap();
      dispatch(addNotification({
        type: 'success',
        title: 'Review Assigned',
        message: 'Review has been assigned to you',
      }));
    } catch (error: any) {
      dispatch(addNotification({
        type: 'error',
        title: 'Assignment Failed',
        message: error.message || 'Failed to assign review',
      }));
    }
  };

  const getStatusColor = (status: ReviewStatus) => {
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

  const getDiffLineStyle = (type: string) => {
    switch (type) {
      case 'added':
        return {
          backgroundColor: '#e6ffed',
          borderLeft: '3px solid #28a745',
        };
      case 'removed':
        return {
          backgroundColor: '#ffeef0',
          borderLeft: '3px solid #dc3545',
        };
      case 'header':
      case 'hunk':
        return {
          backgroundColor: '#f8f9fa',
          fontWeight: 'bold',
          color: '#6c757d',
        };
      default:
        return {};
    }
  };

  const canReview = user && review?.reviewer_id === user.id && review.status === 'in_review';
  const canAssign = user && !review?.reviewer_id && user.role !== 'viewer';

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!review) {
    return (
      <Alert severity="info" sx={{ m: 2 }}>
        Review not found
      </Alert>
    );
  }

  return (
    <Box sx={{ p: 2, maxHeight: '90vh', overflow: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box>
            <Typography variant="h5" component="h1" gutterBottom>
              {review.document?.title || 'Unknown Document'}
            </Typography>
            <Typography variant="subtitle1" color="textSecondary" gutterBottom>
              Change ID: {review.change_id}
            </Typography>
          </Box>
          <Stack direction="row" spacing={1}>
            <Chip
              label={REVIEW_STATUSES[review.status]}
              color={getStatusColor(review.status)}
              size="small"
            />
            <Chip
              label={`Priority ${review.priority}`}
              color={review.priority >= 8 ? 'error' : review.priority >= 6 ? 'warning' : 'info'}
              size="small"
            />
          </Stack>
        </Box>

        {/* Review Info Grid */}
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                <Person sx={{ fontSize: 16, mr: 1, verticalAlign: 'text-bottom' }} />
                Reviewer
              </Typography>
              <Typography variant="body2">
                {review.reviewer ? review.reviewer.email : 'Unassigned'}
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                <Schedule sx={{ fontSize: 16, mr: 1, verticalAlign: 'text-bottom' }} />
                Created
              </Typography>
              <Typography variant="body2">
                {formatDistanceToNow(new Date(review.created_at), { addSuffix: true })}
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                <Description sx={{ fontSize: 16, mr: 1, verticalAlign: 'text-bottom' }} />
                Impact Score
              </Typography>
              <Typography variant="body2">
                {review.impact_score}/10
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
          <Tab label="Diff View" icon={<Code />} />
          <Tab label="AI Summary" icon={<Description />} />
          <Tab label="Context" icon={<Link />} />
          <Tab label="History" icon={<History />} />
        </Tabs>
      </Box>

      {/* Tab Panels */}
      <TabPanel value={activeTab} index={0}>
        {/* Diff Content */}
        {parsedDiff && parsedDiff.lines.length > 0 ? (
          <Box>
            {/* Diff Statistics */}
            <Box sx={{ mb: 2, p: 2, bgcolor: 'background.paper', borderRadius: 1 }}>
              <Stack direction="row" spacing={3}>
                <Typography variant="body2">
                  <strong>Changes:</strong> {parsedDiff.stats.total}
                </Typography>
                <Typography variant="body2" color="success.main">
                  <strong>+{parsedDiff.stats.additions}</strong> additions
                </Typography>
                <Typography variant="body2" color="error.main">
                  <strong>-{parsedDiff.stats.deletions}</strong> deletions
                </Typography>
              </Stack>
            </Box>

            {/* Diff Lines */}
            <Paper sx={{ p: 0, fontFamily: 'monospace', fontSize: '0.875rem' }}>
              {parsedDiff.lines.map((line, index) => (
                <Box
                  key={index}
                  sx={{
                    display: 'flex',
                    minHeight: '1.5em',
                    ...getDiffLineStyle(line.type),
                    px: 1,
                    py: 0.25,
                  }}
                >
                  <Box sx={{ minWidth: '80px', color: 'text.secondary', mr: 2 }}>
                    {line.oldLineNumber && (
                      <span style={{ marginRight: '0.5em' }}>{line.oldLineNumber}</span>
                    )}
                    {line.newLineNumber && <span>{line.newLineNumber}</span>}
                  </Box>
                  <Box sx={{ flex: 1, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                    {line.content}
                  </Box>
                </Box>
              ))}
            </Paper>
          </Box>
        ) : (
          <Alert severity="info">
            No diff content available for this review
          </Alert>
        )}
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        {/* AI Summary */}
        <Stack spacing={2}>
          {review.ai_summary && (
            <Card>
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  AI-Generated Summary
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {review.ai_summary}
                </Typography>
              </CardContent>
            </Card>
          )}

          {review.reason && (
            <Card>
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Review Reason
                </Typography>
                <Typography variant="body2">
                  {review.reason}
                </Typography>
              </CardContent>
            </Card>
          )}
        </Stack>
      </TabPanel>

      <TabPanel value={activeTab} index={2}>
        {/* Context Information */}
        <Stack spacing={2}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>
                Document Information
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="caption" color="textSecondary">
                    Type
                  </Typography>
                  <Typography variant="body2">
                    {review.document?.document_type || 'Unknown'}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="textSecondary">
                    Location
                  </Typography>
                  <Typography variant="body2">
                    {review.document?.source_path || 'Unknown'}
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {review.document?.external_links && (
            <Card>
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Related Links
                </Typography>
                <Stack spacing={1}>
                  {Object.entries(review.document.external_links).map(([key, url]) => (
                    <Button
                      key={key}
                      variant="outlined"
                      size="small"
                      startIcon={<Link />}
                      href={url as string}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {key}
                    </Button>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          )}
        </Stack>
      </TabPanel>

      <TabPanel value={activeTab} index={3}>
        {/* Review History */}
        <Typography variant="body2" color="textSecondary">
          Review history functionality will be implemented when audit log integration is complete.
        </Typography>
      </TabPanel>

      {/* Action Buttons */}
      <Box sx={{ mt: 3, pt: 2, borderTop: 1, borderColor: 'divider' }}>
        <Stack direction="row" spacing={2} justifyContent="flex-end">
          {onClose && (
            <Button variant="outlined" onClick={onClose}>
              Close
            </Button>
          )}

          {canAssign && (
            <Button
              variant="outlined"
              startIcon={<Assignment />}
              onClick={handleAssignToMe}
            >
              Assign to Me
            </Button>
          )}

          {canReview && (
            <>
              <Button
                variant="outlined"
                color="error"
                startIcon={<Cancel />}
                onClick={() => setRejectionDialogOpen(true)}
              >
                Reject
              </Button>
              <Button
                variant="contained"
                color="success"
                startIcon={<CheckCircle />}
                onClick={() => setApprovalDialogOpen(true)}
              >
                Approve
              </Button>
            </>
          )}
        </Stack>
      </Box>

      {/* Approval Dialog */}
      <Dialog open={approvalDialogOpen} onClose={() => setApprovalDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Approve Review</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Approval Type</InputLabel>
            <Select
              value={approvalAction}
              onChange={(e) => setApprovalAction(e.target.value as ReviewAction)}
              label="Approval Type"
            >
              <MenuItem value="approve">Approve</MenuItem>
              <MenuItem value="approve_with_changes">Approve with Changes</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApprovalDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleApprove} variant="contained" color="success">
            Approve
          </Button>
        </DialogActions>
      </Dialog>

      {/* Rejection Dialog */}
      <Dialog open={rejectionDialogOpen} onClose={() => setRejectionDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Reject Review</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Rejection Feedback"
            type="text"
            fullWidth
            multiline
            rows={4}
            variant="outlined"
            value={rejectionFeedback}
            onChange={(e) => setRejectionFeedback(e.target.value)}
            placeholder="Please provide feedback on why this review is being rejected..."
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRejectionDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleReject}
            variant="contained"
            color="error"
            disabled={!rejectionFeedback.trim()}
          >
            Reject
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DiffViewer;