"""
Reviews API router for Kinexus AI.

Handles all review workflow operations including queue management,
assignment, approval/rejection, and metrics.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import (
    create_audit_logger,
    get_current_active_user,
    get_db,
    require_reviewer,
)
from core.services.review_service import get_review_service
from database.models import Document, Review, ReviewStatus, User

router = APIRouter()


# Pydantic models
class ReviewResponse(BaseModel):
    """Review response model."""

    id: str
    document_id: str
    change_id: str
    proposed_version: int
    status: ReviewStatus
    priority: int
    impact_score: int
    reviewer_id: Optional[str] = None
    assigned_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    decision: Optional[str] = None
    feedback: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None
    ai_reasoning: Optional[str] = None
    ai_confidence: Optional[int] = None
    ai_model: Optional[str] = None
    change_context: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: Optional[str] = None

    # Related objects
    document: Optional[Dict[str, Any]] = None
    reviewer: Optional[Dict[str, Any]] = None
    documentation_plans: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_review(cls, review: Review) -> "ReviewResponse":
        """Create response from Review model."""
        data = {
            "id": str(review.id),
            "document_id": str(review.document_id),
            "change_id": review.change_id,
            "proposed_version": review.proposed_version,
            "status": review.status,
            "priority": review.priority,
            "impact_score": review.impact_score,
            "reviewer_id": str(review.reviewer_id) if review.reviewer_id else None,
            "assigned_at": (
                review.assigned_at.isoformat() if review.assigned_at else None
            ),
            "reviewed_at": (
                review.reviewed_at.isoformat() if review.reviewed_at else None
            ),
            "decision": review.decision,
            "feedback": review.feedback,
            "modifications": review.modifications,
            "ai_reasoning": review.ai_reasoning,
            "ai_confidence": review.ai_confidence,
            "ai_model": review.ai_model,
            "change_context": review.change_context,
            "created_at": review.created_at.isoformat(),
            "updated_at": review.updated_at.isoformat() if review.updated_at else None,
        }

        # Add related objects if loaded
        if hasattr(review, "document") and review.document:
            data["document"] = {
                "id": str(review.document.id),
                "title": review.document.title,
                "document_type": review.document.document_type,
                "source_system": review.document.source_system,
                "path": review.document.path,
            }

        if hasattr(review, "reviewer") and review.reviewer:
            data["reviewer"] = {
                "id": str(review.reviewer.id),
                "email": review.reviewer.email,
                "full_name": review.reviewer.full_name,
                "role": review.reviewer.role.value,
            }

        if hasattr(review, "documentation_plans") and review.documentation_plans:
            data["documentation_plans"] = [
                {
                    "id": str(plan.id),
                    "status": plan.status.value,
                    "execution_mode": plan.execution_mode,
                    "created_at": (
                        plan.created_at.isoformat() if plan.created_at else None
                    ),
                }
                for plan in review.documentation_plans
            ]

        return cls(**data)


class ReviewAssignment(BaseModel):
    """Review assignment request model."""

    reviewer_id: str


class ReviewApproval(BaseModel):
    """Review approval request model."""

    feedback: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None


class ReviewRejection(BaseModel):
    """Review rejection request model."""

    feedback: str = Field(
        ..., min_length=1, description="Feedback is required for rejection"
    )


class ReviewCreate(BaseModel):
    """Review creation request model."""

    document_id: str
    change_id: str
    proposed_version: int
    impact_score: int = Field(..., ge=1, le=10, description="Impact score from 1-10")
    ai_reasoning: Optional[str] = None
    ai_confidence: Optional[int] = Field(
        None, ge=1, le=100, description="AI confidence from 1-100"
    )
    ai_model: Optional[str] = None
    change_context: Optional[Dict[str, Any]] = None
    priority: Optional[int] = Field(None, ge=1, le=10, description="Priority from 1-10")


class ReviewMetrics(BaseModel):
    """Review metrics response model."""

    period_days: int
    total_reviews: int
    pending_reviews: int
    approved_reviews: int
    rejected_reviews: int
    auto_approved_reviews: int
    approval_rate: float
    avg_review_time_minutes: float
    top_reviewers: List[Dict[str, Any]]


@router.get("/", response_model=List[ReviewResponse])
async def get_reviews(
    status: Optional[List[ReviewStatus]] = Query(
        None, description="Filter by review status"
    ),
    reviewer_id: Optional[str] = Query(None, description="Filter by reviewer ID"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    priority_min: Optional[int] = Query(
        None, ge=1, le=10, description="Minimum priority level"
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    """
    Get reviews from the queue with filtering and pagination.

    Reviewers can see all reviews, but viewers can only see completed reviews.
    """
    review_service = get_review_service(db)

    # Convert reviewer_id to UUID if provided
    reviewer_uuid = None
    if reviewer_id:
        try:
            reviewer_uuid = UUID(reviewer_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reviewer ID format",
            )

    # Get reviews
    reviews = review_service.get_review_queue(
        reviewer_id=reviewer_uuid,
        status=status,
        priority_min=priority_min,
        document_type=document_type,
        limit=limit,
        offset=offset,
    )

    return [ReviewResponse.from_review(review) for review in reviews]


@router.get("/my-queue", response_model=List[ReviewResponse])
async def get_my_review_queue(
    status: Optional[List[ReviewStatus]] = Query(
        [ReviewStatus.PENDING, ReviewStatus.IN_REVIEW]
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    """
    Get reviews assigned to the current user.
    """
    review_service = get_review_service(db)

    reviews = review_service.get_review_queue(
        reviewer_id=current_user.id, status=status, limit=limit, offset=offset
    )

    return [ReviewResponse.from_review(review) for review in reviews]


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: str,
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    """
    Get a specific review by ID.
    """
    try:
        review_uuid = UUID(review_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid review ID format"
        )

    review = db.query(Review).filter(Review.id == review_uuid).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review not found"
        )

    return ReviewResponse.from_review(review)


@router.post("/", response_model=ReviewResponse)
async def create_review(
    review_data: ReviewCreate,
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
    audit_log=Depends(create_audit_logger("review_created", "review")),
):
    """
    Create a new review (typically called by webhook handlers).
    """
    review_service = get_review_service(db)

    try:
        document_uuid = UUID(review_data.document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document ID format"
        )

    try:
        review = review_service.create_review(
            document_id=document_uuid,
            change_id=review_data.change_id,
            proposed_version=review_data.proposed_version,
            impact_score=review_data.impact_score,
            ai_reasoning=review_data.ai_reasoning,
            ai_confidence=review_data.ai_confidence,
            ai_model=review_data.ai_model,
            change_context=review_data.change_context,
            priority=review_data.priority,
        )

        # Update audit log with review ID
        audit_log.resource_id = review.id
        db.commit()

        return ReviewResponse.from_review(review)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{review_id}/assign", response_model=ReviewResponse)
async def assign_review(
    review_id: str,
    assignment: ReviewAssignment,
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
    audit_log=Depends(create_audit_logger("review_assigned", "review")),
):
    """
    Assign a review to a specific reviewer.
    """
    review_service = get_review_service(db)

    try:
        review_uuid = UUID(review_id)
        reviewer_uuid = UUID(assignment.reviewer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format"
        )

    try:
        review = review_service.assign_review(review_uuid, reviewer_uuid)

        # Update audit log
        audit_log.resource_id = review.id
        audit_log.new_values = {"reviewer_id": assignment.reviewer_id}
        db.commit()

        return ReviewResponse.from_review(review)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{review_id}/approve", response_model=ReviewResponse)
async def approve_review(
    review_id: str,
    approval: ReviewApproval,
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
    audit_log=Depends(create_audit_logger("review_approved", "review")),
):
    """
    Approve a review with optional feedback and modifications.
    """
    review_service = get_review_service(db)

    try:
        review_uuid = UUID(review_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid review ID format"
        )

    try:
        review = review_service.approve_review(
            review_uuid,
            current_user.id,
            feedback=approval.feedback,
            modifications=approval.modifications,
        )

        # Update audit log
        audit_log.resource_id = review.id
        audit_log.new_values = {
            "status": review.status.value,
            "decision": review.decision,
            "has_modifications": bool(approval.modifications),
        }
        db.commit()

        return ReviewResponse.from_review(review)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{review_id}/reject", response_model=ReviewResponse)
async def reject_review(
    review_id: str,
    rejection: ReviewRejection,
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
    audit_log=Depends(create_audit_logger("review_rejected", "review")),
):
    """
    Reject a review with required feedback.
    """
    review_service = get_review_service(db)

    try:
        review_uuid = UUID(review_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid review ID format"
        )

    try:
        review = review_service.reject_review(
            review_uuid, current_user.id, feedback=rejection.feedback
        )

        # Update audit log
        audit_log.resource_id = review.id
        audit_log.new_values = {
            "status": review.status.value,
            "decision": review.decision,
        }
        db.commit()

        return ReviewResponse.from_review(review)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/metrics/summary", response_model=ReviewMetrics)
async def get_review_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days for metrics"),
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db),
):
    """
    Get review metrics and analytics.
    """
    review_service = get_review_service(db)
    metrics = review_service.get_review_metrics(days=days)
    return ReviewMetrics(**metrics)
