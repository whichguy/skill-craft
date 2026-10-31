# Question record experiments (2026-10-31): X1-T, X2, X4 and the SG1 replay

Follow-on to [docs/shiploop-planning-pipeline-2026-10-30.md](../../shiploop-planning-pipeline-2026-10-30.md) §9 and
journal [docs/shiploop-question-driven-planning-journal.md](../../shiploop-question-driven-planning-journal.md) (E5
onwards). The owner (2026-10-31): "Yes, exhaustively continue with experiments, evaluation and replanning, anchoring
each goal in a conclusive verdict with evidence or determining a better isolated test to aide conclusions then produce
an improvement plan and implement/test end to end".

This file was written and committed **before** any subject or judge call of these experiments ran (three smoke calls,
named below, checked the routes and are not scored). The rules below are the pre-registered decision rules; results
are appended under "Results" and never edit a rule.

## Subjects

- **Subject: Codex Terra 6.1 (`gpt-6.1-terra`) at `model_reasoning_effort=high`.** The owner, 2026-10-31, while this
  harness was being written and before any call ran: "Focus using Terra 6.1 high for now". Called as the E2E harness
  isolates Codex (`hosts.CodexHost.env`): `codex exec --json --ephemeral --ignore-user-config --skip-git-repo-check -s
  read-only -c approval_policy="never" -c model_reasoning_effort=high -m gpt-6.1-terra`, stdin closed, in a throwaway
  `CODEX_HOME` per call that links only `auth.json` (so no global AGENTS.md, hook or plugin loads), from an empty
  directory outside any repository; the answer is the final agent message (`-o`), and `turn.completed`'s token usage is
  kept. A smoke call on X1's `battleship-A` prompt took 11 s: 470 output tokens (40 reasoning), a 2,239-character result.
