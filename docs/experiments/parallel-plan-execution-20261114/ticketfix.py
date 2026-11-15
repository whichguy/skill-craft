#!/usr/bin/env python3
"""ticketfix.py: the real-repository fixture of journal entry E17 (README Amendment A14): three independent feature requests on the E2E
harness's brownfield base, a teammate's change that lands on main while the workers work, and the hidden oracle (apparatus).

Apparatus for docs/experiments/parallel-plan-execution-20261114. E13's write fixture was four toy functions in files of a few hundred
bytes. This one is a real service (``test/shiploop_e2e/fixtures/node-tickets``: about 1,700 lines of source, 117 tests, eight decision
records) and three real requests, the E2E cases ``ticket-assignment``, ``ticket-import`` and ``ticket-due-times``, whose own acceptance checks
are the oracle. The harness's files are read here, never changed. It holds

  FEATURES        the three tasks (T1 assignment, T2 import, T3 due times) and the E2E case each one is
  make_repo       writes the base files and makes the base commit every worker starts from
  plan            the ppe-plan/v1 plan of the three tasks (frozen into plans/tickets3.json by ``--write-plan``)
  apply_landing   the teammate's change: the store's creating method is renamed (create -> createTicket) at every call site
  landing_patch   that change as a unified diff of the base (frozen into real-repo/landing.patch by ``--write-landing``)
  evaluate        the oracle's verdict on a finished trial: each feature's acceptance checks on the final tree and, in an isolated run, on
                  each task's first branch alone; the interaction checks (real-repo/interactions.py) on the final tree

  python3 ticketfix.py --selfcheck      the base, the landing and the oracle behave as they should (no model call)
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
E2E = REPO / "test" / "shiploop_e2e"
BASE_FIXTURE = E2E / "fixtures" / "node-tickets"
CASES = E2E / "cases.json"
CHECKS = E2E / "checks"
ASSIGNED_BASE = E2E / "fixtures" / "node-tickets-assigned"   # the base with assignment (T1) in it: what "as today" means for a tree that has T1
REAL = HERE / "real-repo"
GIT = ["git", "-c", "user.name=ppe", "-c", "user.email=ppe@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
       "-c", "maintenance.auto=false", "-c", "gc.auto=0"]

FEATURES = (("T1", "ticket-assignment"), ("T2", "ticket-import"), ("T3", "ticket-due-times"))
LANDING_MESSAGE = "refactor(store): name the creating method for what it creates (create -> createTicket)"

TASK = ("Work only inside the workspace {ws}: the help-desk ticket service your task describes is the git checkout there (every path is relative to it, "
        "and 'this directory' below means {ws}); do not touch any other directory and do not run git: the kit saves your work. "
        "{prompt} "
        "Run the tests with `npm test` inside {ws} (it runs `node --test`) and fix your work until every test passes. "
        "Report as the integer answer the number of tests that `npm test` reports as passed (its `pass` line).")


def git(cwd, *args) -> tuple[int, str]:
    done = subprocess.run(GIT + ["-C", str(cwd)] + list(args), capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return done.returncode, done.stdout + done.stderr


def base_files(folder: Path) -> list[Path]:
    sys.path.insert(0, str(E2E))
    import brownfield   # noqa: PLC0415  (the harness's own list of a base's files: no node_modules, no compiled files)
    return brownfield.base_files(folder)


def make_repo(dest: Path) -> str:
    """Write the base into ``dest`` and commit it; returns the base commit."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for source in base_files(BASE_FIXTURE):
        target = dest / source.relative_to(BASE_FIXTURE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    subprocess.run(GIT + ["-C", str(dest), "init", "-q", "-b", "main"], check=True, capture_output=True)
    git(dest, "add", "-A")
    rc, out = git(dest, "commit", "-q", "-m", "base: the help-desk ticket service")
    if rc != 0:
        raise SystemExit("the base commit failed: " + out.strip())
    return git(dest, "rev-parse", "HEAD")[1].strip()


def case_prompt(case: str) -> str:
    cases = json.loads(CASES.read_text())
    cases = cases if "ticket-comments" in cases else cases.get("cases", cases)
    return cases[case]["prompt"]


def case_checks(case: str) -> list[str]:
    cases = json.loads(CASES.read_text())
    cases = cases if "ticket-comments" in cases else cases.get("cases", cases)
    return list(cases[case]["checks"])


def plan() -> dict:
    steps = [{"id": sid, "task": TASK.replace("{prompt}", case_prompt(case)), "deps": [], "criteria": [f"C-{sid}"], "proof": f"test -s out/{sid}.json",
              "paths": ["*"], "kit": {"mode": "task"}} for sid, case in FEATURES]
    return {"schema": "ppe-plan/v1", "name": "tickets3", "fixture": "tickets", "expected_verdict": "OK",
            "description": "three independent feature requests on a real service, in overlapping files (README Amendment A14)", "steps": steps}


# ------------------------------------------------------------------ the teammate's change

def apply_landing(tree: Path) -> list[str]:
    """Rename the store's creating method at its definition and every call site under src/, bin/ and test/; returns the files changed."""
    changed = []
    call = re.compile(r"\b(store|tickets|again)\.create\(")
    definition = re.compile(r"^(  )create\(\{ title, priority, requester \}, actor\) \{$", re.M)
    for folder in ("src", "bin", "test"):
        for path in sorted((tree / folder).rglob("*.js")):
            text = path.read_text()
            new = call.sub(r"\1.createTicket(", text)
            if path.name == "store.js":
                new = definition.sub(r"\1createTicket({ title, priority, requester }, actor) {", new)
            if new != text:
                path.write_text(new)
                changed.append(str(path.relative_to(tree)))
    return changed


def landing_patch() -> str:
    """The landing as a unified diff of the base (``git apply --index`` applies it to a checkout of the base)."""
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "w"
        make_repo(work)
        apply_landing(work)
        return git(work, "diff", "--no-color")[1]


def base_after_landing(dest: Path) -> Path:
    """The base with the landing applied, as plain files: the base the final tree's own-tests checks compare with once the landing has landed."""
    dest = Path(dest)
    for source in base_files(BASE_FIXTURE):
        target = dest / source.relative_to(BASE_FIXTURE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    apply_landing(dest)
    return dest


# ------------------------------------------------------------------ the oracle

TRANSIENT = re.compile(r"EADDRINUSE|ECONNRESET|ECONNREFUSED|EPIPE|socket hang up")   # an error string of the machine's network, not proof of its cause
INTERACTION_IDS = ("I1", "I2", "I3", "I4", "I5")
PROVENANCE_CHECKS = ("base_tests.py", "serve.py", "due_times_probe.py", "ticket_assignment_accept.py", "ticket_import_accept.py")


def provenance() -> dict:
    """What the oracle is made of, hashed at launch: a later change to any of these files is visible in the trial's record."""
    import hashlib
    sys.path.insert(0, str(E2E))
    import brownfield   # noqa: PLC0415
    cases = json.loads(CASES.read_text())
    cases = cases if "ticket-comments" in cases else cases.get("cases", cases)
    entries = json.dumps({case: cases[case] for _, case in FEATURES}, sort_keys=True)
    files = {"ticketfix.py": HERE / "ticketfix.py", "dagkit.py": HERE / "dagkit.py", "interactions.py": REAL / "interactions.py",
             "landing.patch": REAL / "landing.patch", "plans/tickets3.json": HERE / "plans" / "tickets3.json", "quality.py": E2E / "quality.py"}
    files.update({f"checks/{name}": CHECKS / name for name in PROVENANCE_CHECKS})
    files["listeners.py"] = E2E / "listeners.py"
    out = {name: hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.is_file() else None for name, path in files.items()}
    out["cases (the three requests, their checks and acceptance blocks)"] = hashlib.sha256(entries.encode()).hexdigest()[:16]
    out["fixture digest"] = brownfield.digest(BASE_FIXTURE)
    status = subprocess.run(["git", "-C", str(REPO), "status", "--short", "--", "docs/experiments/parallel-plan-execution-20261114", "test/shiploop_e2e"],
                            capture_output=True, text=True).stdout.strip()
    out["skill-craft HEAD"] = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    out["dirty files under the study and the harness"] = status.splitlines()   # a clean worktree at a pushed commit is what the registered trials run from
    return out


def run_checks(tree: Path, case: str, base: Path | None = None, timeout: int = 300, with_assignment: bool = False, only: str | None = None) -> list[dict]:
    """The case's own checks run from ``tree`` the way the harness runs them (E2E_CHECKS set, a shell, exit 0 is a pass). ``only`` is ``"behavior"``
    (the request's own HTTP or probe checks), ``"global"`` (the two own-tests checks: the delivery's tests pass and outnumber the base's, and the base's
    own tests pass unchanged; they are about the whole tree, not about one feature) or None (all). A machine-level network error string (a port taken,
    a connection reset: seen when other sessions use the machine) is run again, at most twice, and every earlier output is kept. ``base`` stands in for
    the base folder of the two own-tests checks (the base with a landing applied). ``with_assignment`` is for a tree that holds assignment: due times'
    ``off`` check compares the delivered service with the base byte for byte (it ignores only times), so a tree whose tickets all show `assignee`
    can never pass it as written; for such a tree it is run against the base with assignment, the one pin changed."""
    env = dict(os.environ, E2E_CHECKS=str(CHECKS))
    rows = []
    for command in case_checks(case):
        is_global = "base_tests.py" in command
        if (only == "behavior" and is_global) or (only == "global" and not is_global):
            continue
        shown = command
        if with_assignment and case == "ticket-due-times" and command.rstrip().endswith('due_times_probe.py" off'):
            command = "python3 -c " + shlex.quote(f"import sys, pathlib; sys.path.insert(0, {str(CHECKS)!r}); import due_times_probe as p; "
                                                   f"p.BASE = pathlib.Path({str(ASSIGNED_BASE)!r}); raise SystemExit(p.main(['off']))")
            shown += " [against the base with assignment]"
        if base is not None and is_global:
            command = command.replace(" node-tickets", " " + shlex.quote(str(base)))
        earlier = []
        for tries in (1, 2, 3):
            try:
                done = subprocess.run(["bash", "-c", command], cwd=tree, env=env, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
                rc, text = done.returncode, (done.stdout + done.stderr)
            except subprocess.TimeoutExpired:
                rc, text = 124, "timed out"
            if rc == 0 or not TRANSIENT.search(text) or tries == 3:
                break
            earlier.append(" ".join(text.split())[-200:])
        rows.append({"command": shown[:90], "kind": "global" if is_global else "behavior", "pass": rc == 0, "tries": tries, "earlier": earlier,
                     "output": " ".join(text.split())[-240:]})
    return rows


def run_acceptance(tree: Path, case: str) -> list[dict]:
    """The case's held-out acceptance checks, run the way the harness runs them (``quality.acceptance`` on a copy of the tree): black-box checks written
    from the request and the base's documents and never shown to a worker (18 for assignment, 13 for import; due times has none, its probes are its
    acceptance). A check that could not be measured counts as failing. A run whose failing notes show a network error string of the machine is run
    again, at most twice, and the earlier failing ids are kept."""
    cases = json.loads(CASES.read_text())
    cases = cases if "ticket-comments" in cases else cases.get("cases", cases)
    block = (cases[case].get("quality") or {}).get("acceptance")
    if not block:
        return []
    sys.path.insert(0, str(E2E))
    import quality   # noqa: PLC0415  (the harness's runner, used read-only)
    earlier = []
    for tries in (1, 2, 3):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "delivery"
            copy.mkdir()
            quality.export_delivery(tree, copy)
            result = quality.acceptance(copy, block, groups=set(), stop=lambda: None, logs=Path(tmp) / "logs", ports=())
        if "checks" not in result:
            rows = [{"id": "acceptance", "kind": "acceptance", "pass": False, "note": str(result.get("reason", "unobserved"))[:200]}]
        else:
            rows = [{"id": r["id"], "kind": "acceptance", "pass": r["pass"] is True, "note": str(r["note"])[:160]} for r in result["checks"]]
        bad = [r for r in rows if not r["pass"]]
        if not bad or not any(TRANSIENT.search(r["note"]) for r in bad) or tries == 3:
            break
        earlier.append([r["id"] for r in bad])
    for r in rows:
        r["tries"], r["earlier"] = tries, earlier
    return rows


def feature_rows(tree: Path, case: str, base: Path | None = None, with_assignment: bool = False) -> list[dict]:
    """What a feature must do, wherever it is checked: its request's own HTTP or probe checks, and its held-out acceptance checks if it has any."""
    return run_checks(tree, case, base, only="behavior", with_assignment=with_assignment) + run_acceptance(tree, case)


def suite_passed(tree: Path) -> int | None:
    done = subprocess.run(["npm", "test", "--silent"], cwd=tree, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
    found = re.findall(r"^(?:ℹ|#) pass (\d+)\s*$", done.stdout + done.stderr, re.M)
    return int(found[-1]) if found else None


def interactions(tree: Path) -> dict:
    """The interaction checks (real-repo/interactions.py: exactly I1 to I5). The oracle fails closed: a missing module stops the scoring, and a checker that
    printed anything but the five results, or exited non-zero without failing a check, leaves an ``error`` that makes the trial invalid."""
    module = REAL / "interactions.py"
    if not module.is_file():
        raise SystemExit(f"the interaction checks are missing: {module}")
    done = subprocess.run([sys.executable, str(module), "check", str(tree)], capture_output=True, text=True, timeout=900, stdin=subprocess.DEVNULL)
    try:
        found = json.loads(done.stdout)
    except ValueError:
        return {"error": "the checker printed no result: " + (done.stdout + done.stderr)[-300:], "rc": done.returncode}
    if not isinstance(found, dict) or set(found) - {"error"} != set(INTERACTION_IDS) or "error" in found:
        found = {**found, "error": found.get("error") or f"expected exactly {', '.join(INTERACTION_IDS)}, got {sorted(found)}"}
    found["rc"] = done.returncode
    return found


def interactions_ok(found: dict) -> bool:
    return "error" not in found and all(isinstance(found.get(k), dict) and found[k].get("ok") is True for k in INTERACTION_IDS)


def evaluate(trial: Path, meta: dict, events: list, candidates: bool = True) -> dict:
    """The verdict on a finished trial. Valid when every feature's behavior checks (its request's own checks and its held-out acceptance checks) pass
    on the final tree, the whole tree's own-tests checks pass (the delivery's tests pass and outnumber the base's, the base's own tests pass unchanged),
    and exactly the five interaction checks pass. In an isolated run each task's first branch, as the worker delivered it before any merge (checked only
    when it forked the original base), is checked too: a feature whose behavior passes alone and fails in the final tree was broken by the combination
    (interference). The whole-tree checks are kept apart so that one task's broken test is not charged to the others. ``candidates`` also looks, offline,
    at the exact tree of every attempted integration (what the re-test decided, and whether it was right)."""
    repo = Path(meta["repo"])
    landed = any(e["kind"] == "landed" and e["detail"].get("ok") for e in events)
    base = None
    if landed:
        base = trial / "oracle" / "base-after-landing"
        if not base.is_dir():
            base_after_landing(base)
    root = git(repo, "rev-list", "--max-parents=0", "HEAD")[1].split()[0]
    whole = run_checks(repo, FEATURES[0][1], base, only="global")
    final = {sid: feature_rows(repo, case, base, with_assignment=True) for sid, case in FEATURES}
    ok_final = {sid: all(r["pass"] for r in rows) for sid, rows in final.items()}
    alone, ok_alone, skipped, alone_whole = {}, {}, {}, {}
    for sid, case in FEATURES:
        first = [e["detail"] for e in events if e["kind"] == "workspace" and e["step"] == sid and e["detail"].get("attempt") == 1 and e["detail"].get("mode") == "isolated"]
        committed = any(e["kind"] == "commit" and e["step"] == sid and e["detail"].get("attempt") == 1 for e in events)
        if not (first and committed and Path(first[0]["path"]).is_dir()):
            continue
        if first[0].get("base") != root:   # a late first start forked from main with the landing or another feature in it: not an isolated implementation
            skipped[sid] = "the first workspace did not fork the original base"
            continue
        alone[sid] = feature_rows(Path(first[0]["path"]), case)
        ok_alone[sid] = all(r["pass"] for r in alone[sid])
        alone_whole[sid] = all(r["pass"] for r in run_checks(Path(first[0]["path"]), case, None, only="global"))
    inter = interactions(repo)
    inter_ok = interactions_ok(inter)
    old_name = subprocess.run(["grep", "-rnE", r"\b(store|tickets|again)\.create\(|^  create\(", "src", "bin", "test"], cwd=repo, capture_output=True, text=True).stdout.splitlines()
    out = {"valid": all(ok_final.values()) and all(r["pass"] for r in whole) and inter_ok, "features_ok": ok_final, "whole_tree_ok": all(r["pass"] for r in whole),
           "alone_ok": ok_alone, "alone_skipped": skipped, "alone_whole_tree_ok": alone_whole,
           "interference": sorted(s for s in ok_alone if ok_alone[s] and not ok_final[s]), "interactions": inter, "interactions_ok": inter_ok,
           "suite_passed": suite_passed(repo), "landed": landed, "old_name_remaining": len(old_name) if landed else None, "whole_tree": whole, "final": final, "alone": alone,
           "root": root}
    if candidates:
        out["candidates"] = evaluate_candidates(repo, events, base)
    return out


def evaluate_candidates(repo: Path, events: list, base: Path | None) -> list[dict]:
    """The exact tree of every attempted clean integration, looked at after the run: for each ``merged`` (the re-test was green) and ``redtest`` (it was
    red) event, the behavior checks of the features that were in main then plus the one being merged. A green candidate that fails a behavior check is a
    defect the re-test missed; a red one that passes them all is a red the features' behavior does not explain (a test that pinned a shape, say)."""
    out, merged_before = [], []
    for e in events:
        d = e["detail"]
        if e["kind"] == "merged" and d.get("commit"):
            commit, kind, retest_ok = d["commit"], "merged", True
        elif e["kind"] == "redtest" and d.get("candidate"):
            commit, kind, retest_ok = d["candidate"], "redtest", False
        else:
            continue
        present = [s for s, _ in FEATURES if s in merged_before or s == e["step"]]
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "candidate"
            rc, why = git(repo, "worktree", "add", "-q", "--detach", str(tree), commit)
            if rc != 0:
                out.append({"step": e["step"], "attempt": d.get("attempt"), "kind": kind, "commit": commit, "error": why.strip()[-200:]})
            else:
                rows = {sid: feature_rows(tree, case, None, with_assignment="T1" in present) for sid, case in FEATURES if sid in present}
                git(repo, "worktree", "remove", "--force", str(tree))
                out.append({"step": e["step"], "attempt": d.get("attempt"), "kind": kind, "commit": commit, "retest_ok": retest_ok, "present": present,
                            "behavior_ok": {sid: all(r["pass"] for r in r_) for sid, r_ in rows.items()},
                            "failing": [f"{sid}: {r.get('id') or r['command'][-40:]}" for sid, r_ in rows.items() for r in r_ if not r["pass"]]})
        if kind == "merged":
            merged_before.append(e["step"])
    return out


# ------------------------------------------------------------------ self-check

def selfcheck() -> int:
    failures = []

    def expect(name, ok, detail=""):
        print(("ok   " if ok else "FAIL ") + name + (f"  {detail}" if detail and not ok else ""))
        if not ok:
            failures.append(name)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        repo = tmp / "base"
        head = make_repo(repo)
        expect("the base commit exists", len(head) == 40, head)
        base_count = suite_passed(repo)
        expect("the base's own tests pass (117)", base_count == 117, str(base_count))
        p = plan()
        expect("the plan names the three tasks with no dependency", [s["id"] for s in p["steps"]] == ["T1", "T2", "T3"] and all(s["deps"] == [] for s in p["steps"]))
        expect("every task text has the workspace slot and the request", all("{ws}" in s["task"] and "Add" in s["task"] or "Each ticket" in s["task"] for s in p["steps"]))
        patch = landing_patch()
        expect("the landing is a non-empty diff of the base", patch.startswith("diff --git") and patch.count("\n+") > 20, f"{len(patch)} bytes")
        patch_file = tmp / "landing.patch"
        patch_file.write_text(patch)
        rc, out = git(repo, "apply", "--check", str(patch_file))
        expect("the landing applies to the base", rc == 0, out)
        rc, out = git(repo, "apply", "--index", str(patch_file))
        git(repo, "commit", "-q", "-m", LANDING_MESSAGE)
        landed_count = suite_passed(repo)
        expect("the base's tests still pass after the landing (117)", rc == 0 and landed_count == 117, f"{rc} {landed_count}")
        expect("no call of the old name is left", subprocess.run(["grep", "-rnE", r"\b(store|tickets|again)\.create\(", "src", "bin", "test"], cwd=repo, capture_output=True).returncode == 1)
        after = base_after_landing(tmp / "after")
        pristine = subprocess.run(["bash", "-c", f'python3 "$E2E_CHECKS/base_tests.py" pristine {shlex.quote(str(after))}'], cwd=repo, env=dict(os.environ, E2E_CHECKS=str(CHECKS)), capture_output=True, text=True)
        expect("the harness's own-tests check accepts the landed tree against the landed base", pristine.returncode == 0, (pristine.stdout + pristine.stderr)[-200:])
        fresh = tmp / "fresh"
        make_repo(fresh)
        for sid, case in FEATURES:
            rows = feature_rows(fresh, case)
            expect(f"the bare base fails {sid}'s behavior checks (the feature is absent)", not all(r["pass"] for r in rows), json.dumps([r["pass"] for r in rows]))
        acc = {case: run_acceptance(fresh, case) for _, case in FEATURES}
        expect("the held-out acceptance checks are there: 18 for assignment, 13 for import, none for due times",
               (len(acc["ticket-assignment"]), len(acc["ticket-import"]), len(acc["ticket-due-times"])) == (18, 13, 0),
               str((len(acc["ticket-assignment"]), len(acc["ticket-import"]), len(acc["ticket-due-times"]))))
        failing = {case: sum(1 for r in rows if not r["pass"]) for case, rows in acc.items()}
        expect("the bare base fails most of them (they test what the base lacks) and passes its pass-to-pass ones",
               0 < failing["ticket-assignment"] < 18 and 0 < failing["ticket-import"] < 13, str(failing))
        composed = tmp / "composed"
        make_repo(composed)
        if (REAL / "refs" / "composed.patch").is_file():
            rc, out = git(composed, "apply", str(REAL / "refs" / "composed.patch"))
            expect("the composed reference applies to the base", rc == 0, out)
            ok = {case: all(r["pass"] for r in feature_rows(composed, case, None, with_assignment=True)) for _, case in FEATURES}
            expect("the composed reference passes every feature's behavior checks, acceptance included", all(ok.values()), json.dumps(ok))
        expect("the provenance hashes the oracle's files and names the commit", all(v for k, v in provenance().items() if k != "dirty files under the study and the harness"))
    print("SELFCHECK " + ("OK" if not failures else "FAILED: " + "; ".join(failures)))
    return 0 if not failures else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--selfcheck", action="store_true")
    parser.add_argument("--write-plan", action="store_true", help="write plans/tickets3.json")
    parser.add_argument("--write-landing", action="store_true", help="write real-repo/landing.patch")
    args = parser.parse_args(argv)
    if args.write_plan:
        (HERE / "plans" / "tickets3.json").write_text(json.dumps(plan(), indent=1) + "\n")
        print("wrote plans/tickets3.json")
    if args.write_landing:
        REAL.mkdir(exist_ok=True)
        (REAL / "landing.patch").write_text(landing_patch())
        print("wrote real-repo/landing.patch")
    if args.selfcheck:
        return selfcheck()
    return 0


if __name__ == "__main__":
    sys.exit(main())
