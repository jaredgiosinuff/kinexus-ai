#!/bin/bash
set -e

echo "🚀 Deploying Kinexus AI MVP to AWS..."

# Check AWS credentials
echo "📋 Checking AWS credentials..."
aws sts get-caller-identity > /dev/null || { echo "❌ AWS credentials not configured"; exit 1; }

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt -q

# Build Lambda layer
echo "🏗️ Building Lambda layer..."
rm -rf lambda_layer lambda_layer.zip
pip install -r requirements.txt -t lambda_layer/python -q
cd lambda_layer
zip -r ../lambda_layer.zip . -q
cd ..

# Bootstrap CDK (if needed)
echo "🎯 Bootstrapping CDK..."
npx cdk bootstrap || echo "CDK already bootstrapped"

# Deploy stack
echo "☁️ Deploying CDK stack..."
npx cdk deploy --require-approval never

echo "✅ Deployment complete!"
echo ""
echo "🔗 Important URLs:"
aws cloudformation describe-stacks --stack-name KinexusAIMVPStack --query 'Stacks[0].Outputs' --output table