"""
Review Ticket Creator
Creates Jira review tickets with diff previews
Automatically triggered after documentation generation
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict

import boto3
import structlog
from diff_generator import (
    compare_image_references,
    generate_html_diff,
    generate_jira_description_diff,
)

logger = structlog.get_logger()

# AWS Clients
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# Environment variables
DOCUMENTS_BUCKET = os.environ.get("DOCUMENTS_BUCKET")
JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")
PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "TOAST")  # Default to TOAST project


def get_previous_version_content(document: Dict[str, Any]) -> str:
    """
    Get content from previous version of document
    """
    previous_version_id = document.get("previous_version")

    if not previous_version_id:
        # No previous version - this is a new document
        return ""

    try:
        # Get from S3
        s3_key = f"documents/{previous_version_id}.md"
        response = s3.get_object(Bucket=DOCUMENTS_BUCKET, Key=s3_key)
        return response["Body"].read().decode("utf-8")
    except Exception as e:
        logger.warning(f"Could not load previous version {previous_version_id}: {e}")
        return ""


def get_current_version_content(document: Dict[str, Any]) -> str:
    """
    Get content from current version of document
    """
    # Get s3_key directly from document
    s3_key = document.get("s3_key", "")

    if not s3_key:
        logger.error("Document missing s3_key field")
        return ""

    try:
        response = s3.get_object(Bucket=DOCUMENTS_BUCKET, Key=s3_key)
        return response["Body"].read().decode("utf-8")
    except Exception as e:
        logger.error(f"Could not load current version: {e}")
        return ""


def upload_diff_to_s3(html_diff: str, document_id: str) -> str:
    """
    Upload HTML diff to S3 and return presigned URL
    """
    s3_key = f"diffs/{document_id}_diff_{int(datetime.utcnow().timestamp())}.html"

    s3.put_object(
        Bucket=DOCUMENTS_BUCKET,
        Key=s3_key,
        Body=html_diff.encode("utf-8"),
        ContentType="text/html",
        CacheControl="max-age=86400",
    )

    # Generate presigned URL (7 days expiry)
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": DOCUMENTS_BUCKET, "Key": s3_key},
        ExpiresIn=604800,
    )

    return url


def create_jira_review_ticket(
    document: Dict[str, Any], diff_summary: str, diff_url: str, image_changes: dict
) -> Dict[str, Any]:
    """
    Create Jira ticket for documentation review
    """
    import requests

    # Build description
    description_parts = []

    # Header
    description_parts.append(
        {
            "type": "heading",
            "attrs": {"level": 1},
            "content": [{"type": "text", "text": "📚 Documentation Review Required"}],
        }
    )

    # Document info
    description_parts.append(
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Document: ", "marks": [{"type": "strong"}]},
                {"type": "text", "text": document.get("title", "Untitled")},
            ],
        }
    )

    description_parts.append(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "Document ID: ",
                    "marks": [{"type": "strong"}],
                },
                {
                    "type": "text",
                    "text": document["document_id"],
                    "marks": [{"type": "code"}],
                },
            ],
        }
    )

    description_parts.append(
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "Version: ", "marks": [{"type": "strong"}]},
                {"type": "text", "text": str(document.get("version", 1))},
            ],
        }
    )

    # Source change
    if document.get("source_change_id"):
        source_match = re.search(r"jira_([A-Z]+-\d+)_", document["source_change_id"])
        if source_match:
            source_ticket = source_match.group(1)
            description_parts.append(
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Source Ticket: ",
                            "marks": [{"type": "strong"}],
                        },
                        {
                            "type": "text",
                            "text": source_ticket,
                            "marks": [
                                {
                                    "type": "link",
                                    "attrs": {
                                        "href": f"{JIRA_BASE_URL}/browse/{source_ticket}"
                                    },
                                }
                            ],
                        },
                    ],
                }
            )

    # Diff preview link
    description_parts.append({"type": "rule"})
    description_parts.append(
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "📊 Review Changes"}],
        }
    )

    description_parts.append(
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "🔗 ", "marks": [{"type": "strong"}]},
                {
                    "type": "text",
                    "text": "View Full Diff (HTML)",
                    "marks": [
                        {"type": "link", "attrs": {"href": diff_url}},
                        {"type": "strong"},
                    ],
                },
            ],
        }
    )

    # Add diff summary
    description_parts.append(
        {
            "type": "codeBlock",
            "attrs": {"language": "text"},
            "content": [{"type": "text", "text": diff_summary}],
        }
    )

    # Image changes section
    if image_changes["added"] or image_changes["removed"]:
        description_parts.append({"type": "rule"})
        description_parts.append(
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "🖼️ Image Changes"}],
            }
        )

        if image_changes["added"]:
            description_parts.append(
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": f"✅ {len(image_changes['added'])} new images added",
                            "marks": [{"type": "strong"}],
                        }
                    ],
                }
            )

        if image_changes["removed"]:
            description_parts.append(
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": f"❌ {len(image_changes['removed'])} images removed",
                            "marks": [{"type": "strong"}],
                        }
                    ],
                }
            )

        description_parts.append(
            {
                "type": "panel",
                "attrs": {"panelType": "warning"},
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "⚠️ Image changes require separate review. Please verify all images after approving text changes.",
                                "marks": [{"type": "em"}],
                            }
                        ],
                    }
                ],
            }
        )

    # Approval instructions
    description_parts.append({"type": "rule"})
    description_parts.append(
        {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "✅ How to Approve"}],
        }
    )

    description_parts.append(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "Comment on this ticket with one of the following:",
                }
            ],
        }
    )

    description_parts.append(
        {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "APPROVED",
                                    "marks": [{"type": "code"}],
                                },
                                {"type": "text", "text": " - Approve and publish"},
                            ],
                        }
                    ],
                },
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "REJECTED",
                                    "marks": [{"type": "code"}],
                                },
                                {
                                    "type": "text",
                                    "text": " - Reject and request regeneration",
                                },
                            ],
                        }
                    ],
                },
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "NEEDS REVISION",
                                    "marks": [{"type": "code"}],
                                },
                                {"type": "text", "text": " - Request specific changes"},
                            ],
                        }
                    ],
                },
            ],
        }
    )

    # Created by
    description_parts.append({"type": "rule"})
    description_parts.append(
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "Generated by Kinexus AI at ",
                    "marks": [{"type": "em"}],
                },
                {
                    "type": "text",
                    "text": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                    "marks": [{"type": "em"}],
                },
            ],
        }
    )

    # Build full description
    description_doc = {"version": 1, "type": "doc", "content": description_parts}

    # Create Jira issue
    issue_data = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": f"Review: {document.get('title', 'Untitled Document')}",
            "description": description_doc,
            "issuetype": {"name": "Task"},
            # Note: labels and priority removed as they may not be configured on all Jira screens
        }
    }

    # Add assignee if specified
    if document.get("reviewer"):
        issue_data["fields"]["assignee"] = {"accountId": document["reviewer"]}

    url = f"{JIRA_BASE_URL}/rest/api/3/issue"
    response = requests.post(
        url,
        auth=(JIRA_EMAIL, JIRA_API_TOKEN),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json=issue_data,
    )

    if response.status_code in [200, 201]:
        issue = response.json()
        issue_key = issue["key"]
        logger.info(f"Created review ticket {issue_key}")

        # Add labels via update API (labels field may not be on create screen)
        labels_to_add = ["documentation-review", "auto-generated", "kinexus-ai"]
        try:
            update_url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}"
            update_response = requests.put(
                update_url,
                auth=(JIRA_EMAIL, JIRA_API_TOKEN),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={
                    "update": {"labels": [{"add": label} for label in labels_to_add]}
                },
            )

            if update_response.status_code in [200, 204]:
                logger.info(f"Added labels to {issue_key}: {labels_to_add}")
            else:
                logger.warning(
                    f"Failed to add labels to {issue_key}: {update_response.status_code}"
                )
        except Exception as e:
            logger.warning(f"Could not add labels to {issue_key}: {e}")

        return {
            "success": True,
            "issue_key": issue_key,
            "issue_id": issue["id"],
            "issue_url": f"{JIRA_BASE_URL}/browse/{issue_key}",
        }
    else:
        logger.error(
            f"Failed to create Jira ticket: {response.status_code} - {response.text}"
        )
        return {"success": False, "error": response.text}


def create_review_ticket_for_document(document_id: str) -> Dict[str, Any]:
    """
    Main function to create review ticket for a generated document
    Called by document orchestrator after document generation
    """
    # Get document from DynamoDB
    documents_table = os.environ.get("DOCUMENTS_TABLE", "kinexus-documents")
    table = dynamodb.Table(documents_table)
    result = table.get_item(Key={"document_id": document_id})

    if "Item" not in result:
        logger.error(f"Document {document_id} not found")
        return {"success": False, "error": "Document not found"}

    document = result["Item"]

    # Get original and modified content
    original_content = get_previous_version_content(document)
    modified_content = get_current_version_content(document)

    # Generate diffs
    html_diff = generate_html_diff(
        original_content,
        modified_content,
        title=document.get("title", "Documentation Changes"),
    )

    text_diff_summary = generate_jira_description_diff(
        original_content, modified_content
    )

    # Compare image references
    image_changes = compare_image_references(original_content, modified_content)

    # Upload HTML diff to S3
    diff_url = upload_diff_to_s3(html_diff, document_id)

    # Create Jira review ticket
    ticket_result = create_jira_review_ticket(
        document, text_diff_summary, diff_url, image_changes
    )

    if ticket_result["success"]:
        # Update document with review ticket info
        table.update_item(
            Key={"document_id": document_id},
            UpdateExpression="SET review_ticket_key = :key, review_ticket_url = :url, diff_url = :diff_url, image_changes = :img_changes",
            ExpressionAttributeValues={
                ":key": ticket_result["issue_key"],
                ":url": ticket_result["issue_url"],
                ":diff_url": diff_url,
                ":img_changes": image_changes,
            },
        )

        logger.info(f"Review ticket created: {ticket_result['issue_key']}")

        return {
            "success": True,
            "document_id": document_id,
            "review_ticket": ticket_result["issue_key"],
            "diff_url": diff_url,
            "image_changes": image_changes,
        }
    else:
        return {"success": False, "error": ticket_result.get("error")}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for review ticket creation
    Can be invoked directly or via EventBridge after document generation
    """
    try:
        # Check if this is an EventBridge event
        if (
            event.get("source") == "kinexus.orchestrator"
            and event.get("detail-type") == "DocumentGenerated"
        ):
            document_id = event["detail"]["document_id"]
        else:
            # Direct invocation
            document_id = event.get("document_id")

        if not document_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "document_id required"}),
            }

        result = create_review_ticket_for_document(document_id)

        if result["success"]:
            return {"statusCode": 200, "body": json.dumps(result)}
        else:
            return {"statusCode": 500, "body": json.dumps(result)}

    except Exception as e:
        logger.error(f"Error creating review ticket: {str(e)}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
