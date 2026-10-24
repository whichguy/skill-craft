#!/usr/bin/env python3
"""Prompt overlays and ref builds for template experiments (experiment.py): a B arm before its code exists.

An overlay is a JSON file of edits to the ShipLoop scripts of a plugin BUILD copy, never the source checkout:

    {"about": "...", "edits": [
      {"module": "shiploop_prompts.py", "constant": "DUTIES", "key": "test-spec",
       "old": "<exact source text inside that entry>", "new": "<replacement source text>"},
      {"module": "shiploop_navigator.py", "function": "_improve_commit_lines", "old": "...", "new": "..."}]}

Each edit names where it lands: a top-level constant (optionally one ``key`` of a dict literal) or a top-level function.
``old`` is matched against the module's SOURCE text inside that span and must occur there exactly once, so an overlay
written against another build's text is refused instead of silently doing nothing. ``new`` is source text too (it sits
inside the same string literal as ``old``). The edited module must still compile.

    python3 test/shiploop_e2e/overlay.py check OVERLAY [--scripts DIR]   # does every edit apply (default: this checkout)

``build_ref`` builds the plugin from a git ref, read-only: a detached temporary worktree of that ref (never a checkout in
another worktree), its own scripts/build-packages.py, then the worktree is removed.
"""
from __future__ import annotations

import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
PLUGIN_SCRIPTS = Path("skills") / "shiploop" / "scripts"
sys.path.insert(0, str(HERE))


class OverlayError(ValueError):
    pass


def load(path: Path) -> dict:
    data = json.loads(Path(path).read_text())
    edits = data.get("edits")
    if not isinstance(edits, list) or not edits:
        raise OverlayError(f"{path}: an overlay needs a non-empty `edits` list")
    for n, edit in enumerate(edits, 1):
        if not isinstance(edit, dict) or not all(isinstance(edit.get(k), str) for k in ("module", "old", "new")):
            raise OverlayError(f"{path}: edit {n} needs `module`, `old` and `new` strings")
        if bool(edit.get("constant")) == bool(edit.get("function")):
            raise OverlayError(f"{path}: edit {n} names exactly one of `constant` or `function`")
    return data


def _span(source: str, edit: dict) -> tuple[int, int]:
    """(start, end) character offsets of the named constant, dict entry or function in ``source``."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def at(node: ast.AST) -> tuple[int, int]:
        start = offsets[node.lineno - 1] + node.col_offset
        end = offsets[node.end_lineno - 1] + node.end_col_offset
        return start, end

    for node in tree.body:
        if edit.get("function") and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == edit["function"]:
            return at(node)
        if edit.get("constant") and isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == edit["constant"] for t in targets):
                if not edit.get("key"):
                    return at(node)
                if not isinstance(node.value, ast.Dict):
                    raise OverlayError(f"{edit['module']}: {edit['constant']} is not a dict literal; `key` needs one")
                for key, value in zip(node.value.keys, node.value.values):
                    if isinstance(key, ast.Constant) and key.value == edit["key"]:
                        return at(value)
                raise OverlayError(f"{edit['module']}: {edit['constant']} has no key {edit['key']!r}")
    raise OverlayError(f"{edit['module']}: no top-level {edit.get('function') or edit.get('constant')}")


def apply_to_source(source: str, edit: dict) -> str:
    start, end = _span(source, edit)
    segment = source[start:end]
    found = segment.count(edit["old"])
    where = edit.get("function") or edit["constant"] + (f"[{edit['key']!r}]" if edit.get("key") else "")
    if found != 1:
        raise OverlayError(f"{edit['module']} {where}: `old` occurs {found} times there (it must occur once): "
                           f"{edit['old'][:80]!r}")
    return source[:start] + segment.replace(edit["old"], edit["new"]) + source[end:]


def apply(overlay: dict, scripts: Path) -> list[dict]:
    """Apply every edit to the scripts folder ``scripts`` (a build copy). All edits are checked before any file is written.
    Returns one record per edited module with the sha256 before and after."""
    scripts = Path(scripts)
    if scripts.resolve() == SCRIPTS.resolve():
        raise OverlayError("refusing to overlay the source checkout's scripts; overlays apply to a build copy only")
    texts: dict[str, str] = {}
    before: dict[str, str] = {}
    for edit in overlay["edits"]:
        name = edit["module"]
        if name not in texts:
            texts[name] = (scripts / name).read_text()
            before[name] = hashlib.sha256(texts[name].encode()).hexdigest()[:12]
        texts[name] = apply_to_source(texts[name], edit)
    for name, text in texts.items():
        compile(text, name, "exec")
    records = []
    for name, text in texts.items():
        path = scripts / name
        path.unlink()  # a build file could be a link to the source: never write through it
        path.write_text(text)
        for cache in (scripts / "__pycache__").glob(Path(name).stem + ".*.pyc"):
            cache.unlink()
        records.append({"module": name, "before": before[name], "after": hashlib.sha256(text.encode()).hexdigest()[:12]})
    return records


def apply_to_plugin(overlay_path: Path, plugin_dir: Path) -> dict:
    overlay = load(overlay_path)
    return {"overlay": str(overlay_path), "modules": apply(overlay, Path(plugin_dir) / PLUGIN_SCRIPTS)}


def resolve_ref(ref: str) -> str:
    done = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", ref + "^{commit}"], capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(f"unknown git ref {ref!r}: {done.stderr.strip()}")
    return done.stdout.strip()


def build_ref(ref: str, out: Path) -> Path:
    """The skill-craft plugin built from ``ref`` into ``out``/build, read-only from a detached temporary worktree."""
    from run import PLUGIN_NAME  # noqa: PLC0415
    commit = resolve_ref(ref)
    source = Path(tempfile.mkdtemp(prefix="shiploop-ref-")) / "src"
    subprocess.run(["git", "-C", str(ROOT), "worktree", "add", "--detach", "-q", str(source), commit],
                   check=True, capture_output=True, text=True)
    try:
        subprocess.run([sys.executable, "-B", str(source / "scripts/build-packages.py"), str(out / "build")],
                       check=True, stdout=subprocess.DEVNULL)
    finally:
        subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", str(source)], capture_output=True)
        shutil.rmtree(source.parent, ignore_errors=True)
    (out / "build" / "ref.json").write_text(json.dumps({"ref": ref, "commit": commit}) + "\n")
    return out / "build" / "plugins" / PLUGIN_NAME


def check(overlay_path: Path, scripts: Path = SCRIPTS) -> list[str]:
    """Problems applying the overlay to a copy of ``scripts`` (empty: it applies)."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "scripts"
        shutil.copytree(scripts, copy, ignore=shutil.ignore_patterns("__pycache__"))
        try:
            apply(load(overlay_path), copy)
        except (OverlayError, SyntaxError, OSError) as error:
            return [str(error)]
    return []


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) >= 2 and args[0] == "check":
        scripts = Path(args[args.index("--scripts") + 1]) if "--scripts" in args else SCRIPTS
        problems = check(Path(args[1]), scripts)
        print("\n".join(problems) or "applies")
        return 1 if problems else 0
    sys.stderr.write(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
