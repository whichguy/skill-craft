#!/usr/bin/env python3
"""The deep judge: what each product does where the request speaks and where it is silent, read by running it.

Design and registered readings: docs/ratchet-vs-shiploop-journal.md, section 10 with its first amendment. This script
calls no model. It lays out the folders and the instruction files the model sessions are pointed at, checks and
joins their JSON answers, and computes the readings. Everything lives under ROOT/deep/.

    deep_judge.py prepare ROOT CASE            products under code names, the request, the starting files, prompts
    deep_judge.py rate-packet ROOT CASE        after merged.json: the rating instructions, sources left out
    deep_judge.py inventory ROOT CASE          after both ratings: inventory.json, inventory.md, the audit prompts
    deep_judge.py calibrate ROOT [ROUND]       after the ticket inventory: the instrument check as a case of its own
    deep_judge.py join-shares ROOT CASE        a long inventory is audited in shares: one audit a product from them
    deep_judge.py defects ROOT CASE            after the audits: reported defects, items the audits differ on, probe.md
    deep_judge.py told-packet ROOT CASE        after the cross-probe: one reader's instructions for what each product's documents tell
    deep_judge.py verdict-packet ROOT CASE     after told.json: one masked packet for each of the two judges
    deep_judge.py fixed ROOT CASE              CASE-fixed: the looked-at and fixed product beside the two it is compared with
    deep_judge.py clean ROOT FRESH CASE        CASE-clean: a fresh run's delivery, the same after look and fix, and Ratchet's final
    deep_judge.py fresh ROOT FRESH RATCHET CASE  CASE-fresh: as CASE-clean, but L is the final of RATCHET/CASE-2 (after measure.py)
    deep_judge.py grab IN.json OUT.json        the first JSON object in an `ask` answer's text
    deep_judge.py score ROOT OUT_DIR           D1 to D6, the gate, the pairs, deep.json and deep.md

CASE is the short name: expenses, chess, tickets, grokbot (and calibration for the last four steps).
"""
import json
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "ratchet-pilot-20261120"
CASES = {"expenses": "shared-expenses", "chess": "node-chess-engine", "tickets": "ticket-assignment",
         "grokbot": "grokbot-local"}
POINTS = (("S", "1", "final", "docs/shiploop/spec.md"), ("F", "2", "first-build", "ratchet/spec.md"),
          ("L", "2", "final", "ratchet/spec.md"))
NAMES = {"S": "ShipLoop's delivery", "F": "Ratchet's first build", "L": "Ratchet's final"}
FIXED_NAMES = {"S": "ShipLoop's delivery after one look and one fix", "F": "ShipLoop's delivery", "L": "Ratchet's final"}
CLEAN_NAMES = {"S": "a fresh ShipLoop delivery after one look and one fix", "F": "the fresh ShipLoop delivery",
               "L": "Ratchet's final, audited again"}
FRESH_NAMES = {"S": "a fresh ShipLoop delivery after one look and one fix", "F": "the fresh ShipLoop delivery",
               "L": "a fresh Ratchet final"}
CALIBRATION_NAMES = {"S": "the correct reference", "F": "the reference, padded", "L": "a stated requirement broken"}
PAIRS = (("S", "L"), ("S", "F"), ("F", "L"))
JUDGES = ("a", "b")
MASKS = [(re.compile(r"ship\s*loop", re.IGNORECASE), "[tool]"), (re.compile(r"ratchet", re.IGNORECASE), "[tool]")]
SKIP = shutil.ignore_patterns(".git", "node_modules")
PROVED = 6  # stated items a case, drawn by seed, whose test must be proved by breaking the behaviour
EXPLORE = 12  # probes of the auditor's own beyond the inventory, the same for every product
# This machine's Playwright and headless browser, the ones the pilot's grade.py uses.
PLAYWRIGHT = "/Users/dadleet/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright"
BROWSER = ("/Users/dadleet/Library/Caches/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-mac-arm64/"
           "chrome-headless-shell")
SHARES = 3  # an inventory of more than SHARE_OVER items is audited in this many shares by separate sessions
SHARE_OVER = 80
# The ticket case's calibrated defects (test/fixtures/quality/reference_ticket_assignment.py) that break a behaviour
# the request states, and those that break one the request leaves unsaid but the new feature raises.
STATED_DEFECTS = ("closed-assignable", "cli-no-assignee", "empty-filter-ignored", "filter-or", "listing-hides-assignee",
                  "name-limit-off-by-one", "no-unassign", "notify-requester", "same-agent-not-noop")
UNSTATED_DEFECTS = ("actor-ignored", "audit-bypassed", "conflict-as-invalid", "memory-only-assignee",
                    "notify-key-per-ticket", "old-data-refused", "raw-column-inserted")

LISTER = """# What a request asks for, and what it leaves unsaid

Read `{case}/request.md`: a request a customer gave a software builder. {base_line}
You will not see anything that was built. Do not build anything.

Write two lists.

**stated**: every requirement the request states, as separate items that can each be checked on a running product
on its own. One behaviour an item. Keep the request's own words for values, names and limits. Leave nothing out and
add nothing the request does not say.

**unstated**: the conditions the request leaves unsaid that the customer, someone operating the product or the next
person to maintain it would plausibly care about once the product is in use. For each one: what the request does
not settle, why someone would care, and a `probe`: exact steps on a running product that show what it does there.
Leave out anything a reasonable builder could ignore: taste, speculative scale, hardening no one asked for. Do not
decide the answer; where several answers would be fine, say so in `fine_answers`.

Answer with one JSON object and nothing else:

```json
{{"stated": [{{"text": "..."}}],
 "unstated": [{{"text": "what is left unsaid", "why": "who cares and why", "probe": "exact steps", "fine_answers": "..."}}]}}
```
"""

MERGE = """# Merge the lists into one inventory

In `{case}/` are two lists written from the same request by two readers who saw no product: `lister-a.json` and
`lister-b.json` (the request is `request.md`). `arm-points.md` is a third list: points raised by people who built
the product.

Work in this order and write `{case}/merged.json`:

```json
{{"stated": [{{"id": "S-1", "text": "..."}}],
 "unstated": [{{"id": "U-1", "text": "...", "why": "who cares and what a failure costs", "probe": "exact steps on a running product",
               "fine_answers": "the outcomes that would be acceptable", "sources": ["a", "b", "arm"]}}]}}
```

1. `stated`: the union of the two readers' stated items, duplicates merged, one checkable behaviour an item, in the
   request's order. Check each against `request.md`: drop an item the request does not state, and add one it states
   that both readers missed.
2. `unstated`, first from the two readers only: the union of their unstated points. Merge duplicates and merge
   variants of one obligation into one item (one obligation, one item, however many ways it can be worded), with
   the sources that raised it (`a`, `b`). Finish this list before you open `arm-points.md`.
3. Then read `arm-points.md`. Where a point there is already an item, add `arm` to that item's sources and change
   nothing else in it. Where it is new, add an item with sources `["arm"]`, as a condition a product can be
   probed for. Leave out lines that are not about the product's behaviour (benchmark hardware, visual taste).
4. Do not judge whether a point matters: that is another step. Every item needs a probe a person could follow on
   any build of this request, written against the product's interface and not one build's internals, and the
   outcomes that would be acceptable. Write them where the source gave none.
5. Number the items S-1.. and U-1.. Write nothing else in the file. Reply with the two counts and the number of
   unstated items by source combination.
"""

RATE = """# Would the customer care?

`{case}/request.md` is a request a customer gave a software builder. {base_line}Below are conditions the request
leaves unsaid. For each, say whether the customer, an operator or the next maintainer would care how the product
behaves there once it is in use:

- `must`: getting it wrong loses data, misleads a user, breaks something that worked, or is a plain defect anyone
  would report.
- `should`: a careful builder handles it, or tells the customer what was chosen; getting it wrong is a real but
  smaller cost.
- `no`: a reasonable builder could ignore it; handling it is taste, speculation or over-engineering for this
  request.

Rate each on its own. Most lists like this hold a good share of `no`.

Answer with one JSON object and nothing else: `{{"ratings": [{{"id": "U-1", "rating": "must|should|no", "why": "one sentence"}}]}}`

## The conditions

{items}
"""

