#!/usr/bin/env bash
# Stable CI entrypoint for the action-oriented one-step ShipLoop walk.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"

suite="test/shiploop-action-walk.test.py"
if [[ ! -f "$suite" ]]; then
  printf 'shiploop-walk-journal.test.sh: missing %s\n' "$suite" >&2
  exit 1
fi

PYTHONDONTWRITEBYTECODE=1 python3 "$suite"
printf 'shiploop-walk-journal.test.sh: PASS\n'
