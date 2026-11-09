"""Owner-only report trees and allowlisted evidence projections for V7."""
from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile


COUNT_KEYS = ("tests", "pass", "fail", "cancelled", "skipped", "todo")
COUNT_LINE = re.compile(r"^(#|ℹ)[ \t]+(" + "|".join(COUNT_KEYS) + r")(?=$|[^\w])")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2) + "\n").encode()


def private_file(path, raw):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as file:
        os.fchmod(file.fileno(), 0o600)
        file.write(raw)


def fresh_output(path, *, inputs=()):
    path = Path(path).absolute()
    parent = path.parent
    if (path != path.resolve() or os.path.lexists(path) or not parent.is_dir()
            or parent.stat().st_uid != os.getuid()):
        raise ValueError("use a fresh path in an existing owned directory")
    for source in map(Path, inputs):
        source = source.resolve(strict=True)
        if path == source or source in path.parents or path in source.parents:
            raise ValueError("output must be separate from protected inputs")
    return path


def private_dir(path):
    Path(path).mkdir(mode=0o700)
    Path(path).chmod(0o700)
    return Path(path)


def _rename_new(source, target):
    """Same-filesystem atomic publication that refuses even an empty target."""
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        result = libc.renamex_np(os.fsencode(source), os.fsencode(target), 0x00000004)
    elif sys.platform.startswith("linux"):
        result = libc.renameat2(-100, os.fsencode(source), -100, os.fsencode(target), 1)
    else:
        raise OSError(errno.ENOTSUP, "exclusive directory rename unavailable")
    if result:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), target)


def _paths(files):
    directories = {"."}
    for name, raw in files.items():
        if not isinstance(name, str) or not isinstance(raw, bytes):
            raise ValueError("report expects relative file names and bytes")
        rel = PurePosixPath(name)
        if (not rel.parts or rel.is_absolute() or rel.as_posix() != name
                or ".." in rel.parts or "\\" in name or "\x00" in name):
            raise ValueError("invalid report path")
        directories.update(p.as_posix() for p in rel.parents)
    if directories.intersection(files):
        raise ValueError("report file conflicts with a directory")
    return directories


def write_tree(output, files, *, inputs=()):
    """Verify staged bytes, path inventory and modes, then publish once.

    Failed stages remain private and separate from the named completed output.
    Only caller-owned new output is created. Source evidence is never chmodded.
    """
    output = fresh_output(output, inputs=inputs)
    directories = _paths(files)
    stage = Path(tempfile.mkdtemp(prefix=".report-stage-", dir=output.parent))
    stage.chmod(0o700)
    for rel in sorted(directories - {"."}, key=lambda name: (name.count("/"), name)):
        private_dir(stage / rel)
    for rel, raw in sorted(files.items()):
        private_file(stage / rel, raw)
    observed_dirs, observed_files = {"."}, {}
    for path in sorted(stage.rglob("*")):
        rel = path.relative_to(stage).as_posix()
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode) and stat.S_IMODE(mode) == 0o700:
            observed_dirs.add(rel)
        elif stat.S_ISREG(mode) and stat.S_IMODE(mode) == 0o600:
            observed_files[rel] = sha(path.read_bytes())
        else:
            raise ValueError("unexpected staged report entry or mode")
    if (observed_dirs != directories or stat.S_IMODE(stage.stat().st_mode) != 0o700
            or observed_files != {name: sha(raw) for name, raw in files.items()}):
        raise ValueError("staged report differs from requested inventory")
    _rename_new(stage, output)
    return observed_files


def public_counts(stdout, exit_code, timeout):
    """Read structural TAP/spec totals; do not export raw stdout or test titles."""
    values = {k: [] for k in COUNT_KEYS}
    formats = set()
    for line in stdout.splitlines():
        match = COUNT_LINE.match(line)
        if not match:
            continue
        marker, key = match.groups()
        formats.add(marker)
        exact = re.fullmatch(re.escape(marker + " " + key) + r" ([0-9]{1,9})", line)
        values[key].append(int(exact[1]) if exact else None)
    reporter = {"#": "tap", "ℹ": "node_spec"}.get(next(iter(formats))) if len(formats) == 1 else None
    counts = {k: v[0] if len(v) == 1 else None for k, v in values.items()}
    tests = counts["tests"]
    buckets = [counts[k] for k in COUNT_KEYS[1:]]
    observed_sum = sum(n for n in buckets if n is not None)
    consistent = (
        (tests is None or (observed_sum <= tests and (None in buckets or observed_sum == tests)))
        and (exit_code != 0 or not any(counts[k] for k in ("fail", "cancelled")))
    )
    if not reporter or not consistent or timeout:
        counts = dict.fromkeys(COUNT_KEYS)
    status = ("timed_out" if timeout else "absent" if not formats else
              "ambiguous_reporter" if not reporter else "inconsistent" if not consistent else
              "partial_or_unknown" if None in counts.values() else "complete")
    return {"reporter": reporter, "status": status, "counts": counts}


def scope_context(scope):
    """Keep native scope facts without exporting candidate-controlled path names."""
    if scope["baseline"] != "native_start":
        raise ValueError("native scope baseline missing")
    result = {"baseline": "native_start", "mode_entry_type": "regular_file", "pass": scope["pass"]}
    for key in ("changed_paths", "excluded_changes", "outside_allowed_subtrees",
                "new_executable_files", "link_paths", "native_skipped_paths"):
        result[key + "_count"] = len(scope[key])
    for key in ("regular_file_mode_changes", "fixture_to_native_mode_differences"):
        result[key] = sorted([dict(pair) for pair in scope[key].values()],
                             key=lambda pair: tuple(pair[k] for k in sorted(pair)))
    return result
