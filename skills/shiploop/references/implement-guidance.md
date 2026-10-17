# Implement guidance

ShipLoop inserts each section below into every implement packet, word for word (shiploop_static.static_text).
Edit the guidance here; the packet tests pin what each packet prints.

## Method
Complete this step's assigned criteria (Serves), with the connections they need, so this step's part works at its
boundary. Follow the R-n requirements and AD-n decisions that constrain it. Build nothing a later step owns, and do
not claim a whole R-n is satisfied because this step contributes to it. A step can change code, configuration,
platform settings, data, content or documents; the method is the same.

1. Read the assignment and its anchors: the criteria, their quoted R-n, the item's AD-n, the HOME sections under
   Anchored in, and the listed cards. Give a reason for any card you set aside. Use each listed step skill for its
   purpose (invoke it, or read its SKILL.md and follow it). Write a short checklist of the constraints these put on
   this step in RUN/notes/<action>.md. Reuse it each iteration, refresh an entry when its anchor changes, and rebuild
   it from this packet after context loss.
2. Inspect what exists: the parts this step changes, what depends on them, the existing example, and the services the
   surrounding environment already provides.
3. Settle scope, authority and design before building, using the considerations below. Where the anchors settle a
   question, follow them. Where they are silent, decide within the assignment and write it back. If the work
   conflicts with an R-n or AD-n, or needs something outside the assignment, report revise.
4. Build and check: run the relevant checks after each meaningful batch of changes, and run the Proof on the final work.
5. Compare the final change with every checklist entry and each consideration.
6. Record `considerations`, `evidence` and the write-backs.

## Considerations
Answer each in `considerations`: the concrete handling and the anchor that governs it, or why this step does not
affect it. "Handled", "reviewed" and a bare "N/A" are not answers.
1. Whole step [criteria · ## Structure]. Everything the assigned criteria need at this step's boundary: the change and
   its connections (entry points, registration, wiring, configuration, permissions, content, documentation a criterion
   requires), placed where ## Structure says. Note any changed usage or operations for the document stage.
2. Interactions [criteria · ## Interfaces and boundaries · interaction AD-n]. Those this step affects or its criteria
   require. People: what they see and do; waiting, error and empty states; accessible use. Systems: contracts,
   untrusted input and its validation, which actors may do what, sensitive output, slow, failed or repeated messages,
   compatibility with existing consumers. New work outside the assignment: report revise.
3. Building [## Stack · ## Commands]. Produce a valid artifact the way this project builds or validates it. Add no tool
   or dependency without a present need, and record any you add.
4. Deploying [## Targets and runtimes · ## Access and accounts · ## Platform facts · ## Real-boundary checks]. Target,
   order, settings per environment, staged or reversible activation where the risk calls for it, the check after, and
   the undo. Perform only the effects the run's recorded authority covers. Preparing or recording a release action
   does not authorize running it.
5. State [## Structure · storage AD-n · ## Non-functional requirements]. What the step reads, creates or changes, with
   its owner and its shape before and after; compatibility with stored state; ordering, atomicity and concurrent
   updates. Any transition it needs is prepared, applied only where authorized, safe to rerun, and recoverable from a
   partial failure. Invent no storage.
6. Operating [## Non-functional requirements · ## Conventions · ## Platform facts]. What an operator can see and
   diagnose; cost, limits and capacity; independent work run in parallel where the platform supports it and the gain
   is real; secrets and permissions over time; retention, cleanup and owner.
7. What exists [## Structure · ## Conventions · ## Skills · ## Platform facts]. Before creating anything, reuse it
   unchanged, combine existing pieces, or extend one. That applies in the repository and to the services the
   environment already provides (identity, storage, queues, scheduling, caching, logging, search, notification).
   Duplicate none. Keep current behaviour working, and follow the example.
8. Proof [## Commands · ## Harnesses and suites]. What demonstrates each assigned criterion now.

## Evidence and proof
- `evidence`, one entry per assigned criterion: what you ran or inspected, what you observed, where the output is,
  what it establishes and what it does not. A description of the change or a future check is not evidence. For
  document work, an inspected passage plus a consistency check is.
- An unconfirmed assigned criterion blocks done. A check a later stage owns stays deferred, with its owner, and is
  never presented as done.
- Do not weaken or replace the Proof to get accepted. If it cannot validly assess this step now, report revise naming
  the mismatch. A passing Proof never replaces criterion evidence.
- Add no permanent tests or suites here; the test stage writes them. Temporary probes in RUN/scratch are allowed.

## Write back
- A new implementation decision that fits every R-n and AD-n: the next AD-<n> under architecture.md ## Decisions, with
  its basis. A change to, or departure from, an R-n or AD-n is a revise; recording an AD-n does not authorize it.
- A command that now works: environment.md ## Commands. A platform fact or limit: ## Platform facts. A new module,
  file or data entry: architecture.md ## Structure. Never edit spec.md here.
- For a step that changes code, Code craft (inserted below) is the detail under these considerations. Report it
  through them, not as a second assessment.
