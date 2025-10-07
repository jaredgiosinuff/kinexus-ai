#!/usr/bin/env python3
"""
Deploy Lambda functions for Kinexus AI
"""
import boto3
import json
import zipfile
import os

def create_simple_lambda():
    """Create a simple Lambda function for the MVP"""

    # Create a simple Lambda function code
    lambda_code = '''
import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Simple Kinexus AI webhook handler
    Processes GitHub/Jira webhooks and triggers document updates
    """

    logger.info(f"Received event: {json.dumps(event)}")

    # Extract webhook data
    try:
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event

        # Initialize AWS services
        dynamodb = boto3.resource('dynamodb')
        changes_table = dynamodb.Table('kinexus-changes')

        # Process different webhook types
        webhook_source = "unknown"
        change_data = {}

        if 'repository' in body:
            # GitHub webhook
            webhook_source = "github"
            change_data = {
                'change_id': f"github-{body.get('after', 'unknown')}",
                'source': 'github',
                'repository': body['repository']['full_name'],
                'commits': body.get('commits', []),
                'timestamp': body.get('head_commit', {}).get('timestamp', ''),
                'status': 'pending'
            }
        elif 'issue' in body:
            # Jira webhook
            webhook_source = "jira"
            change_data = {
                'change_id': f"jira-{body['issue']['id']}",
                'source': 'jira',
                'issue_key': body['issue']['key'],
                'summary': body['issue']['fields']['summary'],
                'status': 'pending'
            }

        # Store change in DynamoDB
        if change_data:
            changes_table.put_item(Item=change_data)
            logger.info(f"Stored {webhook_source} change: {change_data['change_id']}")

        # Simulate AI processing
        ai_response = {
            'analysis': f"Detected {webhook_source} change",
            'documents_affected': ['README.md', 'ARCHITECTURE.md'],
            'confidence': 0.85,
            'recommendations': ['Update documentation', 'Review code changes']
        }

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Webhook processed successfully',
                'source': webhook_source,
                'change_id': change_data.get('change_id', 'unknown'),
                'ai_analysis': ai_response
            })
        }

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Internal server error'
            })
        }
'''

    # Create deployment package
    with zipfile.ZipFile('lambda_function.zip', 'w') as zip_file:
        zip_file.writestr('lambda_function.py', lambda_code)

    # Deploy Lambda function
    lambda_client = boto3.client('lambda')

    try:
        with open('lambda_function.zip', 'rb') as zip_file:
            response = lambda_client.create_function(
                FunctionName='kinexus-webhook-handler',
                Runtime='python3.11',
                Role=f'arn:aws:iam::{boto3.client("sts").get_caller_identity()["Account"]}:role/kinexus-lambda-role',
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_file.read()},
                Description='Kinexus AI webhook handler for GitHub and Jira',
                Timeout=30,
                MemorySize=512,
                Environment={
                    'Variables': {
                        'REGION': 'us-east-1',
                        'DOCUMENTS_TABLE': 'kinexus-documents',
                        'CHANGES_TABLE': 'kinexus-changes'
                    }
                }
            )

        function_arn = response['FunctionArn']
        print(f"✅ Created Lambda function: {function_arn}")

        # Add API Gateway permission
        lambda_client.add_permission(
            FunctionName='kinexus-webhook-handler',
            StatementId='api-gateway-invoke',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws:execute-api:us-east-1:{boto3.client("sts").get_caller_identity()["Account"]}:388tx4f8ri/*'
        )
        print("✅ Added API Gateway permissions")

        return function_arn

    except Exception as e:
        if 'ResourceConflictException' in str(e):
            print("✅ Lambda function already exists")
            return f"arn:aws:lambda:us-east-1:{boto3.client('sts').get_caller_identity()['Account']}:function:kinexus-webhook-handler"
        else:
            print(f"❌ Error creating Lambda: {e}")
            return None

def setup_api_methods():
    """Set up API Gateway methods"""
    apigateway = boto3.client('apigateway')

    api_id = '388tx4f8ri'
    # Get account ID dynamically
    account_id = boto3.client('sts').get_caller_identity()['Account']
    function_arn = f'arn:aws:lambda:us-east-1:{account_id}:function:kinexus-webhook-handler'

    try:
        # Get resources
        resources = apigateway.get_resources(restApiId=api_id)
        webhooks_resource_id = None

        for resource in resources['items']:
            if resource.get('pathPart') == 'webhooks':
                webhooks_resource_id = resource['id']
                break

        if not webhooks_resource_id:
            print("❌ Webhooks resource not found")
            return

        # Create GitHub webhook endpoint
        github_resource = apigateway.create_resource(
            restApiId=api_id,
            parentId=webhooks_resource_id,
            pathPart='github'
        )

        # Create POST method for GitHub
        apigateway.put_method(
            restApiId=api_id,
            resourceId=github_resource['id'],
            httpMethod='POST',
            authorizationType='NONE'
        )

        # Set up Lambda integration
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=github_resource['id'],
            httpMethod='POST',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=f'arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{function_arn}/invocations'
        )

        # Create Jira webhook endpoint
        jira_resource = apigateway.create_resource(
            restApiId=api_id,
            parentId=webhooks_resource_id,
            pathPart='jira'
        )

        # Create POST method for Jira
        apigateway.put_method(
            restApiId=api_id,
            resourceId=jira_resource['id'],
            httpMethod='POST',
            authorizationType='NONE'
        )

        # Set up Lambda integration
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=jira_resource['id'],
            httpMethod='POST',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=f'arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{function_arn}/invocations'
        )

        # Deploy the API
        apigateway.create_deployment(
            restApiId=api_id,
            stageName='prod'
        )

        api_url = f"https://{api_id}.execute-api.us-east-1.amazonaws.com/prod"
        print(f"✅ API deployed with webhooks:")
        print(f"  🔗 GitHub: {api_url}/webhooks/github")
        print(f"  🔗 Jira: {api_url}/webhooks/jira")

        return api_url

    except Exception as e:
        print(f"❌ Error setting up API methods: {e}")
        return None

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

    print("🚀 Deploying Lambda functions...")

    # Deploy Lambda
    function_arn = create_simple_lambda()

    if function_arn:
        # Set up API methods
        api_url = setup_api_methods()

        print("\n" + "="*60)
        print("🎯 LAMBDA DEPLOYMENT COMPLETE!")
        print("="*60)
        print(f"⚡ Function: {function_arn}")
        print(f"🌐 API URL: {api_url}")
        print("="*60)
    else:
        print("❌ Lambda deployment failed")