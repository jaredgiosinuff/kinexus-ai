"""Service for persisting and retrieving documentation automation plans."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database.models import DocumentationPlan, DocumentationPlanStatus, Review


class DocumentationPlanService:
    """Handles CRUD operations for documentation plans."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_plan(
        self,
        repository: str,
        pr_number: int,
        branch: Optional[str],
        execution_mode: str,
        plan_payload: Dict[str, Any],
        status: DocumentationPlanStatus = DocumentationPlanStatus.PENDING,
        review_id: Optional[UUID] = None
    ) -> DocumentationPlan:
        plan = DocumentationPlan(
            repository=repository,
            pr_number=pr_number,
            branch=branch,
            execution_mode=execution_mode,
            plan=plan_payload,
            status=status,
            review_id=review_id
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def list_plans(
        self,
        repository: Optional[str] = None,
        status_filter: Optional[DocumentationPlanStatus] = None,
        limit: int = 50
    ) -> List[DocumentationPlan]:
        query = self.db.query(DocumentationPlan)
        if repository:
            query = query.filter(DocumentationPlan.repository == repository)
        if status_filter:
            query = query.filter(DocumentationPlan.status == status_filter)
        return (
            query.order_by(DocumentationPlan.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_plan(self, plan_id: UUID) -> Optional[DocumentationPlan]:
        return (
            self.db.query(DocumentationPlan)
            .filter(DocumentationPlan.id == plan_id)
            .first()
        )

    def update_status(
        self,
        plan_id: UUID,
        status: DocumentationPlanStatus,
        execution_mode: Optional[str] = None,
        execution_details: Optional[Dict[str, Any]] = None
    ) -> Optional[DocumentationPlan]:
        plan = self.get_plan(plan_id)
        if not plan:
            return None
        plan.status = status
        if execution_mode:
            plan.execution_mode = execution_mode
        if execution_details:
            plan.plan = {**plan.plan, "execution_results": execution_details}
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def update_plan_payload(
        self,
        plan_id: UUID,
        plan_payload: Dict[str, Any],
        execution_mode: Optional[str] = None,
        status: Optional[DocumentationPlanStatus] = None
    ) -> Optional[DocumentationPlan]:
        plan = self.get_plan(plan_id)
        if not plan:
            return None
        plan.plan = plan_payload
        if execution_mode:
            plan.execution_mode = execution_mode
        if status:
            plan.status = status
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def link_to_review(
        self,
        plan_id: UUID,
        review_id: UUID,
        status: DocumentationPlanStatus = DocumentationPlanStatus.IN_REVIEW
    ) -> Optional[DocumentationPlan]:
        plan = self.get_plan(plan_id)
        if not plan:
            return None

        review = (
            self.db.query(Review)
            .filter(Review.id == review_id)
            .first()
        )
        if not review:
            raise ValueError("Review not found")

        plan.review_id = review.id
        plan.status = status
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan
