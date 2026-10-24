---
bump: minor
---
- **Quality rules from a product review of a live run:**
  - step-plan: behaviour is confirmed by running it whenever any runner can, and inspection confirms only text or
    wiring. A count or prefix check proves nothing where a criterion names an exact value. A new check script is listed
    in `paths` or kept in RUN/scratch.
  - test-strategy: name each code surface's native unit harness; an absent one is prerequisite work, never N/A. Record
    whether a target keeps state between runs, and how a base-state failure is produced there.
  - test-spec: RED comes from the missing behaviour, given what earlier items left deployed; a file guard is not RED.
    Pair each absence assertion with a presence or count assertion, drop assertions that cannot fail, and test each
    documented throw or refusal branch.
  - verify: "not a quoted case" is no reason to leave a path untested, and each requirement's Confirm-by clause is
    compared with the assertions that exist.
  - spec: non-functional bounds are numeric and inside any hard platform limit, and excluded domain rules are listed.
  - product-acceptance: an outcome evidenced only by inspection or a deferred assumption is not accepted.
  - Improve: the end review also looks for grep-only checks, parsers that miss cross-field validity, a pitfall fixed in
    one place only, and failure states without a next action; each of its fixes comes with a test that fails before
    it. The step review also flags a scaled-down UI that drops assistive state and a server entry point with no
    declared access posture.
