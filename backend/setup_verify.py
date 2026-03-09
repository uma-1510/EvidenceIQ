"""
EvidenceIQ — AWS Setup & Verification Script
Run this FIRST to verify everything is configured correctly.
Usage: python setup_verify.py
"""

import boto3
import json
import sys
import os
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION            = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME        = os.getenv("S3_BUCKET_NAME", "evidenceiq-videos")

NOVA_MODELS = {
    "Nova Lite 2":   "us.amazon.nova-lite-v1:0",
    "Nova Pro":      "us.amazon.nova-pro-v1:0",
    "Nova Premier":  "us.amazon.nova-premier-v1:0",
}

def print_step(step: str, status: str = "running"):
    icons = {"running": "⏳", "ok": "✅", "fail": "❌", "warn": "⚠️"}
    print(f"{icons.get(status, '•')} {step}")

def check_credentials():
    print("\n── Step 1: Verifying AWS Credentials ──────────────────")
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        print_step("Credentials missing in .env file", "fail")
        sys.exit(1)

    try:
        sts = boto3.client(
            "sts",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        identity = sts.get_caller_identity()
        print_step(f"Credentials valid — Account: {identity['Account']}", "ok")
        print_step(f"IAM ARN: {identity['Arn']}", "ok")
        return True
    except Exception as e:
        print_step(f"Credential error: {e}", "fail")
        sys.exit(1)

def check_or_create_s3_bucket():
    print("\n── Step 2: S3 Bucket Setup ─────────────────────────────")
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )

    try:
        s3.head_bucket(Bucket=S3_BUCKET_NAME)
        print_step(f"Bucket '{S3_BUCKET_NAME}' already exists", "ok")
    except Exception:
        print_step(f"Bucket '{S3_BUCKET_NAME}' not found — creating...", "running")
        try:
            if AWS_REGION == "us-east-1":
                s3.create_bucket(Bucket=S3_BUCKET_NAME)
            else:
                s3.create_bucket(
                    Bucket=S3_BUCKET_NAME,
                    CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
                )

            # Block all public access
            s3.put_public_access_block(
                Bucket=S3_BUCKET_NAME,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": True,
                    "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True,
                    "RestrictPublicBuckets": True,
                },
            )

            # Add CORS for frontend uploads
            s3.put_bucket_cors(
                Bucket=S3_BUCKET_NAME,
                CORSConfiguration={
                    "CORSRules": [
                        {
                            "AllowedHeaders": ["*"],
                            "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
                            "AllowedOrigins": ["http://localhost:3000"],
                            "MaxAgeSeconds": 3600,
                        }
                    ]
                },
            )

            print_step(f"Bucket '{S3_BUCKET_NAME}' created with private access + CORS", "ok")
        except Exception as e:
            print_step(f"Failed to create bucket: {e}", "fail")
            sys.exit(1)

def check_bedrock_model_access():
    print("\n── Step 3: Verifying Bedrock Model Access ──────────────")
    bedrock = boto3.client(
        "bedrock-runtime",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )

    all_ok = True
    for name, model_id in NOVA_MODELS.items():
        try:
            # Send a minimal test prompt to verify model access
            body = json.dumps({
                "schemaVersion": "messages-v1",
                "messages": [
                    {"role": "user", "content": [{"text": "Reply with OK only."}]}
                ],
                "inferenceConfig": {"max_new_tokens": 5},
            })
            response = bedrock.invoke_model(
                modelId=model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            result = json.loads(response["body"].read())
            reply = result["output"]["message"]["content"][0]["text"].strip()
            print_step(f"{name} ({model_id}) — Response: '{reply}'", "ok")
        except bedrock.exceptions.AccessDeniedException:
            print_step(
                f"{name}: Access DENIED — Enable model access in AWS Bedrock Console → Model Access",
                "fail",
            )
            all_ok = False
        except Exception as e:
            print_step(f"{name}: Error — {e}", "fail")
            all_ok = False

    return all_ok

def check_s3_bedrock_permission():
    print("\n── Step 4: Verifying Bedrock can read your S3 bucket ───")
    print_step(
        "Note: Bedrock accesses S3 using your IAM credentials passed in the API call.",
        "warn",
    )
    print_step(
        "Ensure your IAM user has s3:GetObject permission on the bucket.",
        "warn",
    )
    
    # Check IAM policies by testing a real s3 read
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    try:
        s3.list_objects_v2(Bucket=S3_BUCKET_NAME, MaxKeys=1)
        print_step("S3 read access confirmed", "ok")
    except Exception as e:
        print_step(f"S3 read error: {e}", "fail")

def print_iam_policy():
    print("\n── IAM Policy Required for your User ───────────────────")
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "BedrockFullAccess",
                "Effect": "Allow",
                "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                "Resource": "*",
            },
            {
                "Sid": "S3BucketAccess",
                "Effect": "Allow",
                "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:ListBucket", "s3:CreateBucket", "s3:PutBucketCORS", "s3:PutPublicAccessBlock"],
                "Resource": [
                    f"arn:aws:s3:::{S3_BUCKET_NAME}",
                    f"arn:aws:s3:::{S3_BUCKET_NAME}/*",
                ],
            },
        ],
    }
    print("\nAttach this inline policy to your IAM user if any step above failed:")
    print(json.dumps(policy, indent=2))

def main():
    print("=" * 55)
    print("  EvidenceIQ — AWS Setup Verification")
    print("=" * 55)

    check_credentials()
    check_or_create_s3_bucket()
    models_ok = check_bedrock_model_access()
    check_s3_bedrock_permission()
    print_iam_policy()

    print("\n" + "=" * 55)
    if models_ok:
        print("✅  All checks passed. You are ready to build!")
        print("    Next step: python backend/main.py")
    else:
        print("⚠️  Some model access checks failed.")
        print("   Go to: AWS Console → Bedrock → Model Access")
        print("   Request access to all Amazon Nova models.")
    print("=" * 55 + "\n")

if __name__ == "__main__":
    main()