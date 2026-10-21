"""Tool registration for splitwise_mcp.

ALL wave modules are listed here from day one (even while some are still empty
stubs) so that parallel worktrees implementing individual modules never need to
touch this file — eliminating merge conflicts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

# Hidden unless SPLITWISE_ALLOW_DESTRUCTIVE is on (on top of the write kill-switch).
DESTRUCTIVE_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "splitwise_delete_expense",
        "splitwise_delete_group",
        "splitwise_delete_friend",
        "splitwise_delete_comment",
        "splitwise_remove_user_from_group",
    }
)


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


def apply_destructive_gate(mcp: FastMCP) -> None:
    """Unregister the destructive tools unless SPLITWISE_ALLOW_DESTRUCTIVE is on.

    Called once from the stdio/http entry points, so the model never sees them by default.
    """
    from splitwise_mcp.config import get_settings

    if get_settings().splitwise_allow_destructive:
        return
    for name in DESTRUCTIVE_TOOL_NAMES:
        if mcp._tool_manager.get_tool(name) is not None:  # noqa: SLF001 — no public lookup
            mcp.remove_tool(name)
