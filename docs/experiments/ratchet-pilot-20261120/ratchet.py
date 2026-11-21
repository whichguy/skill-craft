#!/usr/bin/env python3
"""Ratchet pilot: build a request in one pass, then let tests and what was learned drive every further pass.

    python3 ratchet.py run --case shared-expenses --host codex --model gpt-6.2-sol --effort high --output DIR
    python3 ratchet.py run --case ticket-assignment --host codex ... --start-tree TREE --frozen-from RUN   (a repair start)

This is an experiment apparatus (docs/ratchet-pilot-journal.md), not a released skill. The script owns the order of
the stages and writes every prompt; a model session does one stage and sees only the files. The stages:

  spec    (enrich) one session turns the request into use cases and numbered clauses a test can decide, with the
          requirements the request only implies (ratchet/spec.md)
  then, cycle after cycle:
  plan    one session plans how to build it, without cutting it into steps: approach, decisions, the nuances a quick
          build gets wrong, a build order (ratchet/plan.md), inside an Until Loop that asks for one more full look
          after the first; it may add clauses
  build   one session builds the whole request (cycle 1), or whatever does not yet match the longer specification
          (later cycles), inside an Until Loop whose exit check is this pilot's gate
  tests   another session, which did not build, writes acceptance tests for every clause and runs them; the script
          then freezes them
  fix     while the gate fails, a session fixes the product inside an Until Loop whose exit check is the gate; a test
          the builder disputes goes to the test owner (a referee session), never to the builder
  delta   every check passes: a session asks what was learned that the specification does not say, and adds clauses
  The run ends when a delta stage adds no clause. New clauses start the next cycle.

The spec only grows: a later stage may add a clause and never change one. Only script-run checks decide anything.
Limits of this apparatus (not of the idea): --max-cycles and --max-fixes bound a run and are reported when they end it.

Everything is written under the output folder: work/ (the product's Git repository; a commit per stage), sessions/,
gates/, loops/, tools/ (copies of gate.py and the Until Loop runtime, so no prompt names this repository) and
run.json (the record grade.py reads).
"""
import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
E2E = REPO / "test" / "shiploop_e2e"
RUNTIME = REPO / "skills" / "improve" / "runtime" / "until-loop" / "scripts"
sys.path.insert(0, str(HERE))
import gate as gate_module

ITEM = re.compile(r"^### ((?:C|U)-\d+): *(.+)$", re.MULTILINE)
HELD_OUT_MARKS = ("shiploop_e2e", "chess_hidden", "fixtures/quality", "due_times_probe", "ticket_assignment_accept",
                  "expense_service.py", "skill-craft")
SESSION_SECONDS = 2700

CONDUCT = """## Rules of conduct
- Work only inside this folder: {work}. Nothing outside it is yours to read for this task or to change.
- Temporary files go under {tmp} (TMPDIR is set to it).
- A server you start listens on a port that is free at that moment (ask the system for port 0, or pick a random high
  port), never a fixed default. Stop every process you started, by its process id. Never stop processes by name
  (no pkill, no killall).
- Install nothing from the network. Do not commit, push or change Git history: the script that runs you commits.
- You run unattended. Ask no questions: where you must choose, choose, and write the choice where this packet says.
"""

FRAME = ("You are one stage of a loop that a script runs: the request enriched into a specification, a plan, a build of "
         "all of it in one pass, a heavy test pass, fixes until every check passes, then a look at what was learned, which "
         "may lengthen the specification and start the next cycle. A different session does each stage and knows only what "
         "the files say.")

SPEC_PACKET = """# Ratchet stage: enrich (the request, made complete)

{frame} This stage turns the incoming request into the enriched specification that everything after it is planned,
built and tested from. Write no product code and no tests.

## The incoming request
{request}

## What to do
1. Read what is here: the README, the documents, the code and its tests, as far as the request touches them. In an
   existing product the rules it already follows (how it answers errors, how it stores data, what its documents
   promise) bind the change too.
2. Find the use cases: everyone who will meet this change, and every way they meet it. The ordinary use the request
   describes. The same use at its edges: the first time, the repeated time, the empty case, the largest case. The
   unhappy paths: wrong input, a refused action, a limit reached. What an operator does: start, restart, configure,
   carry on with the data that exists today, go back to the version before. And where the change touches features
   that already exist.
3. Find the implied requirements. For each use case ask what must be true for it to work that the request never
   says, and what the request's own sentences take for granted. Each becomes a clause.
4. Write `ratchet/spec.md` in exactly this form, use cases first:

## Use cases

### U-<n>: <who> <does what, to get what>
Flow: <the steps they take and what they see, with the exact values where the request gives them>
Source: <request | implied: <by which sentence or situation> | existing: <the file that describes it>>

## Clauses

### C-<n>: <one statement of one behaviour, complete in itself>
Observable: <what someone outside the code does and sees when it holds, with the exact values>
Source: <request | implied: <by which use case or sentence> | existing: <the file that states the rule> | choice: <why, where the request is silent>>

The clauses cover every sentence of the request; every implied requirement; every limit, boundary and error case,
with its exact number; every existing rule the change must keep (one clause each); and what must not change. Where
the request is silent and a builder would have to guess, decide and say so (Source: choice). Add no feature the
request's intent does not cover. Number use cases U-1, U-2, ... and clauses C-1, C-2, ... with no gaps. One behaviour
a clause: a statement joined by "and" is two clauses.

## Done when
- `ratchet/spec.md` exists in that form and is the only file you changed.
{problems}
{conduct}"""

