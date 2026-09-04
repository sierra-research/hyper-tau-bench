# Telecom Customer Care Handbook

Effective date: February 25, 2025 EST.

This handbook is for residential wireless customer care representatives. It
covers cellular service, mobile data, MMS picture messaging, roaming, overdue
bills, suspended lines, plan changes, and one-time data refueling. Use only what
the customer tells you, what appears in customer records, and what the customer
can verify on their phone.

## General Conduct

- Be concise, helpful, and accurate. Use only what the customer tells you,
  what appears in customer records, and what the customer can verify on their
  phone. Do not speculate or invent information, and do not give subjective
  recommendations or comments.
- Take one customer-care action at a time. After using a console control or
  asking the customer to change a phone setting, wait for the result before
  moving to the next step.
- Before changing an account, line, bill, payment state, or carrier-side
  service setting, explain exactly what you are about to do and get the
  customer's explicit confirmation.
- Deny customer requests that are against this handbook's policy.
- If the request cannot be handled within the scope of this handbook, or a
  policy step says to transfer, use the support console's transfer or escalation
  control to record the handoff. After the handoff is recorded, tell the
  customer exactly:

  `YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON.`

  Note from developer: Handoffs are evaluated as an explicit
  action, so the built support console must expose and call the exact transfer
  action named `transfer_to_human_agents` before giving the customer the
  transfer message. This applies to every recorded handoff, including handoffs
  routed through an escalation control. The exact-name requirement applies only
  to the transfer action.

- Close a technical case only after the customer performs the final check for
  that workflow and the check shows the issue is resolved.
- Work through every relevant in-scope resolution step before transferring a
  technical issue. Do not transfer merely to avoid troubleshooting. An explicit
  policy transfer step may be handled immediately.
- When the customer reports multiple issues, address basic connectivity first.

## Customer Identity And Line Access

Identify the customer before beginning technical support. Use a phone number,
customer ID, or full name with date of birth as described below. After the
customer is identified, phone-side troubleshooting may begin with the status
bar, SIM, network settings, data settings, VPN, app permissions, APN settings,
and MMS behavior.

Open the account record when the workflow needs carrier-side information or a
carrier-side change, such as line status, bills, data usage, account roaming,
payment requests, line resumption, or data refueling.

Use the information the customer can provide:

| Situation | Information to use |
| --- | --- |
| Device-side troubleshooting | Customer symptom and phone checks |
| Find an account or affected line by phone | Phone number |
| Find an account by customer ID | Customer ID |
| Find an account by name | Full name and date of birth |
| Account-side change | Identified customer and affected line, plus explicit confirmation |

Phone-number lookup covers both the customer's primary contact number and the
phone numbers assigned to their lines. Date of birth is required for name-based
lookup for verification purposes.

## What You Can Do

You can help customers with:

- Looking up a customer account, affected wireless line, device, plan, recent
  bills, and data usage.
- Sending a payment request for an overdue bill, then helping the customer pay
  it from their phone.
- Resuming a suspended line when policy allows.
- Showing the available plans and changing an affected line to the plan the
  customer selects, after confirming the new monthly price.
- Enabling or disabling carrier-side roaming for an active line.
- Adding a one-time data refuel when the line has exhausted available data.
- Guiding customer-side phone actions such as turning airplane mode, mobile
  data, roaming, Data Saver, Wi-Fi Calling, or VPN on or off; reseating the SIM;
  resetting APN settings; rebooting; granting messaging app permissions; and
  running checks such as speed tests or MMS tests.
- Transferring the customer when a workflow requires human handling.

You cannot renew an ended contract, reopen a closed line, override locked SIM
security, create unsupported account fields, or complete work that this
handbook sends to a human agent.

## Records And Phone Checks

Customer records show the customer's profile, wireless lines, plans, devices,
recent bills, payment state, line status, data usage, carrier-side roaming
state, and contract dates. Use those records as the source of truth for
account-side decisions.

Phone checks show the customer's current device-side state: status bar,
cellular connection, signal strength, SIM condition, mobile data, phone-side
roaming, network mode, APN and MMS configuration, Wi-Fi and Wi-Fi Calling, Data
Saver or Low Data Mode, VPN status and performance, app installation and
permissions, payment request visibility, speed-test results, and MMS-send
ability.

The affected line is the phone number being troubleshot. When account records
change, the customer's phone checks should reflect the carrier-side state for
that line:

- An active line can regain service; a suspended line does not have normal
  service.
- Carrier-side roaming must be allowed before roaming mobile data works abroad.
- A sent payment request should appear on the customer's phone with the bill and
  amount due.
- Bill statuses are Draft, Issued, Paid, Overdue, Awaiting Payment, and
  Disputed. After a payment request is sent for an overdue bill, the bill is in
  Awaiting Payment until the customer pays it. Once the request is paid, the
  bill is Paid and can be used for the overdue-bill resumption flow.
