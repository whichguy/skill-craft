# E25: house-style extraction and the repository's record-keeping rules

Journal entry: E25 in [docs/shiploop-question-driven-planning-journal.md](../../shiploop-question-driven-planning-journal.md);
findings F47 and F48. The change under test is one bullet in skills/shiploop/references/house-style.md.

## What was measured

1. **Stage-level pilot (base arm only; dropped).** `document/repo-record-persistence` on the stage suite: the document stage alone, the
   persistence step of `ticket-due-times`, AD-4 seeded, no "write a decision record" in the request. ShipLoop 1.35.0 at
   05b362cab3959f19f2a88cb65d770f68b547e345, Grok CLI 1.0.77, grok-4.6 xhigh, 10 valid samples, none invalid.
   [evidence/base-samples.json](evidence/base-samples.json): 7 wrote the repository's record, 6 graded as passing (sample 7 wrote a
   correct record that does not contain the words "data file", so my word test failed it), 3 wrote none; 2 linked the AD to the
   record unprompted; the accepted records and the product's tests held in 10 of 10; 6 to 9 minutes a sample. The scenario, its
   oracle and the registration (predictions Q1 to Q10, rules D1 to D4, re-registration R1) are on the local branch
   `feat/doc-records-e562cd` (f8cf9a2ec7f2a6519b12e32cf13835d5912a62fb, 3be0f2620831a964b87dae186f2d5ab2415bfa30), not merged.
2. **Capture check on the real flow.** Three runs of `ticket-due-times` on the candidate build, each ended after discovery:

   ```sh
   python3 test/shiploop_e2e/run.py --case ticket-due-times --source checkout --output <dir>   # x3, then `touch <dir>/stop`
   ```

   The stop file was created by a watcher as soon as the state's history showed an accepted `discovery` stage, after it copied the
   knowledge home. [evidence/capture-hs-1](evidence/capture-hs-1), [hs-2](evidence/capture-hs-2) and [hs-3](evidence/capture-hs-3)
   hold each run's environment.md as discovery left it (the house-style record is the "House style" entry) and the time it was
   copied. Each run installed the candidate's house-style.md (checked: the new bullet is in the installed plugin).

## Result

| | E24 base (ShipLoop 1.34.3) | Candidate (house-style.md + 1 bullet) |
|---|---|---|
| Runs whose house-style record names the decision-record rule | 0 of 3 | 3 of 3 |

The rule appears with its location in all three, with its template and index in two, and with its trigger (API, data-file or
notification changes) in two. The discovery duties and house-style.md are byte-identical between E24's build
(48bc8d63cc64f090f26ba46ee7c273611d14f1de) and this change's base, so the comparison is like for like.

## Limits

One repository shape (an ADR folder with a template and an index), one host and model, three runs. Capture is necessary and not shown
sufficient: whether the match contract carries the rule to the step that owes the record, and whether a full run writes it, are not
measured. The release carries a `No-E2E-Round` exemption that says so. The lean path was chosen over the registered stage-level plan
after the owner objected that it was excessive; the numbers above are what the stage-level pilot reached before it was stopped.
