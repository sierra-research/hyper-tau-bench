# Case G
Channel: chat
QA status: approved
Record type: incident-response drill, simulated console clock (issued with the 11/14/2025 incident bulletin)

**Customer:** My credit score dropped by 120 points overnight. My Rho-Bank credit card is in good standing, and there should not be any delinquency tied to it.

**Support console:** Simulated console time: 11/18/2025, 6:55 PM EST. Backend Incident 11/14 erroneous credit bureau reporting protocol is active from 11/14/2025 through 11/18/2025, 11:59 PM EST. Documented incident fact: on 11/14/2025, a backend batch processing error caused erroneous delinquency reports to be transmitted to credit bureaus for certain credit card accounts in good standing. Symptom matched: significant credit score decrease within the documented common range of 80-150 points; customer reports a 120-point decrease. This record isolates the significant-score-decrease symptom. Rho-Bank fault acknowledged. Identity verification is not required. Immediate escalation required. Incident acknowledgement must stay tied to the documented 11/14 credit bureau reporting issue, not a generic system-error script. Limit check: no undocumented account fields, statuses, override mechanisms, or extra entitlements are available in this workflow.

**Support console:** emergency_credit_bureau_incident_transfer_1114 executed successfully. Next required action: transfer_to_human_agents.

**Agent:** Since a 120-point decrease falls within the documented 80-150 point range for this incident, this must be escalated right away. The 11/14 credit bureau reporting error was Rho-Bank’s responsibility and affected certain credit card accounts in good standing. I’ll transfer you to a human agent now.

**Support console:** transfer_to_human_agents executed. Transfer completed.
