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
import shutil
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


def call_full(model: str, prompt: str, *, timeout: int = 600, tools: str = "", workspace: str | Path | None = None) -> dict:
    """Run one prompt on `model` with no MCP servers, from an empty directory.

    Returns {"text", "input_tokens", "output_tokens", "seconds"}; text is '' on failure. Input tokens count
    cached and uncached prompt tokens; output tokens include reasoning. Seconds is wall-clock time.
    `tools` is "" (none) or "Read". A prompt that asks the model to check something (a review focus that says
    to run a command) needs a tool to reach for; with none, a model may announce a call and stop, a stub.
    Read from an empty directory lets it try, find nothing, and answer.
    `workspace`: a folder whose contents are copied into the call's own directory (reference files the
    prompt points to), read with the Read tools. Prompts are passed inline, so no prompt file exists on disk;
    every path a Grok call touched is audited from its session log and returned as "outside_paths" when it
    lies outside the call's own directory (`run` discards and reruns such a call).
    """
    if tools not in ("", "Read"):
        raise ValueError(f"call: tools must be '' or 'Read', got {tools!r}")
    if model not in MODELS:
        raise ValueError(f"call: model must be one of {MODELS}, got {model!r}")
    rec = {"text": "", "input_tokens": None, "output_tokens": None, "seconds": 0.0}
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="rubric-eval-") as cwd:
        if workspace:
            shutil.copytree(workspace, cwd, dirs_exist_ok=True)
        try:
            if model in ("sonnet", "opus"):
                pick = ["--model", "sonnet"] if model == "sonnet" else ["--model", OPUS_MODEL, "--effort", OPUS_EFFORT]
                allowed = "Read,Grep,Glob" if tools else ""
                argv = ["claude", "-p", *pick, "--output-format", "json", "--tools", allowed, *NO_MCP] + (["--allowedTools", allowed] if tools else [])
                out = subprocess.run(argv, input=prompt, capture_output=True, text=True, timeout=timeout, cwd=cwd).stdout
                d = json.loads(out) if out.strip() else {}
                u = d.get("usage")
                rec["text"] = d.get("result", "") if not d.get("is_error") else ""
                if isinstance(u, dict) and "input_tokens" in u and "output_tokens" in u:  # input_tokens excludes cache
                    rec.update(input_tokens=u["input_tokens"] + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0),
                               output_tokens=u["output_tokens"])
            else:
                home = _grok_home()
                env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "GROK_CONFIG_DIR": str(home / ".grok"),
                       "XDG_CONFIG_HOME": str(home / ".config"), "XDG_DATA_HOME": str(home / ".local/share"),
                       "XDG_CACHE_HOME": str(home / ".cache"), "XDG_STATE_HOME": str(home / ".local/state"),
                       "GROK_CLAUDE_SKILLS_ENABLED": "false", "GROK_CURSOR_SKILLS_ENABLED": "false", "NO_COLOR": "1"}
                # The prompt goes inline (-p), so no prompt file sits on disk for any call to find.
                argv = ["grok", "--cwd", cwd, "-p", prompt, "--verbatim", "--model", GROK_MODEL,
                        "--reasoning-effort", GROK_EFFORT, "--output-format", "json", "--no-auto-update",
                        "--disable-web-search"]
                # Grok reads `--tools ""` as no restriction (every tool, shell included), so name an allowlist:
                # todo_write touches no files. With tools, it may read, list and search; never a shell, never
                # auto-approval. Grok's kernel sandbox cannot start on a Mac whose /var/run/docker.sock is a
                # symlink, so reads are audited instead: see outside_paths.
                argv += (["--tools", "read_file,list_dir,grep", "--max-turns", "40"] if tools
                         else ["--tools", "todo_write", "--max-turns", "6"]) + ["--disallowed-tools", "search_tool,use_tool"]
                out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env).stdout
                d = json.loads(out) if out.strip() else {}
                u = d.get("usage")
                rec["text"] = d.get("text", "")
                if tools and d.get("sessionId"):
                    rec["outside_paths"] = outside_paths(home, d["sessionId"], cwd)
                if isinstance(u, dict) and "input_tokens" in u and "output_tokens" in u:
                    # input_tokens excludes cache reads (total_tokens = input + cache read + output); output includes reasoning
                    rec.update(input_tokens=u["input_tokens"] + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0),
                               output_tokens=u["output_tokens"])
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            pass
    rec["seconds"] = round(time.monotonic() - start, 1)
    return rec


