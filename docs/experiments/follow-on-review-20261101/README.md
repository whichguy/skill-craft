# Independent review and audit of the follow-on work (2026-11-01, Round 8)

Consumer: the owner, deciding whether the follow-on work is concluded and what, if anything, to measure next; the journal (`docs/shiploop-follow-on-run-journal.md`, Round 8) records the dispositions.
No ShipLoop run was made in this round. Everything here is a model review or a read of existing records.

## What was asked, and of whom

1. **Astra at max effort** (`ask.sh astra ask --effort max --profile consult`, exit 0, about 5 minutes, read-only). The question was the owner's: "did we ask Astra if there's any feedback on the
   intention that we were trying to do with this session and see if it had any other ideas?" The brief (`astra_brief.md`) states the intention in the owner's words, what was built and measured, flags
   my readings as "our reading" and asks six questions; the answer is `astra_answer.txt`, verbatim.
2. **A 12-agent workflow** (`workflow.js`; agents inherited the session model, Claude Sonnet 5.5, at the session's effort). Four lens reviews of the intention, each given only the neutral brief and
   read-only access to the repository (cut, gate, ideas, evidence), then a synthesis; and six adversarial audits of the Round 5 to 7 numbers, hashes and claims against the raw run folders
   (Round 6 numbers, Round 6 instruments, Round 7 numbers, docs consistency, release claims, the unprimed rate), then a completeness critic. The full return is `workflow-result.json`; the audit's
   issues, with the evidence each cites, are rendered in `audit-issues.txt`.

## What I verified myself before relying on any of it

Each of these I re-ran or re-read; the rest of the audit's issues are relayed with the audit's own evidence and are marked as such in the journal.

| Claim | Check | Result |
|---|---|---|
| `SKILL.md` was 30,011 bytes before b65984554d7769306518ed4bcb822dbaffbb9292 and 30,115 from it on; the 2.29.0 release did not add 104 | `git cat-file blob <rev>:skills/shiploop/SKILL.md \| wc -c` at 3d5732d0, b6598455^, b6598455, d06e18a5, 4224161b, 6a6cb101 | 30011, 30011, 30115, 30115, 30115, 30115: the audit is right |
| ShipLoop stopped committing `SHIPLOOP.md` as knowledge on 2026-10-11, before both builds | `git show -s 589bc03ebe4bb31759a371e10bbc261bb071aab3`; `git merge-base --is-ancestor` that commit and 5c9bf5e8786a1d44a1389a3b98fa8c5da3c05a8a | title "...remove ... ShipLoop's SHIPLOOP.md", dated 2026-10-11, an ancestor of the 2.31.0 release: the audit is right |
| The first readout slip was a full-length hash compared with a 12-character stored hash, not "a different string" | `run.py` line 637 `hashlib.sha256(prompt.strip().encode()).hexdigest()[:12]`; fa7b34ab31896eebddb69e23d977e11d0b388669's readout compared the full digest | the audit is right; my stated cause was wrong |
| Both link-3 runs made digits separators | `python3 slug.py "Hello2World"` and `"Route 66 Café"` in all six work trees | link 1 and link 2: `hello2world`; link 3 (a and b): `hello-world`, `route-cafe`: the audit is right |
| Round 7 had 3 runs, not 4 | `tally_follow_on.py` on `follow-on-gap-d79bc3` | `runs: 3` |
| link3-a took 12.9 minutes, not 12.8 | `result.json` `process.elapsed_seconds` | 772.4 s = 12.87 min |
| The runs' own start loads were 12 to 22 on 18 CPUs | `result.json` `environment.start.loadavg` | 1-minute values 12.4 to 22.0 |
| 2.31.0 was published at 10:38:16 on 2026-11-01 | `git show -s 5c9bf5e8786a1d44a1389a3b98fa8c5da3c05a8a` | 10:38:16 -0800 |
| Between the 2.31.0 and 2.32.0 builds ShipLoop's diff is wider than the plan marker line | `git diff --stat 5c9bf5e8 01d537e9 -- skills/shiploop` | 6 files, 43 insertions, 769 deletions (`shiploop_backchain_graph.py` 778 of them) |
| Astra: a `gap` must map to a sentence of the request | `shiploop_follow_on.py` (`request_sentence`, `_need`) | true: a gap without an `S<n>` is refused; a requirement absent from the request can only be a `decision` or an `extension` |
| Astra: the follow-on test lets a known request defect coexist with `done` | `test/shiploop-follow-on.test.py`, `test_a_gap_and_a_decision_recommend_a_run_...done_is_not_blocked` | true as a description: it asserts `done` with a `gap` filed. It is the design ("`done` is never blocked", design D2/4.3), not an oversight; whether it should be is a design question for the owner |

## Dispositions (the journal's Round 8 has the same table with the edits)

| Idea | From | Disposition |
|---|---|---|
| Score the list and any gate against the owner's own next message after a real delivery | all four lenses | **Cannot be done now, as far as a bounded search shows.** The M3 tally pointed at `~/.shiploop`, `~/src/.shiploop-runs` and `~/src/workflow-engine/.runs` read 2 runs, both `active` (the `sf-battleship` pair), 0 with a recorded list. `~/.shiploop` holds one old tic-tac-toe run in an older layout with no `follow_on`; `workflow-engine/.runs` holds five `succeeded` runs of another harness. A `find` for `state.md` under `~/src` to depth 5 found nothing else. It is a bounded search, not a census of the machine. So there is no corpus of finished real deliveries to read. The owner's one-line prompts in this session followed my deliveries, not ShipLoop runs. The owner's, from their next deliveries. |
| Seed a known gap into finished runs and see whether the list files it | gate, evidence, ideas | **Not cheap with this harness.** The list is written by the run that did the work, at its handoff; a gap seeded afterwards would need the handoff stage replayed on altered state, which `run.py` does not do (`--continue-from` starts a new run). Not built; a harness feature, the owner's call. |
| Unprimed-occasion test: 4 runs with the occasion in the sandbox and none of the words "later", "defer", "reserve" | evidence, gate | **Kept as the one experiment that would most change the picture; not run.** Pre-registered in the journal (prediction: at least 2 of 4 do not file). Three reviewers said to stop contrived primed rounds; this one is a detection test, but it still needs a go because its result decides cut or keep. |
| Fresh-context acceptance-probe stage (verbatim request plus the running build, advisory) | cut, gate, ideas, Astra | **Not built.** It is the gate the owner described and the list is not; building it is a new feature whose value on real work is unmeasured. Recorded as the candidate if M3 shows demand. |
| Cut the classes down to a one-field handoff note | cut | **Not now.** Deleting a shipped feature sets direction (AGENTS.md); the lenses disagree on timing; recommendation 6 of the synthesis waits for owner-action data that does not exist yet. |
| Stop rule: frozen if under 1 in 5 deliveries start a recommended run within 30 days | cut, ideas | **Proposed to the owner, not adopted by me.** The rule would have stopped Rounds 5 to 7 only if the owner's deliveries had been counted then; they were not. |
| Stop writing journal rounds and design revisions on primed tasks; answer repeated "conclude" prompts with a stopping judgment | Astra, cut, evidence | **Adopted.** This round is the last one on primed or arranged tasks; the closing judgment is in the journal. |
| Wording fixes from the audit (about 30 items) | audit | **Applied** in the journal, the design note and the three experiment READMEs, each marked "corrected 2026-11-01 (Round 8)" in place. The older commit messages stay as written. |

## Contrary evidence and limits

- The four lenses share one model family and one brief, and the brief carried my framing; Astra is a different family but read the same brief. They agree with each other more than the brief's flagged
  weaknesses alone would make them, so I do not count the agreement as independent confirmation of the direction. The strongest shared point (value on real features is unmeasured) was already in the brief.
- The audit's issues were verified by me only where the table above says so. The audit did not cover Round 5's README as a group, findings F41 to F48 and F50 on, the follow-on module's behaviour beyond
  the double-period fix, the request file's self-sufficiency in a fresh checkout, the host refreshes on Codex, Grok and Cursor, or cost (`audit-issues.txt` ends with the critic's list in
  `workflow-result.json`). Those remain unaudited.
- Nothing here measures whether the feature helps on real work. That needs the owner's deliveries.
