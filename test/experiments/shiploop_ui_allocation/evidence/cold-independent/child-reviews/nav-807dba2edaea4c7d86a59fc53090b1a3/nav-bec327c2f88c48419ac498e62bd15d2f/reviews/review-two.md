# Improve review two — material API-contract correction

Binding: `nav-807dba2edaea4c7d86a59fc53090b1a3/nav-bec327c2f88c48419ac498e62bd15d2f`.
This is a distinct review after `review-one.md`, not a replay of the first
callback.

## Revalidated facts

- `git --no-optional-locks -C product log -n 7` again exited 128 because this
  fixture archive has no Git repository or reachable history.
- The original producer output remains SHA-256
  `5664255bd6d7b370ed7b7c6f62342c6d7d7d45944c510567cd10c70d23fe2461`.
  The only non-evidence edit is the named W1 plan; product content retains every
  hash recorded at the producer boundary.
- `docs/api.md:2` names routes and high-level outcomes but does not specify the
  account-to-collection mapping, list-item/job identity, operation response,
  job response, status/terminal vocabulary, revision representation, or field
  holding a completed download path. Neither current `app.js` nor `index.html`
  supplies an export implementation or an alternative authoritative schema.
- The current v2 probe, `node --check app.js`, and the zero-test `node --test`
  observation remain as recorded in `checks.md`.

## Finding and decision

The first correction fixed the unsafe fake collection mapping, but it left two
material plan defects:

1. it treated the high-level route prose as sufficient to make list, operation,
   job, revision, terminal-state, and download-path fakes authoritative; and
2. it said the collection gate blocked every later case and all product mutation,
   even though only the API-dependent assertions require those missing contracts
   and local preservation/storage coverage is separately absent because there is
   no test harness.

The revised W1 plan now makes `T-W1-00` / `EXP-000` require both the
account-scoped collection source and the response contracts. It maps each
API-dependent case to the precise required portion of that source, rejects both
invented IDs and invented JSON fields, and separates the missing integration
contract from the independent missing-test-harness fact. It still does not
authorize code, test, API, or deployment work.

This is a material correction to prerequisite ordering and test-oracle
validity. The clean-review streak resets again. Two later, distinct qualifying
no-change reviews remain necessary before the runtime can complete.

## Review limitation

No independent reviewer was available within this cold-independent,
single-fixture assignment. This remains a self-review limitation; the required
later reviews will be separate in time and evidence, but are not represented as
an independent external assessment.

## Check evidence

See the second-cycle section appended to `checks.md`. No product behavior,
remote API, deployment, or browser behavior was exercised.
