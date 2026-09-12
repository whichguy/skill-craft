#!/usr/bin/env bash
# Stable CI entrypoint for ShipLoop's Markdown-authoritative protocol suites.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"

for suite in \
  test/shiploop-store.test.py \
  test/shiploop-evidence.test.py \
  test/shiploop-validators.test.py \
  test/shiploop-boundaries.test.py \
  test/shiploop-objectives.test.py \
  test/shiploop-contracts.test.py \
  test/shiploop-contract-protocol.test.py \
  test/shiploop-delivery.test.py \
  test/shiploop-report.test.py \
  test/shiploop-packets.test.py \
  test/shiploop-protocol.test.py \
  test/shiploop-knowledge.test.py \
  test/shiploop-planning.test.py \
  test/shiploop-until.test.py \
  test/shiploop-step-planning.test.py \
  test/shiploop-action-walk.test.py; do
  printf '==> %s\n' "$suite"
  PYTHONDONTWRITEBYTECODE=1 python3 "$suite"
done

printf 'shiploop.test.sh: PASS\n'
