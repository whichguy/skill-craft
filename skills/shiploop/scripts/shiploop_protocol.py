"""ShipLoop CLI protocol: argument parsing, run-directory locking and routing.

The navigator (shiploop_navigator) owns the graph, the durable cursor and the
packet for the current step.  This module parses the CLI, holds the run lock,
refuses saved runs from removed protocols, and hands every verb for a
protocol 4 run to ``navigator.dispatch``.  Workspace effects stay in their own
module.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, TextIO

import shiploop_navigator as navigator
import shiploop_navigator_dry_run as navigator_dry_run
import shiploop_store as store


class ProtocolError(RuntimeError):
    """A command was refused; the message is shown to the caller."""
    pass


def need(ok: object, message: str) -> None:
    """Raise ProtocolError with ``message`` unless ``ok``."""
    if not ok:
        raise ProtocolError(message)


def _require_retry_delegation(existing: dict, requested: "str | None", run_dir: Path) -> None:
    """Recovery retries keep the recorded delegation; only the toggle changes it."""
    if requested is None:
        return
    recorded = navigator.recorded_delegation(existing)
    need(recorded == requested,
         f"--delegation {requested} differs from this run's recorded delegation {recorded}; rerun "
         "without --delegation to recover the run, and change the setting only on an explicit "
         f"user request with: shiploop delegation --run-dir {run_dir} --set {requested}")


def _require_retry_lint(existing: dict, requested: "str | None", run_dir: Path) -> None:
    """Recovery retries keep the recorded lint option; only lint-mode changes it."""
    if requested is None:
        return
    recorded = navigator.lint_mode(existing)
    need(recorded == requested,
         f"--lint {requested} differs from this run's recorded lint option {recorded}; rerun without "
         f"--lint to recover the run, and change it with: shiploop lint-mode --run-dir {run_dir} --set {requested}")


def _require_retry_fixed_option(requested: "str | None", flag: str, label: str, recorded: str) -> None:
    """Recovery retries keep an option no verb changes mid-run: the one guard for every such option."""
    if requested is None:
        return
    need(recorded == requested,
         f"{flag} {requested} differs from this run's recorded {label} {recorded}; rerun without {flag} "
         f"to recover the run. The option cannot change mid-run: only the owner starts a fresh run "
         f"(a fresh --run-dir or --workspace-root) to use {requested}")


def _require_retry_planning_review(existing: dict, requested: "str | None", run_dir: Path) -> None:
    """Recovery retries keep the recorded planning review option; no verb changes it mid-run."""
    _require_retry_fixed_option(requested, "--planning-review", "planning review option",
                                navigator.recorded_planning_review(existing))


def _require_card_for_unreviewed_planning(requested: "str | None", card: str) -> None:
    """A run with no planning child names its Improve card where it starts, and the card is resolved there.

    Under ``stage`` the first child, at ``spec``, binds the card.  Under ``none`` the first child is the first
    implement step's review, but every inner stage's Until Loop reads the recorded card from step-plan on (falling
    back to the bundled one), so the card a run names is recorded here, before its first loop.
    """
    if (requested or navigator.DEFAULT_PLANNING_REVIEW) != "none":
        return
    need(bool(card), "--planning-review none needs --improve-skill=<absolute selected Improve SKILL.md>: with no "
                     "Improve stage at the planning stages nothing else binds the card before the first item's "
                     "stage Until Loops, which read it. Start the run again with the flag.")
    import shiploop_standalone_improve as standalone
    try:
        standalone.resolve_skill(str(Path(card).expanduser().absolute()))
    except standalone.StandaloneImproveError as exc:
        raise ProtocolError(f"the selected Improve card cannot be resolved: {exc}") from exc


class _Paths:
    """A printed line that holds a path list: ``head``, the paths, ``tail``.  ``_fit`` decides how many paths show."""

    def __init__(self, head: str, paths: Sequence[str], tail: str = "") -> None:
        self.head, self.paths, self.tail = head, list(paths), tail

    def text(self, room: int) -> str:
        """The line within ``room`` characters; a longer list is cut at a path and the rest counted."""
        room -= len(self.head) + len(self.tail)
        whole = ", ".join(self.paths)
        if len(whole) <= room:
            return self.head + whole + self.tail

        def more(count: int) -> str:
            """Suffix naming how many further items were left out."""
            return f", and {count} more"

        room -= len(more(len(self.paths)))
        shown, used = [], 0
        for path in self.paths:
            if used + len(path) + 2 > room:
                break
            shown.append(path)
            used += len(path) + 2
        return self.head + ", ".join(shown) + more(len(self.paths) - len(shown)) + self.tail


# The most one command's output holds (the return-review and workspace commands' lists): the navigator's whole-print limit
# when the two were one constant, apart from it now so the packet limits can move without changing these outputs.
OUTPUT_LIMIT = 16_000


def _fit(parts: Sequence[str | _Paths], limit: Optional[int] = None) -> list[str]:
    """The lines of one command's output, as text of at most ``limit`` characters (default ``OUTPUT_LIMIT``) in all.

    A plain string is a fixed line and prints whole.  Each ``_Paths`` takes an even share of the room the fixed lines
    leave, in order, so a short list leaves its room to the longer ones after it.  Output hosts cut near 20,000
    characters, and the line a cleared context needs is the last one (the next command), so the whole output, not each
    list, is held to the limit.
    """
    room = (limit or OUTPUT_LIMIT) - sum(len(part) + 1 for part in parts if isinstance(part, str))
    lists = sum(not isinstance(part, str) for part in parts)
    lines = []
    for part in parts:
        if not isinstance(part, str):
            part = part.text(room // lists - 1)
            room -= len(part) + 1
            lists -= 1
        lines.append(part)
    return lines


def _emit(parts: Sequence[str | _Paths], stream: Optional[TextIO] = None) -> None:
    for line in _fit(parts):
        print(line, file=stream or sys.stdout)


def _recorded_parts(reviewed: Mapping[str, Any]) -> list[str | _Paths]:
    """What a review-return call recorded, for the model that has to confirm it.

    The excludes are counted here and listed once, with the other excludes a review decided, by ``_review_parts``.
    """
    kept, excluded = reviewed["kept"], reviewed["excluded"]
    if not kept and not excluded:
        return ["No decision was recorded (no --keep or --exclude path was named)."]
    return [*([_Paths("Recorded: kept ", kept, ".")] if kept else []),
            *([f"Recorded: excluded {len(excluded)} (every exclude a review decided is listed below)."]
              if excluded else [])]


def _review_parts(core: Any, root: Path, summary: Mapping[str, Any], expected: Optional[str] = None,
                  policy: Optional[str] = None, rollback: Sequence[str] = ()) -> list[str | _Paths]:
    """The plan's tally, the excludes a review decided, and the next command, which is always the last line.

    While paths are undecided the next command is the review that decides them; with none left it is the return, after
    ``expected``, the route a return would take, and ``rollback``, its undo with the keep rows filled in, for the model
    to compare with the rollback it wrote at release-plan.
    """
    parts = [f"Return plan {root / 'return-plan.md'}: {summary['total']} paths, {summary['keep']} keep, "
             f"{summary['exclude']} exclude, {len(summary['pending'])} undecided."]
    if policy:
        parts.append(policy)
    if summary["reviewed_excludes"]:
        parts.append(_Paths("Excluded by review: ", summary["reviewed_excludes"], "."))
    if summary["pending"]:
        return [*parts, _Paths(f"Undecided ({len(summary['pending'])}): ", summary["pending"], "."),
                navigator.REVIEW_RETURN_RULE, "Decide them with: " + navigator.review_return_command(core, root)]
    if expected:
        parts.append(f"Expected return: {expected}; the return itself still refuses a moved source or a collision.")
    parts.extend(rollback)
    return [*parts, "Nothing is undecided; run: " + shlex.join(
        ["python3", str(core.PACKAGE_ROOT / "scripts" / "shiploop"), "workspace", "return", "--workspace-root", str(root)])]


# Not "default": under --planning-review none there is none, and the run is refused without the flag.
IMPROVE_SKILL_HELP = ("absolute selected Improve SKILL.md (a stage run without it records the card installed beside "
                      "ShipLoop; required with --planning-review none)")


def _new_run_card(explicit: str) -> str:
    """The Improve card a new run records: the one selected with ``--improve-skill``, else the one installed beside ShipLoop.

    The installed card is found by file location in this plugin install and accepted only when
    ``resolve_skill`` validates it, so no name or PATH search is involved.  Where none resolves the run records
    nothing; under ``stage`` the first bind is then the spec checkpoint's packet, which prints a marked blank.
    """
    if explicit:
        return explicit
    import shiploop_prompts as prompts
    import shiploop_standalone_improve as standalone
    try:
        return standalone.resolve_skill(str(prompts.installed_improve_card()))["skill_card"]
    except standalone.StandaloneImproveError:
        return ""


def workspace_command(core: Any, argv: Sequence[str]) -> int:
    """One CLI family; workspace effects stay outside the opaque navigator."""
    import shiploop_workspace as workspace

    parser = argparse.ArgumentParser(prog="shiploop workspace")
    subs = parser.add_subparsers(dest="operation", required=True)
    start = subs.add_parser("start", help="isolate the current branch and begin a new run")
    start.add_argument("--repo", required=True)
    start.add_argument("--workspace-root", default="",
                       help="default: <repo-parent>/.shiploop-runs/<repo>-<utc stamp>-<hex>")
    start.add_argument("--prompt", required=True)
    start.add_argument("--include-untracked", action="append", default=[])
    start.add_argument("--exclude", action="append", default=[])
    start.add_argument("--delivery-contract", action="store_true")
    start.add_argument("--improve-skill", default="", help=IMPROVE_SKILL_HELP)
    start.add_argument("--bound-plan", default="")
    start.add_argument("--delegation", choices=navigator.DELEGATIONS, default=None,
                       help="new run: inline (default), agents (hybrid reviews + read-only fan-out), or ask-agent")
    start.add_argument("--lint", choices=navigator.LINT_MODES, default=None,
                       help="new run: script-owned advisory lint fix (default), report or off")
    start.add_argument("--planning-review", choices=navigator.PLANNING_REVIEW_MODES, default=None,
                       help="new run: which planning results start an Improve stage, stage (default) or none")
    for name in ("plan-return", "review-return", "return"):
        child = subs.add_parser(name)
        child.add_argument("--workspace-root", required=True)
        if name == "review-return":
            for decision in ("keep", "exclude"):
                child.add_argument("--" + decision, action="append", nargs="+", default=[], metavar="PATH",
                                   help=f"paths (or directories) to {decision}, relative to the execution checkout")
    args = parser.parse_args(argv)
    import shiploop_grants as grants
    rerun = ["python3", str(core.PACKAGE_ROOT / "scripts" / "shiploop"), "workspace", *argv]
    try:
        if args.operation == "start" and not args.workspace_root:
            # A new root under one stable parent, so a sandbox grant made once covers later runs.
            stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime()) + "-" + secrets.token_hex(3)
            args.workspace_root = str(workspace.default_root(Path(args.repo), stamp))
            rerun += ["--workspace-root", args.workspace_root]
            print(f"Workspace root: {args.workspace_root}")
        root = Path(args.workspace_root).absolute()
        if args.operation != "start":
            workspace.require_grants(root)
        if args.operation == "start":
            need(bool(args.prompt.strip()), "prompt must not be empty")
            saved = root / "run" / "state.md"
            if saved.exists():
                existing = store.read_record(saved)
                navigator.validate(existing)
                need(existing.get("prompt") == args.prompt,
                     "new request needs a fresh workspace root; use next for the saved request")
                need(existing.get("execution_mode") == "navigator-worktree",
                     "workspace start cannot replace an existing direct run")
                record = workspace.assert_binding(root, Path(existing["repo"]))
                need(str(Path(args.repo).resolve()) == record["source_repo"],
                     "workspace source differs from this saved run")
                need(sorted({Path(value).as_posix() for value in args.include_untracked})
                     == record["selected_untracked"]
                     and sorted({Path(value).as_posix() for value in args.exclude})
                     == record["excluded"],
                     "workspace start cannot change capture options on retry; use next to recover")
                need(not args.delivery_contract or existing.get("delivery_contract_version") == 1,
                     "cannot retrofit delivery-contract on an existing run")
                _require_retry_delegation(existing, args.delegation, root / "run")
                _require_retry_lint(existing, args.lint, root / "run")
                _require_retry_planning_review(existing, args.planning_review, root / "run")
                # Identical re-entry is recovery, not another capture of the
                # source after product work or a completed integration.
                return main(core, ["next", "--run-dir", str(root / "run")])
            # Both refusals come before anything is created, so a refusal leaves the source as it was.
            _require_card_for_unreviewed_planning(args.planning_review, args.improve_skill)
            # The parent grant is proven before an empty directory becomes a repository.
            workspace.require_parent_grant(root)
            baseline = workspace.bootstrap_empty(Path(args.repo))
            if baseline:
                print(f"Initialized a Git repository in the empty directory {Path(args.repo).resolve()} "
                      f"with an empty baseline commit {baseline[:12]}.")
            record = workspace.prepare(Path(args.repo), root,
                                       args.include_untracked, args.exclude)
            init = ["init", "--repo", record["worktree"],
                    "--run-dir", record["run_dir"],
                    "--execution-mode", "navigator-worktree", "--prompt=" + args.prompt,
                    "--improve-skill=" + args.improve_skill]   # one word: a path that starts with a dash is not another option
            if args.bound_plan:
                init.append("--bound-plan=" + args.bound_plan)
            if args.delivery_contract:
                init.append("--delivery-contract")
            if args.delegation:
                init += ["--delegation", args.delegation]
            if args.lint:
                init += ["--lint", args.lint]
            if args.planning_review:
                init += ["--planning-review", args.planning_review]
            try:
                import shiploop_registry as registry
                source_abs = os.path.abspath(record["source_repo"])
                other_active = [
                    str(item.get("run_id") or item.get("run_key") or "")
                    for item in registry.discover_runs(extra_roots=(root.parent,))
                    if item["state"].get("status") not in ("done", "halted")
                    and os.path.abspath(str(item.get("source_repo") or item.get("repo") or "")) == source_abs
                    and os.path.abspath(str(item["run_dir"])) != os.path.abspath(record["run_dir"])
                ]
                if other_active:
                    print(
                        f"ShipLoop notice: {len(other_active)} other active run(s) target {source_abs} "
                        f"({', '.join(other_active)}); both work in isolated worktrees, and the second "
                        "workspace return will reconcile against the first.",
                        file=sys.stderr,
                    )
            except Exception:  # noqa: BLE001 - informational notice must never block workspace start
                pass
            return main(core, init)
        if args.operation in ("plan-return", "review-return"):
            # Like every run-bound verb, refuse a retired or unloadable run
            # before touching its workspace.
            saved = store.read_record(root / "run" / "state.md")
            navigator.validate(saved)
            workspace.assert_binding(root, Path(saved["repo"]))
            parts = []  # everything this command prints, held to one budget (see _fit)
            try:
                if args.operation == "plan-return":
                    leftover = workspace.commit_leftovers(root)
                    if leftover.commit:
                        parts.append(_Paths("ShipLoop committed these files that were left uncommitted (no action "
                                            "needed): ", leftover.paths, f" ({leftover.commit[:12]})."))
                    workspace.plan_return(root)
                    summary = workspace.plan_summary(root)
                else:
                    reviewed = workspace.review_return(root, [name for group in args.keep for name in group],
                                                       [name for group in args.exclude for name in group])
                    parts.extend(_recorded_parts(reviewed))
                    summary = reviewed["summary"]
                kind = None if summary["pending"] else workspace.expected_return(root)
                expected = None if kind is None else f"{kind} ({workspace.ROUTE_TEXT[kind]})"
                rollback = workspace.rollback_lines(root) if kind else []
                policy = ("Return policy: fast-forward only for a clean starting checkout and a clean committed candidate "
                          "with all reviewed paths kept; otherwise return only the kept working-tree delta, without a "
                          "Git merge or commit." if args.operation == "plan-return" else None)
                parts.extend(_review_parts(core, root, summary, expected, policy, rollback))
            except Exception:
                _emit(parts)  # what ShipLoop already did (the files it committed) stays visible when a later step refuses
                raise
            _emit(parts)
        else:
            saved = store.read_record(root / "run" / "state.md")
            navigator.validate(saved)
            workspace.assert_binding(root, Path(saved["repo"]))
            with core.run_lock(root / "run"):
                saved = core.load_state(root / "run")
                navigator.validate(saved)
                need(saved.get("execution_mode") == "navigator-worktree"
                     and saved.get("status") == "active"
                     and navigator.current_stage(saved) in ("release", "handoff"),
                     "workspace return is allowed only at active release or handoff, "
                     "after the graph's assembled-candidate checks")
                # validate() refuses an Improve child at release or handoff, so
                # return follows the assembled-candidate checks with none active.
                workspace.assert_binding(root, Path(saved["repo"]))
                receipt = workspace.execute_return(root)
            print(f"Verified workspace return: {receipt['kind']}.")
            print(f"Receipt: {root / 'return-receipt.md'}")
            print(f"Original checkout/branch and baseline: {root / 'workspace.md'}")
            print("Return does not advance ShipLoop. Recover the current packet, finish its "
                  "remaining duties, then submit its exact callback:")
            print(shlex.join(["python3", str(core.PACKAGE_ROOT / "scripts" / "shiploop"),
                              "next", "--run-dir", str(root / "run")]))
        return 0
    except grants.GrantError as exc:
        print(grants.report(exc, shlex.join(rerun), starting=(args.operation == "start")), file=sys.stderr)
        return grants.EXIT_GRANT_NEEDED
    except workspace.ReviewRefused as exc:
        # Line 1 carries the verb, the count and the paths: hosts and models read refusals through `head` and `cut`.
        if isinstance(exc, workspace.PendingDispositions):
            parts = [_Paths("ShipLoop workspace blocked: review-return is needed for "
                            f"{len(exc.undecided)} undecided return paths: ", exc.undecided)]
        else:
            parts = [f"ShipLoop workspace blocked: {exc}"]
            if exc.undecided:
                parts.append(_Paths(f"Undecided ({len(exc.undecided)}): ", exc.undecided, "."))
        parts += ["Run: " + navigator.review_return_command(core, root),
                  navigator.REVIEW_RETURN_RULE + " Then run workspace return again."]
        _emit(parts, sys.stderr)
        return 2
    except (workspace.WorkspaceError, ProtocolError, store.StorageError, OSError, ValueError) as exc:
        print(f"ShipLoop workspace blocked: {exc}", file=sys.stderr)
        print("Preserve the workspace and source checkout; do not force, stash, reset, "
              "or create a replacement run to bypass this condition.", file=sys.stderr)
        return 2


def workspace_completion_guard(root: Path, previous: Mapping[str, Any], updated: Mapping[str, Any]) -> None:
    """Enforce decided return plans at ``release-check`` and verified returns at ``release`` and ``handoff``."""
    if previous.get("execution_mode") != "navigator-worktree":
        return
    prev_history = previous.get("history") or ()
    new_rows = [row for row in (updated.get("history") or ())[len(prev_history):] if isinstance(row, Mapping)]
    need_plan = any(row.get("stage") == "release-check" and row.get("outcome") == "done" for row in new_rows)
    need_release_receipt = any(row.get("stage") == "release" and row.get("outcome") == "done" for row in new_rows)
    need_handoff_receipt = updated.get("status") == "done"
    if not (need_plan or need_release_receipt or need_handoff_receipt):
        return
    import shiploop_workspace as workspace

    cli = shlex.quote(str(Path(__file__).resolve().parent / "shiploop"))
    where = shlex.quote(str(root.parent))
    repo = Path(previous["repo"])
    plan_cmds = (f"python3 {cli} workspace plan-return --workspace-root {where}, decide every undecided path "
                 f"with python3 {cli} workspace review-return --workspace-root {where} --keep <paths> --exclude <paths>")
    return_cmds = f"{plan_cmds}, then python3 {cli} workspace return --workspace-root {where}"
    try:
        if need_plan:
            ready, reason = workspace.return_plan_ready(root.parent, repo)
            if not ready:
                need(False, f"release-check requires a current decided return plan ({reason}): run {plan_cmds}")
        for required, stage_label, follow_note in (
            (need_release_receipt, "release", ""),
            (need_handoff_receipt, "handoff",
             " (for example ShipLoop's own docs/shiploop/ commit at release-verify)"),
        ):
            if not required:
                continue
            receipt = workspace.completed_receipt(root.parent, repo)
            if receipt is None:
                if workspace.returned_before(root.parent):
                    need(False, f"{stage_label} requires a current workspace return, and the recorded one is stale: "
                         f"the candidate or source changed after it{follow_note}. Run a follow-up return: "
                         + return_cmds)
                need(False, f"{stage_label} requires a verified workspace return: {return_cmds}")
    except workspace.WorkspaceError as exc:
        raise ProtocolError(str(exc)) from exc


CALLBACK_ATTEMPTS = "callback-attempts"
PACKET_VERBS = frozenset({"next", "resume", "complete", "improve-bind", "improve-start", "improve-pass",
                          "improve-reconcile"})
CALLBACK_VERBS = frozenset({"complete", "check", "improve-bind", "improve-reconcile"})


def _callback_attempts(root: Path) -> int:
    try:
        return int((root / CALLBACK_ATTEMPTS).read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0


def _count_callback_attempt(root: Path) -> None:
    """Record one callback attempt, accepted or refused; state is untouched."""
    try:
        (root / CALLBACK_ATTEMPTS).write_text(str(_callback_attempts(root) + 1) + "\n", encoding="utf-8")
    except OSError:
        pass


def _loop_iteration(root: Path, state: Mapping[str, Any]) -> int:
    """The innermost Until Loop's reported iterations: the active Improve review's, else the current inner stage's.

    Read-only, and never raising (it is a progress hint): 0 when there is no such loop or its receipt cannot be read.
    """
    try:
        child = state.get("active_improve")
        if isinstance(child, dict) and child.get("skill"):
            import shiploop_standalone_improve as standalone
            path = standalone.receipt_path(child)
        else:
            import shiploop_loops as loops
            found = loops.cursor(state)
            if found is None:
                return 0
            path = loops.receipt_path(root, found[1])
        packet = json.loads(Path(path).read_text(encoding="utf-8"))
        return int((packet.get("progress") or {}).get("action_number") or 0)
    except Exception:  # noqa: BLE001 - a read-only progress hint must never fail
        return 0


def hook_status(core: Any, argv: Sequence[str]) -> int:
    """Answer whether a run can still move, for keepalive hooks and the driver.

    Read-only and lock-free: it runs when a host is about to end a turn, so it
    must never wait on a command in progress or recover a transaction.  The one
    JSON line it prints is the whole contract; exit 2 means "no answer".
    """
    parser = argparse.ArgumentParser(prog="shiploop hook-status")
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args(argv)
    root = core.run_dir_from_arg(args.run_dir, walk=False).resolve()
    try:
        state = core.load_state(root)
        retired = navigator.retired_run_reason(state)
        need(retired is None, retired or "")
        navigator.validate(state)
        stage = navigator.current_stage(state)
        profile = navigator.stage_spec.stage_profile(stage)
        action = navigator.current_action(state)
        iteration = _loop_iteration(root, state)
    except SystemExit:
        # core.load_state already printed its reason on stderr.
        print(json.dumps({"run_dir": str(root), "error": "run state cannot be read"}))
        return 2
    except (ProtocolError, navigator.NavigatorError, store.StorageError, OSError,
            KeyError, ValueError, TypeError) as exc:
        print(json.dumps({"run_dir": str(root), "error": str(exc)}))
        return 2
    print(json.dumps({
        "run_dir": str(root),
        "run_id": state["run_id"],
        "repo": state["repo"],
        "status": state["status"],
        "status_reason": state.get("status_reason", ""),
        # A run blocked on a person: the stop stays quiet until their reply resumes it.
        "awaiting": (navigator.awaiting(state) or (None, {}))[1].get("kind", ""),
        "stage": stage,
        "profile": profile,
        "action": (action or {}).get("id"),
        "revision": state["revision"],
        # Keepalive progress: the revision, callback attempts (a refused callback is
        # still work) and the reported iterations of the innermost Until Loop.
        "progress": f"{state['revision']}.{_callback_attempts(root)}.{iteration}",
        # A pending required acknowledgement stays unfinished even if progress is unchanged.
        "completion": navigator.completion_instructions(core, root, state),
        "next": shlex.join(["python3", str(core.PACKAGE_ROOT / "scripts" / "shiploop"),
                            "next", "--run-dir", str(root)]),
    }))
    return 0


def _grant_refusal(core: Any, raw_argv: Sequence[str], run_dir: Optional[Path]) -> Optional[int]:
    """Exit 3 with the repair when an isolated run's grants are gone; else None."""
    if run_dir is None or not (Path(run_dir).parent / "workspace.md").is_file():
        return None
    import shiploop_grants as grants
    import shiploop_workspace as workspace
    try:
        workspace.require_grants(Path(run_dir).parent)
    except grants.GrantError as exc:
        print(grants.report(exc, shlex.join(["python3", str(core.PACKAGE_ROOT / "scripts" / "shiploop"),
                                             *raw_argv]), starting=False), file=sys.stderr)
        return grants.EXIT_GRANT_NEEDED
    except workspace.WorkspaceError:
        pass  # binding problems are reported by the verb's own checks
    return None


