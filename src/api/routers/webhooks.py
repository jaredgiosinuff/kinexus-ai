"""
Webhooks API router for Kinexus AI.

Handles incoming webhooks from GitHub, Jira, and other integrated systems.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.dependencies import get_db, validate_webhook_signature
from core.config import settings
from core.services.change_intake_service import ChangeIntakeService
from core.services.documentation_plan_service import DocumentationPlanService
from integrations.github_actions_integration import process_github_actions_webhook

router = APIRouter()


@router.post("/github")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle GitHub webhook events.

    This will integrate with the existing Lambda function logic.
    """
    # Validate signature if secret is configured
    if settings.WEBHOOK_SECRET_GITHUB:
        await validate_webhook_signature(
            request, "X-Hub-Signature-256", settings.WEBHOOK_SECRET_GITHUB
        )

    # Get event data
    event_type = request.headers.get("X-GitHub-Event")
    payload = await request.json()

    service = ChangeIntakeService(db)

    if event_type == "push":
        try:
            result = await service.process_github_push(payload)
            result.update({"event": event_type})
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"status": "received", "event": event_type}


@router.post("/jira")
async def jira_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Jira webhook events.

    This will integrate with the existing Lambda function logic.
    """
    # TODO: Validate Jira webhook signature

    # Get event data
    payload = await request.json()
    event_type = payload.get("webhookEvent")

    # TODO: Process webhook using existing logic from Lambda function

    return {"status": "received", "event": event_type}


@router.post("/slack")
async def slack_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Slack webhook events.
    """
    _payload = await request.json()

    # TODO: Process Slack events

    return {"status": "received"}


@router.post("/github/actions")
async def github_actions_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle GitHub Actions workflow hooks for pull request automation."""
    expected_token = settings.GITHUB_ACTIONS_WEBHOOK_TOKEN
    if not expected_token:
        raise HTTPException(
            status_code=503, detail="GitHub Actions automation not configured"
        )

    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "", 1).strip()
    if token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid authorization token")

    payload = await request.json()

    result = await process_github_actions_webhook(payload, execute_updates=False)
    result["request_payload"] = payload

    plan_service = DocumentationPlanService(db)
    repository_name = payload.get("repository", {}).get("full_name", "")
    plan = plan_service.create_plan(
        repository=repository_name,
        pr_number=payload.get("pull_request", {}).get("number", 0),
        branch=payload.get("pull_request", {}).get("base", {}).get("ref"),
        execution_mode=result.get("execution_mode", "plan_only"),
        plan_payload=result,
    )
    result["plan_id"] = str(plan.id)

    return result
