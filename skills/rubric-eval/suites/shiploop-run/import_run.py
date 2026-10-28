#!/usr/bin/env python3
"""Place artifacts that ShipLoop runs produced into a rubric-eval RUN folder, so `judge`, `reliability` and
`analyze` grade them as if `run` had written them.

  import_run.py collect RUNROOT [RUNROOT ...] --out POOL.jsonl
      one line per gradable artifact found in the run folders: its text (the stage's accepted result, or an
      Improve review note for pass 2 or later) and its run record (the facts block), both scrubbed.
  import_run.py place RUN --pool POOL.jsonl --arm NAME --condition MODEL [--select IDS.txt] [--trial-by ...]
      writes RUN/manifest.json (one recorded condition) and RUN/out/<scenario>_<slot>_<arm>_<trial>.json with
      text, facts, tokens and seconds. Refuses to mix a second condition or arm into a RUN that has one.

A RUNROOT is a ShipLoop E2E run folder (it holds invocation.json and .shiploop-runs/*/run/state.md). The facts
block holds only what ShipLoop's scripts and the run's state.md recorded, never the arm, host, model or effort:
the judge must not see the condition (rubric-eval SPEC section 5). Run with `python3 -B`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

KINDS = ("system-test", "product-acceptance", "release-verify", "operations")
# What each outer kind's run record shows besides its own reruns: the stage whose reruns it relies on, and the
# earlier accepted results it reads (a subset of the Stage.reads in skills/shiploop/scripts/shiploop_stage_spec.py).
RELIES = {"system-test": (None, ("system-test-author",)),
          "product-acceptance": ("system-test", ("system-test",)),
          "release-verify": (None, ("release",)),
          "operations": ("release-verify", ("release", "release-verify"))}
TAIL_LINES, TAIL_CHARS = 6, 180


# ---------------------------------------------------------------- scrubbing

SECRET = [
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "<email>"),
    (re.compile(r"\b00D[A-Za-z0-9]{12,15}![A-Za-z0-9._]+"), "<session-token>"),
    (re.compile(r"(?i)\b(bearer|token|secret|password|passwd|api[_-]?key|sid|access_token)(\s*[=:]\s*|\s+)([^\s\"',;&]{8,})"), r"\1\2<redacted>"),
    (re.compile(r"\b(?:sk|xox[abp]|ghp|gho|github_pat)[-_][A-Za-z0-9_-]{16,}"), "<redacted>"),
]
# A long run of mixed-case letters and digits is a token; hex digests, ids and paths are kept (they are checkable).
LONG = re.compile(r"[A-Za-z0-9+=_-]{40,}")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _token(m: re.Match) -> str:
    w = m.group(0)
    mixed = sum(c.isupper() for c in w) >= 2 and sum(c.islower() for c in w) >= 2 and sum(c.isdigit() for c in w) >= 2
    return "<redacted>" if mixed else w


def scrub(text: str, prefixes: list[tuple[str, str]]) -> str:
    """Shorten the run folder's absolute paths and remove anything that looks like a credential or address."""
    text = ANSI.sub("", text or "")
    for long, short in prefixes:
        text = text.replace(long, short)
    for pat, rep in SECRET:
        text = pat.sub(rep, text)
    return LONG.sub(_token, text).replace(str(Path.home()), "~")


# ---------------------------------------------------------------- records

