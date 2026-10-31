# agentdiff

Regression testing for AI agents. Record what an agent did (every tool call, arguments, result, tokens, latency), then diff a new run against a known-good baseline and fail CI if behavior got worse.

Zero dependencies. Pure Python 3.9+.

## Why

When you change a prompt, model, or tool, the agent's final answer may look fine while its behavior quietly degrades: it loops, calls extra tools, burns 2x tokens, or reaches a different answer. Unit tests don't catch this because agents are non-deterministic pipelines, not functions. `agentdiff` treats a run as a *trace* and compares traces.

## Quickstart

```bash
pip install -e .
agentdiff demo --dir examples                 # writes baseline.jsonl + candidate.jsonl
agentdiff diff examples/baseline.jsonl examples/candidate.jsonl   # exit code 1 = regression
agentdiff show examples/candidate.jsonl
```

## Record your own agent

```python
from agentdiff import Recorder

rec = Recorder("v2-prompt", task="Refund order 7")
lookup = rec.wrap("lookup_order", my_lookup_fn)   # keyword args only
refund = rec.wrap("refund", my_refund_fn)
...
rec.finish(final_answer).save("candidate.jsonl")
```

## What it flags

| code | severity | meaning |
|---|---|---|
| ANSWER_CHANGED | fail | final answer differs from baseline |
| NEW_ERRORS | fail | more tool errors than baseline |
| LOOP | fail | identical call repeated 3+ times (new vs baseline) |
| TOOL_ADDED / TOOL_DROPPED | warn | tool set changed |
| MORE_STEPS / TOKEN_GROWTH | warn | grew past threshold (default 25%) |
| DIVERGED | info | first step where call sequences differ |

Add `--strict` to fail on warnings too. Exit codes: 0 pass, 1 regression, 2 bad input.

## Demo with a real Claude agent

`demo_agent/` contains a refund-triage agent on the Anthropic API (key from `ANTHROPIC_API_KEY`). It records a baseline trace with prompt v1, a candidate trace with prompt v2, and diffs them. See `demo_agent/README.md`.

## CI

See `.github/workflows/ci.yml`. In your own repo, commit a baseline trace and run `agentdiff diff baseline.jsonl candidate.jsonl` after your eval run.

## Test

```bash
python -m unittest discover -s tests -v
```

## Roadmap

HTML report, semantic answer comparison via an LLM judge, OpenTelemetry import, per-tool cost tables.
