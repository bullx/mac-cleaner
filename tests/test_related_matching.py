from pathlib import Path

from mac_cleaner.domain.models import AppInfo, MatchReason
from mac_cleaner.scanners.library_index import IndexEntry, LibraryIndex
from mac_cleaner.scanners.related import _bundle_matches_name, _name_match, find_related_files


def test_bundle_exact_and_prefix():
    assert _bundle_matches_name("com.foo.bar", "com.foo.bar") == MatchReason.EXACT_BUNDLE
    assert (
        _bundle_matches_name("com.foo.bar.plist", "com.foo.bar") == MatchReason.EXACT_BUNDLE
    )
    assert (
        _bundle_matches_name("com.foo.bar.ShipIt", "com.foo.bar") == MatchReason.EXACT_BUNDLE
    )


def test_name_match_exact_only():
    assert _name_match("Cursor", "Cursor")
    assert not _name_match("CursorHelper", "Cursor")
    assert not _name_match("Sparkify", "Spark")
    assert not _name_match("ssh", "ssh")


def test_find_related_uses_bundle(tmp_path, monkeypatch):
    home = tmp_path / "Users" / "test"
    app = home / "Applications" / "DemoApp.app"
    (app / "Contents").mkdir(parents=True)
    info = app / "Contents" / "Info.plist"
    info.write_bytes(
        b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>com.example.demoapp</string>
<key>CFBundleName</key><string>DemoApp</string>
<key>CFBundleDisplayName</key><string>DemoApp</string>
</dict></plist>"""
    )
    cache = home / "Library" / "Caches" / "com.example.demoapp"
    cache.mkdir(parents=True)
    (cache / "x.bin").write_bytes(b"12345")
    support = home / "Library" / "Application Support" / "DemoApp"
    support.mkdir(parents=True)

    monkeypatch.setattr("mac_cleaner.domain.rules.home", lambda: home.resolve())
    monkeypatch.setattr(
        "mac_cleaner.scanners.related.library_roots",
        lambda: {
            "crash_reporter": home / "Library" / "CrashReporter",
        },
    )
    monkeypatch.setattr(
        "mac_cleaner.scanners.related.items_for_bundle",
        lambda *a, **k: [],
    )

    index = LibraryIndex(
        entries=[
            IndexEntry(cache, cache.name, "caches", False),
            IndexEntry(support, support.name, "application_support", False),
        ]
    )

    app_info = AppInfo(
        name="DemoApp",
        path=app,
        bundle_id="com.example.demoapp",
    )
    items = find_related_files(app_info, compute_size=True, library_index=index)
    paths = {i.path.resolve() for i in items}
    assert cache.resolve() in paths
    assert support.resolve() in paths
    assert app.resolve() in paths
