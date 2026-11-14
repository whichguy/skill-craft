#!/usr/bin/env python3
"""Score the planning-points probe's runs (README.md beside this file: measures M1-M9, binding, predictions P1-P17).

    python3 -I docs/experiments/planning-points-probe-20261114/score.py RUN_OUT [RUN_OUT ...]

RUN_OUT is a run's output folder (run.py --output). Writes evidence/scores.json (every measure per run, with the excerpts
that matched) and evidence/scores.md (the tables), and prints the tables. Reads the run folders only.

Everything here is a script check: no model is called. Each measure is the README's definition; where a pattern decides,
the pattern is a constant below with the README's wording, and the excerpt it matched is kept.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
EVIDENCE = HERE / "evidence"
CASE = "ticket-due-times"
BASE_FIXTURE = REPO / "test" / "shiploop_e2e" / "fixtures" / "node-tickets"
sys.path.insert(0, str(REPO / "skills" / "shiploop" / "scripts"))
import shiploop_concerns  # noqa: E402  (the concern list and owner stages; never copied here)

BLOCK = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)
ROWS = ("migrate-before", "migrate-after", "switchover", "state", "config")
assert set(ROWS) <= set(shiploop_concerns.CONCERN_IDS), "a scored row is not a concern of shiploop_concerns"
MIGRATION = re.compile(r"backfill|migrat|existing tickets?|already in the (production )?data file|saved before|older (data )?files?",
                       re.I)
OVERDUE = re.compile(r"overdue", re.I)
ROLLBACK = re.compile(r"roll ?back|revert|go back", re.I)
DATA_AWARE = re.compile(r"DUE_TIMES|1\.4\.0|data file|DATA_FILE|tickets\.json|backup|version 1|format", re.I)
SHIPLOOP_PATH = re.compile(r"docs/shiploop/\S*")
DOCS = {
    "README.md": re.compile(r"(?<![/\w])README(\.md)?\b"),
    "docs/operations.md": re.compile(r"docs/operations\.md|(?<![/\w])operations\.md|runbook", re.I),
    "docs/api.md": re.compile(r"docs/api\.md|(?<![/\w])api\.md"),
    "CHANGELOG.md": re.compile(r"CHANGELOG(\.md)?"),
    "docs/decisions/": re.compile(r"docs/decisions|decision record", re.I),
    "the word documentation": re.compile(r"\bdocumentation\b|\bdocs\b(?!/)", re.I),
}
BASE_SETTINGS = {"PORT", "DATA_FILE", "NOTIFY_FILE", "WORKER_INTERVAL_MS", "MAX_BODY_BYTES", "LOG_REQUESTS"}
UPPER = re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]*[A-Z0-9]\b")
CONFIG_FILE = re.compile(r"[\w./-]+\.(?:json|env|conf)\b")
NOT_CONFIG = re.compile(r"package(-lock)?\.json|tickets\.json|notifications?\.jsonl?")
HOUR = re.compile(r"hour", re.I)
SWITCH_ON = re.compile(r"DUE_TIMES|switch(?:ed|ing|es)?\b[^.\n]{0,40}\bon\b", re.I)
GO_BACK = re.compile(r"1\.4\.0|roll ?back|go back", re.I)
ENV_READ = re.compile(r"process\.env\.([A-Z][A-Z0-9_]*)|process\.env\[['\"]([A-Z][A-Z0-9_]*)['\"]\]|\benv\.([A-Z][A-Z0-9_]*)"
                      r"|\benv\[['\"]([A-Z][A-Z0-9_]*)['\"]\]|['\"]([A-Z][A-Z0-9]*_[A-Z0-9_]*[A-Z0-9])['\"]")
PROBE_CHECKS = ("migrate", "restart", "switch", "rollback", "off", "cli")
SKIP_KEYS = {"id", "applies", "owner_stage", "follows", "outcome", "due_item", "anchor"}


# Reading a run

def block(path: pathlib.Path):
    try:
        match = BLOCK.search(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    return json.loads(match.group(1)) if match else None


def strings(value, key=None):
    """Every string value of `value`, depth first, skipping the keys whose values are labels rather than text."""
    if key in SKIP_KEYS:
        return
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for name, item in value.items():
            yield from strings(item, name)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item, key)


def text_of(value) -> str:
    return "\n".join(strings(value))


def segments(text: str) -> list[str]:
    """Line ends and sentence ends (a full stop, question or exclamation mark followed by white space)."""
    out = []
    for line in text.splitlines():
        out += [piece.strip() for piece in re.split(r"(?<=[.!?])\s+", line) if piece.strip()]
    return out


class Run:
    def __init__(self, out: pathlib.Path):
        self.out = out
        self.result = json.loads((out / "result.json").read_text()) if (out / "result.json").is_file() else {}
        receipt = json.loads((out / "shiploop-run.json").read_text()) if (out / "shiploop-run.json").is_file() else {}
        self.run_dir = pathlib.Path(receipt.get("run_dir") or (self.result.get("shiploop") or {}).get("run_dir") or "")
        self.state = block(self.run_dir / "state.md") or {} if self.run_dir.name else {}
        self.accepted = set((self.state.get("accepted") or {}).keys())
        self.history = [entry for entry in self.state.get("history") or [] if isinstance(entry, dict)]
        self.work = out / "work"
        self.start_head = (self.result.get("base") or {}).get("start_head")

    def results(self, stage: str) -> list[dict]:
        """The accepted results of `stage`, in history order, each {action, workitem, result}."""
        found, seen = [], set()
        for entry in self.history:
            action = entry.get("action")
            if entry.get("stage") != stage or action not in self.accepted or action in seen:
                continue
            seen.add(action)
            data = block(self.run_dir / "results" / f"{action}.md")
            if data and isinstance(data.get("result"), dict):
                found.append({"action": action, "workitem": data.get("workitem") or entry.get("workitem"),
                              "result": data["result"]})
        return found

    def base_file(self, relative: str) -> str | None:
        if not self.start_head:
            path = BASE_FIXTURE / relative
            return path.read_text(errors="replace") if path.is_file() else None
        done = subprocess.run(["git", "-C", str(self.work), "show", f"{self.start_head}:{relative}"], capture_output=True,
                              text=True)
        return done.stdout if done.returncode == 0 else None

    def file(self, relative: str) -> str | None:
        path = self.work / relative
        return path.read_text(errors="replace") if path.is_file() else None

    def tracked(self) -> list[str]:
        done = subprocess.run(["git", "-C", str(self.work), "ls-files", "--cached", "--others", "--exclude-standard"],
                              capture_output=True, text=True)
        return sorted(set(done.stdout.split())) if done.returncode == 0 else []

    def base_tracked(self) -> list[str]:
        if not self.start_head:
            return sorted(str(p.relative_to(BASE_FIXTURE)) for p in BASE_FIXTURE.rglob("*") if p.is_file())
        done = subprocess.run(["git", "-C", str(self.work), "ls-tree", "-r", "--name-only", self.start_head],
                              capture_output=True, text=True)
        return sorted(set(done.stdout.split())) if done.returncode == 0 else []


def added_lines(before: str | None, after: str | None) -> str:
    """The lines of `after` that `before` does not have (a multiset difference, enough for documents)."""
    if after is None:
        return ""
    pool = {}
    for line in (before or "").splitlines():
        pool[line] = pool.get(line, 0) + 1
    out = []
    for line in after.splitlines():
        if pool.get(line):
            pool[line] -= 1
        else:
            out.append(line)
    return "\n".join(out)


# Measures

def m1_rows(plan: dict) -> dict:
    concerns = plan.get("concerns") or {}
    out = {}
    for name in ROWS:
        rows = [{"item": item, "owner_stage": row.get("owner_stage"), "decision": row.get("decision"),
                 "anchor": row.get("anchor")}
                for item, item_rows in concerns.items() for row in item_rows or []
                if isinstance(row, dict) and row.get("id") == name and row.get("applies") == "yes"]
        out[name] = {"applies": bool(rows), "rows": rows}
    return out


def item_text(item: dict) -> str:
    return text_of({"title": item.get("title"), "context": item.get("context")})


def step_text(step: dict) -> str:
    return text_of({key: value for key, value in step.items() if key != "proof"})


def m2_order(plan: dict, rows: dict, step_plans: list[dict]) -> dict:
    items = [item for item in plan.get("work_items") or [] if isinstance(item, dict)]
    ids = [item.get("id") for item in items]
    migration = sorted({ids.index(row["item"]) for row in rows["migrate-before"]["rows"] if row["item"] in ids})
    basis = "migrate-before rows"
    if not migration:
        migration = [n for n, item in enumerate(items) if MIGRATION.search(item_text(item))]
        basis = "MIGRATION words in item title or context"
    feature = [n for n, item in enumerate(items) if OVERDUE.search(item_text(item))]
    record = {"items": ids, "migration_items": [ids[n] for n in migration], "migration_basis": basis,
              "feature_items": [ids[n] for n in feature]}
    if not migration or not feature:
        record["verdict"] = "unknown"
        return record
    first_m, first_f = migration[0], feature[0]
    record["verdict"] = "before" if first_m < first_f else "same" if first_m == first_f else "after"
    if record["verdict"] == "same":
        item_id = ids[first_m]
        plans = [entry for entry in step_plans if entry["workitem"] == item_id]
        steps = (plans[0]["result"].get("steps") if plans else None) or []
        m_step = next((n for n, step in enumerate(steps) if isinstance(step, dict) and MIGRATION.search(step_text(step))), None)
        f_step = next((n for n, step in enumerate(steps) if isinstance(step, dict) and OVERDUE.search(step_text(step))), None)
        record["steps"] = [step.get("id") for step in steps if isinstance(step, dict)]
        record["first_migration_step"] = None if m_step is None else steps[m_step].get("id")
        record["first_overdue_step"] = None if f_step is None else steps[f_step].get("id")
        record["migration_step_first"] = (m_step is not None and (f_step is None or m_step <= f_step))
    record["held"] = record["verdict"] == "before" or (record["verdict"] == "same" and record.get("migration_step_first", False))
    return record


def m3_release_last(plan: dict, rows: dict) -> dict:
    ids = [item.get("id") for item in plan.get("work_items") or [] if isinstance(item, dict)]
    applicable = rows["switchover"]["rows"]
    if not applicable:
        return {"verdict": "none", "rows": []}
    last = ids[-1] if ids else None
    early = [row for row in applicable if row["owner_stage"] not in ("release-plan", "operations") and row["item"] != last]
    return {"verdict": "early" if early else "last", "rows": applicable, "last_item": last}


def m4_rollback(release_plans: list[dict]) -> dict:
    if not release_plans:
        return {"reached": False}
    text = text_of(release_plans[-1]["result"])
    pieces = [piece for piece in segments(text) if ROLLBACK.search(piece)]
    aware = [piece for piece in pieces if DATA_AWARE.search(piece)]
    return {"reached": True, "action": release_plans[-1]["action"], "planned": bool(pieces), "data_aware": bool(aware),
            "rollback_segments": pieces[:12], "data_aware_segments": aware[:8]}


def m5_docs(plan_text: str) -> dict:
    text = SHIPLOOP_PATH.sub(" ", plan_text)
    found = {}
    for name, pattern in DOCS.items():
        hits = [piece for piece in segments(text) if pattern.search(piece)]
        if hits:
            found[name] = hits[:3]
    return {"named": sorted(found), "any": bool(found), "excerpts": found}


def m6_setup(plan_text: str, base_files: set) -> dict:
    names_due = "DUE_TIMES" in plan_text
    hits = []
    for piece in segments(plan_text):
        if not HOUR.search(piece):
            continue
        uppers = {name for name in UPPER.findall(piece)} - BASE_SETTINGS - {"DUE_TIMES"}
        files = {name for name in CONFIG_FILE.findall(piece) if not NOT_CONFIG.search(name) and name not in base_files}
        if uppers or files:
            hits.append({"segment": piece[:400], "names": sorted(uppers), "files": sorted(files)})
    return {"names_DUE_TIMES": names_due, "hours_setting": bool(hits), "held": names_due and bool(hits), "excerpts": hits[:6]}


def env_names(texts) -> set:
    names = set()
    for text in texts:
        for groups in ENV_READ.findall(text):
            names.update(name for name in groups if name)
    return names


def m9_setup_product(run: Run) -> dict:
    files, base = run.tracked(), set(run.base_tracked())
    code = [name for name in files if name.split("/")[0] in ("src", "bin") and name.endswith(".js")]
    base_code = [name for name in base if name.split("/")[0] in ("src", "bin") and name.endswith(".js")]
    delivered = env_names(run.file(name) or "" for name in code)
    before = env_names(run.base_file(name) or "" for name in base_code)
    new = sorted(delivered - before - {"DUE_TIMES"})
    configs = sorted(name for name in files if name not in base and re.search(r"\.(json|env|conf)$", name)
                     and name.split("/")[0] not in ("test", "docs") and not NOT_CONFIG.search(name))
    return {"new_settings": new, "new_config_files": configs, "reads_DUE_TIMES": "DUE_TIMES" in delivered,
            "has_setting": bool(new or configs)}


def m8_docs_product(run: Run, settings: dict) -> dict:
    readme, readme_base = run.file("README.md") or "", run.base_file("README.md") or ""
    ops, ops_base = run.file("docs/operations.md") or "", run.base_file("docs/operations.md") or ""
    api, api_base = run.file("docs/api.md") or "", run.base_file("docs/api.md") or ""
    changelog, changelog_base = run.file("CHANGELOG.md") or "", run.base_file("CHANGELOG.md") or ""
    package, package_base = run.file("package.json") or "{}", run.base_file("package.json") or "{}"
    d1 = "DUE_TIMES" in readme
    wanted = settings["new_settings"] + [pathlib.PurePosixPath(name).name for name in settings["new_config_files"]]
    d2 = bool(wanted) and all(name in readme for name in wanted)
    operator = added_lines(readme_base, readme) + "\n" + added_lines(ops_base, ops)
    pieces = segments(operator)
    switch = [piece for piece in pieces if SWITCH_ON.search(piece)]
    back = [piece for piece in pieces if GO_BACK.search(piece)]
    d3 = bool(switch) and bool(back)
    try:
        version_changed = json.loads(package).get("version") != json.loads(package_base).get("version")
    except ValueError:
        version_changed = False
    d4 = changelog.count("\n## ") > changelog_base.count("\n## ") and version_changed
    base = set(run.base_tracked())
    d5 = [name for name in run.tracked() if name.startswith("docs/decisions/") and name not in base]
    api_added = added_lines(api_base, api)
    d6 = bool(re.search(r"\bdue\b", api_added)) and "overdue" in api_added
    miss = not (d1 and d2 and d3 and d6)
    return {"D1_readme_DUE_TIMES": d1, "D2_readme_settings": d2, "D2_wanted": wanted, "D3_operator_procedure": d3,
            "D3_switch_segments": switch[:4], "D3_back_segments": back[:4], "D4_changelog_and_version": d4,
            "D5_new_decision_records": d5, "D6_api_due_overdue": d6, "miss": miss}


def m7_checks(run: Run) -> dict:
    out = {}
    for check in run.result.get("checks") or []:
        command = str(check.get("command") or "")
        name = next((mode for mode in PROBE_CHECKS if command.endswith(f"due_times_probe.py\" {mode}")), None)
        if name is None:
            name = "suite" if "base_tests.py\" suite" in command else "pristine" if "base_tests.py\" pristine" in command else command
        out[name] = {"pass": bool(check.get("pass")), "output": str(check.get("output") or "")[-600:]}
    return {"ran": bool(out), "checks": out}


def binding(run: Run, rows: dict, step_plans: list[dict], checks: dict) -> dict:
    serves = {"migrate-before": ("migrate", "restart", "switch"), "switchover": ("off", "rollback")}
    words = {"migrate-before": re.compile(MIGRATION.pattern + r"|data file", re.I), "switchover": re.compile(r"DUE_TIMES")}
    out = {}
    for name in ("migrate-before", "switchover"):
        applicable = rows[name]["rows"]
        acted = []
        for row in applicable:
            if row["owner_stage"] == "step-plan":
                plans = [entry for entry in step_plans if entry["workitem"] == row["item"]]
                mapped = any(isinstance(entry, dict) and entry.get("id") == name and entry.get("steps")
                             for plan in plans for entry in plan["result"].get("concerns") or [])
                acted.append({"item": row["item"], "owner": "step-plan", "acted": mapped,
                              "how": "mapped to steps" if mapped else "not mapped in the item's accepted step plans"})
            else:
                texts = [text_of(entry["result"]) for entry in run.results(row["owner_stage"])]
                hit = any(words[name].search(text) for text in texts)
                acted.append({"item": row["item"], "owner": row["owner_stage"], "acted": hit,
                              "how": f"{len(texts)} accepted {row['owner_stage']} results, named: {hit}"})
        product = {mode: checks["checks"].get(mode, {}).get("pass") for mode in serves[name]}
        a, b = bool(applicable), bool(applicable) and all(entry["acted"] for entry in acted)
        c = checks["ran"] and all(product.values())
        out[name] = {"a_applies": a, "b_acted": b, "c_product": c, "binds": a and b and c, "owners": acted,
                     "product_checks": product}
    return out


def validity(run: Run) -> dict:
    """Signs of another run's server on a fixed port: EADDRINUSE, or a start command naming port 4180."""
    hits = {"EADDRINUSE": 0, "port_4180_start": 0}
    for name in ("events.jsonl", "transcript.md"):
        path = run.out / name
        if not path.is_file():
            continue
        text = path.read_text(errors="replace")
        hits["EADDRINUSE"] += text.count("EADDRINUSE")
        hits["port_4180_start"] += len(re.findall(r"PORT=4180|:4180\b", text))
    return hits


