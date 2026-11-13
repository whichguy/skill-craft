"""Survey every file in real ShipLoop run directories: syntax per format, shape of the small display files,
leftovers (transaction.md, pending-*.patch, atomic-write temp files), and the inventory of names for a catalog diff.

Read-only. Usage: python3 -I 2026-11-13-run-dir-survey.py <file listing state.md paths> [--json out.json]
The listing came from `find ~ -maxdepth 9 -name state.md` (2,636 files on 2026-11-13); only the runs whose state names
navigator protocol 4 are walked. The shiploop_store module is read from the checkout this file sits in.
"""
import collections
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "shiploop" / "scripts"))
import shiploop_store as store  # noqa: E402

listing = [line.strip() for line in open(sys.argv[1]) if line.strip()]
out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None

SKIP_PARTS = ("node_modules", "/.git/")
def pattern(rel):
    parts = rel.split("/")
    base = parts[-1]
    base = re.sub(r"[0-9a-f]{8,}", "<hex>", base)
    base = re.sub(r"\b[A-Z]{1,3}\d+(\.\d+)*\b", "<id>", base)
    base = re.sub(r"-?\d+", "<n>", base)
    top = parts[0] if len(parts) > 1 else ""
    mid = "/".join(parts[1:-1])
    return (top + "/" + ("…/" if mid else "") + base) if top else base

runs = []
for s in listing:
    d = os.path.dirname(s)
    try:
        head = open(s, "rb").read(4096).decode("utf-8", "replace")
    except OSError:
        continue
    runs.append(d)

stats = collections.defaultdict(collections.Counter)   # pattern -> {ok, bad, ...}
bad = collections.defaultdict(list)
sizes = {}
leftovers = collections.defaultdict(list)
nonutf8 = []
protocols = collections.Counter()
shape_bad = collections.defaultdict(list)
total_files = 0
runs_ok = 0

for d in runs:
    state_path = os.path.join(d, "state.md")
    try:
        state = store.read_record(state_path)
    except Exception as exc:
        stats["state.md"]["unparsable"] += 1
        bad["state.md"].append((d, str(exc)[:120]))
        continue
    if not isinstance(state, dict) or "navigator_protocol_version" not in state:
        stats["state.md"]["notstate"] += 1
        continue
    protocols[str(state.get("navigator_protocol_version"))] += 1
    if state.get("navigator_protocol_version") != 4:
        continue
    runs_ok += 1
    for root, dirs, files in os.walk(d, followlinks=False):
        if any(p in root + "/" for p in SKIP_PARTS):
            dirs[:] = []
            continue
        if root == d:
            dirs[:] = [x for x in dirs if x not in ("scratch", "worktree", "worktrees", "repo")]
        for name in files:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, d)
            total_files += 1
            pat = pattern(rel)
            try:
                size = os.lstat(path).st_size
            except OSError:
                continue
            sizes.setdefault(pat, []).append(size)
            if name == "transaction.md":
                leftovers["transaction.md"].append(path)
            if name.startswith("pending-") and name.endswith(".patch"):
                leftovers["pending-patch"].append(path)
            if re.match(r"^\..*\.tmp$", name) or ".shiploop-lint-" in name:
                leftovers["atomic-temp"].append(path)
            ext = os.path.splitext(name)[1]
            if ext in (".md", ".json", ".jsonl", ".txt", ".patch", ".html", "") and size < 8_000_000:
                try:
                    raw = open(path, "rb").read()
                except OSError:
                    continue
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    nonutf8.append(path)
                    stats[pat]["non-utf8"] += 1
                    continue
                if ext == ".md" and "```shiploop-state" in text:
                    try:
                        store.loads(text)
                        stats[pat]["fence-ok"] += 1
                    except Exception as exc:
                        stats[pat]["fence-bad"] += 1
                        bad[pat].append((path, str(exc)[:100]))
                elif ext == ".md":
                    stats[pat]["markdown-text"] += 1
                elif ext == ".json":
                    try:
                        value = json.loads(text)
                        stats[pat]["json-ok"] += 1
                        if not text.endswith("\n"):
                            stats[pat]["json-no-final-newline"] += 1
                        if name == "timeline.json":
                            ok = (isinstance(value, dict) and set(value) == {"started", "accepted"}
                                  and isinstance(value["started"], str) and isinstance(value["accepted"], dict)
                                  and all(isinstance(k, str) and isinstance(v, str) for k, v in value["accepted"].items()))
                            if not ok:
                                shape_bad["timeline.json"].append(path)
                        if name == "progress-observer.json":
                            if not (isinstance(value, dict) and value.get("schema") == "shiploop-progress-observer/v1"):
                                shape_bad["progress-observer.json"].append(path)
                    except Exception as exc:
                        stats[pat]["json-bad"] += 1
                        bad[pat].append((path, str(exc)[:100]))
                elif ext == ".jsonl":
                    nbad = 0
                    for line in text.split("\n"):
                        if line.strip():
                            try:
                                json.loads(line)
                            except Exception:
                                nbad += 1
                    stats[pat]["jsonl-ok" if not nbad else "jsonl-bad-lines"] += 1
                elif name == "callback-attempts":
                    try:
                        int(text.strip() or 0)
                        stats[pat]["int-ok"] += 1
                    except ValueError:
                        stats[pat]["int-bad"] += 1
                        bad[pat].append((path, repr(text[:40])))
                else:
                    stats[pat]["other"] += 1
            else:
                stats[pat]["binary-or-skipped"] += 1

print("runs listed", len(runs), "with a parsable protocol state", runs_ok, "files walked", total_files)
print("protocols", dict(protocols))
print("non-utf8 files", len(nonutf8), nonutf8[:5])
print("leftovers", {k: len(v) for k, v in leftovers.items()})
for k, v in leftovers.items():
    print("  ", k, v[:4])
print("shape problems", {k: len(v) for k, v in shape_bad.items()})
for k, v in shape_bad.items():
    print("  ", k, v[:3])
print("\n=== patterns (name: counters) ===")
for pat in sorted(stats):
    print(f"{pat:60s} {dict(stats[pat])}")
print("\n=== parse failures ===")
for pat, rows in sorted(bad.items()):
    print(pat, len(rows))
    for row in rows[:4]:
        print("   ", row)
if out:
    json.dump({"runs": len(runs), "ok": runs_ok, "files": total_files, "protocols": protocols,
               "patterns": {k: dict(v) for k, v in stats.items()},
               "leftovers": {k: v[:20] for k, v in leftovers.items()},
               "bad": {k: v[:20] for k, v in bad.items()}}, open(out, "w"), indent=1, default=str)
