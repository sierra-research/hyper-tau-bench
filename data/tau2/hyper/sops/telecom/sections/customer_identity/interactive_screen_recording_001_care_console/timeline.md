# Customer identity — Care Console walkthrough (controlled-distractor fixture)

- 00:00–00:08: An inbound mobile-data chat opens in the Northline Care Console.
  The workspace shows `Identity not verified`, the Troubleshoot, Usage, Plans,
  and Billing tabs carry lock icons, and a banner reads `Technical support is
  locked. Identify the customer before beginning technical support.`
- 00:08–00:17: In the Identify customer form the agent switches to the
  `Full name` lookup and types `Jordan Lee`, but Search is rejected with
  `Date of birth is required to search by name.` — the search never runs and
  no record opens.
- 00:17–00:28: The lookup succeeds on another path, the match card shows
  `Jordan Lee · C-804219`, and `Verify & link` flips the header chip to
  `Verified · C-804219` with the toast `Identity verified — support tools
  unlocked`. The previously locked tabs lose their lock icons only after the
  customer is identified: identification comes before any technical support.
- 00:28–00:40: Guided troubleshooting starts device-side from the customer's
  reported symptom (`5G signal, apps load on Wi-Fi only`) plus phone checks
  the customer performs in chat (`Mobile data is on`). The Account record card
  stays `Closed` the whole time — phone-side troubleshooting runs before the
  account record is opened.
- 00:40–00:48: The agent opens the unrelated help-center article `Set up
  Wi-Fi Calling` from global search, scrolls it, and closes it; the
  troubleshooting checklist and account state are exactly as before.
- 00:48–00:56: The next checklist step needs carrier-side information (line
  data usage), so the agent confirms `Open account record?` — the record card
  flips to `Open · 1:56 PM` and the carrier-side usage panel loads. The record
  was opened only when the workflow needed carrier-side information.
