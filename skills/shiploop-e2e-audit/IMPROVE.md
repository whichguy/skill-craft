# Improve ShipLoop across software projects

Start from the authorized skill-craft source checkout. Resolve its Git root
from the current directory or the supplied checkout path and use the existing
`test/shiploop_e2e` source harness there.
Installed audit packages contain the audit harness. Improvement uses the source
checkout so the campaign can compare and deliver changes to ShipLoop.

Use a clean checkout of current `origin/main` for the first published trial.
If the working checkout has changes or comes from another revision, use a new
campaign-owned checkout from current main. Record the source SHA and use a new
output directory and external baseline ledger. The harness creates an empty
product directory for a fresh create case. Reuse case predecessors only when
that case explicitly measures an incremental change.

## Run and review

1. Pick the requested local case. Start with `csv-report` for an unspecified
   first pass. Use the catalog prompt and independent checks. Resolve the latest
   available Sol and Astra families from the current official model list and
   the Codex host. Use Sol medium for the subject and improver and separate
   fresh Astra high reviewer and judge sessions. Record the selected IDs and
   effective controls. Preserve a resumed trial's existing identity.
2. Run the source harness on the published build. Fill the absolute paths and
   resolved Sol ID once. Add an explicit run timeout when the owner sets one.

   ```sh
   python3.15 -B "$SOURCE/test/shiploop_e2e/run.py" \
     --case "$CASE" --source marketplace --host codex --model "$SOL" --effort medium \
     --codex-auto-review --output "$RUN" --baseline "$BASELINES"
   ```

   The runner automatically checks source freshness and the installed ShipLoop
   and Improve packages before the first builder dispatch. The Codex route uses
   the workspace sandbox and reviews individual commands outside it
   automatically. Follow failures to their source and repair in-scope
   prerequisites in the campaign checkout. Keep the failed attempt and use a
   new run identity if the launch must be repeated.
3. After the run, reuse its output for independent review and judgment. Set
   the explicit role IDs on the actual invocation.

   ```sh
   python3.15 -B "$SOURCE/test/shiploop_e2e/iterate.py" \
     --case "$CASE" --review-run "$RUN" --output "$ASSESSMENT" \
     --host codex --model "$SOL" --effort medium --codex-auto-review \
     --reviewer-host codex --reviewer-model "$ASTRA" --reviewer-effort high \
     --judge-host codex --judge-model "$ASTRA" --judge-effort high \
     --improver-host codex --improver-model "$SOL" --improver-effort medium
   ```

   Record a findings-and-changes report in the campaign output for every
   attempt, including a failed or blocked launch. Link the retained product,
   verdict, actual test executions and assertions, review and stage evidence.
   Describe coverage gaps, efficiency counters and their limitations. Give the
   exact ShipLoop changes and their qualification and publication status, or
   say that no ShipLoop change was made.

## Improve and repeat

Group admitted findings into hypotheses about the SDLC workflow. Prefer the
smallest experiment that can resolve each hypothesis. Start with a targeted
regression when it can distinguish the faulty and corrected behavior. Use a
second local case of a different style when a comparison needs evidence of
generality. For example, a file CLI and a stateful service exercise different
kinds of work. Report the scope actually measured.

Use `iterate.py --qualify --iterations 1` with the same role and permission
settings for a registered comparison. Include `--review-run "$RUN"` at this
step if the retained trial has yet to be assessed. If it has, start the cycle
from the isolated branch containing the learning and pass `--record` with its admitted ID.
For a separate generality case pass `--generality-case`. The existing calibration or recorded
attempt and tolerance policy supplies the comparison parameters. When it is
missing, retain the exploration and continue with calibration or a targeted
investigation. Keep candidates isolated until qualification.

Read the recorded cycle decision and measured candidate. For a qualified
production ShipLoop change, merge the tested change to main, run the repository
release procedure, verify CI and the fresh marketplace install, then continue
from that published revision. Repeat the affected case from equivalent inputs.
Use a new trial directory and keep the generations and their evidence for
review.

Continue while a material finding or coverage gap has an in-scope experiment
and budget. If the result is unchanged or inconclusive, record why. A local
case supports the SDLC behaviors it exercised. Add other case styles for
broader claims about ShipLoop.
