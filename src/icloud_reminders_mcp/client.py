from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .config import Settings


ServiceFactory = Callable[[Settings], Any]
BEIJING_TIMEZONE_NAME = "Asia/Shanghai"
BEIJING_TIMEZONE = ZoneInfo(BEIJING_TIMEZONE_NAME)


def _default_service_factory(settings: Settings) -> Any:
    from pyicloud import PyiCloudService
    from keyring.errors import KeyringError
    from pyicloud.utils import get_password_from_keyring

    keyring_error: KeyringError | None = None
    try:
        password = get_password_from_keyring(settings.username)
    except KeyringError as exc:
        # A valid saved iCloud session does not require access to the password.
        # This keeps headless Linux usable when no desktop keyring is available.
        password = None
        keyring_error = exc
    session_service = PyiCloudService(
        settings.username,
        password=password,
        china_mainland=settings.china_mainland,
        authenticate=False,
    )
    status = session_service.get_auth_status()
    if status["authenticated"]:
        return session_service
    if password is None:
        keyring_hint = (
            " The system keyring is unavailable; configure a secure keyring backend."
            if keyring_error is not None
            else ""
        )
        raise RuntimeError(
            "No authenticated iCloud session or keyring password was found. "
            "Run 'icloud auth login' interactively and restart the MCP server."
            f"{keyring_hint}"
        )
    return PyiCloudService(
        settings.username,
        password=password,
        china_mainland=settings.china_mainland,
        authenticate=True,
    )


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(BEIJING_TIMEZONE).isoformat()


