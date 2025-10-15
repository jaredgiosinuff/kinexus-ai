"""
Change Tracking System with Multiple Sources and Review Workflows
Supports internal reviews, Jira ticket workflows, and ServiceNow integration
"""

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from ..services.logging_service import StructuredLogger


class ChangeSource(Enum):
    """Sources of change detection"""

    GITHUB = "github"
    GITLAB = "gitlab"
    JIRA = "jira"
    SERVICENOW = "servicenow"
    CONFLUENCE = "confluence"
    SHAREPOINT = "sharepoint"
    MONDAY = "monday"
    SLACK = "slack"
    MANUAL = "manual"
    API = "api"


class ChangeType(Enum):
    """Types of changes detected"""

    CODE_CHANGE = "code_change"
    DOCUMENTATION_UPDATE = "documentation_update"
    CONFIGURATION_CHANGE = "configuration_change"
    PROCESS_CHANGE = "process_change"
    INCIDENT_RESOLUTION = "incident_resolution"
    FEATURE_REQUEST = "feature_request"
    BUG_FIX = "bug_fix"
    SECURITY_UPDATE = "security_update"
    INFRASTRUCTURE_CHANGE = "infrastructure_change"
    POLICY_UPDATE = "policy_update"


class ReviewWorkflow(Enum):
    """Available review workflows"""

    INTERNAL_ONLY = "internal_only"  # Use our dashboard only
    JIRA_TICKET = "jira_ticket"  # Create Jira ticket and track
    HYBRID = "hybrid"  # Both internal and external
    SERVICENOW_TICKET = "servicenow_ticket"  # ServiceNow change request
    EXTERNAL_ONLY = "external_only"  # Only external system


class ChangeStatus(Enum):
    """Status of a change throughout its lifecycle"""

    DETECTED = "detected"
    ANALYZING = "analyzing"
    PENDING_REVIEW = "pending_review"
    IN_REVIEW = "in_review"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ExternalTicketStatus(Enum):
    """Status mapping for external ticket systems"""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class ExternalTicket:
    """Represents a ticket in an external system"""

    ticket_id: str
    system: str  # jira, servicenow, etc.
    url: str
    status: ExternalTicketStatus
    assignee: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangeEvent:
    """Represents a detected change from any source"""

    id: str = field(default_factory=lambda: str(uuid4()))
    source: ChangeSource = ChangeSource.API
    change_type: ChangeType = ChangeType.DOCUMENTATION_UPDATE
    title: str = ""
    description: str = ""
    affected_documents: List[str] = field(default_factory=list)
    impact_assessment: Optional[Dict[str, Any]] = None
    confidence_score: float = 0.5
    urgency: str = "medium"  # low, medium, high, critical
    risk_level: str = "medium"  # low, medium, high

    # Source-specific data
    source_id: Optional[str] = None  # ID in the source system
    source_url: Optional[str] = None
    source_metadata: Dict[str, Any] = field(default_factory=dict)

    # Change details
    changes_detected: List[Dict[str, Any]] = field(default_factory=list)
    files_affected: List[str] = field(default_factory=list)

    # Workflow configuration
    review_workflow: ReviewWorkflow = ReviewWorkflow.INTERNAL_ONLY
    auto_approve_rules: List[str] = field(default_factory=list)
    required_approvers: List[str] = field(default_factory=list)

    # Status tracking
    status: ChangeStatus = ChangeStatus.DETECTED
    external_tickets: List[ExternalTicket] = field(default_factory=list)

    # Timestamps
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    review_started_at: Optional[datetime] = None
    review_completed_at: Optional[datetime] = None

    # AI Analysis
    ai_analysis: Optional[Dict[str, Any]] = None
    recommended_actions: List[str] = field(default_factory=list)