def block(path: Path) -> dict | None:
    """The JSON in a ShipLoop record's ```shiploop-state fence, or None."""
    try:
        m = re.search(r"```shiploop-state\n(.*?)\n```", path.read_text(errors="replace"), re.S)
        return json.loads(m.group(1)) if m else None
    except (OSError, ValueError):
        return None


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def git(worktree: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(worktree), *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def repo_for(worktree: Path, root: Path) -> Path | None:
    """The run's worktree if git still reads it, else the run's own checkout (after a workspace return)."""
    for d in (worktree, root / "work"):
        if d.exists() and git(d, "rev-parse", "--git-dir").strip():
            return d
    return None


def commits(worktree: Path | None, after: str | None, until: str) -> list[dict] | None:
    """Commits in the worktree with committer time in (after, until], newest first, with changed file names
    (only the newest when `after` is None); None when no repository is left to read."""
    if worktree is None:
        return None
    args = ["log", "--format=%x1e%h%x1f%cI%x1f%s", "--name-only", f"--until={until}"] + ([f"--since={after}"] if after else ["-1"])
    out = []
    for chunk in git(worktree, *args).split("\x1e")[1:]:
        head, *files = chunk.strip().split("\n")
        h, t, s = head.split("\x1f")
        t = iso(datetime.fromisoformat(t).timestamp())
        if after and parse_iso(t) <= parse_iso(after):
            continue
        out.append({"sha": h, "at": t, "subject": s, "files": [f for f in files if f.strip()]})
    return out


def commit_line(c: dict) -> str:
    files = ", ".join(c["files"][:8]) + (f" and {len(c['files']) - 8} more" if len(c["files"]) > 8 else "")
    return f"{c['sha']} at {c['at']}: \"{c['subject']}\" (files: {files or 'none'})"


def scalar(v) -> str:
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)


def render_items(value) -> list[str]:
    """A recorded field as lines, values verbatim: a dict as `key: value`, a list item by item."""
    if isinstance(value, dict):
        return [f"- {k}: {scalar(v)}" for k, v in value.items()]
    if isinstance(value, list):
        return ["- " + ("; ".join(f"{k}: {scalar(v)}" for k, v in x.items()) if isinstance(x, dict) else scalar(x)) for x in value]
    return [scalar(value)]


def render_result(result: dict) -> str:
    """A stage's accepted result as text: every field the model submitted, in a fixed order, values verbatim."""
    lines = [f"Headline: {result.get('headline', '')}", f"Outcome: {result.get('outcome', '')}", "", "Summary:", result.get("summary", "")]
    for key in sorted(k for k in result if k not in ("headline", "outcome", "summary")):
        value = result[key]
        if key == "delivery_assessment" and isinstance(value, dict):
            value = {k: v for k, v in value.items() if k != "contract_anchor"}
        lines += ["", key.replace("_", " ").capitalize() + ":"] + render_items(value)
    return "\n".join(lines).strip() + "\n"


def tail(text: str) -> str:
    rows = [r.strip() for r in (text or "").splitlines() if r.strip() and not set(r.strip()) <= set("─━═-=*▶ ")]
    return " | ".join(r[:TAIL_CHARS] for r in rows[-TAIL_LINES:])


def rerun_lines(run: Path, action: str) -> list[str]:
    """ShipLoop's own reruns of a stage's recorded commands (run/tests/<action>*.md), compact."""
    out, seen = [], {}
    for f in sorted(run.glob(f"tests/{action}*.md")):
        r = block(f)
        if not r or not isinstance(r.get("runs"), list):
            continue
        label = f.stem[len(action):].lstrip("-") or "record"
        head = (f"- ShipLoop record `{label}`, created {r.get('created_at', '?')}, disposition {r.get('disposition', '?')}, "
                f"passed {r.get('passed')}")
        sig = json.dumps([[x.get(k) for k in ("command", "exit", "status", "ids", "ids_missing", "counts")] for x in r["runs"]])
        if sig in seen:  # a rerun with the same commands and results is named, not repeated
            out.append(head + f": the same {len(r['runs'])} commands with the same exits, statuses and ids as `{seen[sig]}`")
            continue
        seen[sig] = label
        out.append(head + ":")
        for i, x in enumerate(r["runs"], 1):
            ids = x.get("ids") or []
            idtxt = (f"; expected ids {', '.join(ids)}; missing {', '.join(x.get('ids_missing') or []) or 'none'}" if ids else "")
            counts = f"; counts {json.dumps(x['counts'])}" if x.get("counts") else ""
            out.append(f"  {i}. `{x.get('command', '')}` exit {x.get('exit')}, status {x.get('status')}, {x.get('seconds')} s{idtxt}{counts}")
            t = tail(x.get("stdout", "")) or tail(x.get("stderr", ""))
            if t:
                out.append(f"     output tail: {t}")
    return out


