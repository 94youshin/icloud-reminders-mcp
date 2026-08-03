---
name: icloud-reminders-mcp
description: Install, configure, and safely use the local iCloud Reminders MCP server backed by pyicloud. Use when the user wants Codex on Windows, Linux, or macOS to list Apple reminder lists, create or query parent and child tasks, configure repeated reminders, manage reminder hashtags, update or complete reminders, or delete reminders after confirmation without browser automation.
---

# iCloud Reminders MCP

Use the bundled Python MCP server to manage Apple Reminders through the current
`pyicloud` CloudKit v2 reminders service. Treat it as an unofficial iCloud web
integration. Read [references/pyicloud-notes.md](references/pyicloud-notes.md)
when authentication, list selection, dates, or API compatibility matter. Read
[README.md](README.md) for complete Windows and Linux setup instructions.

## Install and authenticate

Create a Python 3.10+ virtual environment, install the project, then run
`icloud auth login --username "APPLE_ID"` from the virtual environment in an
interactive terminal. Append `--china-mainland` for a mainland China account.

Complete password and 2FA prompts locally. Never ask the user to paste an Apple
password or 2FA code into chat, an environment variable, source code, or MCP
configuration.

## Configure Codex

Register a stdio server using the virtual environment's Python executable:

```toml
[mcp_servers.apple-reminders]
command = "C:/absolute/path/icloud-reminders-mcp/.venv/Scripts/python.exe"
args = ["-m", "icloud_reminders_mcp"]

[mcp_servers.apple-reminders.env]
ICLOUD_USERNAME = "APPLE_ID"
ICLOUD_CHINA_MAINLAND = "false"
ICLOUD_DEFAULT_REMINDER_LIST = "Work"
```

On Linux, use `/absolute/path/icloud-reminders-mcp/.venv/bin/python` for
`command`. Restart Codex after changing MCP configuration. Omit the default
list when the user prefers selecting a list each time.

## Use safely

Follow this order:

1. Call `check_session_status` when authentication may have expired.
2. Call `list_reminder_lists` before a write if the destination is ambiguous.
3. Prefer list IDs over titles for writes.
4. Interpret natural-language dates in Beijing time and convert them to ISO
   8601 before calling a tool, for example `2026-08-31T18:00:00+08:00`. Treat
   returned timestamps as `Asia/Shanghai` (`+08:00`).
5. Create the parent first, then call `create_subtask` with its returned ID.
6. Use recurrence frequencies `daily`, `weekly`, `monthly`, or `yearly`.
   `occurrence_count=0` means no occurrence limit; `first_day_of_week` is 0-6.
7. Accept tag names with or without a leading `#`; prefer tag IDs for removal.
8. Confirm with the user before calling `clear_reminder_recurrence` with
   `confirm=true`.
9. For deletion, show the exact reminder to the user and obtain approval before
   calling `delete_reminder` with `confirm=true`.

Available tools:

- `check_session_status`
- `list_reminder_lists`
- `list_reminders`
- `get_reminder`
- `list_subtasks`
- `create_subtask`
- `create_reminder`
- `update_reminder`
- `set_reminder_completed`
- `get_reminder_recurrence`
- `set_reminder_recurrence`
- `clear_reminder_recurrence`
- `list_reminder_tags`
- `add_reminder_tag`
- `remove_reminder_tag`
- `delete_reminder`

Priority mapping is `0` none, `1` high, `5` medium, and `9` low. Use
`all_day=true` for date-only reminders. Pass `parent_reminder_id` only after the
parent has been created successfully.

## Recover authentication

If a tool reports 2FA, an untrusted session, changed Apple terms, or login
failure, stop the MCP process, rerun the interactive `icloud auth login`
command, and restart Codex. Do not automate Apple ID passwords or 2FA.
