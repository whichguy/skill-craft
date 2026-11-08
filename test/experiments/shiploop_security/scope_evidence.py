"""Private V6 mode and scope evidence. The native snapshot owns file selection."""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
from pathlib import Path
import stat

REGISTRATION = "shiploop-security-pilot/v2"
OBSERVATION = "shiploop-security-observation/v2"
RECEIPT = "shiploop-security-snapshot/v2"
PREPARED = "prepared-v3"
PHASES = {"start": "initial-product-export", "terminal": "product-export"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                     separators=(",", ":")).encode()).hexdigest()


def inventory(root):
    """Record regular-file mode+content and link targets; do not follow links."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"missing or linked snapshot directory: {root.name}")
    rows = {}
    for path in sorted(root.rglob("*")):
        name = path.relative_to(root).as_posix()
        mode = path.lstat().st_mode
        if stat.S_ISREG(mode):
            rows[name] = {"kind": "file", "mode": stat.S_IMODE(mode),
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        elif stat.S_ISLNK(mode):
            rows[name] = {"kind": "link", "target": os.readlink(path)}
        elif not stat.S_ISDIR(mode):
            raise ValueError("unsupported snapshot entry type")
    return rows


def receipt_path(trial, phase):
    return trial / f"scope-{phase}.json"


def capture(snapshot, worktree, trial, phase, binding):
    """Snapshot once; store a trial-bound receipt and return its content digest."""
    trial, worktree = Path(trial), Path(worktree)
    target = trial / PHASES[phase]
    receipt = receipt_path(trial, phase)
    if os.path.lexists(receipt):
        raise ValueError(f"scope {phase} receipt already exists")
    export = snapshot(worktree, target)
    data = {"schema": RECEIPT, "phase": phase, "binding": binding,
            "export": export, "entries": inventory(target)}
    with receipt.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    return digest(data)


def verify(trial, phase, expected_digest, binding):
    trial = Path(trial)
    path = receipt_path(trial, phase)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or linked scope {phase} receipt")
    data = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("schema") != RECEIPT
            or data.get("phase") != phase or data.get("binding") != binding
            or digest(data) != expected_digest):
        raise ValueError(f"scope {phase} receipt identity mismatch")
    actual = inventory(trial / PHASES[phase])
    if data.get("entries") != actual:
        raise ValueError(f"scope {phase} export content or mode mismatch")
    return data


def binding(trial, worktree, case, arm, seed_action):
    return {"trial": str(Path(trial).resolve()), "worktree": str(Path(worktree).resolve()),
            "case": case, "arm": arm, "seed_action": seed_action}


def _matches(name, patterns):
    return any(fnmatch.fnmatchcase(name, pattern)
               or pattern.endswith("/**") and name == pattern[:-3].rstrip("/")
               for pattern in patterns)


def compare(case, before, after, *, fixture=None, skipped=()):
    """Compare native endpoints. Fixture drift is diagnostic, never the baseline."""
    all_changed = sorted(name for name in before.keys() | after.keys()
                         if before.get(name) != after.get(name))
    exclusions = case.get("scope_exclusions", [])
    excluded = [name for name in all_changed if _matches(name, exclusions)]
    changed = [name for name in all_changed if name not in excluded]
    sources = case.get("allowed_source_subtrees", [])
    docs = case.get("allowed_documentation_paths", [])
    metadata = case.get("allowed_repository_metadata_paths", [])
    outside = [name for name in changed if name not in metadata and not _matches(name, sources + docs)]
    mode_changes = {name: {"start": before[name]["mode"], "terminal": after[name]["mode"]}
                    for name in all_changed if name in before and name in after
                    and before[name]["kind"] == after[name]["kind"] == "file"
                    and before[name]["mode"] != after[name]["mode"]}
    executable = [name for name in all_changed
                  if after.get(name, {}).get("mode", 0) & ~before.get(name, {}).get("mode", 0) & 0o111]
    # The synthetic public seeds contain no links. Even in excluded paths a
    # new link is scope evidence, and no oracle should execute a linked tree.
    links = sorted(name for name, row in after.items() if row["kind"] == "link")
    fixture_modes = {name: {"fixture": fixture[name]["mode"], "native_start": before[name]["mode"]}
                     for name in sorted(fixture.keys() & before.keys()) if fixture[name]["kind"] == before[name]["kind"] == "file"
                     and fixture[name]["mode"] != before[name]["mode"]} if fixture is not None else {}
    return {
        "pass": not (outside or executable or links or skipped or mode_changes),
        "baseline": "native_start" if fixture is not None else "reference_fixture",
        "mode_coverage": "complete POSIX modes for regular files; no directory or symlink modes",
        "fixture_to_native_mode_differences": fixture_modes,
        "allowed_source_subtrees": sources, "allowed_documentation_paths": docs,
        "allowed_repository_metadata_paths": metadata, "excluded_changes": excluded,
        "changed_paths": changed, "outside_allowed_subtrees": outside,
        "new_executable_files": executable, "regular_file_mode_changes": mode_changes,
        "link_paths": links, "native_skipped_paths": list(skipped),
    }
