"""Base storage backend interface."""

from abc import ABC, abstractmethod

from idp.models.document import Document


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def save(self, document: Document) -> str:
        """Save a document and return its storage key.

        Args:
            document: Document to save

        Returns:
            Storage key for the document
        """
        ...

    @abstractmethod
    async def load(self, key: str) -> Document | None:
        """Load a document by its storage key.

        Args:
            key: Storage key

        Returns:
            Document if found, None otherwise
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a document by its storage key.

        Args:
            key: Storage key

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a document exists.

        Args:
            key: Storage key

        Returns:
            True if exists, False otherwise
        """
        ...

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all storage keys with optional prefix filter.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            List of storage keys
        """
        ...
