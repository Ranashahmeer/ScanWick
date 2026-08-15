"""S3-compatible file storage abstraction.

Two backends: a local filesystem backend for dev (no infra required), and an
S3 backend that works against either real AWS S3 (prod) or a MinIO endpoint
(dev), since MinIO speaks the same S3 API and only needs s3_endpoint_url set.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath

import boto3
from botocore.client import Config as BotoConfig

from app.config import settings


class FileStorage(ABC):
    @abstractmethod
    def upload_file(self, path: str, data: bytes) -> str:
        """Store `data` under `path` and return a URL to retrieve it."""

    @abstractmethod
    def get_file_url(self, key: str) -> str:
        """Return a URL to retrieve the object already stored at `key`."""

    @abstractmethod
    def download_file(self, key: str) -> bytes:
        """Read back the raw bytes stored at `key`. Used by the Celery
        ingestion tasks to read a staged upload (audit #12) — with the S3
        backend, this is what actually lets the API process (which stages
        the file) and the Celery worker process (which reads it back) see
        the same object even when they're different containers/replicas
        with no shared local filesystem."""

    @abstractmethod
    def delete_file(self, key: str) -> None:
        """Delete the object at `key`, if it exists. Used once an ingestion
        task has finished reading a staged upload (audit #16) — staged
        files were previously never cleaned up."""


class LocalFileStorage(FileStorage):
    def __init__(self, base_dir: str, base_url: str):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url.rstrip("/")

    def _resolve(self, key: str) -> Path:
        # Reject absolute paths and traversal outside base_dir up front —
        # the key may end up containing a user-supplied filename.
        if PurePosixPath(key).is_absolute() or ".." in PurePosixPath(key).parts:
            raise ValueError(f"Invalid storage key: {key!r}")
        dest = (self.base_dir / key).resolve()
        if self.base_dir not in dest.parents and dest != self.base_dir:
            raise ValueError(f"Invalid storage key: {key!r}")
        return dest

    def upload_file(self, path: str, data: bytes) -> str:
        dest = self._resolve(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return self.get_file_url(path)

    def get_file_url(self, key: str) -> str:
        return f"{self.base_url}/static/uploads/{key}"

    def download_file(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def delete_file(self, key: str) -> None:
        self._resolve(key).unlink(missing_ok=True)


class S3FileStorage(FileStorage):
    def __init__(
        self,
        bucket: str,
        region: str,
        endpoint_url: str | None,
        access_key: str,
        secret_key: str,
        expiry_seconds: int,
    ):
        client_kwargs: dict = {"region_name": region}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if access_key and secret_key:
            client_kwargs["aws_access_key_id"] = access_key
            client_kwargs["aws_secret_access_key"] = secret_key

        self.client = boto3.client(
            "s3", config=BotoConfig(signature_version="s3v4"), **client_kwargs
        )
        self.bucket = bucket
        self.expiry_seconds = expiry_seconds
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Auto-create the bucket for dev/MinIO. In real prod S3 this is a
        no-op if the bucket already exists, and is expected to be a no-op
        anyway since prod credentials typically can't create buckets."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self.client.create_bucket(Bucket=self.bucket)
            except Exception:
                pass

    def upload_file(self, path: str, data: bytes) -> str:
        self.client.put_object(Bucket=self.bucket, Key=path, Body=data)
        return self.get_file_url(path)

    def get_file_url(self, key: str) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=self.expiry_seconds,
        )

    def download_file(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def delete_file(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


def build_storage() -> FileStorage:
    if settings.storage_backend == "s3":
        return S3FileStorage(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url or None,
            access_key=settings.s3_access_key_id,
            secret_key=settings.s3_secret_access_key,
            expiry_seconds=settings.s3_presigned_url_expiry_seconds,
        )
    return LocalFileStorage(base_dir=settings.local_storage_dir, base_url=settings.backend_base_url)


storage: FileStorage = build_storage()


def upload_file(path: str, data: bytes) -> str:
    return storage.upload_file(path, data)


def get_file_url(key: str) -> str:
    return storage.get_file_url(key)


def download_file(key: str) -> bytes:
    return storage.download_file(key)


def delete_file(key: str) -> None:
    storage.delete_file(key)
