"""Trace data model + recorder. A trace is a JSONL file: line 1 = header, rest = steps."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Step:
    tool: str
    args: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    tokens: int = 0

    @property
    def signature(self) -> str:
        """Stable identity of a call: tool name + canonical args."""
        return f"{self.tool}({json.dumps(self.args, sort_keys=True)})"


@dataclass
class Trace:
    name: str = "run"
    task: str = ""
    final_answer: str = ""
    steps: List[Step] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return sum(s.tokens for s in self.steps)

    @property
    def total_latency_ms(self) -> float:
        return sum(s.latency_ms for s in self.steps)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            header = {"type": "header", "name": self.name, "task": self.task,
                      "final_answer": self.final_answer}
            f.write(json.dumps(header) + "\n")
            for s in self.steps:
                f.write(json.dumps({"type": "step", **asdict(s)}) + "\n")

    @classmethod
    def load(cls, path: str) -> "Trace":
        t = cls()
        with open(path, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"{path}:{n}: invalid JSON ({e})") from e
                kind = obj.pop("type", None)
                if kind == "header":
                    t.name = obj.get("name", t.name)
                    t.task = obj.get("task", "")
                    t.final_answer = obj.get("final_answer", "")
                elif kind == "step":
                    t.steps.append(Step(**obj))
                else:
                    raise ValueError(f"{path}:{n}: unknown record type {kind!r}")
        return t


class Recorder:
    """Wrap tool functions so every call is captured as a Step.

    rec = Recorder("v1", task="refund order 42")
    search = rec.wrap("search", search_fn)
    """

    def __init__(self, name: str = "run", task: str = "",
                 token_counter: Optional[Callable[[Any], int]] = None):
        self.trace = Trace(name=name, task=task)
        self._count = token_counter or (lambda x: max(1, len(str(x)) // 4))

    def wrap(self, tool: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        def inner(**kwargs: Any) -> Any:
            start = time.perf_counter()
            step = Step(tool=tool, args=dict(kwargs))
            try:
                step.result = fn(**kwargs)
                return step.result
            except Exception as e:  # recorded, then re-raised
                step.error = f"{type(e).__name__}: {e}"
                raise
            finally:
                step.latency_ms = (time.perf_counter() - start) * 1000
                step.tokens = self._count(kwargs) + self._count(step.result)
                self.trace.steps.append(step)
        return inner

    def add_step(self, tool: str, args: Dict[str, Any] = None, result: Any = None,
                 error: Optional[str] = None, latency_ms: float = 0.0,
                 tokens: int = 0) -> Step:
        """Append a step you measured yourself (e.g. an LLM call with real token usage)."""
        step = Step(tool=tool, args=dict(args or {}), result=result, error=error,
                    latency_ms=latency_ms, tokens=tokens)
        self.trace.steps.append(step)
        return step

    def finish(self, final_answer: str) -> Trace:
        self.trace.final_answer = final_answer
        return self.trace
