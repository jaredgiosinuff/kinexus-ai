"""Documents API router for Kinexus AI.

Provides read access to documents, versions, and diffs for reviewers.
"""

import difflib
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.dependencies import get_db, require_reviewer
from database.models import Document, DocumentStatus, DocumentVersion, User

router = APIRouter()


class DocumentListItem(BaseModel):
    id: str
    external_id: str
    source_system: str
    path: str
    title: str
    document_type: str
    status: DocumentStatus
    current_version: int
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True
        from_attributes = True


class DocumentVersionSummary(BaseModel):
    id: str
    version: int
    ai_generated: bool
    ai_model: Optional[str]
    ai_confidence: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentVersionDetail(DocumentVersionSummary):
    content: str
    content_format: str
    change_summary: Optional[str]


class DocumentDetail(BaseModel):
    id: str
    external_id: str
    source_system: str
    path: str
    title: str
    document_type: str
    status: DocumentStatus
    current_version: int
    doc_metadata: Optional[dict]
    created_at: datetime
    updated_at: Optional[datetime]
    latest_version: Optional[DocumentVersionDetail]
    version_count: int

    class Config:
        use_enum_values = True
        from_attributes = True


def _parse_document_id(document_id: str) -> UUID:
    try:
        return UUID(document_id)
    except ValueError as exc:  # pragma: no cover - validated by FastAPI in practice
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document ID") from exc


@router.get("/", response_model=List[DocumentListItem])
async def get_documents(
    status_filter: Optional[DocumentStatus] = Query(None, alias="status"),
    document_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search title or path"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db)
):
    """Return a list of documents with optional filtering."""
    query = db.query(Document)

    if status_filter:
        query = query.filter(Document.status == status_filter)
    if document_type:
        query = query.filter(Document.document_type == document_type)
    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(Document.title.ilike(pattern), Document.path.ilike(pattern)))

    documents = (
        query.order_by(Document.updated_at.desc().nullslast(), Document.created_at.desc())
        .limit(limit)
        .all()
    )

    return [DocumentListItem.from_orm(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: str,
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db)
):
    """Return metadata for a specific document including its latest version."""
    doc_uuid = _parse_document_id(document_id)
    document = (
        db.query(Document)
        .filter(Document.id == doc_uuid)
        .first()
    )

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    latest_version = document.latest_version
    latest_detail = DocumentVersionDetail.from_orm(latest_version) if latest_version else None

    return DocumentDetail(
        id=str(document.id),
        external_id=document.external_id,
        source_system=document.source_system,
        path=document.path,
        title=document.title,
        document_type=document.document_type,
        status=document.status,
        current_version=document.current_version,
        doc_metadata=document.doc_metadata,
        created_at=document.created_at,
        updated_at=document.updated_at,
        latest_version=latest_detail,
        version_count=len(document.versions)
    )


@router.get("/{document_id}/versions", response_model=List[DocumentVersionDetail])
async def get_document_versions(
    document_id: str,
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db)
):
    """Return all versions for a document ordered by newest first."""
    doc_uuid = _parse_document_id(document_id)
    versions = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == doc_uuid)
        .order_by(DocumentVersion.version.desc())
        .all()
    )

    if not versions:
        # Validate document existence before returning empty list
        document_exists = db.query(Document.id).filter(Document.id == doc_uuid).first()
        if not document_exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return []

    return [DocumentVersionDetail.from_orm(version) for version in versions]


@router.get("/{document_id}/diff")
async def get_document_diff(
    document_id: str,
    version_from: int = Query(..., ge=1),
    version_to: int = Query(..., ge=1),
    current_user: User = Depends(require_reviewer),
    db: Session = Depends(get_db)
):
    """Return a unified diff between two document versions."""
    if version_from == version_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Versions must be different")

    doc_uuid = _parse_document_id(document_id)

    version_a = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == doc_uuid, DocumentVersion.version == version_from)
        .first()
    )
    version_b = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == doc_uuid, DocumentVersion.version == version_to)
        .first()
    )

    if not version_a or not version_b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or both versions not found")

    diff_lines = difflib.unified_diff(
        version_a.content.splitlines(),
        version_b.content.splitlines(),
        fromfile=f"v{version_from}",
        tofile=f"v{version_to}",
        lineterm=""
    )

    diff_text = "\n".join(diff_lines)

    return {
        "document_id": document_id,
        "version_from": version_from,
        "version_to": version_to,
        "diff": diff_text
    }