PATH_KEYS = ("target_file", "target_directory", "path", "file_path")
READ_TOOLS = ("read_file", "list_dir", "grep")


def outside_paths(home: Path, session_id: str, cwd: str) -> list[str] | None:
    """What a Grok session touched beyond its own directory: every path argument outside `cwd`, and any tool
    outside the read-only allowlist (as "tool:<name>"). None if the session log is missing."""
    logs = list((home / ".grok" / "sessions").glob(f"*/{session_id}/updates.jsonl"))
    if not logs:
        return None
    root = os.path.realpath(cwd); seen = set()
    for line in logs[0].read_text(errors="replace").splitlines():
        try:
            u = json.loads(line)["params"]["update"]
        except (ValueError, KeyError, TypeError):
            continue
        if u.get("sessionUpdate") != "tool_call":
            continue
        if u.get("title") not in READ_TOOLS:
            seen.add(f"tool:{u.get('title')}")
        for k in PATH_KEYS:
            v = (u.get("rawInput") or {}).get(k)
            if isinstance(v, str) and v:
                full = os.path.realpath(v if os.path.isabs(v) else os.path.join(root, v))
                if full != root and not full.startswith(root + os.sep):
                    seen.add(v)
    return sorted(seen)


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

def run(run_dir: str | Path, model: str, *, workers: int = 8, attempts: int = 3, tools: str = "",
        workspace: str | Path | None = None, timeout: int | None = None) -> dict:
    """Run every prompt without a finished output; rerun a stub up to `attempts` times.

    timeout (seconds per call) defaults to 600, or 1800 with tools: a review that reads its references took
    13 minutes, and a call cut off by the timeout is a stub, rerun into the same wall."""
    timeout = timeout or (1800 if tools else 600)
    run_ = Path(run_dir); out = run_ / "out"; out.mkdir(exist_ok=True)
    reviews = json.loads((run_ / "manifest.json").read_text()).get("reviews", False)

    def one(p: Path):
        dest = out / (p.stem + ".json")
        if dest.exists() and words(plan_text(json.loads(dest.read_text())["text"], reviews)) >= STUB_WORDS:
            return "done"
        text = ""; used = {"input_tokens": 0, "output_tokens": 0, "seconds": 0.0}
        for n in range(1, attempts + 1):
            r = call_full(model, p.read_text(), tools=tools, workspace=workspace, timeout=timeout); text = r["text"]
            for k in used:  # stub reruns are real cost, so usage sums every attempt; unknown stays unknown
                used[k] = None if used[k] is None or r[k] is None else used[k] + r[k]
            if r.get("outside_paths") or (tools and model == "grok" and r.get("outside_paths") is None and text):
                with open(run_ / "isolation.log", "a") as log:  # read outside its own directory, or unaudited
                    log.write(f"{p.stem}\t{r.get('outside_paths')}\n")
                text = ""; continue
            if words(plan_text(text, reviews)) >= STUB_WORDS:
                used["seconds"] = round(used["seconds"], 1)
                dest.write_text(json.dumps({"model": model, "text": text, "attempts": n, **used}) + "\n"); return "ok"
        with open(run_ / "stubs.log", "a") as log:
            log.write(f"{p.stem}\t{words(text)} words\t{used['seconds']}s over {attempts} attempts\n")
        return "stub"

    man_path = run_ / "manifest.json"; man = json.loads(man_path.read_text())
    prev = man.get("condition")
    cond = {"model": model, "tools": tools}
    if workspace:
        if not tools:
            raise SystemExit("run: a workspace needs --tools Read, or the model cannot open it")
        files = sorted(f for f in Path(workspace).rglob("*") if f.is_file())
        cond["workspace"] = {"files": len(files), "sha": sha("".join(f"{f.relative_to(workspace)}:{sha(f.read_text(errors='replace'))}" for f in files))}
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
    return re.sub(r"[^0-9a-z]+", " ", s.lower()).strip()


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
            lowered = "partial" if g == "met" else "missed"
            verdict["grades"][c] = lowered; e["judge_grade"] = g; e["grade"] = lowered; changed.append(c)
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
    smeans = [sum(v) / len(v) for v in per.values()]
    return {"mean": round(m, 4), "low": round(lo, 4), "high": round(hi, 4), "arm_higher": w, "arm_lower": l, "n": len(diffs),
            "scenarios": len(per), "scenario_mean": round(sum(smeans) / len(smeans), 4), "wilcoxon_p": wilcoxon(smeans),
            **({"baseline_mean": round(sum(base) / len(base), 4)} if base else {})}


