"""Local filesystem storage backend."""

import json
from pathlib import Path

from idp.core.config import Settings, get_settings
from idp.core.exceptions import StorageError
from idp.models.document import Document
from idp.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(
        self,
        base_path: str | Path | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize local storage.

        Args:
            base_path: Base directory for storage
            settings: Application settings
        """
        settings = settings or get_settings()
        self._base_path = Path(base_path or settings.storage_local_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        """Get the file path for a key."""
        # Sanitize key to prevent path traversal
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self._base_path / f"{safe_key}.json"

    async def save(self, document: Document) -> str:
        """Save a document to the filesystem."""
        key = document.id
        path = self._get_path(key)

        try:
            path.write_text(document.model_dump_json(indent=2))
        except Exception as e:
            raise StorageError(
                f"Failed to save document: {e}",
                details={"key": key, "path": str(path)},
            ) from e

        return key

    async def load(self, key: str) -> Document | None:
        """Load a document from the filesystem."""
        path = self._get_path(key)

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text())
            return Document.model_validate(data)
        except Exception as e:
            raise StorageError(
                f"Failed to load document: {e}",
                details={"key": key, "path": str(path)},
            ) from e

    async def delete(self, key: str) -> bool:
        """Delete a document from the filesystem."""
        path = self._get_path(key)

        if not path.exists():
            return False

        try:
            path.unlink()
            return True
        except Exception as e:
            raise StorageError(
                f"Failed to delete document: {e}",
                details={"key": key, "path": str(path)},
            ) from e

    async def exists(self, key: str) -> bool:
        """Check if a document exists on the filesystem."""
        return self._get_path(key).exists()

    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all document keys in the storage directory."""
        keys = []
        for path in self._base_path.glob("*.json"):
            key = path.stem
            if not prefix or key.startswith(prefix):
                keys.append(key)
        return sorted(keys)
