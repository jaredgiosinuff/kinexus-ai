#!/usr/bin/env python3
"""
AWS CDK Production Infrastructure for Kinexus AI
Complete production-ready stack with ECS, RDS, ElastiCache, and more
"""
import os
from aws_cdk import (
    App, Stack, Duration, RemovalPolicy, Size,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_rds as rds,
    aws_elasticache as elasticache,
    aws_iam as iam,
    aws_logs as logs,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_route53 as route53,
    aws_certificatemanager as acm,
    aws_secretsmanager as secretsmanager,
    aws_ssm as ssm,
    aws_elasticloadbalancingv2 as elbv2,
    aws_elasticloadbalancingv2_targets as targets,
    aws_events as events,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_cognito as cognito,
    aws_opensearchserverless as opensearch,
    aws_backup as backup,
    aws_cloudwatch as cloudwatch,
    CfnOutput,
)
from constructs import Construct


class KinexusAIProductionStack(Stack):
    """Production infrastructure stack for Kinexus AI"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get environment configuration
        self.environment = self.node.try_get_context("environment") or "production"
        self.domain_name = self.node.try_get_context("domain_name") or "kinexus.ai"

        # Create VPC and networking
        self._create_networking()

        # Create databases and caching
        self._create_databases()

        # Create container infrastructure
        self._create_container_infrastructure()

        # Create authentication and user management
        self._create_authentication()

        # Create storage and search
        self._create_storage_and_search()

        # Create monitoring and logging
        self._create_monitoring()

        # Create backup and disaster recovery
        self._create_backup_and_dr()

        # Create Lambda functions for webhooks and events
        self._create_lambda_functions()

        # Create API Gateway for webhooks
        self._create_api_gateway()

        # Create outputs
        self._create_outputs()

    def _create_networking(self):
        """Create VPC and networking infrastructure"""
        # VPC with public and private subnets across 3 AZs
        self.vpc = ec2.Vpc(
            self, "KinexusVPC",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=3,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="PublicSubnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="PrivateSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="DatabaseSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ]
        )

        # Security Groups
        self.alb_security_group = ec2.SecurityGroup(
            self, "ALBSecurityGroup",
            vpc=self.vpc,
            description="Security group for Application Load Balancer",
            allow_all_outbound=True
        )
        self.alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "HTTP traffic"
        )
        self.alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "HTTPS traffic"
        )

        self.ecs_security_group = ec2.SecurityGroup(
            self, "ECSSecurityGroup",
            vpc=self.vpc,
            description="Security group for ECS services",
            allow_all_outbound=True
        )
        self.ecs_security_group.add_ingress_rule(
            self.alb_security_group,
            ec2.Port.tcp(8000),
            "API traffic from ALB"
        )

        self.database_security_group = ec2.SecurityGroup(
            self, "DatabaseSecurityGroup",
            vpc=self.vpc,
            description="Security group for RDS databases",
            allow_all_outbound=False
        )
        self.database_security_group.add_ingress_rule(
            self.ecs_security_group,
            ec2.Port.tcp(5432),
            "PostgreSQL from ECS"
        )

        self.redis_security_group = ec2.SecurityGroup(
            self, "RedisSecurityGroup",
            vpc=self.vpc,
            description="Security group for ElastiCache Redis",
            allow_all_outbound=False
        )
        self.redis_security_group.add_ingress_rule(
            self.ecs_security_group,
            ec2.Port.tcp(6379),
            "Redis from ECS"
        )

    def _create_databases(self):
        """Create RDS PostgreSQL and ElastiCache Redis"""
        # RDS Subnet Group
        self.db_subnet_group = rds.SubnetGroup(
            self, "DatabaseSubnetGroup",
            description="Subnet group for RDS databases",
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            )
        )

        # Database credentials in Secrets Manager
        self.db_credentials = secretsmanager.Secret(
            self, "DatabaseCredentials",
            description="Credentials for Kinexus AI database",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "kinexus_admin"}',
                generate_string_key="password",
                exclude_characters='"@/\\'
            )
        )

        # RDS PostgreSQL Instance
        self.database = rds.DatabaseInstance(
            self, "KinexusDatabase",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_4
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3,
                ec2.InstanceSize.MEDIUM
            ),
            credentials=rds.Credentials.from_secret(self.db_credentials),
            database_name="kinexus_prod",
            allocated_storage=100,
            max_allocated_storage=1000,
            storage_encrypted=True,
            multi_az=True,
            vpc=self.vpc,
            subnet_group=self.db_subnet_group,
            security_groups=[self.database_security_group],
            backup_retention=Duration.days(7),
            delete_automated_backups=False,
            deletion_protection=True,
            parameter_group=rds.ParameterGroup.from_parameter_group_name(
                self, "PostgresParameterGroup",
                "default.postgres15"
            ),
            monitoring_interval=Duration.seconds(60),
            performance_insights_encryption_key=None,
            performance_insights_retention=rds.PerformanceInsightsRetention.DEFAULT,
            cloudwatch_logs_exports=["postgresql"]
        )

        # ElastiCache Redis Subnet Group
        self.redis_subnet_group = elasticache.CfnSubnetGroup(
            self, "RedisSubnetGroup",
            description="Subnet group for ElastiCache Redis",
            subnet_ids=[subnet.subnet_id for subnet in self.vpc.private_subnets]
        )

        # ElastiCache Redis Cluster
        self.redis_cluster = elasticache.CfnCacheCluster(
            self, "RedisCluster",
            cache_node_type="cache.t3.micro",
            engine="redis",
            num_cache_nodes=1,
            cache_subnet_group_name=self.redis_subnet_group.ref,
            vpc_security_group_ids=[self.redis_security_group.security_group_id],
            snapshot_retention_limit=5,
            snapshot_window="03:00-05:00",
            preferred_maintenance_window="sun:05:00-sun:06:00"
        )

    def _create_container_infrastructure(self):
        """Create ECS cluster and services"""
        # ECS Cluster
        self.ecs_cluster = ecs.Cluster(
            self, "KinexusCluster",
            vpc=self.vpc,
            cluster_name="kinexus-production",
            container_insights=True,
            enable_fargate_capacity_providers=True
        )

        # Application Load Balancer
        self.load_balancer = elbv2.ApplicationLoadBalancer(
            self, "KinexusALB",
            vpc=self.vpc,
            internet_facing=True,
            security_group=self.alb_security_group,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            )
        )

        # Target Group for API
        self.api_target_group = elbv2.ApplicationTargetGroup(
            self, "APITargetGroup",
            vpc=self.vpc,
            port=8000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                enabled=True,
                healthy_http_codes="200",
                interval=Duration.seconds(30),
                path="/health",
                protocol=elbv2.Protocol.HTTP,
                timeout=Duration.seconds(5),
                unhealthy_threshold_count=2
            )
        )

        # ALB Listener
        self.alb_listener = self.load_balancer.add_listener(
            "HTTPListener",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            default_target_groups=[self.api_target_group]
        )

        # Task Role for ECS
        self.task_role = iam.Role(
            self, "ECSTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )

        # Grant permissions to access Bedrock
        self.task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]
            )
        )

        # Grant access to secrets
        self.db_credentials.grant_read(self.task_role)

        # Task Definition
        self.api_task_definition = ecs.FargateTaskDefinition(
            self, "APITaskDefinition",
            memory_limit_mib=2048,
            cpu=1024,
            task_role=self.task_role,
            execution_role=self.task_role
        )

        # Environment variables
        environment_vars = {
            "ENVIRONMENT": self.environment,
            "DB_HOST": self.database.instance_endpoint.hostname,
            "DB_PORT": "5432",
            "DB_NAME": "kinexus_prod",
            "REDIS_HOST": self.redis_cluster.attr_redis_endpoint_address,
            "REDIS_PORT": "6379",
            "AWS_DEFAULT_REGION": self.region,
            "LOG_LEVEL": "INFO"
        }

        # Secrets from Secrets Manager
        secrets = {
            "DB_PASSWORD": ecs.Secret.from_secrets_manager(
                self.db_credentials, "password"
            ),
            "DB_USER": ecs.Secret.from_secrets_manager(
                self.db_credentials, "username"
            )
        }

        # Container Definition
        self.api_container = self.api_task_definition.add_container(
            "APIContainer",
            image=ecs.ContainerImage.from_registry("kinexus-ai-api:latest"),  # Update with actual image
            memory_limit_mib=1024,
            cpu=512,
            environment=environment_vars,
            secrets=secrets,
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="kinexus-api",
                log_retention=logs.RetentionDays.ONE_MONTH
            ),
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(60)
            )
        )

        # Port mapping
        self.api_container.add_port_mappings(
            ecs.PortMapping(
                container_port=8000,
                protocol=ecs.Protocol.TCP
            )
        )

        # ECS Service
        self.api_service = ecs.FargateService(
            self, "APIService",
            cluster=self.ecs_cluster,
            task_definition=self.api_task_definition,
            desired_count=2,
            assign_public_ip=False,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[self.ecs_security_group],
            enable_execute_command=True,
            circuit_breaker=ecs.DeploymentCircuitBreaker(
                rollback=True
            )
        )

        # Attach service to target group
        self.api_service.attach_to_application_target_group(self.api_target_group)

        # Auto Scaling
        scaling = self.api_service.auto_scale_task_count(
            min_capacity=2,
            max_capacity=10
        )

        scaling.scale_on_cpu_utilization(
            "CPUScaling",
            target_utilization_percent=70
        )

        scaling.scale_on_memory_utilization(
            "MemoryScaling",
            target_utilization_percent=80
        )

    def _create_authentication(self):
        """Create Cognito User Pool for authentication"""
        # User Pool
        self.user_pool = cognito.UserPool(
            self, "KinexusUserPool",
            user_pool_name="kinexus-users",
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY  # For non-production
        )

        # User Pool Client
        self.user_pool_client = self.user_pool.add_client(
            "KinexusUserPoolClient",
            user_pool_client_name="kinexus-web-client",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True
                ),
                scopes=[cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID, cognito.OAuthScope.PROFILE],
                callback_urls=[f"https://{self.domain_name}/auth/callback"]
            )
        )

        # Identity Pool
        self.identity_pool = cognito.CfnIdentityPool(
            self, "KinexusIdentityPool",
            identity_pool_name="kinexus_identity_pool",
            allow_unauthenticated_identities=False,
            cognito_identity_providers=[
                cognito.CfnIdentityPool.CognitoIdentityProviderProperty(
                    client_id=self.user_pool_client.user_pool_client_id,
                    provider_name=self.user_pool.user_pool_provider_name
                )
            ]
        )

    def _create_storage_and_search(self):
        """Create S3 buckets and OpenSearch"""
        # S3 Bucket for documents
        self.documents_bucket = s3.Bucket(
            self, "DocumentsBucket",
            bucket_name=f"kinexus-documents-{self.account}-{self.region}",
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    abort_incomplete_multipart_upload_after=Duration.days(1),
                    noncurrent_version_expiration=Duration.days(90),
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        )
                    ]
                )
            ],
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN
        )

        # S3 Bucket for backups
        self.backups_bucket = s3.Bucket(
            self, "BackupsBucket",
            bucket_name=f"kinexus-backups-{self.account}-{self.region}",
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(365),
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(30)
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.DEEP_ARCHIVE,
                            transition_after=Duration.days(90)
                        )
                    ]
                )
            ],
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN
        )

        # Grant ECS access to S3
        self.documents_bucket.grant_read_write(self.task_role)
        self.backups_bucket.grant_read_write(self.task_role)

    def _create_monitoring(self):
        """Create CloudWatch dashboards and alarms"""
        # CloudWatch Dashboard
        self.dashboard = cloudwatch.Dashboard(
            self, "KinexusDashboard",
            dashboard_name="Kinexus-AI-Production"
        )

        # ECS Service Metrics
        self.dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="ECS Service CPU and Memory",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/ECS",
                        metric_name="CPUUtilization",
                        dimensions_map={
                            "ServiceName": self.api_service.service_name,
                            "ClusterName": self.ecs_cluster.cluster_name
                        }
                    )
                ],
                right=[
                    cloudwatch.Metric(
                        namespace="AWS/ECS",
                        metric_name="MemoryUtilization",
                        dimensions_map={
                            "ServiceName": self.api_service.service_name,
                            "ClusterName": self.ecs_cluster.cluster_name
                        }
                    )
                ]
            )
        )

        # RDS Metrics
        self.dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="RDS Connections and Performance",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/RDS",
                        metric_name="DatabaseConnections",
                        dimensions_map={
                            "DBInstanceIdentifier": self.database.instance_identifier
                        }
                    )
                ],
                right=[
                    cloudwatch.Metric(
                        namespace="AWS/RDS",
                        metric_name="CPUUtilization",
                        dimensions_map={
                            "DBInstanceIdentifier": self.database.instance_identifier
                        }
                    )
                ]
            )
        )

        # Alarms
        cloudwatch.Alarm(
            self, "HighCPUAlarm",
            metric=cloudwatch.Metric(
                namespace="AWS/ECS",
                metric_name="CPUUtilization",
                dimensions_map={
                    "ServiceName": self.api_service.service_name,
                    "ClusterName": self.ecs_cluster.cluster_name
                }
            ),
            threshold=80,
            evaluation_periods=2,
            alarm_description="ECS Service CPU utilization is too high"
        )

        cloudwatch.Alarm(
            self, "DatabaseConnectionsAlarm",
            metric=cloudwatch.Metric(
                namespace="AWS/RDS",
                metric_name="DatabaseConnections",
                dimensions_map={
                    "DBInstanceIdentifier": self.database.instance_identifier
                }
            ),
            threshold=80,
            evaluation_periods=2,
            alarm_description="RDS connection count is too high"
        )

    def _create_backup_and_dr(self):
        """Create backup and disaster recovery resources"""
        # Backup Vault
        self.backup_vault = backup.BackupVault(
            self, "KinexusBackupVault",
            backup_vault_name="kinexus-backup-vault",
            encryption_key=None,  # Use default AWS managed key
            removal_policy=RemovalPolicy.RETAIN
        )

        # Backup Plan
        self.backup_plan = backup.BackupPlan(
            self, "KinexusBackupPlan",
            backup_plan_name="kinexus-backup-plan",
            backup_vault=self.backup_vault
        )

        # Backup rules
        self.backup_plan.add_rule(
            backup.BackupPlanRule(
                backup_vault=self.backup_vault,
                rule_name="DailyBackups",
                schedule_expression=events.Schedule.cron(
                    hour="2",
                    minute="0"
                ),
                delete_after=Duration.days(30),
                move_to_cold_storage_after=Duration.days(7)
            )
        )

        # Add RDS to backup plan
        self.backup_plan.add_selection(
            "DatabaseBackupSelection",
            resources=[
                backup.BackupResource.from_rds_database_instance(self.database)
            ]
        )

    def _create_lambda_functions(self):
        """Create Lambda functions for webhooks and events"""
        # Lambda Layer for shared dependencies
        self.lambda_layer = lambda_.LayerVersion(
            self, "KinexusLayer",
            code=lambda_.Code.from_asset("lambda_layer.zip"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Shared dependencies for Kinexus AI"
        )

        # Environment variables for Lambdas
        lambda_environment = {
            "API_BASE_URL": f"http://{self.load_balancer.load_balancer_dns_name}",
            "DOCUMENTS_BUCKET": self.documents_bucket.bucket_name,
            "AWS_DEFAULT_REGION": self.region
        }

        # GitHub Webhook Handler Lambda
        self.github_webhook_handler = lambda_.Function(
            self, "GitHubWebhookHandler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            code=lambda_.Code.from_asset("src/lambdas"),
            handler="github_webhook_handler_v2.lambda_handler",
            timeout=Duration.seconds(30),
            memory_size=512,
            environment=lambda_environment,
            layers=[self.lambda_layer],
            log_retention=logs.RetentionDays.ONE_MONTH,
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[self.ecs_security_group]
        )

        # Grant Lambda access to S3 and Bedrock
        self.documents_bucket.grant_read_write(self.github_webhook_handler)
        self.github_webhook_handler.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]
            )
        )

    def _create_api_gateway(self):
        """Create API Gateway for webhooks"""
        # API Gateway for webhooks
        self.webhook_api = apigateway.RestApi(
            self, "KinexusWebhookAPI",
            rest_api_name="Kinexus Webhook API",
            description="Webhook endpoints for external integrations",
            default_cors_preflight_options={
                "allow_origins": apigateway.Cors.ALL_ORIGINS,
                "allow_methods": ["GET", "POST", "OPTIONS"],
                "allow_headers": apigateway.Cors.DEFAULT_HEADERS
            }
        )

        # Webhook endpoints
        webhooks_resource = self.webhook_api.root.add_resource("webhooks")

        # GitHub webhook endpoint
        github_resource = webhooks_resource.add_resource("github")
        github_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.github_webhook_handler)
        )

    def _create_outputs(self):
        """Create CloudFormation outputs"""
        CfnOutput(
            self, "LoadBalancerDNS",
            value=self.load_balancer.load_balancer_dns_name,
            description="Application Load Balancer DNS name"
        )

        CfnOutput(
            self, "DatabaseEndpoint",
            value=self.database.instance_endpoint.hostname,
            description="RDS PostgreSQL endpoint"
        )

        CfnOutput(
            self, "RedisEndpoint",
            value=self.redis_cluster.attr_redis_endpoint_address,
            description="ElastiCache Redis endpoint"
        )

        CfnOutput(
            self, "DocumentsBucket",
            value=self.documents_bucket.bucket_name,
            description="S3 bucket for documents"
        )

        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID"
        )

        CfnOutput(
            self, "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID"
        )

        CfnOutput(
            self, "WebhookAPIEndpoint",
            value=self.webhook_api.url,
            description="Webhook API Gateway endpoint"
        )

        CfnOutput(
            self, "GitHubWebhookURL",
            value=f"{self.webhook_api.url}webhooks/github",
            description="GitHub webhook URL"
        )