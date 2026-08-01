from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


CancelCheck = Callable[[], bool]


class CancellationToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def cancelled(self) -> bool:
        return self._event.is_set()

    def check(self) -> None:
        if self._event.is_set():
            raise InterruptedError("cancelled")

    def as_check(self) -> CancelCheck:
        return self.cancelled


@dataclass(frozen=True, slots=True)
class _CacheKey:
    path: str
    mtime_ns: int
    ino: int
    is_dir: bool


class SizeCache:
    """Thread-safe size cache keyed by path identity + mtime."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: dict[_CacheKey, int] = {}

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def _key_for(self, path: Path) -> _CacheKey | None:
        try:
            st = path.stat(follow_symlinks=False)
        except OSError:
            return None
        return _CacheKey(
            path=str(path),
            mtime_ns=getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)),
            ino=st.st_ino,
            is_dir=path.is_dir() and not path.is_symlink(),
        )

    def get(self, path: Path) -> int | None:
        key = self._key_for(path)
        if key is None:
            return None
        with self._lock:
            return self._data.get(key)

    def put(self, path: Path, size: int) -> None:
        key = self._key_for(path)
        if key is None:
            return
        with self._lock:
            self._data[key] = size


_GLOBAL_CACHE = SizeCache()


def global_size_cache() -> SizeCache:
    return _GLOBAL_CACHE


def path_size(
    path: Path,
    *,
    cancel: CancelCheck | None = None,
    cache: SizeCache | None = None,
) -> int:
    """Return total size in bytes for a file or directory tree."""
    cache = cache if cache is not None else _GLOBAL_CACHE
    cached = cache.get(path)
    if cached is not None:
        return cached

    try:
        if not path.exists():
            return 0
        if path.is_file() or path.is_symlink():
            try:
                size = path.stat(follow_symlinks=False).st_size
            except OSError:
                size = 0
            cache.put(path, size)
            return size
    except OSError:
        return 0

    total = 0
    stack = [path]
    while stack:
        if cancel and cancel():
            break
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    if cancel and cancel():
                        cache.put(path, total)
                        return total
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                    except OSError:
                        continue
        except OSError:
            continue

    if not (cancel and cancel()):
        cache.put(path, total)
    return total


def size_many(
    paths: Iterable[Path],
    *,
    cancel: CancelCheck | None = None,
    cache: SizeCache | None = None,
    max_workers: int = 4,
    on_progress: Callable[[Path, int, int, int], None] | None = None,
) -> dict[str, int]:
    """Size independent paths in parallel. on_progress(path, size, done, total)."""
    unique: list[Path] = []
    seen: set[str] = set()
    for p in paths:
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)

    total = len(unique)
    results: dict[str, int] = {}
    if total == 0:
        return results

    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(path_size, p, cancel=cancel, cache=cache): p for p in unique
        }
        for fut in as_completed(futures):
            p = futures[fut]
            if cancel and cancel():
                break
            try:
                size = fut.result()
            except Exception:
                size = 0
            results[str(p)] = size
            done += 1
            if on_progress:
                on_progress(p, size, done, total)
    return results


def format_bytes(n: int) -> str:
    if n < 0:
        return "…"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(n)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


def format_size_cell(size_bytes: int, *, pending: bool) -> str:
    if pending:
        return "Calculating…"
    return format_bytes(size_bytes)
