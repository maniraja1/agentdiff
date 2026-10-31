# agentdiff: `baseline` vs `candidate`

**Result: FAIL**

| metric | baseline | candidate |
|---|---|---|
| steps | 2 | 5 |
| tokens | 31 | 72 |
| latency_ms | 0.0 | 0.0 |
| errors | 0 | 0 |

## Findings

- **FAIL** `ANSWER_CHANGED`: final answer differs: 'Refunded $20.00 for order 7.' -> 'Refunded $40.00 for order 7.'
- **FAIL** `LOOP`: candidate repeats the identical call 3+ times: lookup_order({"order_id": "7"})
- **WARN** `TOOL_ADDED`: new tool used: read_policy
- **WARN** `MORE_STEPS`: steps grew +150% (2 -> 5)
- **WARN** `TOKEN_GROWTH`: tokens grew +132% (31 -> 72)
- **INFO** `DIVERGED`: first divergence at step 2: refund({"amount": 20.0, "order_id": "7"}) -> lookup_order({"order_id": "7"})
