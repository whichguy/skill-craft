#!/usr/bin/env python3
"""Freeze the E-EFF1 manifest (docs/shiploop-effort-by-stage-experiment-plan-2026-10-24.md, section 4 R0.7).

    python3 -B docs/experiments/shiploop-effort-by-stage-20261024/freeze_manifest.py [--check]

Writes manifest.json and manifest.sha256 beside this file: the scenarios, the class list, both schedules, the arm order
draw, the 16 run commands, the harness file hashes, the plugin and host pins, the judge and the analysis command. The hash
covers the manifest without its own `sha256` field. Refuses to overwrite a manifest once a run folder of the experiment
exists (a frozen text must not change after the first decision-round run). `--check` recomputes the hashes of the files the
manifest names and says which changed since the freeze.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
import time
from pathlib import Path

EXP = Path(__file__).resolve().parent
ROOT = EXP.parents[2]
RUNS = Path("/Users/dadleet/e2e-runs/effort-eeff1")
# The checkout R2 runs from: a worktree at the 2.9.0 release commit with the experiment's changes applied uncommitted
# (sync/make_r2_harness.sh). The canonical checkout is not the harness: it moves under the experiment.
_ROOT_FILE = EXP / "sync" / "r2-harness-root.txt"
HARNESS_ROOT = Path(_ROOT_FILE.read_text().strip()) if _ROOT_FILE.exists() else ROOT
PLAN = ROOT / "docs" / "shiploop-effort-by-stage-experiment-plan-2026-10-24.md"
ORDER_SEED = 20261024  # the date, so the draw is a fact of the plan and not a choice made after seeing anything
# The eight scenarios of plan section 3 and why each is in. The Claude seconds come from cost/b-grok-time-estimate.json.
SCENARIOS = [
    ("hello", "smallest full run; 15 Claude rows"),
    ("seat-reservations", "a service with state; legacy rows only"),
    ("battleship-scoring", "a heavier service; 1 Claude row"),
    ("csv-report", "a file-processing tool; legacy rows only"),
    ("unit-converter", "parallel-graph case; no baseline row"),
    ("word-report", "parallel-graph case; no baseline row"),
    ("temperature-report", "Ask-Agent delegation; no current baseline row"),
    ("temperature-plain", "inline counterpart of temperature-report; no baseline row"),
]
HARNESS = ("run.py", "slice.py", "effort.py", "sessionlog.py", "hosts.py", "metrics.py", "clear.py")
SUITE = HARNESS_ROOT / "skills" / "rubric-eval" / "suites" / "shiploop-run"
DECISION_RULE = ("skills/rubric-eval/SPEC.md section 8: near-identical quality first (interval inside the judge's measured "
                 "noise, three passes): fewer tokens that are significant (95% cluster bootstrap and Wilcoxon signed-rank "
                 "over per-scenario means, both agreeing), then less time; a material quality difference trumps; a tie keeps "
                 "the control; fewer than 8 scenarios blocks a win")


def sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def payload_digest() -> str | None:
    """The harness's own digest (run.tree_digest_checked) of the pinned worktree's plugins/skill-craft: the tree a host loads."""
    code = ("import sys; sys.dont_write_bytecode=True; sys.path.insert(0,'test/shiploop_e2e'); import run; "
            "d,w=run.tree_digest_checked(__import__('pathlib').Path('plugins/skill-craft').resolve()); print(d or '')")
    done = subprocess.run(["python3", "-B", "-c", code], cwd=HARNESS_ROOT, capture_output=True, text=True)
    return done.stdout.strip() or None


def canonical(manifest: dict) -> bytes:
    body = {k: v for k, v in manifest.items() if k != "sha256"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def build() -> dict:
    cost = json.loads((EXP / "cost" / "b-grok-time-estimate.json").read_text())
    claude = cost["claude_seconds_per_case"]
    restated = json.loads((EXP / "cost" / "e-r2-time-restated.json").read_text())
    grok = restated["central"]
    upper = restated["high"]
    lower = restated["low"]
    schedules = {arm: json.loads((EXP / f"{'control' if arm == 'control' else 'treatment'}.json").read_text())
                 for arm in ("control", "treatment")}
    rng = random.Random(ORDER_SEED)
    scenarios, runs = [], []
    for case, why in SCENARIOS:
        arms = ["control", "treatment"]
        rng.shuffle(arms)
        scenarios.append({"case": case, "why": why, "arm_order": arms,
                          "claude_seconds": claude[case]["seconds"], "claude_basis": claude[case]["basis"],
                          "grok_seconds_estimate": grok["per_case_seconds"][case],
                          "grok_seconds_low_estimate": lower["per_case_seconds"][case],
                          "grok_seconds_high_estimate": upper["per_case_seconds"][case]})
        for arm in arms:
            out = RUNS / f"{arm}-{case}"
            runs.append({"id": f"{arm}-{case}", "case": case, "arm": arm, "output": str(out),
                         "baseline": str(EXP / f"baselines-{arm}.jsonl"),
                         "cwd": str(HARNESS_ROOT),
                         "argv": ["python3", "-B", "test/shiploop_e2e/run.py", "--case", case, "--host", "grok",
                                  "--model", "grok-4.7", "--effort-schedule", str(EXP / f"{arm}.json"),
                                  "--baseline", str(EXP / f"baselines-{arm}.jsonl"), "--output", str(out),
                                  "--timeout", "10800", "--source", "checkout",
                                  "--plugin-dir", str(HARNESS_ROOT / "plugins" / "skill-craft")]})
    preflight = (EXP / "preflight-grok.txt").read_text().strip() if (EXP / "preflight-grok.txt").exists() else None
    judges = json.loads((HARNESS_ROOT / "skills/rubric-eval/references/judges.json").read_text())
    grok_build = subprocess.run(["grok", "--version"], capture_output=True, text=True).stdout.strip()
    python3_version = subprocess.run(["python3", "--version"], capture_output=True, text=True).stdout.strip()
    python3_path = subprocess.run(["python3", "-I", "-c", "import sys; print(sys.executable)"], capture_output=True,
                                  text=True).stdout.strip()
    return {
        "id": "E-EFF1", "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "plan": {"path": str(PLAN.relative_to(ROOT)), "sha256": sha256(PLAN)},
        "question": "does low effort on mechanical stages and Improve passes 2+ cut tokens and time without a material loss "
                    "of quality?",
        "decision_rule": DECISION_RULE,
        "classes": {"M": ["prepare", "system-test", "product-acceptance", "release-check", "release", "release-verify",
                          "operations"],
                    "I2": "an Improve child's pass n >= 2: the Until Loop receipt packet is active with "
                          "progress.action_number >= 2 (effort.running_pass)",
                    "D": "every other position, Improve pass 1 and handoff included"},
        "schedules": {**schedules, "files": {a: {"path": str((EXP / f"{a}.json").relative_to(ROOT)),
                                                  "sha256": sha256(EXP / f"{a}.json")} for a in schedules}},
        "blocking": "both arms restart the session at every change of class; the control schedule names one level three times",
        "subject": {"host": "grok", "model": "grok-4.7", "host_build": grok_build,
                    "levels": {"control": "medium everywhere", "treatment": "low on M and I2, medium on D"},
                    "fallback": "codex gpt-6-luna xhigh against low if Grok credits are out; claude is exploratory only"},
        "harness_checkout": {"root": str(HARNESS_ROOT), "cwd_for_runs": str(HARNESS_ROOT),
                             "base_commit": subprocess.run(["git", "-C", str(HARNESS_ROOT), "rev-parse", "HEAD"], capture_output=True,
                                                           text=True).stdout.strip(),
                             "base_is": "the skill-craft 2.9.0 / ShipLoop 1.9.0 release commit (31933a73), a published ancestor of origin/main",
                             "overlay": "the experiment's changes applied uncommitted: sync/tracked-changes.patch (7 tracked files), "
                                        "effort.py, the shiploop-run suite, run_totals.py",
                             "overlay_patch_sha256": sha256(EXP / "sync" / "tracked-changes.patch"),
                             "recipe": "docs/experiments/shiploop-effort-by-stage-20261024/sync/make_r2_harness.sh",
                             "why_not_the_canonical_checkout": "another session rebased it onto origin/main on 2026-10-24 (autostash kept the "
                                 "uncommitted work); 13 more harness commits changing run.py and cases.json are due; the harness imports "
                                 "ShipLoop's modules from its own checkout, so it must match the plugin under test"},
        "plugin": {"source": "checkout", "plugin_dir": str(HARNESS_ROOT / "plugins" / "skill-craft"),
                   "release_commit": "31933a73", "versions": {"skill_craft": "2.9.0", "shiploop": "1.9.0"},
                   "payload_sha256": payload_digest(),
                   "chosen_by": "the owner, 2026-10-25: R2 on --source checkout from the pinned worktree at 31933a73",
                   "is_the_marketplace_payload": "plugins/skill-craft is identical between 31933a73 and origin/main (checked at "
                       "e707b794): the marketplace serves origin/main's plugins/skill-craft byte for byte, so --plugin-dir at it tests "
                       "the 2.9.0 marketplace payload with no gate and no drift",
                   "why_plugin_dir": "the default checkout build also packs the experiment's rubric-eval overlay (3 paths under "
                                     "skills/rubric-eval; digest 4dd13076c669): sync/plugin-build-comparison.json",
                   "gate": "none for --source checkout; the marketplace gate was REFUSING when frozen (3 unreleased change notes on "
                           "origin/main), which no longer matters",
                   "launch_guard": "before every run: git -C harness root rev-parse HEAD is 31933a73, freeze_manifest.py --check is "
                                   "clean, and the payload digest equals payload_sha256; after launch the run's invocation.json "
                                   "versions.plugin_sha256 must equal it (a run on any other build is not an R2 run)",
                   "marketplace_state_when_frozen": (EXP / "preflight-grok-2.9.0-gate.txt").read_text().strip()
                   if (EXP / "preflight-grok-2.9.0-gate.txt").exists() else None,
                   "earlier_preflight_2.8.0": preflight},
        "harness": {name: sha256(HARNESS_ROOT / "test" / "shiploop_e2e" / name) for name in HARNESS},
        "analysis_scripts": {name: sha256(EXP / name) for name in ("run_totals.py",)},
        "scenarios": scenarios, "order_seed": ORDER_SEED, "trials": 1, "runs": runs,
        "run_rules": ["run from the pinned harness checkout (harness_checkout.root), never from the canonical checkout",
                      "check plugin.launch_guard before every launch; the queue stops, it does not continue on another build",
                      "run_in_background with run.py --resume-run after the background limit, never nohup",
                      "at most two runs at a time; the two arms of one scenario are adjacent in the queue",
                      "no engine change, release or restart of a run mid-batch; an unfinished run is a recorded outcome",
                      "a progress monitor re-armed every 30 minutes", "separate --baseline file per arm"],
        "judge": {"model": "claude:claude-opus-5-5@medium", "passes": 3, "one_judge": True,
                  "suite": str(SUITE.relative_to(ROOT)),
                  "suite_sha256": {p.name: sha256(p) for p in sorted(SUITE.glob("*")) if p.is_file()},
                  "recorded_reliability": judges},
        "metrics": {"tokens": "prompt plus output as the CLI reports them, summed over a run's model calls (run_totals.py): "
                              "prompt = input_tokens + cache_read_input_tokens + cache_creation_input_tokens; output "
                              "includes reasoning. Output alone and reasoning are reported beside it.",
                    "seconds": "host session span per run, the sum of end minus start in sessions.jsonl",
                    "quality": "Q1 script gates (run verdicts, refusals, SPEC flips, ledger obligations, tree-digest "
                               "agreement of Improve passes) and Q2 shiploop-run rubric percent per artifact, mean per "
                               "scenario, three judge passes",
                    "unit": "the scenario (8); an artifact carries its run's totals so the per-scenario mean is the run's",
                    "class_measures": "beside the totals, same tests: tokens and seconds of the M-class sessions per scenario "
                                      "(every run visits the same mechanical stages) and of the I2-class sessions where a run "
                                      "reached pass 2 (a run with none is left out, never zero); per-call reasoning and output "
                                      "tokens by class are descriptive",
                    "reading_rule": "the run totals decide, as the decision rule says. A class measure does not decide. If the "
                                    "totals are inconclusive and quality is near-identical, a significant saving in the M class "
                                    "is reported as 'mechanism seen, total not detectable at 8 scenarios' and the owner decides "
                                    "whether more scenarios are worth it",
                    "refusals": "the refusal gate counts navigator refusals per run minus restart-induced ones (an improve-pass "
                                "refusal of the two kinds R1 showed, in a session started for a boundary); both counts are "
                                "reported for each arm"},
        "analysis": [
            "import_run.py collect <the 8 run folders of one arm> --out pool-<arm>.jsonl",
            "run_totals.py tokens pool-<arm>.jsonl --out tokens-<arm>.json   (run totals; also --class M and --class I2 "
            "into tokens-<arm>-M.json and tokens-<arm>-I2.json)",
            "import_run.py place RUN --pool pool-<arm>.jsonl --arm control|treatment --condition grok:grok-4.7 "
            "--tokens tokens-<arm>.json   (both arms into one RUN folder; repeat into RUN-M and RUN-I2 with the class "
            "token files for the beside analyses)",
            "rubric-eval judge RUN --model opus --dest judge_p1 ; again for judge_p2 and judge_p3 (one loop at a time)",
            "rubric-eval analyze RUN --baseline control --judge-dir judge_p1,judge_p2,judge_p3   (decides)",
            "run_totals.py refusals <each run folder>   (the refusal gate, restart-induced apart)"],
        "limits": ["Improve reviews were all at the ceiling in the acceptance set, so the judged score may not separate a "
                   "weaker low-effort review; Q1 gates and the R3 replay carry I2 quality",
                   "arms pair by order within case and slot: a pass that exists in one arm only is dropped from the quality "
                   "comparison, its cost stays in the run totals",
                   "with fewer than 3 judge passes analyze falls back to another judge row's noise; the plan uses 3",
                   "the acceptance set mixed Grok and Claude artifacts and made no comparison",
                   "Grok per-run time is uncertain: hello took 4,340 s and 4,504 s at two at a time in R1 (1.7x the earlier "
                   "estimate); the other seven scenarios are scaled from it or from older runs",
                   "R1 saw run-to-run variance in the unchanged class (reasoning per call +24%, seconds +18%) several times the "
                   "M-class effect, so the run totals may not resolve it at 8 scenarios; that is why class measures are reported",
                   "a restart-induced refusal rule can hide a real improve-pass error in a restart session; same in both arms",
                   "the `committed` verdict differed between two R1 runs of one case and is not shown to be effort-related"],
        "unresolved_before_r2": ["a Grok window: another session's E6 batch (32 slices, 4 lanes, from about 22:50, 2.5 to 3 hours) "
                                 "and the other session's chess-salesforce run share the account; seconds are a measured quantity",
                                 "one 'write this pass's review' refusal per D to I2 boundary remains (attributed by rule)",
                                 "the blocked design (control restarting at treatment's positions) was last seen in R1; the "
                                 "chosen-id fix restores it and has not been run since",
                                 "four scenarios have no Claude timing and no Grok timing under 2.8.0",
                                 "a Grok window: another session's batch runs three concurrent slices; seconds are measured",
                                 "Opus judge seconds and tokens are not recorded by rubric-eval (acceptance: 123 calls, "
                                 "about 1.23M tokens in the agent's tally)",
                                 "committing skills/rubric-eval needs a changes/rubric-eval note or a No-Change-Note trailer"],
        "estimates": {"restated_after": "R1 (cost/e-r2-time-restated.json)",
                      "central": {"serial_hours": grok["serial_hours"], "two_at_a_time_hours": grok["two_at_a_time_hours"]},
                      "low": {"serial_hours": lower["serial_hours"], "two_at_a_time_hours": lower["two_at_a_time_hours"]},
                      "high": {"serial_hours": upper["serial_hours"], "two_at_a_time_hours": upper["two_at_a_time_hours"]},
                      "cli_reported_usd": restated["cli_reported_cost"],
                      "label": "estimates from one case (hello, 4,340 s and 4,504 s at two at a time); four scenarios have no "
                               "Claude timing; the Grok account is shared with other sessions' batches"},
        "environment": {"python3": python3_version, "python3_path": python3_path,
                        "note": "Homebrew replaced Python 3.14.7 with 3.14.9 and moved python3 to 3.15.1 at 18:33 on 2026-10-24; "
                                "R1 ran on 3.14.7; the plan-sizing session saw lazy stdlib imports fail in processes started "
                                "before the upgrade. The touched suites pass on 3.15.1 (slice 77 tests, e2e 433)."},
        "revision": {"n": 6, "after": "the owner chose --source checkout for R2 (journal section 16)",
                     "supersedes": [{"n": 1, "sha256": "2b4120c17fb092ba5d0e7f3424dffe245dae0ed54f86290134f7dc7c8bd52026"},
                                    {"n": 2, "sha256": "fb47d9d736d2bcb3ec50fc735b43324cfac1d9062c5f8c0141e86c6185a67962"},
                                    {"n": 3, "sha256": "177a6a334f4f9b450e6049fd303ddf3fd2a891ec9a63d6771a46380fff754390"},
                                    {"n": 4, "sha256": "815996c5b51f77b76520dc9ca402f7ef023f607dd0dafd151ec0cf576ffd379a"},
                                    {"n": 5, "sha256": "23dabea9c5564c8dd20a75343b9ddcb6399a4ad04323c53ec00376988dd336d9"}],
                     "changes": ["revision 6: the plugin under test is the committed 2.9.0 payload of the pinned worktree "
                                 "(--source checkout --plugin-dir), byte-identical to what the marketplace serves; the marketplace gate no "
                                 "longer applies; the launch guard checks the worktree HEAD, the harness hashes and the payload digest",
"revision 5: the plugin under test is the marketplace 2.9.0 build (31933a73), run from a pinned "
                                 "harness worktree at that commit with the experiment's changes uncommitted; the harness file hashes "
                                 "are of that worktree; a launch guard stops the queue if the marketplace moves past 2.9.0 or the gate refuses",
                                 "revision 4: the harness chooses the first Grok session's id (--session-id) and resumes by it, so a "
                                 "boundary before the first turn ends is resumable; the can_resume guard stays for other hosts",
                                 "revision 4: refusal fixes tested live: the hold removes the 'loop already ended' refusal, the "
                                 "restart note does not remove the 'write this pass's review' one (attributed by rule)",
                                 "revision 4: time and cost estimate updated with the second pair's hello timings",
                                 "revision 3: the interpreter is recorded (environment)",
                                 "revision 2 changes follow:","I2 class is held while the Improve loop is closing (effort.running_pass), so no boundary falls "
                                 "between the loop's completion and the model's complete call",
                                 "the session after a boundary is told nothing was undone (effort.RESTART_NOTE)",
                                 "restart-induced improve-pass refusals are attributed and kept out of the refusal gate "
                                 "(run_totals.py refusals)",
                                 "M-class and I2-class tokens and seconds per scenario are reported beside the run totals "
                                 "(run_totals.py classes; tokens --class)",
                                 "time and cost restated from R1"]},
    }


def check(manifest: dict) -> int:
    changed = []
    for name, digest in manifest["harness"].items():
        if sha256(HARNESS_ROOT / "test" / "shiploop_e2e" / name) != digest:
            changed.append(f"test/shiploop_e2e/{name} (in {HARNESS_ROOT.name})")
    if sha256(PLAN) != manifest["plan"]["sha256"]:
        changed.append(manifest["plan"]["path"])
    if manifest["plugin"].get("payload_sha256") and payload_digest() != manifest["plugin"]["payload_sha256"]:
        changed.append("the plugin payload under " + str(HARNESS_ROOT.name) + "/plugins/skill-craft")
    head = subprocess.run(["git", "-C", str(HARNESS_ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != manifest["harness_checkout"]["base_commit"]:
        changed.append(f"the harness worktree HEAD ({head[:8]})")
    for name, digest in manifest.get("analysis_scripts", {}).items():
        if sha256(EXP / name) != digest:
            changed.append(f"docs/experiments/shiploop-effort-by-stage-20261024/{name}")
    for a, info in manifest["schedules"]["files"].items():
        if sha256(ROOT / info["path"]) != info["sha256"]:
            changed.append(info["path"])
    for name, digest in manifest["judge"]["suite_sha256"].items():
        if sha256(SUITE / name) != digest:
            changed.append(f"{manifest['judge']['suite']}/{name}")
    again = hashlib.sha256(canonical(manifest)).hexdigest()
    print("manifest hash", "matches" if again == manifest.get("sha256") else "DOES NOT MATCH its recorded value")
    print("changed since the freeze:", ", ".join(changed) if changed else "nothing")
    return 0 if not changed and again == manifest.get("sha256") else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="compare the files the manifest names with their frozen hashes")
    args = parser.parse_args()
    path = EXP / "manifest.json"
    if args.check:
        return check(json.loads(path.read_text()))
    if RUNS.exists() and any(RUNS.iterdir()):
        raise SystemExit(f"{RUNS} holds a run of the experiment: a frozen manifest does not change after the first run")
    manifest = build()
    manifest["sha256"] = hashlib.sha256(canonical(manifest)).hexdigest()
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (EXP / "manifest.sha256").write_text(manifest["sha256"] + "\n")
    print(f"froze {path.relative_to(ROOT)}\nsha256 {manifest['sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
