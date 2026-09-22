#!/usr/bin/env bash
# Stable ShipLoop facade: --smoke, --shard N/3, and --list stay compatible.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"
exec python3 -B test/run_suites.py --shiploop-entrypoint "$@"
