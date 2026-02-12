"""Document storage backends."""

from idp.storage.base import StorageBackend
from idp.storage.local import LocalStorage
from idp.storage.memory import MemoryStorage

__all__ = [
    "StorageBackend",
    "LocalStorage",
    "MemoryStorage",
]
