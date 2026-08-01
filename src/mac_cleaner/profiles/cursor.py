from __future__ import annotations

import os
from pathlib import Path

from mac_cleaner.domain.models import Category, Risk

PROFILE_NAME = "Cursor"
BUNDLE_IDS = frozenset({"com.todesktop.230313mzl4w4u92"})
NAME_HINTS = frozenset({"cursor"})


def matches(bundle_id: str, app_name: str = "") -> bool:
    if bundle_id in BUNDLE_IDS:
        return True
    return app_name.strip().lower() in NAME_HINTS


def extra_paths() -> list[dict]:
    home = Path.home()
    lib = home / "Library"
    tmp = Path(os.environ.get("TMPDIR") or "/tmp")
    return [
        {
            "path": Path("/Applications/Cursor.app"),
            "category": Category.APP,
            "note": "Cursor application bundle",
            "selected": True,
        },
        {
            "path": home / "Applications" / "Cursor.app",
            "category": Category.APP,
            "note": "Cursor application bundle (user Applications)",
            "selected": True,
        },
        {
            "path": lib / "Application Support" / "Cursor",
            "category": Category.SUPPORT,
            "note": "Cursor user data (settings, extensions cache, agent data)",
            "selected": True,
        },
        {
            "path": home / ".cursor",
            "category": Category.PROFILE,
            "note": "Cursor CLI / agent / extensions home",
            "selected": True,
        },
        {
            "path": lib / "Caches" / "com.todesktop.230313mzl4w4u92",
            "category": Category.CACHE,
            "note": "Cursor ToDesktop cache",
            "selected": True,
        },
        {
            "path": lib / "Caches" / "com.todesktop.230313mzl4w4u92.ShipIt",
            "category": Category.CACHE,
            "note": "Cursor ShipIt updater cache",
            "selected": True,
        },
        {
            "path": lib / "Caches" / "cursor-compile-cache",
            "category": Category.CACHE,
            "note": "Cursor compile cache",
            "selected": True,
        },
        {
            "path": lib / "Caches" / "cursor-updater",
            "category": Category.CACHE,
            "note": "Cursor updater cache",
            "selected": True,
        },
        {
            "path": lib / "Application Support" / "cursor-updater",
            "category": Category.SUPPORT,
            "note": "Cursor updater support",
            "selected": True,
        },
        {
            "path": lib / "Preferences" / "com.todesktop.230313mzl4w4u92.plist",
            "category": Category.PREFERENCES,
            "note": "Cursor preferences",
            "selected": True,
        },
        {
            "path": lib / "HTTPStorages" / "com.todesktop.230313mzl4w4u92",
            "category": Category.OTHER,
            "note": "Cursor HTTP storage",
            "selected": True,
        },
        {
            "path": lib / "Logs" / "Cursor",
            "category": Category.LOGS,
            "note": "Cursor logs",
            "selected": True,
        },
        {
            "path": tmp / "cursor-sandbox-cache",
            "category": Category.CACHE,
            "note": "Cursor agent sandbox cache (TMPDIR)",
            "selected": True,
        },
        {
            "path": tmp / "cursor-agent-logs-501",
            "category": Category.LOGS,
            "note": "Cursor agent logs (TMPDIR)",
            "selected": True,
        },
        # Explicitly do NOT include Application Support/Code (VS Code).
    ]
