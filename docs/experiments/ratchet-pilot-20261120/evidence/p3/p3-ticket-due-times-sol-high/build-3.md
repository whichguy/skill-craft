## Done

- C-1–C-290 retain the previous build's behavior, with saved-deadline validation tightened by C-291. C-89,
  C-92–C-93 and C-259–C-260 are reflected in the API reference, runbook and CLI documentation. C-275 was verified
  with the original 1.4.0 release. C-276–C-278 are covered by decision 0011 and the 1.5.2 release entry.
- C-291 compares canonical saved deadlines against explicitly zoned ISO creation times by instant. Preparation and
  enabled startup refuse an early deadline and name its file, field and ticket. Preparation also validates the
  recovery copy. Equal instants are valid. Enabled CLI details omit the unusable assignment and still show the ticket
  and its history. Dark saves preserve the saved value for inspection.
- C-292 was already satisfied by the shared store commit path. New HTTP tests force an effective PATCH and a
  resolution save to fail and check the ticket, overdue page, audit, outbox and file immediately. The tests also
  verify a later unrelated save, restart and successful resolution retry. After an HTTP stall during the first gate run,
  the new regression uses sequential requests with fresh connections and request deadlines.
- C-293 was already satisfied by the recovery reader and file identity check. New tests exercise direct, symlink
  and hard-link aliases and verify that successful recovery preserves the archive's bytes, identity, mode and
  modification time.
- C-294 expands the rollback runbook to name both exhausted counters, the writes that allocate from them and the
  restart failure. In drills on disposable copies, 1.4.0 started, read and edited tickets at either exhausted
  counter. After a create at ticket exhaustion or a resolution that needed a new event at outbox exhaustion,
  its next startup refused the resulting snapshot.
- C-295 was already satisfied before tightening validation. Tests and the runbook cover assigning a legacy local
  deadline in Los Angeles, retaining it through repeat preparation and enabled startup in Honolulu, and restoring
  it there from a separate archive after a real 1.4.0 rollback.
- C-272–C-274 preserve all existing tests and add six `node:test` regressions. All 154 tests passed in `npm test`.
  The original 1.4.0 tests matched the files at the baseline commit byte-for-byte.

## Not done

No unfinished product clauses. The exit check is blocked by 21 frozen checks, covering C-34, C-37, C-39, C-42, C-43, C-45–C-48,
C-50–C-53, C-64, C-66, U-5–U-7, U-9, U-12 and U-16. They require startup or preparation to accept a saved deadline
that precedes explicit creation, which C-291 requires the product to refuse. The acceptance files were left intact.

## Discoveries

- An overdue fixture needs a creation instant at or before its saved deadline and a request clock after that deadline. | Observable: Several frozen fixtures set `created` to `2025-09-01T08:15:00.000Z` and `due` a day earlier. Startup or preparation exits 2 with the affected ticket. | Why: The older fixtures used a past deadline to test the queue without advancing the request clock or moving the creation instant.
- Timestamp format and deadline ordering need independent fixture values at the negative Date endpoint. | Observable: Preparation accepts a deadline equal to a creation instant at `-271821-04-20T00:00:00.000Z`. The frozen C-66 check instead pairs that deadline with a 2025 creation and fails validation. | Why: A canonical timestamp can still be invalid for the particular ticket under C-291.
