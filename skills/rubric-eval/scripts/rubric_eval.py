"""rubric-eval: run prompt arms over a rubric suite, grade blind, and decide with paired statistics.

Each function is one composable step with a file contract (see SPEC.md):
  call        one isolated headless model call (sonnet or grok)
  extract     the exact text of a prompt constant or file, with its hash
  build       prompts for every scenario-runtime cell and arm, plus a manifest
  run         the subject model over pending prompts, rerunning stubs
  judge       evidence-first grading of every finished output
  analyze     composites, paired intervals and tests, and the quality > tokens > time decision
  reliability re-grade a sample and report agreement (Cohen's kappa) and the judge's noise

Run folders hold everything an experiment produced; nothing is kept in memory
between steps, so any step can be rerun or resumed on its own.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import random
import re
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Analytic-rubric points per criterion; a plan scores the percentage of available points it earned (0-100).
VAL = {"met": 2, "partial": 1, "missed": 0, "overbuilt": 0}
JUDGES = Path(__file__).resolve().parents[1] / "references" / "judges.json"
STUB_WORDS = 150
MODELS = ("grok", "opus", "sonnet")
OPUS_MODEL, OPUS_EFFORT = "claude-opus-5-5", "medium"
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


def call_full(model: str, prompt: str, *, timeout: int = 600, tools: str = "") -> dict:
    """Run one prompt on `model` with no MCP servers, from an empty directory.

    Returns {"text", "input_tokens", "output_tokens", "seconds"}; text is '' on failure. Input tokens count
    cached and uncached prompt tokens; output tokens include reasoning. Seconds is wall-clock time.
    `tools` is "" (none) or "Read". A prompt that asks the model to check something (a review focus that says
    to run a command) needs a tool to reach for; with none, a model may announce a call and stop, a stub.
    Read from an empty directory lets it try, find nothing, and answer.
    """
    if tools not in ("", "Read"):
        raise ValueError(f"call: tools must be '' or 'Read', got {tools!r}")
    if model not in MODELS:
        raise ValueError(f"call: model must be one of {MODELS}, got {model!r}")
    rec = {"text": "", "input_tokens": 0, "output_tokens": 0, "seconds": 0.0}
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="rubric-eval-") as cwd:
        try:
            if model in ("sonnet", "opus"):
                pick = ["--model", "sonnet"] if model == "sonnet" else ["--model", OPUS_MODEL, "--effort", OPUS_EFFORT]
                argv = ["claude", "-p", *pick, "--output-format", "json", "--tools", tools, *NO_MCP] + (["--allowedTools", tools] if tools else [])
                out = subprocess.run(argv, input=prompt, capture_output=True, text=True, timeout=timeout, cwd=cwd).stdout
                d = json.loads(out) if out.strip() else {}
                u = d.get("usage") or {}
                rec.update(text=d.get("result", "") if not d.get("is_error") else "",
                           input_tokens=u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0),
                           output_tokens=u.get("output_tokens", 0))
            else:
                home = _grok_home()
                pf = Path(cwd) / "prompt.txt"
                pf.write_text(prompt)
                env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "GROK_CONFIG_DIR": str(home / ".grok"),
                       "XDG_CONFIG_HOME": str(home / ".config"), "XDG_DATA_HOME": str(home / ".local/share"),
                       "XDG_CACHE_HOME": str(home / ".cache"), "XDG_STATE_HOME": str(home / ".local/state"),
                       "GROK_CLAUDE_SKILLS_ENABLED": "false", "GROK_CURSOR_SKILLS_ENABLED": "false", "NO_COLOR": "1"}
                argv = ["grok", "--cwd", cwd, "--prompt-file", str(pf), "--verbatim", "--model", GROK_MODEL,
                        "--reasoning-effort", GROK_EFFORT, "--output-format", "json", "--no-auto-update",
                        "--disable-web-search"]
                # Grok reads `--tools ""` as no restriction (every tool, shell included), so name an allowlist:
                # todo_write touches no files. With tools, list_dir alone lets it look at the empty directory,
                # find nothing and answer; it cannot read files, so no run can see another's prompt.
                argv += ["--tools", "list_dir" if tools else "todo_write", "--disallowed-tools", "search_tool,use_tool", "--max-turns", "6"]
                out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env).stdout
                d = json.loads(out) if out.strip() else {}
                u = d.get("usage") or {}
                rec.update(text=d.get("text", ""),
                           input_tokens=u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0),
                           output_tokens=u.get("output_tokens", 0))  # Grok's output_tokens already include reasoning
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            pass
    rec["seconds"] = round(time.monotonic() - start, 1)
    return rec


def call(model: str, prompt: str, *, timeout: int = 600, tools: str = "") -> str:
    """The text of one isolated call ('' on failure); see call_full for usage and time."""
    return call_full(model, prompt, timeout=timeout, tools=tools)["text"]


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
          plans_from: str | Path | None = None, scenarios=None, runtimes=None, input_arm: str | None = None) -> dict:
    """Write prompts/<cell>_<arm>_<trial>.txt for every cell, arm and trial, and manifest.json.

    `arms` maps an arm name to {"text": ..., "source": ...}. For the review frame, `plans_from`
    is a run folder whose finished outputs (one arm, named in arm["plans_arm"]) are the plans reviewed.
    `input_arm` (review frames) also writes each input plan, unreviewed, as output `<cell>_<input_arm>_<k>`:
    the no-review baseline, marked "role": "input" and costing nothing this round.
    """
    run = Path(run_dir); (run / "prompts").mkdir(parents=True, exist_ok=True)
    tpl = suite["frames"][frame]; n = 0
    reviews = "{plan}" in tpl  # a review frame is any frame that wraps an existing plan
    for name, arm in arms.items():
        if "_" in name:
            raise ValueError(f"build: arm names cannot contain '_' ({name!r})")
    for s, rt, ui in cells(suite, scenarios, runtimes):
        env = suite["scenarios"]["runtimes"][rt]
        for name, arm in arms.items():
            for k in range(1, trials + 1):
                plan = ""
                if reviews:
                    src = Path(plans_from) / "out" / f"{s['id']}_{rt}_{arm['plans_arm']}_{k}.json"
                    if not src.exists():
                        continue
                    plan = json.loads(src.read_text())["text"]
                    if input_arm:
                        (run / "out").mkdir(exist_ok=True)
                        (run / "out" / f"{s['id']}_{rt}_{input_arm}_{k}.json").write_text(json.dumps(
                            {"model": "input", "text": "## Findings\nNone\n\n## Revised plan\n" + plan}) + "\n")
                text = fill(tpl, request=request_text(s, ui), environment=env, arm=arm["text"], plan=plan)
                (run / "prompts" / f"{s['id']}_{rt}_{name}_{k}.txt").write_text(text); n += 1
    if input_arm and not reviews:
        raise ValueError("build: an input arm is only for review frames")
    if input_arm and "_" in input_arm:
        raise ValueError(f"build: arm names cannot contain '_' ({input_arm!r})")
    if reviews and n == 0:
        raise ValueError(f"build: frame {frame!r} reviews plans but none were found in {plans_from}")
    manifest = {"suite": suite["dir"], "frame": frame, "reviews": reviews, "trials": trials, "prompts": n,
                "arms": {k: {"sha": sha(v["text"]), "source": v.get("source", ""), "words": words(v["text"]),
                             **({"plans_arm": v["plans_arm"]} if "plans_arm" in v else {})} for k, v in arms.items()}}
    if input_arm:
        pa = next(iter(arms.values()))["plans_arm"]
        manifest["arms"][input_arm] = {"sha": "", "source": f"the unreviewed {pa} plan", "words": 0, "plans_arm": pa, "role": "input"}
    prev = run / "manifest.json"
    if prev.exists() and "condition" in json.loads(prev.read_text()):
        manifest["condition"] = json.loads(prev.read_text())["condition"]  # a rebuild keeps the recorded condition
    (run / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def plan_text(output: str, reviews: bool) -> str:
    """The part of an output that is graded: the whole plan, or a review's revised plan."""
    if not reviews:
        return output
    i = output.find("## Revised plan")
    return output[i:] if i >= 0 else ""


# ---------------------------------------------------------------- run

def run(run_dir: str | Path, model: str, *, workers: int = 8, attempts: int = 3, tools: str = "") -> dict:
    """Run every prompt without a finished output; rerun a stub up to `attempts` times."""
    run_ = Path(run_dir); out = run_ / "out"; out.mkdir(exist_ok=True)
    reviews = json.loads((run_ / "manifest.json").read_text()).get("reviews", False)

    def one(p: Path):
        dest = out / (p.stem + ".json")
        if dest.exists() and words(plan_text(json.loads(dest.read_text())["text"], reviews)) >= STUB_WORDS:
            return "done"
        text = ""; used = {"input_tokens": 0, "output_tokens": 0, "seconds": 0.0}
        for n in range(1, attempts + 1):
            r = call_full(model, p.read_text(), tools=tools); text = r["text"]
            for k in used:  # stub reruns are real cost, so usage sums every attempt
                used[k] += r[k]
            if words(plan_text(text, reviews)) >= STUB_WORDS:
                used["seconds"] = round(used["seconds"], 1)
                dest.write_text(json.dumps({"model": model, "text": text, "attempts": n, **used}) + "\n"); return "ok"
        with open(run_ / "stubs.log", "a") as log:
            log.write(f"{p.stem}\t{words(text)} words\n")
        return "stub"

    man_path = run_ / "manifest.json"; man = json.loads(man_path.read_text())
    prev = man.get("condition")
    cond = {"model": model, "tools": tools}
    if prev and prev != cond:
        raise SystemExit(f"run: this run folder was run with {prev}; refusing to mix in {cond} (SPEC section 5)")
    man["condition"] = cond; man_path.write_text(json.dumps(man, indent=1) + "\n")
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


def _norm(s: str) -> str:
    """Lower case, with whitespace and markdown punctuation collapsed, for quote matching."""
    return re.sub(r"[\s*_`#>|-]+", " ", s.lower()).strip()


def quote_found(quote: str, plan: str) -> bool:
    """True when every fragment of the quote (split at ellipses) appears in the plan, after normalising."""
    frags = [f for f in re.split(r"\.\.\.|\u2026", quote or "") if len(_norm(f)) >= 4]
    p = _norm(plan)
    return bool(frags) and all(_norm(f) in p for f in frags)


def verify_quotes(verdict: dict, plan: str) -> dict:
    """Quote check (judge v2 + check): a met or partial grade whose quote is not in the plan drops one level.

    The judge must quote before it grades; a quote the plan does not contain is evidence the grade is not
    supported by the plan (it credits what the plan never says). Records the criteria it changed.
    """
    changed = []
    for c, e in verdict.get("criteria", {}).items():
        g = verdict["grades"].get(c)
        if g in ("met", "partial") and not quote_found(str(e.get("evidence", "")), plan):
            verdict["grades"][c] = "partial" if g == "met" else "missed"; changed.append(c)
    verdict["quote_check"] = {"unverified": changed}
    return verdict


def judge(run_dir: str | Path, suite: dict, *, model: str = "opus", workers: int = 10, attempts: int = 3,
          dest: str = "judge", only: list[str] | None = None) -> dict:
    """Grade every finished output not yet graded; log (never drop) outputs that cannot be graded."""
    run_ = Path(run_dir); jd = run_ / dest; jd.mkdir(exist_ok=True)
    reviews = json.loads((run_ / "manifest.json").read_text()).get("reviews", False)
    todo = []
    for f in sorted((run_ / "out").glob("*.json")):
        if only is not None and f.stem not in only:
            continue
        d = jd / (f.stem + ".json")
        if d.exists():
            continue
        plan = plan_text(json.loads(f.read_text())["text"], reviews)
        if words(plan) >= STUB_WORDS:
            todo.append((f.stem, plan, d))

    def one(job):
        stem, plan, d = job
        sid, rt = stem.split("_")[:2]
        p = judge_prompt(suite, sid, rt, plan)
        for _ in range(attempts):
            # Grok at medium effort took about 6.5 minutes per rubric grade in round 4; give it room.
            v = parse_verdict(call(model, p, timeout=900 if model == "grok" else 300))
            if v:
                v = verify_quotes(v, plan)
                v["judge_model"] = model  # a run's verdicts must come from one judge (checked by analyze)
                d.write_text(json.dumps(v, indent=1)); return True
        with open(jd / "failures.log", "a") as log:
            log.write(f"{stem}\n")
        return False

    with ThreadPoolExecutor(workers) as ex:
        ok = list(ex.map(one, todo))
    return {"graded": sum(ok), "failed": ok.count(False)}


def recheck(run_dir: str | Path, src: str = "judge", dest: str | None = None) -> dict:
    """Apply the quote check to verdicts graded without it; write them to `dest` (default <src>_qc)."""
    run_ = Path(run_dir); dest = dest or f"{src}_qc"; out = run_ / dest; out.mkdir(exist_ok=True)
    reviews = json.loads((run_ / "manifest.json").read_text()).get("reviews", False)
    n = changed = 0
    for stem, v in load_verdicts(run_, src).items():
        if "quote_check" in v:
            raise SystemExit(f"recheck: {src}/{stem} already carries the quote check")
        plan = plan_text(json.loads((run_ / "out" / f"{stem}.json").read_text())["text"], reviews)
        v = verify_quotes(v, plan); n += 1; changed += len(v["quote_check"]["unverified"])
        (out / f"{stem}.json").write_text(json.dumps(v, indent=1))
    return {"verdicts": n, "grades_lowered": changed, "dest": dest}


# ---------------------------------------------------------------- analyze

def load_verdicts(run_dir: str | Path, dest: str = "judge") -> dict:
    return {f.stem: json.loads(f.read_text()) for f in sorted((Path(run_dir) / dest).glob("*.json"))}


def score(verdict: dict, crits=None) -> float | None:
    """Percentage of available rubric points earned (met 2, partial 1, missed or overbuilt 0), 0-100."""
    xs = [VAL[g] for c, g in verdict["grades"].items() if g in VAL and (crits is None or c in crits)]
    return 100 * sum(xs) / (2 * len(xs)) if xs else None


def bootstrap(diffs: list[float], n: int = 4000, seed: int = 3, clusters: list[str] | None = None) -> tuple[float, float, float]:
    """Mean and 95% percentile-bootstrap interval; with `clusters`, resample whole clusters (e.g. scenarios)."""
    rnd = random.Random(seed); m = len(diffs)
    if not clusters:
        means = sorted(sum(rnd.choice(diffs) for _ in range(m)) / m for _ in range(n))
        return sum(diffs) / m, means[int(0.025 * n)], means[int(0.975 * n)]
    groups: dict[str, list[float]] = {}
    for d, c in zip(diffs, clusters):
        groups.setdefault(c, []).append(d)
    keys = list(groups); means = []
    for _ in range(n):
        pick = [x for k in (rnd.choice(keys) for _ in keys) for x in groups[k]]
        means.append(sum(pick) / len(pick))
    means.sort()
    return sum(diffs) / m, means[int(0.025 * n)], means[int(0.975 * n)]


def wilcoxon(diffs: list[float]) -> float | None:
    """Two-sided p of the Wilcoxon signed-rank test (normal approximation, tie-corrected; zeros dropped)."""
    xs = [d for d in diffs if abs(d) > 1e-9]
    n = len(xs)
    if n < 6:
        return None
    order = sorted(range(n), key=lambda i: abs(xs[i])); ranks = [0.0] * n; ties = 0.0; i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(abs(xs[order[j + 1]]) - abs(xs[order[i]])) < 1e-9:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        ties += (j - i + 1) ** 3 - (j - i + 1); i = j + 1
    w = sum(r for r, x in zip(ranks, xs) if x > 0)
    mu = n * (n + 1) / 4; sd = math.sqrt(n * (n + 1) * (2 * n + 1) / 24 - ties / 48)
    z = (w - mu) / sd if sd else 0.0
    return round(math.erfc(abs(z) / math.sqrt(2)), 4)


def paired_values(values: dict[str, float], arm: str, baseline: str, cluster: str | None = None,
                  baseline_zero: bool = False) -> dict | None:
    """Paired comparison of any per-output value (score, tokens, seconds) of `arm` against `baseline`.

    Stems are <scenario>_<runtime>_<arm>_<trial>. Reports the mean difference, a 95% bootstrap interval
    (whole scenarios resampled when cluster="scenario"), cells won and lost (higher value), and the
    Wilcoxon signed-rank p over per-scenario mean differences (the independent units).
    baseline_zero: the baseline is an input that costs nothing this round (the unreviewed plan).
    """
    by = {}
    for stem, x in values.items():
        sid, rt, a, k = stem.split("_"); by.setdefault(a, {})[(sid, rt, k)] = x
    diffs, keys, w, l = [], [], 0, 0
    for key, x in by.get(arm, {}).items():
        y = 0.0 if baseline_zero else by.get(baseline, {}).get(key)
        if x is None or y is None:
            continue
        diffs.append(x - y); keys.append(key[0]); w += x > y + 1e-9; l += y > x + 1e-9
    if not diffs:
        return None
    m, lo, hi = bootstrap(diffs, clusters=keys if cluster == "scenario" else None)
    per = {}
    for d, k in zip(diffs, keys):
        per.setdefault(k, []).append(d)
    base = [y for y in (by.get(baseline, {}).values() if not baseline_zero else []) if y is not None]
    return {"mean": round(m, 4), "low": round(lo, 4), "high": round(hi, 4), "won": w, "lost": l, "n": len(diffs),
            "scenarios": len(per), "wilcoxon_p": wilcoxon([sum(v) / len(v) for v in per.values()]),
            **({"baseline_mean": round(sum(base) / len(base), 4)} if base else {})}


def paired(verdicts: dict, arm: str, baseline: str, crits=None, cluster: str | None = None) -> dict | None:
    """Paired score comparison (percentage points) over matching cell-trials; see paired_values."""
    return paired_values({s: score(v, crits) for s, v in verdicts.items()}, arm, baseline, cluster)


def two_proportion_p(x1: int, n1: int, x2: int, n2: int) -> float | None:
    """Two-sided p of the pooled two-proportion z-test."""
    if not n1 or not n2:
        return None
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return 1.0 if se == 0 else round(math.erfc(abs(x1 / n1 - x2 / n2) / se / math.sqrt(2)), 4)


def kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Linear-weighted Cohen's kappa over ordinal grades (missed/overbuilt < partial < met); na pairs dropped."""
    lv = {"missed": 0, "overbuilt": 0, "partial": 1, "met": 2}
    xs = [(lv[a], lv[b]) for a, b in pairs if a in lv and b in lv]
    if not xs:
        return None
    n = len(xs); k = 3
    w = lambda i, j: 1 - abs(i - j) / (k - 1)
    po = sum(w(a, b) for a, b in xs) / n
    ra = [sum(a == i for a, _ in xs) / n for i in range(k)]; rb = [sum(b == i for _, b in xs) / n for i in range(k)]
    pe = sum(w(i, j) * ra[i] * rb[j] for i in range(k) for j in range(k))
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def landis_koch(k: float | None) -> str:
    """The Landis and Koch (1977) band for a kappa."""
    if k is None:
        return "n/a"
    for bound, name in ((0, "poor"), (0.2, "slight"), (0.4, "fair"), (0.6, "moderate"), (0.8, "substantial")):
        if k <= bound:
            return name
    return "almost perfect"


def judge_noise(model: str) -> float | None:
    """The judge's measured test-retest noise: mean absolute per-plan score change (points) on re-grading."""
    try:
        return json.loads(JUDGES.read_text())[model]["noise_points"]
    except (OSError, KeyError, ValueError):
        return None


MIN_SCENARIOS = 8
ALPHA = 0.05


def _efficiency(c: dict | None, what: str):
    """Which side a paired cost comparison favours: 'arm' (costs less), 'baseline', or None (no difference)."""
    if not c:
        return None, f"{what}: not recorded for both arms"
    if c["high"] < 0:
        return "arm", f"{what}: arm uses less ({c['mean']:+.1f} per output, 95% [{c['low']:+.1f}, {c['high']:+.1f}])"
    if c["low"] > 0:
        return "baseline", f"{what}: arm uses more ({c['mean']:+.1f} per output, 95% [{c['low']:+.1f}, {c['high']:+.1f}])"
    return None, f"{what}: no difference (95% [{c['low']:+.1f}, {c['high']:+.1f}] includes 0)"


def decide(comparison: dict, guardrails: list[str], noise: float | None, *, scenarios: int | None = None,
           checks: list[str] | None = None, tokens: dict | None = None, seconds: dict | None = None) -> dict:
    """The SPEC section 8 rule: quality first, then tokens, then time.

    comparison: paired score comparisons (points) by group, "overall" required. noise: the judge's measured
    test-retest noise in points, the smallest difference this judge can tell apart. checks: blocking problems
    found elsewhere (conditions, significant rises in overbuilding or platform errors, stub or na rates).

    1. Quality. The arm is better when the overall 95% interval lies above 0 and the Wilcoxon signed-rank test
       over scenarios agrees (p < ALPHA); worse when both show it below 0; equivalent when the interval lies
       within +/- noise. Otherwise the result is inconclusive. (A percentile bootstrap over few clusters runs
       narrow, so the rank test must agree before a difference counts.)
    2. Tokens, only when quality is equivalent: the side whose paired token interval shows it uses fewer wins.
    3. Time, only when tokens show no difference: likewise for wall-clock seconds.
    A tie at every level keeps the baseline (a change must earn its place). Guardrail groups and the checks
    block the arm from winning at any level.
    """
    reasons, blockers = [], list(checks or [])
    overall = comparison.get("overall")
    if noise is None:
        blockers.append("the judge has no measured noise (run reliability and record it in references/judges.json)")
    if scenarios is not None and scenarios < MIN_SCENARIOS:
        blockers.append(f"only {scenarios} scenarios compared (minimum {MIN_SCENARIOS})")
    for g in guardrails:
        c = comparison.get(g)
        if not c:
            blockers.append(f"guardrail {g} has no comparison (no applicable criteria graded)")
        elif c["high"] < 0:
            blockers.append(f"guardrail {g} regressed (95% interval wholly below zero)")
        elif noise is not None and c["mean"] < -noise:
            blockers.append(f"guardrail {g} mean {c['mean']:+.1f} points is worse than the judge's noise ({noise})")
    if not overall:
        return {"winner": None, "decided_by": None, "ship": False, "reasons": ["no overall comparison"] + blockers}
    p = overall.get("wilcoxon_p")
    q = f"quality {overall['mean']:+.1f} points, 95% [{overall['low']:+.1f}, {overall['high']:+.1f}], Wilcoxon p={p}"
    agrees = p is not None and p < ALPHA
    winner = decided = None
    if overall["low"] > 0 and agrees:
        winner, decided = "arm", "quality"; reasons.append(q + ": arm better")
    elif overall["high"] < 0 and agrees:
        winner, decided = "baseline", "quality"; reasons.append(q + ": arm worse")
    elif noise is not None and -noise <= overall["low"] and overall["high"] <= noise:
        reasons.append(q + f": equivalent (within the judge's noise, +/-{noise})")
        for what, c in (("tokens", tokens), ("time", seconds)):
            side, why = _efficiency(c, what); reasons.append(why)
            if side:
                winner, decided = side, what; break
        if not winner:
            winner, decided = "baseline", "tie"; reasons.append("tie at every level: the baseline stays")
    else:
        reasons.append(q + ": inconclusive (neither above 0 nor within the judge's noise); add scenarios or trials")
    if winner == "arm" and blockers:
        reasons.append("the arm cannot win while any check below fails")
        winner = None
    return {"winner": winner, "decided_by": decided if winner else None, "ship": winner == "arm",
            "reasons": reasons + blockers}


def check_condition(run_dir: str | Path, baseline: str) -> list[str]:
    """Problems that void a comparison (SPEC section 5): arms not run under one recorded condition."""
    man = json.loads((Path(run_dir) / "manifest.json").read_text())
    problems = []
    if "condition" not in man:
        problems.append("manifest records no run condition (model, tools); rerun with this version of `run`")
    for name, arm in man.get("arms", {}).items():
        if arm.get("role") == "input" and name != baseline:
            problems.append(f"arm {name} is an input (not run this round) but is not the baseline")
    return problems


def usage(run_dir: str | Path) -> dict[str, dict]:
    """Per-output tokens (input + output) and seconds recorded by `run`; outputs without usage are omitted."""
    out = {}
    for f in (Path(run_dir) / "out").glob("*.json"):
        d = json.loads(f.read_text())
        if "seconds" in d:
            out[f.stem] = {"tokens": d.get("input_tokens", 0) + d.get("output_tokens", 0), "seconds": d["seconds"]}
    return out


def analyze(run_dir: str | Path, suite: dict, baseline: str, dest: str = "judge", cluster: str | None = "scenario",
            noise: float | None = None) -> dict:
    """Composites, paired comparisons and the quality > tokens > time decision for every arm against `baseline`."""
    verdicts = load_verdicts(run_dir, dest)
    run_ = Path(run_dir)
    man = json.loads((run_ / "manifest.json").read_text())
    base_is_input = man.get("arms", {}).get(baseline, {}).get("role") == "input"
    stubs = {}
    if (run_ / "stubs.log").exists():
        for line in (run_ / "stubs.log").read_text().splitlines():
            stubs.setdefault(line.split("_")[2], set()).add(line.split("\t")[0])
    arms = sorted({s.split("_")[2] for s in verdicts}, key=lambda a: (a != baseline, a))
    groups = {"overall": None, **suite["rubric"]["groups"]}
    sc = {x["id"]: x for x in suite["scenarios"]["scenarios"]}
    problems = check_condition(run_dir, baseline)
    judges = {v["judge_model"] for v in verdicts.values() if v.get("judge_model")}
    if len(judges) > 1:
        problems.append(f"verdicts come from more than one judge {sorted(judges)}; a round keeps one judge")
    checked = {"quote_check" in v for v in verdicts.values()}
    if len(checked) > 1:
        problems.append("some verdicts carry the quote check and some do not; re-grade or re-check the round")
    if noise is None and len(judges) == 1:
        noise = judge_noise(next(iter(judges)))
    use = usage(run_dir)
    tokens = {s: u["tokens"] for s, u in use.items()}; secs = {s: u["seconds"] for s, u in use.items()}
    per_plan = {"overbuilt scope grades": {s: sum(v["grades"].get(c) == "overbuilt" for c in ("P1", "P3")) for s, v in verdicts.items()},
                "platform errors": {s: len(v.get("platform_errors") or []) for s, v in verdicts.items()}}
    report = {"baseline": baseline, "judge_dir": dest, "judges": sorted(judges), "judge_noise_points": noise,
              "scale": "percentage of rubric points (met 2, partial 1, missed or overbuilt 0)",
              "cluster": cluster or "cell", "condition_problems": problems, "arms": {}}
    prompts = {}
    for f in (run_ / "prompts").glob("*.txt"):
        prompts[f.stem.split("_")[2]] = prompts.get(f.stem.split("_")[2], 0) + 1
    for a in arms:
        vs = {s: v for s, v in verdicts.items() if s.split("_")[2] == a}
        comp = {}
        for g, cs in groups.items():
            xs = [x for x in (score(v, cs) for v in vs.values()) if x is not None]
            comp[g] = round(sum(xs) / len(xs), 2) if xs else None
        na = sum(g == "na" for v in vs.values() for g in v["grades"].values())
        graded = sum(len(v["grades"]) for v in vs.values())
        mine = [u for s, u in use.items() if s.split("_")[2] == a]
        entry = {"plans": len(vs), "composites": comp, "stubs": len(stubs.get(a, ())), "prompts": prompts.get(a, 0),
                 "na": na, "graded": graded, "na_rate": round(na / max(graded, 1), 3),
                 "tier_matched": sum(v.get("tier_chosen") == sc[s.split("_")[0]]["tier"] for s, v in vs.items()),
                 "overbuilt_scope": sum(per_plan["overbuilt scope grades"][s] for s in vs),
                 "platform_errors": sum(per_plan["platform errors"][s] for s in vs),
                 **({"mean_tokens": round(sum(u["tokens"] for u in mine) / len(mine)),
                     "mean_seconds": round(sum(u["seconds"] for u in mine) / len(mine), 1)} if mine else {})}
        if a != baseline:
            b = report["arms"].get(baseline) or {}
            cmp_ = {g: paired(verdicts, a, baseline, cs, cluster) for g, cs in groups.items()}
            entry["against_baseline"] = cmp_
            checks = list(problems)
            for what, vals in per_plan.items():  # a significant rise blocks the arm
                c = paired_values(vals, a, baseline, cluster)
                if c and c["low"] > 0:
                    checks.append(f"{what} rose significantly ({c['mean']:+.2f} per plan, 95% [{c['low']:+.2f}, {c['high']:+.2f}])")
            for what, x1, n1, x2, n2 in (("stub", entry["stubs"], entry["prompts"], b.get("stubs", 0), b.get("prompts", 0)),
                                         ("na", na, graded, b.get("na", 0), b.get("graded", 0))):
                pv = None if base_is_input and what == "stub" else two_proportion_p(x1, n1, x2, n2)
                if pv is not None and pv < ALPHA:
                    checks.append(f"{what} rates differ between arms (two-proportion z-test p={pv})")
            tok = paired_values(tokens, a, baseline, cluster, baseline_zero=base_is_input)
            sec = paired_values(secs, a, baseline, cluster, baseline_zero=base_is_input)
            entry["cost_against_baseline"] = {"tokens": tok, "seconds": sec}
            entry["decision"] = decide(cmp_, suite["rubric"]["guardrails"], noise, checks=checks, tokens=tok, seconds=sec,
                                       scenarios=len({s.split("_")[0] for s in vs}))
        report["arms"][a] = entry
    name = "analysis" + ("" if dest == "judge" else "_" + dest) + ("" if not cluster else "_" + cluster)
    (Path(run_dir) / f"{name}.json").write_text(json.dumps(report, indent=1) + "\n")
    return report


def reliability(run_dir: str | Path, suite: dict, n: int = 30, seed: int = 11, model: str = "opus",
                first_dest: str = "judge", second_dest: str = "judge_regrade") -> dict:
    """Re-grade a random sample with the same judge; report Cohen's kappa and the judge's noise.

    noise_points (mean absolute per-plan score change) is the judge's test-retest noise: record it in
    references/judges.json, where `analyze` reads it as the equivalence bound.
    """
    run_ = Path(run_dir); first = load_verdicts(run_, first_dest)
    sample = random.Random(seed).sample(sorted(first), min(n, len(first)))
    judge(run_, suite, model=model, dest=second_dest, only=sample)
    second = load_verdicts(run_, second_dest)
    return agreement(first, second, sample)


