"""The delivery snapshot (SPEC "The promotion contract", build step 4; R6 of the final verdict): what the run delivered,
recorded before the checks run and again after them, so grading reads records instead of a work tree that may be gone.

* ``fingerprint`` is the delivered ``work/`` as git sees it: HEAD, its tree and ``git status --porcelain`` (untracked
  files included, ignored ones not). ``{observed: False, reason}`` when it can't be read.
* ``capture`` takes the fingerprint and archives the tree as ``<output>/delivery/work.bundle`` (``git bundle --all``),
  the delivery a later reader can rebuild with ``restore``.
* ``changed`` says how two fingerprints differ; the scorecard's correctness reads it.

Reads ``work/`` only; ``capture`` writes under ``<output>/delivery`` and ``restore`` into the folder it is given.
"""

from __future__ import annotations

from pathlib import Path
import subprocess

FOLDER = "delivery"
BUNDLE = f"{FOLDER}/work.bundle"


def _git(work: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(work), *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)


def fingerprint(work: Path) -> dict:
    """``{observed: True, head, tree, status}`` for a git work tree (head and tree null before its first commit), else
    ``{observed: False, reason}``."""
    work = Path(work)
    if not (work / ".git").exists():
        return {"observed": False, "reason": "no work/ repository (torn down, or nothing was delivered)"}
    status = _git(work, "status", "--porcelain")
    if status.returncode != 0:
        return {"observed": False, "reason": "git status failed: " + (status.stderr.strip().splitlines() or ["no message"])[0][:160]}
    head = _git(work, "rev-parse", "--verify", "-q", "HEAD")
    tree = _git(work, "rev-parse", "--verify", "-q", "HEAD^{tree}")
    return {"observed": True, "head": head.stdout.strip() or None, "tree": tree.stdout.strip() or None,
            "status": [line for line in status.stdout.splitlines() if line.strip()]}


def capture(work: Path, out: Path) -> dict:
    """The fingerprint before the checks, with the bundle that archives the delivered history (``bundle`` null, with the
    reason, when there is nothing to bundle or git refuses)."""
    found = fingerprint(work)
    if not found.get("observed"):
        return found
    if not found["head"]:
        return {**found, "bundle": None, "bundle_unmeasured": "the work tree has no commit to bundle"}
    path = Path(out) / BUNDLE
    path.parent.mkdir(parents=True, exist_ok=True)
    done = _git(work, "bundle", "create", "-q", str(path), "--all")
    if done.returncode != 0 or not path.is_file():
        return {**found, "bundle": None, "bundle_unmeasured": "git bundle failed: "
                + (done.stderr.strip().splitlines() or ["no message"])[0][:160]}
    return {**found, "bundle": BUNDLE, "bundle_bytes": path.stat().st_size}


def changed(before: dict, after: dict) -> list[str]:
    """How ``after`` differs from ``before`` (empty: the same delivery). Only observed fingerprints are compared."""
    reasons = []
    if before.get("head") != after.get("head"):
        reasons.append(f"HEAD moved from {str(before.get('head'))[:8]} to {str(after.get('head'))[:8]}")
    elif before.get("tree") != after.get("tree"):
        reasons.append("the committed tree changed")
    added = [line for line in after.get("status") or [] if line not in (before.get("status") or [])]
    if added:
        reasons.append("the work tree changed: " + ", ".join(added[:3]))
    return reasons


def restore(out: Path, dest: Path, head: str | None = None) -> Path:
    """Rebuild the delivered tree from ``<out>/delivery/work.bundle`` into ``dest`` (which must not exist), at ``head``
    when given. Raises ``FileNotFoundError`` when the run has no bundle and ``RuntimeError`` when git refuses."""
    bundle = Path(out) / BUNDLE
    if not bundle.is_file():
        raise FileNotFoundError(f"{bundle}: the run archived no delivery")
    done = subprocess.run(["git", "clone", "-q", str(bundle), str(dest)], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if done.returncode != 0:
        raise RuntimeError("git clone of the delivery bundle failed: " + done.stderr.strip()[:200])
    if head:
        checkout = _git(Path(dest), "checkout", "-q", head)
        if checkout.returncode != 0:
            raise RuntimeError(f"the bundle has no commit {head[:8]}: " + checkout.stderr.strip()[:200])
    return Path(dest)
