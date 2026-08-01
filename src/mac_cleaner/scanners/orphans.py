from __future__ import annotations

from pathlib import Path

from mac_cleaner.domain.models import (
    Category,
    Confidence,
    MatchReason,
    RelatedItem,
    Risk,
)
from mac_cleaner.domain.rules import is_apple_bundle_id
from mac_cleaner.domain.sizes import path_size
from mac_cleaner.profiles import orphan_profile_items
from mac_cleaner.scanners.apps import installed_bundle_ids
from mac_cleaner.scanners.library_index import LibraryIndex, get_library_index


BUNDLE_LIKE = frozenset(
    {
        "preferences",
        "preferences_byhost",
        "caches",
        "containers",
        "saved_state",
        "http_storages",
        "webkit",
        "cookies",
        "application_scripts",
        "launch_agents",
    }
)


def _looks_like_bundle_id(name: str) -> str | None:
    stem = name
    for suffix in (".plist", ".savedState", ".binarycookies"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    parts = stem.split(".")
    if len(parts) >= 3 and parts[0] in {"com", "org", "net", "io", "co", "app"}:
        if len(parts[-1]) >= 8 and all(c in "0123456789abcdefABCDEF-" for c in parts[-1]):
            if len(parts) > 3:
                stem = ".".join(parts[:-1])
        return stem
    return None


def _category_for_key(key: str) -> Category:
    return {
        "application_support": Category.SUPPORT,
        "caches": Category.CACHE,
        "preferences": Category.PREFERENCES,
        "preferences_byhost": Category.PREFERENCES,
        "containers": Category.CONTAINERS,
        "group_containers": Category.GROUP_CONTAINERS,
        "saved_state": Category.STATE,
        "logs": Category.LOGS,
        "http_storages": Category.OTHER,
        "webkit": Category.OTHER,
        "cookies": Category.OTHER,
        "launch_agents": Category.AGENTS,
        "application_scripts": Category.OTHER,
        "crash_reporter": Category.OTHER,
    }.get(key, Category.OTHER)


def scan_orphans(
    *,
    compute_size: bool = True,
    library_index: LibraryIndex | None = None,
) -> list[RelatedItem]:
    owned = installed_bundle_ids()
    items: list[RelatedItem] = []
    seen: set[str] = set()
    lib_index = library_index or get_library_index()

    def add(item: RelatedItem) -> None:
        try:
            key = str(item.path.resolve())
        except OSError:
            key = str(item.path)
        if key in seen:
            return
        seen.add(key)
        items.append(item)

    for entry in lib_index.entries:
        if entry.locked:
            continue
        if entry.root_key not in BUNDLE_LIKE:
            continue
        bid = _looks_like_bundle_id(entry.name)
        if not bid or is_apple_bundle_id(bid):
            continue
        if any(bid == o or bid.startswith(o + ".") or o.startswith(bid + ".") for o in owned):
            continue
        add(
            RelatedItem(
                path=entry.path,
                category=_category_for_key(entry.root_key),
                reason=MatchReason.ORPHAN,
                confidence=Confidence.MEDIUM,
                risk=Risk.CAUTION if entry.root_key == "group_containers" else Risk.SAFE,
                size_bytes=path_size(entry.path) if compute_size else 0,
                size_pending=not compute_size,
                selected=False,
                note=f"No installed app owns bundle ID “{bid}”",
            )
        )

    for item in orphan_profile_items(compute_size=compute_size):
        note = item.note.lower()
        if "cursor" in note and Path("/Applications/Cursor.app").exists():
            continue
        if "claude" in note and Path("/Applications/Claude.app").exists():
            continue
        if ("codex" in note or "chatgpt" in note or "openai" in note) and (
            Path("/Applications/ChatGPT.app").exists()
            or Path("/Applications/Codex.app").exists()
        ):
            continue
        item.reason = MatchReason.ORPHAN
        item.selected = False
        if not compute_size:
            item.size_pending = True
        add(item)

    items.sort(
        key=lambda i: (0 if i.size_pending else 1, -i.size_bytes, str(i.path))
    )
    return items
