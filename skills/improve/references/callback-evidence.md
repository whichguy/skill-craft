# Improve callback evidence

This reference applies to a **new standalone Improve run** using Until Loop's
single-file callback runtime. It defines what the executing host should retain
and summarize before the exact `done_argv` call. It does not add a collector,
another state file, or an alternative transition authority.

## Record one completed review cycle

For every active callback, retain a host-visible record of one full review
cycle. The host record may be the task transcript and its command results; it
does not need to be a file in the reviewed repository. Keep enough concrete
detail for the next context to distinguish an observation from a plan:

1. **Candidate and scope.** State the baseline or named range separately from
   the current candidate identity and its named inventory. Keep every included
   path in that inventory, including relevant untracked product or requirements
   artifacts when the initial commit is empty or `HEAD` does not move. Name
   explicit scratch or pre-existing user paths that remain outside the change,
   plus any adjacent context inspected. For a large inventory, one exact
   resource locator is enough; do not recopy every path in each cycle.
2. **History.** Record that the latest seven reachable commit messages were
   read in full, or name the smaller available window. Keep their IDs and the
   lessons that affected this review; history does not authorize unrelated
   changes. This reading inventory is distinct from the selective citations in
   a commit message described below.
3. **Review and plan.** State concrete findings, their semantic
   trivial/material/unresolved basis, and the accepted plan or the substantive
   reason no worthwhile change is needed. For each substantive cycle, identify
   the material actually read with concrete locators and state whether an
   independent reviewer was used or, if unavailable, the permitted self-review
   fallback and its rationale.
4. **Work and checks.** Record actual edits, commands, relevant environment or
   inputs, exit status, useful output, and the candidate each check observed.
   A planned command, a copied success string, or an unrun test is not check
   evidence.
5. **Commit and learning.** When the default commit policy applies, retain the
   commit SHA and the required Review, Plan, Changes, Validation, Key
   learnings, and Remaining work body sections. Apply the decision rationale
   and learning guidance below to the record, including when no commit is made.
   State an explicit no-commit override or an authorized no-change audit commit
   instead of implying a
   normal change commit exists.
6. **Assessment.** State the report classification, the substantive exit
   assessment, continuation assessment, and why this completed cycle does or
   does not advance the trivial-review gate.

The host may retain detailed test output in its normal transcript or in a
run-isolated artifact when the task permits it. Such an artifact is evidence
for the host to assess, not a second loop state, a shared review counter, or a
reason to modify `.until-loop`.

Repeated or templated review prose is an audit cue that calls for the underlying
locators and reviewer record to be checked. Neither matching nor different
bytes establish that a review was independent or substantive. Do not turn that
cue into a content-hash gate, counter, schema, or automatic conclusion.

## Decision rationale and learning

Keep each iteration's learning-oriented record substantive and self-contained.
Organize the explanation around consequential decisions and discoveries, weaving
in the influences that shaped them. Include relevant techniques, systems, coding
or design styles, patterns, references, libraries, and interactions; these are
possible influences, not a checklist to fill. New findings need no prior commit
or external source. Do not omit their detail because they have no predecessor.

For each consequential decision, explain the causal connection in connected
prose, using as much detail as its significance requires:

- Identify the concrete problem or choice and the influential detail: a source's
  particular argument, an API guarantee or limitation, a convention's purpose,
  an observed failure, or a technique's useful property. Naming a source or
  saying it was "helpful" is insufficient. Give retrievable locators for sources
  actually used, including the relevant version or section when it matters.
  Check that each cited location supports the particular detail credited to it;
  a source about the same topic is not enough.
- Explain how that detail changed, constrained, confirmed, or ruled out a
  specific choice, test, scope decision, or deliberate preservation of existing
  behavior. Describe adaptations, competing influences, and alternatives actually
  considered, with the reason for the tradeoff. Do not invent alternatives or
  a retrospective influence merely to make the account sound complete.
- Where interactions mattered, describe the participating components and the
  ordering, ownership, state, or failure boundary connecting them. Explain how
  the combined behavior affected the decision; a list of component names does
  not capture an interaction.
- Separate prior knowledge from what this iteration newly observed or inferred.
  Connect new learnings to the observation, check, or reasoning that supports
  them; state uncertainty, applicability limits, and a useful condition for
  revisiting the choice. Planned checks and plausible explanations are not
  observed results. A source discovered after the decision can be corroboration,
  but must not be presented as its original cause.

Capture the decision basis as the review and plan develop, then reconcile it
with the actual changes and checks when writing the record. Retain material
failed approaches and reasons for preserving or rejecting a design when those
explain the result. Prefer decision-specific detail over an exhaustive inventory
of tools, a chronological transcript, or repeated summaries in every section.