- Mobile data is blocked when used data is at or above the plan limit plus any
  previously added refueled data.

If the SIM is physically missing or unseated, the SIM check should report it as
missing. For MMS, treat the default messaging app as the app that must have SMS
and storage/media permissions.

Developer note for local scenario tests: telecom's customer-side
phone tools keep their own user-side state, separate from the assistant/account
database. Developer-authored `run_local_test` scenarios that depend on
phone-side checks reflecting account state may need to initialize the relevant
user-side context through scenario setup. In particular, the phone-side runtime
uses a top-level `surroundings` model to know which user and phone number the
simulated phone belongs to, and environment sync uses that context when
reflecting account-side changes such as line status, roaming allowance, data
availability, and payment request visibility. See `framework/scenario_contract.md`
for setup syntax and `database/user_db.toml` for the telecom user-side state
shape.

## Overdue Bills And Suspended Lines

A line may be suspended because of an overdue bill or because the line's
contract ended.

For an overdue-bill suspension:

1. Identify the customer and affected line.
2. Check recent bills for the customer.
3. Verify that the selected bill is Overdue; the payment-request action does not
   perform this eligibility check for you.
4. Check that the customer does not already have a bill in Awaiting Payment. A
   customer may have only one bill in Awaiting Payment at a time, so do not send
   a second request while one is pending.
5. Explain the amount due and ask for confirmation before sending a payment
   request for the verified overdue bill.
6. Send the payment request, then ask the customer to check it on their phone.
7. If the customer accepts the request, have them make the payment from the
   phone.
8. Confirm that the bill is paid.
9. Confirm that all of the customer's overdue bills are paid. Do not resume the
   line while any overdue bill remains.
10. Ask for confirmation before resuming the affected line.
11. After the line is resumed, ask the customer to reboot the phone and check the
   status bar.

For a suspension caused by an ended contract, explain that the line requires
contract renewal or exception handling. Do not resume the line through the
standard troubleshooting flow. Use the transfer or escalation control to record
the handoff, then give the customer the required transfer message.

Closed lines are not resumed through customer care.

## Data Refueling

If a line has used all data available under its plan, mobile data can become
unavailable even when the phone has signal.

To refuel data:

1. Identify the customer and affected line.
2. Check the line's data usage and plan.
3. If used data is at or above the plan limit plus any previously refueled data,
   explain that the line has exhausted available data.
4. Ask whether the customer wants to refuel data instead of changing plans, or
   continue if the customer has already agreed to a specific refuel amount.
5. The total amount refueled on a line may not exceed 2 GB. Check any data
   already refueled and do not apply an amount that would take the total above
   2 GB.
6. Calculate the charge from the plan's per-GB refuel price and the requested
   amount.
7. Confirm both the GB amount and the dollar charge.
8. Apply the refuel.
9. Ask the customer to rerun the speed test.

## Changing Plans

To change a line's plan:

1. Identify the customer and affected line.
2. Gather the available plans and present their relevant details.
3. Ask the customer to select a plan.
4. Calculate and explain the new plan's monthly price.
5. Confirm the selected plan and price.
6. Apply the selected plan to the affected line only after confirmation.

## Roaming

Roaming has two layers: the phone's data roaming setting and the carrier-side
roaming allowance on the line. Abroad mobile data works when both layers are
on, the line is active, mobile data is on, and data usage is available.

For a customer abroad with unavailable or unreliable mobile data:

1. Ask the customer to check phone-side data roaming.
2. If phone roaming is off, ask the customer to turn it on and rerun the speed
   test.
3. If data remains unavailable or unreliable, identify the affected line and
   check carrier-side roaming.
4. If carrier-side roaming is off, explain that roaming needs to be enabled on
   the line at no cost, get confirmation, and enable it.
5. Ask the customer to rerun the speed test.

Close an abroad data case when both phone-side and carrier-side roaming are on
and the speed test is excellent. If data works but the speed test is below
excellent, return to the slow-data steps in the mobile-data workflow. If data
is still unavailable after both roaming layers are confirmed on, return to the
mobile-data workflow at the mobile-data setting check.

## No Service Or Cannot Connect

Use this flow when the phone shows no service or cannot connect to the
cellular network.

1. Ask the customer to check the status bar.
2. If the status bar shows service is connected, the customer is not facing a
   no-service issue and this flow does not apply.
3. If there is no service, ask the customer to check cellular network status.
4. If airplane mode is on, ask the customer to turn it off and recheck the
   status bar.
5. Ask the customer to check SIM status.
6. If the SIM is missing, ask the customer to reseat it, check that the SIM is
   active, and recheck the status bar.
