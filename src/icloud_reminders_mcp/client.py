from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .config import Settings


ServiceFactory = Callable[[Settings], Any]


def _default_service_factory(settings: Settings) -> Any:
    from pyicloud import PyiCloudService
    from pyicloud.utils import get_password_from_keyring

    password = get_password_from_keyring(settings.username)
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
        raise RuntimeError(
            "No authenticated iCloud session or keyring password was found. "
            "Run 'icloud auth login' interactively and restart the MCP server."
        )
    return PyiCloudService(
        settings.username,
        password=password,
        china_mainland=settings.china_mainland,
        authenticate=True,
    )


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


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
        parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return parsed


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
        return {
            "username": self.settings.username,
            "china_mainland": service.is_china_mainland,
            "trusted_session": service.is_trusted_session,
            "requires_2fa": service.requires_2fa,
            "requires_2sa": service.requires_2sa,
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
        time_zone_name: str | None = None,
        parent_reminder_id: str | None = None,
    ) -> dict[str, Any]:
        if not title.strip():
            raise ValueError("title must not be empty")
        if priority not in {0, 1, 5, 9}:
            raise ValueError("priority must be 0 (none), 1 (high), 5 (medium), or 9 (low)")
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
        elif clear_due:
            item.due_date = None
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
        item.completed_date = datetime.now(timezone.utc) if completed else None
        self.reminders.update(item)
        return serialize_reminder(item)

    def delete_item(self, reminder_id: str, *, confirm: bool) -> dict[str, Any]:
        if not confirm:
            raise ValueError("Deletion requires confirm=true")
        item = self.reminders.get(reminder_id)
        snapshot = serialize_reminder(item)
        self.reminders.delete(item)
        return {"deleted": True, "reminder": snapshot}