def agreement(first: dict, second: dict, sample=None) -> dict:
    """Grade agreement between two sets of verdicts on the same plans: kappa, its band, and score change."""
    pairs, tier, d = [], 0, []
    for s in (sample or sorted(first)):
        if s not in first or s not in second:
            continue
        a, b = first[s], second[s]; tier += a.get("tier_chosen") == b.get("tier_chosen")
        pairs += [(g, b["grades"][c]) for c, g in a["grades"].items() if c in b["grades"]]
        x, y = score(a), score(b)
        if x is not None and y is not None:
            d.append(abs(x - y))
    k = kappa(pairs)
    return {"plans": len(d), "kappa": k, "band": landis_koch(k),
            "exact_agreement": round(sum(x == y for x, y in pairs) / max(len(pairs), 1), 3),
            "tier_agreement": f"{tier}/{len(d)}", "noise_points": round(sum(d) / max(len(d), 1), 2),
            "max_change_points": round(max(d, default=0), 2)}


# ---------------------------------------------------------------- diff check (review experiments)

DIFF = """You compare an original plan with the same plan after a review, for the request below. Count only real changes between them.
Request: {request}

Return only JSON with integer counts and one short example string for each nonzero count:
{{"removed_required": n, "removed_required_examples": [...],
 "added_unrequested": n, "added_unrequested_examples": [...],
 "contradictions": n, "contradictions_examples": [...],
 "invented_numbers": n, "invented_numbers_examples": [...]}}
Definitions: removed_required = something the request needs that the original had and the revision removed; added_unrequested = a feature, store, service, sign-in, channel, job or policy the revision added that the request does not need; contradictions = pairs of requirements in the revision that cannot both hold; invented_numbers = a numeric limit, quota, retention period or threshold the revision introduced with no source in the request and no cited documentation.

Original plan:
<<<
{original}
>>>

Revised plan:
<<<
{revised}
>>>
"""
DIFF_KEYS = ("removed_required", "added_unrequested", "contradictions", "invented_numbers")


def parse_diff(output: str) -> dict | None:
    m = re.search(r"\{.*\}", output or "", re.S)
    try:
        j = json.loads(m.group(0))
        return j if all(isinstance(j.get(k), int) and j[k] >= 0 for k in DIFF_KEYS) else None
    except Exception:
        return None


def diffcheck(run_dir: str | Path, suite: dict, plans_from: str | Path, *, model: str = "sonnet", workers: int = 10) -> dict:
    """For a review run, count what each review removed, added, contradicted or invented against its input plan."""
    run_ = Path(run_dir); dd = run_ / "diff"; dd.mkdir(exist_ok=True)
    man = json.loads((run_ / "manifest.json").read_text())
    sc = {x["id"]: x for x in suite["scenarios"]["scenarios"]}
    todo = []
    for f in sorted((run_ / "out").glob("*.json")):
        d = dd / (f.stem + ".json")
        if d.exists():
            continue
        sid, rt, arm, k = f.stem.split("_")
        if man["arms"].get(arm, {}).get("role") == "input":
            continue  # an input arm (the unreviewed plan) has nothing to diff against itself
        src = Path(plans_from) / "out" / f"{sid}_{rt}_{man['arms'][arm]['plans_arm']}_{k}.json"
        revised = plan_text(json.loads(f.read_text())["text"], True)
        if src.exists() and words(revised) >= STUB_WORDS:
            s = sc[sid]; ui = s.get("ui") if rt in s.get("runtimes_ext", []) else None
            todo.append((fill(DIFF, request=request_text(s, ui), original=json.loads(src.read_text())["text"],
                              revised=revised).replace("{{", "{").replace("}}", "}"), d))

    def one(job):
        prompt, d = job
        for _ in range(3):
            v = parse_diff(call(model, prompt, timeout=300))
            if v:
                d.write_text(json.dumps(v, indent=1)); return True
        with open(dd / "failures.log", "a") as log:
            log.write(d.stem + "\n")
        return False

    with ThreadPoolExecutor(workers) as ex:
        ok = list(ex.map(one, todo))
    totals = {}
    for f in dd.glob("*.json"):
        arm = f.stem.split("_")[2]; v = json.loads(f.read_text())
        t = totals.setdefault(arm, {"reviews": 0, **{k: 0 for k in DIFF_KEYS}})
        t["reviews"] += 1
        for k in DIFF_KEYS:
            t[k] += v[k]
    (run_ / "diff_summary.json").write_text(json.dumps(totals, indent=1) + "\n")
    return {"checked": sum(ok), "failed": ok.count(False), "totals": totals}
