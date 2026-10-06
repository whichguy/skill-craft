"""ShipLoop CLI protocol: argument parsing, run-directory locking and routing.

The navigator (shiploop_navigator) owns the graph, the durable cursor and the
packet for the current step.  This module parses the CLI, holds the run lock,
refuses saved runs from removed protocols, and hands every verb for a
protocol 4 run to ``navigator.dispatch``.  Workspace effects and chain
operations stay in their own modules.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shlex
import sys
import time
from pathlib import Path

import shiploop_git
import shiploop_navigator as navigator
import shiploop_navigator_dry_run as navigator_dry_run
import shiploop_store as store


class ProtocolError(RuntimeError):
    pass


def need(ok, message):
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


def _require_retry_backchain_passes(existing: dict, requested: "str | None", run_dir: Path) -> None:
    """Recovery retries keep the recorded Backchain passes option; no verb changes it mid-run."""
    _require_retry_fixed_option(requested, "--backchain-passes", "Backchain passes option",
                                navigator.recorded_backchain_passes(existing))


def _require_retry_planning_review(existing: dict, requested: "str | None", run_dir: Path) -> None:
    """Recovery retries keep the recorded planning review option; no verb changes it mid-run."""
    _require_retry_fixed_option(requested, "--planning-review", "planning review option",
                                navigator.recorded_planning_review(existing))


def workspace_command(core, argv):
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
    start.add_argument("--improve-skill", default="")
    start.add_argument("--delegation", choices=navigator.DELEGATIONS, default=None,
                       help="new run: inline (default) or ask-agent delegation")
    start.add_argument("--lint", choices=navigator.LINT_MODES, default=None,
                       help="new run: script-owned advisory lint fix (default), report or off")
    start.add_argument("--backchain-passes", choices=navigator.BACKCHAIN_PASSES_MODES, default=None,
                       help="new run: Backchain planning child passes, one (default), converge or none")
    start.add_argument("--planning-review", choices=navigator.PLANNING_REVIEW_MODES, default=None,
                       help="new run: which planning results start an Improve child, stage (default) or none")
    for name in ("plan-return", "return"):
        child = subs.add_parser(name)
        child.add_argument("--workspace-root", required=True)
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
            # Screen before workspace.prepare creates a worktree and branch.
            import shiploop_privacy
            need(not shiploop_privacy.sensitive_text(args.prompt),
                 "prompt appears to contain a credential secret; remove it and name the "
                 "credential's location instead (the value is not echoed)")
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
                _require_retry_backchain_passes(existing, args.backchain_passes, root / "run")
                _require_retry_planning_review(existing, args.planning_review, root / "run")
                # Identical re-entry is recovery, not another capture of the
                # source after product work or a completed integration.
                return main(core, ["next", "--run-dir", str(root / "run")])
            # The parent grant is proven before an empty directory becomes a
            # repository, so a refusal leaves the source exactly as it was.
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
                    "--improve-skill", args.improve_skill]
            if args.delivery_contract:
                init.append("--delivery-contract")
            if args.delegation:
                init += ["--delegation", args.delegation]
            if args.lint:
                init += ["--lint", args.lint]
            if args.backchain_passes:
                init += ["--backchain-passes", args.backchain_passes]
            if args.planning_review:
                init += ["--planning-review", args.planning_review]
            return main(core, init)
        if args.operation == "plan-return":
            # Like every run-bound verb, refuse a retired or unloadable run
            # before touching its workspace.
            saved = store.read_record(root / "run" / "state.md")
            navigator.validate(saved)
            workspace.assert_binding(root, Path(saved["repo"]))
            leftover = workspace.commit_leftovers(root)
            if leftover.commit:
                print("Committed files left uncommitted in the candidate: " + ", ".join(leftover.paths)
                      + f" ({leftover.commit[:12]}).")
            if leftover.skipped:
                print(shiploop_git.skipped_notice(leftover.skipped))
            workspace.plan_return(root)
            print(f"Review all keep/exclude dispositions in {root / 'return-plan.md'}.")
            print("Keep only intended product changes and durable knowledge, not run artifacts.")
            print("Return policy: fast-forward only for a clean starting checkout and a "
                  "clean committed candidate with all reviewed paths kept; otherwise return "
                  "only the kept working-tree delta, without a Git merge or commit.")
            print("When reviewed, run:")
            print(shlex.join(["python3", str(core.PACKAGE_ROOT / "scripts" / "shiploop"),
                              "workspace", "return", "--workspace-root", str(root)]))
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
                  "remaining duties, then submit its exact completion call:")
            print(shlex.join(["python3", str(core.PACKAGE_ROOT / "scripts" / "shiploop"),
                              "next", "--run-dir", str(root / "run")]))
        return 0
    except grants.GrantError as exc:
        print(grants.report(exc, shlex.join(rerun)), file=sys.stderr)
        return grants.EXIT_GRANT_NEEDED
    except (workspace.WorkspaceError, ProtocolError, store.StorageError, OSError, ValueError) as exc:
        print(f"ShipLoop workspace blocked: {exc}", file=sys.stderr)
        print("Preserve the workspace and source checkout; do not force, stash, reset, "
              "or create a replacement run to bypass this condition.", file=sys.stderr)
        return 2


def workspace_completion_guard(root, previous, updated):
    """A new isolated run cannot declare completion before verified return."""
    if (previous.get("execution_mode") == "navigator-worktree"
            and updated.get("status") == "done"):
        import shiploop_workspace as workspace
        try:
            receipt = workspace.completed_receipt(root.parent, Path(previous["repo"]))
            if receipt is None:
                cli = shlex.quote(str(Path(__file__).resolve().parent / "shiploop"))
                where = shlex.quote(str(root.parent))
                commands = (f"python3 {cli} workspace plan-return --workspace-root {where}, review the plan, "
                            f"then python3 {cli} workspace return --workspace-root {where}")
                if workspace.returned_before(root.parent):
                    need(False, "handoff requires a current workspace return, and the recorded one is stale: "
                         "the candidate or source changed after it (for example ShipLoop's own docs/shiploop/ "
                         "commit at release-verify). Run a follow-up return: " + commands)
                need(False, "handoff requires a verified workspace return: " + commands)
        except workspace.WorkspaceError as exc:
            raise ProtocolError(str(exc)) from exc


CALLBACK_ATTEMPTS = "callback-attempts"
PACKET_VERBS = frozenset({"next", "resume", "complete", "improve-bind", "improve-start", "improve-complete",
                          "improve-reconcile"})
CALLBACK_VERBS = frozenset({"complete", "improve-bind", "improve-complete", "improve-reconcile"})


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


def _improve_pass(state) -> int:
    """The active Improve review's pass number from its runtime receipt; 0 when unknown."""
    child = state.get("active_improve")
    if not isinstance(child, dict) or not child.get("skill"):
        return 0
    try:
        import shiploop_standalone_improve as standalone
        packet = json.loads(standalone.receipt_path(child).read_text(encoding="utf-8"))
        return int((packet.get("progress") or {}).get("action_number") or 0)
    except Exception:  # noqa: BLE001 - a read-only status hint must never fail
        return 0


