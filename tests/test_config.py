import pytest

from icloud_reminders_mcp.config import Settings


def test_settings_require_username(monkeypatch):
    monkeypatch.delenv("ICLOUD_USERNAME", raising=False)
    with pytest.raises(RuntimeError, match="ICLOUD_USERNAME"):
        Settings.from_env()


def test_settings_load_china_mainland_and_default_list(monkeypatch):
    monkeypatch.setenv("ICLOUD_USERNAME", "user@example.com")
    monkeypatch.setenv("ICLOUD_CHINA_MAINLAND", "true")
    monkeypatch.setenv("ICLOUD_DEFAULT_REMINDER_LIST", "Work")
    settings = Settings.from_env()
    assert settings.china_mainland is True
    assert settings.default_list == "Work"
