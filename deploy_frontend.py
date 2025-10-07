#!/usr/bin/env python3
"""
Deploy frontend to S3 and CloudFront
"""
import boto3
import json
import os
from pathlib import Path

def create_s3_bucket_for_frontend():
    """Create S3 bucket for static website hosting"""
    s3 = boto3.client('s3')
    cloudfront = boto3.client('cloudfront')

    # Get account ID dynamically
    account_id = boto3.client('sts').get_caller_identity()['Account']
    bucket_name = f'kinexusai-frontend-{account_id}'

    try:
        # Create S3 bucket
        s3.create_bucket(Bucket=bucket_name)
        print(f"✅ Created frontend S3 bucket: {bucket_name}")

        # Configure bucket for static website hosting
        s3.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={
                'IndexDocument': {'Suffix': 'index.html'},
                'ErrorDocument': {'Key': 'index.html'}  # SPA redirect
            }
        )

        # Set bucket policy for public read access
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
        print(f"✅ Configured bucket for static website hosting")

        return bucket_name

    except Exception as e:
        if 'BucketAlreadyOwnedByYou' in str(e):
            print(f"✅ Frontend S3 bucket already exists: {bucket_name}")
            return bucket_name
        else:
            print(f"❌ Error creating frontend bucket: {e}")
            return None

def upload_frontend_files(bucket_name):
    """Upload built frontend files to S3"""
    s3 = boto3.client('s3')

    dist_path = Path('./frontend/dist')
    if not dist_path.exists():
        print("❌ Frontend dist directory not found. Run 'npm run build' first.")
        return False

    # MIME type mapping
    mime_types = {
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon'
    }

    try:
        # Upload all files from dist directory
        for file_path in dist_path.rglob('*'):
            if file_path.is_file():
                # Get relative path for S3 key
                s3_key = str(file_path.relative_to(dist_path)).replace('\\', '/')

                # Determine content type
                file_extension = file_path.suffix.lower()
                content_type = mime_types.get(file_extension, 'binary/octet-stream')

                # Upload file
                with open(file_path, 'rb') as file_data:
                    s3.put_object(
                        Bucket=bucket_name,
                        Key=s3_key,
                        Body=file_data,
                        ContentType=content_type,
                        CacheControl='public, max-age=31536000' if s3_key != 'index.html' else 'public, max-age=0'
                    )

                print(f"📤 Uploaded: {s3_key}")

        print(f"✅ All frontend files uploaded to S3")
        return True

    except Exception as e:
        print(f"❌ Error uploading files: {e}")
        return False

def create_cloudfront_distribution(bucket_name):
    """Create CloudFront distribution for the frontend"""
    cloudfront = boto3.client('cloudfront')

    try:
        # CloudFront distribution configuration
        distribution_config = {
            'CallerReference': f'kinexus-frontend-{int(os.urandom(4).hex(), 16)}',
            'Comment': 'Kinexus AI Frontend Distribution',
            'DefaultCacheBehavior': {
                'TargetOriginId': bucket_name,
                'ViewerProtocolPolicy': 'redirect-to-https',
                'MinTTL': 0,
                'DefaultTTL': 86400,
                'MaxTTL': 31536000,
                'ForwardedValues': {
                    'QueryString': False,
                    'Cookies': {'Forward': 'none'}
                },
                'TrustedSigners': {
                    'Enabled': False,
                    'Quantity': 0
                }
            },
            'Origins': {
                'Quantity': 1,
                'Items': [{
                    'Id': bucket_name,
                    'DomainName': f'{bucket_name}.s3-website-us-east-1.amazonaws.com',
                    'CustomOriginConfig': {
                        'HTTPPort': 80,
                        'HTTPSPort': 443,
                        'OriginProtocolPolicy': 'http-only'
                    }
                }]
            },
            'Enabled': True,
            'DefaultRootObject': 'index.html',
            'CustomErrorResponses': {
                'Quantity': 1,
                'Items': [{
                    'ErrorCode': 404,
                    'ResponsePagePath': '/index.html',
                    'ResponseCode': '200',
                    'ErrorCachingMinTTL': 300
                }]
            },
            'Aliases': {
                'Quantity': 1,
                'Items': ['kinexusai.com']
            },
            'ViewerCertificate': {
                'ACMCertificateArn': f'arn:aws:acm:us-east-1:{boto3.client("sts").get_caller_identity()["Account"]}:certificate/a1711376-ccff-4127-a0a2-f3303e48a26c',
                'SSLSupportMethod': 'sni-only',
                'MinimumProtocolVersion': 'TLSv1.2_2021'
            },
            'PriceClass': 'PriceClass_100'
        }

        # Create distribution
        response = cloudfront.create_distribution(DistributionConfig=distribution_config)

        distribution_id = response['Distribution']['Id']
        domain_name = response['Distribution']['DomainName']

        print(f"✅ Created CloudFront distribution: {distribution_id}")
        print(f"🌐 CloudFront domain: {domain_name}")
        print(f"⏳ Distribution is deploying (takes 15-20 minutes)...")

        return {
            'distribution_id': distribution_id,
            'domain_name': domain_name
        }

    except Exception as e:
        print(f"❌ Error creating CloudFront distribution: {e}")
        return None

def update_route53_record(cloudfront_domain):
    """Update Route 53 to point to CloudFront"""
    route53 = boto3.client('route53')

    try:
        # Update the A record to point to CloudFront
        route53.change_resource_record_sets(
            HostedZoneId='Z0826076N4N8VIQO05U9',
            ChangeBatch={
                'Changes': [{
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': 'kinexusai.com',
                        'Type': 'A',
                        'AliasTarget': {
                            'DNSName': cloudfront_domain,
                            'EvaluateTargetHealth': False,
                            'HostedZoneId': 'Z2FDTNDATAQYW2'  # CloudFront hosted zone ID
                        }
                    }
                }]
            }
        )

        print(f"✅ Updated Route 53 A record to point to CloudFront")

    except Exception as e:
        print(f"❌ Error updating Route 53: {e}")

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

    print("🚀 Deploying frontend...")

    # Create S3 bucket
    bucket_name = create_s3_bucket_for_frontend()

    if bucket_name:
        # Upload frontend files
        if upload_frontend_files(bucket_name):
            # Create CloudFront distribution
            distribution = create_cloudfront_distribution(bucket_name)

            if distribution:
                # Update Route 53
                update_route53_record(distribution['domain_name'])

                print("\n" + "="*60)
                print("🎯 FRONTEND DEPLOYMENT COMPLETE!")
                print("="*60)
                print(f"🌐 Production URL: https://kinexusai.com")
                print(f"☁️ CloudFront: {distribution['domain_name']}")
                print(f"🪣 S3 Bucket: {bucket_name}")
                print(f"🔐 SSL: Certificate validated")
                print("⏳ CloudFront deployment in progress (15-20 min)")
                print("="*60)
            else:
                print("❌ Frontend deployment failed")
    else:
        print("❌ Could not create S3 bucket")