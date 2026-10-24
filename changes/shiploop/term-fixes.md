---
bump: patch
---
- **One term per concept** (the 2026-10-24 nomenclature audit):
  - **Test layers:** test-strategy's new rows are `test_layers`, keyed `code` and `layer` (`test_layers_na` when the
    run writes no code). "Surface" keeps its meaning: where a requirement is observed.
  - **Send back:** "Revise" is gone from the test and validate-existing duties. The `/shiploop-complete` card lists
    the four outcomes, without the retired `repeat` and `replan`.
  - **Blocked:** the shared rules now match the blocked rule. Only a person or an outside service unblocks a stage;
    a missing tool or a command that does not run what it claims is repair work.
  - **Stage:** a graph position is a "stage", never a "step", in the shared rules, the reference, the Improve handoff
    and the command card.
  - **Expected failure:** this replaces "expected-RED" for a baseline repair. "Characterisation" is spelled one way.
  - **Private store:** a sensitive locator goes in an authorized private store, never in the committed KNOWLEDGE/.
  - **Remote test:** the Salesforce card no longer says to list org-bound tests in `red_na`; the base run skips remote
    tests.
  - **Bound and destination:** an NFR has a bound, and a send-back has a destination.
  - **Unconfirmable:** implement no longer lets a criterion be "unconfirmable", since a condition no command can
    confirm is not a criterion.