def parse_due(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(
            "due must be ISO 8601, for example 2026-08-31T18:00:00+08:00"
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BEIJING_TIMEZONE)
    return parsed.astimezone(BEIJING_TIMEZONE)


def serialize_list(item: Any) -> dict[str, Any]:
    return {
        "id": item.id,
        "title": item.title,
        "color": item.color,
        "count": item.count,
        "is_group": item.is_group,
    }


def serialize_reminder(item: Any) -> dict[str, Any]:
    return {
        "id": item.id,
        "list_id": item.list_id,
        "title": item.title,
        "description": item.desc,
        "completed": item.completed,
        "completed_date": _iso(item.completed_date),
        "due": _iso(item.due_date),
        "priority": item.priority,
        "flagged": item.flagged,
        "all_day": item.all_day,
        "time_zone": item.time_zone,
        "parent_reminder_id": item.parent_reminder_id,
        "hashtag_ids": list(getattr(item, "hashtag_ids", [])),
        "recurrence_rule_ids": list(getattr(item, "recurrence_rule_ids", [])),
        "created": _iso(item.created),
        "modified": _iso(item.modified),
    }


class RemindersClient:
    def __init__(
        self,
        settings: Settings,
        service_factory: ServiceFactory = _default_service_factory,
    ) -> None:
        self.settings = settings
        self._service_factory = service_factory
        self._service: Any | None = None

    @property
    def service(self) -> Any:
        if self._service is None:
            self._service = self._service_factory(self.settings)
        return self._service

    @property
    def reminders(self) -> Any:
        return self.service.reminders

    def session_status(self) -> dict[str, Any]:
        service = self.service
        status = service.get_auth_status()
        return {
            "authenticated": status["authenticated"],
            "china_mainland": service.is_china_mainland,
            "trusted_session": status["trusted_session"],
            "requires_2fa": status["requires_2fa"],
            "requires_2sa": status["requires_2sa"],
        }

    def list_lists(self) -> list[dict[str, Any]]:
        return [serialize_list(item) for item in self.reminders.lists()]

    def _resolve_list_id(self, selector: str | None) -> str:
        selected = selector or self.settings.default_list
        lists = list(self.reminders.lists())
        if selected:
            by_id = [item for item in lists if item.id == selected]
            if by_id:
                return by_id[0].id
            by_title = [item for item in lists if item.title.casefold() == selected.casefold()]
            if len(by_title) == 1:
                return by_title[0].id
            if len(by_title) > 1:
                raise ValueError(f"More than one reminder list is named {selected!r}; use an ID")
            raise ValueError(f"Reminder list {selected!r} was not found")
        if len(lists) == 1:
            return lists[0].id
        raise ValueError(
            "list_id is required when more than one list exists. Call "
            "list_reminder_lists or configure ICLOUD_DEFAULT_REMINDER_LIST."
        )

    def list_items(
        self,
        list_id: str | None = None,
        include_completed: bool = False,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        resolved = self._resolve_list_id(list_id)
        result = self.reminders.list_reminders(
            resolved,
            include_completed=include_completed,
            results_limit=limit,
        )
        return [serialize_reminder(item) for item in result.reminders]

    def get_item(self, reminder_id: str) -> dict[str, Any]:
        return serialize_reminder(self.reminders.get(reminder_id))

    def list_subtasks(
        self,
        parent_reminder_id: str,
        include_completed: bool = False,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        parent = self.reminders.get(parent_reminder_id)
        result = self.reminders.list_reminders(
            parent.list_id,
            include_completed=include_completed,
            results_limit=1000,
        )
        children = [
            serialize_reminder(item)
            for item in result.reminders
            if item.parent_reminder_id == parent_reminder_id
        ]
        return children[:limit]

    def create_subtask(
        self,
        parent_reminder_id: str,
        *,
        title: str,
        description: str = "",
        due: str | None = None,
        priority: int = 0,
        flagged: bool = False,
        all_day: bool = False,
    ) -> dict[str, Any]:
        parent = self.reminders.get(parent_reminder_id)
        return self.create_item(
            title=title,
            list_id=parent.list_id,
            description=description,
            due=due,
            priority=priority,
            flagged=flagged,
            all_day=all_day,
            parent_reminder_id=parent_reminder_id,
        )

    @staticmethod
    def _serialize_recurrence_rule(rule: Any) -> dict[str, Any]:
        frequency = getattr(rule.frequency, "name", str(rule.frequency)).lower()
        return {
            "id": rule.id,
            "reminder_id": rule.reminder_id,
            "frequency": frequency,
            "interval": rule.interval,
            "occurrence_count": rule.occurrence_count,
            "first_day_of_week": rule.first_day_of_week,
        }

    def list_recurrence_rules(self, reminder_id: str) -> list[dict[str, Any]]:
        item = self.reminders.get(reminder_id)
        return [
            self._serialize_recurrence_rule(rule)
            for rule in self.reminders.recurrence_rules_for(item)
        ]

    def set_recurrence(
        self,
        reminder_id: str,
        *,
        frequency: str,
        interval: int = 1,
        occurrence_count: int = 0,
        first_day_of_week: int = 0,
    ) -> dict[str, Any]:
        from pyicloud.services.reminders.models import RecurrenceFrequency

        frequencies = {
            "daily": RecurrenceFrequency.DAILY,
            "weekly": RecurrenceFrequency.WEEKLY,
            "monthly": RecurrenceFrequency.MONTHLY,
            "yearly": RecurrenceFrequency.YEARLY,
        }
        normalized = frequency.strip().casefold()
        if normalized not in frequencies:
            raise ValueError("frequency must be daily, weekly, monthly, or yearly")
        if interval < 1:
            raise ValueError("interval must be at least 1")
        if occurrence_count < 0:
            raise ValueError("occurrence_count must be 0 or greater")
        if not 0 <= first_day_of_week <= 6:
            raise ValueError("first_day_of_week must be between 0 and 6")

        item = self.reminders.get(reminder_id)
        existing = list(self.reminders.recurrence_rules_for(item))
        if len(existing) > 1:
            raise RuntimeError(
                "The reminder has multiple recurrence rules; clear them explicitly first"
            )
        if existing:
            rule = existing[0]
            self.reminders.update_recurrence_rule(
                rule,
                frequency=frequencies[normalized],
                interval=interval,
                occurrence_count=occurrence_count,
                first_day_of_week=first_day_of_week,
            )
            rule.frequency = frequencies[normalized]
            rule.interval = interval
            rule.occurrence_count = occurrence_count
            rule.first_day_of_week = first_day_of_week
        else:
            rule = self.reminders.create_recurrence_rule(
                item,
                frequency=frequencies[normalized],
                interval=interval,
                occurrence_count=occurrence_count,
                first_day_of_week=first_day_of_week,
            )
        return self._serialize_recurrence_rule(rule)

    def clear_recurrence(self, reminder_id: str, *, confirm: bool) -> dict[str, Any]:
        if not confirm:
            raise ValueError("Clearing recurrence requires confirm=true")
        item = self.reminders.get(reminder_id)
        rules = list(self.reminders.recurrence_rules_for(item))
        for rule in rules:
            self.reminders.delete_recurrence_rule(item, rule)
        return {"cleared": True, "reminder_id": reminder_id, "deleted_rules": len(rules)}

    @staticmethod
    def _serialize_hashtag(tag: Any) -> dict[str, Any]:
        return {
            "id": tag.id,
            "reminder_id": tag.reminder_id,
            "name": tag.name,
            "created": _iso(tag.created),
        }

    def list_tags(self, reminder_id: str) -> list[dict[str, Any]]:
        item = self.reminders.get(reminder_id)
        return [self._serialize_hashtag(tag) for tag in self.reminders.tags_for(item)]

    def add_tag(self, reminder_id: str, name: str) -> dict[str, Any]:
        normalized = name.strip().lstrip("#").strip()
        if not normalized:
            raise ValueError("tag name must not be empty")
        item = self.reminders.get(reminder_id)
        existing = list(self.reminders.tags_for(item))
        for tag in existing:
            if tag.name.casefold() == normalized.casefold():
                return {"created": False, "tag": self._serialize_hashtag(tag)}
        tag = self.reminders.create_hashtag(item, normalized)
        return {"created": True, "tag": self._serialize_hashtag(tag)}

    def remove_tag(self, reminder_id: str, tag_id_or_name: str) -> dict[str, Any]:
        selector = tag_id_or_name.strip().lstrip("#").strip()
        if not selector:
            raise ValueError("tag_id_or_name must not be empty")
        item = self.reminders.get(reminder_id)
        matches = [
            tag
            for tag in self.reminders.tags_for(item)
            if tag.id == selector or tag.name.casefold() == selector.casefold()
        ]
        if not matches:
            raise ValueError(f"Tag {tag_id_or_name!r} was not found on the reminder")
        if len(matches) > 1:
            raise ValueError("More than one tag matches that name; use the tag ID")
        tag = matches[0]
        snapshot = self._serialize_hashtag(tag)
        self.reminders.delete_hashtag(item, tag)
        return {"removed": True, "tag": snapshot}

    def create_item(
        self,
        *,
        title: str,
        list_id: str | None = None,
        description: str = "",
        due: str | None = None,
        priority: int = 0,
        flagged: bool = False,
        all_day: bool = False,
        time_zone_name: str = BEIJING_TIMEZONE_NAME,
        parent_reminder_id: str | None = None,
    ) -> dict[str, Any]:
        if not title.strip():
            raise ValueError("title must not be empty")
        if priority not in {0, 1, 5, 9}:
            raise ValueError("priority must be 0 (none), 1 (high), 5 (medium), or 9 (low)")
        if time_zone_name != BEIJING_TIMEZONE_NAME:
            raise ValueError("time_zone_name must be Asia/Shanghai")
        item = self.reminders.create(
            self._resolve_list_id(list_id),
            title.strip(),
            desc=description,
            due_date=parse_due(due),
            priority=priority,
            flagged=flagged,
            all_day=all_day,
            time_zone=time_zone_name,
            parent_reminder_id=parent_reminder_id,
        )
        return serialize_reminder(item)

    def update_item(
        self,
        reminder_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        due: str | None = None,
        clear_due: bool = False,
        priority: int | None = None,
        flagged: bool | None = None,
        all_day: bool | None = None,
    ) -> dict[str, Any]:
        if due is not None and clear_due:
            raise ValueError("due and clear_due cannot be used together")
        if priority is not None and priority not in {0, 1, 5, 9}:
            raise ValueError("priority must be 0, 1, 5, or 9")
        item = self.reminders.get(reminder_id)
        if title is not None:
            if not title.strip():
                raise ValueError("title must not be empty")
            item.title = title.strip()
        if description is not None:
            item.desc = description
        if due is not None:
            item.due_date = parse_due(due)
            item.time_zone = BEIJING_TIMEZONE_NAME
        elif clear_due:
            item.due_date = None
            item.time_zone = None
        if priority is not None:
            item.priority = priority
        if flagged is not None:
            item.flagged = flagged
        if all_day is not None:
            item.all_day = all_day
        self.reminders.update(item)
        return serialize_reminder(item)

    def set_completed(self, reminder_id: str, completed: bool = True) -> dict[str, Any]:
        item = self.reminders.get(reminder_id)
        item.completed = completed
        item.completed_date = datetime.now(BEIJING_TIMEZONE) if completed else None
        self.reminders.update(item)
        return serialize_reminder(item)

    def delete_item(self, reminder_id: str, *, confirm: bool) -> dict[str, Any]:
        if not confirm:
            raise ValueError("Deletion requires confirm=true")
        item = self.reminders.get(reminder_id)
        snapshot = serialize_reminder(item)
        self.reminders.delete(item)
        return {"deleted": True, "reminder": snapshot}