def paired(verdicts: dict, arm: str, baseline: str, crits=None, cluster: str | None = None) -> dict | None:
    """Paired score comparison (percentage points) over matching cell-trials; see paired_values.

    For scores, arm_higher and arm_lower are the cells the arm won and lost (also given as won and lost)."""
    c = paired_values({s: score(v, crits) for s, v in verdicts.items()}, arm, baseline, cluster)
    if c:
        c["won"], c["lost"] = c["arm_higher"], c["arm_lower"]
    return c


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


def significant(c: dict | None, sign: int) -> bool:
    """A difference counts only when both tests agree on its direction (sign +1 or -1): the 95% interval
    excludes zero on that side, and the Wilcoxon test over scenario means rejects (p < ALPHA) with the
    scenario mean on the same side. A percentile bootstrap over few clusters runs narrow on its own."""
    if not c or c.get("wilcoxon_p") is None or c["wilcoxon_p"] >= ALPHA:
        return False
    return (c["low"] > 0 and c["scenario_mean"] > 0) if sign > 0 else (c["high"] < 0 and c["scenario_mean"] < 0)


def _efficiency(c: dict | None, what: str):
    """Which side a paired cost comparison favours: 'arm' (costs less), 'baseline', or None (no difference)."""
    if not c:
        return None, f"{what}: not recorded for both arms"
    span = f"{c['mean']:+.1f} per output, 95% [{c['low']:+.1f}, {c['high']:+.1f}], Wilcoxon p={c.get('wilcoxon_p')}"
    if significant(c, -1):
        return "arm", f"{what}: arm uses less ({span})"
    if significant(c, +1):
        return "baseline", f"{what}: arm uses more ({span})"
    return None, f"{what}: no significant difference ({span})"