def score(out: pathlib.Path) -> dict:
    run = Run(out)
    plans = run.results("plan")
    record = {"run": str(out), "case": run.result.get("case"), "host": run.result.get("host"), "model": run.result.get("model"),
              "effort": run.result.get("effort"), "pass": run.result.get("pass"),
              "versions": {key: (run.result.get("versions") or {}).get(key) for key in ("source", "plugin_version",
                                                                                      "shiploop_version")},
              "shiploop_status": (run.result.get("shiploop") or {}).get("status"),
              "termination": run.result.get("termination"), "validity": validity(run)}
    if not plans:
        record["plan"] = None
        return record
    plan = plans[0]["result"]
    record["plan_action"] = plans[0]["action"]
    record["replans"] = [entry["action"] for entry in plans[1:]]
    record["work_items"] = [{"id": item.get("id"), "title": item.get("title")} for item in plan.get("work_items") or []
                            if isinstance(item, dict)]
    step_plans = run.results("step-plan")
    plan_text = text_of(plan)
    base_files = set(run.base_tracked())
    rows = m1_rows(plan)
    record["M1_rows"] = rows
    record["M2_order"] = m2_order(plan, rows, step_plans)
    record["M3_release_last"] = m3_release_last(plan, rows)
    record["M4_rollback"] = m4_rollback(run.results("release-plan"))
    record["M5_docs_in_plan"] = m5_docs(plan_text)
    record["M6_setup_in_plan"] = m6_setup(plan_text, base_files)
    checks = m7_checks(run)
    record["M7_checks"] = checks
    if run.work.is_dir():
        settings = m9_setup_product(run)
        record["M9_setup_product"] = settings
        record["M8_docs_product"] = m8_docs_product(run, settings)
        record["M9_setup_product"]["miss"] = (not settings["has_setting"]) or not record["M8_docs_product"]["D2_readme_settings"]
    record["binding"] = binding(run, rows, step_plans, checks)
    return record


