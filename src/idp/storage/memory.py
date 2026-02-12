"""In-memory storage backend for testing."""

from idp.models.document import Document
from idp.storage.base import StorageBackend


class MemoryStorage(StorageBackend):
    """In-memory storage backend."""

    def __init__(self) -> None:
        """Initialize memory storage."""
        self._documents: dict[str, Document] = {}

    async def save(self, document: Document) -> str:
        """Save a document to memory."""
        key = document.id
        self._documents[key] = document
        return key

    async def load(self, key: str) -> Document | None:
        """Load a document from memory."""
        return self._documents.get(key)

    async def delete(self, key: str) -> bool:
        """Delete a document from memory."""
        if key in self._documents:
            del self._documents[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        """Check if a document exists in memory."""
        return key in self._documents

    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys in memory."""
        if prefix:
            return [k for k in self._documents if k.startswith(prefix)]
        return list(self._documents.keys())

    def clear(self) -> None:
        """Clear all documents from memory."""
        self._documents.clear()
