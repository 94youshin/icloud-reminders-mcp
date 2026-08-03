import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


EXPECTED_TOOLS = {
    "check_session_status",
    "list_reminder_lists",
    "list_reminders",
    "get_reminder",
    "list_subtasks",
    "create_subtask",
    "create_reminder",
    "update_reminder",
    "set_reminder_completed",
    "get_reminder_recurrence",
    "set_reminder_recurrence",
    "clear_reminder_recurrence",
    "list_reminder_tags",
    "add_reminder_tag",
    "remove_reminder_tag",
    "delete_reminder",
}


async def _list_tools_over_stdio():
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "icloud_reminders_mcp"],
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await session.list_tools()


def test_stdio_server_exposes_expected_tools():
    result = asyncio.run(_list_tools_over_stdio())
    assert {tool.name for tool in result.tools} == EXPECTED_TOOLS
    delete_tool = next(tool for tool in result.tools if tool.name == "delete_reminder")
    assert delete_tool.inputSchema["properties"]["confirm"]["default"] is False
    clear_tool = next(
        tool for tool in result.tools if tool.name == "clear_reminder_recurrence"
    )
    assert clear_tool.inputSchema["properties"]["confirm"]["default"] is False
