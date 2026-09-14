#!/usr/bin/env bash
# Stable CI entrypoint for ShipLoop's Markdown-authoritative protocol suites.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"

for suite in \
  test/shiploop-store.test.py \
  test/shiploop-evidence.test.py \
  test/shiploop-file-safety.test.py \
  test/shiploop-prompt-integrity.test.py \
  test/shiploop-literal-transport.test.py \
  test/shiploop-validators.test.py \
  test/shiploop-discovery.test.py \
  test/shiploop-system-context.test.py \
  test/shiploop-research-template.test.py \
  test/shiploop-research-packet-protocol.test.py \
  test/shiploop-question-resume.test.py \
  test/shiploop-iteration-docs.test.py \
  test/shiploop-iteration-docs-protocol.test.py \
  test/shiploop-system-tests.test.py \
  test/shiploop-system-tests-protocol.test.py \
  test/shiploop-system-tests-report.test.py \
  test/shiploop-history-policy.test.py \
  test/shiploop-outer-work.test.py \
  test/shiploop-outer-work-protocol.test.py \
  test/shiploop-observations.test.py \
  test/shiploop-observations-protocol.test.py \
  test/shiploop-artifacts.test.py \
  test/shiploop-artifact-consumers.test.py \
  test/shiploop-privacy.test.py \
  test/shiploop-revalidation.test.py \
  test/shiploop-revalidation-context.test.py \
  test/shiploop-risk.test.py \
  test/shiploop-boundaries.test.py \
  test/shiploop-objectives.test.py \
  test/shiploop-contracts.test.py \
  test/shiploop-contract-protocol.test.py \
  test/shiploop-delivery.test.py \
  test/shiploop-report.test.py \
  test/shiploop-packets.test.py \
  test/shiploop-orientation.test.py \
  test/shiploop-loop-scope.test.py \
  test/shiploop-orientation-context.test.py \
  test/shiploop-orientation-integration.test.py \
  test/shiploop-reference-routing.test.py \
  test/shiploop-teachback.test.py \
  test/shiploop-protocol.test.py \
  test/shiploop-history-pages.test.py \
  test/shiploop-merge-recovery.test.py \
  test/shiploop-migration-prompt.test.py \
  test/shiploop-knowledge.test.py \
  test/shiploop-planning.test.py \
  test/shiploop-until.test.py \
  test/shiploop-step-planning.test.py \
  test/shiploop-action-walk.test.py; do
  printf '==> %s\n' "$suite"
  PYTHONDONTWRITEBYTECODE=1 python3 "$suite"
done

printf 'shiploop.test.sh: PASS\n'