def last_action(history: list[dict], before: int, stage: str) -> dict | None:
    for e in reversed(history[:before]):
        if e.get("stage") == stage:
            return e
    return None


# ---------------------------------------------------------------- collect

def collect(root: Path) -> list[dict]:
    """Every gradable artifact in one ShipLoop E2E run folder."""
    inv = json.loads((root / "invocation.json").read_text())
    case = inv.get("case") or root.name
    if case == "custom":  # older Grok runs named the case only in the folder
        case = next((c for c in ("battleship-scoring", "battleship", "checkers", "hello", "seat-reservations") if c in root.name), root.name)
    request = (root / "prompt.txt").read_text(errors="replace").strip() if (root / "prompt.txt").exists() else ""
    arts = []
    for state_md in sorted(root.glob(".shiploop-runs/*/run/state.md")):
        run, ws = state_md.parent, state_md.parent.parent
        worktree = ws / "worktree"
        prefixes = [(str(run) + "/", "run/"), (str(run), "run"), (str(worktree) + "/", "worktree/"), (str(worktree), "worktree"),
                    (str(ws) + "/", ""), (str(root) + "/", "")]
        s = block(state_md)
        if not s:
            continue
        tl = json.loads((run / "timeline.json").read_text()) if (run / "timeline.json").exists() else {}
        accepted = tl.get("accepted", {}) if isinstance(tl.get("accepted"), dict) else {}
        history = s.get("history", [])
        sc = lambda t: scrub(t, prefixes)
        for i, e in enumerate(history):
            if e.get("stage") not in KINDS:
                continue
            res = block(run / "results" / f"{e['action']}.md")
            at = accepted.get(e["action"])
            if not res or "result" not in res or not at:
                continue
            prev_at = next((accepted.get(x["action"]) for x in reversed(history[:i]) if accepted.get(x["action"])), None)
            facts = [f"Stage {e['stage']}, action {e['action']}, accepted {at}"
                     + (f"; the previous stage was accepted {prev_at}." if prev_at else ".")]
            repo = repo_for(worktree, root)
            last = commits(repo, None, at)
            facts.append("Last commit before this result was accepted: "
                         + ("not available (no repository left in the run folder)" if last is None else commit_line(last[0]) if last else "none"))
            during = commits(repo, prev_at, at) if prev_at else None
            if during is not None:
                facts.append("Commits made during this stage: " + ("none" if not during else ""))
                facts += [f"- {commit_line(c)}" for c in during]
            relied, reads = RELIES[e["stage"]]
            own = rerun_lines(run, e["action"])
            facts.append("ShipLoop reruns of this stage's recorded commands: " + ("none recorded" if not own else ""))
            facts += own
            if relied:
                src = last_action(history, i, relied)
                lines = rerun_lines(run, src["action"]) if src else []
                facts.append(f"ShipLoop reruns recorded at the latest {relied} stage: " + ("none recorded" if not lines else ""))
                facts += lines
            for st in reads:
                src = last_action(history, i, st)
                if src:
                    facts.append(f"Accepted {st} result ({src['action']}, accepted {accepted.get(src['action'], '?')}), summary as state.md records it: "
                                 + (src.get("summary") or ""))
            if e["stage"] == "product-acceptance" and request:
                facts.append("The run's request, verbatim: " + request)
            text = sc(render_result(res["result"]))
            arts.append({"id": f"{root.name}--{e['action'][4:12]}", "case": case, "kind": e["stage"], "slot": e["stage"],
                         "text": text, "facts": sc("\n".join(facts)), "seconds": round(parse_iso(at) - parse_iso(prev_at), 1) if prev_at else None,
                         "source": {"run": str(root), "state": str(state_md), "action": e["action"], "accepted": at}})
        arts += reviews(root, case, run, worktree, sc)
    for a in arts:
        a["words"], a["facts_words"] = len(a["text"].split()), len(a["facts"].split())
        a["sha"] = hashlib.sha256(a["text"].encode()).hexdigest()[:16]
    return arts


