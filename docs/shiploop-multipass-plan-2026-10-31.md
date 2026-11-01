---
Execute: inline
Status: **D1 to D5 approved as recommended (owner, 2026-10-31, "Approve all")**. The harness side (sections 4 and 5) is built, tested and pushed to main
  (03d046c6, aa601d37; quick tier 65 of 65). The ShipLoop behaviour changes (D2 to D4) are built as one candidate on a branch and stay off main until the A/B
  (E2) meets the bar the journal's Round 2 fixed before any run; the fourth link waits for the first live third pass (E1), chain B for E2.
Opened: 2026-10-31
Consumer: the owner, who decides D1 to D5 in section 7; later whoever adds the fourth link or changes how a stage writes the
  living files, and reads the ledger as the before and after
Journal: [shiploop-multipass-journal.md](shiploop-multipass-journal.md); evidence in [experiments/multipass-20261031/](experiments/multipass-20261031/)
---

# ShipLoop for a second, third and fourth pass: the files, the cases and the decisions (plan, 2026-10-31)

## 0. The answer

1. **A second and a third pass work, and the third repeats both leaks.** Eight saved second passes (four pairs on Codex Terra) all passed, kept every earlier
   requirement and decision, numbered the new ones correctly, wrote tests only for the new requirements and touched no earlier test
   ([journal F4, F7](shiploop-multipass-journal.md)). The first live third pass (E1, 2026-10-31) passed 13 of 13 checks and 14 of 14 hidden checks, kept R-1 to R-7
   byte for byte, added 8 stage-report headings (+6.0 KiB) and filed its new decision under `## Superseded` again (journal Round 1, F8).
2. **The permanent files do not stay permanent.** `environment.md` grows 5 to 6 KiB per pass as a chronological record of stage reports,
   and `architecture.md` receives each pass's decision by appending after the last heading: in one of four runs a live decision landed
   under `## Superseded`, and the engine itself then labels it superseded in the next pass's packet (F1, F2).
3. **Do not add per-run files to the repository.** The separation you asked about already exists by location: the three living files and
   the commit trail are permanent; the run folder is the current activity; the delta between them is derived by script (`spec_diff`, and now
   the ledger). The failure is a leak of activity into the permanent files, so the fix is at the leak (section 2, D1 to D4).
4. **A chain longer than two could not be graded.** `load_case` read one level, so a third link dropped the first link's checks. Fixed in
   `chains.py`, with the scorecard reading the same chain (F5).
5. **The case set is built as a chain.** `ticket-comments` is the third link of the ticket chain (assignment, escalation, comments), a request
   that is the delta alone, held to both earlier links' checks and to the hidden acceptance it inherits, with a retention check on
   decision IDs and a calibration (base, reference, seven defects). The fourth link, `ticket-sla`, a request that changes an earlier
   requirement, is built and calibrated (journal Round 3); a second chain on a small base is designed here and not built (section 4).
6. **The delta is now recorded.** Every run's `metrics.json` carries a `delta` block: what changed against the head the run started from,
   where new knowledge landed, how much of the plan was about the new feature, and what the next pass finds. It is a record, not a verdict.
7. **Decided (owner, 2026-10-31, "Approve all"):** D1 to D5 as recommended. D2 to D4 change what ShipLoop's stages write (a counted notice, duty
   edits); they are built as a candidate and tested by an A/B read through the ledger (E2) before they reach main. D1 and D5 are scope.

## 1. The request, in order, and where each part is answered

| You said | Answered in |
|---|---|
| Add end-to-end cases that take an existing case and add a feature, to validate, trace and track the delta | section 4 (the family), section 5 (the ledger) |
| Keep the right files from the prior run; keep this run apart from the old run | section 2 (lifecycle), D1 |
| Maybe separate file names between current activity and permanent decisions; architecture permanent, updated when the increment updates it | section 2 (options), F1, `changed_sections` |
| Prompt, plan and spec checked against the new feature only; old features have their own tests | section 4 (the request is the delta), F4 |
| First make sure ShipLoop is set up for a second, third and fourth pass | section 3 |
| Examine the code, plan, run the experiments needed | sections 3 and 6; journal Round 0 |

## 2. Where each kind of data lives

```
 THE PRODUCT'S REPOSITORY (committed; outlives every run)           THE RUN FOLDER (outside the repository; this run's activity)
 ─────────────────────────────────────────────────────────          ───────────────────────────────────────────────────────────
 src/, test/, docs/…            the product and its tests            state.md      the plan, step plans, test cases, assumptions
 docs/shiploop/spec.md          WHAT   R-<n>, Retired               notes/        discovery, the as-is baseline, run notes
 docs/shiploop/architecture.md  HOW    AD-<n>, Superseded           packets/      what each stage was told
 docs/shiploop/environment.md   RUN, TEST, RELEASE it                run-baseline.txt   the head the run began from
 git history: knowledge commits, the lessons commit                  report.html, trace.html
            ▲                                                                   ▲
            │ the next run reads: the three files (listed by contents in 17 of │ this run, the harness's ledger and Run
            │ 24 stages' packets), the last three commits, the newest lessons  │ Review read these; the next run does not
            │ commit                                                           │
            └──────────────── spec_diff = git diff run-baseline.txt, spec.md and architecture.md (derived, 6 stages' packets) ──┘
```

Each artefact has a consumer (the owner's rule: no consumer, no artefact): the living files are read by the next run's stages with a cleared
context; the run folder by the run's own recovery after a context loss; the ledger by the owner and by the A/B of any change to what a
stage writes. The per-run feature folder was removed on 2026-10-11 because no stage read it
([consumer contract](shiploop-consumer-contract-2026-10-11.md), K1, X11, X13); the eight saved runs agree: the second pass opened the
three files and the commit messages and nothing of the first run's folder.

| Option for "separate file names" | For | Against | Verdict |
|---|---|---|---|
| **A. Three living files, edited in place; current activity stays in the run folder and the commit trail** | already the design; the next pass reads exactly these; no new consumer | the leak (F1 to F3) needs a fix at the stages that write | **recommended (D1)** |
| B. A file per run in the repository (`docs/shiploop/runs/<label>.md`) | explicit trace of each pass | removed 2026-10-11 for lack of a reader; the delta is derivable from Git; n files for n passes | reject |
| C. A change log section in the spec | human-readable history | duplicates `git log`; grows; the origin of an ID is derivable (`git log -S`) | reject; add run-label provenance instead (D4) |
| D. Stage reports out of `environment.md` and into the run's notes | removes F2 at its root: 30 of the 36 stray headings are stage reports and 2 are second copies of the release procedure (the other 4 are that procedure, which X11 intends), and the next run needs none of them | edits the duty text of eight stages; touches X11's "under whatever heading the run uses" | this is D3 |

## 3. Is ShipLoop set up for an nth pass?

| Need | How the engine meets it | Evidence | Verdict |
|---|---|---|---|
| The nth run starts from what the last left | `--continue-from`, `workspace start`; the head is recorded as `run-baseline.txt` | 8 of 8 | works |
| It reads the inherited knowledge | `READS` lists the living files in 17 of 24 stages; intake quotes the last three commits and the newest lessons commit | shell reads of the files in every run; one lessons commit per pass with three non-empty fields | works |
| New data gets new IDs and old ones stay | monotonic `R-<n>` and `AD-<n>`; the refusal of a dropped ID | 0 changed, dropped or retired earlier entries in 4 of 4; numbering continued correctly | works |
| It does not rebuild the old run | `primary` and the test cases scope to the delta | tests cite no kept ID (0 of 19); no earlier test touched (0 of 4); `follows` still names kept IDs in 3 of 4 | works at n=2; `follows` interim |
| It inherits decisions | the AD list, the standing suite, hidden latent facts | pair: 14 of 14 hidden checks in 4 of 4, 7 facts kept from pass 1; third pass: 14 of 14 | works at n=2, and in one run at n=3 |
| Permanent files stay permanent | nothing enforces position or purpose; `X11` forbids a heading gate | `environment.md` +4.5 to 6.4 KiB in pass 2; 4 of 4 `architecture.md` outside their sections; the third pass's first packet lists `AD-3` under `## Superseded` and 22 `environment.md` headings, and a 40-heading cap would hide the newest sections from the fifth pass (arithmetic) | **fails, and compounds** |
| Architecture updated when the feature updates it | stages' duties say "under `## Decisions`" | updated in a section it belongs in: 2 of 4; under Superseded: 1; nowhere: 1 | **inconsistent** |
| The delta can be traced afterwards | `spec_diff` covers spec and architecture only | the ledger now covers IDs, placement, footprint, plan, handoff | built (section 5) |
| A chain longer than two can be graded | `follows` read one level | link 3 dropped link 1's checks | **was broken; fixed** |
| Dating and provenance survive a third pass | none | "Basis: current request" in 4 of 4 pass-2 specs; 3 of 4 titled for the first feature | **fails at n=3**: "current" means another request |

The pass-3 effect of the mislabelled decision and the log-like `environment.md` is the open question; function was not harmed at n=2.

## 4. The case family

**Principles.** (1) A link's request is the delta alone: it names the new behaviour and says that everything the project already does
keeps working. (2) The earlier links' tests are the standing assumption: ShipLoop runs them as the project's suite, and the harness runs the
earlier links' checks and hidden acceptance again afterwards. (3) Retention is mechanical: nothing lost, including decision IDs. (4) The
ledger says where the new knowledge landed and how much of the plan was about the new feature. (5) Each link is a different kind of
increment; (6) chains rotate domains so a fix cannot overfit one probe (SPEC S-8).

| Kind of increment | What it tests | Link |
|---|---|---|
| K1. Additive, must reuse an inherited rule | a decision recorded earlier is respected, not re-derived: the outbox key rule, the data file's record functions | **ticket-comments** (built) |
| K2. Cross-cutting field | a field that flows through API, persistence, CLI, audit and filters keeps every convention | designed |
| K3. Modifying | a request that changes or retires an earlier requirement: `Retired` or in-place rewrite, an earlier decision moved to `Superseded` with its reason, old tests that must change named by the request | **ticket-sla**, built 2026-10-31 |
| K4. Silent conflict | the request says nothing about an earlier rule its obvious implementation breaks | folded into K1 and K3 |
| K5. Changes how the product is built | `architecture.md` is updated in place (`changed_sections` names Structure, Interfaces or Decisions) and gains an `AD` | `ticket-escalation` already; the ledger reads it |

**Chain A, the ticket service** (medium base, [fixtures/node-tickets](../test/shiploop_e2e/fixtures/node-tickets/)): assignment, escalation, comments (built),
then **ticket-sla**, the modifying link (built and calibrated 2026-10-31): escalation waits per priority (urgent 60 minutes, high 240) and an escalated, still
unassigned ticket is escalated once more after twice the wait. That changes the earlier "at most once" requirement and the decision behind it,
so the right result is an edit or retirement of that requirement with its reason, a new `AD` that supersedes the old one, and the old
"escalated once" tests changed by the request. A case names the earlier sentences it changes
(`delta.may_change`, built), so the ledger lists any other changed entry as unexplained and any named one left standing.

**Chain B, a small base** (designed): `user-listing` on `fixtures/node-base` then three links of 30 to 60 lines each, kinds K2, K1 and K3.
Cheap to run (minutes) and a second domain for S-8; built after E2 so it carries the new ledger's A/B.

**What a link carries in `cases.json`.** `follows`; a delta prompt; its own checks (fail-to-pass for the new behaviour); retention (files kept,
no dependency added, no fewer tests passing with the added tests naming the feature, requirement IDs and decision IDs kept); no `quality`
unless it has hidden acceptance of its own, in which case it inherits the nearest by key. Its calibration is a reference delivery built on the
previous link's reference and one defect per sentence or inherited decision it reads.

## 5. What is built

All on `main` (03d046c6, aa601d37); nothing under `skills/`, `agents/` or `changes/` moved, so there is no release and no E2E round owed.

| Piece | File | Tests |
|---|---|---|
| Chains read to their end for regression, quality and the scorecard | [chains.py](../test/shiploop_e2e/chains.py), [run.py](../test/shiploop_e2e/run.py), [scorecard.py](../test/shiploop_e2e/scorecard.py) | [shiploop-e2e-delta.test.py](../test/shiploop-e2e-delta.test.py) `ChainTest` (17) |
| The `delta` block and `delta.py OUTPUT...` | [delta.py](../test/shiploop_e2e/delta.py) | same file, 49 more tests, 11 of them on the eight saved runs and one through `run.main` with the three fake hosts |
| The third link | [cases.json](../test/shiploop_e2e/cases.json) `ticket-comments`, [reference_ticket_comments.py](../test/fixtures/quality/reference_ticket_comments.py) | [shiploop-e2e-ticket-comments.test.py](../test/shiploop-e2e-ticket-comments.test.py) (17) |
| The fourth link, a request that changes an earlier rule, with its own hidden acceptance and the ledger's `may_change` | [cases.json](../test/shiploop_e2e/cases.json) `ticket-sla`, [reference_ticket_sla.py](../test/fixtures/quality/reference_ticket_sla.py), [ticket_sla_accept.py](../test/shiploop_e2e/checks/ticket_sla_accept.py), [delta.py](../test/shiploop_e2e/delta.py) | [shiploop-e2e-ticket-sla.test.py](../test/shiploop-e2e-ticket-sla.test.py) (20), `MayChangeTest` (6) |
| Evidence and its regeneration | [experiments/multipass-20261031/](experiments/multipass-20261031/) | pinned by `SavedPairsTest` |
| SPEC S-11 rows and the README section | [SPEC.md](../test/shiploop_e2e/SPEC.md), [README.md](../test/shiploop_e2e/README.md) | `test-groups` (50) |

What the ledger answers about a pass, per run: IDs added, dropped, changed, retired and **born retired**; stray and duplicate headings and
the named sections that changed (**did the update land where it belongs**); footprint by class, the earlier tests touched and the share of
the start's source files modified; the plan's `follows`, test cases and `primary` split into delta and kept; how the host read and wrote the
living files; the lessons commit and the sections still missing. Its limits: `writes`, `relative_wording` and the class of a path are
heuristics, and a ledger of a first pass on a fixture has nothing to compare an earlier version against.

## 6. Experiments

| | Question | State |
|---|---|---|
| E0 | What does a second pass leave in the three files? | done: 8 saved runs, [journal Round 0](shiploop-multipass-journal.md) |
| E1 | Does a third pass inherit and is it harmed by the second's leftovers? | done 2026-10-31: `ticket-comments` from the saved `bf-codex-r2` pass 2, Codex Terra `xhigh`, ShipLoop 1.26.0: passed, nothing lost, both leaks repeated (journal Round 1) |
| E2 | Does a counted notice plus named destinations (D2, D3, D4) reduce the leak without losing function? | candidate built; arms, bar and predictions fixed in the journal's Round 2; runs after E1 |
| E3 | Does a modifying fourth link retire and supersede rather than duplicate? | link built and calibrated; the live run follows E2, on the real third pass (predictions in the journal's Round 3) |

**E1 predictions** are in the journal before the run, and [round1_readout.py](experiments/multipass-20261031/round1_readout.py) scores them from the run's own files. **Decision rule for E1:** a lost retained check or inherited hidden check means the leftovers
are harmful, and D2 to D4 become urgent. A pass with the same hygiene as pass 2 means they are cost and noise, and E2 decides the fix.

**E2 as proposed.** Arms: A = ShipLoop as published; B = A plus the notice (D2) and the duty edits (D3, D4). Three chains per arm (assignment
then escalation) on Terra `xhigh` with hooks, read through the ledger. Bar, set before the runs: B has `born_retired` 0 in every run, a median of
at most 2 stray headings added to `environment.md` against 4 or more for A, a named section changed in `architecture.md` whenever the pass
added a decision, and no hidden check lost in either arm. About six chains at 40 minutes: four hours of Terra.

## 7. Decisions for the owner

| | Decision | Recommendation | Why |
|---|---|---|---|
| **D1** | Keep three living files, add no per-run file to the repository, derive the delta | **yes** | section 2 |
| **D2** | A counted, non-refusing notice at each knowledge close: an entry that is new in this edit but sits under Retired or Superseded; level-2 headings the edit added that are no named section or repeat one | **yes, behind E2** | consistent with X11 (a count, never a refusal); the first alone fixes the case where the script mislabels a live decision |
| **D3** | Name the destination in the duties of the stages that report (prepare, carry-forward, release-plan, release-verify, operations, system-test-author, discovery, test-strategy): standing facts under the named sections, no stage report, no date, no "this run" | **yes, behind E2** | 30 of the 36 stray headings are those stages' reports and 2 are second copies of the release procedure; the other 4, release-plan's first-pass procedure, stay allowed; amends X11's "under whatever heading the run uses" to "standing, without run-specific values", its stated intent |
| **D4** | The spec duty: title the file by the product, cite a requirement's basis by run label or date, never "current request" | **yes, with D3** | 4 of 4 specs; one sentence, no gate |
| **D5** | Build the fourth link (modifying) after E1, and chain B after E2 | **yes** | section 4 |

Each of D2 to D4 changes what a ShipLoop stage writes, which `AGENTS.md` keeps for the owner. **Decided 2026-10-31: the owner approved D1 to D5 as
recommended ("Approve all").** D2 to D4 are built as one candidate (branch `feat/multipass-placement-725e1a`); "behind E2" is read as: kept off main,
merged only when E2 meets its bar.

## 8. Order

```
 done     [E0: 8 saved runs] ─► [chains.py + delta.py + ticket-comments + calibration] ─► [journal, plan, SPEC/README]
 running                                                     [E1: live third pass] ◄── waits for the port-4180 lease (another session)
 next     E1 result ─► journal + owner reads the plan ─► D1..D5
                       ├─► D2, D3, D4 yes ─► build ─► E2 (A/B through the ledger) ─► release (preflight + E2E round) ─► hosts
                       └─► D5 yes ─► ticket-sla (fourth link) ─► E3 ─► chain B
```

## 9. Risks and unknowns

- **One case pair, one host, one model.** Every number is from the ticket pair on Codex Terra; chain B and a second host are the answer (SPEC S-8).
- **The leak may be harmless.** If E1 passes with the same hygiene, D2 to D4 buy tidiness and fewer tokens, and the owner may decide that is not worth a release.
- **A notice can cause churn.** A model told to move a section may spend a review cycle on it; E2 reads cost and minutes beside the count.
- **The mislabel's false positives.** An entry that is new in an edit and rightly retired in the same edit is rare; the notice says "move it or say why".
- **The hidden acceptance inherited by the third link is the second link's.** It guards the earlier behaviour and does not check comments beyond the inline checks.
  A dedicated module and an independent alternative delivery come with the fourth link.
- **Port 4180 contention** between sessions is a harness fact: one machine-wide lease per fixed port, held for a whole run.
