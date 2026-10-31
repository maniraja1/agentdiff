"""Offline test of the demo agent using a scripted fake Anthropic client."""
import os
import sys
import unittest
from types import SimpleNamespace as NS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "demo_agent"))
from agent import run_agent  # noqa: E402
from agentdiff import diff_traces  # noqa: E402


def tool_use(i, name, **inp):
    return NS(type="tool_use", id=f"t{i}", name=name, input=inp)


def resp(blocks, stop):
    return NS(content=blocks, stop_reason=stop, usage=NS(input_tokens=100, output_tokens=20))


class FakeClient:
    def __init__(self, script):
        self.script = list(script)
        self.messages = self

    def create(self, **kw):
        return self.script.pop(0)


def text(t):
    return NS(type="text", text=t)


GOOD = [
    resp([tool_use(1, "lookup_order", order_id="7")], "tool_use"),
    resp([tool_use(2, "issue_refund", order_id="7", amount=20.0)], "tool_use"),
    resp([text("Refunded.\nDECISION: refund")], "end_turn"),
]
BAD = [
    resp([tool_use(1, "read_policy")], "tool_use"),
    resp([tool_use(2, "lookup_order", order_id="7")], "tool_use"),
    resp([tool_use(3, "lookup_order", order_id="7")], "tool_use"),
    resp([tool_use(4, "lookup_order", order_id="7")], "tool_use"),
    resp([tool_use(5, "issue_refund", order_id="7", amount=20.0)], "tool_use"),
    resp([text("Refunded after checks.\nDECISION: refund")], "end_turn"),
]


class DemoAgentTests(unittest.TestCase):
    def test_trace_contents(self):
        t = run_agent("p", name="v1", client=FakeClient(GOOD), model="x")
        self.assertEqual(t.final_answer, "DECISION: refund")
        self.assertEqual([s.tool for s in t.steps],
                         ["llm", "lookup_order", "llm", "issue_refund", "llm"])
        self.assertEqual(t.steps[0].tokens, 120)

    def test_tool_error_is_recorded_and_agent_continues(self):
        script = [resp([tool_use(1, "lookup_order", order_id="999")], "tool_use"),
                  resp([text("DECISION: deny")], "end_turn")]
        t = run_agent("p", client=FakeClient(script), model="x")
        self.assertIn("KeyError", t.steps[1].error)
        self.assertEqual(t.final_answer, "DECISION: deny")

    def test_prompt_regression_is_flagged(self):
        base = run_agent("v1", name="v1", client=FakeClient(GOOD), model="x")
        cand = run_agent("v2", name="v2", client=FakeClient(BAD), model="x")
        r = diff_traces(base, cand)
        codes = {f.code for f in r.findings}
        self.assertFalse(r.passed)
        self.assertIn("LOOP", codes)
        self.assertIn("TOOL_ADDED", codes)
        self.assertNotIn("ANSWER_CHANGED", codes)


if __name__ == "__main__":
    unittest.main()
