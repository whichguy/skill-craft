# Side-effect taxonomy

Every finding carries `disposition ∈ {ok, note, fail}`.
`SIDEEFFECTS_OK` ⇔ zero findings with `disposition: fail`.

## Filesystem classes

| Class | Meaning | Default disposition |
|---|---|---|
| `BASELINE` | Present before suite; content hash unchanged | ok |
| `EXPECTED_ARTIFACT` | Common litter / allowlisted (`__pycache__`, coverage, …) | note (gitignore if unignored) |
| `HARNESS_OUTPUT` | Intentional harness dirs (`results/`, `reports/runs/`, `reports/harness/`) | note |
| `UNINTENDED_WRITE` | Product/config/fixture created, changed, or deleted | **fail** |
| `IGNORED_WRITE` | Ignored path created/changed (bounded inventory) | note; **fail** under `src/`, `lib/`, `app/`; more note-only paths via `ignored_write_note_globs` |
| `TMPDIR_LEAK` | Leftovers under pinned run tmp | note — **run-relative** `sample` paths; hint `not repo dirt; optional test cleanup` |
| `UNKNOWN` | Unclassified | **fail** |

Unmapped future classes default to **fail**.

## Control-channel classes (policy)

| Class | Meaning | Default disposition |
|---|---|---|
| `CONTROL_FORBID_HIT` | Forbidden substring/regex in stdout/stderr (e.g. Traceback on hermetic run) | **fail** |
| `CONTROL_REQUIRE_MISS` | Required marker missing for suite exit code (`control_require_on_exit`) | **fail** |
| `CONTROL_POLICY_ERROR` | Malformed policy / invalid regex / evaluation error | **fail** |

Resolved policy lives at `$RUN_DIR/control-policy.json` (from `control_policy.py resolve`).  
Repo overlay: `.test-harness.yml` (unknown keys fail closed). Defaults always include Traceback + secret-shaped patterns for fast/full/unknown profiles.

Paste surfaces (`chat-card.md`, `channels_excerpt.md`) use **redact → cap → render**. Raw `stdout.log` / `stderr.log` are unredacted on disk for operators.

## Service classes

| Class | Meaning | Default disposition |
|---|---|---|
| `LIVE_CALL_SUSPECT` | Log/env evidence; agent decides | note |
| `LIVE_CALL_UNEXPECTED` | Agent-promoted FAIL on hermetic profile | fail |
| `LIVE_CALL_EXPECTED` | `--full` / allowlisted live | ok |
| `LIVE_GATE_ON_FAST` | Live env gate set while profile=fast | fail (script) |
| `MISSING_INJECTION` | Real binary/API hit; missing override seam | fail |

### Suspect rules

- Attach matched line + source file.
- Exempt `localhost` / `127.0.0.1` / `::1`.
- Exempt matches only inside fixture/snapshot/golden paths.
- **Do not** hard-FAIL on `ECONNREFUSED` alone (often hermetic proof).
- Classifier must not nonzero-exit solely on URL greps.

## Restore rules (applied before any fix edit)

| Path kind | Action |
|---|---|
| Dirty-at-pre, changed/deleted | **Preserve exact post state**; record failing finding + `preserve-dirty-pre-post-state` in `restore.json`; stop for manual reconciliation |
| Tracked clean-at-pre, changed/deleted | Restore from captured `head_pre` (`git restore --source <head_pre> --worktree -- <path>`; the index is never touched) |
| Untracked UNINTENDED_WRITE, absent at pre | Delete |
| `restorable: false` | No snapshot-byte restore; disposition fail until manually reconciled/allowlisted |
| Never | Blanket HEAD restore of dirty-at-pre paths |

Safe restore runs **before** fix edits. A dirty-at-pre preservation terminates
the mechanical loop so a later round cannot silently promote the suite's post
state into a new baseline. `round-N/restore.json` is the action record.

## Audit scope honesty

When ignored-path inventory hits caps → `fs_scope: git-visible-only` and result
label narrows to “git-visible + TMPDIR clean”.
