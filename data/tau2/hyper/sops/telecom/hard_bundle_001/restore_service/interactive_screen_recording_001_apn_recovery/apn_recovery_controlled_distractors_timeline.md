# APN recovery — controlled distractors (hard replacement)

- 00:00–00:05: The Northline SIM shows `SIM 1 · No service` in SIM manager;
  the status bar carries empty signal bars.
- 00:05–00:10: The turned-off Travel eSIM is opened (`SIM status Off`,
  network selection and access point names `Unavailable`) and backed out of
  without changes.
- 00:10–00:15: The active Northline SIM opens Mobile networks: `SIM status
  Active` next to `Network status No service` — the state that sends the
  walkthrough to the APN settings.
- 00:15–00:20: A hotspot/tethering and VPN detour shows everything off or
  not connected and is backed out of without changes.
- 00:20–00:30: A restart without an APN reset visibly leaves the phone on
  `No service` (clock and battery advance across the reboot).
- 00:30–00:45: Access Point Names shows the stray `Manual APN
  (internet.manual)` selected; `Reset to default` is confirmed in the dialog
  and the toast `Access point names reset to default` lands, with `Northline
  Internet` now selected.
- 00:45–00:56: The walkthrough first rechecks WITHOUT restarting: back on
  Mobile networks the access point already reads `Northline Internet`, yet
  `Network status` visibly stays `No service`. Nothing changes while the
  screen lingers.
- 00:56–01:06: The restart happens (clock and battery advance again) and the
  recheck lands on Mobile networks with `Network status Connected · 5G`.
- 01:06–01:12: The status bar shows full bars and `5G` — the connected close
  that ends the walkthrough.
