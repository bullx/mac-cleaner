from __future__ import annotations

import os
import subprocess
from pathlib import Path


def is_app_running(app_path: Path | None = None, bundle_id: str = "") -> bool:
    if bundle_id:
        try:
            result = subprocess.run(
                ["pgrep", "-f", bundle_id],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return True
        except (OSError, subprocess.SubprocessError):
            pass
    if app_path is not None:
        name = app_path.stem
        try:
            result = subprocess.run(
                ["pgrep", "-x", name],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return True
        except (OSError, subprocess.SubprocessError):
            pass
    return False


def quit_app(app_name: str, *, force: bool = False) -> bool:
    """Ask the app to quit via AppleScript. Returns True if quit succeeded."""
    verb = "quit" if not force else "quit"
    script = f'tell application "{app_name}" to {verb}'
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def open_full_disk_access_settings() -> None:
    # Opens Privacy & Security → Full Disk Access on modern macOS.
    url = (
        "x-apple.systempreferences:com.apple.preference.security"
        "?Privacy_AllFiles"
    )
    try:
        subprocess.run(["open", url], check=False, timeout=5)
    except (OSError, subprocess.SubprocessError):
        try:
            subprocess.run(
                ["open", "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension"],
                check=False,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            pass


def can_list_containers() -> bool:
    """Heuristic: Full Disk Access often required to list Containers fully."""
    containers = Path.home() / "Library" / "Containers"
    try:
        if not containers.exists():
            return True
        # Try listing a few entries; TCC may return empty or raise.
        next(containers.iterdir(), None)
        # Attempt reading a known protected-ish path marker.
        for child in containers.iterdir():
            try:
                next(child.iterdir(), None)
                return True
            except PermissionError:
                return False
            except OSError:
                continue
        return True
    except PermissionError:
        return False
    except OSError:
        return False


def tmpdir() -> Path:
    return Path(os.environ.get("TMPDIR") or "/tmp")


def reveal_in_finder(path: Path) -> None:
    """Reveal a file/folder in Finder."""
    try:
        target = path if path.exists() else path.parent
        subprocess.run(["open", "-R", str(target)], check=False, timeout=5)
    except (OSError, subprocess.SubprocessError):
        try:
            subprocess.run(["open", str(path.parent)], check=False, timeout=5)
        except (OSError, subprocess.SubprocessError):
            pass
