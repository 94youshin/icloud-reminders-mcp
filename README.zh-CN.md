# iCloud Reminders MCP

[English](README.md) | 简体中文

`icloud-reminders-mcp` 是一个跨平台的 Apple 提醒事项 Model Context
Protocol（MCP）服务。它基于持续维护的 `pyicloud` 和 iCloud CloudKit v2
提醒事项服务，使 Windows 和 Linux 电脑无需 macOS、AppleScript 或浏览器自动化，
也能管理 Apple 提醒事项。

> 这是非官方的 iCloud 集成。Apple 没有公开稳定的提醒事项 API；如果 Apple
> 调整 iCloud 服务，本项目可能需要同步适配。

## 功能

服务提供 8 个 MCP 工具：

| 工具 | 能力 |
| --- | --- |
| `check_session_status` | 检查受信任会话及双重认证状态 |
| `list_reminder_lists` | 查询提醒事项列表及稳定 ID |
| `list_reminders` | 查询未完成或已完成的提醒事项 |
| `get_reminder` | 根据 ID 读取单条提醒事项 |
| `create_reminder` | 创建提醒事项或子任务 |
| `update_reminder` | 修改标题、备注、时间、优先级、旗标或全天状态 |
| `set_reminder_completed` | 完成提醒事项或将其重新打开 |
| `delete_reminder` | 仅当传入 `confirm=true` 时删除提醒事项 |

其他能力：

- 通过 `parent_reminder_id` 创建父任务和子任务
- 支持带时区的截止时间和全天提醒
- 支持 Apple 优先级：`0` 无、`1` 高、`5` 中、`9` 低
- 支持按列表稳定 ID 或精确名称选择列表
- 支持中国大陆 iCloud 服务端点
- 通过 pyicloud 的系统密钥环和会话机制持久化本地登录状态

## 环境要求

- Python 3.10 或更高版本
- 已启用 iCloud 提醒事项的 Apple ID
- 首次登录时能够在交互式终端输入密码并完成双重认证
- 支持 stdio MCP 服务的客户端，例如 Codex

不要把 Apple ID 密码或双重认证验证码写入源代码、MCP 配置、环境变量或
GitHub Issue。认证应始终在本地交互式终端中完成。

## Windows 安装

打开 PowerShell：

```powershell
git clone https://github.com/94youshin/icloud-reminders-mcp.git
cd icloud-reminders-mcp

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

交互式登录 iCloud：

```powershell
.\.venv\Scripts\icloud.exe auth login --username "your-apple-id@example.com"
```

如果 Apple 账户使用中国大陆 iCloud 服务：

```powershell
.\.venv\Scripts\icloud.exe auth login --username "your-apple-id@example.com" --china-mainland
```

按终端提示输入密码并完成双重认证。登录成功后，pyicloud 会在本机保存会话，
后续由 MCP 服务复用。

## Linux 安装

如果 Linux 发行版没有安装虚拟环境组件，需要先安装。Debian 或 Ubuntu 通常执行：

```bash
sudo apt-get install python3 python3-venv
```

然后安装项目：

```bash
git clone https://github.com/94youshin/icloud-reminders-mcp.git
cd icloud-reminders-mcp

python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e .
```

交互式登录 iCloud：

```bash
./.venv/bin/icloud auth login --username "your-apple-id@example.com"
```

中国大陆账户需要追加 `--china-mainland`。无桌面的 Linux 主机必须配置可用的
密钥环后端，并在首次登录和双重认证时提供交互式终端。不要把 MCP 服务直接暴露到
公网。

## 运行 MCP 服务

通常由 MCP 客户端自动启动 stdio 进程。也可以使用以下命令进行启动检查；进程启动后
会等待从标准输入接收 MCP 消息。

Windows：

```powershell
.\.venv\Scripts\python.exe -m icloud_reminders_mcp
```

Linux：

```bash
./.venv/bin/python -m icloud_reminders_mcp
```

也可以在虚拟环境中直接使用安装生成的 `icloud-reminders-mcp` 命令。

## Windows 下配置 Codex

在 Codex MCP 配置中添加以下内容，并使用实际的绝对路径：

```toml
[mcp_servers.apple-reminders]
command = "C:/path/to/icloud-reminders-mcp/.venv/Scripts/python.exe"
args = ["-m", "icloud_reminders_mcp"]

[mcp_servers.apple-reminders.env]
ICLOUD_USERNAME = "your-apple-id@example.com"
ICLOUD_CHINA_MAINLAND = "false"
ICLOUD_DEFAULT_REMINDER_LIST = "提醒事项"
```

## Linux 下配置 Codex

```toml
[mcp_servers.apple-reminders]
command = "/path/to/icloud-reminders-mcp/.venv/bin/python"
args = ["-m", "icloud_reminders_mcp"]

[mcp_servers.apple-reminders.env]
ICLOUD_USERNAME = "your-apple-id@example.com"
ICLOUD_CHINA_MAINLAND = "false"
ICLOUD_DEFAULT_REMINDER_LIST = "提醒事项"
```

修改配置后重启 Codex。Apple ID 用户名本身不是密码，但绝对不要把 Apple ID 密码
或双重认证验证码写入这里。

### 环境变量

| 变量 | 是否必填 | 说明 |
| --- | --- | --- |
| `ICLOUD_USERNAME` | 是 | 与本地已保存会话对应的 Apple ID 用户名 |
| `ICLOUD_CHINA_MAINLAND` | 否 | 使用中国大陆端点时设为 `true`，默认为 `false` |
| `ICLOUD_DEFAULT_REMINDER_LIST` | 否 | 工具未传 `list_id` 时使用的列表 ID 或精确名称 |

如果账户中存在多个列表，并且没有配置默认列表或传入 `list_id`，服务会安全地返回
错误，而不会自行选择一个可能错误的列表。

## 使用示例

- “查询我的 Apple 提醒事项列表。”
- “在工作列表中创建一个 8 月 31 日的全天提醒。”
- “创建一个名为‘发布 v2’的父任务，然后把这些工作逐条创建为子任务。”
- “把指定 ID 的提醒事项标记为已完成。”
- “先显示指定提醒事项，得到我确认后再删除。”

截止时间使用 ISO 8601 格式，建议包含明确时区，例如：
`2026-08-31T18:00:00+08:00`。

## 开发和测试

安装开发依赖并运行测试：

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

测试覆盖列表选择、ISO 时间解析、子任务创建、局部更新、完成提醒、删除确认，
以及真实的 stdio MCP 初始化和工具发现流程。测试使用模拟 iCloud 服务，不会修改
开发者账户中的真实提醒事项。

## 安全和限制

- `pyicloud` 使用非公开的 iCloud Web API，无法保证长期兼容。
- 已保存的会话和凭据必须留在本机，不能提交到 Git。
- 删除操作同时要求 Agent 层获得用户同意，并要求 MCP 工具传入 `confirm=true`。
- 会话可能过期或重新要求双重认证。此时停止 MCP 进程，重新执行
  `icloud auth login`，然后重启 MCP 客户端。
- 列表名称和提醒标题可能重复，条件允许时优先使用稳定 ID。
