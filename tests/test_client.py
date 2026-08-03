from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from icloud_reminders_mcp.client import RemindersClient, parse_due
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


class FakeService:
    def __init__(self):
        self.reminders = FakeReminders()
        self.is_china_mainland = False
        self.is_trusted_session = True
        self.requires_2fa = False
        self.requires_2sa = False


@pytest.fixture
def fake_service():
    return FakeService()


@pytest.fixture
def client(fake_service):
    return RemindersClient(
        Settings(username="user@example.com"),
        service_factory=lambda _: fake_service,
    )


def test_parse_due_adds_local_timezone_to_naive_value():
    parsed = parse_due("2026-08-31T18:00:00")
    assert parsed is not None
    assert parsed.tzinfo is not None


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
    assert sent["priority"] == 1


def test_update_only_changes_supplied_fields(client, fake_service):
    client.update_item("r1", description="Changed", flagged=True)
    item = fake_service.reminders.items["r1"]
    assert item.title == "Test"
    assert item.desc == "Changed"
    assert item.flagged is True
    assert fake_service.reminders.updated == [item]


def test_complete_sets_utc_timestamp(client, fake_service):
    result = client.set_completed("r1")
    assert result["completed"] is True
    assert fake_service.reminders.items["r1"].completed_date.tzinfo == timezone.utc


def test_delete_requires_explicit_confirmation(client, fake_service):
    with pytest.raises(ValueError, match="confirm=true"):
        client.delete_item("r1", confirm=False)
    assert fake_service.reminders.deleted == []
    result = client.delete_item("r1", confirm=True)
    assert result["deleted"] is True
    assert fake_service.reminders.deleted[0].id == "r1"
