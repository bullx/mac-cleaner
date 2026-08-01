#!/usr/bin/env python3
"""Remove unused PySide6/Qt bits from a py2app .app bundle.

AppUnload only imports QtCore / QtGui / QtWidgets. Everything else
(QML, Designer tools, OpenGL, SQL, …) can be deleted after the build.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# Python extension modules we keep under site-packages/PySide6/
KEEP_MODULES = {
    "QtCore",
    "QtGui",
    "QtWidgets",
}

# Qt frameworks / dylib stems required (direct or transitive) for Widgets on macOS.
KEEP_FRAMEWORK_PREFIXES = (
    "QtCore",
    "QtGui",
    "QtWidgets",
    "QtDBus",  # often linked by QtGui on macOS
    "QtNetwork",  # common transitive link; Python module still unused
)

# Plugins required to show a window + load app icons (.icns / png).
KEEP_PLUGIN_DIRS = {
    "platforms",
    "imageformats",
    "styles",
}


def _rm(path: Path) -> int:
    if not path.exists():
        return 0
    size = _tree_size(path)
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return size


def _tree_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


def _find_pyside_roots(app: Path) -> list[Path]:
    roots: list[Path] = []
    for candidate in app.rglob("PySide6"):
        if candidate.is_dir() and (candidate / "__init__.py").exists():
            roots.append(candidate)
    return roots


def strip_pyside(root: Path) -> int:
    freed = 0

    # Drop designer / helper apps and CLI tools shipped inside the wheel.
    for pattern in ("*.app", "qmlls", "qmlformat", "qml*", "lupdate", "lrelease", "pyside6-*"):
        for path in root.glob(pattern):
            # Keep real Python modules named Qt*.
            if path.name.startswith("Qt") and path.suffix in {".so", ".py", ".pyi"}:
                continue
            if path.name in KEEP_MODULES or path.name.startswith("Qt") and path.suffix == ".abi3.so":
                continue
            freed += _rm(path)

    # Keep only needed .abi3.so / .py bindings.
    for path in list(root.iterdir()):
        name = path.name
        if name.startswith("Qt") and (
            name.endswith(".abi3.so")
            or name.endswith(".py")
            or name.endswith(".pyi")
            or name.endswith(".so")
        ):
            module = name.split(".", 1)[0]
            if module not in KEEP_MODULES:
                freed += _rm(path)
        elif name in {
            "Assistant.app",
            "Designer.app",
            "Linguist.app",
            "metatypes",
            "typesystems",
            "glue",
            "doc",
            "examples",
        }:
            freed += _rm(path)

    qt_dir = root / "Qt"
    if not qt_dir.is_dir():
        return freed

    # QML tree is large and unused for Widgets-only apps.
    freed += _rm(qt_dir / "qml")
    freed += _rm(qt_dir / "translations")  # optional; app has no i18n yet
    freed += _rm(qt_dir / "libexec")

    # Frameworks / dylibs
    lib = qt_dir / "lib"
    if lib.is_dir():
        for path in list(lib.iterdir()):
            stem = path.name
            if stem.endswith(".framework"):
                stem = stem[: -len(".framework")]
            elif ".dylib" in stem:
                stem = stem.split(".dylib", 1)[0]
                # libQt6Core.6 → Qt6Core-ish; normalize
                stem = stem.removeprefix("lib")
            keep = any(
                stem == prefix
                or stem.startswith(prefix + ".")
                or stem.startswith(prefix + "-")
                or stem == f"Qt6{prefix[2:]}"  # QtCore → Qt6Core
                or stem.startswith(f"Qt6{prefix[2:]}.")
                for prefix in KEEP_FRAMEWORK_PREFIXES
            )
            # Always keep ICU / supporting dylibs QtCore needs
            if stem.startswith(("icu", "libicu")) or "icu" in stem.lower():
                keep = True
            if not keep:
                freed += _rm(path)

    # Plugins
    plugins = qt_dir / "plugins"
    if plugins.is_dir():
        for path in list(plugins.iterdir()):
            if path.name not in KEEP_PLUGIN_DIRS:
                freed += _rm(path)

    return freed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path, help="Path to Foo.app")
    args = parser.parse_args()
    app = args.app.expanduser().resolve()
    if not app.is_dir() or app.suffix != ".app":
        print(f"Not an .app bundle: {app}", file=sys.stderr)
        return 2

    roots = _find_pyside_roots(app)
    if not roots:
        print("No PySide6 package found inside app; nothing to strip.")
        return 0

    before = _tree_size(app)
    freed = 0
    for root in roots:
        print(f"Stripping {root}")
        freed += strip_pyside(root)
    after = _tree_size(app)
    print(
        f"Done. Freed ~{freed / (1024**2):.0f} MiB "
        f"(bundle {before / (1024**2):.0f} → {after / (1024**2):.0f} MiB)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