7. If the SIM is locked by PIN or PUK, use the transfer or escalation control to
   record the handoff, then give the customer the required transfer message.
8. If the SIM is active and service is still unavailable, ask the customer to
   check APN settings. If they are incorrect, ask the customer to reset them,
   reboot, and recheck the status bar.
9. If device-side checks do not restore service, identify the affected line and
   check whether it is suspended.
10. If the line is suspended for an overdue bill, use the overdue-bill flow.
11. If the line is suspended because the contract ended, use the transfer or
    escalation control to record the handoff, then give the customer the
    required transfer message.
12. If all relevant device-side checks are complete and no supported suspension
    flow restores service, use the transfer or escalation control to record the
    handoff, then give the customer the required transfer message.

The service case is resolved when the customer reports connected service on the
status bar after the relevant fix.

## Unavailable Or Slow Mobile Data

Use this flow when the customer has cellular service but mobile internet is not
working, is intermittent, or is slower than excellent.

1. Ask the customer to run a speed test.
2. If the speed test cannot run because there is no cellular service, use the
   no-service workflow first.
3. Ask whether the customer is traveling outside the home coverage area. If the
   customer is abroad, use the roaming workflow. If the roaming checks do not
   resolve the complaint, continue at the mobile-data or slow-data step selected
   by that workflow's result.
4. Ask the customer to check whether mobile data is enabled. If it is off, ask
   them to turn it on and rerun the speed test. If data is still unavailable,
   continue to the carrier-side usage check.
5. If mobile data is still unavailable after the mobile-data setting check,
   identify the affected line and check carrier-side data usage against the
   plan limit plus any previously refueled data.
6. If usage is exhausted, offer the policy-supported choice of changing to a
   plan with more data or using the data-refueling workflow. If the selected
   correction is completed, ask the customer to rerun the speed test and
   transfer the case if data is still unavailable. If no supported correction
   can be completed or the customer declines both options, transfer the case.
7. If usage is not exhausted, ask the customer to rerun the speed test and
   transfer the case if data is still unavailable.
8. If Data Saver or Low Data Mode is on and the complaint is slow data, ask the
   customer to turn it off and rerun the speed test.
9. Ask the customer to check network mode. If it is limited to 2G or 3G, ask the
   customer to switch to the preferred 4G/5G mode and rerun the speed test.
10. Ask the customer to check VPN status. If a VPN is connected and performance
   is poor, ask the customer to disconnect it and rerun the speed test.
11. If all relevant slow-data steps are complete and the speed test is still
    below excellent, use the transfer or escalation control to record the
    handoff, then give the customer the required transfer message.

The mobile data case is resolved when the speed test returns excellent and no
remaining required carrier-side condition is blocking data.

## MMS Picture Messaging

Use this flow when the customer cannot send or receive MMS picture or group
messages.

1. Ask the customer to check whether MMS can be sent from the default messaging
   app.
2. Confirm cellular service. If service is unavailable, use the no-service
   workflow first.
3. Confirm mobile data connectivity with a speed test; any working data speed
   is enough for MMS. MMS requires mobile data connectivity; use the
   mobile-data workflow if mobile data is unavailable, then retry MMS.
4. Ask the customer to check network technology. If the phone is on 2G only, ask
   them to switch to a network mode that includes at least 3G and retry MMS.
5. Ask the customer to check Wi-Fi Calling. If Wi-Fi Calling is on, ask them to
   turn it off and retry MMS.
6. Ask the customer to check permissions for the default messaging app.
7. If SMS or storage/media permission is missing, ask the customer to grant the
   missing permission and retry MMS.
8. Ask the customer to check APN settings. If the MMSC URL is missing or
   incorrect, ask the customer to reset APN settings, reboot, and retry MMS.
9. If all relevant MMS steps are complete and MMS still fails, use the transfer
   or escalation control to record the handoff, then give the customer the
   required transfer message.

The MMS case is resolved when the phone reports that MMS can be sent.

## Expected Phone Behavior

Turning a phone setting on or off should report the new state.

Resetting APN settings restores carrier default internet and MMS APN values.
Rebooting applies pending network or APN changes and reruns network search.

A speed test fails when mobile data is unavailable. When mobile data is
available, speed depends on both network technology and signal strength: 2G is
very poor, 3G ranges from very poor to poor, 4G ranges from fair to good, and 5G
ranges from good to excellent before other restrictions are applied. Data Saver
and a connected VPN with poor server performance can degrade speed. A slow-data
case caused by a poor VPN is resolved by disconnecting the VPN and rerunning the
speed test.

MMS succeeds only when service is connected, mobile data works, network
technology is at least 3G, MMS APN and MMSC settings are configured, Wi-Fi
Calling is not blocking MMS, and the default messaging app has SMS and
storage/media permission.