def decide(comparison: dict, guardrails: list[str], noise: float | None, *, scenarios: int | None = None,
           checks: list[str] | None = None, tokens: dict | None = None, seconds: dict | None = None) -> dict:
    """The SPEC section 8 rule: a material quality difference trumps; near-identical quality goes to tokens,
    then time.

    comparison: paired score comparisons (points) by group, "overall" required. noise: the judge's measured
    test-retest noise in points, the smallest difference this judge can tell apart. checks: blocking problems
    found elsewhere (conditions, rises in overbuilding or platform errors, differing stub or na rates).

    1. Near-identical first: when the whole overall interval lies within +/- noise, quality does not decide.
       2. Tokens: the side that significantly uses fewer wins. 3. Time, when tokens show no difference.
       4. A tie at every level keeps the baseline (a change must earn its place).
    Otherwise the difference is material if it is significant (see `significant`): better or worse on
    quality alone. Anything else is inconclusive. Guardrails and checks block the arm from winning at any
    level; a harm blocks on the interval alone, while a win needs both tests (a deliberate asymmetry).
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
    q = (f"quality {overall['mean']:+.1f} points, 95% [{overall['low']:+.1f}, {overall['high']:+.1f}], "
         f"Wilcoxon p={overall.get('wilcoxon_p')}")
    winner = decided = None
    if noise is not None and -noise <= overall["low"] and overall["high"] <= noise:
        reasons.append(q + f": near-identical (within the judge's noise, +/-{noise})")
        for what, c in (("tokens", tokens), ("time", seconds)):
            side, why = _efficiency(c, what); reasons.append(why)
            if side:
                winner, decided = side, what; break
        if not winner:
            winner, decided = "baseline", "tie"; reasons.append("tie at every level: the baseline stays")
    elif significant(overall, +1):
        winner, decided = "arm", "quality"; reasons.append(q + ": materially better")
    elif significant(overall, -1):
        winner, decided = "baseline", "quality"; reasons.append(q + ": materially worse")
    else:
        reasons.append(q + ": inconclusive (not near-identical, and the tests do not agree on a difference); "
                       "add scenarios or trials")
    if winner == "arm" and blockers:
        winner = None
        return {"winner": None, "decided_by": None, "ship": False,
                "reasons": ["blocked: the arm cannot win while these checks fail"] + blockers + reasons}
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
            known = d.get("input_tokens") is not None and d.get("output_tokens") is not None
            out[f.stem] = {"tokens": d["input_tokens"] + d["output_tokens"] if known else None, "seconds": d["seconds"]}
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
                 **({"mean_tokens": round(sum(u["tokens"] for u in mine if u["tokens"] is not None) / max(1, sum(u["tokens"] is not None for u in mine))),
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
            na_rate = {s: sum(g == "na" for g in v["grades"].values()) / max(len(v["grades"]), 1) for s, v in verdicts.items()}
            stub_ind = {f.stem: float(f.stem in stubs.get(f.stem.split("_")[2], ())) for f in (run_ / "prompts").glob("*.txt")}
            for what, vals, zero in (("na", na_rate, False), ("stub", stub_ind, base_is_input)):
                c = paired_values(vals, a, baseline, cluster, baseline_zero=zero)
                if c and (c["low"] > 0 or c["high"] < 0):
                    checks.append(f"{what} rates differ between arms (paired 95% [{c['low']:+.3f}, {c['high']:+.3f}] per output)")
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
    reviews = json.loads((run_ / "manifest.json").read_text()).get("reviews", False)
    for s in sample:  # judge() applies the quote check; compare like with like
        if s in first and "quote_check" not in first[s]:
            first[s] = verify_quotes(first[s], plan_text(json.loads((run_ / "out" / f"{s}.json").read_text())["text"], reviews))
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


# ---------------------------------------------------------------- value audit (review experiments)

VALUE = """You audit what a review changed in an architecture plan. Question every change in both directions: an
addition the request did not ask for may still be valuable, and a removal that looks like tidying may lose value.

Request: {request}

List every material item the revision ADDED and every material item it REMOVED or weakened: a feature, store,
service, sign-in or access rule, check, safeguard, limit, step or channel. Ignore rewording. For each item:
- "for": the strongest case that the item has value for THIS request: a stated need (quote the request), or a
  clearly implied one (security, correctness, data integrity, reliability, accessibility, cost, operability).
- "against": the strongest case that it does not: not needed for this request, or it adds scope, cost, risk,
  maintenance or friction for the user.
- "verdict": weigh both honestly. For an addition: "valuable" (a reasonable owner of this request would want it),
  "optional" (defensible, but the request is complete without it) or "unwanted" (costs more than it gives). For a
  removal: "loss" (the removed item had value) or "fine" (removing it cost nothing of value).

Original plan:
<<<
{original}
>>>

Revised plan:
<<<
{revised}
>>>

Return only JSON: {{"added": [{{"item": "...", "for": "...", "against": "...", "verdict": "valuable|optional|unwanted"}}],
 "removed": [{{"item": "...", "for": "...", "against": "...", "verdict": "loss|fine"}}]}}
