from __future__ import annotations

import os
from pathlib import Path

from mac_cleaner.domain.models import JunkCategory, Risk
from mac_cleaner.domain.sizes import path_size


def _existing(paths: list[Path]) -> list[Path]:
    return [p for p in paths if p.exists()]


def scan_junk(*, compute_size: bool = True) -> list[JunkCategory]:
    home = Path.home()
    lib = home / "Library"
    tmp = Path(os.environ.get("TMPDIR") or "/tmp")

    categories: list[JunkCategory] = []

    user_cache_root = lib / "Caches"
    cache_paths: list[Path] = []
    if user_cache_root.exists():
        try:
            # Only top-level cache dirs; user selects whole category
            cache_paths = [
                p
                for p in user_cache_root.iterdir()
                if not p.name.startswith(".") and not p.name.startswith("com.apple.")
            ]
        except OSError:
            cache_paths = []

    logs_root = lib / "Logs"
    log_paths: list[Path] = []
    if logs_root.exists():
        try:
            log_paths = [
                p
                for p in logs_root.iterdir()
                if not p.name.startswith(".") and not p.name.startswith("com.apple.")
            ]
        except OSError:
            log_paths = []

    temp_paths = _existing(
        [
            tmp,
            Path("/tmp"),
            home / "Library" / "Caches" / "TemporaryItems",
        ]
    )
    # Don't offer wiping entire TMPDIR — too dangerous. Offer common large regenerable dirs only.
    safe_temp: list[Path] = []
    for p in (tmp, Path("/tmp")):
        if not p.exists():
            continue
        try:
            for child in p.iterdir():
                name = child.name.lower()
                if any(
                    k in name
                    for k in (
                        "cache",
                        "tmp",
                        "temp",
                        "cursor-sandbox",
                        "cursor-agent",
                    )
                ):
                    safe_temp.append(child)
        except OSError:
            continue

    defs = [
        JunkCategory(
            id="user_caches",
            title="User caches",
            description="Regenerable files in ~/Library/Caches (excludes Apple system caches)",
            paths=cache_paths,
            selected=False,
            risk=Risk.CAUTION,
        ),
        JunkCategory(
            id="user_logs",
            title="User logs",
            description="App log folders in ~/Library/Logs (excludes Apple system logs)",
            paths=log_paths,
            selected=False,
            risk=Risk.SAFE,
        ),
        JunkCategory(
            id="temp_caches",
            title="Temporary caches",
            description="Known temp/cache folders under TMPDIR (conservative)",
            paths=safe_temp,
            selected=False,
            risk=Risk.SAFE,
        ),
    ]

    for cat in defs:
        if compute_size:
            cat.size_bytes = sum(path_size(p) for p in cat.paths)
        categories.append(cat)
    return categories