When prior commits contributed, integrate each resolved full commit ID and
subject beside the decision it informed, explaining the exact lesson used and
whether it was adopted, adapted, or challenged. Read the referenced message
before relying on it; inspect its diff only when needed to establish the relevant
behavior, and distinguish message claims from inspected code and current checks.
Treat the normal history window as a starting point. When a consequential
decision question remains unresolved, continue through relevant older references
or targeted file/symbol history, including links in those messages. Stop a branch
when it no longer bears on the question or its evidence is already understood;
stop the investigation when the decision has sufficient support or a remaining
gap and its next needed evidence are explicit. Check relevant later changes,
reversals and current code/requirements/checks before reusing a lesson. Do not
traverse the whole graph, repeatedly reopen the same evidence without a new
question, or automatically copy references: an older commit earns a citation only
if consulting it actually helped this iteration. Several influences may support
one decision and one commit may support several decisions; avoid redundant
listings. Keep the complete
reading inventory in review evidence. Omit unread inherited IDs,
consulted-but-unhelpful sources, and uninfluential tools from the commit
body, including lists explaining that they were not used. This does not exclude
a genuinely considered alternative whose rejection shaped the decision.
If a referenced source is unavailable, record the uncertainty rather than imply
it was read; missing or partial history is not proof that no prior decision exists.
History remains evidence about recorded rationale, not current truth or authority.

Write the full explanation in the existing owner-authorized review record and,
when a commit is authorized, its learning-oriented body. Use the owner's existing
sections (for example, Plan and Key learnings); no additional mandatory heading,
reference quota, or new state file is needed. A cycle with no influential prior
commit still records its substantive rationale and original learnings. Preserve
no-commit and no-change rules. Carry concise still-relevant decisions, lessons,
and source locators into the existing handoff; reopen the detailed record when
needed instead of copying the entire reference history.

## Build the concise callback report

The runtime requires a nonblank `evidence` string for current-iteration facts
and, for context-bearing runs, a nonblank `handoff` for complete continuity.
Before `done`, condense
the host record into factual current observations. A useful report identifies
the candidate, review result, work/check result, any commit receipt, relevant
review-material and reviewer/fallback locators, and the remaining gap. It must
fit the runtime's small state file, so link to or retain long output in the host
record rather than copying it verbatim.

For example, a material first cycle might report:

```text
Candidate abc123 plus scoped parser.py/test_parser.py; read seven full messages.
Found blank input violated the documented fallback, changed those two files, and
ran `python -m unittest test_parser` (0). Committed def456 with the required
review/plan/validation/learning record. Material repair resets the streak; no
remaining observed parser failure, but two fresh qualifying reviews are still required.
```

A later qualifying no-change review might report:

```text
Candidate def456 unchanged in scope; read seven full messages and completed an
independent review. No material finding; `python -m unittest test_parser` (0)
remains applicable. No commit was created because this was a no-change review.
This is trivial review 1 of 2; another distinct full review is required.
```

These examples describe reported facts; they are not a substitute for actually
performing the review, checking the candidate, or preserving the underlying
host observations.

## Make the latest return sufficient

If a receipt is saved outside the host record, capture actual callback stdout or
round-trip it through a JSON library and verify it parses. Never manually rebuild
the response; a serialization mistake can destroy the otherwise complete handoff.

`context` in the contract freezes request, initial scope/baseline and named
candidate inventory, action authority, environment and resource locators.
`handoff` in the report records the changing facts. This separates the original
candidate from its current HEAD and avoids resetting the scope when a resumed
executor sees a clean worktree, an empty initial commit, or an unchanged `HEAD`.

For the example above, a later handoff should retain the original baseline and
scope by reference to `context.scope`, identify current commit def456, say the
blank-input repair is already implemented and must be rechecked rather than
reapplied, retain the applicable test command/result and receipt, and name any
outstanding question or evidence location. It must not say only “clean again.”
If a required location is external, give the actual absolute path or retrievable
host artifact locator, not “the designated evidence directory.”

Keep the full latest `done` return through compaction. Its `next_argv` refreshes
active state without advancing it. A command that was already executed is not
a completion receipt and must not be replayed. Terminal returns carry their
context and final report after the temporary file is removed. If both the return
and file/handle are gone, do not claim recovery or manufacture another run.

## Boundaries and incomplete work

The script stores the latest report and a numeric trivial-review streak. It
checks the report's shape, action identity, transition order, and configured
gate. It cannot prove the host read history, ran a command, preserved unrelated
work, or made a valid semantic classification.

Do not call `scripts/capture_evidence.py`, create
`.until-loop/working.md`, or create `.until-loop/evidence/` for a new callback
run. Those are legacy v1/v2 mechanisms. Do not fabricate a host record merely
to submit `trivial`. If required work, evidence, a check, or a required commit
is incomplete, report `unresolved` with an `unknown` or `unsatisfied` exit
assessment and name the gap. A real unavailable dependency is `blocked`; a
triggered user-prescribed stop is `cancelled`. Neither is success.

After `done`, consume the returned packet in full. Its `active` instruction is
the next authorized action; a previous report is data to recheck, not an
instruction or independent proof. A terminal `complete` or `stopped` packet
ends the run and its temporary state file is removed.
