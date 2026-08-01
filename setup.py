"""py2app setup for AppUnload (macOS .app bundle).

Widgets-only: QtCore / QtGui / QtWidgets. Do not ship full PySide6 Addons.
After build, `scripts/strip_pyside_bundle.py` removes leftover Essentials bloat
(QML, Designer, OpenGL, SQL, …).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from setuptools import find_packages, setup

ROOT = Path(__file__).resolve().parent
ICON = ROOT / "assets" / "AppIcon.icns"
VERSION = "0.1.0"

APP = ["main.py"]


def _ensure_pyside6_findable() -> None:
    """PySide6-Essentials alone is a namespace package (no __init__.py).

    py2app still uses legacy ``imp.find_module``, which cannot see namespaces.
    Stage a real package dir (symlinks + stub ``__init__.py``) on ``sys.path``.
    """
    try:
        from modulegraph import _imp as imp

        imp.find_module("PySide6")
        return
    except ImportError:
        pass

    try:
        import PySide6
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "PySide6 is not installed. Run:\n"
            "  pip3 install -r requirements-build.txt\n"
        ) from exc

    src = Path(list(PySide6.__path__)[0]).resolve()
    staging_root = ROOT / "build" / "_py2app_syspath"
    pkg = staging_root / "PySide6"
    if staging_root.exists():
        shutil.rmtree(staging_root)
    pkg.mkdir(parents=True)

    for item in src.iterdir():
        target = pkg / item.name
        try:
            target.symlink_to(item)
        except OSError:
            if item.is_dir():
                shutil.copytree(item, target, symlinks=True)
            else:
                shutil.copy2(item, target)

    try:
        from importlib.metadata import version as pkg_version

        ver = pkg_version("PySide6-Essentials")
    except Exception:
        ver = "0.0.0"

    (pkg / "__init__.py").write_text(
        '"""Stub so py2app can locate PySide6-Essentials (namespace package)."""\n'
        f'__version__ = "{ver}"\n',
        encoding="utf-8",
    )

    sys.path.insert(0, str(staging_root))
    for name in list(sys.modules):
        if name == "PySide6" or name.startswith("PySide6."):
            del sys.modules[name]

    from modulegraph import _imp as imp

    imp.find_module("PySide6")  # fail fast if staging is broken


_ensure_pyside6_findable()

# Modules this app actually imports (see src/mac_cleaner/ui + app.py).
PYSIDE_INCLUDES = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
]

# Never pull these into the module graph / zip (even if present on the build Mac).
EXCLUDES = [
    # PySide Addons (should not be installed for builds)
    "PySide6.QtWebEngine",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel",
    "PySide6.QtWebSockets",
    "PySide6.QtWebView",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DExtras",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    "PySide6.QtGraphsWidgets",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtLocation",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSerialBus",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtTextToSpeech",
    "PySide6.QtHttpServer",
    # Essentials modules we do not use (strip script also deletes binaries)
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.QtQuickTest",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPrintSupport",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtUiTools",
    "PySide6.QtXml",
    "PySide6.QtConcurrent",
    "PySide6.QtNetwork",
    # Dev / unrelated (polluted site-packages must not enter the bundle)
    "tkinter",
    "unittest",
    "pytest",
    "_pytest",
    "numpy",
    "scipy",
    "sklearn",
    "pandas",
    "matplotlib",
    "PIL",
    "llvmlite",
    "numba",
    "IPython",
    "notebook",
]

OPTIONS: dict = {
    "argv_emulation": False,
    # Copy PySide6 / shiboken package trees so Qt frameworks resolve; strip after.
    "packages": [
        "mac_cleaner",
        "PySide6",
        "shiboken6",
        "send2trash",
    ],
    "includes": [
        *PYSIDE_INCLUDES,
        "mac_cleaner.app",
        "mac_cleaner.ui.main_window",
        "mac_cleaner.ui.workers",
        "mac_cleaner.ui.theme",
        "mac_cleaner.ui.widgets.checkable_tree",
        "mac_cleaner.ui.widgets.confirm_dialog",
    ],
    "excludes": EXCLUDES,
    # Only plugins needed for a Cocoa Widgets window + icon pixmaps.
    "qt_plugins": [
        "platforms",
        "styles",
        "imageformats",
    ],
    "plist": {
        "CFBundleName": "AppUnload",
        "CFBundleDisplayName": "AppUnload",
        "CFBundleIdentifier": "com.karan.appunload",
        "CFBundleVersion": VERSION,
        "CFBundleShortVersionString": VERSION,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "13.0",
        "NSHumanReadableCopyright": "Copyright © 2026",
        "NSPrincipalClass": "NSApplication",
    },
}

if ICON.is_file():
    OPTIONS["iconfile"] = str(ICON)

# NOTE: Keep install_requires out of this file. py2app rejects it, and
# setuptools would also pull dependencies from pyproject.toml — the Makefile
# temporarily moves pyproject.toml aside during `make app`.
setup(
    name="AppUnload",
    version=VERSION,
    description="macOS app uninstaller and leftover cleaner",
    app=APP,
    packages=find_packages("src"),
    package_dir={"": "src"},
    options={"py2app": OPTIONS},
)
