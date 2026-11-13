#!/usr/bin/env bash
# X-A (README.md): N samples of step-plan/proof-runs-focused-suite for one arm, Codex Terra 6.1 xhigh, from this checkout's
# stage suite with the plugin built from the arm's commit.
#   bash launch_xa.sh <arm label> <arm commit> <samples> <jobs> <results root>
# Example: bash launch_xa.sh B 49d21bc5bd3c76dfd5a3a9b1c88a840c022bb019 4 2 ~/e2e-runs-sp/20261101/round2/xa-B
set -euo pipefail
arm=$1 ref=$2 samples=$3 jobs=$4 out=$5
root=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
[ -e "$out" ] && { echo "refusing: $out exists (stages.py live needs a new folder)" >&2; exit 2; }
mkdir -p "$(dirname "$out")"
echo "$(date -u +%FT%TZ) arm=$arm ref=$ref samples=$samples jobs=$jobs out=$out checkout=$(git -C "$root" rev-parse HEAD)" \
  >> "$(dirname "$out")/launch.log"
exec python3 "$root/test/shiploop_e2e/stage_suite/stages.py" live step-plan/proof-runs-focused-suite \
  --host codex --model gpt-6.1-terra --effort xhigh --ref "$ref" --samples "$samples" --jobs "$jobs" --out "$out"
