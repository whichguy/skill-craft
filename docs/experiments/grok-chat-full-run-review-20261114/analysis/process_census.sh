#!/usr/bin/env bash
# How often a model ran a whole-machine process listing, over the retained runs' host events.
#
#   bash process_census.sh RUN_DIR   # RUN_DIR: this trial's harness output, the positive control
#
# The strict pattern is a command that starts `ps -axo`, `ps aux`, `ps -ef` or `ps -e`; the loose one any ps, lsof or
# pgrep.  Both read the "command" key of each host tool call, which every host's events carry.  A zero from the strict
# pattern means no such command in any retained run, and the control proves the pattern matches where one is known.
# `find -exec grep ... {} +` is used, not xargs: BSD xargs -I refuses some of these long paths ("command line cannot be
# assembled, too long"), which silently shortens the list.  Every error is printed, and a file count is printed first.
set -euo pipefail
control="$1"
roots=("$HOME/e2e-runs" "$HOME/e2e-runs-sp")
strict='"command": "[^"]*(ps -axo|ps aux|ps -ef|ps -e )'
loose='"command": "[^"]*(\bps -|\bps aux|\blsof\b|\bpgrep\b)'
total=$(find "${roots[@]}" -name events.jsonl -size +100k | wc -l)
echo "events.jsonl files over 100 KB: $total"
for name in strict loose; do
  pattern="${!name}"
  # grep exits 1 when a batch has no match; that is a count of zero here, not a failure
  hits=$({ find "${roots[@]}" -name events.jsonl -size +100k -exec grep -l -E "$pattern" {} + || true; } | wc -l)
  echo "$name pattern, retained runs: $hits of $total"
done
echo "positive control, this trial: $(grep -c -E "$strict" "$control/events.jsonl") matching lines"
