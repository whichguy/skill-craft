# Test-strategy Improve review one — preserved UI baseline

## Review scope

This first review compared the current strategy with the accepted R-1 UI baseline,
the conditional specification, and the blocked real-boundary requirements. It
also rechecked local harness evidence and the distinction between tracked source
and package-bound runtime artifacts.

## Material finding: TEST-REV-01

The strategy named browser/accessibility as a required surface, but it had no
stable case with an independent expected outcome for the accepted native
account-selector/list/detail/editor/save/cancel/back journey, narrow layout,
keyboard/touch behavior, focus, reading position, draft preservation, and visual
identity. Scattered browser follow-ups in FN-TC-1/FN-TC-2 could not ensure those
preserved requirements survived a future feature plan.

## Correction

Added FN-NFR-1 / R-1 to run/notes/test-strategy.md. It defines a browser-only,
blocked regression assertion with recorded viewport/account/note/focus/reading
position setup, keyboard and pointer/touch journey stimulus, an independent
native-control and navy/amber/white/system/Georgia outcome, asynchronous
reconciliation preservation, and owned-data cleanup. It deliberately has no
selected browser command or target claim until Q-R4/Q-R5 are supplied.

## Checks and limits

- baseline-coverage-review-one.txt maps every accepted UI clause to FN-NFR-1.
- test-strategy-artifact-check.txt confirms FN-TC-1 through FN-TC-7, FN-NFR-1,
  blocked surfaces, fixtures, expected-RED, commands, and documentation owner.
- tracked-only status/diff are clean; node --check app.js passed syntax-only.
- No test was authored or executed, no product source/configuration/documentation
  changed, and no target/browser/API action occurred. Intake consumed the only
  independent reviewer; this is self-review with that limitation recorded.

Classification: **non-trivial**, because TEST-REV-01 materially closes a missing
preserved-requirement test contract.
