"""Deterministic fake 'agents' so the tool can be demoed with no API keys."""
from __future__ import annotations

from .trace import Recorder, Trace

ORDERS = {"42": {"status": "delivered", "total": 59.0}, "7": {"status": "lost", "total": 20.0}}


def _lookup(order_id: str):
    if order_id not in ORDERS:
        raise KeyError(f"no order {order_id}")
    return ORDERS[order_id]


def _refund(order_id: str, amount: float):
    return {"ok": True, "order_id": order_id, "amount": amount}


def _policy(topic: str):
    return "Refunds allowed for lost or damaged orders only."


def good_agent(order_id: str = "7") -> Trace:
    rec = Recorder("baseline", task=f"Refund order {order_id} if eligible")
    lookup, refund = rec.wrap("lookup_order", _lookup), rec.wrap("refund", _refund)
    o = lookup(order_id=order_id)
    if o["status"] == "lost":
        refund(order_id=order_id, amount=o["total"])
        return rec.finish(f"Refunded ${o['total']:.2f} for order {order_id}.")
    return rec.finish(f"Order {order_id} is not eligible.")


def regressed_agent(order_id: str = "7") -> Trace:
    """Simulates a prompt change that makes the agent loop and over-refund."""
    rec = Recorder("candidate", task=f"Refund order {order_id} if eligible")
    lookup = rec.wrap("lookup_order", _lookup)
    refund = rec.wrap("refund", _refund)
    policy = rec.wrap("read_policy", _policy)
    for _ in range(3):
        o = lookup(order_id=order_id)
    policy(topic="refunds")
    refund(order_id=order_id, amount=o["total"] * 2)
    return rec.finish(f"Refunded ${o['total'] * 2:.2f} for order {order_id}.")
