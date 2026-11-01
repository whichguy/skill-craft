#!/usr/bin/env python3
"""Read the four live passes of chain B against the bar and the predictions the journal fixed before any run
(docs/shiploop-multipass-journal.md, "Round 5").

    python3 chain_b_readout.py [--as NAME=FOLDER ...] ROOT

ROOT holds the run folders under the names below; ``--as`` points a name at any other folder (it is how the instrument is checked, with no model
call, against saved runs whose numbers are known: E2's ``B1-ticket-assignment`` and ``B1-ticket-escalation`` as passes 1 and 2, E1 as pass 3 and E3 as pass 4,
and a saved ``user-listing`` run as pass 1). A bar line or a prediction is ``held``, ``missed`` or ``unknown`` (a run it needs is absent or a part
it reads was not recorded). Nothing is written. Each run is read through the ledger (test/shiploop_e2e/delta.py), ``round2_readout.one`` and
``round4_readout.read_run``, so the instrument does not depend on any change under test.

Chain B is user-listing (pass 1, a run on fixtures/node-base) and three links that follow it, each continuing the folder the pass before left:

    B1  user-listing     filtering and pagination of GET /users
    B2  user-roles       K2, a cross-cutting field: a role on every user, a role filter that combines with name
    B3  user-team-listing       K1, an additive link that must reuse the first request's rules: GET /teams "the way GET /users lists users"
    B4  user-page-size   K3, a link that changes an earlier rule: the default page size is PAGE_SIZE (25) and the largest size 50, for both listings
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "multipass-20261031"))
import round4_readout as r4  # noqa: E402

r2, delta, knowledge, verdict = r4.r2, r4.delta, r4.knowledge, r4.verdict

NAMES = ("B1-user-listing", "B2-user-roles", "B3-user-team-listing", "B4-user-page-size")
PASSES = dict(zip(("B1", "B2", "B3", "B4"), NAMES))
INHERITED_RULES = ("teams-name-filter", "teams-pages", "teams-page-defaults", "teams-size-bounds", "teams-bad-page-or-size")  # pass 3's checks that read the users' rules


def read_run(folder: Path | None) -> dict | None:
    """One pass through round4_readout.read_run, plus the cost, the versions it ran on, the footprint and the plan, and what the hidden checks said."""
    run = r4.read_run(folder)
    if run is None:
        return None
    metrics = json.loads((folder / "metrics.json").read_text())
    result = json.loads((folder / "result.json").read_text())
    try:
        versions = json.loads((folder / "invocation.json").read_text()).get("versions") or {}
    except (OSError, ValueError):
        versions = {}
    block = (delta.saved(folder) or {}).get("delta") or {}  # the saved block, or the one the ledger builds from the run folder for a run made before it existed
    footprint, plan = block.get("footprint") or {}, block.get("plan") or {}
    acceptance = (result.get("quality") or {}).get("acceptance") or {}
    checks = result.get("checks") or []
    run.update({
        "model_calls": metrics.get("model_calls"), "tokens": (metrics.get("tokens") or {}).get("processed"),
        "versions": (versions.get("plugin_version"), versions.get("shiploop_version"), versions.get("source")),
        "checks": (sum(1 for row in checks if row.get("pass")), len(checks)),
        "hidden_passed": (len(acceptance.get("passed") or []), len(acceptance.get("checks") or [])),
        "hidden_failed": [row["id"] for row in acceptance.get("checks") or [] if not row.get("pass")],
        "prior_tests_modified": footprint.get("prior_tests_modified"),
        "source_modified": (footprint.get("prior_source_modified"), footprint.get("prior_source_files")),
        "plan": plan, "env_sections_changed": ((block.get("placement") or {}).get("environment.md") or {}).get("changed_sections"),
    })
    return run


def kept_ids_cited(run: dict | None) -> int | None:
    """How many earlier requirements the run's step plans and test cases cite (the plan block's ``preserved``)."""
    if run is None or not run.get("plan"):
        return None
    return sum(((run["plan"].get(part) or {}).get("preserved") or 0) for part in ("step_plan_follows", "test_cases"))


def all_of(values: list) -> bool | None:
    return r4.all_of(values)


def minutes(run: dict | None) -> float | None:
    return None if run is None or run["seconds"] is None else round(run["seconds"] / 60, 1)


def main(argv: list[str]) -> int:
    args = list(argv)
    mapping: dict[str, Path] = {}
    while args and args[0] == "--as":
        args.pop(0)
        name, _, folder = args.pop(0).partition("=")
        mapping[name] = Path(folder).expanduser()
    if len(args) != 1:
        print(__doc__)
        return 2
    root = Path(args[0]).expanduser()
    runs = {key: read_run(mapping.get(name) or (root / name)) for key, name in PASSES.items()}
    for key, name in PASSES.items():
        run = runs[key]
        if run is None:
            print(f"{key} {name:20s} (no result yet)")
            continue
        plugin, shiploop, source = run["versions"]
        print(f"{key} {name:20s} {'pass' if run['pass'] else 'FAILED'} · {minutes(run)} min · {run['model_calls']} calls · checks {run['checks'][0]}/{run['checks'][1]}"
              f" · hidden {run['hidden_passed'][0]}/{run['hidden_passed'][1]} · stray +{r4.stray(run)} · decisions added {run['decisions_added']}"
              f" · born retired {run['born_retired']} · notices {len(run['notices'])} (flagged that survive {run['flagged_that_survive']})"
              f" · ShipLoop {shiploop} (skill-craft {plugin}, {source})")
        print(f"{'':25s} {run['line']}")
        print(f"{'':25s} earlier tests modified {run['prior_tests_modified']} · source files modified {run['source_modified'][0]} of {run['source_modified'][1]}"
              f" · earlier requirements cited by the plan {kept_ids_cited(run)} · still retired at the end {run['retired_now']}"
              f" · live sections of architecture.md changed {run['live_sections_changed']}")
        if run["failed"] or run["hidden_failed"]:
            print(f"{'':25s} failed checks {run['failed']} · hidden failed {run['hidden_failed']}")
    r = runs
    pass_list = [r[key] for key in PASSES]
    known = [run for run in pass_list if run is not None]
    chain_done = len(known) == 4

    b2_run = r["B2"]
    print(f"\nPass 2 (read, not barred): earlier test files modified {None if b2_run is None else b2_run['prior_tests_modified']}")
    print("\nBar, fixed before the runs")
    c4 = r["B4"]
    rows = [
        ("B1", "every pass passes and loses no hidden check (a FAILED pass whose only failing check is a base test is rerun five times first; see the journal)",
         all_of([r4.clean(run) for run in pass_list])),
        ("B2", "every pass adds at most 2 stray headings to environment.md", all_of([None if run is None else r4.stray(run) <= 2 for run in pass_list])),
        ("B3", "no pass files a new decision or requirement as retired", all_of([None if run is None else not run["born_retired"] and not (run["spec"].get("born_retired")) for run in pass_list])),
        ("B4", "pass 4: no earlier entry changed that the request did not name (unexplained is empty in the spec and in the architecture)",
         None if c4 is None else not c4["arch"].get("unexplained") and not c4["spec"].get("unexplained")),
        ("B5", "pass 4 changed the old rules: at least one of the requirements that state the old default and largest size was edited or retired",
         None if c4 is None else bool(c4["spec"].get("expected_touched"))),
        ("B6", "pass 3 modifies no earlier test file and pass 4 modifies at least one (its request names the tests that state the old rules); pass 2 is read, not barred",
         None if None in (r["B3"], c4) else not r["B3"]["prior_tests_modified"] and bool(c4["prior_tests_modified"])),
    ]
    for name, text, held in rows:
        print(f"{name} {verdict(held):8s} {text}")

    print("\nPredictions, fixed before the runs")
    b1, b2, b3 = r["B1"], r["B2"], r["B3"]
    inherited_held = None if b3 is None else not set(INHERITED_RULES) & set(b3["hidden_failed"]) and b3["hidden"]["observed"] is True
    total = None if not chain_done else round(sum(run["seconds"] for run in pass_list) / 60, 1)
    preds = [
        ("P1", "pass 1 (user-listing) passes all its checks", None if b1 is None else bool(r4.clean(b1))),
        ("P2", "passes 2 to 4 each pass every check, the hidden ones included", all_of([r4.clean(run) for run in (b2, b3, c4)])),
        ("P3", "passes 2 and 3 cite no earlier requirement in their step plans and test cases (the plan is the delta alone)",
         None if None in (b2, b3) else kept_ids_cited(b2) == 0 and kept_ids_cited(b3) == 0),
        ("P4", "pass 3 respects the five rules it inherits (name matching, pages, defaults, bounds, refusals): its five checks that read them pass",
         inherited_held),
        ("P5", "pass 4 leaves the architecture's pagination decision (AD-1) standing: it is about the page count, not the sizes, and a new decision carries the new rule",
         None if c4 is None else bool(c4["arch"].get("expected_untouched"))),
        ("P6", "the placement notice is printed in at least one of the four passes",
         True if any(run["notices"] for run in known) else (False if chain_done else None)),
        ("P7", "every pass runs in at most 25 minutes and the chain in at most 100", None if not chain_done else all(run["seconds"] <= 1500 for run in pass_list) and total <= 100),
        ("P8", "all four passes ran on one ShipLoop version", None if not chain_done else len({run["versions"][1] for run in pass_list}) == 1),
    ]
    for name, text, held in preds:
        print(f"{name} {verdict(held):8s} {text}")
    if chain_done:
        print(f"\ntotal {total} min; model calls {[run['model_calls'] for run in pass_list]}; tokens processed {[run['tokens'] for run in pass_list]}")
    print("\n" + json.dumps({key: ({k: v for k, v in run.items() if k in ("pass", "seconds", "born_retired", "decisions_added", "model_calls", "versions")}
                                    if run else None) for key, run in runs.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
