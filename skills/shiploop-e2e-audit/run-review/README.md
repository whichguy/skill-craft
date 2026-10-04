# Run Review page

The owner's iteration tool: expected versus observed for each run, the Backchain ledger, the plan's iterations with editable
expectations, and a prompt builder. The page is a static template; every run adds data, not template code. The contract is
[SCHEMA.md](SCHEMA.md).

## After every iteration

An iteration is one run (or batch) that has been reviewed and journaled. Do this straight after the learnings commit.

1. **Export.** `python3 skills/shiploop-e2e-audit/run-review/export.py <run output directory>` writes the run's documents,
   `writes.json` and `facts.md` under `<output>/review-export/`, plus one compact `review-export.json` to commit with the
   learnings entry. `test/shiploop_e2e/iterate.py` and `run.py` do this for you.
2. **Find or create the page.** With the Artifact tools: `Artifact list` for the title "ShipLoop Run Review". If there is none,
   publish `template/index.html` with `capabilities: {db: {}}`, then seed the starting expectations with
   `export.py --defaults` (create-only: list what exists first and skip it).
3. **Upload.** Apply `writes.json` with `ArtifactData` `batch`. For a document that already exists, read its version and pin
   `if_version`; never overwrite what the owner edited on the page.
4. **Add the judgment.** Write observations (what we expected, what we saw, the evidence path) from the review, set the result of
   the iteration card, and revise an expectation, with its reason, when the evidence shows the expectation was wrong rather than
   the engine.
5. **Provide it.** Open the page once (`Artifact` action `open`) and give the owner the link with a short narrative: what was done,
   what is running and why, the conclusions, what was learned, what is next.
6. **No Artifact tools?** Keep `review-export.json` with the learnings entry and say the page was not updated.

## Rules

- Data changes never republish the template. A template change is one republish, recorded in the journal.
- A hand-set verdict stays interim; derive from digests and receipts where the run kept them.
- The journal and the committed `review-export.json` are the durable record; the artifact database is the working copy.
