# Changelog

Written by scripts/release.py.

## 2026-09-25

### shiploop 0.26.0

- Code craft gains rule 7, *Write text that can be translated*: user-facing
  messages go through the repository's message catalog when one exists, and
  otherwise stay whole sentences with named placeholders so they can be
  externalized later. Numbers, dates, currency and plurals use locale-aware
  APIs, and logs, error codes and identifiers stay untranslated. The quality
  loop reviews for concatenated or catalog-bypassing text, and a new
  Localization practice card in the coding decision guide covers catalogs,
  plurals, explicit locales, UI expansion and right-to-left layout, and tests.
- `static-checks` now runs a quality loop on the Until Loop bound to the selected
  Improve card. ShipLoop writes the loop contract. Each iteration traces every
  changed public entry point with a valid, a boundary and an invalid input, then
  reviews the change against the new *Code craft* rubric: argument checks,
  contract docstrings, and comments that are useful rather than token-wasting.
  The loop ends after an iteration with only trivial findings, and a third
  iteration that still finds a material issue stops it. The stage accepts `done`
  only with a terminal packet that matches the contract; `repeat` is no longer
  accepted there.
  - The *Code craft* rubric replaces the implementation constitution. Step plans
    gain an argument-check/docstring criterion, test specs gain rejection cases,
    `verify` checks the loop's entry-point inventory, and the end-of-work Improve
    reviews against the same rubric.
  - The change inventory (tracked and untracked files since the item base) is
    recorded in every lint mode; `lint: off` still stops linters and auto-fix.
  - Fixed: the lint snapshot failed when the run directory sat inside the
    checkout and was git-ignored.
- A product fix committed after the workspace return no longer strands the run.
  Run `workspace plan-return` and `workspace return` again: the follow-up starts
  from the source state the previous receipt recorded and uses the same route
  (working-tree update or another fast-forward). The new receipt keeps the old
  one as `previous_receipt`. A source that already holds exactly the follow-up
  result (a fix copied in by hand) is recorded without writing; any other source
  change made since that receipt still blocks.
- Installing the ShipLoop plugin from the marketplace now sets up the status hook: the package carries generated hook files for Claude Code, Codex, Grok and Cursor. Claude Code and Codex show the status block to you after each ShipLoop call (Codex asks you to trust the hook once in `/hooks`). Grok and Cursor run the hook but cannot display it, so the in-packet block stays the display there. The hook now recognizes each host's payload shape.
- Every packet now carries a script-rendered status block: where the run is (phase, work item and stage group), what was just accepted, what comes next, the item's plan sentence and the completed items. The host shows it unchanged instead of writing its own progress summary. Each saved transition also writes `status.md` in the run directory, and the new `shiploop status` verb prints the block. On Claude Code, the optional `scripts/shiploop-status-hook` PostToolUse hook shows the block to you directly from ShipLoop's own output; see `references/status-display.md` for the settings snippet.

### shiploop-e2e-audit 0.4.4

- The Grok adapter recognizes ShipLoop's new read-only `status` verb as a direct ShipLoop subcommand.

### skill-interop 0.2.5

- The marketplace-hosts reference records plugin-bundled hook support for Claude, Grok and Codex.

### backchain 0.6.0

- Plan Dispatcher leaves the `backchain` plugin and ships as its own `plan-dispatcher` plugin; `backchain:plan-dispatcher` no longer exists, so install `plan-dispatcher` instead. Backchain's source now lives in Skill Craft, and `./install.sh --skill backchain` installs it from a Skill Craft checkout. The card now says that the harness, schema, fixtures and samples it mentions live in the separate Backchain development checkout and are not shipped with the skill.

### plan-dispatcher 0.3.0

- First release as its own `plan-dispatcher` plugin (previously `backchain:plan-dispatcher`). Its source now lives in Skill Craft, and `./install.sh --skill plan-dispatcher` installs it from a Skill Craft checkout.

### backchain 0.5.1

- Vendored from upstream a6eeda0056af

### shiploop 0.25.1

- A saved run whose Improve child sits at a stage that never starts one (anything other than a planning stage or the final carry-forward), or whose Improve result belongs to such a step, is now refused on load with a message naming that stage. `workspace return` relies on this check instead of its own active-child guard.

## 2026-09-24

### backchain 0.5.0

- Vendored from upstream 0f09091a9c3b

### shiploop 0.25.0

- Each step's exit criteria now carry their confirmation. Step-plan duties write every completion criterion as `<condition>. Confirm by: <command, observation, or inspection>; pass when <expected result>`. This includes whether inspection is sufficient, and an explicit `unconfirmable here` marker instead of dropping the criterion.

  The implement duty and chain worker packets loop until each criterion is confirmed. They never download a tool to confirm a criterion. They stop BLOCKED only for a criterion that is proven unachievable, and FAILED after 3 genuine attempts. Workers write an `exit-criteria.json` receipt, verify checks each item, and a retried step carries its prior attempts and their rejection reasons.

  New script-owned lint, set by the `lint: fix|report|off` run option (`--lint` on `init` and `workspace start`, `lint-mode --set` mid-run; new runs default to `fix`). It runs on entry to static-checks and verify. The model receives each linter's exact command and complete output, an applied auto-fix diff, per-file coverage and install recommendations. Deletion-type and unsafe fixes, version-manager shims, repo-local binaries and linters that execute repo code are never applied or run. Lint output is supporting output, never exit-criteria evidence.

### shiploop-e2e-audit 0.4.3

- The Grok trace adapter recognizes ShipLoop's new `lint` and `lint-mode` direct subcommands. The host trace fixtures are re-pinned to the updated adapter.

### improve 0.3.0-rc.5

- Improve vendors Until Loop 0.5.1, whose packets now ask for clear, evidence-grounded status updates without changing control flow.

### review-coverage 0.3.1

- The host matrix installs from whichguy/skill-craft, explains moving an old Claude registration without uninstalling plugins, and replaces the plugin sync step with a change note.

### shiploop 0.24.2

- The README and navigator reference say a ShipLoop source edit adds a changes/shiploop note and checks a fresh package build; plugins/ and catalogs are release output that ordinary work items never regenerate or commit.

### shiploop-e2e-audit 0.4.2

- The freshness gate reads the released plugins/<leaf> and its entry in skill-craft's own marketplace catalog on the same main, instead of the retired skill-craft-market repository; a pending change note stops the gate until release.

### skill-interop 0.2.4

- Skill Interop now names skill-craft itself as the marketplace, with release-output catalogs and commit-pinned external plugins, and its checklist asks for a change note instead of a plugin view sync.
