"""Tests for the HTTP client against the fake device."""

from __future__ import annotations

import aiohttp
import pytest

from custom_components.netgear_m6.client import (
    NetgearM6AuthError,
    NetgearM6Client,
    NetgearM6CommandError,
    NetgearM6ConnectionError,
)

from .fake_device import PASSWORD, FakeM6


async def test_login_returns_an_admin_document(
    device: FakeM6, session: aiohttp.ClientSession
) -> None:
    """A good password yields the full device document."""
    client = NetgearM6Client(session, device.host, PASSWORD)
    model = await client.async_login()
    assert model["session"]["userRole"] == "Admin"
    assert model["general"]["model"] == "MR6450"


async def test_wrong_password(device: FakeM6, session: aiohttp.ClientSession) -> None:
    """The failed-login redirect is reported as an auth error."""
    client = NetgearM6Client(session, device.host, "nope")
    with pytest.raises(NetgearM6AuthError):
        await client.async_login()


async def test_polling_logs_in_once(
    device: FakeM6, session: aiohttp.ClientSession
) -> None:
    """The session is reused between polls."""
    client = NetgearM6Client(session, device.host, PASSWORD)
    await client.async_get_model()
    await client.async_get_model()
    assert device.logins == 1


async def test_relogin_after_the_device_drops_the_session(
    device: FakeM6, session: aiohttp.ClientSession
) -> None:
    """Someone else logging in kicks us out; the next poll logs in again."""
    client = NetgearM6Client(session, device.host, PASSWORD)
    await client.async_get_model()
    device.drop_sessions()
    model = await client.async_get_model()
    assert model["session"]["userRole"] == "Admin"
    assert device.logins == 2


async def test_unreachable_device(
    socket_enabled: None, session: aiohttp.ClientSession
) -> None:
    """Connection failures are wrapped."""
    client = NetgearM6Client(session, "127.0.0.1:1", PASSWORD)
    with pytest.raises(NetgearM6ConnectionError):
        await client.async_get_model()


async def test_set_applies_the_form(
    device: FakeM6, session: aiohttp.ClientSession
) -> None:
    """Settings are posted as form fields."""
    client = NetgearM6Client(session, device.host, PASSWORD)
    await client.async_set({"power.lpm": "true"})
    assert device.model["power"]["lpm"] is True


async def test_set_rejected_field(
    device: FakeM6, session: aiohttp.ClientSession
) -> None:
    """An errno redirect is a refused command."""
    client = NetgearM6Client(session, device.host, PASSWORD)
    with pytest.raises(NetgearM6CommandError):
        await client.async_set({"lbs.enabled": "true"})


async def test_reboot(device: FakeM6, session: aiohttp.ClientSession) -> None:
    """Reboot posts the shutdown field."""
    client = NetgearM6Client(session, device.host, PASSWORD)
    await client.async_reboot()
    assert device.reboots == 1
