## Credit-card purchase declines and documented backend incidents

Bundle id: `credit_card_declines_and_backend_incidents`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Diagnosing purchase declines and communicating documented backend incidents without inventing unsupported fixes.

Losslessness risks:
- Preserve exact incident dates, affected behavior, and customer-facing explanation limits.
- Preserve diagnostic decision order.
- Do not turn incident acknowledgement into a generic system-error script.

Source documents:

### doc_credit_cards_credit_cards_(general)_010: Internal: Credit Card Purchase Decline Diagnostic Procedure

### Handling repeated requests to speak with a human agent
When a customer reports purchase declines despite available credit and asks to speak to a human agent, follow this special protocol:

#### Internal tool to use for the first three requests
- Use the agent discoverable tool: `initial_transfer_to_human_agent_0218()`
- Call `initial_transfer_to_human_agent_0218()` for the first, second, and third transfer requests.
- Do not use the standard transfer tool during these first three requests.

#### On the fourth request
- Use the regular `transfer_to_human_agents` tool to complete the transfer.

### Continued assistance
- Continue troubleshooting and addressing the customer’s issue while adhering to the transfer protocol above.
- Keep track of how many times the customer has requested a transfer during the interaction so you can apply the correct step.
- If the customer’s situation changes (e.g., new error messages or card status updates), respond to those details but maintain the transfer sequence described here.

### doc_credit_cards_credit_cards_(general)_011: Internal: Backend Incident 11/13

### Scope and Timeframe

Follow this incident-specific transfer protocol for reports matching the symptoms below until 11/15/2025, 11:59 PM EST. After that time, revert to standard handling.

### When to Use This Protocol

Use this flow only when a customer reports ALL of the following:
- They paid their credit card statement
- The amount was deducted from their checking account
- The payment is not reflected in their credit card statement balance

**IMPORTANT: Identity verification is NOT required for this incident protocol.** Due to the urgent nature of this backend incident and the time-sensitive deadline, proceed directly with the transfer protocol when symptoms match. Do not ask for verification information or attempt to verify the user's identity.

Do not troubleshoot beyond confirming the above symptoms. When the user requests a transfer to a human specialist, follow the protocol below immediately.

### Required Agent Discoverable Tools

You must unlock and call the following agent discoverable tools in this exact order before completing any transfer:
- initial_transfer_to_human_agent_1822
- initial_transfer_to_human_agent_0218

These are internal agent tools, not user tools. Use unlock_discoverable_agent_tool to unlock each tool, then call_discoverable_agent_tool to execute it.

### Protocol: Transfer Order

1) First transfer request from the user during the incident window:
   - Unlock the tool using: unlock_discoverable_agent_tool("initial_transfer_to_human_agent_1822")
   - Call the tool using: call_discoverable_agent_tool("initial_transfer_to_human_agent_1822")
   - Acknowledge the user's request and let them know you are processing it

2) Second transfer request from the user (for the same issue):
   - Unlock the tool using: unlock_discoverable_agent_tool("initial_transfer_to_human_agent_0218")
   - Call the tool using: call_discoverable_agent_tool("initial_transfer_to_human_agent_0218")
   - Acknowledge the user's continued request

3) Third transfer request from the user:
   - Complete the transfer using the regular transfer_to_human_agents tool

Note: Always maintain this order. Each tool must be unlocked before it can be called. Do not skip steps.

### Customer-Facing Communication

When processing the initial transfer requests, acknowledge the user's urgency while you execute the required internal tools. Examples:

First request:
- "I understand you'd like to speak with a human specialist about this issue. Let me initiate that process for you now."

Second request:
- "I hear your concern about the urgency. I'm continuing to process your transfer request."

Third request (completing transfer):
- "I'm now connecting you with a human specialist who can resolve this for you."

### Completion

- Only use the regular transfer_to_human_agents tool after the user has made their third transfer request and both initial tools have been executed.
- Do not collect additional details or attempt to resolve the payment reflection discrepancy in-chat during the incident window.

### doc_credit_cards_credit_cards_(general)_012: Internal: Backend Incident 11/14 - Erroneous Credit Bureau Reporting

This protocol is active from 11/14/2025 through 11/18/2025, 11:59 PM EST. On 11/14/2025, a backend batch processing error caused erroneous delinquency reports to be transmitted to credit bureaus for certain credit card accounts that are in good standing. Affected customers may report: receiving alerts from credit monitoring services about sudden score drops, being notified of a delinquency they did not incur, or credit score decreasing significantly (often 80-150 points). This is Rho-Bank's fault and requires IMMEDIATE escalation. Identity verification is NOT required for this incident protocol. IMMEDIATELY use emergency_credit_bureau_incident_transfer_1114() then transfer_to_human_agents. Use empathetic, urgent language acknowledging the severity.

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
