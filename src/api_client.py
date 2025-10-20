"""
Kinexus AI API Client
Simple client for interacting with the deployed API
"""

import time
from typing import Any, Dict, Optional

import boto3
import requests


class KinexusClient:
    """Client for Kinexus AI API and AWS resources"""

    def __init__(self, api_url: Optional[str] = None, region: str = "us-east-1"):
        self.api_url = api_url
        self.region = region

        # AWS clients
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.s3 = boto3.client("s3", region_name=region)

    def trigger_github_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a webhook event to the API"""
        if not self.api_url:
            raise ValueError("API URL not configured")

        response = requests.post(
            f"{self.api_url}/webhooks/github",
            json=payload,
            headers={"x-github-event": "push", "Content-Type": "application/json"},
            timeout=30,
        )
        return response.json()

    def get_change_status(self, change_id: str) -> Dict[str, Any]:
        """Get the status of a change from DynamoDB"""
        table = self.dynamodb.Table("kinexus-changes")
        response = table.get_item(Key={"change_id": change_id})
        return response.get("Item", {})

    def get_document(self, document_id: str) -> Dict[str, Any]:
        """Get document metadata from DynamoDB"""
        table = self.dynamodb.Table("kinexus-documents")
        response = table.get_item(Key={"document_id": document_id})
        return response.get("Item", {})

    def get_document_content(
        self, s3_key: str, bucket: str = "kinexus-documents"
    ) -> str:
        """Get document content from S3"""
        response = self.s3.get_object(Bucket=bucket, Key=s3_key)
        return response["Body"].read().decode("utf-8")

    def list_recent_changes(self, limit: int = 10) -> list:
        """List recent changes from DynamoDB"""
        table = self.dynamodb.Table("kinexus-changes")
        response = table.scan(Limit=limit)
        items = response.get("Items", [])
        # Sort by created_at
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    def simulate_code_change(self) -> Dict[str, Any]:
        """Simulate a code change for demo purposes"""

        payload = {
            "ref": "refs/heads/main",
            "repository": {
                "full_name": "kinexusai/demo-repo",
                "html_url": "https://github.com/kinexusai/demo-repo",
            },
            "pusher": {"name": "demo-user"},
            "commits": [
                {
                    "id": f"demo_{int(time.time())}",
                    "message": "Add new payment processing API endpoint",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "author": {"name": "Demo User"},
                    "added": ["src/api/payment.py"],
                    "modified": ["README.md", "docs/api/endpoints.md"],
                    "removed": [],
                }
            ],
        }

        return self.trigger_github_webhook(payload)

    def wait_for_processing(self, change_id: str, timeout: int = 60) -> Dict[str, Any]:
        """Wait for a change to be processed"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            change = self.get_change_status(change_id)

            if change.get("status") == "completed":
                return change
            elif change.get("status") == "error":
                raise Exception(f"Change processing failed: {change}")

            time.sleep(2)

        raise TimeoutError(f"Change {change_id} not processed within {timeout} seconds")


def demo_flow():
    """Run a complete demo flow"""

    # Get API URL from CloudFormation stack
    cf = boto3.client("cloudformation", region_name="us-east-1")
    stack = cf.describe_stacks(StackName="KinexusAIMVPStack")
    outputs = {o["OutputKey"]: o["OutputValue"] for o in stack["Stacks"][0]["Outputs"]}

    api_url = outputs.get("APIEndpoint")

    if not api_url:
        print("❌ API not deployed. Run ./scripts/deploy.sh first")
        return

    client = KinexusClient(api_url=api_url)

    print("🚀 Kinexus AI Demo")
    print(f"📡 API URL: {api_url}")
    print("-" * 50)

    # Simulate a code change
    print("\n1️⃣ Simulating GitHub push event...")
    response = client.simulate_code_change()
    change_id = response.get("change_id")
    print(f"   ✅ Change ID: {change_id}")

    # Wait for processing
    print("\n2️⃣ Waiting for AI to process change...")
    try:
        _change = client.wait_for_processing(change_id)
        print("   ✅ Processing completed!")
    except TimeoutError:
        print("   ⏱️ Processing taking longer than expected...")
        return

    # Get generated documentation
    print("\n3️⃣ Retrieving generated documentation...")
    docs = client.dynamodb.Table("kinexus-documents").scan(
        FilterExpression="change_id = :change_id",
        ExpressionAttributeValues={":change_id": change_id},
    )

    if docs["Items"]:
        doc = docs["Items"][0]
        print(f"   📄 Document ID: {doc['document_id']}")
        print(f"   📝 Title: {doc.get('title', 'N/A')}")
        print("\n   Preview:")
        print("   " + "-" * 40)
        print(f"   {doc.get('content_preview', 'No preview available')[:200]}...")

        # Get full content from S3
        if "s3_key" in doc:
            _content = client.get_document_content(doc["s3_key"])
            print(f"\n   Full document saved to S3: {doc['s3_key']}")
    else:
        print("   ⚠️ No documentation generated yet")

    print("\n✨ Demo completed successfully!")


if __name__ == "__main__":
    demo_flow()