class ChangeDetector(ABC):
    """Base class for change detection from various sources"""

    def __init__(self, source: ChangeSource, config: Dict[str, Any]):
        self.source = source
        self.config = config
        self.logger = StructuredLogger(name=f"ChangeDetector-{source.value}")

    @abstractmethod
    async def detect_changes(
        self, since: Optional[datetime] = None
    ) -> List[ChangeEvent]:
        """Detect changes from the source"""
        pass

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate connection to the source"""
        pass

    @abstractmethod
    def get_supported_change_types(self) -> List[ChangeType]:
        """Get supported change types for this source"""
        pass


class ServiceNowChangeDetector(ChangeDetector):
    """ServiceNow change detection and integration"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ChangeSource.SERVICENOW, config)
        self.instance_url = config.get("instance_url")
        self.username = config.get("username")
        self.password = config.get("password")
        self.table = config.get("table", "change_request")

    async def detect_changes(
        self, since: Optional[datetime] = None
    ) -> List[ChangeEvent]:
        """Detect changes from ServiceNow change requests"""
        changes = []

        try:
            # Build ServiceNow API query
            query_params = {
                "sysparm_table": self.table,
                "sysparm_query": self._build_query(since),
                "sysparm_fields": "sys_id,number,short_description,description,state,priority,risk,impact,assigned_to,opened_at,updated_at",
            }

            # Make API call to ServiceNow
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.instance_url}/api/now/table/{self.table}",
                    params=query_params,
                    auth=(self.username, self.password),
                    headers={"Accept": "application/json"},
                )

                if response.status_code == 200:
                    data = response.json()
                    for record in data.get("result", []):
                        change_event = self._parse_servicenow_record(record)
                        changes.append(change_event)

        except Exception as e:
            self.logger.error(f"Failed to detect ServiceNow changes: {e}")

        return changes

    async def create_change_request(
        self, change_event: ChangeEvent
    ) -> Optional[ExternalTicket]:
        """Create a change request in ServiceNow"""
        try:
            payload = {
                "short_description": change_event.title,
                "description": change_event.description,
                "priority": self._map_urgency_to_priority(change_event.urgency),
                "risk": self._map_risk_level(change_event.risk_level),
                "category": "Documentation",
                "type": "Normal",
                "state": "1",  # New
                "requested_by": self.config.get("default_requestor"),
                "assignment_group": self.config.get("assignment_group"),
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.instance_url}/api/now/table/{self.table}",
                    json=payload,
                    auth=(self.username, self.password),
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )

                if response.status_code == 201:
                    result = response.json()["result"]
                    return ExternalTicket(
                        ticket_id=result["sys_id"],
                        system="servicenow",
                        url=f"{self.instance_url}/nav_to.do?uri=change_request.do?sys_id={result['sys_id']}",
                        status=ExternalTicketStatus.OPEN,
                        metadata=result,
                    )

        except Exception as e:
            self.logger.error(f"Failed to create ServiceNow change request: {e}")

        return None

    async def update_change_request(
        self, ticket: ExternalTicket, updates: Dict[str, Any]
    ) -> bool:
        """Update a ServiceNow change request"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.instance_url}/api/now/table/{self.table}/{ticket.ticket_id}",
                    json=updates,
                    auth=(self.username, self.password),
                    headers={"Content-Type": "application/json"},
                )
                return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Failed to update ServiceNow change request: {e}")
            return False

    async def validate_connection(self) -> bool:
        """Validate ServiceNow connection"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.instance_url}/api/now/table/{self.table}",
                    params={"sysparm_limit": "1"},
                    auth=(self.username, self.password),
                )
                return response.status_code == 200
        except:
            return False

    def get_supported_change_types(self) -> List[ChangeType]:
        return [
            ChangeType.DOCUMENTATION_UPDATE,
            ChangeType.PROCESS_CHANGE,
            ChangeType.CONFIGURATION_CHANGE,
            ChangeType.INFRASTRUCTURE_CHANGE,
            ChangeType.POLICY_UPDATE,
        ]

    def _build_query(self, since: Optional[datetime]) -> str:
        """Build ServiceNow query string"""
        query_parts = []

        if since:
            since_str = since.strftime("%Y-%m-%d %H:%M:%S")
            query_parts.append(f"updated_at>={since_str}")

        # Filter for relevant change types
        query_parts.append(
            "category=Documentation^ORcategory=Software^ORcategory=Hardware"
        )

        return "^".join(query_parts)

    def _parse_servicenow_record(self, record: Dict[str, Any]) -> ChangeEvent:
        """Parse ServiceNow record into ChangeEvent"""
        return ChangeEvent(
            source=ChangeSource.SERVICENOW,
            change_type=ChangeType.PROCESS_CHANGE,
            title=record.get("short_description", ""),
            description=record.get("description", ""),
            source_id=record.get("sys_id"),
            source_url=f"{self.instance_url}/nav_to.do?uri=change_request.do?sys_id={record.get('sys_id')}",
            source_metadata=record,
            urgency=self._map_priority_to_urgency(record.get("priority", "3")),
            risk_level=self._map_servicenow_risk(record.get("risk", "3")),
            review_workflow=ReviewWorkflow.SERVICENOW_TICKET,
            external_tickets=[
                ExternalTicket(
                    ticket_id=record.get("sys_id"),
                    system="servicenow",
                    url=f"{self.instance_url}/nav_to.do?uri=change_request.do?sys_id={record.get('sys_id')}",
                    status=self._map_servicenow_state(record.get("state", "1")),
                    metadata=record,
                )
            ],
        )

    def _map_urgency_to_priority(self, urgency: str) -> str:
        mapping = {"low": "4", "medium": "3", "high": "2", "critical": "1"}
        return mapping.get(urgency, "3")

    def _map_priority_to_urgency(self, priority: str) -> str:
        mapping = {"1": "critical", "2": "high", "3": "medium", "4": "low"}
        return mapping.get(priority, "medium")

    def _map_risk_level(self, risk: str) -> str:
        mapping = {"low": "4", "medium": "3", "high": "2"}
        return mapping.get(risk, "3")

    def _map_servicenow_risk(self, risk: str) -> str:
        mapping = {"1": "high", "2": "high", "3": "medium", "4": "low"}
        return mapping.get(risk, "medium")

    def _map_servicenow_state(self, state: str) -> ExternalTicketStatus:
        mapping = {
            "-5": ExternalTicketStatus.CLOSED,  # Cancelled
            "-4": ExternalTicketStatus.REJECTED,  # Cancelled
            "-3": ExternalTicketStatus.CLOSED,  # Closed Incomplete
            "-2": ExternalTicketStatus.CLOSED,  # Closed Skipped
            "-1": ExternalTicketStatus.CLOSED,  # Closed
            "0": ExternalTicketStatus.RESOLVED,  # Closed Complete
            "1": ExternalTicketStatus.OPEN,  # New
            "2": ExternalTicketStatus.IN_PROGRESS,  # Assess
            "3": ExternalTicketStatus.APPROVED,  # Authorize
            "4": ExternalTicketStatus.IN_PROGRESS,  # Scheduled
            "5": ExternalTicketStatus.IN_PROGRESS,  # Implement
            "6": ExternalTicketStatus.IN_PROGRESS,  # Review
        }
        return mapping.get(state, ExternalTicketStatus.OPEN)


