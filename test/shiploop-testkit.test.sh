#!/usr/bin/env bash
# Isolation pins for test/shiploop-testkit.sh (no ShipLoop CLI).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
# shellcheck source=shiploop-testkit.sh
source "$root/test/shiploop-testkit.sh"

fail() {
  printf 'shiploop-testkit.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

host_tmp="${TMPDIR:-/tmp}"

shiploop_suite_begin shiploop-testkit-pin
[[ -n "$SUITE_TMP" && -d "$SUITE_TMP" ]] || fail "suite_begin missing SUITE_TMP"

pkt_h2=$'## Next prompt\njob1\n## 2. Best\njob2\n## When done invoke\n'
got2="$(packet_section "$pkt_h2" "## Next prompt")"
printf '%s\n' "$got2" | grep -Fq 'job1' || fail "2-arg dropped job1"
if printf '%s\n' "$got2" | grep -Fq 'job2'; then
  fail "2-arg included body after inner ##"
fi
got3="$(packet_section "$pkt_h2" "## Next prompt" "## When done invoke")"
printf '%s\n' "$got3" | grep -Fq 'job2' || fail "3-arg missed job2 past inner ##"
pkt_h3=$'## Next prompt\njob1\n### 2. Best\njob2\n## When done invoke\n'
got_h3="$(packet_section "$pkt_h3" "## Next prompt")"
printf '%s\n' "$got_h3" | grep -Fq 'job2' || fail "2-arg stopped at ###"
case "$TMPDIR" in
  "$SUITE_TMP"/*) ;;
  *) fail "TMPDIR not inside SUITE_TMP: $TMPDIR" ;;
esac

tmpf="$(mktemp "${TMPDIR}/pin.XXXXXX")"
[[ -f "$tmpf" ]] || fail "mktemp failed"
case "$tmpf" in
  "$SUITE_TMP"/*) ;;
  *) fail "mktemp escaped suite: $tmpf" ;;
esac
case "$tmpf" in
  "$host_tmp"/pin.*) fail "mktemp used host TMPDIR: $tmpf" ;;
esac

shiploop_sandbox_open A
dir_a="$SL_DIR"
run_a="$SL_RUN"
printf 'secret-a\n' >"$SL_DIR/marker-a"
mkdir -p "$SL_REPO"
printf 'repo-a\n' >"$SL_REPO/file.txt"
[[ -d "$dir_a" ]] || fail "sandbox A missing"

set +e
out_open="$(shiploop_sandbox_open B 2>&1)"
rc_open=$?
set -e
[[ "$rc_open" -ne 0 ]] || fail "second sandbox_open should fail"
printf '%s\n' "$out_open" | grep -qi 'still open' || fail "second open message: $out_open"

shiploop_sandbox_close
[[ ! -d "$dir_a" ]] || fail "sandbox_close left $dir_a"
[[ ! -f "$dir_a/marker-a" ]] || fail "sandbox_close left marker-a"
[[ ! -e "$run_a" ]] || fail "sandbox_close left SL_RUN"

shiploop_sandbox_open B
[[ "$SL_DIR" != "$dir_a" ]] || fail "B reused A path"
[[ ! -f "$SL_DIR/marker-a" ]] || fail "B saw A's marker"
printf 'secret-b\n' >"$SL_DIR/marker-b"

# Worktree teardown: extra checkout under the sandbox repo.
mkdir -p "$SL_REPO"
git -C "$SL_REPO" init >/dev/null
git -C "$SL_REPO" config user.email "shiploop-test@example.com"
git -C "$SL_REPO" config user.name "ShipLoop Test"
git -C "$SL_REPO" config commit.gpgsign false
printf 'seed\n' >"$SL_REPO/README"
git -C "$SL_REPO" add README
git -C "$SL_REPO" commit -m seed >/dev/null
wt="$SL_DIR/extra-wt"
git -C "$SL_REPO" worktree add "$wt" -b pin-wt >/dev/null 2>&1
[[ -d "$wt" ]] || fail "worktree add failed"
dir_b="$SL_DIR"
shiploop_sandbox_close
[[ ! -d "$dir_b" ]] || fail "close left sandbox B"
[[ ! -d "$wt" ]] || fail "close left git worktree $wt"

# After close, a new A must not see old files.
shiploop_sandbox_open A
[[ ! -f "$SL_DIR/marker-a" ]] || fail "reopened A saw previous marker"
shiploop_sandbox_close

suite_path="$SUITE_TMP"
trap - EXIT
shiploop_suite_cleanup
[[ ! -d "$suite_path" ]] || fail "suite_cleanup left $suite_path"
[[ ! -f "$tmpf" ]] || fail "suite_cleanup left mktemp file"

printf 'shiploop-testkit.test.sh: PASS\n'
