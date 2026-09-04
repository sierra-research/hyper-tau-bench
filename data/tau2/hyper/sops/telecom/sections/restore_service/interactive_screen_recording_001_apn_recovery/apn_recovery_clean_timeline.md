# APN recovery — clean fixture

- 00:00–00:05: SIM manager shows the Northline SIM enabled while the phone has
  no service; the status bar shows empty signal bars.
- 00:05–00:10: The Northline Mobile networks screen shows SIM status `Active`
  with Network status `No service`, and the flow proceeds into Access Point
  Names.
- 00:10–00:15: The Access Point Names list shows the selected APN
  `internet.manual`, a manual entry that does not match the unselected carrier
  default `Northline Internet (northline)`.
- 00:15–00:20: Reset to default is confirmed in the reset dialog; the carrier
  default `Northline Internet (northline)` becomes selected and the manual APN
  is removed.
- 00:20–00:25: The phone reboots (`Restarting…`) to apply the reset and rerun
  network search.
- 00:25–00:30: After the reboot the status bar shows connected 5G service and
  Network status reads `Connected · 5G`, resolving the case.
