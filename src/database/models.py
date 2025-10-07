"""
SQLAlchemy models for Kinexus AI human-supervised documentation system.

This module defines the core database schema supporting:
- User management with role-based access control
- Document tracking and versioning
- Human review workflow with approval states
- Configurable approval rules
- Complete audit trails
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey,
    Integer, String, Text, JSON, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

Base = declarative_base()


class UserRole(str, Enum):
    """User roles with escalating permissions."""
    VIEWER = "viewer"           # Read-only access
    REVIEWER = "reviewer"       # Can review and approve documents
    LEAD_REVIEWER = "lead_reviewer"  # Can approve high-impact changes
    ADMIN = "admin"            # Full system access


class ReviewStatus(str, Enum):
    """Review workflow states."""
    PENDING = "pending"         # Awaiting human review
    IN_REVIEW = "in_review"     # Currently being reviewed
    APPROVED = "approved"       # Approved for publication
    APPROVED_WITH_CHANGES = "approved_with_changes"  # Modified then approved
    REJECTED = "rejected"       # Rejected with feedback
    AUTO_APPROVED = "auto_approved"  # Automatically approved by rules


class DocumentStatus(str, Enum):
    """Document lifecycle states."""
    ACTIVE = "active"           # Currently managed
    ARCHIVED = "archived"       # No longer actively managed
    DELETED = "deleted"         # Soft deleted


class ApprovalAction(str, Enum):
    """Approval rule actions."""
    AUTO_APPROVE = "auto_approve"
    REQUIRE_REVIEW = "require_review"
    REQUIRE_LEAD_REVIEW = "require_lead_review"
    REQUIRE_ADMIN_REVIEW = "require_admin_review"


class User(Base):
    """User accounts with role-based permissions."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.REVIEWER)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    reviews = relationship("Review", back_populates="reviewer")
    created_documents = relationship("Document", back_populates="created_by_user")
    document_versions = relationship("DocumentVersion", back_populates="created_by_user")

    @validates('email')
    def validate_email(self, key, email):
        assert '@' in email, "Invalid email format"
        return email.lower()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def can_review(self) -> bool:
        """Check if user can perform reviews."""
        return self.role in [UserRole.REVIEWER, UserRole.LEAD_REVIEWER, UserRole.ADMIN]

    def can_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.role == UserRole.ADMIN

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Document(Base):
    """Documents under management by Kinexus AI."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id = Column(String(255), nullable=False)  # ID in source system
    source_system = Column(String(50), nullable=False)  # 'confluence', 'github', etc.
    path = Column(Text, nullable=False)  # Path within source system
    title = Column(String(500), nullable=False)
    document_type = Column(String(100), nullable=False)  # 'api_doc', 'user_guide', etc.
    current_version = Column(Integer, default=1, nullable=False)
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.ACTIVE, nullable=False)
    doc_metadata = Column(JSON)  # Source-specific metadata (renamed to avoid SQLAlchemy conflict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Indexes for performance
    __table_args__ = (
        Index('idx_document_source_external', 'source_system', 'external_id'),
        Index('idx_document_type_status', 'document_type', 'status'),
        UniqueConstraint('source_system', 'external_id', name='uq_document_source_external'),
    )

    # Relationships
    created_by_user = relationship("User", back_populates="created_documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="document")

    @property
    def latest_version(self) -> Optional["DocumentVersion"]:
        """Get the most recent version of this document."""
        return max(self.versions, key=lambda v: v.version) if self.versions else None

    def __repr__(self):
        return f"<Document {self.source_system}:{self.external_id}>"


class DocumentVersion(Base):
    """Versioned content for documents."""
    __tablename__ = "document_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    version = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_format = Column(String(20), default="markdown", nullable=False)
    change_summary = Column(Text)  # Human-readable summary of changes
    ai_generated = Column(Boolean, default=False, nullable=False)
    ai_model = Column(String(100))  # Model used for generation
    ai_confidence = Column(Integer)  # 1-100 confidence score
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_version_document_version', 'document_id', 'version'),
        UniqueConstraint('document_id', 'version', name='uq_document_version'),
    )

    # Relationships
    document = relationship("Document", back_populates="versions")
    created_by_user = relationship("User", back_populates="document_versions")

    def __repr__(self):
        return f"<DocumentVersion {self.document_id} v{self.version}>"


class Review(Base):
    """Human review workflow for document changes."""
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    change_id = Column(String(255), nullable=False, index=True)  # External change ID
    proposed_version = Column(Integer, nullable=False)  # Version being reviewed
    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False)
    priority = Column(Integer, default=5, nullable=False)  # 1-10 priority scale
    impact_score = Column(Integer, nullable=False)  # 1-10 impact assessment

    # Review assignment and completion
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    assigned_at = Column(DateTime(timezone=True))
    reviewed_at = Column(DateTime(timezone=True))

    # Review decision and feedback
    decision = Column(String(50))  # 'approved', 'rejected', 'approved_with_changes'
    feedback = Column(Text)  # Human feedback
    modifications = Column(JSON)  # Any modifications made during review

    # AI context
    ai_reasoning = Column(Text)  # AI's reasoning for the change
    ai_confidence = Column(Integer)  # AI confidence score 1-100
    ai_model = Column(String(100))  # Model used for generation

    # Metadata
    change_context = Column(JSON)  # Context from source system (commits, issues, etc.)
    auto_approval_rule_id = Column(UUID(as_uuid=True), ForeignKey("approval_rules.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Indexes for performance
    __table_args__ = (
        Index('idx_review_status_priority', 'status', 'priority'),
        Index('idx_review_reviewer_status', 'reviewer_id', 'status'),
        Index('idx_review_created', 'created_at'),
    )

    # Relationships
    document = relationship("Document", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")
    approval_rule = relationship("ApprovalRule")

    @property
    def is_pending(self) -> bool:
        """Check if review is awaiting action."""
        return self.status in [ReviewStatus.PENDING, ReviewStatus.IN_REVIEW]

    @property
    def review_time_minutes(self) -> Optional[int]:
        """Calculate review time in minutes."""
        if self.assigned_at and self.reviewed_at:
            delta = self.reviewed_at - self.assigned_at
            return int(delta.total_seconds() / 60)
        return None

    def can_be_reviewed_by(self, user: User) -> bool:
        """Check if user can review this item."""
        if not user.can_review():
            return False

        if self.impact_score >= 8 and user.role not in [UserRole.LEAD_REVIEWER, UserRole.ADMIN]:
            return False

        return True

    def __repr__(self):
        return f"<Review {self.change_id} ({self.status})>"


class DocumentationPlanStatus(str, Enum):
    """Status for documentation automation plans."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentationPlan(Base):
    """Stored automation plans generated from GitHub Actions."""
    __tablename__ = "documentation_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    repository = Column(String(255), nullable=False)
    pr_number = Column(Integer, nullable=False)
    branch = Column(String(255))
    execution_mode = Column(String(50), default="plan_only", nullable=False)
    plan = Column(JSON, nullable=False)
    status = Column(SQLEnum(DocumentationPlanStatus), nullable=False, default=DocumentationPlanStatus.PENDING)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_doc_plan_repo_pr', 'repository', 'pr_number'),
        Index('idx_doc_plan_status', 'status'),
    )

    review = relationship("Review", backref="documentation_plans")

    def __repr__(self):
        return f"<DocumentationPlan {self.repository}#{self.pr_number} ({self.status})>"


