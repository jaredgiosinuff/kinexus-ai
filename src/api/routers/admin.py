"""
Admin API router for Kinexus AI.

Handles administrative functions like user management, system configuration,
approval rules, and system metrics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, require_admin, require_lead_reviewer
from database.models import ApprovalRule, User

router = APIRouter()


@router.get("/users")
async def list_users(
    current_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """List all users (admin only)."""
    users = db.query(User).all()
    return [
        {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
        }
        for user in users
    ]


@router.get("/approval-rules")
async def list_approval_rules(
    current_user: User = Depends(require_lead_reviewer), db: Session = Depends(get_db)
):
    """List approval rules."""
    rules = db.query(ApprovalRule).order_by(ApprovalRule.priority.desc()).all()
    return [
        {
            "id": str(rule.id),
            "name": rule.name,
            "description": rule.description,
            "conditions": rule.conditions,
            "action": rule.action.value,
            "priority": rule.priority,
            "is_active": rule.is_active,
            "times_applied": rule.times_applied,
            "last_applied": (
                rule.last_applied.isoformat() if rule.last_applied else None
            ),
        }
        for rule in rules
    ]


@router.get("/system-status")
async def get_system_status(
    current_user: User = Depends(require_lead_reviewer), db: Session = Depends(get_db)
):
    """Get system status and health metrics."""
    return {
        "status": "healthy",
        "database": "connected",
        "active_users": db.query(User).filter(User.is_active is True).count(),
        "pending_reviews": 0,  # TODO: Get from review service
        "message": "System status endpoint - to be fully implemented",
    }
