# Stage-prompt review: brief for each reviewer (2026-10-31)

The owner asked: "Examine each prompt template and help identify if improvements or side tests should be executed."
You review a group of ShipLoop's stage prompts (the packet each stage's model receives). For each one, decide:

- **improve**: the evidence already shows a defect, and you can name the wording or mechanism change that fixes it;
- **side-test**: there is a plausible gain, but it needs an offline experiment before deciding (design that
  experiment);
- **no-change**: nothing measurable to gain, or the idea was already tried and rejected.

You are read-only. Do not edit files, commit, run E2E cases, or call models. Local read-only scripts and `git` reads
are fine.

## Where things are (repo root /Users/dadleet/src/skill-craft, on main)

- **Rendered prompt.** `cd skills/shiploop/scripts && python3 -c "import shiploop_prompts as p; print(p.PROMPTS['<stage>'])"`.
  Duty text is `p.DUTIES['<stage>']`; the stage row and its done_when are in `shiploop_stage_spec.STAGE_SPEC['<stage>']`.
  Callback validation for the stage lives in the scripts. Grep a refusal message to find its code.
- **Stage health across 96 traced archived runs.** `docs/experiments/prompt-template-review-20261031/stage-health.txt`
  and `.json`, made by `stage_health.py` in the same folder. Columns:
  - runs reaching the stage, and packets sent;
  - `ref`: real refused callbacks, which the model had to repair;
  - `chk`: refusals from `check_only` callbacks;
  - runs with any refusal;
  - median and total wall minutes;
  - other accepted outcomes (send-back, add-work);
  - the commonest refusal messages, with numbers stripped.

  Many runs predate current code. Before treating a refusal as live, check that its message still exists in
  `skills/shiploop/scripts` and when it was last changed.
- **Archived runs.** `~/e2e-runs*/**/.shiploop-runs/*/run/`, skipping `/slice/` and `/test/fixtures/`. Each run
  directory holds:
  - `trace.jsonl` (packets and commands; refusals are `complete` commands with nonzero `exit` and an `error`);
  - `packets/sent/*.md` (the exact packets);
  - `results/` (the model's submitted results);
  - `callback-attempts/`;
  - `state.md` (history);
  - `tests/*-verify*.md` (ShipLoop's test-run records).

  The case folder above `.shiploop-runs` has `quality/` (the harness's own checks) and `review-export/`.
- **Earlier measurements.**
  - `docs/experiments/coverage-ledger-20261031/README.md` (test coverage by requirement ID, 72 runs);
  - `docs/shiploop-test-stage-prompt-design-2026-10-30.md` (E7/E7-F test-stage arms);
  - `git show -s 488ffbd9` (condition-review pilot on product-acceptance);
  - `git show -s d9fefb11` (final-test-completeness evaluation).

  Other journals are under `docs/` and `test/shiploop_e2e/LEARNINGS.md`.
- **History.** For each stage:
  - find the commits that shaped its duty: `git log --format='%h %ad %s' --date=short -S'<distinctive phrase>' -- skills/shiploop/scripts/shiploop_prompts.py`;
  - also run `git log --grep='<stage>'`;
  - read the full messages of the material ones (`git show -s <hash>`).

  Messages record measurements, rejected approaches and owner decisions. Do not re-propose a rejected approach
  without new evidence, and cite the commit that rejected it.

## Owner rules a proposal must respect

- Fix generically: no stack-, language- or product-specific rules in prompts, even in catalogs.
- No arbitrary small caps on model text (owner 2026-10-28). Spill long text to a file rather than refuse it. A
  refusal that is only a character cap is a candidate for removal, not for more prompt text.
- Evidence of progress is a script-run test that passed. Never make model judgement the completion check.
- Context is cleared between stages, so every packet restates its stage. That repetition is grounding, not waste.
- Prompts should be concise. A change must be meaningful: cut ineffective detail and keep every obligation.
- Packets mention Improve only as a directive.
- Never add or change a limit on ShipLoop's loops. Flag such an idea for the owner instead.
- KISS: fix what breaks a normal run; do not add guards against adversarial models.
- Use one term per concept, matching `skills/shiploop/references/glossary.md`.
- Tests follow each step's intention. Request coverage is a plan property (owner 2026-10-28; F3 replaced TS1).
- Rank by the gain on any project. Quality comes first, then tokens, then time.

## What to return

Write your report to `docs/experiments/prompt-template-review-20261031/reviews/<group>.md`. Keep it to about 1,500
words, and return the same text as your final message. For each stage, in this shape:

```
### <stage> — verdict: improve | side-test | no-change
Signals: <runs, packets, refusals (live or retired), minutes; one line>
Findings:
- <claim> — evidence: <run path or packet file, refusal count, commit hash>; live in current code: yes/no
Proposal: <the exact wording or mechanism change, or "none">
Gain / risk: <what it buys on any project; what could break>
Side test (if side-test): question; corpus (archived packets or runs, offline); measure; predeclared decision rule; cost
History respected: <commit hashes whose decisions this keeps or would revisit>
```

End with **Group top picks**: at most two items, ranked by expected gain on any project, each with its cost.

Prefer a few well-evidenced findings to many speculative ones. Say "no-change" plainly when that is the answer. A
claim is evidenced only when it cites a file, count or commit you read.
