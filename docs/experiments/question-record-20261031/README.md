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

## Results

(appended after the runs)
