from __future__ import annotations

from pathlib import Path

from mac_cleaner.domain.models import (
    Category,
    Confidence,
    MatchReason,
    RelatedItem,
    Risk,
)
from mac_cleaner.domain.sizes import path_size
from mac_cleaner.infra.macos import tmpdir

from . import claude, codex, cursor


def all_profiles():
    return [cursor, claude, codex]


def items_for_bundle(
    bundle_id: str,
    *,
    app_name: str = "",
    compute_size: bool = True,
) -> list[RelatedItem]:
    items: list[RelatedItem] = []
    for mod in all_profiles():
        if not mod.matches(bundle_id, app_name):
            continue
        for spec in mod.extra_paths():
            path = Path(spec["path"]).expanduser()
            if not path.exists():
                continue
            size = path_size(path) if compute_size else 0
            items.append(
                RelatedItem(
                    path=path,
                    category=spec.get("category", Category.PROFILE),
                    reason=MatchReason.PROFILE,
                    confidence=Confidence.HIGH,
                    risk=spec.get("risk", Risk.SAFE),
                    size_bytes=size,
                    size_pending=not compute_size,
                    selected=spec.get("selected", True),
                    note=spec.get("note", "Deep profile match"),
                    locked=spec.get("locked", False),
                )
            )
    return _dedupe(items)


def orphan_profile_items(*, compute_size: bool = True) -> list[RelatedItem]:
    """Surfaces profile leftovers even when the .app is gone."""
    items: list[RelatedItem] = []
    for mod in all_profiles():
        for spec in mod.extra_paths():
            path = Path(spec["path"]).expanduser()
            if not path.exists():
                continue
            # Skip the .app itself for orphan mode
            if path.suffix == ".app":
                continue
            size = path_size(path) if compute_size else 0
            items.append(
                RelatedItem(
                    path=path,
                    category=spec.get("category", Category.PROFILE),
                    reason=MatchReason.PROFILE,
                    confidence=Confidence.HIGH,
                    risk=spec.get("risk", Risk.SAFE),
                    size_bytes=size,
                    size_pending=not compute_size,
                    selected=False,
                    note=f"{mod.PROFILE_NAME}: {spec.get('note', 'profile leftover')}",
                    locked=False,
                )
            )
    return _dedupe(items)


def _dedupe(items: list[RelatedItem]) -> list[RelatedItem]:
    seen: set[str] = set()
    out: list[RelatedItem] = []
    for item in items:
        key = str(item.path.resolve()) if item.path.exists() else str(item.path)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


__all__ = ["items_for_bundle", "orphan_profile_items", "tmpdir", "all_profiles"]
