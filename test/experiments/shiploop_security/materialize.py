#!/usr/bin/env python3
"""Build a fresh private V6 harness from an exact, retained V5 source snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

from controls import add_controls

HERE = Path(__file__).resolve().parent
V5_REGISTRATION = "9c11b3fdbb2ffd5e975600697183f4f1f9f7e7473c29e05bcfe283f2faa3c912"
V5_PATHS = "4b3a1d9b1c67ad2c83ef46ef0f8572c8185e0d8c36fa394b45c1033afd2e9102"
V5_SOURCES = "ddac48d86bfc01954d9fb985cf432f79533832d8aa561c8c45e8ba98518c6ba0"
CASES = (
    "already-secure", "authorization", "cosmetic", "integrated-secure",
    "integration-only", "later-added-work", "secret-exposure", "tenant-isolation",
)
FILES = (
    "analysis/grade.py", "analysis/decision.py",
    "coordination/dispatch.py", "coordination/fingerprint.py",
    "operator/runner.py", "corpus/calibration.py", "preflight/make_schedule.py",
    "corpus/outer-oracle/export-coverage.cjs", "corpus/outer-oracle/failure-reporter.cjs",
)


def _safe(root, path, directory=False):
    """Refuse links in any selected component and anything but expected types."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError("source root is missing or linked")
    current = root
    for part in Path(path).parts[:-1]:
        current /= part
        if not stat.S_ISDIR(current.lstat().st_mode):
            raise ValueError(f"source parent is not a regular directory: {path}")
    source = root / path
    mode = source.lstat().st_mode
    if not (stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)):
        raise ValueError(f"unexpected source type: {path}")
    return source


def _files(root, directory):
    folder = _safe(root, directory, directory=True)
    for parent, subfolders, files in os.walk(folder, followlinks=False):
        for name in subfolders:
            _safe(root, (Path(parent) / name).relative_to(root), directory=True)
        for name in files:
            yield (Path(parent) / name).relative_to(root).as_posix()


def source_payload(root):
    """Select only frozen operator/analysis sources and synthetic case files."""
    registration = _safe(root, "registration.json").read_bytes()
    if hashlib.sha256(registration).hexdigest() != V5_REGISTRATION:
        raise ValueError("source registration is not the frozen V5 retry")
    paths = list(FILES)
    for case in CASES:
        prefix = f"corpus/{case}"
        paths.append(prefix + "/case.json")
        paths.extend(prefix + "/oracle/" + name for name in ("calibration.json", "oracle.cjs", "probe.cjs"))
        for tree in ("repo", "references", *(("product",) if case.startswith("integrat") else ())):
            paths.extend(_files(root, f"{prefix}/{tree}"))
    paths = sorted(paths)
    if hashlib.sha256(json.dumps(paths, separators=(",", ":")).encode()).hexdigest() != V5_PATHS:
        raise ValueError("frozen V5 source inventory differs")
    payload = []
    for relative in paths:
        path = _safe(root, relative)
        payload.append((relative, stat.S_IMODE(path.stat().st_mode), path.read_bytes()))
    return payload


def source_digest(payload):
    rows = [(name, mode, hashlib.sha256(data).hexdigest()) for name, mode, data in payload]
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()


def materialize(source, output):
    source, output = Path(source), Path(output)
    if source.is_symlink():
        raise ValueError("source root cannot be a symlink")
    source = source.resolve(strict=True)
    if os.path.lexists(output):
        raise ValueError("output already exists")
    output = output.resolve()
    if output == source or source in output.parents or output in source.parents:
        raise ValueError("output must be separate from frozen source")
    payload = source_payload(source)
    if source_digest(payload) != V5_SOURCES:
        raise ValueError("frozen V5 source path/content/mode identity mismatch")

    output.mkdir(mode=0o700)  # Requires an existing, caller-owned parent.
    try:
        for relative, mode, data in payload:
            path = output / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            path.chmod(mode)

        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(GIT_CEILING_DIRECTORIES=str(output.parent),
                   GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        patch = HERE / "v6.patch"
        for options in (["--check"], []):
            subprocess.run(["git", "-C", str(output), "apply", "--no-index",
                            "--whitespace=nowarn", "--unidiff-zero", *options, str(patch)], env=env, check=True)
        for name in ("scope_evidence.py", "logger_failure.cjs"):
            shutil.copyfile(HERE / name, output / name)
        add_controls(output)
        receipt = {"schema": "shiploop-security-materialization/v1", "corpus_version": 6,
                   "source_registration_sha256": V5_REGISTRATION, "source_sha256": V5_SOURCES,
                   "source_files": len(payload),
                   "overlay_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
                   "support_sha256": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                                      for name in ("scope_evidence.py", "logger_failure.cjs", "controls.py")}}
        (output / "materialization.json").write_text(json.dumps(receipt, indent=2) + "\n")
    except BaseException:
        shutil.rmtree(output)
        raise
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--frozen", type=Path, required=True, help="frozen V5 retry evidence directory")
    p.add_argument("--output", type=Path, required=True, help="new, separate private directory")
    args = p.parse_args()
    try:
        print(json.dumps(materialize(args.frozen, args.output), indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        p.exit(1, f"Refusing materialization: {error}\n")


if __name__ == "__main__":
    main()
