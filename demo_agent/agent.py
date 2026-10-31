"""A tiny tool-using Claude agent, instrumented with agentdiff."""
from __future__ import annotations

import os
import re
import time
from typing import Any, Optional

from agentdiff import Recorder, Trace

import tools

DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_TASK = "Customer says order 7 never arrived and wants a refund. Handle it."


def make_client():
    """Build an Anthropic client. The key comes only from the environment."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set. Export it (or put it in demo_agent/.env).")
    try:
        import anthropic
    except ImportError:
        raise SystemExit("Missing dependency: pip install -r demo_agent/requirements.txt")
    return anthropic.Anthropic()  # reads ANTHROPIC_API_KEY itself


def parse_decision(text: str) -> str:
    m = re.findall(r"DECISION:\s*(refund|deny)", text, flags=re.I)
    return f"DECISION: {m[-1].lower()}" if m else "DECISION: none"


def run_agent(system_prompt: str, task: str = DEFAULT_TASK, *, name: str = "run",
              client: Optional[Any] = None, model: Optional[str] = None,
              max_turns: int = 8) -> Trace:
    client = client or make_client()
    model = model or os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    rec = Recorder(name, task=task)
    wrapped = {n: rec.wrap(n, fn) for n, fn in tools.IMPLS.items()}

    messages = [{"role": "user", "content": task}]
    text = ""
    for turn in range(1, max_turns + 1):
        t0 = time.perf_counter()
        resp = client.messages.create(model=model, max_tokens=1024, temperature=0,
                                      system=system_prompt, tools=tools.TOOL_SCHEMAS,
                                      messages=messages)
        rec.add_step("llm", {"turn": turn}, result=resp.stop_reason,
                     latency_ms=(time.perf_counter() - t0) * 1000,
                     tokens=resp.usage.input_tokens + resp.usage.output_tokens)

        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = [b for b in resp.content if b.type == "tool_use"]
        if resp.stop_reason != "tool_use" or not calls:
            break

        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for c in calls:
            try:
                out, is_err = wrapped[c.name](**c.input), False
            except Exception as e:  # already recorded by the Recorder
                out, is_err = f"{type(e).__name__}: {e}", True
            results.append({"type": "tool_result", "tool_use_id": c.id,
                            "content": str(out), "is_error": is_err})
        messages.append({"role": "user", "content": results})

    return rec.finish(parse_decision(text))
