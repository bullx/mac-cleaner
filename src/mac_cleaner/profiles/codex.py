from __future__ import annotations

from pathlib import Path

from mac_cleaner.domain.models import Category

PROFILE_NAME = "Codex"
BUNDLE_IDS = frozenset(
    {
        "com.openai.codex",
        "com.openai.chat",
        "com.openai.chatgpt",
    }
)
NAME_HINTS = frozenset({"codex", "chatgpt"})


def matches(bundle_id: str, app_name: str = "") -> bool:
    if bundle_id in BUNDLE_IDS:
        return True
    lower = app_name.strip().lower()
    return lower in NAME_HINTS or bundle_id.startswith("com.openai.")


def extra_paths() -> list[dict]:
    home = Path.home()
    lib = home / "Library"
    return [
        {
            "path": Path("/Applications/ChatGPT.app"),
            "category": Category.APP,
            "note": "ChatGPT / Codex desktop app",
            "selected": True,
        },
        {
            "path": Path("/Applications/Codex.app"),
            "category": Category.APP,
            "note": "Codex application bundle",
            "selected": True,
        },
        {
            "path": home / ".codex",
            "category": Category.PROFILE,
            "note": "Codex CLI home (config, auth, sessions)",
            "selected": True,
        },
        {
            "path": home / ".local" / "bin" / "codex",
            "category": Category.PROFILE,
            "note": "Codex CLI binary",
            "selected": True,
        },
        {
            "path": home / ".openai",
            "category": Category.PROFILE,
            "note": "OpenAI home data",
            "selected": True,
        },
        {
            "path": lib / "Application Support" / "Codex",
            "category": Category.SUPPORT,
            "note": "Codex application support",
            "selected": True,
        },
        {
            "path": lib / "Application Support" / "com.openai.chat",
            "category": Category.SUPPORT,
            "note": "ChatGPT application support",
            "selected": True,
        },
        {
            "path": lib / "Application Support" / "ChatGPT",
            "category": Category.SUPPORT,
            "note": "ChatGPT application support",
            "selected": True,
        },
        {
            "path": lib / "Caches" / "com.openai.chat",
            "category": Category.CACHE,
            "note": "ChatGPT cache",
            "selected": True,
        },
        {
            "path": lib / "Caches" / "com.openai.codex",
            "category": Category.CACHE,
            "note": "Codex cache",
            "selected": True,
        },
        {
            "path": lib / "Preferences" / "com.openai.chat.plist",
            "category": Category.PREFERENCES,
            "note": "ChatGPT preferences",
            "selected": True,
        },
        {
            "path": lib / "Preferences" / "com.openai.codex.plist",
            "category": Category.PREFERENCES,
            "note": "Codex preferences",
            "selected": True,
        },
        {
            "path": lib / "Logs" / "Codex",
            "category": Category.LOGS,
            "note": "Codex logs",
            "selected": True,
        },
        {
            "path": lib / "HTTPStorages" / "com.openai.chat",
            "category": Category.OTHER,
            "note": "ChatGPT HTTP storage",
            "selected": True,
        },
    ]
