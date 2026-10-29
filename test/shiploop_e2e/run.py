#!/usr/bin/env python3
"""Run ShipLoop end to end from one prompt in a new, empty directory.

Each run creates a fresh empty working directory, invokes the ShipLoop skill
there with one headless host process, shows its progress live, and grades:

  invoked   the host registered the invoked skill command, so the prompt went
            to the skill (Claude: /skill-craft:shiploop; Grok: /shiploop, since
            Grok does not namespace plugin skills)
  plugin    exactly one skill-craft plugin loaded, and it is the build under test
            (a resumed or regraded Grok or Codex run keeps its first launch's
            verdict, which invocation.json records; Claude shows it in its events)
  process   the host exited 0 within the timeout
  shiploop  a ShipLoop state.md under the output directory reports status
            "done" and its report.html exists
  committed the source checkout ends committed: HEAD moved past where the run
            started, holds at least one file (ShipLoop's own empty baseline
            commit is not product) and no product path is left uncommitted
            (logs aside)
  checks    every case check command exits 0 in the working directory

--seed-at step-plan starts an Ask-Agent run whose stages before step-plan are
recorded without doing them (the case prompt is the specification), so a host
reaches the implementation chain in minutes instead of hours of planning. The
host then follows ShipLoop's own packets from step-plan. A seeded run is also
graded on `chain` (every step accepted and at least two workers in flight
together) and writes no baseline row, since it does not start from intake.
--seed-at release-plan (or system-test-author) starts a RELEASE SLICE: the build is recorded without doing it and the case's prebuilt
product is committed in the run's worktree, so the host plans, checks, performs and verifies the release in minutes
(test/shiploop_e2e/release_slice.py, README "The release slice"). It is graded on `release_slice` instead of `chain`: which stages
ShipLoop accepted from the seed point on, where it stopped, and whether the case's platform change (the deploy) happened in its own
stage. --platform-existing update lets such a run deploy over work an earlier run kept: the items already in the platform are the
baseline and the cleanup removes only what the run adds beyond it. The seed also records the item's base snapshot
and commits a neutral knowledge home (spec R-1 = the request, environment ## Commands = the case's checks), so the gates that
read them run; --seed-without-home leaves the home out (run.seed_run, test/shiploop_e2e/README.md "The seed").

A follow-on case (`follows` in cases.json) runs a second feature in a copy of an
earlier run's source checkout (--continue-from <earlier output>), to see whether
ShipLoop builds on what the first run decided. Its checks are the followed
case's checks (regression), its own feature checks and retention checks, which
get $PRIOR_WORK (the earlier checkout, read only).

Besides the verdicts, metrics.json records where ShipLoop spent turns, tokens,
cost and time (per accepted stage), its failed commands, host truncations,
compactions and the knowledge-home facts (see metrics.py), and a record-only `fidelity`
block (see fidelity.py: what the run's own records show about how ShipLoop was carried; in
metrics.json only, at most five printed lines, never a verdict). The run's Run Review
documents go to <output>/review-export/ (skills/shiploop-run-review/);
an export problem is printed and never changes a verdict.

The default host is Claude (Sonnet 5.5, claude-sonnet-5-5). By default the run tests
what the whichguy marketplace publishes now (--source marketplace, gated on
local HEAD == origin/main and matching versions); --source checkout builds
this checkout instead. The host is isolated from the user's configuration:

  grok    a throwaway HOME whose .grok holds only a symlink to the user's
          auth.json and the plugin under test, so neither the user's Grok
          plugins nor anything Grok inherits from ~/.claude load, and nothing
          is installed into the real profile
  claude  --setting-sources project,local plus --plugin-dir, so the user's
          plugins and hooks stay out, and --strict-mcp-config, so none of the
          account's claude.ai connectors load (~/.claude/CLAUDE.md still loads)

A Grok session that ends while the ShipLoop run is still active is resumed
(bounded by --max-resumes). Every attempt keeps its prompt, argv, event
stream, arrival timeline, stderr, metrics.json and result.json in a new
output directory outside the checkout.

--resume-run on a run whose ShipLoop is already done or blocked (a regrade) starts no
host. It restates the run's own last record (result.json, else invocation.json): host,
model, effort, plugin verdict and the process block, whatever --host, --model or
--effort say, and grades ShipLoop, the checkout and the checks again. A host that
failed stays failed; a run with no record of its exit says "not observed" and leaves
the process verdict out of the result. A blocked run waits for a person (SPEC S-14), so
it is never resumed as if answered: it is only graded again, which refreshes its
metrics.json and result.json. An active run is a real resume, on the host, model and effort its last launch recorded (no --host
means that host, not Claude); another --host is refused unless --allow-host-change says the change is deliberate, which makes a mixed-host
run. --grade-only does the
same regrade for a run in any status that has a ShipLoop state, for a run whose harness
was killed with its host and so never wrote its records. Creating <output>/stop ends a
running host on purpose: it is not relaunched, the records are written, and the exit
code is non-zero. A SIGTERM or SIGHUP to the harness (not a SIGHUP the launch ignored, as under nohup) ends every live host at
once and is recorded the same way, as `terminated by SIGTERM`; a Ctrl-C does so for a suite. After each host session and after the
case checks the harness stops the TCP listeners left under the case's output folder and records them as `left_behind` in
result.json. A launch is refused while an ended case's listener is still bound, and so is a --resume-run of a case whose harness
is running (README, "Launching long runs"). What a run owns is in <output>/resources.jsonl: before a host starts it leases its
platform and its declared fixed ports (a held one refuses it), an orphan of a killed harness or a low disk refuses it, and a
--resume-run first stops what the killed harness left, by recorded identity (lifecycle.py; SPEC "The resource lifecycle").
After the verdicts are written, a delivery that is finished and returned (and only then) is measured on a copy under
<output>/quality and recorded as `quality` in result.json, beside the verdicts and never as one: a mutation ratio of the
delivered tests, the held-out acceptance a case declares, the Claude memory writes the events show (quality.py, README
"Delivered quality"). --planning-review stage|none gives a run its ShipLoop mode as an option of the harness.
This launches a real model and costs money; it is never part of default CI.
`--baseline-report [--baseline FILE] [--runs DIR ...] [--json]` is the one read-only exception: it starts no host and
probes no CLI, unions the baseline file with the run folders and prints, per cell, the attempts, builds and the n, min,
median and max of cost, turns, minutes and planning minutes (README, "The baseline report").

  python3 test/shiploop_e2e/run.py --case battleship
  python3 test/shiploop_e2e/run.py --case battleship-scoring --continue-from <battleship output>
  python3 test/shiploop_e2e/run.py --case hello --host claude
  python3 test/shiploop_e2e/run.py --case temperature-report --host codex --effort xhigh --seed-at step-plan
  python3 test/shiploop_e2e/run.py --case battleship-salesforce --seed-at release-plan --host grok --keep-platform --output <folder>
  python3 test/shiploop_e2e/run.py --prompt "..." --check "python3 -m unittest"
"""

from __future__ import annotations

import argparse
import atexit
from collections import Counter
import contextlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import functools
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time

# datetime.strptime imports _strptime on its first call. Load it now: run 5a (2026-10-24) crashed at its end when
# Homebrew swapped the interpreter under the running process and that module was no longer on disk.
import _strptime  # noqa: E402,F401

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
sys.path.insert(0, str(HERE))
import boundary  # noqa: E402
import brownfield  # noqa: E402
import counters  # noqa: E402
import delivery  # noqa: E402
import environment  # noqa: E402
import fidelity  # noqa: E402
import flow  # noqa: E402
import hosts  # noqa: E402
import lifecycle  # noqa: E402
import listeners  # noqa: E402
import metrics  # noqa: E402
import owner_note  # noqa: E402
import quality  # noqa: E402
import release_slice  # noqa: E402
import run_choice
import run_trace  # noqa: E402
import runrecord  # noqa: E402
import sessionlog  # noqa: E402
import shiploop_knowledge_home as knowledge_home  # noqa: E402
import shiploop_chain_ledger as chain_ledger  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402
from run_choice import RUN_IDENTITY, run_identity, shiploop_runs, state_digest

CASES = HERE / "cases.json"
SUITES = HERE / "suites.json"
BASELINES = HERE / "baselines.jsonl"
REVIEW_EXPORTER = ROOT / "skills" / "shiploop-run-review" / "scripts" / "export.py"
PLUGIN_NAME = "skill-craft"
# How often a running host is checked for its deadline, a requested stop and an interrupt.
POLL_SECONDS = 2
EXIT_POLL_SECONDS = 0.1  # how soon the end of a host session is seen (its leader is polled, not reaped, until its group is ended)
# What a host gets to run its SessionEnd hooks after it is signalled (end_host): the keepalive registers its session-end hook
# with a 10 s timeout, so a host that is still there after this long has not run it in time and is ended with the group.
SESSION_END_SECONDS = 15
# With no resume limit by default, a host that cannot run (its auth expired, its binary broke) or a model that ends every
# turn without moving the run would be resumed forever. Evidence, not a count of work: this many resumed sessions in a row
# that left ShipLoop's revision where it was end the loop (the owner's rule for autonomous runs: stop on three
# no-progress iterations).
RESUME_STALL = 3
# Hosts this process has started and not yet reaped, by the pid of the leader of the group it leads. A host starts in a
# session of its own (start_new_session=True), so a SIGTERM to the harness does not reach it: on 2026-10-08 the Grok host of a
# round-2 run went on working for about 28 minutes after the harness died of one, with nothing collecting its events.
LIVE_HOST_GROUPS: set[int] = set()
HOST_THREAD: dict[int, int] = {}  # the same leaders, by the ident of the thread that launched them (see end_live_hosts)
# Set when the harness was told to end (SIGTERM, SIGHUP): every launch and every resume treats it as a requested stop.
TERMINATION = threading.Event()
TERMINATED_BY: list[str] = []  # the name of the first signal, for the record
HANDLED_SIGNALS: list[int] = []  # the signals install_termination_handlers took over


def end_live_hosts(thread: int | None = None, wait: float = 0.0) -> None:
    """Kill every host session that is running, and the browser of a capability probe that is running (the probe registers its
    group in environment.LIVE_PROBE_GROUPS). Also runs at exit, so a Ctrl-C or a crash leaves no orphan host or browser. Each
    group is ended by listeners.end_group, which signals nothing whose leader was already reaped (its number may be reused).

    ``thread`` limits it to the hosts that thread launched (and leaves the probes): a platform cleanup, in a suite that runs
    cases side by side, ends its own case's host and never a sibling's. ``wait`` seconds at most for each of those leaders to
    be gone (exited or reaped) before returning, which is what a caller that acts on the platform next needs."""
    leaders = [pid for pid in tuple(LIVE_HOST_GROUPS)  # a copy: suite worker threads add and discard concurrently
               if thread is None or HOST_THREAD.get(pid) == thread]
    for pid in leaders:
        listeners.end_group(pid)
    if thread is None:
        environment.end_live_probes()
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline and any(listeners.unreaped(pid) == "running" for pid in leaders):
        time.sleep(0.05)


atexit.register(end_live_hosts)


def terminate(name: str) -> None:
    """The harness was told to end by `name`: end every host at once and let main write the records as a requested stop."""
    TERMINATED_BY.append(name)
    TERMINATION.set()  # before the kill, so a launch that finds its host dead already knows why
    end_live_hosts()
    for number in HANDLED_SIGNALS:
        signal.signal(number, signal.SIG_DFL)  # a second signal means it: the default action ends the harness now


def on_termination(signum, frame) -> None:
    """A SIGTERM or SIGHUP reached the harness."""
    terminate(signal.Signals(signum).name)


def install_termination_handlers() -> list[int]:
    """Take over SIGTERM and SIGHUP, except one the launch ignored: `nohup` keeps a run alive through a hangup by ignoring it."""
    for number in (signal.SIGTERM, signal.SIGHUP):
        if signal.getsignal(number) is not signal.SIG_IGN:
            signal.signal(number, on_termination)
            HANDLED_SIGNALS.append(number)
    return list(HANDLED_SIGNALS)


def stop_cause(stop_file: Path) -> str:
    """Why a run ended on purpose: a signal that told the harness to end, or a stop file."""
    if TERMINATION.is_set():
        return f"terminated by {TERMINATED_BY[0] if TERMINATED_BY else 'a signal'}"
    return f"stopped by {stop_file}"


# Grok does not namespace plugin skills; Claude prefixes them with the plugin name.
def the_host(args) -> "hosts.Host":
    """The selected host, with the binary its --<host>-bin flag names and the backend --backend names (Claude only); with no
    --backend, the run default (hosts.RUN_DEFAULT_BACKEND: the Claude host on Ollama)."""
    backend = getattr(args, "backend", None) or hosts.RUN_DEFAULT_BACKEND.get(args.host)
    return hosts.host(args.host, getattr(args, args.host + "_bin"), backend)


def load_case(args) -> tuple[str, str, list[str], str | None]:
    """Name, prompt, checks and the case it follows (None for a fresh start)."""
    if args.prompt:
        return "custom", args.prompt, args.check or [], None
    cases = catalog()
    if args.case not in cases:
        raise SystemExit(f"unknown case {args.case!r}; known: {', '.join(sorted(cases))}")
    case = cases[args.case]
    follows = case.get("follows")
    regression = cases[follows]["checks"] if follows else []
    return args.case, case["prompt"], regression + case["checks"] + case.get("retention", []) + (args.check or []), follows


def case_quality(name: str) -> dict:
    """The quality measures a case declares: its own entry, else the one of the case it follows (a follow-on is measured by its
    followed case's declaration unless it names its own). ``{}`` for a case that declares none, and for a name that is not a
    case. Kept apart from load_case, whose four values callers unpack."""
    cases = catalog()
    case = cases.get(name) or {}
    own, earlier = case.get("quality") or {}, (cases.get(case.get("follows")) or {}).get("quality") or {}
    found = {key: own.get(key) or earlier.get(key) for key in ("mutation", "acceptance", "refuse_ports")}
    return {key: value for key, value in found.items() if value}


# The platform prefix this run uses in place of its case's (--platform-prefix): (case name, prefix), or None. _main sets it once for
# the run it starts or resumes and main clears it, so every reader of the case (catalog) sees the same renamed text.
RUN_PREFIX: tuple[str, str] | None = None
PLATFORM_PREFIX_SHAPE = re.compile(r"[A-Z][A-Za-z0-9]{3,19}")


def catalog() -> dict:
    """cases.json as this run reads it: with --platform-prefix, the run's case renamed (with_prefix)."""
    cases = json.loads(CASES.read_text())
    if RUN_PREFIX and RUN_PREFIX[0] in cases:
        cases[RUN_PREFIX[0]] = with_prefix(cases[RUN_PREFIX[0]], RUN_PREFIX[1])
    return cases


@functools.cache
def salesforce_library():
    """checks/chess_salesforce.py, the Salesforce library both platform cases share, loaded by path (it is an oracle, not a module
    of this folder)."""
    spec = importlib.util.spec_from_file_location("shiploop_e2e_chess_salesforce", HERE / "checks" / "chess_salesforce.py")
    library = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(library)
    return library


def prefix_spellings(kind: str, prefix: str) -> tuple[str, ...]:
    """Every spelling a platform kind gives a prefix in a case's text. Salesforce names Apex classes, tabs, apps and permission
    sets with it as it is (SLBattle) and a component with its leading capitals lowered (slBattle: lwc_prefix)."""
    if kind == "salesforce":
        return prefix, salesforce_library().lwc_prefix(prefix)
    raise SystemExit(f"--platform-prefix: a {kind!r} platform does not say how its items spell a prefix")


def with_prefix(case: dict, prefix: str) -> dict:
    """The case with its platform prefix renamed everywhere its text names it (the prompt, the checks, every platform command and
    the guard): each spelling of the catalog's prefix becomes the same spelling of `prefix` (SPEC: a hosted-platform run's prefix)."""
    platform = case["platform"]
    text = json.dumps(case)
    for old, new in zip(prefix_spellings(platform["kind"], platform["prefix"]), prefix_spellings(platform["kind"], prefix)):
        text = text.replace(old, new)
    return json.loads(text)


def run_prefix(asked: str | None, name: str, cases: dict, *, resuming: bool = False, earlier: str | None = None) -> str | None:
    """The prefix a run uses in place of its case's, or None for the case's own; `cases` is the catalog as written.

    A resume keeps the prefix its run started with (invocation.json). A new prefix must be a capital letter and 3 to 19 letters or
    digits, for a case whose platform has a prefix, and must share no beginning with any case's prefix, ignoring case: the preflight,
    the guard and the cleanup match items by a case-insensitive beginning, so either run would take the other's items for its own."""
    if resuming:
        if asked and asked != earlier:
            raise SystemExit(f"--platform-prefix {asked}: this run started with "
                             + (f"prefix {earlier}" if earlier else "its case's own prefix") + ", and a resume keeps its run's prefix")
        return earlier
    if not asked:
        return None
    if not ((cases.get(name) or {}).get("platform") or {}).get("prefix"):
        raise SystemExit(f"--platform-prefix: case {name!r} has no platform prefix to rename")
    if not PLATFORM_PREFIX_SHAPE.fullmatch(asked):
        raise SystemExit(f"--platform-prefix {asked}: a prefix is a capital letter and 3 to 19 letters or digits (it begins class "
                         "and component names)")
    for other, spec in sorted(cases.items()):
        theirs = str(((spec.get("platform") or {}).get("prefix") if isinstance(spec, dict) else None) or "")
        if theirs and (asked.lower().startswith(theirs.lower()) or theirs.lower().startswith(asked.lower())):
            raise SystemExit(f"--platform-prefix {asked}: it shares a beginning with case {other!r}'s prefix {theirs}, so that "
                             "case's preflight, guard and cleanup would take this run's items for its own, or the reverse")
    return asked


def quality_stop(stop_file: Path) -> str | None:
    """Why the quality phase should end now: the harness was told to end, or a person created the stop file. None otherwise."""
    return stop_cause(stop_file) if TERMINATION.is_set() or stop_file.exists() else None


def quality_gate(*, shiploop: dict, committed: dict, engine: dict, process: dict, stop_seen: bool, stop_file: Path,
                 lock_held: bool) -> str | None:
    """Why this run's delivery is not measured (None: it is a finished, returned one). The order is the order of what a
    reader would fix first. The phase runs under the case lock this harness already holds and never takes another."""
    if TERMINATION.is_set() or stop_seen or process.get("status") == "stopped" or stop_file.exists():
        return f"a stop was requested ({stop_cause(stop_file)}), so the delivery is not a finished one"
    if engine.get("status") == "active":
        return f"ShipLoop is still active (stage {engine.get('stage')}), so no delivery was returned"
    if not shiploop.get("pass"):
        return f"ShipLoop did not reach done ({shiploop.get('status') or shiploop.get('reason')}), so no delivery was returned"
    if not committed.get("pass"):
        return "the returned checkout is not committed (the committed verdict failed), so it is not a finished delivery"
    if not lock_held:
        return ("this harness does not hold the case lock (another harness holds it, or it could not be made): a second "
                "phase over the same folder could clash with that harness's")
    return None


def quality_record(out: Path, work: Path, name: str, gate: str | None, stop_file: Path) -> dict:
    """The run's ``quality`` block. Recording fails open: an error is recorded as the reason and never changes a verdict."""
    spec: dict = {}
    try:
        spec = case_quality(name) if name != "custom" else {}
        return quality.measure(out, work, spec, gate=gate, groups=lifecycle.Recorded(LIVE_HOST_GROUPS, out, "quality"),
                               stop=lambda: quality_stop(stop_file))
    except Exception as exc:
        return quality.failed_block(out, spec, exc)


def improve_card(plugin_dir: Path) -> Path:
    """The Improve card of a plugin build: the file `--improve-skill` names under `--planning-review none`."""
    return Path(plugin_dir) / "skills" / "improve" / "SKILL.md"


def require_improve_card(planning_review: str | None, plugin_dir: Path) -> None:
    """`none` needs the plugin's Improve card (SPEC S-10 carve-out of 2026-10-05): refuse as soon as the plugin directory is known,
    before any host CLI runs, so a refusal leaves no profile, plugin install or host session behind."""
    if planning_review == "none" and not improve_card(plugin_dir).is_file():
        raise SystemExit(f"--planning-review none needs the plugin's Improve card (--improve-skill), and {improve_card(plugin_dir)} is "
                         "not a file: nothing was started")


def planning_review_sentence(improve_skill: str) -> str:
    """The sentence that makes the model start ShipLoop with `--planning-review none`, which needs the Improve card named
    (`--improve-skill`). `stage` is the engine's default and appends nothing: the run's prompt stays the case's own."""
    return f"Start ShipLoop with the run option --planning-review none and --improve-skill {improve_skill}."


def case_prompt(prompt: str, improve_skill: str | None) -> str:
    """The case's own prompt: ``prompt`` without the sentence ``--planning-review none`` appended to it (planning_review_sentence of
    the run's recorded ``improve_skill``). What prompt_sha256 hashes: the mode is a key of its own, and the sentence names an
    absolute path, so two `none` runs of one case would otherwise hash apart by where their plugin build sits."""
    text = prompt.strip()
    tail = " " + planning_review_sentence(improve_skill) if improve_skill else None
    return text[:-len(tail)] if tail and text.endswith(tail) else text


def planning_review_choice(requested: str | None, earlier: dict | None) -> str | None:
    """The mode this invocation records. A new run records what was asked (None when nothing was). A resume continues a run
    whose mode is fixed at its start, so it names that value or none, and an unrecorded run cannot be given one now."""
    if earlier is None:
        return requested
    recorded = earlier.get("planning_review")
    if requested is not None and requested != recorded:
        raise SystemExit(f"--planning-review {requested} on a resume: the run's own mode is {recorded or 'not recorded'} and "
                         "is fixed when the run starts (state.md); name that value or leave the option out")
    return recorded


def continue_from(prior: Path, work: Path) -> dict:
    """Copy an earlier run's source checkout into `work`, as that run left it.

    The copy keeps .git and every untracked file; worktree records point at the
    earlier run's execution worktree, so they are dropped (the branches stay).
    """
    source = prior / "work"
    if not (source / ".git").exists():
        raise SystemExit(f"--continue-from has no work/.git: {prior}")
    work.rmdir()
    shutil.copytree(source, work, symlinks=True)
    shutil.rmtree(work / ".git" / "worktrees", ignore_errors=True)
    subprocess.run(["git", "-C", str(work), "worktree", "prune"], check=False, capture_output=True)
    earlier = json.loads((prior / "result.json").read_text()) if (prior / "result.json").is_file() else {}
    head = subprocess.run(["git", "-C", str(work), "rev-parse", "HEAD"], capture_output=True, text=True)
    return {"prior": str(prior), "start_head": head.stdout.strip() if head.returncode == 0 else None, "prior_case": earlier.get("case"), "prior_pass": earlier.get("pass"),
            "prior_turns": (earlier.get("metrics") or earlier.get("cli") or {}).get("turns")
            or (earlier.get("cli") or {}).get("num_turns"),
            "prior_cost_usd": (earlier.get("metrics") or earlier.get("cli") or {}).get("cost_usd"),
            "prior_lower_bound": metrics.lower_bound(earlier.get("metrics") or {})}


def new_output_dir(requested: Path | None, name: str) -> Path:
    if requested is None:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        requested = Path(tempfile.gettempdir()) / "shiploop-e2e" / f"{name}-{stamp}-{secrets.token_hex(3)}"
    out = requested.expanduser().resolve()
    if out == ROOT or ROOT in out.parents:
        raise SystemExit(f"output must be outside the checkout: {out}")
    out.mkdir(parents=True, exist_ok=False)
    return out


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout


def card_version(card: Path) -> str | None:
    """The top-level `version:` of a SKILL.md front matter."""
    match = re.match(r"---\n(?:(?!---\n).*\n)*?version:[ \t]*(\S+)", card.read_text()) if card.is_file() else None
    return match.group(1) if match else None


def published_versions() -> dict:
    """The skill-craft and ShipLoop versions origin/main's catalog publishes, read from the local ref (nothing is fetched)."""
    catalog = json.loads(git("show", "origin/main:.claude-plugin/marketplace.json"))
    plugin = next(p for p in catalog["plugins"] if p["name"] == PLUGIN_NAME)
    shiploop = re.search(r"^version:[ \t]*(\S+)", git("show", f"origin/main:plugins/{PLUGIN_NAME}/skills/shiploop/SKILL.md"), re.M)
    return {"catalog_version": plugin.get("version"), "shiploop_version": shiploop.group(1) if shiploop else None}


def released_versions() -> dict:
    """What the marketplace serves now: the catalog and ShipLoop versions on origin/main."""
    git("fetch", "-q", "origin")
    published = published_versions()
    # A pending change note on main is source the marketplace does not serve yet: release.py has not run.
    pending = [name for name in git("ls-tree", "-r", "--name-only", "origin/main", "changes/").split()
               if name.endswith(".md") and name != "changes/README.md"]
    origin_main = git("rev-parse", "origin/main").strip()
    local = git("rev-parse", "HEAD").strip()
    # Behind origin/main is fine (the plugin comes from the marketplace); unpublished local commits are not.
    behind = subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", local, origin_main]).returncode == 0
    return {"origin_main": origin_main, "local_head": local, "local_behind_main": behind, **published,
            "unreleased": pending, "ci": main_ci(origin_main)}


def isolate_git_discovery(environ, out: Path) -> dict:
    """``environ`` with the run's output folder added to GIT_CEILING_DIRECTORIES, so Git started in a case's work folder
    never finds a repository above the run.

    A case starts in a fresh folder that is not a repository; without the ceiling Git walks up and adopts the first
    repository it meets (2026-10-10: a home folder that is itself a repository made the hello case's ShipLoop start there,
    and the sandbox refused). Existing ceilings are kept.
    """
    given = [part for part in str(environ.get("GIT_CEILING_DIRECTORIES", "")).split(os.pathsep) if part]
    ceilings = list(dict.fromkeys([str(Path(out).resolve()), str(Path(out).absolute()), *given]))
    return {**environ, "GIT_CEILING_DIRECTORIES": os.pathsep.join(ceilings)}


def main_ci(commit: str) -> str:
    """origin/main's CI result: success, failure, pending, or unknown (no gh, or no run found).

    The full hermetic tier runs in CI on release commits, not locally; the E2E runs wait for it.
    """
    try:
        done = subprocess.run(["gh", "run", "list", "--repo", "whichguy/skill-craft", "--commit", commit,
                               "--json", "status,conclusion"], capture_output=True, text=True, timeout=60)
        runs = json.loads(done.stdout) if done.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        runs = None
    if not runs:
        return "unknown"
    if any(run.get("conclusion") == "failure" for run in runs):
        return "failure"
    if any(run.get("status") != "completed" for run in runs):
        return "pending"
    return "success" if all(run.get("conclusion") == "success" for run in runs) else "failure"


def version_gate(released: dict, plugin_version: str | None, shiploop_version: str | None) -> list[str]:
    """Why a marketplace run would not test what main and the marketplace publish, if at all."""
    problems = []
    # Optimistic: a run starts while CI is still pending and is cancelled if CI then fails (SPEC).
    if released.get("ci") == "failure":
        problems.append("origin/main's CI failed: fix it (or revert) before spending a live run")
    if released.get("unreleased"):
        problems.append("origin/main has unreleased changes (" + ", ".join(released["unreleased"][:5])
                        + "): run scripts/release.py and push so the marketplace serves them")
    if released["local_head"] != released["origin_main"] and not released.get("local_behind_main"):
        problems.append(f"local HEAD {released['local_head'][:8]} has commits origin/main "
                        f"{released['origin_main'][:8]} does not: publish them first")
    if plugin_version != released["catalog_version"]:
        problems.append(f"installed skill-craft {plugin_version} is not the catalog's {released['catalog_version']}")
    if shiploop_version != released["shiploop_version"]:
        problems.append(f"installed ShipLoop {shiploop_version} is not the released {released['shiploop_version']}")
    return problems


