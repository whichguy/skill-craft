# Improve review six — W1 step plan

## Candidate and history

Reviewed the current W1 plan and its permitted source/evidence locators, with
particular attention to whether a blocked host contract was being treated as if
it already supplied safe client inputs. The required
`git --no-optional-locks -c diff.autoRefreshIndex=false log -7 --format='%H%n%s%n%b%n---'`
read exited 128 because this fixture is non-Git. No repository was initialized.

## Fresh independent finding and scoped correction

A fresh independent read-only review found three material contract gaps in the
conditional plan: the fixture's integer revision has no JavaScript-safe ordering
rule, `id` is not guaranteed unique per snapshot, and labels/jobs have no stated
bounds even though the proposed UI is fixed-size. Those are supplier-readiness
gaps, not authority for this W1 run to choose a host protocol, numeric limits,
or product implementation.

Corrected only the allowed W1 plan. It now makes the host/API owner supply a
complete response contract with a JavaScript-representable monotonic revision
rule, documented job/field limits, and per-snapshot unique opaque IDs, alongside
the already-required bootstrap/replacement authorization bridge. The future
plan can validate that supplied contract before ordering or rendering and use
text-only bounded presentation; it does not invent the missing values. The
conditional test matrix records the resulting boundary/schema checks only after
the owner supplies that contract and its controlled fixture.

The current fixture remains insufficient for W1 test bootstrap or implementation,
so W1 stays blocked on the host/API owner rather than weakening account
attribution or claiming feature proof. The current plan SHA-256 is
`5fba7c86b1c9be2fdb04ec2020dd370d7e23f6981a53db33a6d88d034ef5df55`.
Product `app.js`, `index.html`, and `styles.css` remain unchanged at
`729f0db397fe3b0eaae3fadff9de10facd82b071fb7bbe00a95dcb9d9b5f8ac2`,
`f52423358a46b6210774533586602fb75267deb631129ba9bf96293e68f88213`, and
`cd3106112e5ddff749af99d9e3de730274f7786ccde2a2c4e75c172753b646bf`.

## Checks and assessment

Current command results are retained in [checks.md](checks.md). `node --check
app.js` passed. `node --test` exited 0 with zero discovered tests, so it remains
a baseline coverage gap rather than W1 feature evidence. The environment probe
records controlled fixture facts only. No implementation, dependency, Git,
remote, deployment, browser, or consumer claim is made.

Classification: **non-trivial**. The plan correction is material and resets the
Improve trivial-review count. Two subsequent distinct full reviews must find no
material planning defect before the bound runtime can complete; the final W1
disposition remains blocked until the host/API owner supplies the documented
authorization and complete response contracts.
