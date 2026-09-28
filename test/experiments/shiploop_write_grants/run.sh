#!/bin/sh
# Run probe.py under one host sandbox variant. Usage: run.sh BASE VARIANT
# BASE comes from setup.sh. Prints the PROBE line (or the host's transcript tail).
set -u
base="$1"; variant="$2"
here="$(cd "$(dirname "$0")" && pwd)"
probe="python3 $here/probe.py --repo $base/src/toy --runs-parent $base/src/.shiploop-runs"
ask="Run this exact shell command once and reply with its output line verbatim, nothing else: $probe"
cd "$base/src/toy"
case "$variant" in
  codex-ws)        codex sandbox -c 'sandbox_mode="workspace-write"' -- $probe ;;
  codex-ws-grant)  codex sandbox -c 'sandbox_mode="workspace-write"' \
                     -c "sandbox_workspace_write.writable_roots=[\"$base/src/.shiploop-runs\",\"$base/src/toy/.git\"]" -- $probe ;;
  codex-exec-ws)   codex exec --skip-git-repo-check -s workspace-write "$ask" 2>&1 | grep PROBE ;;
  codex-exec-ws-grant) codex exec --skip-git-repo-check -s workspace-write --add-dir "$base/src/.shiploop-runs" \
                     -c "sandbox_workspace_write.writable_roots=[\"$base/src/toy/.git\"]" "$ask" 2>&1 | grep PROBE ;;
  grok-off)        grok -p "$ask" --permission-mode bypassPermissions 2>&1 | grep PROBE ;;
  grok-workspace)  grok -p "$ask" --sandbox workspace --permission-mode bypassPermissions 2>&1 | grep PROBE ;;
  grok-strict)     grok -p "$ask" --sandbox strict --permission-mode bypassPermissions 2>&1 | grep PROBE ;;
  claude-plain)    claude -p "$ask" --permission-mode bypassPermissions 2>&1 | grep PROBE ;;
  claude-sandbox)  claude -p "$ask" --permission-mode bypassPermissions \
                     --settings '{"sandbox":{"enabled":true,"autoAllowBashIfSandboxed":true,"allowUnsandboxedCommands":false}}' 2>&1 | grep PROBE ;;
  claude-sandbox-grant) claude -p "$ask" --permission-mode bypassPermissions --add-dir "$base/src/.shiploop-runs" \
                     --settings '{"sandbox":{"enabled":true,"autoAllowBashIfSandboxed":true,"allowUnsandboxedCommands":false}}' 2>&1 | grep PROBE ;;
  # Acceptance: the real ShipLoop start under Codex's seatbelt, without and with the printed grant.
  shiploop-codex)  codex sandbox -c 'sandbox_mode="workspace-write"' -- \
                     python3 "$here/../../../skills/shiploop/scripts/shiploop" workspace start --repo . --prompt 'Grant acceptance.'
                   echo "exit=$?" ;;
  shiploop-codex-grant) codex sandbox -c 'sandbox_mode="workspace-write"' \
                     -c "sandbox_workspace_write.writable_roots=[\"$base/src/.shiploop-runs\",\"$base/src/toy/.git\"]" -- \
                     python3 "$here/../../../skills/shiploop/scripts/shiploop" workspace start --repo . --prompt 'Grant acceptance.' | head -3
                   echo "exit=$?" ;;
  # Acceptance through a real Claude model with the Bash sandbox on.
  shiploop-claude-sandbox|shiploop-claude-sandbox-grant)
                   start="python3 $here/../../../skills/shiploop/scripts/shiploop workspace start --repo . --prompt 'Grant acceptance.'"
                   extra=""; [ "$variant" = shiploop-claude-sandbox-grant ] && extra="--add-dir $base/src/.shiploop-runs"
                   claude -p "Run this exact shell command once, then reply with its exit code on a line 'EXIT=<n>' followed by its complete stderr and the first 2 lines of stdout, verbatim: $start" \
                     --permission-mode bypassPermissions $extra \
                     --settings '{"sandbox":{"enabled":true,"autoAllowBashIfSandboxed":true,"allowUnsandboxedCommands":false}}' 2>&1 ;;
  *) echo "unknown variant $variant" >&2; exit 2 ;;
esac
