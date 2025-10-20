"""
Approval Handler Lambda
Processes Jira comments on documentation review tickets
Handles approval, rejection, and revision requests
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

import boto3
import structlog

logger = structlog.get_logger()

# AWS Clients
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")
eventbridge = boto3.client("events")

# Environment variables
DOCUMENTS_TABLE = os.environ.get("DOCUMENTS_TABLE", "kinexus-documents")
DOCUMENTS_BUCKET = os.environ.get("DOCUMENTS_BUCKET")
EVENT_BUS = os.environ.get("EVENT_BUS", "kinexus-events")
JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")
CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL")

# Approval patterns
APPROVAL_PATTERNS = [
    r"(?i)^approved?$",
    r"(?i)^lgtm$",  # Looks good to me
    r"(?i)^✅",
    r"(?i)approve[ds]?\s*-",
    r"(?i)^ship\s*it$",
]

REJECTION_PATTERNS = [
    r"(?i)^rejected?$",
    r"(?i)^❌",
    r"(?i)reject[eds]?\s*-",
    r"(?i)^needs?\s*work$",
    r"(?i)^not\s*approved?$",
]

REVISION_PATTERNS = [
    r"(?i)^needs?\s*revision",
    r"(?i)^request[eds]?\s*changes?",
    r"(?i)^please\s*(update|revise|fix)",
]


def extract_approval_decision(comment_body: str) -> Optional[str]:
    """
    Extract approval decision from Jira comment
    Returns: 'approved', 'rejected', 'needs_revision', or None
    """
    comment_lower = comment_body.strip()

    # Check for approval
    for pattern in APPROVAL_PATTERNS:
        if re.search(pattern, comment_lower):
            return "approved"

    # Check for rejection
    for pattern in REJECTION_PATTERNS:
        if re.search(pattern, comment_lower):
            return "rejected"

    # Check for revision request
    for pattern in REVISION_PATTERNS:
        if re.search(pattern, comment_lower):
            return "needs_revision"

    return None


def get_document_from_review_ticket(issue_key: str) -> Optional[Dict[str, Any]]:
    """
    Extract document ID from review ticket description
    Review tickets have format: "Review documentation for ORIGINAL-123"
    """
    import requests

    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}"
    response = requests.get(
        url, auth=(JIRA_EMAIL, JIRA_API_TOKEN), headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        logger.error(f"Failed to get Jira ticket {issue_key}: {response.status_code}")
        return None

    issue = response.json()
    description = issue.get("fields", {}).get("description", "")

    # Extract document_id from description
    # Format: "Document ID: doc_xyz_v3"
    doc_id_match = re.search(r"Document ID:\s*([a-z0-9_-]+)", description, re.IGNORECASE)
    if not doc_id_match:
        logger.warning(f"No document ID found in {issue_key} description")
        return None

    document_id = doc_id_match.group(1)

    # Get document from DynamoDB
    table = dynamodb.Table(DOCUMENTS_TABLE)
    result = table.get_item(Key={"document_id": document_id})

    if "Item" not in result:
        logger.error(f"Document {document_id} not found in DynamoDB")
        return None

    return result["Item"]


def publish_to_confluence(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Publish approved documentation to Confluence
    """
    import requests

    # Download content from S3
    s3_key = document.get("s3_key", "")
    if not s3_key:
        logger.error("Document missing s3_key field")
        return {"error": "Document missing s3_key field"}

    s3_response = s3.get_object(Bucket=DOCUMENTS_BUCKET, Key=s3_key)
    markdown_content = s3_response["Body"].read().decode("utf-8")

    # Convert markdown to Confluence storage format
    confluence_content = markdown_to_confluence_storage(markdown_content)

    # Determine if this is update or create
    confluence_page_id = document.get("confluence_page_id")

    if confluence_page_id:
        # Update existing page
        url = f"{CONFLUENCE_URL}/api/v2/pages/{confluence_page_id}"

        # Get current version
        response = requests.get(
            url,
            auth=(JIRA_EMAIL, JIRA_API_TOKEN),
            headers={"Accept": "application/json"},
        )
        current_version = response.json().get("version", {}).get("number", 1)

        # Update page
        update_data = {
            "id": confluence_page_id,
            "status": "current",
            "title": document["title"],
            "body": {"representation": "storage", "value": confluence_content},
            "version": {"number": current_version + 1, "message": f"Updated via Kinexus AI - {document.get('source_change_id', '')}"},
        }

        response = requests.put(
            url,
            auth=(JIRA_EMAIL, JIRA_API_TOKEN),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=update_data,
        )

        if response.status_code in [200, 201]:
            logger.info(f"Updated Confluence page {confluence_page_id}")
            return {"page_id": confluence_page_id, "action": "updated", "url": response.json().get("_links", {}).get("webui")}
        else:
            logger.error(f"Failed to update Confluence page: {response.status_code} - {response.text}")
            return {"error": "Failed to update Confluence page"}

    else:
        # Create new page
        # Note: You'll need to determine space_id and parent_id based on your Confluence structure
        space_id = document.get("confluence_space_id", "163845")  # Software development space
        parent_id = document.get("confluence_parent_id", "163964")  # Default parent

        create_data = {
            "spaceId": space_id,
            "status": "current",
            "title": document["title"],
            "parentId": parent_id,
            "body": {"representation": "storage", "value": confluence_content},
        }

        url = f"{CONFLUENCE_URL}/api/v2/pages"
        response = requests.post(
            url,
            auth=(JIRA_EMAIL, JIRA_API_TOKEN),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=create_data,
        )

        if response.status_code in [200, 201]:
            page_data = response.json()
            logger.info(f"Created Confluence page {page_data['id']}")
            return {
                "page_id": page_data["id"],
                "action": "created",
                "url": f"{CONFLUENCE_URL}/spaces/{space_id}/pages/{page_data['id']}",
            }
        else:
            logger.error(f"Failed to create Confluence page: {response.status_code} - {response.text}")
            return {"error": "Failed to create Confluence page"}


