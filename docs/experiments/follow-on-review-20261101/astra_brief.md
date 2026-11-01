# Brief for an independent design review (please answer the questions at the end)

**What I want from you.** I am the Claude session that did the work below for the repository owner. The owner asked whether an independent model could give feedback on the *intention* of this work and offer other ideas. Please be critical: say where the intention is wrong, thin or aimed at the wrong target. Do not defend my choices; where I describe a reading of mine, it is flagged as "our reading" and you should challenge it.

## The system

ShipLoop is a markdown-authoritative delivery harness (the skill-craft monorepo). Scripts own navigation and prompts; the model does one step per packet. One run is one request. Stages run intake, discovery, research, spec, test-strategy, plan, an implement loop per work item, system-test, release stages and a handoff. The script gates each stage's result. A run writes permanent project knowledge files (a living spec, an environment file, an architecture file) and a lessons commit ("learned", "key considerations", "open for the next run") that the next run quotes. A run that cannot proceed without a person's answer stops ("blocked") and asks.

## The owner's intention (dictated, 2026-10-31)

"Once a feature is built and deployed, a replanning-style step asks what building taught about the feature or spec; for a substantial feature that has not concluded, re-enter ShipLoop from the top with an improvement prompt instead of exiting, behind a gate." Since then the owner has sent the one-line prompt "Determine how to conclude, plan out, and implement." after each delivery and expects the work to be driven to a stopping point.

## What was done (two days)

1. A design note, six revisions, with options for a post-delivery step and four decisions (D1 a follow-on run rather than an in-run back edge; D2 recommend-only versus auto-start; D3 no ceiling on chains; D4 build or not).
2. An offline look at 166 finished E2E runs (small, saturated, every run completes): the leftovers each run reports were classified by a first reader and three later reader passes (two passes of one model, one of another). Result: a "decision" (a choice only a person can make) in 1.2% to 1.8% of runs; no confirmed "gap" (an unmet request outcome that needs no person's answer).
3. Built the recommend-only version and released it. The handoff result now carries `follow_on`: a classified, evidence-cited list of leftovers (classes gap, decision, person, capability, extension, debt, note), each citing a record the run holds (an unverified row, an assumption, the lessons, a stage result, a commit). A gap or a decision makes the script write a request file for a follow-on run and print the command that starts it. Nothing starts by itself and `done` is never blocked.
4. Live checks (Codex gpt-6.1-terra at xhigh, small command-line tasks). Four unprimed runs: lists of 0, 1, 1 and 0 entries (notes only), all accepted on the first try. Then primed requests: (a) a request that reserves one choice for the person: both runs filed a `decision`; a run started from the generated request file blocked at its spec stage and asked the requester; a run started from the same request plus the answer delivered and did not re-file. (b) a request that defers one option to a later run: one run filed a `gap`, the other a `note`; a run started from the gap's request delivered unattended.
5. Our reading: a recommended decision is a request for a person, so only a gap could ever run unattended; gaps seem to appear only when the request arranges them; so auto-start has little to start and we stayed recommend-only.

## Known weaknesses

All live evidence is on tiny tasks with the occasion arranged, two to four runs per cell. The natural rate of recommendations on the owner's real features is unmeasured. The classes are our own definitions and the model decides what counts as a leftover. No run has used the list on a substantial feature. The "gate" of the original idea (decide whether the feature has concluded) was never built: we built a list of leftovers, not a test for whether to continue. A person starts every follow-on run.

## Questions (answer each separately, with reasons)

1. Is the intention right? What is the real goal behind "re-enter with an improvement prompt", and does a recommend-only list of leftovers serve it, or is it aimed at a symptom?
2. What is the strongest argument that this whole direction is not worth the complexity it adds? Where would you cut?
3. The original idea has a gate ("has the feature concluded?"). Is there a better way to decide whether a delivery should be followed up than a model-classified list of leftovers? Give concrete alternatives (for example held-out acceptance checks, spec-versus-behaviour diffs, usage or failure signals from the deployed feature, a reviewer pass).
4. What other ideas would you try for the same intention: inside a run (a reflection stage, stronger release verification), between runs (a learning log feeding the next intake), or at the owner's level (a review cadence)? Rank by expected value and cost.
5. What are the biggest blind spots or risks in what was measured (priming, small n, model-written classes, one host and model)? What single experiment would most change the picture, and how would you run it cheaply?
6. If you were the owner reading this summary, what would you do next, and what would you stop doing?

Give a ranked list of at most seven recommendations. For each: the claim, why, the smallest experiment or check that would refute it, and its rough cost. Keep the whole answer under about 1,200 words. If you can read files, the design note is docs/shiploop-follow-on-run-design-2026-10-31.md and the journal is docs/shiploop-follow-on-run-journal.md (Rounds 0 to 7) in the working directory; you do not need them to answer.
