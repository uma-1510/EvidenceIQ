"""
EvidenceIQ — S3 Handler
Manages all video upload and retrieval operations with S3.
"""

import os
import uuid
import boto3
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION            = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME        = os.getenv("S3_BUCKET_NAME", "evidenceiq-videos")

SUPPORTED_FORMATS = {"mp4", "mov", "avi", "mkv", "webm"}


def _get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )


def upload_video(file_bytes: bytes, filename: str) -> dict:
    """
    Upload a video file to S3.
    Returns the S3 URI and a unique job ID.
    """
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format: .{ext}. Use: {SUPPORTED_FORMATS}")

    job_id  = str(uuid.uuid4())
    s3_key  = f"uploads/{job_id}/{filename}"
    s3_uri  = f"s3://{S3_BUCKET_NAME}/{s3_key}"

    s3 = _get_s3_client()
    s3.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=s3_key,
        Body=file_bytes,
        ContentType=f"video/{ext}",
    )

    return {
        "job_id":   job_id,
        "s3_uri":   s3_uri,
        "s3_key":   s3_key,
        "filename": filename,
        "format":   ext,
    }


def get_presigned_url(s3_key: str, expires_in: int = 3600) -> str:
    """Generate a temporary URL so the frontend can play the uploaded video."""
    s3 = _get_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET_NAME, "Key": s3_key},
        ExpiresIn=expires_in,
    )


def delete_video(s3_key: str):
    """Clean up a video after analysis is complete."""
    s3 = _get_s3_client()
    s3.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)