def markdown_to_confluence_storage(markdown: str) -> str:
    """
    Convert markdown to Confluence storage format (simplified)
    For production, use a proper markdown-to-confluence converter
    """
    # This is a simplified conversion - you may want to use a library like
    # mistune or markdown2 with a Confluence renderer

    html = markdown

    # Headers
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    # Code blocks
    html = re.sub(r"```(\w+)?\n(.*?)\n```", r'<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">\1</ac:parameter><ac:plain-text-body><![CDATA[\2]]></ac:plain-text-body></ac:structured-macro>', html, flags=re.DOTALL)

    # Inline code
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

    # Bold
    html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", html)

    # Italic
    html = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", html)

    # Lists
    html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    html = re.sub(r"(<li>.*</li>)", r"<ul>\1</ul>", html, flags=re.DOTALL)

    # Links
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)

    # Paragraphs
    html = re.sub(r"\n\n", r"</p><p>", html)
    html = f"<p>{html}</p>"

    return html


def update_jira_ticket(issue_key: str, comment: str, transition_to: Optional[str] = None):
    """
    Add comment to Jira ticket and optionally transition status
    """
    import requests

    # Add comment
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/comment"
    response = requests.post(
        url,
        auth=(JIRA_EMAIL, JIRA_API_TOKEN),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json={"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}]}},
    )

    if response.status_code not in [200, 201]:
        logger.error(f"Failed to add comment to {issue_key}: {response.status_code}")

    # Transition if requested
    if transition_to:
        # Get available transitions
        transitions_url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions"
        response = requests.get(transitions_url, auth=(JIRA_EMAIL, JIRA_API_TOKEN), headers={"Accept": "application/json"})

        if response.status_code == 200:
            transitions = response.json().get("transitions", [])
            target_transition = next((t for t in transitions if t["to"]["name"].lower() == transition_to.lower()), None)

            if target_transition:
                # Execute transition
                transition_data = {"transition": {"id": target_transition["id"]}}
                response = requests.post(
                    transitions_url,
                    auth=(JIRA_EMAIL, JIRA_API_TOKEN),
                    headers={"Accept": "application/json", "Content-Type": "application/json"},
                    json=transition_data,
                )

                if response.status_code in [200, 204]:
                    logger.info(f"Transitioned {issue_key} to {transition_to}")
                else:
                    logger.error(f"Failed to transition {issue_key}: {response.status_code}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for approval processing
    Triggered by Jira webhook when comments are added to review tickets
    """
    try:
        # Parse webhook payload
        body = json.loads(event.get("body", "{}"))

        webhook_event = body.get("webhookEvent", "")
        issue = body.get("issue", {})
        comment = body.get("comment", {})

        issue_key = issue.get("key")
        comment_body = comment.get("body", "")
        comment_author = comment.get("author", {}).get("displayName", "Unknown")

        logger.info("Processing approval comment", issue_key=issue_key, webhook_event=webhook_event)

        # Only process comment_created events on review tickets
        if webhook_event != "comment_created":
            return {"statusCode": 200, "body": json.dumps({"message": "Not a comment event"})}

        # Check if this is a review ticket
        # Primary: Check for "documentation-review" label
        # Fallback: Check if summary starts with "Review:"
        labels = issue.get("fields", {}).get("labels", [])
        summary = issue.get("fields", {}).get("summary", "")

        is_review_ticket = (
            "documentation-review" in labels or
            summary.startswith("Review:")
        )

        if not is_review_ticket:
            logger.info(f"Not a review ticket: labels={labels}, summary={summary}")
            return {"statusCode": 200, "body": json.dumps({"message": "Not a review ticket"})}

        # Extract approval decision
        decision = extract_approval_decision(comment_body)

        if not decision:
            logger.info("No approval decision found in comment")
            return {"statusCode": 200, "body": json.dumps({"message": "No approval decision found"})}

        logger.info(f"Approval decision: {decision}", author=comment_author)

        # Get associated document
        document = get_document_from_review_ticket(issue_key)

        if not document:
            return {"statusCode": 400, "body": json.dumps({"error": "Associated document not found"})}

        # Process based on decision
        if decision == "approved":
            # Publish to Confluence
            publish_result = publish_to_confluence(document)

            if "error" not in publish_result:
                # Update document status in DynamoDB
                table = dynamodb.Table(DOCUMENTS_TABLE)
                table.update_item(
                    Key={"document_id": document["document_id"]},
                    UpdateExpression="SET #status = :status, approved_by = :approver, approved_at = :timestamp, confluence_page_id = :page_id, confluence_url = :url",
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={
                        ":status": "published",
                        ":approver": comment_author,
                        ":timestamp": datetime.utcnow().isoformat(),
                        ":page_id": publish_result.get("page_id"),
                        ":url": publish_result.get("url"),
                    },
                )

                # Update Jira ticket with success
                success_comment = f"✅ Documentation approved and published!\n\n📚 Confluence: {publish_result.get('url')}\n\nApproved by: {comment_author}"
                update_jira_ticket(issue_key, success_comment, transition_to="Done")

                # Comment on original source ticket
                if document.get("source_change_id"):
                    source_match = re.search(r"jira_([A-Z]+-\d+)_", document["source_change_id"])
                    if source_match:
                        source_ticket = source_match.group(1)
                        source_comment = f"📚 Documentation published: {publish_result.get('url')}"
                        update_jira_ticket(source_ticket, source_comment)

                # Send EventBridge event
                eventbridge.put_events(
                    Entries=[
                        {
                            "Source": "kinexus.approval",
                            "DetailType": "DocumentationPublished",
                            "Detail": json.dumps(
                                {
                                    "document_id": document["document_id"],
                                    "confluence_url": publish_result.get("url"),
                                    "approved_by": comment_author,
                                    "review_ticket": issue_key,
                                }
                            ),
                            "EventBusName": EVENT_BUS,
                        }
                    ]
                )

                return {"statusCode": 200, "body": json.dumps({"message": "Documentation approved and published", "confluence_url": publish_result.get("url")})}

            else:
                error_comment = f"❌ Publication failed: {publish_result.get('error')}"
                update_jira_ticket(issue_key, error_comment)
                return {"statusCode": 500, "body": json.dumps({"error": "Publication failed"})}

        elif decision == "rejected":
            # Update document status
            table = dynamodb.Table(DOCUMENTS_TABLE)
            table.update_item(
                Key={"document_id": document["document_id"]},
                UpdateExpression="SET #status = :status, rejected_by = :rejector, rejected_at = :timestamp",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":status": "rejected", ":rejector": comment_author, ":timestamp": datetime.utcnow().isoformat()},
            )

            # Update Jira ticket
            rejection_comment = f"❌ Documentation rejected by {comment_author}\n\nPlease address feedback and regenerate."
            update_jira_ticket(issue_key, rejection_comment, transition_to="Done")

            return {"statusCode": 200, "body": json.dumps({"message": "Documentation rejected"})}

        elif decision == "needs_revision":
            # Update document status
            table = dynamodb.Table(DOCUMENTS_TABLE)
            table.update_item(
                Key={"document_id": document["document_id"]},
                UpdateExpression="SET #status = :status, revision_requested_by = :requester, revision_requested_at = :timestamp",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":status": "needs_revision", ":requester": comment_author, ":timestamp": datetime.utcnow().isoformat()},
            )

            # Update Jira ticket
            revision_comment = f"🔄 Revisions requested by {comment_author}\n\nPlease address feedback."
            update_jira_ticket(issue_key, revision_comment)

            return {"statusCode": 200, "body": json.dumps({"message": "Revisions requested"})}

    except Exception as e:
        logger.error(f"Error processing approval: {str(e)}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error"})}
