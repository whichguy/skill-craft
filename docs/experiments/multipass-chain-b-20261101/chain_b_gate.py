#!/usr/bin/env python3
"""The gate between two passes of chain B: what a REAL prior says about the link that is about to run on it. No model is called, nothing is written.

    python3 chain_b_gate.py LINK PRIOR_RUN_FOLDER

LINK is the case about to run (user-roles, user-team-listing or user-page-size); PRIOR_RUN_FOLDER is the run folder of the pass before it, whose ``work`` the
link continues from. The journal's Round 3 method learning is that a case written from the request and a synthetic prior failed a correct delivery on its
first contact with a real prior (E3). Round 5 therefore reads every link against the real prior BEFORE it runs, and a word or pattern wrong by construction
is fixed (with a test, in its own commit) before the link runs, never after:

1. the link's spec word (the retention check's) is not in the prior's spec, so the in-place route of that check is open to a correct delivery;
2. for ``user-page-size``, the case's ledger patterns find the rules they stand for in the prior's spec and architecture (``expected``);
3. the link's own checks and its new hidden checks FAIL on the prior (the prior is the link's base, which does not have the feature), and the earlier
   passes' checks and hidden checks PASS on it (the prior kept what it had to keep). A pass-to-pass check failing here is the previous pass's result, not a
   defect of the link, and is reported as such.

Exit 0 when the link is clear to run, 1 when a word or pattern is wrong by construction (fix it first), 2 on a usage error.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
import delta  # noqa: E402
import quality  # noqa: E402
import run  # noqa: E402

NEW = {
    "user-roles": ("role-shown", "role-filter", "filters-combine", "role-then-page", "bad-role"),
    "user-team-listing": ("teams-listing", "team-by-id", "teams-name-filter", "teams-pages", "teams-page-defaults", "teams-size-bounds", "teams-bad-page-or-size"),
    "user-page-size": ("page-size-default", "page-size-setting", "page-size-largest"),
}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in NEW:
        print(__doc__)
        return 2
    link, prior = argv[0], Path(argv[1]).expanduser()
    work = prior / "work"
    cases = run.catalog()
    case = cases[link]
    problems, notes = [], []

    spec = (work / "docs" / "shiploop" / "spec.md").read_text(errors="replace")
    arch = (work / "docs" / "shiploop" / "architecture.md").read_text(errors="replace")
    words = re.findall(r"grep -qi (\S+) docs/shiploop/spec\.md", " ".join(case["retention"]))
    for word in words:
        present = re.search(re.escape(word), spec, re.I) is not None
        (problems if present else notes).append(f"retention word {word!r}: " + ("IN the prior's spec, so the in-place route is closed to a correct delivery" if present
                                                                                 else "absent from the prior's spec (both routes open)"))
    if case.get("delta"):
        may = case["delta"]["may_change"]
        for name, text, prefix in (("spec.md", spec, "R"), ("architecture.md", arch, "AD")):
            expected = delta.ids_block(text, text, prefix, may[name])["expected"]
            (notes if expected else problems).append(f"ledger patterns for {name} find {expected or 'nothing'} in the prior")
        notes.append("the patterns' reading of the prior's entries: " + json.dumps({
            name: {ident: re.sub(r'\s+', ' ', entry.text)[:110] for ident, entry in delta.knowledge._entries(text, prefix).items()
                   if any(re.search(p, entry.text, re.I) for p in may[name])}
            for name, text, prefix in (("spec.md", spec, "R"), ("architecture.md", arch, "AD"))}))

    own_rows = run.run_checks(work, case["checks"], timeout=180)
    own_failed = [index for index, row in enumerate(own_rows) if not row["pass"]]
    (notes if own_failed == [0, 1, 2] else problems).append(f"the link's own checks fail on the prior (they must all fail): failed {own_failed}")
    regression = chains_regression(cases, link)
    rows = run.run_checks(work, regression, timeout=300)
    broken = [index for index, row in enumerate(rows) if not row["pass"]]
    (notes if not broken else notes).append(f"the earlier passes' own checks on the prior: {len(rows) - len(broken)} of {len(rows)} pass"
                                           + (f" (failed: {broken}; the previous pass's result, not the link's)" if broken else ""))

    spec_q = copy.deepcopy(run.case_quality(link))
    with tempfile.TemporaryDirectory() as logs:
        block = quality.acceptance(work, spec_q["acceptance"], groups=set(), stop=lambda: None, logs=Path(logs), ports=spec_q["refuse_ports"])
    failed = {row["id"] for row in block.get("checks") or [] if not row["pass"]}
    new_ok = failed >= set(NEW[link])
    notes.append(f"hidden acceptance on the prior: observed {block.get('observed')}; the new checks all fail: {new_ok}; inherited checks failing "
                 f"(the previous pass's result): {sorted(failed - set(NEW[link])) or 'none'}")
    if not new_ok:
        problems.append(f"new hidden checks that PASS on the prior (it already does what the link asks): {sorted(set(NEW[link]) - failed)}")
    if not block.get("observed"):
        problems.append(f"the hidden block was not observed: {block.get('reason')}")

    for line in notes:
        print("ok     " + line)
    for line in problems:
        print("WRONG  " + line)
    print("clear to run" if not problems else "fix the case before this link runs")
    return 1 if problems else 0


def chains_regression(cases: dict, link: str) -> list[str]:
    import chains
    return chains.regression(cases, link)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