class JiraChangeDetector(ChangeDetector):
    """Enhanced Jira integration for change detection and ticket management"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ChangeSource.JIRA, config)
        self.base_url = config.get("base_url")
        self.username = config.get("username")
        self.api_token = config.get("api_token")
        self.project_key = config.get("project_key")

    async def detect_changes(
        self, since: Optional[datetime] = None
    ) -> List[ChangeEvent]:
        """Detect changes from Jira issues"""
        changes = []

        try:
            # Build JQL query
            jql_query = self._build_jql_query(since)

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/rest/api/3/search",
                    params={
                        "jql": jql_query,
                        "fields": "summary,description,status,priority,updated,assignee",
                    },
                    auth=(self.username, self.api_token),
                )

                if response.status_code == 200:
                    data = response.json()
                    for issue in data.get("issues", []):
                        change_event = self._parse_jira_issue(issue)
                        changes.append(change_event)

        except Exception as e:
            self.logger.error(f"Failed to detect Jira changes: {e}")

        return changes

    async def create_change_ticket(
        self, change_event: ChangeEvent
    ) -> Optional[ExternalTicket]:
        """Create a Jira ticket for change review"""
        try:
            # Build description with change details
            description = self._build_jira_description(change_event)

            issue_data = {
                "fields": {
                    "project": {"key": self.project_key},
                    "summary": f"Review Required: {change_event.title}",
                    "description": description,
                    "issuetype": {"name": "Task"},
                    "priority": {
                        "name": self._map_urgency_to_jira_priority(change_event.urgency)
                    },
                    "labels": [
                        "documentation-review",
                        "kinexus-ai",
                        f"source-{change_event.source.value}",
                    ],
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/rest/api/3/issue",
                    json=issue_data,
                    auth=(self.username, self.api_token),
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 201:
                    result = response.json()
                    return ExternalTicket(
                        ticket_id=result["key"],
                        system="jira",
                        url=f"{self.base_url}/browse/{result['key']}",
                        status=ExternalTicketStatus.OPEN,
                        metadata=result,
                    )

        except Exception as e:
            self.logger.error(f"Failed to create Jira ticket: {e}")

        return None

    async def update_ticket_status(
        self, ticket: ExternalTicket, status: ExternalTicketStatus, comment: str = None
    ) -> bool:
        """Update Jira ticket status and add comment"""
        try:
            # Get available transitions
            async with httpx.AsyncClient() as client:
                transitions_response = await client.get(
                    f"{self.base_url}/rest/api/3/issue/{ticket.ticket_id}/transitions",
                    auth=(self.username, self.api_token),
                )

                if transitions_response.status_code == 200:
                    transitions = transitions_response.json()["transitions"]
                    transition_id = self._find_transition_for_status(
                        transitions, status
                    )

                    if transition_id:
                        # Perform transition
                        transition_data = {"transition": {"id": transition_id}}

                        transition_response = await client.post(
                            f"{self.base_url}/rest/api/3/issue/{ticket.ticket_id}/transitions",
                            json=transition_data,
                            auth=(self.username, self.api_token),
                            headers={"Content-Type": "application/json"},
                        )

                        # Add comment if provided
                        if comment and transition_response.status_code == 204:
                            comment_data = {"body": comment}
                            await client.post(
                                f"{self.base_url}/rest/api/3/issue/{ticket.ticket_id}/comment",
                                json=comment_data,
                                auth=(self.username, self.api_token),
                                headers={"Content-Type": "application/json"},
                            )

                        return transition_response.status_code == 204

        except Exception as e:
            self.logger.error(f"Failed to update Jira ticket: {e}")

        return False

    async def validate_connection(self) -> bool:
        """Validate Jira connection"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/rest/api/3/myself",
                    auth=(self.username, self.api_token),
                )
                return response.status_code == 200
        except:
            return False

    def get_supported_change_types(self) -> List[ChangeType]:
        return [
            ChangeType.BUG_FIX,
            ChangeType.FEATURE_REQUEST,
            ChangeType.DOCUMENTATION_UPDATE,
            ChangeType.CONFIGURATION_CHANGE,
        ]

    def _build_jql_query(self, since: Optional[datetime]) -> str:
        """Build JQL query for change detection"""
        query_parts = [f"project = {self.project_key}"]

        if since:
            since_str = since.strftime("%Y-%m-%d %H:%M")
            query_parts.append(f"updated >= '{since_str}'")

        query_parts.append("labels in (documentation-impact, process-change)")

        return " AND ".join(query_parts)

    def _parse_jira_issue(self, issue: Dict[str, Any]) -> ChangeEvent:
        """Parse Jira issue into ChangeEvent"""
        fields = issue.get("fields", {})

        return ChangeEvent(
            source=ChangeSource.JIRA,
            change_type=ChangeType.BUG_FIX,  # Could be determined from issue type
            title=fields.get("summary", ""),
            description=fields.get("description", ""),
            source_id=issue.get("key"),
            source_url=f"{self.base_url}/browse/{issue.get('key')}",
            source_metadata=issue,
            urgency=self._map_jira_priority_to_urgency(
                fields.get("priority", {}).get("name", "Medium")
            ),
            review_workflow=ReviewWorkflow.JIRA_TICKET,
            external_tickets=[
                ExternalTicket(
                    ticket_id=issue.get("key"),
                    system="jira",
                    url=f"{self.base_url}/browse/{issue.get('key')}",
                    status=self._map_jira_status(
                        fields.get("status", {}).get("name", "Open")
                    ),
                    assignee=(
                        fields.get("assignee", {}).get("displayName")
                        if fields.get("assignee")
                        else None
                    ),
                    metadata=issue,
                )
            ],
        )

    def _build_jira_description(self, change_event: ChangeEvent) -> str:
        """Build comprehensive Jira ticket description"""
        description_parts = [
            f"*Change Title:* {change_event.title}",
            f"*Description:* {change_event.description}",
            f"*Source:* {change_event.source.value}",
            f"*Change Type:* {change_event.change_type.value}",
            f"*Detected:* {change_event.detected_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"*Urgency:* {change_event.urgency}",
            f"*Risk Level:* {change_event.risk_level}",
        ]

        if change_event.affected_documents:
            description_parts.append(
                f"*Affected Documents:* {', '.join(change_event.affected_documents)}"
            )

        if change_event.files_affected:
            description_parts.append(
                f"*Files Affected:* {', '.join(change_event.files_affected)}"
            )

        if change_event.ai_analysis:
            description_parts.append(
                f"*AI Analysis:* {json.dumps(change_event.ai_analysis, indent=2)}"
            )

        if change_event.recommended_actions:
            description_parts.append(f"*Recommended Actions:*")
            for action in change_event.recommended_actions:
                description_parts.append(f"- {action}")

        description_parts.append(
            "\n---\n*This ticket was automatically created by Kinexus AI*"
        )

        return "\n\n".join(description_parts)

    def _map_urgency_to_jira_priority(self, urgency: str) -> str:
        mapping = {
            "low": "Low",
            "medium": "Medium",
            "high": "High",
            "critical": "Highest",
        }
        return mapping.get(urgency, "Medium")

    def _map_jira_priority_to_urgency(self, priority: str) -> str:
        mapping = {
            "Lowest": "low",
            "Low": "low",
            "Medium": "medium",
            "High": "high",
            "Highest": "critical",
        }
        return mapping.get(priority, "medium")

    def _map_jira_status(self, status_name: str) -> ExternalTicketStatus:
        # Common Jira status mappings
        status_lower = status_name.lower()

        if status_lower in ["open", "to do", "new"]:
            return ExternalTicketStatus.OPEN
        elif status_lower in ["in progress", "in review"]:
            return ExternalTicketStatus.IN_PROGRESS
        elif status_lower in ["done", "resolved", "closed"]:
            return ExternalTicketStatus.RESOLVED
        elif status_lower in ["cancelled", "rejected"]:
            return ExternalTicketStatus.REJECTED
        else:
            return ExternalTicketStatus.OPEN

    def _find_transition_for_status(
        self, transitions: List[Dict], target_status: ExternalTicketStatus
    ) -> Optional[str]:
        """Find the transition ID for a target status"""
        # This would need to be customized based on your Jira workflow
        status_transition_mapping = {
            ExternalTicketStatus.IN_PROGRESS: ["In Progress", "Start Progress"],
            ExternalTicketStatus.RESOLVED: ["Done", "Resolve", "Close"],
            ExternalTicketStatus.REJECTED: ["Reject", "Cancel"],
        }

        target_names = status_transition_mapping.get(target_status, [])

        for transition in transitions:
            if transition["name"] in target_names:
                return transition["id"]

        return None


