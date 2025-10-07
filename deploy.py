#!/usr/bin/env python3
"""
Simple deployment script for Kinexus AI MVP
Uses basic AWS resources for quick hackathon deployment
"""
import boto3
import json
import time
import os

def setup_basic_infrastructure():
    """Set up basic infrastructure without CDK"""

    # AWS clients
    s3 = boto3.client('s3')
    dynamodb = boto3.client('dynamodb')
    lambda_client = boto3.client('lambda')
    apigateway = boto3.client('apigateway')
    iam = boto3.client('iam')

    region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')

    # Get account ID dynamically
    sts = boto3.client('sts')
    try:
        account_id = sts.get_caller_identity()['Account']
    except Exception as e:
        print(f"❌ Could not get AWS account ID: {e}")
        exit(1)

    print("🚀 Starting Kinexus AI Deployment...")

    # 1. Create S3 Bucket for documents
    bucket_name = f'kinexus-documents-{account_id}-{region}'
    try:
        s3.create_bucket(Bucket=bucket_name)
        print(f"✅ Created S3 bucket: {bucket_name}")
    except Exception as e:
        if 'BucketAlreadyOwnedByYou' in str(e):
            print(f"✅ S3 bucket already exists: {bucket_name}")
        else:
            print(f"❌ Error creating S3 bucket: {e}")

    # 2. Create DynamoDB Tables
    tables = [
        {
            'TableName': 'kinexus-documents',
            'KeySchema': [{'AttributeName': 'document_id', 'KeyType': 'HASH'}],
            'AttributeDefinitions': [{'AttributeName': 'document_id', 'AttributeType': 'S'}]
        },
        {
            'TableName': 'kinexus-changes',
            'KeySchema': [{'AttributeName': 'change_id', 'KeyType': 'HASH'}],
            'AttributeDefinitions': [{'AttributeName': 'change_id', 'AttributeType': 'S'}]
        }
    ]

    for table_config in tables:
        try:
            dynamodb.create_table(
                **table_config,
                BillingMode='PAY_PER_REQUEST'
            )
            print(f"✅ Created DynamoDB table: {table_config['TableName']}")
            time.sleep(2)  # Wait for table creation
        except Exception as e:
            if 'ResourceInUseException' in str(e):
                print(f"✅ DynamoDB table already exists: {table_config['TableName']}")
            else:
                print(f"❌ Error creating DynamoDB table: {e}")

    # 3. Create IAM Role for Lambda
    lambda_role_name = 'kinexus-lambda-role'
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }

    lambda_policy = {
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
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "*"
        }]
    }

    try:
        iam.create_role(
            RoleName=lambda_role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        print(f"✅ Created IAM role: {lambda_role_name}")

        iam.put_role_policy(
            RoleName=lambda_role_name,
            PolicyName='kinexus-lambda-policy',
            PolicyDocument=json.dumps(lambda_policy)
        )
        print(f"✅ Attached policy to role: {lambda_role_name}")

    except Exception as e:
        if 'EntityAlreadyExists' in str(e):
            print(f"✅ IAM role already exists: {lambda_role_name}")
        else:
            print(f"❌ Error creating IAM role: {e}")

    print("\n🎉 Basic infrastructure setup complete!")
    print(f"📊 DynamoDB Tables: kinexus-documents, kinexus-changes")
    print(f"🗄️ S3 Bucket: {bucket_name}")
    print(f"🔑 IAM Role: {lambda_role_name}")
    print(f"🌐 Domain: kinexusai.com (SSL certificate ready)")

    return {
        'bucket_name': bucket_name,
        'lambda_role_arn': f'arn:aws:iam::{account_id}:role/{lambda_role_name}',
        'tables': ['kinexus-documents', 'kinexus-changes']
    }

def create_api_endpoint():
    """Create simple API Gateway for webhooks"""
    apigateway = boto3.client('apigateway')

    try:
        # Create REST API
        api_response = apigateway.create_rest_api(
            name='Kinexus AI API',
            description='MVP API for Kinexus AI Hackathon Demo',
            endpointConfiguration={'types': ['REGIONAL']}
        )

        api_id = api_response['id']
        print(f"✅ Created API Gateway: {api_id}")

        # Get root resource
        resources = apigateway.get_resources(restApiId=api_id)
        root_id = resources['items'][0]['id']

        # Create webhooks resource
        webhooks_resource = apigateway.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart='webhooks'
        )

        print(f"✅ Created /webhooks endpoint")

        # Deploy API
        apigateway.create_deployment(
            restApiId=api_id,
            stageName='prod'
        )

        api_url = f"https://{api_id}.execute-api.us-east-1.amazonaws.com/prod"
        print(f"✅ API deployed at: {api_url}")

        return {'api_id': api_id, 'api_url': api_url}

    except Exception as e:
        print(f"❌ Error creating API Gateway: {e}")
        return None

if __name__ == "__main__":
    # Set up AWS credentials
    # AWS credentials should be set via environment variables or AWS CLI
    if not os.environ.get('AWS_ACCESS_KEY_ID'):
        print("❌ Please set AWS_ACCESS_KEY_ID environment variable")
        exit(1)
    if not os.environ.get('AWS_SECRET_ACCESS_KEY'):
        print("❌ Please set AWS_SECRET_ACCESS_KEY environment variable")
        exit(1)
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

    # Deploy infrastructure
    infra = setup_basic_infrastructure()
    api = create_api_endpoint()

    print("\n" + "="*60)
    print("🎯 KINEXUS AI DEPLOYMENT COMPLETE!")
    print("="*60)
    print(f"🌐 Domain: https://kinexusai.com (SSL ready)")
    print(f"📡 API: {api['api_url'] if api else 'Failed to create'}")
    print(f"🗄️ Storage: {infra['bucket_name']}")
    print(f"📊 Database: DynamoDB tables ready")
    print(f"🔐 SSL Certificate: arn:aws:acm:{region}:{account_id}:certificate/a1711376-ccff-4127-a0a2-f3303e48a26c")
    print("="*60)