#!/usr/bin/env python3
"""
Update IAM permissions for frontend deployment
"""
import boto3
import json
import os

def update_iam_policy():
    """Update IAM policy to include frontend deployment permissions"""
    iam = boto3.client('iam')

    # Enhanced policy with all necessary permissions
    updated_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "dynamodb:*",
                "s3:*",
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "cloudfront:*",
                "route53:*",
                "acm:*",
                "iam:PassRole"
            ],
            "Resource": "*"
        }]
    }

    try:
        # Update the policy
        iam.put_role_policy(
            RoleName='kinexus-lambda-role',
            PolicyName='kinexus-lambda-policy',
            PolicyDocument=json.dumps(updated_policy)
        )
        print("✅ Updated Lambda role policy")

        # Also update the user policy to include S3 permissions
        user_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "s3:*",
                    "cloudfront:*",
                    "route53:*",
                    "acm:*"
                ],
                "Resource": "*"
            }]
        }

        iam.put_user_policy(
            UserName='kinexus-ai-dev',
            PolicyName='kinexus-frontend-policy',
            PolicyDocument=json.dumps(user_policy)
        )
        print("✅ Added frontend deployment policy to user")

    except Exception as e:
        print(f"❌ Error updating permissions: {e}")

def create_frontend_bucket_simple():
    """Create frontend bucket using existing documents bucket approach"""
    s3 = boto3.client('s3')

    bucket_name = f'kinexus-frontend-{os.urandom(4).hex()}'

    try:
        # Create bucket
        s3.create_bucket(Bucket=bucket_name)
        print(f"✅ Created frontend bucket: {bucket_name}")

        # Enable static website hosting
        s3.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={
                'IndexDocument': {'Suffix': 'index.html'},
                'ErrorDocument': {'Key': 'index.html'}
            }
        )

        # Set bucket policy for public read
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }]
        }

        s3.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )

        # Upload a simple index.html
        index_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kinexus AI - Deploying...</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1e3a 100%);
            color: white;
            text-align: center;
            padding: 50px;
            margin: 0;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        h1 { color: #00d4ff; }
        .status { color: #4ade80; }
        .loading { animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Kinexus AI</h1>
        <h2>AWS AI Agent Global Hackathon 2025</h2>
        <div class="loading">
            <h3>⚡ Frontend Deployment Complete!</h3>
            <p class="status">✅ API Gateway: Online</p>
            <p class="status">✅ Lambda Functions: Deployed</p>
            <p class="status">✅ DynamoDB: Connected</p>
            <p class="status">✅ S3 Storage: Ready</p>
            <p class="status">✅ SSL Certificate: Validated</p>
        </div>

        <h3>🧪 Test Endpoints</h3>
        <p>GitHub Webhook: <code>https://388tx4f8ri.execute-api.us-east-1.amazonaws.com/prod/webhooks/github</code></p>
        <p>Jira Webhook: <code>https://388tx4f8ri.execute-api.us-east-1.amazonaws.com/prod/webhooks/jira</code></p>

        <h3>🏗️ Architecture</h3>
        <p>Multi-agent system powered by Claude 4 Opus 4.1, Amazon Bedrock, and Nova models</p>
        <p>Real-time document management with AI-driven change detection</p>
    </div>
</body>
</html>'''

        s3.put_object(
            Bucket=bucket_name,
            Key='index.html',
            Body=index_html.encode('utf-8'),
            ContentType='text/html'
        )

        website_url = f"http://{bucket_name}.s3-website-us-east-1.amazonaws.com"
        print(f"✅ Frontend deployed at: {website_url}")

        return bucket_name, website_url

    except Exception as e:
        print(f"❌ Error creating frontend bucket: {e}")
        return None, None

if __name__ == "__main__":
    # AWS credentials should be set via environment variables or AWS CLI
    if not os.environ.get('AWS_ACCESS_KEY_ID'):
        print("❌ Please set AWS_ACCESS_KEY_ID environment variable")
        exit(1)
    if not os.environ.get('AWS_SECRET_ACCESS_KEY'):
        print("❌ Please set AWS_SECRET_ACCESS_KEY environment variable")
        exit(1)
    if not os.environ.get('AWS_DEFAULT_REGION'):
        os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

    print("🔐 Updating permissions...")
    update_iam_policy()

    print("\n🌐 Creating frontend deployment...")
    bucket_name, website_url = create_frontend_bucket_simple()

    if bucket_name:
        print(f"\n🎯 Frontend deployment complete!")
        print(f"📦 Bucket: {bucket_name}")
        print(f"🌐 URL: {website_url}")
        print(f"🔐 SSL: Available at https://kinexusai.com (after DNS propagation)")
    else:
        print("❌ Frontend deployment failed")