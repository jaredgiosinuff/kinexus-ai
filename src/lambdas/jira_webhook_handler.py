"""
Jira Webhook Handler Lambda
Processes Jira ticket transitions and determines documentation impact

JIRA BEST PRACTICES FOR DOCUMENTATION:
1. Only process tickets when moved to Done/Closed (not during work)
2. Respect ticket types - Features/Stories need docs, Bugs might not
3. Look for documentation flags/labels
4. Consider ticket size/story points for impact
5. Check linked tickets and epics for context
"""

import json
import os
from datetime import datetime
from typing import Any, Dict

import boto3
import structlog

logger = structlog.get_logger()

# AWS Clients
dynamodb = boto3.resource("dynamodb")
eventbridge = boto3.client("events")
secrets = boto3.client("secretsmanager")

# Environment variables
CHANGES_TABLE = os.environ.get("CHANGES_TABLE", "kinexus-changes")
EVENT_BUS = os.environ.get("EVENT_BUS", "kinexus-events")
JIRA_SECRET_ARN = os.environ.get("JIRA_SECRET_ARN")

# Configuration for what to process
JIRA_CONFIG = {
    # Status transitions that trigger documentation
    "trigger_statuses": ["Done", "Closed", "Resolved", "Complete"],
    # Previous statuses that indicate real work (not just closing old tickets)
    "valid_from_statuses": ["In Progress", "In Review", "Testing", "QA"],
    # Issue types that typically need documentation
    "documentation_types": ["Story", "Feature", "Epic", "Task", "Improvement"],
    # Issue types to usually skip
    "skip_types": ["Sub-task", "Test", "Bug"],  # Bugs handled separately
    # Labels/tags that indicate documentation is needed
    "documentation_labels": [
        "needs-docs",
        "documentation",
        "api-change",
        "breaking-change",
        "new-feature",
    ],
    # Labels that mean skip documentation
    "skip_labels": ["no-docs", "internal-only", "tech-debt", "refactor"],
    # Minimum story points to consider (if using story points)
    "min_story_points": 2,
    # How recent the ticket must be (avoid old ticket cleanup triggering docs)
    "max_age_days": 30,
}


def should_process_ticket(
    issue_data: Dict[str, Any], changelog: Dict[str, Any]
) -> tuple[bool, str]:
    """
    Determine if this Jira ticket change should trigger documentation.
    Returns (should_process, reason)

    LOGIC:
    1. Must be moving TO a done state (not FROM done)
    2. Must be a meaningful ticket type
    3. Must have been actively worked on (not just closed as won't fix)
    4. Should respect explicit documentation labels
    5. Should be recent work (not cleaning up old tickets)
    """

    fields = issue_data.get("fields", {})
    issue_type = fields.get("issuetype", {}).get("name", "")
    _status = fields.get("status", {}).get("name", "")
    labels = fields.get("labels", [])
    created = fields.get("created", "")
    _updated = fields.get("updated", "")
    resolution = fields.get("resolution", {})

    # Check if this is a transition TO a done state
    from_status = None
    to_status = None

    for item in changelog.get("items", []):
        if item.get("field") == "status":
            from_status = item.get("fromString")
            to_status = item.get("toString")
            break

    # Rule 1: Must be transitioning TO done
    if to_status not in JIRA_CONFIG["trigger_statuses"]:
        return False, f"Status {to_status} is not a completion status"

    # Rule 2: Must be FROM an active work state (not just closing old tickets)
    if from_status and from_status not in JIRA_CONFIG["valid_from_statuses"]:
        # Exception: If it has a 'needs-docs' label, process it anyway
        if not any(label in labels for label in JIRA_CONFIG["documentation_labels"]):
            return False, f"Ticket wasn't in active development (was in {from_status})"

    # Rule 3: Check explicit skip labels
    if any(label in labels for label in JIRA_CONFIG["skip_labels"]):
        return False, "Has explicit no-docs label"

    # Rule 4: Check resolution type (Won't Fix, Duplicate, etc. should be skipped)
    resolution_name = resolution.get("name", "") if resolution else ""
    if resolution_name in [
        "Won't Fix",
        "Won't Do",
        "Duplicate",
        "Cannot Reproduce",
        "Invalid",
    ]:
        return False, f"Resolution is {resolution_name}"

    # Rule 5: Check ticket age (skip old tickets being cleaned up)
    if created:
        try:
            created_date = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_days = (datetime.utcnow() - created_date.replace(tzinfo=None)).days
            if age_days > JIRA_CONFIG["max_age_days"] * 3:  # Very old tickets
                # Unless explicitly marked for docs
                if not any(
                    label in labels for label in JIRA_CONFIG["documentation_labels"]
                ):
                    return False, f"Ticket is {age_days} days old (likely cleanup)"
        except Exception:
            pass  # If we can't parse date, continue

    # Rule 6: Check issue type
    if issue_type in JIRA_CONFIG["skip_types"]:
        # Exception: Bugs with 'breaking-change' or 'api-change' labels need docs
        if issue_type == "Bug":
            if any(
                label in ["breaking-change", "api-change", "documentation"]
                for label in labels
            ):
                return True, "Bug with documentation impact"
        return False, f"Issue type {issue_type} typically doesn't need docs"

    # Rule 7: Explicit documentation labels override other rules
    if any(label in labels for label in JIRA_CONFIG["documentation_labels"]):
        return True, "Has explicit documentation label"

    # Rule 8: Check story points if available (optional)
    story_points = fields.get("customfield_10004")  # Common story points field
    if story_points is not None:
        try:
            if float(story_points) < JIRA_CONFIG["min_story_points"]:
                return False, f"Only {story_points} story points (too small)"
        except Exception:
            pass

    # Rule 9: Default - process if it's a documentation type
    if issue_type in JIRA_CONFIG["documentation_types"]:
        return True, f"{issue_type} completed and moved to {to_status}"

    return False, "Doesn't match documentation criteria"