class HybridReviewWorkflowManager:
    """Manages hybrid review workflows combining internal and external systems"""

    def __init__(self):
        self.logger = StructuredLogger(name="HybridReviewWorkflow")
        self.change_detectors: Dict[ChangeSource, ChangeDetector] = {}
        self.workflow_configs: Dict[str, Dict[str, Any]] = {}

    def register_change_detector(self, detector: ChangeDetector):
        """Register a change detector for a specific source"""
        self.change_detectors[detector.source] = detector
        self.logger.info(f"Registered change detector for {detector.source.value}")

    async def process_change_event(self, change_event: ChangeEvent) -> Dict[str, Any]:
        """Process a change event through the appropriate workflow"""
        workflow_result = {
            "change_id": change_event.id,
            "workflow": change_event.review_workflow.value,
            "internal_review_created": False,
            "external_tickets_created": [],
            "status": "processing",
        }

        try:
            # Always create internal review record
            internal_review = await self._create_internal_review(change_event)
            workflow_result["internal_review_created"] = internal_review is not None
            workflow_result["internal_review_id"] = (
                internal_review.get("id") if internal_review else None
            )

            # Handle workflow-specific processing
            if change_event.review_workflow == ReviewWorkflow.INTERNAL_ONLY:
                workflow_result["status"] = "internal_review_only"

            elif change_event.review_workflow == ReviewWorkflow.JIRA_TICKET:
                ticket = await self._create_jira_ticket(change_event)
                if ticket:
                    change_event.external_tickets.append(ticket)
                    workflow_result["external_tickets_created"].append(ticket.ticket_id)
                workflow_result["status"] = "jira_ticket_created"

            elif change_event.review_workflow == ReviewWorkflow.SERVICENOW_TICKET:
                ticket = await self._create_servicenow_ticket(change_event)
                if ticket:
                    change_event.external_tickets.append(ticket)
                    workflow_result["external_tickets_created"].append(ticket.ticket_id)
                workflow_result["status"] = "servicenow_ticket_created"

            elif change_event.review_workflow == ReviewWorkflow.HYBRID:
                # Create both internal and external tickets
                jira_ticket = await self._create_jira_ticket(change_event)
                if jira_ticket:
                    change_event.external_tickets.append(jira_ticket)
                    workflow_result["external_tickets_created"].append(
                        jira_ticket.ticket_id
                    )
                workflow_result["status"] = "hybrid_workflow_active"

            elif change_event.review_workflow == ReviewWorkflow.EXTERNAL_ONLY:
                # Determine external system based on source or configuration
                if change_event.source == ChangeSource.SERVICENOW:
                    ticket = await self._create_servicenow_ticket(change_event)
                else:
                    ticket = await self._create_jira_ticket(change_event)

                if ticket:
                    change_event.external_tickets.append(ticket)
                    workflow_result["external_tickets_created"].append(ticket.ticket_id)
                workflow_result["status"] = "external_only"

            # Start monitoring external tickets
            if change_event.external_tickets:
                await self._start_ticket_monitoring(change_event)

            self.logger.info(
                "Change event processed",
                change_id=change_event.id,
                workflow=change_event.review_workflow.value,
                external_tickets=len(change_event.external_tickets),
            )

        except Exception as e:
            self.logger.error(f"Failed to process change event: {e}")
            workflow_result["status"] = "error"
            workflow_result["error"] = str(e)

        return workflow_result

    async def sync_external_status(self, change_event: ChangeEvent) -> Dict[str, Any]:
        """Synchronize status from external systems"""
        sync_results = {}

        for ticket in change_event.external_tickets:
            try:
                if ticket.system == "jira":
                    new_status = await self._get_jira_ticket_status(ticket)
                elif ticket.system == "servicenow":
                    new_status = await self._get_servicenow_ticket_status(ticket)
                else:
                    continue

                if new_status != ticket.status:
                    old_status = ticket.status
                    ticket.status = new_status
                    ticket.updated_at = datetime.now(timezone.utc)

                    # Update internal review status if needed
                    await self._sync_internal_review_status(change_event, ticket)

                    sync_results[ticket.ticket_id] = {
                        "old_status": old_status.value,
                        "new_status": new_status.value,
                        "updated": True,
                    }
                else:
                    sync_results[ticket.ticket_id] = {
                        "status": ticket.status.value,
                        "updated": False,
                    }

            except Exception as e:
                self.logger.error(f"Failed to sync ticket {ticket.ticket_id}: {e}")
                sync_results[ticket.ticket_id] = {"error": str(e), "updated": False}

        return sync_results

    async def _create_internal_review(
        self, change_event: ChangeEvent
    ) -> Optional[Dict[str, Any]]:
        """Create internal review record"""
        try:
            # This would integrate with your existing review creation logic
            # For now, return a mock response
            return {
                "id": str(uuid4()),
                "change_event_id": change_event.id,
                "status": "pending_review",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Failed to create internal review: {e}")
            return None

    async def _create_jira_ticket(
        self, change_event: ChangeEvent
    ) -> Optional[ExternalTicket]:
        """Create Jira ticket for change event"""
        jira_detector = self.change_detectors.get(ChangeSource.JIRA)
        if isinstance(jira_detector, JiraChangeDetector):
            return await jira_detector.create_change_ticket(change_event)
        return None

    async def _create_servicenow_ticket(
        self, change_event: ChangeEvent
    ) -> Optional[ExternalTicket]:
        """Create ServiceNow ticket for change event"""
        servicenow_detector = self.change_detectors.get(ChangeSource.SERVICENOW)
        if isinstance(servicenow_detector, ServiceNowChangeDetector):
            return await servicenow_detector.create_change_request(change_event)
        return None

    async def _start_ticket_monitoring(self, change_event: ChangeEvent):
        """Start monitoring external tickets for status changes"""
        # This would typically be handled by a background task or scheduler
        # For now, just log that monitoring has started
        self.logger.info(
            f"Started monitoring {len(change_event.external_tickets)} external tickets for change {change_event.id}"
        )

    async def _get_jira_ticket_status(
        self, ticket: ExternalTicket
    ) -> ExternalTicketStatus:
        """Get current status of Jira ticket"""
        # Implementation would query Jira API
        return ticket.status  # Placeholder

    async def _get_servicenow_ticket_status(
        self, ticket: ExternalTicket
    ) -> ExternalTicketStatus:
        """Get current status of ServiceNow ticket"""
        # Implementation would query ServiceNow API
        return ticket.status  # Placeholder

    async def _sync_internal_review_status(
        self, change_event: ChangeEvent, ticket: ExternalTicket
    ):
        """Synchronize internal review status based on external ticket status"""
        # Map external status to internal status
        if ticket.status == ExternalTicketStatus.APPROVED:
            # Update internal review to approved
            pass
        elif ticket.status == ExternalTicketStatus.REJECTED:
            # Update internal review to rejected
            pass
        elif ticket.status == ExternalTicketStatus.RESOLVED:
            # Update internal review to completed
            pass

    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get statistics about workflow usage and performance"""
        return {
            "registered_detectors": list(self.change_detectors.keys()),
            "workflow_types": [workflow.value for workflow in ReviewWorkflow],
            "supported_sources": [source.value for source in ChangeSource],
        }


# Global workflow manager instance
workflow_manager = HybridReviewWorkflowManager()
