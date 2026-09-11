#!/usr/bin/env bash
# Stable CI entrypoint for ShipLoop's Markdown-authoritative protocol suites.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"

for suite in \
  test/shiploop-store.test.py \
  test/shiploop-evidence.test.py \
  test/shiploop-validators.test.py \
  test/shiploop-protocol.test.py; do
  printf '==> %s\n' "$suite"
  PYTHONDONTWRITEBYTECODE=1 python3 "$suite"
done

printf 'shiploop.test.sh: PASS\n'
