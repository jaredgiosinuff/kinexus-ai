"""
GitHub Webhook Handler Lambda
Receives GitHub push events and triggers documentation analysis
"""

import hashlib
import hmac
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
GITHUB_SECRET_ARN = os.environ.get("GITHUB_SECRET_ARN")


def verify_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature:
        return False

    sha_name, signature = signature.split("=")
    if sha_name != "sha256":
        return False

    mac = hmac.new(secret.encode(), msg=payload.encode(), digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature)


def extract_change_data(github_event: Dict[str, Any]) -> Dict[str, Any]:
    """Extract relevant data from GitHub webhook payload"""

    # Handle push events
    if "commits" in github_event:
        commits = github_event["commits"]
        repository = github_event["repository"]

        # Aggregate all changed files
        files_changed = set()
        for commit in commits:
            files_changed.update(commit.get("added", []))
            files_changed.update(commit.get("modified", []))
            files_changed.update(commit.get("removed", []))

        return {
            "repository_name": repository["full_name"],
            "repository_url": repository["html_url"],
            "branch": github_event.get("ref", "").replace("refs/heads/", ""),
            "commits": [
                {
                    "id": c["id"],
                    "message": c["message"],
                    "author": c["author"]["name"],
                    "timestamp": c["timestamp"],
                }
                for c in commits
            ],
            "files_changed": list(files_changed),
            "pusher": github_event.get("pusher", {}).get("name"),
            "event_type": "push",
        }

    # Handle pull request events
    elif "pull_request" in github_event:
        pr = github_event["pull_request"]
        return {
            "repository_name": github_event["repository"]["full_name"],
            "repository_url": github_event["repository"]["html_url"],
            "pull_request_number": pr["number"],
            "pull_request_title": pr["title"],
            "pull_request_body": pr.get("body", ""),
            "action": github_event.get("action"),
            "branch": pr["head"]["ref"],
            "base_branch": pr["base"]["ref"],
            "event_type": "pull_request",
        }

    return {}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for GitHub webhooks"""

    try:
        # Parse the request
        body = event.get("body", "{}")
        headers = event.get("headers", {})

        # Verify GitHub signature if secret is configured
        if GITHUB_SECRET_ARN:
            secret_response = secrets.get_secret_value(SecretId=GITHUB_SECRET_ARN)
            github_secret = json.loads(secret_response["SecretString"])[
                "webhook_secret"
            ]

            signature = headers.get("x-hub-signature-256")
            if not verify_signature(body, signature, github_secret):
                logger.warning("Invalid GitHub signature")
                return {
                    "statusCode": 401,
                    "body": json.dumps({"error": "Invalid signature"}),
                }

        # Parse GitHub event
        github_event = json.loads(body)
        github_event_type = headers.get("x-github-event", "unknown")

        logger.info(f"Received GitHub event", event_type=github_event_type)

        # Extract change data
        change_data = extract_change_data(github_event)
        if not change_data:
            logger.info("No relevant change data found")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Event received but no action taken"}),
            }

        # Create change record
        change_id = (
            f"github_{change_data['repository_name']}_{datetime.utcnow().timestamp()}"
        )
        change_record = {
            "change_id": change_id,
            "source": "github",
            "source_event_type": github_event_type,
            "change_data": change_data,
            "raw_event": github_event,
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "processed": False,
        }

        # Store in DynamoDB
        table = dynamodb.Table(CHANGES_TABLE)
        table.put_item(Item=change_record)

        # Send to EventBridge for processing
        eventbridge.put_events(
            Entries=[
                {
                    "Source": "kinexus.github",
                    "DetailType": "ChangeDetected",
                    "Detail": json.dumps(
                        {
                            "change_id": change_id,
                            "repository": change_data["repository_name"],
                            "files_changed": change_data.get("files_changed", []),
                            "event_type": github_event_type,
                        }
                    ),
                    "EventBusName": EVENT_BUS,
                }
            ]
        )

        logger.info(f"Change recorded and event published", change_id=change_id)

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "Change event processed", "change_id": change_id}
            ),
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }
