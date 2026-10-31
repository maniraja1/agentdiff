# Demo: a real Claude agent, traced and diffed with agentdiff

A small customer-support agent (refund triage) built on the Anthropic API. It shows the full agentdiff loop:

1. Run the agent with **prompt v1** and save the trace as your baseline.
2. Change the prompt (**v2**) and run again to produce a candidate trace.
3. `agentdiff diff` the two. A behavior regression fails with exit code 1.

## Setup

```bash
# from the repo root
pip install -e .
pip install -r demo_agent/requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."        # never commit this
# optional: pick a model (default is set in agent.py)
export ANTHROPIC_MODEL="claude-sonnet-4-5"
```

The key is read only from the `ANTHROPIC_API_KEY` environment variable. You can also put it in a local `.env` file (git-ignored) as `ANTHROPIC_API_KEY=...`; `run.py` loads it if present.

## Run the whole demo

```bash
cd demo_agent
./demo.sh
```

Or step by step:

```bash
python run.py --prompt prompts/v1_baseline.txt  --name v1 --out traces/baseline.jsonl
python run.py --prompt prompts/v2_candidate.txt --name v2 --out traces/candidate.jsonl
agentdiff diff traces/baseline.jsonl traces/candidate.jsonl --strict --out traces/report.md
```

Try your own task: `python run.py --prompt prompts/v1_baseline.txt --task "Customer says order 42 arrived broken. Handle it." --out traces/mine.jsonl`

## What is in here

| file | purpose |
|---|---|
| `agent.py` | the tool-use loop; every tool call and every model call is recorded via `agentdiff.Recorder` |
| `tools.py` | mock order database, refund policy and refund tool (deterministic, no side effects) |
| `prompts/v1_baseline.txt` | the known-good system prompt |
| `prompts/v2_candidate.txt` | a "well-meant" change that makes the agent over-cautious: repeated lookups, extra policy reads |
| `run.py` | CLI: run one prompt on one task and save the trace |
| `demo.sh` | runs v1, v2 and the diff |

## How the trace is captured

`agent.py` wraps each tool with `Recorder.wrap(...)`, so name, arguments, result, errors and latency are stored automatically. Each model call is stored as an `llm` step using `Recorder.add_step(...)` with the real `input_tokens + output_tokens` from the API response. The agent's `final_answer` is a normalized decision line (`DECISION: refund`), not free text, so ordinary wording changes do not cause false `ANSWER_CHANGED` failures.

## Things to know

- `--strict` makes warnings (extra steps, token growth, tool-set changes) fail the run. Without it only hard failures (changed decision, new errors, loops) give exit code 1. v2's "look up twice, read policy first" produces warnings, so the demo uses `--strict`.
- LLMs are non-deterministic. The agent uses `temperature=0`, which reduces but does not remove variation. Run the baseline a couple of times before trusting it, and tune `--max-step-growth` / `--max-token-growth` for your tolerance.
- This makes real API calls and costs a small amount of money (a handful of short requests per run).
- Offline tests use a scripted fake client, so `python -m unittest discover -s tests` needs no API key.
