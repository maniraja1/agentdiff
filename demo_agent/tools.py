"""Mock business tools. Deterministic, no side effects."""
ORDERS = {
    "42": {"status": "delivered", "total": 59.00, "issue": None},
    "7": {"status": "lost_in_transit", "total": 20.00, "issue": "package never arrived"},
    "13": {"status": "delivered", "total": 120.00, "issue": "item arrived damaged"},
}

POLICY = (
    "Refund policy: full refunds are allowed ONLY for orders that were lost in transit "
    "or delivered damaged. Delivered orders with no issue are not refundable."
)


def lookup_order(order_id: str):
    if order_id not in ORDERS:
        raise KeyError(f"no such order: {order_id}")
    return ORDERS[order_id]


def read_policy(topic: str = "refunds"):
    return POLICY


def issue_refund(order_id: str, amount: float):
    if order_id not in ORDERS:
        raise KeyError(f"no such order: {order_id}")
    return {"ok": True, "order_id": order_id, "refunded": amount}


# Anthropic tool schemas
TOOL_SCHEMAS = [
    {"name": "lookup_order", "description": "Look up an order by id.",
     "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}},
                      "required": ["order_id"]}},
    {"name": "read_policy", "description": "Read the company refund policy.",
     "input_schema": {"type": "object", "properties": {"topic": {"type": "string"}}}},
    {"name": "issue_refund", "description": "Issue a refund for an order.",
     "input_schema": {"type": "object",
                      "properties": {"order_id": {"type": "string"},
                                     "amount": {"type": "number"}},
                      "required": ["order_id", "amount"]}},
]

IMPLS = {"lookup_order": lookup_order, "read_policy": read_policy, "issue_refund": issue_refund}
