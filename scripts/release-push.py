#!/usr/bin/env python3
"""Check a frozen, clean release candidate, push it without force, and publish release assets.

Qualification commands are operator-selected argv arrays, not shell programs.
This is a publication guard, not a replacement for reviews or server-side rules.
Concurrent pushes: qualify the frozen release commit with `--group quick --changed-from <base>` first,
then pass fast invariant checks (such as `check-release-boundary.py` and `--group smoke`) here to minimize push-window races.

When the pushed range includes a `Skill-Craft-Release:` commit for `skill-craft@<version>` and the target
is GitHub (or `--github-release require` is specified), builds the deterministic Antigravity `.zip`
archive, verifies its sha256 against `.antigravity-plugin/marketplace.json` before pushing, and creates
or updates the `v<version>` GitHub Release with `skill-craft-<version>.zip` after push succeeds.
With `--refresh-hosts`, invokes `scripts/release-refresh.py` after publication.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

PLUGIN_NAME = "skill-craft"
RELEASE_VERSION_RE = re.compile(r"\bskill-craft@([0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)\b")
GITHUB_REMOTE_RE = re.compile(
    r"^(?:https://github\.com/|ssh://git@github\.com/|git@github\.com:)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)
GITHUB_REPO_ARG_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ReleaseError(Exception):
    pass


def run(argv, *, cwd, timeout=120, env=None):
    result = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise ReleaseError(f"command failed ({result.returncode}): {argv[0]}\n{detail}")
    return result.stdout.strip()


def git(repo, *args):
    return run(["git", *args], cwd=repo)


def local_identity(repo, head, tree):
    if git(repo, "rev-parse", "HEAD") != head:
        raise ReleaseError("candidate HEAD does not match --expected-head")
    if git(repo, "rev-parse", "HEAD^{tree}") != tree:
        raise ReleaseError("candidate tree does not match --expected-tree")
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ReleaseError("candidate checkout must be clean, including untracked files")


def remote_identity(repo, remote, branch, expected_base):
    urls = git(repo, "remote", "get-url", "--push", "--all", remote).splitlines()
    if len(urls) != 1:
        raise ReleaseError("release remote must have exactly one push URL")
    url = urls[0]
    refs = git(repo, "ls-remote", "--exit-code", url, f"refs/heads/{branch}").splitlines()
    if refs != [f"{expected_base}\trefs/heads/{branch}"]:
        raise ReleaseError("remote branch moved or differs from --expected-base")
    return url


def resolve_gh_bin() -> str | None:
    override = os.environ.get("GH_BIN", "").strip()
    if override:
        return override if (os.path.isfile(override) and os.access(override, os.X_OK)) else shutil.which(override)
    return shutil.which("gh")


def infer_github_repo(remote_url: str, override: str | None) -> str | None:
    if override is not None:
        cleaned = override.strip()
        if not GITHUB_REPO_ARG_RE.fullmatch(cleaned):
            raise ReleaseError(f"--github-repo must be owner/repo, got {override!r}")
        return cleaned
    match = GITHUB_REMOTE_RE.fullmatch(remote_url.strip())
    return match.group(1) if match else None


def find_release_in_range(repo: Path, base: str, head: str) -> dict | None:
    raw = git(
        repo,
        "log",
        "--no-merges",
        "--format=%H%x1f%s%x1f%(trailers:key=Skill-Craft-Release,valueonly,unfold)%x1e",
        f"{base}..{head}",
    )
    for record in raw.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split("\x1f", 2)
        if len(parts) != 3:
            continue
        commit, subject, trailer_val = parts
        match = RELEASE_VERSION_RE.search(trailer_val)
        if match:
            body = git(repo, "log", "-1", "--format=%B", commit).strip()
            return {
                "commit": commit,
                "subject": subject.strip(),
                "trailer": trailer_val.strip(),
                "version": match.group(1),
                "notes": body,
            }
    return None


def prepare_github_release(repo: Path, release_info: dict, gh_repo: str, tmp_dir: Path) -> dict:
    """Validate marketplace metadata and build deterministic Antigravity .zip before pushing."""
    gh_bin = resolve_gh_bin()
    if not gh_bin:
        raise ReleaseError("gh CLI binary not found on PATH; cannot publish GitHub Release")

    version = release_info["version"]
    bundle_path = repo / "catalog" / "skill-craft-plugin.json"
    if not bundle_path.is_file():
        raise ReleaseError(f"missing {bundle_path}")
    try:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReleaseError(f"unreadable {bundle_path}: {exc}") from exc
    if bundle.get("version") != version:
        raise ReleaseError(
            f"catalog/skill-craft-plugin.json version {bundle.get('version')!r} != release commit version {version!r}"
        )

    mp_path = repo / ".antigravity-plugin" / "marketplace.json"
    if not mp_path.is_file():
        raise ReleaseError(f"missing {mp_path} in release candidate")
    try:
        mp = json.loads(mp_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReleaseError(f"unreadable {mp_path}: {exc}") from exc
    plugins = mp.get("plugins") if isinstance(mp, dict) else None
    matches = [p for p in plugins if isinstance(p, dict) and p.get("name") == PLUGIN_NAME] if isinstance(plugins, list) else []
    if len(matches) != 1:
        raise ReleaseError(f".antigravity-plugin/marketplace.json must list 1 {PLUGIN_NAME} entry")
    entry = matches[0]
    if entry.get("version") != version:
        raise ReleaseError(
            f".antigravity-plugin/marketplace.json version {entry.get('version')!r} != release version {version!r}"
        )
    source = entry.get("source")
    if not isinstance(source, dict):
        raise ReleaseError(".antigravity-plugin/marketplace.json entry missing source object")
    asset_name = f"{PLUGIN_NAME}-{version}.zip"
    expected_url = f"https://github.com/{gh_repo}/releases/download/v{version}/{asset_name}"
    if source.get("url") != expected_url:
        raise ReleaseError(
            f".antigravity-plugin/marketplace.json source.url {source.get('url')!r} != {expected_url!r}"
        )
    expected_sha = source.get("sha256")
    if not isinstance(expected_sha, str) or not SHA256_RE.fullmatch(expected_sha):
        raise ReleaseError(".antigravity-plugin/marketplace.json source.sha256 must be a 64-char hex digest")

    zip_helper = repo / "scripts" / "antigravity-zip.py"
    if not zip_helper.is_file():
        raise ReleaseError(f"missing {zip_helper}")
    pkg_dir = repo / "plugins" / PLUGIN_NAME
    if not pkg_dir.is_dir():
        raise ReleaseError(f"missing {pkg_dir}")

    zip_path = tmp_dir / asset_name
    built = run(
        [sys.executable, "-B", str(zip_helper), "--source", str(pkg_dir), "--output", str(zip_path), "--json"],
        cwd=repo,
    )
    meta = json.loads(built)
    if meta.get("sha256") != expected_sha:
        raise ReleaseError(
            f"deterministic zip sha256 {meta.get('sha256')!r} != .antigravity-plugin/marketplace.json {expected_sha!r}"
        )

    return {
        "gh_bin": gh_bin,
        "gh_repo": gh_repo,
        "tag": f"v{version}",
        "asset": asset_name,
        "zip_path": zip_path,
        "sha256": meta["sha256"],
        "bytes": meta["bytes"],
        "files": meta["files"],
        "url": expected_url,
        "title": f"{PLUGIN_NAME} v{version}",
        "notes": release_info["notes"],
    }


def upload_github_release(plan: dict, *, target_commit: str, timeout: float) -> dict:
    """Create the tag/release if absent or clobber-upload the verified deterministic .zip asset."""
    gh_bin = plan["gh_bin"]
    gh_repo = plan["gh_repo"]
    tag = plan["tag"]
    zip_path = str(plan["zip_path"])

    probe = subprocess.run(
        [gh_bin, "release", "view", tag, "--repo", gh_repo, "--json", "tagName"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if probe.returncode != 0:
        run(
            [
                gh_bin,
                "release",
                "create",
                tag,
                zip_path,
                "--repo",
                gh_repo,
                "--target",
                target_commit,
                "--title",
                plan["title"],
                "--notes",
                plan["notes"],
            ],
            cwd=plan["zip_path"].parent,
            timeout=timeout,
        )
        action = "created"
    else:
        run(
            [gh_bin, "release", "upload", tag, zip_path, "--repo", gh_repo, "--clobber"],
            cwd=plan["zip_path"].parent,
            timeout=timeout,
        )
        action = "updated"

    return {
        "action": action,
        "repo": gh_repo,
        "tag": tag,
        "asset": plan["asset"],
        "sha256": plan["sha256"],
        "bytes": plan["bytes"],
        "files": plan["files"],
        "url": plan["url"],
    }


def run_host_refresh(repo: Path, args: argparse.Namespace) -> dict:
    refresh_script = repo / "scripts" / "release-refresh.py"
    refresh_repo = Path(args.refresh_repo).resolve(strict=True) if args.refresh_repo else repo
    cmd = [
        sys.executable,
        "-B",
        str(refresh_script),
        "--repo",
        str(refresh_repo),
        "--timeout",
        str(args.refresh_timeout),
    ]
    for host in args.refresh_host:
        cmd.extend(["--host", host])
    if args.allow_live:
        cmd.append("--allow-live")

    done = subprocess.run(
        cmd,
        cwd=refresh_repo,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=max(args.refresh_timeout * 5, 60.0),
        check=False,
    )
    raw = (done.stdout or done.stderr).strip()
    try:
        parsed = json.loads(raw) if raw else None
    except ValueError:
        parsed = None
    if done.returncode != 0:
        detail = raw or f"exit {done.returncode}"
        raise ReleaseError(f"host refresh failed after push:\n{detail}")
    return parsed if isinstance(parsed, dict) else {"status": "refreshed", "raw": raw}


def publish(args):
    # Git context overrides could make the explicit repository identity misleading.
    forbidden = {"GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
                 "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                 "GIT_NAMESPACE", "GIT_SHALLOW_FILE", "GIT_REPLACE_REF_BASE"}
    overrides = sorted(key for key in os.environ if key in forbidden or key.startswith("GIT_CONFIG"))
    if overrides:
        raise ReleaseError("remove Git context overrides: " + ", ".join(overrides))
    repo = Path(args.repo).resolve(strict=True)
    if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise ReleaseError("--repo must name the repository worktree root")
    for name in ("expected_head", "expected_tree", "expected_base"):
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", getattr(args, name)):
            raise ReleaseError(f"--{name.replace('_', '-')} must be a full object ID")
    git(repo, "check-ref-format", f"refs/heads/{args.branch}")
    checks = []
    for raw in args.check:
        check = json.loads(raw)
        if not isinstance(check, list) or not check or any(not isinstance(v, str) or not v for v in check):
            raise ReleaseError("each --check must be a nonempty JSON argv array of nonempty strings")
        checks.append(check)

    if args.refresh_hosts and not (repo / "scripts" / "release-refresh.py").is_file():
        raise ReleaseError(f"missing {repo / 'scripts' / 'release-refresh.py'} for --refresh-hosts")

    local_identity(repo, args.expected_head, args.expected_tree)
    url = remote_identity(repo, args.remote, args.branch, args.expected_base)
    git(repo, "merge-base", "--is-ancestor", args.expected_base, args.expected_head)

    gh_repo = infer_github_repo(url, args.github_repo)
    release_info = find_release_in_range(repo, args.expected_base, args.expected_head)
    should_publish_gh = False
    if args.github_release == "require":
        if not release_info:
            raise ReleaseError("no Skill-Craft-Release commit in range for --github-release require")
        if not gh_repo:
            raise ReleaseError("could not infer GitHub owner/repo from push URL; pass --github-repo")
        should_publish_gh = True
    elif args.github_release == "auto":
        should_publish_gh = bool(release_info and gh_repo)

    tmp_ctx = tempfile.TemporaryDirectory(prefix="release-push-zip-") if should_publish_gh else None
    try:
        gh_plan = (
            prepare_github_release(repo, release_info, gh_repo, Path(tmp_ctx.name))
            if should_publish_gh
            else None
        )

        for number, check in enumerate(checks, 1):
            print(f"release check {number}/{len(checks)}: {json.dumps(check)}", file=sys.stderr, flush=True)
            result = subprocess.run(check, cwd=repo, timeout=args.check_timeout, stdout=sys.stderr)
            if result.returncode:
                raise ReleaseError(f"release check {number} failed ({result.returncode}); no push attempted")
            local_identity(repo, args.expected_head, args.expected_tree)
        if remote_identity(repo, args.remote, args.branch, args.expected_base) != url:
            raise ReleaseError("release push URL changed during checks")
        local_identity(repo, args.expected_head, args.expected_tree)
        # Push the frozen object, not a movable branch/HEAD; never use '+' or --force.
        # Server rules still apply. A racing divergent update is rejected by Git.
        receipt_line = git(
            repo,
            "-c",
            "push.followTags=false",
            "push",
            "--porcelain",
            url,
            f"{args.expected_head}:refs/heads/{args.branch}",
        )
        out = {
            "status": "pushed",
            "head": args.expected_head,
            "tree": args.expected_tree,
            "previous_remote_head": args.expected_base,
            "branch": args.branch,
            "checks_passed": len(checks),
            "push_receipt": receipt_line,
        }
        if gh_plan is not None:
            out["github_release"] = upload_github_release(
                gh_plan, target_commit=args.expected_head, timeout=args.gh_timeout
            )
        if args.refresh_hosts:
            out["host_refresh"] = run_host_refresh(repo, args)
        return out
    finally:
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-tree", required=True)
    parser.add_argument("--expected-base", required=True)
    parser.add_argument("--check", action="append", required=True, help="JSON argv array; repeat for multiple checks")
    parser.add_argument("--check-timeout", type=float, default=1800)
    parser.add_argument(
        "--github-release",
        choices=("auto", "require", "never"),
        default="auto",
        help="GitHub Release publication mode for Skill-Craft-Release commits (default: auto)",
    )
    parser.add_argument("--github-repo", default=None, help="explicit GitHub owner/repo (default: inferred from remote)")
    parser.add_argument("--gh-timeout", type=float, default=300, help="per-command timeout in seconds for gh (default: 300)")
    parser.add_argument(
        "--refresh-hosts",
        action="store_true",
        help="run scripts/release-refresh.py after push and GitHub Release upload",
    )
    parser.add_argument("--refresh-repo", default=None, help="checkout path passed to scripts/release-refresh.py")
    parser.add_argument("--refresh-host", action="append", default=[], help="forwarded --host filter for release-refresh.py")
    parser.add_argument("--allow-live", action="store_true", help="forward --allow-live to release-refresh.py")
    parser.add_argument("--refresh-timeout", type=float, default=300, help="per-command timeout for release-refresh.py")
    args = parser.parse_args()
    try:
        if args.check_timeout <= 0:
            raise ReleaseError("--check-timeout must be positive")
        if args.gh_timeout <= 0 or args.refresh_timeout <= 0:
            raise ReleaseError("--gh-timeout and --refresh-timeout must be positive")
        print(json.dumps(publish(args), sort_keys=True))
        return 0
    except (ReleaseError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
