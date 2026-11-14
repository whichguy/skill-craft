#!/usr/bin/env bash
# worktree-fixloop.sh — enter/exit disposable fix-loop worktree (package-aware).
#
# --repo is WORK_ROOT (suite cwd; skill package path OK). Worktree is always created
# from GIT_ROOT so nested packages get a full monorepo checkout; suite_cwd is the
# package subpath inside the worktree.
#
# enter: git worktree add under $RUN_DIR/worktree; overlay launch dirty paths
#        (scoped to AUDIT_PREFIX when nested); write $RUN_DIR/scope.json + suite_cwd
# exit:  remove if clean, else write fixes.patch and keep
#
# Usage:
#   worktree-fixloop.sh enter --repo <work_root> --run-dir <dir> [--slug <s>]
#   worktree-fixloop.sh exit  --repo <work_root> --run-dir <dir>
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd -P)"

ACTION="${1:-}"
shift || true

REPO=""
RUN_DIR=""
SLUG_OVERRIDE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO="${2:-}"; shift 2 ;;
    --run-dir) RUN_DIR="${2:-}"; shift 2 ;;
    --slug) SLUG_OVERRIDE="${2:-}"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$REPO" || -z "$RUN_DIR" ]]; then
  echo "usage: $0 enter|exit --repo <work_root> --run-dir <dir>" >&2
  exit 1
fi
if [[ ! -d "$REPO" ]]; then
  echo "error: --repo not a directory: $REPO" >&2
  exit 1
fi

SCOPE_JSON="$(python3 "$SKILL_DIR/scripts/resolve-scope.py" --repo "$REPO")"
eval "$(python3 -c '
import json,sys,shlex
d=json.loads(sys.argv[1])
def e(k,v):
    if v is None: v=""
    print(f"{k}={shlex.quote(str(v))}")
e("WORK_ROOT", d["work_root"])
e("GIT_ROOT", d.get("git_root") or "")
e("AUDIT_PREFIX", d.get("audit_prefix") or "")
e("PORC_REPO", d["porc_repo"])
e("SUITE_REL", d.get("suite_rel") or "")
e("SLUG", d["slug"])
' "$SCOPE_JSON")"

# Git operations always use git root when available
GIT_BASE="${GIT_ROOT:-$WORK_ROOT}"
if [[ -n "$SLUG_OVERRIDE" ]]; then
  SLUG="$SLUG_OVERRIDE"
fi

mkdir -p "$RUN_DIR"
RUN_DIR="$(cd "$RUN_DIR" && pwd -P)"
WT="$RUN_DIR/worktree"
printf '%s\n' "$SCOPE_JSON" >"$RUN_DIR/scope.json"

json_out() {
  python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1]), separators=(",", ":")))' "$1"
}

suite_cwd_for() {
  local base="$1"
  if [[ -n "$SUITE_REL" ]]; then
    echo "$base/$SUITE_REL"
  else
    echo "$base"
  fi
}

