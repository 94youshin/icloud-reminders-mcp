from __future__ import annotations

from functools import lru_cache
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import BEIJING_TIMEZONE_NAME, RemindersClient
from .config import Settings


mcp = FastMCP(
    "Apple Reminders",
    instructions=(
        "Manage Apple Reminders through pyicloud. List IDs before writing when "
        "the target list is unclear. Interpret and return all date-times in Beijing "
        "time (Asia/Shanghai). Never delete without explicit user approval."
    ),
)


@lru_cache(maxsize=1)
def _client() -> RemindersClient:
    return RemindersClient(Settings.from_env())


@mcp.tool()
def check_session_status() -> dict[str, Any]:
    """Check whether the saved iCloud session is trusted or needs 2FA."""
    return _client().session_status()


@mcp.tool()
def list_reminder_lists() -> list[dict[str, Any]]:
    """List Apple Reminder lists and their stable IDs."""
    return _client().list_lists()


@mcp.tool()
def list_reminders(
    list_id: str | None = None,
    include_completed: bool = False,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """List reminders; all returned timestamps use Beijing time (+08:00)."""
    return _client().list_items(list_id, include_completed, limit)


@mcp.tool()
def get_reminder(reminder_id: str) -> dict[str, Any]:
    """Get one reminder by ID with timestamps in Beijing time (+08:00)."""
    return _client().get_item(reminder_id)


@mcp.tool()
def list_subtasks(
    parent_reminder_id: str,
    include_completed: bool = False,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """List immediate child tasks of one parent reminder."""
    return _client().list_subtasks(parent_reminder_id, include_completed, limit)


@mcp.tool()
def create_subtask(
    parent_reminder_id: str,
    title: str,
    description: str = "",
    due: str | None = None,
    priority: int = 0,
    flagged: bool = False,
    all_day: bool = False,
) -> dict[str, Any]:
    """Create a child task in the same list as its parent reminder."""
    return _client().create_subtask(
        parent_reminder_id,
        title=title,
        description=description,
        due=due,
        priority=priority,
        flagged=flagged,
        all_day=all_day,
    )


@mcp.tool()
def create_reminder(
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
    """Create a reminder or child task using Beijing time (Asia/Shanghai)."""
    return _client().create_item(
        title=title,
        list_id=list_id,
        description=description,
        due=due,
        priority=priority,
        flagged=flagged,
        all_day=all_day,
        time_zone_name=time_zone_name,
        parent_reminder_id=parent_reminder_id,
    )


@mcp.tool()
def update_reminder(
    reminder_id: str,
    title: str | None = None,
    description: str | None = None,
    due: str | None = None,
    clear_due: bool = False,
    priority: int | None = None,
    flagged: bool | None = None,
    all_day: bool | None = None,
) -> dict[str, Any]:
    """Update supplied fields; due values are normalized to Beijing time."""
    return _client().update_item(
        reminder_id,
        title=title,
        description=description,
        due=due,
        clear_due=clear_due,
        priority=priority,
        flagged=flagged,
        all_day=all_day,
    )


@mcp.tool()
def set_reminder_completed(reminder_id: str, completed: bool = True) -> dict[str, Any]:
    """Complete or reopen a reminder using Beijing time for completion."""
    return _client().set_completed(reminder_id, completed)


@mcp.tool()
def get_reminder_recurrence(reminder_id: str) -> list[dict[str, Any]]:
    """Get recurrence rules attached to a reminder."""
    return _client().list_recurrence_rules(reminder_id)


@mcp.tool()
def set_reminder_recurrence(
    reminder_id: str,
    frequency: str,
    interval: int = 1,
    occurrence_count: int = 0,
    first_day_of_week: int = 0,
) -> dict[str, Any]:
    """Create or update one daily, weekly, monthly, or yearly recurrence rule."""
    return _client().set_recurrence(
        reminder_id,
        frequency=frequency,
        interval=interval,
        occurrence_count=occurrence_count,
        first_day_of_week=first_day_of_week,
    )


@mcp.tool()
def clear_reminder_recurrence(
    reminder_id: str,
    confirm: bool = False,
) -> dict[str, Any]:
    """Remove all recurrence rules after explicit confirmation."""
    return _client().clear_recurrence(reminder_id, confirm=confirm)


@mcp.tool()
def list_reminder_tags(reminder_id: str) -> list[dict[str, Any]]:
    """List hashtags attached to a reminder."""
    return _client().list_tags(reminder_id)


@mcp.tool()
def add_reminder_tag(reminder_id: str, name: str) -> dict[str, Any]:
    """Attach a hashtag to a reminder; a leading # is optional."""
    return _client().add_tag(reminder_id, name)


@mcp.tool()
def remove_reminder_tag(reminder_id: str, tag_id_or_name: str) -> dict[str, Any]:
    """Remove a hashtag from a reminder by stable ID or exact name."""
    return _client().remove_tag(reminder_id, tag_id_or_name)


@mcp.tool()
def delete_reminder(reminder_id: str, confirm: bool = False) -> dict[str, Any]:
    """Delete a reminder. The caller must pass confirm=true after user approval."""
    return _client().delete_item(reminder_id, confirm=confirm)


def main() -> None:
    mcp.run(transport="stdio")