def reviews(root: Path, case: str, run: Path, worktree: Path, sc) -> list[dict]:
    """Improve review notes for pass 2 or later, from children whose per-pass records ShipLoop wrote (pass-<n>.json)."""
    out = []
    for child in sorted((worktree / ".shiploop-improve").glob("*/reviews")) if worktree.exists() else []:
        for note in sorted(child.glob("review-*.md")):
            n = int(re.fullmatch(r"review-(\d+)\.md", note.name).group(1)) if re.fullmatch(r"review-(\d+)\.md", note.name) else 0
            cur, prev = child / f"pass-{n}.json", child / f"pass-{n - 1}.json"
            if n < 2 or not cur.exists():
                continue
            p = json.loads(cur.read_text())
            stage = child.parent.name.rsplit("-", 1)[0]
            facts = [f"Improve child {child.parent.name} reviewing the accepted {stage} result; this note is pass {n}."]
            for q in sorted(child.glob("pass-*.json"), key=lambda x: int(re.sub(r"\D", "", x.stem) or 0)):
                r = json.loads(q.read_text())
                if r.get("pass", 0) <= n:
                    facts.append(f"- ShipLoop pass record {r.get('pass')}: label {r.get('label')}, tree changed {r.get('changed')}, "
                                 f"commit {r.get('commit') or 'none'}, tree {str(r.get('tree'))[:12]}, recorded {r.get('at')}")
            rep = child / f"report-{n}.json"
            if rep.exists():
                ev = json.loads(rep.read_text()).get("evidence", "")
                k = ev.find("ShipLoop facts:")
                if k >= 0:
                    facts.append(ev[k:].strip())
            pp = json.loads(prev.read_text()) if prev.exists() else {}
            repo = repo_for(worktree, root)
            during = commits(repo, pp.get("at"), p["at"]) if pp.get("at") else None
            if during is not None:
                facts.append(f"Commits between pass {n - 1} and pass {n}: " + ("none" if not during else ""))
                facts += [f"- {commit_line(c)}" for c in during]
            head = commits(repo, None, p["at"])
            facts.append(f"HEAD when pass {n} was recorded: "
                         + ("not available (no repository left in the run folder)" if head is None else commit_line(head[0]) if head else "none"))
            checks = child / "checks.md"
            if checks.exists():
                facts.append(f"checks.md last written {iso(checks.stat().st_mtime)}; review-{n}.md last written {iso(note.stat().st_mtime)}.")
            out.append({"id": f"{root.name}--{child.parent.name}-r{n}", "case": case, "kind": "improve-review",
                        "slot": f"review-{stage}", "text": sc(note.read_text(errors="replace")), "facts": sc("\n".join(facts)),
                        "seconds": round(parse_iso(p["at"]) - parse_iso(pp["at"]), 1) if pp.get("at") else None,
                        "source": {"run": str(root), "note": str(note), "pass": n, "recorded": p["at"]}})
    return out


# ---------------------------------------------------------------- place

