#!/usr/bin/env python3
"""Run the demo agent once with a given prompt file and save the trace."""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def load_dotenv(path):
    """Minimal .env loader (KEY=VALUE lines). Existing env vars win."""
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main():
    load_dotenv(os.path.join(HERE, ".env"))
    from agent import run_agent, DEFAULT_TASK

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prompt", required=True, help="path to a system prompt file")
    p.add_argument("--out", required=True, help="where to write the trace (.jsonl)")
    p.add_argument("--name", default=None, help="label stored in the trace")
    p.add_argument("--task", default=DEFAULT_TASK)
    a = p.parse_args()

    prompt = open(a.prompt, encoding="utf-8").read()
    name = a.name or os.path.splitext(os.path.basename(a.prompt))[0]
    trace = run_agent(prompt, a.task, name=name)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    trace.save(a.out)
    print(f"saved {a.out}: {len(trace.steps)} steps, {trace.total_tokens} tokens, "
          f"answer={trace.final_answer}")


if __name__ == "__main__":
    main()
