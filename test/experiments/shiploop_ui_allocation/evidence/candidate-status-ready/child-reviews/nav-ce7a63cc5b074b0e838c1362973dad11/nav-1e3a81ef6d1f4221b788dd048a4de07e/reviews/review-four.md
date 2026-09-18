# Improve review four - W1 step-plan

## Candidate and history

Reviewed the current W1 plan and permitted source/evidence locators after the
third material correction. The required
`git --no-optional-locks -c diff.autoRefreshIndex=false log -7 --format='%H%n%s%n%b%n---'`
history read again exited 128 because this controlled fixture has no Git
repository. No repository was initialized.

## Fresh independent finding and correction

A fresh independent read-only review found an internal contradiction in the
prior blocker wording. It allowed a documented selector-to-host bridge while
the conditional implementation required a verified opaque epoch and explicitly
forbade using the selector as an export scope key. The selector alternative
would leave no response-context token or in-flight invalidation rule.

Corrected only the W1 planning evidence. The sole prerequisite is now an opaque
authorization epoch on every complete snapshot plus a documented host transition
signal that invalidates the preceding epoch before old responses can render.
The local selector is explicitly never that signal. TC-W1-00 requires the
two-epoch host fixture, TC-W1-03 requires a stale old request after that host
transition, and harness lifecycle records the required transition signal. This
preserves the actual external blocker; it does not invent a bridge, change the
fixture schema, or implement an observer.

The current candidate SHA-256 is
`be5f548833b6b62bf69ca954837093d8dbb8024cde11332bf71569e97fbeac61`.
Product `app.js`, `index.html`, and `styles.css` remain unchanged at
`729f0db397fe3b0eaae3fadff9de10facd82b071fb7bbe00a95dcb9d9b5f8ac2`,
`f52423358a46b6210774533586602fb75267deb631129ba9bf96293e68f88213`, and
`cd3106112e5ddff749af99d9e3de730274f7786ccde2a2c4e75c172753b646bf`.

## Checks and assessment

Current outputs are retained in [checks.md](checks.md). `node --check app.js`
passed. `node --test` exited 0 with zero discovered tests, which remains a
coverage gap rather than feature evidence. The probe reports only controlled
fixture facts. No browser, live deployment, or consumer behavior was claimed.

Classification: **non-trivial**. The correction removes an unsafe alternative
from the planned authorization contract, so it resets Improve's trivial streak.
The W1 plan remains truthfully blocked pending the host/API owner's actual
epoch-and-transition contract. Two later distinct full reviews must find no
material plan defect before the Improve runtime may complete.
