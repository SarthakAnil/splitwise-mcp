"""SPLITWISE_ALLOW_DESTRUCTIVE: the client guard and the tool-registration gate."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from splitwise_mcp.client import SplitwiseClient, WritesDisabledError, is_destructive
from splitwise_mcp.config import Settings, get_settings
from splitwise_mcp.server import mcp
from splitwise_mcp.tools import DESTRUCTIVE_TOOL_NAMES, apply_destructive_gate


def _client(**kwargs: Any) -> SplitwiseClient:
    settings = Settings(splitwise_api_key="k" * 16, **kwargs)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"success": True}))
    return SplitwiseClient(settings=settings, transport=transport)


# -- pure helper ---------------------------------------------------------------


def test_is_destructive() -> None:
    assert is_destructive("/delete_expense/123") is True
    assert is_destructive("delete_group/5") is True
    assert is_destructive("/remove_user_from_group") is True  # no id suffix
    assert is_destructive("/undelete_expense/1") is False  # recovery, not destruction
    assert is_destructive("/create_expense") is False
    assert is_destructive("/delete_expenses_summary") is False  # not a prefix boundary


# -- client guard --------------------------------------------------------------


async def test_delete_refused_when_destructive_off() -> None:
    client = _client(splitwise_allow_writes=True, splitwise_allow_destructive=False)
    with pytest.raises(WritesDisabledError, match="SPLITWISE_ALLOW_DESTRUCTIVE=1"):
        await client.request("POST", "/delete_expense/123")


async def test_delete_allowed_when_destructive_on() -> None:
    client = _client(splitwise_allow_writes=True, splitwise_allow_destructive=True)
    resp = await client.request("POST", "/delete_expense/123")
    assert resp.status_code == 200


async def test_create_still_allowed_with_destructive_off() -> None:
    client = _client(splitwise_allow_writes=True, splitwise_allow_destructive=False)
    resp = await client.request("POST", "/create_expense", data={"cost": "1.00"})
    assert resp.status_code == 200


async def test_destructive_off_still_names_writes_first() -> None:
    # With writes themselves off, the write kill-switch fires before the destructive one.
    client = _client(splitwise_allow_writes=False, splitwise_allow_destructive=False)
    with pytest.raises(WritesDisabledError, match="SPLITWISE_ALLOW_WRITES=1"):
        await client.request("POST", "/delete_expense/123")


# -- tool-registration gate (conftest restores the registry after each test) ---


async def test_destructive_tools_hidden_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPLITWISE_ALLOW_DESTRUCTIVE", raising=False)
    get_settings.cache_clear()
    apply_destructive_gate(mcp)

    names = {tool.name for tool in await mcp.list_tools()}
    assert DESTRUCTIVE_TOOL_NAMES.isdisjoint(names)
    # Non-destructive writes stay registered.
    assert "splitwise_create_expense" in names
    assert "splitwise_undelete_expense" in names


async def test_destructive_tools_listed_when_flag_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPLITWISE_ALLOW_DESTRUCTIVE", "1")
    get_settings.cache_clear()
    apply_destructive_gate(mcp)

    names = {tool.name for tool in await mcp.list_tools()}
    assert DESTRUCTIVE_TOOL_NAMES <= names
