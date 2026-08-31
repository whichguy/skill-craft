#!/usr/bin/env bash
# Lightweight setup / test / teardown for ShipLoop hermetic tests.
#
# Source from a test that already has `set -euo pipefail` and (optionally) fail().
# One open sandbox at a time. Sequential walk CASES share a sandbox; independent
# edges get their own. Suite EXIT trap always tears down leftover git worktrees
# then rm -rf the suite tmpdir. mktemp follows TMPDIR inside the suite tmp.
#
#   shiploop_suite_begin <name>
#   shiploop_sandbox_open <layer>
#   # SL_RUN, SL_REPO, SL_DIR
#   shiploop_sandbox_close
#   # suite trap runs shiploop_suite_cleanup
#
# Not the /test-harness FS-audit skill.
if [[ "${SHIPLOOP_TESTKIT_LOADED:-}" == 1 ]]; then
  return 0
fi
SHIPLOOP_TESTKIT_LOADED=1

_shiploop_die() {
  if declare -F fail >/dev/null 2>&1; then
    fail "$*"
  fi
  printf 'shiploop-testkit: FAIL %s\n' "$*" >&2
  exit 1
}

shiploop_teardown_git_repo() {
  local repo="$1"
  [[ -d "$repo" ]] || return 0
  if ! git -C "$repo" rev-parse --git-dir >/dev/null 2>&1; then
    return 0
  fi
  local wt main
  main="$(git -C "$repo" rev-parse --show-toplevel 2>/dev/null || printf '%s' "$repo")"
  while IFS= read -r wt; do
    [[ -n "$wt" ]] || continue
    [[ "$wt" == "$main" ]] && continue
    git -C "$repo" worktree remove --force "$wt" >/dev/null 2>&1 || rm -rf "$wt"
  done < <(git -C "$repo" worktree list --porcelain 2>/dev/null | awk '/^worktree / { print substr($0, 11) }')
  git -C "$repo" worktree prune >/dev/null 2>&1 || true
}

shiploop_sandbox_teardown_dir() {
  local dir="$1"
  [[ -n "$dir" && -d "$dir" ]] || return 0
  local repo
  if [[ -d "$dir/repo" ]]; then
    shiploop_teardown_git_repo "$dir/repo"
  fi
  while IFS= read -r repo; do
    [[ -n "$repo" ]] || continue
    shiploop_teardown_git_repo "$(dirname "$repo")"
  done < <(find "$dir" -type d -name .git 2>/dev/null || true)
  rm -rf "$dir"
}

shiploop_suite_cleanup() {
  local dir repo
  if [[ -n "${SL_DIR:-}" ]]; then
    shiploop_sandbox_teardown_dir "$SL_DIR" || true
  fi
  if [[ -n "${SUITE_TMP:-}" && -d "${SUITE_TMP:-}" ]]; then
    while IFS= read -r repo; do
      [[ -n "$repo" ]] || continue
      shiploop_teardown_git_repo "$(dirname "$repo")" || true
    done < <(find "$SUITE_TMP" -type d -name .git 2>/dev/null || true)
    rm -rf "$SUITE_TMP"
  fi
  if [[ -n "${SUITE_TMPDIR_ORIG+x}" ]]; then
    if [[ -n "${SUITE_TMPDIR_ORIG}" ]]; then
      export TMPDIR="$SUITE_TMPDIR_ORIG"
    else
      unset TMPDIR
    fi
  fi
  SL_DIR=""
  SL_RUN=""
  SL_REPO=""
  SL_NAME=""
  SUITE_TMP=""
}

shiploop_suite_begin() {
  local name="${1:-shiploop}"
  if [[ -n "${SUITE_TMP:-}" ]]; then
    _shiploop_die "suite_begin while SUITE_TMP already set"
  fi
  SUITE_TMPDIR_ORIG="${TMPDIR-}"
  SUITE_TMP="$(mktemp -d "${TMPDIR:-/tmp}/${name}.XXXXXX")"
  mkdir -p "$SUITE_TMP/tmp"
  export TMPDIR="$SUITE_TMP/tmp"
  SL_DIR=""
  SL_RUN=""
  SL_REPO=""
  SL_NAME=""
  trap shiploop_suite_cleanup EXIT
}

shiploop_sandbox_open() {
  local name="${1:-}"
  [[ -n "$name" ]] || _shiploop_die "sandbox_open needs a name"
  [[ -n "${SUITE_TMP:-}" ]] || _shiploop_die "sandbox_open before suite_begin"
  if [[ -n "${SL_DIR:-}" ]]; then
    _shiploop_die "sandbox_open $name while ${SL_NAME:-open} still open; close first"
  fi
  case "$name" in
    *[!A-Za-z0-9._-]*) _shiploop_die "unsafe sandbox name $name" ;;
  esac
  SL_NAME="$name"
  SL_DIR="$SUITE_TMP/sb-$name"
  mkdir -p "$SL_DIR"
  SL_RUN="$SL_DIR/.shiploop"
  SL_REPO="$SL_DIR/repo"
}

shiploop_sandbox_close() {
  local dir="${SL_DIR:-}"
  SL_DIR=""
  SL_RUN=""
  SL_REPO=""
  SL_NAME=""
  [[ -n "$dir" ]] || return 0
  shiploop_sandbox_teardown_dir "$dir"
}

# Extract a packet H2 body. With no stop: until the next `## ` (packet contract).
# With stop: until that exact heading (inner `## ` does not truncate).
# `###` does not match `/^## /`.
packet_section() {
  local out="$1" start="$2" stop="${3:-}"
  printf '%s\n' "$out" | awk -v s="$start" -v e="$stop" '
    $0==s {p=1; next}
    p && e != "" && $0==e {exit}
    p && e == "" && /^## / {exit}
    p
  '
}
