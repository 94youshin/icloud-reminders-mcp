# iCloud Reminders MCP

English | [简体中文](README.zh-CN.md)

`icloud-reminders-mcp` is a cross-platform Model Context Protocol (MCP) server
for Apple Reminders. It uses the maintained `pyicloud` package and iCloud's
CloudKit v2 reminders service, so Windows and Linux machines can manage reminders
without macOS, AppleScript, or browser automation.

> This is an unofficial iCloud integration. Apple does not publish a stable
> Reminders API, so an iCloud service change can require a project update.

## Capabilities

The server exposes sixteen MCP tools:

| Tool | Capability |
| --- | --- |
| `check_session_status` | Check trusted-session and 2FA state |
| `list_reminder_lists` | List reminder lists and stable IDs |
| `list_reminders` | List active or completed reminders |
| `get_reminder` | Read one reminder by ID |
| `create_reminder` | Create a reminder, optionally with a parent ID |
| `list_subtasks` | List the immediate children of a parent reminder |
| `create_subtask` | Create a child task in its parent's list |
| `update_reminder` | Change title, notes, due date, priority, flag, or all-day state |
| `set_reminder_completed` | Complete or reopen a reminder |
| `get_reminder_recurrence` | Read recurrence rules |
| `set_reminder_recurrence` | Create or update a daily, weekly, monthly, or yearly rule |
| `clear_reminder_recurrence` | Clear recurrence only when `confirm=true` is supplied |
| `list_reminder_tags` | List hashtags attached to a reminder |
| `add_reminder_tag` | Add a hashtag idempotently |
| `remove_reminder_tag` | Remove a hashtag by ID or exact name |
| `delete_reminder` | Delete only when `confirm=true` is supplied |

Additional behavior:

- Parent/child tasks with dedicated create and list tools
- Daily, weekly, monthly, and yearly recurrence with interval and occurrence limits
- Hashtag creation, lookup, and removal
- Timezone-aware due dates and all-day reminders
- Beijing time (`Asia/Shanghai`, UTC+08:00) for all inputs and outputs
- Apple priority values: `0` none, `1` high, `5` medium, `9` low
- Exact list-name resolution with stable ID support
- Mainland China iCloud endpoints
- Persistent local authentication through pyicloud's keyring/session handling

## Requirements

- Python 3.10 or newer
- An Apple ID with iCloud Reminders enabled
- Interactive access for the initial Apple ID password and 2FA login
- An MCP client that supports stdio servers, such as Codex

Never place an Apple password or 2FA code in source code, MCP configuration, an
environment variable, or an issue. Authentication is performed interactively.

## Windows installation

Open PowerShell:

```powershell
git clone https://github.com/94youshin/icloud-reminders-mcp.git
cd icloud-reminders-mcp

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install .
```

Authenticate interactively:

```powershell
.\.venv\Scripts\icloud.exe auth login --username "your-apple-id@example.com"
```

For an Apple account served from mainland China:

```powershell
.\.venv\Scripts\icloud.exe auth login --username "your-apple-id@example.com" --china-mainland
```

## Linux installation

Install Python's virtual-environment support if your distribution does not
already provide it. On Debian or Ubuntu this is typically:

```bash
sudo apt-get install python3 python3-venv
```

Then install the project:

```bash
git clone https://github.com/94youshin/icloud-reminders-mcp.git
cd icloud-reminders-mcp

python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install .
```

Authenticate interactively:

```bash
./.venv/bin/icloud auth login --username "your-apple-id@example.com"
```

Append `--china-mainland` when required. On a headless Linux host, run the MCP
server and the login command as the same OS user. A secure keyring backend is
recommended so pyicloud can renew an expired session without storing the Apple
password in configuration. Diagnose the active backend with:

```bash
./.venv/bin/python -m keyring diagnose
```

The MCP server can still reuse an already authenticated saved session when no
keyring backend is available. A new login or 2FA challenge always requires an
interactive terminal. Do not expose the MCP server directly to the public
internet.

## Run the server

MCP clients normally start the stdio process automatically. It is not a
standalone HTTP daemon and should not be registered as a public systemd network
service. For a direct smoke test, run the following command; it waits for MCP
messages on standard input.

Windows:

```powershell
.\.venv\Scripts\python.exe -m icloud_reminders_mcp
```

Linux:

```bash
./.venv/bin/python -m icloud_reminders_mcp
```

## Configure Codex on Windows

Add the server to the Codex MCP configuration, using an absolute path:

```toml
[mcp_servers.apple-reminders]
command = "C:/path/to/icloud-reminders-mcp/.venv/Scripts/python.exe"
args = ["-m", "icloud_reminders_mcp"]

[mcp_servers.apple-reminders.env]
ICLOUD_USERNAME = "your-apple-id@example.com"
ICLOUD_CHINA_MAINLAND = "false"
ICLOUD_DEFAULT_REMINDER_LIST = "Reminders"
```

## Configure Codex on Linux

```toml
[mcp_servers.apple-reminders]
command = "/path/to/icloud-reminders-mcp/.venv/bin/python"
args = ["-m", "icloud_reminders_mcp"]

[mcp_servers.apple-reminders.env]
ICLOUD_USERNAME = "your-apple-id@example.com"
ICLOUD_CHINA_MAINLAND = "false"
ICLOUD_DEFAULT_REMINDER_LIST = "Reminders"
```

Restart Codex after updating the configuration. The Apple ID username is not a
secret, but the password and 2FA code must never be added here.

### Environment variables

| Variable | Required | Meaning |
| --- | --- | --- |
| `ICLOUD_USERNAME` | Yes | Apple ID username used by the saved session |
| `ICLOUD_CHINA_MAINLAND` | No | `true` to use mainland China endpoints; defaults to `false` |
| `ICLOUD_DEFAULT_REMINDER_LIST` | No | Stable list ID or exact list title used when a tool omits `list_id` |

If multiple lists exist and no default or `list_id` is supplied, the server
fails safely instead of choosing the wrong list.

## Example requests

- "List my Apple reminder lists."
- "Create an all-day reminder on 31 August in the Work list."
- "Create a parent task named Release v2, then add these rows as child tasks."
- "Repeat this reminder every two weeks, for six occurrences."
- "Add the tags #ReleaseV2 and #InterfaceDesign to this reminder."
- "Mark reminder `REMINDER_ID` completed."
- "Show reminder `REMINDER_ID`, then ask before deleting it."

For due dates, MCP tools accept ISO 8601 and always normalize values to Beijing
time (`Asia/Shanghai`, UTC+08:00). A timestamp without an offset is interpreted
as Beijing time; a timestamp with another offset is converted to Beijing time.
For example, `2026-08-31T10:00:00Z` becomes
`2026-08-31T18:00:00+08:00`. Returned timestamps also use `+08:00`.

## Development and tests

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

The test suite covers list selection, ISO date handling, child-task creation,
recurrence, hashtags, partial updates, completion, deletion confirmation, and a real stdio MCP
initialize/list-tools exchange. Tests use fake iCloud services and do not change
the developer's reminders.

## Security and limitations

- `pyicloud` uses private iCloud web APIs; compatibility is not guaranteed.
- Saved sessions and credentials remain local and must not be committed.
- Deletion requires both user approval at the agent layer and `confirm=true` at
  the MCP tool layer.
- Sessions can expire or require fresh 2FA. Stop the MCP process, rerun
  `icloud auth login`, and restart the MCP client.
- Use stable reminder and list IDs when possible; names can be duplicated.
