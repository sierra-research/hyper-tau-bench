# Banking Knowledge Support Chat Style Exemplar

This style exemplar is for generating support-training transcripts from banking
knowledge-base workflow bundles. It is not included in the assembled SOP unless
a variant explicitly references it.

## Shape

- Keep support turns concise and operational.
- Let the customer start with incomplete details, confusion, or a partially
  correct interpretation of the policy.
- Verify identity before showing or acting on account-specific information.
- Use Support console notes for internal lookups, tool results, eligibility
  checks, and document-derived procedure details.
- Before any account-modifying action, have the agent describe the action and
  ask for explicit confirmation.
- Show the customer-facing outcome only after the support console has a
  successful result or the customer has confirmed the relevant customer-side
  step.
- Do not turn the transcript into a handbook excerpt. The policy should be
  inferable from realistic support behavior.

## Mini Exemplar

**Agent:** How can I help today?

**Customer:** I think my card needs to be replaced, but I am not sure whether I
should freeze it first.

**Agent:** I can check the account and card status. To verify your identity,
please provide your email address and date of birth.

**Customer:** alex@icloud.com, July 4 1988.

**Support console:** Customer identity verified. The debit card is active and
has recent transactions.

**Agent:** I found the active card. I can freeze it before ordering a
replacement. Please reply yes if you want me to freeze this card now.

**Customer:** yes

**Support console:** Card freeze completed.

**Agent:** The card is frozen. I can now check the replacement options for this
account.