def extract_documentation_context(issue_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant context from Jira ticket for documentation generation.

    WHAT TO EXTRACT:
    - Acceptance criteria (often contains API/behavior specs)
    - Description (the actual change)
    - Comments mentioning documentation
    - Linked issues for context
    - Components and versions affected
    """

    fields = issue_data.get("fields", {})

    context = {
        "issue_key": issue_data.get("key"),
        "issue_type": fields.get("issuetype", {}).get("name"),
        "summary": fields.get("summary"),
        "description": fields.get("description", ""),
        "status": fields.get("status", {}).get("name"),
        "priority": fields.get("priority", {}).get("name"),
        "labels": fields.get("labels", []),
        "components": [c.get("name") for c in fields.get("components", [])],
        "fix_versions": [v.get("name") for v in fields.get("fixVersions", [])],
        "story_points": fields.get("customfield_10004"),  # Common field
        "acceptance_criteria": fields.get("customfield_10005", ""),  # Common field
        "epic_link": fields.get("customfield_10006"),  # Common field
    }

    # Extract key information from description and acceptance criteria
    # These often contain the actual technical details needed for docs
    doc_hints = []

    # Look for API endpoints mentioned
    import re

    api_pattern = r"(GET|POST|PUT|DELETE|PATCH)\s+(/[a-zA-Z0-9/_-]+)"
    for text in [context["description"], context["acceptance_criteria"]]:
        if text:
            apis = re.findall(api_pattern, text)
            if apis:
                doc_hints.append(f"API endpoints: {apis}")

    # Look for documentation mentions in comments
    comments = fields.get("comment", {}).get("comments", [])
    doc_comments = []
    for comment in comments[-5:]:  # Last 5 comments
        body = comment.get("body", "")
        if any(
            word in body.lower() for word in ["documentation", "docs", "readme", "api"]
        ):
            doc_comments.append(
                {
                    "author": comment.get("author", {}).get("displayName"),
                    "text": body[:500],  # First 500 chars
                }
            )

    context["documentation_hints"] = doc_hints
    context["relevant_comments"] = doc_comments

    # Determine documentation type needed
    if "api-change" in context["labels"] or "API" in context["summary"]:
        context["documentation_type"] = "api"
    elif "new-feature" in context["labels"]:
        context["documentation_type"] = "feature"
    elif context["issue_type"] == "Bug" and "breaking-change" in context["labels"]:
        context["documentation_type"] = "breaking-change"
    else:
        context["documentation_type"] = "general"

    return context


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for Jira webhooks"""

    try:
        # Parse the request
        body = json.loads(event.get("body", "{}"))

        # Jira webhook structure
        webhook_event = body.get("webhookEvent", "")
        issue = body.get("issue", {})
        changelog = body.get("changelog", {})

        logger.info(
            "Received Jira event", event_type=webhook_event, issue_key=issue.get("key")
        )

        # Check if we should process this ticket
        should_process, reason = should_process_ticket(issue, changelog)

        if not should_process:
            logger.info("Skipping ticket", issue_key=issue.get("key"), reason=reason)
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"message": "Ticket received but not processed", "reason": reason}
                ),
            }

        # Extract documentation context
        doc_context = extract_documentation_context(issue)

        # Create change record
        change_id = f"jira_{issue.get('key')}_{datetime.utcnow().timestamp()}"
        change_record = {
            "change_id": change_id,
            "source": "jira",
            "source_event_type": webhook_event,
            "change_data": {
                "issue_key": issue.get("key"),
                "summary": doc_context["summary"],
                "documentation_context": doc_context,
                "processing_reason": reason,
            },
            "raw_event": body,
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "processed": False,
        }

        # Store in DynamoDB
        table = dynamodb.Table(CHANGES_TABLE)
        table.put_item(Item=change_record)

        # Send to EventBridge for processing
        event_response = eventbridge.put_events(
            Entries=[
                {
                    "Source": "kinexus.jira",
                    "DetailType": "ChangeDetected",
                    "Detail": json.dumps(
                        {
                            "change_id": change_id,
                            "issue_key": issue.get("key"),
                            "summary": doc_context["summary"],
                            "documentation_type": doc_context["documentation_type"],
                            "priority": doc_context["priority"],
                        }
                    ),
                    "EventBusName": EVENT_BUS,
                }
            ]
        )

        logger.info(
            "EventBridge event sent",
            change_id=change_id,
            failed_entry_count=event_response.get("FailedEntryCount", 0),
            entries=event_response.get("Entries", []),
        )

        logger.info(
            "Jira change recorded",
            change_id=change_id,
            documentation_type=doc_context["documentation_type"],
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Jira change processed",
                    "change_id": change_id,
                    "documentation_type": doc_context["documentation_type"],
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error processing Jira webhook: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }
