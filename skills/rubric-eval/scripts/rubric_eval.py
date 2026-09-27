"""rubric-eval: run prompt arms over a rubric suite, grade blind, and decide with paired statistics.

Each function is one composable step with a file contract (see SPEC.md):
  call        one isolated headless model call (sonnet or grok)
  extract     the exact text of a prompt constant or file, with its hash
  build       prompts for every scenario-runtime cell and arm, plus a manifest
  run         the subject model over pending prompts, rerunning stubs
  judge       evidence-first grading of every finished output
  analyze     composites, paired bootstrap intervals, wins/losses and the ship decision
  reliability re-grade a sample and report agreement

Run folders hold everything an experiment produced; nothing is kept in memory
between steps, so any step can be rerun or resumed on its own.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import random
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

VAL = {"met": 1.0, "partial": 0.5, "missed": 0.0, "overbuilt": 0.0}
STUB_WORDS = 150
MODELS = ("sonnet", "grok")
NO_MCP = ["--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}']
GROK_MODEL, GROK_EFFORT = "grok-4.7", "medium"


# ---------------------------------------------------------------- model calls

def _grok_home() -> Path:
    """An isolated Grok home holding only the sign-in, so no plugins, skills or MCP servers load."""
    home = Path(os.environ.get("RUBRIC_EVAL_GROK_HOME") or Path(tempfile.gettempdir()) / "rubric-eval-grok-home")
    auth = Path.home() / ".grok" / "auth.json"
    (home / ".grok").mkdir(parents=True, exist_ok=True)
    link = home / ".grok" / "auth.json"
    if not link.exists():
        if not auth.is_file():
            raise SystemExit(f"rubric-eval: Grok is not signed in ({auth} is missing)")
        link.symlink_to(auth)
    return home


def call(model: str, prompt: str, *, timeout: int = 600) -> str:
    """Run one prompt on `model` with no tools and no MCP servers; return the text ('' on timeout or failure)."""
    if model not in MODELS:
        raise ValueError(f"call: model must be one of {MODELS}, got {model!r}")
    with tempfile.TemporaryDirectory(prefix="rubric-eval-") as cwd:
        try:
            if model == "sonnet":
                argv = ["claude", "-p", "--model", "sonnet", "--tools", "", *NO_MCP]
                return subprocess.run(argv, input=prompt, capture_output=True, text=True, timeout=timeout, cwd=cwd).stdout
            home = _grok_home()
            pf = Path(cwd) / "prompt.txt"
            pf.write_text(prompt)
            env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "GROK_CONFIG_DIR": str(home / ".grok"),
                   "XDG_CONFIG_HOME": str(home / ".config"), "XDG_DATA_HOME": str(home / ".local/share"),
                   "XDG_CACHE_HOME": str(home / ".cache"), "XDG_STATE_HOME": str(home / ".local/state"),
                   "GROK_CLAUDE_SKILLS_ENABLED": "false", "GROK_CURSOR_SKILLS_ENABLED": "false", "NO_COLOR": "1"}
            argv = ["grok", "--cwd", cwd, "--prompt-file", str(pf), "--verbatim", "--model", GROK_MODEL,
                    "--reasoning-effort", GROK_EFFORT, "--output-format", "json", "--no-auto-update",
                    "--disable-web-search", "--tools", "", "--max-turns", "3"]
            out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env).stdout
            return json.loads(out).get("text", "") if out.strip() else ""
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            return ""


def words(text: str) -> int:
    return len(text.split())


# ---------------------------------------------------------------- arms and suites

def extract(source: str | Path, symbol: str | None = None) -> str:
    """Return a Python string constant's exact value (by assignment name), or a whole file's text."""
    text = Path(source).read_text()
    if symbol is None:
        return text
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == symbol for t in node.targets):
            value = ast.literal_eval(node.value)
            if not isinstance(value, str):
                raise ValueError(f"extract: {symbol} in {source} is not a string constant")
            return value
    raise ValueError(f"extract: no string constant named {symbol} in {source}")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def load_suite(suite_dir: str | Path) -> dict:
    d = Path(suite_dir)
    suite = {"dir": str(d), "rubric": json.loads((d / "rubric.json").read_text()),
             "scenarios": json.loads((d / "scenarios.json").read_text()),
             "frames": {f.stem: f.read_text() for f in sorted((d / "frames").glob("*.txt"))}}
    for key in ("criteria", "groups", "guardrails", "anchors"):
        if key not in suite["rubric"]:
            raise ValueError(f"load_suite: rubric.json lacks {key!r}")
    return suite


def fill(template: str, **values: str) -> str:
    """Replace {name} tokens only (plans contain braces, so str.format is unsafe)."""
    for k, v in values.items():
        template = template.replace("{" + k + "}", v)
    return template


def cells(suite: dict, scenarios: list[str] | None = None, runtimes: list[str] | None = None):
    """Yield (scenario, runtime, ui) for every scenario-runtime cell, filtered if asked."""
    for s in suite["scenarios"]["scenarios"]:
        if scenarios and s["id"] not in scenarios:
            continue
        for rt in s["runtimes"] + s.get("runtimes_ext", []):
            if runtimes and rt not in runtimes:
                continue
            ui = s.get("ui") if rt in s.get("runtimes_ext", []) else None
            yield s, rt, ui


def request_text(s: dict, ui: str | None) -> str:
    return s["request"] + (f" Use {ui} for the UI." if ui else "")


def build(run_dir: str | Path, suite: dict, arms: dict[str, dict], *, frame: str = "plan", trials: int = 2,
          plans_from: str | Path | None = None, scenarios=None, runtimes=None) -> dict:
    """Write prompts/<cell>_<arm>_<trial>.txt for every cell, arm and trial, and manifest.json.

    `arms` maps an arm name to {"text": ..., "source": ...}. For the review frame, `plans_from`
    is a run folder whose finished outputs (one arm, named in arm["plans_arm"]) are the plans reviewed.
    """
    run = Path(run_dir); (run / "prompts").mkdir(parents=True, exist_ok=True)
    tpl = suite["frames"][frame]; n = 0
    for name, arm in arms.items():
        if "_" in name:
            raise ValueError(f"build: arm names cannot contain '_' ({name!r})")
    for s, rt, ui in cells(suite, scenarios, runtimes):
        env = suite["scenarios"]["runtimes"][rt]
        for name, arm in arms.items():
            for k in range(1, trials + 1):
                plan = ""
                if frame == "review":
                    src = Path(plans_from) / "out" / f"{s['id']}_{rt}_{arm['plans_arm']}_{k}.json"
                    if not src.exists():
                        continue
                    plan = json.loads(src.read_text())["text"]
                text = fill(tpl, request=request_text(s, ui), environment=env, arm=arm["text"], plan=plan)
                (run / "prompts" / f"{s['id']}_{rt}_{name}_{k}.txt").write_text(text); n += 1
    manifest = {"suite": suite["dir"], "frame": frame, "trials": trials, "prompts": n,
                "arms": {k: {"sha": sha(v["text"]), "source": v.get("source", ""), "words": words(v["text"]),
                             **({"plans_arm": v["plans_arm"]} if "plans_arm" in v else {})} for k, v in arms.items()}}
    (run / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def plan_text(output: str, frame: str) -> str:
    """The part of an output that is graded: the whole plan, or a review's revised plan."""
    if frame != "review":
        return output
    i = output.find("## Revised plan")
    return output[i:] if i >= 0 else ""


# ---------------------------------------------------------------- run

def run(run_dir: str | Path, model: str, *, workers: int = 8, attempts: int = 3) -> dict:
    """Run every prompt without a finished output; rerun a stub up to `attempts` times."""
    run_ = Path(run_dir); out = run_ / "out"; out.mkdir(exist_ok=True)
    frame = json.loads((run_ / "manifest.json").read_text())["frame"]

    def one(p: Path):
        dest = out / (p.stem + ".json")
        if dest.exists() and words(plan_text(json.loads(dest.read_text())["text"], frame)) >= STUB_WORDS:
            return "done"
        text = ""
        for _ in range(attempts):
            text = call(model, p.read_text())
            if words(plan_text(text, frame)) >= STUB_WORDS:
                dest.write_text(json.dumps({"model": model, "text": text}) + "\n"); return "ok"
        with open(run_ / "stubs.log", "a") as log:
            log.write(f"{p.stem}\t{words(text)} words\n")
        return "stub"

    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(one, sorted((run_ / "prompts").glob("*.txt"))))
    return {k: results.count(k) for k in ("done", "ok", "stub")}


# ---------------------------------------------------------------- judge

JUDGE = """You grade an architecture plan against a rubric. Judge what the plan ADOPTS, not what it mentions or rejects.
Runtime: {runtime}
Request: {request}
Expected tier: {tier} — {tierdef}
Overbuild note: {overbuild}

Grade anchors:
{anchors}

Criteria to grade:
{criteria}

For each criterion, first copy the shortest exact quote from the plan that decides the grade (or "none"/"na"), then give the grade that quote supports. Never grade met or partial without a quote.

Plan:
<<<
{plan}
>>>

Grade these criteria now: {ids}.
Return only JSON: {{"tier_chosen": one of {tiers}, "criteria": {{criterion id: {{"evidence": quote, "grade": grade}}}}, "overbuilt_items": [short strings], "platform_errors": [factually wrong claims about the runtime]}}
"""


def judge_prompt(suite: dict, sid: str, rt: str, plan: str) -> str:
    s = {x["id"]: x for x in suite["scenarios"]["scenarios"]}[sid]
    ext = rt in s.get("runtimes_ext", [])
    applies = s["applies"] + (s.get("applies_ui", []) if ext and s.get("ui") else [])
    R = suite["rubric"]; sc = suite["scenarios"]
    return fill(JUDGE, runtime=sc.get("runtime_names", {}).get(rt, rt), request=request_text(s, s.get("ui") if ext else None),
                tier=s["tier"], tierdef=sc["tiers"][s["tier"]], overbuild=s["overbuild"],
                anchors="\n".join(f"- {g}: {d}" for g, d in R["anchors"].items()),
                criteria="\n".join(f"{c} {R['criteria'][c][0]}: {R['criteria'][c][1]}" for c in applies),
                ids=", ".join(applies), tiers=json.dumps(list(sc["tiers"])), plan=plan).replace("{{", "{").replace("}}", "}")


def parse_verdict(output: str) -> dict | None:
    """Parse an evidence-first verdict; return it with a flat 'grades' map, or None if malformed."""
    m = re.search(r"\{.*\}", output or "", re.S)
    try:
        j = json.loads(m.group(0))
        j["grades"] = {c: v["grade"] for c, v in j["criteria"].items()}
        if not all(g in (*VAL, "na") for g in j["grades"].values()):
            return None
        return j
    except Exception:
        return None


def judge(run_dir: str | Path, suite: dict, *, model: str = "sonnet", workers: int = 10, attempts: int = 3,
          dest: str = "judge", only: list[str] | None = None) -> dict:
    """Grade every finished output not yet graded; log (never drop) outputs that cannot be graded."""
    run_ = Path(run_dir); jd = run_ / dest; jd.mkdir(exist_ok=True)
    frame = json.loads((run_ / "manifest.json").read_text())["frame"]
    todo = []
    for f in sorted((run_ / "out").glob("*.json")):
        if only is not None and f.stem not in only:
            continue
        d = jd / (f.stem + ".json")
        if d.exists():
            continue
        plan = plan_text(json.loads(f.read_text())["text"], frame)
        if words(plan) >= STUB_WORDS:
            todo.append((f.stem, plan, d))

    def one(job):
        stem, plan, d = job
        sid, rt = stem.split("_")[:2]
        p = judge_prompt(suite, sid, rt, plan)
        for _ in range(attempts):
            v = parse_verdict(call(model, p, timeout=300))
            if v:
                d.write_text(json.dumps(v, indent=1)); return True
        with open(jd / "failures.log", "a") as log:
            log.write(f"{stem}\n")
        return False

    with ThreadPoolExecutor(workers) as ex:
        ok = list(ex.map(one, todo))
    return {"graded": sum(ok), "failed": ok.count(False)}


# ---------------------------------------------------------------- analyze

def load_verdicts(run_dir: str | Path, dest: str = "judge") -> dict:
    return {f.stem: json.loads(f.read_text()) for f in sorted((Path(run_dir) / dest).glob("*.json"))}


def score(verdict: dict, crits=None) -> float | None:
    xs = [VAL[g] for c, g in verdict["grades"].items() if g in VAL and (crits is None or c in crits)]
    return sum(xs) / len(xs) if xs else None


def bootstrap(diffs: list[float], n: int = 4000, seed: int = 3) -> tuple[float, float, float]:
    rnd = random.Random(seed); m = len(diffs)
    means = sorted(sum(rnd.choice(diffs) for _ in range(m)) / m for _ in range(n))
    return sum(diffs) / m, means[int(0.025 * n)], means[int(0.975 * n)]


def paired(verdicts: dict, arm: str, baseline: str, crits=None) -> dict | None:
    """Paired comparison of `arm` against `baseline` over matching cell-trials."""
    by = {}
    for stem, v in verdicts.items():
        sid, rt, a, k = stem.split("_"); by.setdefault(a, {})[(sid, rt, k)] = v
    diffs, w, l = [], 0, 0
    for key, v in by.get(arm, {}).items():
        b = by.get(baseline, {}).get(key)
        if b is None:
            continue
        x, y = score(v, crits), score(b, crits)
        if x is None or y is None:
            continue
        diffs.append(x - y); w += x > y + 1e-9; l += y > x + 1e-9
    if not diffs:
        return None
    m, lo, hi = bootstrap(diffs)
    return {"mean": round(m, 4), "low": round(lo, 4), "high": round(hi, 4), "won": w, "lost": l, "n": len(diffs)}


def decide(comparison: dict, guardrails: list[str], margin: float = 0.02) -> dict:
    """Ship when the overall interval is above zero and no guardrail interval lies wholly below -margin."""
    overall = comparison.get("overall")
    reasons = []
    if not overall or overall["low"] <= 0:
        reasons.append("overall improvement not established (95% lower bound <= 0)")
    for g in guardrails:
        c = comparison.get(g)
        if c and c["high"] < -margin:
            reasons.append(f"guardrail {g} regressed (upper bound {c['high']:+.3f} < -{margin})")
    return {"ship": not reasons, "reasons": reasons}


def analyze(run_dir: str | Path, suite: dict, baseline: str, dest: str = "judge") -> dict:
    verdicts = load_verdicts(run_dir, dest)
    arms = sorted({s.split("_")[2] for s in verdicts})
    groups = {"overall": None, **suite["rubric"]["groups"]}
    sc = {x["id"]: x for x in suite["scenarios"]["scenarios"]}
    report = {"baseline": baseline, "arms": {}}
    for a in arms:
        vs = {s: v for s, v in verdicts.items() if s.split("_")[2] == a}
        comp = {}
        for g, cs in groups.items():
            xs = [x for x in (score(v, cs) for v in vs.values()) if x is not None]
            comp[g] = round(sum(xs) / len(xs), 4) if xs else None
        entry = {"plans": len(vs), "composites": comp,
                 "tier_matched": sum(v.get("tier_chosen") == sc[s.split("_")[0]]["tier"] for s, v in vs.items()),
                 "overbuilt_scope": sum(v["grades"].get(c) == "overbuilt" for v in vs.values() for c in ("P1", "P3")),
                 "platform_errors": sum(len(v.get("platform_errors") or []) for v in vs.values())}
        if a != baseline:
            cmp_ = {g: paired(verdicts, a, baseline, cs) for g, cs in groups.items()}
            entry["against_baseline"] = cmp_
            entry["decision"] = decide(cmp_, suite["rubric"]["guardrails"])
        report["arms"][a] = entry
    (Path(run_dir) / "analysis.json").write_text(json.dumps(report, indent=1) + "\n")
    return report


def reliability(run_dir: str | Path, suite: dict, n: int = 30, seed: int = 11, model: str = "sonnet") -> dict:
    """Re-grade a random sample and report grade agreement and per-plan score change."""
    run_ = Path(run_dir); first = load_verdicts(run_)
    sample = random.Random(seed).sample(sorted(first), min(n, len(first)))
    judge(run_, suite, model=model, dest="judge_regrade", only=sample)
    second = load_verdicts(run_, "judge_regrade")
    agree = tot = tier = 0; d = []
    for s in sample:
        if s not in second:
            continue
        a, b = first[s], second[s]; tier += a.get("tier_chosen") == b.get("tier_chosen")
        for c, g in a["grades"].items():
            if c in b["grades"]:
                tot += 1; agree += g == b["grades"][c]
        d.append(abs(score(a) - score(b)))
    return {"plans": len(d), "grade_agreement": round(agree / max(tot, 1), 3), "tier_agreement": f"{tier}/{len(d)}",
            "mean_score_change": round(sum(d) / max(len(d), 1), 4), "max_score_change": round(max(d, default=0), 4)}
