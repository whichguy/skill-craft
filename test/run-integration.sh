#!/usr/bin/env bash
# Explicit optional integrations.  This entrypoint is intentionally absent from
# default CI; list/help are host-independent and selected checks fail closed.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

usage() {
  cat <<'EOF'
Usage: test/run-integration.sh <command>

Optional commands (never part of default CI):
  list, --list       List available optional integrations.
  help, --help, -h   Show this help without checking host prerequisites.
  cursor-imports     Verify imported Cursor skills are available on this host.
  marketplace-claude  Install local candidate plugins in a disposable Claude profile.
  marketplace-grok    Install local candidate plugins in a disposable Grok profile.
  marketplace-codex   Install local candidate plugins in a disposable Codex profile.
  marketplace-codex-ask-agent  Exercise installed Ask Agent in a disposable Codex profile.
  shiploop-e2e [--case NAME | --prompt TEXT --check CMD] [run.py options]
                    Run ShipLoop live from one prompt in a new empty directory
                    (Grok, medium effort, by default) and grade it. Costs money.
  shiploop-e2e-review RUN_DIR [review.py options]
                    Ask a reviewer model what that run teaches about the skill.
  shiploop-e2e-iterate [--case NAME] [--iterations N] [iterate.py options]
                    Run, review, improve and rerun ShipLoop in a dedicated
                    worktree until clean or capped. Publishes nothing.
  current-dispatcher --dispatcher-skill /absolute/SKILL.md --output /new/absolute/dir
                    Qualify the offline native-pilot composition against a
                    clean, explicitly selected current Dispatcher checkout.

current-dispatcher is local-only: it neither fetches a dependency nor launches
a model or native agent. Its output directory must be new and outside both
source checkouts.
EOF
}

case "${1:-list}" in
  list|--list|help|--help|-h)
    [[ "$#" == "0" || "$#" == "1" ]] || { usage >&2; exit 64; }
    usage
    ;;
  cursor-imports)
    [[ "$#" == "1" ]] || { usage >&2; exit 64; }
    exec bash "$root/test/cursor-imported-skills.test.sh"
    ;;
  marketplace-claude|marketplace-grok|marketplace-codex)
    [[ "$#" == "1" ]] || { usage >&2; exit 64; }
    exec python3 "$root/test/marketplace-host-smoke.py" --host "${1#marketplace-}"
    ;;
  marketplace-codex-ask-agent)
    [[ "$#" == "1" ]] || { usage >&2; exit 64; }
    exec python3 "$root/test/marketplace-host-smoke.py" --host codex --ask-agent
    ;;
  shiploop-e2e)
    shift
    exec python3 -B "$root/test/shiploop_e2e/run.py" "$@"
    ;;
  shiploop-e2e-review)
    shift
    exec python3 -B "$root/test/shiploop_e2e/review.py" "$@"
    ;;
  shiploop-e2e-iterate)
    shift
    exec python3 -B "$root/test/shiploop_e2e/iterate.py" "$@"
    ;;
  current-dispatcher)
    shift
    exec python3 -B "$root/test/current_dispatcher.py" "$@"
    ;;
  *)
    printf 'run-integration: unknown command %q\n' "$1" >&2
    usage >&2
    exit 64
    ;;
esac
