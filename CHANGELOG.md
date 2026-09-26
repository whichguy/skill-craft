# Changelog

Written by scripts/release.py.

## 2026-09-25

### shiploop 0.30.1

- The generated plugin hook commands are no longer wrapped in quotes. Grok runs
  the ShipLoop plugin's hooks once its leader restarts, but it does not strip
  quotes: it read `"…/shiploop-keepalive-observe"` as a file name inside the
  plugin's hooks folder and failed every hook with "command not found". Commands
  are now `${CLAUDE_PLUGIN_ROOT}/skills/shiploop/scripts/<script>` (and the Codex
  and Cursor equivalents).

### shiploop 0.30.0

- Every stage now gets the run's global picture. Each save writes
  `context-index.md`, a derived index of the request, every accepted planning
  result with its summary, notes and Improve lessons, the plan's assumptions, each
  work item's accepted results, the outer loop and superseded results. Every packet
  names it right after the callback line, and active packets add a script-owned
  "Read first" list of the accepted results that stage builds on (for example,
  `verify` reads the spec, test strategy and the item's step-plan and test-spec).
  `pause` now refuses context-housekeeping reasons (a clear, context boundary,
  compaction or fresh conversation), and the keepalive log records why a run paused.
- Tests now run on a script-enforced loop. `step-plan` must record the work
  item's test commands in its result (`test_commands`, each `focused` or
  `regression`; an empty list needs `test_commands_na` with the reason).
  `test-green` loops on the focused commands and `regression` on all of them, on
  the Until Loop bound to the selected Improve card: ShipLoop writes the loop
  contract with the exact commands, and each iteration runs every command, fixes
  the code (never a check) and reruns the whole list, for at most 4 iterations.
  Both stages accept only `done` or `blocked`. `done` needs the loop's terminal
  packet, checked against the contract, and then ShipLoop runs every command
  itself from the repository (10 minutes each, 30 per stage) and refuses unless
  each exits 0, printing the failures. The prompt-only pass-or-stop loop now
  covers `implement`, `test-refine` and `integration-verify`.

  The packet-size caps in the test suite are removed; complete prompts take
  priority over packet length.
- Tests stay green after every stage that can edit code. On done at
  `test-refine`, `static-checks` and `integration-verify`, ShipLoop reruns every
  test command the step plan recorded and refuses unless each exits 0; the packet
  lists the commands. Each action allows 3 refused test runs (at these stages and
  the test loops); after that only `blocked` is accepted, so a restarted loop can
  no longer retry forever. The lint gate now also runs on done at `test-green`
  and `regression`, before the test run, since the test loops edit code too;
  `lint_waivers` are accepted there as at `implement`.

### shiploop 0.29.0

- Lint now runs right after implementation and gates it. When `implement` is
  submitted as done, ShipLoop lints every file the work item changed and applies
  safe fixes on changed lines. It refuses the submission once after an auto-fix,
  so the step reruns its checks. It also refuses while a new finding on a line
  the item changed remains, unless the result lists it in the new `lint_waivers`
  field (`[{"id", "reason"}]`) with the ID the refusal prints. Findings from
  before the item, missing tools, tool errors and timeouts never block, and
  `lint: off` turns the gate off. The implement packet prints the `lint` command
  to run after each step.

  Linters are now discovered per changed file type. Besides ruff and shellcheck,
  ShipLoop runs the linters a repository configures (eslint, prettier, tsc, mypy,
  black, markdownlint-cli2, yamllint, gofmt), actionlint whenever it is on PATH,
  and `npm run lint` or `make lint` for changed files no other linter covers.
  Repository-configured linters run repository code by design; pre-commit is
  still never run, and nothing is ever installed. The lint time limit rises from
  20 to 120 seconds (60 per tool). `shiploop lint --show --gate N` reads a gate
  record.

  `test-green`, `test-refine`, `regression` and `integration-verify` now carry the
  same pass-or-stop loop as `implement`: fix the code and rerun until every check
  passes, and stop only as `blocked` when a check is proven unachievable or still
  fails after 3 genuine fix attempts. A red check never leaves these stages as
  done. The navigator guide gains a whole-run map of the prelude, inner and outer
  loops.
- The stages that turn the accepted plan into work now receive it. `step-plan`,
  `test-spec`, `system-test-author` and `release-plan` packets name the accepted
  `spec` and `plan` results under "Current planning sources", beside the test
  strategy source. Before, they carried only the previous stage's result and the
  test strategy, so the requirements and the plan reached step creation only if
  the model searched `state.md` for them. The step-plan and test-spec duties point
  at those sources.
  `system-test-author` and `release-plan` are now also told to register every
  planning file they produce in `evidence_refs`, like the other planning stages.

### shiploop 0.28.0

- Keepalive now works on Grok without an installer. Grok lists a plugin's hooks but
  never runs them, so the marketplace install left Grok runs with no keepalive. Any
  `shiploop` command that runs under Grok now writes
  `~/.grok/hooks/shiploop-keepalive.json` when it is missing, or repairs it when its
  script is gone, and says so once on stderr. New Grok sessions load it; an open
  session picks it up from `/hooks`, then `r`. `SHIPLOOP_KEEPALIVE=off` skips it.
- Planning now decides where new code and its data live, in every execution
  environment the change runs in or reaches: the local checkout, a remote runtime
  behind an MCP server, API or CLI, a hosted platform, and each service of a
  multi-service system. The `plan` stage maps each environment's library
  structure, how it resolves names, the libraries and services the code shares
  names with, and how it stores data (existing and destination schema with their
  owner, or a new schema with its storage policy), and records a Namespace and
  data map. `step-plan` names each new file, module, public symbol and stored
  field with its environment, home, visibility and collision or round-trip
  check. Code craft gains rule 8, "Put it where it belongs", which the quality
  loop reviews. New stack-neutral Namespaces and placement and Schema and storage
  practice cards; the platform cards give Apps Script, Python, Bash, Salesforce
  and UI examples.

  UI work now defaults to an ambitious, highly interactive interface: plans name
  the rich interactions they deliver and any they scale back with a reason, and
  KISS/YAGNI no longer justify trimming the planned UI.
- A run no longer stops at the start of each work item. The `select-work` packet
  used to ask for a context clear and, since no host lets a packet, script or hook
  clear the conversation, offered a "context-boundary" pause that left the user
  to type `/clear` and two recovery commands before every item. Every inline
  stage now continues in the same conversation and the host's own compaction
  manages context; an ask-agent producer without a usable fresh worker runs in
  the conversation too. No packet offers a pause for a clear, and serial chains
  no longer have a manual-handoff route.

### shiploop 0.27.0

- The plan result now carries an `assumptions` list, and the navigator enforces
  it. A done plan submitted through `complete` or `improve-complete` is refused
  unless every load-bearing assumption is listed as evidenced, probed or open.
  Every local evidence path must exist, a probed entry must cite a nonempty saved
  output file, and each open entry must name a work item in the plan's queue. The
  Plan Improve loop exits only when no open entry could be settled by a bounded
  probe now. Research lists its assumptions in its decision note as the plan's
  starting point, without a gate. The model still decides whether to experiment;
  the gate makes a decision not to probe visible.
- The status hook recognizes Grok's real PostToolUse payload (camelCase keys with snake_case aliases, output as a list of byte values), and the status-display guide records how to make Grok use the trusted plugin install.
- Keepalive: host hooks stop an agent from ending its turn while a run can still move, for Claude Code, Codex, Grok, Cursor and OpenCode. A marketplace install brings them (declared in `host-hooks.json`, generated per host); a skill-directory install adds them with `scripts/shiploop-hook install --host HOST`. See `references/keepalive.md`.
  Only one session per run is kept alive; parallel workers and second terminals on the same run are let go, and ownership passes on when the owner's turn ends.
  New `shiploop hook-status` (read-only JSON run status) and a `Keepalive marker:` line in every packet.
  New `scripts/shiploop-drive` runs or resumes host sessions until a run is done, paused, blocked or stuck; use it for unattended Cursor and OpenCode runs.
  A question about the loop no longer pauses the run, and the agent is told not to pause on its own to ask whether to continue; only an explicit stop or pause, or a real blocker, does.
- The status block shortens any absolute path in a title, summary or reason to its last segment, so it never repeats full file paths from host text.

### shiploop-e2e-audit 0.4.5

- Recognize ShipLoop's new read-only `hook-status` verb in the Grok adapter's direct-subcommand allowlist.

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
