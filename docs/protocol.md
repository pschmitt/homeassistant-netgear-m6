# Local protocol

Reverse-engineered from the device's web interface; verified on an MR6450
(firmware NTGX65_12.01.74.00).

## Session

Every request needs the `sessionId` cookie. The device hands it out through a
redirect (`/sess_cd_tmp`), so the client needs a cookie jar of its own: Home
Assistant's shared aiohttp session discards cookies. Because the device is
usually addressed by IP, the jar must be created with `unsafe=True`.

## Reading state

`GET /model.json?internalapi=1` returns one JSON document with the whole device
state. Without a login, the document only carries `session` (`userRole: Guest`).
After a login `session.userRole` is `Admin` and every section is present. The
client treats "not Admin" as a lost session and logs in again.

## Logging in

1. `GET /model.json?internalapi=1` and read `session.secToken`.
2. `POST /Forms/config` with `token`, `session.password`, `ok_redirect` and
   `err_redirect`, without following redirects.
3. A failed login redirects to `err_redirect` with `errno` and `errdetail`
   appended; a good login redirects to `ok_redirect`.

## Changing settings

`POST /Forms/config` with the web interface's form field names plus a current
`token`, `ok_redirect` and `err_redirect`. The device answers with a redirect:
`ok_redirect` on success, `err_redirect?errno=…&errdetail=<field>` when it
refuses a field. Values are `"true"`/`"false"` strings. New state shows in
`model.json` right away.

| Setting | Form field | State |
|---------|-----------|-------|
| Airplane mode | `power.lpm` | `power.lpm` |
| Mobile data | `wwan.domesticdata` | `wwan.autoconnect` |
| Data roaming | `wwan.intlroaming` | `wwan.autoconnect` |
| UPnP | `router.UPNPenabled` | `router.UPNPenabled` |
| VPN passthrough | `router.VPNpassthrough` | `router.VPNpassthrough` |
| Power mode | `powermanager.profile` | `power.profileCurrent` |

Mobile data and roaming share one form and are posted together. The state is
`wwan.autoconnect`: `Never` (neither), `HomeNetwork` (data only), `RoamNetwork`
(roaming only) and `Always` (both).

## Restart

`POST /Forms/config` with `general.shutdown=restart`. The device may drop the
connection instead of answering while it reboots, which the client treats as
success. This command is not verified on hardware.

## Traffic

`wwan.dataTransferredRx` and `wwan.dataTransferredTx` count bytes of the current
data session, with `wwan.sessStartTime` identifying it. The billing-cycle counter
under `wwan.dataUsage` reads zero when no plan is configured.
