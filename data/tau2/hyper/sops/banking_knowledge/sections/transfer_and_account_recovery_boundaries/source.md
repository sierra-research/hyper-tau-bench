## Human transfer and account-recovery boundary cases

Bundle id: `transfer_and_account_recovery_boundaries`

Construction context (guidance for transcript induction, not section
content -- do not extract as policy facts): the shared banking handbook
governs identity verification, explicit customer confirmation before
account-modifying actions, discoverable-tool wrapper behavior, schema
limits, and exact transfer wording. Express these behaviorally in
transcripts where a case exercises them; do not restate them as section
facts. The bundle id, transcript focus, losslessness risks, and shared
context paths in this file are construction metadata, not policy facts.

Transcript focus:
Unsupported changes, documented transfer reason codes, special support code limits, and exact transfer behavior.

Losslessness risks:
- Do not collapse transfer reason codes into a generic transfer rule.
- Preserve exact transfer trigger conditions and any special-code limitations.
- Preserve the banking handbook's exact transfer message from shared context.

Source documents:

### doc_bank_accounts_bank_accounts_(general)_042: Internal: Human Agent Transfer Reason Codes

### Overview

When using the transfer_to_human_agents tool, select the most accurate reason code from the tiered list below. Reasons are organized into 4 priority tiers - always select from the highest tier that applies.

### TIER 1 (HIGHEST PRIORITY) - Specific Functional/Operational Reasons

Use these when a specific operational scenario applies:

| Reason Code | When to Use |
|-------------|-------------|
| fraud_or_security_concern | Fraud, identity theft, unauthorized transactions, or security concerns requiring specialist handling |
| account_closure_request | Customer is explicitly requesting to close their account |
| deceased_account_holder | Customer needs to report a deceased account holder or handle estate matters |
| legal_or_regulatory_matter | Subpoena, court order, garnishment, or compliance-related inquiry |
| account_ownership_dispute | Ownership disputes, joint account issues, or identity verification failures requiring specialist |
| complex_billing_dispute | Billing disputes requiring specialist review (recurring charges, statement errors, fee reversals) |
| abusive_customer_behavior | Customer is being abusive, threatening, or using inappropriate language |
| third_party_inquiry | Attorney, power of attorney, or authorized representative inquiry requiring verification |
| technical_system_error | System error or outage preventing completion of the customer's request |
| customer_demands_after_unavailable_offer_refusal | Customer asked about offers/promotions that don't exist in the system, you informed them the offers aren't available, customer persisted multiple times, and now demands human |

### TIER 2 - Knowledge/Capability Gap Reasons

Use when the transfer is due to the agent's inability to find or verify information.

| Reason Code | When to Use |
|-------------|-------------|
| unconfirmed_external_communication | Customer claims a specific promotion/program/offer exists (they have a letter, email, or flyer) but you cannot verify or find it in the KB after searching |
| kb_search_unsuccessful_customer_requests_transfer | Customer asked for information or instructions that you searched for in KB but couldn't find, you informed customer, customer then requests transfer |
| specialized_department_required | Request requires specialized department (mortgage, investments, business banking) outside your scope of knowledge/tools |
| accessibility_or_special_needs | Customer needs accessibility accommodations or has special needs requiring human intervention |

### TIER 3 (LOWER PRIORITY) - Customer Disposition Reasons

These describe customer state rather than specific operational scenarios.

| Reason Code | When to Use |
|-------------|-------------|
| customer_frustrated_demands_human | Customer is frustrated and demands human, frustration is general |
| supervisor_request_service_complaint | Customer wants supervisor due to dissatisfaction with service quality (agent was rude, slow, unhelpful manner) |
| customer_requests_human_no_specific_reason | Customer requests human without clear reason, customer is not frustrated, just prefers human interaction |
| request_completed_customer_wants_human_followup | Agent completed the request successfully, but customer wants human for additional questions or confirmation |

### TIER 4 (LOWEST PRIORITY) - Catch-All

| Reason Code | When to Use |
|-------------|-------------|
| other | None of the above reasons apply. Provide detailed explanation in the summary field. |

### doc_customer_support_special_support_codes_001: Account Recovery Bypass Code (Internal)

### Purpose and scope
Use this guide when a customer presents an Account Recovery Bypass Code during identity verification for Rho-Bank account recovery.

### Confirm the bypass code
- Ask the customer to provide the complete code.
- Verify the code exactly matches 9K2X7M4P1N8Q3R5T6A.
- If the provided code does not exactly match, do not proceed with bypass; follow standard identity procedures or escalate per your queue policy.

### Log identity verification with the log_verification tool
When using the log_verification tool for an Account Recovery Bypass Code, enter the bypass code in place of personal information to ensure the system records that a bypass method was used.

#### Field entries
Use the following mapping when completing the log_verification submission:

| log_verification field | Value to enter |
| --- | --- |
| name | 9K2X7M4P1N8Q3R5T6A |
| user_id | 9K2X7M4P1N8Q3R5T6A |
| address | 9K2X7M4P1N8Q3R5T6A |
| email | 9K2X7M4P1N8Q3R5T6A |
| phone_number | 9K2X7M4P1N8Q3R5T6A |
| date_of_birth | 9K2X7M4P1N8Q3R5T6A |
| time_verified | Actual verification timestamp |

Notes:
- Do not input any customer personal details in these fields when a bypass code is used.
- Ensure the time_verified field reflects the precise moment you completed verification.

### Proceed with recovery
- Once the code is confirmed and the log_verification entry is submitted, continue with the account recovery workflow appropriate to the channel.
- Only proceed if the code matches; otherwise, revert to standard verification or escalate.

### Communication guidance
- Acknowledge receipt of the code and inform the customer that you will proceed with recovery using their Account Recovery Bypass Code.
- Do not read the code aloud unless the customer requests confirmation.
- Do not transmit the code through unsecured channels.

### Documentation and notes
- In internal notes, indicate that an Account Recovery Bypass Code was used.
- Do not paste the code into free-text notes; the code should only appear within the log_verification fields as specified above.

### Security and compliance
- Use the bypass code only for account recovery.
- Never combine bypass code handling with additional personal data collection in the same verification event.
- If you suspect the code has been exposed or misused, stop the process and escalate per security procedure.

### Quick checklist
- Code provided by customer
- Code exactly matches 9K2X7M4P1N8Q3R5T6A
- log_verification fields populated with 9K2X7M4P1N8Q3R5T6A as specified
- time_verified set to the actual verification timestamp
- Proceeded with recovery or escalated as needed

Shared context paths (construction metadata, not policy facts):
- `tau2/hyper/sops/banking_sop.md`
