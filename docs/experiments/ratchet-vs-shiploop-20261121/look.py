#!/usr/bin/env python3
"""One look at a delivered product: the instruction file and the command for each case (journal section 11).

    look.py prepare ROOT        writes ROOT/look/prompts/CASE.md and prints the one_session.py command for each case
    look.py judged ROOT CASE    after the deep judge scored the case: its findings on ShipLoop's delivery, and match.md
    look.py unmatched ROOT CASE after matched.json: the look's other shortfalls, with probe.md and rate.md
    look.py tally ROOT          K1 to K3 for every matched case
    look.py prepare-clean FRESH the same look for a fresh run's deliveries (section 14): copies and commands

The look is one session of the builder's model in a copy of ShipLoop's delivered product (the copy the deep judge
audited, ROOT/deep/CASE/products/<S>). It may write `docs/shiploop/look.md` and nothing else. This script calls no
model.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "ratchet-pilot-20261120"
sys.path.insert(0, str(HERE))
import deep_judge  # the cases, and this machine's Playwright paths

HOST, MODEL, EFFORT = "codex", "gpt-6.2-sol", "medium"
ALLOW = "docs/shiploop/look.md"
RENDERED = ("grokbot", "roundtable")  # cases with a page: the look and its probe are told how to drive it in a browser
LOOK = """# One look at a delivered product

This folder ({{work}}) holds a product that was built and delivered for the request below. Every check passes. Its
builders' specification and working notes are in `docs/shiploop/`.

This look asks one question: now that the product runs, is there anything a user or an operator needs that it does
not do, or that it does without anyone having been told?

## The request
{request}

## What to weigh
- The product itself. Start it and use it as its users and operators would: the request's own examples, values at
  and just past each limit, wrong and odd input, the features next to what was asked, a restart, what its documents
  promise. Use it; do not only read it.{browser}
- The request, read once more for what it implies and the specification does not state.
- The specification and notes in `docs/shiploop/`, for a choice the builders made that the request did not settle.

## What to write
Write `docs/shiploop/look.md` and change nothing else: not the product, not a test, not another document.

**Shortfalls.** Each thing the product does not do that a user or an operator would care about and the request's
intent covers. For each: what is needed; the exact steps that show the product falling short (the commands or page
actions, what came back, what should have); and how much it matters: `high` (loses data, misleads a user or breaks
what worked), `medium` or `low`. A shortfall is not a new feature, a matter of taste or hardening nobody asked for.
If another correct product could behave differently and nobody would miss it, leave it out. Try what you suspect
before you write it: a shortfall you did not see happen does not belong here.

**Choices the customer was not told.** Each place where the request left something open, the product does
something reasonable there, and neither the request nor the documents delivered with the product (not counting
`docs/shiploop/`) say what it does. One line each: the open point, and what the product does.

Write the single line "Nothing found." under a heading whose list is empty.

## Conduct
Work only inside {{work}}; temporary files go in {{tmp}}. Use a free port you pick yourself and data files under
{{tmp}}. Stop every process you start, by its process id, before you finish; never stop processes by name.
"""
BROWSER = """
  Where it has a page, drive the page for real with Playwright from a Node script:
  `const {{{{ chromium }}}} = require('{playwright}')` and
  `chromium.launch({{{{ executablePath: '{browser}' }}}})` (headless). Close every browser you open."""


MATCH = """# Match one review's findings to another list

`{look}` is a review of a delivered product: a list of shortfalls and a list of choices the customer was not told.
`{judged}` is what other people found on the same product, working separately: `shortfalls` (conditions it handles
badly, ids U-n), `defects` (ids D-n) and `silent` (conditions it handles acceptably but its documents do not
mention, ids U-n). The request is `{request}`.

For each shortfall in the review, list the ids in `shortfalls` or `defects` that describe the same behaviour of the
product (the same thing going wrong, whatever the wording), or none. For each choice in the review, list the ids
in `silent` (or `shortfalls`) about the same open point, or none. Match on substance; do not stretch.

Write `{out}` as one JSON object and nothing else:

```json
{{"shortfalls": [{{"n": 1, "title": "the review's own heading", "severity": "high|medium|low", "matches": ["D-2"]}}],
 "choices": [{{"n": 1, "text": "the first words of the review's line", "matches": ["U-7"]}}]}}
```

Number the review's items in its own order. Reply with the counts: shortfalls, of them matched; choices, of them
matched.
"""

PROBE = """# Try a review's findings on every build of the request

`{unmatched}` lists shortfalls a reviewer reported for one product built from the request `{request}`, each with
the reviewer's steps. Three products built from that request by different builders are in `{products}` under code
names: {codes}. The reviewer saw the one named `{reviewed}`. Their internals differ; carry the steps out through
each product's own interface (adapt a port, a file name, a start command or page markup, never what is being
tested).{browser}

For each shortfall and each product, run the steps yourself and record `present` (the product falls short as
described), `absent` (it behaves as the reviewer says it should), `not-applicable` or `could-not-run`, with what you
observed. Copy each product once to your own work folder `{work}/<code>` and run everything there, on free ports
you pick and data files inside your work folder. Stop every process you start, by its process id; never stop
processes by name. Edit nothing outside `{work}`.

Write `{out}` as one JSON object and nothing else:

```json
{{"probed": [{{"n": 1, "results": {{"<code>": {{"result": "present", "observed": "..."}}}}}}]}}
```

Reply with, a product, the count present.
"""

RATE = """# Would the customer care?

`{request}` is a request a customer gave a software builder. Below are things a reviewer says the delivered product
gets wrong. For each, taking the reviewer's description as true, say whether the customer, an operator or the next
maintainer would care:

- `must`: it loses data, misleads a user, breaks something that worked, or is a plain defect anyone would report.
- `should`: a careful builder would not have left it; a real but smaller cost.
- `no`: a reasonable builder could ignore it; fixing it is taste, speculation or over-engineering for this request.

Answer with one JSON object and nothing else: `{{"ratings": [{{"n": 1, "rating": "must|should|no", "why": "one sentence"}}]}}`

## The reported shortfalls

{items}
"""


def judged(root: Path, case: str) -> None:
    """What the deep judge found on ShipLoop's delivery, for the matcher: no look session sees this."""
    case_dir, out = root / "deep" / case, root / "look" / case
    key, inv = deep_judge.load(case_dir / "key.json"), deep_judge.load(case_dir / "inventory.json")
    code = next(code for code, entry in key.items() if entry["point"] == "S")
    audit = deep_judge.audit_of(case_dir, code)
    text = {item["id"]: item["text"] for item in inv["unstated"]}
    rows = [row for row in audit["unstated"] if row["id"] in text]
    short = [{"id": row["id"], "condition": text[row["id"]], "what_it_does": row.get("behaviour", "")}
             for row in rows if row.get("handling") in ("poor", "unhandled")]
    silent = [{"id": row["id"], "condition": text[row["id"]], "what_it_does": row.get("behaviour", "")}
              for row in rows if row.get("handling") in ("sound", "acceptable") and row.get("told") == "no"]
    found = [{"id": defect["id"], "severity": defect["severity"], "title": defect["title"], "expected": defect.get("expected", "")}
             for defect in deep_judge.load(case_dir / "defects-probed.json")["defects"]
             if defect["results"].get(code, {}).get("result") == "present"]
    deep_judge.dump(out / "judged.json", {"shortfalls": short, "defects": found, "silent": silent})
    (out / "match.md").write_text(MATCH.format(look=out / "work" / "docs" / "shiploop" / "look.md", judged=out / "judged.json",
                                               request=case_dir / "request.md", out=out / "matched.json"))
    print(f"{case}: the deep judge on S: {len(short)} unstated items short, {len(found)} defects, {len(silent)} silent choices; match.md")


def unmatched(root: Path, case: str) -> None:
    """The look's shortfalls the deep judge did not have: a probe on all three products, and a rating by two families."""
    case_dir, out = root / "deep" / case, root / "look" / case
    key = deep_judge.load(case_dir / "key.json")
    rows = [row for row in deep_judge.load(out / "matched.json")["shortfalls"] if not row["matches"]]
    deep_judge.dump(out / "unmatched.json", {"shortfalls": [{"n": row["n"], "title": row["title"]} for row in rows],
                                             "steps_are_in": str(out / "work" / "docs" / "shiploop" / "look.md")})
    codes = ", ".join(f"`{code}`" for code in key)
    reviewed = next(code for code, entry in key.items() if entry["point"] == "S")
    browser = ""
    if case in RENDERED:
        browser = (f" Where a step needs the page, drive it with Playwright from a Node script: `const {{ chromium }} = "
                   f"require('{deep_judge.PLAYWRIGHT}')` and `chromium.launch({{ executablePath: '{deep_judge.BROWSER}' }})`.")
    (out / "probe.md").write_text(PROBE.format(unmatched=out / "unmatched.json", request=case_dir / "request.md",
                                               products=case_dir / "products", codes=codes, reviewed=reviewed,
                                               browser=browser, work=out / "probe-work", out=out / "probed.json"))
    look_text = (out / "work" / "docs" / "shiploop" / "look.md").read_text()
    items = "\n".join(f"- **{row['n']}**: {row['title']}" for row in rows)
    (out / "rate.md").write_text(RATE.format(request=case_dir / "request.md", items=items)
                                 + "\n## The reviewer's full text, for the detail of each\n\n" + deep_judge.mask(look_text))
    print(f"{case}: {len(rows)} shortfalls the deep judge did not have; probe.md and rate.md")


def tally(root: Path) -> None:
    """K1 to K3 for every case that has been matched (and, for K2, probed and rated)."""
    for case in deep_judge.CASES:
        out = root / "look" / case
        if not (out / "matched.json").exists():
            continue
        key = deep_judge.load(root / "deep" / case / "key.json")
        code = next(code for code, entry in key.items() if entry["point"] == "S")
        judged_list, matched = deep_judge.load(out / "judged.json"), deep_judge.load(out / "matched.json")
        known = {row["id"] for row in judged_list["shortfalls"]} | {row["id"] for row in judged_list["defects"]}
        hit = {found for row in matched["shortfalls"] for found in row["matches"] if found in known}
        silent = {row["id"] for row in judged_list["silent"]}
        told = {found for row in matched["choices"] for found in row["matches"] if found in silent}
        shortfalls = matched["shortfalls"]
        on_list = [row for row in shortfalls if row["matches"]]
        extra, real = [row for row in shortfalls if not row["matches"]], None
        line = (f"{case}: K1 {len(hit)} of {len(known)} of the deep judge's findings named; "
                f"K3 {len(told)} of {len(silent)} silent choices listed ({len(matched['choices'])} choices written); "
                f"the look's shortfalls: {len(shortfalls)}, on the deep judge's list {len(on_list)}")
        if extra and all((out / name).exists() for name in ("probed.json", "rate-a.json", "rate-b.json")):
            probed = {row["n"]: row["results"] for row in deep_judge.load(out / "probed.json")["probed"]}
            rates = [{row["n"]: row["rating"] for row in deep_judge.load(out / f"rate-{name}.json")["ratings"]} for name in "ab"]
            real = [row["n"] for row in extra if probed.get(row["n"], {}).get(code, {}).get("result") == "present"
                    and all(rate.get(row["n"]) in ("must", "should") for rate in rates)]
            shared = {point: sum(1 for row in extra if row["n"] in real and probed[row["n"]].get(other, {}).get("result") == "present")
                      for other, point in ((other, key[other]["point"]) for other in key if other != code)}
            line += (f"; not on it {len(extra)}, of them real (reproduce and both raters keep) {len(real)} "
                     f"-> K2 {len(on_list) + len(real)} of {len(shortfalls)}; of the real new ones, also present on "
                     + ", ".join(f"{point} {count}" for point, count in sorted(shared.items())))
        elif extra:
            line += f"; not on it {len(extra)} (not yet probed and rated)"
        else:
            line += f" -> K2 {len(on_list)} of {len(shortfalls)}"
        print(line)


