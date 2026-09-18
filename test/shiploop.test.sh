#!/usr/bin/env bash
# Stable CI entrypoint for ShipLoop's Markdown-authoritative protocol suites.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"

# The one ordered ShipLoop inventory. Full runs and CI shards select only from
# this array so a suite cannot silently drift between their inventories.
suites=(
  test/shiploop-context-host.test.py \
  test/shiploop-host-codex.test.py \
  test/shiploop-host-grok.test.py \
  test/shiploop-host-claude.test.py \
  test/shiploop-navigator.test.py \
  test/shiploop-navigator-v3.test.py \
  test/shiploop-standalone-improve.test.py \
  test/shiploop-actual-improve-cli.test.py \
  test/shiploop-packet-bounds.test.py \
  test/shiploop-v3-guidance.test.py \
  test/shiploop-full-runtime.test.py \
  test/shiploop-navigator-dry-run.test.py \
  test/shiploop-auth-readiness.test.py \
  test/shiploop-environment-lifecycle.test.py \
  test/shiploop-cross-run.test.py \
  test/shiploop-workspace.test.py \
  test/shiploop-consumer-delivery.test.py \
  test/shiploop-consumer-delivery-cli.test.py \
  test/shiploop-delivery-prompts.test.py \
  test/experiments/shiploop_delivery/fake_deployment.test.py \
  test/experiments/shiploop_delivery/browser_consumer/serve_fixture.test.py \
  test/improve-managed.test.py \
  test/shiploop-graph-driver.test.py \
  test/shiploop-graph-trace.test.py \
  test/shiploop-store.test.py \
  test/shiploop-evidence.test.py \
  test/shiploop-file-safety.test.py \
  test/shiploop-prompt-integrity.test.py \
  test/shiploop-literal-transport.test.py \
  test/shiploop-validators.test.py \
  test/shiploop-discovery.test.py \
  test/shiploop-capability-fixture.test.py \
  test/shiploop-capability-runtime.test.py \
  test/shiploop-generalized-discovery.test.py \
  test/shiploop-capability-async.test.cjs \
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
  test/shiploop-improve-policy.test.py \
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
  test/shiploop-backchain-guidance.test.py \
  test/shiploop-teachback.test.py \
  test/shiploop-protocol.test.py \
  test/shiploop-history-pages.test.py \
  test/shiploop-merge-recovery.test.py \
  test/shiploop-migration-prompt.test.py \
  test/shiploop-knowledge.test.py \
  test/shiploop-planning.test.py \
  test/shiploop-until.test.py \
  test/shiploop-step-planning.test.py \
  test/shiploop-sdlc.test.py \
  test/shiploop-improve-bridge.test.py \
  test/shiploop-managed-contracts.test.py \
  test/shiploop-invalidation.test.py \
  test/shiploop-managed-invalidation.test.py \
  test/shiploop-managed-package.test.py \
  test/shiploop-managed-walk.test.py \
  test/shiploop-action-walk.test.py
)

usage() {
  printf 'Usage: bash test/shiploop.test.sh [--shard 1/3|2/3|3/3] [--list]\n'
}

shard=""
list_only=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --shard)
      [[ $# -ge 2 && -z "$shard" ]] || { usage >&2; exit 64; }
      case "$2" in
        1/3|2/3|3/3) shard="$2" ;;
        *) usage >&2; exit 64 ;;
      esac
      shift 2
      ;;
    --list)
      [[ "$list_only" -eq 0 ]] || { usage >&2; exit 64; }
      list_only=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 64
      ;;
  esac
done

shard_index=0
if [[ -n "$shard" ]]; then
  shard_index="${shard%%/*}"
fi

for index in "${!suites[@]}"; do
  if [[ -n "$shard" ]] && (( index % 3 != shard_index - 1 )); then
    continue
  fi
  if [[ "$list_only" -eq 1 ]]; then
    printf '%s\n' "${suites[$index]}"
  fi
done

[[ "$list_only" -eq 0 ]] || exit 0

printf '==> scripts/sync-improve-managed.py\n'
PYTHONDONTWRITEBYTECODE=1 python3 scripts/sync-improve-managed.py

for index in "${!suites[@]}"; do
  if [[ -n "$shard" ]] && (( index % 3 != shard_index - 1 )); then
    continue
  fi
  suite="${suites[$index]}"
  printf '==> %s\n' "$suite"
  case "$suite" in
    *.py) PYTHONDONTWRITEBYTECODE=1 python3 "$suite" ;;
    *.cjs) node "$suite" ;;
    *) printf 'Unknown suite interpreter: %s\n' "$suite" >&2; exit 64 ;;
  esac
done

printf 'shiploop.test.sh: PASS\n'
