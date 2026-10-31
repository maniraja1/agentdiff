"""Compare a baseline trace to a candidate trace and flag regressions."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import List

from .trace import Trace

SEVERITY = {"info": 0, "warn": 1, "fail": 2}


@dataclass
class Finding:
    severity: str  # info | warn | fail
    code: str
    message: str


@dataclass
class DiffReport:
    baseline: str
    candidate: str
    findings: List[Finding] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    strict: bool = False  # treat warnings as failures

    @property
    def worst(self) -> str:
        if not self.findings:
            return "info"
        return max(self.findings, key=lambda f: SEVERITY[f.severity]).severity

    @property
    def passed(self) -> bool:
        limit = "warn" if self.strict else "fail"
        return SEVERITY[self.worst] < SEVERITY[limit]

    def to_markdown(self) -> str:
        s = self.stats
        out = [f"# agentdiff: `{self.baseline}` vs `{self.candidate}`", "",
               f"**Result: {'PASS' if self.passed else 'FAIL'}**", "",
               "| metric | baseline | candidate |", "|---|---|---|"]
        for k in ("steps", "tokens", "latency_ms", "errors"):
            out.append(f"| {k} | {s[k][0]} | {s[k][1]} |")
        out += ["", "## Findings", ""]
        if not self.findings:
            out.append("No differences that matter.")
        for f in sorted(self.findings, key=lambda f: -SEVERITY[f.severity]):
            out.append(f"- **{f.severity.upper()}** `{f.code}`: {f.message}")
        return "\n".join(out) + "\n"


def _loops(trace: Trace, threshold: int = 3) -> List[str]:
    c = Counter(s.signature for s in trace.steps)
    return [sig for sig, n in c.items() if n >= threshold]


def diff_traces(base: Trace, cand: Trace, *, max_token_growth: float = 0.25,
                max_step_growth: float = 0.25,
                strict: bool = False) -> DiffReport:
    r = DiffReport(base.name, cand.name, strict=strict)
    be = sum(1 for s in base.steps if s.error)
    ce = sum(1 for s in cand.steps if s.error)
    r.stats = {
        "steps": (len(base.steps), len(cand.steps)),
        "tokens": (base.total_tokens, cand.total_tokens),
        "latency_ms": (round(base.total_latency_ms, 1), round(cand.total_latency_ms, 1)),
        "errors": (be, ce),
    }

    if base.final_answer.strip() != cand.final_answer.strip():
        r.findings.append(Finding("fail", "ANSWER_CHANGED",
            f"final answer differs: {base.final_answer!r} -> {cand.final_answer!r}"))

    if ce > be:
        r.findings.append(Finding("fail", "NEW_ERRORS",
            f"tool errors increased {be} -> {ce}"))

    for sig in _loops(cand):
        if sig not in _loops(base):
            r.findings.append(Finding("fail", "LOOP",
                f"candidate repeats the identical call 3+ times: {sig}"))

    bt, ct = {s.tool for s in base.steps}, {s.tool for s in cand.steps}
    for t in sorted(bt - ct):
        r.findings.append(Finding("warn", "TOOL_DROPPED", f"tool no longer used: {t}"))
    for t in sorted(ct - bt):
        r.findings.append(Finding("warn", "TOOL_ADDED", f"new tool used: {t}"))

    def grew(a: float, b: float) -> float:
        return (b - a) / a if a else (1.0 if b else 0.0)

    sg = grew(len(base.steps), len(cand.steps))
    if sg > max_step_growth:
        r.findings.append(Finding("warn", "MORE_STEPS",
            f"steps grew {sg:+.0%} ({len(base.steps)} -> {len(cand.steps)})"))
    tg = grew(base.total_tokens, cand.total_tokens)
    if tg > max_token_growth:
        r.findings.append(Finding("warn", "TOKEN_GROWTH",
            f"tokens grew {tg:+.0%} ({base.total_tokens} -> {cand.total_tokens})"))

    # first point where the call sequences diverge
    for i, (a, b) in enumerate(zip(base.steps, cand.steps)):
        if a.signature != b.signature:
            r.findings.append(Finding("info", "DIVERGED",
                f"first divergence at step {i + 1}: {a.signature} -> {b.signature}"))
            break
    return r