case "$ACTION" in
  enter)
    if [[ -d "$WT" ]]; then
      branch="$(git -C "$WT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
      sc="$(suite_cwd_for "$WT")"
      json_out "{\"workspace\":\"$WT\",\"suite_cwd\":\"$sc\",\"branch\":\"$branch\",\"mode\":\"reuse\",\"git_root\":\"$GIT_BASE\",\"work_root\":\"$WORK_ROOT\",\"audit_prefix\":\"$AUDIT_PREFIX\"}"
      exit 0
    fi
    RAND="$(openssl rand -hex 3 2>/dev/null || python3 -c 'import secrets;print(secrets.token_hex(3))')"
    # The slug is a folder name; a branch name cannot hold spaces, "~", "^", ":", ".." and more, so keep a safe subset.
    BRANCH_SLUG="$(printf '%s' "$SLUG" | LC_ALL=C tr -c 'A-Za-z0-9_-' '-' | sed -E 's/-+/-/g; s/^-//; s/-$//')"
    [[ -n "$BRANCH_SLUG" ]] || BRANCH_SLUG="repo"
    BRANCH="test-harness/${BRANCH_SLUG}-${RAND}"
    # Full-repo worktree from git base (not package-only — paths are git-root-relative)
    git -C "$GIT_BASE" worktree add -b "$BRANCH" "$WT" HEAD >/dev/null

    # Overlay launch dirty paths into worktree (scoped to package when nested)
    while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      status="${line:0:2}"
      rest="${line:3}"
      path=""
      if [[ "$status" == R* || "$status" == C* ]]; then
        path="${rest##* -> }"
        path="${path#\"}"; path="${path%\"}"
      else
        path="$rest"
        if [[ "$path" == \"*\" ]]; then
          path="$(printf '%b' "${path:1:${#path}-2}")"
        fi
      fi
      [[ -z "$path" ]] && continue
      # Package scope: only overlay paths under AUDIT_PREFIX
      if [[ -n "$AUDIT_PREFIX" ]]; then
        case "$path" in
          "$AUDIT_PREFIX"|"$AUDIT_PREFIX"/*) ;;
          *) continue ;;
        esac
      fi
      src="$GIT_BASE/$path"
      dst="$WT/$path"
      if [[ -e "$src" || -L "$src" ]]; then
        mkdir -p "$(dirname "$dst")"
        if [[ -d "$src" && ! -L "$src" ]]; then
          rm -rf "$dst"
          cp -a "$src" "$dst"
        else
          cp -a "$src" "$dst"
        fi
      elif [[ "$status" == *D* || "$status" == D* ]]; then
        rm -rf "$dst"
      fi
    done < <(
      if [[ -n "$AUDIT_PREFIX" ]]; then
        git -C "$GIT_BASE" status --porcelain -uall -- "$AUDIT_PREFIX" 2>/dev/null || true
      else
        git -C "$GIT_BASE" status --porcelain -uall 2>/dev/null || true
      fi
    )

    sc="$(suite_cwd_for "$WT")"
    # Record for agents
    python3 -c '
import json,sys
from pathlib import Path
rd=Path(sys.argv[1])
data={
  "workspace": sys.argv[2],
  "suite_cwd": sys.argv[3],
  "branch": sys.argv[4],
  "git_root": sys.argv[5],
  "work_root": sys.argv[6],
  "audit_prefix": sys.argv[7],
  "mode": "created",
}
(rd/"worktree-meta.json").write_text(json.dumps(data, indent=2)+"\n")
print(json.dumps(data, separators=(",", ":")))
' "$RUN_DIR" "$WT" "$sc" "$BRANCH" "$GIT_BASE" "$WORK_ROOT" "$AUDIT_PREFIX"
    ;;

  exit)
    if [[ ! -d "$WT" ]]; then
      json_out '{"removed":false,"reason":"no_worktree"}'
      exit 0
    fi
    dirty="$(git -C "$WT" status --porcelain -uall 2>/dev/null || true)"
    # When package-scoped, only package dirt blocks auto-remove (optional strict)
    if [[ -n "$AUDIT_PREFIX" && -n "$dirty" ]]; then
      # still consider whole worktree dirty for patch purposes
      :
    fi
    if [[ -z "$dirty" ]]; then
      branch="$(git -C "$WT" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
      git -C "$GIT_BASE" worktree remove --force "$WT" >/dev/null 2>&1 || rm -rf "$WT"
      if [[ -n "$branch" && "$branch" == test-harness/* ]]; then
        git -C "$GIT_BASE" branch -D "$branch" >/dev/null 2>&1 || true
      fi
      json_out '{"removed":true,"kept":false}'
    else
      git -C "$WT" diff HEAD > "$RUN_DIR/fixes.patch" 2>/dev/null || true
      git -C "$WT" status --porcelain -uall > "$RUN_DIR/worktree-status.txt" 2>/dev/null || true
      json_out "{\"removed\":false,\"kept\":true,\"worktree\":\"$WT\",\"suite_cwd\":\"$(suite_cwd_for "$WT")\",\"fixes_patch\":\"$RUN_DIR/fixes.patch\"}"
    fi
    ;;

  *)
    echo "usage: $0 enter|exit --repo <work_root> --run-dir <dir>" >&2
    exit 1
    ;;
esac
