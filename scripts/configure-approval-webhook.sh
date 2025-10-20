#!/bin/bash
# Configure Jira Webhook for Approval Comments
# This webhook monitors review tickets for APPROVED/REJECTED comments

set -e

# Configuration
JIRA_URL="${JIRA_URL:-https://jared-cluff.atlassian.net}"
JIRA_EMAIL="${JIRA_EMAIL:-jbcluff@gmail.com}"
JIRA_API_TOKEN="${JIRA_API_TOKEN}"
KINEXUS_WEBHOOK_URL="https://z1rsr9mld0.execute-api.us-east-1.amazonaws.com/prod/webhooks/approval"

if [ -z "$JIRA_API_TOKEN" ]; then
    echo "Error: JIRA_API_TOKEN environment variable not set"
    echo "Usage: JIRA_API_TOKEN=your-token ./configure-approval-webhook.sh"
    exit 1
fi

echo "🔗 Configuring Jira Approval Webhook for Kinexus AI"
echo "=================================================="
echo "Jira URL: $JIRA_URL"
echo "Webhook URL: $KINEXUS_WEBHOOK_URL"
echo ""

# Create webhook for comment events
echo "Creating approval webhook..."
RESPONSE=$(curl -s -X POST \
  "$JIRA_URL/rest/webhooks/1.0/webhook" \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Kinexus AI - Approval Handler",
    "url": "'"$KINEXUS_WEBHOOK_URL"'",
    "events": [
      "comment_created"
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
  echo "✅ Approval webhook created successfully!"
  WEBHOOK_ID=$(echo "$RESPONSE" | jq -r '.self' | sed 's/.*\///')
  echo "Webhook ID: $WEBHOOK_ID"
else
  echo "❌ Failed to create webhook"
  echo "Response: $RESPONSE"
  exit 1
fi

echo ""
echo "📝 Webhook Configuration Complete!"
echo ""
echo "Now you have TWO webhooks configured:"
echo "1. Main Webhook (ID: 1) - Monitors ticket status changes"
echo "2. Approval Webhook (ID: $WEBHOOK_ID) - Monitors review ticket comments"
echo ""
echo "🧪 Test the workflow:"
echo "1. Close a Jira ticket with 'needs-docs' label"
echo "2. Wait for review ticket to be created (~2 min)"
echo "3. Comment 'APPROVED' on review ticket"
echo "4. Documentation will publish to Confluence!"