def export_released(out: Path) -> Path:
    """origin/main's plugins/skill-craft, byte for byte: the payload the marketplace serves."""
    target = out / "marketplace"
    target.mkdir()
    archive = subprocess.run(["git", "-C", str(ROOT), "archive", "origin/main", f"plugins/{PLUGIN_NAME}"],
                             check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", str(target)], input=archive, check=True)
    return target / "plugins" / PLUGIN_NAME


def build_candidate(out: Path) -> Path:
    """A fresh package build of this checkout, working-tree changes included."""
    subprocess.run([sys.executable, "-B", str(ROOT / "scripts/build-packages.py"), str(out / "build")],
                   check=True, stdout=subprocess.DEVNULL)
    return out / "build" / "plugins" / PLUGIN_NAME


def tree_digest_checked(root: Path) -> tuple[str | None, str | None]:
    """(a digest of the plugin tree a host loads, None) or (None, why it could not be made). 12 hex.

    Each file's relative path and the sha256 of its bytes. A version string does not identify a build (two Battleship
    Sonnet runs said plugin 1.22.0 with different scripts) and a git head over-splits (two heads built byte-identical
    trees), so the bytes are what is compared. Left out: ``__pycache__`` folders and ``*.pyc`` (a host compiles them when
    it runs the scripts, so they differ between a plugin before and after a run), symlinks (their target is not part of
    the plugin) and anything that is not a regular file. A file or folder that cannot be read gives no digest at all, with
    the reason: a digest of the files that could be read would be another build's digest for the same bytes.
    """
    root = Path(root)
    if not root.is_dir():
        return None, "the plugin folder does not exist"
    problems: list[str] = []
    found: list[Path] = []

    def unreadable(error: OSError) -> None:
        problems.append(f"{error.filename}: {error.strerror}")

    for here, folders, names in os.walk(root, onerror=unreadable):
        folders[:] = [f for f in folders if f != "__pycache__" and not (Path(here) / f).is_symlink()]
        for name in names:
            path = Path(here) / name
            if path.suffix != ".pyc" and not path.is_symlink() and path.is_file():
                found.append(path.relative_to(root))
    digest = hashlib.sha256()
    for relative in sorted(found):
        try:
            data = (root / relative).read_bytes()
        except OSError as error:
            problems.append(f"{root / relative}: {error.strerror}")
            continue
        digest.update(relative.as_posix().encode() + b"\0" + hashlib.sha256(data).hexdigest().encode() + b"\n")
    if problems:
        return None, f"unreadable: {problems[0]}" + (f" (and {len(problems) - 1} more)" if len(problems) > 1 else "")
    return digest.hexdigest()[:12], None


def tree_digest(root: Path) -> str | None:
    """The digest of ``tree_digest_checked``, None when it could not be made."""
    return tree_digest_checked(root)[0]


def output_forms(out: Path, requested: Path | None = None) -> list[str]:
    """Every spelling of a run's output folder a prompt may carry, longest first: the resolved path, the path as it was
    asked for (``--output /tmp/x`` resolves to ``/private/tmp/x`` on macOS), the same without ``/private``, and the
    home-relative ``~/...`` form."""
    forms = {str(out)}
    if requested is not None:
        forms |= {str(requested), os.path.abspath(os.path.expanduser(str(requested)))}
    home = str(Path.home())
    for form in list(forms):
        if form.startswith("/private/"):
            forms.add(form[len("/private"):])
    for form in list(forms):
        if form.startswith(home + "/"):
            forms.add("~" + form[len(home):])
    return sorted((f for f in forms if f), key=len, reverse=True)


def masked_prompt_digest(prompt: str, out: Path, requested: Path | None = None) -> str:
    """The sha256 (12 hex) of a run's prompt with its own output folder replaced by ``<output>``, in every spelling.

    A case that names no path hashes to the plain hash of its text. The Grok ``none`` runs' prompt tells the host to read
    ``<run folder>/build/.../improve/SKILL.md``, so five runs of one prompt had five raw hashes and one masked hash. A
    spelling only counts as the folder when it is not part of a longer name (``/a/run1`` inside ``/a/run10`` or
    ``/other/a/run1``, ``/a/run1.bak``); a sentence-ending full stop does not hide it.
    """
    for form in output_forms(out, requested):
        prompt = re.sub(r"(?<![\w.~/-])" + re.escape(form) + r"(?!\w|-|\.\w)", "<output>", prompt)
    return hashlib.sha256(prompt.strip().encode()).hexdigest()[:12]


def installed_versions(plugin_dir: Path) -> dict:
    """The skill-craft and ShipLoop versions of the plugin a host will actually load, and the digest of its tree."""
    manifest = plugin_dir / ".claude-plugin" / "plugin.json"
    digest, why = tree_digest_checked(plugin_dir)
    return {"plugin_version": json.loads(manifest.read_text()).get("version") if manifest.is_file() else None,
            "shiploop_version": card_version(plugin_dir / "skills" / "shiploop" / "SKILL.md"),
            "plugin_sha256": digest, **({"plugin_sha256_unmeasured": why} if why else {})}


def marketplace_preflight(args, out: Path, env: dict) -> tuple[Path, dict | None, dict]:
    """Pull from the marketplace the way the host does, then report and gate what was actually installed.

    Grok: add the published marketplace and install skill-craft into the fresh profile in ``env``.
    Claude: load origin/main's plugins/skill-craft, the bytes the marketplace serves.
    Prints one line naming what main publishes and what the host got, so a stale
    marketplace is visible before any run starts (SPEC: publish, refresh, then run).
    """
    released = released_versions()
    plugin = None
    host = the_host(args)
    if host.marketplace:
        installed = host.install_marketplace(env)
        plugin_dir = Path(installed["path"]) if installed["path"] else out / "missing-plugin"
        plugin = {"pass": installed["pass"], "loaded": installed["loaded"], "source": installed["source"],
                  "registry_version": installed["version"]}
        how = f"{host.name} marketplace add + install (fresh profile)"
    else:
        plugin_dir = export_released(out)
        how = "origin/main export"
    versions = {"source": "marketplace", "installed_by": how, **installed_versions(plugin_dir), "released": released}
    versions["gate"] = version_gate(released, versions["plugin_version"], versions["shiploop_version"])
    if plugin is not None and not plugin["pass"]:
        versions["gate"].append("the marketplace install failed: " + ("; ".join(plugin["loaded"]) or "no plugin"))
    print(preflight_line(versions), flush=True)
    return plugin_dir, plugin, versions


def preflight_line(versions: dict) -> str:
    released = versions["released"]
    return (f"marketplace preflight: origin/main {released['origin_main'][:8]} publishes skill-craft "
            f"{released['catalog_version']} / ShipLoop {released['shiploop_version']}; "
            f"{versions['installed_by']} got skill-craft {versions['plugin_version']} / ShipLoop "
            f"{versions['shiploop_version']}; unreleased notes: {len(released.get('unreleased') or [])}; "
            f"main CI: {released.get('ci', 'unknown')}; "
            + ("OK" if not versions["gate"] else "REFUSED: " + "; ".join(versions["gate"])))


class LiveView:
    """One short line per assistant message or tool call, from either host's stream."""

    def __init__(self, start: float, enabled: bool, priced: bool = True):
        # ``priced`` False: the host's own cost figure is not the run's (Claude on Ollama prices at Anthropic's rates).
        self.start, self.enabled, self.text, self.priced = start, enabled, "", priced

    def emit(self, line: str):
        if self.enabled:
            print(f"[{time.time() - self.start:6.0f}s] {scrub(line)}", flush=True)  # the terminal and its logs keep no credential

    def flush_text(self):
        if self.text.strip():
            self.emit("say   " + " ".join(self.text.split())[:160])
        self.text = ""

    def event(self, event: dict):
        kind = event.get("type")
        if kind == "text" and isinstance(event.get("data"), str):  # Grok text delta
            self.text += event["data"]
            return
        if kind in ("thought", "usage"):
            return
        self.flush_text()
        if kind == "assistant":  # Claude whole message
            for block in (event.get("message") or {}).get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    self.text = block.get("text", "")
                    self.flush_text()
                elif block.get("type") == "tool_use":
                    self.tool(block.get("name"), block.get("input"))
        elif kind == "tool_call":  # Grok
            name = next((event[k] for k in ("toolName", "tool_name", "tool", "name", "title") if event.get(k)), "?")
            self.tool(name, event.get("rawInput"))
        elif kind in ("result", "end"):
            turns = event.get("num_turns")
            cost = metrics.money(event.get("total_cost_usd")) if self.priced else "not measured (Ollama)"
            self.emit(f"done  {metrics.session_stop(event) or 'ended'} turns={'not reported' if turns is None else turns} "
                      f"cost={cost}")

    def tool(self, name, arg):
        arg = arg if isinstance(arg, dict) else {}
        detail = next((arg[k] for k in ("command", "cmd", "file_path", "target_file", "target_directory", "pattern",
                                    "path", "skill", "description") if arg.get(k)), "")
        self.emit(f"tool  {name}: " + " ".join(str(detail).split())[:140])


def keep_awake(argv: list[str]) -> list[str]:
    """The host's argv, run under `caffeinate -d -i` on macOS and unchanged elsewhere.

    A run takes an hour or more. -i keeps the machine from idle-sleeping, which otherwise freezes the host mid-stage
    and stretches every stage timing. -d keeps the display on: on 2026-10-07 the display was off from 06:04 to 10:10
    (pmset log), the whole window in which headless Chrome never loaded a page for the Grok run, and on 2026-10-06,
    display on, the same host loaded it. SUPERSEDED 2026-10-09: with the display held awake headless Chrome still failed to load http://127.0.0.1 in the Grok host and worked in every Claude run, so display sleep is not the explanation; the hold stays only as harmless hygiene. That is a correlation, not a proven cause (a display woken with
    `caffeinate -u -d` still hung once), so this removes a variable and claims nothing more.
    """
    caffeinate = shutil.which("caffeinate") if sys.platform == "darwin" else None
    return [caffeinate, "-d", "-i", *argv] if caffeinate else argv


def events_line_count(events_path: Path, repair: bool = True) -> int:
    """The lines events.jsonl already holds: the number of the next session's first event, in the file and in the runner's
    timeline. A session killed mid-write leaves a last line without its newline, which the next session's first event
    would join (one unparsable line instead of two events, and every later number off by one), so ``repair`` ends the
    line first. The one count: the start and end rows of sessions.jsonl and ``launch`` all call it."""
    if not events_path.is_file():
        return 0
    lines, last = 0, b"\n"
    with events_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            lines += chunk.count(b"\n")
            last = chunk[-1:]
    if last != b"\n":  # a last line with no newline is a line too
        lines += 1
        if repair:
            with events_path.open("ab") as handle:
                handle.write(b"\n")
    return lines


def resume_identity(args, asked: bool, last: dict, out: Path) -> tuple[str, str | None, str | None]:
    """(host, model, effort) a resume runs with: the run's last launch's, unless a host is named (SPEC: a resume continues the
    run's own driver).

    ``--host`` names a host only if it was given (the parser's default is not a choice). A different host is refused, before
    anything starts, unless ``--allow-host-change`` says it is deliberate: the run would then be a mixed-host run, whose
    verdicts and costs belong to no one host. Model and effort given explicitly win; the recorded ones apply only while the
    host is the recorded one.
    """
    recorded = last.get("host")
    if asked and args.host != recorded and not args.allow_host_change:
        used = runrecord.hosts_used(out)
        what = (f"it already is a mixed-host run (hosts so far: {', '.join(used)}) and --host {args.host} would continue it on a "
                f"host other than its last, {recorded}" if len(used) > 1 else
                f"--host {args.host} would finish it on a different host, so it would become a mixed-host run (hosts so far: "
                f"{', '.join(used) or recorded})")
        raise SystemExit(f"--resume-run: this run was last launched on {recorded} ({last.get('model')}); {what}, and its verdicts "
                         f"and costs belong to no one host. Nothing was started. Drop --host to continue on {recorded}, or pass "
                         f"--allow-host-change to continue it on {args.host} on purpose.")
    host = args.host if asked else recorded
    same = host == recorded
    return host, args.model or (last.get("model") if same else None), args.effort or (last.get("effort") if same else None)


def resume_backend(args, last: dict) -> str | None:
    """The backend a resume runs on: the run's last launch's (SPEC: a resume keeps its run's backend). One named that
    differs is refused before anything starts, as a host change is: the run's costs and verdicts would belong to no one
    driver. A launch from before the field ran on Anthropic."""
    recorded = last.get("backend") or ("anthropic" if last.get("host") == "claude" else None)
    if args.backend and recorded and args.backend != recorded:
        raise SystemExit(f"--resume-run: this run was launched on backend {recorded}; --backend {args.backend} would make it a "
                         f"mixed-backend run, whose costs and verdicts belong to no one driver. Nothing was started. Drop "
                         "--backend to continue on its own.")
    return args.backend or recorded


def launch_stamp(out: Path, host_name: str) -> int:
    """The number a resume's launch record and prompt file are named with: the second it began in, or the next free one.

    A launch record is the run's only trace of who ran it (runrecord reads them in the order of this number), so another launch
    or a regrade that began in the same second must not overwrite it: it takes the next number instead.
    """
    stamp = int(time.time())
    while any((out / name).exists() for name in (f"invocation-resume-{host_name}-{stamp}.json", f"resume-{host_name}-{stamp}.txt")):
        stamp += 1
    return stamp


def display_held() -> bool:
    """Whether a host session runs under a display hold: the one decision is keep_awake's, asked and not repeated."""
    marker = ["host"]
    return keep_awake(marker) != marker


def declared_needs(name: str, args, earlier: dict | None = None) -> list[str]:
    """The needs this launch declares (SPEC: a record exists only where something declares its need): the case's, the
    ``--need`` flags', and those the run's own first launch recorded. A custom prompt declares none by itself."""
    case = catalog().get(name, {}) if name != "custom" else {}
    found = [*case.get("needs", []), *(args.need or []), *((earlier or {}).get("needs") or [])]
    return list(dict.fromkeys(found))


def end_host(leader: int, signum: int, grace: float = SESSION_END_SECONDS) -> bool:
    """Signal the host's leader with ``signum`` and wait, up to ``grace`` seconds, until its whole process group has gone: the
    host runs its SessionEnd hooks while it ends itself (docs/shiploop-owed-outcome-evidence/session_end_probe.out: SIGTERM,
    SIGINT and SIGHUP do, under `caffeinate` too, in under a second; SIGKILL never does). True when the group went by itself.
    The caller ends the group afterwards either way (listeners.end_group). SIGKILL is not waited for: nothing runs after it."""
    if listeners.unreaped(leader) != "running":
        return True
    try:
        os.kill(leader, signum)
    except ProcessLookupError:
        return True
    if signum == signal.SIGKILL:
        return False
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        if listeners.unreaped(leader) != "running":
            with contextlib.suppress(listeners.Unobserved):
                if not [row for row in lifecycle.table().values() if row["pgid"] == leader and row["pid"] != leader]:
                    return True
        time.sleep(EXIT_POLL_SECONDS)
    return False


def launch(argv: list[str], work: Path, out: Path, env: dict, timeout: int, watch: bool,
           first: bool = True, fresh: bool = True, translate=None, stop_when=None, stop_file: Path | None = None,
           before_start=None, end_signal=None) -> dict:
    """Run one host session. `stop_when`, polled every POLL_SECONDS, kills the session (status "interrupted").

    `end_signal()`, asked once when `stop_when` ended the session, may name a signal to send the host first (end_host): the
    host runs its session-end hooks and exits, and the group is ended after it as always. Unset, or None from it, the group
    is killed at once. The result's ``end_signal`` names the signal sent.

    `before_start(line)` is called once the checks above pass and before the host is spawned, with the number of events.jsonl
    lines already written (the session's first event will be that line): the session record's start row, which therefore
    exists for every host that ran and for no launch that was refused.

    A `stop_file` that exists kills it the same way with status "stopped": a person's request to end the run
    (the caller consumes the file). So does a SIGTERM or SIGHUP to the harness (TERMINATION, set by on_termination, which
    has already killed the host's group): the session reads as "stopped". One that begins after the harness was told to end
    (during the install, say) is ended at its first poll, with its files in place so the run's records can still be written.
    The deadline wins over all.

    The result carries ``stop``: the host's own reason from the last end/result event this
    session wrote, or None when it wrote none (killed, crashed), so a termination record can
    hold one entry per session and say unknown for the ones that never reported.

    It also carries ``left_behind``: the listeners the session left under `out` (a model's backgrounded
    server), stopped as the session ends and recorded (see listeners.py).
    """
    if first and fresh:
        # The skill must start from a directory with nothing in it.
        leftover = sorted(p.name for p in work.iterdir())
        if leftover:
            raise SystemExit(f"working directory is not empty: {leftover}")
    start = time.time()
    view = LiveView(start, watch, priced=env.get("ANTHROPIC_BASE_URL") != hosts.OLLAMA_URL)  # the route the host set
    mode = "wb" if first else "ab"  # a resumed session appends to the same streams
    stop = None
    events_path = out / "events.jsonl"
    line = 0 if first else events_line_count(events_path)
    if before_start is not None:
        before_start(line)
    argv = keep_awake(argv)
    with events_path.open(mode) as events, (out / "stderr.txt").open(mode) as stderr, \
            (out / "timeline.jsonl").open("w" if first else "a") as stamps:
        proc = subprocess.Popen(argv, cwd=work, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=stderr, env=env, start_new_session=True)
        LIVE_HOST_GROUPS.add(proc.pid)  # a signal to the harness now ends this group (on_termination)
        HOST_THREAD[proc.pid] = threading.get_ident()
        # In the run's ledger with its leader's creation identity, so a later invocation can stop it if this harness is killed.
        owned = lifecycle.own(out, proc.pid, "host")

        def record(raw: bytes):
            nonlocal line, stop
            events.write(raw)
            events.flush()
            number, line = line, line + 1
            try:
                event = json.loads(raw)
            except ValueError:
                return
            if isinstance(event, dict):
                if event.get("type") in ("end", "result"):
                    stop = metrics.session_stop(event)
                # Grok events carry no time; stamp the ones metrics.py attributes.
                if event.get("type") not in ("text", "thought"):
                    stamps.write(json.dumps({"line": number, "t": round(time.time(), 3)}) + "\n")
                    stamps.flush()
                view.event(event)

        def pump():
            # The host's translator turns its stream into the shared event shape.
            for original in proc.stdout:
                for raw in (translate or (lambda b: [b]))(original):
                    record(raw)
            view.flush_text()

        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        deadline = time.monotonic() + timeout
        status = None
        left: list = []  # what a session that ended left in its own group, ended with it
        sent_signal = None  # the signal end_signal named, once sent
        try:
            # The leader is watched without being reaped (listeners.unreaped), so once it has ended its number is still its group's.
            next_check = 0.0
            while listeners.unreaped(proc.pid) == "running":
                if time.monotonic() >= next_check:
                    if time.monotonic() >= deadline:
                        status = "timeout"
                    elif (stop_file is not None and stop_file.exists()) or TERMINATION.is_set():
                        status = "stopped"
                    elif stop_when is not None and stop_when():
                        status = "interrupted"
                    if status:
                        break
                    next_check = time.monotonic() + POLL_SECONDS
                time.sleep(EXIT_POLL_SECONDS)  # wake soon after the session ends: the stop checks above keep their own tick
            if status is None:
                with contextlib.suppress(listeners.Unobserved):
                    left = [{"pid": row["pid"], "command": row["command"][:200]}
                            for row in lifecycle.table().values() if row["pgid"] == proc.pid and row["pid"] != proc.pid]
            if status == "interrupted" and end_signal is not None and (sent := end_signal()):
                sent_signal = signal.Signals(sent).name
                end_host(proc.pid, sent)
            # The whole process group: the host and any native workers it started, or what a session that ended left in it (SPEC
            # "The resource lifecycle"). Sent while the leader is unreaped, so the number is still its group's; reaped right after.
            listeners.end_group(proc.pid)
            proc.wait()
        finally:
            if proc.poll() is not None:
                LIVE_HOST_GROUPS.discard(proc.pid)  # reaped: its pgid may be reused, so it is never signalled again
                HOST_THREAD.pop(proc.pid, None)
                lifecycle.ended(out, owned, "session ended" if status is None else status,
                                **({"left_in_group": left} if left else {}))
        if status is None:
            # A signal may have killed the group before this loop saw it: that is a stop, not a host failure.
            status = "stopped" if TERMINATION.is_set() else "exited" if proc.returncode == 0 else "failed"
        reader.join(timeout=10)
        proc.stdout.close()
    return {"status": status, "returncode": proc.returncode,
            "elapsed_seconds": round(time.time() - start, 1), "stop": stop, "left_behind": listeners.reap(out),
            **({"end_signal": sent_signal} if sent_signal else {})}


def summarize_events(path: Path) -> dict:
    """What the host reported: commands, plugins, model, turns and cost."""
    seen: dict = {"commands": [], "plugins": []}
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":  # Claude
            seen["model"] = event.get("model")
            seen["commands"] = event.get("slash_commands") or []
            seen["plugins"] = [p for p in event.get("plugins") or [] if isinstance(p, dict)]
        elif kind == "available_commands" and not seen["commands"]:  # Grok
            seen["commands"] = [c for c in event.get("commands") or [] if isinstance(c, str)]
        elif kind in ("result", "end"):
            # The stop is the host's own reason, an error never a success (metrics.session_stop, the one rule).
            stop = metrics.session_stop(event)
            seen.setdefault("sessions", []).append(
                {"num_turns": event.get("num_turns"), "cost_usd": event.get("total_cost_usd"), "stop": stop})
            seen.update(stop=stop)
    ended = seen.get("sessions") or []
    if ended:
        # Each host session reports its own totals; a resumed run adds them up. The cost is
        # unknown unless every ended session reported one (metrics.total_cost, the one rule),
        # and the turns are unknown unless one did: a count nobody reported is not 0.
        reported = [s["num_turns"] for s in ended if isinstance(s["num_turns"], int)
                    and not isinstance(s["num_turns"], bool)]
        seen["num_turns"] = sum(reported) if reported else None
        seen["cost_usd"] = metrics.total_cost(ended)
    return seen


def _runs_shiploop_cli(command: str) -> bool:
    # Claude often builds the path from a variable (SKILL_ROOT=.../skills/shiploop; $SKILL_ROOT/scripts/shiploop).
    return "skills/shiploop" in command and "scripts/shiploop" in command


def shiploop_cli_ran(events_path: Path) -> bool:
    """Whether any tool call ran the installed ShipLoop CLI (Grok/Codex tool_call or Claude tool_use events)."""
    for line in events_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "tool_call":
            arg = event.get("rawInput") if isinstance(event.get("rawInput"), dict) else {}
            if "skills/shiploop/scripts/shiploop" in str(arg.get("command") or ""):
                return True
        elif event.get("type") == "assistant" and isinstance(event.get("message"), dict):
            for block in event["message"].get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and isinstance(block.get("input"), dict):
                    if _runs_shiploop_cli(str(block["input"].get("command") or "")):
                        return True
    return False


def last_session_id(events_path: Path) -> str | None:
    """The host session to resume: the last session id the event stream carried."""
    found = None
    for line in events_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and isinstance(event.get("sessionId"), str):
            found = event["sessionId"]
    return found


def shiploop_cli(plugin_dir: Path) -> Path:
    """The ShipLoop CLI file of a plugin build."""
    return plugin_dir / "skills" / "shiploop" / "scripts" / "shiploop"


def run_cli(host_name: str, out: Path, plugin_dir: Path) -> Path:
    """The ShipLoop CLI a run uses: the copy its host installed into the run's profile (Grok, Codex), else the plugin
    build itself (Claude loads --plugin-dir directly). The one place the seed and every resume prompt get it from."""
    return hosts.host(host_name).plugin_cli(out / "home") or shiploop_cli(plugin_dir)


def resume_prompt(run_dir: str | None, cli: Path, note: str | None = None) -> str:
    """The prompt that continues a run: the exact command of the CLI the run started on (SPEC: a resume names the
    CLI the run itself uses). There is no bare-command form; main refuses a resume whose CLI file is gone.
    ``note`` (a platform case's `resume_note`, see resume_platform_note) is appended as it is; without one the prompt is unchanged."""
    if run_dir is None:
        prompt = ("This session ended before the ShipLoop run was started. Continue the original "
                  "request now: start the ShipLoop run as its skill directs and follow each packet to "
                  "the end of the run. Never end the turn while a ShipLoop command is still running.")
    else:
        prompt = ("This session ended while the ShipLoop run was still active. Continue it now: run "
                  f"`python3 \"{cli}\" next --run-dir \"{run_dir}\"` and follow the packet it prints, to the end of the "
                  "run. Never end the turn while a ShipLoop command is still running.")
    return f"{prompt} {note}" if note else prompt


def resume_told(run_dir: str | None, cli: Path) -> dict | None:
    """What ``resume_prompt`` names, as values: the CLI and the run directory (None where the prompt names no recovery command).
    The Claude host passes its prompt in ``-p`` and keeps no prompt file, so sessions.jsonl stores these."""
    return None if run_dir is None else {"cli": str(cli), "run_dir": run_dir}


def resume_command(out: Path, args) -> str:
    """The exact command that continues this run in place, with the harness flags that bound it.

    invocation.json keeps the host's argv and not the harness flags, so a command with only --resume-run would
    fall back to the default --timeout, which is above the limit of a launching task (a task kill leaves no
    records). The binary flag is carried because a fake or a non-default binary is part of the invocation.
    """
    parts = ["python3", str(Path(__file__).resolve()), "--resume-run", str(out), "--host", args.host,
             "--model", args.model, *(["--effort", args.effort] if args.effort else []),
             *(["--timeout", str(args.timeout)] if args.timeout else []),
             *(["--max-resumes", str(args.max_resumes)] if args.max_resumes is not None else []),
             *(["--max-budget-usd", str(args.max_budget_usd)] if args.max_budget_usd else []),
             "--permission-mode", args.permission_mode]
    binary = getattr(args, args.host + "_bin")
    if binary != parser().get_default(args.host + "_bin"):
        parts += [f"--{args.host}-bin", binary]
    if args.source == "checkout":  # a checkout build the harness made itself has no --plugin-dir; the line still says what it ran on
        parts += ["--source", "checkout", *(["--plugin-dir", str(args.plugin_dir)] if args.plugin_dir else [])]
    if getattr(args, "keep_platform", False):
        parts.append("--keep-platform")  # a resume keeps the platform only if it is told to again
    if getattr(args, "platform_existing", None) == "update":
        parts += ["--platform-existing", "update"]  # accepted on a resume only if it names the run's own mode
    return shlex.join(parts)


def model_visible_output(raw) -> str:
    """The text a host showed the model for one tool result.

    Grok stores shell output twice: `output` as a list of byte values and
    `output_for_prompt` as the (possibly truncated) text the model saw.
    """
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        for key in ("output_for_prompt", "content", "text"):
            if isinstance(raw.get(key), str):
                return raw[key]
    return ""


def host_truncations(events_path: Path) -> list[dict]:
    """Tool results the host cut off before the model saw them (Grok's ~20 KB cap)."""
    calls, cut = {}, {}
    for line in events_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "tool_call":
            arg = event.get("rawInput") if isinstance(event.get("rawInput"), dict) else {}
            calls[event.get("toolCallId")] = str(arg.get("command") or arg.get("target_file") or "")[-160:]
        elif event.get("type") == "tool_call_update" and isinstance(event.get("rawOutput"), dict):
            raw = event["rawOutput"]
            if raw.get("truncated"):
                cut[event.get("toolCallId")] = {"total_bytes": raw.get("total_bytes"),
                                                "shown_chars": len(model_visible_output(raw))}
    return [dict(item, call=calls.get(call_id, "")) for call_id, item in cut.items()]


def write_transcript(events_path: Path, path: Path) -> None:
    """A readable transcript (messages and tool calls) for people and the reviewer."""
    lines: list[str] = []
    view = LiveView(0.0, False)
    view.emit = lambda line: lines.append(line)  # type: ignore[method-assign]
    for raw in events_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if isinstance(event, dict):
            if event.get("type") == "user":  # Claude tool results
                for block in (event.get("message") or {}).get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        content = block.get("content")
                        text = content if isinstance(content, str) else json.dumps(content)
                        lines.append("out   " + " ".join(str(text).split())[:400])
            elif event.get("type") == "tool_call_update" and event.get("status"):  # Grok
                shown = model_visible_output(event.get("rawOutput"))
                if shown:
                    lines.append(f"out   {event.get('status')} " + " ".join(shown[:400].split()))
            view.event(event)
    view.flush_text()
    path.write_text("\n".join(lines) + "\n")


def grade_claude_plugin(plugins: list[dict], plugin_dir: Path | None) -> dict:
    paths = [p.get("path") for p in plugins if p.get("name") == PLUGIN_NAME]
    if plugin_dir is None:
        return {"pass": len(paths) == 1, "loaded": paths}
    wanted = str(plugin_dir.resolve())
    return {"pass": paths == [wanted], "loaded": paths, "wanted": wanted}


# Which ShipLoop run an output folder holds, and the one rule that picks it from several, is run_choice.py: this module
# records the identity (below) and run_choice reads it back, with metrics.run_dir_of and the progress monitor.
def record_run_identity(out: Path, **fields) -> None:
    (out / RUN_IDENTITY).write_text(json.dumps({**run_identity(out), **fields}, indent=2) + "\n")


def record_preexisting_runs(out: Path) -> None:
    """Before the first host or seed of a new output folder: the runs already in it, each with its state.md digest, are not
    this invocation's. A run at one of those paths whose state has since changed is (a new run can reuse the path)."""
    record_run_identity(out, preexisting={found["run_dir"]: state_digest(found["run_dir"]) for found in shiploop_runs(out)})


def live_run_dir(out: Path) -> str | None:
    """While the host drives it, the run this invocation created, by the one rule (run_choice.choose); None while there is
    none, or several that nothing tells apart."""
    chosen = run_choice.choose(out).chosen
    return chosen["run_dir"] if chosen else None


def grade_shiploop(out: Path) -> dict:
    """The state of the ShipLoop run this output folder's invocation created (SPEC: a verdict is earned by the run graded).

    The run is the one run_choice.choose picks: the run RUN_IDENTITY records, else the only run that was not already there
    when the invocation started, else, among several, the live one (not paused or halted) and then the one the host's ShipLoop
    commands named. A choice that holds whatever the runs' statuses become is then recorded; a choice that follows statuses is
    made again at every grade. Several candidates that nothing tells apart are reported as ambiguous and never pass: a run
    that was already there when the invocation started is never a candidate (2026-10-16 E2E audit,
    docs/experiments/shiploop-e2e-audit-20261016/grading/), and nothing is picked at random. The runs not chosen are listed as `other_runs`.
    """
    picked = run_choice.choose(out)
    if not picked.runs:
        return {"pass": False, "reason": "no ShipLoop state.md under the output directory"}
    chosen = picked.chosen
    if chosen is None:
        if not picked.mine:
            return {"pass": False, "runs": len(picked.runs), "reason": "no ShipLoop run of this invocation: every state.md was "
                    "there before it started (" + ", ".join(sorted(picked.before)) + ")"}
        return {"pass": False, "runs": len(picked.runs), "ambiguous": [found["run_dir"] for found in picked.tied],
                "reason": f"ambiguous: {len(picked.tied)} ShipLoop runs under the output directory{picked.why} and nothing "
                          "records or names the one this invocation created"}
    if picked.basis != "recorded" and picked.bind:
        record_run_identity(out, run_dir=chosen["run_dir"], basis=picked.basis)
    # ShipLoop builds in its own worktree beside the run and returns it to the
    # source only at release; name it so an unreturned product can be inspected.
    worktree = Path(chosen["run_dir"]).parent / "worktree"
    others = [found["run_dir"] for found in picked.runs if found is not chosen]
    return {"pass": chosen["status"] == "done" and chosen["report_html"], **chosen, "runs": len(picked.runs),
            "identity": picked.basis, **({"other_runs": others} if others else {}),
            "worktree": str(worktree) if worktree.is_dir() else None}


# The stage a seeded run starts at. step-plan opens an item's inner loop (the stages before it are recorded). A stage in
# release_slice.DELIVERED starts a release slice: the inner loop is recorded too and the case's product is committed in the worktree.
SEED_STAGES = ("step-plan", *release_slice.DELIVERED)
DEFAULT_SEED_ITEM = {"id": "seeded-request", "title": "The whole request"}
# Runs in a separate interpreter on the installed plugin's own navigator, so the
# seeded state is exactly what that version's CLI reads back.
# When an item enters its inner loop it records the item's base snapshot, as shiploop_lint.on_transition does on a real run
# (the record lint/items/<item>.md, saved in the same transaction as the state). The base run, the mutation check, the change
# inventory and the item commit read it and, without it, record "skipped: no item base was recorded" and do nothing.
SEED_SCRIPT = """
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import shiploop_lint as lint, shiploop_navigator as nav, shiploop_store as store
run_dir, stop = Path(sys.argv[2]), sys.argv[3]
item = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {"id": "seeded-request", "title": "The whole request"}
records = json.loads(sys.argv[5]) if len(sys.argv) > 5 else {}  # {stage: fields merged into that stage's synthetic result}
state = store.read_record(run_dir / "state.md")
skipped, bases = [], []
while nav.current_stage(state) != stop:
    stage, action = nav.current_stage(state), str(nav.current_action(state)["id"])
    result = {"outcome": "done", "summary": "Synthetic: recorded by the E2E seed without doing it; "
              "the request is the specification."}
    result.update(records.get(stage) or {})
    if stage == "plan":
        result["work_items"] = [item]
    entering = set(state.get("inner_loops") or {})
    state = nav.apply(state, action, result)
    if state["active_improve"] is not None:
        state = nav.finish_improve(state, action, {"summary": "Synthetic Improve receipt from the E2E seed."})
    writes = {}
    for ident in sorted(set(state.get("inner_loops") or {}) - entering):
        if lint.read_base(run_dir, ident) is None:
            writes.update(lint.capture_base(run_dir, Path(state["repo"]), ident))
            bases.append(ident)
    skipped.append(stage)
    nav.save(run_dir, state, writes)
print(json.dumps({"skipped": skipped, "stage": nav.current_stage(state),
                  "action": str(nav.current_action(state)["id"]), "delegation": state.get("delegation"),
                  "item_bases": bases}))
"""

# The knowledge home a run that had run its spec and discovery stages would have left (docs/shiploop/): the request as the only
# requirement and the case's own commands. The seed records those stages without doing them, so a later gate that reads the home
# (a test case's requirement must have an entry in the living spec) would otherwise send the model off to write one.
SEED_HOME = "docs/shiploop"


def seed_home(work: Path, prompt: str, checks: list[str] | None = None) -> list[str]:
    """Write a neutral spec (R-1 = the request) and environment (## Commands = the case's checks) into the seed repository.

    Returns the paths written, relative to `work`; a file the fixture already holds is kept. The files are written before the
    seed's baseline commit, so they are part of the checkout the run starts from and of every item's base snapshot.
    """
    request = " ".join(prompt.split())
    commands = [check.strip() for check in checks or [] if check.strip()]
    files = {
        "spec.md": ("# Living spec\n\nSeeded by the E2E harness: the stages before step-plan are recorded without doing them, so the "
                    f"request is the specification.\n\n## Requirements\n\nR-1: {request}\n"),
        "environment.md": ("# Environment\n\nSeeded by the E2E harness from the case's own checks; discovery did not run.\n\n"
                           "## Commands\n\n" + ("```sh\n" + "\n".join(commands) + "\n```\n" if commands else "none recorded\n")),
    }
    written = []
    for name, text in files.items():
        path = work / SEED_HOME / name
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            written.append(f"{SEED_HOME}/{name}")
    return written


def seed_run(cli: Path, work: Path, out: Path, prompt: str, stop: str, *, fixture: Path | None = None,
             work_item: dict | None = None, delegation: str | None = None, checks: list[str] | None = None,
             home: bool = True, product: Path | None = None, home_fixture: Path | None = None,
             records: dict | None = None, exclude: list[str] | tuple = (), planning_review: str | None = None,
             improve_skill: str = "") -> dict:
    """Start a run and record its stages before `stop` as synthetic.

    `planning_review` and `improve_skill` are the run's `--planning-review` and `--improve-skill` options (unset: the
    engine's default, `stage`); `none` needs the Improve card, since no planning child binds one.

    ShipLoop refuses a repository without a commit, so the seed commits a README first, or the whole `fixture`
    directory when one is given (a step slice starts on an existing product). `work_item` is the plan's only item
    (default: the whole request); `delegation` is the run's route (default Ask-Agent, which the chain cases need, and inline
    for a release slice, as a real run of such a case is). `records` ({stage: fields}) are merged into the synthetic result of
    each stage the seed records (SEED_SCRIPT).
    The seed records the item's base snapshot (SEED_SCRIPT) and, unless `home` is false (the flagged no-home variant:
    `--seed-without-home`), commits a neutral knowledge home built from `prompt` and `checks` (seed_home).

    A stop in release_slice.DELIVERED starts a RELEASE SLICE: the item's whole inner loop is recorded too, `home_fixture` is
    the knowledge home (release_slice.copy_home) instead of the neutral one, and `product` (a folder, less `exclude`) is
    committed in the run's worktree after the item's base was recorded, so the item reads as delivered: built after its base,
    not part of it. The source checkout holds only the baseline until the run's own return.
    """
    delivered = release_slice.delivered(stop)
    if delivered and (product is None or home_fixture is None):
        raise SystemExit(f"seed: a seed at {stop} needs the case's product and knowledge home (seed_product, seed_home)")
    delegation = delegation or ("inline" if delivered else "ask-agent")
    item = work_item or DEFAULT_SEED_ITEM
    if fixture is not None:
        shutil.copytree(fixture, work, dirs_exist_ok=True)
    else:
        (work / "README.md").write_text("# Seeded ShipLoop E2E case\n")
    written = (release_slice.copy_home(work, home_fixture) if delivered else seed_home(work, prompt, checks)) if home else []
    # The seed must not depend on the machine's Git config: a global or system filter (for example git-lfs on a
    # CI runner) would make ShipLoop's workspace refuse the repository.
    git_env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    identity = ["-c", "user.name=ShipLoop E2E seed", "-c", "user.email=shiploop-e2e-seed@example.invalid"]
    for args in (["init", "-q"], ["add", "-A"], [*identity, "commit", "-qm", "seed: baseline"]):
        subprocess.run(["git", "-C", str(work), *args], check=True, capture_output=True, text=True, env=git_env)
    head = subprocess.run(["git", "-C", str(work), "rev-parse", "HEAD"], check=True, capture_output=True,
                          text=True, env=git_env).stdout.strip()
    root = out / ".shiploop-runs" / "seed"
    options = ([f"--planning-review={planning_review}"] if planning_review else []) + \
        ([f"--improve-skill={improve_skill}"] if improve_skill else [])
    started = subprocess.run([sys.executable, str(cli), "workspace", "start", f"--repo={work}",
                              f"--workspace-root={root}", f"--delegation={delegation}", f"--prompt={prompt}", *options],
                             capture_output=True, text=True, env=git_env)
    if started.returncode:
        raise SystemExit(f"seed: workspace start failed: {(started.stderr or started.stdout)[-2000:]}")
    run_dir = root / "run"

    def advance(to: str) -> dict:
        done = subprocess.run([sys.executable, "-c", SEED_SCRIPT, str(cli.parent), str(run_dir), to, json.dumps(item),
                               json.dumps(records or {})], capture_output=True, text=True, env=git_env)
        if done.returncode:
            raise SystemExit(f"seed: could not advance the run to {to}: {done.stderr[-2000:]}")
        return json.loads(done.stdout)

    # A release slice stops at the item's first stage once: the item's base is recorded there (what it started from is the
    # baseline), and only then is the built product committed on top of it.
    reached = advance(stage_spec.INNER[0] if delivered else stop)
    built = None
    if delivered:
        worktree = Path(store.read_record(run_dir / "state.md")["repo"])
        built = release_slice.commit_product(worktree, product, list(exclude), item, git_env, identity)
        later = advance(stop)
        reached = {**later, "skipped": reached["skipped"] + later["skipped"], "item_bases": reached["item_bases"]}
    return {"stage": stop, "run_dir": str(run_dir), "start_head": head, "home": written, **reached,
            **({"product": built, "home_fixture": home_fixture.name} if built else {})}


def seed_materials(name: str, stage: str | None) -> dict | None:
    """What a release-slice seed at ``stage`` takes from the case (release_slice.materials), or None for no seed and for a seed that
    is not a release slice. A custom --prompt has no built product to start from."""
    if not release_slice.delivered(stage):
        return None
    if name == "custom":
        raise SystemExit(f"--seed-at {stage} starts after the build and needs a case that declares its built product "
                         "(seed_product, seed_home and seed_release in cases.json): a custom --prompt has none")
    return release_slice.materials(name, catalog().get(name) or {}, stage)


def seed_prompt(cli: Path, run_dir: str, prompt: str, delegation: str = "ask-agent", stage: str = "step-plan") -> str:
    route = "Ask-Agent" if delegation == "ask-agent" else "inline"
    recorded = (f"The test harness recorded its stages before {stage} without doing them: the product the request describes is "
                "already built and committed in the run's worktree, and the request itself is the specification."
                if release_slice.delivered(stage) else
                f"The test harness recorded its stages before {stage} without doing them, so the request itself is the "
                "specification.")
    return (f"A ShipLoop run for the request below is already active, with {route} delegation. {recorded} "
            f"Continue the run now: run `python3 \"{cli}\" next --run-dir \"{run_dir}\"` and "
            "follow the packet it prints, to the end of the run. Never end the turn while a ShipLoop command "
            f"is still running.\n\nThe request: {prompt}")


CHAIN_DEFAULTS = {"min_steps": 2, "min_in_flight": 2, "min_depth": 1}


def _bindings(out: Path):
    for binding_path in sorted(out.rglob("chains/*/binding.md")):
        if binding_path.relative_to(out).parts[0] not in ("home", "build", "marketplace"):
            yield binding_path


def _depth(deps: dict[str, list[str]]) -> int:
    """Steps on the longest dependency path (1 = no step depends on another)."""
    memo: dict[str, int] = {}

    def level(step: str, seen: frozenset = frozenset()) -> int:
        if step not in memo:
            memo[step] = 1 + max((level(d, seen | {step}) for d in deps.get(step, []) if d not in seen), default=0)
        return memo[step]
    return max((level(step) for step in deps), default=0)


def chain_facts(out: Path, expect: dict | None = None) -> dict:
    """ShipLoop chain evidence from files only, never from the model's account.

    For each binding under run/chains/<action>/, from the dispatcher state and the
    bridge ledger (in ledger order): steps accepted, native vs main-context
    attempts, the most launched workers not yet imported (fan-out), each step's
    integrations (contribution_recorded; exactly one each), and whether every step
    launched only after each dependency was integrated. `expect` (a case's
    "chain" entry) sets min_steps, min_in_flight and min_depth.
    """
    expect = {**CHAIN_DEFAULTS, **(expect or {})}
    chains = []
    for binding_path in _bindings(out):
        fact = {"binding": str(binding_path)}
        try:
            binding = store.read_record(binding_path)
            state_file = Path(binding["dispatcher_run"]) / "plan-dispatcher-state.json"
            state = json.loads(state_file.read_text()) if state_file.is_file() else {"steps": {}, "attempts": {}}
            events = chain_ledger.read_events(str(binding_path.parent / "events"))
        except (store.StorageError, ValueError, KeyError, OSError) as exc:
            chains.append(dict(fact, error=str(exc)))
            continue
        attempts = state.get("attempts", {})
        steps = state.get("steps", {})
        deps = {s["id"]: list(s.get("deps") or []) for s in (state.get("graph") or {}).get("steps", [])}
        step_of = {attempt: record.get("step") for attempt, record in attempts.items()}
        in_flight, most, after_retry, retried = set(), 0, 0, False
        first_launch, integrated, integrations = {}, {}, {}
        for row in events:
            event = row["event"]
            data = event.get("data") or {}
            attempt = data.get("attempt")
            step = data.get("step") or step_of.get(attempt)
            if event["kind"] == "launched_result":
                in_flight.add(attempt)
                most = max(most, len(in_flight))
                if retried:
                    after_retry = max(after_retry, len(in_flight))
                first_launch.setdefault(step, event["seq"])
            elif event["kind"] in ("handoff_import_result", "retry_result"):
                # A retried attempt was lost or rejected; it is no longer running work for the chain.
                in_flight.discard(attempt)
                retried = retried or event["kind"] == "retry_result"
            elif event["kind"] == "contribution_recorded":
                integrations[step] = integrations.get(step, 0) + 1
                integrated.setdefault(step, event["seq"])
        out_of_order = sorted(step for step, needs in deps.items() if step in first_launch and any(
            dep not in integrated or integrated[dep] > first_launch[step] for dep in needs))
        accepted = sum(1 for s in steps.values() if s.get("status") == "accepted")
        fact.update({
            "mode": binding.get("mode"),
            "steps": len(steps),
            "accepted": accepted,
            "depth": _depth(deps),
            "native_attempts": sum(1 for a in attempts.values() if a.get("handle")),
            "main_context_attempts": sum(1 for a in attempts.values() if a.get("executor")),
            "attempts": len(attempts),
            "max_in_flight": most,
            "max_in_flight_after_retry": after_retry if retried else None,
            "out_of_order": out_of_order,
            "integrated_twice": sorted(step for step, count in integrations.items() if count > 1),
            "not_integrated": sorted(step for step in steps if integrations.get(step, 0) == 0),
            "events": len(events),
        })
        fact["pass"] = (fact["steps"] >= expect["min_steps"] and accepted == fact["steps"]
                        and fact["depth"] >= expect["min_depth"] and most >= expect["min_in_flight"]
                        and not out_of_order and not fact["integrated_twice"] and not fact["not_integrated"])
        chains.append(fact)
    return {"pass": any(c.get("pass") for c in chains), "expect": expect, "bindings": chains}


RECOVERY_SOURCE = ("SPEC S-6 (runs survive session resumes) and S-14 (unattended by default): a fresh session "
                   "recovers the chain without a person")


def run_minutes(run_dir: str | None) -> float | None:
    """Minutes from ShipLoop's run start to its last accepted action, from the run's own timeline.

    It survives killed sessions, and includes any pause between a kill and its resume.
    """
    if not run_dir:
        return None
    try:
        timeline = json.loads((Path(run_dir) / "timeline.json").read_text())
        stamps = [datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ") for v in timeline.get("accepted", {}).values()]
        start = datetime.strptime(timeline["started"], "%Y-%m-%dT%H:%M:%SZ")
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return round((max(stamps) - start).total_seconds() / 60, 1) if stamps else None


def budget_facts(budget: dict | None, seeded: bool, run_dir: str | None, interrupted: bool = False) -> dict | None:
    """A should-level expectation: reported beside the verdicts, never failing the run.

    An interrupted run is not held to it: the deliberate kill makes the run replay its lost
    workers' work, so its time measures recovery, not the request (c1, 2026-10-04: 30.9 min).
    """
    if not budget or not seeded or "seeded_minutes" not in budget:
        return None
    observed = run_minutes(run_dir)
    if interrupted:
        return {"level": "should", "applies": False, "expected_minutes": budget["seeded_minutes"],
                "observed_minutes": observed, "pass": None, "source": budget.get("source"),
                "reason": "interrupted on purpose: recovery replays the lost workers' work"}
    return {"level": "should", "applies": True, "expected_minutes": budget["seeded_minutes"],
            "observed_minutes": observed, "pass": observed is not None and observed <= budget["seeded_minutes"],
            "source": budget.get("source")}


MISMATCH_TEMPLATE = """# Mismatch: {case} on {host} ({output})

Fill in every field, then record the decision in test/shiploop_e2e/LEARNINGS.md.

## Expected
{expected}

## Observed
{observed}

## Triage (answer in order; stop at the first yes)
1. Is the check itself wrong? (Does it pass a reference solution and fail an empty one? If not, fix the test.)
2. Is it the environment? (Network, session limits, host outages: fix the harness or ops; the expectation stands.)
3. Is it reproduced, or is its trigger clear? (If not, rerun before changing anything.)
4. Does the expectation describe how instead of what? (Then the expectation changes.)
5. Would a normal run hit it? (If not, document it as a known limit.)
6. Does the behaviour come from a deliberate design rule? (Then two intents conflict: the owner decides.)
7. Does the expectation trace to its source? (Then the product changes. An expectation with no source gets one first, or is dropped.)

## Why

## Decision (product / expectation / owner / known limit / environment)

## Verified by
"""


def write_mismatch(out: Path, name: str, host: str, failed: list[tuple[str, str, str]]) -> Path:
    """One file per failing run, pre-filled with each failed must-level expectation and what was observed."""
    expected = "\n".join(f"- **{verdict}**: {want}" for verdict, want, _ in failed)
    observed = "\n".join(f"- **{verdict}**: {got}" for verdict, _, got in failed)
    path = out / "mismatch.md"
    path.write_text(MISMATCH_TEMPLATE.format(case=name, host=host, output=out, expected=expected, observed=observed))
    return path


def chain_in_flight(out: Path) -> bool:
    """Whether some chain worker has launched and its result is not yet imported."""
    for binding_path in _bindings(out):
        try:
            events = chain_ledger.read_events(str(binding_path.parent / "events"))
        except (ValueError, OSError):
            continue
        open_attempts = set()
        for row in events:
            event = row["event"]
            attempt = (event.get("data") or {}).get("attempt")
            if event["kind"] == "launched_result":
                open_attempts.add(attempt)
            elif event["kind"] in ("handoff_import_result", "retry_result"):
                open_attempts.discard(attempt)
        if open_attempts:
            return True
    return False


def knowledge_facts(work: Path) -> dict:
    """How the run left the source checkout: knowledge home, commits and branches.

    Informational: it shows whether a later run could inherit the spec and
    environment notes from the repository itself.
    """
    def g(*args: str) -> str:
        done = subprocess.run(["git", "-C", str(work), *args], capture_output=True, text=True)
        return done.stdout if done.returncode == 0 else ""

    spec = work / "docs" / "shiploop" / "spec.md"
    status = g("status", "--porcelain", "--untracked-files=all").splitlines()
    untracked = [ln[3:] for ln in status if ln.startswith("??")]
    # Logs a server or test run leaves behind are not product; anything else uncommitted is.
    uncommitted = [ln[3:] for ln in status if not ln[3:].endswith(".log")]
    return {"spec": spec.is_file(),
            "head": g("rev-parse", "HEAD").strip() or None,
            "uncommitted": uncommitted,
            "spec_tracked": bool(g("ls-files", "--", "docs/shiploop/spec.md").strip()),
            "requirement_ids": sorted(set(knowledge_home._REQUIREMENT_ID.findall(spec.read_text())),
                                      key=lambda value: int(value.split("-")[1])) if spec.is_file() else [],
            "head_commits": len(g("rev-list", "HEAD").split()),
            "head_files": len(g("ls-tree", "-r", "--name-only", "HEAD").splitlines()),
            "untracked_files": len(untracked),
            "branches": g("branch", "--format=%(refname:short)").split()}


def committed_facts(knowledge: dict, start_head: str | None) -> dict:
    """The ``committed`` verdict: the product is in HEAD, and none of it is left outside.

    HEAD must have moved past where the run started, hold at least one file and leave no product
    path uncommitted (logs aside). The file count is what makes the first test mean something: on a
    fresh run ShipLoop's first act is an empty baseline commit, so HEAD always differs from a start
    with no commit, and a run that ended before it returned anything would otherwise pass.

    Known limit, not guarded: any file counts. A future ShipLoop that returned only knowledge files
    (docs/shiploop/) to the source checkout before the product would pass early; today those stay in
    ShipLoop's worktree until the product is returned.
    """
    head, files = knowledge["head"], knowledge["head_files"]
    return {"pass": bool(head) and head != start_head and files > 0 and not knowledge["uncommitted"],
            "start_head": start_head, "head": head, "head_files": files,
            "uncommitted": knowledge["uncommitted"][:20]}


def review_export(out: Path) -> str:
    """Export the run's Run Review documents (skills/shiploop-run-review/SKILL.md). Fail-open: a problem is reported in
    the returned line and never changes a verdict or the exit code."""
    try:
        if not REVIEW_EXPORTER.is_file():
            return f"review export skipped: no exporter at {REVIEW_EXPORTER}"
        folder = fidelity.load_exporter(REVIEW_EXPORTER).export_run(out)
        page = Path(str(folder)) / "run-review.html"  # the standalone page the exporter writes beside the bundle (0.1.3 and later)
        return f"review export: {folder}" + (f"; page {page}" if page.is_file() else "")
    except Exception as exc:  # noqa: BLE001 - any export failure is reported, never raised
        return f"review export skipped: {' '.join(str(exc).split())[:300] or type(exc).__name__}"


def flow_record(out: Path) -> str:
    """flow.json and flow.html (flow.py): the run as a ShipLoop-to-model sequence. A record, never a verdict: a failure
    is one line."""
    try:
        flow.write(out)
        return str(out / "flow.html")
    except BaseException as exc:  # noqa: BLE001 - fail-open recording (SystemExit too: a run with no state has no flow)
        return f"not written: {' '.join(str(exc).split())[:200] or type(exc).__name__}"


def untracked(work: Path) -> set[str]:
    done = subprocess.run(["git", "-C", str(work), "status", "--porcelain", "--untracked-files=all"],
                          capture_output=True, text=True)
    return {ln[3:] for ln in done.stdout.splitlines() if ln.startswith("?? ")} if done.returncode == 0 else set()


CHECK_TIMEOUT = 180  # seconds, one case check's ceiling; a platform case may raise it (platform.check_timeout)


def run_checks(work: Path, checks: list[str], timeout: int = CHECK_TIMEOUT, env: dict | None = None, scrubbed: bool = False) -> list[dict]:
    """Run each check in `work`, then delete any untracked file the checks created.

    A follow-on run copies this checkout; a leftover (a server log, say) would
    make ShipLoop see a dirty start and return only a working-tree delta.

    ``scrubbed`` (a case with a platform) removes credentials from the stored output.
    """
    before = untracked(work)
    results = []
    for command in checks:
        try:
            done = subprocess.run(command, shell=True, cwd=work, capture_output=True, stdin=subprocess.DEVNULL,
                                  text=True, timeout=timeout,
                                  env=dict(os.environ, E2E_CHECKS=str(HERE / "checks"), **(env or {})))
            code, output = done.returncode, (done.stdout + done.stderr)[-2000:]
        except subprocess.TimeoutExpired:
            code, output = None, "timeout"
        output = scrub(output) if scrubbed else output
        results.append({"command": command, "pass": code == 0, "returncode": code, "output": output})
    for leftover in sorted(untracked(work) - before):
        (work / leftover).unlink(missing_ok=True)
    return results


# One check's ceiling in the product-at-stop run, the same 180 s as a check in the working directory (CHECK_TIMEOUT); a platform
# case's check_timeout does not raise it, because a check that runs out here is `timed_out`, never a product failure. A ceiling
# for a check that never ends, not a tuning value.
PRODUCT_AT_STOP_TIMEOUT = 180


def product_at_stop(shiploop: dict, engine: dict, checks: list[str], env: dict | None = None, scrubbed: bool = False) -> dict | None:
    """For a run whose ShipLoop did not reach done: do the case checks pass in ShipLoop's unreturned worktree?

    Information only (SPEC S-11): it never touches ``checks``, ``committed``, ``pass`` or the exit code, because a run that
    never delivered must not pass. It names the engine's position, so a partial product at ``implement`` is not read as a
    finished one, and keeps each check's return code, so a check that timed out is ``timed_out`` and not a product failure.
    None for a run that passed. ``{"ran": false, "reason": ...}`` where there was nothing to run, never an absent key.
    """
    if shiploop.get("pass"):
        return None
    position = {"status": engine.get("status") or "unknown", "stage": metrics.current_stage(engine) or "unknown"}
    head = {"information_only": True}
    if not shiploop.get("worktree"):
        reason = ("no ShipLoop state.md under the output directory" if shiploop.get("reason")
                  else "no worktree directory under the run's workspace")
        return {**head, "ran": False, "reason": reason, "engine": position}
    if not checks:
        return {**head, "ran": False, "reason": "the case declares no checks", "engine": position}
    entries = []
    for done in run_checks(Path(shiploop["worktree"]), checks, timeout=PRODUCT_AT_STOP_TIMEOUT, env=env, scrubbed=scrubbed):
        timed_out = done["returncode"] is None
        entry = {"command": done["command"], "pass": done["pass"], "returncode": done["returncode"], "timed_out": timed_out}
        if not done["pass"] and not timed_out:
            entry["output"] = " ".join(str(done.get("output") or "").split())[-300:]
        entries.append(entry)
    timed = sum(entry["timed_out"] for entry in entries)
    passed = sum(entry["pass"] for entry in entries)
    return {**head, "ran": True, "worktree": shiploop["worktree"], "engine": position, "checks": entries,
            "passed": passed, "failed": len(entries) - passed - timed, "timed_out": timed, "total": len(entries)}


# ---------------------------------------------------------------- platform hooks
# A case may carry a `platform` object: the commands that make a hosted platform (an org, an account, a cloud project) safe to
# give a model, and that remove what the run made there. The harness knows nothing about any platform; it runs the commands the
# case names (README, "Platform hooks"):
#   preflight  with the HOST's environment, before any model call: non-zero aborts the run (a bad home link shows up here)
#   before     once, on a fresh run only, with E2E_PLATFORM_DIR=<output>/platform: a snapshot of what exists before the model
#   cleanup    after grading, always (a `finally`: failure, crash, Ctrl-C): remove what the run created
#   home_links names under the real HOME linked into a throwaway HOME (Grok, Codex), so the model's CLI is already signed in
#   model_bin  {command name: shell command}: a guarded stand-in for each name, written to <output>/platform/bin and put first on
#              the host's PATH. It runs the command with the REAL HOME and the model's argv as "$@", so the case's policy decides
#              what the model may do and the real CLI keeps working where a throwaway HOME hides its login (a keychain).
#              A login shell (the shell tool of Grok, `zsh -l`) runs macOS path_helper, which puts /etc/paths.d (Homebrew) ahead
#              of the PATH the host was launched with, so pin_shell_path writes the PATH back to the front in the throwaway
#              HOME's startup files and shell_resolution_problems proves, per shell, that each name still resolves to the wrapper
#   resume_note  a sentence appended to the prompt of a RESUMED run whose earlier segment's cleanup ran (the platform was reset)
#   resume_note_kept  the same for a RESUMED run whose earlier segment KEPT an unfinished platform (see keep_checks): what the
#              model deployed is still there, and the case's own preflight (which refuses a platform that is not clean) is skipped
#   keep_checks  the words (the verb of a command, for example `deployed`) of the case's own checks that must all pass for
#              --keep-platform to keep the platform of a run that did not finish; each word names exactly one of the case's checks
#   check_timeout  seconds (60..3600) one of the case's checks may run, in place of CHECK_TIMEOUT: a check that asks the platform many
#              times and cannot be run again once the cleanup has reset it
# Every command output the harness stores or prints goes through scrub().
PLATFORM_COMMANDS = ("preflight", "before", "cleanup")
PLATFORM_TIMEOUT = 900  # seconds, one command's ceiling; a command that never ends, not a tuning value
PLATFORM_TAIL = 2000  # characters of scrubbed output kept per command
HOST_END_WAIT = 10  # seconds a platform cleanup waits for this case's hosts to be gone before it acts on the platform

# Values of these keys are credentials wherever they appear (JSON, escaped JSON inside an event stream, `key: value`, `key=value`).
SECRET_KEYS = ("accessToken", "refreshToken", "clientSecret", "sfdxAuthUrl")
_SECRET_VALUE = re.compile(r"(?P<head>(?:" + "|".join(SECRET_KEYS) + r")(?:\\*[\"'])?\s*[:=]\s*(?:\\*[\"'])?)(?P<value>[^\s\"'\\,}]+)")
# A Salesforce session token, whatever key (if any) carries it: <org id>!<session>.
_SESSION_TOKEN = re.compile(r"00D[A-Za-z0-9]{12,15}![A-Za-z0-9._]{20,}")
REDACTED = "[redacted]"


def scrub(text) -> str:
    """``text`` with every credential replaced by ``[redacted]``: the value of a key named accessToken, refreshToken, clientSecret
    or sfdxAuthUrl, and any string shaped like a Salesforce session token. Idempotent; text with neither is returned unchanged."""
    text = text if isinstance(text, str) else ("" if text is None else str(text))
    text = _SECRET_VALUE.sub(lambda match: match.group("head") + REDACTED, text)
    return _SESSION_TOKEN.sub(REDACTED, text)


def scrub_files(folder: Path) -> list[str]:
    """Scrub, in place, the regular files directly in ``folder`` (the harness's own records: event stream, transcript, prompts,
    stderr), not the work folder or the host's throwaway profile. Byte-preserving where nothing matches. Returns the names changed."""
    changed = []
    for path in sorted(folder.iterdir()):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8", errors="surrogateescape")
            clean = scrub(raw)
            if clean != raw:
                path.write_text(clean, encoding="utf-8", errors="surrogateescape")
                changed.append(path.name)
        except OSError:
            continue
    return changed


def case_platform(name: str) -> dict | None:
    """The validated `platform` object of a named case, None for a case without one (and for a custom prompt)."""
    if name == "custom":
        return None
    spec = (catalog().get(name) or {}).get("platform")
    if spec is None:
        return None
    return validate_platform(name, spec)


def validate_platform(name: str, spec) -> dict:
    problems = []
    if not isinstance(spec, dict):
        raise SystemExit(f"case {name!r}: platform must be an object")
    for key in PLATFORM_COMMANDS:
        if key in spec and not (isinstance(spec[key], str) and spec[key].strip()):
            problems.append(f"{key} must be a non-empty command string")
    for key in ("resume_note", "resume_note_kept"):
        if key in spec and not (isinstance(spec[key], str) and spec[key].strip()):
            problems.append(f"{key} must be a non-empty string")
    words = spec.get("keep_checks")
    if "keep_checks" in spec and not (isinstance(words, list) and words and len(set(map(str, words))) == len(words)
                                      and all(isinstance(word, str) and word.split() == [word] for word in words)):
        problems.append("keep_checks must be a non-empty list of distinct words, each one word of a check command (for example \"deployed\")")
    if "host_allow" in spec and not (isinstance(spec["host_allow"], list)
                                     and all(isinstance(rule, str) and rule.strip() for rule in spec["host_allow"])):
        problems.append("host_allow must be a list of non-empty permission rules (for example \"Bash(sf *)\")")
    timeout = spec.get("check_timeout", CHECK_TIMEOUT)
    if not (isinstance(timeout, int) and 60 <= timeout <= 3600):
        problems.append("check_timeout must be an integer number of seconds from 60 to 3600")
    modes = spec.get("existing", [])
    if not (isinstance(modes, list) and set(modes) <= set(PLATFORM_EXISTING_MODES) and len(set(modes)) == len(modes)):
        problems.append("existing must be a list of the extra modes the case's commands support (" + ", ".join(PLATFORM_EXISTING_MODES) + ")")
    if spec.get("before") and not spec.get("cleanup"):
        problems.append("before without cleanup: nothing would remove what the run makes")
    links = spec.get("home_links", [])
    if not (isinstance(links, list) and all(isinstance(n, str) and n and "/" not in n and n not in (".", "..") for n in links)):
        problems.append("home_links must be a list of plain names under the home folder (no path separators)")
    bins = spec.get("model_bin", {})
    if not (isinstance(bins, dict) and all(isinstance(n, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", n)
                                           and isinstance(c, str) and c.strip() for n, c in bins.items())):
        problems.append("model_bin must be an object of plain command names to non-empty shell commands")
    if problems:
        raise SystemExit(f"case {name!r}: platform: " + "; ".join(problems))
    return spec


def keep_check_names(spec: dict | None, checks: list) -> dict:
    """{word: the case's checks whose command holds it as a whole word}, for each word of the platform's `keep_checks`."""
    return {word: [c for c in checks if word in str(c).split()] for word in (spec or {}).get("keep_checks") or ()}


def refuse_unmatched_keep_checks(name: str, spec: dict | None, checks: list) -> None:
    """A keep word that names no check, or more than one, would silently clean a working platform at the end of a long run:
    refused before any model starts."""
    bad = {word: len(found) for word, found in keep_check_names(spec, checks).items() if len(found) != 1}
    if bad:
        raise SystemExit(f"case {name!r}: platform.keep_checks must each name exactly one of the case's checks; "
                         + ", ".join(f"{word!r} names {count}" for word, count in bad.items()))


# What a run does about items already in the platform under the case's prefix (--platform-existing). "fresh" is how every case has
# always run: none may be there. A case lists the extra modes its commands support in platform.existing; the harness hands the mode
# to the preflight and snapshot commands as $E2E_PLATFORM_EXISTING (set only for a mode other than fresh), and the case's cleanup
# reads it back from the snapshot it compares with.
PLATFORM_EXISTING_MODES = ("update",)


def platform_existing_mode(asked: str | None, name: str, spec: dict | None, earlier: str | None = None) -> str:
    """The --platform-existing mode a run uses. ``asked`` is the flag (None: not given), ``earlier`` the mode the run being resumed
    started in (None: a new run). A resume keeps its run's mode, because the snapshot it compares with was taken under it. A mode
    other than fresh needs a case with a platform that lists it (``platform.existing``): a case whose commands do not know it would
    treat the items already there as a platform that is not clean, or ignore the flag and remove them."""
    mode = asked or earlier or "fresh"
    if earlier is not None and asked and asked != earlier:
        raise SystemExit(f"--platform-existing {asked}: this run started in {earlier} mode, and a resume keeps its run's mode")
    if mode != "fresh" and mode not in ((spec or {}).get("existing") or []):
        raise SystemExit(f"--platform-existing {mode}: case {name!r} " + (
            "has no platform, so there is nothing for the mode to apply to" if not spec else
            f"does not list {mode!r} in its platform.existing, so its commands do not know that mode"))
    return mode


def platform_env(base: dict, platform_dir: Path, existing: str = "fresh") -> dict:
    return dict(base, E2E_CHECKS=str(HERE / "checks"), E2E_PLATFORM_DIR=str(platform_dir),
                **({"E2E_PLATFORM_EXISTING": existing} if existing != "fresh" else {}))


def write_model_bin(bins: dict, platform_dir: Path, real_home: Path) -> dict:
    """Write ``<platform_dir>/bin/<name>`` for each name: an executable ``#!/bin/sh`` script that runs the case's command with the
    real HOME and the model's argv as "$@". The harness's E2E_* variables are baked in as literals (the model's environment has
    none). Returns {name: path}. The command is the case's own text, run as the case wrote it."""
    folder = platform_dir / "bin"
    folder.mkdir(parents=True, exist_ok=True)
    baked = {"E2E_CHECKS": str(HERE / "checks"), "E2E_PLATFORM_DIR": str(platform_dir), "E2E_MODEL_BIN_DIR": str(folder)}
    written = {}
    for name, command in bins.items():
        path = folder / name
        path.write_text("#!/bin/sh\n# written by the E2E harness (platform.model_bin); the case's policy decides what the model may run\n"
                        + "".join(f"export {key}={shlex.quote(value)}\n" for key, value in baked.items())
                        + f"exec env HOME={shlex.quote(str(real_home))} {command} \"$@\"\n")
        path.chmod(0o755)
        written[name] = str(path)
    return written


# The startup files a shell the model may use reads after /etc/zprofile or /etc/profile ran path_helper: zsh login (.zprofile),
# zsh interactive (.zshrc), bash login (the first of .bash_profile, .profile) and bash interactive (.bashrc).
SHELL_STARTUP_FILES = (".zprofile", ".zshrc", ".bash_profile", ".bashrc", ".profile")
PIN_MARK = "# skill-craft E2E (platform.model_bin): the guarded commands stay first on PATH after macOS path_helper moved them"
# The shells whose resolution of a guarded name is checked: a plain `-c` shell (what the host's own tools use), a login shell and
# an interactive login shell (what Grok's shell tool starts). One that is not installed here is skipped. The host's own $SHELL,
# when it is none of these, is checked too (login and interactive login): see resolution_shells.
RESOLUTION_SHELLS = (("/bin/sh", "-c"), ("/bin/sh", "-lc"), ("/bin/bash", "-c"), ("/bin/bash", "-lc"), ("/bin/zsh", "-c"),
                     ("/bin/zsh", "-lc"), ("/bin/zsh", "-ilc"))
RESOLUTION_TIMEOUT = 30  # seconds per shell


def pin_shell_path(home: Path, bin_dir: Path, real_home: Path) -> list[str]:
    """Make ``bin_dir`` the first PATH folder again after path_helper: append a marked PATH line to each shell startup file of
    the throwaway ``home``, once (a file that already holds the block is left as it is, and a file's own content is kept).

    Returns the names of the startup files that carry the block. Nothing is written when ``home`` is the real home (a Claude
    host), and a startup file that is a symlink (a ``home_links`` name) is never written through, so the real home's files are
    never touched; a host without a throwaway home is left to shell_resolution_problems to refuse."""
    home = Path(home)
    if home.resolve() == Path(real_home).resolve():
        return []
    block = f'{PIN_MARK}\nPATH={shlex.quote(str(bin_dir))}":$PATH"\nexport PATH\n'
    home.mkdir(parents=True, exist_ok=True)
    pinned = []
    for name in SHELL_STARTUP_FILES:
        path = home / name
        if path.is_symlink():
            continue
        try:
            text = path.read_text(errors="replace") if path.exists() else ""
            if block not in text:
                with path.open("a") as handle:
                    handle.write(("" if not text or text.endswith("\n") else "\n") + block)
        except OSError:
            continue
        pinned.append(name)
    return pinned


def resolution_shells(env: dict) -> list[tuple[str, str]]:
    """RESOLUTION_SHELLS, and the host's own ``$SHELL`` (login and interactive login) when ``env`` names one that is executable
    and not already listed: a host's shell tool normally starts ``$SHELL -l``, which may be Homebrew's zsh or another shell."""
    shells = list(RESOLUTION_SHELLS)
    own = env.get("SHELL")
    if own and os.path.isfile(own) and os.access(own, os.X_OK) and own not in {shell for shell, _ in shells}:
        shells += [(own, "-lc"), (own, "-ilc")]
    return shells


def shell_resolution_problems(names, bin_dir: Path, env: dict) -> list[str]:
    """One problem per guarded name and shell where the name does not resolve to ``bin_dir/<name>``: each shell of
    resolution_shells (the ones installed) is started with ``env`` (the host's: throwaway HOME, wrapper-first PATH) and asked
    ``command -v <name>``, which prints the path and never runs it. Empty means the wrapper is what the model's shells find."""
    # SHELL_SESSIONS_DISABLE: Apple Terminal's zsh session files, which an interactive zsh would write into HOME
    probe_env = dict(env, SHELL_SESSIONS_DISABLE="1")
    problems = []
    for shell, flag in resolution_shells(env):
        if not os.access(shell, os.X_OK):
            continue
        for name in names:
            want = str(Path(bin_dir) / name)
            try:
                done = subprocess.run([shell, flag, "command -v " + shlex.quote(name)], env=probe_env, stdin=subprocess.DEVNULL,
                                      capture_output=True, text=True, errors="replace", timeout=RESOLUTION_TIMEOUT,
                                      start_new_session=True)
            except subprocess.TimeoutExpired:
                problems.append(f"`{shell} {flag}` did not answer `command -v {name}` within {RESOLUTION_TIMEOUT}s")
                continue
            lines = [line.strip() for line in done.stdout.splitlines() if line.strip()]
            found = lines[-1] if lines else ""
            if found != want:
                problems.append(f"`{name}` resolves to {found or 'nothing'} under `{shell} {flag}`, not to the wrapper {want}: "
                                "the model's shell would run the real command, outside the case's policy")
    return problems


# What a model that was given a guarded sf can be seen to have run, and where the guard (checks/sf_guard.py) keeps its record.
GUARD_LOG = "sf-calls.jsonl"
PREFLIGHT_RANGES = "preflight-ranges.jsonl"  # next to the guard log: one [from, to] line per preflight that ran, appended as it ends
GUARDED_NAMES = ("sf", "sfdx")

# A command counts as running sf only where a shell would start it: the case prompt ShipLoop's `workspace start` is given, a note
# written through a heredoc, `command -v sf` and `echo "sf missing"` all contain the word without running it. So a command is read
# the way a shell reads it (quotes, here-documents, substitutions, `bash -c` scripts); the one place the word counts inside a
# string is the list form of a program's own subprocess call (`["sf", ...`, in a python heredoc or `python3 -c`).
_SHELLS = frozenset(("sh", "bash", "zsh", "dash", "ksh"))
# Words that may stand before the command a simple command runs: reserved words, and wrappers whose own flags and numbers
# (`timeout 60`, `nice -n 5`, `env -i`) are skipped with them.
_BEFORE_COMMAND = frozenset(("if", "then", "elif", "else", "do", "while", "until", "!", "{", "env", "exec", "command", "builtin",
                             "time", "nohup", "nice", "sudo", "timeout", "xargs"))
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
_SHELL_SCRIPT_FLAG = re.compile(r"-[A-Za-z]*c[A-Za-z]*")
_SF_LIST = re.compile(r"""\[\s*["']((?:[^"'\s]*/)?sf(?:dx)?)["']""")
_SF_LOOKUP = re.compile(r"(?:\$\(|`)\s*(?:command -v|which|type -p)\s+(?:sf|sfdx)\s*(?:\)|`)")
_NESTING = 4  # how deep `bash -c '... $(...) ...'` is followed


def _skip_quoted(text: str, i: int) -> int:
    """The index just past the quoted string that opens at ``text[i]`` (the end of the text where it never closes)."""
    quote, j = text[i], i + 1
    while j < len(text) and text[j] != quote:
        j += 2 if quote == '"' and text[j] == "\\" else 1
    return j + 1


def _paren_end(text: str, i: int) -> int:
    """The index of the ``)`` that closes a ``$(`` whose body starts at ``i`` (the end of the text where it never closes)."""
    depth = 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
        elif text[i] in "'\"":
            i = _skip_quoted(text, i)
        else:
            depth += (text[i] == "(") - (text[i] == ")")
            if depth == 0:
                return i
            i += 1
    return len(text)


def _substitution(text: str, i: int) -> tuple[str, int]:
    """For the ``$(`` or backtick at ``text[i]``: (the text inside the substitution, the index just past it)."""
    if text[i] == "`":
        end = text.find("`", i + 1)
        end = len(text) if end < 0 else end
        return text[i + 1:end], end + 1
    end = _paren_end(text, i + 2)
    return text[i + 2:end], end + 1


def _heredoc_body(text: str, i: int, delimiter: str, strip_tabs: bool) -> tuple[str, int]:
    """(body, index after it) of the here-document whose lines start at ``i``: everything up to the line that is the delimiter."""
    lines = []
    while i < len(text):
        end = text.find("\n", i)
        end = len(text) if end < 0 else end
        line, i = text[i:end], min(end + 1, len(text))
        if (line.lstrip("\t") if strip_tabs else line) == delimiter:
            break
        lines.append(line)
    return "\n".join(lines), i


def _shell_tokens(text: str):
    """What a POSIX shell reads in ``text``: ("word", w) with its quoting removed, ("op", c) for a separator of simple commands,
    ("sub", s) for the text inside a `$(...)` or backtick substitution (commands of their own), ("data", s) for a here-document
    body (input, not commands). A comment is dropped; an unclosed quote runs to the end of the text."""
    word: list[str] = []
    started = False  # a word is open, so a quoted '' is a word
    heredocs: list[tuple[str, bool]] = []  # read at the next newline
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t;&|()\n" or text.startswith("<<", i) and not text.startswith("<<<", i):
            if started:
                yield "word", "".join(word)
                word, started = [], False
            if c == "<":  # a here-document: its delimiter is not a word, its body starts after this line
                j = i + 2
                strip_tabs = text.startswith("-", j)
                j += strip_tabs
                while j < n and text[j] in " \t":
                    j += 1
                if j < n and text[j] in "'\"":
                    end = _skip_quoted(text, j)
                    delimiter = text[j + 1:end - 1]
                else:
                    end = j
                    while end < n and text[end] not in " \t\n;&|()<>":
                        end += 1
                    delimiter = text[j:end]
                heredocs.append((delimiter, strip_tabs))
                i = end
                continue
            if c == "\n":
                for delimiter, strip_tabs in heredocs:
                    body, i = _heredoc_body(text, i + 1, delimiter, strip_tabs)
                    yield "data", body
                    i -= 1  # the newline that ended the body's last line is the next one read
                heredocs = []
            if c not in " \t":
                yield "op", c
            i += 1
        elif c == "#" and not started:
            end = text.find("\n", i)
            i = n if end < 0 else end
        elif c == "'":
            end = _skip_quoted(text, i)
            word.append(text[i + 1:end - 1])
            started, i = True, end
        elif c == '"':
            j, part = i + 1, []
            while j < n and text[j] != '"':
                if text[j] == "\\" and text[j + 1:j + 2] and text[j + 1] in '$`"\\\n':
                    part.append(text[j + 1])
                    j += 2
                elif text.startswith("$(", j) or text[j] == "`":
                    inner, end = _substitution(text, j)
                    yield "sub", inner
                    part.append(text[j:end])
                    j = end
                else:
                    part.append(text[j])
                    j += 1
            word.append("".join(part))
            started, i = True, j + 1
        elif text.startswith("$(", i) or c == "`":
            inner, end = _substitution(text, i)
            yield "sub", inner
            word.append(text[i:end])
            started, i = True, end
        elif text.startswith("<<<", i):  # a here-string: its word is an argument
            word.append("<<<")
            started, i = True, i + 3
        elif c == "\\":
            if text[i + 1:i + 2] != "\n":  # a backslash before a newline continues the line
                word.append(text[i + 1:i + 2])
                started = True
            i += 2
        else:
            word.append(c)
            started = True
            i += 1
    if started:
        yield "word", "".join(word)


def _simple_command_runs(words: list[str], depth: int) -> list[str]:
    """The word by which the simple command ``words`` runs sf or sfdx (``sf``, ``/opt/homebrew/bin/sf``), else nothing. Leading
    `VAR=x` assignments, reserved words and wrappers are looked through; ``command -v sf`` looks sf up and does not run it; the
    script of a `bash -c` or `eval` is read as commands."""
    wrapped = False
    for start, word in enumerate(words):
        if _ASSIGNMENT.match(word) or word in _BEFORE_COMMAND:
            wrapped = wrapped or word in _BEFORE_COMMAND
        elif wrapped and word in ("-v", "-V") and words[start - 1] == "command":
            return []
        elif not (wrapped and (word.startswith("-") or word.isdigit())):
            break
    else:
        return []
    command = words[start:]
    program = command[0].rsplit("/", 1)[-1]
    if program in GUARDED_NAMES:
        return [command[0]]
    if _SF_LOOKUP.fullmatch(command[0]):
        return ["sf"]  # `$(command -v sf) org list`: whatever the PATH finds
    if depth >= _NESTING:
        return []
    if program in _SHELLS:
        for number, flag in enumerate(command[1:-1], 1):
            if _SHELL_SCRIPT_FLAG.fullmatch(flag):
                return _sf_words(command[number + 1], depth + 1)
    elif program == "eval":
        return _sf_words(" ".join(command[1:]), depth + 1)
    return []


def _sf_words(text: str, depth: int = 0) -> list[str]:
    """Every word by which a command of the shell text ``text`` runs sf or sfdx, in the order read (see _simple_command_runs)."""
    found: list[str] = []
    words: list[str] = []
    for kind, value in _shell_tokens(text):
        if kind == "word":
            words.append(value)
        elif kind == "op":
            found += _simple_command_runs(words, depth)
            words = []
        elif kind == "sub" and depth < _NESTING:
            found += _sf_words(value, depth + 1)
    return found + _simple_command_runs(words, depth)


def sf_words(command: str) -> list[str]:
    """The words by which one model command runs sf or sfdx: as a shell command (`sf`, `HOME=x /opt/homebrew/bin/sf`, `bash -lc
    'cd w && sfdx ...'`) and in the list form of a subprocess call (`["sf", ...`, `["/opt/homebrew/bin/sf", ...`)."""
    return _sf_words(command) + [match.group(1) for match in _SF_LIST.finditer(command)]


def _command_strings(value):
    """Every command under a key named `command` or `cmd`, anywhere in a decoded event (the model's own tool inputs). A list is
    an argv, as a Codex command may be, and is quoted into the one command line it stands for."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("command", "cmd") and isinstance(item, str):
                yield item
            elif key in ("command", "cmd") and isinstance(item, list) and item and all(isinstance(word, str) for word in item):
                yield shlex.join(item)
            else:
                yield from _command_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _command_strings(item)


def _model_sf(events_path: Path) -> dict[str, list[str]]:
    """{command: the words by which it runs sf} for each distinct command in the host's event stream that runs sf or sfdx. A line
    that is not JSON is skipped."""
    found: dict[str, list[str]] = {}
    try:
        lines = events_path.read_text(errors="replace").splitlines()
    except OSError:
        return found
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        for command in _command_strings(event):
            if command not in found and (words := sf_words(command)):
                found[command] = words
    return found


def model_sf_commands(events_path: Path) -> list[str]:
    """The distinct commands in the host's event stream that run `sf` or `sfdx` (`sf org list`, `HOME=/x sf apex run`,
    `subprocess.run(["sf", ...`, `/opt/homebrew/bin/sf ...`). Text that only mentions sf (the prompt, a note, a model's prose) does
    not run it and is not counted. A heuristic: it reads commands, not intent."""
    return list(_model_sf(events_path))


def _outside(word: str, bin_dir: Path) -> bool:
    """Whether ``word``, how a command started sf, is a path to something other than the wrapper in ``bin_dir``."""
    if "/" not in word:
        return False
    folder = os.path.dirname(os.path.expanduser(word))
    return not os.path.isabs(folder) or os.path.realpath(folder) != os.path.realpath(bin_dir)


def _direct(found: dict[str, list[str]], bin_dir: Path) -> list[str]:
    return [command for command, words in found.items() if any(_outside(word, bin_dir) for word in words)]


def direct_sf_commands(events_path: Path, bin_dir: Path) -> list[str]:
    """The commands among model_sf_commands that start sf or sfdx by a path (`/opt/homebrew/bin/sf`, `~/.local/share/sf/client/bin/sf`,
    `./sf`) other than the wrapper folder ``bin_dir``: the real CLI, which no wrapper stands in front of."""
    return _direct(_model_sf(events_path), bin_dir)


def guard_log_lines(out: Path) -> int:
    """The lines <output>/platform/sf-calls.jsonl holds now (0 where there is none)."""
    try:
        with (out / "platform" / GUARD_LOG).open("rb") as handle:
            return sum(chunk.count(b"\n") for chunk in iter(lambda: handle.read(1 << 20), b""))
    except OSError:
        return 0


def preflight_ranges(out: Path) -> list[tuple[int, int]]:
    """The ranges [from, to) of guard-log lines that the harness's own preflights wrote, one per preflight that ran
    (<output>/platform/preflight-ranges.jsonl, appended by platform_preflight the moment the preflight ends, so a resume that is
    refused later still has its range): wrapper calls the case's preflight command made, which are not the model's. A line that
    is not a pair of integers is skipped; empty where the file is absent."""
    ranges = []
    try:
        lines = (out / "platform" / PREFLIGHT_RANGES).read_text().splitlines()
    except OSError:
        return ranges
    for line in lines:
        try:
            first, last = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(first, int) and isinstance(last, int):
            ranges.append((first, last))
    return ranges


def guard_coverage(out: Path, preflights=()) -> dict:
    """Did the guard see the model's sf, and did the model go around it? ``{model_sf_commands, guard_calls, direct_sf_commands,
    bypassed}``: the distinct sf commands in the event stream; the calls the guard logged outside ``preflights`` (the line ranges
    of the harness's own preflights, see preflight_ranges; a call is a log line without an `end` key, allowed or denied); the
    commands that started sf by a path outside the wrapper folder; and ``bypassed``: commands were run and the guard saw none, or
    a command went around the wrapper, so the policy did not govern this run (an invalid trial, not a ShipLoop verdict). It
    catches total bypass and the direct forms above; a model that makes a guarded call and then reaches the real CLI some other way
    (its own HOME, a variable holding the path) is not seen."""
    calls = 0
    try:
        with (out / "platform" / GUARD_LOG).open(errors="replace") as handle:
            for number, line in enumerate(handle):
                if any(first <= number < last for first, last in preflights):
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if isinstance(record, dict) and "end" not in record and record.get("name", "sf") in GUARDED_NAMES:
                    calls += 1  # a host-automation stand-in's line (osascript, open) is not an sf call
    except OSError:
        pass
    found = _model_sf(out / "events.jsonl")
    commands, direct = len(found), len(_direct(found, out / "platform" / "bin"))
    return {"model_sf_commands": commands, "guard_calls": calls, "direct_sf_commands": direct,
            "bypassed": (commands > 0 and calls == 0) or direct > 0}


def bypass_lines(coverage: dict) -> list[str]:
    """The plain lines that say why a run is an invalid trial (empty where it is not)."""
    lines = []
    if coverage["direct_sf_commands"]:
        lines.append(f"the model started sf by a path outside the wrapper in {coverage['direct_sf_commands']} sf-looking commands "
                     "(see transcript.md), so the policy did not govern those calls: an invalid trial, not a ShipLoop verdict")
    if coverage["model_sf_commands"] and not coverage["guard_calls"]:
        lines.append(f"the guard saw no model call although the transcript shows {coverage['model_sf_commands']} sf-looking "
                     "commands, so the policy may not have governed this run: an invalid trial, not a ShipLoop verdict")
    return lines


def run_platform_command(command: str, cwd: Path, env: dict, timeout: int = PLATFORM_TIMEOUT) -> dict:
    """Run one platform command in a shell of its own session; {command, returncode, ok, output} with the output scrubbed and
    cut to its tail (a timeout is returncode None). A Ctrl-C while it runs is noted and waited out once, so a cleanup that has
    begun is not abandoned; a second Ctrl-C leaves it running and says so."""
    proc = subprocess.Popen(command, shell=True, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, errors="replace", start_new_session=True)
    interrupts, code, output = 0, None, ""
    deadline = time.monotonic() + timeout
    while True:
        try:
            output, _ = proc.communicate(timeout=max(1, deadline - time.monotonic()))
            code = proc.returncode
            break
        except subprocess.TimeoutExpired:
            listeners.end_group(proc.pid)  # the harness's one group kill (S-12): the shell and whatever it started
            output, _ = proc.communicate()
            output += f"\ntimeout after {timeout}s"
            break
        except KeyboardInterrupt:
            interrupts += 1
            if interrupts > 1:
                output, code = "abandoned by a second Ctrl-C; it may still be running", None
                break
            print("Ctrl-C: waiting for the platform command to finish (press again to abandon it)", flush=True)
    return {"command": command, "returncode": code, "ok": code == 0, "output": scrub(output)[-PLATFORM_TAIL:]}


def link_homes(names: list[str], env: dict) -> list[dict]:
    """Symlink ``<throwaway home>/<name>`` to ``~/<name>`` for each name that exists, and say what happened to each name.

    Only existence is checked (a stat), never the contents: the harness does not read credentials. A host on the real HOME (Claude)
    needs nothing; a name that does not exist is skipped silently and recorded as absent.
    """
    real, target = Path.home(), Path(env.get("HOME") or Path.home())
    if target.resolve() == real.resolve():
        return [{"name": name, "linked": False, "reason": "the host runs in the real HOME"} for name in names]
    records = []
    for name in names:
        source, link = real / name, target / name
        if not source.exists():
            records.append({"name": name, "linked": False, "reason": "absent from the real HOME"})
        elif link.is_symlink() and os.readlink(link) == str(source):
            records.append({"name": name, "linked": True, "target": str(source)})
        elif os.path.lexists(link):
            records.append({"name": name, "linked": False, "reason": "already present in the throwaway HOME; not replaced"})
        else:
            link.symlink_to(source)
            records.append({"name": name, "linked": True, "target": str(source)})
    return records


def platform_preflight(spec: dict, host_env: dict, out: Path, skip_command: str | None = None, existing: str = "fresh") -> dict:
    """Make the home links and the model_bin wrappers, then run the case's preflight command with the host's environment;
    {home_links, preflight} (plus, where the case has a model_bin: model_bin {name: wrapper path}, shell_path_pinned,
    model_bin_resolution {ok, problems}). With a model_bin it also appends [from, to], the guard-log lines the case's preflight
    command wrote through the wrappers (not the model's calls), to <output>/platform/preflight-ranges.jsonl as the preflight
    ends (see preflight_ranges). ``preflight`` is None where the case names no command.
    ``host_env`` is changed in place: with model_bin its PATH starts with the wrappers' folder, which is what the host launches
    with and what the preflight runs under (so it proves the wrapper works from the host's environment).

    With model_bin the wrapper must also be what the model's shells find: pin_shell_path puts it first again in the throwaway
    HOME's startup files, and shell_resolution_problems checks each shell. Any problem makes ``preflight`` a failing record and
    the case's own preflight command is not run, so both callers refuse the run (a host on the real HOME is not pinned, so it
    is refused when a login shell reorders its PATH: refused rather than run unguarded).

    ``existing`` is the run's --platform-existing mode, handed to the command as $E2E_PLATFORM_EXISTING.

    ``skip_command`` (a reason) leaves the case's own preflight command unrun and records it as skipped, ok: the resume of a run
    whose earlier segment kept an unfinished platform, which the command would refuse as not clean. The links, the wrappers and
    their per-shell proof still run."""
    platform_dir = out / "platform"
    platform_dir.mkdir(exist_ok=True)
    links = link_homes(spec.get("home_links") or [], host_env)
    state: dict = {"home_links": links}
    if spec.get("model_bin"):
        real_home = Path(os.environ.get("HOME") or Path.home())
        state["model_bin"] = write_model_bin(spec["model_bin"], platform_dir, real_home)
        host_env["PATH"] = str(platform_dir / "bin") + os.pathsep + host_env.get("PATH", "")
        state["shell_path_pinned"] = pin_shell_path(Path(host_env.get("HOME") or real_home), platform_dir / "bin", real_home)
        problems = shell_resolution_problems(list(spec["model_bin"]), platform_dir / "bin", host_env)
        state["model_bin_resolution"] = {"ok": not problems, "problems": problems}
        if problems:
            state["preflight"] = {"command": "model_bin shell resolution", "returncode": 1, "ok": False,
                                  "output": scrub("\n".join(problems))[-PLATFORM_TAIL:]}
            return state
    command = spec.get("preflight")
    first = guard_log_lines(out)  # where this invocation's preflight starts writing (a resume's preflight calls are not the model's)
    try:
        state["preflight"] = ({"command": command, "returncode": None, "ok": True, "skipped": skip_command, "output": ""}
                              if command and skip_command
                              else run_platform_command(command, out, platform_env(host_env, platform_dir, existing)) if command else None)
    finally:
        if spec.get("model_bin"):
            # Recorded here, not with the invocation record: a resume can be refused after its preflight (the version gate), and
            # the wrapper lines that preflight wrote must still not read as the model's calls at the next resume.
            with (platform_dir / PREFLIGHT_RANGES).open("a") as handle:
                handle.write(json.dumps([first, guard_log_lines(out)]) + "\n")
    return state


def manual_cleanup_command(out: Path, spec: dict) -> str:
    """The cleanup as one command to paste into any shell: `env` sets the two variables before the shell expands the case's
    text (a `VAR=x cmd "$VAR"` prefix does not: $VAR is empty in that same command's arguments)."""
    return (f"env E2E_PLATFORM_DIR={shlex.quote(str(out / 'platform'))} E2E_CHECKS={shlex.quote(str(HERE / 'checks'))} "
            f"sh -c {shlex.quote(spec['cleanup'])}")


# What an armed guard writes to the cleanup record until its own cleanup or keep replaces it. A harness killed hard in between (a
# task limit, SIGKILL) then leaves a record that shows no successful cleanup, not the ok record an earlier segment of the run wrote.
PENDING_CLEANUP = {"ran": False, "ok": False, "pending": True, "reason": "this invocation has not cleaned yet"}


def write_cleanup_record(out: Path, record: dict) -> None:
    """Write <output>/platform/cleanup-record.json, the file earlier_cleanup_record reads; a write that fails leaves what the file held."""
    with contextlib.suppress(OSError):
        (out / "platform").mkdir(exist_ok=True)
        (out / "platform" / "cleanup-record.json").write_text(json.dumps(record, indent=2) + "\n")


def earlier_cleanup_record(out: Path) -> dict | None:
    """The cleanup record the run's last cleanup wrote (<output>/platform/cleanup-record.json); None where there is none. A
    Ctrl-C or a crash runs the cleanup but never reaches result.json, so this is where a resume learns that the platform was reset."""
    try:
        record = json.loads((out / "platform" / "cleanup-record.json").read_text())
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) else None


def resume_platform_note(spec: dict | None, earlier_platform: dict, regrade: bool) -> str | None:
    """The case's `resume_note` for a run that continues after its platform was reset (the earlier invocation's cleanup ran), or
    its `resume_note_kept` where the earlier invocation kept an unfinished platform (what the model deployed is still there);
    None for a regrade (no host starts), for a case without that note, and where neither happened. ``earlier_platform`` is the
    earlier result's platform block, or {"cleanup": earlier_cleanup_record(...)} where that run never wrote a result."""
    cleanup = earlier_platform.get("cleanup") or {}
    note = (spec or {}).get("resume_note_kept" if cleanup.get("kept_unfinished") else "resume_note")
    return note.strip() if note and not regrade and (cleanup.get("ran") or cleanup.get("kept_unfinished")) else None


def cleanup_banner(out: Path, spec: dict, record: dict) -> str:
    tail = [line for line in str(record.get("output") or "").splitlines() if line.strip()][-5:]
    return "\n".join([
        "!" * 78,
        f"PLATFORM CLEANUP FAILED: what this run created in the platform may still be there ({out}).",
        "Remove it now by running, from any directory:",
        f"  {manual_cleanup_command(out, spec)}",
        *(f"  | {line}" for line in tail),
        "!" * 78])


def kept_banner(out: Path, spec: dict, unfinished: bool = False) -> str:
    """The block printed when --keep-platform kept what a run made in the platform: where it is and the one way to remove it.
    ``unfinished``: ShipLoop did not finish, so the block says this is NOT a pass and that a resume continues with the platform in place."""
    return "\n".join([
        "=" * 78,
        f"PLATFORM KEPT (--keep-platform): what this run made is still in the {spec.get('kind') or 'platform'} ({out}).",
        *([f"ShipLoop did not finish, so this is NOT a pass: the platform is kept because the case's keep checks passed "
           f"({', '.join(spec.get('keep_checks') or ())}). Resuming this run continues with it in place."] if unfinished else []),
        f"The cleanup did not run, so everything the run deployed stays until you remove it; the snapshot taken before the run is in "
        f"{out / 'platform'}. Nothing else removes it, and a later run of this case may refuse to start while it is there.",
        "Remove it now by running, from any directory:",
        f"  {manual_cleanup_command(out, spec)}" if spec.get("cleanup")
        else "  (the case names no cleanup command: remove it in the platform itself)",
        "=" * 78])


def keep_blocker(*, process: dict, stop_seen: bool, stop_file: Path, invalid: bool, earlier_cleanup: dict | None = None) -> str | None:
    """Why no run may be kept, finished or not; None where nothing forbids it. A person's stop, a stop file or a signal, an invalid
    trial, and (for a regrade) an earlier cleanup that was attempted and failed: what is in the platform is then not a delivery
    anyone chose to keep. No record at all, or only the pending one an armed guard leaves (a harness that was killed), does not
    forbid it."""
    if earlier_cleanup and not earlier_cleanup.get("ok") and not earlier_cleanup.get("pending"):
        return "an earlier cleanup of this run failed: run the printed command first"
    if TERMINATION.is_set() or stop_seen or stop_file.exists() or process.get("status") == "stopped":
        return f"the run was stopped ({stop_cause(stop_file)})"
    if invalid:
        return "an invalid trial: the guard did not govern the model's sf"
    return None


def keep_refusal(*, shiploop: dict, engine: dict, process: dict, stop_seen: bool, stop_file: Path, checks: list,
                 invalid: bool, earlier_cleanup: dict | None = None) -> str | None:
    """Why a --keep-platform request is not honoured for a FINISHED delivery; None where it is. A finished delivery is ShipLoop
    done and its report written, the host ended by itself, every case check passed, and no stop, no timeout and no invalid trial
    (keep_blocker). Every other ending is judged by keep_decision. ``earlier_cleanup`` is the cleanup record of the run being
    graded again (a regrade)."""
    if blocked := keep_blocker(process=process, stop_seen=stop_seen, stop_file=stop_file, invalid=invalid,
                               earlier_cleanup=earlier_cleanup):
        return blocked
    if process.get("status") == "timeout":
        return "the host timed out"
    if engine.get("status") != "done":
        return f"ShipLoop is {engine.get('status') or 'unknown'}, not done"
    if not shiploop.get("pass"):
        return f"ShipLoop wrote no report ({shiploop.get('status') or shiploop.get('reason')})"
    if process.get("pass") is False:
        return f"the host ended {process.get('status')} rc={process.get('returncode')}"
    if failed := [check["command"] for check in checks if not check["pass"]]:
        return f"a case check failed ({failed[0][:120]})"
    return None


KEPT_FINISHED, KEPT_UNFINISHED = "finished", "unfinished"


def keep_decision(*, keep_checks: tuple | list = (), **ended) -> tuple[str | None, str | None]:
    """How a --keep-platform request ends: (KEPT_FINISHED, None) for a finished delivery (keep_refusal), (KEPT_UNFINISHED, None)
    for a run that did not finish (ShipLoop not done, or the host timed out) whose platform is nevertheless working, or
    (None, why) when it is cleaned. The platform of an unfinished run is working when the case declares ``keep_checks`` (words of
    its own checks, for example `deployed`, `tests`, `rules`) and every one of them ran and passed; a person's stop, a signal, an
    invalid trial and a failed earlier cleanup (keep_blocker) forbid it. The run is then recorded NOT a pass. A run whose ShipLoop
    is done and whose host did not time out is judged as a finished delivery only: a failed check there is a failed delivery."""
    why = keep_refusal(**ended)
    if why is None:
        return KEPT_FINISHED, None
    unfinished = ended["process"].get("status") == "timeout" or ended["engine"].get("status") != "done"
    if not (keep_checks and unfinished) or keep_blocker(process=ended["process"], stop_seen=ended["stop_seen"], stop_file=ended["stop_file"],
                                                         invalid=ended["invalid"], earlier_cleanup=ended.get("earlier_cleanup")):
        return None, why
    unmet = [word for word in keep_checks
             if not any(word in str(check["command"]).split() and check["pass"] for check in ended["checks"])]
    if unmet:
        return None, f"{why}; not kept as an unfinished run either: the keep check(s) {', '.join(unmet)} did not pass"
    return KEPT_UNFINISHED, None


class PlatformGuard:
    """Owns the platform cleanup of one invocation. ``arm`` it once the model may start (or has started); ``finish`` runs the
    cleanup once, from the normal path after grading and again from main's `finally`, which is what covers a crash, a
    KeyboardInterrupt and a SystemExit. Before it acts on the platform it ends this thread's own host and waits for it to be
    gone (HOST_END_WAIT), so a cleanup never runs beside a model that can still deploy. ``keep`` instead leaves a finished
    delivery in the platform (--keep-platform): a later ``finish`` then does nothing, and ``print_kept`` shows the block that says
    how to remove it by hand. A guard that was never armed does nothing. Arming also replaces the cleanup record an earlier
    invocation left with a pending one (PENDING_CLEANUP), so a harness killed before its own cleanup is not read as already cleaned."""

    def __init__(self):
        self.spec: dict | None = None
        self.out: Path | None = None
        self.done = False
        self.record: dict | None = None
        self.banner: str | None = None  # the kept block, until it has been printed

    def arm(self, spec: dict, out: Path) -> None:
        self.spec, self.out, self.done, self.record, self.banner = spec, out, False, None, None
        if spec.get("cleanup"):  # a case with no cleanup command writes no record at its end either (finish)
            write_cleanup_record(out, PENDING_CLEANUP)

    def armed(self) -> bool:
        """Whether a cleanup is still pending: armed, and neither run nor kept yet."""
        return self.spec is not None and not self.done

    def keep(self, reason: str, unfinished: bool = False) -> dict | None:
        """Leave the platform as the run made it. The record is {ran: False, ok: True, kept: True, reason}: ok, because nothing
        failed (a regrade does not clean a kept run), kept, so a reader of result.json or cleanup-record.json can tell. With
        ``unfinished`` (ShipLoop did not finish: see keep_decision) it also holds kept_unfinished: True, which is what a resume reads
        to leave the case's preflight unrun and to say what the model deployed is still there. None where no cleanup is pending."""
        if not self.armed():
            return None
        self.done = True
        with contextlib.suppress(KeyboardInterrupt):  # a host that is somehow still alive must not deploy into what is kept
            end_live_hosts(thread=threading.get_ident(), wait=HOST_END_WAIT)
        self.record = {"ran": False, "ok": True, "kept": True, **({"kept_unfinished": True} if unfinished else {}), "reason": reason}
        self.banner = kept_banner(self.out, self.spec, unfinished)
        write_cleanup_record(self.out, self.record)
        return self.record

    def print_kept(self) -> None:
        """Print the kept block once (also from main's `finally`, so a crash after the decision still shows how to remove it)."""
        if self.banner:
            print(self.banner, flush=True)
            self.banner = None

    def finish(self) -> dict | None:
        if self.spec is None or self.done:
            return self.record
        self.done = True
        # A Ctrl-C or an exception can arrive while this case's host still works: end it and wait until it is gone, so the
        # cleanup never overlaps a model that can still deploy.
        with contextlib.suppress(KeyboardInterrupt):  # a second Ctrl-C ends the wait, never the cleanup
            end_live_hosts(thread=threading.get_ident(), wait=HOST_END_WAIT)
        command = self.spec.get("cleanup")
        if not command:
            self.record = {"ran": False, "ok": True, "reason": "the case names no cleanup command"}
            return self.record
        try:
            done = run_platform_command(command, self.out, platform_env(dict(os.environ), self.out / "platform"))
            self.record = {"ran": True, "ok": done["ok"], "returncode": done["returncode"], "output": done["output"]}
        except BaseException as exc:  # noqa: BLE001 - the record of a cleanup that could not run is the point
            self.record = {"ran": True, "ok": False, "returncode": None,
                           "output": scrub(f"cleanup could not run: {type(exc).__name__}: {exc}")[-PLATFORM_TAIL:]}
        if not self.record["ok"]:
            print(cleanup_banner(self.out, self.spec, self.record), flush=True)
        write_cleanup_record(self.out, self.record)
        return self.record


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--case", default="hello", help="case name from cases.json (default: hello)")
    p.add_argument("--suite", help="run a suite from suites.json in order (focused: one style in depth; "
                                   "breadth: one case per style); --output becomes the suite directory")
    p.add_argument("--baseline", type=Path, default=BASELINES,
                   help="append one summary row per run to this file (default: the committed baselines.jsonl)")
    p.add_argument("--prompt", help="run this prompt instead of a named case")
    p.add_argument("--resume-run", type=Path,
                   help="an earlier run's output directory whose ShipLoop run stopped while active (a host ran "
                        "out of credits, a machine slept): continue that same run in place, on --host, and grade "
                        "it as usual. The case and checks come from the earlier run. A run that is already "
                        "done or blocked is only graded again (a regrade): no host starts, so its metrics.json "
                        "and result.json are refreshed and a blocked run is not resumed as if answered. "
                        "The harness prints the exact command that continues a run when it starts and when it "
                        "ends with the run still active.")
    p.add_argument("--grade-only", action="store_true",
                   help="with --resume-run: start no host for any run, whatever its status, and write metrics.json, "
                        "result.json and the review export from what is on disk. For a run whose harness was killed "
                        "with its host (a task limit, an owner kill) and so never wrote them. Stop the host first: "
                        "a live host makes this a mid-run snapshot, and for a run with a platform whose cleanup never "
                        "succeeded it is cleaned now, which a model still running in it (a host outlives a killed "
                        "harness) can undo or race.")
    p.add_argument("--platform-existing", choices=("fresh", "update"),
                   help="a case with a platform that lists the mode (platform.existing in cases.json): what the run does about "
                        "items already in the platform under the case's prefix. fresh (the default): none may be there, the "
                        "preflight refuses when one is, and the cleanup restores that. update: the run deploys over work an earlier "
                        "run kept (--keep-platform): the items already there are the baseline, the snapshot records them, and the "
                        "cleanup removes only what the run adds beyond it (with --keep-platform nothing is removed). A resume keeps "
                        "its run's mode. Not with --suite")
    p.add_argument("--platform-prefix", metavar="PREFIX",
                   help="a case with a platform: name everything this run creates there with PREFIX instead of the case's own "
                        "prefix, renamed everywhere the case names it (the prompt, the checks, the platform commands and the guard), "
                        "so a kept app of the same case is left alone. A capital letter and 3 to 19 letters or digits, sharing no "
                        "beginning with any case's prefix. A resume keeps its run's prefix. Not with --suite or --seed-at")
    p.add_argument("--keep-platform", action="store_true",
                   help="a case with a platform: when the run ends normally with a finished delivery (ShipLoop done, every "
                        "case check passed), do not run the platform cleanup; keep what the run made there for a person to "
                        "use, and print the command that removes it later by hand. A run that did not finish (ShipLoop not "
                        "done, or the host timed out) is kept too, recorded NOT a pass, when the case's keep_checks (the "
                        "checks that prove the platform works) all pass and the trial is valid. Any other ending (a crash, "
                        "Ctrl-C, stop, a failed keep check or case check, an invalid trial) cleans as usual and says the keep "
                        "was not honoured. A resumed run keeps it only if the resume command passes it again. A new run "
                        "needs --output <a durable folder> (the snapshot the later cleanup needs must not live in $TMPDIR). "
                        "Not with --suite")
    p.add_argument("--continue-from", type=Path,
                   help="an earlier run's output directory: start in a copy of its source checkout "
                        "(required by follow-on cases, which name the case they follow)")
    p.add_argument("--seed-at", choices=SEED_STAGES,
                   help="start a run at this stage, with the earlier stages recorded without doing them. step-plan: an "
                        "Ask-Agent run that reaches the implementation chain without hours of planning, graded on the chain. "
                        "system-test-author or release-plan: a RELEASE SLICE of a case that declares seed_product, seed_home and "
                        "seed_release: an inline run whose built product is committed in its worktree, so only the release "
                        "stages run; graded on which of them ShipLoop accepted and whether the platform change (the deploy) "
                        "happened in the release stage (test/shiploop_e2e/README.md, \"The release slice\")")
    p.add_argument("--seed-without-home", action="store_true",
                   help="with --seed-at: do not commit the neutral knowledge home (docs/shiploop/spec.md with R-1, "
                        "environment.md with the case's checks) into the seed repository. The item base is recorded either way. "
                        "The flagged variant, to see which refusals a run with no spec hits")
    p.add_argument("--interrupt-at", choices=("chain-launched",),
                   help="kill the host (and its workers) as soon as a chain worker is in flight, then resume the "
                        "run with a fresh session; graded as `recovery`")
    p.add_argument("--owner-note-at", choices=stage_spec.STAGES, metavar="STAGE",
                   help="write one owner note (`shiploop note`, with the run's own CLI) once a step of STAGE is current and its "
                        "packet has printed, as the run's owner would mid-step; recorded in owner-note.json, and its fate "
                        "(held, delivered, cited) in metrics.json run_trace.checks.owner_note. A resume keeps the stage")
    p.add_argument("--check", action="append", help="extra shell check run in the work dir (repeatable)")
    p.add_argument("--planning-review", choices=stage_spec.PLANNING_REVIEW_MODES,
                   help="the ShipLoop run option: append it to the prompt of a --case or --prompt run so the model starts "
                        "ShipLoop with it (none also names this plugin's Improve card, --improve-skill, which that mode "
                        "requires). A named case keeps its case, style and baseline key; without the option the prompt "
                        "is the case's own and the engine's default applies. Not with --seed-at")
    p.add_argument("--output", type=Path, help="new directory for this attempt (default: under $TMPDIR)")
    p.add_argument("--host", choices=[*sorted(hosts.HOSTS), "all"], default="claude",
                   help="the host that drives ShipLoop; 'all' only with --preflight-only (checks every host)")
    p.add_argument("--backend", choices=("anthropic", "ollama"), default=None,
                   help="claude only: ollama (default), Claude Code on a model the local Ollama server serves, default "
                        f"{hosts.OLLAMA_MODEL}, with the user's Anthropic credentials scrubbed (SPEC \"The Claude host can run "
                        "on Ollama\"); or anthropic, Claude's own models. A resume keeps its run's backend")
    p.add_argument("--model", help=f"default: {hosts.OLLAMA_MODEL} (claude), claude-sonnet-5-5 (claude --backend "
                                   "anthropic), grok-4.7 (grok)")
    p.add_argument("--effort", help="reasoning effort; default: host default (claude), medium (grok)")
    p.add_argument("--skill", help="command that invokes ShipLoop; default: skill-craft:shiploop (claude), shiploop (grok)")
    p.add_argument("--source", choices=("marketplace", "checkout"), default="marketplace",
                   help="marketplace (default): test what the whichguy marketplace publishes now, gated on "
                        "local HEAD == origin/main and matching versions; checkout: build this checkout")
    p.add_argument("--preflight-only", action="store_true",
                   help="pull skill-craft from the marketplace into a fresh profile, print what main publishes "
                        "and what the host installed, and exit non-zero if the version gate refuses")
    p.add_argument("--plugin-dir", type=Path, help="test this skill-craft plugin build (implies --source checkout)")
    p.add_argument("--max-turns", type=int, default=None,
                   help="a turn limit for the host session; default: none (the owner wants no turn limit)")
    # No limit is imposed unless one is asked for (owner 2026-10-24: no turn, spend, time or resume limit by default).
    p.add_argument("--max-budget-usd", type=float, default=None,
                   help="claude --backend anthropic only, default none; grok has no spend cap")
    p.add_argument("--permission-mode", default="auto")
    p.add_argument("--timeout", type=int, default=None, help="seconds before the host is killed; default: none")
    p.add_argument("--max-resumes", type=int, default=None,
                   help="grok only: resume the same session at most this many times while ShipLoop is still active; "
                        "default: no limit")
    p.add_argument("--quiet", action="store_true", help="do not print the live progress view")
    p.add_argument("--max-parallel", type=int, default=3,
                   help="suites: run up to this many independent case chains at once (default 3)")
    p.add_argument("--serial", action="store_true",
                   help="suites: run every case one after another (rerun a failure that appears only in parallel "
                        "this way before attributing it to ShipLoop)")
    p.add_argument("--suite-name", help=argparse.SUPPRESS)
    p.add_argument("--allow-host-change", action="store_true",
                   help="with --resume-run: finish the run on the --host named even though its last launch was on another "
                        "host, which makes it a mixed-host run (without this flag that is refused; a resume that names no "
                        "--host continues on the host the run was last launched on)")
    p.add_argument("--need", action="append", choices=environment.NEEDS, default=[],
                   help="declare a need of this run, which records its capability on the harness side before the host "
                        "starts (browser: can a headless browser load a stand-in page here). A named case declares its own "
                        "(`needs` in cases.json); a custom --prompt declares none by itself. A record, never a verdict")
    p.add_argument("--baseline-report", action="store_true",
                   help="read-only: print, per cell of the baseline file and the run folders, how many attempts there were, "
                        "which count, on how many builds, and the n, min, median and max of cost, turns, minutes and "
                        "planning minutes. Starts no host and writes nothing; exits 0")
    p.add_argument("--runs", type=Path, nargs="+",
                   help="with --baseline-report: run folders (or folders of run folders) to read beside the baseline file")
    p.add_argument("--json", action="store_true", help="with --baseline-report: print JSON instead of text")
    p.add_argument("--release-gate", action="store_true",
                   help="with --baseline-report: also print, per case style, the last pass a marketplace run recorded and how "
                        "many ShipLoop releases origin/main made since (the local ref; nothing is fetched)")
    p.add_argument("--grok-bin", default="grok")
    p.add_argument("--claude-bin", default="claude")
    p.add_argument("--codex-bin", default="codex")
    p.add_argument("--browser-bin", default=None,
                   help="the browser the capability record probes (default: a Chrome or Chromium found in the usual places)")
    return p


def host_given(argv: list[str]) -> bool:
    """Whether --host was passed at all (argparse cannot tell a default from the same value given)."""
    probe = parser()
    probe.set_defaults(host=None)
    return probe.parse_args(argv).host is not None


# The identity fields of a row and a result: what the run ran on and for how long. Each is null where it is not known, and
# `identity_unmeasured` says why for each null one.
IDENTITY_FIELDS = ("plugin_sha256", "prompt_sha256", "host_build", "local_head", "started", "ended", "planning_seconds")
# Termination keys that are records of how the run ended (group G4: the blocked detail and what a regrade read), kept in
# result.json and left out of the baseline row, which carries what its eligibility (row_reached_done reads engine_status) and
# comparison read. engine_status_at_regrade predates them and stays.
_BLOCKED_KEYS = tuple(f"engine_{key}" for key in metrics.blocked_detail({}))
ROW_EXCLUDED_TERMINATION = frozenset((*_BLOCKED_KEYS, *(f"{key}_at_regrade" for key in (
    "engine_stage", "engine_status_reason", *_BLOCKED_KEYS))))


def row_termination(termination) -> dict | None:
    """A result's termination as the baseline row keeps it: without ROW_EXCLUDED_TERMINATION."""
    if not isinstance(termination, dict):
        return termination
    return {key: value for key, value in termination.items() if key not in ROW_EXCLUDED_TERMINATION}
PREDATES = "not recorded by this result (it predates the field)"
LAUNCH_PREDATES = runrecord.LAUNCH_PREDATES
FIRST_PREDATES = "first launch predates the field"


def baseline_stages(stages: list | None) -> list | None:
    """The per-stage fields worth committing: enough to locate a regression, no more.

    `tool_calls` stays in the run's own metrics.json, which is
    disposable; a committed baseline only needs what a comparison reads, plus the
    markers that say a row is not comparable. A counter the host did not report is
    committed as null (see metrics.per_stage), never as 0.
    """
    if stages is None:
        return None
    keep = ("stage", "outcome", "seconds", "turns", "timing", "incomplete")
    return [{k: row[k] for k in keep if k in row} for row in stages if isinstance(row, dict)]


def concurrent_line(out) -> str | None:
    """The line printed when a run starts beside other live harness runs under its runs root (``environment.alive_runs``), so
    a run meant for a timing comparison is not started there by mistake (SPEC "Parallel work"). Printed only, never a refusal,
    and a scan that fails prints nothing: the run's own overlap record, read at its end, says what overlapped."""
    try:
        alive = environment.alive_runs(out)
    except Exception:  # noqa: BLE001 - a notice that cannot be made is left out, never raised
        return None
    if not alive:
        return None
    return (f"  concurrent  {len(alive)} other harness run(s) alive under {environment.runs_root(out)}: "
            f"{', '.join(alive[:5])}{' …' if len(alive) > 5 else ''}; a wall-time or cost comparison with this run is not clean")


def overlapped_runs(result: dict) -> int | None:
    """How many neighbouring runs the run's own overlap record saw (``environment.overlap``), for the baseline row; null where
    the record was not observed. A record, never an exclusion: no baseline rule reads it."""
    seen = (result.get("environment") or {}).get("overlap")
    if isinstance(seen, dict) and seen.get("observed") is True and isinstance(seen.get("runs"), list):
        return len(seen["runs"])
    return None


def baseline_row(result: dict, style: str | None, suite: str | None,
                 planning_review: str = metrics.NOT_RECORDED) -> dict:
    """One comparable summary of a run: the per-case history the suites judge against (SPEC: E2E suites).

    Carries host, model and effort because a baseline compares only with rows
    from the same three (SPEC: the driver is a parameter, not a code path), and
    per-stage rows so a regression can be located in a stage rather than only in
    a whole-run total. ``baseline_stages`` decides which stage fields are worth
    committing; the full rows stay in the run's own metrics.json. A counter the host's
    events cannot show is null here and named in ``unmeasured``, so a later run on that
    host compares it as not measured and never as 0 -> 0. ``planning_review`` is the
    run's option as its state.md recorded it (``metrics.planning_review``): a run is
    compared only with a row of the same mode (``planning_review_line``).
    """
    m = result.get("metrics") or {}
    versions = result.get("versions") or {}
    row = {"date": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "case": result.get("case"), "style": style,
            "suite": suite, "host": result.get("host"), "model": result.get("model"),
            "effort": result.get("effort"), "stages": baseline_stages(m.get("stages")),
            "termination": row_termination(result.get("termination")), "unmeasured": sorted(m.get("unmeasured") or {}),
            "source": versions.get("source"), "plugin_version": versions.get("plugin_version"),
            "shiploop_version": versions.get("shiploop_version"), "planning_review": planning_review,
            "pass": result.get("pass"),
            "verdicts": {k: (result.get(k) or {}).get("pass") for k in ("invoked", "plugin", "process",
                                                                       "shiploop", "committed")},
            "checks_passed": sum(bool(c.get("pass")) for c in result.get("checks") or []),
            "checks": len(result.get("checks") or []),
            "turns": m.get("turns"), "cost_usd": m.get("cost_usd"),
            # Whether turns and cost cover only the sessions that reported (metrics.lower_bound): stated on the row from
            # build step 8, when sessions.jsonl made the count exact on every host, so a Grok row is no longer one by host.
            "lower_bound": metrics.lower_bound(m),
            "sessions": len((result.get("process") or {}).get("sessions") or []),
            "cancelled_tool_calls": m.get("cancelled_tool_calls"), "model_glue": m.get("model_glue"),
            "tmp_writes": m.get("tmp_writes"),
            "shiploop_failures": m.get("shiploop_failures"), "compactions": m.get("compactions"),
            "truncated_outputs": m.get("truncated_outputs"), "narrative": m.get("narrative"),
            # Identity: what the run ran on and for how long, null where the result does not say (never 0 or ''). A
            # checkout run records its head in versions.local_head, a marketplace run under versions.released.
            "plugin_sha256": versions.get("plugin_sha256"), "prompt_sha256": result.get("prompt_sha256"),
            "host_build": result.get("host_build"),
            "local_head": versions.get("local_head") or (versions.get("released") or {}).get("local_head"),
            "started": (result.get("span") or {}).get("started"), "ended": (result.get("span") or {}).get("ended"),
            "planning_seconds": m.get("planning_seconds"),
            "overlapped_runs": overlapped_runs(result),
            "output": result.get("output")}
    reasons = result.get("identity_unmeasured") if isinstance(result.get("identity_unmeasured"), dict) else {}
    row["identity_unmeasured"] = {name: reasons.get(name) or PREDATES for name in IDENTITY_FIELDS if row[name] is None}
    return row


# `planning_review` (state.md key, ShipLoop 1.22.0 and later) says which planning results start an Improve child: `stage`
# after each of spec, test-strategy, plan, step-plan and test-spec, `none` after none of them. Planning minutes, Improve
# passes and turns are not the same quantity in the two modes, so a run is compared with the last row of its own mode
# (the same case, source, host, model and effort as ever) and never with a row of the other mode; when no earlier row of
# that driver has the run's mode, nothing is compared and the report says so (`planning_review_line`). A row written before
# the field existed has no mode; it stands for `stage` only when its recorded plugin_version is below
# PLANNING_REVIEW_FIRST_RELEASE (the option did not exist then, so each of its planning stages started an Improve child,
# which is what `stage` does). A row with no usable plugin_version, or with that release or a later one and no field, stands
# for nothing known ("not recorded") and is compared with no run: a mode is never inferred from anything else.
PLANNING_REVIEW_FIRST_RELEASE = "1.22.0"


def _release(text) -> tuple[int, int, int] | None:
    """A MAJOR.MINOR.PATCH version as numbers, or None for a missing version or any other shape (a development build)."""
    found = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", text) if isinstance(text, str) else None
    return tuple(int(part) for part in found.groups()) if found else None


def row_planning_review(row: dict) -> tuple[str, str]:
    """(the planning_review mode a baseline row stands for, why, when the row does not say: "" for a recorded mode)."""
    recorded = row.get("planning_review")
    if recorded is not None:
        return (recorded if isinstance(recorded, str) else json.dumps(recorded)), ""
    version = row.get("plugin_version")
    placed = _release(version)
    if placed is not None and placed < _release(PLANNING_REVIEW_FIRST_RELEASE):
        return "stage", f"records no mode, read as stage because plugin {version} predates the option"
    return (metrics.NOT_RECORDED, "records no mode and " + (
        f"plugin {version} does not predate the option" if placed is not None
        else "no plugin_version places it before the option"))


def planning_review_line(mode: str, last: dict) -> str:
    """The report line for a run that has no earlier row of its own mode to compare with. `last` is the last row of the
    same driver, which stands for another mode or for none (a run that records no mode matches no row)."""
    earlier, why = row_planning_review(last)
    reason = "this run records no mode" if mode == metrics.NOT_RECORDED else f"no earlier row of mode {mode}"
    return (f"  baseline  not compared across planning_review modes ({mode} vs {earlier}); {reason}; the last row for this "
            f"driver is {str(last.get('date'))[:10]}, ShipLoop {last.get('shiploop_version')}" + (f"; it {why}" if why else ""))


def row_reached_done(row: dict) -> bool:
    """False when a row's own record says ShipLoop did not reach done: its ``shiploop`` verdict is false, or its engine
    status is anything but done. A row that says neither (written before the verdicts or the termination record existed,
    or by a test) is not refused: unknown is not excluded. A finished run whose product failed a check is still done."""
    if (row.get("verdicts") or {}).get("shiploop") is False:
        return False
    status = (row.get("termination") or {}).get("engine_status")
    return status is None or status == "done"


def _prompt_differs(case: str, prompt_sha256: str | None, row: dict) -> bool:
    """Whether the prompt key excludes a row. For the ``custom`` case (a prompt given on the command line) the key always
    applies: a row compares only if both it and the run carry a hash and the hashes are equal, because two unknown
    prompts are not known to be one. For a named case the prompt is the case's own, so the key applies only when the run
    and the row both carry a hash: a row written before the field existed keeps comparing."""
    theirs = row.get("prompt_sha256")
    if case == "custom":
        return prompt_sha256 is None or theirs != prompt_sha256
    return prompt_sha256 is not None and theirs is not None and theirs != prompt_sha256


def _source_name(text) -> str | None:
    """'marketplace (resumed on its original install)' is a marketplace run: the part before the note."""
    return text.split(" (")[0] if isinstance(text, str) else text


def row_matches(row: dict, case: str, source: str | None, host: str | None = None, model: str | None = None,
                effort: str | None = None, planning_review: str | None = None,
                prompt_sha256: str | None = None) -> str | None:
    """None when ``row`` is a basis for a run with this key, else why not, in words (the keys of ``matching_rows``' counter).

    The one predicate (S-12) behind ``matching_rows``, ``scan_baseline``, ``previous_row`` and ``--baseline-report``. SPEC: a
    baseline compares only with rows from the same host, model and effort, so a row that does not name all three, or names
    different ones, is no basis, and rows written before those fields existed are therefore not compared against. The source
    is compared by its name, not by the note a resume adds. With ``planning_review`` (this run's mode) a row that stands for
    another mode (``row_planning_review``) is no basis either; a run that records no mode matches no row. The prompt key is
    ``_prompt_differs``. A row that did not reach done is a record and not a basis (``row_reached_done``).
    """
    if row.get("case") != case or _source_name(row.get("source")) != _source_name(source):
        return "another case or source"
    if (row.get("host"), row.get("model"), row.get("effort")) != (host, model, effort):
        return "another host, model or effort"
    if planning_review is not None and (planning_review == metrics.NOT_RECORDED
                                        or row_planning_review(row)[0] != planning_review):
        return "another planning_review mode"
    if _prompt_differs(case, prompt_sha256, row):
        return "another prompt"
    if not row_reached_done(row):
        return "did not reach done"
    return None


def matching_rows(path: Path, case: str, source: str | None, host: str | None = None, model: str | None = None,
                  effort: str | None = None, planning_review: str | None = None,
                  prompt_sha256: str | None = None) -> tuple[list[dict], int, Counter]:
    """(the rows this run may be compared with, in file order; how many rows the case and source have; why each other was
    skipped), by ``row_matches``."""
    skipped: Counter = Counter()
    if not path.is_file():
        return [], 0, skipped
    rows, seen = [], 0
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        reason = row_matches(row, case, source, host, model, effort, planning_review, prompt_sha256)
        if reason == "another case or source":
            continue
        seen += 1
        if reason:
            skipped[reason] += 1
        else:
            rows.append(row)
    return rows, seen, skipped


def scan_baseline(path: Path, case: str, source: str | None, host: str | None = None,
                  model: str | None = None, effort: str | None = None,
                  planning_review: str | None = None, prompt_sha256: str | None = None) -> tuple[dict | None, int]:
    """(the last comparable row, how many rows were recorded for this case and source), by ``matching_rows``.

    The count lets a caller say "rows exist but none is comparable" instead of printing nothing.
    """
    rows, seen, _ = matching_rows(path, case, source, host, model, effort, planning_review, prompt_sha256)
    return (rows[-1] if rows else None), seen


def previous_row(path: Path, case: str, source: str | None, host: str | None = None,
                 model: str | None = None, effort: str | None = None, prompt_sha256: str | None = None) -> dict | None:
    """The last recorded row for this case that is actually comparable with this run, whatever its planning_review mode."""
    return scan_baseline(path, case, source, host, model, effort, None, prompt_sha256)[0]


def row_lower_bound(row: dict) -> bool | None:
    """Whether a baseline row's cost and turns cover only the sessions that reported. A row from build step 8 on says so
    itself (``lower_bound``, from metrics.lower_bound). A row whose metrics could not tell (null) or an older row carries no count
    (it is not a baseline key), so: True when the row lists ``unreported_sessions`` among its unmeasured counters (Grok's
    events cannot show a session that never reported), and True for any Grok row (the rows from before that listing were
    written the same way); None otherwise, which is unknown and is not marked."""
    if row.get("lower_bound") is not None:
        return row["lower_bound"]
    if "unreported_sessions" in (row.get("unmeasured") or []) or row.get("host") == "grok":
        return True
    return None


def marked(figure, bound: bool | None) -> str:
    """A printed figure, with '(lower bound)' after it where it is one."""
    return f"{figure} (lower bound)" if bound else str(figure)


def sample_line(row: dict, before: dict, cell: list[dict]) -> str:
    """The facts a comparison rests on, as a line: no claim that the run is within, above or below anything (SPEC, "A
    comparison names its sample"). Whether the plugin tree is the one the earlier row ran on, how the host build changed, and
    how many earlier rows the cell has on how many builds; a fact one side does not record is said to be unknown, not
    guessed."""
    def pair(was, now, same: str, differs: str, label: str) -> str:
        if was is None or now is None:
            return f"{label} unknown ({'this run' if now is None else 'the earlier row'} records none)"
        return same.format(now) if was == now else differs.format(was, now)

    trees = pair(before.get("plugin_sha256"), row.get("plugin_sha256"), "plugin tree same ({})",
                 "plugin tree different ({} -> {})", "plugin tree")
    label = "Claude Code build" if row.get("host") == "claude" else f"{row.get('host')} build"
    builds = pair(before.get("host_build"), row.get("host_build"), label + " {} (same)", label + " {} -> {}", label)
    recorded = {r["plugin_sha256"] for r in cell if r.get("plugin_sha256")}
    unrecorded = sum(1 for r in cell if not r.get("plugin_sha256"))
    rows = (f"{len(cell)} earlier row(s) in this cell on {len(recorded)} recorded build(s)"
            + (f", {unrecorded} with no recorded tree" if unrecorded else ""))
    return f"{trees}; {builds}; {rows}"


# ------------------------------------------------------------------------------- run.py --baseline-report
#
# Read-only. It unions the baseline file with the run folders (by the run's recorded output path) and says, per cell, how
# many attempts there were, which of them count, on how many builds, and the n, min, median and max of what they cost. It
# states facts: no run is placed within or outside a range (SPEC, "A comparison names its sample"). It writes nothing and
# starts no host or CLI: a build a run did not record stays null, because today's CLI is not the one that ran. Whether a
# row is a basis for a run is decided by ``row_matches``, the predicate the live line uses.

# The class of each attempt; exactly one applies, the first that does, in this order.
ATTEMPT_COUNTS = {"counted": "counted", "did not reach done": "did_not_reach_done", "mixed host": "mixed_host",
                  "resumed": "resumed", "seeded": "seeded", "ended by the harness": "ended_by_harness",
                  "process not observed": "process_not_observed", "no driver recorded": "no_driver_recorded",
                  "no result.json": "no_result"}
# What a folder can supply for a row that lacks it: the cell fields and the identity fields.
SUPPLIED_FIELDS = ("source", "host", "model", "effort", "planning_review", *IDENTITY_FIELDS)
REPORT_NOTES = (
    "n, min, median and max describe the rows counted; a range across builds is not a noise estimate, and no run is placed "
    "against it.",
    "A figure marked as a lower bound covers only the sessions that reported; Grok's events cannot show a session that "
    "never did, so every Grok cost and turns figure is marked.",
    "Overlap is a count of rows whose recorded span crossed another recorded span. It misses a run that left no record "
    "and a row with no span, and it can include a resumed run's pause (a span runs from the first to the last stamp).",
    "Where a baseline row and a run folder both describe a run, the row wins wherever it has a value; the folder fills "
    "only what the row lacks, and every field it supplied is listed in `recomputed`. A build a run did not record "
    "stays null, with its reason in `identity_unmeasured`.",
)
SKIPPED_DIRECTORIES = ("node_modules", "__pycache__")


def _json_file(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _inside(folder: Path, recorded_output: str | None, recorded) -> Path | None:
    """A path a run recorded, found under its folder as the folder lies now: a copied or moved run folder keeps the
    absolute paths it was made with. None for a path outside the run's own folder: what lies there now is not what the run
    used, so nothing is derived from it."""
    if not isinstance(recorded, str) or not isinstance(recorded_output, str) or not recorded_output:
        return None
    if recorded == recorded_output or recorded.startswith(recorded_output + "/"):
        return folder / recorded[len(recorded_output):].lstrip("/")
    return None


def is_run_folder(path: Path) -> bool:
    """A folder in the harness's own record shape: an ``invocation.json`` naming a case and a host, or a ``result.json``
    naming a case, a host and an output. The audit harness's trial folders have neither."""
    first = _json_file(path / "invocation.json")
    if first is not None and isinstance(first.get("case"), str) and isinstance(first.get("host"), str):
        return True
    result = _json_file(path / "result.json")
    return (result is not None and isinstance(result.get("case"), str) and isinstance(result.get("host"), str)
            and isinstance(result.get("output"), str))


def run_folders(roots: list[Path]) -> tuple[list[Path], list[str]]:
    """(the run folders at any depth under each root, the walk stopping at a run folder; a note for each root with none or
    that does not exist). Resolved and de-duplicated, so the result does not depend on how a root is spelled."""
    found: dict[str, Path] = {}
    notes: list[str] = []
    for root in roots:
        root = Path(root).expanduser()
        if not root.is_dir():
            notes.append(f"the --runs directory {root} does not exist")
            continue
        before = len(found)
        for here, folders, _names in os.walk(root):
            if is_run_folder(Path(here)):
                found.setdefault(str(Path(here).resolve()), Path(here).resolve())
                folders[:] = []
            else:
                folders[:] = sorted(f for f in folders if not f.startswith(".") and f not in SKIPPED_DIRECTORIES)
        if len(found) == before:
            notes.append(f"no run folder was found under {root}")
    return [found[key] for key in sorted(found)], notes


def folder_record(folder: Path, cases: dict) -> dict:
    """What a run folder says about its run: the row its result stands for, the fields the report supplied from the folder's
    other files (and why it could not supply the others), and the facts that decide whether the run counts. Nothing here
    starts a process."""
    result = _json_file(folder / "result.json")
    first = _json_file(folder / "invocation.json") or {}
    launches = runrecord.launches(folder)
    first_launch = launches[0][1] if launches else {}
    saved = _json_file(folder / "metrics.json") or {}
    identity = first if result is None else result
    if result is not None and not isinstance(result.get("output"), str):
        raise ValueError("result.json has no output path")
    recorded = (result or {}).get("output") or str(folder)
    run_dir = _inside(folder, (result or {}).get("output"), ((result or {}).get("shiploop") or {}).get("run_dir"))
    name = identity.get("case")
    style = None if name == "custom" else (cases.get(name) or {}).get("style")
    stand_in = result if result is not None else {"case": name, "host": identity.get("host"), "model": identity.get("model"),
                                                  "effort": identity.get("effort"), "versions": identity.get("versions"),
                                                  "output": recorded, "metrics": {}}
    state = metrics.engine_state(run_dir) if run_dir else {}
    row = baseline_row(stand_in, style, None, metrics.planning_review(state))
    if state.get("planning_review") is None:
        row["planning_review"] = None  # no mode recorded: ``row_planning_review`` reads it from the plugin version, as for a row
    row["source"] = _source_name((first.get("versions") or {}).get("source") or row.get("source"))
    filled: list[str] = []
    why_not: dict[str, str] = {}

    def fill(key: str, value, why: str | None = None) -> None:
        if row.get(key) is not None:
            return
        if value is not None:
            row[key] = value
            filled.append(key)
        elif why:
            why_not[key] = why

    plugin_dir = _inside(folder, (result or {}).get("output"), first.get("plugin_dir"))
    if row.get("plugin_sha256") is None:
        digest, why = tree_digest_checked(plugin_dir) if plugin_dir else (None, "the plugin build is not inside the run folder")
        fill("plugin_sha256", digest, why)
    try:
        fill("prompt_sha256", masked_prompt_digest(case_prompt((folder / "prompt.txt").read_text(), first.get("improve_skill")),
                                                   Path(recorded)))
    except OSError:
        why_not["prompt_sha256"] = "no prompt.txt in the folder"
    if row.get("host") == "claude":
        build = (((result or {}).get("metrics") or {}).get("claude_code_version") or saved.get("claude_code_version")
                 or metrics.claude_builds(folder / "events.jsonl"))
        fill("host_build", build, "the init events name no Claude Code build")
    else:  # the build the FIRST launch recorded; a run launched before the field existed has none, and none is not asked for now
        fill("host_build", *runrecord.host_build(first_launch))
    span = metrics.span(folder / "timeline.jsonl")
    fill("started", span["started"], "no timeline.jsonl stamps")
    fill("ended", span["ended"], "no timeline.jsonl stamps")
    fill("planning_seconds", metrics.planning_seconds(saved.get("planning")),
         metrics.planning_unmeasured(saved.get("planning")) if saved else "no metrics.json in the folder")
    unreadable = result is None and (folder / "result.json").is_file()
    return {"row": row, "filled": filled, "why_not": why_not, "result_reasons": (result or {}).get("identity_unmeasured") or {},
            "folder": folder, "has_result": result is not None, "unreadable": unreadable,
            "hosts_used": runrecord.hosts_used(folder), "mixed_host": runrecord.mixed_host(folder),
            "launches": len(launches), "seeded": bool((result or {}).get("seeded")),
            "earlier": len((result or {}).get("earlier_terminations") or []),
            "process_status": ((result or {}).get("process") or {}).get("status"),
            "termination": (result or {}).get("termination") or {},
            "lower_bound": metrics.lower_bound((result or {}).get("metrics") or {})}


def classify_attempt(row: dict, folder: dict | None) -> tuple[str, str | None]:
    """(the class of an attempt, why it is not counted). The first that applies: a run nobody recorded the end of, seeded,
    worked on by two hosts, really resumed (a regrade is not a resume: it started no host), ended by the harness (the live
    path writes it no row), its host never observed, not done, or with no driver named."""
    if folder is not None:
        if not folder["has_result"]:
            return "no result.json", ("result.json is unreadable" if folder["unreadable"] else
                                      "the folder holds launch records and no result.json: its harness died before writing "
                                      "the records, or the run is still going")
        if folder["seeded"]:
            return "seeded", "seeded at a later stage: it did not start from intake"
        if folder["mixed_host"]:
            return "mixed host", f"launched by {' and '.join(folder['hosts_used'])}: it belongs to no host's cell"
        if folder["earlier"] or folder["launches"] > 1:
            return "resumed", (f"resumed ({folder['launches']} launch(es), {folder['earlier']} earlier termination(s)): "
                               "a fragment of a run is not a baseline")
        if folder["process_status"] in ("timeout", "stopped") or folder["termination"].get("engine_status") == "active":
            return "ended by the harness", ("its host was killed by a deadline or a stop, or its engine is still active: the "
                                            "live path wrote no row for it")
        if folder["process_status"] == "not observed":
            return "process not observed", "no host ran in this record and none was recorded: nothing says it ended"
    if not row_reached_done(row):
        status = (row.get("termination") or {}).get("engine_status") or (
            "blocked" if (row.get("verdicts") or {}).get("shiploop") is False else "unknown")
        return "did not reach done", f"engine {status}: its turns, cost and stages stop there"
    if row.get("host") is None and row.get("model") is None and row.get("effort") is None:
        return "no driver recorded", "the row names no host, model or effort, so no run is compared with it"
    return "counted", None


def _stats(values: list, digits: int) -> dict:
    """n, min, median and max of the measured values; None for each when there is none."""
    got = sorted(v for v in values if v is not None)
    if not got:
        return {"n": 0, "min": None, "median": None, "max": None}
    middle = statistics.median(got)
    return {"n": len(got), "min": round(got[0], digits), "median": round(middle, digits), "max": round(got[-1], digits)}


def span_overlaps(spans: list[tuple[float | None, float | None]]) -> list[int | None]:
    """For each (started, ended) span, how many of the others it crosses (touching spans do not cross); None for a span with
    an end unknown. The interval rule is metrics.spans_overlap, which environment.overlap asks too."""
    counts: list[int | None] = []
    for index, (start, end) in enumerate(spans):
        if start is None or end is None:
            counts.append(None)
            continue
        counts.append(sum(1 for other, pair in enumerate(spans)
                          if other != index and metrics.spans_overlap((start, end), pair)))
    return counts


def assign_cells(records: list[dict]) -> dict[tuple, list[dict]]:
    """Group records into cells: the live key (case, source, host, model, effort, planning_review mode) plus the prompt. A
    record with a hash goes to the cell of that hash. One with none goes to the only cell of its driver when there is one
    prompt (the live rule matches it with any prompt of a named case), and to a cell of its own when the driver has
    several, or when the case is ``custom`` (the live rule matches it with none)."""
    def base(r: dict) -> tuple:
        return tuple(r[k] for k in ("case", "source", "host", "model", "effort", "planning_review"))

    hashes: dict[tuple, set] = {}
    for r in records:
        if r["prompt_sha256"]:
            hashes.setdefault(base(r), set()).add(r["prompt_sha256"])
    groups: dict[tuple, list[dict]] = {}
    for r in records:
        found = hashes.get(base(r), set())
        prompt = r["prompt_sha256"] or (next(iter(found)) if r["case"] != "custom" and len(found) == 1 else None)
        groups.setdefault((*base(r), prompt), []).append(r)
    return groups


def _public_record(key: str, entry: dict) -> dict:
    """One attempt, merged from the baseline row and the folder: the row wins wherever it has a value."""
    file_row, found = entry.get("file"), entry.get("folder")
    row = dict(found["row"]) if found else {}
    if file_row:
        row.update({k: v for k, v in file_row.items() if v is not None and k != "identity_unmeasured"})
        row["source"] = _source_name(row.get("source"))
    if found and file_row:
        derived = sorted(k for k in SUPPLIED_FIELDS if file_row.get(k) is None and row.get(k) is not None)
    else:
        derived = sorted(found["filled"]) if found else []
    klass, why = classify_attempt(row, found)
    started, ended, planning = row.get("started"), row.get("ended"), row.get("planning_seconds")
    for name, value in (("started", started), ("ended", ended), ("planning_seconds", planning), ("cost_usd", row.get("cost_usd")),
                        ("turns", row.get("turns"))):
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise TypeError(f"{name} is {value!r}, not a number")
    file_reasons = (file_row or {}).get("identity_unmeasured") or {}
    reasons = {}
    for name in IDENTITY_FIELDS:
        if row.get(name) is None:
            reasons[name] = (file_reasons.get(name) or (found or {}).get("result_reasons", {}).get(name)
                             or (found or {}).get("why_not", {}).get(name)
                             or (row.get("identity_unmeasured") or {}).get(name) or "not recorded")
    bound = found["lower_bound"] if found and found["lower_bound"] is not None else row_lower_bound(row)
    return {
        "output": row.get("output") or key, "record": "file+folder" if file_row and found else "folder" if found else "file",
        "case": row.get("case"), "source": row.get("source"), "host": row.get("host"), "model": row.get("model"),
        "effort": row.get("effort"), "planning_review": row_planning_review(row)[0],
        "prompt_sha256": row.get("prompt_sha256"), "plugin_version": row.get("plugin_version"),
        "plugin_sha256": row.get("plugin_sha256"), "host_build": row.get("host_build"), "local_head": row.get("local_head"),
        "started": started, "ended": ended,
        "minutes": round((ended - started) / 60, 1) if started is not None and ended is not None else None,
        "planning_seconds": planning, "planning_minutes": round(planning / 60, 2) if planning is not None else None,
        "cost_usd": row.get("cost_usd"), "turns": row.get("turns"),
        "lower_bound": bound,
        "pass": row.get("pass"),
        "engine_status": (found["termination"].get("engine_status") if found and found["termination"] else None)
        or (row.get("termination") or {}).get("engine_status"),
        "process_status": (found["process_status"] if found else None) or (row.get("termination") or {}).get("process_status"),
        "hosts_used": found["hosts_used"] if found else None, "class": klass, "why": why, "recomputed": derived,
        "identity_unmeasured": reasons, "overlaps": None}


def _unreadable_record(key: str, entry: dict, error: Exception) -> dict:
    row = entry.get("file") if isinstance(entry.get("file"), dict) else {}
    output = key if not isinstance(row.get("output"), str) else row["output"]
    blank = {name: None for name in ("case", "source", "host", "model", "effort", "prompt_sha256", "plugin_version",
                                     "plugin_sha256", "host_build", "local_head", "started", "ended", "minutes",
                                     "planning_seconds", "planning_minutes", "cost_usd", "turns", "lower_bound", "pass",
                                     "engine_status", "process_status", "hosts_used", "overlaps")}
    return {"output": output, "record": "file+folder" if entry.get("file") and entry.get("folder") else
            "folder" if entry.get("folder") else "file", **blank, "planning_review": None,
            "class": "unreadable record", "why": f"{type(error).__name__}: {error}", "recomputed": [],
            "identity_unmeasured": {}}


def baseline_report(baseline: Path | None, runs: list[Path]) -> dict:
    """The report: every attempt once (a baseline row and a run folder that describe the same run are one record, keyed by
    the run's recorded output path), its class, and per cell the attempts, builds, measures and overlap. A record that
    cannot be read is an 'unreadable record' with the exception text, and never stops the report."""
    cases = json.loads(CASES.read_text())
    notes: list[str] = []
    entries: dict[str, dict] = {}
    if baseline is not None:
        if not baseline.is_file():
            notes.append(f"the baseline file {baseline} does not exist")
        else:
            for number, line in enumerate(baseline.read_text().splitlines()):
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    output = row.get("output")
                    entries[os.path.normpath(output if isinstance(output, str) and output else f"<row {number}>")] = {"file": row}
    folders, folder_notes = run_folders(runs)
    notes += folder_notes
    for folder in folders:
        try:
            found = folder_record(folder, cases)
            key = os.path.normpath(found["row"].get("output") or str(folder))
            entries.setdefault(key, {})["folder"] = found
        except Exception as error:  # one bad record is one unreadable record
            entries.setdefault(os.path.normpath(str(folder)), {})["error"] = error
    records = []
    for key, entry in entries.items():
        try:
            if "error" in entry:
                raise entry["error"]
            records.append(_public_record(key, entry))
        except Exception as error:
            records.append(_unreadable_record(key, entry, error))
    readable = [r for r in records if r["class"] != "unreadable record"]
    for record, count in zip(readable, span_overlaps([(r["started"], r["ended"]) for r in readable])):
        record["overlaps"] = count
    records.sort(key=lambda r: (r["started"] is None, r["started"] or 0.0, str(r["output"])))
    cells = []
    groups = assign_cells([r for r in records if r["class"] != "unreadable record"])
    for key in sorted(groups, key=lambda k: tuple("" if part is None else str(part) for part in k)):
        members = groups[key]
        counted = [r for r in members if r["class"] == "counted"]
        attempts = {"seen": len(members), "counted": len(counted), "passed": sum(1 for r in counted if r["pass"] is True),
                    **{ATTEMPT_COUNTS[c]: sum(1 for r in members if r["class"] == c) for c in ATTEMPT_COUNTS if c != "counted"}}
        trees = Counter(r["plugin_sha256"] for r in counted if r["plugin_sha256"])
        hosts_seen = Counter(r["host_build"] for r in counted if r["host_build"])
        measures = {}
        for name, field, digits in (("cost_usd", "cost_usd", 4), ("turns", "turns", 0), ("minutes", "minutes", 1),
                                    ("planning_minutes", "planning_minutes", 2)):
            values = [r[field] for r in counted]
            stat = _stats(values, digits)
            if name == "turns":
                stat = {k: (int(v) if isinstance(v, float) and v == int(v) else v) for k, v in stat.items()}
            stat["not_measured"] = sum(1 for v in values if v is None)
            if name in ("cost_usd", "turns"):
                stat["lower_bound_rows"] = sum(1 for r in counted if r[field] is not None and r["lower_bound"] is True)
                stat["lower_bound_unknown_rows"] = sum(1 for r in counted if r[field] is not None and r["lower_bound"] is None)
            if name == "minutes":  # a wall-time range is read beside how many of its rows overlapped
                stat["overlapped_by_span"] = sum(1 for r in counted if r["minutes"] is not None and r["overlaps"])
                stat["not_seen_overlapping"] = sum(1 for r in counted if r["minutes"] is not None and r["overlaps"] == 0)
            measures[name] = stat
        cells.append({
            "cell": dict(zip(("case", "source", "host", "model", "effort", "planning_review", "prompt_sha256"), key)),
            "attempts": attempts,
            "builds": {"plugin_sha256": dict(sorted(trees.items())),
                       "unrecorded": sum(1 for r in counted if not r["plugin_sha256"])},
            "host_builds": {**dict(sorted(hosts_seen.items())), "unrecorded": sum(1 for r in counted if not r["host_build"])},
            "measures": measures,
            "overlap": {"rows": len(counted), "overlapped_by_span": sum(1 for r in counted if r["overlaps"]),
                        "not_seen_overlapping": sum(1 for r in counted if r["overlaps"] == 0),
                        "unknown": sum(1 for r in counted if r["overlaps"] is None)},
            "outputs": {c: [Path(str(r["output"])).name for r in members if r["class"] == c]
                        for c in ATTEMPT_COUNTS if any(r["class"] == c for r in members)}})
    return {"inputs": {"baseline": str(baseline) if baseline else None, "runs": [str(r) for r in runs]},
            "records": records, "cells": cells, "notes": [*notes, *REPORT_NOTES]}


def render_report(report: dict) -> str:
    """The report as text: one block per cell, then the notes."""
    records = report["records"]
    kinds = Counter(r["record"] for r in records)
    unreadable = [r for r in records if r["class"] == "unreadable record"]
    lines = [f"baseline report: {len(records)} record(s) ({kinds['file+folder']} in the file and a folder, {kinds['folder']} in "
             f"a folder only, {kinds['file']} in the file only; {len(unreadable)} unreadable) in {len(report['cells'])} cell(s)"]
    for cell in report["cells"]:
        c = cell["cell"]
        lines += ["", "cell " + " | ".join([str(c["case"]), str(c["source"]), c["host"] or "host not recorded",
                                            c["model"] or "model not recorded", f"effort {c['effort'] or '-'}",
                                            f"planning_review {c['planning_review']}",
                                            f"prompt {c['prompt_sha256'] or 'not recorded'}"])]
        a = cell["attempts"]
        extra = "".join(f", {label} {a[key]}" for label, key in (
            ("did not reach done", "did_not_reach_done"), ("mixed host", "mixed_host"), ("resumed", "resumed"),
            ("seeded", "seeded"), ("ended by the harness", "ended_by_harness"),
            ("process not observed", "process_not_observed"),
            ("no driver recorded", "no_driver_recorded"), ("no result.json", "no_result")) if a[key])
        lines.append(f"  attempts   seen {a['seen']}, counted {a['counted']}, passed {a['passed']}{extra}")
        trees = cell["builds"]["plugin_sha256"]
        lines.append(f"  builds     {len(trees)} plugin tree(s)" + (f" ({', '.join(str(n) for n in trees.values())} row(s) each)"
                     if trees else "") + f", {cell['builds']['unrecorded']} row(s) with no recorded tree")
        lines.append("  host build " + (", ".join(f"{b} x{n}" for b, n in cell["host_builds"].items() if b != "unrecorded")
                                        or "none recorded") + f"; {cell['host_builds']['unrecorded']} unrecorded")
        for name, label in (("cost_usd", "cost_usd  "), ("turns", "turns     "), ("minutes", "minutes   "),
                            ("planning_minutes", "planning  ")):
            m = cell["measures"][name]
            if not m["n"]:
                lines.append(f"  {label} n=0 ({m['not_measured']} not measured)")
                continue
            note = ""
            if "lower_bound_rows" in m and (m["lower_bound_rows"] or m["lower_bound_unknown_rows"]):
                note = (f" (lower bound in {m['lower_bound_rows']} of {m['n']} rows"
                        + (f", unknown in {m['lower_bound_unknown_rows']}" if m["lower_bound_unknown_rows"] else "") + ")")
            if name == "minutes":
                note = f" ({m['overlapped_by_span']} of {m['n']} overlapped)"
            lines.append(f"  {label} n={m['n']} min {m['min']} median {m['median']} max {m['max']}{note}"
                         + (f"; {m['not_measured']} not measured" if m["not_measured"] else ""))
        o = cell["overlap"]
        lines.append(f"  overlap    {o['overlapped_by_span']} of {o['rows']} rows overlapped another recorded span; "
                     f"{o['not_seen_overlapping']} not seen to"
                     + (f"; {o['unknown']} row(s) record no span" if o["unknown"] else ""))
        for klass, names in cell["outputs"].items():
            if klass != "counted":
                lines.append(f"  {klass}: {', '.join(names)}")
    if unreadable:
        lines += ["", *(f"unreadable record: {Path(str(r['output'])).name}: {r['why']}" for r in unreadable)]
    lines += ["", *report["notes"]]
    return "\n".join(lines) + "\n"


RELEASE_GATE_CLASSES = ("counted", "no driver recorded")  # a finished run that passed; an old row names no driver
SHIPLOOP_RELEASE = re.compile(r"\bshiploop \d")  # a release commit's subject names each skill it shipped with its version


def release_commits() -> list[tuple[float, str]]:
    """(commit time, subject) of every release commit on origin/main, read from the local ref (nothing is fetched)."""
    lines = git("log", "origin/main", "--grep=^release:", "--format=%ct%x09%s").splitlines()
    return [(float(when), subject) for when, _, subject in (line.partition("\t") for line in lines) if when.isdigit()]


def release_gate(baseline: Path | None, published: dict | None = None,
                 releases: list[tuple[float, str]] | None = None) -> dict:
    """Per style of the case catalog: the last pass a marketplace run recorded in the baseline file, what origin/main publishes
    now, and how many ShipLoop releases origin/main made after that pass (SPEC "Promotion" and "Choose the verification runs
    from a coverage map"). Basis: the 2026-10-24 runner review (D1) found that no case had passed from the marketplace since
    2026-10-10, fourteen releases earlier, and nothing printed it. A record: it gates nothing. ``published`` and ``releases``
    default to the local origin/main ref; a ref that cannot be read is named, and the passes are still listed."""
    cases = json.loads(CASES.read_text())
    styles = sorted({case["style"] for case in cases.values() if case.get("style")})
    rows = []
    if baseline is not None and baseline.is_file():
        for line in baseline.read_text().splitlines():
            with contextlib.suppress(ValueError):
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
    unread = None
    try:
        published = published if published is not None else published_versions()
        releases = releases if releases is not None else release_commits()
    except Exception as exc:  # noqa: BLE001 - the passes are listed whatever the ref says
        published, releases, unread = None, None, " ".join(str(exc).split())[:200] or type(exc).__name__
    by_style = {}
    for style in styles:
        passes = [row for row in rows if row.get("pass") is True and _source_name(row.get("source")) == "marketplace"
                  and (cases.get(row.get("case")) or {}).get("style") == style]
        last = passes[-1] if passes else None  # the file is appended in run order
        if last is None:
            by_style[style] = None
            continue
        when = last.get("ended") if isinstance(last.get("ended"), (int, float)) else None
        if when is None:
            with contextlib.suppress(TypeError, ValueError):
                when = datetime.strptime(str(last.get("date")), "%Y-%m-%dT%H:%M:%S%z").timestamp()
        since = (None if releases is None or when is None
                 else sum(1 for stamp, subject in releases if stamp > when and SHIPLOOP_RELEASE.search(subject)))
        by_style[style] = {"case": last.get("case"), "date": str(last.get("date") or "")[:10] or None,
                           "plugin_version": last.get("plugin_version"), "shiploop_version": last.get("shiploop_version"),
                           "driver": "/".join(str(last.get(k) or "-") for k in ("host", "model", "effort")) if last.get("host") else None,
                           "shiploop_releases_since": since}
    return {"baseline": str(baseline) if baseline else None, "published": published, "unread": unread, "styles": by_style}


def render_release_gate(gate: dict) -> str:
    """The release gate as text: one line per style."""
    published = gate["published"]
    head = (f"origin/main publishes skill-craft {published['catalog_version']} / ShipLoop {published['shiploop_version']}"
            if published else f"origin/main could not be read ({gate['unread']})")
    lines = [f"release gate: {head}; the last marketplace pass per style in {gate['baseline']}"]
    for style, last in gate["styles"].items():
        if last is None:
            lines.append(f"  {style:<17} no marketplace pass recorded")
            continue
        since = last["shiploop_releases_since"]
        lines.append(f"  {style:<17} {last['case']} {last['date']}, skill-craft {last['plugin_version']} / ShipLoop "
                     f"{last['shiploop_version']} ({last['driver'] or 'driver not recorded'}); "
                     + ("ShipLoop releases since not known" if since is None else f"{since} ShipLoop release(s) since"))
    return "\n".join(lines) + "\n"


def baseline_report_main(args) -> int:
    """`--baseline-report`: print the report (JSON with --json), and with --release-gate the last marketplace pass per style.
    Reads files and the local origin/main ref only, and always exits 0."""
    report = baseline_report(args.baseline, args.runs or [])
    gate = release_gate(args.baseline) if args.release_gate else None
    if args.json:
        print(json.dumps({**report, "release_gate": gate} if gate else report, indent=1))
    else:
        print(render_report(report) + ("\n" + render_release_gate(gate) if gate else ""), end="")
    return 0


NOT_OBSERVED = "not observed (regraded: no host ran)"


def regraded_process(observed: dict | None) -> dict:
    """The ``process`` block of a regrade: what the original run observed, or nothing.

    A regrade starts no host, so it claims no exit. The block the original run recorded is kept as it
    was, verdict included (marked ``regraded``), so a host that failed stays failed and the per-session
    list and elapsed time survive. With no record the harness never saw an exit: the block says so and
    its verdict is None, which no verdict list counts and no report calls a pass.
    """
    if isinstance(observed, dict) and observed.get("status"):
        kept = dict(observed, regraded=True)
        kept.setdefault("pass", kept["status"] == "exited")
        return kept
    return {"status": "not observed", "returncode": None, "elapsed_seconds": None, "sessions": [],
            "resumes": None, "pass": None, "regraded": True}


def termination_facts(process: dict, engine: dict, resume_stop: str | None, earlier: dict | None = None) -> dict:
    """Why this run is not still going, from the observer that owns the process.

    ShipLoop cannot answer this: it is not running when its host times out, runs
    out of credits, or is killed, so only the harness around the process can say
    what happened. Every field keeps ``unknown`` rather than a guess, and the
    last ShipLoop refusal is never reported as the cause -- a refusal is a
    rejected callback, not a terminated run.

    ``session_stops`` has one entry per session this invocation launched, in
    launch order, the same population ``sessions`` counts: the host's own reason,
    or ``unknown`` for a session that wrote no terminal event (killed, crashed).
    A resumed invocation describes its own sessions; the ones before it stay in the
    result's ``earlier_terminations``.

    A regrade (``process.regraded``) started no host, so nothing was observed: it
    keeps ``earlier`` (the termination the original run recorded) when there is one,
    and otherwise says no host ran. It never reports an exit that nobody saw.
    """
    pending = metrics.pending_stage(engine)
    reason = engine.get("status_reason")
    engine_facts = {
        "engine_status": engine.get("status") or "unknown",
        # Where the graph stopped: the stage it never accepted, when there is one, else the stage it is in.
        "engine_stage": metrics.current_stage(engine) or "unknown",
        "engine_unaccepted_stage": pending,
        # The engine's own recorded cause for a blocked, paused or halted run.
        "engine_status_reason": " ".join(reason.split())[:200] if isinstance(reason, str) and reason.strip() else None,
        # What the engine accepted when it blocked (null where it did not block, or recorded no blocked result).
        **{f"engine_{key}": value for key, value in metrics.blocked_detail(engine).items()},
    }
    if process.get("regraded"):
        if isinstance(earlier, dict) and earlier.get("process_status"):
            # The ending stays the one the original run recorded; the engine is read again, so the class can name what it is now.
            return {**earlier, "regraded": True, "engine_status_at_regrade": engine_facts["engine_status"],
                    **{f"{key}_at_regrade": engine_facts[key] for key in (
                        "engine_stage", "engine_status_reason", "engine_blocked_by", "engine_awaiting_kind",
                        "engine_awaiting_no_default")}}
        return {"process_status": NOT_OBSERVED, "returncode": None, "sessions": 0, "resumes": None,
                "session_stops": [], "resume_stop": "not evaluated (regraded)", **engine_facts, "regraded": True}
    sessions = process.get("sessions") or []
    return {
        "process_status": process.get("status") or "unknown",
        "returncode": process.get("returncode"),
        "sessions": len(sessions),
        "resumes": process.get("resumes"),
        "session_stops": [(s.get("stop") if isinstance(s, dict) else None) or "unknown" for s in sessions],
        "resume_stop": resume_stop or "unknown",
        **engine_facts,
    }


# How the run ended, as one word (SPEC: outcome_class is a record and not a verdict; it changes neither pass nor the exit code).
OUTCOME_CLASSES = ("PASS", "FAILED", "BLOCKED", "STOPPED")

# The wordings of `termination.resume_stop` the harness itself writes when the engine's own status is not the reason the
# resume loop ended, with the class each means (prefixes: some carry a number or a path). "ShipLoop run is <status>" and "not
# evaluated (regraded)" are decided by the engine's status. A new wording must be added here: a test reads this file's source
# for every `resume_stop` and fails on one that is not, so an unlisted ending is never silently called FAILED.
RESUME_STOP_CLASSES = (
    ("host is not resumable", "FAILED"),
    ("no host session id to resume", "FAILED"),
    ("run deadline spent", "STOPPED"),
    ("resume budget spent", "STOPPED"),
    ("resumed host failed ", "FAILED"),
    ("resumed host made no ShipLoop progress ", "STOPPED"),
    ("stopped by ", "STOPPED"),
    ("terminated by ", "STOPPED"),
)


# A host session's recorded stop (`metrics.session_stop`) that names a limit the harness gave the host: Claude's `error_max_turns` and
# `error_max_budget_usd` (--max-turns, --max-budget-usd) and Grok's `{"kind": "max_turns"}`. Codex has neither limit. The harness ending the
# session on its own cap is the harness ending the run (STOPPED), not the host's own failure, whether or not the host can be resumed.
CAP_STOPS = ("max_turns", "max_budget_usd")


def _head(text, size: int = 100) -> str:
    return " ".join(str(text).split())[:size]


def outcome_class(passed: bool, t: dict) -> tuple[str | None, str]:
    """(class, basis): how a run ended, a pure function of ``pass`` and the termination block (SPEC S-14).

    PASS: every verdict passed. BLOCKED: the engine accepted a blocked result, or is paused (it awaits resume the same way);
    the class says what the engine recorded and never that the block was warranted, which is a model judgement S-9 excludes
    as evidence. FAILED: the engine finished or halted without passing, or the host ended on its own with the engine
    unfinished. STOPPED: the harness ended the run (a requested stop, a signal, the deadline, a spent resume budget, or a host
    session that ended on the cap the harness gave it: ``CAP_STOPS``). None:
    unknown, and the basis says why (a regrade that observed no host, or an ending this function does not know). The engine's
    status wins over how the host ended: a stop requested after the engine blocked does not turn the block into a stop.
    A regrade that kept the original ending reads the engine as it is now (the ``*_at_regrade`` fields) and the ending as it
    was recorded.
    """
    if passed:
        return "PASS", "every verdict passed"
    regraded = "engine_status_at_regrade" in t

    def now(key: str):
        return t.get(f"{key}_at_regrade") if regraded else t.get(key)

    engine = now("engine_status") or "unknown"
    stage = now("engine_stage") or "unknown"
    reason = now("engine_status_reason")
    why = f" ({_head(reason)})" if reason else ""
    if engine == "paused":
        return "BLOCKED", f"engine paused at {stage}{why}: it awaits resume; no blocked result names who can unblock it"
    if engine == "blocked":
        by, kind, no_default = now("engine_blocked_by"), now("engine_awaiting_kind"), now("engine_awaiting_no_default")
        if by is None and kind is None:
            return "BLOCKED", f"engine blocked at {stage}{why}; no blocked result was read from the state (an old state, or none accepted)"
        # A current blocked result names what it awaits (answer or present: a person; service: an outside service) and has no
        # blocked_by; a run recorded before the four outcomes (run-insights plan N5) names who can unblock it as `by`, user,
        # access or external, and usually the wait beside it.
        who = "an outside service" if kind == "service" else "a person"
        wait = ("" if kind is None else
                f"; awaits {who} ({kind}), " + ("and states why no default would do" if no_default else "and gives no reason that no default would do"))
        return "BLOCKED", f"engine blocked at {stage}" + (f" by {by}" if by is not None else "") + wait
    if engine == "halted":
        return "FAILED", f"engine halted at {stage}{why}"
    if engine == "done":
        return "FAILED", "engine done; at least one verdict failed"
    process, stop = t.get("process_status"), t.get("resume_stop") or ""
    if process in ("stopped", "timeout"):
        return "STOPPED", f"host {process} with the engine {engine}" + (f" at {stage}" if stage != "unknown" else "") + f"; {_head(stop)}"
    stops = t.get("session_stops")
    last_stop = str(stops[-1]) if isinstance(stops, list) and stops else ""
    if any(cap in last_stop for cap in CAP_STOPS):
        return "STOPPED", (f"engine {engine}" + (f" at {stage}" if stage != "unknown" else "")
                           + f"; the host session ended on the cap the harness gave it ({_head(last_stop)})")
    for prefix, cls in RESUME_STOP_CLASSES:
        if stop.startswith(prefix):
            return cls, f"engine {engine}" + (f" at {stage}" if stage != "unknown" else "") + f"; {_head(stop)}"
    if stop.startswith("not evaluated"):
        return None, f"no host ran (regraded) and the engine is {engine}: the end of the run was not observed"
    return None, f"engine {engine}; the ending {_head(stop)!r} has no class"


def stopped_line(t: dict) -> str:
    """The printed answer to why the run is not still going."""
    if t["process_status"] == NOT_OBSERVED:
        line = f"no host ran (regraded); engine {t['engine_status']}"
    else:
        line = (f"host {t['process_status']} rc={t['returncode']}; "
                f"session stops {', '.join(str(s) for s in t['session_stops']) or 'none'}; "
                f"no further resume: {t['resume_stop']}; engine {t['engine_status']}")
    if t["engine_unaccepted_stage"]:
        line += f" with {t['engine_unaccepted_stage']} never accepted"
    elif t["engine_status"] in ("blocked", "paused", "halted") and t["engine_stage"] != "unknown":
        line += f" at {t['engine_stage']}"  # the engine recorded that stage's own result: nothing was lost
    if t.get("engine_status_reason"):
        line += f" ({t['engine_status_reason'][:100]})"
    if t.get("regraded") and t["process_status"] != NOT_OBSERVED:
        line += f"; the original record, regraded with engine {t.get('engine_status_at_regrade')}"
    return line


def _minutes(seconds: float) -> str:
    return f"{seconds / 60:.0f}" if seconds >= 600 else f"{seconds / 60:.1f}"


def stage_diff_lines(before: list | None, now: list | None, top: int = 5) -> list[str]:
    """Where a whole-run difference actually landed, by stage.

    Compares whole, measured stage rows only. A row the run stopped in
    (``incomplete``) or that has no measured timing is never counted as a visit, so a
    stage with any such row on either side is not comparable: it is named and counted
    in the coverage line, which covers both runs. Stages are summed per name because
    a stage can be visited more than once (one `implement` action per planned step).
    Turns rank the differences where both runs report them; a host that reports no
    per-stage turns is compared by minutes, and the line says so. Stage turns are good
    to about one per boundary and minutes are wall clock, interruption gaps included
    (see metrics.per_stage). This prints; it gates nothing, because no threshold is
    calibrated yet.
    """
    def sides(rows: list | None) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            seen = out.setdefault(row.get("stage") or "?", {"turns": 0, "seconds": 0.0, "whole": True,
                                                              "has_turns": True})
            if row.get("incomplete") or row.get("seconds") is None:
                seen["whole"] = False
                continue
            seen["seconds"] += row["seconds"]
            if row.get("turns") is None:
                seen["has_turns"] = False
            else:
                seen["turns"] += row["turns"]
        return out

    was, became = sides(before), sides(now)
    if not any(s["whole"] for s in was.values()) or not any(s["whole"] for s in became.values()):
        return ["per-stage comparison unavailable (one run has no measured stage timing)"]
    names = set(was) | set(became)
    comparable = sorted(s for s in set(was) & set(became) if was[s]["whole"] and became[s]["whole"])
    not_comparable = sorted(s for s in names if not was.get(s, {"whole": True})["whole"]
                            or not became.get(s, {"whole": True})["whole"])
    only_now = sorted(s for s in set(became) - set(was) if became[s]["whole"])
    only_before = sorted(s for s in set(was) - set(became) if was[s]["whole"])
    lines = []
    if not_comparable or only_now or only_before:
        lines.append(f"per-stage comparison covers {len(comparable)} of {len(names)} stages"
                     + (f" ({len(not_comparable)} not comparable, incomplete or unmeasured on a side: "
                        f"{', '.join(not_comparable[:top])})" if not_comparable else ""))
    by_turns = [s for s in comparable if was[s]["has_turns"] and became[s]["has_turns"]]
    by_minutes = [s for s in comparable if s not in by_turns]
    turn_moves = sorted((s for s in by_turns if became[s]["turns"] != was[s]["turns"]),
                        key=lambda s: abs(became[s]["turns"] - was[s]["turns"]), reverse=True)
    minute_moves = sorted((s for s in by_minutes if became[s]["seconds"] != was[s]["seconds"]),
                          key=lambda s: abs(became[s]["seconds"] - was[s]["seconds"]), reverse=True)
    if turn_moves:
        lines.append("stage turns: " + ", ".join(
            f"{s} {was[s]['turns']}->{became[s]['turns']}"
            f" ({_minutes(was[s]['seconds'])}->{_minutes(became[s]['seconds'])}m)" for s in turn_moves[:top]))
    if minute_moves:
        lines.append("stage minutes (this host reports no per-stage turns): " + ", ".join(
            f"{s} {_minutes(was[s]['seconds'])}->{_minutes(became[s]['seconds'])}" for s in minute_moves[:top]))
    for label, listed in (("only now", only_now), ("only before", only_before)):
        if listed:
            lines.append(f"{label}: " + ", ".join(listed[:top]))
    if not turn_moves and not minute_moves:
        lines.append("no per-stage turn difference" if by_turns else
                     "no per-stage minute difference (turns not measured)" if by_minutes else
                     "no stage is comparable on both runs")
    return lines


def shared_tmp_writes(outputs: list[Path]) -> dict[str, list[str]]:
    """Each literal /tmp path that more than one of these runs wrote, with the runs that wrote it.

    Every host's tool calls are read (Claude's tool_use blocks too), so a run that wrote nothing is a measured none.
    """
    writers: dict[str, list[str]] = {}
    for out in outputs:
        for name in metrics.collect(out).get("tmp_writes") or []:
            writers.setdefault(name, []).append(out.name)
    return {name: runs for name, runs in sorted(writers.items()) if len(runs) > 1}


def suite_chains(order: list[str], cases: dict) -> list[list[str]]:
    """Independent chains: a case with its follow-ons, in suite order. Chains share nothing, so they may run
    concurrently; a follow-on always runs after its predecessor, in the same chain."""
    chains: list[list[str]] = []
    home: dict[str, list[str]] = {}
    for case in order:
        follows = cases[case].get("follows")
        chain = home.get(follows) if follows else None
        if chain is None:
            chain = []
            chains.append(chain)
        chain.append(case)
        home[case] = chain
    return chains


def stale_listener_lines(own: Path | None) -> list[str]:
    """One line per listener an ended case left behind (see listeners.stale): the process, its port, its case and the command.

    Where the process table cannot be read the check is skipped with a printed note, never refused on a guess.
    """
    try:
        found = listeners.stale(own)
    except listeners.Unobserved as exc:
        print(f"stale-listener check skipped: {exc}", flush=True)
        return []
    return [f"pid {item['pid']} {item['command']} listens on port {','.join(map(str, item['ports']))} (working directory "
            f"{item['cwd']}), left by {item['case']}, whose harness is not running: stop it by pid with `kill {item['pid']}`"
            for item in found]


def refuse_stale_listeners(own: Path | None) -> None:
    """Start nothing while an ended case still has a server bound: a later run would meet it (SPEC: a run leaves nothing listening)."""
    lines = stale_listener_lines(own)
    if lines:
        raise SystemExit("a listener an ended case left is still bound, so no host is started (no override: stop it by pid):\n  "
                         + "\n  ".join(lines))


def planned_output(requested: Path | None, name: str) -> Path:
    """Where new_output_dir would put a run's folder, without making it: what the refusals before it read (its runs root and
    its file system)."""
    return (requested.expanduser().resolve() if requested is not None
            else Path(tempfile.gettempdir()) / "shiploop-e2e" / name)


def lifecycle_problems(out: Path, runs: int = 1, own: Path | None = None) -> tuple[list[str], dict]:
    """The refusals of SPEC "The resource lifecycle" made before a host starts, as lines: an orphan of a run under the runs root
    whose harness is not alive, and a disk below the headroom of the `runs` cases this invocation runs. Also the disk record."""
    lines = lifecycle.orphan_lines(environment.runs_root(out), own)
    found = lifecycle.disk(out, runs)
    if line := lifecycle.disk_line(found):
        lines.append(line)
    return lines, found


def refuse_lifecycle(out: Path, runs: int = 1, own: Path | None = None) -> dict:
    """Start nothing beside an orphan or on a disk below the headroom; returns the disk record when there is no refusal."""
    lines, found = lifecycle_problems(out, runs, own)
    if lines:
        raise lifecycle.Refused("no host is started (SPEC \"The resource lifecycle\"):\n  " + "\n  ".join(lines))
    return found


def take_leases(name: str, platform_spec: dict | None, only_platform: bool = False) -> "lifecycle.Lease":
    """Lease the case's platform state and its declared fixed ports, all or none (lifecycle.take raises Refused)."""
    ports = [] if only_platform or name == "custom" else list(case_quality(name).get("refuse_ports") or [])
    lease = lifecycle.take(lifecycle.lease_keys(platform_spec, ports),
                           {"pid": os.getpid(), "case": name, "since": datetime.now().isoformat(timespec="seconds")}, ports=ports)
    for note in lease.notes:
        print(note, flush=True)
    return lease


def run_suite(args, argv: list[str]) -> int:
    """Run a suite's cases in order; a follow-on starts from its predecessor and is skipped if it failed.

    A case's neighbours are its suite's: its overlap record and its concurrent line read the runs root of the suite folder,
    not of the case folder one level deeper (2026-10-24: the release-gate batch under <runs>/<day>/<suite>/<case> saw only
    its day's runs, while a case run alone beside it saw the experiment slices in another folder). A root the caller
    named in the environment is kept, and the environment is restored when the suite ends."""
    named = os.environ.get(environment.RUNS_ROOT_ENV)
    try:
        return _run_suite(args, argv)
    finally:
        if named is None:
            os.environ.pop(environment.RUNS_ROOT_ENV, None)


def _run_suite(args, argv: list[str]) -> int:
    suites = json.loads(SUITES.read_text())
    if args.suite not in suites or args.suite.startswith("_"):
        raise SystemExit(f"unknown suite {args.suite!r}; known: {', '.join(k for k in suites if not k.startswith('_'))}")
    cases = json.loads(CASES.read_text())
    # Once, up front (like the version gate): a refusal raised inside a case's worker thread would reach the suite only after
    # the running chains finish, with no suite-result.json. Its cases skip their own check (--suite-name).
    refuse_stale_listeners(None)
    refuse_lifecycle(planned_output(args.output, "suite-" + args.suite), runs=len(suites[args.suite].get("gate") or [])
                     + len(suites[args.suite]["cases"]))
    base = new_output_dir(args.output, "suite-" + args.suite)
    os.environ.setdefault(environment.RUNS_ROOT_ENV, str(environment.runs_root(base)))
    passthrough, skip = [], {"--suite", "--output", "--case", "--continue-from", "--max-parallel"}
    it = iter(argv)
    for token in it:
        name = token.split("=", 1)[0]
        if name in skip:
            if "=" not in token:
                next(it, None)
            continue
        passthrough.append(token)
    if args.source == "marketplace" and not args.plugin_dir:
        check = base / "preflight"
        check.mkdir()
        env = the_host(args).env(check / "home")
        _, _, versions = marketplace_preflight(args, check, env)
        (check / "preflight.json").write_text(json.dumps(versions, indent=2) + "\n")
        if versions["gate"]:
            raise SystemExit("suite not started, version gate: " + "; ".join(versions["gate"]))
    gate = suites[args.suite].get("gate") or []
    gate_rows = []
    for case in gate:
        # A batch suite's gate runs first and alone: a cheap case that fails stops the costly ones.
        if TERMINATION.is_set():
            gate_rows.append({"case": case, "pass": False, "skipped": stop_cause(base / "stop"), "gate": True})
            continue
        out = base / case
        code = main([*passthrough, "--case", case, "--output", str(out), "--suite-name", args.suite])
        gate_rows.append({"case": case, "pass": code == 0, "output": str(out), "gate": True})
    if not all(row["pass"] for row in gate_rows):
        summary = gate_rows + [{"case": case, "skipped": "the gate failed"} for case in suites[args.suite]["cases"]]
        (base / "suite-result.json").write_text(json.dumps({"suite": args.suite, "cases": summary}, indent=2) + "\n")
        print(f"suite {args.suite}: gate failed ({', '.join(r['case'] for r in gate_rows if not r['pass'])}); "
              "the other cases did not run")
        return 1
    order = suites[args.suite]["cases"]
    chains = suite_chains(order, cases)
    if len(chains) > 1 and not args.serial and "--quiet" not in passthrough:
        passthrough.append("--quiet")  # concurrent live views would interleave

    def run_chain(chain: list[str]) -> list[dict]:
        outputs: dict[str, Path] = {}
        rows = []
        for case in chain:
            if TERMINATION.is_set():
                # Not main's own early return: a case that wrote no result.json would break the readers of the rows below.
                rows.append({"case": case, "skipped": stop_cause(base / "stop")})
                continue
            follows = cases[case].get("follows")
            prior = outputs.get(follows) if follows else None
            if follows and prior is None:
                rows.append({"case": case, "skipped": f"its predecessor {follows!r} is not in this suite run"})
                continue
            if prior is not None and not json.loads((prior / "result.json").read_text()).get("pass"):
                rows.append({"case": case, "skipped": f"its predecessor {follows!r} failed; nothing to build on"})
                continue
            out = base / case
            case_argv = [*passthrough, "--case", case, "--output", str(out), "--suite-name", args.suite]
            if prior is not None:
                case_argv += ["--continue-from", str(prior)]
            try:
                code = main(case_argv)
            except lifecycle.Refused as refused:  # a lease another run holds: this case is not started, the others go on
                rows.append({"case": case, "pass": False, "refused": str(refused)})
                print(f"suite {args.suite}: {case} refused: {refused}", flush=True)
                continue
            outputs[case] = out
            rows.append({"case": case, "pass": code == 0, "output": str(out)})
        return rows

    workers = 1 if args.serial else max(1, min(args.max_parallel, len(chains)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows: list[dict] = []
        for future in [pool.submit(run_chain, chain) for chain in chains]:
            try:
                rows += future.result()
            except KeyboardInterrupt:
                # A Ctrl-C reaches this thread only, and leaving the pool waits for the chains and for the hosts they run, so
                # the exit-time kill would come too late: end the hosts now, as a SIGTERM does, and wait for their records.
                terminate("SIGINT")
                rows += future.result()
    summary = gate_rows + sorted(rows, key=lambda row: order.index(row["case"]))
    shared = shared_tmp_writes([Path(row["output"]) for row in summary if row.get("output")])
    if shared:
        # Concurrent runs that wrote the same /tmp name may have read each other's files (plan P13).
        print("suite " + args.suite + ": /tmp names written by more than one case (their evidence is suspect): "
              + "; ".join(f"{name} ({', '.join(cases_)})" for name, cases_ in shared.items()), flush=True)
    (base / "suite-result.json").write_text(json.dumps({"suite": args.suite, "cases": summary,
                                                        "shared_tmp_writes": shared}, indent=2) + "\n")
    print(f"suite {args.suite}: " + ", ".join(
        f"{row['case']} {'SKIP' if 'skipped' in row else 'PASS' if row['pass'] else 'FAIL'}" for row in summary))
    return 0 if all(row.get("pass") for row in summary) else 1


def main(argv: list[str] | None = None) -> int:
    """Run one case (or a suite) and return the exit code; see _main."""
    held: list = []  # the case lock, taken inside once the output folder is known, and released here whatever happens
    guard = PlatformGuard()  # a case's platform cleanup, armed inside once the model may start, run here whatever happens
    global RUN_PREFIX
    try:
        return _main(argv, held, guard)
    finally:
        guard.finish()  # a crash, a Ctrl-C or an exit after the model started still removes what the run created
        guard.print_kept()  # last, so it ends the log: when --keep-platform kept a finished delivery, what is still there and how to remove it
        for handle in held:
            handle.close()
        RUN_PREFIX = None  # one run's: the next run in this process (a suite's, iterate's) reads the catalog as written


def _main(argv: list[str] | None, held: list, guard: "PlatformGuard | None" = None) -> int:
    global RUN_PREFIX
    guard = guard or PlatformGuard()
    argv = list(sys.argv[1:] if argv is None else argv)
    args = parser().parse_args(argv)
    if args.keep_platform and (args.suite or args.preflight_only or args.baseline_report):
        raise SystemExit("--keep-platform keeps what one run of a case with a platform made there: it does not go with --suite, "
                         "--preflight-only or --baseline-report")
    if args.keep_platform and not args.output and not args.resume_run:  # a resume reuses its run's folder; --output is ignored there
        raise SystemExit("--keep-platform needs --output <a durable folder>: the snapshot the later cleanup needs must not live in "
                         "$TMPDIR, which macOS purges after days")
    if args.platform_existing and (args.suite or args.baseline_report):
        raise SystemExit("--platform-existing is the mode of one run of a case with a platform: it does not go with --suite or "
                         "--baseline-report")
    if args.platform_prefix and (args.suite or args.baseline_report or args.seed_at):
        raise SystemExit("--platform-prefix renames the prefix of one run of a case with a platform: it does not go with --suite "
                         "or --baseline-report, nor with --seed-at, whose seeded product carries the case's own names")
    if args.baseline_report:
        return baseline_report_main(args)
    if args.runs or args.json or args.release_gate:
        raise SystemExit("--runs, --json and --release-gate belong to --baseline-report")
    if args.preflight_only:
        # Before a rerun, every host must get the latest release (SPEC: publish, refresh, then run).
        out = new_output_dir(args.output, "preflight")
        problems = stale_listener_lines(None) + lifecycle_problems(out, own=out)[0]
        prefix = None if args.prompt else run_prefix(args.platform_prefix, args.case, json.loads(CASES.read_text()))
        RUN_PREFIX = (args.case, prefix) if prefix else None
        spec = None if args.prompt else case_platform(args.case)  # the case's platform checks run here too
        try:  # would the run get its leases now? Taken and given back at once
            take_leases("custom" if args.prompt else args.case, spec).close()
        except lifecycle.Refused as refused:
            problems.append(str(refused))
        for line in problems:
            print(f"refused: {line}", flush=True)
        refused = bool(problems)
        existing = platform_existing_mode(args.platform_existing, args.case, spec)
        if args.backend not in (None, "anthropic") and args.host == "all":
            raise SystemExit(f"--backend {args.backend} is a Claude host option; name --host claude, not all")
        for name in (sorted(hosts.HOSTS) if args.host == "all" else [args.host]):
            args.host = name
            check = out / name
            check.mkdir()
            the = the_host(args)
            if getattr(the, "backend", None) == "ollama":  # the Ollama route is part of what this host needs to run
                the.model = args.model or the.model
                why = hosts.ollama_ready(the.model)
                print(f"ollama preflight ({name}, {the.model}): " + ("OK" if why is None else f"REFUSED: {why}"), flush=True)
                refused = refused or why is not None
            host_env = the.env(check / "home")
            _, _, versions = marketplace_preflight(args, check, host_env)
            if spec:
                versions["platform"] = platform_preflight(spec, host_env, check, existing=existing)
                found = versions["platform"]["preflight"]
                print(f"platform preflight ({name}): " + ("no command" if found is None else
                      ("OK" if found["ok"] else "REFUSED: ") + (found["output"].strip()[-1500:] if not found["ok"] else "")), flush=True)
                refused = refused or (found is not None and not found["ok"])
            (check / "preflight.json").write_text(json.dumps(versions, indent=2) + "\n")
            refused = refused or bool(versions["gate"])
        return 1 if refused else 0
    if args.grade_only and not args.resume_run:
        raise SystemExit("--grade-only needs --resume-run <output directory>: it grades a run that already exists")
    if args.host == "all":
        raise SystemExit("--host all is only for --preflight-only; a run needs one host")
    if args.seed_without_home and not args.seed_at:
        raise SystemExit("--seed-without-home needs --seed-at: it changes what the harness seeds")
    if args.planning_review and args.seed_at:
        raise SystemExit("--planning-review with --seed-at: the harness starts a seeded run itself and records its stages "
                         "without doing them, so the option would change nothing")
    if args.suite:
        return run_suite(args, argv)
    if args.plugin_dir:
        args.source = "checkout"
    if args.plugin_dir and not (args.plugin_dir / ".claude-plugin" / "plugin.json").is_file():
        raise SystemExit(f"--plugin-dir has no .claude-plugin/plugin.json: {args.plugin_dir}")

    resumed = None
    regrade = False
    start_disk = None  # the disk headroom checked before this invocation started anything (None: a suite's case or a regrade)
    earlier = {}
    earlier_result: dict = {}
    recorded: dict = {}  # a regrade restates this: the run's own last record
    if args.resume_run:
        # Continue a stopped run in place: same work directory, run state and event stream.
        out = args.resume_run.expanduser().resolve()
        earlier = json.loads((out / "invocation.json").read_text())
        name, checks, follow_on = earlier["case"], earlier["checks"], earlier.get("follow_on")
        based = earlier.get("base")  # the base the run started from (SPEC: A brownfield case)
        prefix = run_prefix(args.platform_prefix, name, json.loads(CASES.read_text()), resuming=True,
                            earlier=earlier.get("platform_prefix"))
        RUN_PREFIX = (name, prefix) if prefix else None  # the checks, prompt and platform it recorded are renamed already
        planning_review = planning_review_choice(args.planning_review, earlier)
        # The platform the run started with (invocation.json), not whatever cases.json says now: its cleanup is what undoes it.
        seed_built = None  # a resume continues the run the seed made
        platform_spec = validate_platform(name, (earlier.get("platform") or {})["spec"]) if (earlier.get("platform") or {}).get("spec") else None
        existing = platform_existing_mode(args.platform_existing, name, platform_spec,
                                          earlier=(earlier.get("platform") or {}).get("existing") or "fresh")
        if args.keep_platform and not platform_spec:
            raise SystemExit(f"--keep-platform: case {name!r} has no platform, so there is nothing to keep")
        refuse_unmatched_keep_checks(name, platform_spec, checks)
        prompt = (out / "prompt.txt").read_text().strip()
        work = out / "work"
        state = grade_shiploop(out)
        # A run that finished while no harness was watching (its parent was killed) is graded again, not resumed.
        # So is a blocked run: it waits for a person (SPEC S-14), so no host may continue it as if answered,
        # but its metrics and verdicts can be refreshed from what is on disk. --grade-only does the same for a run
        # in any status that has a ShipLoop state: the records a killed harness never wrote, with no host started.
        regrade = state.get("status") in ("done", "blocked") or (args.grade_only and state.get("status") is not None)
        if state.get("status") != "active" and not regrade:
            raise SystemExit(f"--resume-run needs an active, blocked or finished ShipLoop run; found "
                             f"{state.get('status')!r} in {out}" + (f": {state['reason']}" if state.get("reason") else ""))
        launched = runrecord.launches(out)
        last_launch = launched[-1][1] if launched else earlier  # the launch that ran it last, which a resume continues
        if not regrade:
            asked = host_given(argv)
            args.host, args.model, args.effort = resume_identity(args, asked, last_launch, out)
            args.backend = resume_backend(args, last_launch)
            if not args.quiet:
                if asked and args.host != last_launch.get("host"):
                    print(f"resume: --allow-host-change: finishing on {args.host} a run last launched on "
                          f"{last_launch.get('host')}; it is a mixed-host run", flush=True)
                elif not asked:
                    print(f"resume: --host not given; continuing on {args.host} ({args.model}, {args.effort or 'default effort'}), "
                          "as the run's last launch recorded", flush=True)
                if args.host == last_launch.get("host"):
                    changed = [f"{label} {new} (the last launch used {old})" for label, new, old in (
                        ("model", args.model, last_launch.get("model")), ("effort", args.effort, last_launch.get("effort")))
                        if new is not None and new != old]
                    if changed:
                        print("resume: " + "; ".join(changed), flush=True)
        if not regrade and not args.suite_name:
            refuse_stale_listeners(out)  # the run's own leftovers are stopped below, not refused
        # The one CLI value every prompt of this invocation names (a record with no plugin_dir yields a path that is not a file).
        resumed_cli = run_cli(earlier["host"], out, Path(earlier.get("plugin_dir") or out / "missing-plugin"))
        if not regrade and not resumed_cli.is_file():
            raise SystemExit(f"--resume-run: the ShipLoop CLI this run started on is gone: {resumed_cli}. A resume "
                             "names that CLI in its prompt, so no host is started. Grade what is on disk with "
                             "--grade-only, or start the case again.")
        try:
            earlier_result = json.loads((out / "result.json").read_text())
        except (OSError, ValueError):
            earlier_result = {}
        if regrade:
            # Nothing is launched, so identity is not a choice: restate the identity of the run's last launch
            # (runrecord.launches, the reader a resume continues from; invocation.json when it is the only one), so a run that
            # two hosts worked on is named by the host that ran it last and not by a result.json an earlier regrade wrote.
            # --host, --model and --effort cannot relabel a finished run with a host that did not run it.
            recorded = last_launch if isinstance(last_launch.get("host"), str) else (
                earlier_result if isinstance(earlier_result.get("host"), str) else earlier)
            kept = {"host": recorded["host"], "model": recorded.get("model") or earlier.get("model"),
                    "effort": recorded.get("effort") or earlier.get("effort")}
            asked = {"host": args.host if host_given(argv) else None, "model": args.model, "effort": args.effort}
            ignored = [f"--{key} {value}" for key, value in asked.items() if value and value != kept[key]]
            if ignored and not args.quiet:
                print(f"regrade: no host starts, so the run's recorded host, model and effort stay ({kept['host']}, "
                      f"{kept['model']}, {kept['effort'] or 'no effort'}); ignoring {', '.join(ignored)}", flush=True)
            args.host, args.model, args.effort = kept["host"], kept["model"], kept["effort"]
            # A regrade starts no host: the run's recorded backend stays. A launch from before the field ran on Anthropic, so
            # the run default (Ollama) never relabels it.
            args.backend = recorded.get("backend") or ("anthropic" if recorded["host"] == "claude" else None)
        resumed = {"from_host": last_launch.get("host") or earlier["host"], "from_model": last_launch.get("model") or earlier.get("model"),
                   "run_dir": state.get("run_dir"),
                   "revision": state.get("revision"), "stage": state.get("stage")}
    else:
        if args.platform_prefix and args.prompt:
            raise SystemExit("--platform-prefix: a custom --prompt has no case prefix to rename")
        prefix = run_prefix(args.platform_prefix, args.case, json.loads(CASES.read_text()))
        RUN_PREFIX = (args.case, prefix) if prefix else None
        name, prompt, checks, follows = load_case(args)
        seed_built = seed_materials(name, args.seed_at)  # refused here, before the folder, the install and the platform
        platform_spec = case_platform(name)
        existing = platform_existing_mode(args.platform_existing, name, platform_spec)
        if args.keep_platform and not platform_spec:
            raise SystemExit(f"--keep-platform: case {name!r} has no platform, so there is nothing to keep")
        refuse_unmatched_keep_checks(name, platform_spec, checks)
        planning_review = planning_review_choice(args.planning_review, None)
        if follows and not args.continue_from:
            raise SystemExit(f"case {name!r} follows {follows!r}: pass --continue-from <that run's output directory>")
        based_on = catalog().get(name) if name != "custom" else None
        if (based_on or {}).get("base") and (args.continue_from or args.seed_at):
            raise SystemExit(f"case {name!r} starts from its base, fixtures/{based_on['base']['fixture']}: it takes neither "
                             "--continue-from nor --seed-at")
        brownfield.resolve(based_on)  # a base that no longer matches its pin is refused before the folder exists
        if not args.suite_name:
            refuse_stale_listeners(None)  # before the folder exists, so a refusal leaves nothing behind
            start_disk = refuse_lifecycle(planned_output(args.output, name))
        lease = take_leases(name, platform_spec)  # all or none, before the folder exists (SPEC "The resource lifecycle")
        held.append(lease)
        out = new_output_dir(args.output, name)
        lease.bind(out)
        work = out / "work"
        work.mkdir()
        follow_on = continue_from(args.continue_from.expanduser().resolve(), work) if args.continue_from else None
        based = brownfield.start(work, based_on)  # the base, committed before the host starts (None: an empty folder)
        record_preexisting_runs(out)  # a follow-on's copy can bring an earlier run's state along: never this run's
    args.platform_existing = existing  # resume_command reads it: a resume keeps its run's mode
    stop_file = out / "stop"  # a person (or a watcher) creates it to end the run; main consumes it
    # This harness is alive while main runs: a launch elsewhere reads the lock to tell a sibling's server from a leftover.
    # The kernel also drops it on any death, SIGKILL included, which is why a lock and not a pid file.
    lock = listeners.hold_case(out)
    if lock is not None:
        held.append(lock)
    elif not regrade and listeners.case_alive(out):
        # Two harnesses in one case: the second would stop the first's servers and consume its stop request. A regrade starts
        # and stops nothing, so it may read a case that is running.
        raise SystemExit(f"--resume-run: another harness is running {out} (it holds {out / listeners.LOCK_NAME}), so nothing was "
                         f"started or stopped. Create {stop_file} to end that run, or wait for it, then resume.")
    if resumed and lock is not None:
        stop_file.unlink(missing_ok=True)  # an earlier invocation's request must not stop this one; only the harness holding the case owns it
    left_behind: list = []  # what each reap pass of this invocation found (see listeners.py)
    retry_cleanup = None  # what a resume stopped of an earlier invocation's processes before it started anything
    if resumed and not regrade and lock is not None:
        # Crash and retry (SPEC "The resource lifecycle"): what a killed harness left (its host, the observer) is stopped by its
        # recorded identity, and a server its model left is reaped, before anything is leased or started. The reap was done just
        # before the session until 2026-10-26; here it also frees a declared port for the lease below.
        retry_cleanup = lifecycle.cleanup(out)
        left_behind.append(listeners.reap(out))
        if not args.suite_name:
            start_disk = refuse_lifecycle(out, own=out)
        lease = take_leases(name, platform_spec)
        held.append(lease)
        lease.bind(out)

    def engine_now() -> dict | None:
        """Where the ledger stands now (None before ShipLoop has written any state, or where it cannot be read: the record of a
        session never stops the session)."""
        try:
            running = grade_shiploop(out)
            return metrics.engine_position(Path(running["run_dir"]) if running.get("run_dir") else None)
        except Exception:  # noqa: BLE001 - fail-open recording
            return None

    def session(*launch_args, kind: str, reason: str, told: dict | None = None, resumed_session: str | None = None,
                **launch_kw) -> dict:
        """One host launch, bracketed in sessions.jsonl: the start row before the host runs (a harness that dies keeps the
        boundary), the end row after it, with the ledger as it stands at that moment (also when the launch raises)."""
        events_path = out / "events.jsonl"
        started: list = []

        def begin(events_line: int) -> None:
            started.append(sessionlog.start(out, kind=kind, reason=reason, host=host.name, model=args.model, told=told,
                                            events_line=events_line, resumed_session=resumed_session, engine=engine_now()))

        done = None
        try:
            done = launch(*launch_args, before_start=begin, **launch_kw)
        finally:
            if started:  # a launch refused before any host ran leaves no session behind
                sessionlog.end(out, started[0], events_line=events_line_count(events_path, repair=False),
                               status=(done or {}).get("status", "crashed"), returncode=(done or {}).get("returncode"),
                               engine=engine_now())
        left_behind.append(done.pop("left_behind", None))  # a run's one record is built below, not repeated per session
        return done

    # Everything this run starts (the host, ShipLoop, the grading of the work folder) finds no repository above the run.
    os.environ.update(isolate_git_discovery(os.environ, out))
    host = the_host(args)
    args.model = args.model or host.model
    args.effort = args.effort or host.effort
    args.skill = args.skill or host.skill
    host.model = args.model  # the model the host's environment routes to (the Claude host on Ollama names it there)
    backend = getattr(host, "backend", None)
    if backend == "ollama" and not regrade:
        if args.max_budget_usd:
            raise SystemExit("--max-budget-usd is not with --backend ollama: Claude Code prices the tokens at Anthropic's "
                             "rates, so the cap would stop the run on a figure that is not its cost. Nothing was started.")
        if why := hosts.ollama_ready(args.model):
            raise SystemExit(f"--backend ollama: {why}. Nothing was started.")
    env = host.env(out / "home")
    earlier_platform = earlier_result.get("platform") or {}
    # The run's last cleanup or keep: a Ctrl-C or a crash ends the run before result.json is written, and a later invocation's
    # crash leaves result.json holding an older one, so the record the cleanup itself writes (platform/cleanup-record.json) wins.
    earlier_cleanup = (earlier_cleanup_record(out) if resumed else None) or earlier_platform.get("cleanup")
    # A run that ended by Ctrl-C or a crash ran its cleanup but wrote no result.json: its cleanup record tells the resumed model.
    note_platform = earlier_platform if earlier_platform.get("cleanup") or not resumed else {"cleanup": earlier_cleanup_record(out)}
    platform_state: dict = {}
    if platform_spec and regrade:
        platform_state = {key: earlier_platform.get(key) for key in ("home_links", "model_bin", "preflight")
                          if key != "model_bin" or key in earlier_platform}  # nothing starts: restate the run's own
        platform_state.update({key: earlier_platform[key] for key in ("shell_path_pinned", "model_bin_resolution")
                               if key in earlier_platform})
    elif platform_spec:
        # Before the marketplace install and before any model call: the host's own environment, so a bad home link shows here.
        # The earlier segment kept an unfinished platform: what is in it is this run's own work, which the case's preflight (it
        # refuses a platform that is not clean) would refuse. The links, the wrappers and their proof still run (platform_preflight).
        kept_unfinished_before = bool(resumed and (earlier_cleanup or {}).get("kept_unfinished"))
        platform_state = platform_preflight(platform_spec, env, out, skip_command=(
            "the earlier segment kept this run's own unfinished work in the platform" if kept_unfinished_before else None),
            existing=existing)
        if kept_unfinished_before and not args.quiet:
            print(f"resume: the earlier segment kept an unfinished {platform_spec.get('kind') or 'platform'}: the case's own preflight "
                  "is skipped, because what this run deployed is still there and that preflight would refuse it", flush=True)
        refusal = platform_state["preflight"]
        if refusal is not None and not refusal["ok"]:
            if not resumed:  # a resumed run already has a result.json worth more than a refusal stub
                (out / "result.json").write_text(json.dumps({"case": name, "pass": False, "output": str(out),
                                                             "platform": {**platform_state, "refused": True}}, indent=2) + "\n")
            raise SystemExit(f"platform preflight refused the run before any model started (exit {refusal['returncode']}): "
                             f"{refusal['output'].strip()[-1500:]} (see {out / 'result.json'})")
    if regrade:
        # No host starts, so nothing is installed or gated: a regrade keeps the plugin identity and the plugin
        # verdict the run recorded (see the invocation record below). Claude's init event shows the plugin on
        # any launch, so Claude is graded from its events again.
        plugin_dir = Path(earlier.get("plugin_dir") or out / "missing-plugin")
        plugin = None if args.host == "claude" else recorded.get("plugin")
        versions = {"source": None, "plugin_version": None, "shiploop_version": None,
                    **(recorded.get("versions") or earlier.get("versions") or {}), "regraded": True}
    elif resumed and earlier.get("host") == args.host and Path(earlier.get("plugin_dir") or "").is_dir():
        # A resumed run keeps the plugin it started on: reinstalling would replace that version's files, and a
        # bound Improve child records paths inside them. Only the CI and checkout checks still apply. It also
        # keeps that launch's plugin verdict, since a Grok or Codex stream cannot show which plugin loaded.
        plugin_dir, plugin = Path(earlier["plugin_dir"]), earlier.get("plugin")
        if str((earlier.get("versions") or {}).get("source") or "").startswith("checkout"):
            # Started on --source checkout: that build is the thing under test and was never published, so the marketplace
            # gate (CI of origin/main, "publish your commits first") does not apply to its resume (found 2026-10-17: it refused
            # the resume of a run whose local HEAD was, by design, ahead of origin/main).
            released = None
            versions = {"source": "checkout (resumed on its original build)", **installed_versions(plugin_dir),
                        "local_head": git("rev-parse", "HEAD").strip(), "gate": []}
        else:
            released = released_versions()
            versions = {"source": "marketplace (resumed on its original install)", **installed_versions(plugin_dir),
                        "released": released,
                        "gate": [problem for problem in version_gate(released, None, None)
                                 if not problem.startswith("installed ")]}
        if versions["gate"]:
            raise SystemExit("version gate: " + "; ".join(versions["gate"]))
        if released is not None and host.name == "codex" and versions["plugin_version"] != released["catalog_version"]:
            # Codex syncs installed plugins to its marketplace's current release when a session starts and
            # deletes the old version's files, which the run's CLI and any bound Improve child point to.
            raise SystemExit(f"a Codex run started on skill-craft {versions['plugin_version']} cannot resume after "
                             f"release {released['catalog_version']}: Codex replaces the plugin at session start. "
                             "Start the case again.")
    elif args.source == "marketplace":
        plugin_dir, plugin, versions = marketplace_preflight(args, out, env)
        if not resumed:
            require_improve_card(planning_review, plugin_dir)  # the install above is the only host CLI that could run before this
        if resumed:
            # No original install to reuse: a newer release is still not a reason to refuse the run.
            versions["gate"] = [problem for problem in versions["gate"] if not problem.startswith("installed ")]
        if versions["gate"]:
            if resumed:
                # The run already has a result.json worth more than a refusal stub; leave it as it was.
                raise SystemExit("version gate: " + "; ".join(versions["gate"]))
            (out / "result.json").write_text(json.dumps({"case": name, "pass": False, "versions": versions,
                                                         "output": str(out)}, indent=2) + "\n")
            raise SystemExit("version gate: " + "; ".join(versions["gate"]) + f" (see {out / 'result.json'})")
    else:
        plugin = None
        plugin_dir = args.plugin_dir or build_candidate(out)
        if not resumed:
            require_improve_card(planning_review, plugin_dir)  # before the host CLI installs the plugin into its profile
        plugin = host.install_plugin(env, plugin_dir)
        versions = {"source": "checkout", **installed_versions(plugin_dir), "local_head": git("rev-parse", "HEAD").strip()}
    keepalive = hosts.grok_keepalive(env, plugin_dir) if host.keepalive else None
    improve_skill = earlier.get("improve_skill") if resumed else None
    if planning_review == "none" and not resumed:
        # The run option rides in the prompt the model is given (and prompt.txt keeps), as it did in a custom --prompt.
        improve_skill = str(improve_card(plugin_dir).absolute())
        prompt = f"{prompt} {planning_review_sentence(improve_skill)}"
    seeded = earlier.get("seeded") if resumed else None
    interrupt_at = earlier.get("interrupt_at") if resumed else args.interrupt_at
    owner_note_at = earlier.get("owner_note_at") if resumed else args.owner_note_at
    # The CLI of the host and plugin the run started on (a resume on another host keeps it): every prompt below names it.
    the_cli = resumed_cli if resumed else run_cli(host.name, out, plugin_dir)
    # The machine and any declared capability, recorded before the host starts and before the deadline is set, so the probe
    # spends none of the run's time (SPEC: a record, not a verdict). A regrade launches nothing and so reads nothing.
    needs = declared_needs(name, args, last_launch if resumed else None)
    if regrade:
        start_environment = environment.unobserved("regraded: no host was launched")
    else:
        try:
            start_environment = environment.start_record(display_held(), needs, args.browser_bin, TERMINATION.is_set)
        except Exception as exc:  # noqa: BLE001 - a record that cannot be made is reported, never raised
            start_environment = environment.unobserved("could not be recorded: " + (" ".join(str(exc).split())[:200] or type(exc).__name__))
    if args.seed_at and not resumed:
        seeded = seed_run(the_cli, work, out, prompt, args.seed_at, checks=checks, home=not args.seed_without_home,
                          **({"product": seed_built["product"], "home_fixture": seed_built["home_fixture"],
                              "work_item": seed_built["work_item"], "records": seed_built["records"],
                              "exclude": seed_built["exclude"]} if seed_built else {}))
        record_run_identity(out, run_dir=str(Path(seeded["run_dir"]).resolve()), basis="seeded by the harness")
        if not args.quiet:
            print(f"seeded: {', '.join(seeded['skipped'])} recorded without doing them; host starts at "
                  f"{seeded['stage']} in {seeded['run_dir']}", flush=True)
    # The permission rules the case's platform asks the host to pre-approve (the host's own classifier would otherwise judge them).
    host_allow = tuple((platform_spec or {}).get("host_allow") or ())
    # A resumed run keeps the ShipLoop CLI of the host that started it, so its version does not change.
    opening = (resume_prompt(resumed["run_dir"], the_cli, resume_platform_note(platform_spec, note_platform, regrade)) if resumed
               else host.invoke(args.skill, seed_prompt(the_cli, seeded["run_dir"], prompt, seeded["delegation"],
                                                        seeded["stage"])) if seeded
               else host.invoke(args.skill, prompt))
    stamp = launch_stamp(out, host.name) if resumed else None
    cli = host.argv(prompt=opening, prompt_file=out / ("host-prompt.txt" if not resumed else
                                                       f"resume-{host.name}-{stamp}.txt"),
                    cwd=work, model=args.model, effort=args.effort,
                    permission_mode=args.permission_mode, max_turns=args.max_turns,
                    max_budget_usd=args.max_budget_usd,
                    plugin_dir=None if host.marketplace else plugin_dir, allow=host_allow)
    # The host CLI's build, probed once for this launch and written on this launch's record. A regrade starts no host: it
    # restates what the run recorded, and a run recorded before the field existed stays null (today's CLI is not the one
    # that ran). Claude's build is its init event's (read below), so it is never probed.
    if regrade:
        launch_build, launch_why = runrecord.host_build(recorded)
    else:
        launch_build, launch_why = host.cli_version(env)
    # The run's `host_build` has one meaning, the first launch's: this launch's when it is the first, else the first
    # launch's record, and never a probe made now for a launch made before the field existed.
    if args.host == "claude":
        host_build, host_build_why = None, None  # the init event, read after the run
    elif regrade:
        # `recorded` is the run's last launch (a regrade restates that launch's identity), but the run's `host_build` is the
        # first launch's: restate what the run recorded for it (its result, else invocation.json, the first launch's record).
        host_build, host_build_why = runrecord.host_build(earlier_result if "host_build" in earlier_result else earlier)
    elif resumed and earlier.get("host") != args.host:
        host_build, host_build_why = None, "resumed on another host: see the launch records"
    elif resumed:
        host_build, host_build_why = runrecord.host_build(earlier)  # invocation.json: the first launch's record
        host_build_why = FIRST_PREDATES if host_build_why == LAUNCH_PREDATES else host_build_why
    else:
        host_build, host_build_why = launch_build, launch_why
    plugin_why = versions.get("plugin_sha256_unmeasured") or (
        LAUNCH_PREDATES if regrade and "plugin_sha256" not in versions else "no reason recorded")
    # `plugin` is the install check made before the host started (Grok, Codex), kept so a resume or a regrade
    # grades the run on its first launch's evidence; None for Claude, whose init event shows it on every launch.
    invocation = {"case": name, "host": args.host, "backend": backend, "model": args.model, "effort": args.effort, "argv": cli,
                  "cwd": str(work), "plugin_dir": str(plugin_dir), "plugin": plugin, "versions": versions,
                  "host_build": launch_build, "checks": checks,
                  "follow_on": follow_on, "base": based, "resumed_run": resumed, "seeded": seeded,
                  "interrupt_at": interrupt_at, "owner_note_at": owner_note_at, "needs": needs, "environment": start_environment,
                  **({"platform_prefix": RUN_PREFIX[1]} if RUN_PREFIX else {}),
                  "planning_review": planning_review, "improve_skill": improve_skill,
                  # why each null identity field of this launch is null (empty: all known)
                  "identity_unmeasured": {**({} if launch_build else {"host_build": launch_why}),
                                          **({} if versions.get("plugin_sha256") else {"plugin_sha256": plugin_why})}}
    if platform_spec:
        invocation["platform"] = {"spec": platform_spec, "dir": str(out / "platform"), **platform_state,
                                  **({"existing": existing} if existing != "fresh" else {})}
        invocation["keep_platform"] = args.keep_platform  # this invocation's own: a resume keeps the platform only if told again
    if resumed:
        # The original invocation stays as it was; each resume is recorded beside it.
        (out / f"invocation-resume-{host.name}-{stamp}.json").write_text(
            json.dumps(invocation, indent=2) + "\n")
    else:
        (out / "prompt.txt").write_text(prompt + "\n")
        (out / "invocation.json").write_text(json.dumps(invocation, indent=2) + "\n")
    # Provider contention is observed, not reserved (SPEC "The resource lifecycle"): the live runs on this host and model now.
    start_contention = None if regrade else lifecycle.contention(out, args.host, args.model)
    if not args.quiet:
        print(f"shiploop e2e case={name} host={args.host}" + (f" backend={backend}" if backend not in (None, "anthropic") else "")
              + f" model={args.model} effort={args.effort} work={work}", flush=True)
        if not regrade:
            # Before any host spend: a later session that finds only this log, even after the harness was
            # killed, holds the output directory and the command that continues the run.
            print(f"resume: {resume_command(out, args)}", flush=True)
            if line := concurrent_line(out):
                print(line, flush=True)
            if platform_spec:
                linked = [link["name"] for link in platform_state["home_links"] or [] if link["linked"]]
                guarded = (f"; guarded commands {', '.join(platform_state['model_bin'])}" if platform_state.get("model_bin") else "") + (
                    "; update mode: items already there are the baseline, the cleanup removes only what the run adds"
                    if existing == "update" else "")
                cleanup_runs = ("cleanup runs after grading unless --keep-platform keeps a finished delivery"
                                + (f", or an unfinished one whose keep checks ({', '.join(platform_spec['keep_checks'])}) pass"
                                   if platform_spec.get("keep_checks") else "") if args.keep_platform
                                else "cleanup runs after grading, always")
                print(f"  platform  home links {', '.join(linked) or 'none'}{guarded}; {cleanup_runs}. By hand: "
                      f"{manual_cleanup_command(out, platform_spec) if platform_spec.get('cleanup') else 'the case names no cleanup'}",
                      flush=True)
            if needs:
                print(f"  environment  {environment.browser_line(start_environment.get('browser') or {})}"
                      if "browser" in needs and start_environment.get("observed") else
                      f"  environment  needs declared ({', '.join(needs)}); the start record could not be made", flush=True)
            elif name == "custom" and not resumed:
                print("  environment  a custom prompt declares no need by itself, so no browser capability is recorded "
                      "(pass --need browser if this run uses a browser)", flush=True)

    platform_dir = out / "platform"
    before_record_file = platform_dir / "before-record.json"
    platform_before = None
    if platform_spec and not regrade:
        if resumed:
            # A resume does not snapshot again: the first run's snapshot is what the cleanup compares with.
            platform_before = (json.loads(before_record_file.read_text()) if before_record_file.is_file()
                               else {"ran": False, "reason": "the earlier invocation recorded no snapshot"})
        elif platform_spec.get("before"):
            platform_before = run_platform_command(platform_spec["before"], out, platform_env(dict(os.environ), platform_dir, existing))
            before_record_file.write_text(json.dumps(platform_before, indent=2) + "\n")
            if not platform_before["ok"]:
                (out / "result.json").write_text(json.dumps({"case": name, "pass": False, "output": str(out), "platform": {
                    **platform_state, "before": platform_before, "refused": True}}, indent=2) + "\n")
                raise SystemExit(f"platform before command failed (exit {platform_before['returncode']}), so no model started: "
                                 f"{platform_before['output'].strip()[-600:]} (see {out / 'result.json'})")
        guard.arm(platform_spec, out)  # from here the model may start: the cleanup runs after grading, whatever happens
    elif platform_spec and regrade and not (earlier_cleanup or {}).get("ok"):
        if lock is not None:
            # A run whose cleanup never succeeded is cleaned when it is graded again. The lock proves that no harness is running
            # this case, not that no model is: a host runs in its own session and outlives a harness that was killed (SIGKILL
            # drops the lock), so a regrade of such a run must wait until its host is stopped (see --grade-only).
            try:  # and no other run may be using the platform the cleanup acts on (SPEC "The resource lifecycle")
                platform_lease = take_leases(name, platform_spec, only_platform=True)
            except lifecycle.Refused as refused:
                print(f"regrade: this run's platform cleanup did not succeed, but {refused}; no cleanup is run now. Grade it "
                      f"again later, or clean by hand: {manual_cleanup_command(out, platform_spec)}", flush=True)
            else:
                held.append(platform_lease)
                platform_lease.bind(out)
                guard.arm(platform_spec, out)
        else:
            # Another harness holds the case (or the lock cannot be taken): its trial may still be using what a cleanup removes.
            print(f"regrade: this run's platform cleanup did not succeed, but {out / listeners.LOCK_NAME} is held by another "
                  "harness, so the run may still be live and no cleanup is run now. Grade it again once that harness has "
                  f"ended, or clean by hand: {manual_cleanup_command(out, platform_spec)}", flush=True)
    if platform_spec and regrade:
        platform_before = earlier_platform.get("before")
    # Active time, not wall time: a Mac that slept 10 h spent run 5's 5 h cap with 3.8 h of work (2026-10-25);
    # time.monotonic stops during sleep (mach_absolute_time, CLOCK_MONOTONIC), time.time does not.
    deadline = time.monotonic() + (args.timeout or float("inf"))
    note_watcher = (owner_note.Watcher(out, the_cli, owner_note_at, lambda: live_run_dir(out)).start()
                    if owner_note_at and not regrade else None)
    if regrade:
        # ShipLoop is done or blocked: no host is started, and the verdicts are computed from what is on disk.
        process = regraded_process(earlier_result.get("process"))
    else:
        interrupt_file = out / "interrupt.json"
        stop_when = ((lambda: chain_in_flight(out)) if interrupt_at and not interrupt_file.exists() else None)
        process = session(cli, work, out, env, args.timeout or float("inf"), watch=not args.quiet,
                         fresh=follow_on is None and seeded is None and based is None,
                         first=resumed is None, translate=host.translator(), stop_when=stop_when,
                         stop_file=stop_file, kind="first" if resumed is None else "fresh",
                         reason="start" if resumed is None else "resume-run",
                         told=resume_told(resumed["run_dir"], the_cli) if resumed else None)
    sessions = [] if regrade else [dict(process, resumed=None, host=host.name)]  # a regrade launched no session
    if process["status"] == "interrupted":
        state = grade_shiploop(out)
        interrupt_file.write_text(json.dumps({
            "at": interrupt_at, "elapsed_seconds": process["elapsed_seconds"], "stage": state.get("stage"),
            "revision": state.get("revision"), "chain": chain_facts(out)["bindings"]}, indent=2) + "\n")
        if not args.quiet:
            print(f"interrupted: killed the host at {process['elapsed_seconds']}s with a chain worker in flight; "
                  "resuming with a fresh session", flush=True)
        argv = host.argv(prompt=resume_prompt(state.get("run_dir"), the_cli),
                         prompt_file=out / "resume-after-interrupt.txt", cwd=work, model=args.model,
                         effort=args.effort, permission_mode=args.permission_mode, max_turns=args.max_turns,
                         max_budget_usd=args.max_budget_usd, plugin_dir=None if host.marketplace else plugin_dir,
                         allow=host_allow)
        process = session(argv, work, out, env, max(60, deadline - time.monotonic()), watch=not args.quiet,
                         first=False, translate=host.translator(), stop_file=stop_file,
                         kind="fresh", reason="after-interrupt", told=resume_told(state.get("run_dir"), the_cli))
        sessions.append(dict(process, resumed="after-interrupt", host=host.name))
    # A headless Grok session ends whenever the model ends its turn. While ShipLoop's
    # run is still active, resume that same session instead of losing the run.
    resume_stop = ("not evaluated (regraded)" if regrade
                   else None if host.resumable else "host is not resumable")
    stop_seen = not regrade and process["status"] == "stopped"  # a requested stop ended the host
    # Resumed sessions in a row that left ShipLoop's revision unchanged (None before ShipLoop wrote any state counts too).
    stalled, failures, launched_at, resumed_any = 0, 0, None, False
    while host.resumable and not regrade and (args.max_resumes is None or len(sessions) <= args.max_resumes):
        state = grade_shiploop(out)
        session_id = last_session_id(out / "events.jsonl")
        remaining = deadline - time.monotonic()
        if resumed_any:
            moved = state.get("revision") != launched_at
            stalled = 0 if moved else stalled + 1
            failures = 0 if moved else failures + (process["status"] == "failed")
        # No run yet means the session ended before ShipLoop wrote its state; a
        # run that is paused, blocked, halted or done is not resumed. (A question
        # waiting for a person is a view of blocked, not a status of its own.)
        # Each reason is recorded, because "why did this run stop?" is answerable
        # only here: the engine is not running when its host goes away.
        if state.get("status") not in ("active", None):
            resume_stop = f"ShipLoop run is {state.get('status')}"
            break
        if stop_seen or stop_file.exists() or TERMINATION.is_set():
            stop_seen = True  # asked for between two sessions, or the host was stopped: never relaunched
            break
        if not session_id:
            resume_stop = "no host session id to resume"
            break
        if remaining <= 60:
            resume_stop = "run deadline spent"
            break
        if stalled >= RESUME_STALL:
            # Every stalled session failed: the host cannot run (FAILED). Otherwise the harness ends a run that stopped moving.
            resume_stop = (f"resumed host failed {stalled} times in a row with ShipLoop still at revision "
                           f"{state.get('revision')} (last exit code {process['returncode']})" if failures == stalled
                           else f"resumed host made no ShipLoop progress {stalled} times in a row (revision "
                                f"{state.get('revision')})")
            break
        if not args.quiet:
            print(f"resume {len(sessions)}/{args.max_resumes if args.max_resumes is not None else 'no limit'}: session {session_id} ended with ShipLoop "
                  f"{'not yet started' if state.get('status') is None else 'active at revision ' + str(state.get('revision')) + ', stage ' + str(state.get('stage'))}", flush=True)
        argv = host.argv(prompt=resume_prompt(state.get("run_dir"), the_cli),
                         prompt_file=out / f"resume-{len(sessions)}.txt", cwd=work, model=args.model,
                         effort=args.effort, permission_mode=args.permission_mode,
                         max_turns=args.max_turns, resume=session_id, allow=host_allow)
        launched_at, resumed_any = state.get("revision"), True
        process = session(argv, work, out, env, remaining, watch=not args.quiet, first=False,
                         translate=host.translator(), stop_file=stop_file, kind="continued", reason="resume-loop",
                         told=resume_told(state.get("run_dir"), the_cli), resumed_session=session_id)
        sessions.append(dict(process, resumed=session_id, host=host.name))
        stop_seen = process["status"] == "stopped"
    if note_watcher is not None:
        note_watcher.stop()  # the host sessions are over: a note now would reach no model
    if resume_stop is None and host.resumable:
        # The loop also ends on its budget without grading the run again, and the last session it
        # was allowed may have finished it: say what the run is, not that the budget was spent.
        status = grade_shiploop(out).get("status")
        resume_stop = (f"ShipLoop run is {status}" if status not in ("active", None)
                       else stop_cause(stop_file) if stop_seen
                       else f"resume budget spent ({args.max_resumes})")
    if not regrade:
        if stop_seen:
            stop_file.unlink(missing_ok=True)  # consumed: the request is answered, a later resume starts clean
            if resume_stop == "host is not resumable":
                resume_stop = stop_cause(stop_file)  # the stop, not the host kind, is why this one is over
            # However the request arrived (it killed the host, or it was found as a session ended on its own), the run
            # ends stopped; the last session keeps its own status in `sessions`.
            process = dict(process, status="stopped")
        process = dict(process, sessions=sessions, resumes=len(sessions) - 1 if sessions else None)
        # A requested stop is not a host failure: no process verdict (None, which no verdict list counts).
        process["pass"] = None if process["status"] == "stopped" else process["status"] == "exited"
    if platform_spec and not regrade:
        scrub_files(out)  # the event stream is a record: a credential the model's tool output showed is not kept in it
    cli_seen = summarize_events(out / "events.jsonl")
    write_transcript(out / "events.jsonl", out / "transcript.md")
    cli_seen["truncated_outputs"] = host_truncations(out / "events.jsonl")
    commands = cli_seen.pop("commands")
    invoked = {"pass": args.skill in commands, "skill": args.skill}
    if not commands or resumed:
        # A host that lists no commands (Codex), or a run continued on another host whose
        # stream mixes both hosts' command lists: the skill was invoked if its CLI ran.
        invoked.update({"pass": shiploop_cli_ran(out / "events.jsonl"), "evidence": "ShipLoop CLI ran"})
    plugins = cli_seen.pop("plugins")
    if plugin is None:
        plugin = grade_claude_plugin(plugins, plugin_dir)
    shiploop = grade_shiploop(out)
    shiploop["knowledge"] = knowledge_facts(work)
    start_head = (follow_on or {}).get("start_head") or (seeded or {}).get("start_head") or (based or {}).get("start_head")
    knowledge = shiploop["knowledge"]
    committed = committed_facts(knowledge, start_head)
    ledger = Path(shiploop["run_dir"]) if shiploop.get("run_dir") else None
    tool_log = metrics.ToolLog()
    run_metrics = metrics.collect(out, ledger, tools=tool_log)
    # The fidelity block is a record in metrics.json only (SPEC 2026-10-09): built once here, so a regrade adds it too, and never
    # a reason for a different verdict, exit code or baseline row. A builder failure is its error block and one printed line.
    run_metrics["fidelity"] = fidelity.safe_build(out, ledger, tool_log, engine_scripts=the_cli.parent, exporter=REVIEW_EXPORTER)
    # The packets and commits counters (SPEC 2026-10-10): four more keys of metrics.json only, built from the same tool log, absent
    # meaning unknown; never a verdict, a baseline key or a line of the report.
    run_metrics.update(counters.safe_build(out, ledger, tool_log))
    if "truncated_outputs" in (run_metrics.get("unmeasured") or {}):
        cli_seen["truncated_outputs"] = None  # [] would read as a measured none
    (out / "metrics.json").write_text(json.dumps(run_metrics, indent=2) + "\n")
    check_env = {"PRIOR_WORK": str(Path(follow_on["prior"]) / "work")} if follow_on else {}
    case = catalog().get(name, {}) if name != "custom" else {}
    # A release slice starts without the product in the source checkout: the checks that read it wait for the return.
    sliced = bool(seeded) and release_slice.delivered(seeded.get("stage"))
    release_spec = release_slice.release_spec(case)
    to_run, skipped_checks = (release_slice.split_checks(
        checks, release_spec.get("source_checks", []), work, release_slice.FIXTURES / case["seed_product"],
        release_spec.get("product_exclude", [])) if sliced else (checks, []))
    # A regrade of a platform run that was cleaned cannot ask the platform again: it restates the checks the run made while the
    # work was deployed, rather than replace a pass with checks that find nothing there.
    restated = bool(regrade and platform_spec and (earlier_cleanup or {}).get("ok") and earlier_result.get("checks"))
    # The delivery snapshot (SPEC: build step 4): the delivered tree before the checks, with a bundle that rebuilds it. A regrade
    # keeps the first run's, since this tree may already have been checked once.
    earlier_delivery = (earlier_result.get("delivery") or {}).get("before") if regrade else None
    delivered_before = earlier_delivery if isinstance(earlier_delivery, dict) else delivery.capture(work, out)
    check_results = (earlier_result["checks"] if restated else
                     run_checks(work, to_run, timeout=(platform_spec or {}).get("check_timeout", CHECK_TIMEOUT), env=check_env,
                                scrubbed=bool(platform_spec)))
    delivered_after = delivery.fingerprint(work)  # what the checks left; scorecard's correctness compares the two
    engine = metrics.engine_state(Path(shiploop["run_dir"]) if shiploop.get("run_dir") else None)
    try:
        # Informational only (SPEC S-11): does the unreturned candidate already pass? Before the reap below, so a server that a
        # check which timed out leaves is stopped with the rest in a run that launched a host. A regrade reaps nothing (the run
        # it grades may have a live host), so there the server stays up: stop it by pid (README).
        at_stop = earlier_result.get("product_at_stop") if restated else product_at_stop(shiploop, engine, checks, check_env, scrubbed=bool(platform_spec))
    except Exception as exc:  # noqa: BLE001 - a record that cannot be made is reported, never raised
        at_stop = {"information_only": True, "ran": False,
                   "reason": "could not be computed: " + (" ".join(str(exc).split())[:200] or type(exc).__name__)}
    run_cleanup = None
    if not regrade:
        # A check may leave a server too (a timed-out check leaves its `node server.js &`). A regrade reaps nothing: it
        # starts no host, and the run it grades may have a live one.
        left_behind.append(listeners.reap(out))
        # What the run's ledger says it owns and is still alive, ShipLoop's progress observer adopted first (SPEC "The resource
        # lifecycle"); the run's data directories are recorded beside it.
        run_cleanup = lifecycle.cleanup(out)
        lifecycle.record_directories(out, args.host, work)
    platform_block = None
    keep_not_honoured = None  # why --keep-platform did not keep the platform (None: kept, moot, or not asked)
    keep_moot = False  # --keep-platform where no cleanup was pending (a regrade of a run already cleaned or kept): changes nothing
    if platform_spec:
        # Did the guard see the model's sf at all, and did the model go around it? Counted outside the harness's own preflights
        # (one range per preflight that ran, platform/preflight-ranges.jsonl); a run that recorded none is not judged.
        ranges = preflight_ranges(out)
        guarded = any(name in (platform_spec.get("model_bin") or {}) for name in GUARDED_NAMES)
        coverage = guard_coverage(out, ranges) if guarded and ranges else None
        if args.keep_platform:
            if not guard.armed():
                keep_moot = True
            else:
                kept_kind, keep_not_honoured = keep_decision(
                    shiploop=shiploop, engine=engine, process=process, stop_seen=stop_seen, stop_file=stop_file,
                    checks=check_results, invalid=bool((coverage or {}).get("bypassed")),
                    earlier_cleanup=earlier_cleanup if regrade else None, keep_checks=platform_spec.get("keep_checks") or ())
                if kept_kind == KEPT_FINISHED:
                    guard.keep("--keep-platform")
                elif kept_kind == KEPT_UNFINISHED:
                    guard.keep("--keep-platform (ShipLoop did not finish: NOT a pass)", unfinished=True)
        # After grading, so the checks saw the deployed work; the guard's `finally` in main() is the same call for a run that never gets here.
        cleanup = guard.finish() or earlier_cleanup or {"ran": False, "ok": False, "reason": "no cleanup record"}
        scrub_files(out)
        earlier_cleanups = list(earlier_platform.get("earlier_cleanups") or [])
        if resumed and not regrade and earlier_platform.get("cleanup"):
            earlier_cleanups.append(earlier_platform["cleanup"])
        platform_block = {"spec": platform_spec, "dir": str(platform_dir), **platform_state, "before": platform_before,
                          **({"existing": existing} if existing != "fresh" else {}), "cleanup": cleanup, **({"kept_unfinished": True} if cleanup.get("kept_unfinished") else {}),
                          **({"earlier_cleanups": earlier_cleanups} if earlier_cleanups else {}),
                          **({"guard_log_preflight_ranges": [list(item) for item in ranges]} if ranges else {}),
                          **({"guard_coverage": coverage} if coverage else {}),
                          **({"keep_not_honoured": keep_not_honoured} if keep_not_honoured else {}),
                          **({"checks_restated": "the platform was already cleaned; these are the checks made while deployed"} if restated else {})}
    invalid_trial = bool(platform_block and (platform_block.get("guard_coverage") or {}).get("bypassed"))
    left = (earlier_result.get("left_behind") if regrade
            else listeners.merge_left_behind([earlier_result.get("left_behind") if resumed else None, *left_behind]))
    # This invocation's resources (a regrade restates the run's own): the ledger holds every invocation's rows.
    resources = earlier_result.get("resources") if regrade else {
        "ledger": lifecycle.LEDGER, "leases": [key for handle in held if isinstance(handle, lifecycle.Lease) for key in handle.keys],
        "contention": start_contention, "disk": start_disk,
        "cleanup": {**({"before_resume": retry_cleanup} if retry_cleanup is not None else {}), "end": run_cleanup}}
    expect = case.get("chain")
    # An inner-loop seed is graded on its chain; a release slice has none (its items are recorded, not built).
    chain = chain_facts(out, expect) if ((seeded and not sliced) or interrupt_at or expect) else None
    release = release_slice.grade(
        seeded=seeded, run_dir=Path(shiploop["run_dir"]) if shiploop.get("run_dir") else None, state=engine, out=out, case=case,
        skipped_checks=skipped_checks, preflights=preflight_ranges(out)) if sliced else None
    if chain is not None:
        chain["source"] = (expect or {}).get("source") or "the harness default: a fanned-out chain (seeded or interrupted run)"
    recovery = None
    if interrupt_at:
        interrupt_file = out / "interrupt.json"
        interrupted = json.loads(interrupt_file.read_text()) if interrupt_file.is_file() else None
        recovery = {"pass": bool(interrupted) and chain["pass"], "interrupt": interrupted, "source": RECOVERY_SOURCE}
    budget = budget_facts(case.get("budget"), bool(seeded), shiploop.get("run_dir"), interrupted=bool(interrupt_at))
    expectations = {
        "checks": case.get("checks_source") or "the --check arguments given with --prompt",
        **({"retention": case["retention_source"]} if case.get("retention_source") else {}),
        **({"chain": {k: v for k, v in chain["expect"].items()} | {"source": chain["source"]}} if chain else {}),
        **({"recovery": RECOVERY_SOURCE} if recovery else {}),
        **({"release_slice": release["source"] or "the case's seed_release"} if release else {}),
        **({"budget": {"seeded_minutes": budget["expected_minutes"], "level": "should",
                       "source": budget["source"]}} if budget else {}),
    }
    verdicts = [invoked["pass"], plugin["pass"], *([] if process["pass"] is None else [process["pass"]]),
                shiploop["pass"], committed["pass"],
                *([chain["pass"]] if chain else []), *([recovery["pass"]] if recovery else []),
                *([release["pass"]] if release else []),
                *(c["pass"] for c in check_results),
                *([bool(platform_block["cleanup"].get("ok"))] if platform_block else []),  # a platform left dirty is a failed run
                *([not platform_block.get("kept_unfinished")] if platform_block else []),  # a kept unfinished platform is NOT a pass
                *([not platform_block["guard_coverage"]["bypassed"]] if platform_block and platform_block.get("guard_coverage") else [])]
    if keepalive is not None:
        keepalive["decisions"] = hosts.keepalive_decisions(out / "home")
    termination = termination_facts(process, engine, resume_stop,
                                    earlier_result.get("termination") if regrade else None)
    try:
        outcome, outcome_basis = outcome_class(all(verdicts), termination)
    except Exception as exc:  # noqa: BLE001 - a record that cannot be made is reported, never raised
        outcome, outcome_basis = None, "could not be computed: " + (_head(exc, 200) or type(exc).__name__)
    if invalid_trial:
        # Not a ShipLoop verdict: the class is unknown, and the basis keeps what the termination alone would have said.
        outcome, outcome_basis = None, f"invalid trial: {'; '.join(bypass_lines(platform_block['guard_coverage']))} (otherwise {outcome_basis})"
    # The machine at the end and the whole run's hosts and neighbours; each part that cannot be read says so (SPEC).
    if regrade:
        end_environment = environment.unobserved("regraded: the end of the run was not observed")
        result_start = environment.restated_start(out)
    else:
        try:
            end_environment = environment.end_record()
        except Exception as exc:  # noqa: BLE001
            end_environment = environment.unobserved("could not be recorded: " + (" ".join(str(exc).split())[:200] or type(exc).__name__))
        result_start = start_environment
    run_environment = environment.result_block(out, result_start, end_environment)
    if platform_block and isinstance(run_environment, dict):
        run_environment = {**run_environment, "platform_home_links": platform_state.get("home_links"),  # what the model could reach
                           **({"platform_model_bin": platform_state["model_bin"]} if platform_state.get("model_bin") else {})}
    # A resumed run overwrites result.json: keep the termination each earlier invocation recorded.
    earlier_terminations = list(earlier_result.get("earlier_terminations") or []) if resumed else []
    if resumed and not regrade and isinstance(earlier_result.get("termination"), dict):
        earlier_terminations.append(earlier_result["termination"])
    stamps_why = "no timeline.jsonl stamps"
    local_head = versions.get("local_head") or (versions.get("released") or {}).get("local_head")
    known = {"plugin_sha256": versions.get("plugin_sha256"), "prompt_sha256": True,
             "host_build": run_metrics["claude_code_version"] if args.host == "claude" else host_build,
             "local_head": local_head, "started": run_metrics["span"]["started"], "ended": run_metrics["span"]["ended"],
             "planning_seconds": metrics.planning_seconds(run_metrics.get("planning"))}
    why = {"plugin_sha256": plugin_why, "host_build": "the init events name no Claude Code build" if args.host == "claude"
           else host_build_why, "local_head": "no head recorded", "started": stamps_why, "ended": stamps_why,
           "planning_seconds": metrics.planning_unmeasured(run_metrics.get("planning"))}
    identity_unmeasured = {name: why.get(name) or "no reason recorded" for name, value in known.items() if value is None}
    result = {"case": name, "host": args.host, "backend": backend, "model": args.model, "effort": args.effort,
              "pass": all(verdicts), "invoked": invoked, "plugin": plugin, "versions": versions,
              # Identity, null where unknown: the case prompt (before a `--planning-review none` sentence) with the run's own
              # folder masked, the host CLI's build (Claude's
              # init event; the others' launch probe) and the stream's first and last stamp.
              "prompt_sha256": masked_prompt_digest(case_prompt(prompt, improve_skill), out, args.resume_run or args.output),
              # What graded this run (SPEC: the evaluator boundary): the harness's code, its checks/ and the case entry read
              # above. A regrade records its own; promotion.py compares a case only across equal digests.
              "boundary": boundary.fingerprint(HERE, case),
              **({"platform_prefix": RUN_PREFIX[1]} if RUN_PREFIX else {}),  # the case digest above is of the renamed entry
              "host_build": run_metrics["claude_code_version"] if args.host == "claude" else host_build,
              "span": run_metrics["span"],
              "identity_unmeasured": identity_unmeasured,
              "process": process, "termination": termination, "outcome_class": outcome, "outcome_basis": outcome_basis,
              "environment": run_environment,
              **({"platform": platform_block} if platform_block else {}),
              **({"earlier_terminations": earlier_terminations} if earlier_terminations else {}),
              **({"left_behind": left} if left is not None else {}),
              **({"resources": resources} if resources is not None else {}),
              "keepalive": keepalive,
              "shiploop": shiploop, "committed": committed, "checks": check_results, "cli": cli_seen, "follow_on": follow_on,
              "base": based, "delivery": {"before": delivered_before, "after": delivered_after},
              "resumed_run": resumed, "seeded": seeded, "chain": chain, "recovery": recovery, "budget": budget,
              **({"release_slice": release} if release else {}),
              "expectations": expectations,
              **({"product_at_stop": at_stop} if at_stop is not None else {}),
              "metrics": {k: run_metrics[k] for k in ("claude_code_version", "turns", "model_calls", "window_tokens",
                                                      "cost_usd", "unreported_sessions", "compactions",
                                                      "truncated_outputs", "improve_children", "stages", "unmeasured")}
              # None, not 0, where the host's events cannot show the thing counted.
              | {"script_verifications": run_metrics["script_verifications"],
                 "planning_seconds": metrics.planning_seconds(run_metrics.get("planning")),
                 "model_glue": metrics.count(run_metrics, "model_glue"),
                 "tmp_writes": metrics.count(run_metrics, "tmp_writes"),
                 "asked_user": len(run_metrics["asked_user"]),
                 "narrative": {k: v for k, v in run_metrics["narrative"].items() if k != "skipped"},
                 "shiploop_failures": metrics.count(run_metrics, "shiploop_failures"),
                 "cancelled_tool_calls": metrics.count(run_metrics, "cancelled_tool_calls")},
              "output": str(out)}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    flow_record(out)  # first, so the Review page finds flow.html and links each visit to its action there
    exported = review_export(out)
    print(f"  flow      {flow_record(out)}")  # again, now that the Review page exists for flow.html's header to link to
    style = catalog().get(name, {}).get("style") if name != "custom" else None
    row = baseline_row(result, style, args.suite_name, metrics.planning_review(engine))
    # A baseline measures one host running a case from the start to its end; a resumed run is not one, and neither is
    # a run the harness ended: its engine still active (a deadline, a requested stop, a spent resume budget) or its host
    # killed by the deadline or a stop before ShipLoop wrote any state (engine unknown). The turns, cost and stages are a
    # fragment, and the next run would be compared with it (SPEC). A host that ends by itself is a finished run's row.
    engine_active = engine.get("status") == "active"
    unfinished = engine_active or process["status"] in ("timeout", "stopped") or invalid_trial  # an invalid trial measures nothing of ShipLoop
    baseline_file = args.baseline if not (resumed or seeded or unfinished) else None
    # The row is written for any run that ended, but only a run that reached done is compared: a blocked or halted run's
    # turns, cost and stages stop at the block (r1 Grok printed "503 -> 301" for a blocked run against a blocked row).
    reached_done = engine.get("status") == "done"
    cell, rows_for_case, skipped = (
        matching_rows(baseline_file, name, versions["source"], args.host, args.model, args.effort, row["planning_review"],
                      row["prompt_sha256"]) if baseline_file and reached_done else ([], 0, Counter()))
    before = cell[-1] if cell else None
    last = (previous_row(baseline_file, name, versions["source"], args.host, args.model, args.effort, row["prompt_sha256"])
            if baseline_file and reached_done and before is None else None)  # the driver's last row, of another mode: what the report names
    if baseline_file:
        with baseline_file.open("a") as handle:
            handle.write(json.dumps(row) + "\n")

    mark = lambda ok: "PASS" if ok else "FAIL"  # noqa: E731
    print(f"{'STOPPED' if stop_seen and not result['pass'] else mark(result['pass'])}  "
          f"shiploop e2e case={name} host={args.host}  output={out}")
    print(f"  versions  {versions['source']}: skill-craft {versions['plugin_version']}, "
          f"ShipLoop {versions['shiploop_version']}")
    print(f"  invoked   {mark(invoked['pass'])}  /{args.skill}")
    print(f"  plugin    {mark(plugin['pass'])}  {', '.join(map(str, plugin['loaded'])) or 'none loaded'}")
    print(f"  process   {'n/a ' if process['pass'] is None else mark(process['pass'])}  " + (
        "no host ran: regraded from what is on disk" if process.get("regraded") and process["pass"] is None else
        f"no host ran: regraded, the original run's {process['status']} rc={process['returncode']} is kept"
        if process.get("regraded") else
        f"{process['status']} rc={process['returncode']} {sum(s['elapsed_seconds'] for s in sessions):.1f}s "
        f"cost={metrics.cost_text(run_metrics)} sessions={len(sessions)}"))
    if keepalive is not None:
        print(f"  keepalive {'installed' if keepalive['installed'] else 'NOT installed'}; "
              f"decisions {keepalive['decisions'] or 'none (hooks never ran)'}")
    print(f"  shiploop  {mark(shiploop['pass'])}  {shiploop.get('status') or shiploop.get('reason')}")
    if line := run_trace.checks_line((run_metrics.get("run_trace") or {}).get("checks")):
        print(f"  trace checks  {line}")
    print(f"  stopped   {stopped_line(termination)}")
    print(f"  outcome   {outcome or 'unknown'}  {outcome_basis}")
    for line in environment.summary_lines(run_environment):
        print(f"  environment  {line}")
    if line := listeners.left_behind_line(left):
        print(line)
    for found in ((resources or {}).get("cleanup") or {}).values() if not regrade else ():
        if line := lifecycle.cleanup_line(found):
            print(line)
    if at_stop is not None and at_stop["ran"]:
        print(f"            product at stop (information only, engine {at_stop['engine']['status']} at "
              f"{at_stop['engine']['stage']}): {at_stop['passed']}/{at_stop['total']} checks pass in {at_stop['worktree']}"
              + (f"; {at_stop['timed_out']} timed out" if at_stop["timed_out"] else ""))
    print(f"  committed {mark(committed['pass'])}  HEAD {str(committed['head'])[:8]} (started at "
          f"{str(committed['start_head'])[:8] if committed['start_head'] else 'no commit'}); "
          f"{committed['head_files']} files in HEAD, {len(knowledge['uncommitted'])} uncommitted product paths")
    print(f"  knowledge docs/shiploop/spec.md {'present' if knowledge['spec'] else 'missing'}"
          f"{', tracked' if knowledge['spec_tracked'] else ', not committed'}; {len(knowledge['requirement_ids'])} "
          f"requirement ids; HEAD has {knowledge['head_commits']} commits, {knowledge['untracked_files']} untracked files"
          + ("; the seed committed the spec and environment (R-1 is the request)" if (seeded or {}).get("home") else ""))
    if chain is not None:
        want = chain["expect"]
        print(f"            expected  >= {want['min_steps']} steps all accepted, >= {want['min_in_flight']} in flight, "
              f"depth >= {want['min_depth']}, dependency order, each merged once ({chain['source']})")
        for binding in chain["bindings"] or [{}]:
            print(f"  chain     {mark(chain['pass'])}  " + (
                f"{binding.get('mode')} {binding.get('accepted')}/{binding.get('steps')} steps accepted, depth "
                f"{binding.get('depth')}, native {binding.get('native_attempts')}, main-context "
                f"{binding.get('main_context_attempts')}, most in flight {binding.get('max_in_flight')}"
                + "".join(f", {key} {binding[key]}" for key in ("out_of_order", "integrated_twice", "not_integrated")
                          if binding.get(key))
                if binding.get("steps") is not None else binding.get("error") or "no chain bound"))
    if release is not None:
        shown = release_slice.lines(release)
        print(f"  release   {mark(release['pass'])}  {shown[0]}")
        for line in shown[1:]:
            print(f"            {line}")
    if recovery is not None:
        stop = recovery["interrupt"]
        print(f"  recovery  {mark(recovery['pass'])}  " + (
            f"killed at {stop['elapsed_seconds']}s in {stop['stage']}; a fresh session resumed the chain"
            if stop else "the host was never interrupted (no chain worker was ever in flight)"))
        print(f"            expected  {recovery['source']}")
    if budget is not None and not budget["applies"]:
        print(f"  budget    n/a   took {budget['observed_minutes']} min; {budget['reason']}")
    elif budget is not None:
        print(f"  budget    {'met ' if budget['pass'] else 'over'}  should finish within {budget['expected_minutes']} min; "
              f"took {budget['observed_minutes']} min ({budget['source']})")
    for line in metrics.summary_lines(run_metrics):
        print(f"  metrics   {line}")
    for line in fidelity.lines(run_metrics["fidelity"]):
        print(f"  fidelity  {line}")
    for failure in run_metrics["shiploop_failures"][:5]:
        print(f"  failed    shiploop {failure['verb']} {metrics.failure_text(failure)}: {failure['line']}")
    if follow_on:
        prior_bound = follow_on.get("prior_lower_bound")
        print(f"  follow-on of {follow_on['prior_case']} ({follow_on['prior']}): turns {metrics.turns_text(run_metrics)} vs "
              f"{marked('not reported' if follow_on['prior_turns'] is None else follow_on['prior_turns'], prior_bound)}, "
              f"cost {marked(metrics.money(run_metrics['cost_usd']), metrics.lower_bound(run_metrics))} vs "
              f"{marked(metrics.money(follow_on['prior_cost_usd']), prior_bound)}")
    print(f"  checks    expected from {expectations['checks']}")
    for check in check_results:
        print(f"  check     {mark(check['pass'])}  {check['command']}")
    if platform_block:
        cleaned, seen = platform_block["cleanup"], platform_block.get("guard_coverage")
        print(f"  platform  {'KEPT' if cleaned.get('kept_unfinished') else mark(cleaned.get('ok') and not (seen or {}).get('bypassed'))}  "
              + ("platform KEPT (--keep-platform), ShipLoop did not finish: NOT a pass" if cleaned.get("kept_unfinished")
                 else "platform KEPT (--keep-platform), no cleanup run" if cleaned.get("kept")
                 else "cleanup ran" if cleaned.get("ran") else "cleanup did not run") + f"; home links "
              + (", ".join(link["name"] for link in platform_state.get("home_links") or [] if link["linked"]) or "none")
              + (f"; guarded commands {', '.join(platform_state['model_bin'])}" if platform_state.get("model_bin") else "")
              + (f"; guard saw {seen['guard_calls']} model calls (transcript shows {seen['model_sf_commands']} sf-looking commands"
                 + (f", {seen['direct_sf_commands']} by a path outside the wrapper" if seen["direct_sf_commands"] else "") + ")"
                 if seen else ""))
        if keep_not_honoured:
            print(f"            --keep-platform NOT honoured ({keep_not_honoured}), so the platform was cleaned as usual")
        elif keep_moot:
            print("            --keep-platform changes nothing here: no cleanup was pending (an earlier invocation already "
                  "cleaned or kept the platform, or another harness holds the run)")
        for line in bypass_lines(seen) if seen else []:
            print(f"            {line}")
    print(f"  {exported}")
    if before:
        unknown = lambda value: "not measured" if value is None else value  # noqa: E731
        was, now = row_lower_bound(before), metrics.lower_bound(run_metrics)  # a lower bound stays marked wherever it is shown
        print(f"  baseline  vs {before['date'][:10]} (ShipLoop {before['shiploop_version']}, same "
              f"{args.host}/{args.model}/{args.effort}, planning_review {row['planning_review']}): "
              f"turns {marked(unknown(before['turns']), was)} -> {marked(unknown(row['turns']), now)}, "
              f"cost {marked(metrics.money(before['cost_usd']), was)} -> {marked(metrics.money(row['cost_usd']), now)}, "
              f"sessions {before['sessions']} -> {row['sessions']}, "
              f"glue {unknown(before['model_glue'])} -> {unknown(row['model_glue'])}"
              + (f", narrative shown {before['narrative']['shown']}/{before['narrative']['emitted']} -> "
                 f"{row['narrative']['shown']}/{row['narrative']['emitted']}"
                 if before.get("narrative") and row.get("narrative") else ""))
        print(f"            sample: {sample_line(row, before, cell)}")
        if why := row_planning_review(before)[1]:  # a row with no mode compared as stage by the plugin version rule
            print(f"            the earlier row {why}")
        for line in stage_diff_lines(before.get("stages"), row.get("stages")):
            print(f"            {line}")
    elif baseline_file and not reached_done:
        print(f"  baseline  nothing compared: this run did not reach done (engine {engine.get('status') or 'unknown'}), so "
              "its turns, cost and stages are no comparison; its row is recorded")
    elif last:
        print(planning_review_line(row["planning_review"], last))  # turns, cost and stages mean something else in the other mode
    elif baseline_file:
        only_driver = set(skipped) <= {"another host, model or effort"}
        print("  baseline  nothing compared: " + (
            f"{rows_for_case} earlier row(s) for {name}, none recorded with {args.host}/{args.model}/"
            f"{args.effort}, so there is no baseline" if rows_for_case and only_driver
            else f"{rows_for_case} earlier row(s) for {name}, none comparable with this run ("
                 + ", ".join(f"{count} {reason}" for reason, count in skipped.items()) + ")" if rows_for_case
            else f"no earlier row for {name} from this source"))
    elif resumed or seeded:
        print("  baseline  nothing compared: a resumed or seeded run is not a baseline")
    elif invalid_trial:
        print("  baseline  nothing compared: an invalid trial (the guard did not govern the model's sf) says nothing of ShipLoop, so no row is written")
    else:
        why = ("its engine is still active" if engine_active else
               f"the harness ended the host: {process['status']}; engine {engine.get('status') or 'unknown'}")
        print(f"  baseline  nothing compared: the run is not finished ({why}), so it is not a baseline")
    if engine_active and not regrade:
        # The exact command, flags included, for whoever finds only this log (SPEC: a resume names what the run uses).
        # Only an active engine can be resumed: --resume-run refuses a run that never wrote ShipLoop state.
        print(f"  resume    {resume_command(out, args)}")
    elif engine_active:
        # A regrade's flags are the grading invocation's (the default --timeout is above any task limit), not the run's.
        print("  resume    use the command printed when the run started, with --timeout below the launcher's limit "
              "(this regrade's own flags are not the run's)")
    if not result["pass"] and not stop_seen:
        failed = [(verdict, want, got) for ok, verdict, want, got in (
            (invoked["pass"], "invoked", "the host registers the invoked ShipLoop skill", "not registered"),
            (plugin["pass"], "plugin", "exactly the skill-craft build under test loads", str(plugin.get("loaded"))),
            (process["pass"], "process", "the host exits 0 within the timeout",
             f"{process['status']} rc={process['returncode']}"),
            (shiploop["pass"], "shiploop", "ShipLoop reaches done and writes its report",
             str(shiploop.get("status") or shiploop.get("reason"))),
            (committed["pass"], "committed", "HEAD moves past the start, has files in HEAD and no product path is "
             "uncommitted", f"HEAD {str(committed['head'])[:8]}, {committed['head_files']} files in HEAD, "
             f"{len(committed['uncommitted'])} uncommitted"),
        ) if ok is not None and not ok]
        if chain is not None and not chain["pass"]:
            want = chain["expect"]
            got = "; ".join(f"{b.get('accepted')}/{b.get('steps')} accepted, depth {b.get('depth')}, "
                            f"most in flight {b.get('max_in_flight')}, out of order {b.get('out_of_order')}, "
                            f"merged twice {b.get('integrated_twice')}, not merged {b.get('not_integrated')}"
                            if b.get("steps") is not None else b.get("error", "no chain")
                            for b in chain["bindings"]) or "no chain bound"
            failed.append(("chain", f">= {want['min_steps']} steps all accepted, >= {want['min_in_flight']} in "
                           f"flight, depth >= {want['min_depth']}, in dependency order, each merged once "
                           f"(source: {chain['source']})", got))
        if release is not None and not release["pass"]:
            shown = release_slice.lines(release)
            failed.append(("release_slice", f"ShipLoop accepts every stage from {release['from']} on"
                           + (f" and the {release['operation']['name']} happens in the {release['operation']['stage']} stage"
                              if release.get("operation") else "") + f" (source: {release['source'] or 'the case'})",
                           "; ".join(shown[1:] or shown)))
        if recovery is not None and not recovery["pass"]:
            failed.append(("recovery", f"a fresh session finishes the chain after the kill (source: {RECOVERY_SOURCE})",
                           "never interrupted" if not recovery["interrupt"] else "the chain did not finish"))
        def check_observed(check: dict) -> str:
            lines = [line for line in str(check.get("output") or "").splitlines() if line.strip()]
            last = f": {lines[-1].strip()[:300]}" if lines else ""
            return ("timed out" if check.get("returncode") is None else f"exit {check['returncode']}") + last

        failed.extend(("check", f"`{c['command']}` exits 0 (source: {expectations['checks']})", check_observed(c))
                      for c in check_results if not c["pass"])
        if platform_block and not platform_block["cleanup"].get("ok"):
            failed.append(("platform", "the case's cleanup command exits 0 and leaves the platform as it found it",
                           str(platform_block["cleanup"].get("output") or platform_block["cleanup"].get("reason"))[-300:]))
        if invalid_trial:
            seen = platform_block["guard_coverage"]
            failed.append(("platform", "the model's sf runs through the guard (an invalid trial otherwise)",
                           f"{seen['model_sf_commands']} sf-looking commands in the transcript ({seen['direct_sf_commands']} by a path "
                           f"outside the wrapper), {seen['guard_calls']} guard calls"))
        print(f"  mismatch  {write_mismatch(out, name, args.host, failed)}")
    # The delivered-quality phase runs last: it can take minutes after the host ended and a task launcher's limit is near 30, so
    # the result, the metrics, the Run Review export and the baseline row are all written before it, and it adds its block to
    # result.json and to nothing else (SPEC, Delivered quality). The report above is already printed.
    gate = quality_gate(shiploop=shiploop, committed=committed, engine=engine, process=process, stop_seen=stop_seen,
                        stop_file=stop_file, lock_held=lock is not None)
    block = quality_record(out, work, name, gate, stop_file)
    kept = earlier_result.get("quality") if regrade else None
    if isinstance(kept, dict) and kept.get("observed") and not block.get("observed"):
        # A regrade that cannot measure (the case is held by another harness, a port is busy) never replaces a measurement with a gap.
        result["quality"], result["quality_regrade_skipped"] = kept, {"reason": block.get("reason")}
    else:
        result["quality"] = block
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"  quality   {quality.line(result['quality'])}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    install_termination_handlers()  # a program only: signal.signal is main-thread-only, and tests call main() from workers
    raise SystemExit(main())
