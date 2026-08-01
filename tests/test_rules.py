from pathlib import Path

from mac_cleaner.domain.rules import (
    is_hard_denied,
    is_name_token_allowed,
    is_path_allowed_for_trash,
    is_shared_vendor_folder,
)


def test_name_token_rejects_short_and_generic():
    assert not is_name_token_allowed("app")
    assert not is_name_token_allowed("ssh")
    assert not is_name_token_allowed("helper")
    assert is_name_token_allowed("Cursor")
    assert is_name_token_allowed("Claude")


def test_shared_vendor():
    assert is_shared_vendor_folder("Adobe")
    assert is_shared_vendor_folder("Google")
    assert not is_shared_vendor_folder("Cursor")


def test_hard_deny_ssh(tmp_path, monkeypatch):
    home = tmp_path / "Users" / "test"
    home.mkdir(parents=True)
    ssh = home / ".ssh"
    ssh.mkdir()
    key = ssh / "id_rsa"
    key.write_text("x")
    monkeypatch.setattr("mac_cleaner.domain.rules.home", lambda: home.resolve())
    assert is_hard_denied(key, user_home=home.resolve())
    ok, reason = is_path_allowed_for_trash(key, user_home=home.resolve())
    assert not ok


def test_allows_library_support(tmp_path, monkeypatch):
    home = tmp_path / "Users" / "test"
    support = home / "Library" / "Application Support" / "Cursor"
    support.mkdir(parents=True)
    monkeypatch.setattr("mac_cleaner.domain.rules.home", lambda: home.resolve())
    ok, reason = is_path_allowed_for_trash(support, user_home=home.resolve())
    assert ok, reason
