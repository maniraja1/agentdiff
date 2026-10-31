#!/usr/bin/env bash
# Record baseline (v1) and candidate (v2) traces, then diff them.
set -euo pipefail
cd "$(dirname "$0")"
python run.py --prompt prompts/v1_baseline.txt  --name v1 --out traces/baseline.jsonl
python run.py --prompt prompts/v2_candidate.txt --name v2 --out traces/candidate.jsonl
set +e
agentdiff diff traces/baseline.jsonl traces/candidate.jsonl --strict --out traces/report.md
code=$?
echo "agentdiff exit code: $code (0 = pass, 1 = regression)"
exit 0
