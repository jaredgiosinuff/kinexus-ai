"""
Test GitHub webhook locally
"""
import json
import requests
from datetime import datetime


def test_github_push_event():
    """Simulate a GitHub push event"""

    # Sample GitHub webhook payload
    github_payload = {
        "ref": "refs/heads/main",
        "repository": {
            "full_name": "test-org/test-repo",
            "html_url": "https://github.com/test-org/test-repo"
        },
        "pusher": {
            "name": "test-user"
        },
        "commits": [
            {
                "id": "abc123",
                "message": "Update API documentation and add new endpoints",
                "timestamp": datetime.utcnow().isoformat(),
                "author": {
                    "name": "Test User"
                },
                "added": ["src/api/new_endpoint.py"],
                "modified": ["README.md", "docs/API.md"],
                "removed": []
            }
        ]
    }

    # Test locally with the Lambda handler
    from src.lambdas.github_webhook_handler import lambda_handler

    event = {
        "body": json.dumps(github_payload),
        "headers": {
            "x-github-event": "push"
        }
    }

    response = lambda_handler(event, None)
    print(f"Response: {json.dumps(response, indent=2)}")

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'change_id' in body


def test_document_orchestrator():
    """Test the document orchestrator locally"""

    from src.lambdas.document_orchestrator import lambda_handler

    # Simulate EventBridge event
    event = {
        "detail-type": "ChangeDetected",
        "detail": {
            "change_id": "test_change_123",
            "repository": "test-org/test-repo",
            "files_changed": ["README.md", "src/api.py"],
            "event_type": "push"
        }
    }

    response = lambda_handler(event, None)
    print(f"Orchestrator Response: {json.dumps(response, indent=2)}")

    assert response['statusCode'] == 200


if __name__ == "__main__":
    print("🧪 Testing GitHub Webhook Handler...")
    test_github_push_event()
    print("✅ Webhook test passed!\n")

    print("🧪 Testing Document Orchestrator...")
    # Note: This will fail without AWS credentials and resources
    # test_document_orchestrator()
    print("⚠️ Orchestrator test requires AWS deployment\n")