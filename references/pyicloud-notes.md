# pyicloud integration notes

## Supported baseline

- Target `pyicloud` 2.6.5 or newer in the 2.x line.
- Use the maintained `timlaing/pyicloud` package, not the old
  `pyicloudreminders` package.
- Reminders use Apple's private iCloud web APIs through CloudKit v2. This is
  unofficial and can break if Apple changes the service.

## Authentication

- Authenticate interactively with `icloud auth login` before starting MCP.
- Let pyicloud store credentials in the operating-system keyring and its saved
  session. Never put an Apple password or 2FA code in Codex configuration.
- A session can expire or require fresh 2FA. Use `check_session_status`, stop the
  server, run the interactive login again, and restart Codex.
- Set `ICLOUD_CHINA_MAINLAND=true` for Apple accounts served from mainland China.

## Reminder behavior

- Priority values are: `0` none, `1` high, `5` medium, `9` low.
- This MCP uses Beijing time (`Asia/Shanghai`, UTC+08:00) consistently. A naive
  ISO 8601 timestamp is interpreted as Beijing time; other offsets are converted
  to Beijing time; returned timestamps are serialized with `+08:00`.
- `parent_reminder_id` creates a child under an existing reminder.
- Prefer `create_subtask`; it looks up the parent and automatically uses the
  same reminder list. `list_subtasks` returns immediate children only.
- Recurrence frequencies are daily, weekly, monthly, and yearly. Interval must
  be at least 1, occurrence count 0 means open-ended, and first day of week is
  represented by an integer from 0 through 6.
- Hashtags are separate CloudKit records linked to a reminder. Normalize an
  optional leading `#`, avoid case-insensitive duplicates, and prefer stable
  tag IDs when removing a tag.
- Clearing recurrence changes future reminder behavior and requires
  `confirm=true` in this MCP.
- Deletion is irreversible from this MCP and requires `confirm=true`.
- List titles are resolved only when exactly one exact case-insensitive match
  exists. Prefer stable list IDs.
