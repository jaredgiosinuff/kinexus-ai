/**
 * TypeScript type definitions for Kinexus AI frontend
 */

// User and Authentication Types
export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_active: boolean;
  last_login?: string;
  created_at: string;
}

export type UserRole = 'viewer' | 'reviewer' | 'lead_reviewer' | 'admin';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// Review Types
export interface Review {
  id: string;
  document_id: string;
  change_id: string;
  proposed_version: number;
  status: ReviewStatus;
  priority: number;
  impact_score: number;
  reviewer_id?: string;
  assigned_at?: string;
  reviewed_at?: string;
  decision?: string;
  feedback?: string;
  modifications?: Record<string, any>;
  ai_reasoning?: string;
  ai_confidence?: number;
  ai_model?: string;
  change_context?: Record<string, any>;
  created_at: string;
  updated_at?: string;
  document?: DocumentSummary;
  reviewer?: UserSummary;
}

export type ReviewStatus =
  | 'pending'
  | 'in_review'
  | 'approved'
  | 'approved_with_changes'
  | 'rejected'
  | 'auto_approved';

export interface ReviewAction {
  feedback?: string;
  modifications?: Record<string, any>;
}

export interface ReviewMetrics {
  period_days: number;
  total_reviews: number;
  pending_reviews: number;
  approved_reviews: number;
  rejected_reviews: number;
  auto_approved_reviews: number;
  approval_rate: number;
  avg_review_time_minutes: number;
  top_reviewers: Array<{
    email: string;
    count: number;
  }>;
}

// Document Types
export interface Document {
  id: string;
  external_id: string;
  source_system: string;
  path: string;
  title: string;
  document_type: string;
  current_version: number;
  status: DocumentStatus;
  doc_metadata?: Record<string, any>;
  created_by: string;
  created_at: string;
  updated_at?: string;
}

export interface DocumentSummary {
  id: string;
  title: string;
  document_type: string;
  source_system: string;
  path: string;
}

export type DocumentStatus = 'active' | 'archived' | 'deleted';

export interface DocumentVersion {
  id: string;
  document_id: string;
  version: number;
  content: string;
  content_format: string;
  change_summary?: string;
  ai_generated: boolean;
  ai_model?: string;
  ai_confidence?: number;
  created_by: string;
  created_at: string;
}

// Approval Rules Types
export interface ApprovalRule {
  id: string;
  name: string;
  description?: string;
  conditions: Record<string, any>;
  action: ApprovalAction;
  priority: number;
  is_active: boolean;
  times_applied: number;
  last_applied?: string;
  created_at: string;
  updated_at?: string;
}

export type ApprovalAction =
  | 'auto_approve'
  | 'require_review'
  | 'require_lead_review'
  | 'require_admin_review';

// WebSocket Types
export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
  user_id?: string;
}

export interface NotificationMessage extends WebSocketMessage {
  type: 'review_created' | 'review_assigned' | 'review_completed' | 'queue_update' | 'system_alert';
}

// API Response Types
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  errors?: string[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// UI State Types
export interface DashboardStats {
  pending_reviews: number;
  my_reviews: number;
  completed_today: number;
  avg_review_time: number;
  approval_rate: number;
}

export interface FilterOptions {
  status?: ReviewStatus[];
  priority_min?: number;
  document_type?: string;
  reviewer_id?: string;
}

export interface SortOptions {
  field: string;
  direction: 'asc' | 'desc';
}

// Error Types
export interface ApiError {
  message: string;
  status: number;
  code?: string;
  details?: Record<string, any>;
}

// Utility Types
export interface UserSummary {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
}

export interface ChangeContext {
  repository?: string;
  branch?: string;
  files_changed?: string[];
  commits?: Array<{
    id: string;
    message: string;
    author: string;
    timestamp: string;
  }>;
  ai_assessment?: {
    affected_docs: string[];
    priority: 'high' | 'medium' | 'low';
    reasoning: string;
    suggested_updates: string;
  };
}

// Theme and UI Types
export interface Theme {
  mode: 'light' | 'dark';
  primary: string;
  secondary: string;
}

export interface NotificationConfig {
  enabled: boolean;
  sound: boolean;
  desktop: boolean;
  email: boolean;
}

// Component Props Types
export interface BaseComponentProps {
  className?: string;
  children?: React.ReactNode;
}

export interface LoadingState {
  loading: boolean;
  error?: string | null;
}

// Form Types
export interface LoginFormData {
  email: string;
  password: string;
  remember?: boolean;
}

export interface ReviewFormData {
  decision: 'approve' | 'reject' | 'approve_with_changes';
  feedback?: string;
  modifications?: string;
}

export interface UserFormData {
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  password?: string;
}

// Constants
export const REVIEW_STATUSES: Record<ReviewStatus, string> = {
  pending: 'Pending',
  in_review: 'In Review',
  approved: 'Approved',
  approved_with_changes: 'Approved with Changes',
  rejected: 'Rejected',
  auto_approved: 'Auto-approved'
};

export const USER_ROLES: Record<UserRole, string> = {
  viewer: 'Viewer',
  reviewer: 'Reviewer',
  lead_reviewer: 'Lead Reviewer',
  admin: 'Administrator'
};

export const DOCUMENT_TYPES = [
  'api_doc',
  'user_guide',
  'README',
  'changelog',
  'security_guide',
  'deployment_guide',
  'troubleshooting',
  'general'
] as const;

export type DocumentType = typeof DOCUMENT_TYPES[number];