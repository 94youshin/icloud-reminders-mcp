from __future__ import annotations

from functools import lru_cache
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import RemindersClient
from .config import Settings


mcp = FastMCP(
    "Apple Reminders",
    instructions=(
        "Manage Apple Reminders through pyicloud. List IDs before writing when "
        "the target list is unclear. Never delete without explicit user approval."
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
    """List reminders from a list ID or exact list title."""
    return _client().list_items(list_id, include_completed, limit)


@mcp.tool()
def get_reminder(reminder_id: str) -> dict[str, Any]:
    """Get one reminder by its stable ID."""
    return _client().get_item(reminder_id)


@mcp.tool()
def create_reminder(
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
    """Create a reminder or child task. Due dates must be ISO 8601 with timezone."""
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
    """Update only the supplied fields of an existing reminder."""
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
    """Complete a reminder, or reopen it with completed=false."""
    return _client().set_completed(reminder_id, completed)


@mcp.tool()
def delete_reminder(reminder_id: str, confirm: bool = False) -> dict[str, Any]:
    """Delete a reminder. The caller must pass confirm=true after user approval."""
    return _client().delete_item(reminder_id, confirm=confirm)


def main() -> None:
    mcp.run(transport="stdio")
