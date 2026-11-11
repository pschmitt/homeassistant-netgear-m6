"""A fake Nighthawk M6 that speaks the real device's HTTP protocol.

It mirrors what the device does, as observed on hardware: a cookie handshake
through ``/sess_cd_tmp``, the ``Guest`` role until a login succeeds, redirects
for every form post and ``errno`` on rejected fields.
"""

from __future__ import annotations

import copy
from typing import Any

from aiohttp import web

PASSWORD = "s3cret-pw"
SESSION_COOKIE = "sessionId"
TOKEN = "tok-123"


def base_model() -> dict[str, Any]:
    """Return a device document with the shape of a real 5G session."""
    return {
        "session": {"userRole": "Guest", "secToken": TOKEN},
        "general": {
            "FSN": "FSN0000000001",
            "IMEI": "350000000000001",
            "SVN": "19",
            "model": "MR6450",
            "FWversion": "NTGX65_12.01.74.00",
            "HWversion": "1.0",
            "modemFwVersion": "MPSS.TEST-1.0",
            "devTemperature": 53,
            "upTime": 1860000,
            "LEDenabled": True,
        },
        "wwan": {
            "connection": "Connected",
            "connectionText": "5G",
            "registerNetworkDisplay": "Test Telecom",
            "roamingType": "Home",
            "thermalState": "Normal",
            "IP": "10.1.2.3",
            "autoconnect": "HomeNetwork",
            "sessStartTime": 1_000_000,
            "sessDuration": 3600,
            "dataTransferredRx": "2147483648",
            "dataTransferredTx": "1073741824",
            "signalStrength": {
                "bars": 4,
                "rssi": -65,
                "rsrp": -102,
                "rsrq": -16,
                "sinr": 5,
                "rscp": -32768,
                "nr5gRsrp": -94,
                "nr5gRsrq": -11,
                "nr5gSinr": 18,
            },
            "lteBandInfo": [
                {"band": 1, "isPcc": False},
                {"band": 3, "isPcc": True},
                {"band": None},
            ],
            "nr5gBandInfo": [{"band": 78, "isPcc": True}, {"band": None}],
        },
        "wwanadv": {"cellId": 1234567, "MCC": "262", "MNC": "07"},
        "sim": {
            "iccid": "8949000000000000001",
            "imsi": "262070000000001",
            "phoneNumber": "491700000001",
            "status": "Ready",
            "pin": {"mode": "Disabled"},
        },
        "power": {
            "lpm": False,
            "batteryState": "NoBattery",
            "battChargeLevel": 0,
            "batteryTemperature": -99,
            "profileCurrent": "0",
            "profileList": [
                {"id": "0", "name": "Balanced", "label": "Balanced"},
                {"id": "1", "name": "Performance", "label": "Performance"},
                {"id": "2", "name": "ACPowered", "label": "Plugged in"},
                {"id": None, "name": None, "label": None},
            ],
        },
        "router": {
            "UPNPenabled": True,
            "VPNpassthrough": True,
            "clientList": [
                {"IP": "192.168.1.10", "name": "laptop"},
                {"IP": "192.168.1.11", "name": "phone"},
                {},
            ],
        },
        "wifi": {
            "MAC": "AA:BB:CC:00:00:01",
            "SSID": "TestNet",
            "enabled": True,
            "clientCount": 2,
        },
        "ethernet": {"mac": "AA:BB:CC:00:00:02", "speedMax": "2500M"},
        "failover": {"enabled": True, "backhaul": "LTE", "wanConnected": True},
    }


class FakeM6:
    """The fake device and its HTTP application."""

    def __init__(self) -> None:
        self.host = ""
        self.password = PASSWORD
        self.model = base_model()
        self.sessions: set[str] = set()
        self.logins = 0
        self.reboots = 0
        self.posts: list[dict[str, str]] = []
        self.fail_requests = False
        self.app = web.Application()
        self.app.router.add_get("/model.json", self._model)
        self.app.router.add_get("/sess_cd_tmp", self._sess)
        self.app.router.add_post("/Forms/config", self._config)

    # -- test helpers ------------------------------------------------------
    def drop_sessions(self) -> None:
        """Forget every login, like the device does when someone else logs in."""
        self.sessions.clear()

    # -- handlers ----------------------------------------------------------
    def _session_id(self, request: web.Request) -> str | None:
        return request.cookies.get(SESSION_COOKIE)

    async def _sess(self, request: web.Request) -> web.Response:
        response = web.HTTPFound("/model.json?internalapi=1")
        response.set_cookie(SESSION_COOKIE, "guest-1")
        raise response

    async def _model(self, request: web.Request) -> web.Response:
        if self.fail_requests:
            raise web.HTTPInternalServerError
        sid = self._session_id(request)
        if sid is None:
            raise web.HTTPFound("/sess_cd_tmp?op=/model.json")
        model = copy.deepcopy(self.model)
        if sid in self.sessions:
            model["session"]["userRole"] = "Admin"
        else:
            # Guests only get the session block.
            model = {"session": model["session"]}
        return web.json_response(model)

    async def _config(self, request: web.Request) -> web.Response:
        form = dict(await request.post())  # type: ignore[arg-type]
        sid = self._session_id(request)
        ok = str(form.get("ok_redirect", "/ok"))
        err = str(form.get("err_redirect", "/err"))
        self.posts.append(
            {k: str(v) for k, v in form.items() if k != "session.password"}
        )
        if form.get("token") != TOKEN:
            raise web.HTTPBadRequest
        if "session.password" in form:
            if form["session.password"] != self.password or sid is None:
                raise web.HTTPFound(f"{err}&errno=2&errdetail=session%2Epassword")
            self.logins += 1
            self.sessions.add(sid)
            raise web.HTTPFound(ok)
        if sid not in self.sessions:
            raise web.HTTPFound(f"{err}?errno=5")
        if "general.shutdown" in form:
            self.reboots += 1
            raise web.HTTPFound(ok)
        for key, value in form.items():
            if key in ("token", "ok_redirect", "err_redirect"):
                continue
            if not self._apply(key, str(value)):
                raise web.HTTPFound(f"{err}?errno=2&errdetail={key}")
        raise web.HTTPFound(ok)

    def _apply(self, key: str, value: str) -> bool:
        flag = value == "true"
        model = self.model
        if key == "power.lpm":
            model["power"]["lpm"] = flag
        elif key == "router.UPNPenabled":
            model["router"]["UPNPenabled"] = flag
        elif key == "router.VPNpassthrough":
            model["router"]["VPNpassthrough"] = flag
        elif key == "powermanager.profile":
            model["power"]["profileCurrent"] = value
        elif key == "wwan.domesticdata":
            self._pending_data = flag
        elif key == "wwan.intlroaming":
            data = getattr(self, "_pending_data", False)
            model["wwan"]["autoconnect"] = {
                (False, False): "Never",
                (True, False): "HomeNetwork",
                (False, True): "RoamNetwork",
                (True, True): "Always",
            }[(data, flag)]
        else:
            return False
        return True
