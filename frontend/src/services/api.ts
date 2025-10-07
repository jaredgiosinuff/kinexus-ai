/**
 * API service layer for Kinexus AI frontend
 * Handles all HTTP requests to the FastAPI backend
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  User,
  Review,
  Document,
  AuthToken,
  LoginCredentials,
  ReviewAction,
  ReviewMetrics,
  ApprovalRule,
  DocumentVersion,
  FilterOptions,
  UserFormData,
  PaginatedResponse,
  ApiResponse,
  ApiError
} from '@/types';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';
const TOKEN_KEY = 'kinexus_auth_token';

class ApiService {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Load token from localStorage
    this.loadToken();

    // Request interceptor for auth
    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          this.clearToken();
          window.location.href = '/login';
        }
        return Promise.reject(this.handleError(error));
      }
    );
  }

  private loadToken(): void {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (stored) {
      try {
        const tokenData = JSON.parse(stored);
        // Check if token is expired
        const expiryTime = tokenData.expires_at;
        if (expiryTime && new Date().getTime() < expiryTime) {
          this.token = tokenData.access_token;
        } else {
          this.clearToken();
        }
      } catch {
        this.clearToken();
      }
    }
  }

  private saveToken(tokenData: AuthToken): void {
    const expiryTime = new Date().getTime() + (tokenData.expires_in * 1000);
    const stored = {
      ...tokenData,
      expires_at: expiryTime,
    };
    localStorage.setItem(TOKEN_KEY, JSON.stringify(stored));
    this.token = tokenData.access_token;
  }

  private clearToken(): void {
    localStorage.removeItem(TOKEN_KEY);
    this.token = null;
  }

  private handleError(error: AxiosError): ApiError {
    const message = error.response?.data?.detail || error.message || 'An unexpected error occurred';
    const status = error.response?.status || 500;

    return {
      message,
      status,
      code: error.code,
      details: error.response?.data,
    };
  }

  // Authentication Methods
  async login(credentials: LoginCredentials): Promise<AuthToken> {
    const response = await this.client.post<AuthToken>('/auth/login', credentials);
    this.saveToken(response.data);
    return response.data;
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/auth/logout');
    } finally {
      this.clearToken();
    }
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/auth/me');
    return response.data;
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await this.client.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  // Review Methods
  async getReviews(params?: {
    status?: string[];
    reviewer_id?: string;
    document_type?: string;
    priority_min?: number;
    limit?: number;
    offset?: number;
  }): Promise<Review[]> {
    const response = await this.client.get<Review[]>('/reviews', { params });
    return response.data;
  }

  async getMyReviews(params?: {
    status?: string[];
    limit?: number;
    offset?: number;
  }): Promise<Review[]> {
    const response = await this.client.get<Review[]>('/reviews/my-queue', { params });
    return response.data;
  }

  async getReview(id: string): Promise<Review> {
    const response = await this.client.get<Review>(`/reviews/${id}`);
    return response.data;
  }

  async assignReview(id: string, reviewerId: string): Promise<Review> {
    const response = await this.client.post<Review>(`/reviews/${id}/assign`, {
      reviewer_id: reviewerId,
    });
    return response.data;
  }

  async approveReview(id: string, action: ReviewAction): Promise<Review> {
    const response = await this.client.post<Review>(`/reviews/${id}/approve`, action);
    return response.data;
  }

  async rejectReview(id: string, feedback: string): Promise<Review> {
    const response = await this.client.post<Review>(`/reviews/${id}/reject`, {
      feedback,
    });
    return response.data;
  }

  async getReviewMetrics(days: number = 30): Promise<ReviewMetrics> {
    const response = await this.client.get<ReviewMetrics>('/reviews/metrics/summary', {
      params: { days },
    });
    return response.data;
  }

  // Document Methods
  async getDocuments(params?: {
    source_system?: string;
    document_type?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<Document[]> {
    const response = await this.client.get<Document[]>('/documents', { params });
    return response.data;
  }

  async getDocument(id: string): Promise<Document> {
    const response = await this.client.get<Document>(`/documents/${id}`);
    return response.data;
  }

  async getDocumentVersions(id: string): Promise<DocumentVersion[]> {
    const response = await this.client.get<DocumentVersion[]>(`/documents/${id}/versions`);
    return response.data;
  }

  async getDocumentDiff(
    id: string,
    versionFrom: number,
    versionTo: number
  ): Promise<{ diff: string; from_content: string; to_content: string }> {
    const response = await this.client.get(`/documents/${id}/diff`, {
      params: { version_from: versionFrom, version_to: versionTo },
    });
    return response.data;
  }

  // User Management (Admin only)
  async getUsers(): Promise<User[]> {
    const response = await this.client.get<User[]>('/admin/users');
    return response.data;
  }

  async createUser(userData: UserFormData): Promise<User> {
    const response = await this.client.post<User>('/auth/users', userData);
    return response.data;
  }

  async updateUser(id: string, userData: Partial<UserFormData>): Promise<User> {
    const response = await this.client.put<User>(`/admin/users/${id}`, userData);
    return response.data;
  }

  // Approval Rules (Lead Reviewer and Admin)
  async getApprovalRules(): Promise<ApprovalRule[]> {
    const response = await this.client.get<ApprovalRule[]>('/admin/approval-rules');
    return response.data;
  }

  async createApprovalRule(ruleData: Omit<ApprovalRule, 'id' | 'times_applied' | 'last_applied' | 'created_at' | 'updated_at'>): Promise<ApprovalRule> {
    const response = await this.client.post<ApprovalRule>('/admin/approval-rules', ruleData);
    return response.data;
  }

  async updateApprovalRule(id: string, ruleData: Partial<ApprovalRule>): Promise<ApprovalRule> {
    const response = await this.client.put<ApprovalRule>(`/admin/approval-rules/${id}`, ruleData);
    return response.data;
  }

  async deleteApprovalRule(id: string): Promise<void> {
    await this.client.delete(`/admin/approval-rules/${id}`);
  }

  // System Status
  async getSystemStatus(): Promise<{
    status: string;
    database: string;
    active_users: number;
    pending_reviews: number;
  }> {
    const response = await this.client.get('/admin/system-status');
    return response.data;
  }

  // WebSocket Connection Stats
  async getWebSocketStats(): Promise<{
    total_connections: number;
    unique_users: number;
    rooms: number;
    connections_by_role: Record<string, number>;
  }> {
    const response = await this.client.get('/ws/stats');
    return response.data;
  }

  // Health Check
  async healthCheck(): Promise<{
    status: string;
    database: string;
    version: string;
  }> {
    const response = await this.client.get('/health');
    return response.data;
  }

  // Utility Methods
  isAuthenticated(): boolean {
    return !!this.token;
  }

  getToken(): string | null {
    return this.token;
  }
}

// Create singleton instance
export const apiService = new ApiService();

// Export convenience methods
export const {
  login,
  logout,
  getCurrentUser,
  changePassword,
  getReviews,
  getMyReviews,
  getReview,
  assignReview,
  approveReview,
  rejectReview,
  getReviewMetrics,
  getDocuments,
  getDocument,
  getDocumentVersions,
  getDocumentDiff,
  getUsers,
  createUser,
  updateUser,
  getApprovalRules,
  createApprovalRule,
  updateApprovalRule,
  deleteApprovalRule,
  getSystemStatus,
  getWebSocketStats,
  healthCheck,
  isAuthenticated,
  getToken,
} = apiService;