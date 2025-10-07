#!/usr/bin/env python3
"""
AWS CDK Infrastructure for Kinexus AI MVP
Quick deployment stack for hackathon demo
"""
import os
from aws_cdk import (
    App, Stack, Duration, RemovalPolicy,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct


class KinexusAIMVPStack(Stack):
    """MVP infrastructure stack for Kinexus AI"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 Bucket for documents
        self.documents_bucket = s3.Bucket(
            self, "DocumentsBucket",
            bucket_name=f"kinexus-documents-{self.account}-{self.region}",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,  # For hackathon only
            auto_delete_objects=True,  # For hackathon only
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
                    allowed_origins=["*"],  # Update for production
                    allowed_headers=["*"]
                )
            ]
        )

        # DynamoDB Tables
        self.changes_table = dynamodb.Table(
            self, "ChangesTable",
            table_name="kinexus-changes",
            partition_key=dynamodb.Attribute(
                name="change_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY  # For hackathon only
        )

        self.documents_table = dynamodb.Table(
            self, "DocumentsTable",
            table_name="kinexus-documents",
            partition_key=dynamodb.Attribute(
                name="document_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY  # For hackathon only
        )

        # EventBridge Event Bus
        self.event_bus = events.EventBus(
            self, "KinexusEventBus",
            event_bus_name="kinexus-events"
        )

        # Lambda Layer for shared dependencies
        self.lambda_layer = lambda_.LayerVersion(
            self, "KinexusLayer",
            code=lambda_.Code.from_asset("lambda_layer.zip"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Shared dependencies for Kinexus AI"
        )

        # GitHub Webhook Handler Lambda
        self.github_webhook_handler = lambda_.Function(
            self, "GitHubWebhookHandler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("src/lambdas"),
            handler="github_webhook_handler.lambda_handler",
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "CHANGES_TABLE": self.changes_table.table_name,
                "EVENT_BUS": self.event_bus.event_bus_name
            },
            layers=[self.lambda_layer],
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Jira Webhook Handler Lambda
        self.jira_webhook_handler = lambda_.Function(
            self, "JiraWebhookHandler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("src/lambdas"),
            handler="jira_webhook_handler.lambda_handler",
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "CHANGES_TABLE": self.changes_table.table_name,
                "EVENT_BUS": self.event_bus.event_bus_name
            },
            layers=[self.lambda_layer],
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Document Orchestrator Lambda
        self.document_orchestrator = lambda_.Function(
            self, "DocumentOrchestrator",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("src/lambdas"),
            handler="document_orchestrator.lambda_handler",
            timeout=Duration.minutes(5),
            memory_size=1024,
            environment={
                "CHANGES_TABLE": self.changes_table.table_name,
                "DOCUMENTS_TABLE": self.documents_table.table_name,
                "DOCUMENTS_BUCKET": self.documents_bucket.bucket_name,
                "EVENT_BUS": self.event_bus.event_bus_name
            },
            layers=[self.lambda_layer],
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Grant permissions
        self.changes_table.grant_read_write_data(self.github_webhook_handler)
        self.changes_table.grant_read_write_data(self.jira_webhook_handler)
        self.changes_table.grant_read_write_data(self.document_orchestrator)
        self.documents_table.grant_read_write_data(self.document_orchestrator)
        self.documents_bucket.grant_read_write(self.document_orchestrator)
        self.event_bus.grant_put_events_to(self.github_webhook_handler)
        self.event_bus.grant_put_events_to(self.jira_webhook_handler)
        self.event_bus.grant_put_events_to(self.document_orchestrator)

        # Grant Bedrock access to orchestrator
        self.document_orchestrator.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]  # Bedrock doesn't support resource-level permissions
            )
        )

        # EventBridge Rule to trigger orchestrator from multiple sources
        events.Rule(
            self, "ChangeDetectedRule",
            event_bus=self.event_bus,
            event_pattern={
                "source": ["kinexus.github", "kinexus.jira"],
                "detail-type": ["ChangeDetected"]
            },
            targets=[targets.LambdaFunction(self.document_orchestrator)]
        )

        # API Gateway
        self.api = apigateway.RestApi(
            self, "KinexusAPI",
            rest_api_name="Kinexus AI API",
            description="API for Kinexus AI Hackathon Demo",
            default_cors_preflight_options={
                "allow_origins": ["*"],  # Update for production
                "allow_methods": ["GET", "POST", "OPTIONS"],
                "allow_headers": ["*"]
            }
        )

        # Webhook endpoints
        webhooks_resource = self.api.root.add_resource("webhooks")

        # GitHub webhook endpoint
        github_resource = webhooks_resource.add_resource("github")
        github_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.github_webhook_handler)
        )

        # Jira webhook endpoint
        jira_resource = webhooks_resource.add_resource("jira")
        jira_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.jira_webhook_handler)
        )

        # Documents API endpoints
        documents_resource = self.api.root.add_resource("documents")
        documents_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.document_orchestrator)
        )

        # Output important values
        from aws_cdk import CfnOutput

        CfnOutput(
            self, "APIEndpoint",
            value=self.api.url,
            description="API Gateway endpoint URL"
        )

        CfnOutput(
            self, "GitHubWebhookURL",
            value=f"{self.api.url}webhooks/github",
            description="GitHub webhook URL"
        )

        CfnOutput(
            self, "JiraWebhookURL",
            value=f"{self.api.url}webhooks/jira",
            description="Jira webhook URL"
        )

        CfnOutput(
            self, "DocumentsBucket",
            value=self.documents_bucket.bucket_name,
            description="S3 bucket for documents"
        )


# Import production stack
from production_stack import KinexusAIProductionStack

# CDK App
app = App()

# Get deployment type from context
deployment_type = app.node.try_get_context("deployment_type") or "mvp"
environment = app.node.try_get_context("environment") or "development"

if deployment_type == "production":
    # Deploy production stack with full infrastructure
    KinexusAIProductionStack(
        app,
        f"KinexusAIProductionStack-{environment.title()}",
        env={
            "region": app.node.try_get_context("region") or "us-east-1",
            "account": app.node.try_get_context("account")
        }
    )
else:
    # Deploy MVP stack for quick demos and development
    KinexusAIMVPStack(
        app,
        f"KinexusAIMVPStack-{environment.title()}"
    )

app.synth()