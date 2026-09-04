# APN recovery — controlled-distractor fixture

- 00:00–00:05: SIM manager shows the Northline SIM enabled while the phone has
  no service; the status bar shows empty signal bars.
- 00:05–00:10: The user opens the wrong, turned-off Travel eSIM; its network
  settings are unavailable and the user backs out without changing anything.
- 00:10–00:15: The affected Northline Mobile networks screen shows SIM status
  `Active` with Network status `No service`.
- 00:15–00:20: The user detours through Connections into Mobile Hotspot and
  Tethering; hotspot, tethering, and VPN are all off or not connected, and the
  user backs out without changing anything.
- 00:20–00:25: The user reboots without having opened or reset the APN
  settings.
- 00:25–00:30: After the reboot the SIM manager still shows `No service`, so
  the restart-only attempt visibly failed.
- 00:30–00:35: The user returns through the Northline Mobile networks screen
  into Access Point Names, where the selected APN `internet.manual` does not
  match the unselected carrier default `Northline Internet (northline)`.
- 00:35–00:40: Reset to default is confirmed in the reset dialog; the carrier
  default `Northline Internet (northline)` becomes selected and the manual APN
  is removed.
- 00:40–00:45: The phone reboots again (`Restarting…`) to apply the reset and
  rerun network search.
- 00:45–00:50: The status bar shows connected 5G service and Network status
  reads `Connected · 5G`, resolving the case.
