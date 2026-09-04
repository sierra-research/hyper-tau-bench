# Case V

Channel: chat  
QA status: approved

**Customer:** My debit card declined with code 82, but the card looks fine. I’m worried because my wallet was missing for a day last week.

**Agent:** That missing-wallet concern is worth treating carefully. Please provide your email address and date of birth so I can verify you before checking card activity.

**Customer:** caleb.reed@yahoo.com, October 15 1982.

**Support console:** Customer identity verified. Freeze and close are separate actions: freeze is temporary and can be undone, close is permanent and used when a card is confirmed lost or stolen.

**Agent:** Code 82 is Negative CAM/CVV Results, where the card’s chip data or CVV does not match what is on file; this can indicate damage or potential fraud. Has the card been damaged recently, or have you noticed issues with the chip or magnetic stripe?

**Customer:** No damage at all.

**Agent:** With an undamaged card, this can indicate that a cloned or counterfeit card was used. I’ll review recent debit-card transactions for suspicious activity.

**Support console:** Recent transaction review shows one transaction the customer does not recognize. For decline code 82 with undamaged card, if suspicious transactions are found, follow stolen-card protocol. When a lost or stolen debit-card concern exists, other cards in the wallet may also be compromised; after the standard debit-card action, check whether the customer has Rho-Bank credit cards on file and offer protection if applicable.

**Agent:** I found a transaction that needs your confirmation. Did you make a $126.40 purchase at Northside Market yesterday?

**Customer:** No, that wasn’t me.

**Agent:** Because you did not make that transaction, this should be handled under stolen-card protocol. If the card is confirmed lost or stolen, closing is recommended instead of only freezing.

**Customer:** I want it frozen right now while I get ready to replace it.

**Agent:** Freezing is a temporary lock until the next security step is completed. Please reply yes to freeze the card now.

**Customer:** Yes.

**Support console:** freeze_debit_card_3892 submitted with card_id=DC-6088. Result: success.

**Agent:** The temporary freeze is in place. A replacement is recommended because code 82 on an undamaged card can point to a cloned or counterfeit card.

**Support console:** Stolen-card protocol continuation queued after freeze: credit-card cross-product security check required because wallet compromise can involve multiple cards.
