# iCloud Reminders MCP

`icloud-reminders-mcp` is a cross-platform Model Context Protocol (MCP) server
for Apple Reminders. It uses the maintained `pyicloud` package and iCloud's
CloudKit v2 reminders service, so Windows and Linux machines can manage reminders
without macOS, AppleScript, or browser automation.

> This is an unofficial iCloud integration. Apple does not publish a stable
> Reminders API, so an iCloud service change can require a project update.

## Capabilities

The server exposes eight MCP tools:

| Tool | Capability |
| --- | --- |
| `check_session_status` | Check trusted-session and 2FA state |
| `list_reminder_lists` | List reminder lists and stable IDs |
| `list_reminders` | List active or completed reminders |
| `get_reminder` | Read one reminder by ID |
| `create_reminder` | Create reminders and child tasks |
| `update_reminder` | Change title, notes, due date, priority, flag, or all-day state |
| `set_reminder_completed` | Complete or reopen a reminder |
| `delete_reminder` | Delete only when `confirm=true` is supplied |

Additional behavior:

- Parent/child tasks through `parent_reminder_id`
- Timezone-aware due dates and all-day reminders
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
.\.venv\Scripts\python.exe -m pip install -e .
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
./.venv/bin/python -m pip install -e .
```

Authenticate interactively:

```bash
./.venv/bin/icloud auth login --username "your-apple-id@example.com"
```

Append `--china-mainland` when required. A headless Linux host must have a
usable keyring backend and an interactive terminal for the initial login and
2FA. Do not expose the MCP server directly to the public internet.

## Run the server

MCP clients normally start the stdio process automatically. For a direct smoke
test, run the following command; it waits for MCP messages on standard input.

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

- “List my Apple reminder lists.”
- “Create an all-day reminder on 31 August in the Work list.”
- “Create a parent task named Release v2, then add these rows as child tasks.”
- “Mark reminder `…` completed.”
- “Show reminder `…`, then ask before deleting it.”

For due dates, MCP tools accept ISO 8601. Prefer an explicit timezone, for
example `2026-08-31T18:00:00+08:00`.

## Development and tests

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

The test suite covers list selection, ISO date handling, child-task creation,
partial updates, completion, deletion confirmation, and a real stdio MCP
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
