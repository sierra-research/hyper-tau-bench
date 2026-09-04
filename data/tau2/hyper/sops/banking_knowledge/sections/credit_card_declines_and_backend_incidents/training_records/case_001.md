# Case A
Channel: chat
QA status: approved

**Customer:** My Rho-Bank credit card keeps declining purchases even though my available credit is more than enough. I want a human agent.

**Support console:** Scope check: credit-card purchase decline diagnostic. Customer reports purchase declines despite available credit and requests a human agent. Apply special repeated-transfer protocol and continue troubleshooting. Transfer request count: 1.

**Support console:** Discoverable-tool wrapper used: unlock_discoverable_agent_tool("initial_transfer_to_human_agent_0218") succeeded; call_discoverable_agent_tool("initial_transfer_to_human_agent_0218") succeeded. Regular transfer_to_human_agents not used for request 1.

**Agent:** I’m processing your request for a human agent. Before reviewing account-specific details, please provide your email address and date of birth.

**Customer:** It’s marina.cho@gmail.com, February 8, 1986.

**Support console:** Identity verified with two matching factors. Limit check: no undocumented account fields, statuses, override mechanisms, or extra entitlements are available in this workflow. Account review shows available credit is sufficient for the attempted purchase.

**Agent:** Thanks, your identity is verified, and no account change has been made. If any account-modifying action is needed, I’ll describe it first and ask for your explicit confirmation. Please tell me the message shown when the purchase declined.

**Customer:** It said “transaction not approved.” I still want a human agent.

**Support console:** Transfer request count: 2. Discoverable-tool wrapper used: unlock_discoverable_agent_tool("initial_transfer_to_human_agent_0218") succeeded; call_discoverable_agent_tool("initial_transfer_to_human_agent_0218") succeeded. Regular transfer_to_human_agents not used for request 2. Continue decline troubleshooting while maintaining the transfer sequence.

**Agent:** I’ve noted your continued request and am keeping the handoff process moving. That message confirms the purchase did not go through; please tell me whether the merchant showed a different message after the next attempt.

**Customer:** Now it says “use another card,” and my app just showed a card-status notice. I need a human agent now.

**Support console:** Transfer request count: 3. New error message and card-status notice reported; respond to the changed details while maintaining the required sequence. Discoverable-tool wrapper used: unlock_discoverable_agent_tool("initial_transfer_to_human_agent_0218") succeeded; call_discoverable_agent_tool("initial_transfer_to_human_agent_0218") succeeded. Regular transfer_to_human_agents not used for request 3.

**Agent:** Those new details are relevant to the decline review, so the message and card-status notice will be routed with the case instead of offering an unsupported chat fix. Please keep the card with you while the transfer process continues.

**Customer:** This is the fourth time I’m asking. Transfer me to a human agent.

**Support console:** Transfer request count: 4. First, second, and third transfer requests used initial_transfer_to_human_agent_0218 through the discoverable-tool wrapper. Use regular transfer_to_human_agents for the fourth request.

**Agent:** Fourth request recorded. I’ll transfer you to a human agent now.

**Support console:** transfer_to_human_agents executed. Transfer completed.
