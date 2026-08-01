from __future__ import annotations

import re
from pathlib import Path

from mac_cleaner.domain.models import (
    AppInfo,
    Category,
    Confidence,
    MatchReason,
    RelatedItem,
    Risk,
)
from mac_cleaner.domain.rules import (
    is_apple_bundle_id,
    is_name_token_allowed,
    is_shared_vendor_folder,
    library_roots,
)
from mac_cleaner.domain.sizes import path_size
from mac_cleaner.profiles import items_for_bundle
from mac_cleaner.scanners.library_index import LibraryIndex, get_library_index


def _category_for_root_key(key: str) -> Category:
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
        "internet_plugins": Category.OTHER,
        "preference_panes": Category.OTHER,
        "services": Category.OTHER,
        "launch_daemons": Category.AGENTS,
        "privileged_helpers": Category.AGENTS,
    }.get(key, Category.OTHER)


def _bundle_matches_name(entry_name: str, bundle_id: str) -> MatchReason | None:
    if not bundle_id:
        return None
    stem = entry_name
    for suffix in (".plist", ".savedState", ".binarycookies", ".ShipIt"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    if stem == bundle_id or stem.startswith(bundle_id + "."):
        return MatchReason.EXACT_BUNDLE
    if bundle_id.startswith(stem) and len(stem) >= 8:
        return MatchReason.BUNDLE_PREFIX
    if stem.startswith(bundle_id + ".") or entry_name.startswith(bundle_id):
        return MatchReason.EXACT_BUNDLE
    return None


def _name_match(entry_name: str, app_name: str) -> bool:
    if not is_name_token_allowed(app_name):
        return False
    stem = entry_name
    if stem.endswith(".plist"):
        stem = stem[:-6]
    if stem.endswith(".savedState"):
        stem = stem[: -len(".savedState")]
    return stem.lower() == app_name.lower()


def _make_item(
    path: Path,
    *,
    category: Category,
    reason: MatchReason,
    confidence: Confidence,
    risk: Risk,
    selected: bool,
    note: str,
    locked: bool = False,
    compute_size: bool = True,
) -> RelatedItem:
    pending = not compute_size
    size = path_size(path) if compute_size else 0
    return RelatedItem(
        path=path,
        category=category,
        reason=reason,
        confidence=confidence,
        risk=risk,
        size_bytes=size,
        size_pending=pending,
        selected=selected and not locked,
        note=note,
        locked=locked,
    )


def _classify_entry(
    name: str,
    *,
    category: Category,
    bundle_id: str,
    app_name: str,
    locked: bool,
) -> tuple[MatchReason, Confidence, Risk, bool, str] | None:
    reason = _bundle_matches_name(name, bundle_id) if bundle_id else None
    name_hit = _name_match(name, app_name) if app_name else False
    if reason is None and not name_hit:
        return None
    if reason is None and name_hit:
        reason = MatchReason.NAME_MATCH

    is_group = category == Category.GROUP_CONTAINERS
    is_shared = is_shared_vendor_folder(name)
    if is_apple_bundle_id(name) or name.startswith("com.apple."):
        return None

    if is_group or is_shared or reason == MatchReason.NAME_MATCH:
        return (
            MatchReason.SHARED_CAUTION if (is_group or is_shared) else reason,
            Confidence.MEDIUM,
            Risk.CAUTION,
            False,
            (
                "Shared / group container — review before deleting"
                if (is_group or is_shared)
                else f"Name match on “{app_name}” — review before deleting"
            ),
        )
    if reason in (MatchReason.EXACT_BUNDLE, MatchReason.BUNDLE_PREFIX):
        return (
            reason,
            Confidence.HIGH,
            Risk.LOCKED if locked else Risk.SAFE,
            not locked,
            f"Bundle ID match: {bundle_id}",
        )
    return None


def _match_rank(item: RelatedItem) -> int:
    reason_score = {
        MatchReason.PROFILE: 40,
        MatchReason.EXACT_BUNDLE: 30,
        MatchReason.BUNDLE_PREFIX: 20,
        MatchReason.NAME_MATCH: 10,
        MatchReason.SHARED_CAUTION: 5,
        MatchReason.ORPHAN: 8,
        MatchReason.JUNK: 8,
    }.get(item.reason, 0)
    conf_score = {
        Confidence.HIGH: 3,
        Confidence.MEDIUM: 2,
        Confidence.LOW: 1,
    }.get(item.confidence, 0)
    return reason_score + conf_score + (0 if item.locked else 1)


def find_related_files(
    app: AppInfo,
    *,
    compute_size: bool = True,
    include_app_bundle: bool = True,
    library_index: LibraryIndex | None = None,
) -> list[RelatedItem]:
    items: list[RelatedItem] = []
    index: dict[str, int] = {}
    lib_index = library_index or get_library_index()

    def add(item: RelatedItem) -> None:
        try:
            key = str(item.path.resolve())
        except OSError:
            key = str(item.path)
        if key in index:
            existing = items[index[key]]
            if _match_rank(item) > _match_rank(existing):
                if item.size_bytes == 0 and existing.size_bytes > 0:
                    item.size_bytes = existing.size_bytes
                    item.size_pending = existing.size_pending
                items[index[key]] = item
            return
        index[key] = len(items)
        items.append(item)

    if include_app_bundle and app.path.exists():
        add(
            _make_item(
                app.path,
                category=Category.APP,
                reason=MatchReason.EXACT_BUNDLE,
                confidence=Confidence.HIGH,
                risk=Risk.SAFE if not app.protected else Risk.LOCKED,
                selected=not app.protected,
                note="Application bundle",
                locked=app.protected,
                compute_size=compute_size,
            )
        )

    for entry in lib_index.entries:
        category = _category_for_root_key(entry.root_key)
        classified = _classify_entry(
            entry.name,
            category=category,
            bundle_id=app.bundle_id,
            app_name=app.name,
            locked=entry.locked,
        )
        if classified is None:
            continue
        reason, confidence, risk, selected, note = classified
        if entry.locked:
            note = f"{note} (system — locked in v1)"
            risk = Risk.LOCKED
            selected = False
        add(
            _make_item(
                entry.path,
                category=category,
                reason=reason,
                confidence=confidence,
                risk=risk,
                selected=selected,
                note=note,
                locked=entry.locked,
                compute_size=compute_size,
            )
        )

    for item in items_for_bundle(
        app.bundle_id, app_name=app.name, compute_size=compute_size
    ):
        add(item)

    crash = library_roots().get("crash_reporter")
    if crash and crash.exists() and is_name_token_allowed(app.name):
        try:
            pattern = re.compile(re.escape(app.name) + r"_", re.IGNORECASE)
            for entry in crash.iterdir():
                if pattern.match(entry.name):
                    add(
                        _make_item(
                            entry,
                            category=Category.OTHER,
                            reason=MatchReason.NAME_MATCH,
                            confidence=Confidence.MEDIUM,
                            risk=Risk.CAUTION,
                            selected=False,
                            note="CrashReporter leftover",
                            compute_size=compute_size,
                        )
                    )
        except OSError:
            pass

    items.sort(
        key=lambda i: (
            i.category.value,
            0 if i.size_pending else 1,
            -i.size_bytes,
            str(i.path),
        )
    )
    return items
