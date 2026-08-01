# AppUnload

**macOS** app uninstaller and leftover cleaner. Find the hidden files that dragging an app to Trash leaves behind — then review and move them to Trash safely.

![Platform](https://img.shields.io/badge/macOS-13%2B-blue)
![Python](https://img.shields.io/badge/Python-3.11%2B-green)

**Version:** 0.1.0 · **macOS only** · Bundle ID `com.karan.appunload`

## Features

- **Apps** — List installed apps, discover related files by bundle ID across `~/Library`, show sizes, select what to remove
- **Orphans** — Leftovers whose owning app is already gone
- **Junk** — Conservative user caches / logs / temp cleanup
- **Deep profiles** — Extra paths for Cursor, Claude, and Codex
- **Fast scans** — Discover paths quickly; size in background workers; Library index + size cache
- **Safe by default** — Trash only (`send2trash`); shared vendor folders stay unchecked; deletion logs under `~/Library/Logs/AppUnload`
- **UI** — Parent → child selection, expandable categories, Reveal in Finder

## Requirements

- macOS 13+
- Python 3.11+ (system / user `python3` — **no venv**)
- **Full Disk Access** recommended (System Settings → Privacy & Security → Full Disk Access) so Containers scans are complete

---

## Quick start (development)

```bash
cd mac-cleaner
pip3 install -U pip
pip3 install -e ".[dev]"
python3 -m mac_cleaner
```

Or: `python3 main.py` / `appunload`

Install **PySide6-Essentials** only. Do not `pip install PySide6` (that pulls Addons including WebEngine ~600MB).

```bash
pip3 uninstall -y PySide6 PySide6-Addons   # if previously installed
pip3 install -r requirements-build.txt
```

`make app` auto-handles Essentials’ missing `__init__.py` (py2app needs a real package).

## Tests

```bash
python3 -m pytest
```

---

## Build a Mac `.app` + zip (distribute)

Same pattern as statsinfo: system `python3` + **py2app** → strip unused Qt → `.app` → zip. No venv.

Icon: `assets/AppIcon.icns` (from `assets/icon-sweep-slate.png`).

### One-time build deps

```bash
pip3 install -r requirements-build.txt
```

### Release

```bash
make release
```

That runs: `python3 setup.py py2app` → `scripts/strip_pyside_bundle.py` → ad-hoc `codesign` → zip.

Outputs:

- `dist/AppUnload.app` — run locally
- `dist/AppUnload-0.1.0-macos.zip` — share / upload

```bash
make app
make zip
make clean-dist   # remove build/ and dist/
```

Builds are **ad-hoc signed** (fine for local use). Downloaded zips on other Macs may need **System Settings → Privacy & Security → Open Anyway** until you codesign + notarize with an Apple Developer ID.

### Notarization (later)

When you have a Developer ID:

```bash
codesign --deep --force --options runtime \
  --sign "Developer ID Application: YOUR NAME (TEAMID)" \
  "dist/AppUnload.app"
# zip, then:
xcrun notarytool submit AppUnload.zip --apple-id YOU@email --team-id TEAMID --wait
xcrun stapler staple "dist/AppUnload.app"
```

Remind users to grant **Full Disk Access** to **AppUnload** if Containers look empty.

---

## How matching works

1. Read the app’s `CFBundleIdentifier` from `Info.plist`
2. Scan known Library roots for exact / prefix bundle ID matches
3. Optionally match exact display-name folders (never short/generic tokens)
4. Attach curated deep-profile paths for known hard-to-find tools
5. You review the checklist → confirm → **Move to Trash**

## Safety

- Never permanently deletes (`rm -rf`)
- Blocks `/System`, sensitive home paths (`~/.ssh`, `~/.aws`, shell histories, etc.)
- Does not auto-select Group Containers or shared vendor folders (Adobe, Google, Microsoft, …)
- Does not touch VS Code’s `Application Support/Code` when cleaning Cursor
- System `/Library` leftovers are shown as locked in v1 (no sudo)

## Project docs

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** — package layout, data flow, Qt keep/strip list, and AI/agent context
