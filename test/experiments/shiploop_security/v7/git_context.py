"""Private, bounded Git evidence for a drained native worktree (V7 only)."""

from __future__ import annotations

import base64
import binascii
import functools
import hashlib
import io
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import stat
import struct
import subprocess
import tempfile
import time
import zlib


class ContextError(ValueError):
    """Git evidence is incomplete; no subject outcome can be inferred."""


SCHEMA = "shiploop-security-git-context/v1"
SCAN_SCHEMA = "shiploop-security-history-scan/v1"
MAX_OBJECTS = 20_000
MAX_OBJECT_BYTES = 16 << 20
MAX_TOTAL_BYTES = 128 << 20
MAX_PACK_BYTES = 64 << 20
MAX_METADATA_BYTES = 8 << 20
MAX_EXPORT_BYTES = 64 << 20
MAX_ENTRIES = 20_000
MAX_SOURCE_OBJECT_BYTES = 512 << 20  # compressed storage, including unselected source objects
MAX_REFS = 1024
MAX_SECONDS = 90
OID = re.compile(rb"[0-9a-f]{40}")
SHA = re.compile(r"[0-9a-f]{64}")
PATH_LIMIT = 4096
EXCLUSIONS = (".git", ".shiploop-improve", ".shiploop-runs", "**/__pycache__", "**/*.pyc")
COVERAGE = "blobs reachable from captured HEAD or declared direct refs"
MARKER_FORMS = ("literal-bytes", "standard-base64")
_INDEX_MODES = {b"100644", b"100755", b"120000"}
_BEHAVIOR_CONFIG = {"core.filemode": True, "core.ignorecase": False,
                    "core.symlinks": True, "core.precomposeunicode": False}
_INERT_CONFIG = {"core.logallrefupdates", "core.bare", "core.repositoryformatversion",
                 "core.hookspath", "core.fsmonitor", "core.untrackedcache",
                 "core.abbrev", "user.name", "user.email"}
_UNSUPPORTED_METADATA = ("shallow", "info/grafts", "info/attributes", "config.worktree",
                         "MERGE_HEAD", "MERGE_MSG", "rebase-apply", "rebase-merge",
                         "CHERRY_PICK_HEAD", "REVERT_HEAD", "sequencer", "BISECT_START",
                         "index.lock", "HEAD.lock", "packed-refs.lock", "commondir.lock")


def _require(condition, reason):
    if not condition:
        raise ContextError(reason)


