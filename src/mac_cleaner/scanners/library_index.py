from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from mac_cleaner.domain.rules import library_roots, system_library_roots


@dataclass(slots=True)
class IndexEntry:
    path: Path
    name: str
    root_key: str
    locked: bool = False


@dataclass
class LibraryIndex:
    """Flat listing of top-level entries under Library roots."""

    entries: list[IndexEntry] = field(default_factory=list)
    by_name: dict[str, list[IndexEntry]] = field(default_factory=dict)

    def entries_for_root(self, key: str) -> list[IndexEntry]:
        return [e for e in self.entries if e.root_key == key]


_INDEX: LibraryIndex | None = None


def clear_library_index() -> None:
    global _INDEX
    _INDEX = None


def build_library_index(*, include_system: bool = True) -> LibraryIndex:
    entries: list[IndexEntry] = []
    by_name: dict[str, list[IndexEntry]] = {}

    def ingest(roots: dict[str, Path], *, locked: bool) -> None:
        for key, root in roots.items():
            if not root.exists():
                continue
            try:
                children = list(root.iterdir())
            except OSError:
                continue
            for child in children:
                if child.name.startswith("."):
                    continue
                entry = IndexEntry(
                    path=child, name=child.name, root_key=key, locked=locked
                )
                entries.append(entry)
                by_name.setdefault(child.name.lower(), []).append(entry)

    ingest(library_roots(), locked=False)
    if include_system:
        ingest(system_library_roots(), locked=True)

    return LibraryIndex(entries=entries, by_name=by_name)


def get_library_index(*, refresh: bool = False) -> LibraryIndex:
    global _INDEX
    if _INDEX is None or refresh:
        _INDEX = build_library_index()
    return _INDEX
