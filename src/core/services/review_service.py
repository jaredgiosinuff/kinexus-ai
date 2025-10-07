"""
Review workflow service for Kinexus AI.

This service manages the complete review lifecycle:
- Creating reviews from change events
- Queue management and assignment
- Approval/rejection workflow
- Auto-approval rule evaluation
- Metrics and analytics
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import Session, joinedload

from database.models import (
    Review, ReviewStatus, Document, User, UserRole,
    ApprovalRule, ApprovalAction, AuditLog, SystemMetric
)
from core.config import settings

logger = logging.getLogger(__name__)


class ReviewService:
    """Service for managing document review workflow."""

    def __init__(self, db: Session, notification_service=None):
        self.db = db
        self.notification_service = notification_service

    def _send_notification(self, notification_func, *args, **kwargs):
        """
        Send a notification asynchronously if notification service is available.

        This is a helper to handle notifications without blocking the main thread.
        """
        if self.notification_service:
            try:
                # Get the current event loop or create a new one
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, schedule the notification
                        asyncio.create_task(notification_func(*args, **kwargs))
                    else:
                        # If no loop is running, run the notification
                        loop.run_until_complete(notification_func(*args, **kwargs))
                except RuntimeError:
                    # No event loop in current thread, create a new one
                    asyncio.run(notification_func(*args, **kwargs))
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")

    def create_review(
        self,
        document_id: UUID,
        change_id: str,
        proposed_version: int,
        impact_score: int,
        ai_reasoning: str = None,
        ai_confidence: int = None,
        ai_model: str = None,
        change_context: Dict[str, Any] = None,
        priority: int = None
    ) -> Review:
        """
        Create a new review for a document change.

        Args:
            document_id: ID of the document being changed
            change_id: External change identifier (e.g., commit hash, issue ID)
            proposed_version: Version number of the proposed changes
            impact_score: Impact assessment score (1-10)
            ai_reasoning: AI's explanation for the changes
            ai_confidence: AI confidence score (1-100)
            ai_model: AI model used for generation
            change_context: Additional context from the change source
            priority: Review priority (1-10, defaults based on impact)

        Returns:
            Review: Created review object

        Raises:
            ValueError: If document not found or validation fails
        """
        # Validate document exists
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Check for duplicate reviews
        existing_review = self.db.query(Review).filter(
            and_(
                Review.document_id == document_id,
                Review.change_id == change_id,
                Review.status.in_([ReviewStatus.PENDING, ReviewStatus.IN_REVIEW])
            )
        ).first()

        if existing_review:
            logger.warning(f"Review already exists for change {change_id}")
            return existing_review

        # Calculate priority if not provided
        if priority is None:
            priority = self._calculate_priority(impact_score, document.document_type)

        # Create review
        review = Review(
            id=uuid4(),
            document_id=document_id,
            change_id=change_id,
            proposed_version=proposed_version,
            status=ReviewStatus.PENDING,
            priority=priority,
            impact_score=impact_score,
            ai_reasoning=ai_reasoning,
            ai_confidence=ai_confidence,
            ai_model=ai_model,
            change_context=change_context or {}
        )

        self.db.add(review)

        # Check if auto-approval rules apply
        auto_approval_rule = self._evaluate_approval_rules(review)
        if auto_approval_rule:
            review.auto_approval_rule_id = auto_approval_rule.id
            review.status = ReviewStatus.AUTO_APPROVED
            review.reviewed_at = datetime.utcnow()
            review.decision = "auto_approved"

            # Update rule usage stats
            auto_approval_rule.times_applied += 1
            auto_approval_rule.last_applied = datetime.utcnow()

            logger.info(f"Review {review.id} auto-approved by rule: {auto_approval_rule.name}")
        else:
            # Assign to reviewer if auto-assignment is enabled
            if settings.AUTO_ASSIGN_REVIEWS:
                self._auto_assign_review(review)

        self.db.commit()

        # Record metrics
        self._record_review_metric("reviews_created", 1, {
            "document_type": document.document_type,
            "impact_score": impact_score,
            "status": review.status.value
        })

        # Send real-time notification
        self._send_notification(
            self.notification_service.notify_review_created,
            {
                "id": str(review.id),
                "document_id": str(document_id),
                "change_id": change_id,
                "status": review.status.value,
                "priority": priority,
                "impact_score": impact_score,
                "document": {
                    "title": document.title,
                    "type": document.document_type,
                    "path": document.path
                }
            }
        )

        logger.info(f"Created review {review.id} for document {document_id}")
        return review

    def get_review_queue(
        self,
        reviewer_id: UUID = None,
        status: List[ReviewStatus] = None,
        priority_min: int = None,
        document_type: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Review]:
        """
        Get reviews from the queue with filtering and pagination.

        Args:
            reviewer_id: Filter by assigned reviewer
            status: Filter by review status
            priority_min: Minimum priority level
            document_type: Filter by document type
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List[Review]: Filtered and sorted reviews
        """
        query = self.db.query(Review).options(
            joinedload(Review.document),
            joinedload(Review.reviewer)
        )

        # Apply filters
        if reviewer_id:
            query = query.filter(Review.reviewer_id == reviewer_id)

        if status:
            query = query.filter(Review.status.in_(status))

        if priority_min:
            query = query.filter(Review.priority >= priority_min)

        if document_type:
            query = query.join(Document).filter(Document.document_type == document_type)

        # Sort by priority (high to low), then by creation time (old to new)
        query = query.order_by(desc(Review.priority), Review.created_at)

        return query.offset(offset).limit(limit).all()

    def assign_review(self, review_id: UUID, reviewer_id: UUID) -> Review:
        """
        Assign a review to a specific reviewer.

        Args:
            review_id: ID of the review to assign
            reviewer_id: ID of the reviewer to assign to

        Returns:
            Review: Updated review object

        Raises:
            ValueError: If review or reviewer not found, or assignment invalid
        """
        review = self.db.query(Review).filter(Review.id == review_id).first()
        if not review:
            raise ValueError(f"Review {review_id} not found")

        reviewer = self.db.query(User).filter(User.id == reviewer_id).first()
        if not reviewer:
            raise ValueError(f"Reviewer {reviewer_id} not found")

        # Validate reviewer can handle this review
        if not review.can_be_reviewed_by(reviewer):
            raise ValueError(f"Reviewer {reviewer.email} cannot review this item")

        # Check if review is in assignable state
        if review.status not in [ReviewStatus.PENDING, ReviewStatus.IN_REVIEW]:
            raise ValueError(f"Review {review_id} is not in assignable state")

        # Assign review
        review.reviewer_id = reviewer_id
        review.assigned_at = datetime.utcnow()
        review.status = ReviewStatus.IN_REVIEW

        self.db.commit()

        # Record metrics
        self._record_review_metric("reviews_assigned", 1, {
            "reviewer_role": reviewer.role.value,
            "impact_score": review.impact_score
        })

        # Send real-time notification
        self._send_notification(
            self.notification_service.notify_review_assigned,
            {
                "id": str(review.id),
                "change_id": review.change_id,
                "document_title": review.document.title if hasattr(review, 'document') else "Unknown",
                "priority": review.priority,
                "assigned_by": "System",  # TODO: Track who assigned
                "reviewer": {
                    "id": str(reviewer.id),
                    "email": reviewer.email,
                    "name": reviewer.full_name
                }
            },
            str(reviewer_id)
        )

        logger.info(f"Assigned review {review_id} to {reviewer.email}")
        return review

    def approve_review(
        self,
        review_id: UUID,
        reviewer_id: UUID,
        feedback: str = None,
        modifications: Dict[str, Any] = None
    ) -> Review:
        """
        Approve a review with optional modifications.

        Args:
            review_id: ID of the review to approve
            reviewer_id: ID of the reviewer approving
            feedback: Optional feedback from reviewer
            modifications: Optional modifications made during review

        Returns:
            Review: Updated review object

        Raises:
            ValueError: If review validation fails
        """
        review = self._validate_review_action(review_id, reviewer_id)

        # Determine approval type
        if modifications:
            review.status = ReviewStatus.APPROVED_WITH_CHANGES
            review.decision = "approved_with_changes"
            review.modifications = modifications
        else:
            review.status = ReviewStatus.APPROVED
            review.decision = "approved"

        review.feedback = feedback
        review.reviewed_at = datetime.utcnow()

        self.db.commit()

        # Record metrics
        self._record_review_metric("reviews_approved", 1, {
            "with_changes": bool(modifications),
            "impact_score": review.impact_score,
            "review_time_minutes": review.review_time_minutes
        })

        # Send real-time notification
        self._send_notification(
            self.notification_service.notify_review_completed,
            {
                "id": str(review.id),
                "change_id": review.change_id,
                "status": review.status.value,
                "decision": review.decision,
                "has_modifications": bool(modifications),
                "reviewer": {
                    "email": review.reviewer.email,
                    "name": review.reviewer.full_name
                },
                "document_title": review.document.title if hasattr(review, 'document') else "Unknown"
            }
        )

        logger.info(f"Approved review {review_id} by {review.reviewer.email}")
        return review

    def reject_review(
        self,
        review_id: UUID,
        reviewer_id: UUID,
        feedback: str
    ) -> Review:
        """
        Reject a review with required feedback.

        Args:
            review_id: ID of the review to reject
            reviewer_id: ID of the reviewer rejecting
            feedback: Required feedback explaining rejection

        Returns:
            Review: Updated review object

        Raises:
            ValueError: If review validation fails or feedback missing
        """
        if not feedback or not feedback.strip():
            raise ValueError("Feedback is required when rejecting a review")

        review = self._validate_review_action(review_id, reviewer_id)

        review.status = ReviewStatus.REJECTED
        review.decision = "rejected"
        review.feedback = feedback
        review.reviewed_at = datetime.utcnow()

        self.db.commit()

        # Record metrics
        self._record_review_metric("reviews_rejected", 1, {
            "impact_score": review.impact_score,
            "review_time_minutes": review.review_time_minutes
        })

        # Send real-time notification
        self._send_notification(
            self.notification_service.notify_review_completed,
            {
                "id": str(review.id),
                "change_id": review.change_id,
                "status": review.status.value,
                "decision": review.decision,
                "feedback": feedback,
                "reviewer": {
                    "email": review.reviewer.email,
                    "name": review.reviewer.full_name
                },
                "document_title": review.document.title if hasattr(review, 'document') else "Unknown"
            }
        )

        logger.info(f"Rejected review {review_id} by {review.reviewer.email}")
        return review

    def get_review_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get review metrics for the specified time period.

        Args:
            days: Number of days to include in metrics

        Returns:
            Dict: Comprehensive review metrics
        """
        since = datetime.utcnow() - timedelta(days=days)

        # Basic counts
        total_reviews = self.db.query(Review).filter(Review.created_at >= since).count()
        pending_reviews = self.db.query(Review).filter(
            and_(Review.status == ReviewStatus.PENDING, Review.created_at >= since)
        ).count()
        approved_reviews = self.db.query(Review).filter(
            and_(Review.status.in_([ReviewStatus.APPROVED, ReviewStatus.APPROVED_WITH_CHANGES]),
                 Review.reviewed_at >= since)
        ).count()
        rejected_reviews = self.db.query(Review).filter(
            and_(Review.status == ReviewStatus.REJECTED, Review.reviewed_at >= since)
        ).count()
        auto_approved_reviews = self.db.query(Review).filter(
            and_(Review.status == ReviewStatus.AUTO_APPROVED, Review.reviewed_at >= since)
        ).count()

        # Average review time
        review_times = self.db.query(
            func.extract('epoch', Review.reviewed_at - Review.assigned_at) / 60
        ).filter(
            and_(
                Review.reviewed_at >= since,
                Review.assigned_at.isnot(None),
                Review.reviewed_at.isnot(None)
            )
        ).all()

        avg_review_time = sum(time[0] for time in review_times if time[0]) / len(review_times) if review_times else 0

        # Top reviewers
        top_reviewers = self.db.query(
            User.email,
            func.count(Review.id).label('review_count')
        ).join(Review).filter(
            Review.reviewed_at >= since
        ).group_by(User.id, User.email).order_by(desc('review_count')).limit(5).all()

        return {
            "period_days": days,
            "total_reviews": total_reviews,
            "pending_reviews": pending_reviews,
            "approved_reviews": approved_reviews,
            "rejected_reviews": rejected_reviews,
            "auto_approved_reviews": auto_approved_reviews,
            "approval_rate": (approved_reviews + auto_approved_reviews) / total_reviews if total_reviews > 0 else 0,
            "avg_review_time_minutes": round(avg_review_time, 2),
            "top_reviewers": [{"email": email, "count": count} for email, count in top_reviewers]
        }

    def _calculate_priority(self, impact_score: int, document_type: str) -> int:
        """Calculate review priority based on impact and document type."""
        priority = impact_score

        # Boost priority for critical document types
        critical_types = ["api_doc", "security_guide", "deployment_guide"]
        if document_type in critical_types:
            priority = min(10, priority + 2)

        return priority

    def _evaluate_approval_rules(self, review: Review) -> Optional[ApprovalRule]:
        """
        Evaluate approval rules against a review.

        Args:
            review: Review to evaluate

        Returns:
            ApprovalRule: Matching rule if auto-approval applies, None otherwise
        """
        # Get active rules ordered by priority
        rules = self.db.query(ApprovalRule).filter(
            ApprovalRule.is_active == True
        ).order_by(desc(ApprovalRule.priority)).all()

        for rule in rules:
            if rule.matches_review(review) and rule.action == ApprovalAction.AUTO_APPROVE:
                return rule

        return None

    def _auto_assign_review(self, review: Review) -> None:
        """
        Automatically assign a review to an appropriate reviewer.

        Args:
            review: Review to assign
        """
        # Find available reviewers based on impact score
        if review.impact_score >= 8:
            # High impact - require lead reviewer or admin
            eligible_roles = [UserRole.LEAD_REVIEWER, UserRole.ADMIN]
        else:
            # Normal impact - any reviewer
            eligible_roles = [UserRole.REVIEWER, UserRole.LEAD_REVIEWER, UserRole.ADMIN]

        # Find reviewer with least current assignments
        reviewer = self.db.query(User).filter(
            and_(
                User.role.in_(eligible_roles),
                User.is_active == True
            )
        ).outerjoin(
            Review, and_(
                Review.reviewer_id == User.id,
                Review.status.in_([ReviewStatus.PENDING, ReviewStatus.IN_REVIEW])
            )
        ).group_by(User.id).order_by(func.count(Review.id)).first()

        if reviewer:
            review.reviewer_id = reviewer.id
            review.assigned_at = datetime.utcnow()
            review.status = ReviewStatus.IN_REVIEW

    def _validate_review_action(self, review_id: UUID, reviewer_id: UUID) -> Review:
        """
        Validate that a review action can be performed.

        Args:
            review_id: ID of the review
            reviewer_id: ID of the reviewer

        Returns:
            Review: Validated review object

        Raises:
            ValueError: If validation fails
        """
        review = self.db.query(Review).options(
            joinedload(Review.reviewer),
            joinedload(Review.document)
        ).filter(Review.id == review_id).first()

        if not review:
            raise ValueError(f"Review {review_id} not found")

        if review.reviewer_id != reviewer_id:
            raise ValueError(f"Review {review_id} is not assigned to this reviewer")

        if review.status not in [ReviewStatus.PENDING, ReviewStatus.IN_REVIEW]:
            raise ValueError(f"Review {review_id} is not in reviewable state")

        return review

    def _record_review_metric(self, metric_name: str, value: int, dimensions: Dict[str, Any] = None):
        """
        Record a review metric for analytics.

        Args:
            metric_name: Name of the metric
            value: Metric value
            dimensions: Additional dimensions for the metric
        """
        try:
            metric = SystemMetric(
                id=uuid4(),
                metric_name=metric_name,
                metric_value=value,
                dimensions=dimensions or {}
            )
            self.db.add(metric)
            # Don't commit here - let the caller handle transaction
        except Exception as e:
            logger.error(f"Failed to record metric {metric_name}: {e}")


def get_review_service(db: Session) -> ReviewService:
    """Factory function to get ReviewService instance."""
    try:
        # Import here to avoid circular imports
        from core.websocket_manager import notification_service
        return ReviewService(db, notification_service)
    except ImportError:
        # Fall back to service without notifications if WebSocket not available
        return ReviewService(db)