def _api(func):
    @functools.wraps(func)
    def checked(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ContextError:
            raise
        except (OSError, ValueError, TypeError, OverflowError, KeyError,
                RecursionError, struct.error, subprocess.SubprocessError):
            # Diagnostics from data-dependent exceptions can contain source
            # locators, paths or bytes. This message is safe to retain.
            raise ContextError("invalid or unavailable Git context evidence") from None
    return checked


def _canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("ascii")


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _binding(value):
    _require(type(value) is dict and len(_canonical(value)) <= 64 * 1024, "invalid binding")
    _require(all(type(k) is str for k in value), "invalid binding")
    for key in ("registration_sha256", "scope_start_sha256", "scope_terminal_sha256"):
        _require(type(value.get(key)) is str and SHA.fullmatch(value[key]), "invalid binding digest")
    for key in ("trial_id", "case_id"):
        _require(type(value.get(key)) is str and bool(value[key]), "invalid trial or case binding")
    canonical = json.loads(_canonical(value))
    _require(canonical == value, "binding must contain canonical JSON values")
    return canonical


def _signature(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read(path, limit):
    initial = path.lstat()
    _require(stat.S_ISREG(initial.st_mode) and initial.st_size <= limit, "invalid or oversized input file")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        _require(_signature(os.fstat(stream.fileno())) == _signature(initial), "input changed while opening")
        value = stream.read(limit + 1)
        _require(len(value) == initial.st_size and _signature(os.fstat(stream.fileno())) ==
                 _signature(initial) == _signature(path.lstat()), "input changed while reading")
    return value


def _exists(path):
    return os.path.lexists(path)


def _dir(path):
    _require(stat.S_ISDIR(path.lstat().st_mode), "expected a real directory")
    return path


def _root(path):
    return _dir(Path(path)).resolve(strict=True)


def _fresh(path, *inputs):
    path = Path(path)
    parent = _root(path.parent)
    _require(path.name not in ("", ".", ".."), "invalid output path")
    output = parent / path.name
    _require(not _exists(output), "output already exists")
    _require(all(output != root and root not in output.parents for root in inputs),
             "output must not be inside an input")
    return output


def _disjoint(a, b):
    _require(a != b and a not in b.parents and b not in a.parents, "overlapping input roots")


def _mkdir(path):
    path.mkdir(mode=0o700)
    path.chmod(0o700)


def _write(path, data, mode=0o600):
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fchmod(stream.fileno(), mode)


def _time(end):
    remaining = end - time.monotonic()
    _require(remaining > 0, "Git context deadline exceeded")
    return remaining


def _git(cwd, end, *argv, meta=None, work=None, objects=None, data=None, limit=MAX_METADATA_BYTES):
    executable = shutil.which("git")
    _require(bool(executable), "Git is unavailable")
    environment = {
        "PATH": os.defpath, "HOME": os.devnull, "XDG_CONFIG_HOME": os.devnull, "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_SYSTEM": os.devnull, "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ATTR_NOSYSTEM": "1", "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_ALLOW_PROTOCOL": "",
        "GIT_ALLOC_LIMIT": str(256 << 20),
        "GIT_CEILING_DIRECTORIES": str(cwd.parent),
    }
    if meta is not None:
        environment["GIT_DIR"] = str(meta)
    if work is not None:
        environment["GIT_WORK_TREE"] = str(work)
    if objects is not None:
        environment["GIT_OBJECT_DIRECTORY"] = str(objects)
    args = [executable, "--no-pager", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
            "-c", "core.untrackedCache=false", "-c", "core.commitGraph=false",
            "-c", "core.multiPackIndex=false", "-c", "gc.auto=0", "-c", "maintenance.auto=false",
            "-c", "protocol.allow=never", "-c", "pack.threads=1", *argv]
    deadline = time.monotonic() + min(25, _time(end))
    with tempfile.TemporaryFile() as feed:
        if data is not None:
            feed.write(data)
            feed.seek(0)
        with subprocess.Popen(args, cwd=cwd, env=environment, stdin=feed,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            try:
                output = bytearray()
                err_size = 0
                with selectors.DefaultSelector() as sel:
                    sel.register(proc.stdout, selectors.EVENT_READ, True)
                    sel.register(proc.stderr, selectors.EVENT_READ, False)
                    while sel.get_map():
                        for key, _ in sel.select(_time(deadline)):
                            block = os.read(key.fd, 65536)
                            if not block:
                                sel.unregister(key.fileobj)
                            elif key.data:
                                output.extend(block)
                                _require(len(output) <= limit, "Git output limit exceeded")
                            else:
                                err_size += len(block)
                                _require(err_size <= 65536, "Git diagnostic output limit exceeded")
                _require(proc.wait(timeout=_time(deadline)) == 0, f"Git {argv[0]} failed")
                return bytes(output)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()


def _rel(raw):
    _require(type(raw) is bytes and 0 < len(raw) <= PATH_LIMIT and
             all(part not in (b"", b".", b"..") and part.lower() != b".git"
                 for part in raw.split(b"/")) and b"\0" not in raw,
             "unsafe Git or export path")
    return os.fsdecode(raw)


def _excluded(path):
    parts = path.split("/")
    return parts[0] in EXCLUSIONS[:3] or "__pycache__" in parts or path.endswith(".pyc")


def _children(path, limit, end):
    rows = []
    with os.scandir(_dir(path)) as entries:
        for item in entries:
            _time(end)
            _require(len(rows) < limit, "filesystem entry limit exceeded")
            rows.append(Path(item.path))
    return sorted(rows)


def _record(path, remaining):
    info = path.lstat()
    mode = info.st_mode
    if stat.S_ISLNK(mode):
        target = os.fsencode(os.readlink(path))
        _require(len(target) <= PATH_LIMIT and _signature(info) == _signature(path.lstat()),
                 "oversized or changing symbolic link")
        return ("link", _b64(target)), len(target)
    _require(stat.S_ISREG(mode), "unsupported export file type")
    raw = _read(path, min(MAX_OBJECT_BYTES, remaining))
    return ("file", stat.S_IMODE(mode), len(raw), _hash(raw)), len(raw)


def _export(root, end, *, restored=False):
    files, dirs = {}, {}
    pending = [root]
    consumed = 0
    while pending:
        parent = pending.pop()
        for path in _children(parent, MAX_ENTRIES, end):
            if restored and path == root / ".git":
                continue
            rel = _rel(os.fsencode(path.relative_to(root).as_posix()))
            _require(not _excluded(rel), "export contains excluded content")
            _require(len(files) + len(dirs) < MAX_ENTRIES, "export entry limit exceeded")
            info = path.lstat()
            if stat.S_ISDIR(info.st_mode):
                dirs[rel] = stat.S_IMODE(info.st_mode)
                pending.append(path)
            else:
                files[rel], count = _record(path, MAX_EXPORT_BYTES - consumed)
                consumed += count
                _require(consumed <= MAX_EXPORT_BYTES, "export size limit exceeded")
    needed = {str(parent) for rel in files for parent in Path(rel).parents if parent != Path(".")}
    _require(set(dirs) == needed, "export contains unexpected empty directories")
    return files, dirs


def _b64(value):
    return base64.b64encode(value).decode("ascii")


def _unb64(value):
    _require(type(value) is str, "invalid encoded data")
    try:
        decoded = base64.b64decode(value, validate=True)
    except binascii.Error:
        raise ContextError("invalid encoded data") from None
    _require(_b64(decoded) == value, "noncanonical encoded data")
    return decoded


def _line(value):
    _require(value.endswith(b"\n") and value.count(b"\n") == 1 and b"\0" not in value,
             "invalid Git metadata line")
    return value[:-1]


def _ref(name):
    _require(type(name) is str and name.startswith("refs/") and
             name.split("/")[1] not in ("replace", "bisect", "rewritten", "worktree"),
             "unsupported ref")
    raw = name.encode("utf-8")
    _rel(raw)
    _require(all(32 < b != 127 and b not in b"~^:?*[\\" for b in raw) and
             not name.endswith(".") and ".." not in name and "@{" not in name and
             all(not part.startswith(".") and not part.endswith(".lock") for part in name.split("/")),
             "invalid ref name")
    return name


def _oid(raw):
    _require(type(raw) is bytes and OID.fullmatch(raw) and raw != b"0" * 40, "invalid Git object ID")
    return raw.decode("ascii")


def _layout(repo, end):
    dot = repo / ".git"
    mode = dot.lstat().st_mode
    if stat.S_ISDIR(mode):
        _require(not _exists(dot / "commondir"), "unexpected common-directory pointer")
        return dot, dot
    pointer = _line(_read(dot, PATH_LIMIT))
    _require(pointer.startswith(b"gitdir: ") and len(pointer) > 8, "invalid worktree pointer")
    raw = repo / os.fsdecode(pointer[8:])
    meta = _dir(raw).resolve(strict=True)
    common = _dir(meta.parent.parent)
    _require(meta.parent.name == "worktrees" and common.name == ".git" and
             not any(part.is_symlink() for part in (raw, raw.parent, raw.parent.parent)) and
             not _exists(meta / "config"), "unsupported linked worktree location")
    forward = _line(_read(meta / "commondir", PATH_LIMIT))
    back = _line(_read(meta / "gitdir", PATH_LIMIT))
    _require(forward == b"../.." and (meta / os.fsdecode(back)).resolve(strict=True) == dot,
             "unverified linked worktree pointers")
    _require((not _exists(meta / "refs") or not _children(meta / "refs", 1, end)) and
             not _exists(meta / "packed-refs"),
             "worktree-private refs are unsupported")
    return meta, common


def _refs(common, end):
    refs = {}
    packed = common / "packed-refs"
    if _exists(packed):
        can_peel = False
        for row in _read(packed, MAX_METADATA_BYTES).splitlines():
            if row.startswith(b"# pack-refs with: ") and not refs:
                continue
            if row.startswith(b"^") and can_peel:
                _oid(row[1:])
                can_peel = False
                continue
            oid, sep, name = row.partition(b" ")
            _require(bool(sep), "malformed packed ref")
            name = _ref(name.decode("utf-8"))
            _require(name not in refs and len(refs) < MAX_REFS, "duplicate or excessive refs")
            refs[name] = _oid(oid)
            can_peel = True
    paths = [common / "refs"] if _exists(common / "refs") else []
    visited = 0
    while paths:
        for path in _children(paths.pop(), MAX_REFS, end):
            visited += 1
            _require(visited <= MAX_REFS * 2, "ref entry limit exceeded")
            if stat.S_ISDIR(path.lstat().st_mode):
                paths.append(path)
            else:
                name = _ref(path.relative_to(common).as_posix())
                refs[name] = _oid(_line(_read(path, 256)))
                _require(len(refs) <= MAX_REFS, "ref limit exceeded")
    return refs


def _object_store(common, end):
    root = common / "objects"
    inventory = {}
    consumed = 0
    for folder in _children(root, 258, end):
        name = folder.name
        _require(name in ("info", "pack") or bool(re.fullmatch("[0-9a-f]{2}", name)),
                 "unsupported source object store")
        if name == "info":
            allowed = re.compile(r"packs|commit-graph")
        elif name == "pack":
            allowed = re.compile(r"pack-[0-9a-f]{40}\.(?:pack|idx|rev|bitmap|keep|mtimes)")
        else:
            allowed = re.compile(r"[0-9a-f]{38}")
        for path in _children(folder, MAX_OBJECTS * 2, end):
            info = path.lstat()
            _require(stat.S_ISREG(info.st_mode) and allowed.fullmatch(path.name),
                     "unsafe or unsupported source object metadata")
            inventory[path.relative_to(root).as_posix()] = _signature(info)
            consumed += info.st_size
            _require(len(inventory) <= MAX_OBJECTS * 2 and consumed <= MAX_SOURCE_OBJECT_BYTES,
                     "source object store limit exceeded")
    return inventory


def _bool(value):
    _require(value in (b"true", b"yes", b"on", b"1", b"false", b"no", b"off", b"0"),
             "unsupported Boolean Git configuration")
    return value in (b"true", b"yes", b"on", b"1")


def _config(scratch, raw, end):
    config = dict(_BEHAVIOR_CONFIG)
    seen = set()
    rows = _git(scratch, end, "config", "--no-includes", "--file", "-", "--null", "--list", data=raw)
    for row in _nul(rows):
        key, _, value = row.partition(b"\n")
        key = key.decode("utf-8").lower()
        if key in _BEHAVIOR_CONFIG or key in ("core.bare", "core.repositoryformatversion"):
            _require(key not in seen, "duplicate Git configuration")
            seen.add(key)
        if key in _BEHAVIOR_CONFIG:
            config[key] = _bool(value.lower())
        elif key == "core.bare":
            _require(not _bool(value.lower()), "bare source is unsupported")
        elif key == "core.repositoryformatversion":
            _require(value == b"0", "unsupported Git repository format")
        elif key in _INERT_CONFIG or re.fullmatch(r"(branch\..+|remote\..+)\.(remote|merge|url|fetch|pushurl)", key):
            continue
        else:
            raise ContextError("unsupported local Git configuration")
    return config


def _native(repo, end):
    meta, common = _layout(repo, end)
    for directory in {meta, common}:
        _require(all(not _exists(directory / name) for name in _UNSUPPORTED_METADATA),
                 "unsupported or changing Git metadata")
    if _exists(common / "info"):
        _dir(common / "info")
    controls = [repo / ".git", meta / "HEAD", meta / "index", common / "config",
                common / "packed-refs", common / "refs", common / "info" / "exclude"]
    if meta != common:
        controls.extend((meta / "commondir", meta / "gitdir", meta / "refs"))
    before = [(_signature(path.lstat()) if _exists(path) else None) for path in controls]
    head_line = _line(_read(meta / "HEAD", PATH_LIMIT))
    refs = _refs(common, end)
    if head_line.startswith(b"ref: "):
        symbolic = _ref(head_line[5:].decode("utf-8"))
        _require(symbolic.startswith("refs/heads/") and symbolic in refs, "unborn or unsupported HEAD")
        head = {"oid": refs[symbolic], "symbolic": symbolic}
    else:
        head = {"oid": _oid(head_line), "symbolic": None}
    config = _read(common / "config", MAX_METADATA_BYTES)
    index = _read(meta / "index", MAX_METADATA_BYTES)
    exclude = common / "info" / "exclude"
    info_exclude = _read(exclude, MAX_METADATA_BYTES) if _exists(exclude) else b""
    objects = _object_store(common, end)
    _require(before == [(_signature(path.lstat()) if _exists(path) else None) for path in controls],
             "Git metadata changed during capture")
    return {"meta": meta, "common": common, "head": head, "refs": refs, "index": index,
            "config": config, "exclude": info_exclude, "objects": objects, "controls": before}


def _index(raw):
    _require(len(raw) >= 32 and raw[:4] == b"DIRC" and hashlib.sha1(raw[:-20]).digest() == raw[-20:],
             "missing or invalid Git index")
    version, count = struct.unpack_from(">II", raw, 4)
    _require(version in (2, 3) and count <= MAX_ENTRIES, "unsupported Git index version or count")
    pos, end = 12, len(raw) - 20
    records = []
    previous = b""
    for _ in range(count):
        _require(pos + 62 < end, "truncated Git index")
        mode, = struct.unpack_from(">I", raw, pos + 24)
        oid = _oid(raw[pos + 40:pos + 60].hex().encode("ascii"))
        flags, = struct.unpack_from(">H", raw, pos + 60)
        _require(not flags & 0xF000, "unsupported Git index flags or conflict")
        stop = raw.find(b"\0", pos + 62, min(end, pos + 62 + PATH_LIMIT + 1))
        _require(stop >= 0, "invalid index path terminator")
        path = raw[pos + 62:stop]
        _rel(path)
        _require(path > previous and (flags & 0xFFF) == min(len(path), 0xFFF), "invalid index path order or length")
        previous = path
        encoded_mode = f"{mode:o}".encode("ascii")
        _require(encoded_mode in _INDEX_MODES, "submodule or unsupported index mode")
        records.append([encoded_mode.decode("ascii"), oid, _b64(path)])
        following = pos + ((stop + 1 - pos + 7) & ~7)
        _require(following <= end and not any(raw[stop:following]), "invalid index padding")
        pos = following
    extensions = set()
    while pos < end:
        _require(pos + 8 <= end, "truncated index extension")
        name, size = struct.unpack_from(">4sI", raw, pos)
        _require(name in (b"TREE", b"UNTR", b"EOIE", b"IEOT") and name not in extensions,
                 "unsupported Git index extension")
        extensions.add(name)
        pos += 8 + size
    _require(pos == end, "truncated Git index")
    return records


def _nul(raw):
    if not raw:
        return []
    _require(raw.endswith(b"\0"), "truncated Git output")
    rows = raw[:-1].split(b"\0")
    _require(len(rows) <= MAX_ENTRIES and all(rows), "invalid Git output count")
    return rows


def _native_files(repo, scratch, meta, objects, end):
    names = _git(scratch, end, "ls-files", "-z", "--cached", "--others", "--exclude-standard",
                 meta=meta, work=repo, objects=objects)
    files = {}
    consumed = 0
    for raw in sorted(set(_nul(names))):
        if _excluded(os.fsdecode(raw)):
            continue
        rel = _rel(raw)
        parts = rel.split("/")
        path = repo
        for part in parts[:-1]:
            path = path / part
            if not _exists(path) or not stat.S_ISDIR(path.lstat().st_mode):
                break
        else:
            path = path / parts[-1]
            if _exists(path):
                files[rel], count = _record(path, MAX_EXPORT_BYTES - consumed)
                consumed += count
                _require(consumed <= MAX_EXPORT_BYTES, "native file size limit exceeded")
        _time(end)
    return files


def _status(scratch, meta, work, end, *, objects=None):
    raw = _git(scratch, end, "status", "--porcelain=v1", "-z", "--untracked-files=all",
               "--no-renames", "--ignore-submodules=none", meta=meta, work=work, objects=objects)
    tracked = untracked = omitted = 0
    kept = []
    for row in _nul(raw):
        _require(len(row) > 3 and row[2:3] == b" " and
                 (row[:2] == b"??" or all(byte in b" MADT" for byte in row[:2]) and row[:2] != b"  "),
                 "unsupported status record")
        path = _rel(row[3:])
        if row.startswith(b"?? ") and _excluded(path):
            omitted += 1
        else:
            kept.append(row + b"\0")
            if row.startswith(b"?? "):
                untracked += 1
            else:
                tracked += 1
    return {"sha256": _hash(b"".join(kept)), "tracked": tracked, "untracked": untracked}, omitted


def _setup(meta, head, refs, config):
    _mkdir(meta)
    for leaf in ("objects", "refs", "info"):
        _mkdir(meta / leaf)
    # No init template, worktree pointer, hooks, logs, remotes or auth.
    protected = {"hooksPath": os.devnull, "fsmonitor": "false", "untrackedCache": "false"}
    pairs = {**{k.split(".", 1)[1]: str(v).lower() for k, v in config.items()}, **protected}
    raw_config = ("[core]\n\trepositoryformatversion = 0\n\tbare = false\n" +
                  "".join(f"\t{k} = {v}\n" for k, v in sorted(pairs.items())) +
                  "[protocol]\n\tallow = never\n").encode("ascii")
    _write(meta / "config", raw_config)
    line = "ref: " + head["symbolic"] if head["symbolic"] else head["oid"]
    _write(meta / "HEAD", (line + "\n").encode("utf-8"))
    if refs:
        # A standalone packed-refs file avoids case-folding collisions and
        # accepts names matching branch/tag prefixes without symlink walks.
        _write(meta / "packed-refs", b"# pack-refs with: sorted\n" +
               b"".join(f"{oid} {name}\n".encode("utf-8") for name, oid in sorted(refs.items())))


def _reachable(scratch, meta, head, refs, end, *, objects=None):
    _require(_git(scratch, end, "cat-file", "-t", head["oid"], meta=meta, objects=objects,
                  limit=128) == b"commit\n", "HEAD is not a commit")
    roots = {head["oid"], *refs.values()}
    raw = _git(scratch, end, "rev-list", "--objects", "--no-object-names", "--missing=error",
               "--stdin", meta=meta, objects=objects, data=_oids(roots), limit=MAX_OBJECTS * 41)
    rows = _oid_rows(raw)
    _require(roots <= rows, "declared history roots were not traversed")
    return rows


def _oids(items):
    return b"".join(oid.encode("ascii") + b"\n" for oid in sorted(items))


def _oid_rows(raw):
    _require(raw.endswith(b"\n"), "truncated object inventory")
    rows = raw[:-1].split(b"\n")
    result = {_oid(row) for row in rows}
    _require(len(result) == len(rows) <= MAX_OBJECTS, "invalid or excessive object inventory")
    return result


def _verify_objects(scratch, meta, reachable, index_oids, end, *, objects=None, markers=()):
    union = reachable | index_oids
    _require(len(union) <= MAX_OBJECTS, "object count limit exceeded")
    oids = _oids(union)
    headers = _git(scratch, end, "cat-file", "--batch-check", meta=meta, objects=objects,
                   data=oids, limit=MAX_OBJECTS * 90)
    expected = []
    count = 0
    header_rows = headers.splitlines(keepends=True)
    _require(len(header_rows) == len(union), "object header count mismatch")
    for oid, row in zip(sorted(union), header_rows):
        found, kind, size = (_line(row).split(b" ") + [b""] * 3)[:3]
        _require(found == oid.encode("ascii") and kind in (b"blob", b"tree", b"commit", b"tag") and
                 size.isdigit() and len(size) <= 9 and _line(row) == b" ".join((found, kind, size)),
                 "missing or malformed object header")
        length = int(size)
        _require(str(length).encode("ascii") == size and length <= MAX_OBJECT_BYTES,
                 "object size limit exceeded")
        _require(oid not in index_oids or kind == b"blob", "index object is not a blob")
        count += length
        _require(count <= MAX_TOTAL_BYTES, "inflated Git object limit exceeded")
        expected.append((oid, kind, size, row, length))
    raw = _git(scratch, end, "cat-file", "--batch", meta=meta, objects=objects, data=oids,
               limit=count + len(headers) + len(union))
    stream = io.BytesIO(raw)
    blobs = matched = 0
    for oid, kind, size, row, length in expected:
        _time(end)
        _require(stream.read(len(row)) == row, "Git object batch header mismatch")
        value = stream.read(length)
        _require(len(value) == length and stream.read(1) == b"\n", "truncated Git object body")
        digest = hashlib.sha1(kind + b" " + size + b"\0")
        digest.update(value)
        _require(digest.hexdigest() == oid, "Git object identity mismatch")
        if kind == b"tree":
            _verify_tree(value)
        if kind == b"blob" and oid in reachable:
            blobs += 1
            matched += any(marker in value for marker in markers)
    _require(not stream.read(1), "unexpected trailing Git batch output")
    return blobs, matched


def _verify_tree(raw):
    pos = 0
    while pos < len(raw):
        nul = raw.find(b"\0", pos, min(len(raw), pos + PATH_LIMIT + 10))
        _require(nul > pos and nul + 21 <= len(raw), "malformed Git tree object")
        mode, sep, name = raw[pos:nul].partition(b" ")
        _require(sep and mode in _INDEX_MODES | {b"40000"} and b"/" not in name,
                 "submodule or unsupported tree entry")
        _rel(name)
        pos = nul + 21


def _pack_structure(pack, end):
    _require(32 <= len(pack) <= MAX_PACK_BYTES and pack[:4] == b"PACK" and
             hashlib.sha1(memoryview(pack)[:-20]).digest() == pack[-20:],
             "invalid retained pack or checksum")
    version, entries = struct.unpack_from(">II", pack, 4)
    _require(version in (2, 3) and 0 < entries <= MAX_OBJECTS, "invalid pack version or object count")
    pos, end_pos, total = 12, len(pack) - 20, 0
    for _ in range(entries):
        _time(end)
        _require(pos < end_pos, "truncated packed object")
        byte = pack[pos]
        pos += 1
        _require(1 <= (byte >> 4) & 7 <= 4, "delta or invalid packed object type")
        length, shift = byte & 15, 4
        while byte & 128:
            _require(pos < end_pos and shift <= 25, "invalid packed size")
            byte = pack[pos]
            pos += 1
            length |= (byte & 127) << shift
            shift += 7
        total += length
        _require(length <= MAX_OBJECT_BYTES and total <= MAX_TOTAL_BYTES, "inflated pack limit exceeded")
        decoder = zlib.decompressobj()
        decoded = 0
        while not decoder.eof:
            _time(end)
            _require(pos < end_pos, "truncated packed stream")
            block = pack[pos:min(pos + 65536, end_pos)]
            try:
                out = decoder.decompress(block, length - decoded + 1)
            except zlib.error:
                raise ContextError("invalid packed stream") from None
            decoded += len(out)
            _require(decoded <= length and not decoder.unconsumed_tail, "packed object length mismatch")
            pos += len(block) - len(decoder.unused_data)
        _require(decoded == length, "packed object length mismatch")
    _require(pos == end_pos, "unaccounted pack data")
    return entries


def _index_records(records):
    _require(type(records) is list and len(records) <= MAX_ENTRIES, "invalid index records")
    lines = []
    previous = b""
    paths = set()
    for record in records:
        _require(type(record) is list and len(record) == 3, "invalid index record")
        mode, oid, encoded_path = record
        _require(type(mode) is str and type(oid) is str, "invalid index mode or object")
        mode = mode.encode("ascii")
        oid = _oid(oid.encode("ascii")).encode("ascii")
        raw = _unb64(encoded_path)
        _rel(raw)
        parts = raw.split(b"/")
        _require(mode in _INDEX_MODES and raw > previous and
                 not any(b"/".join(parts[:i]) in paths for i in range(1, len(parts))),
                 "invalid or unordered index record")
        previous = raw
        paths.add(raw)
        lines.append(mode + b" " + oid + b"\t" + raw + b"\0")
    return b"".join(lines)


def _load(context, expected, end):
    _require({entry.name for entry in _children(context, 3, end)} == {"receipt.json", "objects.pack"},
             "unexpected context inventory")
    raw = _read(context / "receipt.json", MAX_METADATA_BYTES)
    receipt = json.loads(raw)
    _require(type(receipt) is dict and _canonical(receipt) + b"\n" == raw, "noncanonical context receipt")
    keys = {"schema", "context_sha256", "binding", "export_sha256", "pack_sha256", "head",
            "refs", "index", "config", "status", "omitted_untracked", "exclusions",
            "object_count", "reachable_count"}
    _require(set(receipt) == keys and receipt["schema"] == SCHEMA, "unsupported context receipt")
    digest = receipt["context_sha256"]
    _require(digest == _hash(_canonical({k: v for k, v in receipt.items() if k != "context_sha256"})),
             "context digest mismatch")
    _require(_canonical(_binding(receipt["binding"])) == _canonical(_binding(expected)),
             "Git context binding mismatch")
    for key in ("export_sha256", "pack_sha256"):
        _require(type(receipt[key]) is str and SHA.fullmatch(receipt[key]), "invalid receipt digest")
    refs, head = receipt["refs"], receipt["head"]
    _require(type(refs) is dict and len(refs) <= MAX_REFS and
             type(head) is dict and set(head) == {"oid", "symbolic"}, "invalid refs or HEAD")
    for name, oid in refs.items():
        _ref(name)
        _require(type(oid) is str, "invalid ref object")
        _oid(oid.encode("ascii"))
    _require(type(head["oid"]) is str, "invalid HEAD object")
    _oid(head["oid"].encode("ascii"))
    name = head["symbolic"]
    _require(name is None or type(name) is str and name.startswith("refs/heads/") and
             refs.get(name) == head["oid"], "invalid symbolic HEAD")
    _index_records(receipt["index"])
    config = receipt["config"]
    _require(type(config) is dict and set(config) == set(_BEHAVIOR_CONFIG) and
             all(type(value) is bool for value in config.values()), "invalid retained Git configuration")
    status = receipt["status"]
    _require(type(status) is dict and set(status) == {"sha256", "tracked", "untracked"} and
             type(status["sha256"]) is str and SHA.fullmatch(status["sha256"]), "invalid retained status")
    for value in (status["tracked"], status["untracked"], receipt["omitted_untracked"]):
        _require(type(value) is int and 0 <= value <= MAX_ENTRIES, "invalid status count")
    _require(receipt["exclusions"] == list(EXCLUSIONS), "unsupported export exclusions")
    counts = receipt["reachable_count"], receipt["object_count"]
    _require(all(type(value) is int for value in counts) and 0 < counts[0] <= counts[1] <= MAX_OBJECTS,
             "invalid retained object counts")
    pack = _read(context / "objects.pack", MAX_PACK_BYTES)
    _require(_hash(pack) == receipt["pack_sha256"], "pack digest mismatch")
    return receipt, pack


def _install(scratch, meta, receipt, pack, end, markers=()):
    count = _pack_structure(pack, end)
    _require(count == receipt["object_count"], "retained pack count mismatch")
    _setup(meta, receipt["head"], receipt["refs"], receipt["config"])
    _git(scratch, end, "index-pack", "--strict", "--stdin", meta=meta, data=pack, limit=128)
    refs = _git(scratch, end, "for-each-ref", "--format=%(objectname) %(refname)", meta=meta)
    _require(refs == b"".join(f"{oid} {name}\n".encode("utf-8")
                              for name, oid in sorted(receipt["refs"].items())),
             "reconstructed Git refs differ")
    reachable = _reachable(scratch, meta, receipt["head"], receipt["refs"], end)
    staged = {oid for _, oid, _ in receipt["index"]}
    _require(len(reachable) == receipt["reachable_count"] and len(reachable | staged) == count,
             "reachable or staged object count mismatch")
    raw = _git(scratch, end, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)",
               meta=meta, limit=MAX_OBJECTS * 41)
    _require(_oid_rows(raw) == reachable | staged, "missing or unexpected retained objects")
    return _verify_objects(scratch, meta, reachable, staged, end, markers=markers)


def _copy_export(source, output, inventory, end):
    files, dirs = inventory
    _mkdir(output)
    for rel in sorted(dirs, key=lambda path: (path.count("/"), path)):
        _mkdir(output / rel)
    for rel, row in files.items():
        _time(end)
        goal = output / rel
        if row[0] == "link":
            _require(_b64(os.fsencode(os.readlink(source / rel))) == row[1],
                     "export link changed during replay")
            os.symlink(os.fsdecode(_unb64(row[1])), goal)
        else:
            _, mode, length, digest = row
            raw = _read(source / rel, length)
            _require(len(raw) == length and _hash(raw) == digest, "export file changed during replay")
            _write(goal, raw, mode)
    for rel in sorted(dirs, key=lambda path: (-path.count("/"), path)):
        (output / rel).chmod(dirs[rel])


def _rebuild(scratch, meta, work, receipt, end):
    lines = _index_records(receipt["index"])
    _git(scratch, end, "read-tree", "--empty", meta=meta, work=work)
    if lines:
        _git(scratch, end, "update-index", "-z", "--index-info", meta=meta, work=work, data=lines)
    _require(_index(_read(meta / "index", MAX_METADATA_BYTES)) == receipt["index"],
             "reconstructed Git index differs")
    status, omitted = _status(scratch, meta, work, end)
    _require(status == receipt["status"] and not omitted, "reconstructed Git status differs")
    _require(_git(scratch, end, "rev-parse", "--verify", "HEAD", meta=meta, work=work,
                  limit=128) == receipt["head"]["oid"].encode("ascii") + b"\n", "reconstructed HEAD differs")
    for parent, dirs, files in os.walk(meta):
        _time(end)
        Path(parent).chmod(0o700)
        for name in files:
            (Path(parent) / name).chmod(0o600)


@_api
def capture(repo, export_root, output, *, binding):
    """Retain Git evidence for the already exported, drained native endpoint."""
    end = time.monotonic() + MAX_SECONDS
    binding = _binding(binding)
    repo, export_root = _root(repo), _root(export_root)
    _disjoint(repo, export_root)
    native = _native(repo, end)
    output = _fresh(output, repo, export_root, native["common"], native["meta"])
    inventory = _export(export_root, end)
    with tempfile.TemporaryDirectory(prefix="v7-git-capture-", dir=output.parent) as temp:
        scratch = Path(temp)
        meta = scratch / "source.git"
        config = _config(scratch, native["config"], end)
        _setup(meta, native["head"], native["refs"], config)
        _write(meta / "index", native["index"])
        if native["exclude"]:
            _write(meta / "info" / "exclude", native["exclude"])
        index = _index(native["index"])
        objects = native["common"] / "objects"
        _require(_native_files(repo, scratch, meta, objects, end) == inventory[0],
                 "native selected files differ from export")
        status, omitted = _status(scratch, meta, repo, end, objects=objects)
        reachable = _reachable(scratch, meta, native["head"], native["refs"], end, objects=objects)
        staged = {oid for _, oid, _ in index}
        _verify_objects(scratch, meta, reachable, staged, end, objects=objects)
        pack = _git(scratch, end, "pack-objects", "--stdout", "--window=0", "--no-reuse-delta",
                    "--no-reuse-object", meta=meta, objects=objects, data=_oids(reachable | staged),
                    limit=MAX_PACK_BYTES)
        receipt = {
            "schema": SCHEMA, "binding": binding, "export_sha256": _hash(_canonical(inventory)),
            "head": native["head"], "refs": native["refs"], "index": index, "config": config,
            "status": status, "omitted_untracked": omitted, "exclusions": list(EXCLUSIONS),
            "pack_sha256": _hash(pack), "object_count": len(reachable | staged),
            "reachable_count": len(reachable),
        }
        # Verify from the pack alone and compare reconstruction before publishing
        # a receipt, so unsupported native parity is rejected at capture too.
        replay = scratch / "replay"
        _copy_export(export_root, replay, inventory, end)
        _install(scratch, replay / ".git", receipt, pack, end)
        _rebuild(scratch, replay / ".git", replay, receipt, end)
        _require(_export(replay, end, restored=True) == inventory == _export(export_root, end),
                 "export inventory changed during capture")
        _require(_native_files(repo, scratch, meta, objects, end) == inventory[0] and
                 _status(scratch, meta, repo, end, objects=objects) == (status, omitted) and
                 _native(repo, end) == native, "native endpoint changed during capture")
        receipt["context_sha256"] = _hash(_canonical(receipt))
        raw = _canonical(receipt) + b"\n"
        _require(len(raw) <= MAX_METADATA_BYTES, "context receipt exceeds limit")
        _mkdir(output)
        _write(output / "objects.pack", pack)
        _write(output / "receipt.json", raw)
    return receipt


@_api
def restore(context_dir, export_root, output, *, expected_binding):
    """Reconstruct a disposable Git checkout without changing the product export."""
    end = time.monotonic() + MAX_SECONDS
    context, export_root = _root(context_dir), _root(export_root)
    _disjoint(context, export_root)
    output = _fresh(output, context, export_root)
    receipt, pack = _load(context, expected_binding, end)
    inventory = _export(export_root, end)
    _require(_hash(_canonical(inventory)) == receipt["export_sha256"], "export digest mismatch")
    with tempfile.TemporaryDirectory(prefix="v7-git-restore-", dir=output.parent) as temp:
        scratch = Path(temp)
        replay = scratch / "replay"
        _copy_export(export_root, replay, inventory, end)
        _install(scratch, replay / ".git", receipt, pack, end)
        _rebuild(scratch, replay / ".git", replay, receipt, end)
        _require(_export(replay, end, restored=True) == inventory == _export(export_root, end),
                 "export inventory changed during restore")
        entries = _children(replay, MAX_ENTRIES + 1, end)
        _mkdir(output)
        for entry in entries:
            entry.rename(output / entry.name)
    return receipt


@_api
def scan(context_dir, *, expected_binding, markers):
    """Scan verified reachable blobs for explicit synthetic literal/base64 forms."""
    end = time.monotonic() + MAX_SECONDS
    _require(type(markers) in (list, tuple) and 0 < len(markers) <= 16, "invalid marker inventory")
    literals = set()
    for marker in markers:
        if type(marker) is str:
            marker = marker.encode("utf-8")
        _require(type(marker) is bytes and 0 < len(marker) <= 1024, "invalid marker")
        literals.update((marker, base64.b64encode(marker)))
    context = _root(context_dir)
    receipt, pack = _load(context, expected_binding, end)
    with tempfile.TemporaryDirectory(prefix="v7-git-scan-") as temp:
        scratch = Path(temp)
        blobs, matched = _install(scratch, scratch / "scan.git", receipt, pack, end, tuple(sorted(literals)))
    return {
        "schema": SCAN_SCHEMA, "context_sha256": receipt["context_sha256"],
        "status": "FOUND" if matched else "CLEAN", "reachable_objects": receipt["reachable_count"],
        "verified_blobs": blobs, "matched_blobs": matched, "coverage": COVERAGE,
        "marker_forms": list(MARKER_FORMS),
    }
