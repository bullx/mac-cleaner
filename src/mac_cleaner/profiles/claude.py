from __future__ import annotations

from pathlib import Path

from mac_cleaner.domain.models import Category

PROFILE_NAME = "Claude"
BUNDLE_IDS = frozenset({"com.anthropic.claudefordesktop"})
NAME_HINTS = frozenset({"claude"})


def matches(bundle_id: str, app_name: str = "") -> bool:
    if bundle_id in BUNDLE_IDS:
        return True
    return app_name.strip().lower() in NAME_HINTS


def extra_paths() -> list[dict]:
    home = Path.home()
    lib = home / "Library"
    return [
        {
            "path": Path("/Applications/Claude.app"),
            "category": Category.APP,
            "note": "Claude Desktop application bundle",
            "selected": True,
        },
        {
            "path": home / "Applications" / "Claude.app",
            "category": Category.APP,
            "note": "Claude Desktop (user Applications)",
            "selected": True,
        },
        {
            "path": lib / "Application Support" / "Claude",
            "category": Category.SUPPORT,
            "note": "Claude data including vm_bundles / Claude Code (often multi-GB)",
            "selected": True,
        },
        {
            "path": home / ".claude",
            "category": Category.PROFILE,
            "note": "Claude Code CLI home",
            "selected": True,
        },
        {
            "path": home / ".claude.json",
            "category": Category.PROFILE,
            "note": "Claude Code global config",
            "selected": True,
        },
        {
            "path": home / ".local" / "bin" / "claude",
            "category": Category.PROFILE,
            "note": "Claude Code native binary",
            "selected": True,
        },
        {
            "path": home / ".local" / "share" / "claude",
            "category": Category.PROFILE,
            "note": "Claude Code shared data",
            "selected": True,
        },
        {
            "path": home / "Claude",
            "category": Category.SUPPORT,
            "note": "Claude cowork user files folder",
            "selected": True,
        },
        {
            "path": lib / "Caches" / "com.anthropic.claudefordesktop",
            "category": Category.CACHE,
            "note": "Claude Desktop cache",
            "selected": True,
        },
        {
            "path": lib / "Caches" / "com.anthropic.claudefordesktop.ShipIt",
            "category": Category.CACHE,
            "note": "Claude ShipIt updater cache",
            "selected": True,
        },
        {
            "path": lib / "Caches" / "claude-cli-nodejs",
            "category": Category.CACHE,
            "note": "Claude CLI node cache",
            "selected": True,
        },
        {
            "path": lib / "Preferences" / "com.anthropic.claudefordesktop.plist",
            "category": Category.PREFERENCES,
            "note": "Claude preferences",
            "selected": True,
        },
        {
            "path": lib / "HTTPStorages" / "com.anthropic.claudefordesktop",
            "category": Category.OTHER,
            "note": "Claude HTTP storage",
            "selected": True,
        },
        {
            "path": lib / "Logs" / "Claude",
            "category": Category.LOGS,
            "note": "Claude logs",
            "selected": True,
        },
    ]
