# Improve review two — W1 step-plan

## Candidate and scope recheck

Reviewed the current W1 planning candidate at
`<study>/candidate-status-ready/evidence/w1-step-plan.md`
and its permitted product contracts. The scope remains a read-only, account-scoped
`GET /api/exports` observer only: no export request, collection selector,
operation reconciliation, download flow, persistent draft, product implementation,
or remote action is authorized.

The required `git --no-optional-locks -c diff.autoRefreshIndex=false log -7
--format='%H%x09%s'` history read exited 128 because the fixture has no Git
repository. History remains absent; Git was not initialized.

## Independent finding and accepted correction

A fresh independent read-only review found a material verification gap in the
then-variable status presentation: a new job, changed state, or retry message
could shift the page or open detail reader, while the planned fake-DOM tests did
not establish a browser scroll oracle. That finding was rechecked against the
current `main` and `.detail-scroll` structure, accepted, and corrected only in
the allowed W1 plan evidence.

The corrected plan now specifies a bounded summary instead of a variable job list,
places the status slot as the first `main` child outside the existing list/detail
containers, reserves the same explicit block/min/max size per breakpoint, and
keeps error copy inside that slot. It adds a reading-position invariant: status
refreshes may not alter `#detail` geometry, page scroll offset, or
`.detail-scroll.scrollTop`, and may not call focus or scroll APIs. TC-W1-07
now requires a local rendered-browser offset/geometry measurement for new-job,
state-transition, and retryable-error states; TC-W1-09 covers many jobs within
the bounded summary. The plan retains the explicit gap if such a browser fixture
is unavailable later; no browser run is claimed here.

No product source, test, documentation, configuration, host observation, package,
Git state, remote target, account state, or parent run state changed. The current
candidate SHA-256 is
`dbc4421bfa941cd680a0130a7bf6e22f296d0760583800e5846e6a200ada520b`.

## Current checks and assessment

The current check outputs are recorded in [checks.md](checks.md). `node --check
app.js` passed. `node --test` exited 0 with zero discovered tests, so it is a
baseline coverage gap rather than feature evidence. The environment probe again
reported controlled fixture facts only, not a deployed or consumer target.

Classification: **non-trivial**. The corrected layout and executable-browser
oracle materially change the future implementation/test contract. This resets the
trivial-review count. Two later, distinct complete reviews must find only trivial
or no issues before Improve can complete; they must reread the absent history,
recheck the candidate and permitted sources, rerun current local checks, and
preserve their records in this child directory.
