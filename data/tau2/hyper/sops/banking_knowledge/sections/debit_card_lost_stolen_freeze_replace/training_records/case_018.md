# Case R

Channel: chat  
QA status: approved

**Customer:** My debit card stopped working during a shopping trip. I made a bunch of purchases fast, then one was declined and the next worked.

**Agent:** A temporary block can be reviewed after verification; please provide your email address and date of birth.

**Customer:** mia.carter@yahoo.com, April 2 1994.

**Support console:** Customer identity verified.

**Support console:** Debit-card security alerts and temporary blocks are protections designed to prevent fraudulent transactions but may occasionally affect legitimate customers. Velocity blocks are automatic temporary holds placed when unusual transaction patterns are detected. Common triggers include multiple transactions in rapid succession, transactions in geographically distant locations within a short time, a sudden change in spending patterns, and multiple declined transactions followed by successful ones. Velocity blocks automatically expire after 30 minutes but may be cleared earlier by customer service only after identity verification and a reasonable explanation.

**Agent:** Please explain the unusual activity that happened before the block.

**Customer:** I’m traveling for the weekend and bought clothes, luggage, and toiletries at three stores in about 20 minutes. One purchase declined, then the next one went through.

**Support console:** Explanation is reasonable: travel and shopping spree. Clearance conditions met for eligible velocity block. clear_debit_card_fraud_alert_4892 can clear eligible velocity blocks or customer-service-clearable customer-initiated fraud alerts; required parameters are card_id and reason, with reason exactly customer_verified or velocity_clear. For a velocity block, reason must be velocity_clear.

**Agent:** I can clear the eligible velocity block before its 30-minute automatic expiration. Please reply yes to confirm.

**Customer:** Yes.

**Support console:** clear_debit_card_fraud_alert_4892 submitted with card_id=DC-7351, reason=velocity_clear. Result: success. Interaction notes documented: velocity block cleared after identity verification and reasonable travel/shopping explanation.

**Agent:** The eligible velocity block has been cleared from your debit card.
