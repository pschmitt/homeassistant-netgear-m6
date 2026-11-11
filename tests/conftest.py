"""Shared fixtures."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from unittest.mock import patch

import aiohttp
import pytest
from aiohttp.test_utils import TestServer
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.netgear_m6.const import DOMAIN

from .fake_device import PASSWORD, FakeM6


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow the integration under test to load."""


@pytest.fixture
async def device(socket_enabled: None) -> AsyncGenerator[FakeM6]:
    """Run a fake Nighthawk M6 on a local port."""
    fake = FakeM6()
    server = TestServer(fake.app)
    await server.start_server()
    fake.host = f"{server.host}:{server.port}"
    yield fake
    await server.close()


@pytest.fixture
async def session() -> AsyncGenerator[aiohttp.ClientSession]:
    """A session with its own cookie jar, like the one the integration builds."""
    async with aiohttp.ClientSession(
        cookie_jar=aiohttp.CookieJar(unsafe=True)
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def patch_clientsession(session: aiohttp.ClientSession) -> Generator[None]:
    """Make the integration use the test session."""
    with patch(
        "custom_components.netgear_m6.async_create_clientsession",
        return_value=session,
    ):
        yield


@pytest.fixture
def mock_entry(device: FakeM6) -> MockConfigEntry:
    """A config entry pointing at the fake device."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Netgear Nighthawk M6",
        unique_id="FSN0000000001",
        data={CONF_HOST: device.host, CONF_PASSWORD: PASSWORD},
    )