PLAN_PACKET = """# Ratchet stage: plan ({title})

{frame} This stage plans how to build it. It does not cut the work into steps for others: right after you, one
session builds all of it in one pass. The plan is the thinking that pass needs done first, above all where the
nuance is.

## The incoming request
{request}

## The enriched specification
`ratchet/spec.md` holds the use cases (U-n) and the clauses (C-n). {what}

## What to do
Write `ratchet/plan.md`{append} with these five sections:

## Approach
how the change fits what exists: the parts it touches, the data and the interfaces
## Decisions
each design choice a builder would otherwise make by accident: the choice, the reason, the alternative you rejected
## Nuances
what a quick build would get wrong. Look where clauses meet each other, where the change meets behaviour that exists,
and at state, order, limits, error paths, restart, existing data and going back. For each: the clause or use case it
bears on, what goes wrong, what to do about it.
## Build order
the order to build in, within the one pass, so that each part can be checked as it lands
## How we will know
for each use case, what to run or observe to see it work, and what a test of this change must not forget

Look more than once: after a first full plan, read the specification, the code and your plan again for a nuance you
missed, and stop when a full pass finds nothing that would change the build.
If planning shows that the specification lacks something a use case needs, add it at the end of `ratchet/spec.md` as a
clause with the next number and `Source: implied: <what showed it>`. Never edit, reorder or remove an existing clause
or use case. Write no product code and no tests.

{loop}

## Done when
- `ratchet/plan.md` has the five sections, and nothing changed but it and clauses added to `ratchet/spec.md`.

{conduct}"""

BUILD_PACKET = """# Ratchet stage: build ({title})

{frame} This stage builds the product.

## The request
{request}

## The specification
`ratchet/spec.md` holds the request as numbered clauses (C-1, C-2, ...). {what}
Where the code you find disagrees with the specification, the specification wins. Where the specification is silent,
decide, and report the decision as a discovery (below).

## The plan
`ratchet/plan.md` is the plan a session wrote for this pass: its approach, its decisions, the nuances a quick build
gets wrong and a build order. Build by it. Where you find it wrong, do what the specification needs and say so under
Discoveries.

## Everything this pass owes
- The product code for every clause.
- The tests the request itself asks for, with the product's existing tests still passing unchanged.
- The documents the change makes wrong or incomplete (the README, interface or operations documents, a changelog the
  product keeps).
- Code in the product's own style that its own lint and syntax checks accept.
{acceptance_note}

{loop}

## Your report: `ratchet/build-{cycle}.md`
## Done
what you built, by clause id
## Not done
clause ids you did not finish, each with the reason ("none" when there are none)
## Discoveries
what building taught you that the specification does not say and a user or operator would care about: a limit nobody
stated, a sentence with two readings and the one you took, existing behaviour that conflicts with the request, a side
effect that misbehaves. One a line, or "none":
- <the statement the specification should carry> | Observable: <how to see it> | Why: <what you met>

## Done when
- every clause is built or listed under Not done, the loop's exit check passes and the report exists.

{conduct}"""

TESTS_PACKET = """# Ratchet stage: tests (the heavy test pass)

{frame} This stage owns the acceptance tests. You did not build the product, and you judge it by the specification,
never by what the code happens to do.

## The request
{request}

## What to do
1. {scope} write test cases under `acceptance/` that fail when exactly that clause is broken in an otherwise correct
   product and pass when it holds. Take each expected result from the clause's own words and its Observable line. For
   every number or limit a clause states, test the last value that must be accepted and the first that must be
   refused. Test what a clause implies without saying it: the empty case, the repeated case, and the case after a
   restart where data is kept.
   For every use case (U-n) write one scenario test that walks its whole flow as that user would, start to end.
   `ratchet/plan.md` (How we will know, Nuances) and the Discoveries in `ratchet/build-*.md` name scenarios worth a
   test: add those, and any other scenario the specification implies.
2. Reach the product only as its users do: its HTTP interface, its command line, the module interface the request
   names, a data file the request names. Never its internal functions: another correct implementation must pass the
   same tests.
3. Give every clause and every use case an entry in `ratchet/acceptance.json`:
   {{"C-1": {{"command": "<one shell command, run from this folder, that runs only this item's tests and exits 0 when they pass>"}}, "U-1": {{...}}, ...}}
   Each command ends within 60 seconds, uses a free port and leaves no process behind.
4. Run every command against the product as it stands. A test that fails because the product breaks its clause
   STAYS as it is: do not weaken it and do not fix the product. A test that fails because the test is wrong (it
   contradicts its clause) is yours to correct.{keep}
5. Write `ratchet/tests-{cycle}.md`:
## Failing now
clause ids whose tests fail on the product, each with what the product did instead ("none" when none fail)
## Discoveries
what writing and running the tests taught you that the specification does not say: an unstated limit, a clause with
two readings, behaviour next to the change that surprised you. One a line, or "none":
- <the statement the specification should carry> | Observable: <how to see it> | Why: <what you met>

## Done when
- every clause and every use case has tests and an entry, and you changed nothing outside `acceptance/`, `ratchet/acceptance.json` and
  `ratchet/tests-{cycle}.md`.
{problems}
{conduct}"""

