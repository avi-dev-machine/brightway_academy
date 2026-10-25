"""Storage backends: Supabase Storage (private buckets) and a local-disk backend for development."""

import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

import httpx

from app.exceptions import ConflictError, ExternalServiceError, NotFoundError

logger = logging.getLogger(__name__)

_SAFE_PATH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
_SAFE_BUCKET = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")


def validate_object_path(bucket: str, path: str) -> None:
    if not _SAFE_BUCKET.match(bucket):
        raise ValueError(f"Unsafe bucket name: {bucket!r}")
    segments = path.split("/")
    if not _SAFE_PATH.match(path) or ".." in segments or "" in segments:
        raise ValueError(f"Unsafe storage path: {path!r}")


class StorageBackend(Protocol):
    name: str

    def upload(
        self, bucket: str, path: str, data: bytes, content_type: str, upsert: bool
    ) -> None: ...

    def download(self, bucket: str, path: str) -> bytes: ...

    def ping(self) -> None: ...

    def close(self) -> None: ...


class SupabaseStorageBackend:
    name = "supabase"

    def __init__(
        self,
        supabase_url: str,
        service_key: str,
        *,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not supabase_url or not service_key:
            raise ValueError(
                "Supabase Storage requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
            )
        self._http = httpx.Client(
            base_url=f"{supabase_url.rstrip('/')}/storage/v1",
            headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
            timeout=timeout,
            transport=transport,
        )

    def upload(self, bucket: str, path: str, data: bytes, content_type: str, upsert: bool) -> None:
        response = self._request(
            "POST",
            f"/object/{bucket}/{quote(path)}",
            content=data,
            headers={"Content-Type": content_type, "x-upsert": "true" if upsert else "false"},
        )
        if response.status_code in (200, 201):
            return
        if response.status_code == 409 or "duplicate" in response.text.lower():
            raise ConflictError("A file already exists at this location.", code="FILE_EXISTS")
        raise self._failure("upload", response)

    def download(self, bucket: str, path: str) -> bytes:
        response = self._request("GET", f"/object/authenticated/{bucket}/{quote(path)}")
        if response.status_code == 200:
            return response.content
        if response.status_code == 404 or (
            response.status_code == 400 and "not found" in response.text.lower()
        ):
            raise NotFoundError("File was not found.", code="FILE_NOT_FOUND")
        raise self._failure("download", response)

    def ping(self) -> None:
        response = self._request("GET", "/bucket")
        if response.status_code != 200:
            raise self._failure("ping", response)

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        try:
            return self._http.request(method, url, **kwargs)  # type: ignore[arg-type]
        except httpx.HTTPError as exc:
            logger.error("storage request failed", extra={"error_type": type(exc).__name__})
            raise ExternalServiceError("File storage is unavailable.") from exc

    @staticmethod
    def _failure(action: str, response: httpx.Response) -> ExternalServiceError:
        logger.error(
            "storage request rejected",
            extra={"storage_action": action, "status_code": response.status_code},
        )
        return ExternalServiceError("File storage rejected the request.")


class LocalStorageBackend:
    """Stores objects under `root/<bucket>/<path>`. For development and tests only."""

    name = "local"

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def _resolve(self, bucket: str, path: str) -> Path:
        target = (self._root / bucket / path).resolve()
        if not target.is_relative_to(self._root):
            raise ValueError("Storage path escapes the storage root.")
        return target

    def upload(self, bucket: str, path: str, data: bytes, content_type: str, upsert: bool) -> None:
        target = self._resolve(bucket, path)
        if target.exists() and not upsert:
            raise ConflictError("A file already exists at this location.", code="FILE_EXISTS")
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".upload-")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            os.replace(tmp_name, target)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise

    def download(self, bucket: str, path: str) -> bytes:
        target = self._resolve(bucket, path)
        if not target.is_file():
            raise NotFoundError("File was not found.", code="FILE_NOT_FOUND")
        return target.read_bytes()

    def ping(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        return None
