from __future__ import annotations

import base64
import os
from pathlib import Path, PurePosixPath
from typing import Protocol

import boto3
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import Settings


class ObjectStorage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


class LocalObjectStorage:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        normalized = PurePosixPath(key)
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ValueError("Unsafe storage key")
        target = (self.root / Path(*normalized.parts)).resolve()
        if target != self.root and self.root not in target.parents:
            raise ValueError("Unsafe storage key")
        return target

    def put(self, key: str, data: bytes, content_type: str) -> None:
        del content_type
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        target = self._path(key)
        if target.exists():
            target.unlink()


class S3ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType=content_type
        )

    def get(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


class EncryptedObjectStorage:
    """Authenticated encryption wrapper with transparent legacy reads."""

    MAGIC = b"CHKENC1"
    NONCE_BYTES = 12

    def __init__(self, storage: ObjectStorage, encoded_keys: str) -> None:
        self.storage = storage
        self.keys = self._decode_keys(encoded_keys)
        if not self.keys:
            raise ValueError("At least one valid storage encryption key is required")

    @staticmethod
    def _decode_keys(value: str) -> list[bytes]:
        keys: list[bytes] = []
        for encoded in value.split(","):
            if not encoded.strip():
                continue
            try:
                key = base64.b64decode(encoded.strip(), validate=True)
            except (ValueError, TypeError):
                raise ValueError("Storage encryption keys must be valid base64") from None
            if len(key) != 32:
                raise ValueError("Storage encryption keys must decode to exactly 32 bytes")
            keys.append(key)
        return keys

    def put(self, key: str, data: bytes, content_type: str) -> None:
        nonce = os.urandom(self.NONCE_BYTES)
        encrypted = AESGCM(self.keys[0]).encrypt(nonce, data, key.encode("utf-8"))
        self.storage.put(key, self.MAGIC + nonce + encrypted, "application/octet-stream")

    def get(self, key: str) -> bytes:
        payload = self.storage.get(key)
        if not payload.startswith(self.MAGIC):
            return payload
        nonce_start = len(self.MAGIC)
        nonce_end = nonce_start + self.NONCE_BYTES
        nonce, ciphertext = payload[nonce_start:nonce_end], payload[nonce_end:]
        for encryption_key in self.keys:
            try:
                return AESGCM(encryption_key).decrypt(nonce, ciphertext, key.encode("utf-8"))
            except Exception:
                continue
        raise ValueError("Encrypted object could not be authenticated with configured keys")

    def delete(self, key: str) -> None:
        self.storage.delete(key)


def create_storage(settings: Settings) -> ObjectStorage:
    storage: ObjectStorage
    if settings.storage_backend == "s3":
        storage = S3ObjectStorage(settings)
    else:
        storage = LocalObjectStorage(settings.local_storage_path)
    if settings.storage_encryption_keys.strip():
        return EncryptedObjectStorage(storage, settings.storage_encryption_keys)
    return storage