def hook_status(core, argv):
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
        action = navigator.current_action(state)
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
        "action": (action or {}).get("id"),
        "revision": state["revision"],
        # Keepalive progress: the revision, callback attempts (a refused callback is
        # still work) and the active Improve review's pass count.
        "progress": f"{state['revision']}.{_callback_attempts(root)}.{_improve_pass(state)}",
        "next": shlex.join(["python3", str(core.PACKAGE_ROOT / "scripts" / "shiploop"),
                            "next", "--run-dir", str(root)]),
    }))
    return 0


def _grant_refusal(core, raw_argv, run_dir):
    """Exit 3 with the repair when an isolated run's grants are gone; else None."""
    if run_dir is None or not (Path(run_dir).parent / "workspace.md").is_file():
        return None
    import shiploop_grants as grants
    import shiploop_workspace as workspace
    try:
        workspace.require_grants(Path(run_dir).parent)
    except grants.GrantError as exc:
        print(grants.report(exc, shlex.join(["python3", str(core.PACKAGE_ROOT / "scripts" / "shiploop"),
                                             *raw_argv])), file=sys.stderr)
        return grants.EXIT_GRANT_NEEDED
    except workspace.WorkspaceError:
        pass  # binding problems are reported by the verb's own checks
    return None


def _argv_run_dir(raw_argv):
    """The --run-dir value of a chain/lint command line, if given."""
    for index, value in enumerate(raw_argv):
        if value == "--run-dir" and index + 1 < len(raw_argv):
            return Path(raw_argv[index + 1]).resolve()
        if value.startswith("--run-dir="):
            return Path(value.split("=", 1)[1]).resolve()
    return None


