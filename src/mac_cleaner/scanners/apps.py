from __future__ import annotations

from pathlib import Path

from mac_cleaner.domain.models import AppInfo
from mac_cleaner.domain.sizes import path_size
from mac_cleaner.infra.plist import (
    bundle_id_from_app,
    display_name_from_app,
    icon_path_from_app,
    version_from_app,
)

APP_SEARCH_DIRS = (
    Path("/Applications"),
    Path.home() / "Applications",
)

SYSTEM_APP_DIR = Path("/System/Applications")


def iter_app_bundles(roots: tuple[Path, ...] | None = None) -> list[Path]:
    found: list[Path] = []
    for root in roots or APP_SEARCH_DIRS:
        if not root.exists():
            continue
        try:
            for child in root.iterdir():
                if child.suffix == ".app" and child.is_dir():
                    found.append(child)
                elif child.is_dir() and not child.name.startswith("."):
                    # One level of nesting (e.g. Utilities)
                    try:
                        for nested in child.iterdir():
                            if nested.suffix == ".app" and nested.is_dir():
                                found.append(nested)
                    except OSError:
                        continue
        except OSError:
            continue
    return sorted(found, key=lambda p: p.name.lower())


def scan_installed_apps(
    *,
    compute_size: bool = False,
    include_system: bool = False,
) -> list[AppInfo]:
    roots = list(APP_SEARCH_DIRS)
    if include_system and SYSTEM_APP_DIR.exists():
        roots.append(SYSTEM_APP_DIR)

    apps: list[AppInfo] = []
    for path in iter_app_bundles(tuple(roots)):
        protected = str(path).startswith("/System/")
        bundle_id = bundle_id_from_app(path)
        name = display_name_from_app(path)
        apps.append(
            AppInfo(
                name=name,
                path=path,
                bundle_id=bundle_id,
                version=version_from_app(path),
                icon_path=icon_path_from_app(path),
                size_bytes=path_size(path) if compute_size else 0,
                protected=protected,
            )
        )
    apps.sort(key=lambda a: a.name.lower())
    return apps


def installed_bundle_ids(apps: list[AppInfo] | None = None) -> set[str]:
    if apps is None:
        apps = scan_installed_apps(compute_size=False)
    return {a.bundle_id for a in apps if a.bundle_id}
