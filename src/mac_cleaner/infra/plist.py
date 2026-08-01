from __future__ import annotations

import plistlib
import subprocess
from pathlib import Path
from typing import Any


def read_plist(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as f:
            data = plistlib.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, plistlib.InvalidFileException, ValueError):
        return {}


def read_app_info(app_path: Path) -> dict[str, Any]:
    """Read CFBundle* keys from an .app Info.plist."""
    info_path = app_path / "Contents" / "Info.plist"
    data = read_plist(info_path)
    if data:
        return data
    # Fallback via plutil for binary edge cases
    try:
        result = subprocess.run(
            ["plutil", "-convert", "json", "-o", "-", str(info_path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout:
            import json

            parsed = json.loads(result.stdout)
            return parsed if isinstance(parsed, dict) else {}
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return {}


def bundle_id_from_app(app_path: Path) -> str:
    info = read_app_info(app_path)
    return str(info.get("CFBundleIdentifier") or "")


def display_name_from_app(app_path: Path) -> str:
    info = read_app_info(app_path)
    name = (
        info.get("CFBundleDisplayName")
        or info.get("CFBundleName")
        or app_path.stem
    )
    return str(name)


def version_from_app(app_path: Path) -> str:
    info = read_app_info(app_path)
    return str(info.get("CFBundleShortVersionString") or info.get("CFBundleVersion") or "")


def icon_path_from_app(app_path: Path) -> Path | None:
    info = read_app_info(app_path)
    icon_name = info.get("CFBundleIconFile")
    if not icon_name:
        return None
    name = str(icon_name)
    if not name.endswith(".icns"):
        name = f"{name}.icns"
    candidate = app_path / "Contents" / "Resources" / name
    return candidate if candidate.exists() else None
