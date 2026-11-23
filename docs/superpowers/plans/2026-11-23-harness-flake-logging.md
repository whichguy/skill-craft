# Harness Flake Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the next `test-harness` or `security-harness` CI failure name its own cause in the truncated log, without splitting suites into smoke/long tiers or relaxing product timing.

**Architecture:** Keep the existing CI tiers (smoke → quick → full) and the three fixture fixes already on `cursor/fix-flaky-harness-tests-3eba`. Add failure-facing diagnostics in three places that already failed silently or with a one-line `ContextError`: (1) the bash self-test's failure summary, (2) the Python wrapper that truncates that output, (3) Git context status mismatches. Do not change production timeout caps, do not retry-until-pass, and do not introduce a new suite split.

**Tech Stack:** bash self-test (`skills/test-harness/scripts/test-harness-tests.sh`), Python unittest wrappers (`test/test-harness.test.py`, `test/experiments/shiploop_security/test_v7_git_context.py`), `v7/git_context.py` ContextError messages, existing `suite_catalog` / CI tiers.

## Global Constraints

- Preserve decisions in `162d8b6e1` and `b64b17160`: no retry-until-pass; no widening every timing cap; only scoped fixture/diagnostic changes.
- Ordinary commits that touch `skills/test-harness/` need a `changes/test-harness/<slug>.md` note or a `No-Change-Note:` trailer; pure test/docs changes may use `No-Change-Note`.
- Do not edit `plugins/`, catalogs, `CHANGELOG.md`, or skill `version:` fields by hand.
- Do not split `test-harness` / `security-harness` into smoke vs long suites in this plan (revisit only if measured wall time crosses `QUICK_MAX_SECONDS` 120s or becomes `core`'s slowest suite).
- Failure messages must not print secrets, home paths, or marker literals from security fixtures.

---

## File Structure

| File | Responsibility |
|---|---|
| `skills/test-harness/scripts/test-harness-tests.sh` | Emit a machine-readable FAIL index before the summary; keep per-check `  FAIL  ` lines. |
| `test/test-harness.test.py` | Prefer the FAIL index / named failures in assertion detail; enrich missed-barrier messages. |
| `test/experiments/shiploop_security/v7/git_context.py` | On status mismatch, raise with tracked/untracked counts and digests (not path contents). |
| `test/experiments/shiploop_security/test_v7_git_context.py` | Assert the richer mismatch message appears; keep the different-length fixture. |
| `docs/test-harness-journal.md` | Record the 2.8.0 CI failures and the diagnostic decisions (optional closing task). |
| `changes/test-harness/fail-index.md` | Patch note only if Task 1 edits the skill tree. |

---

### Task 1: Self-test FAIL index (named failures survive truncation)

**Files:**
- Modify: `skills/test-harness/scripts/test-harness-tests.sh` (assert helpers near lines 31–74; summary near lines 2830–2834)
- Modify: `test/test-harness.test.py` (`self_test_detail`, `SelfTest`)
- Create: `changes/test-harness/fail-index.md`

**Interfaces:**
- Consumes: existing `assert` / `assert_eq` / `assert_pid_file_dead` that print `  FAIL  $name`
- Produces: `$TMP/fail-index.txt` (one FAIL name per line); summary block that reprints those names; `self_test_detail` prefers names from that block or from `  FAIL  ` lines

- [ ] **Step 1: Write the failing wrapper expectation for a truncated FAIL index**

In `test/test-harness.test.py`, extend `self_test_detail` tests inside `SelfTest` (or a tiny helper unit test at module level run by the existing method) so a synthetic log with only a summary FAIL index still surfaces the name:

```python
def test_self_test_detail_prefers_fail_index_block(self):
    body = (
        "=== fail-index ===\n"
        "synthetic early failure\n"
        "=== end fail-index ===\n"
        + ("y" * 3000)
        + "\n=== summary: PASS=10 FAIL=1 ===\n"
    )
    detail = self_test_detail(body)
    self.assertIn("synthetic early failure", detail)
    self.assertNotIn("y" * 100, detail.split("synthetic early failure", 1)[0])
```

- [ ] **Step 2: Run the focused expectation and confirm it fails on current helpers**

Run:

```bash
python3 -B test/test-harness.test.py SelfTest -v
```

Expected: FAIL because `self_test_detail` does not yet parse the `fail-index` block (or the new method is not yet wired). If you fold the check into the existing method without a new TestCase method, run the whole `SelfTest` class the same way.

- [ ] **Step 3: Implement the FAIL index in the bash self-test**

Near the top of `test-harness-tests.sh`, after `FAIL=0`:

```bash
FAIL_INDEX="$TMP/fail-index.txt"
: > "$FAIL_INDEX"
record_fail() {
  local name="$1"
  printf '%s\n' "$name" >> "$FAIL_INDEX"
}
```

In each failure branch of `assert`, `assert_eq`, and `assert_pid_file_dead`, after printing `  FAIL  ...`, call `record_fail "$name"`.

Replace the summary footer with:

```bash
echo "=== summary: PASS=$PASS FAIL=$FAIL ==="
if [[ "$FAIL" -ne 0 ]]; then
  echo "=== fail-index ==="
  if [[ -s "$FAIL_INDEX" ]]; then
    cat "$FAIL_INDEX"
  else
    echo "(no recorded FAIL names; likely a set -e heredoc abort before assert helpers)"
  fi
  echo "=== end fail-index ==="
  exit 1
fi
exit 0
```

- [ ] **Step 4: Teach `self_test_detail` to prefer the fail-index block**

```python
def self_test_detail(output):
    """Named FAIL lines / fail-index first, then the last 1500 characters."""
    indexed = re.search(
        r"^=== fail-index ===\n(.*?)^=== end fail-index ===$",
        output,
        re.M | re.S,
    )
    if indexed and indexed.group(1).strip():
        names = indexed.group(1).strip()
        return names + "\n--- last 1500 characters ---\n" + output[-1500:]
    failing = [line for line in output.splitlines() if line.startswith("  FAIL  ")]
    tail = output[-1500:]
    if not failing:
        return tail
    return "\n".join(failing) + "\n--- last 1500 characters ---\n" + tail
```

Keep the existing synthetic `  FAIL  ` check; add the fail-index synthetic check from Step 1.

- [ ] **Step 5: Add the change note**

Create `changes/test-harness/fail-index.md`:

```markdown
---
bump: patch
---
Self-test failures now reprint a fail-index of named checks before exit so a truncated CI log still names the failing assertion.
```

- [ ] **Step 6: Run the harness suite and commit**

```bash
python3 -B test/test-harness.test.py -v
```

Expected: 11 tests OK (or one more method if added), bundled summary still `FAIL=0` with PASS ≥ 270.

```bash
git add skills/test-harness/scripts/test-harness-tests.sh test/test-harness.test.py changes/test-harness/fail-index.md
git commit -m "fix(test-harness): reprint a fail-index so truncated CI logs name the check"
```

---

### Task 2: Missed-barrier and empty-staging messages in TimeoutEvidence

**Files:**
- Modify: `test/test-harness.test.py` (`TimeoutEvidence.scenario` assertion path around the barrier check)

**Interfaces:**
- Consumes: existing printed scenario JSON (`barrier`, `final`, `staging_leftovers`, `elapsed`)
- Produces: `AssertionError` text that includes staging sizes and elapsed when the barrier is missing

- [ ] **Step 1: Write a failing expectation for the barrier message**

Add a focused helper used only by the assertion (keep production supervisor untouched):

```python
def barrier_failure_detail(barrier, leftovers, elapsed, stderr):
    sizes = [(row["name"], len(row.get("text", ""))) for row in leftovers]
    return (
        f"operation barrier was not reached; elapsed={elapsed:.3f}s; "
        f"staging_sizes={sizes}; stderr_tail={stderr[-400:]!r}"
    )
```

Unit-check it inside `TimeoutEvidence` or at module level:

```python
msg = barrier_failure_detail(None, [{"name": "x.tmp", "text": ""}], 1.02, "hard timeout\n")
assert "staging_sizes=[('x.tmp', 0)]" in msg
assert "elapsed=1.020s" in msg
```

- [ ] **Step 2: Run to confirm the helper is missing (red)**

```bash
python3 -B -c 'from pathlib import Path; import runpy; runpy.run_path("test/test-harness.test.py")'
```

Or add a one-off assert in a temporary throwaway and delete it after wiring. Prefer calling the helper from a tiny `unittest` method under `TimeoutEvidence` named `test_barrier_failure_detail_names_empty_staging` so it stays in the suite.

Expected: FAIL / ImportError until the helper exists.

- [ ] **Step 3: Wire the helper into the barrier assertion**

Replace:

```python
self.assertIsNotNone(barrier, "operation barrier was not reached")
```

with:

```python
self.assertIsNotNone(
    barrier,
    barrier_failure_detail(barrier, leftovers, elapsed, stderr),
)
```

Do not change caps, reserves, or scenario timing. The cleanup scenario's 4s cap from the prior fix stays.

- [ ] **Step 4: Run TimeoutEvidence and commit**

```bash
python3 -B test/test-harness.test.py TimeoutEvidence -v
```

Expected: 3 methods OK.

```bash
git add test/test-harness.test.py
git commit -m "test(test-harness): name empty staging when the timeout barrier is missed

No-Change-Note: TimeoutEvidence assertion text only; no skill source change."
```

(If this lands in the same commit as Task 1, fold it there instead of a second commit.)

---

### Task 3: Git status mismatch diagnostics (safe digests, not contents)

**Files:**
- Modify: `test/experiments/shiploop_security/v7/git_context.py` (`_rebuild` status check ~line 802)
- Modify: `test/experiments/shiploop_security/test_v7_git_context.py`

**Interfaces:**
- Consumes: `_status(...)` returning `{"sha256", "tracked", "untracked"}`
- Produces: `ContextError` text including both digests and counts when they differ

- [ ] **Step 1: Write a failing control that expects digests in the error**

In `test_v7_git_context.py`, add a narrow test that forces a status mismatch after capture (for example rewrite the retained receipt's `status.sha256` and call `restore`, or patch `_status` on replay). Prefer restoring with a tampered receipt status field:

```python
def test_status_mismatch_names_digests_not_paths(self):
    receipt = self.clean_context()
    receipt["status"] = {
        **receipt["status"],
        "sha256": "0" * 64,
        "tracked": receipt["status"]["tracked"] + 1,
    }
    self.rewrite_receipt(receipt)
    with self.assertRaises(context.ContextError) as raised:
        self.restore()
    message = str(raised.exception)
    self.assertIn("reconstructed Git status differs", message)
    self.assertIn("expected_sha256=", message)
    self.assertIn("observed_sha256=", message)
    self.assertNotIn("keep", message)  # no path dump
```

- [ ] **Step 2: Run the new test (expect FAIL on today's message)**

```bash
cd test/experiments/shiploop_security && python3 -B -m unittest \
  test_v7_git_context.GitContextTests.test_status_mismatch_names_digests_not_paths -v
```

Expected: FAIL — current error is only `reconstructed Git status differs`.

- [ ] **Step 3: Enrich the mismatch in `_rebuild`**

Replace the bare require:

```python
_require(status == receipt["status"] and not omitted, "reconstructed Git status differs")
```

with:

```python
if status != receipt["status"] or omitted:
    expected = receipt["status"]
    raise ContextError(
        "reconstructed Git status differs: "
        f"expected_sha256={expected.get('sha256')} observed_sha256={status.get('sha256')} "
        f"expected_tracked={expected.get('tracked')} observed_tracked={status.get('tracked')} "
        f"expected_untracked={expected.get('untracked')} observed_untracked={status.get('untracked')} "
        f"omitted_untracked={omitted}"
    )
```

Keep `_require` for other checks. Do not include porcelain lines or file paths (security harness retains marker hygiene).

- [ ] **Step 4: Run security-harness and commit**

```bash
python3 -B test/experiments/shiploop_security/run_tests.py
```

Expected: all tests OK (75 → 76 if the new method is additive).

```bash
git add test/experiments/shiploop_security/v7/git_context.py \
        test/experiments/shiploop_security/test_v7_git_context.py
git commit -m "test(security-harness): put status digests in reconstructed-status errors

No-Change-Note: Experiment harness diagnostics only; no skill or agent card change.
No-E2E-Round: Security experiment apparatus only."
```

Note: `v7/git_context.py` lives under `test/experiments/`, so this is apparatus, not a skill leaf. Prefer `No-Change-Note` over a skill change note.

---

### Task 4: Record the measured costs and the non-goals

**Files:**
- Modify: `docs/test-harness-journal.md` (append a short round)
- Optionally modify: `test/suite_durations.json` only if a fresh full-tier receipt is available; otherwise leave the 60s fallback for `security-harness` and note it

**Interfaces:**
- Consumes: local timings already measured (~5s security, ~63s test-harness) and CI run `45134262405`
- Produces: journal round stating: no smoke/long split; FAIL index; status digests; cleanup 4s fixture already landed

- [ ] **Step 1: Append a journal round**

Add at the end of `docs/test-harness-journal.md`:

```markdown
## Round N - 2.8.0 full/core flakes and diagnostics (2026-11-23)

Firm: release commit 4d805b084 failed full/core twice then passed (run 45134262405).
Failures: security-harness reconstructed Git status (same-size keep edit); TimeoutEvidence
cleanup barrier missed with empty staging; SelfTest PASS=278 FAIL=1 with the failing line
cut off by a 1500-character tail.

Decisions: fix fixtures (different-length keep; cleanup scenario 4s cap only); add FAIL index
and status-digest ContextError text; do not split smoke/long suites; do not retry-until-pass;
do not widen every cap (162d8b6e1, b64b17160).
```

Replace `N` with the next round number present in the file.

- [ ] **Step 2: Commit journal only**

```bash
git add docs/test-harness-journal.md
git commit -m "docs(test-harness): record 2.8.0 flake causes and diagnostic decisions

No-Change-Note: Journal only."
```

- [ ] **Step 3: Push and update the PR**

```bash
git push -u origin HEAD
```

Use `ManagePullRequest` `update_pr` on the existing harness-flake PR (or open one if this plan lands alone). Do not change release output.

---

## Out of scope (explicit non-goals)

- Splitting `test-harness` into wrapper-smoke vs bash-self-test long suites.
- Moving `security-harness` or `test-harness` to full-only.
- Retrying flaky checks until pass.
- Widening `TIMING_SLACK_MS`, hang budgets, or production supervisor reserves.
- Printing porcelain paths, marker bytes, or home paths in CI logs.

## Self-review

1. **Spec coverage:** Better logging → Tasks 1–3. Fixture stability already on the branch → assumed complete; Task 4 records it. No smoke/long split → Out of scope. Remaining unknown attempt-2 check name → Task 1 makes the next one visible.
2. **Placeholders:** None left as TBD; commands and code are concrete.
3. **Type consistency:** `self_test_detail(output: str) -> str`; `barrier_failure_detail(...)` returns `str`; ContextError message is plain text with digest fields matching receipt `status` keys (`sha256`, `tracked`, `untracked`).
