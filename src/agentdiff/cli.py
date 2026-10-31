import argparse
import sys

from .diff import diff_traces
from .trace import Trace


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="agentdiff",
        description="Diff two agent traces; exit 1 on regression (CI-friendly).")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("diff", help="compare baseline.jsonl candidate.jsonl")
    d.add_argument("baseline")
    d.add_argument("candidate")
    d.add_argument("--max-token-growth", type=float, default=0.25)
    d.add_argument("--max-step-growth", type=float, default=0.25)
    d.add_argument("--strict", action="store_true",
                   help="treat warnings (extra steps/tokens, tool changes) as failures")
    d.add_argument("--out", help="write markdown report to this file")

    g = sub.add_parser("demo", help="write demo baseline/candidate traces")
    g.add_argument("--dir", default=".")

    s = sub.add_parser("show", help="print a trace summary")
    s.add_argument("trace")

    a = p.parse_args(argv)

    if a.cmd == "demo":
        import os
        from .demo import good_agent, regressed_agent
        good_agent().save(os.path.join(a.dir, "baseline.jsonl"))
        regressed_agent().save(os.path.join(a.dir, "candidate.jsonl"))
        print(f"wrote baseline.jsonl and candidate.jsonl to {a.dir}")
        return 0

    if a.cmd == "show":
        t = Trace.load(a.trace)
        print(f"{t.name}: {len(t.steps)} steps, {t.total_tokens} tokens\ntask: {t.task}")
        for i, s in enumerate(t.steps, 1):
            print(f"  {i}. {s.signature}" + (f"  ERROR {s.error}" if s.error else ""))
        print(f"answer: {t.final_answer}")
        return 0

    try:
        base, cand = Trace.load(a.baseline), Trace.load(a.candidate)
    except (OSError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    rep = diff_traces(base, cand, max_token_growth=a.max_token_growth,
                      max_step_growth=a.max_step_growth, strict=a.strict)
    md = rep.to_markdown()
    print(md)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(md)
    return 0 if rep.passed else 1


if __name__ == "__main__":
    sys.exit(main())
