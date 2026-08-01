from __future__ import annotations

from mac_cleaner.domain.sizes import SizeCache, global_size_cache
from mac_cleaner.scanners.library_index import (
    LibraryIndex,
    clear_library_index,
    get_library_index,
)


class ScanSession:
    """Shared scan state: Library index + size cache."""

    def __init__(self) -> None:
        self.size_cache: SizeCache = global_size_cache()
        self._index: LibraryIndex | None = None

    @property
    def index(self) -> LibraryIndex:
        if self._index is None:
            self._index = get_library_index(refresh=True)
        return self._index

    def refresh_index(self) -> LibraryIndex:
        clear_library_index()
        self._index = get_library_index(refresh=True)
        return self._index

    def invalidate(self) -> None:
        clear_library_index()
        self._index = None
        self.size_cache.clear()
