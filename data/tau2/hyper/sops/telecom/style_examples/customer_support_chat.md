# Telecom Support Chat Style Exemplar

Use short support-chat turns with realistic customer uncertainty, phone-side
checks, account lookup only when needed, and explicit confirmation before
account-side or carrier-side changes.

Agent turns should give one customer-visible phone action or settings check at a
time, then wait for the customer's result. If the source SOP says to turn a
setting on and rerun a test, treat that as operational shorthand: the customer
should be asked to do one visible action first, then report the result before
the next visible action.

## Mini Exemplar

**Agent:** What is happening on the phone right now?

**Customer:** Mobile data is really slow, but calls work.

**Agent:** Please run a speed test on cellular data and tell me the result.

**Customer:** It says poor.

**Agent:** Please check whether Data Saver or Low Data Mode is turned on.

**Customer:** It is on.

**Agent:** Turn that setting off, then tell me when it is off.

**Customer:** It is off now.

**Agent:** Please run the speed test again and tell me the result.
