# Netgear Nighthawk M6 integration

- Local-polling integration for the Netgear Nighthawk M6 (MR6450) 5G/LTE hotspot. No cloud.
- The device allows **one** admin session. Keep a single long-lived session in
  `NetgearM6Client`; never log in on every poll, and serialise all traffic.
- The shared Home Assistant `aiohttp` session discards cookies. The integration builds
  its own session with `CookieJar(unsafe=True)`; the config flow uses `create_session()`.
- Keep the admin password and device identifiers (serial, IMEI, ICCID, IMSI, phone number,
  MACs) out of logs, diagnostics and test fixtures. Redact them in `diagnostics.py`.
- The device's own data-usage counter reads zero. Traffic totals come from
  `TrafficTracker` (session deltas stored in HA storage); keep its reset handling.
- Settings are posted as web-UI form fields; see `docs/protocol.md` for the verified list.
  Verify a new field on the device with a no-op write before adding an entity for it.
- Use native HA config, reauth, reconfigure and options flows. Entities use
  `translation_key`; add every new string to `strings.json`, `translations/en.json`
  and `translations/de.json`, and icons to `icons.json`.
- Tests run against a fake device (`tests/fake_device.py`) over real HTTP. Extend it
  when adding endpoints rather than mocking client methods.
- Test gotchas: scheduled coordinator refreshes run as background tasks, so use
  `freezer.tick(...)`, `async_fire_time_changed(hass)` and
  `await hass.async_block_till_done(wait_background_tasks=True)`; tests that open
  sockets need the `socket_enabled` fixture.
- Home Assistant 2026.9+ uses `probatio` (voluptuous-compatible) for schemas; import
  it as `vol` in flows.
- Run `just` (format, lint, typecheck, test) before committing. Run it on an ad-hoc
  build worker, not on the local agent host.
- Version releases with integers (`manifest.json` and `pyproject.toml`).
- Make focused commits on main; do not open pull requests unless requested.

## CI

- CI runs `uv sync --locked`, Ruff formatting and lint checks, Pyright, pytest, and Hassfest.
- Before changing CI, check [pschmitt/ci-workflows](https://github.com/pschmitt/ci-workflows) for reusable components and preserve these checks.