FIX_PACKET = """# Ratchet stage: fix

{frame} This stage fixes the product until every check the script runs passes.

## The request
{request}

## What fails now (the script ran every check a moment ago)
{failing}

## What to do
Fix the product so that every check passes, the ones listed and the ones that pass today. `ratchet/spec.md` is the
specification. The acceptance tests under `acceptance/`, `ratchet/spec.md` and `ratchet/acceptance.json` are frozen:
the gate puts back any change to them and counts it. If you are sure a test contradicts the specification, do not work
around it: keep the product right by the specification and name the test under Disputed.

{loop}

## Your report: `ratchet/fix-{number}.md`
## Fixed
each failing check and what was wrong in the product
## Disputed
tests that contradict the specification, or "none". One a line:
- <clause id> | the test expects: <...> | the clause says: <...> | why they differ
## Discoveries
what fixing taught you that the specification does not say, one a line in the form
`- <statement> | Observable: <how to see it> | Why: <what you met>`, or "none"

## Done when
- the loop's exit check passes, or every check still failing is named under Disputed; and the report exists.

{conduct}"""

REFEREE_PACKET = """# Ratchet stage: disputed tests

{frame} You own the acceptance tests and did not build the product. The builder says these tests contradict the
specification:

{disputes}

## What to do
For each one read the clause in `ratchet/spec.md`, its Observable line and the test. If the test asks for something
the clause does not say, or contradicts it, correct the test (and its entry in `ratchet/acceptance.json` if the
command changes). If the test is right, leave it as it is. Change neither the product nor the specification.
Write `ratchet/referee-{number}.md`: each dispute, your ruling (test corrected | test stands) and the reason.

## Done when
- every dispute has a ruling, and you changed nothing outside `acceptance/`, `ratchet/acceptance.json` and the report.

{conduct}"""

DELTA_PACKET = """# Ratchet stage: what did we learn (the closing look)

{frame} Every check passes now. This stage asks one question: compared with the specification as it stands, is there
anything we now know (it was implicit, nobody knew it at the start, or building and testing discovered it) that the
specification should state, whether or not the product already keeps to it?

## The request
{request}

## What to weigh
- The reports of the stages before you: `ratchet/build-*.md`, `ratchet/tests-*.md`, `ratchet/fix-*.md` and
  `ratchet/referee-*.md`, above all their Discoveries, Not done and Disputed sections; and `ratchet/plan.md`, for a
  nuance it named that no clause carries.
- The product itself. Start it and use it as its users and operators would: the request's own examples, values at
  and just past each limit, wrong and odd input, the features next to the change, a restart, what its documents
  promise. Use it; do not only read it.
- The request, read once more for what it implies and the specification does not state.

## What to do
Decide whether the specification needs another level: a use case nobody wrote down, an implied requirement that
only shows now that the product runs, a limit or an interaction the first pass did not reach.
For each real finding add a clause at the end of `ratchet/spec.md` (or a use case, for a way of using the product
that nobody wrote down), in the form the others have, with the next number and `Source: discovery: <what showed it>`. A finding is real when a user or operator would care, the request's intent
covers it and a test could show it. It is not a new feature, a matter of taste or an existing clause said again.
Never edit, reorder or remove an existing clause or use case.
Write `ratchet/delta-{cycle}.md`: what you used and tried; then each clause you added with
"product keeps to it: yes | no | not checked"; or the single line "No delta." when you add nothing.
Change neither the product nor any test.

## Done when
- only `ratchet/spec.md` and `ratchet/delta-{cycle}.md` changed.

{conduct}"""

LOOP_BLOCK = """## The loop
This stage runs inside an Until Loop: a small script that restates the work and decides when you are done by running
the exit check itself. RUN it now, once, before any work:

    python3 {runtime} start --receipt {receipt} < {contract}

Then follow each instruction it prints: do the work, then run the `done` command it gives you with your report, and
again, until it says the run is complete or stopped. Never write or edit the receipt file. If the receipt already
exists and says the run is active, run its `next_argv` instead of starting again.
{check_note}"""

GATE_NOTE = ("The exit check is `python3 {gate} {work}`: it runs every acceptance check there is, the project's own checks "
             "({checks}) and a syntax check of the files you changed, and exits 0 only when nothing fails. You may run it "
             "yourself at any time.")


# ------------------------------------------------------------------ small helpers
def git(work, *args, check=True):
    done = subprocess.run(["git", "-C", str(work), *args], capture_output=True, text=True, check=False)
    if check and done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {work}: {done.stderr.strip()[:400]}")
    return done.stdout


def read_spec(work):
    """The specification's items in file order, {id: {statement, observable, source, block}}: clauses (C-n, with an
    Observable line) and use cases (U-n, with a Flow line; `observable` holds its first line). Raises ValueError
    saying what is wrong."""
    path = Path(work) / "ratchet" / "spec.md"
    if not path.is_file():
        raise ValueError("ratchet/spec.md does not exist")
    parts = ITEM.split(path.read_text())
    found = {}
    for index in range(1, len(parts), 3):
        ident, statement, body = parts[index], parts[index + 1].strip(), parts[index + 2]
        body = re.split(r"^## ", body, maxsplit=1, flags=re.MULTILINE)[0]  # a section heading ends the item
        if ident in found:
            raise ValueError(f"{ident} appears twice")
        need = "Observable" if ident.startswith("C-") else "Flow"
        shown = re.search(rf"^{need}: *(.*)$", body, re.MULTILINE)
        source = re.search(r"^Source: *(.+)$", body, re.MULTILINE)
        if not shown or not source:
            raise ValueError(f"{ident} lacks its {need} or Source line")
        found[ident] = {"statement": statement, "observable": shown.group(1).strip(), "source": source.group(1).strip(),
                        "block": f"### {ident}: {statement}{body.rstrip()}\n"}
    for kind, name in (("C-", "clauses"), ("U-", "use cases")):
        numbers = [int(ident[2:]) for ident in found if ident.startswith(kind)]
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError(f"{name} are not numbered {kind}1 to {kind}{len(numbers)} in order")
    if not any(ident.startswith("C-") for ident in found):
        raise ValueError("ratchet/spec.md holds no clause of the form '### C-<n>: <statement>'")
    return found


