#!/usr/bin/env bash
# One link of the recommended-gap check (journal Round 7), started through test/shiploop_e2e/run.py and nothing else.
#
#   TREE=<checkout run.py is started from; HEAD must be an ancestor of origin/main> OUT=<output root> bash launch.sh link1 NAME
#       link 1: request.txt as the prompt, in an empty folder
#   TREE=... OUT=... bash launch.sh link2 NAME PRIOR
#       link 2: the request file ShipLoop wrote in PRIOR (an earlier link-1 output folder) as the prompt, in a copy of PRIOR's source
#       checkout (--continue-from); nobody answers anything, a gap needs no person
#
# Host Codex, model gpt-6.1-terra, effort xhigh, --source marketplace (the published build the hosts run), the harness's defaults
# otherwise.  The checks are shell commands run in the run's working folder; each tests a sentence of the request.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
mode="${1:?link1 or link2}"
name="${2:?output folder name}"
: "${TREE:?TREE: the checkout run.py is started from}"
: "${OUT:?OUT: the output root}"

# What both links keep: the basic tool.
C_HELLO='test "$(python3 slug.py "Hello, World!")" = "hello-world"'
C_SPACES='test "$(python3 slug.py "  Many   spaces here ")" = "many-spaces-here"'
C_TESTS='python3 -m unittest -q'
# Link 1 only: the deferral was respected; until a later run builds it, --max-length is an unknown option and exits 2.
C_DEFERRED='python3 slug.py "Hello World" --max-length 5 >/dev/null 2>&1; test $? -eq 2'
# Link 2 only: the option is built, with the request's two examples.
C_MAX8='test "$(python3 slug.py "Hello, World" --max-length 8)" = "hello-wo"'
C_MAX6='test "$(python3 slug.py "Hello, World" --max-length 6)" = "hello"'

common=(--host codex --model gpt-6.1-terra --effort xhigh --source marketplace --output "$OUT/$name")
case "$mode" in
  link1)
    exec python3 -I "$TREE/test/shiploop_e2e/run.py" --prompt "$(cat "$here/request.txt")" \
      --check "$C_HELLO" --check "$C_SPACES" --check "$C_DEFERRED" --check "$C_TESTS" "${common[@]}"
    ;;
  link2)
    prior="${3:?PRIOR: the link-1 output folder}"
    request=$(ls "$prior"/.shiploop-runs/*/run/follow-on-request.md 2>/dev/null | head -1)
    [ -n "$request" ] || { echo "no follow-on-request.md under $prior: link 1 recommended nothing" >&2; exit 3; }
    exec python3 -I "$TREE/test/shiploop_e2e/run.py" --prompt "$(cat "$request")" --continue-from "$prior" \
      --check "$C_HELLO" --check "$C_SPACES" --check "$C_MAX8" --check "$C_MAX6" --check "$C_TESTS" "${common[@]}"
    ;;
  *)
    echo "usage: launch.sh link1 NAME | link2 NAME PRIOR" >&2
    exit 2
    ;;
esac
