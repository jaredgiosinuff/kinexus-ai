#!/bin/bash
# Configure Jira Webhook for Kinexus AI
# This script creates a webhook in Jira that sends events to the Lambda function

set -e

# Configuration
JIRA_URL="${JIRA_URL:-https://your-domain.atlassian.net}"
JIRA_EMAIL="${JIRA_EMAIL:-your-email@example.com}"
JIRA_API_TOKEN="${JIRA_API_TOKEN:-your-api-token}"
KINEXUS_WEBHOOK_URL="https://z1rsr9mld0.execute-api.us-east-1.amazonaws.com/prod/webhooks/jira"

echo "🔗 Configuring Jira Webhook for Kinexus AI"
echo "================================================"
echo "Jira URL: $JIRA_URL"
echo "Webhook URL: $KINEXUS_WEBHOOK_URL"
echo ""

# Create webhook
echo "Creating webhook..."
RESPONSE=$(curl -s -X POST \
  "$JIRA_URL/rest/webhooks/1.0/webhook" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Kinexus AI Documentation Tracker",
    "url": "'"$KINEXUS_WEBHOOK_URL"'",
    "events": [
      "jira:issue_created",
      "jira:issue_updated",
      "jira:issue_deleted"
    ],
    "filters": {
      "issue-related-events-section": ""
    },
    "excludeBody": false
  }')

echo "Response: $RESPONSE"
echo ""

# Check if webhook was created
if echo "$RESPONSE" | grep -q "self"; then
  echo "✅ Webhook created successfully!"
  WEBHOOK_ID=$(echo "$RESPONSE" | jq -r '.self' | sed 's/.*\///')
  echo "Webhook ID: $WEBHOOK_ID"
else
  echo "❌ Failed to create webhook"
  echo "Response: $RESPONSE"
  exit 1
fi

echo ""
echo "📝 Next steps:"
echo "1. Test the webhook by updating a Jira issue"
echo "2. Check CloudWatch logs for the Lambda function"
echo "3. Verify documentation is generated in S3"
