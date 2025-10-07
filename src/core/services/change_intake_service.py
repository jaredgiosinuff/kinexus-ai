"""Change intake orchestration tying webhooks to review + AI pipeline."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, Optional, Tuple

from sqlalchemy.orm import Session

from core.config import settings
from core.services.metrics_service import metrics_service
from core.services.review_service import ReviewService
from database.models import Document, DocumentStatus, DocumentVersion, Review, User

logger = logging.getLogger(__name__)


class ChangeIntakeService:
    """Coordinates webhook change payloads with review + multi-agent pipeline."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.review_service = ReviewService(db)
        self._supervisor = None

    async def process_github_push(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a GitHub push payload and kick off review + AI analysis."""
        repository = payload.get("repository", {}).get("full_name")
        if not repository:
            raise ValueError("Missing repository information in payload")

        change_id = payload.get("after") or payload.get("head_commit", {}).get("id")
        if not change_id:
            raise ValueError("Unable to determine change identifier")

        commit_files = self._extract_files(payload.get("commits", []))
        change_context = {
            "source": "github",
            "repository": repository,
            "ref": payload.get("ref"),
            "before": payload.get("before"),
            "after": payload.get("after"),
            "pusher": payload.get("pusher", {}),
            "commits": payload.get("commits", []),
            "files": list(commit_files)
        }

        system_user = self._get_system_user()
        document, proposed_version = self._get_or_create_document(repository, commit_files, system_user)
        impact_score = self._estimate_impact(commit_files)

        review = self.review_service.create_review(
            document_id=document.id,
            change_id=change_id,
            proposed_version=proposed_version,
            impact_score=impact_score,
            change_context=change_context
        )

        ai_result = await self._generate_ai_output(change_context)
        self._update_review_with_ai(review, ai_result, change_context)
        self._create_or_update_document_version(document, proposed_version, system_user, review, ai_result)

        document.current_version = proposed_version
        self.db.add_all([document, review])
        self.db.commit()

        metrics_service.changes_detected.labels(source="github", change_type="push").inc()

        return {
            "status": "processed",
            "change_id": change_id,
            "review_id": str(review.id),
            "document_id": str(document.id),
            "ai_automation": bool(ai_result) and not ai_result.get("disabled")
        }

    def _extract_files(self, commits: Iterable[Dict[str, Any]]) -> Iterable[str]:
        files: set[str] = set()
        for commit in commits or []:
            for key in ("added", "modified", "removed"):
                for path in commit.get(key, []) or []:
                    files.add(path)
        return files or {"README.md"}

    def _get_system_user(self) -> User:
        email = getattr(settings, "SYSTEM_USER_EMAIL", "admin@kinexusai.com")
        user = self.db.query(User).filter(User.email == email.lower()).first()
        if not user:
            user = self.db.query(User).order_by(User.created_at).first()
        if not user:
            raise RuntimeError("No users available to associate automated changes")
        return user

    def _get_or_create_document(
        self,
        repository: str,
        files: Iterable[str],
        system_user: User
    ) -> Tuple[Document, int]:
        primary_path = next(iter(files), "repository")
        external_id = f"{repository}:{primary_path}"

        document = (
            self.db.query(Document)
            .filter(Document.source_system == "github", Document.external_id == external_id)
            .first()
        )

        if not document:
            document = Document(
                external_id=external_id,
                source_system="github",
                path=primary_path,
                title=f"{repository} :: {primary_path}",
                document_type="code_change",
                doc_metadata={"repository": repository, "primary_path": primary_path},
                created_by=system_user.id,
                status=DocumentStatus.ACTIVE
            )
            self.db.add(document)
            self.db.flush()

        proposed_version = (document.current_version or 1) + 1
        return document, proposed_version

    def _estimate_impact(self, files: Iterable[str]) -> int:
        count = len(list(files)) if files else 1
        return max(1, min(count, 10))

    async def _generate_ai_output(self, change_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not settings.ENABLE_MULTI_AGENT_AUTOMATION:
            return {"disabled": True, "reason": "ENABLE_MULTI_AGENT_AUTOMATION is false"}

        supervisor = await self._get_supervisor()
        if not supervisor:
            return {"disabled": True, "reason": "MultiAgentSupervisor unavailable"}

        try:
            return await supervisor.process_change_event(change_context)
        except Exception as exc:  # pragma: no cover - network/service failures
            logger.exception("Multi-agent supervisor failed")
            return {"error": str(exc)}

    async def _get_supervisor(self):
        if self._supervisor is not None:
            return self._supervisor
        try:
            from agents.multi_agent_supervisor import MultiAgentSupervisor

            self._supervisor = MultiAgentSupervisor(region=settings.BEDROCK_REGION)
        except Exception as exc:  # pragma: no cover
            logger.warning("Unable to initialize MultiAgentSupervisor: %s", exc)
            self._supervisor = None
        return self._supervisor

    def _update_review_with_ai(
        self,
        review: Review,
        ai_result: Optional[Dict[str, Any]],
        change_context: Dict[str, Any]
    ) -> None:
        review.change_context = change_context
        if not ai_result:
            return

        review.ai_model = "multi-agent-supervisor"
        review.ai_reasoning = json.dumps(ai_result, indent=2, default=str)

        confidence = 0
        try:
            confidence = ai_result.get("multi_agent_processing", {}).get("average_confidence", 0)
        except AttributeError:
            confidence = 0
        review.ai_confidence = int(confidence * 100)

    def _create_or_update_document_version(
        self,
        document: Document,
        version: int,
        system_user: User,
        review: Review,
        ai_result: Optional[Dict[str, Any]]
    ) -> None:
        if not ai_result or ai_result.get("disabled"):
            return

        synthesis = ai_result.get("multi_agent_processing", {}).get("synthesis")
        if isinstance(synthesis, dict):
            analysis = synthesis.get("analysis")
            recommendations = synthesis.get("recommendations", [])
            content_parts = []
            if analysis:
                content_parts.append(f"## Analysis\n\n{analysis}")
            if recommendations:
                content_parts.append("## Recommendations\n\n" + "\n".join(f"- {item}" for item in recommendations))
            if not content_parts:
                content_parts.append(json.dumps(synthesis, indent=2, default=str))
            content = "\n\n".join(content_parts)
        else:
            content = json.dumps(ai_result, indent=2, default=str)

        doc_version = (
            self.db.query(DocumentVersion)
            .filter(DocumentVersion.document_id == document.id, DocumentVersion.version == version)
            .first()
        )

        confidence_value = review.ai_confidence if isinstance(review.ai_confidence, int) else 0

        if not doc_version:
            doc_version = DocumentVersion(
                document_id=document.id,
                version=version,
                content=content,
                ai_generated=True,
                ai_model="multi-agent-supervisor",
                ai_confidence=min(100, max(confidence_value, 0)),
                created_by=system_user.id
            )
        else:
            doc_version.content = content
            doc_version.ai_generated = True
            doc_version.ai_model = "multi-agent-supervisor"
            doc_version.ai_confidence = min(100, max(confidence_value, 0))

        self.db.add(doc_version)
        # End of document version update