def section(text, title):
    """The lines of a `## title` section of a report, without blank lines."""
    found = re.search(rf"^## {re.escape(title)}\s*$(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    return [line.strip() for line in found.group(1).splitlines() if line.strip()] if found else []


def items(lines):
    """The real entries of a report section: `- ...` lines, with a lone "none" read as nothing."""
    entries = [line[1:].strip() for line in lines if line.startswith("-")]
    return [entry for entry in entries if entry.lower().strip(". ") != "none"]


def load_case(name):
    cases = json.loads((HERE / "cases.json").read_text())
    if name not in cases or name.startswith("_"):
        raise SystemExit(f"unknown case {name!r}; known: {', '.join(key for key in cases if not key.startswith('_'))}")
    return cases[name]


def load_fake(path):
    spec = importlib.util.spec_from_file_location("ratchet_fake_host", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.act


# ------------------------------------------------------------------ the run
class Run:
    def __init__(self, args, case):
        self.args, self.case = args, case
        self.out = Path(args.output).resolve()
        if self.out.exists() and any(self.out.iterdir()):
            raise SystemExit(f"{self.out} is not empty; give a new output folder")
        self.work, self.tmp, self.tools = self.out / "work", self.out / "tmp", self.out / "tools"
        for folder in (self.work, self.tmp, self.tools, self.out / "sessions", self.out / "gates", self.out / "loops"):
            folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HERE / "gate.py", self.tools / "gate.py")
        for script in RUNTIME.glob("*.py"):
            shutil.copy2(script, self.tools / script.name)
        self.request = case["request"]
        self.checks = list(case.get("checks") or [])
        self.record = {"case": args.case, "host": args.host, "model": args.model, "effort": args.effort,
                       "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "start_tree": args.start_tree,
                       "frozen_from": args.frozen_from, "build_from": args.build_from, "sessions": [], "gates": [], "snapshots": [], "cycles": [],
                       "reverted": [], "spec_violations": [], "local_head": git(REPO, "rev-parse", "HEAD").strip()}
        self.fake = load_fake(args.fake) if args.host == "fake" else None
        self.host = self.env = None
        if not self.fake:
            sys.path.insert(0, str(E2E))
            import hosts  # the E2E harness's host launcher
            self.hosts = hosts
            self.host = hosts.host(args.host)
            self.host.model = args.model or self.host.model
            self.record["model"] = self.host.model
            self.record["effort"] = args.effort or self.host.effort
            self.env = dict(self.host.env(self.out / "home"), TMPDIR=str(self.tmp))

    # -- records
    def save(self):
        (self.out / "run.json").write_text(json.dumps(self.record, indent=1) + "\n")

    def say(self, text):
        if not self.args.quiet:
            print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)

    def conduct(self):
        return CONDUCT.format(work=self.work, tmp=self.tmp)

    # -- the work repository
    def gate_config(self, **changes):
        path = self.work / ".git" / "ratchet-gate.json"
        config = json.loads(path.read_text()) if path.exists() else {"base": None, "frozen": None, "checks": self.checks}
        config.update(changes)
        path.write_text(json.dumps(config) + "\n")
        return config

    def commit(self, label):
        git(self.work, "add", "-A")
        git(self.work, "commit", "-q", "--allow-empty", "-m", label)
        commit = git(self.work, "rev-parse", "HEAD").strip()
        self.record["snapshots"].append({"label": label, "commit": commit, "tree": git(self.work, "rev-parse", "HEAD^{tree}").strip(),
                                         "at": round(time.time() - self.began, 1)})
        self.save()
        return commit

    def setup(self):
        self.began = time.time()
        if self.args.start_tree:
            shutil.copytree(self.args.start_tree, self.work, dirs_exist_ok=True)
        else:
            if self.case.get("fixture"):
                shutil.copytree(E2E / "fixtures" / self.case["fixture"], self.work, dirs_exist_ok=True)
            shutil.rmtree(self.work / "docs" / "shiploop", ignore_errors=True)  # the seeded knowledge home: Ratchet writes its own spec
        git(self.work, "init", "-q", "-b", "main")
        git(self.work, "config", "user.name", "Ratchet pilot")
        git(self.work, "config", "user.email", "ratchet-pilot@example.invalid")
        base = self.commit("base")
        self.gate_config(base=base, frozen=None, checks=self.checks)
        if self.args.frozen_from:
            source = Path(self.args.frozen_from).resolve() / "work"
            for name in gate_module.FROZEN_PATHS:
                listed = git(source, "ls-tree", "-r", "--name-only", "HEAD", "--", name).splitlines()
                for relative in listed:
                    target = self.work / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(subprocess.run(["git", "-C", str(source), "show", f"HEAD:{relative}"],
                                                      capture_output=True, check=True).stdout)
            self.gate_config(frozen=self.commit("frozen suite of an earlier run"))

    def changed(self, since):
        names = set(git(self.work, "diff", "--name-only", since, "--").splitlines())
        names |= set(git(self.work, "ls-files", "--others", "--exclude-standard").splitlines())
        return sorted(name for name in names if name)

    def enforce(self, since, allowed, role):
        """Put back every path changed since `since` that the role may not change; the paths put back."""
        back = []
        for name in self.changed(since):
            if any(name == rule or (rule.endswith("/") and name.startswith(rule)) or
                   (rule.endswith("*") and name.startswith(rule[:-1])) for rule in allowed):
                continue
            had = subprocess.run(["git", "-C", str(self.work), "cat-file", "-e", f"{since}:{name}"], capture_output=True, check=False).returncode == 0
            if had:
                git(self.work, "checkout", "-q", since, "--", name)
            else:
                (self.work / name).unlink(missing_ok=True)
            back.append(name)
        if back:
            self.record["reverted"].append({"role": role, "paths": back})
            self.say(f"put back {len(back)} path(s) the {role} stage may not change: {', '.join(back[:6])}")
        return back

    # -- sessions
    def session(self, role, prompt, label):
        number = len(self.record["sessions"]) + 1
        folder = self.out / "sessions" / f"{number:02d}-{label}"
        folder.mkdir(parents=True)
        (folder / "prompt.txt").write_text(prompt)
        self.say(f"session {number}: {label}")
        began = time.time()
        if self.fake:
            self.fake(role, self.work, prompt, number)
            status = {"status": "exited", "returncode": 0}
        else:
            argv, payload = self.host.prepare(prompt=prompt, prompt_file=folder / "host-prompt.txt", cwd=self.work,
                                              model=self.record["model"], effort=self.record["effort"], permission_mode="auto",
                                              max_turns=None, max_budget_usd=self.args.max_budget_usd, plugin_dir=None)
            status = self.hosts.run_agent(argv, self.work, self.env, folder / "events.jsonl", folder / "stderr.txt",
                                          self.args.session_seconds, translate=self.host.translator(), stdin_payload=payload)
        row = {"number": number, "role": role, "label": label, "seconds": round(time.time() - began, 1), **status}
        events = folder / "events.jsonl"
        if events.exists():
            text = events.read_text(errors="replace")
            row["held_out_marks"] = sorted(mark for mark in HELD_OUT_MARKS if mark in text)
            costs = re.findall(r'"total_cost_usd": *([0-9.]+)', text)
            if costs:
                row["cost_usd"] = float(costs[-1])
        self.record["sessions"].append(row)
        self.save()
        self.say(f"  ended {row['status']} after {row['seconds']} s")
        return row

    def loop_block(self, name, work_text, exit_text, plan=False):
        """Write an Until Loop contract and return the packet's loop block. A build or fix loop exits on the gate; a plan
        loop exits when the plan exists and one full pass after the first found nothing to add."""
        contract = self.out / "loops" / f"{name}-contract.json"
        receipt = self.out / "loops" / f"{name}-receipt.json"
        if plan:
            check = {"id": "plan", "clause": "ratchet/plan.md exists and is not empty", "command": "test -s ratchet/plan.md"}
            note = ("The exit check only sees that `ratchet/plan.md` exists. The loop also asks for one full pass, after the "
                    "first, that finds nothing to add: report that pass as trivial only when it changed nothing that matters.")
            scope = f"ratchet/plan.md, and clauses added at the end of ratchet/spec.md, in {self.work}. No product code, no tests."
            authority = "Write ratchet/plan.md; add clauses at the end of ratchet/spec.md. Nothing else. No commits, no pushes."
        else:
            check = {"id": "gate", "clause": "every check the script runs passes",
                     "command": f"python3 {self.tools / 'gate.py'} {self.work}"}
            note = GATE_NOTE.format(gate=self.tools / "gate.py", work=self.work, checks=", ".join(self.checks) or "none")
            scope = f"The product in {self.work}. Never acceptance/, ratchet/spec.md or ratchet/acceptance.json: they are frozen."
            authority = ("Edit product files, their tests and documents in the workspace. No commits, no pushes, nothing "
                         "installed from the network, no process stopped by name.")
        contract.write_text(json.dumps({
            "workspace": str(self.work), "work": work_text, "exit_condition": exit_text,
            "repeat_condition": ("Repeat while a full pass still finds a nuance that would change the build." if plan else
                                 "Repeat while the exit check fails and a change to the product can still make it pass. "
                                 "Stop incomplete when every remaining failure is a test you dispute, or you are blocked."),
            **({"required_trivial_reviews": 1} if plan else {}),
            "context": {
                "request": self.request, "scope": scope, "authority": authority,
                "environment": f"Run commands in {self.work}. Temporary files under {self.tmp}. Servers on a free port only.",
                "resources": [{"purpose": "the specification: use cases and numbered clauses", "locator": str(self.work / "ratchet" / "spec.md")},
                              {"purpose": "the plan for the build pass", "locator": str(self.work / "ratchet" / "plan.md")}]},
            "exit_checks": [check],
        }, indent=1) + "\n")
        return LOOP_BLOCK.format(runtime=self.tools / "until_loop_ephemeral.py", receipt=receipt, contract=contract, check_note=note)

    def loop_status(self, name):
        receipt = self.out / "loops" / f"{name}-receipt.json"
        try:
            return json.loads(receipt.read_text()).get("status")
        except (OSError, ValueError):
            return None

    # -- the gate
    def gate(self, label):
        record = gate_module.gate(self.work)
        number = len(self.record["gates"]) + 1
        (self.out / "gates" / f"{number:02d}-{label}.json").write_text(json.dumps(record, indent=1) + "\n")
        previous = self.record["gates"][-1]["passing"] if self.record["gates"] else []
        passing = sorted(ident for ident, row in record["clauses"].items() if row["pass"])
        row = {"number": number, "label": label, "pass": record["pass"], "failing": record["failing"], "passing": passing,
               "regressions": sorted(set(previous) & set(record["failing"])), "restored": record["restored"],
               "unstable": sorted(ident for ident, r in record["clauses"].items() if r.get("unstable")),
               "clauses": len(record["clauses"]), "at": round(time.time() - self.began, 1)}
        self.record["gates"].append(row)
        self.save()
        self.say(f"gate {number} ({label}): {'PASS' if row['pass'] else 'FAIL'}; {len(passing)} of {row['clauses']} clauses pass"
                 + (f"; failing {', '.join(record['failing'][:8])}" if record["failing"] else "")
                 + (f"; restored {len(record['restored'])} frozen file(s)" if record["restored"] else ""))
        return record

    # -- stages
    def stage_spec(self):
        problems = ""
        for attempt in range(1, 4):
            before = git(self.work, "rev-parse", "HEAD").strip()
            self.session("spec", SPEC_PACKET.format(frame=FRAME, request=self.request, problems=problems, conduct=self.conduct()),
                         f"spec-{attempt}")
            self.enforce(before, ["ratchet/spec.md"], "spec")
            try:
                clauses = read_spec(self.work)
            except ValueError as error:
                problems = f"\n## The script refused your last specification\n- {error}\nWrite it again in the form above.\n"
                self.say(f"  spec refused: {error}")
                continue
            self.commit("spec")
            return clauses
        raise RuntimeError("no usable specification after three sessions")

    def stage_build(self, cycle, new):
        name = f"build-{cycle}"
        if cycle == 1:
            title, what = "one pass over the whole request", "Build all of it in this one pass, not a first slice."
            note = "A separate session writes the acceptance tests from the specification after you; they are not yours to write."
            work_text = "Build the whole request as ratchet/spec.md states it, with its tests, documents and report."
        else:
            listing = "\n".join(f"- {ident}: {row['statement']}" for ident, row in new.items())
            title = "continue: build what does not yet match the longer specification"
            what = ("The specification has grown since the product was built. These items are new:\n" + listing +
                    "\nBased on the specification as it now stands and the code as it is, build whatever does not yet match it. "
                    "A new item the product already keeps to needs no change: say so in the report.")
            note = ("- `acceptance/` holds the acceptance tests another session wrote; read and run them, never edit them: "
                    "the gate puts back any change and counts it.")
            work_text = "Build whatever the product lacks against the specification as it now stands, keeping every passing check passing."
        loop = self.loop_block(name, work_text, "The exit check passes and the report ratchet/" + name + ".md exists.")
        self.session("build", BUILD_PACKET.format(frame=FRAME, title=title, request=self.request, what=what, acceptance_note=note,
                                                  loop=loop, cycle=cycle, conduct=self.conduct()), name)
        self.record["cycles"][-1]["build_loop"] = self.loop_status(name)
        self.gate(f"after-{name}")  # also puts back the frozen paths
        self.commit(name)

    def given_build(self):
        """Cycle 1's build without a session: lay a given product tree over the work folder (--build-from)."""
        shutil.copytree(self.args.build_from, self.work, dirs_exist_ok=True)
        self.say(f"build 1 is the given tree {self.args.build_from}")
        self.gate("after-given-build")
        self.commit("build-1")

    def stage_tests(self, cycle, clauses, new):
        self.gate_config(frozen=None)  # the test owner may change the acceptance tests
        problems = ""
        for attempt in range(1, 4):
            before = git(self.work, "rev-parse", "HEAD").strip()
            if cycle == 1:
                scope, keep = "For every clause (C-n) of `ratchet/spec.md`", ""
            else:
                scope = ("The specification has grown. For each of these new items of `ratchet/spec.md` (" + ", ".join(new) +
                         "), and for any older clause you find weakly tested,")
                keep = "\n   The acceptance tests already here stay: add to them and strengthen them, never weaken or remove one."
            self.session("tests", TESTS_PACKET.format(frame=FRAME, request=self.request, scope=scope, keep=keep, cycle=cycle,
                                                      problems=problems, conduct=self.conduct()), f"tests-{cycle}-{attempt}")
            self.enforce(before, ["acceptance/", "ratchet/acceptance.json", f"ratchet/tests-{cycle}.md"], "tests")
            wrong = self.manifest_problems(clauses)
            if not wrong:
                break
            problems = ("\n## The script refused your last result\n" + "\n".join(f"- {line}" for line in wrong) +
                        "\nCorrect these; keep the rest of your work.\n")
            self.say(f"  tests refused: {'; '.join(wrong)[:300]}")
            self.commit(f"tests-{cycle}-refused-{attempt}")
        else:
            raise RuntimeError("no usable acceptance manifest after three sessions")
        earlier = self.cycle_start_frozen
        frozen = self.commit(f"tests-{cycle}")
        if earlier and cycle > 1:  # how many acceptance files that already existed did the test owner change or remove
            status = git(self.work, "diff", "--name-status", earlier, frozen, "--", "acceptance").splitlines()
            self.record["cycles"][-1]["existing_tests_changed"] = sorted(line.split("\t", 1)[1] for line in status
                                                                         if line[:1] in ("M", "D"))
        self.gate_config(frozen=frozen)

    def manifest_problems(self, clauses):
        path = self.work / "ratchet" / "acceptance.json"
        try:
            manifest = json.loads(path.read_text())
        except (OSError, ValueError) as error:
            return [f"ratchet/acceptance.json cannot be read as JSON: {error}"]
        wrong = [f"clause {ident} has no entry in ratchet/acceptance.json" for ident in clauses if ident not in manifest]
        wrong += [f"entry {ident} names no clause of the specification" for ident in manifest if ident not in clauses]
        wrong += [f"entry {ident} has no command" for ident, entry in manifest.items()
                  if not (isinstance(entry, dict) and isinstance(entry.get("command"), str) and entry["command"].strip())]
        return wrong

    def stage_fix(self, cycle, record):
        """Fix sessions until the gate passes; True when it does. A dispute goes to a referee session once per fix."""
        unchanged = 0
        for attempt in range(1, self.args.max_fixes + 1):
            number = sum(1 for row in self.record["sessions"] if row["role"] == "fix") + 1
            failing = "\n\n".join(self.failure_text(record, name) for name in record["failing"])
            name = f"fix-{number}"
            loop = self.loop_block(name, "Fix the product so that every check the gate runs passes, and write the report.",
                                   f"The exit check passes, or every check still failing is named under Disputed in ratchet/{name}.md.")
            self.session("fix", FIX_PACKET.format(frame=FRAME, request=self.request, failing=failing, loop=loop, number=number,
                                                  conduct=self.conduct()), name)
            before_failing = list(record["failing"])
            record = self.gate(f"after-{name}")
            self.commit(name)
            if record["pass"]:
                return True
            report = self.work / "ratchet" / f"{name}.md"
            disputes = items(section(report.read_text(), "Disputed")) if report.is_file() else []
            if disputes:
                self.record["cycles"][-1].setdefault("disputes", []).extend(disputes)
                before = git(self.work, "rev-parse", "HEAD").strip()
                self.gate_config(frozen=None)
                self.session("referee", REFEREE_PACKET.format(frame=FRAME, disputes="\n".join(f"- {line}" for line in disputes),
                                                              number=number, conduct=self.conduct()), f"referee-{number}")
                self.enforce(before, ["acceptance/", "ratchet/acceptance.json", f"ratchet/referee-{number}.md"], "referee")
                self.gate_config(frozen=self.commit(f"referee-{number}"))
                record = self.gate(f"after-referee-{number}")
                if record["pass"]:
                    return True
            unchanged = unchanged + 1 if record["failing"] == before_failing else 0
            if unchanged >= 2:
                self.say("  the same checks failed after two fix sessions in a row: stopping this run as stuck")
                self.record["stop"] = "stuck"
                return False
        self.record["stop"] = "max-fixes"
        return False

    def failure_text(self, record, name):
        row = (record["clauses"].get(name) or record["checks"].get(name.removeprefix("check: "))
               or record["syntax"].get(name.removeprefix("syntax: ")) or {})
        try:
            clause = read_spec(self.work).get(name)
        except ValueError:
            clause = None
        head = f"### {name}" + (f": {clause['statement']}" if clause else "")
        lines = [head] + ([f"command: {row['command']}"] if row.get("command") else [])
        return "\n".join(lines + ["  | " + line for line in row.get("tail") or []])

    def grown(self, stage, cycle, clauses, old_text):
        """After a stage that may lengthen the specification: put back any change to an existing item, keep the new
        items, and return them ({id: row})."""
        try:
            after = read_spec(self.work)
        except ValueError as error:
            self.record["spec_violations"].append({"stage": stage, "cycle": cycle, "problem": str(error)})
            (self.work / "ratchet" / "spec.md").write_text(old_text)
            return {}
        touched = [ident for ident, row in clauses.items()
                   if ident not in after or after[ident]["statement"] != row["statement"] or after[ident]["observable"] != row["observable"]]
        new = {ident: row for ident, row in after.items() if ident not in clauses}
        if touched:  # keep the old text and add the new items after it
            self.record["spec_violations"].append({"stage": stage, "cycle": cycle, "changed_existing": touched})
            (self.work / "ratchet" / "spec.md").write_text(old_text.rstrip("\n") + "\n\n" + "\n".join(row["block"] for row in new.values()))
            self.say(f"  the {stage} stage changed existing item(s) {', '.join(touched)}: put back, new items kept")
        return new

    def stage_plan(self, cycle, clauses, new):
        """The heavy plan pass, inside an Until Loop that asks for one more full look after the first; the items it added."""
        before = git(self.work, "rev-parse", "HEAD").strip()
        old_text = (self.work / "ratchet" / "spec.md").read_text()
        name = f"plan-{cycle}"
        if cycle == 1:
            title, what, append = "how to build the whole request", "Plan the build of all of it.", ""
            work_text = "Write ratchet/plan.md for the whole request, then read spec, code and plan again for a nuance you missed."
        else:
            listing = "\n".join(f"- {ident}: {row['statement']}" for ident, row in new.items())
            title = "how to build what the longer specification adds"
            what = ("The specification has grown since the product was built. These items are new:\n" + listing +
                    "\nPlan how to build them into the product as it stands.")
            append = f" (keep what is there and add a part headed `# Cycle {cycle}` at its end)"
            work_text = "Extend ratchet/plan.md for the new items, then read spec, code and plan again for a nuance you missed."
        loop = self.loop_block(name, work_text, "ratchet/plan.md covers the build, and a full pass after the first found nothing to add.",
                               plan=True)
        self.gate_config(frozen=None)
        self.session("plan", PLAN_PACKET.format(frame=FRAME, title=title, request=self.request, what=what, append=append, loop=loop,
                                                conduct=self.conduct()), name)
        self.enforce(before, ["ratchet/plan.md", "ratchet/spec.md"], "plan")
        added = self.grown("plan", cycle, clauses, old_text)
        self.record["cycles"][-1].update(plan_loop=self.loop_status(name), plan_added=list(added))
        self.gate_config(frozen=self.commit(name))
        if added:
            self.say(f"  plan {cycle}: {len(added)} item(s) added to the specification: {', '.join(added)}")
        return added

    def stage_delta(self, cycle, clauses):
        before = git(self.work, "rev-parse", "HEAD").strip()
        old_text = (self.work / "ratchet" / "spec.md").read_text()
        self.gate_config(frozen=None)
        self.session("delta", DELTA_PACKET.format(frame=FRAME, request=self.request, cycle=cycle, conduct=self.conduct()),
                     f"delta-{cycle}")
        self.enforce(before, ["ratchet/spec.md", f"ratchet/delta-{cycle}.md"], "delta")
        new = self.grown("delta", cycle, clauses, old_text)
        frozen = self.commit(f"delta-{cycle}")
        self.gate_config(frozen=frozen)
        self.say(f"  delta {cycle}: {len(new)} new item(s)" + (": " + ", ".join(new) if new else ""))
        return new

    # -- the whole run
    def run(self):
        self.setup()
        if self.args.frozen_from:
            clauses = read_spec(self.work)
        else:
            clauses = self.stage_spec()
        self.gate_config(frozen=git(self.work, "rev-parse", "HEAD").strip())
        new = {}
        cycle = 0
        while True:
            cycle += 1
            entry = {"cycle": cycle, "clauses_at_start": len(clauses), "new_clauses": list(new)}
            self.record["cycles"].append(entry)
            repair_start = cycle == 1 and bool(self.args.frozen_from)
            self.cycle_start_frozen = git(self.work, "rev-parse", "HEAD").strip()
            if not repair_start:
                added = self.stage_plan(cycle, clauses, new)
                if added:
                    clauses, new = read_spec(self.work), {**new, **added}
                if cycle == 1 and self.args.build_from:
                    self.given_build()
                else:
                    self.stage_build(cycle, new)
                self.stage_tests(cycle, clauses, new)
            record = self.gate(f"cycle-{cycle}-first")
            entry["first_gate_failing"] = record["failing"]
            if self.args.stop_after == "tests":
                self.record["stop"] = "stop-after-tests"
                break
            if not record["pass"] and not self.stage_fix(cycle, record):
                break
            self.commit(f"green-{cycle}")
            new = self.stage_delta(cycle, clauses)
            entry["delta_clauses"] = {ident: row["statement"] for ident, row in new.items()}
            if not new:
                self.record["stop"] = "converged"
                break
            clauses = read_spec(self.work)
            if cycle >= self.args.max_cycles:
                self.record["stop"] = "max-cycles"
                break
        final = self.gate("final")
        self.commit("final")
        tamper = self.work / ".git" / "ratchet-tamper.log"
        ids = list(read_spec(self.work))
        self.record.update(final_pass=final["pass"], seconds=round(time.time() - self.began, 1),
                           clauses=sum(1 for ident in ids if ident.startswith("C-")),
                           use_cases=sum(1 for ident in ids if ident.startswith("U-")),
                           tamper=tamper.read_text().splitlines() if tamper.exists() else [],
                           finished=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        self.save()
        self.say(f"run ended: {self.record.get('stop')}; final gate {'PASS' if final['pass'] else 'FAIL'}; "
                 f"{self.record['clauses']} clauses, {self.record['use_cases']} use cases; {len(self.record['sessions'])} sessions; {self.record['seconds']} s")
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="verb", required=True)
    run = sub.add_parser("run", help="run one case through the loop")
    run.add_argument("--case", required=True)
    run.add_argument("--host", required=True, choices=("codex", "claude", "grok", "fake"))
    run.add_argument("--model")
    run.add_argument("--effort")
    run.add_argument("--output", required=True)
    run.add_argument("--fake", help="with --host fake: a Python file whose act(role, work, prompt, number) plays the model")
    run.add_argument("--start-tree", help="start from this product tree instead of the case's fixture (a repair start)")
    run.add_argument("--frozen-from", help="a finished run whose spec and acceptance tests this run starts with, frozen")
    run.add_argument("--build-from", help="cycle 1's build is this product tree, laid over the work folder by the script: no build session")
    run.add_argument("--stop-after", choices=("tests",), help="end the run once cycle 1's acceptance tests are frozen and gated")
    run.add_argument("--max-cycles", type=int, default=3, help="apparatus limit: cycles before the run is stopped (reported)")
    run.add_argument("--max-fixes", type=int, default=4, help="apparatus limit: fix sessions per cycle (reported)")
    run.add_argument("--max-budget-usd", type=float, default=None, help="per session, on hosts that price a session")
    run.add_argument("--session-seconds", type=int, default=SESSION_SECONDS)
    run.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    if bool(args.start_tree) != bool(args.frozen_from):
        raise SystemExit("--start-tree and --frozen-from go together: a repair start needs both")
    return Run(args, load_case(args.case)).run()


if __name__ == "__main__":
    sys.exit(main())
