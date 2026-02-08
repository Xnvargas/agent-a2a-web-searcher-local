"""
=============================================================================
MINIO CLIENT - Object storage for document artifacts
=============================================================================

MinIO Python SDK wrapper for storing agent-generated documents.
This is the one non-LangChain utility — no LangChain integration exists
for object storage.

=============================================================================
"""

import os
import io
from minio import Minio

_minio_client = None


def get_minio_client() -> Minio:
    """
    Get the shared MinIO client instance.

    Configuration via environment variables:
    - MINIO_ENDPOINT: MinIO server endpoint (default: localhost:9000)
    - MINIO_ACCESS_KEY: Access key (default: minioadmin)
    - MINIO_SECRET_KEY: Secret key
    - MINIO_USE_SSL: Whether to use SSL (default: false)
    """
    global _minio_client
    if _minio_client is None:
        _minio_client = Minio(
            endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            secure=os.getenv("MINIO_USE_SSL", "false").lower() == "true",
        )
    return _minio_client


async def upload_to_minio(
    object_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    bucket: str = None,
) -> str:
    """
    Upload data to MinIO.

    Args:
        object_name: Path/name for the object in the bucket
        data: Raw bytes to upload
        content_type: MIME type of the content
        bucket: Bucket name (defaults to MINIO_BUCKET env var)

    Returns:
        The object name/path that was stored
    """
    client = get_minio_client()
    bucket_name = bucket or os.getenv("MINIO_BUCKET", "documents")

    # Ensure bucket exists
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)

    # Upload the data
    data_stream = io.BytesIO(data)
    client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=data_stream,
        length=len(data),
        content_type=content_type,
    )

    return object_name