def _argv_run_dir(raw_argv: Sequence[str]) -> Optional[Path]:
    """The --run-dir value of a lint/red-check command line, if given."""
    for index, value in enumerate(raw_argv):
        if value == "--run-dir" and index + 1 < len(raw_argv):
            return Path(raw_argv[index + 1]).resolve()
        if value.startswith("--run-dir="):
            return Path(value.split("=", 1)[1]).resolve()
    return None


# What the run trace records about the command in progress: the run directory, the saved state before the verb (set
# only once that state loaded as a current run), whether init created the run, and the refusal text.  Set by
# ``_main``, read by ``main`` once the command has finished.  A command on a retired or unloadable run, or one whose
# command line did not parse, records nothing: it must leave that directory as it was.
_TRACE: dict[str, Any] = {}
# How many ``main`` calls are running.  A command another one runs (``workspace start`` runs init, or next on an
# identical re-entry) is part of that command line: only the outermost is recorded, with the run the inner one loaded.
_DEPTH = [0]


def _in_place_refusal(core: Any, repo: Path, run_dir: Path, in_place: bool, carry: Sequence[str] = ()) -> Optional[str]:
    """Why a new direct-entry run is refused here, or None. `init` works in the folder itself, with no isolated worktree and no
    return protection; in an empty folder that is not a Git repository that is almost always the wrong entry, because
    `workspace start` makes the folder a Git repository, works in a separate worktree and returns the finished work to the
    folder (docs/experiments/start-route-20261101: a request that named the current directory began with `init` there in
    about one session in three on the 2.27.2 card). The user's own request for an in-place or non-Git run is stated with
    --in-place. Git being unusable here (not installed, an ownership refusal) is not the empty-folder case: nothing is
    refused. ``carry`` is the options the refused command carried that `workspace start` also takes (--delivery-contract,
    --delegation, ...): the printed command repeats them, so following it does not drop what the user asked for."""
    if in_place or not repo.is_dir() or repo == run_dir:  # a run directory that is the folder itself is refused later, in its own words
        return None
    try:
        if run_dir.is_dir() and any(entry.name != ".lock" for entry in run_dir.iterdir()):
            return None  # a run directory that is not empty is refused later: nothing here starts a new run
        if any(repo.iterdir()):
            # The folder must be empty in the sense `workspace start` bootstraps (workspace.bootstrap_empty: no entry at all).
            # A run directory made beforehand inside it counts: the printed recovery would not bootstrap such a folder and
            # would fail (checked on 2.31.0 with an empty .shiploop), and a refusal must not point at a command that cannot work.
            return None
    except OSError:
        return None
    try:
        # A neutral locale: the refusal reads Git's "not a git repository" diagnostic, which a translation would change.
        probe = subprocess.run(["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True,
                               check=False, timeout=30, env={**os.environ, "LC_ALL": "C", "LANGUAGE": "C"})
    except (OSError, subprocess.SubprocessError):
        return None
    if probe.returncode == 0 or "not a git repository" not in probe.stderr.lower():
        return None
    cli = shlex.quote(str(core.PACKAGE_ROOT / "scripts" / "shiploop"))
    options = "".join(" " + option for option in carry)
    return (f"{repo} is an empty folder that is not a Git repository, and `init` is the direct entry: it works in the folder "
            f"itself, with no isolated worktree and no return protection. Start this request with the isolated entry, which "
            f"makes the folder a Git repository, works in a separate worktree and returns the finished work to this folder: "
            f"python3 {cli} workspace start --repo {shlex.quote(str(repo))}{options} --prompt='<user request>'. Only if the user "
            f"explicitly asked for an in-place or non-Git run (a request that names the current directory is not that: "
            f"`workspace start` returns the finished work there), run this same `init` command again with --in-place. "
            f"No run was started.")


def _carried_options(args: Any) -> list:
    """The options of an `init` that `workspace start` also takes, as words for the command a refusal prints."""
    carried = []
    if args.improve_skill:
        carried.append("--improve-skill=" + shlex.quote(str(args.improve_skill)))
    if args.bound_plan:   # as `init` records it, so a command run from another folder reads the same file
        carried.append("--bound-plan=" + shlex.quote(str(Path(args.bound_plan).resolve())))
    if args.delivery_contract:
        carried.append("--delivery-contract")
    for name in ("delegation", "lint", "planning_review"):
        value = getattr(args, name, None)
        if value:
            carried.append("--" + name.replace("_", "-") + "=" + shlex.quote(str(value)))
    return carried


def main(core: Any, argv: Optional[Sequence[str]] = None) -> int:
    """Dispatch one ShipLoop command line and record it in the run trace; returns the process exit code."""
    import shiploop_trace

    raw_argv = list(sys.argv[1:] if argv is None else argv)
    outermost = not _DEPTH[0]
    if outermost:
        _TRACE.clear()
    _DEPTH[0] += 1
    started = time.monotonic()
    code = 2
    try:
        code = _main(core, argv)
        return code
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
        raise
    except BaseException as exc:
        # Not ShipLoop's answer: an interrupt (the host or a harness stopped the process) or a crash.  The trace says
        # which, with the exit the process gets, so no reader counts it as a refusal (exit 2, ``EXIT_BLOCKED``).
        code = 130 if isinstance(exc, KeyboardInterrupt) else 1
        _TRACE["crashed"] = type(exc).__name__
        _TRACE["error"] = ("interrupted before the command finished" if code == 130 else
                           f"crashed: {type(exc).__name__}: {exc}")
        raise
    finally:
        _DEPTH[0] -= 1
        if outermost:  # an inner command's packets stay in the trace until the command line that ran it ends
            shiploop_trace.ACTIVE = False
            _record_command(raw_argv, code, started)


def _record_command(raw_argv: Sequence[str], code: int, started: float) -> None:
    """Append the finished command to its run's trace.  The state after it was captured inside the run lock, so a
    command that ran next is never credited to this one; a refused command saved nothing, so its after is its before.
    Only a command that loaded a current run (or created one) is traced: the display verbs and the routed verbs (lint,
    red-check, backchain-check), which never load it here, are not."""
    import shiploop_trace as trace

    root = _TRACE.get("root")
    if not raw_argv or root is None:
        return
    if _TRACE.get("before") is None and not _TRACE.get("created"):
        return
    after = _TRACE.get("after", _TRACE.get("before"))
    trace.record_command(root, raw_argv, code, started, before=_TRACE.get("before"),
                         after=after if isinstance(after, dict) else None, error=_TRACE.get("error"),
                         note=_TRACE.get("note"), crashed=_TRACE.get("crashed"))


def _saved_state(root: Path) -> Optional[dict]:
    """``state.md`` as saved, or None when it cannot be read (the trace then records no after-state)."""
    try:
        state = store.read_record(root / "state.md")
    except (OSError, ValueError, store.StorageError):
        return None
    return state if isinstance(state, dict) else None


def _format_runs_text(payload: Mapping[str, Any], cli_path: Path, *, active_only: bool = False) -> str:
    runs = payload.get("runs") or []
    if active_only:
        runs = [row for row in runs if row.get("status") not in ("done", "halted")]
    lines: list[str] = []
    if not runs:
        lines.append("No active ShipLoop runs discovered." if active_only else "No ShipLoop runs discovered.")
    else:
        for row in runs:
            inf = row.get("inflight") or {}
            extras = []
            if inf.get("step_id") and inf.get("step_total"):
                extras.append(f"Step {inf['step_id']} {inf.get('step_number')}/{inf['step_total']}")
            if inf.get("loop_iteration"):
                extras.append(f"loop pass {inf['loop_iteration']}")
            if inf.get("improve_active"):
                extras.append("improve" + (f" ({inf['improve_review_mode']})" if inf.get("improve_review_mode") else ""))
            if inf.get("open_notes"):
                extras.append(f"{inf['open_notes']} open note(s)")
            if row.get("planning_summary"):
                extras.append(row["planning_summary"])
            if row.get("attention_reasons"):
                extras.extend(row["attention_reasons"])
            suffix = f" [{' · '.join(extras)}]" if extras else ""
            lines.append(
                f"[{row.get('display_label') or row.get('status')}] {row.get('run_id')} "
                f"({row.get('repo_name') or row.get('repo')}) · {row.get('where')}{suffix}"
            )
            lines.append(f"  Goal: {row.get('goal')} · Run dir: {row.get('run_dir')}")
    conflicts = payload.get("shared_repo_conflicts") or {}
    for repo, ids in sorted(conflicts.items()):
        lines.append(f"Shared source repo warning: {repo} has concurrent runs ({', '.join(ids)})")
    viewer = payload.get("viewer")
    if isinstance(viewer, Mapping) and viewer.get("url"):
        lines.append(f"Viewer running: {str(viewer['url']).rstrip('/')}/")
    else:
        lines.append(f"Launch browser dashboard: python3 {shlex.quote(str(cli_path))} view --serve")
    return "\n".join(lines)


def _run_watch_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    inf = row.get("inflight") or {}
    return (
        row.get("display_status"),
        row.get("stage"),
        row.get("revision"),
        row.get("planning_summary"),
        inf.get("step_id"),
        inf.get("loop_iteration"),
        inf.get("improve_passes"),
        inf.get("last_check_yes"),
        inf.get("open_notes"),
    )


def runs_command(core: Any, argv: Sequence[str]) -> int:
    """List or watch discovered ShipLoop runs across repositories."""
    import shiploop_progress_serve as viewer_mod

    parser = argparse.ArgumentParser(prog="shiploop runs", description="List or watch discovered ShipLoop runs")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit JSON payload")
    parser.add_argument("--active", action="store_true", help="only show non-terminal runs")
    parser.add_argument("--prune", action="store_true", help="remove stale registry entries for missing runs")
    parser.add_argument("--runs-root", action="append", default=[], help="extra run or .shiploop-runs directory")
    parser.add_argument("--watch", action="store_true", help="watch discovered runs until Ctrl-C")
    parser.add_argument("--interval", type=float, default=2.0, help="polling interval in seconds for --watch")
    args = parser.parse_args(argv)
    if args.interval < 0.1:
        parser.error("--interval must be at least 0.1 seconds")
    pruned: list[str] = []
    if args.prune:
        import shiploop_registry as registry
        pruned = registry.prune_registry()
    extra_roots = tuple(Path(item).expanduser().resolve() for item in args.runs_root)
    cli_path = core.PACKAGE_ROOT / "scripts" / "shiploop"
    if args.as_json:
        payload = viewer_mod.hub_runs_payload(extra_roots=extra_roots)
        if args.prune:
            payload["pruned"] = pruned
        if args.active:
            payload["runs"] = [row for row in payload["runs"] if row.get("status") not in ("done", "halted")]
            payload["counts"]["total"] = len(payload["runs"])
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    cache: dict[str, Any] = {}
    payload = viewer_mod.hub_runs_payload(extra_roots=extra_roots, cache=cache)
    if args.prune:
        print(f"Pruned {len(pruned)} stale registry entry(s).", flush=True)
    print(_format_runs_text(payload, cli_path, active_only=args.active), flush=True)
    if not args.watch:
        return 0
    seen = {row["run_dir"]: _run_watch_key(row) for row in payload["runs"]}
    try:
        while True:
            time.sleep(args.interval)
            nxt = viewer_mod.hub_runs_payload(extra_roots=extra_roots, cache=cache)
            for row in nxt["runs"]:
                if args.active and row.get("status") in ("done", "halted"):
                    continue
                key = _run_watch_key(row)
                if seen.get(row["run_dir"]) != key:
                    seen[row["run_dir"]] = key
                    stamp = time.strftime("%H:%M:%S")
                    print(f"[{stamp}] [{row.get('display_label')}] {row.get('run_id')} · {row.get('where')}",
                          flush=True)
    except KeyboardInterrupt:
        return 0
    return 0


def _watch_status(core: Any, root: Path, interval: float) -> int:
    """Print status_block and watch read-only for transitions/loop activity until done/halted or Ctrl-C."""
    import shiploop_progress_data as data
    import shiploop_registry as registry

    if interval < 0.1:
        raise ProtocolError("--interval must be at least 0.1 seconds")
    state = core.load_state(root)
    retired = navigator.retired_run_reason(state)
    need(retired is None, retired or "")
    navigator.validate(state)
    print(navigator.status_block(state), flush=True)
    viewer = registry.active_viewer()
    cli_path = core.PACKAGE_ROOT / "scripts" / "shiploop"
    if isinstance(viewer, Mapping) and viewer.get("url"):
        run_key = registry.safe_run_key(state.get("run_id"), root)
        url = str(viewer["url"]).rstrip("/")
        if viewer.get("mode") == "hub":
            print(f"Viewer: {url}/runs/{run_key}/ (all runs: {url}/)", flush=True)
        else:
            print(f"Viewer: {url}/", flush=True)
    else:
        print(f"Launch browser dashboard: python3 {shlex.quote(str(cli_path))} view --serve", flush=True)

    def sig_of(st: Mapping[str, Any]) -> tuple[Any, ...]:
        inf = data.inflight_activity(root, st)
        return (
            st.get("revision"),
            st.get("status"),
            navigator.display_status(st)[0],
            navigator.current_stage(st),
            inf.get("step_id"),
            inf.get("loop_iteration"),
            inf.get("improve_passes"),
            inf.get("last_check_yes"),
            inf.get("open_notes"),
        )

    last_sig = sig_of(state)
    if state.get("status") in ("done", "halted"):
        return 0
    try:
        while True:
            time.sleep(interval)
            try:
                current = core.load_state(root)
                navigator.validate(current)
            except (SystemExit, OSError, ValueError, navigator.NavigatorError, store.StorageError):
                continue
            cur_sig = sig_of(current)
            if cur_sig != last_sig:
                last_sig = cur_sig
                print(navigator.status_block(current), flush=True)
                if current.get("status") in ("done", "halted"):
                    return 0
    except KeyboardInterrupt:
        return 0


def _main(core: Any, argv: Optional[Sequence[str]] = None) -> int:
    """Dispatch one ShipLoop command line; returns the process exit code."""
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv and raw_argv[0] == "view":
        import shiploop_progress
        return shiploop_progress.main(raw_argv[1:], core=core)
    if raw_argv and raw_argv[0] == "runs":
        return runs_command(core, raw_argv[1:])
    if raw_argv and raw_argv[0] == "trace":
        import shiploop_trace
        return shiploop_trace.main(raw_argv[1:], core=core)
    if raw_argv and raw_argv[0] == "hook-status":
        return hook_status(core, raw_argv[1:])
    if raw_argv and raw_argv[0] == "note":
        # The owner's note: no run lock (a note never waits for the model's command) and no packet (the model, not the
        # owner, reads packets).  Recorded once the run loaded as current.
        import shiploop_owner_notes
        return shiploop_owner_notes.main(raw_argv[1:], trace_record=_TRACE)
    if raw_argv and raw_argv[0] == "workspace":
        return workspace_command(core, raw_argv[1:])
    if raw_argv and raw_argv[0] in ("lint", "red-check"):
        # Both write run state; a lost grant gets the same repair as next.
        refused = _grant_refusal(core, raw_argv, _argv_run_dir(raw_argv))
        if refused is not None:
            return refused
    if raw_argv and raw_argv[0] == "lint":
        import shiploop_lint
        return shiploop_lint.main(core, raw_argv[1:])
    if raw_argv and raw_argv[0] == "red-check":
        return navigator.red_check_command(core, raw_argv[1:])
    if raw_argv and raw_argv[0] == "backchain-check":
        import shiploop_backchain_graph
        return shiploop_backchain_graph.main(core, raw_argv[1:])
    parser = argparse.ArgumentParser(
        prog="shiploop",
        description="Markdown-authoritative, script-navigated session harness",
    )
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("view", help="portable HTML progress snapshot, background observer, and read-only browser hub")
    subs.add_parser("runs", help="list or watch all discovered ShipLoop runs across repositories")
    subs.add_parser("trace", help="read the run trace: every stage done, current or pending, the steps run, each packet "
                                  "as sent, refusals and hook continuations (--action, --json, --html)")
    subs.add_parser("note", help="the run's owner: leave a note the next done result must account for with a row "
                                 "(applied, already, carried or declined; --text or --file)")
    subs.add_parser("workspace", help="isolated start, return-plan review, and guarded return")
    subs.add_parser("lint", help="advisory lint rerun for the current action, or show a stored record part (never gates)")
    subs.add_parser("red-check", help="the test stage's base run without completing: does any new test pass "
                                      "without this item's change? (never counted, never gates)")
    subs.add_parser("backchain-check", help="record-only Backchain graph check of a candidate plan file (never gates)")
    subs.add_parser("hook-status", help="read-only JSON: can this run still move (for keepalive hooks and the driver)")
    hb = subs.add_parser("host-binding", help="read-only JSON: detected native host and its host-bindings/v2 entry")
    hb.add_argument("--host", default="auto",
                    help="auto (default: detect from environment) or an explicit host name")
    navigator_dry_run.add_arguments(subs.add_parser(
        "graph-dry-run", help="inspect navigator routes and prompts without project work"))
    for name in (
        "init",
        "delegation",
        "lint-mode",
        "improve-bind",
        "improve-start",
        "improve-commit",
        "improve-pass",
        "improve-reconcile",
        "next",
        "status",
        "report",
        "context",
        "complete",
        "check",
        "halt",
        "pause",
        "resume",
    ):
        sub = subs.add_parser(name)
        sub.add_argument("--run-dir")
        if name == "init":
            sub.add_argument("--prompt", required=True)
            sub.add_argument("--repo")
            sub.add_argument("--bound-plan", default="")
            sub.add_argument("--execution-mode", choices=("navigator", "navigator-worktree"), default="navigator",
                             help="navigator-worktree is created by workspace start; existing runs retain their recorded mode")
            sub.add_argument("--improve-skill", default="", help=IMPROVE_SKILL_HELP)
            sub.add_argument("--delivery-contract", action="store_true",
                             help="opt a new run in to consumer-delivery declaration checks")
            # Named by the refusal, not by --help: a session that has chosen the direct entry by mistake reads --help first
            # and would pass the flag in advance, so the refusal that asks "did the user ask for this?" would never be seen.
            sub.add_argument("--in-place", action="store_true", help=argparse.SUPPRESS)
            sub.add_argument("--delegation", choices=navigator.DELEGATIONS, default=None,
                             help="new run: inline (default), agents (hybrid reviews + read-only fan-out), or ask-agent")
            sub.add_argument("--lint", choices=navigator.LINT_MODES, default=None,
                             help="new run: script-owned advisory lint fix (default), report or off")
            sub.add_argument("--planning-review", choices=navigator.PLANNING_REVIEW_MODES, default=None,
                             help="new run: which planning results start an Improve stage, stage (default) or none")
        if name == "delegation":
            sub.add_argument("--set", dest="delegation_value", choices=navigator.DELEGATIONS, required=True,
                             help="execution delegation for this run's future assignments")
        if name == "lint-mode":
            sub.add_argument("--set", dest="lint_value", choices=navigator.LINT_MODES, required=True,
                             help="script-owned advisory lint for this run's later passes")
        if name == "improve-bind":
            sub.add_argument("--skill-card", required=True)
        if name == "improve-start":
            # ShipLoop starts every Improve stage itself at the transition; this verb only restarts one.
            sub.add_argument("--restart-stopped", action="store_true", required=True,
                             help="archive the Improve stage's stopped or refused review and start it again")
        if name == "improve-commit":
            sub.add_argument("--message", required=True,
                             help="the printed commit-message file, written with a file tool")
            sub.add_argument("--remote-change", dest="remote_change", action="store_true",
                             help="record a change to a remote system that left no file change: the message needs a "
                                  "'Remote change:' section, and with no file pending the commit holds no files")
        if name == "improve-pass":
            sub.add_argument("--no-commit", dest="no_commit",
                             help="the user's or repository's instruction not to commit this review's edits")
        if name in ("complete", "check", "improve-bind", "improve-start", "improve-commit", "improve-pass",
                    "improve-reconcile"):
            sub.add_argument("--action", required=True)
        if name == "improve-reconcile":
            sub.add_argument("--result", required=True)
        if name in ("complete", "check"):
            # Every producer stage reads it; the one path accepted is RUN/inbox/<action>.md, so it may be left out.  An
            # improve stage takes no result (--final-result is its changed result).
            sub.add_argument("--result", help="the result file; default and only accepted path: RUN/inbox/<action>.md")
        if name == "complete":
            sub.add_argument("--notes", metavar="FILE",
                             help="optional: the path of a plain-text file (not the text itself) holding the review's "
                                  "lessons for later steps; the handoff names the file to write")
            sub.add_argument("--final-result", dest="final_result",
                             help="optional step-result record, only when the review changed a decision")
            sub.add_argument("--no-commit", dest="no_commit",
                             help="the user's or repository's instruction not to commit the review's edits")
            sub.add_argument("--review-mode", dest="review_mode", choices=navigator.CLI_REVIEW_MODES, default=None,
                             help="optional (Improve stage only): record how the review ran (fork, fresh, inline, or inline-fallback)")
        if name == "context":
            sub.add_argument("--section", default="navigator")
        if name == "status":
            sub.add_argument("--watch", action="store_true", help="watch this run's status until done/halted or Ctrl-C")
            sub.add_argument("--interval", type=float, default=2.0, help="polling interval in seconds for --watch")
        if name in ("halt", "pause"):
            sub.add_argument("--reason", required=True)
        if name == "resume":
            reply = sub.add_mutually_exclusive_group()
            reply.add_argument("--answer", help="the user's own reply to the question the run is waiting on")
            reply.add_argument("--observed", help="what the person reported after the steps the run waits on, or what an "
                               "outside service's check printed once it exits 0")
    args = parser.parse_args(argv)
    if args.command == "host-binding":
        import shiploop_host_bindings as host_bindings
        try:
            value = host_bindings.report(os.environ, host_override=args.host)
        except (OSError, ValueError, KeyError) as exc:
            print(json.dumps({"code": "bindings_error", "observed": str(exc)}, sort_keys=True, separators=(",", ":")),
                  file=sys.stderr)
            return 2
        print(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        return 0
    if args.command == "graph-dry-run":
        # Deliberately before run-directory discovery, locking or state access.
        return navigator_dry_run.run(args)
    import shiploop_keepalive
    notice = shiploop_keepalive.ensure_hooks()
    if notice:
        print(notice, file=sys.stderr)
    raw_root = args.run_dir
    if args.command == "init" and not raw_root and args.repo:
        raw_root = str(Path(args.repo) / ".shiploop")
    unresolved_root = core.run_dir_from_arg(raw_root, walk=args.command != "init")
    if unresolved_root.is_symlink():
        print("ShipLoop blocked: run directory must not be a symlink", file=sys.stderr)
        return 2
    root = unresolved_root.resolve()
    _TRACE["root"] = root
    if args.command != "init" and not root.is_dir():
        # Only init may create a run directory; the lock would otherwise
        # materialize a mistyped --run-dir (or a stray repo .shiploop/).
        # Keep the established "error:" contract of core.die for a missing run.
        print(f"error: no ShipLoop run directory at {root}; check --run-dir",
              file=sys.stderr)
        return 2
    if args.command not in ("init", "status", "report", "context"):
        refused = _grant_refusal(core, raw_argv, root)
        if refused is not None:
            return refused
    if (args.command == "init" and args.execution_mode != "navigator-worktree" and (args.prompt or "").strip()
            and not (root / "state.md").exists()):
        carry = _carried_options(args)
        refused = _in_place_refusal(core, Path(args.repo or os.getcwd()).resolve(), root, args.in_place, carry)
        if refused:
            print(f"ShipLoop blocked: {refused}", file=sys.stderr)
            return 2
    if args.command == "status" and getattr(args, "watch", False):
        return _watch_status(core, root, args.interval)
    progress_ready = False
    try:
        with core.run_lock(root):
            if (root / "state.md").exists():
                existing = core.load_state(root)
                # A run saved by a removed protocol or mode is refused before
                # any verb-specific check; it never routes into another graph.
                retired = navigator.retired_run_reason(existing)
                if retired is not None:
                    print(f"ShipLoop blocked: {retired}", file=sys.stderr)
                    return 2
                try:
                    navigator.validate(existing)
                except navigator.NavigatorError as exc:
                    # No verb, including init or next, can recover a saved
                    # state this navigator cannot load.
                    print(f"ShipLoop blocked: saved run state cannot be loaded: {exc}",
                          file=sys.stderr)
                    return 2
                _TRACE["before"] = existing
                import shiploop_trace
                shiploop_trace.ACTIVE = True  # this command's packets go in the trace
                if args.command == "init":
                    # Idempotent entry must never substitute a saved request for
                    # a new one.
                    need(
                        args.prompt == existing.get("prompt")
                        and (args.repo is None
                             or str(Path(args.repo).resolve()) == existing.get("repo")),
                        "init request/repository differs from this saved run; "
                        "use next to resume the same request, or a fresh --run-dir "
                        "with the new --prompt for new work. Preserve the prior run; "
                        "completed runs stay complete.",
                    )
                    need(not args.delivery_contract
                         or existing.get("delivery_contract_version") == 1,
                         "--delivery-contract cannot retrofit an existing run; preserve it and use its recorded settings")
                if args.command in CALLBACK_VERBS:
                    # Only a loadable current run counts attempts; refused runs stay untouched.
                    _count_callback_attempt(root)
                _require_retry_delegation(existing, getattr(args, "delegation", None), root)
                _require_retry_lint(existing, getattr(args, "lint", None), root)
                _require_retry_planning_review(existing, getattr(args, "planning_review", None), root)
                if args.command in ("init", "next"):
                    # Recovery may restore only a snapshot's bound HEAD; never capture a resumed run's current bytes.
                    import shiploop_knowledge_home as knowledge_home
                    problem = knowledge_home.repair_baseline_pointer(root)
                    if problem:
                        print("ShipLoop knowledge: the run baseline pointer was not repaired (" + problem
                              + "); packets print the spec diff as not recorded.", file=sys.stderr)
                code = navigator.dispatch(
                    core, root, existing, args,
                    completion_guard=lambda before, after: workspace_completion_guard(root, before, after),
                )
                # The run trace's after-state, read while this command still holds the lock.
                _TRACE["after"] = (existing if args.command in ("status", "context", "report")
                                   else _saved_state(root))
                if args.command in PACKET_VERBS:
                    import shiploop_keepalive
                    health = shiploop_keepalive.health_notice(str(root))
                    if health:
                        print(health, file=sys.stderr)
                progress_ready = code == 0 and args.command in (PACKET_VERBS | {"init", "pause", "halt"})
                return code
            if (root / "state.json").exists():
                print(f"ShipLoop blocked: {navigator.retired_json_run_reason(root)}", file=sys.stderr)
                return 2
            need(args.command != "delegation",
                 "delegation needs an existing run; choose it with --delegation at init or "
                 "workspace start")
            need(args.command != "lint-mode",
                 "lint-mode needs an existing run; choose it with --lint at init or workspace start")
            if args.command != "init":
                core.die(core.EXIT_BLOCKED, f"no authoritative state.md in {root}")
            need(bool(args.prompt.strip()), "prompt must not be empty")
            need(
                not any(path.name != ".lock" for path in root.iterdir()),
                "new run directory must be dedicated and empty; choose a fresh --run-dir to preserve existing files",
            )
            repo = Path(args.repo or os.getcwd()).resolve()
            need(root != repo, "run directory cannot be the product repository root")
            _require_card_for_unreviewed_planning(args.planning_review, args.improve_skill)
            if args.execution_mode == "navigator-worktree":
                import shiploop_workspace as workspace
                try:
                    binding = workspace.assert_binding(root.parent, Path(args.repo or os.getcwd()))
                    need(binding["run_dir"] == str(root),
                         "workspace navigator must use its prepared run directory")
                except workspace.WorkspaceError as exc:
                    raise ProtocolError(str(exc)) from exc
            state = navigator.new_state(
                str(repo), args.prompt,
                str(Path(args.bound_plan).resolve()) if args.bound_plan else "",
                improve_skill=_new_run_card(args.improve_skill),
                delivery_contract=args.delivery_contract,
                worktree=args.execution_mode == "navigator-worktree",
                delegation=args.delegation or navigator.DEFAULT_DELEGATION,
                lint_option=args.lint or navigator.DEFAULT_LINT,
                planning_review=args.planning_review or navigator.DEFAULT_PLANNING_REVIEW,
            )
            navigator.save(root, state)
            _TRACE["created"], _TRACE["after"] = True, state
            import shiploop_trace
            shiploop_trace.ACTIVE = True
            # The run baseline (consumer contract, owner decision D3): what the execution checkout held before any
            # commit of this run, so later packets can quote the spec and architecture diff since then.  A note, never
            # a refusal.
            import shiploop_knowledge_home as knowledge_home
            problem = knowledge_home.record_baseline(root, state)
            if problem:
                print("ShipLoop knowledge: the run baseline was not recorded (" + problem + "); packets print the "
                      "spec diff as not recorded.", file=sys.stderr)
            navigator.emit(core, root, state)
            progress_ready = True
            return 0
    except navigator.NavigatorError as exc:
        _TRACE["error"] = str(exc)
        if args.command == "check":
            # A result refused for its owner notes leads with them (``navigator.NotesOwed``): its first line names the
            # notes, their folder and the result file, so a host that shows only that line still says what to do.
            print(f"ShipLoop check: {exc}" if isinstance(exc, navigator.NotesOwed) else
                  f"ShipLoop check: the check says no. {exc}", file=sys.stderr)
            print("Nothing was accepted or counted. Fix the cause and run the check again in this turn.",
                  file=sys.stderr)
            return 2
        print(f"ShipLoop navigator: {exc}", file=sys.stderr)
        print("Read the current packet with next; the rejected request did not advance the graph.",
              file=sys.stderr)
        print("The run is still active: fix the result and resubmit in this turn; do not end the "
              "turn over a refused callback.", file=sys.stderr)
        return 2
    except (ProtocolError, store.StorageError, OSError, KeyError, ValueError, TypeError) as exc:
        _TRACE["error"] = str(exc)
        print(f"ShipLoop blocked: {exc}", file=sys.stderr)
        # A rejected result may have changed only the in-memory candidate.
        # Rehydrate the durable cursor; never suggest an inferred next stage.
        recovery = shlex.join([
            "python3", str(core.PACKAGE_ROOT / "scripts" / "shiploop"),
            "next", "--run-dir", str(root),
        ])
        print(
            "Request failure: no in-memory result, candidate, or rejected artifact is trusted.",
            file=sys.stderr,
        )
        print(
            "Durable cursor recovery: the printed command rehydrates only safely available durable orientation from authoritative Markdown. Do not infer a next action from this error; follow the recovery packet.",
            file=sys.stderr,
        )
        print(
            "Broader purpose: unavailable in this failure response; the recovery packet reports what can be recovered and what remains unavailable.",
            file=sys.stderr,
        )
        print(f"Recover the current durable action: {recovery}", file=sys.stderr)
        return 2
    finally:
        # The workflow lock has been released. Observation and run registration
        # are separate, best-effort helpers and never own an action or recovery.
        if progress_ready:
            try:
                after_state = _TRACE.get("after")
                if isinstance(after_state, Mapping):
                    import shiploop_registry as registry
                    registry.register_run(root, after_state)
            except Exception:  # noqa: BLE001 - registry writes must never fail a transition
                pass
            import shiploop_progress
            shiploop_progress.ensure(root)
