from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from icloud_reminders_mcp.client import (
    BEIJING_TIMEZONE_NAME,
    RemindersClient,
    _default_service_factory,
    parse_due,
)
from icloud_reminders_mcp.config import Settings


def reminder(**overrides):
    values = {
        "id": "r1",
        "list_id": "l1",
        "title": "Test",
        "desc": "",
        "completed": False,
        "completed_date": None,
        "due_date": None,
        "priority": 0,
        "flagged": False,
        "all_day": False,
        "time_zone": None,
        "parent_reminder_id": None,
        "hashtag_ids": [],
        "recurrence_rule_ids": [],
        "created": None,
        "modified": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FakeReminders:
    def __init__(self):
        self.items = {"r1": reminder()}
        self.updated = []
        self.deleted = []
        self.created_kwargs = None
        self.hashtags = {}
        self.recurrence_rules = {}

    def lists(self):
        return [
            SimpleNamespace(id="l1", title="Work", color="#f00", count=1, is_group=False),
            SimpleNamespace(id="l2", title="Personal", color=None, count=0, is_group=False),
        ]

    def list_reminders(self, list_id, include_completed=False, results_limit=200):
        assert list_id in {"l1", "l2"}
        return SimpleNamespace(reminders=list(self.items.values())[:results_limit])

    def get(self, reminder_id):
        return self.items[reminder_id]

    def create(self, list_id, title, **kwargs):
        self.created_kwargs = {"list_id": list_id, "title": title, **kwargs}
        item = reminder(id="new", list_id=list_id, title=title, **{
            "desc": kwargs["desc"],
            "due_date": kwargs["due_date"],
            "priority": kwargs["priority"],
            "flagged": kwargs["flagged"],
            "all_day": kwargs["all_day"],
            "time_zone": kwargs["time_zone"],
            "parent_reminder_id": kwargs["parent_reminder_id"],
        })
        self.items[item.id] = item
        return item

    def update(self, item):
        self.updated.append(item)

    def delete(self, item):
        self.deleted.append(item)

    def tags_for(self, item):
        return list(self.hashtags.get(item.id, []))

    def create_hashtag(self, item, name):
        tag = SimpleNamespace(
            id=f"tag-{len(self.hashtags.get(item.id, [])) + 1}",
            reminder_id=item.id,
            name=name,
            created=None,
        )
        self.hashtags.setdefault(item.id, []).append(tag)
        item.hashtag_ids.append(tag.id)
        return tag

    def delete_hashtag(self, item, tag):
        self.hashtags[item.id].remove(tag)
        item.hashtag_ids.remove(tag.id)

    def recurrence_rules_for(self, item):
        return list(self.recurrence_rules.get(item.id, []))

    def create_recurrence_rule(self, item, **kwargs):
        rule = SimpleNamespace(
            id=f"rule-{len(self.recurrence_rules.get(item.id, [])) + 1}",
            reminder_id=item.id,
            **kwargs,
        )
        self.recurrence_rules.setdefault(item.id, []).append(rule)
        item.recurrence_rule_ids.append(rule.id)
        return rule

    def update_recurrence_rule(self, rule, **kwargs):
        for key, value in kwargs.items():
            setattr(rule, key, value)

    def delete_recurrence_rule(self, item, rule):
        self.recurrence_rules[item.id].remove(rule)
        item.recurrence_rule_ids.remove(rule.id)


class FakeService:
    def __init__(self):
        self.reminders = FakeReminders()
        self.is_china_mainland = False
        self.is_trusted_session = True
        self.requires_2fa = False
        self.requires_2sa = False


def test_default_factory_hydrates_saved_session_without_fresh_login(monkeypatch):
    calls = []

    class FakePyiCloudService:
        def __init__(self, username, **kwargs):
            calls.append({"username": username, **kwargs})

        def get_auth_status(self):
            return {"authenticated": True}

    monkeypatch.setattr("pyicloud.PyiCloudService", FakePyiCloudService)
    monkeypatch.setattr(
        "pyicloud.utils.get_password_from_keyring", lambda username: "saved-password"
    )

    result = _default_service_factory(Settings(username="user@example.com"))

    assert isinstance(result, FakePyiCloudService)
    assert calls == [
        {
            "username": "user@example.com",
            "password": "saved-password",
            "china_mainland": False,
            "authenticate": False,
        }
    ]


def test_default_factory_reauthenticates_when_saved_session_expired(monkeypatch):
    calls = []

    class FakePyiCloudService:
        def __init__(self, username, **kwargs):
            calls.append({"username": username, **kwargs})

        def get_auth_status(self):
            return {"authenticated": False}

    monkeypatch.setattr("pyicloud.PyiCloudService", FakePyiCloudService)
    monkeypatch.setattr(
        "pyicloud.utils.get_password_from_keyring", lambda username: "saved-password"
    )

    _default_service_factory(Settings(username="user@example.com"))

    assert calls[-1]["authenticate"] is True
    assert calls[-1]["password"] == "saved-password"


@pytest.fixture
def fake_service():
    return FakeService()


@pytest.fixture
def client(fake_service):
    return RemindersClient(
        Settings(username="user@example.com"),
        service_factory=lambda _: fake_service,
    )


def test_parse_due_interprets_naive_value_as_beijing_time():
    parsed = parse_due("2026-08-31T18:00:00")
    assert parsed is not None
    assert getattr(parsed.tzinfo, "key", None) == BEIJING_TIMEZONE_NAME
    assert parsed.utcoffset().total_seconds() == 8 * 3600


def test_parse_due_converts_other_offsets_to_beijing_time():
    parsed = parse_due("2026-08-31T18:00:00Z")
    assert parsed is not None
    assert parsed.isoformat() == "2026-09-01T02:00:00+08:00"


def test_list_requires_selector_when_multiple_lists_exist(client):
    with pytest.raises(ValueError, match="list_id is required"):
        client.list_items()


def test_exact_list_title_is_resolved(client):
    result = client.list_items("work")
    assert result[0]["id"] == "r1"


def test_create_child_reminder_with_due_date(client, fake_service):
    result = client.create_item(
        title="Child task",
        list_id="l1",
        due="2026-08-31T18:00:00+08:00",
        priority=1,
        parent_reminder_id="parent-1",
    )
    assert result["parent_reminder_id"] == "parent-1"
    sent = fake_service.reminders.created_kwargs
    assert sent["due_date"].utcoffset().total_seconds() == 8 * 3600
    assert sent["time_zone"] == BEIJING_TIMEZONE_NAME
    assert sent["priority"] == 1


def test_create_subtask_uses_parent_list(client, fake_service):
    result = client.create_subtask("r1", title="Child task")
    assert result["parent_reminder_id"] == "r1"
    assert result["list_id"] == "l1"


def test_list_subtasks_returns_only_immediate_children(client, fake_service):
    fake_service.reminders.items["child"] = reminder(
        id="child", title="Child", parent_reminder_id="r1"
    )
    fake_service.reminders.items["other"] = reminder(id="other", title="Other")
    result = client.list_subtasks("r1")
    assert [item["id"] for item in result] == ["child"]


def test_set_and_clear_recurrence(client):
    created = client.set_recurrence(
        "r1", frequency="weekly", interval=2, occurrence_count=6, first_day_of_week=1
    )
    assert created == {
        "id": "rule-1",
        "reminder_id": "r1",
        "frequency": "weekly",
        "interval": 2,
        "occurrence_count": 6,
        "first_day_of_week": 1,
    }
    updated = client.set_recurrence("r1", frequency="monthly", interval=1)
    assert updated["frequency"] == "monthly"
    with pytest.raises(ValueError, match="confirm=true"):
        client.clear_recurrence("r1", confirm=False)
    assert client.clear_recurrence("r1", confirm=True)["deleted_rules"] == 1


def test_add_list_and_remove_tag(client):
    created = client.add_tag("r1", "#国省V2")
    assert created["created"] is True
    assert created["tag"]["name"] == "国省V2"
    duplicate = client.add_tag("r1", "国省v2")
    assert duplicate["created"] is False
    assert [tag["name"] for tag in client.list_tags("r1")] == ["国省V2"]
    removed = client.remove_tag("r1", "国省V2")
    assert removed["removed"] is True
    assert client.list_tags("r1") == []


def test_update_only_changes_supplied_fields(client, fake_service):
    client.update_item("r1", description="Changed", flagged=True)
    item = fake_service.reminders.items["r1"]
    assert item.title == "Test"
    assert item.desc == "Changed"
    assert item.flagged is True
    assert fake_service.reminders.updated == [item]


def test_update_due_normalizes_time_and_sets_beijing_zone(client, fake_service):
    result = client.update_item("r1", due="2026-08-31T10:00:00Z")
    item = fake_service.reminders.items["r1"]
    assert item.due_date.isoformat() == "2026-08-31T18:00:00+08:00"
    assert item.time_zone == BEIJING_TIMEZONE_NAME
    assert result["due"] == "2026-08-31T18:00:00+08:00"


def test_complete_sets_beijing_timestamp(client, fake_service):
    result = client.set_completed("r1")
    assert result["completed"] is True
    completed_date = fake_service.reminders.items["r1"].completed_date
    assert getattr(completed_date.tzinfo, "key", None) == BEIJING_TIMEZONE_NAME
    assert result["completed_date"].endswith("+08:00")


def test_read_timestamps_are_serialized_in_beijing_time(client, fake_service):
    fake_service.reminders.items["r1"].due_date = datetime(
        2026, 8, 31, 10, 0, tzinfo=timezone.utc
    )
    result = client.get_item("r1")
    assert result["due"] == "2026-08-31T18:00:00+08:00"


def test_delete_requires_explicit_confirmation(client, fake_service):
    with pytest.raises(ValueError, match="confirm=true"):
        client.delete_item("r1", confirm=False)
    assert fake_service.reminders.deleted == []
    result = client.delete_item("r1", confirm=True)
    assert result["deleted"] is True
    assert fake_service.reminders.deleted[0].id == "r1"