"""
ADD_VERDICTS, REMOVE_VERDICTS = ("valuable", "optional", "unwanted"), ("loss", "fine")


def parse_value(output: str) -> dict | None:
    m = re.search(r"\{.*\}", output or "", re.S)
    try:
        j = json.loads(m.group(0))
        ok = all(isinstance(j.get(k), list) for k in ("added", "removed"))
        ok = ok and all(x.get("verdict") in ADD_VERDICTS and x.get("item") for x in j["added"])
        ok = ok and all(x.get("verdict") in REMOVE_VERDICTS and x.get("item") for x in j["removed"])
        return j if ok else None
    except Exception:
        return None


def _overlap(a: str, b: str) -> float:
    x, y = set(_norm(a).split()), set(_norm(b).split())
    return len(x & y) / max(1, min(len(x), len(y)))


def valuecheck(run_dir: str | Path, suite: dict, plans_from: str | Path, *, model: str = "opus", workers: int = 8,
               only: list[str] | None = None, dest: str = "value") -> dict:
    """For a review run, weigh every item each review added or removed (case for, case against, verdict), and
    cross-check additions the judge graded overbuilt against the audit's verdict on them."""
    run_ = Path(run_dir); vd = run_ / dest; vd.mkdir(exist_ok=True)
    man = json.loads((run_ / "manifest.json").read_text())
    sc = {x["id"]: x for x in suite["scenarios"]["scenarios"]}
    todo = []
    for f in sorted((run_ / "out").glob("*.json")):
        d = vd / (f.stem + ".json")
        sid, rt, arm, k = f.stem.split("_")
        if d.exists() or man["arms"].get(arm, {}).get("role") == "input" or (only is not None and f.stem not in only):
            continue
        src = Path(plans_from) / "out" / f"{sid}_{rt}_{man['arms'][arm]['plans_arm']}_{k}.json"
        revised = plan_text(json.loads(f.read_text())["text"], True)
        if src.exists() and words(revised) >= STUB_WORDS:
            s = sc[sid]; ui = s.get("ui") if rt in s.get("runtimes_ext", []) else None
            todo.append((fill(VALUE, request=request_text(s, ui), original=json.loads(src.read_text())["text"],
                              revised=revised).replace("{{", "{").replace("}}", "}"), d))

    def one(job):
        prompt, d = job
        for _ in range(3):
            v = parse_value(call(model, prompt, timeout=600))
            if v:
                v["model"] = model; d.write_text(json.dumps(v, indent=1)); return True
        with open(vd / "failures.log", "a") as log:
            log.write(d.stem + "\n")
        return False

    with ThreadPoolExecutor(workers) as ex:
        ok = list(ex.map(one, todo))
    verdicts = load_verdicts(run_dir)
    totals, disputed = {}, []
    for f in sorted(vd.glob("*.json")):
        arm = f.stem.split("_")[2]; v = json.loads(f.read_text())
        t = totals.setdefault(arm, {"reviews": 0, **{f"added_{x}": 0 for x in ADD_VERDICTS}, **{f"removed_{x}": 0 for x in REMOVE_VERDICTS}})
        t["reviews"] += 1
        for x in v["added"]:
            t[f"added_{x['verdict']}"] += 1
        for x in v["removed"]:
            t[f"removed_{x['verdict']}"] += 1
        for ob in (verdicts.get(f.stem, {}).get("overbuilt_items") or []):  # the judge penalised it; was it valuable?
            match = max(v["added"], key=lambda x: _overlap(ob, x["item"]), default=None)
            if match and _overlap(ob, match["item"]) >= 0.3:
                disputed.append({"review": f.stem, "judge_overbuilt": ob, "audit_item": match["item"],
                                 "audit_verdict": match["verdict"], "for": match["for"]})
    summary = {"totals": totals, "judge_overbuilt_matched": len(disputed),
               "judge_overbuilt_verdicts": {x: sum(d["audit_verdict"] == x for d in disputed) for x in ADD_VERDICTS},
               "judge_overbuilt_but_valuable": [d for d in disputed if d["audit_verdict"] == "valuable"]}
    (run_ / f"{dest}_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    return {"checked": sum(ok), "failed": ok.count(False), **summary}
