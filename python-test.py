# test_minio.py
import os
from minio import Minio

endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
use_ssl = os.getenv("MINIO_USE_SSL", "false").lower() == "true"

print(f"Endpoint: {endpoint}")
print(f"Access key: {access_key}")
print(f"Secret key: {secret_key[:4]}***")
print(f"SSL: {use_ssl}")

client = Minio(endpoint=endpoint, access_key=access_key, secret_key=secret_key, secure=use_ssl)

try:
    buckets = client.list_buckets()
    print(f"Buckets: {[b.name for b in buckets]}")
except Exception as e:
    print(f"Error: {e}")