# Predictions, as registered

def predictions(runs: list[dict]) -> list[dict]:
    valid = [run for run in runs if run.get("plan_action")]
    completed = [run for run in valid if run.get("M7_checks", {}).get("ran")]
    reached = [run for run in valid if run.get("M4_rollback", {}).get("reached")]

    def every(population, test):
        return bool(population) and all(test(run) for run in population)

    def check(run, *modes):
        return all(run["M7_checks"]["checks"].get(mode, {}).get("pass") for mode in modes)

    rows = lambda name: (lambda run: run["M1_rows"][name]["applies"])  # noqa: E731
    out = [
        ("P1", "migrate-before applies to at least one work item, in every run", 70, every(valid, rows("migrate-before"))),
        ("P2", "switchover applies to at least one work item, in every run", 55, every(valid, rows("switchover"))),
        ("P3", "state applies to at least one work item, in every run", 80, every(valid, rows("state"))),
        ("P4", "config applies to at least one work item, in every run", 80, every(valid, rows("config"))),
        ("P5", "migrate-after applies in at most one run", 65,
         bool(valid) and sum(1 for run in valid if run["M1_rows"]["migrate-after"]["applies"]) <= 1),
        ("P6", "the migration comes before the feature in every run", 70, every(valid, lambda run: run["M2_order"].get("held"))),
        ("P7", "the release is planned last in every run", 60, every(valid, lambda run: run["M3_release_last"]["verdict"] == "last")),
        ("P8", "in every run that reaches release-plan, its result plans a rollback", 90,
         every(reached, lambda run: run["M4_rollback"]["planned"])),
        ("P9", "in every run that reaches release-plan, the rollback is data-aware", 55,
         every(reached, lambda run: run["M4_rollback"]["data_aware"])),
        ("P10", "in every run, the plan names at least one product document", 70, every(valid, lambda run: run["M5_docs_in_plan"]["any"])),
        ("P11", "in every run, the plan names DUE_TIMES and a setting for the hours", 75,
         every(valid, lambda run: run["M6_setup_in_plan"]["held"])),
        ("P12", "in every completed run, migrate, restart and switch pass", 55,
         every(completed, lambda run: check(run, "migrate", "restart", "switch"))),
        ("P13", "in every completed run, rollback passes", 75, every(completed, lambda run: check(run, "rollback"))),
        ("P14", "in every completed run, off passes", 50, every(completed, lambda run: check(run, "off"))),
        ("P15", "in every completed run, there is no documentation miss", 40,
         every(completed, lambda run: not run.get("M8_docs_product", {}).get("miss", True))),
        ("P16", "in every completed run, there is no setup miss", 65,
         every(completed, lambda run: not run.get("M9_setup_product", {}).get("miss", True))),
        ("P17", "migrate-before and switchover both bind in every run", 35,
         every(valid, lambda run: run["binding"]["migrate-before"]["binds"] and run["binding"]["switchover"]["binds"])),
    ]
    return [{"id": pid, "prediction": text, "probability": prob, "held": held,
             "population": len(reached) if pid in ("P8", "P9") else len(completed) if pid in ("P12", "P13", "P14", "P15", "P16")
             else len(valid)} for pid, text, prob, held in out]


