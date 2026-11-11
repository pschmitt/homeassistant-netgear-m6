"""Constants for the Netgear Nighthawk M6 integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "netgear_m6"

DEFAULT_HOST: Final = "192.168.1.1"
DEFAULT_TITLE: Final = "Netgear Nighthawk M6"
MANUFACTURER: Final = "Netgear"

CONF_SCAN_INTERVAL: Final = "scan_interval"
DEFAULT_SCAN_INTERVAL: Final = 60
MIN_SCAN_INTERVAL: Final = 15
MAX_SCAN_INTERVAL: Final = 3600

REQUEST_TIMEOUT: Final = 10

MODEL_PATH: Final = "/model.json?internalapi=1"
CONFIG_PATH: Final = "/Forms/config"

LOGIN_OK_REDIRECT: Final = "/index.html"
LOGIN_FAILED_REDIRECT: Final = "/index.html?loginFailed"
REBOOT_OK_REDIRECT: Final = "/error.json"
REBOOT_FAILED_REDIRECT: Final = "/success.json"
SET_OK_REDIRECT: Final = "/ok.json"
SET_FAILED_REDIRECT: Final = "/err.json"

ROLE_ADMIN: Final = "Admin"

# The firmware reports this sentinel for signal values it does not have.
INVALID_SIGNAL: Final = -32768

STORAGE_VERSION: Final = 1

# wwan.autoconnect values: which kinds of mobile data the device may use.
AUTOCONNECT_NEVER: Final = "Never"
AUTOCONNECT_HOME: Final = "HomeNetwork"
AUTOCONNECT_ROAMING: Final = "RoamNetwork"
AUTOCONNECT_ALWAYS: Final = "Always"
