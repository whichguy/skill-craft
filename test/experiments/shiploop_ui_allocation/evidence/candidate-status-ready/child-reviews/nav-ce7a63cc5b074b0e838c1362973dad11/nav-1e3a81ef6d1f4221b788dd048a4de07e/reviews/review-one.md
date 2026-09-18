# Improve review one — W1 step-plan

## Candidate and frozen scope

Reviewed the current W1 planning candidate at
`<study>/candidate-status-ready/evidence/w1-step-plan.md`
after the producer callback. The product fixture files were read only for the
named W1 contracts: `README.md`, `docs/design.md`, `docs/platform.md`,
`docs/api.md`, `scripts/probe_environment.py`, `host-observation.json`,
`index.html`, `app.js`, and `styles.css`; the controlled response contract and
raw W1 check evidence were also reviewed. No other case, expected result,
private criterion, report, product implementation, package, remote target, or
Git state was read or changed.

The required `git --no-optional-locks -c diff.autoRefreshIndex=false log -7`
history read exited 128 because this is not a Git repository. No history is
available, and Git was not initialized. The no-commit authority remains in
force.

## Review and independent finding

The review found that `TC-W1-03` incorrectly combined two different boundaries:
the existing account switch intentionally leaves the editor/detail view, whereas
a late old export response must be harmless after that transition. A fresh
read-only independent reviewer independently identified this conflict and also
asked that the complete controlled response schema be made explicit rather than
left implicit in API prose.

## Accepted correction

Updated only the allowed W1 planning evidence. The plan now names
`evidence/controlled-status-schema.md` as the complete response contract and
states the `revision`/`jobs`/`id`/`label`/status normalization boundary. It
reframes TC-W1-03 around a late earlier-account response preserving the completed
account-transition state, and adds TC-W1-08 for the separate same-account
polling invariant: focus, textarea content/selection, editor mode, list/detail
state, and reading position remain unchanged. No product file, test, docs,
configuration, account state, or run state changed.

## Checks and limits

Current outputs are retained in [checks.md](checks.md). `node --check app.js`
passed; `node --test` passed structurally with zero discovered tests, which is
not feature coverage; and `python3 scripts/probe_environment.py` again returned
only controlled fixture facts. The corrected planning candidate SHA-256 is
`cf7924470914b4b89fe746e5aba87f95c9da64162675afa9e12b3c7521214f2c`.
There is no remote deployment access or rendered consumer run, so neither is
claimed.

## Assessment and handoff

Classification: **non-trivial**. The test-boundary correction materially changes
the future implementation oracle, so it resets the Improve trivial streak even
though no product behavior was implemented. The W1 plan remains scoped to
read-only export observation; W2 persistent drafts remain blocked. A second
fresh full review is required after re-reading the absent history and current
candidate, rerunning applicable checks, and checking that this correction itself
introduced no new scope or evidence defect.
