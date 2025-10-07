"""API endpoints for viewing documentation automation plans."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencies import get_db, require_reviewer
from core.services.documentation_plan_service import DocumentationPlanService
from integrations.github_actions_integration import process_github_actions_webhook
from database.models import DocumentationPlanStatus, User

router = APIRouter()


class DocumentationPlanSummary(BaseModel):
    id: str
    repository: str
    pr_number: int
    branch: Optional[str]
    status: DocumentationPlanStatus
    execution_mode: str
    created_at: Optional[str]

    class Config:
        use_enum_values = True


class DocumentationPlanDetail(DocumentationPlanSummary):
    plan: dict
    updated_at: Optional[str]

    class Config:
        use_enum_values = True


class DocumentationPlanLinkRequest(BaseModel):
    review_id: UUID
    status: Optional[DocumentationPlanStatus] = DocumentationPlanStatus.IN_REVIEW


class DocumentationPlanRerunRequest(BaseModel):
    execute_updates: bool = False


@router.get("/", response_model=List[DocumentationPlanSummary])
async def list_documentation_plans(
    repository: Optional[str] = Query(None),
    status_filter: Optional[DocumentationPlanStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db)
):
    service = DocumentationPlanService(db)
    plans = service.list_plans(repository=repository, status_filter=status_filter, limit=limit)
    return [
        DocumentationPlanSummary(
            id=str(plan.id),
            repository=plan.repository,
            pr_number=plan.pr_number,
            branch=plan.branch,
            status=plan.status,
            execution_mode=plan.execution_mode,
            created_at=plan.created_at.isoformat() if plan.created_at else None
        )
        for plan in plans
    ]


@router.get("/{plan_id}", response_model=DocumentationPlanDetail)
async def get_documentation_plan(
    plan_id: str,
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db)
):
    service = DocumentationPlanService(db)
    try:
        plan_uuid = UUID(plan_id)
    except ValueError as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail="Invalid plan id") from exc

    plan = service.get_plan(plan_uuid)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return DocumentationPlanDetail(
        id=str(plan.id),
        repository=plan.repository,
        pr_number=plan.pr_number,
        branch=plan.branch,
        status=plan.status,
        execution_mode=plan.execution_mode,
        plan=plan.plan,
        created_at=plan.created_at.isoformat() if plan.created_at else None,
        updated_at=plan.updated_at.isoformat() if plan.updated_at else None
    )


@router.post("/{plan_id}/link-review", response_model=DocumentationPlanDetail)
async def link_plan_to_review(
    plan_id: str,
    link_request: DocumentationPlanLinkRequest,
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db)
):
    service = DocumentationPlanService(db)
    try:
        plan_uuid = UUID(plan_id)
    except ValueError as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail="Invalid plan id") from exc

    try:
        plan = service.link_to_review(
            plan_uuid,
            review_id=link_request.review_id,
            status=link_request.status or DocumentationPlanStatus.IN_REVIEW
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return DocumentationPlanDetail(
        id=str(plan.id),
        repository=plan.repository,
        pr_number=plan.pr_number,
        branch=plan.branch,
        status=plan.status,
        execution_mode=plan.execution_mode,
        plan=plan.plan,
        created_at=plan.created_at.isoformat() if plan.created_at else None,
        updated_at=plan.updated_at.isoformat() if plan.updated_at else None
    )


@router.post("/{plan_id}/rerun", response_model=DocumentationPlanDetail)
async def rerun_documentation_plan(
    plan_id: str,
    rerun_request: DocumentationPlanRerunRequest,
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db)
):
    service = DocumentationPlanService(db)
    try:
        plan_uuid = UUID(plan_id)
    except ValueError as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail="Invalid plan id") from exc

    plan = service.get_plan(plan_uuid)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    request_payload = plan.plan.get("request_payload") if isinstance(plan.plan, dict) else None
    if not request_payload:
        raise HTTPException(status_code=400, detail="Stored plan does not include request payload")

    new_result = await process_github_actions_webhook(
        request_payload,
        execute_updates=rerun_request.execute_updates
    )
    new_result["request_payload"] = request_payload

    updated_plan = service.update_plan_payload(
        plan_uuid,
        plan_payload=new_result,
        execution_mode=new_result.get("execution_mode"),
        status=DocumentationPlanStatus.PENDING
    )

    if not updated_plan:
        raise HTTPException(status_code=500, detail="Failed to update plan")

    return DocumentationPlanDetail(
        id=str(updated_plan.id),
        repository=updated_plan.repository,
        pr_number=updated_plan.pr_number,
        branch=updated_plan.branch,
        status=updated_plan.status,
        execution_mode=updated_plan.execution_mode,
        plan=updated_plan.plan,
        created_at=updated_plan.created_at.isoformat() if updated_plan.created_at else None,
        updated_at=updated_plan.updated_at.isoformat() if updated_plan.updated_at else None
    )
