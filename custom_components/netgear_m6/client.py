"""Async client for the Netgear Nighthawk M6's local web API.

The device serves one JSON document (``model.json``) describing its whole
state, and takes form posts on ``/Forms/config`` for logins and commands.

* Every request needs the ``sessionId`` cookie, which the device hands out
  through a redirect. Home Assistant's shared aiohttp session discards cookies,
  so the client needs a session with its own cookie jar (see
  :func:`create_session`).
* Without a login the document is served with the ``Guest`` role and no modem
  data. A successful login redirects to the success URL, a failed one to the
  failure URL with ``loginFailed`` appended.
* Commands carry the anti-CSRF ``secToken`` from the document.

The device tracks a single admin session, so the client keeps one session
alive, serialises all traffic, and only logs in again when the device has
dropped it (for example because someone opened the web UI).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    CONFIG_PATH,
    LOGIN_FAILED_REDIRECT,
    LOGIN_OK_REDIRECT,
    MODEL_PATH,
    REBOOT_FAILED_REDIRECT,
    REBOOT_OK_REDIRECT,
    REQUEST_TIMEOUT,
    ROLE_ADMIN,
    SET_FAILED_REDIRECT,
    SET_OK_REDIRECT,
)

_LOGGER = logging.getLogger(__name__)

_REDIRECTS = frozenset({301, 302, 303, 307, 308})


class NetgearM6Error(Exception):
    """Base class for all client errors."""


class NetgearM6ConnectionError(NetgearM6Error):
    """The device could not be reached or returned something unusable."""


class NetgearM6AuthError(NetgearM6Error):
    """The device rejected the login."""


class NetgearM6CommandError(NetgearM6Error):
    """The device refused a state-changing command."""


def create_session() -> aiohttp.ClientSession:
    """Return a session that keeps the device's cookies.

    ``unsafe=True`` is required because the device is usually addressed by IP.
    """
    return aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))


class NetgearM6Client:
    """Talk to one Nighthawk M6 over its local web API."""

    def __init__(
        self, session: aiohttp.ClientSession, host: str, password: str
    ) -> None:
        self._session = session
        self._host = host
        self._password = password
        self._lock = asyncio.Lock()

    @property
    def host(self) -> str:
        """Return the configured host."""
        return self._host

    async def async_login(self) -> dict[str, Any]:
        """Authenticate and return the device document (validates credentials)."""
        async with self._lock:
            return await self._login()

    async def async_get_model(self) -> dict[str, Any]:
        """Fetch the device document, logging in only when needed."""
        async with self._lock:
            model = await self._fetch_model()
            if not _is_admin(model):
                _LOGGER.debug("No admin session, logging in")
                model = await self._login()
            return model

    async def async_reboot(self) -> None:
        """Reboot the device."""
        async with self._lock:
            model = await self._fetch_model()
            if not _is_admin(model):
                model = await self._login()
            await self._post(
                {
                    "general.shutdown": "restart",
                    "ok_redirect": REBOOT_OK_REDIRECT,
                    "err_redirect": REBOOT_FAILED_REDIRECT,
                },
                model,
                expect_redirect_to=REBOOT_OK_REDIRECT,
            )

    async def async_set(self, values: dict[str, str]) -> None:
        """Change settings. Keys are the form field names of the web UI."""
        async with self._lock:
            model = await self._fetch_model()
            if not _is_admin(model):
                model = await self._login()
            await self._post(
                {
                    **values,
                    "ok_redirect": SET_OK_REDIRECT,
                    "err_redirect": SET_FAILED_REDIRECT,
                },
                model,
                expect_redirect_to=SET_OK_REDIRECT,
                assume_ok_on_disconnect=False,
            )

    async def _login(self) -> dict[str, Any]:
        model = await self._fetch_model()
        location = await self._post_form(
            {
                "ok_redirect": LOGIN_OK_REDIRECT,
                "err_redirect": LOGIN_FAILED_REDIRECT,
                "session.password": self._password,
                "token": _token(model),
            }
        )
        if location is None:
            raise NetgearM6ConnectionError("Device did not answer the login")
        if "loginFailed" in location:
            raise NetgearM6AuthError("Login rejected")
        model = await self._fetch_model()
        if not _is_admin(model):
            raise NetgearM6ConnectionError(
                "Login accepted but the device did not grant an admin session"
            )
        return model

    async def _post(
        self,
        form: dict[str, str],
        model: dict[str, Any],
        *,
        expect_redirect_to: str,
        assume_ok_on_disconnect: bool = True,
    ) -> None:
        form = {**form, "token": _token(model)}
        try:
            location = await self._post_form(form)
        except NetgearM6ConnectionError:
            if not assume_ok_on_disconnect:
                raise
            # A rebooting device drops the connection instead of answering.
            _LOGGER.debug("Device dropped the connection, assuming the command ran")
            return
        if location is None or expect_redirect_to not in location:
            raise NetgearM6CommandError(f"Command refused (redirected to {location})")

    async def _fetch_model(self) -> dict[str, Any]:
        url = f"http://{self._host}{MODEL_PATH}"
        try:
            async with self._session.get(
                url, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise NetgearM6ConnectionError(f"GET model.json failed: {err}") from err
        if not isinstance(payload, dict):
            raise NetgearM6ConnectionError("model.json is not a JSON object")
        return payload

    async def _post_form(self, form: dict[str, str]) -> str | None:
        """POST to the config endpoint and return the redirect target."""
        url = f"http://{self._host}{CONFIG_PATH}"
        try:
            async with self._session.post(
                url,
                data=form,
                allow_redirects=False,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                if response.status not in _REDIRECTS:
                    response.raise_for_status()
                return response.headers.get("Location")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise NetgearM6ConnectionError(f"POST {CONFIG_PATH} failed: {err}") from err


def _is_admin(model: dict[str, Any]) -> bool:
    session = model.get("session")
    return isinstance(session, dict) and session.get("userRole") == ROLE_ADMIN


def _token(model: dict[str, Any]) -> str:
    session = model.get("session")
    token = session.get("secToken") if isinstance(session, dict) else None
    if not token:
        raise NetgearM6ConnectionError("Device did not provide a session token")
    return str(token)