class ApprovalRule(Base):
    """Configurable rules for automatic approval of document changes."""
    __tablename__ = "approval_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    conditions = Column(JSON, nullable=False)  # Conditions for rule activation
    action = Column(SQLEnum(ApprovalAction), nullable=False)
    priority = Column(Integer, default=0, nullable=False)  # Higher number = higher priority
    is_active = Column(Boolean, default=True, nullable=False)

    # Usage tracking
    times_applied = Column(Integer, default=0, nullable=False)
    last_applied = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_approval_rule_active_priority', 'is_active', 'priority'),
    )

    def matches_review(self, review: Review) -> bool:
        """Check if this rule applies to a given review."""
        if not self.is_active:
            return False

        conditions = self.conditions or {}

        # Check document type
        if 'document_type' in conditions:
            if review.document.document_type not in conditions['document_type']:
                return False

        # Check impact score
        if 'impact_score' in conditions:
            score_condition = conditions['impact_score']
            if isinstance(score_condition, dict):
                if '<' in score_condition and review.impact_score >= score_condition['<']:
                    return False
                if '<=' in score_condition and review.impact_score > score_condition['<=']:
                    return False
                if '>' in score_condition and review.impact_score <= score_condition['>']:
                    return False
                if '>=' in score_condition and review.impact_score < score_condition['>=']:
                    return False
            elif isinstance(score_condition, int):
                if review.impact_score != score_condition:
                    return False

        # Check AI confidence
        if 'ai_confidence' in conditions:
            conf_condition = conditions['ai_confidence']
            if isinstance(conf_condition, dict):
                if '>=' in conf_condition and review.ai_confidence < conf_condition['>=']:
                    return False

        return True

    def __repr__(self):
        return f"<ApprovalRule {self.name} ({self.action})>"


class AuditLog(Base):
    """Comprehensive audit trail for all system actions."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(100), nullable=False)  # 'review_approved', 'document_updated', etc.
    resource_type = Column(String(50), nullable=False)  # 'review', 'document', 'user', etc.
    resource_id = Column(UUID(as_uuid=True), nullable=False)
    old_values = Column(JSON)  # Previous state
    new_values = Column(JSON)  # New state
    audit_metadata = Column(JSON)  # Additional context (renamed to avoid SQLAlchemy conflict)
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Indexes for audit queries
    __table_args__ = (
        Index('idx_audit_user_action', 'user_id', 'action'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_created', 'created_at'),
    )

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.resource_type}:{self.resource_id}>"


class SystemMetric(Base):
    """Time-series metrics for system monitoring and analytics."""
    __tablename__ = "system_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Integer, nullable=False)
    dimensions = Column(JSON)  # Additional dimensions (e.g., {'document_type': 'api'})
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Indexes for time-series queries
    __table_args__ = (
        Index('idx_metric_name_timestamp', 'metric_name', 'timestamp'),
        Index('idx_metric_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<SystemMetric {self.metric_name}={self.metric_value}>"
