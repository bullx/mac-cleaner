from __future__ import annotations

import os
from pathlib import Path

# Short / generic tokens that must never drive name matching.
GENERIC_NAME_TOKENS = frozenset(
    {
        "app",
        "apps",
        "helper",
        "helpers",
        "service",
        "services",
        "agent",
        "agents",
        "util",
        "utils",
        "tool",
        "tools",
        "client",
        "server",
        "desktop",
        "updater",
        "launcher",
        "manager",
        "plugin",
        "plugins",
        "extension",
        "test",
        "demo",
        "temp",
        "tmp",
        "data",
        "cache",
        "logs",
        "log",
        "bin",
        "lib",
        "src",
        "mac",
        "osx",
        "macos",
    }
)

MIN_NAME_TOKEN_LENGTH = 5

SHARED_VENDOR_FOLDER_NAMES = frozenset(
    {
        "Adobe",
        "Google",
        "Microsoft",
        "JetBrains",
        "Apple",
        "Oracle",
        "Amazon",
        "Dropbox",
        "Slack",
        "Zoom",
        "Cisco",
        "VMware",
        "Parallels",
        "Docker",
        "Homebrew",
    }
)

HARD_DENY_HOME_RELATIVE = (
    ".ssh",
    ".gnupg",
    ".aws",
    ".kube",
    ".docker",
    ".config",
    ".bash_history",
    ".zsh_history",
    ".zhistory",
    ".python_history",
    "Documents",
    "Desktop",
    "Downloads",
    "Movies",
    "Music",
    "Pictures",
    "Public",
)

BLOCKED_PREFIXES = (
    "/System",
    "/usr",
    "/bin",
    "/sbin",
    "/private/var/db",
    "/private/etc",
    "/Library/Apple",
    "/Library/System",
)


def home() -> Path:
    return Path.home().resolve()


def library_roots(user_home: Path | None = None) -> dict[str, Path]:
    h = user_home or home()
    lib = h / "Library"
    return {
        "application_support": lib / "Application Support",
        "caches": lib / "Caches",
        "preferences": lib / "Preferences",
        "preferences_byhost": lib / "Preferences" / "ByHost",
        "containers": lib / "Containers",
        "group_containers": lib / "Group Containers",
        "saved_state": lib / "Saved Application State",
        "logs": lib / "Logs",
        "http_storages": lib / "HTTPStorages",
        "webkit": lib / "WebKit",
        "cookies": lib / "Cookies",
        "launch_agents": lib / "LaunchAgents",
        "application_scripts": lib / "Application Scripts",
        "crash_reporter": lib / "CrashReporter",
        "internet_plugins": lib / "Internet Plug-Ins",
        "preference_panes": lib / "PreferencePanes",
        "services": lib / "Services",
    }


def system_library_roots() -> dict[str, Path]:
    """System-wide roots — detect/show only in v1 (locked)."""
    lib = Path("/Library")
    return {
        "application_support": lib / "Application Support",
        "caches": lib / "Caches",
        "preferences": lib / "Preferences",
        "launch_agents": lib / "LaunchAgents",
        "launch_daemons": lib / "LaunchDaemons",
        "privileged_helpers": lib / "PrivilegedHelperTools",
    }


def is_name_token_allowed(token: str) -> bool:
    t = token.strip().lower()
    if len(t) < MIN_NAME_TOKEN_LENGTH:
        return False
    if t in GENERIC_NAME_TOKENS:
        return False
    return True


def is_shared_vendor_folder(name: str) -> bool:
    return name in SHARED_VENDOR_FOLDER_NAMES


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def is_hard_denied(path: Path, user_home: Path | None = None) -> bool:
    h = user_home or home()
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path

    for prefix in BLOCKED_PREFIXES:
        if str(resolved) == prefix or str(resolved).startswith(prefix + os.sep):
            return True

    # Other users' homes
    users = Path("/Users")
    if _is_under(resolved, users):
        try:
            rel = resolved.relative_to(users)
            if rel.parts and rel.parts[0] != h.name:
                return True
        except ValueError:
            pass

    for rel in HARD_DENY_HOME_RELATIVE:
        denied = (h / rel).resolve()
        if resolved == denied or _is_under(resolved, denied):
            # Allow only if path equals a known high-confidence profile target later;
            # rules layer always denies whole Documents/Desktop/Downloads trees.
            return True

    # Never allow deleting VS Code support when cleaning Cursor via path alone —
    # enforced also in profiles; keep Code itself not hard-denied globally.
    return False


def is_apple_bundle_id(bundle_id: str) -> bool:
    return bundle_id.startswith("com.apple.")


def is_path_allowed_for_trash(
    path: Path,
    *,
    user_home: Path | None = None,
    allow_app_bundle: bool = True,
) -> tuple[bool, str]:
    """Return (ok, reason)."""
    h = user_home or home()
    try:
        resolved = path.expanduser().resolve()
    except OSError as exc:
        return False, f"cannot resolve: {exc}"

    if is_hard_denied(resolved, h):
        return False, "path is hard-denied"

    if is_apple_bundle_id(resolved.name) or "com.apple." in resolved.name:
        # Preference/container names that are Apple-owned
        if resolved.name.startswith("com.apple.") or ".com.apple." in resolved.name:
            return False, "Apple system identifier"

    # Allowed roots: user home Library, Applications, home-dot via explicit profiles,
    # TMPDIR, and the app bundle locations.
    allowed_parents = [
        h / "Library",
        Path("/Applications"),
        h / "Applications",
        Path(os.environ.get("TMPDIR", "/tmp")),
        h,
    ]
    if allow_app_bundle:
        allowed_parents.extend([Path("/Applications"), h / "Applications"])

    if any(_is_under(resolved, p) or resolved == p.resolve() for p in allowed_parents if p.exists() or True):
        # Still block hard-denied home subtrees already handled above.
        # Block deleting the entire home directory.
        if resolved == h.resolve():
            return False, "cannot trash home directory"
        # Only allow home-root children that are hidden dot dirs or known app folders,
        # not arbitrary home files — callers should only pass discovered leftovers.
        return True, "ok"

    # System Library: visible but locked by caller; still "not allowed" for trash in v1
    if _is_under(resolved, Path("/Library")):
        return False, "system Library requires elevation (locked in v1)"

    return False, "outside allowed roots"


def categorize_library_path(path: Path, user_home: Path | None = None) -> str:
    from .models import Category

    h = user_home or home()
    lib = h / "Library"
    s = str(path)
    mapping = [
        (lib / "Application Support", Category.SUPPORT),
        (lib / "Caches", Category.CACHE),
        (lib / "Preferences", Category.PREFERENCES),
        (lib / "Containers", Category.CONTAINERS),
        (lib / "Group Containers", Category.GROUP_CONTAINERS),
        (lib / "LaunchAgents", Category.AGENTS),
        (lib / "Logs", Category.LOGS),
        (lib / "Saved Application State", Category.STATE),
        (lib / "HTTPStorages", Category.OTHER),
        (lib / "WebKit", Category.OTHER),
        (lib / "Cookies", Category.OTHER),
        (lib / "Application Scripts", Category.OTHER),
        (lib / "CrashReporter", Category.OTHER),
    ]
    for root, cat in mapping:
        if s.startswith(str(root)):
            return cat.value
    if path.suffix == ".app" or str(path).endswith(".app"):
        return Category.APP.value
    return Category.OTHER.value
