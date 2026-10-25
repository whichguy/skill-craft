#!/usr/bin/env python3
"""Room a required owner-notes block would have in each stage's printed head (design evidence, 2026-10-25).

For every active producer packet of the two-item fixture run of test/shiploop-head-order.test.py, at the normal install
(83-character run directory, 96-character CLI path): HEAD_LIMIT minus the head's required text (tiers P0 and P1) and
its end line.  The optional blocks (lookups, chrome, quoted files) give way to a required block, so this is the most a
notes block can take before the print passes 20,000 characters.  Prints the worst row of each stage.

    python3 docs/shiploop-owner-notes-evidence/head-room.py
"""
import importlib.util
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for part in ("skills/shiploop/scripts", "test/shiploop_e2e", "test"):
    sys.path.insert(0, str(ROOT / part))
spec = importlib.util.spec_from_file_location("head_order", ROOT / "test/shiploop-head-order.test.py")
head_order = importlib.util.module_from_spec(spec)
spec.loader.exec_module(head_order)
import packets  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402

worst: dict = {}
for route in ("inline", "ask-agent"):
    rows = head_order.renders(route, head_order.INSTALL_RUN_DIR)
    with tempfile.TemporaryDirectory(prefix="sl-") as temp:
        scratch = Path(temp)
        work = Path(packets.padded_path(str(scratch), head_order.INSTALL_RUN_DIR - len("/run"), "p"))
        work.mkdir(parents=True)
        run = work / "run"
        run.mkdir()
        package = Path(packets.padded_path(str(scratch), head_order.CLI_PATH_LENGTH - len(packets.CLI_TAIL), "c"))
        package.parent.mkdir(parents=True, exist_ok=True)
        package.symlink_to(Path(navigator.__file__).resolve().parents[1], target_is_directory=True)
        core = types.SimpleNamespace(PACKAGE_ROOT=package)
        for key, row in rows.items():
            state = row["state"]
            if not head_order.plans.is_producer(key, state):
                continue
            blocks = navigator._producer_blocks(core, run, state, None, path=navigator.packet_path(run, state))
            required = navigator._text_of([block for block in blocks if block.tier in navigator.HEAD_REQUIRED], head=True)
            room = navigator.HEAD_LIMIT - len(required) - 1 - len(navigator.HEAD_END) - 1
            stage = head_order.plans.stage_of(key)
            if stage not in worst or room < worst[stage][0]:
                worst[stage] = (room, route, key, len(row["printed"]), row["head"])
print(f"{'stage':<20} {'room':>6}  worst row (route, packet, printed characters, printed as a head)")
for stage, (room, route, key, printed, head) in sorted(worst.items(), key=lambda item: item[1][0]):
    print(f"{stage:<20} {room:>6}  {route}, {key}, {printed}, {head}")