def place(run_dir: Path, pool: list[dict], arm: str, condition: str, select: list[str] | None, suite: str,
          tokens: dict | None = None) -> dict:
    """Write RUN/manifest.json and RUN/out/<scenario>_<slot>_<arm>_<trial>.json for the selected artifacts.

    The trial number counts artifacts of one (scenario, slot) in pool order, so two arms' artifacts pair by
    their order within a case and slot. tokens maps an artifact id to {"input_tokens", "output_tokens"} and, optionally,
    "seconds", which then replaces the artifact's own stage or pass span (an experiment that decides on whole-run cost
    gives every artifact its run's totals: run_totals.py); an artifact without usage records None (left out of cost
    comparisons, never counted as zero)."""
    if "_" in arm or not arm:
        raise SystemExit(f"place: arm names cannot contain '_' ({arm!r})")
    run_dir.mkdir(parents=True, exist_ok=True); (run_dir / "out").mkdir(exist_ok=True)
    cond = {"model": condition, "tools": "", "imported": "shiploop-run import_run.py"}
    man_path = run_dir / "manifest.json"
    man = json.loads(man_path.read_text()) if man_path.exists() else {}
    if man.get("condition") and man["condition"] != cond:
        raise SystemExit(f"place: {run_dir} records condition {man['condition']}; refusing to mix in {cond} (SPEC section 5)")
    chosen = [a for a in pool if select is None or a["id"] in select]
    missing = sorted(set(select or []) - {a["id"] for a in chosen})
    if missing:
        raise SystemExit(f"place: not in the pool: {', '.join(missing)}")
    seen, written = {}, []
    for a in chosen:
        for bad in ("_",):
            if bad in a["case"] or bad in a["slot"]:
                raise SystemExit(f"place: case and slot names cannot contain '_' ({a['case']!r}, {a['slot']!r})")
        k = seen[(a["case"], a["slot"])] = seen.get((a["case"], a["slot"]), 0) + 1
        stem = f"{a['case']}_{a['slot']}_{arm}_{k}"
        u = (tokens or {}).get(a["id"], {})
        rec = {"model": condition, "text": a["text"], "facts": a["facts"], "attempts": 1,
               "input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),
               "seconds": u["seconds"] if u.get("seconds") is not None else (a.get("seconds") or 0.0),
               "artifact": {"id": a["id"], "kind": a["kind"], "sha": a["sha"], "words": a["words"], "facts_words": a["facts_words"]}}
        (run_dir / "out" / f"{stem}.json").write_text(json.dumps(rec, ensure_ascii=False) + "\n")
        written.append(stem)
    arms = man.get("arms", {})
    arms[arm] = {"sha": hashlib.sha256("".join(sorted(a["sha"] for a in chosen)).encode()).hexdigest()[:16],
                 "source": f"{len(chosen)} artifacts imported from ShipLoop run folders", "words": sum(a["words"] for a in chosen)}
    man.update({"suite": suite, "frame": "import", "reviews": False, "trials": max(seen.values(), default=0),
                "prompts": man.get("prompts", 0), "min_words": 1, "arms": arms, "condition": cond})
    man_path.write_text(json.dumps(man, indent=1) + "\n")
    return {"written": len(written), "stems": written}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect"); c.add_argument("roots", nargs="+"); c.add_argument("--out", required=True)
    p = sub.add_parser("place"); p.add_argument("run_dir"); p.add_argument("--pool", required=True)
    p.add_argument("--arm", required=True); p.add_argument("--condition", required=True, help="the subject's model spec, recorded once")
    p.add_argument("--select", help="file of artifact ids, one per line (default: the whole pool)")
    p.add_argument("--tokens", help="JSON file {artifact id: {input_tokens, output_tokens}} from the run's session usage")
    p.add_argument("--suite", default="shiploop-run")
    a = ap.parse_args(argv)
    if a.cmd == "collect":
        arts = [x for r in a.roots for x in collect(Path(r))]
        with open(a.out, "w") as f:
            for x in arts:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
        print(json.dumps({"artifacts": len(arts), "by_kind": {k: sum(x["kind"] == k for x in arts) for k in (*KINDS, "improve-review")}}))
    else:
        pool = [json.loads(line) for line in Path(a.pool).read_text().splitlines() if line.strip()]
        sel = [x.strip() for x in Path(a.select).read_text().split() if x.strip()] if a.select else None
        tok = json.loads(Path(a.tokens).read_text()) if a.tokens else None
        print(json.dumps(place(Path(a.run_dir), pool, a.arm, a.condition, sel, a.suite, tok)))


if __name__ == "__main__":
    sys.exit(main())
