"""Attended entry point for the internal Grok Bot Salesforce discovery case."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from hosted_outcome import attempt, binding, operator_lifecycle as op


def state_path(operator):
    key = binding.sha(binding.encoded([str(operator.campaign), operator.build, operator.binding_sha256]))
    return attempt.registry(operator.binding) / key


def check_attempt(operator, state):
    operator.check_context(attempt.read(state / "start.json"))
    pin = state / "operator-config.json"
    if os.path.lexists(pin):
        op.require(op.read(pin) == {"config_sha256": operator.config_sha256,
                                    "binding_sha256": operator.binding_sha256}, "OPERATOR_ATTEMPT_CONFIG_MISMATCH")


def dispatch(args):
    digest = args.expected_sha256
    if args.command == "preflight" and digest is None:
        digest = binding.sha(binding.absolute(args.config).read_bytes())
    operator = op.Operator(args.config, digest)
    state = state_path(operator)
    if args.command in {"reconcile", "plan-retirement", "retire"}:
        op.require(args.state == state, "RECONCILIATION_ATTEMPT_MISMATCH")
        check_attempt(operator, state)
        now = time.time()
        deadline = operator.deadline if args.cleanup_deadline is None else args.cleanup_deadline
        if now < operator.build_until:
            closure = state / "build-closed.json"
            op.require(closure.is_file() and op.read(closure) == attempt.phase_receipt(state),
                       "BUILD_CUTOFF_NOT_REACHED")
        op.require(now < deadline < 10**12, "CLEANUP_DEADLINE_EXPIRED")
        if args.command == "reconcile":
            return attempt.reconcile(operator.binding_path, state, deadline=deadline, cleanup=operator.cleanup,
                                     retain=operator.retain)
        kwargs = {}
        if args.command == "retire":
            kwargs = {"retire": operator.retire, "approval": args.approval, "approval_sha256": args.approval_sha256}
        return attempt.retirement(operator.binding_path, state, deadline=deadline,
                                  plan_retirement=operator.plan_retirement, **kwargs)

    if state.exists():
        check_attempt(operator, state)
    else:
        op.require(not os.path.lexists(operator.output), "FRESH_OUTPUT_REQUIRED")
    replay = args.command == "run" and state.exists() and operator.binding.get("review_hold") is True
    prepared = {"model": None} if replay else operator.preflight()
    if args.command == "preflight":
        return {"state": "PREFLIGHT_VALIDATED", "state_dir": str(state), "output": str(operator.output), **prepared}
    return attempt.execute(
        operator.binding_path, campaign=str(operator.campaign), build=operator.build,
        codex_bin=operator.codex_bin, model=prepared["model"], baseline=operator.baseline,
        deadline=operator.deadline, observation_seconds=operator.observation_seconds,
        teardown_seconds=operator.teardown_seconds, reset=operator.reset, observe=operator.observe,
        cleanup=operator.cleanup, retain=operator.retain,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("preflight", "run", "reconcile", "plan-retirement", "retire"):
        sub = commands.add_parser(command)
        sub.add_argument("--config", type=Path, required=True)
        sub.add_argument("--expected-sha256", required=command != "preflight",
                         help="SHA256 independently authorized by the operator")
        if command in {"reconcile", "plan-retirement", "retire"}:
            sub.add_argument("--state", type=Path, required=True, help="known attempt state directory")
            sub.add_argument("--cleanup-deadline", type=float,
                             help="absolute Unix cutoff for reconciliation or retirement work")
        if command == "retire":
            sub.add_argument("--approval", type=Path, required=True, help="owner-authorized exact retirement approval")
            sub.add_argument("--approval-sha256", required=True, help="SHA256 of the authorized approval bytes")
    try:
        result = dispatch(parser.parse_args(argv))
    except (op.Refusal, OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError) as exc:
        reason = str(exc) if isinstance(exc, op.Refusal) else type(exc).__name__
        print(f"hosted operator refused ({reason})", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result.get("state") in {"PREFLIGHT_VALIDATED", "SETTLED", "RETAINED_QUIESCENT",
                                       "RETIREMENT_PLANNED"} else 1


if __name__ == "__main__":
    sys.exit(main())
