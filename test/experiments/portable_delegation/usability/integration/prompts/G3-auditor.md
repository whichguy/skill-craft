Assignment reminder: audit shared dirty Git state and write a report outside it. Do not
integrate or mutate the shared checkout.

Shared checkout: `<SHARED_CHECKOUT>`
Report path outside this checkout: `<REPORT_PATH>`

Use read-only Git inspection such as `git status --short`, `git diff --cached`,
`git diff`, `git log` and `git rev-parse`. Report the staged, unstaged, untracked
sentinels and separately identify any owned-change.md edit. Do not pull, merge, rebase,
checkout, reset, restore, clean, switch, commit, stash, push, fetch that updates refs,
or alter files.

The final receipt briefly includes assignment reminder, audit contribution, observed
HEAD/sync state, no-integration/conflict state, commands/outcomes, report reference,
recommended next parent action and unresolved decisions. Do not assert preservation
without observed evidence.
