"""Storage facade used by services. Buckets are private; files are served through the API."""

import logging
from pathlib import Path

from app.config import BACKEND_DIR, Settings
from app.integrations.storage.client import (
    LocalStorageBackend,
    StorageBackend,
    SupabaseStorageBackend,
    validate_object_path,
)
from app.logging import log_operation

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(
        self,
        backend: StorageBackend,
        *,
        photo_bucket: str,
        id_card_bucket: str,
        receipt_bucket: str,
        assets_bucket: str,
    ) -> None:
        self._backend = backend
        self.photo_bucket = photo_bucket
        self.id_card_bucket = id_card_bucket
        self.receipt_bucket = receipt_bucket
        self.assets_bucket = assets_bucket

    @classmethod
    def from_settings(cls, settings: Settings) -> "StorageService":
        backend: StorageBackend
        if settings.resolved_storage_backend == "supabase":
            backend = SupabaseStorageBackend(
                settings.supabase_url, settings.supabase_service_role_key.get_secret_value()
            )
        else:
            root = Path(settings.local_storage_dir)
            backend = LocalStorageBackend(root if root.is_absolute() else BACKEND_DIR / root)
        return cls(
            backend,
            photo_bucket=settings.student_photo_bucket,
            id_card_bucket=settings.id_card_bucket,
            receipt_bucket=settings.receipt_bucket,
            assets_bucket=settings.academy_assets_bucket,
        )

    @property
    def backend_name(self) -> str:
        return self._backend.name

    def upload(
        self, bucket: str, path: str, data: bytes, content_type: str, *, upsert: bool = False
    ) -> str:
        validate_object_path(bucket, path)
        with log_operation(logger, "storage.upload", bucket=bucket, path=path, size=len(data)):
            self._backend.upload(bucket, path, data, content_type, upsert)
        return path

    def download(self, bucket: str, path: str) -> bytes:
        validate_object_path(bucket, path)
        return self._backend.download(bucket, path)

    def ping(self) -> None:
        self._backend.ping()

    def close(self) -> None:
        self._backend.close()
