# Customer identity — Care Console walkthrough (controlled-distractor fixture)

- 00:00–00:08: An inbound mobile-data chat opens in the Northline Care Console.
  The workspace shows `Identity not verified`, the Troubleshoot, Usage, Plans,
  and Billing tabs carry lock icons, and a banner reads `Technical support is
  locked. Identify the customer before beginning technical support.`
- 00:08–00:16: The agent clicks the locked Troubleshoot tab anyway; a toast
  answers `Technical support is locked — identify the customer first` and the
  workspace does not change. The agent returns to `Identify customer`.
- 00:16–00:25: In the Identify customer form the agent switches to the
  `Full name` lookup and types `Jordan Lee`, but Search is rejected with
  `Date of birth is required to search by name.` — the search never runs and
  no record opens.
- 00:25–00:36: The lookup succeeds on another path, the match card shows
  `Jordan Lee · C-804219`, and `Verify & link` flips the header chip to
  `Verified · C-804219` with the toast `Identity verified — support tools
  unlocked`. The previously locked tabs lose their lock icons only after the
  customer is identified: identification comes before any technical support.
- 00:36–00:48: Guided troubleshooting starts device-side from the customer's
  reported symptom (`5G signal, apps load on Wi-Fi only`) plus phone checks
  the customer performs in chat (`Mobile data is on`). The Account record card
  stays `Closed` the whole time — phone-side troubleshooting runs before the
  account record is opened.
- 00:48–00:56: The agent opens the unrelated help-center article `Set up
  Wi-Fi Calling` from global search, scrolls it, and closes it; the
  troubleshooting checklist and account state are exactly as before.
- 00:56–01:06: The next checklist step needs carrier-side information (line
  data usage), so the agent confirms `Open account record?` — the record card
  flips to `Open · 1:56 PM` and the carrier-side usage panel loads. The record
  was opened only when the workflow needed carrier-side information.
- 01:06–01:16: The customer asks for usage alerts on the line. The Line
  settings panel holds the write behind `Explain the change and record the
  customer's confirmation before submitting.` — the agent explains the change
  in chat, the customer answers `Yes please.`, and `Record confirmation`
  flips the panel to `Confirmed in chat · 1:57 PM`, enabling Submit.
- 01:16–01:24: `Submit change` completes: the status pill turns `On`, the
  banner reads `Setting updated`, and the activity log records `Usage alerts
  enabled — explained and confirmed`.
