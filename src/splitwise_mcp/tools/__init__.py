"""Tool registration for splitwise_mcp.

ALL wave modules are listed here from day one (even while some are still empty
stubs) so that parallel worktrees implementing individual modules never need to
touch this file — eliminating merge conflicts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from mcp.server.fastmcp.tools.base import Tool

# Destructive tools, gated behind SPLITWISE_ALLOW_DESTRUCTIVE on top of the write
# kill-switch. They self-register with every other tool on import; `apply_destructive_gate`
# drops them again unless the flag is on, so list_tools() never offers them.
DESTRUCTIVE_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "splitwise_delete_expense",
        "splitwise_delete_group",
        "splitwise_delete_friend",
        "splitwise_delete_comment",
        "splitwise_remove_user_from_group",
    }
)

# The destructive Tool objects captured by register_all (when all are present), so the
# gate can restore them after a test toggles the flag back on.
_destructive_tools: dict[str, Tool] = {}


def register_all(mcp: FastMCP) -> None:
    """Import every tool module; @mcp.tool decorators self-register on import."""
    from splitwise_mcp.tools import (  # noqa: F401
        balances,
        comments,
        expenses,
        friends,
        groups,
        health,
        lookup,
        notifications,
        users,
    )

    manager = mcp._tool_manager  # noqa: SLF001 — the SDK exposes no public per-tool registry
    for name in DESTRUCTIVE_TOOL_NAMES:
        tool = manager.get_tool(name)
        if tool is not None:
            _destructive_tools[name] = tool


def apply_destructive_gate(mcp: FastMCP) -> None:
    """Register the destructive tools only when SPLITWISE_ALLOW_DESTRUCTIVE is on.

    Called from the stdio/http entry points so a running server omits them by default;
    re-callable in tests (after changing the flag and clearing the settings cache) to
    exercise both states.
    """
    from splitwise_mcp.config import get_settings

    allow = get_settings().splitwise_allow_destructive
    manager = mcp._tool_manager  # noqa: SLF001
    for name, tool in _destructive_tools.items():
        present = manager.get_tool(name) is not None
        if allow and not present:
            manager._tools[name] = tool  # noqa: SLF001
        elif not allow and present:
            mcp.remove_tool(name)
