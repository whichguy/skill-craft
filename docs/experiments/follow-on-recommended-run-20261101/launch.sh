#!/usr/bin/env bash
# One link of the recommended-run check (journal Round 6), started through test/shiploop_e2e/run.py and nothing else.
#
#   TREE=<detached checkout of the released tree> OUT=<output root> bash launch.sh link1 NAME
#       link 1: request.txt as the prompt, in an empty folder
#   TREE=... OUT=... bash launch.sh link2 NAME PRIOR
#       link 2: the request file ShipLoop wrote in PRIOR (an earlier link-1 output folder) as the prompt, in a copy of PRIOR's
#       source checkout (--continue-from)
#
# Host Codex, model gpt-6.1-terra, effort xhigh, --source checkout (the plugin tree of $TREE), the harness's defaults otherwise.
# The checks are shell commands run in the run's working folder; each tests a sentence of the request.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
mode="${1:?link1 or link2}"
name="${2:?output folder name}"
: "${TREE:?TREE: the checkout run.py is started from}"
: "${OUT:?OUT: the output root}"

# What link 1 and link 2 both keep: the behaviour the request fixed.
C_HELLO='test "$(python3 slug.py "Hello, World!")" = "hello-world"'
C_SPACES='test "$(python3 slug.py "  Many   spaces here ")" = "many-spaces-here"'
C_TESTS='python3 -m unittest -q'
# Link 1 only: the reserved behaviour, which the request asked for until the SEO team decides.
C_RESERVED='out=$(python3 slug.py "Café" 2>&1 >/dev/null); rc=$?; test "$rc" -eq 2 && printf "%s" "$out" | grep -q "undecided: non-ASCII"'
# Link 2 only: whichever way the finding is settled, a non-ASCII title is handled and does not crash with a traceback (status 1).
C_NO_CRASH='python3 slug.py "Café" >/dev/null 2>&1; test $? -ne 1'

common=(--host codex --model gpt-6.1-terra --effort xhigh --source checkout --output "$OUT/$name")
case "$mode" in
  link1)
    exec python3 -I "$TREE/test/shiploop_e2e/run.py" --prompt "$(cat "$here/request.txt")" \
      --check "$C_HELLO" --check "$C_SPACES" --check "$C_RESERVED" --check "$C_TESTS" "${common[@]}"
    ;;
  link2)
    prior="${3:?PRIOR: the link-1 output folder}"
    request=$(ls "$prior"/.shiploop-runs/*/run/follow-on-request.md 2>/dev/null | head -1)
    [ -n "$request" ] || { echo "no follow-on-request.md under $prior: link 1 recommended nothing" >&2; exit 3; }
    exec python3 -I "$TREE/test/shiploop_e2e/run.py" --prompt "$(cat "$request")" --continue-from "$prior" \
      --check "$C_HELLO" --check "$C_SPACES" --check "$C_NO_CRASH" --check "$C_TESTS" "${common[@]}"
    ;;
  *)
    echo "usage: launch.sh link1 NAME | link2 NAME PRIOR" >&2
    exit 2
    ;;
esac
