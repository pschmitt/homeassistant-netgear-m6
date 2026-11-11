# Setup

## Requirements

- A Netgear Nighthawk M6 reachable from Home Assistant, with its web admin password.
- Home Assistant 2026.9 or later.

## Adding the device

Add **Netgear Nighthawk M6** under **Settings → Devices & services**. If the
hotspot is offline, the form offers **Save anyway**; the integration connects
when the device comes online. The hotspot's serial number becomes the entry's
unique ID, so changing its IP address later is a **Reconfigure**, not a new entry.

## Single admin session

The device allows one admin login at a time. The integration keeps one session
and signs in again only when the device dropped it, for example because someone
opened the web interface. Poll less often (**Configure → Polling interval**) if
an open web interface keeps getting signed out.

## Traffic counters

The M6's own data-usage counter is unreliable: with no data plan set up it stays
at zero. The device does report the bytes moved in the **current data session**,
but that counter restarts whenever the modem reconnects or the hotspot reboots.

The integration turns those readings into deltas and stores the running totals
in Home Assistant, so they survive reconnects and restarts:

| Sensor | Meaning |
|--------|---------|
| Download / Upload / Traffic today | Resets at local midnight |
| Download / Upload / Traffic this month | Resets on the first of the month |
| Download / Upload total | Lifetime totals, for long-term statistics |

Daily and monthly sensors use the `total` state class with `last_reset`, so the
Energy-style statistics work. Counting starts when the integration first sees the
device; earlier traffic is not known.

## Entities

Disabled-by-default entities are hidden until you enable them.

- **Sensors:** signal bars, LTE and 5G signal quality, bands, network type, operator, cell ID, network code, SIM status, active uplink, Wi-Fi clients, connected clients, temperature, battery (only with a battery fitted).
- **Hidden by default:** RSRQ and RSSI, uptime, session duration, WAN IP, Wi-Fi name, Ethernet speed, modem firmware, SIM PIN state, and the identifiers **IMEI**, **SIM serial number (ICCID)**, **IMSI** and **phone number**.
- **Binary sensors:** mobile data connection, Ethernet uplink, failover, Wi-Fi, roaming.
- **Switches:** airplane mode, mobile data, data roaming, UPnP, VPN passthrough.
- **Select:** power mode (the profiles the device offers).
- **Button:** restart.

The Wi-Fi and Ethernet MAC addresses and the serial number are part of the
device's registry entry. Diagnostics downloads redact all identifiers.

## Turning mobile data off

**Mobile data** and **airplane mode** cut the hotspot's own uplink. The
integration keeps working because it talks to the device over the local network.