def main(core, argv=None):
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv and raw_argv[0] == "view":
        import shiploop_progress
        return shiploop_progress.main(raw_argv[1:], core=core)
    if raw_argv and raw_argv[0] == "hook-status":
        return hook_status(core, raw_argv[1:])
    if raw_argv and raw_argv[0] == "workspace":
        return workspace_command(core, raw_argv[1:])
    if raw_argv and raw_argv[0] in ("chain", "lint"):
        # Both write run state; a lost grant gets the same repair as next.
        refused = _grant_refusal(core, raw_argv, _argv_run_dir(raw_argv))
        if refused is not None:
            return refused
    if raw_argv and raw_argv[0] == "chain":
        import shiploop_chain
        return shiploop_chain.main(core, raw_argv[1:])
    if raw_argv and raw_argv[0] == "lint":
        import shiploop_lint
        return shiploop_lint.main(core, raw_argv[1:])
    if raw_argv and raw_argv[0] == "backchain-check":
        import shiploop_backchain_graph
        return shiploop_backchain_graph.main(core, raw_argv[1:])
    parser = argparse.ArgumentParser(
        prog="shiploop",
        description="Markdown-authoritative, script-navigated session harness",
    )
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("view", help="portable HTML progress snapshot and read-only background observer")
    subs.add_parser("workspace", help="isolated start, return-plan review, and guarded return")
    subs.add_parser("chain", help="bind and operate a parallel or serial chain within the current implementation action")
    subs.add_parser("lint", help="advisory lint rerun for the current action, or show a stored record part (never gates)")
    subs.add_parser("backchain-check", help="record-only Backchain graph check of a candidate plan file (never gates)")
    subs.add_parser("hook-status", help="read-only JSON: can this run still move (for keepalive hooks and the driver)")
    navigator_dry_run.add_arguments(subs.add_parser(
        "graph-dry-run", help="inspect navigator routes and prompts without project work"))
    for name in (
        "init",
        "delegation",
        "lint-mode",
        "improve-bind",
        "improve-start",
        "improve-commit",
        "improve-complete",
        "improve-reconcile",
        "next",
        "status",
        "report",
        "context",
        "complete",
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
            sub.add_argument("--improve-skill", default="")
            sub.add_argument("--delivery-contract", action="store_true",
                             help="opt a new run in to consumer-delivery declaration checks")
            sub.add_argument("--delegation", choices=navigator.DELEGATIONS, default=None,
                             help="new run: inline (default) or ask-agent delegation")
            sub.add_argument("--lint", choices=navigator.LINT_MODES, default=None,
                             help="new run: script-owned advisory lint fix (default), report or off")
            sub.add_argument("--backchain-passes", choices=navigator.BACKCHAIN_PASSES_MODES, default=None,
                             help="new run: Backchain planning child passes, one (default), converge or none")
            sub.add_argument("--planning-review", choices=navigator.PLANNING_REVIEW_MODES, default=None,
                             help="new run: which planning results start an Improve child, stage (default) or none")
        if name == "delegation":
            sub.add_argument("--set", dest="delegation_value", choices=navigator.DELEGATIONS, required=True,
                             help="execution delegation for this run's future assignments")
        if name == "lint-mode":
            sub.add_argument("--set", dest="lint_value", choices=navigator.LINT_MODES, required=True,
                             help="script-owned advisory lint for this run's later passes")
        if name == "improve-bind":
            sub.add_argument("--skill-card", required=True)
        if name == "improve-start":
            sub.add_argument("--opening", required=True,
                             help="the printed opening file: the four sections only the parent knows")
            sub.add_argument("--restart-stopped", action="store_true",
                             help="archive a stopped child's receipt and reviews, then start a new child")
        if name == "improve-commit":
            sub.add_argument("--message", required=True,
                             help="the printed commit-message file, written with a file tool")
        if name in ("complete", "improve-bind", "improve-start", "improve-commit", "improve-complete",
                    "improve-reconcile"):
            sub.add_argument("--action", required=True)
        if name in ("complete", "improve-reconcile"):
            sub.add_argument("--result", required=True)
        if name == "improve-complete":
            sub.add_argument("--notes", help="optional plain-text lessons from the review, for later steps")
            sub.add_argument("--final-result", dest="final_result",
                             help="optional step-result record, only when the review changed a decision")
            sub.add_argument("--no-commit", dest="no_commit",
                             help="the user's or repository's instruction not to commit the review's edits")
        if name == "context":
            sub.add_argument("--section", default="navigator")
        if name in ("halt", "pause"):
            sub.add_argument("--reason", required=True)
        if name == "resume":
            reply = sub.add_mutually_exclusive_group()
            reply.add_argument("--answer", help="the user's own reply to the question the run is waiting on")
            reply.add_argument("--observed", help="what the person reported after the steps the run waits on")
    args = parser.parse_args(argv)
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
                _require_retry_backchain_passes(existing, getattr(args, "backchain_passes", None), root)
                _require_retry_planning_review(existing, getattr(args, "planning_review", None), root)
                code = navigator.dispatch(
                    core, root, existing, args,
                    completion_guard=lambda before, after: workspace_completion_guard(root, before, after),
                )
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
                improve_skill=args.improve_skill,
                delivery_contract=args.delivery_contract,
                worktree=args.execution_mode == "navigator-worktree",
                delegation=args.delegation or navigator.DEFAULT_DELEGATION,
                lint_option=args.lint or navigator.DEFAULT_LINT,
                backchain_passes=args.backchain_passes or navigator.DEFAULT_BACKCHAIN_PASSES,
                planning_review=args.planning_review or navigator.DEFAULT_PLANNING_REVIEW,
            )
            navigator.save(root, state)
            navigator.emit(core, root, state)
            progress_ready = True
            return 0
    except navigator.NavigatorError as exc:
        print(f"ShipLoop navigator: {exc}", file=sys.stderr)
        print("Read the current packet with next; the rejected request did not advance the graph.",
              file=sys.stderr)
        print("The run is still active: fix the result and resubmit in this turn; do not end the "
              "turn over a refused callback.", file=sys.stderr)
        return 2
    except (ProtocolError, store.StorageError, OSError, KeyError, ValueError, TypeError) as exc:
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
        # The workflow lock has been released. Observation is a separate,
        # best-effort file publisher and never owns an action or recovery.
        if progress_ready:
            import shiploop_progress
            shiploop_progress.ensure(root)
