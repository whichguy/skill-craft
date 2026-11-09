"""Optional one-turn live collector smoke, separate from the native subject boundary."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "operator"), str(ROOT / "coordination")]

from dispatch import frozen_inputs, sha, verify_runtime
from runner import _capture_invocation, _raw_translator, load_harness, wall_time
from v7 import auth_cleanup, registration as protocol, telemetry
from v7.report_context import fresh_output, private_dir, private_file, json_bytes


def collect(args):
    registration = protocol.read(ROOT / "registration.json")
    registration, _, digest = frozen_inputs(ROOT, Path(registration["harness_root"]), registration["harness_head"])
    approval = args.authorization.absolute()
    if (not args.authorize_live or registration["purpose"] != "smoke"
            or approval != approval.resolve() or not approval.is_file() or not approval.stat().st_size
            or str(approval) == registration["authorization"]["path"] or not 1 <= args.timeout <= 120):
        raise ValueError("retain separate collector authorization and a bounded smoke registration")
    out = private_dir(fresh_output(args.output, inputs=(ROOT, registration["harness_root"], approval)))
    binding = {"purpose": "natural-parent-collector-smoke", "registration_sha256": digest,
               "trial": str(out), "authorization_sha256": sha(approval)}
    private_file(out / "start.json", json_bytes(binding))
    # This process controls its own output mask. Subject/native scope modes are not involved.
    os.umask(0o077)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    harness = load_harness(Path(registration["harness_root"]), registration["harness_head"])
    harness.run.install_termination_handlers()
    work = private_dir(out / "work")
    host = harness.hosts.host("codex", registration["codex_bin"])
    sessions = []
    roles = registration["roles"]["subject"]
    process = None
    try:
        env = host.env(out / "home")
        verify_runtime(registration, env)
        argv = host.argv(prompt="Reply with exactly COLLECTOR-OK. Do not use tools or start another agent.",
                         prompt_file=out / "host-prompt.txt", cwd=work, **roles, permission_mode="auto",
                         max_turns=None, max_budget_usd=None, plugin_dir=None)
        argv[argv.index("-s") + 1] = "read-only"
        protocol.validate_launch(argv, host.binary, cwd=work)
        launch = None

        def start(_):
            nonlocal launch
            launch = telemetry.append_start(out, binding, cwd=work, home=env["CODEX_HOME"], **roles,
                                            started_at=wall_time(), resumed=None, raw_start=0, argv=argv)

        raw = out / "raw-events.jsonl"
        process = harness.run.launch(argv, work, out, env, args.timeout, False, first=True, fresh=True,
                                     translate=_raw_translator(host, raw), before_start=start)
        process.update(launch=launch, raw_usage_bytes=[0, raw.stat().st_size if raw.exists() else 0])
        _capture_invocation(out, env, sessions, process)
    finally:
        cleanup = harness.run.lifecycle.cleanup(out)
        drained = (cleanup.get("observed") is True
                   and not any(cleanup.get(key) for key in ("survived", "unverified", "protected")))
        cleanup["auth_link"] = auth_cleanup.cleanup_auth_link(out, drained=drained)
        result = telemetry.ledger_usage(out, sessions, binding, roles=roles)
        private_file(out / "sessions.json", json_bytes(sessions))
        private_file(out / "usage.json", json_bytes(result))
        private_file(out / "cleanup.json", json_bytes(cleanup))
    complete = (process is not None and process.get("status") == "exited" and process.get("returncode") == 0
                and drained and cleanup["auth_link"]["status"] in ("absent", "removed")
                and result["started_invocations"] == 1 and result["usage_complete"])
    print(json.dumps({"status": "COLLECTOR_COMPLETE" if complete else "INCOMPLETE",
                      "started_invocations": result["started_invocations"], "output": str(out)}))
    return 0 if complete else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--authorize-live", action="store_true")
    p.add_argument("--authorization", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--timeout", type=int, default=90)
    args = p.parse_args()
    try:
        return collect(args)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        p.exit(2, f"Collector smoke refused or incomplete: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