AUDIT = """# Audit one product against a request

You are auditing a product a builder delivered for a customer's request. Your audit will be compared with audits
of other deliveries of the same request, each made with these same instructions, so be exact and observe before
you assert.

- The request: `{case_dir}/request.md`
- {base_line}
- The inventory, the items to check: `{case_dir}/inventory.md` (stated requirements S-n, and conditions the request
  leaves unsaid U-n, each with a probe and the outcomes that would be acceptable)
- The product: `{product}`. {spec_line}

## Rules

1. Work only in your own copy: copy the product to `{work}` first and run everything there. Change no other
   folder. Never edit the original.
2. Use a free port you pick yourself and data files inside your work folder. Stop every process you start, by its
   process id, before you finish; never stop processes by name.
3. `observed` is true only when you ran something and saw the result. Reading the code is `observed: false`.
4. Judge the product against the request and the inventory, not against your taste. Any outcome the inventory
   lists as acceptable is acceptable. A choice the request leaves open is not a defect unless it loses data,
   misleads a user or breaks something that worked.
5. Size is not quality. Do not credit a product for the length of its documents or the number of its tests, and
   do not hold either against it: only what they do counts.

## Part 1: behaviour. Do this before you open the product's tests or its builders' specification.

Start the product and try every inventory item for real, with the item's probe (adapt a port, a file name or a
start command, never what is being tested). Record the command you ran and what came back.

For each stated item, `built`: `yes`, `partly`, `no` (missing) or `wrong` (present and incorrect).

For each unstated item, `behaviour` (what the product does there, as observed) and `handling`: `sound`,
`acceptable`, `poor` (works against the user or loses something), `unhandled` (crashes, hangs, corrupts, or the
product has no behaviour there) or `not-applicable`.

Then up to {explore} probes of your own choosing beyond the inventory, aimed at ordinary use and at the edges of
what was asked. List every one in `explored` with what came back, including those that found nothing. A defect
needs an exact reproduction another person can run on a fresh copy of any build of this request: the commands in
terms of the product's interface (HTTP requests, commands, function calls), what comes back, what should have.
`severity`: `high` loses data, gives a wrong result on an ordinary use, or breaks what worked before; `medium` is
wrong on an unusual but plausible use; `low` otherwise.

Do not change a Part 1 grade because of anything you read in Part 2 or Part 3.

## Part 2: tests

Run the product's own tests and record the command and its result. Then, for each stated and unstated item,
`test`: `strong` when a test in the suite would fail if this item broke (name it in `test_name`), `weak` when a
test touches it but would not notice most breakages, `none`.

For these stated items the claim must be proved: {proved}. For each one, break that behaviour in your copy with the
smallest edit to the product's code that makes the item's probe fail, run the suite, record in `proved` whether it
`fails` (name the failing test) or `passes`, then undo the edit and confirm the suite is back to its first result.
`could-not-break` if the item is not built.

## Part 3: specification and documents

- For each stated item, `spec`: does the builders' specification state it: `stated`, `absent`, `contradicted`, or
  `none` when the product has no specification.
- For each unstated item, `spec`: `open` (marked for the customer to decide), `decided-marked` (decided and marked
  as the builder's own choice or assumption), `decided-unmarked` (decided in an ordinary requirement line),
  `silent`, or `none`.
- For each unstated item, `told`: would a customer who reads the documents delivered with the product (README, API
  or operations documents, a changelog or delivery note; not the builders' specification or working notes) find
  an accurate account of what the product does there: `yes` (say where in `told_where`) or `no`.
- `extras`: things built that the request did not ask for, each `value`, `neutral` or `liability`, with why.
- `spec_notes`: where the specification contradicts the request, decides something without saying so, or pins a
  choice a correct product need not share. `none` if there is no specification.
- `tests_notes`: tests that cover several behaviours at once; tests tied to internals (file names, private
  functions, timing); tests that would fail on another correct build of this request.
- `maintainer`: what the next person would find hardest to change safely, in two or three sentences.

Write your audit to `{out}` as one JSON object and nothing else in the file:

```json
{{"code": "{code}",
 "ran": {{"tests_command": "...", "tests_result": "...", "started_with": "..."}},
 "stated": [{{"id": "S-1", "built": "yes", "observed": true, "evidence": "command and what came back", "spec": "stated", "test": "strong", "test_name": "...", "proved": "fails|passes|could-not-break|not-asked", "proved_by": "the edit, and the test that failed"}}],
 "unstated": [{{"id": "U-1", "behaviour": "...", "handling": "sound", "observed": true, "evidence": "...", "spec": "silent", "told": "no", "told_where": "", "test": "none"}}],
 "explored": [{{"probe": "...", "came_back": "...", "finding": "none|defect"}}],
 "defects": [{{"title": "...", "severity": "medium", "repro": "...", "observed": "...", "expected": "...", "basis": "stated|unstated|other", "item": "S-3 or U-2 or empty"}}],
 "extras": [{{"what": "...", "where": "...", "worth": "neutral", "why": "..."}}],
 "spec_notes": "...", "tests_notes": "...", "maintainer": "..."}}
```

Every inventory item must appear once. When the file is written and every process you started is stopped, reply
with three lines only: the tests' result, the count of stated items not `yes`, the count of defects.
"""

SHARE = """

## Your share of this audit

This inventory is long, so the audit of this product is shared between {shares} auditors who work separately, each
with these same instructions. Your share is these items and no others: {items}.

- Do Parts 1, 2 and 3 for your items only. The `stated` and `unstated` arrays of your file hold your items only,
  each once. This replaces "every inventory item must appear once".
- In Part 2, the items of yours whose test must be proved by breaking the behaviour: {proved}.
- {closing}
- Where an item needs the page in a browser, drive it for real with Playwright from a Node script:
  `const {{ chromium }} = require('{playwright}')` and `chromium.launch({{ executablePath: '{browser}' }})`
  (headless). Close every browser you open.
"""

PROBE = """# Re-run what the audits disagree on, and try each reported defect on every product

Several products were built from one request (`{case_dir}/request.md`) by different builders and audited one at a
time. The products are in `{case_dir}/products/` under code names: {codes}. Their internals differ; a probe or a
reproduction is given in terms of the product's interface and may need the obvious adaptation (a different port,
file name or start command), never a change of what is being tested.

`{case_dir}/defects-reported.json` holds two lists.

**`recheck`**: inventory items (`{case_dir}/inventory.md`) on which the audits gave the products different grades.
For each, run the item's probe on every product yourself, the same steps and inputs for each, and grade what you
see: a stated item `yes`, `partly`, `no` or `wrong`; an unstated item `sound`, `acceptable`, `poor`, `unhandled`
or `not-applicable`, where any outcome the inventory lists as acceptable is acceptable. Your grade replaces the
audits' for these items, so do not copy theirs: run it.

**`defects`**: defects auditors reported, each for one product (`from`), with a reproduction.

1. Merge entries that describe the same defect (the same behaviour, whichever product it was reported for).
2. For each merged defect, run the reproduction on every product, the product it was reported for included, and
   record `present` (the defect shows), `absent` (the product behaves as `expected`), `not-applicable` (the product
   has no such feature) or `could-not-run`. Keep the highest severity among merged entries, and lower it only if
   what you observe is plainly less than the auditor claimed (say so in `note`).

Rules: copy each product once to your own work folder `{work}/<code>` and run everything there. Use free ports you
pick yourself and data files inside your work folder. Stop every process you start, by its process id; never stop
processes by name. Edit nothing outside `{work}`. Every result needs what you observed.

Write `{case_dir}/defects-probed.json` as one JSON object and nothing else:

```json
{{"rechecks": [{{"id": "U-3", "results": {{"<code>": {{"grade": "acceptable", "observed": "..."}}}}}}],
 "defects": [{{"id": "D-1", "title": "...", "severity": "high|medium|low", "merged_from": ["<code>#<n>"],
               "repro": "...", "expected": "...", "note": "",
               "results": {{"<code>": {{"result": "present", "observed": "..."}}}}}}]}}
```

Reply with the count of rechecked items, the count of merged defects and, a product, how many are present.
"""

