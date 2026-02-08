"""
=============================================================================
STORAGE UTILITIES - Object storage access
=============================================================================

- minio_client.py: MinIO SDK for document artifact storage

=============================================================================
"""

from .minio_client import upload_to_minio, get_minio_client

__all__ = ['upload_to_minio', 'get_minio_client']