def request(root: Path, cases: dict, case: str) -> str:
    """CASE's request: the pilot's, as before, for the four cases it has; for one it lacks (roundtable), the one the deep
    judge reads (deep_judge.request_of: the harness's prompt in the checkout ROOT/source.json names)."""
    full_name = deep_judge.CASES[case]
    return cases[full_name]["request"] if full_name in cases else deep_judge.request_of(root, case)[0]


def prepare_clean(fresh: Path) -> None:
    """The same look for a fresh run's deliveries (journal section 14): the delivered commit of FRESH/CASE-1/work is
    exported without its history to FRESH/delivered/CASE, and the look runs there."""
    prompts = fresh / "look" / "prompts"
    prompts.mkdir(parents=True, exist_ok=True)
    cases = json.loads((PILOT / "cases.json").read_text())
    for case in deep_judge.CASES:
        measures, delivered = fresh / "measure" / f"{case}-1" / "measures.json", fresh / "delivered" / case
        if not measures.is_file():
            print(f"# {case}: not measured yet ({measures})")
            continue
        if not delivered.exists():  # the delivered commit of the run's own repository, without its history
            commit = json.loads(measures.read_text())["points"]["final"]
            archive = subprocess.run(["git", "-C", str(fresh / f"{case}-1" / "work"), "archive", commit],
                                     capture_output=True, check=True).stdout
            delivered.mkdir(parents=True)
            subprocess.run(["tar", "-x", "-C", str(delivered)], input=archive, check=True)
        browser = BROWSER.format(playwright=deep_judge.PLAYWRIGHT, browser=deep_judge.BROWSER) if case in RENDERED else ""
        text = LOOK.format(request=request(fresh, cases, case).strip().replace("{", "{{").replace("}", "}}"), browser=browser)
        (prompts / f"{case}.md").write_text(text.replace("{{", "{").replace("}}", "}"))
        print(f"python3 {PILOT / 'one_session.py'} --folder {delivered} --prompt {prompts / f'{case}.md'} --allow {ALLOW} "
              f"--output {fresh / 'look' / case} --host {HOST} --model {MODEL} --effort {EFFORT} --role look")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) == 3 and argv[0] in ("judged", "unmatched") and argv[2] in deep_judge.CASES:
        {"judged": judged, "unmatched": unmatched}[argv[0]](Path(argv[1]).expanduser().resolve(), argv[2])
        return 0
    if len(argv) == 2 and argv[0] == "tally":
        tally(Path(argv[1]).expanduser().resolve())
        return 0
    if len(argv) == 2 and argv[0] == "prepare-clean":
        prepare_clean(Path(argv[1]).expanduser().resolve())
        return 0
    if len(argv) != 2 or argv[0] != "prepare":
        raise SystemExit(__doc__)
    root = Path(argv[1]).expanduser().resolve()
    prompts = root / "look" / "prompts"
    prompts.mkdir(parents=True, exist_ok=True)
    cases = json.loads((PILOT / "cases.json").read_text())
    for case in deep_judge.CASES:
        if not (root / "deep" / case / "key.json").is_file():  # roundtable's products are laid out under a derived name
            print(f"# {case}: no products under {root / 'deep' / case}")
            continue
        key = json.loads((root / "deep" / case / "key.json").read_text())
        code = next(code for code, entry in key.items() if entry["point"] == "S")
        browser = BROWSER.format(playwright=deep_judge.PLAYWRIGHT, browser=deep_judge.BROWSER) if case in RENDERED else ""
        text = LOOK.format(request=request(root, cases, case).strip().replace("{", "{{").replace("}", "}}"), browser=browser)
        (prompts / f"{case}.md").write_text(text.replace("{{", "{").replace("}}", "}"))
        print(f"python3 {PILOT / 'one_session.py'} --folder {root / 'deep' / case / 'products' / code} "
              f"--prompt {prompts / f'{case}.md'} --allow {ALLOW} --output {root / 'look' / case} "
              f"--host {HOST} --model {MODEL} --effort {EFFORT} --role look")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