TOLD = """# What the documents delivered with each product tell a customer

Several products were built from one request (`{case_dir}/request.md`) by different builders. They are in
`{case_dir}/products/` under code names: {codes}. `{case_dir}/inventory.md` lists conditions the request leaves
unsaid (U-n). `{case_dir}/told-input.json` gives, for each of those items, what each product was seen to do there
when it was run (`behaviour`, with its handling grade).

For every item and every product you decide one thing, `told`: would a customer who reads the documents delivered
with that product find an accurate account of what that product does there?

1. For each product, read only the documents delivered with it to a customer: the README, API or operations
   documents, a changelog or delivery note, and anything under a docs folder that is written for a user or an
   operator. Do not count the builders' specification or their working notes. These paths, inside each product's
   folder, are left out:

{excluded}

2. `told` is `yes` only when those documents give an accurate account of what that product does at the item: the
   behaviour given for that product in `told-input.json`. Then `where` is the file and the sentence, quoted.
   Otherwise `told` is `no` and `where` is empty. A document that describes behaviour the product does not have is
   `no`. Silence is `no`.
3. Hold every product to the same standard. Read each product's own documents and compare them with that
   product's own behaviour; do not infer one product's answer from another's, even where their documents look
   alike.
4. Run nothing and edit nothing.

Write `{case_dir}/told.json` as one JSON object and nothing else:

```json
{{"told": [{{"id": "U-1", "results": {{"<code>": {{"told": "yes|no", "where": "file: quoted sentence, or empty"}}}}}}]}}
```

Every item in `told-input.json` appears once, with a result for every product. Reply with, a product, the count of
`yes`.
"""

VERDICT = """# Three deliveries of one request: which is the better feature?

Three builders each delivered the same customer request (below). Each delivery was audited by running it: every
stated requirement, a list of conditions the request leaves unsaid, its tests, its specification and its documents.
Items the audits disagreed on were run again on all three by another person, and every defect an auditor reported
was tried on all three. You have the audits (with those re-runs applied) and the defect table. The deliveries are
labelled {letters}; the labels and their order carry no meaning. You do not have the products and should not guess
at them beyond the audits.

Judge as the person who will run this feature and keep it working: what does each delivery give that the others do
not, and does it matter? Size is not quality: a longer specification, more tests or more code count only through
what the audits show they bought, and count against a delivery where the audits show they cost (requirements the
customer did not ask for, tests that pin one builder's choices, code a maintainer must carry). Count each
consequence once, however many audit lines mention it.

For each pair ({pairs}):

- `better`: `<letter>-much`, `<letter>-some` (naming the better delivery) or `same`.
- `advantages`: each real advantage of either side, with the audit line or defect id behind it (`ref`) and whom it
  matters to: `requester`, `operator`, `maintainer` or `no one`.
- `lesser_lacks`: what the lesser delivery would need to match the better one, as a list of concrete changes.
- `one_task_closes`: `yes` if one short follow-up task (about an hour of the same builder's work) would close that
  list, else `no`. `yes` when `better` is `same`.
- `why`: three sentences at most.

Answer with one JSON object and nothing else:

```json
{{"pairs": [{{"pair": "{example}", "better": "same", "advantages": [{{"of": "X", "what": "...", "ref": "U-4", "matters_to": "operator"}}], "lesser_lacks": ["..."], "one_task_closes": "yes", "why": "..."}}]}}
```

## The request

{request}

## The inventory

{inventory}

## The defect table (each defect with what each delivery did when it was tried)

{defects}

{audits}
"""


def mask(text: str) -> str:
    for pattern, replacement in MASKS:
        text = pattern.sub(replacement, text)
    return text


def load(path: Path):
    return json.loads(path.read_text())


def dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def first_json(text: str):
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start != -1:
        try:
            return decoder.raw_decode(text, start)[0]
        except ValueError:
            start = text.find("{", start + 1)
    return None


def base_line(case_dir: Path) -> str:
    if any((case_dir / "base").iterdir()):
        return f"The files the builder started from are in `{case_dir}/base/` (read them as far as the request touches them). "
    return "The builder started from an empty folder. "


def arm_points(root: Path, case: str) -> str:
    """Points the arms themselves raised, without their names: Ratchet's `Open:` lines and after-build clauses, and
    the first judge's remarks on what either product lacks."""
    lines = ["# Points raised by people who built the product", ""]
    spec = (root / f"{case}-2" / "work" / "ratchet" / "spec.md").read_text()
    lines += ["## Marked as open for the customer", ""]
    lines += [f"- {mask(line[5:].strip())}" for line in spec.splitlines() if line.startswith("Open:")]
    lines += ["", "## Requirements added after looking at a running build", ""]
    for block in re.split(r"(?m)^### ", spec)[1:]:
        if "Source: discovery" in block:
            head, _, body = block.partition("\n")
            first = next((row for row in body.splitlines() if row.strip() and not row.startswith("Source:")), "")
            lines.append(f"- {mask(head.split(':', 1)[-1].strip())} {mask(first.strip())}")
    lines += ["", "## What a reader of the code remarked was missing or risky", ""]
    number = {"expenses": "1", "chess": "2", "tickets": "3", "grokbot": "4"}[case]
    for answer in sorted((root / "judge").glob(f"{number}/answer-*.json")):
        data = load(answer)
        for side in ("X", "Y"):
            for name in ("correctness_risk", "error_handling"):
                lines.append(f"- {mask(data[side]['reasons'][name])}")
    return "\n".join(lines) + "\n"


def write_first_prompts(case_dir: Path) -> None:
    (case_dir / "prompts" / "lister.md").write_text(LISTER.format(case=case_dir, base_line=base_line(case_dir)))
    (case_dir / "prompts" / "merge.md").write_text(MERGE.format(case=case_dir))


def prepare(root: Path, case: str) -> None:
    case_dir = root / "deep" / case
    if (case_dir / "key.json").exists():
        write_first_prompts(case_dir)  # a case's products are laid out once; its first prompts may be rewritten
        print(f"{case}: already laid out; lister.md and merge.md rewritten")
        return
    request = load(PILOT / "cases.json")[CASES[case]]["request"]
    (case_dir / "prompts").mkdir(parents=True)
    (case_dir / "request.md").write_text(request.rstrip() + "\n")
    shutil.copytree(root / "measure" / f"{case}-1" / "fixture", case_dir / "base", ignore=SKIP)
    (case_dir / "arm-points.md").write_text(arm_points(root, case))
    chooser = random.Random(f"deep-judge codes {case}")
    key = {}
    for point, arm, snapshot, spec in POINTS:
        code = f"p{chooser.randrange(16 ** 6):06x}"
        tree = root / "measure" / f"{case}-{arm}" / snapshot / "tree"
        shutil.copytree(tree, case_dir / "products" / code, ignore=SKIP)
        key[code] = {"point": point, "tree": str(tree), "spec": spec}
    dump(case_dir / "key.json", key)
    write_first_prompts(case_dir)
    print(f"{case}: {len(key)} products under {case_dir / 'products'}; prompts lister.md and merge.md")


