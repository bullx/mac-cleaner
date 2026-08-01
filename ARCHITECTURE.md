# AppUnload — Architecture & agent context

**Read this first** in a new chat before changing code. Public user docs: [README.md](./README.md).

## Product summary

| | |
|---|---|
| **Name** | AppUnload |
| **Version** | `0.1.0` (`src/mac_cleaner/__init__.py`, `setup.py`, `Makefile`) |
| **Pitch** | One-stop macOS app uninstaller + leftover cleaner (review → Trash) |
| **Platform** | **macOS only** (13+) |
| **UI** | PySide6 Widgets — tabs Apps / Orphans / Junk |
| **Qt package** | **`PySide6-Essentials` only** (never full `PySide6` / Addons) |
| **Bundle ID** | `com.karan.appunload` |
| **Icon** | `assets/AppIcon.icns` (source art: `assets/icon-sweep-slate.png`) |
| **Distribution** | py2app + Qt strip + `make release` → `.app` + zip (ad-hoc signed) |
| **Python for builds** | System `python3` (**no venv**) — same as statsinfo |
| **Delete model** | Trash only (`send2trash`); never `rm -rf` |
| **Internal package** | `mac_cleaner` (Python import path — keep unless doing a full package rename) |

## Purpose

Dragging an app to Trash leaves data under `~/Library`. This app:

1. Lists installed apps from `/Applications` and `~/Applications`
2. Finds related paths primarily by **bundle ID**
3. Surfaces orphans (no matching app) and conservative junk
4. Lets the user select paths (parent checkbox → children)
5. Confirms, then moves to Trash and writes a log under `~/Library/Logs/AppUnload`

Deep curated profiles exist for **Cursor**, **Claude**, and **Codex**.

---

## Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.11+ |
| UI | PySide6 Essentials — **QtCore / QtGui / QtWidgets only** |
| Dev / ship Python | System `python3` + user site-packages (no venv) |
| Dev install | `pip3 install -e ".[dev]"` (`src/` layout) |
| Ship | `setup.py` + py2app + `scripts/strip_pyside_bundle.py` + `Makefile` |
| Sizing | Parallel `path_size` / `size_many` + `SizeCache` |
| Tests | pytest (`tests/`), including Qt expand tests |

**Entry points**

- Dev: `python3 -m mac_cleaner` or `python3 main.py` → `mac_cleaner.app:run`
- Console: `appunload` (alias `mac-cleaner` kept for now)
- Ship: `dist/AppUnload.app`

---

## Qt: keep vs remove

App imports (audit `src/`): **only** `PySide6.QtCore`, `PySide6.QtGui`, `PySide6.QtWidgets`.

| Keep | Why |
|------|-----|
| `QtCore` / `QtGui` / `QtWidgets` | Entire UI |
| `shiboken6` | PySide binding runtime |
| Frameworks `QtCore`, `QtGui`, `QtWidgets`, `QtDBus`, `QtNetwork` | Direct + common transitive links on macOS |
| Plugins `platforms`, `styles`, `imageformats` | Cocoa window + Fusion + `.icns`/png icons |
| `send2trash` | Trash deletes |

| Remove (do not install / strip from `.app`) | Why |
|-----------------------------------------------|-----|
| **PySide6-Addons** / meta `PySide6` | WebEngine (~600MB), Charts, Multimedia, 3D, … |
| `QtWebEngine*` | Browser stack — unused |
| `QtQml` / `QtQuick*` + `Qt/qml/` | QML — unused |
| `QtOpenGL*`, `QtSql`, `QtTest`, `QtDesigner`, `QtHelp`, `QtSvg*`, `QtPrintSupport`, `QtUiTools`, `QtXml`, `QtConcurrent` | Essentials modules we never import |
| Designer / Assistant / Linguist `.app`, `qmlls`, `lupdate`, … | Dev tools inside the wheel |
| `translations/` | No i18n yet |

Build flow: py2app copies Essentials → `strip_pyside_bundle.py` deletes the rest → ad-hoc codesign.

---

## Directory map

```
main.py                      # GUI / py2app entry
setup.py                     # py2app (plist, excludes, qt_plugins) — no install_requires
Makefile                     # make app | zip | release | clean-dist  (system python3)
requirements-build.txt       # py2app + PySide6-Essentials + send2trash
pyproject.toml               # pip3 install -e ".[dev]" (moved aside during make app)
scripts/strip_pyside_bundle.py
assets/AppIcon.icns          # Dock / .app icon
assets/icon-sweep-slate.png  # source art for icns
src/mac_cleaner/             # internal Python package name
  app.py                     # QApplication, quiet Qt logs, Fusion palette
  __main__.py
  domain/
  infra/trash.py             # logs → ~/Library/Logs/AppUnload
  scanners/
  profiles/
  services/
  ui/main_window.py          # brand "AppUnload"
tests/
```

Ignored / generated: `build/`, `dist/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/`.

---

## Runtime data flow

```
MainWindow
  ├─ AppsScanWorker / RelatedScanWorker / OrphansScanWorker / JunkScanWorker
  └─ DeleteWorker → Trash + manifest
```

---

## UI contracts (do not regress)

| Rule | Why |
|------|-----|
| **No** opacity effects | QPainter spam |
| **No** `Signal(int)` for byte sizes | 32-bit overflow |
| Workers = **`QThread.run`**, not `moveToThread` | timer spam |
| Path UI = **`CheckableTree` only** | expand / checkbox contracts |
| Keep `tests/test_checkable_tree_expand.py` passing | |

---

## Packaging (macOS ship)

```bash
pip3 install -r requirements-build.txt
make release
# → dist/AppUnload.app
# → dist/AppUnload-0.1.0-macos.zip
```

**Gotchas:** Essentials-only; `setup.py` stages namespace `PySide6` for py2app; move `pyproject.toml` aside during build; ad-hoc signed.

---

## Agent working rules (short)

1. macOS-only; Trash-only; no opacity / `moveToThread` / `Signal(int)` sizes.
2. Product name **AppUnload** (`com.karan.appunload`). Internal import package stays `mac_cleaner` unless explicitly renamed.
3. No venv; PySide6-Essentials only.
4. After UI/tree changes: `python3 -m pytest`.
