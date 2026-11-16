"""Break each re-review fix in turn; the test named for it must fail. The facade is restored after every mutation."""
import hashlib
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]  # the repository: docs/experiments/<this folder>/g1b-mutations.py
facade = root / "test/shiploop_e2e/adapter/facade.py"
original = facade.read_text()
digest = hashlib.sha256(original.encode()).hexdigest()
MUTANTS = [
    ("cleanup kills nothing when the lock is free", '''    if held.killed is not None:
        return held.killed
    if rec["state"] not in TERMINAL and rec.get("worker"):
        return kill_step(layout, rec)
    return None''', '''    return held.killed''', "SecondReviewTests.test_cleanup_stops_what_a_worker_that_died_alone_left_in_its_group"),
    ("start without admission", '''    with admission(layout):
        return step_start_admitted(layout, args, key)''', '''    return step_start_admitted(layout, args, key)''', "ReviewFindingsTests.test_two_steps_started_at_the_same_moment_are_not_both_admitted"),
    ("no grace re-check under the lock", '''            if time.time() - rec.get("spawned_epoch", rec["created_epoch"]) < BOOT_GRACE_SECONDS:
                return {"status": "running"}  # checked again under the lock: another poll has just begun a worker
''', '', "SecondReviewTests.test_a_poll_that_read_an_old_spawn_time_does_not_begin_a_second_worker"),
    ("publication outside the lock", '''    begin = False
    with Exclusive(layout, key, wait=False) as held:
        if not held.held:
            return {"status": "running"}  # a worker began, or another caller holds the step''', '''    begin = False
    if rec["state"] == "prepared":
        finish_publication(layout, rec)
        return reply_for(load_step(layout, key))
    with Exclusive(layout, key, wait=False) as held:
        if not held.held:
            return {"status": "running"}  # a worker began, or another caller holds the step''', "SecondReviewTests.test_a_poll_does_not_publish_while_another_caller_holds_the_step"),
    ("receipt seal ignored", '''            sealed = hashlib.sha256(path.read_bytes()).hexdigest() == event.get("receipt_sha256")''', '''            sealed = path.is_file()''', "SecondReviewTests.test_an_epoch_receipt_changed_after_its_review_is_not_a_review"),
    ("first decision", '''    decision = decisions[-1] if decisions else None  # epoch.state takes the last decision''', '''    decision = decisions[0] if decisions else None''', "SecondReviewTests.test_the_last_decision_of_an_epoch_is_the_one_that_counts"),
    ("kill below an unverified group", '''    if verdict != "ok":  # a group that is not provably the worker's: neither it nor anything found below it is signalled
        return {"group": verdict, "detail": detail, "sessions": 0, "survivors": [], "at": now()}''', '''    if verdict == "gone":
        return {"group": verdict, "detail": detail, "sessions": 0, "survivors": [], "at": now()}
    detail = {"members": facade_members(table, worker)} if verdict != "ok" else detail''', "PureTests.test_a_group_whose_leader_is_gone_is_left_alone_when_its_record_is_old_and_stopped_when_it_is_recent"),
    ("tip read before the unsettled check", '''    busy = unsettled_keys(layout)  # first: with none unsettled and admission held, nothing can move the tip before the intent is written
    if busy:
        raise FacadeError(f"step {busy[0]} has not finished: poll it, or run cleanup for it, before another begins (one step at a time)")
    tip = published_tip(layout)''', '''    tip = published_tip(layout)
    busy = unsettled_keys(layout)
    if busy:
        raise FacadeError(f"step {busy[0]} has not finished: poll it, or run cleanup for it, before another begins (one step at a time)")''', "SecondReviewTests.test_a_start_reads_the_tip_only_after_no_step_is_unsettled"),
    ("recommendation not recomputed", '''    if checked.get("recomputed_tolerance") != calibration["tolerance"]:''', '''    if False:''', "ProbeTests.test_the_calibrated_claim_needs_a_report_for_this_profile_whose_digest_still_holds"),
]
HELPER = '''

def facade_members(table, worker):
    return alive_in_group(table, worker["pgid"])
'''
results = []
try:
    for label, old, new, test in MUTANTS:
        if original.count(old) != 1:
            results.append((label, "MUTATION NOT APPLIED"))
            continue
        facade.write_text(original.replace(old, new, 1) + (HELPER if "facade_members" in new else ""))
        done = subprocess.run([sys.executable, "-B", "test/shiploop-e2e-adapter-steps.test.py", test], cwd=root, capture_output=True, text=True, timeout=400,
                              check=False)
        caught = done.returncode != 0
        results.append((label, "caught (test failed)" if caught else "MISSED (test passed)"))
finally:
    facade.write_text(original)
assert hashlib.sha256(facade.read_text().encode()).hexdigest() == digest
for label, verdict in results:
    print(f"{verdict:24}  {label}")
