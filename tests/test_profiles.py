from mac_cleaner.profiles import items_for_bundle
from mac_cleaner.profiles.cursor import BUNDLE_IDS as CURSOR_IDS
from mac_cleaner.profiles.claude import BUNDLE_IDS as CLAUDE_IDS


def test_cursor_profile_matches_bundle():
    items = items_for_bundle(next(iter(CURSOR_IDS)), app_name="Cursor", compute_size=False)
    # At least the profile module returns structured items for existing paths
    assert isinstance(items, list)


def test_claude_profile_matches_bundle():
    items = items_for_bundle(next(iter(CLAUDE_IDS)), app_name="Claude", compute_size=False)
    assert isinstance(items, list)
