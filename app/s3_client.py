"""Thin boto3 S3 wrapper.

The frontend never sees AWS credentials. The backend issues short-lived presigned
URLs so the browser PUTs/GETs bytes directly against S3, and proxies the metadata
operations (list, delete, copy, folder markers) itself.
"""
from functools import lru_cache
from typing import Any

import boto3
from botocore.client import Config
from fastapi import HTTPException

from app.config import get_settings

# Presigned URL lifetime (seconds).
PUT_TTL = 900
GET_TTL = 900


@lru_cache(maxsize=1)
def _client():
    settings = get_settings()
    if not settings.s3_bucket:
        raise HTTPException(status_code=503, detail="S3 storage is not configured")
    # Use the regional endpoint so presigned URLs are region-correct. The global
    # `s3.amazonaws.com` host 301-redirects buckets outside us-east-1 — boto follows
    # that server-side, but a browser presigned PUT/GET drops auth across the redirect.
    endpoint = settings.s3_endpoint_url or f"https://s3.{settings.aws_region}.amazonaws.com"
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        endpoint_url=endpoint,
        config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
    )


def _bucket() -> str:
    bucket = get_settings().s3_bucket
    if not bucket:
        raise HTTPException(status_code=503, detail="S3 storage is not configured")
    return bucket


def presign_put(key: str, content_type: str) -> str:
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": _bucket(), "Key": key, "ContentType": content_type},
        ExpiresIn=PUT_TTL,
    )


def presign_get(key: str, download_name: str | None = None) -> str:
    params: dict[str, Any] = {"Bucket": _bucket(), "Key": key}
    if download_name:
        params["ResponseContentDisposition"] = f'attachment; filename="{download_name}"'
    return _client().generate_presigned_url(
        "get_object", Params=params, ExpiresIn=GET_TTL
    )


def list_prefix(prefix: str) -> dict[str, list]:
    """List a single folder level under `prefix` using a `/` delimiter.

    Returns {"folders": [name, ...], "files": [{key, size, last_modified, content_type}]}.
    The zero-byte folder-marker object (key == prefix) is filtered out of files.
    """
    resp = _client().list_objects_v2(
        Bucket=_bucket(), Prefix=prefix, Delimiter="/"
    )
    folders = [cp["Prefix"] for cp in resp.get("CommonPrefixes", [])]
    files = []
    for obj in resp.get("Contents", []):
        if obj["Key"] == prefix:  # folder marker
            continue
        files.append(
            {
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": int(obj["LastModified"].timestamp() * 1000),
            }
        )
    return {"folders": folders, "files": files}


def put_empty(key: str) -> None:
    """Create a zero-byte object — used as a folder marker."""
    _client().put_object(Bucket=_bucket(), Key=key, Body=b"")


def delete_key(key: str) -> None:
    _client().delete_object(Bucket=_bucket(), Key=key)


def delete_prefix(prefix: str) -> int:
    """Delete every object under `prefix`. Returns count deleted."""
    client = _client()
    bucket = _bucket()
    deleted = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objs = [{"Key": o["Key"]} for o in page.get("Contents", [])]
        if objs:
            client.delete_objects(Bucket=bucket, Delete={"Objects": objs})
            deleted += len(objs)
    return deleted


def copy_key(src: str, dst: str) -> None:
    _client().copy_object(
        Bucket=_bucket(), CopySource={"Bucket": _bucket(), "Key": src}, Key=dst
    )


def copy_prefix(src_prefix: str, dst_prefix: str) -> int:
    """Copy every object under src_prefix to dst_prefix (preserving sub-paths)."""
    client = _client()
    bucket = _bucket()
    copied = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=src_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            dst = dst_prefix + key[len(src_prefix):]
            client.copy_object(
                Bucket=bucket, CopySource={"Bucket": bucket, "Key": key}, Key=dst
            )
            copied += 1
    return copied


def head_key(key: str) -> dict | None:
    try:
        resp = _client().head_object(Bucket=_bucket(), Key=key)
        return {"size": resp["ContentLength"], "content_type": resp.get("ContentType")}
    except _client().exceptions.ClientError:
        return None
