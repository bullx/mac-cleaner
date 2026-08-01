from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from send2trash import send2trash


def move_to_trash(path: Path) -> None:
    send2trash(str(path))


def default_log_dir() -> Path:
    d = Path.home() / "Library" / "Logs" / "AppUnload"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_deletion_manifest(
    paths: list[Path],
    *,
    label: str = "",
    log_dir: Path | None = None,
) -> Path:
    directory = log_dir or default_log_dir()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = directory / f"deletion-{stamp}.json"
    payload = {
        "timestamp": stamp,
        "label": label,
        "paths": [str(p) for p in paths],
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out
