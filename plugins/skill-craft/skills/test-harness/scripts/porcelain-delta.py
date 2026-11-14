#!/usr/bin/env python3
"""porcelain-delta.py — content-aware FS snapshots, diff, and restore for test-harness.

Modes:
  snapshot --side pre|post   write round-N/{pre,post}/ + optional invoke-baseline
  diff                       compare pre vs post → delta JSON
  restore                    restore suite side effects from round-N/pre (or checkout)

Never uses git hash-object. Raw hashlib.sha256 + filesystem byte copies only.

Package scope (monorepo skill subdirs):
  --repo is the start path (usually WORK_ROOT / suite cwd).
  git_root is resolved via `git rev-parse --show-toplevel`.
  All git -C and Path joins use git_root (porcelain paths are git-root-relative).
  Optional --path-prefix REL filters porcelain + ignored inventory to that package.
  When path-prefix is set, fs_scope is "package" and audit_prefix is emitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_PER_FILE_CAP = int(os.environ.get("TEST_HARNESS_PER_FILE_CAP", str(8 * 1024 * 1024)))
DEFAULT_TOTAL_CAP = int(os.environ.get("TEST_HARNESS_TOTAL_CAP", str(256 * 1024 * 1024)))
DEFAULT_IGNORED_PATH_CAP = int(os.environ.get("TEST_HARNESS_IGNORED_PATH_CAP", "5000"))


def run_git(git_root: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", git_root, *args],
        capture_output=True,
        text=True,
        check=False,
    )


def resolve_git_root(repo: str) -> str | None:
    """Return absolute git toplevel for repo, or None if not a git work tree."""
    r = run_git(repo, "rev-parse", "--show-toplevel")
    if r.returncode != 0:
        return None
    top = (r.stdout or "").strip()
    if not top:
        return None
    return str(Path(top).resolve())


def normalize_path_prefix(prefix: str | None) -> str:
    """Posix relative prefix, no leading/trailing slash (empty = full repo)."""
    if not prefix:
        return ""
    p = prefix.strip().replace("\\", "/").lstrip("/")
    while p.endswith("/"):
        p = p[:-1]
    if p in (".",):
        return ""
    return p


def path_under_prefix(path: str, prefix: str) -> bool:
    """True if path is equal to prefix or a descendant (posix, git-root-relative)."""
    if not prefix:
        return True
    path = path.replace("\\", "/").lstrip("./")
    return path == prefix or path.startswith(prefix + "/")


def unquote(p: str) -> str:
    if len(p) >= 2 and p[0] == '"' and p[-1] == '"':
        # git C-style escapes
        return bytes(p[1:-1], "utf-8").decode("unicode_escape")
    return p


def parse_porcelain(git_root: str, path_prefix: str = "") -> list[dict[str, str]]:
    """Parse `git status --porcelain -uall` into [{xy, path, path_old?}].

    Paths are always relative to git_root. When path_prefix is set, restrict via
    pathspec and post-filter renames that leave the package.
    """
    args = ["status", "--porcelain", "-uall"]
    if path_prefix:
        args.extend(["--", path_prefix])
    r = run_git(git_root, *args)
    out = r.stdout or ""
    entries: list[dict[str, str]] = []
    for line in out.splitlines():
        if not line or len(line) < 3:
            continue
        xy = line[:2]
        rest = line[3:]
        path_old = None
        if xy[0] in ("R", "C"):
            if " -> " in rest:
                old, new = rest.split(" -> ", 1)
                path_old = unquote(old)
                path = unquote(new)
            else:
                path = unquote(rest)
        else:
            path = unquote(rest)
        if path_prefix:
            # Keep if new path (or old rename source) is under prefix
            if not (
                path_under_prefix(path, path_prefix)
                or (path_old and path_under_prefix(path_old, path_prefix))
            ):
                continue
        entries.append({"xy": xy, "path": path, **({"path_old": path_old} if path_old else {})})
    return entries


def sha256_file(path: Path) -> str | None:
    if not path.is_file() and not path.is_symlink():
        if path.is_dir():
            # directory marker — hash listing
            h = hashlib.sha256()
            for root, dirs, files in os.walk(path):
                dirs.sort()
                for f in sorted(files):
                    fp = Path(root) / f
                    rel = fp.relative_to(path).as_posix()
                    h.update(rel.encode())
                    try:
                        h.update(fp.read_bytes())
                    except OSError:
                        pass
            return h.hexdigest()
        return None
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def file_size(path: Path) -> int:
    try:
        if path.is_file() or path.is_symlink():
            return path.stat().st_size
        if path.is_dir():
            total = 0
            for root, _dirs, files in os.walk(path):
                for f in files:
                    try:
                        total += (Path(root) / f).stat().st_size
                    except OSError:
                        pass
            return total
    except OSError:
        pass
    return 0


def copy_path(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir() and not src.is_symlink():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, symlinks=True)
    else:
        if dst.exists() or dst.is_symlink():
            if dst.is_dir() and not dst.is_symlink():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        shutil.copy2(src, dst, follow_symlinks=False)


def hardlink_or_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    try:
        if src.is_file() and not src.is_symlink():
            os.link(src, dst)
            return
    except OSError:
        pass
    copy_path(src, dst)


def head_sha(git_root: str) -> str:
    r = run_git(git_root, "rev-parse", "HEAD")
    return (r.stdout or "").strip()


def ignored_inventory(
    git_root: str, path_cap: int, total_cap: int, path_prefix: str = ""
) -> dict[str, Any]:
    args = ["ls-files", "-o", "-i", "--exclude-standard"]
    if path_prefix:
        args.extend(["--", path_prefix])
    r = run_git(git_root, *args)
    paths = [p for p in (r.stdout or "").splitlines() if p]
    if path_prefix:
        paths = [p for p in paths if path_under_prefix(p, path_prefix)]
    over = len(paths) > path_cap
    if over:
        paths = paths[:path_cap]
    items = []
    budget = 0
    budget_hit = False
    for p in paths:
        fp = Path(git_root) / p
        sz = file_size(fp) if fp.exists() else 0
        if budget + sz > total_cap:
            budget_hit = True
            break
        budget += sz
        items.append({"path": p, "sha256": sha256_file(fp) if fp.exists() else None, "size": sz})
    scope = "full"
    if over or budget_hit:
        scope = "git-visible-only"
    return {"paths": items, "fs_scope": scope, "count": len(items), "truncated": over or budget_hit}


def resolve_scope(repo: str, path_prefix: str | None) -> dict[str, Any]:
    """Resolve git_root, work context, and normalized audit prefix."""
    work_root = str(Path(repo).resolve())
    git_root = resolve_git_root(work_root)
    prefix = normalize_path_prefix(path_prefix)
    if git_root is None:
        return {
            "work_root": work_root,
            "git_root": None,
            "audit_prefix": prefix,
            "fs_scope_base": "no-git",
            "has_git": False,
        }
    # When nested and no explicit prefix, do not auto-scope — caller must pass
    # --path-prefix for package audits. Full monorepo audit uses empty prefix.
    return {
        "work_root": work_root,
        "git_root": git_root,
        "audit_prefix": prefix,
        "fs_scope_base": "package" if prefix else "full",
        "has_git": True,
    }


def snapshot(
    repo: str,
    run_dir: Path,
    round_n: int,
    side: str,
    per_file_cap: int,
    total_cap: int,
    ignored_cap: int,
    path_prefix: str | None = None,
) -> dict[str, Any]:
    assert side in ("pre", "post")
    scope = resolve_scope(repo, path_prefix)
    audit_prefix = scope["audit_prefix"]
    git_root = scope["git_root"] or scope["work_root"]
    has_git = scope["has_git"]

    round_dir = run_dir / f"round-{round_n}" / side
    round_dir.mkdir(parents=True, exist_ok=True)
    bytes_dir = round_dir / "bytes"
    bytes_dir.mkdir(exist_ok=True)

    if not has_git:
        # Graceful degrade: no fake paths; document scope.
        manifest = {
            "head": None,
            "side": side,
            "round": round_n,
            "entries": [],
            "dirty_paths": [],
            "ignored": {"paths": [], "fs_scope": "no-git", "count": 0, "truncated": False},
            "fs_scope": "no-git",
            "audit_prefix": audit_prefix,
            "git_root": None,
            "work_root": scope["work_root"],
        }
        (round_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        return manifest

    head = head_sha(git_root)
    porcelain = parse_porcelain(git_root, audit_prefix)
    dirty_paths = {e["path"] for e in porcelain}

    entries: list[dict[str, Any]] = []
    budget = 0
    for e in porcelain:
        path = e["path"]
        abs_p = Path(git_root) / path
        exists = abs_p.exists() or abs_p.is_symlink()
        sz = file_size(abs_p) if exists else 0
        restorable = True
        reason = None
        if exists and sz > per_file_cap:
            restorable = False
            reason = "per-file-cap"
        elif exists and budget + sz > total_cap:
            restorable = False
            reason = "total-cap"
        sha = sha256_file(abs_p) if exists else None
        if restorable and exists:
            budget += sz
            dest = bytes_dir / path
            # hardlink-dedup vs previous round pre if same sha
            prev = run_dir / f"round-{round_n - 1}" / "pre" / "bytes" / path
            if prev.is_file() and sha and sha256_file(prev) == sha:
                hardlink_or_copy(prev, dest)
            else:
                copy_path(abs_p, dest)
        entries.append({
            "path": path,
            "xy": e["xy"],
            "sha256": sha,
            "exists": exists,
            "size": sz,
            "restorable": restorable,
            "restorable_reason": reason,
            "dirty": True,
        })

    # Seed invoke-baseline on first pre of round 1 only (write-once)
    invoke_dir = run_dir / "invoke-baseline"
    if side == "pre" and round_n == 1 and not (invoke_dir / "manifest.json").exists():
        invoke_dir.mkdir(parents=True, exist_ok=True)
        inv_bytes = invoke_dir / "bytes"
        inv_bytes.mkdir(exist_ok=True)
        for e in entries:
            if e["restorable"] and e["exists"]:
                src = bytes_dir / e["path"]
                if src.exists() or src.is_symlink():
                    copy_path(src, inv_bytes / e["path"])
        inv_manifest = {
            "head": head,
            "entries": entries,
            "kind": "invoke-baseline",
            "audit_prefix": audit_prefix,
            "git_root": git_root,
        }
        (invoke_dir / "manifest.json").write_text(json.dumps(inv_manifest, indent=2) + "\n")

    ignored = ignored_inventory(git_root, ignored_cap, total_cap, audit_prefix)
    # Package scope wins over full; truncation upgrades full→git-visible-only
    # but package stays package (intentionally scoped audit).
    if audit_prefix:
        fs_scope = "package"
    else:
        fs_scope = ignored["fs_scope"]  # full or git-visible-only

    manifest = {
        "head": head,
        "side": side,
        "round": round_n,
        "entries": entries,
        "dirty_paths": sorted(dirty_paths),
        "ignored": ignored,
        "fs_scope": fs_scope,
        "audit_prefix": audit_prefix,
        "git_root": git_root,
        "work_root": scope["work_root"],
    }
    (round_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def load_manifest(run_dir: Path, round_n: int, side: str) -> dict[str, Any]:
    p = run_dir / f"round-{round_n}" / side / "manifest.json"
    return json.loads(p.read_text())


def diff(run_dir: Path, round_n: int) -> dict[str, Any]:
    pre = load_manifest(run_dir, round_n, "pre")
    post = load_manifest(run_dir, round_n, "post")
    pre_by = {e["path"]: e for e in pre["entries"]}
    post_by = {e["path"]: e for e in post["entries"]}

    # Also consider paths that exist on disk only in one side via existence flags
    all_paths = set(pre_by) | set(post_by)

    delta: list[dict[str, Any]] = []
    for path in sorted(all_paths):
        pe = pre_by.get(path)
        qe = post_by.get(path)

        if pe and not qe:
            # was dirty at pre, gone from post porcelain — could be cleaned or deleted
            change = "deleted"
            delta.append({
                "path": path,
                "change": change,
                "pre_xy": pe["xy"],
                "post_xy": None,
                "pre_sha256": pe.get("sha256"),
                "post_sha256": None,
                "dirty_at_pre": True,
                "restorable": pe.get("restorable", False),
            })
            continue

        if qe and not pe:
            # Appeared in post porcelain only — was clean (or absent) at pre.
            xy = qe["xy"]
            x, y = (xy + "  ")[:2]
            if x == "?" and y == "?":
                # untracked new file
                change = "added"
                kind = "new"
            elif x == "D" or y == "D":
                # tracked file deleted (was clean at pre)
                change = "deleted"
                kind = "tracked-clean-at-pre"
            elif x == "A" or y == "A":
                # newly staged path
                change = "added"
                kind = "new-staged"
            else:
                # tracked modify (e.g. " M", "M ", "MM") of a file clean at pre
                change = "content_changed"
                kind = "tracked-clean-at-pre"
            delta.append({
                "path": path,
                "change": change,
                "kind": kind,
                "pre_xy": None,
                "post_xy": xy,
                "pre_sha256": None,
                "post_sha256": qe.get("sha256"),
                "dirty_at_pre": False,
                "restorable": qe.get("restorable", True),
            })
            continue

        # both present
        assert pe and qe
        if pe.get("exists", True) and not qe.get("exists", True):
            change = "deleted"
        elif pe.get("sha256") != qe.get("sha256"):
            change = "content_changed"
        else:
            change = "unchanged-baseline"
        delta.append({
            "path": path,
            "change": change,
            "pre_xy": pe["xy"],
            "post_xy": qe["xy"],
            "pre_sha256": pe.get("sha256"),
            "post_sha256": qe.get("sha256"),
            "dirty_at_pre": True,
            "restorable": pe.get("restorable", False) and qe.get("restorable", False),
        })

    # Ignored inventory delta (path + sha only)
    pre_ign = {i["path"]: i.get("sha256") for i in pre.get("ignored", {}).get("paths", [])}
    post_ign = {i["path"]: i.get("sha256") for i in post.get("ignored", {}).get("paths", [])}
    ignored_delta = []
    for p in sorted(set(pre_ign) | set(post_ign)):
        if p not in pre_ign:
            ignored_delta.append({"path": p, "change": "added", "sha256": post_ign[p]})
        elif p not in post_ign:
            ignored_delta.append({"path": p, "change": "deleted", "sha256": pre_ign[p]})
        elif pre_ign[p] != post_ign[p]:
            ignored_delta.append({"path": p, "change": "content_changed", "sha256": post_ign[p]})

    # Scope: package if either side package; else git-visible-only if truncated; else full/no-git
    scopes = {pre.get("fs_scope"), post.get("fs_scope")}
    if "package" in scopes:
        fs_scope = "package"
    elif "no-git" in scopes:
        fs_scope = "no-git"
    elif "git-visible-only" in scopes:
        fs_scope = "git-visible-only"
    else:
        fs_scope = "full"

    audit_prefix = pre.get("audit_prefix") or post.get("audit_prefix") or ""
    git_root = pre.get("git_root") or post.get("git_root")

    result = {
        "round": round_n,
        "head_pre": pre.get("head"),
        "head_post": post.get("head"),
        "delta": delta,
        "ignored_delta": ignored_delta,
        "fs_scope": fs_scope,
        "audit_prefix": audit_prefix,
        "git_root": git_root,
    }
    out_path = run_dir / f"round-{round_n}" / "delta.json"
    out_path.write_text(json.dumps(result, indent=2) + "\n")
    return result


def restore(
    repo: str,
    run_dir: Path,
    round_n: int,
    fix_paths: list[str] | None = None,
    path_prefix: str | None = None,
    restore_policy: str = "preserve-shared",
) -> dict[str, Any]:
    """Reconcile suite side effects according to the workspace ownership policy.

    fix_paths: excluded from restore set (should already be empty if restore-first).
    Paths in manifests are git-root-relative; checkout and abs joins use git_root.

    preserve-shared is the safe default for a caller-owned working tree. Every
    post-round change is preserved because a long-running suite cannot
    distinguish its own write from concurrent operator/agent work that arrived
    after the pre snapshot.

    revert-disposable is valid only for a harness-owned disposable worktree.
    There, clean-at-pre tracked paths and absent-at-pre additions are reverted.
    Dirty-at-pre paths are still preserved because their post state may combine
    pre-existing work with suite output.
    """
    if restore_policy not in ("preserve-shared", "revert-disposable"):
        raise ValueError(f"unsupported restore policy: {restore_policy}")

    fix_paths = set(fix_paths or [])
    pre = load_manifest(run_dir, round_n, "pre")
    d = diff(run_dir, round_n)
    actions = []

    scope = resolve_scope(repo, path_prefix if path_prefix is not None else pre.get("audit_prefix"))
    git_root = pre.get("git_root") or scope["git_root"] or scope["work_root"]

    for item in d["delta"]:
        path = item["path"]
        change = item["change"]
        dirty_at_pre = item.get("dirty_at_pre", False)

        if change == "unchanged-baseline":
            continue

        if restore_policy == "preserve-shared":
            abs_p = Path(git_root) / path
            post_exists = abs_p.exists() or abs_p.is_symlink()
            actions.append({
                "path": path,
                "action": "preserve-shared-post-state",
                "change": change,
                "reason": "shared working tree; suite output cannot be separated from concurrent WIP",
                "post_exists": post_exists,
                "post_sha256": sha256_file(abs_p) if post_exists else None,
                "manual_reconciliation_required": True,
            })
            continue

        if dirty_at_pre and change in ("content_changed", "deleted"):
            abs_p = Path(git_root) / path
            post_exists = abs_p.exists() or abs_p.is_symlink()
            actions.append({
                "path": path,
                "action": "preserve-dirty-pre-post-state",
                "change": change,
                "reason": "dirty-at-round-pre; auto-restore disabled to avoid overwriting concurrent WIP",
                "post_exists": post_exists,
                "post_sha256": sha256_file(abs_p) if post_exists else None,
                "manual_reconciliation_required": True,
            })
            continue

        if path in fix_paths:
            actions.append({"path": path, "action": "skip-fix-path"})
            continue

        if change == "added":
            # Absent at pre and added by the suite — safe to delete.
            abs_p = Path(git_root) / path
            if abs_p.exists() or abs_p.is_symlink():
                if abs_p.is_dir() and not abs_p.is_symlink():
                    shutil.rmtree(abs_p)
                else:
                    abs_p.unlink()
                actions.append({"path": path, "action": "delete-added"})
            continue

        if change in ("content_changed", "deleted"):
            # Disposable worktree only: restore the worktree bytes from the
            # commit captured at pre, not a possibly advanced current HEAD.
            # `git restore --worktree` deliberately leaves the index untouched.
            pre_head = pre.get("head")
            if not pre_head:
                actions.append({
                    "path": path,
                    "action": "restore-error",
                    "reason": "missing-pre-head",
                })
                continue
            r = subprocess.run(
                ["git", "-C", git_root, "restore", "--source", pre_head, "--worktree", "--", path],
                capture_output=True,
                text=True,
            )
            actions.append({
                "path": path,
                "action": "restore-worktree-pre-head",
                "source_head": pre_head,
                "ok": r.returncode == 0,
                "stderr": r.stderr.strip() if r.returncode else None,
            })

    preserved = [a for a in actions if a.get("manual_reconciliation_required")]
    preserved_dirty_pre = [
        a for a in preserved if a.get("action") == "preserve-dirty-pre-post-state"
    ]
    result = {
        "round": round_n,
        "actions": actions,
        "git_root": git_root,
        "restore_policy": restore_policy,
        "preserved_post_state": preserved,
        "preserved_post_state_count": len(preserved),
        "preserved_dirty_pre": preserved_dirty_pre,
        "preserved_dirty_pre_count": len(preserved_dirty_pre),
        "manual_reconciliation_required": bool(preserved),
    }
    out = run_dir / f"round-{round_n}" / "restore.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="test-harness porcelain delta")
    ap.add_argument("--repo", required=True, help="WORK_ROOT or any path inside the git work tree")
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--mode", choices=["snapshot", "diff", "restore"], required=True)
    ap.add_argument("--side", choices=["pre", "post"], default="pre")
    ap.add_argument("--fix-paths", default="", help="comma-separated paths to exclude from restore")
    ap.add_argument(
        "--restore-policy",
        choices=["preserve-shared", "revert-disposable"],
        default="preserve-shared",
        help="preserve all shared-tree post state, or revert only in a harness-owned disposable worktree",
    )
    ap.add_argument(
        "--path-prefix",
        default="",
        help="posix relative path from git root to package (AUDIT_PREFIX); empty = full repo",
    )
    ap.add_argument("--per-file-cap", type=int, default=DEFAULT_PER_FILE_CAP)
    ap.add_argument("--total-cap", type=int, default=DEFAULT_TOTAL_CAP)
    ap.add_argument("--ignored-cap", type=int, default=DEFAULT_IGNORED_PATH_CAP)
    args = ap.parse_args()

    repo = str(Path(args.repo).resolve())
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    path_prefix = args.path_prefix or ""

    if args.mode == "snapshot":
        m = snapshot(
            repo, run_dir, args.round, args.side,
            args.per_file_cap, args.total_cap, args.ignored_cap,
            path_prefix=path_prefix,
        )
        print(json.dumps({
            "ok": True,
            "side": args.side,
            "round": args.round,
            "dirty": len(m["entries"]),
            "fs_scope": m["fs_scope"],
            "audit_prefix": m.get("audit_prefix") or "",
            "git_root": m.get("git_root"),
        }))
        return 0
    if args.mode == "diff":
        d = diff(run_dir, args.round)
        print(json.dumps({
            "ok": True,
            "changes": len(d["delta"]),
            "ignored_changes": len(d["ignored_delta"]),
            "fs_scope": d["fs_scope"],
            "audit_prefix": d.get("audit_prefix") or "",
        }))
        return 0
    if args.mode == "restore":
        fp = [p for p in args.fix_paths.split(",") if p]
        r = restore(
            repo,
            run_dir,
            args.round,
            fp,
            path_prefix=path_prefix or None,
            restore_policy=args.restore_policy,
        )
        print(json.dumps({
            "ok": True,
            "actions": len(r["actions"]),
            "git_root": r.get("git_root"),
            "restore_policy": r.get("restore_policy"),
            "manual_reconciliation_required": r.get("manual_reconciliation_required"),
        }))
        return 0
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)