def rate_packet(root: Path, case: str) -> None:
    case_dir = root / "deep" / case
    merged = load(case_dir / "merged.json")
    items = "\n".join(f"- **{item['id']}**: {item['text']} (Why it might matter: {item.get('why', '')})"
                      for item in merged["unstated"])
    (case_dir / "prompts" / "rate.md").write_text(RATE.format(case=case_dir, base_line=base_line(case_dir), items=items))
    print(f"{case}: {len(merged['stated'])} stated, {len(merged['unstated'])} unstated to rate")


def shares_of(inv: dict) -> list:
    """The inventory's item ids in shares: one share for a short inventory; for a long one the stated items in
    SHARES - 1 runs of equal length and the unstated items as the last share."""
    stated, unstated = [item["id"] for item in inv["stated"]], [item["id"] for item in inv["unstated"]]
    if len(stated) + len(unstated) <= SHARE_OVER:
        return [stated + unstated]
    size = -(-len(stated) // (SHARES - 1))
    return [stated[start:start + size] for start in range(0, len(stated), size)] + [unstated]


def write_audit_prompts(case_dir: Path) -> None:
    inv = load(case_dir / "inventory.json")
    shares = shares_of(inv)
    proved = ", ".join(inv["proved"])
    base = (f"The files the builder started from: `{case_dir}/base/`" if any((case_dir / "base").iterdir())
            else "The builder started from an empty folder")
    (case_dir / "audits").mkdir(exist_ok=True)
    for code, entry in load(case_dir / "key.json").items():
        product, spec = case_dir / "products" / code, entry.get("spec")
        if spec and (product / spec).exists():
            spec_line = f"Its builders' specification is `{spec}` inside it; other working notes of theirs may sit beside it."
        else:
            spec_line = "It holds no specification by its builders."
        if len(shares) == 1:
            (case_dir / "prompts" / f"audit-{code}.md").write_text(AUDIT.format(
                case_dir=case_dir, base_line=base, product=product, spec_line=spec_line, work=case_dir / "work" / code,
                out=case_dir / "audits" / f"{code}.json", code=code, proved=proved, explore=EXPLORE))
            continue
        for number, items in enumerate(shares, 1):
            last = number == len(shares)
            mine = [item for item in inv["proved"] if item in items]
            closing = ("You also make the probes of your own choosing and write `extras`, `spec_notes`, `tests_notes` and "
                       "`maintainer`." if last else
                       "Leave `explored` and `extras` empty and `spec_notes`, `tests_notes` and `maintainer` as empty strings: "
                       "another auditor writes them. Make no probes of your own choosing; report a defect only where you "
                       "meet one while trying your items.")
            text = AUDIT.format(case_dir=case_dir, base_line=base, product=product, spec_line=spec_line,
                                work=case_dir / "work" / f"{code}-share{number}",
                                out=case_dir / "audits" / f"{code}.share{number}.json", code=code, proved=proved,
                                explore=EXPLORE)
            text += SHARE.format(shares=len(shares), items=", ".join(items), proved=", ".join(mine) or "none", closing=closing,
                                 playwright=PLAYWRIGHT, browser=BROWSER)
            (case_dir / "prompts" / f"audit-{code}-share{number}.md").write_text(text)


def inventory(root: Path, case: str) -> None:
    case_dir = root / "deep" / case
    merged = load(case_dir / "merged.json")
    ratings = {name: {row["id"]: row["rating"] for row in load(case_dir / f"rate-{name}.json")["ratings"]}
               for name in JUDGES}
    kept, rows = [], []
    for item in merged["unstated"]:
        pair = [ratings[name].get(item["id"]) for name in JUDGES]
        if None in pair:
            raise SystemExit(f"{case}: {item['id']} has no rating from both raters")
        keep = all(rating in ("must", "should") for rating in pair)
        independent = bool({"a", "b"} & set(item["sources"]))
        rows.append({"id": item["id"], "sources": item["sources"], "ratings": pair, "kept": keep,
                     "independent": independent})
        if keep:
            kept.append({**item, "ratings": pair, "independent": independent})
    stated_ids = [item["id"] for item in merged["stated"]]
    proved = sorted(random.Random(f"deep-judge proved {case}").sample(stated_ids, min(PROVED, len(stated_ids))),
                    key=stated_ids.index)
    dump(case_dir / "inventory.json", {"stated": merged["stated"], "unstated": kept, "rated": rows, "proved": proved})
    text = ["# Inventory", "", "## Stated requirements", ""]
    text += [f"- **{item['id']}**: {item['text']}" for item in merged["stated"]]
    text += ["", "## Conditions the request leaves unsaid", ""]
    for item in kept:
        text += [f"- **{item['id']}**: {item['text']}", f"  - Probe: {item['probe']}",
                 f"  - Outcomes that would be acceptable: {item.get('fine_answers') or 'not given'}"]
    (case_dir / "inventory.md").write_text("\n".join(text) + "\n")
    write_audit_prompts(case_dir)
    arm_only = [row for row in rows if not row["independent"]]
    primary = [row for row in rows if row["independent"]]
    print(f"{case}: stated {len(stated_ids)} (tests proved on {', '.join(proved)}); unstated rated {len(rows)}: "
          f"independent {len(primary)}, kept {sum(1 for row in primary if row['kept'])}; "
          f"arm-only {len(arm_only)}, kept {sum(1 for row in arm_only if row['kept'])}")


def padded(product: Path, request: str) -> None:
    """Make a correct product larger without making it better: a long specification that restates the request, and
    every test of the new behaviour a second time under another name."""
    sentences = [part.strip() for part in re.split(r"(?<=[.;])\s+", request) if part.strip()]
    forms = ("The product shall satisfy the following: {}", "Acceptance: it is verified that {}",
             "Rationale and scope: the customer asked that {}", "Non-goal check: nothing beyond this is implied by {}",
             "Traceability: this clause derives from the request sentence {}", "Review note: confirmed against the request: {}")
    lines = ["# Specification", ""]
    for number, sentence in enumerate(sentences, 1):
        lines += [f"## Requirement {number}", ""] + [f"- {form.format(sentence)}" for form in forms] + [""]
    (product / "docs").mkdir(exist_ok=True)
    (product / "docs" / "spec.md").write_text("\n".join(lines))
    added = [product / "test" / name for name in ("assignment.test.js", "assignee.test.js") if (product / "test" / name).exists()]
    if not added:
        raise SystemExit("the reference has none of the test files this padding copies")
    for source in added:
        copy = re.sub(r"\b(test|it)\((['\"`])", r"\1(\2again: ", source.read_text())
        (source.parent / source.name.replace(".test.js", "-again.test.js")).write_text(copy)


def calibrate(root: Path, round_number: int = 1) -> None:
    """Round 1 lays out all four products. A later round draws two defects not drawn before and takes the reference
    and the padded reference, with their audits, from round 1."""
    sys.path.insert(0, str(PILOT))
    import grade
    first = root / "deep" / "calibration"
    tickets, out_dir = root / "deep" / "tickets", (first if round_number == 1 else root / "deep" / f"calibration{round_number}")
    if (out_dir / "key.json").exists():
        raise SystemExit("this calibration round is already laid out")
    case = load(PILOT / "cases.json")["ticket-assignment"]
    defects_known, _ = grade.variant_names(case)
    missing = sorted(set(STATED_DEFECTS + UNSTATED_DEFECTS) - set(defects_known))
    if missing:
        raise SystemExit(f"unknown calibrated defects: {missing}")
    drawn = {"stated": [], "unstated": []}  # every round's draws, in order, so a later round draws from what is left
    for number in range(1, round_number + 1):
        suffix = "" if number == 1 else f" round {number}"
        for kind, pool in (("stated", STATED_DEFECTS), ("unstated", UNSTATED_DEFECTS)):
            left = sorted(set(pool) - set(drawn[kind]))
            drawn[kind].append(random.Random(f"deep-judge calibration {kind}{suffix}").choice(left))
    stated, unstated = drawn["stated"][-1], drawn["unstated"][-1]
    (out_dir / "prompts").mkdir(parents=True)
    for name in ("request.md", "inventory.json", "inventory.md"):
        shutil.copy2(tickets / name, out_dir / name)
    shutil.copytree(tickets / "base", out_dir / "base")
    request = (out_dir / "request.md").read_text()
    chooser = random.Random("deep-judge calibration codes" + ("" if round_number == 1 else f" round {round_number}"))
    key = {}
    if round_number > 1:
        (out_dir / "audits").mkdir()
        for code, entry in load(first / "key.json").items():
            if entry["point"] in ("S", "F"):
                shutil.copytree(first / "products" / code, out_dir / "products" / code)
                shutil.copy2(first / "audits" / f"{code}.json", out_dir / "audits" / f"{code}.json")
                key[code] = {**entry, "audit_from_round": 1}
    for point, variant in (("S", "reference"), ("F", "reference"), ("L", stated), ("U", unstated)):
        if round_number > 1 and point in ("S", "F"):
            continue
        code = f"c{chooser.randrange(16 ** 6):06x}"
        product = out_dir / "products" / code
        grade.build_variant(case, variant, product, for_session=True)
        spec = None
        if point == "F":
            padded(product, request)
            spec = "docs/spec.md"
        done = subprocess.run(["npm", "test"], cwd=product, capture_output=True, text=True, timeout=600, check=False)
        key[code] = {"point": point, "variant": variant + (", padded" if point == "F" else ""), "spec": spec,
                     "own_tests_pass": done.returncode == 0}
    dump(out_dir / "key.json", key)
    write_audit_prompts(out_dir)
    print("calibration laid out (key.json is not for an auditor): "
          + "; ".join(f"{code} own tests {'pass' if entry['own_tests_pass'] else 'FAIL'}" for code, entry in key.items()))


def join_shares(root: Path, case: str) -> None:
    """One audit a product from its shares: the items of each share, every share's defects, the last share's notes."""
    case_dir = root / "deep" / case
    inv = load(case_dir / "inventory.json")
    shares = shares_of(inv)
    if len(shares) == 1:
        raise SystemExit(f"{case}: this inventory is audited in one piece")
    for code, entry in load(case_dir / "key.json").items():
        if entry.get("audit_from"):  # an audit carried over from the case this one was derived from is already whole
            continue
        parts = [load(case_dir / "audits" / f"{code}.share{number}.json") for number in range(1, len(shares) + 1)]
        audit = {"code": code, "ran": parts[-1].get("ran", {}), "shares": len(parts)}
        for kind in ("stated", "unstated"):
            wanted = [item["id"] for item in inv[kind]]
            rows = {row["id"]: row for part, items in zip(parts, shares) for row in part.get(kind, []) if row["id"] in items}
            missing = [item for item in wanted if item not in rows]
            if missing:
                raise SystemExit(f"{case}: {code} has no audit row for {', '.join(missing)}")
            audit[kind] = [rows[item] for item in wanted]
        audit["defects"] = [defect for part in parts for defect in part.get("defects", [])]
        for name in ("explored", "extras", "spec_notes", "tests_notes", "maintainer"):
            audit[name] = parts[-1].get(name, [] if name in ("explored", "extras") else "")
        dump(case_dir / "audits" / f"{code}.json", audit)
        print(f"{case}: {code} joined from {len(parts)} shares, {len(audit['defects'])} defects")


def fixed(root: Path, case: str) -> None:
    """Lay out CASE-fixed (journal section 11): the fixed product (ROOT/fix/CASE/work) under a new code name as S,
    beside ShipLoop's delivery (as F) and Ratchet's final (as L) with the audits they already have."""
    case_dir, out_dir = root / "deep" / case, root / "deep" / f"{case}-fixed"
    if (out_dir / "key.json").exists():
        raise SystemExit(f"{out_dir} is already laid out")
    (out_dir / "prompts").mkdir(parents=True)
    (out_dir / "audits").mkdir()
    for name in ("request.md", "inventory.json", "inventory.md"):
        shutil.copy2(case_dir / name, out_dir / name)
    shutil.copytree(case_dir / "base", out_dir / "base")
    code = f"p{random.Random(f'deep-judge codes {case} fixed').randrange(16 ** 6):06x}"
    shutil.copytree(root / "fix" / case / "work", out_dir / "products" / code, ignore=SKIP)
    key = {code: {"point": "S", "tree": str(root / "fix" / case / "work"), "spec": "docs/shiploop/spec.md"}}
    for old, entry in load(case_dir / "key.json").items():
        if entry["point"] in ("S", "L"):
            shutil.copytree(case_dir / "products" / old, out_dir / "products" / old)
            shutil.copy2(case_dir / "audits" / f"{old}.json", out_dir / "audits" / f"{old}.json")
            key[old] = {**entry, "point": "F" if entry["point"] == "S" else "L", "audit_from": case}
    dump(out_dir / "key.json", key)
    write_audit_prompts(out_dir)
    print(f"{case}-fixed: the fixed product is {code}; its audit prompt(s): "
          + ", ".join(sorted(path.name for path in (out_dir / "prompts").glob(f"audit-{code}*.md"))))


def lay_out(root: Path, case: str, suffix: str, sources: tuple) -> None:
    """Lay out CASE-SUFFIX: CASE's request, starting files and inventory, and each source as a product under a new
    code name (drawn by the seed "deep-judge codes CASE SUFFIX", in the order given), all to be audited afresh. A
    source is (point, folder, spec, commit). Without a commit the folder is copied, less `.git` and `node_modules`;
    with one, the folder is a Git repository and the product is that commit's files, exported as measure.py exports
    a run's starting files."""
    case_dir, out_dir = root / "deep" / case, root / "deep" / f"{case}-{suffix}"
    if (out_dir / "key.json").exists():
        raise SystemExit(f"{out_dir} is already laid out")
    missing = [str(folder) for _, folder, _, _ in sources if not folder.is_dir()]
    if missing:  # checked before anything is made, so a failed layout leaves no folder that blocks the next try
        raise SystemExit(f"{case}-{suffix}: no folder {', '.join(missing)}")
    (out_dir / "prompts").mkdir(parents=True)
    for name in ("request.md", "inventory.json", "inventory.md"):
        shutil.copy2(case_dir / name, out_dir / name)
    shutil.copytree(case_dir / "base", out_dir / "base")
    chooser = random.Random(f"deep-judge codes {case} {suffix}")
    key = {}
    for point, folder, spec, commit in sources:
        code = f"p{chooser.randrange(16 ** 6):06x}"
        product = out_dir / "products" / code
        if commit:
            product.mkdir(parents=True)
            archive = subprocess.run(["git", "-C", str(folder), "archive", commit], capture_output=True, check=True).stdout
            subprocess.run(["tar", "-x", "-C", str(product)], input=archive, check=True)
            key[code] = {"point": point, "tree": str(folder), "commit": commit, "spec": spec}
        else:
            shutil.copytree(folder, product, ignore=SKIP)
            key[code] = {"point": point, "tree": str(folder), "spec": spec}
    dump(out_dir / "key.json", key)
    write_audit_prompts(out_dir)
    print(f"{case}-{suffix}: " + ", ".join(f"{code} {entry['point']}" for code, entry in key.items()) + "; audit prompts: "
          + ", ".join(sorted(path.name for path in (out_dir / "prompts").glob("audit-*.md"))))


def clean(root: Path, fresh: Path, case: str) -> None:
    """Lay out CASE-clean (journal section 14): three products, all to be audited afresh under new code names. S is
    the fresh ShipLoop delivery after the look and the fix (FRESH/fix/CASE/work), F the fresh delivery itself
    (FRESH/delivered/CASE), L last night's Ratchet final (the copy under ROOT/deep/CASE/products)."""
    case_dir = root / "deep" / case
    old = next(code for code, entry in load(case_dir / "key.json").items() if entry["point"] == "L")
    lay_out(root, case, "clean", (("S", fresh / "fix" / case / "work", "docs/shiploop/spec.md", None),
                                  ("F", fresh / "delivered" / case, "docs/shiploop/spec.md", None),
                                  ("L", case_dir / "products" / old, "ratchet/spec.md", None)))


def ratchet_final(ratchet: Path, case: str) -> tuple:
    """A Ratchet run's final as `prepare` takes it: the commit measure.py records as the point `final` (run.json's
    last snapshot), in the run's work repository. `prepare` copies measure.py's clone checked out at that commit; the
    clone is made only by the parts that read it, so the commit is exported from the run's own repository instead.
    On last night's four runs both give the same files."""
    label = f"{case}-2"  # the Ratchet arm's run, as in POINTS
    path = ratchet / "measure" / label / "measures.json"
    if not path.exists():
        raise SystemExit(f"{path} is missing: run `measure.py {ratchet} {label}` first (any part); it records the "
                         "run's final commit")
    record = load(path)
    commit = (record.get("points") or {}).get("final")
    if record.get("arm") != "ratchet" or record.get("case") != CASES[case] or not commit:
        raise SystemExit(f"{path} records no final point of a Ratchet run of {CASES[case]}")
    return ratchet / label / "work", commit


def fresh_runs(root: Path, fresh: Path, ratchet: Path, case: str) -> None:
    """Lay out CASE-fresh (journal section 16.1): three products, all to be audited afresh under new code names. S and
    F are CASE-clean's (FRESH/fix/CASE/work and FRESH/delivered/CASE); L is the final of a fresh Ratchet run,
    RATCHET/CASE-2, exported at the commit its measure record names."""
    work, commit = ratchet_final(ratchet, case)
    lay_out(root, case, "fresh", (("S", fresh / "fix" / case / "work", "docs/shiploop/spec.md", None),
                                  ("F", fresh / "delivered" / case, "docs/shiploop/spec.md", None),
                                  ("L", work, "ratchet/spec.md", commit)))


def grade_class(kind: str, grade: str | None) -> str:
    if kind == "stated":
        return "yes" if grade == "yes" else "short"
    if grade == "not-applicable":
        return "n/a"
    return "ok" if grade in ("sound", "acceptable") else "short"


def defects(root: Path, case: str) -> None:
    case_dir = root / "deep" / case
    key, inv = load(case_dir / "key.json"), load(case_dir / "inventory.json")
    audits = {code: load(case_dir / "audits" / f"{code}.json") for code in key}
    reported = [{"from": code, "n": f"{code}#{number}", **defect}
                for code, audit in audits.items() for number, defect in enumerate(audit.get("defects", []), 1)]
    recheck = []
    for kind, field in (("stated", "built"), ("unstated", "handling")):
        for item in inv[kind]:
            grades = {code: next((row.get(field) for row in audit[kind] if row["id"] == item["id"]), None)
                      for code, audit in audits.items()}
            if len({grade_class(kind, grade) for grade in grades.values()}) > 1:
                recheck.append({"id": item["id"], "kind": kind, "text": item["text"], "audits_said": grades})
    dump(case_dir / "defects-reported.json", {"recheck": recheck, "defects": reported})
    codes = ", ".join(f"`{code}`" for code in key)
    (case_dir / "prompts" / "probe.md").write_text(PROBE.format(case_dir=case_dir, codes=codes, work=case_dir / "work" / "probe"))
    print(f"{case}: {len(reported)} defects reported, {len(recheck)} items to recheck ({', '.join(row['id'] for row in recheck)}); prompt probe.md")


def letters_of(case: str, key: dict, judge: str) -> dict:
    codes = sorted(code for code, entry in key.items() if entry["point"] in NAMES)
    random.Random(f"deep-judge letters {case} {judge}").shuffle(codes)
    return dict(zip(codes, "XYZ"))


def rechecked(case_dir: Path) -> dict:
    return {(row["id"], code): result["grade"] for row in load(case_dir / "defects-probed.json").get("rechecks", [])
            for code, result in row["results"].items()}


def told_by_reader(case_dir: Path) -> dict:
    """(item id, code) -> the single reader's answer from told.json: {"told": "yes" or "no", "where": ...}."""
    path = case_dir / "told.json"
    if not path.exists():
        raise SystemExit(f"{case_dir.name}: {path} is missing: run `deep_judge.py told-packet ROOT {case_dir.name}`, "
                         "then the session prompts/told.md instructs, before this step")
    answers = {}
    for row in load(path)["told"]:
        for code, result in row["results"].items():
            if result.get("told") not in ("yes", "no"):
                raise SystemExit(f"{path}: {row['id']} on {code} has told {result.get('told')!r}, not yes or no")
            answers[(row["id"], code)] = result
    return answers


def audit_of(case_dir: Path, code: str, reader_told: bool = True) -> dict:
    """The audit with the cross-probe's re-runs applied to the items it re-ran, and with the single reader's `told`
    (told.json) on every unstated item unless `reader_told` is false."""
    audit, again = load(case_dir / "audits" / f"{code}.json"), rechecked(case_dir)
    for kind, field in (("stated", "built"), ("unstated", "handling")):
        for row in audit[kind]:
            if (row["id"], code) in again:
                row[field], row["rerun"] = again[(row["id"], code)], True
    if reader_told:
        # The auditor's own `told` is superseded. On four calibration products whose delivered documents are
        # identical, the four auditors answered yes on 1, 0, 3 and 2 of 19 items: per-auditor noise larger than D4's
        # margin of 2 items. One reader now answers for every product of a case, with one standard and a quoted line.
        told = told_by_reader(case_dir)
        missing = [row["id"] for row in audit["unstated"] if (row["id"], code) not in told]
        if missing:
            raise SystemExit(f"{case_dir / 'told.json'} has no answer for {code} on {', '.join(missing)}")
        for row in audit["unstated"]:
            answer = told[(row["id"], code)]
            row["told"], row["told_where"] = answer["told"], answer.get("where", "")
    return audit


def excluded_paths(product: Path, spec: str | None) -> list:
    """The builders' specification and working notes inside a product, left out of what its documents tell."""
    if not spec:
        return []
    parent = Path(spec).parent
    paths = [f"{parent}/" if parent.name in ("shiploop", "ratchet") else spec]
    paths += [f"{name}/" for name in ("ratchet", "acceptance") if (product / name).is_dir()]
    return list(dict.fromkeys(paths))


def told_packet(root: Path, case: str) -> None:
    case_dir = root / "deep" / case
    key, inv = load(case_dir / "key.json"), load(case_dir / "inventory.json")
    rows = {code: {row["id"]: row for row in audit_of(case_dir, code, reader_told=False)["unstated"]} for code in key}
    seen = {(row["id"], code): result.get("observed", "")
            for row in load(case_dir / "defects-probed.json").get("rechecks", []) for code, result in row["results"].items()}
    items = []
    for item in inv["unstated"]:
        behaviour = {}
        for code in key:
            row = rows[code].get(item["id"])
            if row is None:
                behaviour[code] = "the audit has no row for this item"
                continue
            text = row.get("behaviour") or "not recorded"
            if row.get("rerun"):
                text += f" The cross-probe re-ran it and saw: {seen.get((item['id'], code)) or 'not recorded'}"
            behaviour[code] = f"{text} (handling: {row.get('handling')})"
        items.append({"id": item["id"], "text": item["text"], "behaviour": behaviour})
    dump(case_dir / "told-input.json", {"items": items})
    excluded = []
    for code, entry in key.items():
        paths = excluded_paths(case_dir / "products" / code, entry.get("spec"))
        excluded.append(f"   - `{code}`: " + (", ".join(f"`{path}`" for path in paths) or "nothing"))
    codes = ", ".join(f"`{code}`" for code in key)
    (case_dir / "prompts" / "told.md").write_text(TOLD.format(case_dir=case_dir, codes=codes, excluded="\n".join(excluded)))
    print(f"{case}: {len(items)} unstated items, {len(key)} products; told-input.json and prompt told.md")


def verdict_packet(root: Path, case: str) -> None:
    case_dir = root / "deep" / case
    key = load(case_dir / "key.json")
    probed = load(case_dir / "defects-probed.json")["defects"]
    record = {}
    for judge in JUDGES:
        letters = letters_of(case, key, judge)

        def relabel(text: str, letters=letters) -> str:
            for code, letter in letters.items():
                text = text.replace(code, letter)
            for code in key:  # a product outside the three (the calibration's fourth) is not shown
                text = text.replace(code, "another")
            return mask(text)

        order = sorted(letters, key=letters.get)
        table = []
        for defect in probed:
            results = "; ".join(f"{letters[code]}: {defect['results'].get(code, {}).get('result', 'not tried')}" for code in order)
            if "present" in results:
                table.append(f"- **{defect['id']}** ({defect['severity']}) {defect['title']}. Expected: {defect['expected']} — {results}")
        audits = []
        for code in order:
            audit = audit_of(case_dir, code)
            for name in ("defects", "ran", "explored"):  # the probed table replaces each auditor's own list
                audit.pop(name, None)
            # A test's strength by reading differs between auditors on identical tests (14, 11 and 14 of 21 on the
            # calibration's three copies of one suite), so the judges see only what was proved by breaking the behaviour.
            for row in audit["stated"] + audit["unstated"]:
                row.pop("test", None)
                row.pop("test_name", None)
            audit["code"] = letters[code]
            audits += [f"## Audit of delivery {letters[code]}", "", "```json", relabel(json.dumps(audit, indent=1, ensure_ascii=False)), "```", ""]
        by_point = {key[code]["point"]: letter for code, letter in letters.items()}
        pairs = [f"{by_point[first]}-{by_point[second]}" for first, second in PAIRS]
        text = VERDICT.format(letters="X, Y and Z", pairs=", ".join(pairs), example=pairs[0],
                              request=(case_dir / "request.md").read_text().strip(),
                              inventory=(case_dir / "inventory.md").read_text().strip().replace("# Inventory\n", ""),
                              defects=relabel("\n".join(table)) or "No defect reproduced.", audits="\n".join(audits))
        (case_dir / "prompts" / f"verdict-{judge}.md").write_text(text)
        record[judge] = {"letters": letters, "pairs": pairs, "characters": len(text)}
    dump(case_dir / "letters.json", record)
    print(f"{case}: " + "; ".join(f"verdict-{judge}.md {entry['characters']} characters, pairs {entry['pairs']}" for judge, entry in record.items()))


def share(count: int, total: int):
    return None if not total else round(count / total, 3)


def ahead(first, second, items: int, points: float | None = None, fewer: bool = False):
    """'first', 'second' or None, by the registered margin: `items` more (or fewer), and `points` of share where given."""
    (a_count, a_total), (b_count, b_total) = first, second
    difference = (b_count - a_count) if fewer else (a_count - b_count)
    if abs(difference) < items:
        return None
    if points is not None:
        a_share, b_share = share(a_count, a_total), share(b_count, b_total)
        if a_share is None or b_share is None or abs(a_share - b_share) < points - 1e-9:
            return None
    return "first" if difference > 0 else "second"


def facts_of(case_dir: Path, code: str, inv: dict, probed: list, primary: bool) -> dict:
    audit = audit_of(case_dir, code)
    stated = audit["stated"]
    wanted = {item["id"] for item in inv["unstated"] if item["independent"] or not primary}
    unstated = [row for row in audit["unstated"] if row["id"] in wanted and row.get("handling") != "not-applicable"]
    proved = [row for row in stated if row["id"] in inv["proved"]]
    present = [defect for defect in probed if defect["results"].get(code, {}).get("result") == "present"]
    not_built = [row["id"] for row in stated if row["built"] != "yes"]
    high = [defect["id"] for defect in present if defect["severity"] == "high"]
    return {"stated": len(stated), "built": len(stated) - len(not_built), "not_built": not_built,
            "proved_of": len(proved), "proved": sum(1 for row in proved if row.get("proved") == "fails"),
            "strong_test_read": sum(1 for row in stated if row.get("test") == "strong"),
            "unstated": len(unstated),
            "handled": sum(1 for row in unstated if row.get("handling") in ("sound", "acceptable")),
            "short": [row["id"] for row in unstated if row.get("handling") in ("poor", "unhandled")],
            "told": sum(1 for row in unstated if row.get("told") == "yes"),
            "told_or_marked": sum(1 for row in unstated if row.get("told") == "yes" or row.get("spec") in ("open", "decided-marked")),
            "unstated_strong_test_read": sum(1 for row in unstated if row.get("test") == "strong"),
            "defects": sum(1 for defect in present if defect["severity"] in ("high", "medium")),
            "defects_high": high, "defects_low": sum(1 for defect in present if defect["severity"] == "low"),
            "defect_ids": [defect["id"] for defect in present],
            "serious": len(high) + len(not_built),
            "extras": {worth: sum(1 for extra in audit.get("extras", []) if extra.get("worth") == worth)
                       for worth in ("value", "neutral", "liability")}}


def judges_of(case: str) -> tuple:
    """The judges whose verdicts count for a case. The owner, 2026-11-22, after the twelve products were judged by
    both families: "just use opus for the judge to speed things up". The derived cases (fixed, clean and fresh) are
    judged by Opus."""
    return ("a",) if case.endswith(("-fixed", "-clean", "-fresh")) else JUDGES


def judged(case_dir: Path, case: str, key: dict) -> dict:
    """Each pair's verdict from the case's judges, turned back to points: who is better, and whether one task closes it."""
    out = {}
    for judge in judges_of(case):
        path = case_dir / f"verdict-{judge}.json"
        if not path.exists():
            continue
        point_of = {letter: key[code]["point"] for code, letter in letters_of(case, key, judge).items()}
        for row in load(path)["pairs"]:
            pair = tuple(sorted((point_of[letter] for letter in row["pair"].split("-")), key="SFL".index))
            better = row["better"]
            out.setdefault(pair, {})[judge] = {
                "side": None if better == "same" else point_of[better.split("-")[0]],
                "strength": better.split("-")[-1], "one_task_closes": row.get("one_task_closes"),
                "why": row.get("why"), "lesser_lacks": row.get("lesser_lacks")}
    return out


def score(root: Path, out_dir: Path) -> None:
    report, lines = {}, ["# The deep judge", ""]
    rounds = {path.name: f"the instrument check, {path.name} (ticket assignment)"
              for path in sorted((root / "deep").glob("calibration*"))}
    fixes = {f"{case}-fixed": f"{name}, after one look and one fix" for case, name in CASES.items()}
    fixes.update({f"{case}-clean": f"{name}, clean ShipLoop run with one look and one fix" for case, name in CASES.items()})
    fixes.update({f"{case}-fresh": f"{name}, fresh runs of both tools" for case, name in CASES.items()})
    for case, full_name in {**CASES, **fixes, **rounds}.items():
        case_dir = root / "deep" / case
        if not (case_dir / "defects-probed.json").exists():
            continue
        if not (case_dir / "told.json").exists():  # a case is scored once the single reader has answered
            lines += [f"## {full_name}", "", "Not scored yet: told.json is missing (the `told-packet` step and its reader).", ""]
            continue
        key, inv = load(case_dir / "key.json"), load(case_dir / "inventory.json")
        names = (CALIBRATION_NAMES if case.startswith("calibration") else FIXED_NAMES if case.endswith("-fixed")
                 else CLEAN_NAMES if case.endswith("-clean") else FRESH_NAMES if case.endswith("-fresh") else NAMES)
        code_of = {entry["point"]: code for code, entry in key.items()}
        probed = load(case_dir / "defects-probed.json")["defects"]
        facts = {point: facts_of(case_dir, code, inv, probed, True) for point, code in code_of.items()}
        with_arm = {point: facts_of(case_dir, code, inv, probed, False) for point, code in code_of.items()}
        verdicts = judged(case_dir, case, key)
        pairs = {}
        for first, second in PAIRS:
            a, b = facts[first], facts[second]
            readings = {
                "D1": ahead((a["built"], a["stated"]), (b["built"], b["stated"]), 2),
                "D2": ahead((a["proved"], a["proved_of"]), (b["proved"], b["proved_of"]), 2),
                "D3": ahead((a["handled"], a["unstated"]), (b["handled"], b["unstated"]), 2, 0.10),
                "D4": ahead((a["told"], a["unstated"]), (b["told"], b["unstated"]), 2, 0.10),
                "D5": ahead((a["defects"], 0), (b["defects"], 0), 2, fewer=True)}
            both = verdicts.get((first, second), {})
            wanted = len(judges_of(case))
            sides = [both[judge]["side"] for judge in judges_of(case) if judge in both]
            agreed = sides[0] if len(sides) == wanted and len(set(sides)) == 1 and sides[0] else None
            readings["D6"] = None if agreed is None else ("first" if agreed == first else "second")
            counted = list(readings.values())
            lead = counted.count("first") - counted.count("second")
            better = first if lead >= 2 else second if lead <= -2 else None
            gate = None if a["serious"] == b["serious"] else (first if a["serious"] < b["serious"] else second)
            if gate:
                better = gate
            closes = [both[judge]["one_task_closes"] for judge in judges_of(case) if judge in both]
            pairs[f"{first}-{second}"] = {
                "readings": readings, "gate": gate, "better": better, "verdicts": both,
                "judges_agree": len(sides) == wanted and len(set(sides)) == 1,
                "one_task_closes_both": len(closes) == wanted and all(value == "yes" for value in closes)}
        main = pairs["S-L"]
        nearly = main["gate"] != "L" and (main["better"] in (None, "S") or main["one_task_closes_both"])
        rated = inv["rated"]
        arm_only = [row for row in rated if not row["independent"]]
        report[case] = {"facts": facts, "facts_with_arm_items": with_arm, "pairs": pairs, "nearly_competitive": nearly,
                        "rechecked_items": sorted({item for item, _ in rechecked(case_dir)}),
                        "inventory": {"stated": len(inv["stated"]), "proved": inv["proved"],
                                      "unstated_rated": len(rated),
                                      "independent": len(rated) - len(arm_only),
                                      "independent_kept": sum(1 for row in rated if row["independent"] and row["kept"]),
                                      "arm_only": len(arm_only),
                                      "arm_only_kept": sum(1 for row in arm_only if row["kept"])}}
        lines += [f"## {full_name}", "", "| | " + " | ".join(f"{point}: {names[point]}" for point in "SFL") + " |",
                  "|---|---|---|---|"]
        rows = (("D1 stated items built", lambda f: f"{f['built']} of {f['stated']}"),
                ("D2 tests proved by breaking the behaviour", lambda f: f"{f['proved']} of {f['proved_of']}"),
                ("D3 unstated items handled", lambda f: f"{f['handled']} of {f['unstated']}"),
                ("D4 unstated items told in the delivered documents", lambda f: f"{f['told']} of {f['unstated']}"),
                ("D5 reproducing defects, high or medium (of them high; low)",
                 lambda f: f"{f['defects']} ({len(f['defects_high'])}; {f['defects_low']})"),
                ("Serious: high defects and stated items not built", lambda f: str(f["serious"])),
                ("Reported: told, or marked in the specification", lambda f: f"{f['told_or_marked']} of {f['unstated']}"),
                ("Reported: stated items with a strong test, by reading", lambda f: f"{f['strong_test_read']} of {f['stated']}"),
                ("Reported: beyond the request, value / neutral / liability",
                 lambda f: "{value} / {neutral} / {liability}".format(**f["extras"])))
        lines += [f"| {name} | " + " | ".join(show(facts[point]) for point in "SFL") + " |" for name, show in rows]
        lines += ["| Reported: D3 with the items only an arm raised | " + " | ".join(
            f"{with_arm[point]['handled']} of {with_arm[point]['unstated']}" for point in "SFL") + " |", ""]
        for name, pair in pairs.items():
            first, second = name.split("-")
            shown = ", ".join(f"{reading} {first if side == 'first' else second}" for reading, side in pair["readings"].items() if side)
            said = "; ".join(f"judge {judge}: {entry['side'] or 'same'}" + (f" ({entry['strength']})" if entry["side"] else "")
                             for judge, entry in pair["verdicts"].items())
            lines.append(f"- **{name}**: better feature: {pair['better'] or 'no difference shown'}"
                         + (f" (by the gate: {pair['gate']} has fewer serious failures)" if pair["gate"] else "")
                         + f". Ahead: {shown or 'nowhere'}. {said or 'not judged'}. "
                         f"One short task closes the gap, both judges: {'yes' if pair['one_task_closes_both'] else 'no'}.")
        lines += [f"- **S nearly competitive with L: {'yes' if nearly else 'no'}**", ""]
        if "U" in code_of:
            extra = facts["U"]
            lines += [(f"- The fourth product ({key[code_of['U']]['variant']}): unstated items short {extra['short']}, "
                      f"reproducing defects {extra['defect_ids']}, stated items not built {extra['not_built']}"), ""]
    dump(out_dir / "deep.json", report)
    (out_dir / "deep.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit(__doc__)
    command, rest = argv[0], argv[1:]
    if command == "grab" and len(rest) == 2:
        answer = load(Path(rest[0]))
        found = first_json(answer.get("text") or "")
        if found is None:
            raise SystemExit(f"no JSON object in {rest[0]} (error: {answer.get('error')})")
        dump(Path(rest[1]), found)
        print(f"{rest[1]}: {', '.join(f'{name} {len(value)}' for name, value in found.items() if isinstance(value, list))}; model {answer.get('model_used')}")
        return 0
    if command == "score" and len(rest) == 2:
        score(Path(rest[0]).expanduser().resolve(), Path(rest[1]).expanduser().resolve())
        return 0
    if command == "calibrate" and len(rest) in (1, 2):
        calibrate(Path(rest[0]).expanduser().resolve(), int(rest[1]) if len(rest) == 2 else 1)
        return 0
    steps = {"prepare": prepare, "rate-packet": rate_packet, "inventory": inventory, "defects": defects,
             "join-shares": join_shares, "told-packet": told_packet, "verdict-packet": verdict_packet}
    late = ("defects", "join-shares", "told-packet", "verdict-packet")
    if command == "fixed" and len(rest) == 2 and rest[1] in CASES:
        fixed(Path(rest[0]).expanduser().resolve(), rest[1])
        return 0
    if command == "clean" and len(rest) == 3 and rest[2] in CASES:
        clean(Path(rest[0]).expanduser().resolve(), Path(rest[1]).expanduser().resolve(), rest[2])
        return 0
    if command == "fresh" and len(rest) == 4 and rest[3] in CASES:
        fresh_runs(Path(rest[0]).expanduser().resolve(), Path(rest[1]).expanduser().resolve(),
                   Path(rest[2]).expanduser().resolve(), rest[3])
        return 0
    derived = rest[1:] and (rest[1].startswith("calibration") or rest[1].removesuffix("-fixed") in CASES
                            or rest[1].removesuffix("-clean") in CASES or rest[1].removesuffix("-fresh") in CASES)
    if command in steps and len(rest) == 2 and (rest[1] in CASES or (derived and command in late)):
        steps[command](Path(rest[0]).expanduser().resolve(), rest[1])
        return 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    raise SystemExit(main())
