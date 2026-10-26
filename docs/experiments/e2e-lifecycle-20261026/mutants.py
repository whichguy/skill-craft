#!/usr/bin/env python3
"""Build step 7's mutants: each one breaks one rule of lifecycle.py or its wiring in run.py, and the named tests of
test/shiploop-e2e-lifecycle.test.py must fail on it. Run from the repository root; every file is restored afterwards.

None widens which processes are signalled: the code under test only ever signals groups a test started, and the in-process
tests refuse any other (LifecycleCase.guard). A mutant that selects more processes is never run against real processes
(the 2026-10-08 reap incident)."""
import subprocess
import sys
from pathlib import Path

L, R = Path("test/shiploop_e2e/lifecycle.py"), Path("test/shiploop_e2e/run.py")
MUTANTS = [
    ("M1 no lease refusal", L, "            except BlockingIOError:\n                os.close(descriptor)\n                held_by",
     "            except BlockingIOError if False else ():\n                os.close(descriptor)\n                held_by",
     ["LeaseTest", "ThroughMainTest.test_a_launch_beside_a_held_lease_is_refused_before_its_folder_or_host_exists"]),
    ("M2 identity always matches", L, "return bool(recorded and now) and all(", "return bool(now) or all(", ["StopTest"]),
    ("M3 no cleanup before resume", R, "        retry_cleanup = lifecycle.cleanup(out)\n", "        retry_cleanup = None\n",
     ["CrashAndRetryTest"]),
    ("M4 dispose skips evidence", L, '        if not kept["complete"]:', "        if False:", ["EvidenceTest"]),
    ("M5 lease file kept", L, "                if _same_file(descriptor, path):\n                    os.unlink(path)",
     "                if False:\n                    os.unlink(path)",
     ["LeaseTest.test_a_lease_given_back_leaves_nothing_in_the_state_home"]),
    ("M6 session group not ended", R, "            listeners.end_group(proc.pid)\n            proc.wait()\n        finally:",
     "            listeners.end_group(proc.pid) if status else None\n            proc.wait()\n        finally:",
     ["ThroughMainTest.test_a_session_that_ends_takes_what_it_left_in_its_group_with_it"]),
    ("M7 no orphans", L, "    if not candidates:\n        return []\n    now = table()", "    if True:\n        return []\n    now = table()",
     ["ThroughMainTest.test_an_orphan_and_a_low_disk_refuse_a_launch", "CrashAndRetryTest"]),
    ("M8 no all-or-none release", L, "    except BaseException:\n        lease.close()\n        raise",
     "    except BaseException:\n        raise", ["LeaseTest.test_a_lease_is_all_or_none"]),
    ("M9 observer instance unchecked", L, '    if _flag(words, "--instance") != instance or not run_dir', "    if not run_dir",
     ["StopTest.test_an_orphaned_progress_observer_is_adopted_by_its_record_and_a_lookalike_is_left_alone"]),
]

survived = 0
for name, path, old, new, tests in MUTANTS:
    original = path.read_text()
    if original.count(old) != 1:
        raise SystemExit(f"{name}: its anchor is not in {path} exactly once")
    path.write_text(original.replace(old, new))
    try:
        done = subprocess.run([sys.executable, "-B", "test/shiploop-e2e-lifecycle.test.py", *tests], capture_output=True,
                              text=True, timeout=300)
        killed = done.returncode != 0
    except subprocess.TimeoutExpired:
        killed = True
    finally:
        path.write_text(original)
    survived += not killed
    print(("KILLED  " if killed else "SURVIVED") + "  " + name, flush=True)
raise SystemExit(1 if survived else 0)
