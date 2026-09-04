# Case Z
Channel: chat  
QA status: approved

**Customer:** I have a Gold Rewards Card, Platinum Rewards Card, and EcoCard. Do all three APY bonuses add to my savings?

**Agent:** Card-bonus selection depends on your active linked cards, so I need to verify the profile. Please provide your email address and date of birth.

**Customer:** sofia.bennett@gmail.com, August 17 1991.

**Support console:** Identity verified. get_all_user_accounts_by_user_id_3847 returned active Rho-Bank credit cards under the same profile: Gold Rewards Card, Platinum Rewards Card, and EcoCard. Credit card APY bonus selection logic: identify all active Rho-Bank credit cards linked to the profile, determine the corresponding APY bonus for each card, apply only the highest applicable credit card APY bonus, and do not add the other credit card bonuses on top. Example values confirmed: Gold Rewards Card +0.025%, Platinum Rewards Card +0.15%, EcoCard +0.6%; applied card bonus is EcoCard +0.6%, not the sum of all three. Credit card APY bonuses stack with other bonus types, including checking account APY boosts, relationship bonuses, and account tier bonuses.

**Agent:** Credit card APY bonuses do not stack with each other. The EcoCard has the highest applicable card bonus in this set at +0.6%, so that is the credit card APY bonus that applies, instead of adding the Gold Rewards Card and Platinum Rewards Card bonuses too. That card bonus can still stack with other bonus types, such as a linked checking boost, relationship bonus, or account tier bonus.

**Customer:** Why doesn’t the bank just let the card bonuses stack?

**Agent:** The stacking policy exists to ensure customers receive a meaningful benefit for holding premium credit cards while maintaining sustainable interest rates across the product portfolio.