def table(runs: list[dict], preds: list[dict]) -> str:
    def mark(value):
        return "yes" if value is True else "no" if value is False else "-" if value is None else str(value)

    lines = ["| Measure | " + " | ".join(pathlib.Path(run["run"]).name for run in runs) + " |",
             "|---|" + "---|" * len(runs)]

    def row(label, get):
        values = []
        for run in runs:
            try:
                values.append(mark(get(run)))
            except (KeyError, TypeError):
                values.append("-")
        lines.append(f"| {label} | " + " | ".join(values) + " |")

    row("ShipLoop status", lambda run: run.get("shiploop_status"))
    row("work items", lambda run: len(run["work_items"]))
    for name in ROWS:
        row(f"M1 {name} applies", lambda run, name=name: run["M1_rows"][name]["applies"])
    row("M2 order", lambda run: run["M2_order"]["verdict"] + (" (held)" if run["M2_order"].get("held") else ""))
    row("M3 release", lambda run: run["M3_release_last"]["verdict"])
    row("M4 rollback planned", lambda run: run["M4_rollback"].get("planned"))
    row("M4 data-aware", lambda run: run["M4_rollback"].get("data_aware"))
    row("M5 docs named in plan", lambda run: ", ".join(run["M5_docs_in_plan"]["named"]) or "none")
    row("M6 setup in plan", lambda run: run["M6_setup_in_plan"]["held"])
    for mode in ("suite", "pristine", *PROBE_CHECKS):
        row(f"M7 {mode}", lambda run, mode=mode: run["M7_checks"]["checks"].get(mode, {}).get("pass"))
    for key in ("D1_readme_DUE_TIMES", "D2_readme_settings", "D3_operator_procedure", "D4_changelog_and_version",
                "D6_api_due_overdue", "miss"):
        row(f"M8 {key}", lambda run, key=key: run["M8_docs_product"][key])
    row("M8 D5 new decision records", lambda run: ", ".join(run["M8_docs_product"]["D5_new_decision_records"]) or "none")
    row("M9 new settings", lambda run: ", ".join(run["M9_setup_product"]["new_settings"] + run["M9_setup_product"]["new_config_files"]) or "none")
    row("M9 setup miss", lambda run: run["M9_setup_product"]["miss"])
    for name in ("migrate-before", "switchover"):
        row(f"binds: {name}", lambda run, name=name: "yes" if run["binding"][name]["binds"] else
            "no (" + ", ".join(k for k in ("a_applies", "b_acted", "c_product") if not run["binding"][name][k]) + ")")
    row("validity: EADDRINUSE", lambda run: run["validity"]["EADDRINUSE"])
    row("validity: port 4180 starts", lambda run: run["validity"]["port_4180_start"])
    lines += ["", "| # | Prediction | Probability | n | Outcome |", "|---|---|---|---|---|"]
    for pred in preds:
        lines.append(f"| {pred['id']} | {pred['prediction']} | {pred['probability']}% | {pred['population']} | "
                     f"{'held' if pred['held'] else 'missed as written'} |")
    return "\n".join(lines) + "\n"


def main(argv) -> int:
    if not argv:
        print(__doc__)
        return 2
    runs = [score(pathlib.Path(arg).expanduser().resolve()) for arg in argv]
    preds = predictions(runs)
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "scores.json").write_text(json.dumps({"runs": runs, "predictions": preds}, indent=1) + "\n")
    text = table(runs, preds)
    (EVIDENCE / "scores.md").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