- **Not run now:** Claude Sonnet 5.5 (X1's subject; more samples were planned) and two local Ollama models planned as
  weaker-subject proxies (`qwen3.8:27b-mlx`, `gpt-oss:20b`; smoke calls 60 s and 15 s). The E2E subject, DeepSeek flash
  on Ollama cloud, stays unavailable: a direct `/api/chat` call to `deepseek-v4.1-flash:1017-cloud` at 2026-10-31
  07:35 PDT answered "you (dadleet) have reached your monthly usage limit", and every Ollama cloud model shares that
  account. Verdicts below are for Terra 6.1 high; Sonnet and DeepSeek flash are later confirmations.
- **Judge: Claude Opus** (`ask opus`, a different family from the subject), one call per case per sample pair (six
  outputs), outputs shuffled and relabelled, arms hidden, as in X1. A quote counts only if a script finds it in the
  output. Judge calls also run from the empty directory outside the repository.
- X1's own Sonnet calls ran from `cwd-empty/` inside this repository, so the Claude Code CLI may have loaded the
  repository's instruction files in every arm alike; these runs avoid that.

## X1-T (Terra, intake): X1 on the subject in focus

X1's prompts unchanged (`../key-questions-intake-20261030/prompts/`, built from main `d47d69d4`): 4 cases x arms A, B,
C x 4 samples = 48 calls, judged with X1's judge prompt (two calls per case, samples 1-2 and 3-4).

Rules:
- D2 (no catalog) stands if B's recall is within 5 points of C's and B's default agreement is not above C's; otherwise
  the catalog question reopens.
- A recall gap of 15 points or more between A and C (the proposal's X3 rule, applied to this subject) reopens the
  intake wording: the free-form ledger would be adopted at intake.

## X2 (intake → spec): does a numbered record become requirements better than prose?

The `spec` stage of an unattended run, as an exercise with no tools: the shipped spec duty
(`shiploop_prompts.duty("spec", delegation="inline")` on main `3ae78af7`) in the packet's frame (Goal, Done when, Checked
by, guidance, RULES, result template, earlier results quoted by value, the original request). The model writes
spec.md's full contents in a fenced `spec.md` block and its result in a `shiploop-state` block. Discovery and research
results are fixed, identical in every arm (an empty repository for the three greenfield cases; for user-listing, a
discovery summary read from the `node-base` fixture). Arms:

- **A (today):** intake arm A's output (prose `summary`) → the shipped spec duty.
- **D (duty line only):** the same intake A output → the spec duty plus one item: every open question and recorded
  default in the earlier results becomes an acceptance line under the R-<n> it shapes, marked `default`, and is listed
  under `## Open questions` in spec.md.
- **C (the record, phase 1):** intake arm C's output (its `questions` ledger, Q1..Qn, quoted by value) → the spec duty
  plus the same item phrased for Q-rows, each acceptance line citing its row.

A and D share their intake inputs sample for sample (paired). Inputs: Terra's own X1-T intakes s1-s4. n = 4 per case
and arm, 16 per arm.

Judge measures per decision (38 decisions, X1's ground truth): `acceptance` (spec.md pins a specific choice in an
acceptance line that says how it is confirmed), `spec_pinned` (spec.md pins a specific choice anywhere: requirement,
acceptance line, non-functional requirement, constraint, or a recorded default), `carried` (pinned, or recorded as an
open question, gap or default for a later stage, in spec.md or the result summary), `matches` (the committed choice
agrees with the full request: yes, no, na) and `flagged` (the committed choice is marked as a default or assumption the
owner can confirm). Per output: requirement count and scope additions (requirements adding a feature the request did not
ask for).

Rules (pre-registered):
1. **Phase 1 (the record) is adopted** only if C beats A by 10 points or more on `acceptance` (the proposal's measure)
   on Terra 6.1 high, with C's default agreement no more than 2 points below A's. (The proposal asked for two subjects,
   Sonnet and DeepSeek flash; the owner put Terra in focus, so a pass here is adopted for the build and confirmed on the
   others when they run.)
2. **The duty line alone is adopted instead** if D beats A by 10 points or more on `acceptance`, with agreement no more
   than 2 points below A's, and C does not beat D by 5 points or more. Then the record adds nothing the line does not.
3. **Carriage (F2's mechanism).** If A's `carried` share is 0.95 or more on a subject, prose does not lose intake's
   questions at the intake → spec hand-off on that subject, and F2's harm claim is not supported there.
4. Significance: exact one-sided permutation test (the harness's `decide` rule since D5, a9e398e9) over per-run
   values; a difference is a gain only with p < 0.05. Paired arms (A, D) are also reported with a sign-flip test.

## X2b (intake catalog → spec), added 2026-10-31 after X2 was scored and before any X2b call

X2 showed that spec on Terra high carries about 0.79 of the decisions whatever intake A or C hands it, and X1-T that
intake B (catalog + ledger) surfaces 0.91 against A's 0.49. Does B's ledger reach the spec? Arms, on Terra 6.1 high:
**A→spec** (X2's arm A outputs, re-judged) and **B→spec** (the shipped spec duty, intake B's result quoted by value, no
added duty line). 4 cases x 4 samples. Judge: Opus, X2's judge text, one call per case and sample pair holding the A and
B outputs of that pair (four outputs), shuffled with the seed `x2b-<subject>-<case>-<pair>`.

Rule: the intake catalog is adopted (D2 reversed for this subject) only if B→spec beats A→spec by 5 points or more on
`carried` or on `spec_pinned` with exact one-sided permutation p < 0.05, and B's agreement is no more than 2 points
below A's. Otherwise the intake gain does not reach the spec and the catalog is not adopted.

## X2b-S (Sonnet), added 2026-10-31 after the Terra verdict and before any X2b-S call

The intake catalog ships for every subject, and on Sonnet X1 it committed more guesses that conflict with the full
request (agreement 0.64 against 0.77). Does that reach Sonnet's spec? X2b's design on Claude Sonnet 5.5 (`ask sonnet`,
xhigh), fed X1's own Sonnet intakes A and B (samples 1 and 2 only: n = 8 per arm); judged by Opus as X2b.

Rule: a fall of more than 10 points in B→spec's agreement or carried share against A→spec's flags the catalog as
subject-dependent for the owner; otherwise the catalog stays for every subject.

## X4 (step-plan): does a Proof-input question cut proof-order faults?

Isolated replay with a script grader, no judge. Packets are step-plan packets archived by saved runs (the DeepSeek
battleship W1 of 2026-10-26, whose Proof needed a test the later test stage writes, and control packets whose plans
were clean). Arms: the archived packet with today's step-plan duty in place of its guidance (A), and the same plus one
sentence in the Proof item (Q): "For each step's Proof, name what it reads and which earlier step or the item base
provides it; a test file the test stage writes later is not provided." The subject answers with the step plan only; SG1's
rule (`check_plan` in `../sdlc-gates-20261030/sg1_proof_order.py`, inferred mode) flags a fault.

Subject: Terra 6.1 high, 8 samples per packet and arm. Rule: Q is adopted if its fault rate is below A's with exact
one-sided permutation p < 0.05 and its share of unparseable plans is not higher. If A's fault rate is 0 on every packet,
the replay cannot separate the arms on this subject and X4 is closed as "no measurable fault to cut" for Terra.

## SG1 replay (the SDLC gates proposal's bar, run here because the saved runs are on this machine)

Ran first, read-only, on `~/e2e-runs/2026*/*` (the proposal's corpus), before this file. Its bar was set in the
proposal §5 before any replay. Held-out corpus for any refinement: the saved runs outside that glob
(`~/e2e-runs-brownfield*`, `~/e2e-runs-owner-note`, `~/e2e-runs/{e6,e7,experiments,effort,terra}*`).

Rule for a refinement found on the first corpus: it counts only if, on the held-out corpus, it flags no step whose
Proof passed at implement.

## Results (2026-10-31; journal E5–E9)

Every subject call parsed; every judge call returned JSON; 0 judge quotes were missing from their outputs.

| Experiment | Arms (n per arm) | Result | Rule |
|---|---|---|---|
| X1-T, Terra high | A, B, C (16) | recall 0.493 / 0.907 / 0.657; agreement 0.83 / 0.77 / 0.67; B vs A p < 0.0001, C vs A p 0.003 | D2 does not hold; intake wording reopens (`scores-intake-terra.json`) |
| X1-T, Terra xhigh (control, added after X1-T) | A, B, C (16) | recall 0.513 / 0.981 / 0.681; agreement 0.74 / 0.69 / 0.69 | the same (`scores-intake-terra-xhigh.json`) |
| X2, Terra high | A, D, C (16) | acceptance 0.635 / 0.687 / 0.650; carried 0.789 / 0.808 / 0.807; agreement 0.65 / 0.65 / 0.62 | phase 1 not adopted; duty line not adopted (D +5, paired p 0.008, below the 10-point bar); prose does not carry 0.95 (`scores-spec-terra.json`) |
| X2b, Terra high | A, B (16) | carried 0.776 / 0.897 (+0.120, p 0.013, paired 0.001); pinned 0.650 / 0.717; agreement 0.65 / 0.65 | intake catalog adopted (`scores-spec-x2b-terra.json`) |
| X2b-S, Sonnet 5.5 xhigh (generality check, added after the Terra verdict) | A, B (8) | carried 1.000 / 1.000; pinned 0.935 / 0.960; agreement 0.59 / 0.63 | no fall of 10 points: the catalog stays for every subject (`scores-spec-x2b-sonnet.json`) |
| X4, Terra high | A, Q | v1 no-tool packets: 64 of 64 `blocked` (`x4/terra-v1-blocked/`, `scores-x4-terra-v1-blocked.json`); v2 without the harness lines (`x4/terra-v2-blocked/`, one call): still blocked (packets do not quote the knowledge files); step slices on the Codex harness (`x4/score_slices.py`, `scores-x4-slices.json`): 1 of 1 clean in each arm, both copying the case's seeded proof | closed: no isolated design measures it; D6 is the fix |
| Live A/B, Codex harness, Terra high, all tools | A (3ae78af7), B (the change), 6 runs each | B: 6/6 pass, 0 runs with a proof-order send-back (A: 5/6 pass, 4 of 6), p 0.030; the refusal fired 3 times; every B intake wrote the ledger | the build holds live (`scores-e2e-ab.json`, `e2e_ab.py`; test/shiploop_e2e/LEARNINGS.md) |
| SG1 | — | `sg1/`: proposal corpus 2 flags (1 true, 1 a contract breach); held-out 8 flags in 5 plans; 9 of 12 implement send-backs are proof-order; the shipped rule refuses 9 of 182 plans (7 before that send-back, 1 the breach, 1 with no implement after) | the post-hoc refinement is rejected (misses `bf-codex-r1-ticket-escalation`); D6 built with the original rules plus an earlier-step exemption |

Reproduce: `python3 jobs_intake.py`, then `QR_WORK=<scratch> python3 run.py jobs-intake.tsv`; `python3 judge_intake.py
terra` and `run.py jobs-judge-intake-terra.tsv`; `python3 score_intake.py terra` (and `terra-xhigh`); `python3
build_spec.py terra` (X2) or `build_spec.py terra B` (X2b), `run.py jobs-spec-terra*.tsv`, `python3 judge_spec.py terra`
(X2) or `judge_spec.py terra A,B spec-x2b`, `run.py jobs-judge-spec*.tsv`, `python3 score_spec.py terra` or `score_spec.py
terra spec-x2b`; SG1: `sg1/refined.py`, `sg1/replay_d6.py`; X4: `x4/build.py`, `x4/score.py`, `x4/score_slices.py`.
The judge prompts, spec prompts, Codex event streams and stderr are not committed (`.gitignore`): the builders write the
prompts deterministically from committed inputs, and each envelope keeps the call's token usage.
