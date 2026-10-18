# Changelog

Written by scripts/release.py.

## 2026-10-18

### skill-craft 2.6.0

- Skills: backchain 0.6.6, improve 0.5.0, shiploop 1.6.0, shiploop-e2e-audit 0.7.4, shiploop-run-review 0.2.3

### backchain 0.6.6

- No change to Backchain's behaviour or text: the convergence reference was edited and then restored to its released wording on the integration branch, so this version ships it as the previous one did.

### improve 0.5.0

- The Improve card is a router. A ShipLoop review (the argument `ShipLoop Improve: <handoff path>`) reads the card's ShipLoop subcall, now told to read the handoff with a file-reading tool and not `cat`, and the new `references/shiploop-route.md`, which carries what a ShipLoop child needs from the card, the review policy, the callback evidence and the bundled Until Loop card once each, including that a ShipLoop pass ends with `improve-pass`, which writes the runtime report from the pass's review file, plus the ownership, recovery, stopped-child, commit-message, `final_result` and review-input text that used to repeat in every handoff. A direct `/improve` or an `improve-agent` worker reads the new `references/standalone-route.md`, which holds the five standalone sections (binding, continuation after context loss, completion summary, preview, execution handoff) unchanged. `SKILL.md` goes from 28.4 KB to 10.3 KB; `test/improve_route_ledger.json` has a row for every paragraph of the four sources, and `test/improve-route.test.py` fails when a paragraph has none.

### shiploop 1.6.0

- A check only a person can make is asked so it can be answered, and a partial answer no longer stops the run; a review
  interrupted by a context reset no longer redoes a pass it already recorded.
  - release-verify asks once, as a fill-in list: step 1 says how to reach the consumer entry and what to answer when it is
    missing or hidden, and the report is one yes/no line per case with what to look for. The run's exclusions bind the run,
    not the person. A reply that answers only some cases resumes the stage: the unanswered ones are recorded not-run, as
    open items for handoff quoting the reply, and the stage completes. It asks again only when the reply answers none, or
    when the run's delivery contract still has a required behavior obligation with no passed observation (then only for
    its unanswered lines).
  - The resumed packet prints the person's reply and what it settles in the printed text, not only in the packet file.
  - prepare names the consumer's account or role, entry route and access prerequisites and checks them read-only (the
    platform guide's probe where it has one); release-check reruns the same probe before the release. An unresolved
    prerequisite stays open in `environment.md` with who can grant it; ShipLoop's guidance creates no grant. The Salesforce
    card gains the probe: the user's profile and permission sets, and tab, app and class visibility for them.
  - The Improve packet the recovery command reprints says which review passes improve-pass has already recorded (and a
    review file written but not recorded), tells the model not to redo a recorded pass, and names one next command:
    improve-pass, which prints a recorded pass's runtime done again when that has not run, and otherwise names the next
    step (the next pass's review file, or the stage's complete once the loop has ended).
- Two fixes that the merge of the packet and loop changes needed.
  - The docs no longer say a packet's callback is "the line after the header": the owner rule and the pointer to the run's
    `context-index.md` sit between them, and the Until Loop and pointer changes move more lines above it. The commands
    `shiploop-next` and `shiploop-complete`, the README and `references/navigator.md` name the callback by its label,
    `Callback for this stage` (an Improve child's packet labels it `Next command (` or `2. When the improve skill has
    completed, run:`).
  - The run's `context-index.md` map lists `skill-calls.jsonl`, the record of the Skill-tool calls a Claude Code session made
    in the run (the Improve stage's gate reads it). Before, the map was missing a file every Claude run has.
- The document, verify and carry-forward packets give the model the inputs their duties name, and carry-forward is shorter for
  the common one-item run.
  - Document prints `Changed since the item base (script-derived): <paths>` (or `not computed: <reason>`), and its duty 1
    lists behaviours from those paths; it named a change inventory that exists only at verify.
  - Verify's duty 1 runs the Callback command with `--check-only` after the last edit, which reruns every recorded command into
    `RUN/tests/<action>-check-only.md`, in place of rerunning each command by hand and copying exit codes into notes; duty 11
    no longer asks for exit codes. The ask-agent route keeps item 8 (assembly).
  - A run of one work item with one step and no pending item (proved from state) gets a short carry-forward: duty 2 says no
    item follows and how to add a corrective one, duty 3 records `none` or `reuse` unless an R-<n> says the procedure will
    recur, the queue rule prints only its path line and the Until Loop Work drops the trial clause (about 4.3 KB less in the
    printed head). Every other run keeps the text byte for byte.
  - Carry-forward names the commands that passed at the item's verify and `environment.md` does not name under `## Commands`,
    and an accepted carry-forward prints one counted `ShipLoop knowledge notice:` line for them; it never refuses.
  - The item commit raises when the item's changes cannot be read (no base snapshot) instead of reporting nothing to commit,
    and the `<item> verify item commit` reference is printed only when the worktree log holds a `feat: <item> ` commit.
- The ShipLoop skill card opens with a recovery block and is split into purpose files, so a model that lost its context
  reads about 30 KB instead of 83 KB before it acts.
  - Directly after the title, the card says what to do after a reset, summary or compaction: run
    `python3 <this skill>/scripts/shiploop next --run-dir <the run directory named in your summary or handoff>`, follow the
    packet it prints, and if no run directory is known, list `<repo-parent>/.shiploop-runs/*/run/state.md`, use the only
    active run for this repository, and record an open item instead of guessing when there are several. It asks the model
    to keep that command in any summary it writes.
  - The card (83,199 bytes before, 29,771 now) keeps binding, starting and recovering a run, ownership, the durable
    handoff, following the current packet and the authority limits. Every other section moved, text unchanged, into ten
    files of at most 8 KB under `references/`, each opened behind a one-line trigger in the card's new "Read when" list:
    `run-start.md`, `run-options.md`, `backchain-route.md`, `guide-map.md`, `improve-stages.md`, `improve-child.md`,
    `inner-loop.md`, `test-loop.md`, `chain-route.md` and `chain-navigation.md`. Links from the other references and the
    README now point to the section's new file.
- Sentences that told a cleared model something false or incomplete are corrected, each against the behaviour it describes.
  - The run reference file's rules section lists the planning results that start an Improve child for the run's own
    `planning_review` option (a `none` run lists two, not the seven of a `stage` run).
  - On the ask-agent route, where one implement action builds every step of a plan of several steps, the Goal, the loop's
    exit conditions and the Improve review focus name those steps ("S1 to S2") and their paths instead of "this step"; a
    one-step plan and every inline run keep the per-step wording. The loop's Work line no longer ends "in order,.".
  - A loop's Work cites the duty items the packet prints, counted from the duty text (step-plan 1-12, test-spec 1-7,
    validate-existing 1-4, implement 1-7, test 1-8, document 1-7, carry-forward 1-4; verify 1-9, where its duty says items
    1-7 repeat and items 8-9 are done once). The step-plan, test-spec and test Work say to run the Callback command with
    `--check-only` added (no packet printed a command of its own); the test Work says what that runs, and its Repeat adds
    "a check-only refusal". Verify's assembly item (8) prints on the ask-agent route only.
  - The Checked-by line says `complete --check-only` prints the first refusal without accepting and is repeated until it
    accepts (a gate raises at the first fault, so it never printed every refusal).
  - Removed or corrected: "HOME/spec.md (quoted below)" at spec (the spec stage quotes no file; it now says to read it
    whole), the spec goal's "FEATURE/spec.md", the lint gate sentence "only the item's last step is gated" (every
    implement step is), "a list too large for the loop contract is refused" (no gate refuses a size), and the test-only
    step refusal's "test-author" (no such stage; it now names the test-spec).
  - A validate-existing stage ShipLoop records itself (every expectation matched) has the summary "ShipLoop ran every
    expectation check on the unchanged checkout and each matched its state." in place of the 143-character sentence the
    status line cut mid-word; the check record stays in `evidence_refs`.
  - `SKILL.md` limits "launches no model process" to the skill and its navigator commands and names the optional outer
    driver `scripts/shiploop-drive`.
- A packet's printed head now holds what its stage guidance cites, and every stage a revise sends an item back through says
  it is a revisit (packet review 2026-10-17, F3 and F5). Before, the head cited guides by label without a path, ran "the
  packet's plan-return" and "the printed `backchain-check`" from file-only lines, and a redone test spec searched the run
  for its own earlier result and resubmitted it unchanged.
  - Guides: each guide and policy the stage text names prints as `<label>: GUIDES/<file>#<section>` in the References block,
    after the symbols (a lookup block; a guide whose path the duty already prints is not repeated). The file keeps the
    stage's other guides where they were.
  - Backchain: the planning guide, the resources or the audit resource, the loop-resource status (only where the text cites
    its "Loop resources" line) and the graph check print with the paragraph or line that cites them, ahead of the list of
    results the stage builds on.
  - Release stages: the return route, the plan-return, review-return and return commands print in the head of
    release-plan, release-check, release and handoff; the delivery contract's lines (necessity, authority, obligations)
    print in the head of the stages whose done the release gate refuses on them (release-plan through handoff).
  - Implement (inline): the step's own criteria print by value under the Step line; the quoted hand-off names them by ID,
    so the text prints once. The Improve hand-off still quotes them whole.
  - Revisits: after a revise, the first head of step-plan, test-spec and implement prints four lines: why it is back (the
    revise result's summary and path), its previous accepted result (or none), the IDs the redone step plan and test spec
    added, removed or changed, and "Keep unchanged rows with their IDs". The Done-when "carried over" line names the
    stage's own previous result.
  - Room: the pass, floor and ratchet rules are one shorter line each (every clause kept), and document and verify name
    the step-plan path list once ("every step-plan path, plus ...") instead of repeating it.
- ShipLoop's Improve children follow Improve's own stop rule again, the one the bundled Until Loop runtime (upstream 0.10.0, vendored unchanged) applies: a review ends after two consecutive trivial passes, or after a first pass that is trivial and leaves the workspace unchanged. The one-unchanged-pass rule and its stricter gate for code reviews, which earlier notes on this line announced, do not ship.
  - Every Improve child starts at `required_trivial_reviews: 2` with the two-pass exit and repeat conditions, whatever stage it reviews; its contract lists no `candidate_paths`.
  - The import takes the last two review files, or the one review of an unchanged first pass, and reads the runtime's `trivial_streak` and `unchanged_first_pass`; the change gate and the restart route key on an unchanged first pass.
  - The Improve handoff's pass and evidence lines, and the README and Improve-stage reference, say the same.
- The Improve handoff opens with what a child that lost its context needs: the read-with-a-file-tool sentence, `CHILD` (the child's directory), `ROUTE` (the Improve skill's ShipLoop route file), the one command to finish, and when to open the route; the review focus follows within the first 4,500 characters with the commit and complete commands, and the `improve-pass` command that ends each review pass follows the commit command under Commit. `CHILD` is defined once, on that top line (no longer in the References block). The text that was the same in every handoff (ownership, recovery, the stopped-child route, exclusions, the `final_result` rules and the fixed review inputs) moved to the route file, so the implement handoff drops from 33 KB to 18 KB and the planning handoffs from 27 to 12 KB. A child directory is `<stage>-<last 8 characters of the reviewed action>` (`implement-5e2f1a9b`) directly under `.shiploop-improve/`, not two 36-character IDs. An Improve child that started under the earlier layout is restarted with `improve-start --restart-stopped`.
- New `improve-pass` verb: after each Improve review pass the model writes `review-<n>.md` and runs it; ShipLoop checks
  the recorded improve-skill call before any runtime `done` exists, commits the pass's edits, writes `checks.md` for an
  unchanged tree (and refuses one older than the last edit), composes the runtime report and prints the runtime's `done`
  and the stage's `complete`, literal and absolute. `complete` writes `RUN/improve/<action>/passes.md` at import, and its
  skill-call refusal of an ended loop names `improve-start --restart-stopped`, which now restarts such a loop. The
  implement-step review focus gains a bullet for an unexercised language or library behaviour.
- Packets name the knowledge files and the request by their files instead of quoting them whole (packet review 2026-10-17,
  owner decisions D1 and D2; units U1 and U2).
  - A packet lists each knowledge file it reads (`HOME/spec.md`, `environment.md`, `architecture.md`) by path, size and table
    of contents: every heading, with the R-<n> or AD-<n> entries under it (a run of list entries as `R-1..R-6`). It quotes by
    value only the requirement and decision entries the stage follows. On the recorded Salesforce run the whole quotes were
    53% of all packet text and sat where no print reached; the model reopened the files every time.
  - The spec and architecture diff since the run began names a file that is new since the baseline (its diff is the whole
    file) with its size and contents instead of printing it, at every stage that reads the diff (release-verify printed
    35 KB of it on a first run). A file that existed at the baseline keeps its changed sections, uncut.
  - The original request is quoted whole only at intake, spec and plan (and in the Improve handoff of spec and plan). Every
    other packet prints one line naming `RUN/request.md`, which holds it verbatim with its sentence index; the Improve
    handoff adds the delivery contract's exclusions line beside it when the run has one (a producer packet already prints
    it in its delivery block).
  - The Improve handoff names the reviewed stage's packet (`RUN/packets/<action>.md`) and result (`RUN/inbox/<action>.md`)
    and the knowledge files with their sizes instead of quoting the producer's knowledge files and hand-offs again; it keeps
    by value the criteria the stage was handed, and on a revisited step plan it names the previous accepted result and the
    revise result. A long-home handoff falls from 42-60 KB to about 20 KB.
- The Until Loop block of every inner-stage packet has one start route on every host, and it leads with the command. This
  replaces the Claude Code route that the earlier loop-block note describes (the Skill tool, skill `until-loop`): the recorded
  Claude run called it, got `Unknown skill: until-loop`, searched `ADAPTER.md`, and wrote the stage's result before the loop
  had run; no skill-craft install registers a skill of that name.
  - The block now reads: heading `Until Loop (no iteration limit; the loop script counts the iterations):`; the RUN line (`RUN
    the Until Loop now, once, before any work, and do this stage's work only inside it`, with the foreground command rule and
    the active-receipt clause: if the receipt already exists and is active, run its `next_argv` instead, because a second start
    resets the loop); the literal start command, `python3 <runtime script> start --receipt <receipt> < <contract>`; the follow
    line (follow each packet it prints, run its `done_argv` as printed, until the receipt says complete or stopped; the argument
    is already in the Contract file, do not edit that file or the receipt); the argument between the two marker lines; the
    result line; and the exit-evidence sentence.
  - The result line lists the five fields of the runtime's done report with their values (classification, exit_assessment,
    continuation_assessment, evidence, handoff), so the report is written once and not looked up in the runtime's output.
  - A packet read after the loop started prints the resume line (`do not start it again (a second start resets it)`, then run
    the receipt's `next_argv`) in place of the RUN line and the start command, and its result line names `next_argv` alone: a
    literal start command under a read-again packet invited a second start (measured: it sent `action_number` 2 back to 1).
  - The per-host line is gone (`shiploop_loops.HOST_LINE`). The three places outside the block that said `/until-loop` (the
    inner stage's done-when line, the test stage's where-and-floors line, the SKILL.md and README descriptions) say "the Until
    Loop argument"; SKILL.md "Stage Until Loops" no longer names a tool.
  - The loop contract JSON, its hash and the Improve start contract are unchanged (checked for all eight stages).
  - Each looped stage's printed head and whole text are 246 characters longer (245 for test); the journaled head table
    (`test/shiploop_e2e/head_table.json`) is raised by the same amounts.
- The Until Loop block of every inner-stage packet now says what to run, with what, and what the result is, so a model that
  lost all context acts on it without opening the Until Loop card. Before, it said `INVOKE /until-loop NOW with the argument
  below`, indented the argument's lines among prose, and sent every host but Claude to the 24 KB `ADAPTER.md` for the
  command (the last live Grok run read that card 6 times and the Improve skill 7 times to learn it).
  - `RUN the until-loop skill now, once, with exactly the lines between the two markers`: the argument sits between
    `----- BEGIN until-loop ARGUMENT -----` and `----- END until-loop ARGUMENT -----` and holds the Work, Exit when, Repeat,
    Contract and Receipt lines and nothing else (no indent, no prose between them).
  - Claude Code: the Skill tool, skill `until-loop`, with that argument. Any other host: the literal start command, on its own
    line, `python3 <runtime script> start --receipt <receipt> < <contract>` with the real absolute paths (the command a failed
    `complete` already prints), then each packet it prints until the receipt says complete or stopped.
  - The result: when the Receipt says status complete (stopped: report it), keep it in `evidence_refs` and run the Callback
    command; if that refuses because of the loop, run the start command again (an active receipt: its `next_argv` instead).
  - A packet read after the loop started leads with the resume line (do not invoke it again) instead of the RUN line: the
    runtime does not refuse a second start for one receipt, so a literal start command must not sit under a RUN line then.
  - The closing rule keeps its obligations and adds that the receipt is not to be edited; the old "start the loop again"
    sentence became the result line. The heading is `Until Loop (no iteration limit):`.
  - To keep the step-plan head under the host's 20,000-character cut, the head's pointer sentence is shorter (same
    obligations) and `packets.py --offline` writes the loop contract before it renders, as `emit` does, so an offline
    packet no longer ends with "The loop contract is missing".
- A packet's printed head, its whole print and its packet file are now built from one ordered list of blocks, so a model that
  sees only the first part of a print has what it must act on, on every host and at every run-directory length.
  - Order: the stage line, the callback, the goal and done-when, the Until Loop block, the keepalive marker and status, the
    duties and rules, the stage's own input, the result template with its outcomes and fill rule, the pointer lines; then
    what the file repeats whole, cut first: the References block, the progress view, the pause command, the quoted knowledge
    files and hand-offs. A head keeps every block up to the template and as many of the rest, in that order, as fit 20,000
    characters (the most Grok gives a model whole; above it Grok drops the middle) at a normal install; the packet file has
    them all. Before, the step-plan head was 20,638 characters inline and 22,320 on the ask-agent route at that install and the
    Until Loop start command sat past character 19,900.
  - The head now carries what the stage works on and the file alone held: the work item with a 400-character excerpt of its
    context; for an inline implement step its task, paths, skills, check commands and lint command; the test stage's count
    rules, floors and base-run rule; the verify rerun list, commit scope and lint mode; the carry-forward queue rule; the
    validate-existing mismatch rows; the lessons of the last Improve review.
  - Every print, whole or head, ends with the line `=== end ShipLoop head ===`: a print without it was cut, by the host or by a
    pipe such as `head -N`. The packet file does not carry it.
  - On the ask-agent route the Backchain route paragraph (step-plan, carry-forward, product-acceptance) prints after the result
    template; a one-line stub stands where it was.
  - Step-plan duty 9 keeps the unconditional record topics and, for an item that adds or moves code or stored data, replays a
    pinned value, or changes interactions, UI or service state, names the new `references/plan-record.md`; the three
    conditional topics moved there word for word.
  - `shiploop_protocol.OUTPUT_LIMIT` (16,000) is the limit of a command's list output; it was the navigator's whole-print limit
    by name, which stays 16,000.
- A packet carries one progress block instead of the status block and the narrative side by side (packet review F6:
  28 of 36 packets of a live run carried both, and they said the same).
  - A milestone packet carries the run narrative only. Every other producer packet carries one status line,
    `Where: … · Next: …`, the status block's Where and Next rows. `status.md` and `shiploop status` keep the full block
    unchanged.
  - An Improve packet carries neither. Before, 8 of 11 Improve packets repeated the narrative of the stage they reviewed:
    the milestone test reads the last accepted step, and an Improve child does not change it until it completes. An
    Improve child's packet is no longer a milestone; a stopped run still is.
  - The Claude Code status hook reads the narrative or the status line from the packet. It shows the narrative at a
    milestone and a two-line summary otherwise (`ShipLoop ▶ <where>` and `Next: …`; `shiploop status` still adds what
    finished). Its shell gate now starts on a packet header or a status block.
  - The last accepted transition in the packet file prints its summary even when it is as short as a headline. That
    summary was left out because the Done row showed it, and the Done row has left the packets.
- ShipLoop runs each recorded test command once per run, and `complete` no longer reruns a passing `--check-only` run.
  - A step plan, system-test-author or release-plan result that records the same command string twice keeps one row: rows
    in one suite fold together, and a regression row that repeats a focused row (its IDs all IDs of the focused one) folds
    into the focused row, which then says `regression: true` and lists as "(also recorded as regression)". The one row
    checks the union of the IDs and criteria and the larger `min_tests`; the system-test drift check still runs it as the
    default suite. A check and a test-runner row, a regression row with IDs of its own, or rows that differ in
    `host_dependent` stay apart. In the packet review's run the step plan's 10 rows became 7 and the command listing
    5,360 characters 4,204.
  - `complete` takes the action's passed `complete --check-only` test run instead of running every recorded command
    again when the command list and the working tree (tracked and untracked files, not ignored ones; the tree the
    check-only run started on or the one it left) are unchanged (owner decision D5). The counted `verify<N>` record says
    `reused` with the check-only record's path, time and tree; the test stage prints a `Gates: candidate: reused ...`
    line, and the check-only output says the next complete takes the run while nothing changes. A reused run is held to
    today's floor, and one the floor would refuse is run again. The test stage's base run and mutation check, and
    release-verify's consumer checks, still run at complete.
- An OpenCode session started from a Claude Code shell is no longer held to the Skill-call record when an Improve stage is completed. It inherits Claude's session variables but has no Skill tool, so the exit the refusal named could never be taken; its own `OPENCODE` marker now wins over the inherited Claude session, as the Codex and Cursor markers already did. A test derives the host list from the hook installer's table and fails when a non-Claude host has no nested marker.
- Every ShipLoop packet, the Improve packets included, now carries two lines directly under its first line: the owner rule
  ("concise and exact; no restating", keep every command, path, ID and expected value) and a pointer to the run's
  `context-index.md` to read first after lost context or any doubt. The mid-packet "Run context index" line is gone; the
  pass-log line keeps its own line.
  - `context-index.md` is now the run's master index. It opens with a map of about 3 KB: the current stage with its packet
    file, the next and recovery commands, and one row per file or folder of the run, per knowledge file and for the skill's
    guides, each saying what it holds and when to read it. The run's record (request, accepted results, work items) follows.
    It stays a derived view that every save rewrites; `emit` writes it when a run lacks it.
  - A model that lost its context used to have no single place to learn what the run's files are: in the last live run it
    never opened the index (0 reads across five compactions) although a mid-packet line named it.
  - Reading pins moved with the lines: the callback is now the third line after the header, not the first, and the packet
    anatomy classifier knows both lines.
- Each gate the 2026-10-17 packet review found unstated is now stated in the packet before it refuses, and its refusal names the way out (packet-review units U6 and U8).
  - Delivery authority: the authority's `target` and `operation` are the contract's. The templates leave them out and ShipLoop fills them in; given, they must still match, and the mismatch refusal says to leave them out. The run was refused twice at intake for an authority that restated them in other words.
  - release-plan, in a run with a delivery contract: while the contract's necessity is unresolved, or required with authority not approved, its Checked-by line names the gate, the template carries the replacement contract that settles it, prefilled from the accepted one (supersedes, correction, a required effect, identity and behavior row for each kind it lacks), and the stage's own `complete` and `--check-only` refuse a result that leaves it unsettled. Before, this was refused only when the Improve review was imported, and the run read the delivery script 7 times to learn the shape. The invalid-necessity and invalid-status refusals list the accepted values.
  - The outer reruns' Checked-by names the list they rerun and its count: release-verify's `reruns the N commands in release-plan's consumer_checks`, or `none recorded, so none runs`, and the same for system-test's system_commands. Before, it said "every recorded test command".
  - Verify duty 1 says to write the result to `RUN/inbox/<action>.md` first, because `--check-only` reads that file. A missing result file is refused with `no result file at <path>` and what to write, instead of "navigator result is unavailable".
  - `complete --notes` takes a file path: its help says so (`--notes FILE`), and text passed as the value is refused, naming the file the handoff names.
  - Removed: the result template's `# ShipLoop navigator result` heading (owner decision D4: nothing parsed it; the template is the fence alone), the pointer line's "or you need the duties or the template" (every head carries both), and the `git -C <checkout>` in the rollback recipes, which are now plain `git` run from the repository root, matching the rule beside them.
  - Reworded: the Improve packet's invocation is host-neutral, with the argument on its own line and each host's route on equal terms (it used to lead with a Claude Code example); system-test's "Deploy not to unblock a test" is now "Add no deploy to unblock a test (a recorded command's own deploy step runs as recorded)"; plan's UI default follows the ambition the request states and stays rich only when the request states none (also step-plan's interaction bullet and the Plan record guide); plan item 13 asks for the module format only where the language has more than one.
- Generic ShipLoop text no longer names a platform; the examples live in the platform cards.
  - The release-plan duties say "granting a role or permission, activating an app or menu entry" and "app or menu entry name and
    URL path" instead of Salesforce's permission set and App Launcher; release-check's dry-run example is "the deploy tool's validate
    or check-only mode"; the release-plan `consumer_entry` refusal and `references/consumer-delivery.md` give a generic tab example.
    `references/platforms/salesforce.md` keeps those examples and gains the `consumer_entry` App Launcher route.
  - The `node --test` reporter example leaves the step-plan duty, `COUNT_RULE` and the base-run refusals for
    `references/platforms/node-express.md`; the packets point at `GUIDES/platforms/`. Jest and pytest stay as generic examples.
  - `shiploop_test_counts.READERS` is the reader table and `RUNNERS` the list generated from it; the refusal for an unreadable
    focused command names the runners from it, and a test holds the reference's runner list to the table.
  - A new lint, `test/shiploop-domain-words.test.py` with `test/domain-words.json`, refuses chess, example-app, Salesforce and
    host-automation words anywhere under `skills/shiploop` outside `references/platforms/`, the guidance selector's index row and
    the README's platform link.
- The Salesforce platform card now names the Apex test reporter ShipLoop can read (`--result-format tap`; the default table and `human` put the outcome after the name and are refused as unread) and says an org-run test cannot fail on the item's base unless the command deploys the tree, so `red_na` with its reason is the route. The test stage's refusal for a test whose outcome cannot be read now points at the platform card under `references/platforms/`.
- A packet no longer says a thing twice, or carries a note the run has no use for yet. Each cut has a script that proves the
  text is elsewhere in the same packet or that no stage needs it.
  - A followed `R-<n>` or `AD-<n>` entry whose exact text sits in the whole-file diff the same block prints below it is listed
    by ID ("each entry is in the diff of HOME/spec.md below"), as one in a file the block quotes whole already was. The
    document and verify packets print the spec diff of a new spec and no longer repeat the followed entries inside it (on the
    long-knowledge fixture the hand-off block of each falls from about 38,000 to about 29,400 characters; a modified file's
    diff, which holds only changed lines, still leaves the entries' text where it is). One item's implement steps share one
    `not_covered (<item> implement)` label, so the test and verify blocks no longer repeat a label that names the item and the
    stage and nothing else.
  - "Current planning sources" prints only for a run with a planning reconciliation. The stages up to and including `plan` listed
    every planning stage, most of them "no current accepted result" because they had not run; the current results are the
    "Results this stage builds on" lines of the References block, and a reconciliation is the only event that retires one.
  - The last accepted transition drops its "Summary: as the status block's Done line shows." line (the summary prints only
    when it says more than the Done line), and the Improve lessons print one line each, with no blank line between them.
  - The consumer-delivery block prints whole only where an observation can be declared or a failure retained (system-test,
    product-acceptance, release-plan, release-check, release, release-verify, operations, handoff), at plan and at
    system-test-author (`consumer_delivery.WHOLE_BLOCK_STAGES`, computed from the observation tables). Every other stage
    prints the anchor, the record, the obligation IDs with their phase and the standing exclusions, plus any replanning or
    recovery notice; the contract, authority and observations are in the record the anchor names.
  - A packet that carries a stored lint record prints its findings, the verdict, the gate rule with the `lint_waivers` shape
    and the rerun command, and leaves the scope, coverage, tool, command and Git-plumbing sections to the record, with the
    command that prints it whole. A record whose tool failed or timed out, and a block of several pages, print whole.
  - An inline implement packet names each later step by its id and the paths it owns instead of its task (the task is in the
    step plan's result); a step without paths reads "(no paths declared)".
  - The test packet prints the shapes of `red_na` and `retired_tests` once, in duty 6. The "Optional at test:" line is gone and
    the base-run and floor rules say "(shape: duty 6)".
- Packets quote what the stage acts on, and the request gets a sentence index.
  - An inline implement step now quotes only its own slice of the item's hand-offs: the criteria the step lists, the
    test-spec cases whose criterion is one of them, and the follows entries its task, those criteria and those cases name
    (R-<n>), with every AD-<n> kept. A line says which step the block is cut to and where every step's criteria are. The
    item's whole set is quoted, as before, on the ask-agent route, when the step lists no criterion the plan defines or
    lists them all, and the follows cut alone falls back to the item's list when the step names none of its R-<n>. The
    implement Improve handoff quotes the same block. On a synthetic two-step item with twenty criteria, step 1's block
    falls from 20.5 KB to 1.4 KB.
  - Every save writes `request.md` in the run directory: the request verbatim, then split into sentences `S1..Sn` as a
    display index (the verbatim text still governs and every packet still quotes it). The intake packet points at it, and
    intake's `complete` (and `--check-only`) prints `ShipLoop request notice: ...` naming each sentence the summary does
    not cite (`S2-S4` and `S2 to S4` count as ranges). The notice never refuses. The master index lists the file.
  - system-test-author's "Results this stage builds on" lists each completed item's step-plan, test-spec and test result
    and its latest candidate run, and duty 1 says the records in force are the ones listed there, instead of sending the
    model to search state.md's history.
- A model no longer types, and ShipLoop no longer prints, paths the script already knows.
  - The producer callback has no `--result` flag. Its label names the one path to write, absolute (`Callback for this stage (run
    once after its work, with the result written to <run>/inbox/<action>.md): python3 <cli> complete --run-dir=<run> --action=<id>`),
    and `complete` reads `RUN/inbox/<action>.md` when `--result` is left out. The flag is still read when given, and any other path is
    still refused.
  - A path in `evidence_refs`, or in an assumption's `evidence`, may lead with `RUN/`, `HOME/`, `WORKTREE/` or `GUIDES/` (the
    packet's symbols). ShipLoop expands it before any check, checks that the file exists and stores the absolute path; a leading
    all-capital word and a slash that is none of those roots is refused by name. The same expansion reads an Improve stage's
    `--final-result`, where `CHILD/` (the review's directory) expands too.
  - An inner stage's Until Loop receipt is listed in `evidence_refs` by ShipLoop when the result leaves it out, once the loop's
    terminal packet has passed its checks. A result that lists it still keeps one entry. The refusal for a loop that never ran no
    longer asks the model to list the receipt.
  - The terminal stop is the Pause command with its verb changed: the packet's Halt line reads `Halt (terminal; only on the user's
    explicit stop): the Pause command with `halt` in place of `pause`.` and no longer repeats a second command line.
  - The test packet's red-check line names `python3`, like every other printed command, not the interpreter path of the host that
    rendered it.
  - An Improve handoff has its own symbol, `CHILD` (the review's directory), defined in its References block; the opening, receipt,
    owner record and review-file lines print as `CHILD/opening.md`, `CHILD/packet.json`, `CHILD/reviews/review-<n>.md`. Its commands
    keep the absolute directory.
  - Docs: the README, `references/navigator.md` and `commands/shiploop-complete.md` show `complete` without `--result` and the
    expansion.
- A packet no longer prints a text twice. The hand-off block's "Spec and architecture changes since the run began" diff
  prints a one-line pointer (file, size, section headings) for a living file that is new since the run baseline, when the same
  packet quotes that file whole: such a diff is the whole file. A followed `R-<n>` or `AD-<n>` entry whose exact text is in a
  file the packet quotes whole prints as an ID in one line (retired and superseded marks kept); an entry of a file the packet
  does not quote still prints its text, and so does any diff that is not exactly the quoted file.
  - The block's heading no longer says "the uncut diff"; it reads "nothing cut that is not printed in this packet", which stays
    true when a pointer stands in for text that is printed above it.
  - On a long-knowledge fixture (a 20 KB spec, an architecture, an environment file) the quoted-files-and-hand-offs block of the
    `plan` packet falls from 54,450 to 28,734 characters, `test-strategy` from 48,287 to 26,044, `product-acceptance` from
    51,105 to 28,862 and `test-spec` from 37,840 to 28,532. In the live Salesforce chess run 20.7 KB of the plan packet's
    22.1 KB diff was the spec quoted just above it.
- The step-plan packet again prints the interaction, UI and service-state planning bullet in duty 9 for a work item that may
  change them: a Design basis paragraph or exact section links, rechecking the Interaction design guide's matching
  subsections; baseline and delta; actors, events, connections and state owner; planned recovery checks; for UI the
  component, interaction and skin premises, the design guidance identity and version or digest (or named fallback) and the
  rich interactions planned; the UI decisions the step owns; locators of sources and checks. The packet file again lists
  the Interaction design guide's path.
  - Why: the head budget change moved this bullet to references/plan-record.md to fit the 20,000-character host print, which
    left a UI item's step plan with only a pointer. A model starting with no context rarely opens a pointed-to file, so the
    obligations did not reach the model.
  - When: ShipLoop decides from the original request and the item's title and context. Words for a user interface,
    interactions, events, connections or held state ("client state", "state owner", not the verb "state") mean the item
    may change them. An item with none of these words keeps the short form, the pointer to the Plan record guide alone, so
    its packet does not grow. The node bug-fix case's packets are unchanged.
  - Size: a UI item's step-plan head is 19,862 characters inline and 19,788 on the ask-agent route at a normal install
    (83-character run directory, 96-character CLI path), within 20,000. To fit, it leaves out the lookups and chrome the
    packet file repeats (the results it builds on, the progress view, the pause command), in the head's existing order.
    No duty is dropped.
- Each implementation step is proven by its own command, and the step's packet, its printed head and its Improve hand-off
  carry one Step block.
  - step-plan records `check` on every step: the one command, from the repository root, that proves the step's criteria
    with only that step and accepted earlier steps. A step without it is refused, naming the step. A step's `paths` are
    optional (the parallel chain reads them); when steps name none, the expectations cover the item's own paths. The
    step-plan Improve review flags a check that needs a later step's work or passes by skipping a missing artifact.
  - On the inline route ShipLoop runs the step's Proof when the step reports done and refuses a failure, quoting the exit
    and the output's tail; the refusal gives the loop's start command and both routes (fix and report done, or stop
    blocked and report revise). Each run is recorded at `tests/<action>-step-proof<N>.md`, bound to the action, the step,
    the command and the candidate's working trees; `--check-only` runs it without counting, and `complete` takes a passed
    run whose tree is unchanged. Before importing the step's Improve review ShipLoop runs the Proof again when the review
    changed the candidate, and reuses the record when it did not.
  - The item's check commands leave implement and its step review: they stay with the test stage and verify. The step's
    duty, exit conditions and repeat rule, its Improve focus and `stage_commands` name the step's Proof; the ask-agent
    route's whole-plan Work, repeat rule and gates are unchanged.
  - The Step block (task, the criteria it serves by value with their test cases, what it depends on, its Proof, its
    skills, the accepted steps and the later ones by their first sentence) sits right under Done when, the same lines on
    every surface, with no path fence; the inline step's packet and head end with its Until Loop, whose Work names the
    step's criteria, the R-<n> they serve and the item's AD-<n> ("until each requirement assigned to this step is
    satisfied and none of the others is broken"), and whose first exit condition lists the step's criteria.
  - The step's Improve hand-off names its review base: a `git diff` of the tree recorded when the step began and the tree
    when the review was bound, untracked files included.
  - State version 7: a run saved at version 6 is refused with its reason (its step plans name no check); start it again in
    a fresh run directory.
- A check command now runs from the step that finishes its criteria, not after every step. In the Salesforce chess run
  the step plan had three steps (engine, controller, board); the only check was a grep for the board files, it was
  listed on the first step's implement packet, it could not pass there, and the revise merged all three steps into one,
  so one implement and one Improve review ran instead of three of each. A check naming `criteria` is now due from the
  last step that lists one of them, and later checks are named on the packet as due at their step; a check with no
  criteria (lint, type, build) still runs after every step. The step-plan duty and the implement exit condition say so.
- Every stage's result template now says what its `summary` is for, so a summary records what only that result holds
  instead of restating the request, the spec or the files written.
  - The generic placeholder reads `<decisions, defaults, open questions and owners only this result records; no
    restatement>`. Intake asks for one clause per request sentence, cited S<n>; plan, test-spec and verify carry what their
    duties used to list (the duty text moved into the template, printed once). ShipLoop refuses a summary still equal to a
    placeholder.
  - Intake duty 1 covers each request sentence in one clause cited S<n> instead of copying it. Spec criteria give positive,
    failure and boundary lines only where each adds something, otherwise `n/a: <reason>`. Test-spec states a value every
    case shares once. A step's `task` cites IDs rather than their text; check commands are safe to repeat locally;
    scaffolding folds into the first step that uses it. Step-plan duty 9 opens with the record's status and covers only the
    topics the item touches. Test-strategy: the host's tool listing is the probe that a host tool exists, and IDs use
    characters legal in the runner's test names (`TC_1` where a hyphen is not). Prepare starts each runner in its no-op form,
    not the suite.
  - `--delivery-contract` is added only when the request or the host asks for it.
- Prose paths in a packet print as the References block's symbols. The block gains a fourth symbol, `GUIDES` (this skill's
  references directory), defined once with its absolute value, and its heading reads "References (symbols expand to these
  absolute paths; commands stay literal):". A line that names a file as prose prints `RUN/notes/x.md`, `GUIDES/navigator.md#anchor`,
  `HOME/spec.md` or `WORKTREE/SHIPLOOP.md` where it printed the absolute path: the pass-log line, the work-queue and planning-source
  lines, the previous-result lines of a replan or revise, the Run rules' State and knowledge-index line, the guide and policy lines,
  the test rerun, floors and inherited-learnings lines, the "Excerpt only" pointer and the evidence bullets. The Improve handoff
  file does the same (it carries the same block).
  - Always literal, because hooks and the loop runtime read them: the callback and every command line, the Keepalive marker, the
    "Full packet:" line, the Progress view link, the `evidence_refs` example, the `/until-loop` argument block, the
    `/improve ShipLoop Improve: ...` line and the index pointer. The list of lines that become symbols is closed (a new line that
    prints a path stays literal until it is named), and a packet without the block (done, halted, the Improve packet) is unchanged.
  - On the 24 whole renders of the node-fix-bug case the change is -4,507 characters (-2.9%); on the live Salesforce chess packet
    files it is -3.4% (the live run's long plugin-cache and run paths repeat more).
- The test stage's three gates now say what they did, and no text the model reads shows the refused-run cap.
  - `complete` at the test stage prints one `Gates:` line per gate result after the next packet (after the `--check-only`
    sentence for a check-only run): `Gates: base: skipped (no item base was recorded ...)`, `Gates: candidate: [focused] ... ->
    passed (3 ran, floor 3)`, `Gates: mutation: 2 of 3 mutants of the changed product lines killed ...`. Before, the three
    summaries were discarded, and a base run or mutation check that did nothing (no item base, no focused command, no changed
    line a mutation operator matched) wrote `disposition: passed`, the word a proof files. Such a record now says
    `disposition: skipped` with `passed: true` (every reader of `passed` and of `could-not-run` is unchanged) and keeps its
    reason under `skipped`. The E2E harness (`fidelity.gates_not_exercised`, `metrics.skipped_gates`) counts a record by either
    marker.
  - The refused-run tally prints the count and what it counts, never the cap: the test packet's "Refused runs ... 0 of 11"
    line is gone at zero and reads "Refused runs for this action so far: N (base, candidate and mutation runs together); if
    they keep coming, <the stage's route out>." above it (the old text said base and candidate only; a refused mutation check
    counts too). The same wording replaces the cap in the test rerun list, both refusal tails of `verify`, the tails of the base
    run and the mutation check, and the two "does not count" sentences. The cap stays in the script: `ShipLoop test run: ... was
    refused N times; done is no longer accepted` still names the route out when it stops accepting done.
  - The test result template's `summary` placeholder asks for what no ShipLoop record holds (the tests added and what each
    asserts, the test decisions retained, refined or superseded, any test changed to pass a run and why) and the test stage's
    duty 2 no longer asks for the decision locators and the step plan in `evidence_refs`, which no gate reads and the next
    packet lists itself. A new ledger row, `test-summary`, keeps both obligations in the packet.
- The test-spec stage no longer prints an example ID anywhere a model might copy it, and its refusals and head now say which
  requirements the living spec holds.
  - A refusal about a test case printed a literal example row with `"requirement": "R-3"`. A model copied it ("Requirement is
    expected as R-3; I'll use it"), found the spec held no R-3, and wrote a spec entry to match, which ShipLoop committed.
    Every printed shape of a case now holds placeholders only (`"id": "<a focused command ID>"`, `"criterion": "<a step-plan
    criterion id>"`, `"requirement": "R-<n>"`), the same text the template prints, and a case that keeps one is refused as a
    template placeholder like the oracle, red and green fields already were.
  - The refusal for a case with a missing, unusable or unknown `requirement` ends with the IDs `HOME/spec.md` holds (`lists R-1,
    R-2`; a retired one is marked), or, when it holds none, `lists no R-<n> entry: report revise naming the missing
    requirement`.
  - The test-spec result template has one row per focused-command ID of the item's step plan (the first twelve; the packet names
    the rest). Each row carries the ID, the one criterion the plan's focused commands list for it, and the requirement when that
    criterion's text names exactly one R-<n> the spec holds; the model fills the oracle, RED and GREEN and may change any field.
    An item whose plan lists no focused ID prints `"test_cases": []`.
  - The test-spec packet lists the spec's requirement IDs with the first 60 characters of each entry beside the template (the IDs
    alone for a spec so large the line would pass 2,400 characters), so a printed head that drops the quoted spec still shows
    them.
  - `complete --check-only` on a test-spec result prints a counted notice (`ShipLoop coverage notice: Criterion C2 has no test
    case ...`) for each step-plan criterion that no case names, no recorded non-focused command lists and no open item of the
    result mentions. A notice never refuses.
- A producer packet now opens with two pointer lines, the callback and the owner rule, in that order, whether it is printed whole, printed as a head or read from its file: `Lost context, or unsure? Run <CLI> next --run-dir=<RUN> (it reprints this step).`, then `Full packet: <RUN>/packets/<id>.md - ...`, which says when to open the packet file (a print that was cut, the duties, the template), what else it holds, and the lookup rule that used to close the head. The callback is the third line after the header and now gives its reason: run it exactly as printed, adding only `--check-only`, with no pipe, redirect, `;` or shell variable, because its output is the next stage's instructions and the status display reads the command.
  - Before, the first lines pointed at the 46 KB `context-index.md`, which a model never opened (0 of 103 listed pointers were followed), and the `next` command sat in a footer that a cut print lacked; commands are followed and files are not, so the command comes first. The References block gains one `Run records:` line naming `reference.md` and `context-index.md`, which line two relies on.
  - Gone: the index pointer, the head's footer (its recovery line, its bare `Full packet:` line, its first sentence and its standalone "Never end the turn while a ShipLoop command is still running", which the rules already say). The Improve packet that is bound carries neither pointer nor owner rule; one that asks for a bind or a restart keeps the `next` pointer; the paused, halted, blocked and done packets keep it with the owner rule.
  - A complete print still ends with the line `=== end ShipLoop head ===`; the pointer sentence now quotes it, so the E2E harness reads it as a line, never as text.
- Acceptance procedures are checked where they are written: a procedure whose actions are named but cannot all happen is
  found and revised in planning, not discovered at release.
  - The planning review focus, which the spec and test-strategy duties hold and every planning review (spec,
    test-strategy, plan, step-plan, test-spec, system-test-author, release-plan) prints, gains one condition: walk an
    ordered procedure from its stated start (can the actor reach that start under recorded authority, can each action
    occur in the state the preceding actions leave, can the chosen observer see the expected result?), record an
    unreachable start as an open prerequisite, revise an invalid action or oracle, claim no execution from a plan, and
    treat an observation made before its setup changed as stale.
  - test-spec applies it to its own cases (new duty item 4; the later items are renumbered 5-8), and its loop gains the
    exit condition that each case's procedure can happen as written from its stated start, or its unreachable start is an
    open item. A forbidden action stays its own failure case. A procedure another record holds is cited by its locator in
    the case's `oracle` or the open item's `check`, so implement, its Improve, test, verify, system-test-author and the
    open item's consumer use that one procedure.
  - test-strategy writes a consumer interface case with its start (actor, entry route, initial state) and ordered
    actions under `## Real-boundary checks`, with an ID later stages cite.
  - The test-case planning guide gains a Procedure validity section: the six facts a procedure states (start, actions,
    oracle, observation, ownership, evidence), validity kept apart from execution, and three faults to look for.
  - Unchanged: a test case keeps exactly its six fields (a `procedure` key is still refused), and an opt-in consumer
    check stays outside the focused command set.

### shiploop-e2e-audit 0.7.4

- The Grok adapter recognizes `shiploop improve-pass` as a ShipLoop command, so traces that record an Improve pass are attributed; the host trace fixtures pin the new adapter hash.
- The audit recognises a validate-existing stage that ShipLoop recorded itself by the opening words of its summary, so it
  accepts both the shorter sentence the engine now writes ("... and each matched its state.") and the longer one an
  earlier ShipLoop wrote ("...; validate-existing was recorded without running it. Records: <path>"); before, only the
  longer one counted and a run of the newer engine was reported as missing a callback for that stage.

### shiploop-run-review 0.2.3

- The export recognizes the host-neutral Improve packet as the compact-handoff layout: `1. Run the improve skill on the <stage> result with this argument, ...` with the argument `ShipLoop Improve: <handoff>` on its own line, as ShipLoop prints it since the 2026-10-17 packet review. The earlier `For example, on Claude Code:` and `/improve <argument>` lines are still recognized for saved runs.
- The generated stage catalog (`defaults/stages.json`) carries ShipLoop's corrected spec goal, which no longer names a
  `FEATURE/spec.md` folder: ShipLoop derives a run's requirement ID changes from the spec diff.
- The generated stage catalog (`defaults/stages.json`) carries ShipLoop's implement row as it now stands: its goal no longer
  names the step's paths, and its complete runs add `step-proof`, the step's Proof that ShipLoop runs at done.

## 2026-10-17

### skill-craft 2.5.4

- Skills: improve 0.4.4

### improve 0.4.4

- Clarify how Until Loop composes separate work, success and continuation conditions from a request and accepted clarifications, while retaining literal stop and check obligations. Refresh the vendored Until Loop runtime to 0.10.0; Improve keeps its existing isolated callback mode.

### skill-craft 2.5.3

- Skills: backchain 0.6.5

### backchain 0.6.5

- Run package-local goal and confirmation comparisons through Until Loop's existing exit
  checks. Retain candidate-bound comparison evidence for every review, while keeping
  confirmation repair authority and useful chunk boundaries in the semantic review.
  Clarify that preserving seed labels does not authorize moving their implementation into
  discovered prerequisites, and freeze live-check commands as prepared inputs.
  Reuse scripted artifact checks in live runs, and keep confirmation criteria within the
  request and governing sources.

### skill-craft 2.5.2

- Skills: improve 0.4.3

### improve 0.4.3

- Vendor Until Loop 0.9.0 runtime helpers while keeping standalone Improve on its isolated callback mode.

### skill-craft 2.5.1

- Skills: backchain 0.6.4

### backchain 0.6.4

- Recheck implementable chunk boundaries on every planning review and after repairs.
  Split oversized work along real prerequisite and deliverable boundaries, preserving
  serial/parallel dependencies, outcome coverage, confirmations, and existing edit bounds.
  Add repeatable chunk fixtures, preservation and lifecycle regressions, and an explicit
  native live-check entrypoint; keep model evidence distinct from hermetic checks.
  Preserve unaffected confirmations verbatim and keep unrelated context chunk findings
  advisory, correcting failures observed during the live regression workflow.

## 2026-10-16

### skill-craft 2.5.0

- Skills: shiploop 1.5.0

### shiploop 1.5.0

- ShipLoop commits every file it is asked to commit. Before, any file whose text matched the credential screen (a line such
  as `Auth: sf login (alias de)` or `signature: static` was enough) was unstaged and left out of the item commit, the
  knowledge-home commit, the Improve review's commit and the late-file commit that `plan-return` makes, and a notice told
  the model to reword the file and commit it. A file left out that way kept the return off the user's branch (the return
  fell back to the working-tree route) and left the model a hand-commit to do, which the packets forbid.
  - `plan-return` no longer takes a `fresh` list of skipped paths, and no output says "Not committed, they look like they
    hold a credential".
  - The Return route sentence reads "plan-return commits files left uncommitted, so commit nothing for the return." The
    exception for a file it reports as not committed is gone.
  - Paths ShipLoop never commits are unchanged: run evidence, protected paths and the caller's exclusions.
- ShipLoop refuses no submission or commit message because its text looks like a credential, and no packet says it does.
  Before, a stage result, a prompt, an Improve opening or final result, an `improve-commit` message and any line of
  `docs/shiploop/` was screened for an "explicit credential pattern", and `auth`, `token`, `signature` or `sig` followed
  by `:` or `=` and a word counted as one unless the word was on a short list. Ordinary documentation such as
  `Auth: sf login (alias de)`, `access token: not printed` or `Password: bcrypt, cost 12` was refused, and the model had to
  reword it before the run could go on.
  - The Checked-by line of every stage reads "the usual faults (no outcome or summary, or an absolute evidence_refs path
    that does not exist)"; the gates for `spec`, `plan` and `step-plan` no longer add "or that looks like a credential".
  - The Improve packet's checked-by sentence no longer lists "credential-looking text" among what `improve-commit`
    refuses; the knowledge-home line no longer says ShipLoop "screens them for credentials".
  - The architecture duty keeps one positive instruction: name a credential by its alias or mechanism, never its value.
  - `workspace start` and `init` take a prompt that mentions a token or a key.
  - The progress page and the lint output still redact credential-like text; they are display only and refuse nothing. The
    terminal status block, the narrative and the run files (`state.md`, `status.md`, `timeline.json`) print what was
    submitted as written, as they did for text the old screen let through.
  - `commit_paths` commits every path it is given, including a file named like `.env`. What keeps secrets out of the product
    commit is the `review-return` keep/exclude choice and the duty to keep credentials out of the product commit.
- On Claude Code, ShipLoop now enforces that the improve skill is invoked at every Improve stage, instead of asking for it in
  the packet. In the 2.1.0 live run 3 of 4 Improve reviews were written by a script that reported to the runtime directly, and in
  the 2.4.0 live slice the skill was invoked for 1 of 4 stages; changing the packet's wording did not move either.
  - A new hook, `scripts/shiploop-skill-call` (`PostToolUse` on the Skill tool, declared as `after-skill` in
    `host-hooks.json` for Claude only; `shiploop-hook install --host claude` adds the same entry), appends each Skill call
    of a session the keepalive hooks bound to a run to the run's `skill-calls.jsonl`: time, skill (`skill-craft:improve`
    and `improve` are one), argument, tool-use id, session and, for a subagent, its id. It never blocks the call and writes
    only inside the bound run directory.
  - `complete --action=<improve id>` refuses until the record holds a call to the improve skill made after that Improve
    stage started whose argument carries the stage's handoff path or action id. The refusal's first line names the Skill
    call to make and the command to run after it.
  - Where no record can exist (Grok, Codex, Cursor, OpenCode, no hooks, hooks turned off with `SHIPLOOP_KEEPALIVE=off`,
    hooks installed before this one, or `delegation: ask-agent`, where a fresh worker runs the review) nothing is enforced,
    and `complete` says so once per run when it accepts the import.
  - Codex and Cursor started from a Claude shell inherit its session variables but have no Skill tool, so their own
    markers (`CODEX_THREAD_ID`, `CODEX_SANDBOX`, `CURSOR_PLUGIN_ROOT`) exempt them. A hook reading closed or non-text stdin
    exits 0 with nothing recorded. The refusal reminds the model to keep its `--final-result`, `--notes` and `--no-commit`.
  - The hook generator accepts the new `after-skill` event (Claude only) and refuses it for any other host.

### skill-craft 2.4.1

- Skills: shiploop 1.4.1

### shiploop 1.4.1

- The head printed for a packet longer than 16,000 characters now leads with the stage's duties and rules. Before, the head
  left them in the packet file: for all five such packets of a node-fix-bug item (step-plan, implement, test, verify,
  carry-forward) the duties began 10,400 to 15,000 characters into the file, so a model that read only what was printed
  never saw what to do. The order is now goal, status block, duties, result template, pointers, loop command; the quoted
  knowledge files and hand-offs are dropped from the head first when it would pass the limit.
  - The ask-agent opener reads "Execute the prompt in a fresh context." where it read "Clear and then execute the
    prompt.", which contradicted the rule that no packet pauses for a context clear.
  - The Improve packet says to invoke the improve skill at every Improve stage and not from memory of an earlier one. In
    the last live run the model invoked it for 1 of 4 stages.
  - The head closes with `=== end ShipLoop head ===`, so a reader can tell a whole print from one cut by a pipe. The
    E2E harness reads a head to that line (`counters.head_or_why`, `flow.py`) and still reads saved heads of the older
    layout to the status block.
  - The head's footer and SKILL.md no longer tell the model not to re-read "the Improve card"; the Improve stage's packet says
    to invoke the skill every time.

  Two smaller wording changes ship with it. The opener of every packet now reads "Execute the prompt in a fresh context."
  (it said "Clear and then execute the prompt.", which contradicted the packet's own rule never to pause for a context
  clear). The Improve packet now tells the model to invoke the improve skill at every Improve stage, not from memory of an
  earlier one. The E2E harness readers follow the new head to its closing line.

## 2026-10-15

### skill-craft 2.4.0

- Skills: improve 0.4.2, shiploop 1.4.0, shiploop-e2e-audit 0.7.3, shiploop-run-review 0.2.2

### improve 0.4.2

- On a ShipLoop Improve stage the child is already started: ShipLoop writes the opening and starts the runtime at the
  transition. The skill continues the child from its receipt and never writes the opening or runs `improve-start`.
  Lessons and a revised result go to the Improve stage's `complete` (`--notes`, `--final-result`).

### shiploop 1.4.0

- Improve is now a stage of its own in ShipLoop's sequence (owner, 2026-10-11). After each reviewed stage, the run
  issues an `improve` action with its own id. Its packet says to run the improve skill on the result, then run
  `complete --action=<improve id>`.
  - **ShipLoop sets the review up at the transition.** It binds the card, writes the opening from the run's state,
    freezes the contract and starts the runtime. The model never writes the opening or starts the child.
  - **`complete` imports the review.** `improve-complete` is removed; its `--notes`, `--final-result` and
    `--no-commit` flags are on `complete`.
  - **`improve-start` only restarts** a stopped or refused review, with `--restart-stopped`.
  - **Other Improve commands** (`improve-bind`, `improve-commit`, `improve-reconcile`) take the Improve stage's id.
  - **The packet file** is `packets/<improve id>.md`. The status block and the dry run show `improve` as its own step.
  - **Duplicate reviews are refused.** `complete` refuses a review that repeats another Improve stage's review in the
    same run. In the 2.1.0 live run, a model-written script faked three of four reviews from one template.
  - **Old runs are refused.** A run whose Improve child predates this change cannot be resumed; start a fresh run.

### shiploop-e2e-audit 0.7.3

- The audit harness follows ShipLoop's Improve stage: a `complete` naming the Improve stage's id is attributed to the
  stage it reviews, and `improve-complete` is no longer an allowed callback.

### shiploop-run-review 0.2.2

- The export reads Improve as a stage of its own: it finds the Improve packet by the stage id that state.md records
  (`packets/<improve stage id>.md`), and still reads the older `packets/<action>-improve.md` layout. It recognises the
  Improve stage's `complete` as the return step of the compact packet.

### skill-craft 2.3.3

- Skills: shiploop 1.3.2

### shiploop 1.3.2

- Second script quality pass: `shiploop_quality` no longer lists in `__all__` (or its
  docstring) helpers it does not define, so `from shiploop_quality import *` works again.
  Progress-data read errors now name the file and its size limit, and a malformed dry-run scenario
  reports its type.
  19 more private functions have docstrings that were checked against their code by two
  independent reviewers.
  24 further private functions are documented the same way, leaving two for a later pass.

## 2026-10-11

### skill-craft 2.3.2

- Skills: shiploop 1.3.1

### shiploop 1.3.1

- Script quality pass: re-raised errors keep their cause and carry the value or
  position that failed (progress data, item scope, lint, git timeout, planning
  context); transition hooks catch `Exception` rather than `BaseException` and
  name an unexpected hook failure on stderr; `shiploop-drive` and `lint --show`
  reject non-positive counts at the command line; every public function and
  class has a docstring; cryptic helper and variable names were replaced; and a
  dead variable, two `assert`s used as control flow, unused parameters and a
  closure over loop variables were removed. `SHIPLOOP_DEBUG` names a status-hook
  failure on stderr.

### skill-craft 2.3.1

- Skills: in-parallel 0.1.1, plan-dispatcher 0.6.4

### in-parallel 0.1.1

- Require a distinct recorded native handle for every queued item and retry, preserving the one-item, one-fresh-agent contract while retaining coordinator responsibility for native launch evidence.

### plan-dispatcher 0.6.4

- For the compact Ask Agent profile, reject native handles already bound to another attempt under the Dispatcher lock, including accepted and retried attempts. Keep same-attempt registration replay and ordinary Dispatcher behavior unchanged.

### skill-craft 2.3.0

- Skills: improve 0.4.1, shiploop 1.3.0

### improve 0.4.1

- The bundled Until Loop runtime is upstream 0.8.3 (whichguy/until-loop v0.8.3, 908db9c): stale size-limit wording removed and a test flake fixed; no behavior change. The README now points at PROVENANCE.json for the version and commit instead of repeating them, and the callback-evidence guide no longer justifies brevity by a state-size limit (there is none).

### shiploop 1.3.0

- The last consumer-contract 4c removals, after the renderer swap. The first removals shipped in 1.0.0; these six were
  kept for the swap.
  - **References block.** It no longer defines a `FEATURE` symbol or lists the old feature folder and the
    `features/README.md` list. Its "Knowledge files" line lists the three living files.
  - **Knowledge lines.** The plan packet no longer prints the `Spec: docs/shiploop/spec.md @ <sha>` first-line pin, and
    early stages no longer print the "Earlier features" clause. The home line says "spec, environment and architecture".
  - **Loop contracts.** The unused `{feature}` token fill is gone.
  - **Engine.** `knowledge_home` drops `feature_dir`, `FEATURE_LIST`, `_GROUNDING`, `GROUNDING_LABELS`, `grounding`,
    `earlier_features` and `spec_pin`.
- ShipLoop no longer limits the size of an inner-loop contract (the bundled Until Loop is now 0.8.3, which has no size limit either). The 16 KiB state budget (9,216-byte contract budget, report reserve and bookkeeping reserve) is gone with the Until Loop runtime's own cap (Until Loop 0.8.1+): `improve-start` accepts any opening, step-plan accepts any `test_commands` list, and the Backchain guidance and Improve context no longer print a byte allowance. A deep run directory could previously push the verify stage's contract over the budget and block every item. Contract building, the one-contract-per-action rule, exit and repeat conditions and receipts are unchanged.

### skill-craft 2.2.2

- Skills: shiploop-run-review 0.2.1

### shiploop-run-review 0.2.1

- Run Review recognizes current compact Improve handoff packets and explains that historical checklist labels are not used in that layout.

### skill-craft 2.2.1

- Skills: shiploop 1.2.1

### shiploop 1.2.1

- Parallel and serial implementation-chain worker packets now carry ShipLoop's current Code craft rubric, and their linked guidance matches the implement-stage routes.

### skill-craft 2.2.0

- Skills: improve 0.4.0, shiploop 1.2.0

### improve 0.4.0

- The improve skill accepts `ShipLoop Improve: <handoff path>` as its argument. ShipLoop's Improve packet now only invokes
  the skill and names the done command (owner, 2026-10-11). The handoff file ShipLoop writes takes the place of the packet
  in the "ShipLoop whole-skill subcall" section: the binding marker, the result under review, the start, commit and
  return commands, and the evidence files.

### shiploop 1.2.0

- A completed Improve child that ended on one unchanged trivial pass, with files changed after its bind, now restarts
  through `improve-start --restart-stopped`. Before this change, `improve-complete` refused it and told the model to "run
  the loop's next review", but that loop was already complete and `--restart-stopped` refused any child that was not
  stopped. The run had no route forward and paused (live node-add-route slice, 2026-10-11). The refusal's first line now
  ends with the restart command. A test runs that command through the real CLI.
- The ShipLoop packets are re-cut for concision (owner, 2026-10-11); the plan and rubric are in
  docs/shiploop-packet-recut-2026-10-11.md.
  - **Duties.** Every stage's goal is one action sentence that says where its output goes, and every duty is a short
    numbered list.
  - **Shared rules.** Cut to the five that live runs showed are needed.
  - **Code craft.** Prints in full at implement only. Each step's Improve review and verify apply it.
  - **Loop mechanics.** These live on the Until Loop card.
  - **Printing.** A packet at or under 16k characters prints whole.
  - **Improve packet.** Two instructions: run the improve skill with the handoff path, then run `improve-complete`.
    ShipLoop binds the recorded card itself, and everything else goes in the handoff file beside the opening.
  - **No advance mention.** No producer packet mentions Improve ahead of time, and Improve never mentions Backchain.

  On the live node-fix-bug slice, the packet characters written fell from 546k to 212k.

### skill-craft 2.1.0

- Skills: ask-agent 0.10.1, in-parallel 0.1.0, plan-dispatcher 0.6.3, shiploop 1.1.0

### ask-agent 0.10.1

- Make parent-owned cleanup follow successful worktree edit integration and
  combined checks. Use the existing receipt-bound close for compact tasks as
  well as legacy helper tasks, retain branches and commits, and report refusals.
  Keep failed, unmerged, return-only and findings-only worktrees available.
- Accept exactly one redundant `PYTHONDONTWRITEBYTECODE=1` assignment before the pinned compact-v4 `python3 -B` finish command. Preserve exact matching of every remaining argument, binding digest, worker, and working directory. Reject other or duplicate assignments, `env` wrappers, and wrong digests.

  The live r4 worker really completed its finish call, but this harmless prefix made the native audit fail. Retain the original failed verdict. A separate read-only replay passes all 28 gates without modifying the evidence; 84 native and compact regression tests pass. Fresh live qualification remains required.
- Repair compact-v4 live experiment evidence after the three-worker Grok trial exposed a truncated preparation result and auditor assumptions about prompt ownership, Python interpreter identity, and inspection-specific patch locations.

  Keep full setup and dispatch evidence on disk and emit small versioned, hash-bound summaries. Bind worker ownership through the exact native launch and pinned action packet. Use the producer runtime evidenced by the frozen script invocation instead of the auditor process runtime. Compare semantic commit evidence while independently checking patch bytes and containment. Retain fail-closed checks for truncation, hash drift, cross-worker packets, foreign paths, and unsafe patch artifacts.

  The original trial remains failed. Offline qualification passed 239 tests, including seven new regressions. These changes affect the experiment harness and auditor; they do not establish a speedup or live qualification. Fresh live delivery cases remain required before a live-pass claim.
- Repair native audit compatibility with the compact-v4 worker lifecycle. Require start-only dispatches to bind through the pinned action packet and actual native finish, normalize only equivalent absolute Python interpreter paths, and compare stable action-packet and commit-inspection fields while separately validating patch evidence. Findings-only returns permit absent or null delivery metadata but reject delivered commits, patches, or inspections. Preserve the legacy parser result shape.

  Validate the changes with focused regressions, all five Ask Agent suites, and a separately saved read-only replay of the retained real Grok evidence. A controlled copy with one native finish removed must fail after a passing baseline. Original live verdicts remain unchanged, and fresh live qualification is still required. This audit repair does not establish a speedup or marketplace release.
- Share Git's `/` path separator and protected-path set between the task and workspace helpers. Reject unnormalized path segments in workspace relative paths while preserving one trailing directory marker and legal POSIX Git filenames such as `C:notes`. Reject Windows drive-qualified or drive-relative task scopes.
- Add a reusable Claude Code / Sonnet delivery qualification suite alongside the
  Grok harness. Preserve the shared dirty-parent worktree, production lifecycle,
  commit-delivery, and ephemeral checks while retaining Claude-native dispatch,
  completion, and child transcript evidence. Distinguish explicit command-level
  worktree scope from hosts that expose a native cwd argument, and keep failed
  attempts and timing evidence separate from qualification claims.

### in-parallel 0.1.0

- Document In Parallel as the goal-oriented entry to the coordinator workflow,
  with examples for independent analysis and isolated implementation. The same
  coordinator and existing harness.py runtime own execution and delivery.
- Separate complete task decomposition from worker concurrency. Default new batches
  to at most five concurrent workers, honor an explicit prompt-supplied cap, and
  refill free slots with fresh agents until the full required queue is accepted.
  Preserve unresolved outcomes and verify aggregate membership against the complete
  goal. Add reusable queue tests for bounded refill, full coverage, terminal retry,
  and uncertain-launch reservations; keep Dispatcher as the only queue authority.
  Consume the planned backlog incrementally, preparing only yielded items and
  starting a fresh agent for each, with no persistent worker pool or batch barrier.
  Clarify bytecode-safe report-only inspection after a live trial exposed an
  ignored cache file despite clean Git status; retain full fixture-file auditing.
- Remove integrated worker worktrees after successful combined delivery and
  checks, using Ask Agent's acceptance-bound close. Preserve branches, commits
  and durable evidence; report cleanup refusals separately from integration.
  Keep failed, unmerged, return-only and ephemeral worktrees. Resume interrupted
  cleanup without repeating integration or sweeping historical runs.
- Expose one callable coordinator entry point shared with the CLI and a public
  delivery request validator. Reject malformed arguments before reserving work;
  preserve caller-owned inputs, structured diagnostics, and existing recovery
  rules. Document the composable APIs and add concise comments around evidence,
  locking and cleanup boundaries.
- Add an `in-parallel` skill that composes Ask Agent's compact task interface
  with Plan Dispatcher for independent native-agent batches, with separate native
  collection, evidence-based acceptance, and guarded delivery.

  Live experiments favor a single top-level Grok coordinator for a controlled
  pilot. Retain failed and blocked trials: Claude headless nesting needed parent
  resumes, one direct process remained open after delivery, and Markdown scratch
  reports were refused. The reusable auditor separates native lifecycle evidence
  from filesystem preservation, and retains provenance for parser-corrected
  re-audits. Worktrees and commits remain available for explicit later cleanup.
- Centralize repeated artifact and script names and share repository-path
  validation between coordination and delivery. Keep Git's slash protocol
  separate from native filesystem paths, reject ambiguous drive-qualified
  scopes before dispatch, and read JSON and helper responses as UTF-8 independent
  of the caller's locale. Cover path boundaries and locale behavior with tests.
- Add In Parallel as a prompt-facing entry to Agent Harness. One fresh
  coordinator decomposes a Git-backed goal into independent implementation scopes
  or analytical perspectives, owns the existing worker lifecycle, and returns a
  verified synthesis with partial outcomes, disagreements, and delivery evidence.
  Reuse the existing harness script and host limits without another agent layer.

  Consolidate the unpublished Ask Parallel and Agent Harness entry cards into one
  `in-parallel` skill and matching coordinator card. Keep Ask Agent independently
  usable, preserve Dispatcher as the sole task-state owner, and retain existing
  runtime schemas and pinned historical evidence. Register a reusable
  `in-parallel` suite group with the historical `agent-harness` group as an alias;
  compare direct and composed worker contracts using real Git fixtures.

### plan-dispatcher 0.6.3

- Plan Dispatcher supports an opt-in compact Ask-Agent coordinator profile and allows concurrent read-only attempts to share the same canonical workspace.

### shiploop 1.1.0

- Packets print what the consumer contract hands each stage, by value and uncut.
  - **Knowledge files read.** Each file `knowledge_home.READS` gives the stage is quoted whole after the status block,
    each line prefixed `  | `, or marked "not written yet". The References block names them in one line. This replaces
    the per-stage consult list of headings, because heading matching missed most saved homes (owner decision D1).
  - **Hand-off values.** "Handed off by earlier stages" quotes each `CONSUMES` value from `handoff_sources`:
    - the follows IDs with their spec or architecture entries, marked when retired, or "no entry in HOME/<file>";
    - the criteria, focused commands and system commands;
    - the test cases with oracle, red and green;
    - not_covered;
    - the open items with check, reason, consumer, owner and producer;
    - the lessons;
    - the spec and architecture diff since the run baseline.

    A missing value prints "not recorded by <stage>".
  - **Result-shape block.** It prints the shape of each hand-off field the gate requires and the template leaves out:
    - follows at step-plan;
    - test_cases at test-spec;
    - lessons at release-verify;
    - not_covered, optional, at implement;
    - assumptions at each open-item stage.

    A done result that follows the packet is no longer refused once per missing key.
  - **Duty wording.** test-spec records its cases in `test_cases` and a due-later case as an open item; verify and
    system-test-author record later checks and unrunnable cases as open items in `assumptions`.
  - **Working-tree return.** The handoff packet prints the lessons commit message for the user to commit, since a
    working-tree return makes no commit.

### skill-craft 2.0.1

- Skills: improve 0.3.1

### improve 0.3.1

- The bundled Until Loop runtime is upstream 0.8.2 (whichguy/until-loop v0.8.2, f7d97f6): a contract without exit checks, as Improve and ShipLoop write, no longer gets the verify-script instruction or the check-repairs schema entry, so its packets are 24% smaller than in 0.8.1 (about 6% above 0.7.0).

### skill-craft 2.0.0

- Skills: ask-agent 0.10.0, improve 0.3.0, shiploop 1.0.0, shiploop-e2e-audit 0.7.2, shiploop-run-review 0.2.0

### ask-agent 0.10.0

- Make the compact task interface the standalone route for current workspaces and
  explicitly selected worktrees. Support `mode: edit`, `report-only`, and
  worktree-only `ephemeral`; worktree edits default to `delivery_mode: commits`,
  with `patch` as an explicit alternative. Current edits have no automatic commit;
  report-only makes no filesystem edits; ephemeral work returns findings and audit
  metadata only, with no commit, patch, or code integration.

  Before commit delivery, copy and verify the caller's exact `HEAD`, staged and
  unstaged binary patches, nonignored untracked files, and existing root
  `.gitignore` and `.claspignore` controls. Create base `S` in the child only: use
  the original `HEAD` for a clean source; dirty layers that change the net tree
  create a one-parent snapshot. A dirty net-zero source keeps `S` at its original
  `HEAD` and records `snapshot.source_dirty`. Preserve the source capture and
  patch layers, and do not rewrite copied worker files while updating the child
  index. Have the worker commit only scoped contribution paths after `S` and
  verify the complete ordered `S..C` range, residual paths, scope, and branch
  position. Exclude `S` from returned commits.

  After native completion, parent verification and target revalidation, allow a
  clean captured source with an unchanged parent to cherry-pick the complete
  verified range. For any source with `snapshot.source_dirty: true`, apply only
  the verified contribution patch and preserve parent `HEAD` and index; never
  add the private snapshot to parent history. Keep worker and
  parent scripts limited to filesystem checks: native launch/collection,
  integration, combined tests, acceptance and cleanup stay parent-owned. Preserve
  the existing consumer-owned and orchestrated contracts, with separate source,
  local-pilot and release claims.
- Add opt-in external task packets and pinned command arguments to the standalone
  task interface. Keep inline transport compatible. Return the actionable task
  and mode-specific rules from the existing worker-start check, preserving native
  parent launch/collection and acceptance, current/worktree selection, inherited
  state, scoped commits, explicit patch delivery and findings-only ephemeral work.
  Add packet tamper/path/route regression coverage and harness final-result writing
  with separate native evidence validation. Smaller launch payloads are measurable
  locally; elapsed-time improvement still requires matched live qualification.

### improve 0.3.0

- The bundled Until Loop runtime is now upstream 0.8.1 (whichguy/until-loop v0.8.1, 529a42d); its state has no size limit and exit checks have no count cap. Contracts may carry
  frozen `exit_checks` written from the request before any work; each active packet prints a `verify_script` that the
  executor runs as its shell command's own text (so permission prompts and hooks see every check) and that pipes the
  real results into the runtime's `record` step; a satisfied report needs a fresh recorded run and every check
  passing. Failed checks can be repaired (never their clauses). The runtime's state limit is 64 KiB. Contracts without
  exit checks behave as before. Evidence: until-loop-lab, 374+ graded runs on Sonnet 5.5, Grok 4.7 and GPT-6.1 Sol.
- The bundled Until Loop card can now be invoked by the model (`disable-model-invocation: false`) and opens with
  "Start from a parent-written contract": when the argument or packet names a `Contract:` file and a `Receipt:`, it
  skips interpretation and runs exactly `python3 <script> start --receipt <Receipt> < <Contract>`; the file wins over
  the argument text, and an existing active receipt is continued through its `next_argv` instead of starting a second
  run. The callback adapter reference says the same. The runtime script is unchanged.

### shiploop 1.0.0

- The repository knowledge home gains `docs/shiploop/architecture.md`: the stack (language, frameworks, dependencies and why), the structure (modules and who owns each), conventions, interfaces and boundaries, and the decisions as stable IDs (`AD-<n>`) with a `Superseded` section. The living spec stays the contract and the architecture stays the build, so each survives a change of the other. Plan and step-plan keep the file up to date and the prepare close refuses done while it is missing or empty, so a repository whose home an earlier version wrote is asked for the file at its next run's prepare; a refused prepare names it and says what it holds. A later architecture.md that no longer mentions an earlier committed decision ID is refused, as a living spec that drops a requirement ID already was, when the drop is in an uncommitted edit (the stage's own, or a review's before it commits through `improve-commit`); an edit a review already committed through `improve-commit` is not seen, for the spec too (deferred). The refusal puts the fix, the absolute path and the route's own commands on its first line, the IDs on the second, and for an `improve-complete` import it names `improve-commit` before `improve-complete`. A line the credential screen flags in any home file is refused the same way, with the absolute place, what to write instead (an alias, never a value or code that assigns one) and the route's command.
- ShipLoop records the data each stage's consumer reads, so a stage cleared of its context can work from its packet alone
  (consumer contract, slice 4a).

  - **Whole-file knowledge quotes.** `knowledge_home.READS` names, for every stage, the living files its packet quotes
    whole (`spec.md`, `environment.md`, `architecture.md`); `reads_quotes(state, stage)` returns each file's absolute path
    and its whole text, or None when it is absent or blank. A heading spelled any way is quoted the same.
  - **Entries.** `knowledge_home.entry_text(repo, "R-3")` returns one requirement (from `spec.md`) or decision (`AD-<n>`,
    from `architecture.md`) as the file holds it, uncut, and `entries()` flags one under Retired or Superseded.
  - **Run baseline.** `init` records the execution checkout's HEAD in the run folder (`run-baseline.txt`);
    `spec_diff(root, state)` is the uncut `git diff` of `docs/shiploop/spec.md` and `docs/shiploop/architecture.md` since
    then.
  - **Lessons commit.** release-verify's knowledge commit is always made: its body is the result's `lessons` (Learned, Key
    considerations, Open for the next run) plus the open items still left, and it is an empty commit when the home did not
    change. The next run's intake and discovery quote it whole, found by its subject however many commits follow, beside
    the last three commit messages they already quote.
  - **Hand-off result fields.** step-plan records `follows` (the R-<n> and AD-<n> the item follows; each must have an
    entry in the living spec or architecture), test-spec records `test_cases` (one `{id, criterion, requirement, oracle,
    red, green}` per ID this item's focused commands list, both ways, with the step plan's criteria and real
    requirements; this replaces the check of the feature `test-spec.md` headings), implement may record `not_covered`,
    and release-verify records `lessons`. A template placeholder left in any of them is refused.
  - **Open items.** test-spec, verify, carry-forward, system-test-author, system-test, release-plan and release-verify
    list the open items they leave in `assumptions` (`[]` when none); an open item's consumer is a later outer stage, or
    the same item's carry-forward from test-spec or verify, and may name an `owner`. A row stays open until its consumer
    stage's later done result settles it.
  - **Refusals.** Every hand-off refusal's first line is the fix, the result file's absolute path and the next command;
    on improve-complete without `--final-result` it says to write a final result to the printed path and pass it. The
    Improve packet lists `revise` among the final outcomes at test-spec to verify.
  - **What each packet consumes.** `navigator.CONSUMES` names, for every stage, the hand-off values its packet quotes, and
    `handoff_sources(root, state, stage)` returns them; system-test-author now reads test-spec and release-plan reads
    system-test-author in the stage table.
  - **State version 6.** A run saved by an earlier version is refused with the fresh-run hint.
- ShipLoop's knowledge home has three living files, and every artifact it keeps has a named reader (consumer contract,
  slices 4b to 4d).

  - **Three living files.** `docs/shiploop/spec.md`, `environment.md` and `architecture.md`. `environment.md` gains the
    sections `## Harnesses and suites` (each suite with its files and command, and the system-test catalog) and
    `## ID convention` (the scheme and the one command that lists the IDs already taken); `architecture.md` gains
    `## Real-boundary checks` (each check a local test cannot prove, with its owner). test-strategy writes those two files;
    system-test-author keeps the catalog, and release-check corrects the standing release procedure, in `environment.md`.
    test-spec is no longer a knowledge close (its cases are in the result), and intake keeps no file.
  - **`test-strategy.md` and `docs/shiploop/README.md` are retired.** No close requires them and nothing writes or names
    them; an older repository keeps its copies, which the credential screen still reads.
  - **Rollback at release and operations.** In an isolated run the release, release-plan, release-check and operations
    packets print the return's rollback commands.
  - **The feature folder, the retire and outcome.md are removed.** A run no longer writes or requires
    `docs/shiploop/features/<run>/` (spec, plan, test spec, system tests, release plan, outcome) or the feature list
    `features/README.md`: their content is in the stage results the consumers quote, in the living files, or in the
    release-verify lessons commit. The handoff no longer removes the run's feature spec, and an older version's feature
    folders are left untouched. release-verify's close needs `environment.md` only: the lessons are the result's field.
  - **`SHIPLOOP.md` is the host's file.** ShipLoop no longer commits, screens or returns it as knowledge: a return plan
    reviews it like any product file and may exclude it, and validate-existing treats a change to it as a stray path.
    Packets still name it as the host-authored index to read if present.
  - **Progress view.** It lists the living spec and the run's accepted results; the feature drafts, the test strategy and
    the retired-spec row are gone.
  - **The completion report shows the hand-offs.** After "Work item progress": the uncut spec and architecture diff since
    the run began, each work item's `follows`, test cases and `not_covered` per implement step, the open items still open,
    the system-test commands, and the release-verify lessons commit's exact message. A stage that ran without its field
    says "not recorded"; one that never ran adds no section. After a working-tree return the report says the lessons
    commit did not reach the source branch and asks you to commit the returned files (or an empty commit) with exactly
    that message, so the next run's intake quotes the lessons.
- The inner loop runs 8 stages in 5 phases instead of 17 stages.

  | Phase | Stages |
  |---|---|
  | Plan | step-plan, test-spec |
  | Validate existing | validate-existing |
  | Build | implement per step, test, document |
  | Verify | verify |
  | Carry forward | carry-forward |

  A run saved by the 17-stage loop (state version 4) is refused, with a reason.

  - **Every inner stage is an Until Loop.**
    - The packet says `INVOKE /until-loop NOW`, then the work, the exit conditions (the same words as Done when) and
      the repeat condition.
    - ShipLoop writes the stage's contract to `loops/<action>-contract.json` and, at complete, checks the receipt
      `loops/<action>-terminal.json` against the contract rebuilt from state.
    - `repeat` is no longer an inner outcome.
  - **step-plan** also records:
    - check commands (lint, type, build), or `check_na`;
    - an `expectations` list: works, absent or broken, each with a read-only check command;
    - per-step helper `skills`, which the implement packet prints.
  - **validate-existing** replaces baseline.
    - ShipLoop runs every expectation's check on the unchanged checkout. When all match, the stage is recorded without
      a packet.
    - A known small fix to a works expectation found broken is made here. ShipLoop commits it on accept, as its own
      commit.
  - **implement** is gated by lint on every step, and an Improve child reviews every accepted step.
    - The review uses `IMPLEMENT_STEP_REVIEW_FOCUS` with the Code craft rubric.
    - It runs even under `--planning-review none`.
  - **test** follows implement. It writes the test spec's cases, runs every recorded command and fixes until all pass.
    At done, ShipLoop:
    - runs the item's tests on its base (after any preparatory fix) and refuses a new test ID that passes there,
      unless `red_na: [{id, reason}]` names it;
    - runs every command on the candidate, holding the floor (base count and earlier runs);
    - accepts a deliberate removal declared in `retired_tests`.

    `shiploop red-check` runs the base check without completing.
  - **document** is recorded as not applicable when the item's diff touches no code or test path.
  - **verify** takes over:
    - from static-checks: the change inventory, the first-entry lint auto-fix and the review loop;
    - from integrate: the item commit.
  - **carry-forward** records a skill decision: `none | reuse | update | create`.
    - A created or updated skill must name an existing `SKILL.md` with name and description, and list its repeat
      evidence.
    - ShipLoop commits it.
  - **`complete --check-only`** runs a stage's script gates on a result without completing the action.
- Test and quality loops now allow 11 refused runs per action (was 7) before `done` is no longer accepted, and a
  check may fail after 7 genuine fix attempts (was 3) before the stage reports revise. The keepalive's
  no-progress release follows at 22 continuations (twice the refused-run cap).
  The fix-attempt rule is now the constant `shiploop_stage_spec.GENUINE_FIX_ATTEMPTS`, and a test pins every prose copy
  of the three caps to their constants; the static-checks paragraph of SKILL.md now says the 11th refused run.
- Packets now carry the knowledge home's architecture and spec-retire lines.

  - **Every inner packet** names its grounding files by absolute path: living spec, feature spec, environment,
    architecture and test strategy (`knowledge_home.grounding`). A missing or blank file is left out, and nothing is
    printed when there are none.
  - **plan and step-plan** say what architecture.md holds (`ARCHITECTURE_HOLDS`).
    - Keep every AD-<n> ID, and move a decision that no longer holds under '## Superseded'.
    - Name credential handling without secret values.
    - plan records each structural choice as the next AD-<n>; step-plan adds one for a structural decision and cites
      it.
  - **prepare** writes a missing architecture.md from the plan.
  - **The spec duty** numbers requirements R-<n> only: a structural choice is an AD-<n> in architecture.md.
  - **spec, plan and step-plan** state that a change to docs/shiploop/ losing an R-<n> or AD-<n> ID is refused.
  - **The plan packet** asks plan.md to begin with the living-spec pin (`Spec: docs/shiploop/spec.md @ <sha12>`).
  - **The handoff packet** states when ShipLoop retires the feature spec.
  - **The stages that write the home's README** link the feature list, not a feature spec.
  - **The stages from intake through plan** name earlier features.
- The knowledge home's fact files have named sections, the inner stages that find commands, facts and decisions keep them up to date, and ShipLoop counts the sections a close finds missing.

  - **Sections as constants** (`knowledge_home.SECTIONS`): `spec.md` has Requirements, Non-functional requirements and Retired; `environment.md` has Targets and runtimes, Commands, Skills (the repository's local skill directory), Access and accounts and Platform facts; `architecture.md` has Stack, Structure, Conventions, Interfaces and boundaries, Decisions and Superseded; `test-strategy.md` has Harnesses and suites, Commands, ID convention and Real-boundary checks. They are the one list: a packet is to quote them rather than carry its own, and a test pins that every heading a packet duty names for these files is in `SECTIONS`.
  - **Writer entries on the 8-stage graph** (`knowledge_home.STAGE_FILES`): research, step-plan, validate-existing, implement and test keep `environment.md` up to date; step-plan and implement also keep `architecture.md` (a deviation recorded as the next `AD-<n>`); carry-forward keeps `architecture.md` and `environment.md`. verify reads the architecture and writes nothing. A test pins every key to a stage of the graph, and another that every heading a packet duty or loop text names for one of the four files is in `SECTIONS`.
  - **A counted notice, not a refusal** (`knowledge_home.section_notices`): at the closes (prepare, test-spec, release-plan, release-verify), one line per file of the four that exists, has text and has anything to report (four lines at most a close), naming every section that file lacks or leaves empty. Each line starts `ShipLoop knowledge notice: `, names the file by absolute path first, the missing and the empty sections, that the close is accepted, and the one fix; the architecture file's line ends with what that file holds. A line counts a file, so the reference gives two counts by occurrence: files with `grep -o 'ShipLoop knowledge notice: '` and headings from the quoted names before each line's first semicolon. It prints at the close even when the script records another stage after it (test-spec, then validate-existing), it never blocks a close and never raises. A section counts when a markdown heading (`#` to `####` at the start of the line and outside a code fence, any case, trailing words allowed) starts with its name and has at least one non-blank line before the next heading of the same or higher level. Whether to turn the notice into a refusal waits for a live run that shows packets which quote the headings get them written.
- Packets state each fact once (owner, 2026-10-11: "the full packet file looks far too verbose ... consolidate the
  language and deduplicate").

  - **Shared rules.** A producer packet no longer prints COMMON, the requirement and reference-handoff rules, or the
    progress paragraph. One short **Rules for every stage** list replaces them. The long texts stay whole in the run
    reference file (`reference.md` #rules, #requirements, #progress). Improve, paused and blocked packets print a
    three-line progress rule instead of the paragraph.
  - **Removed duplicates.**
    - The Progress snapshot, which repeated the status block (report.html keeps it).
    - The second "Call this when done" callback.
    - The separate result-path line.
    - The "Owner:" line.
    - The four recovery prose lines; one Recovery command line remains.
    - The Improve line's repeated blocked sentence.
    - Test-source blocks for results that "Results this stage builds on" already lists.
    - The last transition's "read the durable state" sentence, and its empty evidence list.
  - **Run locators.** The 15 policy and guide lines print only when the packet's own text names one. Every other
    locator is reached from reference.md#policies through one line. The state, CLI, scratch, keepalive and SHIPLOOP.md
    index lines remain.
  - **Workspace return.** The return route (plan-return, review-return and the rollback route) prints only at
    release-plan, release-check, release and handoff. Every other worktree packet carries one "Execution checkout"
    line.
  - **Result template.** It is the same JSON in the same fence, laid out with one key per line and one list element
    per line. The step-plan template drops from 115 lines to about 25.
  - **step-plan.** Its duty is a numbered list, one item per result field plus the plan note, knowledge and evidence.
    - Step sizing, the test-facility and test-decision handoffs, the planning handoff and the design-basis text are
      folded into it.
    - The interaction and state-lifecycle text moves to the Interaction design guide.
    - An inline step-plan carries one optional Backchain audit line in place of the caller guidance.
  - **Shorter texts.** The inline preamble, the Until Loop duty paragraph and the pass-log rule are shorter.
  - **Size.** Measured offline on node-fix-bug, the inner loop drops from 431k to 270k characters, and its step-plan
    packet from 58k to 33k.
  - **Second pass.**
    - Four shared test texts are shorter, and each keeps its obligations: test facilities, test decision, the OUTER test
      plans and selected-case reconciliation.
    - Inline carry-forward carries the one optional Backchain audit line instead of the caller guidance and its
      contract budget.
    - An Improve child's packet prints the locators of the policies its review text names.
  - **Restored after main CI.** Step-plan item 7 again tells the model to reopen the plan's Namespace and data map
    (with the collision check), and to give a human-facing UI an ambitious, highly interactive design by default.
- An inner-loop stage's packet now states each thing once. Its head keeps the one `Goal:` line, and in place of the itemised done-when list it prints one line: "Done when: every exit condition in the /until-loop argument below holds; ShipLoop's gate checks the same list." The /until-loop argument is the only place that holds the stage's Work, numbered exit conditions, Repeat and (at test) the recorded command list. The loop contract does not change. Three things stay in the head. A step plan sent back keeps its extra condition as an `Also:` line, because that condition is not in the contract. If the argument cannot be built, the itemised list is printed there instead, still once. A parent packet that waits on an Improve child keeps its itemised list, because it has no invoke block. The test stage's lines after the argument no longer list the commands again. They print where the commands run, each command's floor numbered as in the argument, the red-check command and the refused-run tally. The eight inner duties and the shared loop duty lose the sentences that only restated the goal, the loop's Work, its exit conditions or Repeat. Every how-to rule, field shape, routing rule and refusal explanation is kept. In the offline node-fix-bug walk, the inner packets total 396,762 characters, down from 406,119.
- Every packet a model acts on (producer, Improve parent, paused, blocked or awaiting) now prints a **References** block right after its goal, done-when and Checked-by lines, and each path in it is defined once. The block has a global part that reads the same in every packet of a run. `HOME` is the knowledge home, with each file that has named sections and its headings, plus the feature list. `FEATURE` is this run's feature folder, with the files the stages write there. `RUN` is the run directory and `WORKTREE` is the execution checkout. A file that does not exist yet is still listed, marked "not written yet: <stage> writes it". Every file name comes from knowledge_home's own tables (`SECTIONS`, the grounding labels, `STAGE_FILES`, `FEATURE_LIST`, `feature_dir`). The block has a stage-local part too. An inner stage gets its **consult** note, printed from one navigator table, `_CONSULT`, shaped `{stage: ((file, heading), ...)}` like the planned `knowledge_home.READS`. An active packet also gets **Results this stage builds on**, which lists each earlier stage's accepted result and durable products (`stage_spec` reads plus one `_PRODUCTS` table). Examples are the step plan's plan section, the test spec's cases, validate-existing's check record and preparatory commit, each implement step's lint gate and Improve review, the test stage's base, candidate and mutation runs and loop receipt, and verify's change inventory, rerun record and item commit. Each is labelled `<item> <stage> <product>`, and planning results read "<stage> stage result". Each artifact keeps the same label and symbolic path in every packet. The rest of the packet's prose names files by these symbols: duties, knowledge lines, Checked-by and gate texts. A command the model runs verbatim keeps its absolute paths, and so does the /until-loop argument. This block replaces the knowledge grounding line, the duties' "Consult and cite" lists and step planning's "Current planning sources" list. The test and verify duties no longer restate what ShipLoop checks at done; their Checked-by line is the one place that says it, and it now also states the lint auto-fix refusal, the mutation rule and verify's floor.
- Each run now keeps a derived `reference.md` beside `context-index.md`: the run-wide rules, the blocked and outcome
  shapes, recovery, progress reporting, requirement rules, policies and guides, and the workspace return, in labelled
  sections that packets can cite as `reference#<anchor>`. `next` writes it for a run saved before it existed.
- At the final handoff ShipLoop checks that every requirement ID the run's feature spec (`docs/shiploop/features/<slug>/spec.md`) names is in the living spec (`docs/shiploop/spec.md`) and, when the run's commits reach your branch (an in-place run, or a fast-forward return), removes that file in a commit of its own, `docs(shiploop): retire <slug> spec: checked its requirement IDs against the living spec`; the commit goes back with the knowledge follow-up return, its message gives the recover command and the commit the plan was recorded in, and the branch's history keeps the last committed version (a squash merge drops it). The file stays after a working-tree return or a return that recorded no change, when the living spec lacks an ID it names or names none, when the file has uncommitted changes or was never committed, and when it is a symbolic link; ShipLoop prints one line saying which, and the handoff is never refused for the IDs or the route (a removal or list write that cannot be made leaves the handoff pending with the file's absolute path and the next step). The run's plan, test and outcome records stay. ShipLoop's knowledge commits now also write `docs/shiploop/features/README.md`, a list of the feature folders with commands that find a requirement ID in them (`grep -rlw`, `git log -G`, `git show` of a removed spec, the prepare commit's plan); it is derived from the tree, never makes a commit of its own, and a file at that path that is not ShipLoop's is left alone with a notice. The progress view shows a retired feature spec as Retired with its commit, not as a missing document. A knowledge follow-up return that fails after the retire commit alone no longer replaces the handoff guard's return commands with a dead end. A retried handoff whose result cites the feature spec that ShipLoop's retire removed is accepted (the evidence check counts that file as present). `workspace.return_kind` reads the route of the recorded return.
- step-plan now sizes its steps. Each step lists the criteria it satisfies (`criteria`) and the paths it changes
  (`paths`), and ShipLoop refuses a step plan when:
  - a step names no paths;
  - a step names no criteria while the item has criteria;
  - a step names an unknown criterion;
  - a step path is not one of the item's paths;
  - a criterion is served by no step;
  - a step changes only test files, unless every path of the item is a test file.

  The step-plan packet adds sizing directions. Each step is one behaviour-level change that a named check proves.
  Split a step that holds two separately confirmable behaviours, crosses a module or layer boundary, needs "and"
  between two outcomes, or is too large to recheck in one pass. Merge a step no check can confirm on its own into
  the step it serves. A single fix or mechanical rename is one step. The step-plan done-when line states the rule.
- Printing a done or halted run's packet no longer starts the progress observer. The observer had written
  `.progress.lock` and refreshed `context-index.md` in a run folder that a terminal recovery must leave unchanged.
- The test stage's done gate now runs a mutation check after the candidate run passes (owner decision 2026-10-11:
  "code tests after the build phase, not just run empty tests"). ShipLoop makes at most 8 deterministic one-token
  mutants of the item's changed product lines (comparisons, boolean literals, `+`/`-`, integer literals; comments and
  strings skipped), applies each alone in a temporary worktree of the candidate, runs the focused commands, and refuses
  done when mutants ran and none was killed. The refusal names each surviving mutant (`file:line`, the change) and counts
  toward the refused-run cap; `complete --check-only` runs it without counting. Every check writes
  `tests/<action>-mutation<N>.md` with each mutant and the kill count. The base run still counts a load failure of an
  added file as RED (on new code nothing can run on the base); the mutation check is what proves the assertions.
  Evidence: the Checkers run on 88d412e9 had every TC id "missing" on the base (load failure of rules.js) and its
  mutation score fell 0.86 to 0.66 against the 17-stage run (n=1).
- ShipLoop accepts terminal packets from the Until Loop 0.8.0 runtime (new keys `exit_checks`, `last_check_results`,
  `check_repairs`, `verify_script`) in its loop and standalone Improve checks. ShipLoop keeps its own 16 KiB contract
  budget as a ShipLoop policy; the runtime itself no longer limits state size.

### shiploop-e2e-audit 0.7.2

- The audit harness follows ShipLoop's 8-stage inner loop (step-plan, test-spec, validate-existing, implement, test,
  document, verify, carry-forward; 24 stages in all). The DAG replay oracle states the new stage lists and edges by
  hand, parks every accepted implement step for Improve under both planning-review options, and walks 24 stages with
  33 callbacks (28 in a `none` run, 44 with two work items). The old repeat-at-step-plan scenario became a repeat at the
  test-strategy checkpoint, and a new revise scenario checks that test refuses repeat and sends the item back to its
  step plan. Live lifecycle evidence no longer asks for a callback for a stage ShipLoop recorded by script
  (validate-existing with every expectation matched, a left-out test or document), and `complete --check-only` is not
  credited as a callback. `red-check` is a recognised ShipLoop verb; the behaviour capture's closed stage list is
  the new one, and its outcome list accepts `revise`.

### shiploop-run-review 0.2.0

- The stage catalog (`defaults/stages.json`) follows the engine's stage table again: system-test-author now reads test-spec
  (every item's latest test cases) and release-plan reads system-test-author (the system commands it recorded), the
  producers of what those stages' packets quote under the consumer contract.
- Run Review follows ShipLoop's 8-stage inner loop (step-plan, test-spec, validate-existing, implement, test, document,
  verify, carry-forward). The phases are now Understand, Specify, Plan, Build, Verify, Carry forward, System test and
  Release; `defaults/stages.json` is regenerated (every inner stage ends on its Until Loop's `loop-terminal`, and the
  catalog accepts implement's `improve: step`); an 8-stage run's `delivered.skill.assessed` comes from the last carry-forward
  visit. A saved 17-stage run is read with its own frozen catalog and phases (see the stage-models note).
- A visit with no packet reads as recorded by ShipLoop, not skipped: the page's legend, visit count, table, card list and the
  visit's Outcome line say "recorded by ShipLoop", and facts.md counts "N recorded by ShipLoop". The export keeps
  `stages[].skipped` and adds `stages[].recorded` from the engine's summary: "expectations matched" (an 8-stage
  validate-existing whose expectation checks all matched) or "not applicable" (a stage left out of the item); older exports
  without it keep the previous Outcome wording.
- Run Review counts an Improve packet's recovery label in either of its forms: the "Recovery command:" line printed
  through skill-craft 1.27.0, or the "Recovery command (...)" line that the packet dedupe prints after it.
- A run is read with its own stage model: `runs.stageModel` is `v4` for the 17-stage inner loop (every run saved before
  2026-10-10) or `v5` for the 8-stage one, and the page header says "17-stage run" or "8-stage run". A 17-stage run keeps its
  own stage catalog, purposes, exit checks, reader counts, phases (Build, Prove, Integrate) and phase 3-5 expectations from the
  frozen `defaults/stages-v4.json` (written to the page as `config/stages-v4` by `export.py --defaults`), its skill decision
  from skill-assess and skill-validate, and test-red's "meant to fail" note; every saved run exports as it did before the
  8-stage change, apart from the new field. A script-run card whose stage also has an Improve child now says so.
- Run Review reads a step slice (`test/shiploop_e2e/slice.py`, which writes `slice-result.json` instead of `result.json`) as a slice: the run document has `kind: "slice"` and a `slice` record (work item, stop, stage at the stop, the not-reached sentence); a slice that reached its stop is `finished`, a cleared or otherwise ended one `stopped`; its outcome is PASS or FAILED naming the failing verdicts; the stages the harness seeded read seeded, not skipped; system tests and release read "not reached (slice)"; the return, the release, the quality phase and outer-stage refusals are not measured with a reason that names the slice. The page and facts.md say "step slice", and a slice is compared only with other slices. Whole runs export exactly as before.

## 2026-10-10

### skill-craft 1.27.0

- Skills: improve 0.3.0-rc.12, shiploop 0.59.0, shiploop-run-review 0.1.4

### improve 0.3.0-rc.12

- Inside a ShipLoop run the commit policy points the child at the `improve-commit` command named in `parent-return.md` instead of `git commit`, and contributing commits are credited as `Learned-from: <commit ID> <what it contributed>` lines that ShipLoop checks.
- In a ShipLoop run, cite a commit that helped on a line of its own, `Learned-from: <commit id> <what it contributed>`: `improve-commit` checks that line against Git and writes the full ID into the commit, while a citation inside a sentence is not checked.

### shiploop 0.59.0

- At integrate ShipLoop now also commits the item's changed files of the docs path class (`references/path-classes.json`: Markdown, reStructuredText and AsciiDoc files, anything under `docs/`, `LICENSE*` and `CHANGELOG*`, test paths excluded) even when the step plan did not declare them, so the model no longer commits them by hand; a worktree run never commits a path the workspace excludes or protects, as plan-return does not. The document and integrate packets print one rule for the run: a worktree run says plan-return commits the other files, with the Return route line's own sentence, and an in-place run, which has no return, says to report revise so the step plan declares a file the product needs or to delete it. The integrate packet lists the files ShipLoop will and will not commit. Each test stage's case end states name only the outcomes that stage accepts: system-test-author and system-test record a case that cannot run as an open item with its due stage and continue (a case whose command system-test-author left out of `system_commands`; a recorded command that fails is still refused), and test-author, test-green and regression send it back to the step plan with revise; blocked is for when nothing else can proceed. Product-acceptance reads system-test-author's result, whose open items it carries in.
- Improve commits made through `improve-commit` now carry what the iteration learned: the message needs a `Key learnings:` line (or `## Key learnings`, or the label alone, each starting in column 1; `Key learnings: none` is the honest answer when nothing was learned), and a review that changed no file still makes no commit and is never asked for lessons. `Learned-from: <commit id> <what it contributed>` lines are optional and checked: Git resolves each ID to a commit reachable from HEAD, and a unique prefix is written into the commit as the full ID. `improve-commit --remote-change` records a change to a remote system that left no file change as a commit with no files (the message needs a `Remote change:` section; without the flag the section changes nothing and the command says so). Every refusal puts the fix and the exact next command on its first line (the bound child is never told to run `improve-complete`; that is the parent's), and the Improve import refusal for uncommitted edits now names `improve-commit`, the `improve-complete` command to run again and the `--no-commit` exit with that command, instead of telling the child to run `git commit`. Commits ShipLoop makes now use `--cleanup=whitespace`, so a `## ` heading in a message survives a `commit.cleanup=strip` setting. The commit rules live in `parent-return.md`, which the frozen Improve contract already names.
- The packet that asks for `improve-bind` is kept in its own file, `packets/<action>-improve-bind.md`, so the later `improve-start` packet (`<action>-improve.md`) no longer overwrites it and both can be audited. The navigator reference's recovery paragraph names both files.
- Packets now say what the gates refuse, up front. release-verify's Checked-by and Done-when name the knowledge files and the outcome.md sections its close requires. The loop stages (test-green, regression, static-checks) prefill the terminal packet path in the result template, print the loop's exit and repeat conditions and the Start and Receipt lines after the status block and any milestone narrative (inside the head, so the status hook still shows the narrative), and say the path must be in evidence_refs for done; a blocked or revise result may keep that prefilled path before the loop has written it. test-author prints the focused commands, their IDs, minimum counts and the whole-word ID rule; baseline prints its commands and the discovery baseline result; test-red names red_na; every template says to use each key once. Inner stages no longer offer replan. A bound Improve packet prints the commit command right after improve-start, and an Improve child that reads the release guidance assesses and records a release; no Improve packet says it may perform one (no Improve child runs at the release stage). The progress snapshot shows implement as in progress while planned steps remain. With planning_review none, the spec and test-strategy review-focus lead states only the duty and no longer names Improve. A bound Improve packet's commit line now states the message rules improve-commit enforces: a `Key learnings:` line (`Key learnings: none` when nothing new was learned), an optional `Learned-from:` credit, a `Remote change:` line with `--remote-change`, each on its own line in column 1, and it ends with the command. The planning Improve packet points at the improve-commit command in parent-return.md, and every Improve packet's Checked-by line says what improve-commit and improve-complete refuse.
- Packets now state the rules that real runs were refused for. The step-plan result template prints neutral placeholders instead of a README example that outputs copied into products nobody asked for. The step plan asks for the ids you will title the cases with and lists the `check` suite; test-spec says to title each case with those ids and where the cases go. The system-test-author, release-plan and step-plan packets say a check row carries no ids or min_tests, and the system-test-author template shows one. The spec and test-strategy packets restate the planning review conditions their Improve child applies to them, test-strategy states the whole-word id rule and, for a UI the request names, the choice between a case that drives it through its user interface (for example in a browser) and an outcome recorded as unverified, the plan packet states the exact assumption fields, and the knowledge-home lines name the close that refuses a file left unwritten (prepare now separates the files earlier stages wrote from the one it writes, and says where readiness is recorded; the Checked-by line of a close that also requires earlier stages' files says "this stage's close requires").

  The step-plan duty's `check` example no longer names a README and a flag (a verification run still built a README nobody asked for); it is a generic search for required terms in the file a criterion requires.

### shiploop-run-review 0.1.4

- A run whose Improve children left only `packets/<action>-improve-bind.md` files (each stopped before its card was bound) now says so under `unmeasured.improvePackets`, instead of saying they left no `-improve.md` file.
- The stage defaults (defaults/stages.json) follow the stage table: the Integrate goal now says the item's candidate is assembled in the execution checkout.

### skill-craft 1.26.1

- Skills: shiploop-run-review 0.1.3

### shiploop-run-review 0.1.3

- The Run Review page and export read better and say more: a counter is no longer "1 refusals" (the header line, the Refusals card and
  the run facts count in the right number, as does the exporter's "1 child, 1 review pass"), a size over 1000 KB prints in MB, and the
  unreturned product's checks are exported and shown as how many pass in the worktree ("passes 4/4 checks in the worktree") instead of a
  yes or no. A run exported with the earlier boolean `worktreeChecks` is refused; export it again.
- The Run Review page says each figure once. The header line holds the release, the time and the planning-review mode; refusals, Improve and
  context stay on their cards; the run detail drops the elapsed time, context peak and compactions the cards already show; the Improve packet
  counts and the packet reads moved from the cards to the Fidelity card, which now sits with the Fresh starts and Quality cards after the stage
  cards. A refusal line no longer carries the run's absolute folder (it reads `<run>/.shiploop-runs/...`).
- A stage card opens and closes in place: tap a row in the stage list and its card opens directly under it (every row has a chevron at its right edge, pointing down while it can be opened and up while it is open,
  and the open row is highlighted); tap the row again, or Close, to collapse it. A click on a column of the picture opens the matching row, and Previous visit
  and Next visit move the open card down the list. Keyboard focus stays on the row.
- The Run Review export and page now show four more records the E2E harness writes. How the harness classed the ending (PASS, FAILED,
  BLOCKED or STOPPED, with its grounds) is a line under the run header, as a record and never coloured as a verdict. The build under test
  (plugin hash, prompt hash, host build) is another line, with the harness's reason for any it could not measure. An Environment card
  shows the tools, the browser and the other runs that shared the machine while this one ran, and a chip in the header says so, since
  minutes measured beside another run are not clean. A run that did not pass shows, as information only, how many of its checks pass in
  the worktree it never returned and what each failing check printed. All four are absent for a run exported before the harness wrote them.
- The Run Review export and page now show how ShipLoop was carried in a run. A new Fidelity card reads the harness's fidelity block: how each accepted
  stage's exit was evidenced (a script record, an Improve review, a cited file, notes, the model's sentence alone), what ShipLoop's script checks
  recorded, the model's edits of ShipLoop's own files and its refusals by stage, each heuristic list printed with the harness's own limits text.
  The exporter now scores the Improve child's packets for Goal, Done when, Checked by, Output and Recovery, shown on the Improve card next to the
  run's release (Goal and Done when are printed from skill-craft 1.25.0, so an earlier release reads 0 for them by design). A run without these
  records exports and renders as before, and says why they are not measured.
- The Run Review export and page now show three more things a run recorded. Fresh starts: each time the model lost its context (a
  compaction or a new host session), the calls and seconds it took to re-ground, with the failure and rewrite counts shown as lower
  bounds, and a marker on the visit that followed; a run that could not record them says so instead of reading "none". Quality: the
  mutation ratio with its operator, the survivors, the held-out checks and the model's writes to its own memory. A visit's context
  now follows the harness's stage rows, not the host, so a Grok run shows its calls and peak tokens.
- The Run Review export and page now say what the run delivered. A `delivered` object records whether the product was merged back into
  the branch the run started from (and between which commits), or that it was not and which branch holds it; the kept files sorted into
  source, tests, documentation, ShipLoop's own records and skills; how the tests last ran (the widest command of the release-verify
  visit, never a sum); and the skill and release stages' own words. A new "What was delivered" card shows it, merge line first. A part the
  workspace records cannot give is absent with its reason, never a zero; an export from before it gets no card.
  A run that never returned says so once ("Files kept: not measured ...") instead of on every row, a red run at test-red says its new tests are meant to fail there, files in system/ count as tests, and a stage summary names a file by name, never by where the run lives.
- The Run Review page now turns references in Claude's review text into links: an existing finding or option id jumps to its card,
  a repo path, a commit and a spec clause S-n open on GitHub, and an https URL opens itself. The address is
  `config/page.repoUrl` (in the defaults; `--check` refuses a non-https one; with none the repo references stay text). Run content
  such as stage summaries and packets is never linked: those paths are files on the machine that ran the case.
- Every Run Review export now also writes `run-review.html`: one self-contained, read-only file with that run's documents (the
  run, its packets and Backchain loops, the starting expectations and settings) embedded in the page and a small stand-in for the
  database, so the review of one run opens from disk with no network and can be kept as a reference. It says it is a static copy of
  one run, not the shared record, and writes nothing. `export.py RUN_DIR --no-html` skips it.
- The Run Review export and page now say how a run ended. A run the harness ended while ShipLoop still read active is `stopped`,
  with the stage it never accepted and the minutes and turns that cost, shown as a "How it ended" card and a hatched last column in
  the picture; a blocked run shows its question and options; the listeners the harness ended and whether the unreturned product
  passes its checks in the worktree are recorded. A run resumed on another host lists both hosts and exports no mixed calls, context
  or compaction figure, and a visit with no model call no longer prints "0 calls". The default run name carries the case, and the
  text about refusals, per-visit context and `Checked by:` lines now matches the runs.
- The Run Review export and page now show more of what a run recorded: each visit's script checks (the records ShipLoop kept, how
  many passed or ran red, and where release-verify ran), the outcomes a result left unverified with their owner and due stage, a
  Claude run's wrapper scripts and packet use (so glue reads as a lower bound), and the planning window with its two clocks, where
  it closed and its Improve share. A stage that only ran `backchain-check` now reads as a graph check instead of "no loop".

## 2026-10-08

### skill-craft 1.26.0

- Skills: shiploop 0.58.0

### shiploop 0.58.0

- ShipLoop now creates the directory of a bound Improve child's opening file whenever it prints the packet, so the printed step "write the opening file" needs no `mkdir`. A run bound earlier gets the directory on its next `next`.
- The return-route sentence that every worktree packet prints now says, right after its first sentence, that plan-return commits files left uncommitted, so a run commits nothing by hand for the return except a file plan-return reports as not committed (a credential-like one). The old wording could be read as needing a hand commit before the return, and its working-tree fallback now reads "still leaves a file uncommitted".
- ShipLoop now also refuses a test run of an item's command that ran fewer tests than the most any run of that command it accepted for the item has run since the item's latest step plan, so a test removed or newly skipped to pass is no longer a pass. The test-author probe sets the first number, test-refine (whose duty is to explain removed cases) is not held to it and restarts it, and a revised step plan starts it again; the refusal names both numbers and the stage's real exit, and the packets state the rule.
- The test-strategy stage's "Done when" list, which every run displays, now asks that each case needing a host tool (a browser, a device, an account, a service) names it and cites the output of probing it now against a stand-in while the product does not exist, and that only a failed probe is recorded as the access gap. The probe's how stays in the stage duty.
- ShipLoop's refusal for a listed test ID that the runner prints only inside a longer name (a test titled `TC-4a` for the listed `TC-4`) now states the whole-word rule, quotes the line and shows the rename, instead of telling the model to print test names. The rule is also stated once in the step-plan, test-author, test-red and test-loop packets.

### skill-craft 1.25.0

- Skills: shiploop 0.57.0

### shiploop 0.57.0

- Refusals a model reads through `head` or `cut` now say what to do on their first line: a knowledge-close refusal puts "Before <stage> is done, write:" and the absolute paths there, an invalid return-plan status names the allowed values and the `review-return` verb, and `backchain-check` tells a Markdown candidate that it must be the plan graph JSON and where that shape is defined.
- The one-pass plan packet now says the whole Backchain child is the host's choice (nothing refuses a plan without it, and ShipLoop cannot see whether it ran), that the dependency audit is not optional, and that the result's summary names the route taken. A `backchain-check` on a candidate that is not JSON now points at Backchain's "Plan document shape" instead of leaving the model to read the checker's source. The text describes today's behaviour, not a policy: requiring the child at plan stays open pending the Backchain validator comparison, and plan-stage timings are not comparable across this version.
- A stage whose done runs a knowledge check now lists every file that check requires, so test-spec and release-plan no longer meet a refusal for a file their packet never named.
- The packet a model re-reads while an Improve review runs now states the stage's goal and the Done-when conditions the review holds the result to, and the producer's packet says its Done-when is what that review checks.
- `init` and `workspace start` now record the Improve card installed beside ShipLoop when `--improve-skill` is not given and the card validates, so the first Improve bind packet prints a real path instead of a template. Where no installed card validates, the packet prints a marked blank and the place ShipLoop looked; `--improve-skill` still wins and `--planning-review none` still requires it. `--help` now says the same: the flag is required with `--planning-review none`, and a stage run without it records the installed card.
- The output of `workspace plan-return` and `review-return`, and the refusal of a blocked `return`, is now held to one print limit in all, not one per path list, so a very long list is cut at a path and the rest counted while the last line stays the next command. `review-return` counts the paths it excluded and no longer lists them a second time beside the excludes a review decided.
- Every isolated-run packet now states how the return will go, taken from `workspace.md` (replacing a generic sentence that was wrong for a clean start), the release-plan and release-check packets print tested rollback recipes for each return kind, and `review-return` reports the expected return once nothing is undecided, by the same rule `return` follows. The release-plan and release-check duties tell the model to write and verify the rollback against that route.
- `review-return` now refuses an absolute, `..` or empty `--keep`/`--exclude` path the way it refuses an unknown one, with the undecided paths and the command, and its rule says the paths are relative to the execution checkout. The rollback recipe for a fast-forward with later commits says it also undoes what those commits changed, and points to the diff recipe for keeping their work.
- New `shiploop workspace review-return --keep PATH... --exclude PATH...` records the return plan's keep/exclude decisions, so a model no longer hand-edits `return-plan.md`. `plan-return` now prints the tally, every undecided path and the exact command (and keeps the decisions already recorded for the same path on a fresh plan), a blocked `return` names the undecided paths and the verb on its first line, and a stale plan names `plan-return` as the next step.
- ShipLoop now creates the run's `notes/` directory beside `scratch/` when it prints a packet, so the pass log every packet names can be written (and an `evidence_refs` entry for it resolved) without a `mkdir` first. The log itself is still the model's to create.
- The `notes/` row of the state-files reference now says ShipLoop creates the empty directory when it prints a packet, and that the notes and the pass log stay the host's to write.
- The step plan no longer tells the model to mark a criterion `Confirm by: unconfirmable here` in `criteria`, a shape the gate refuses; it says a condition no command can confirm is recorded as an open item in the summary, and the refusal for an uncovered criterion names the same exit. The implement Done-when no longer names a `Confirm by` field that an item without tests does not hold.
- The test-strategy duty now says a host-dependent tool (a browser, a device, an account, a service) is probed against a stand-in, such as a one-line page opened by `file:` URL or from a throwaway static server, when the product does not exist yet; a request to the product's own address says nothing about the tool.
- Intake, discovery and research ask for a recorded default or open item instead of a person or a suite that may not exist, integrate no longer asks the model to commit (ShipLoop does) and an inline run no longer reads about bound chains, and the Improve packet no longer calls its own review independent.
- A done product-acceptance result now lists, in `unverified`, each request outcome no executed check observed, with its reason, owner and due stage (an empty list says every outcome was observed). ShipLoop refuses a missing list, an incomplete or placeholder entry and a due stage that is not a later stage, and prints each entry at its due stage, the whole list at handoff and a table in the report.

### skill-craft 1.24.0

- Skills: shiploop 0.56.0

### shiploop 0.56.0

- The Checked by line of a stage with no script-run check no longer says nothing automatic runs. It says ShipLoop refuses a result with a mechanical fault (no outcome or summary, an absolute evidence_refs path that does not exist, an explicit credential pattern, and at plan, step-plan, document, system-test-author, release-plan and the knowledge closes the extra faults those stages refuse, including a skill file beside a recorded skill_na at step-plan and a skill file changed after the step plan recorded skill_na at document), that a refusal does not advance the run so the fix is to correct the result and run the same complete command again, and that ShipLoop does not judge the work.
- The run narrative's Pace row now states what was recorded, the steps accepted and the time they took, and no longer adds an "about N min left" forecast. The forecast was an average of unequal steps and read 2.4 to 6.8 times too short after the second step of five recorded preparations. `references/status-display.md` shows the new row.
- The pass-log line in every packet and in the run context index is now one conditional rule that stays true whether or not the log exists: create it when the pass starts, append after each pass what you checked and what is left, and after a reset open it first if it exists. The durable-files reference now says which source is authoritative for the notes, inbox and results copies and for test commands.
- In an isolated run, `release-verify` now runs the consumer checks `release-plan` recorded in a clean copy of the result the workspace return delivered (read from the return receipt into `consumer-check` under the workspace root, never from or into your checkout), so a check that passes only because of a file the return excluded, an ignored file or a later commit is refused with the copy's location, its usual causes and the stage's one exit, `replan`. When no return has been made yet the checks run in the work area as before, and the packet, the test record (`observed`) and the handoff say that they did not observe your checkout. When the return state cannot be read (a corrupt receipt, a busy workspace), no command starts: the attempt is `could-not-run`, which does not count as a refused run, and the reply says so instead of blaming the item. In-place runs run where they always did, in the checkout, and now also record that in the test record and report it in the handoff. Every run's handoff packet carries one `Consumer checks (release-verify)` line saying where the checks ran, or that `release-plan` recorded none. The `release-plan`, `release-verify` and `handoff` duties, SKILL.md and the workspace lifecycle card say where the checks run and ask for paths relative to the directory a command starts in, checks that bring what a fresh consumer needs, and no writes into your checkout.
- A work item sent back to its step plan now gets a packet that names its previous step plan and the result that sent it back, and asks for an amendment rather than a new plan: criteria, steps, paths and test commands the evidence does not touch stay as written, and the summary says which rows are new or changed and which are carried over. No state, protocol or gate change.
- A done step-plan result may carry `skill_na`, the reason no repo-local skill is selected, created or changed for the item: ShipLoop then records skill-assess and skill-validate as not applicable to that item, with a history row and a result file whose text starts "Not applicable to this item" and carries that reason, instead of issuing them. A step plan that lists a skill file in `paths` is refused with `skill_na` (at `complete` and at `improve-complete`), and `document`'s done is refused when the item's real diff touches a skill file; without `skill_na`, or after either refusal, both stages run as before. The skill-file lists are the new `skill_surface` data in `references/path-classes.json`, not a path class.
- A result file that does not parse (no shiploop-state fence, invalid JSON, an unterminated fence or a duplicate key) is now refused as a rejected request, with the file path, the parser's reason and the instruction to fix the file and run the same command again. It no longer gets the lost-state recovery text that told the model not to infer a next action; real storage faults keep that text.

### skill-craft 1.23.0

- Skills: shiploop 0.55.0, shiploop-e2e-audit 0.7.1, shiploop-run-review 0.1.2

### shiploop 0.55.0

- The test stages now state when a test case is finished: a case ends validated (executed, and the observation matches), validated another way (the first method could not observe it, so the method changed and the new one was executed and passed, with what changed and why), or unachievable (a named reason and the requirement it leaves unverified, reported as blocked with `blocked_by access`, or revise/replan when the plan is wrong). A case written but not run, or recorded as not run, is not an end state. The rule is in the Test consideration of test-author, test-green, regression, system-test-author and system-test, and the system-test-author duty asks it to run each system command once while authoring.
- A test runner recorded as suite `check` is still counted: when a check command's output shows a runner summary, the record carries the counts and a zero-test run is refused (`no-tests`) instead of passing on its exit code. The test-strategy duty now asks for a capability probe of a host-dependent tool (for a browser, load a local page and read its title back, not the version) and for a failed probe to be recorded as an access gap with the requirement it leaves unobserved.
- The README now opens with ShipLoop's main tenet: context can be cleared or compacted between any two stages, so every packet restates what its stage is for, how it operates and how its result is checked, even when the previous packet said so too. Only repetition inside one packet is waste. No behaviour changes.
- The stage `select-work` is now `get-next-work-item`, in the stage table, the packets, the status and report labels, the references, README and SKILL.md, the dry-run graph and the audit harness replay. A run saved under the old name is refused with a message that names both names and says to start a fresh run (one supported version; no mapping). Committed history that records the old name (baselines, evidence files, journals) keeps it.
- A system command row may be marked `"host_dependent": true` (its cases need a host tool: a browser, a device, an account, a service). At `system-test` ShipLoop then also runs the accepted regression commands and refuses when any of that row's `ids` is shown, run or failed, in their output, with the remedy to give the case its own opt-in command or make it skip unless an opt-in setting is present. The system-test-author duty and SKILL.md say so. This is the script check behind the settled-fact line from the earlier test-strategy change: a delivered repo's plain `node --test` that needed macOS Chrome passed every gate.
- A packet printed while an Improve child owns the action is now written to `packets/<action>-improve.md`; the producer packet stays at `packets/<action>.md`. Before, the child's packet overwrote the producer's at the same path, so after a run the producer packet of every reviewed planning stage (spec, test-strategy, plan, step-plan, test-spec) could not be audited (10 of 46 visits in one real run).
- The test-loop and quality-loop duties no longer tell the model to save each returned packet to a "printed latest-packet path" and to write the terminal packet itself; the packet prints a receipt the runtime writes and says not to touch it, so the two now agree (the runtime's receipt carries `next_argv` for a resume). The plan duty asks each work item to state its module format and loadable seam, and the test-strategy duty asks the plan to say which test ids each command may print and to keep a host-dependent case (host browser, device, account, service) out of the project's default test command, after naming and probing its tool.
- The test counter now reads `node --test` (spec and TAP reporters, colour codes stripped), so `min_tests` is enforced and a test file that fails to load reads as zero tests instead of a failing test that ran. A test counts as skipped only by its runner's own marker (a skip glyph, `# SKIP`/`# TODO`, pytest `SKIPPED`, unittest `... skipped`, go `--- SKIP:`), never because its title contains `pending`, `skip` or `todo`; a TAP `# Subtest:` announcement no longer shows an id as run. The refusal text and the test-strategy packet name the node reporters that work (spec, tap) and the ones that do not (dot, junit). README and SKILL.md corrections: no packet or hook clears the conversation, `skill-assess` is the reuse/update/create decision, the default one-pass Backchain loop and `--planning-review` are described, and the test loop has no iteration limit.
- Every producer packet now has a `Checked by:` line under its Done-when list: the script checks ShipLoop runs when the stage reports done (lint gate, test-loop terminal packet and rerun, red probe, quality-loop terminal packet), or, for the stages with none, that nothing automatic runs beyond the result's form and the model confirms each Done-when condition. The Improve-phase packet gets a `Checked by:` line naming the `improve-complete` callback and what it validates and imports. A new hermetic suite, `shiploop-packet-completeness`, renders the real packet of every stage and every Improve-phase packet from a cold read of `state.md` and checks the five things the main tenet asks of a packet: what the stage is for, how it operates, how its result is checked, what it must produce, and how to recover.
- Two writes no reader used are gone. The lint pass no longer writes a `.err` log per tool call (stderr is quoted in the lint report) and writes the `.out` log only when the report cites it as a byte-exact copy; a real run had 72 such files, all empty and never opened. The context index no longer points a cleared model at a `-latest.json` loop packet that nothing writes; it points at the loop receipt the runtime writes.

### shiploop-e2e-audit 0.7.1

- The publication/freshness preflight now reads skill-craft's one-plugin layout: the released ShipLoop and Improve are the copies under `plugins/skill-craft/skills/<leaf>`, the catalog has one `skill-craft` entry whose version is the bundle's, and each skill keeps its own version. Before this, every live case was refused at the preflight with `required-package-tree-is-missing`, because the gate looked for a `plugins/<leaf>` per skill that the repository no longer publishes. A repository or catalog in the old per-skill layout is refused, not read.
- The replay oracles (`dag_replay`, `behavior_capture`, and the replay test) name the renamed ShipLoop stage `get-next-work-item` instead of `select-work`; no other behaviour changes.

### shiploop-run-review 0.1.2

- The Run Review exporter and page follow the engine's rename of the stage `select-work` to `get-next-work-item`: the phase table, the page's stage flow, the stage catalog (`defaults/stages.json`, regenerated) and the stage card name it `get-next-work-item` ("Get next work item"). The old name stays in one alias table, in the exporter and the page, so exports of runs of ShipLoop 1.22.0 and earlier, the committed evidence and the page's database still render, in the same phase and with the same catalog entry. Merge this change together with the engine's rename: against an engine that still names the stage `select-work`, the catalog and phase-table tests fail by design.
- The export reads the engine's new packet layout, in which an Improve child's packets go to their own file `packets/<action>-improve.md` and the producer packet that was sent stays intact in `packets/<action>.md`. A visit with both files gets its producer packet document as before and a second document `<runKey>--<action>-improve` (`kind` `improve`), and its stage row gets `improvePacketBytes` and `improvePacketDoc`; the packet checklist (`carried`) is read from the producer packet, so a reviewed stage's checklist is now a real one. A run of the old layout (ShipLoop 1.22.0 and earlier: one file per action, the child's packet replacing the producer's) is read as before and its visit keeps the `packetImprove` mark. `facts.md` counts both. SCHEMA.md documents both layouts and points to the E2E session's record register of 2026-10-07 as the place where record kinds are classified.
- The page's Specify expectation (`phase-1`) keeps its original sentence and now also says what the engine does under each `planning_review` mode, in the words of the SPEC's S-10 carve-out of 2026-10-05: `stage` starts an Improve child after each of the five planning results, `none` starts none and accepts each result without a review loop (the spec and test strategy are then committed unreviewed), and the Improve children after `system-test-author` and `release-plan` and the last `carry-forward` start in every mode. A `none` run is no longer read as a defect of Specify; until the default changes every new run is `stage`, so the added text describes the exception. The change is a revision recorded in `defaults/expectations.json` (finding o44, option a26); a page shows it after the defaults upgrade (`export.py --defaults --live`).
- The run export now records the plan and how the run went through ShipLoop's steps loop, and keeps each visit's packet text. A run document gains `workItems`: per work item its `stepPlans`, `loops` (the first pass plus one per accepted `revise`), `revises`, `repeats`, `implementVisits` by outcome, and the steps of its latest accepted step plan with the implement visit that executed each (`null` for a planned step no visit executed), plus the run's `stepsPlanned` and `stepsExecuted`; each stage row names its `workitem`, `loop` and, on an implement visit, its `step`. All of it is counted from `state.md` history and the accepted results, and a run whose records cannot tell (a seeded plan, the ask-agent route, a step plan with no readable steps) omits the number with its reason in `unmeasured`, never a 0. A new `packets` collection holds one document per visit with a packet file (`<runKey>--<action>`: size, sha256 and the text, cut at 150,000 bytes on a line boundary when longer); it is written under `docs/packets/` and listed last in `writes.json` for upload in batches of its own, and it is never part of the committed `review-export.json`. SCHEMA.md and SKILL.md document the fields, the definitions and the upload.
- Step 1 of the Run Review page gains a "Plan and execution" panel below the six cards: one row per work item with its title, a "steps loop once" or "steps loop x2" badge, a counts line (step plans, implement visits and their outcomes), and one cell per planned step, filled with its visit number when an implement visit executed it and outlined "not run" when none did, with the step tasks in a collapsed list and the run's "Steps planned N, executed M" line; a run whose document has no `workItems` reads "Not measured" with the exporter's reason, never 0. Tapping an item shades its visits in the picture; tapping a step selects the visit that ran it or says it was never executed. A tapped visit's detail names its work item, steps-loop pass and step, and gains a "Packet" box that reads the visit's `packets` document with one on-demand get when opened (the page never subscribes to the collection), shows it in a scroll box with Copy, its size, digest and any truncation, and says "packet not uploaded for this run" when the document is missing. The page needs one republish.
- The run export now records the run's `planning_review` option (ShipLoop 1.22.0) and says what it means for the Improve numbers. A run document gains `planningReview`, the value `state.md` recorded as written (`stage`, `none`, or any other value shown verbatim) and `not recorded` when the key is absent, never a default, and, only for a `none` run, `improveScope` ("planning stages skipped by design (planning_review none)"): under `none` no Improve child starts after spec, test-strategy, plan, step-plan or test-spec, so the run's Improve totals stay what its `improve/` directories hold and are no longer read as a missing measurement. `facts.md` gains a "Planning review option (state.md)" line and the Improve line carries the scope. The page's run header prints `planning review: none` (nothing for an older run, so it reads as before) and shows a chip on a `none` run; its Improve card keeps the measured passes and minutes, prints "no Improve at planning stages (planning_review none)" and no share of elapsed; and the detail of a planning visit in a `none` run says "Improve: not run by design (planning_review none)". SCHEMA.md documents both fields and the `general.review.json` bundle for findings that belong to no single run, and SKILL.md says that a finding spanning runs goes there. The page needs one republish.
- Step 1 of the page now shows a stage card for each visit: tap a column of the picture, or a row of the new "Stage cards" list below it (one row per visit with its stage, purpose, outcome, exit-check chip, minutes, packet size sent, result size written and how many stages declare reading it; a run of skipped visits is one row "xN skipped"). A stage is named by its stage name with the hyphens as spaces and the first letter upper-cased ("Get next work item"), with the raw name as the tooltip and, when it differs, as secondary text. The card has three labelled blocks. Sent: the stage's purpose and exit-check kind (script-run, review loop or model judgement, with the reason), the packet size, a tick or cross for each of seven items the packet text carried ("not found in the packet text" is a statement about the text, not about what the model needed; a visit that started an Improve child says its packet file is the child's and shows no checklist), the packet head (the first 12 non-empty lines, loaded on demand with the same single read as the Packet box) and the Packet box. Done: outcome, minutes and share, work item, steps-loop pass and step, the item's revise count, Improve passes and minutes, refusals ("not recorded per visit" with the run-level figure labelled as such) and context. Written: the result summary, whether the result file exists and its size, and the stages that declare reading it, labelled "declared by the stage spec" (the engine records no observed reads, so none is shown). Older run documents render with whatever fields they have, naming nothing as zero. The page also resolves `select-work` and `get-next-work-item` to one stage. The page needs one republish, and `export.py --defaults --live` writes the stage catalog (`config/stages`) the cards read.
- The stage card follows the engine's two packet files per visit. When a run's row has the Improve child's packet document, the Sent block shows its size and a second closed box "Improve child's packet", loaded on demand by the same single read and cache as the Packet box; the packet checklist beside it is then a real one for every reviewed stage. A run of the old layout (ShipLoop 1.22.0 and earlier) still says its packet file is the Improve child's and shows no checklist. The packet head on the card now starts at the first line beginning "ShipLoop navigator |", so its twelve lines show Goal, Done when, Checked by and the callback for an inline run instead of the delegation preamble; a packet with no such line shows its first twelve non-empty lines as before. The page needs one republish.
- The export now holds what the stage card needs. Each stage row may carry `summary` (the accepted result's summary, cut at 300 characters with `summaryTruncated`), `resultFile` (whether `results/<action>.md` exists), `carried` (which of seven labels the visit's packet text held: where, purpose, operates, checked, produces, recovery, inputs, read from the whole packet file; `checked` is also found by a line starting `Checked by:`, which a later engine prints) or, for a visit that started an Improve child and so keeps only the child's packet, `packetImprove`. A stage catalog, `defaults/stages.json`, is generated from the shiploop skill's stage table by `export.py --stages` (purpose, exit check, completed-by runs, readers; a test fails when it drifts from the table) and written to the page database as `config/stages` by `export.py --defaults`. The exit check of a stage is `script-run`, `review loop` or `model judgement`, by a rule that reads the stage row's own fields and the run's `planning_review` mode. `select-work` and its coming name `get-next-work-item` resolve to one phase through one alias table, so old evidence and new runs both read. SCHEMA.md documents the catalog, the rule, the aliases and the packet checklist, with the markers as the packets of every run on disk showed them; `facts.md` counts the labels.

## 2026-10-06

### skill-craft 1.22.0

- Skills: shiploop 0.54.0, shiploop-e2e-audit 0.7.0

### shiploop 0.54.0

- New run option `--planning-review stage|none` at `init` and `workspace start`, recorded as `planning_review` in `state.md` like `--backchain-passes` (default `stage`). `stage` starts an Improve child after each of the five planning results (`spec`, `test-strategy`, `plan`, `step-plan`, `test-spec`), as every run did before, and no packet changes. `none` starts none: those five results are accepted on ShipLoop's own checks at `complete` and the graph advances, so the planning window no longer includes five reviews. The children after `system-test-author` and `release-plan` and the last `carry-forward` start in both modes. In a `none` run the packets say so (the Improve line, the plan and step-plan duties and the shared handoff sentence name only the stages that hand off), the plan child's `improve-reconcile` route and plan-time experiments do not exist and are not printed, the spec and test strategy are committed to `docs/shiploop` when each is accepted with no review after, and the first Improve child is the last item's `carry-forward`, so a `none` run names its Improve card at the start: `init` and `workspace start` refuse `--planning-review none` without `--improve-skill=<absolute selected Improve SKILL.md>` and resolve it there (the first item's quality and test loops read the card, and no earlier child binds it). The inline step directive and the interaction guide no longer say a step or handoff is reviewed. `--planning-review none` with `--backchain-passes none` leaves no model-run second look at the plan graph; it is documented, not refused. A retry of `init` or `workspace start` cannot change the option and no verb changes it mid-run. A saved run without the key is refused with the fresh-run hint: start the request again in a fresh `--run-dir` or `--workspace-root`. `graph-dry-run` takes the same flag and simulates the selected schedule.
- `test-author` is now script-checked: on `done` ShipLoop runs the item's focused commands once and accepts only a run in which a test ran. Exit 0 needs a counted test (at least `min_tests`) with every listed ID shown; a non-zero exit needs a failing test inside a test. A run that stops before any test runs, for example because a file the tests load is missing, is refused at `test-author` with the rule for fixing it: create the smallest loadable placeholder at a path the step plan's `paths` names, or load it inside the test so a missing file fails that test and not the run. A unittest module the loader cannot import (`unittest.loader._FailedTest`) now counts as no test run, so the probe refuses it without listed IDs, and `test-red` and `test-green` read it the same way; a command that also runs a failing test, with a module that cannot load and no ID listed for it, is still accepted. A refusal for a run in which tests did run no longer says none ran (header "did not show a usable test run"; a passing run with a non-zero exit is told to exit 0 or fail inside a test). Before, only `test-red` could notice, and it forbids product edits. After 7 refused runs `done` is no longer accepted and `revise` is the named remedy; a command that reaches no verdict (timeout, cannot start) refuses without counting; `revise` and `blocked` are never gated. The `step-plan` duty gains one generic sentence and the `test-author` duty two, about where a loadable file comes from. Other packets are unchanged.

### shiploop-e2e-audit 0.7.0

- The DAG replay and the workflow review read ShipLoop's new run option `planning_review` (`stage` or `none`). Every replay case now declares it (a case without one is refused) and the oracle keeps one literal Improve schedule per value, so a `none` run's five planning producers must advance with no child while `system-test-author`, `release-plan` and the last `carry-forward` still park; `synthetic-none-full` replays one. The workflow review judges a run's Improve inventory against the schedule of the mode its state records, and reports a state that records no `planning_review` as unverified instead of comparable (a state that records `none` is judged against the `none` schedule and is comparable).

## 2026-10-05

### skill-craft 1.21.2

- Skills: shiploop 0.53.1, shiploop-run-review 0.1.1

### shiploop 0.53.1

- The refusal for an Improve opening that is too large now says how its byte counts are made: the sizes it lists and the room it states are counted escaped like JSON, so a newline or a quote costs 2 bytes and a non-ASCII character 6, and a file's byte size undercounts them. The stated room itself was already right; this only says what it measures, so a model that shortens the opening can measure it the same way and not be refused a second time.
- Every producer packet now prints, under the done template, the exact fields of each other outcome the stage allows (repeat, blocked with blocked_by and the awaiting wait, revise, replan), and says the result block holds the result object itself rather than the action and result wrapper the stored files under results/ use. The release-plan template now carries the consumer_entry its gate requires. The improve-start line in an Improve packet head names the four opening headings.
- A refused ShipLoop result now says how to fix it. A result that wraps its fields in action and result keys (the shape of the stored files under results/) is told to move the fields up and delete the named keys; a result missing outcome or summary is told which; a blocked, repeat, revise or replan result that still holds done-only fields (work_items, assumptions, steps, test_commands and the like) is refused once with every such field named; an awaiting wait without no_default is told where it goes, with the exact shape; unsupported fields are named; an Improve opening whose section heading is renamed is told the heading it must read and the headings it found. Each reply ends by telling the model to run the same command again. No check was loosened.
- The packet for the stage that records the whole-product test commands (system-test-author) now says which suite a command belongs in: a command that is not a test runner (a shell pipeline, a grep, a curl probe) is suite `check`, judged by its exit code, and `focused` and `regression` are for runners whose output ShipLoop can count. Before, the stage named the three suites without defining `check`, so a shell pipeline recorded as `focused` was refused at system-test ("could not read how many tests it ran") and could only be repaired by a replan.
- When a recorded test command exits 0 but ShipLoop cannot read how many tests it ran, the refusal now names the exit the running stage actually has. At system-test and release-verify, which run commands that system-test-author and release-plan recorded and cannot edit them, the reply says who recorded the command, that a command that is not a test runner (a shell pipeline, a grep, a probe) belongs in suite `check`, and to report replan now with one corrective work item that says to record the command as suite check in system_commands or consumer_checks; it no longer asks for ids and a runner flag or for a code fix that could not help. At the stages that run the step plan's commands the reply keeps the ids and runner flag and adds the `check` alternative. No check was loosened: a done is still refused until the command is counted or recorded as a check.
- At test-green, regression and static-checks, a result submitted before the bound Until Loop ran was told to list the loop's terminal packet in evidence_refs, a file that did not exist; citing it was then refused too. The refusal now says the loop has not run and names the exact start command the packet prints (the same text, from one definition), what to follow until the loop completes (or stops blocked, for revise), and then to list the receipt.

### shiploop-run-review 0.1.1

- The exporter now finds the Backchain loops that ShipLoop 1.21.0 keeps under `run/backchain/<action>/` (before, a 1.21.0 run read "Backchain loops: none found under scratch/"): each loop document gets its pass count, last outcome and trivial-streak requirement from the runtime receipt, its minutes from the start record to the receipt, and the loops under `scratch/` read as before. Each loop document also records, without enforcing anything, the run's `backchain_passes` option as `state.md` wrote it ("not recorded" when absent) and `candidateMatch`: whether the last `backchain-check` receipt is for the loop's final candidate (true, false or "unknown"). A one-pass loop's streak requirement of 0 reads "no trivial-streak requirement on this loop" instead of "0 of 0 required". An unreadable loop reports its passes as unknown, not 0. SCHEMA.md documents the new fields, the three layouts and why the first visit reads shorter than the harness's stage line.
- The prompt the Run Review page builds no longer names a review file after the page's primary run key (for example `hello-1190b.review.json`, which does not exist): a finding can span runs and is written in one run's review bundle, so the head now says "Review files: the *.review.json bundles in test/shiploop_e2e/evidence/", gives a `grep -l` line for the first ticked id and says to edit the bundle that holds it, and the report-back says to set the status "in the review file that holds it". The head's `Page:` part reads `config/page.artifactUrl`, which a draft page left empty because a page cannot read its own URL: `export.py --defaults --page-url URL` now sets it (keeping the page's own title and other fields), and the publish procedure in SKILL.md passes it. The page needs one republish.
- The Backchain pass strip on the Run Review page no longer says a one-pass loop "closes at 2": when a loop document's `trivialRequired` is 0 it draws no streak axis or target and says "no trivial-streak requirement on this loop"; a document with no `trivialRequired` (an older export) is drawn as before, with the target at 2. The loop card already lists the new `Backchain passes option` and `Candidate match` facts. The page needs one republish to show this.

### skill-craft 1.21.1

- Skills: adversarial-review 0.1.0, rubric-eval 0.1.0

### adversarial-review 0.1.0

- New skill: have a model from a different family than the change's author try to break the change, returning testable findings, each with the smallest experiment that would refute it, as findings.json for rubric-eval. Composes rubric-eval's isolated model call; reviewers are Grok, Sonnet or Opus.

### rubric-eval 0.1.0

- New skill: evaluate a prompt change against a rubric over a scenario catalog. Runs arms on Grok 4.7 (medium effort) by default, grades with one evidence-first judge per round (Opus 5.5, medium effort, by default), and decides by quality, then tokens, then time: scores are the percentage of analytic-rubric points earned, arms are compared paired with scenario-clustered bootstrap intervals and the Wilcoxon signed-rank test, equivalence is bounded by the judge's measured test-retest noise, and judges are accepted by Cohen's kappa (Landis–Koch substantial or better). Records tokens and seconds for every call. model_call.py gives Grok, Claude and Codex one interface (host:model@effort specs with pinned aliases grok, opus, sonnet, luna), each call in its own directory with reference files and read-only tools on request, and audits what each call touched outside it. Also adds a quote check and a value audit that weighs every item a review added or removed. Ships the architecture suites (up to 34 criteria and 23 scenarios across seven environments, including cross-runtime ones). SPEC.md is the reference for conditions, models, the ship rule, the change lifecycle and process hygiene for long runs.

## 2026-10-04

### skill-craft 1.21.0

- Skills: backchain 0.6.3, shiploop 0.53.0, shiploop-e2e-audit 0.6.1, shiploop-run-review 0.1.0

### backchain 0.6.3

- The review gate of a whole Backchain planning child is now selected by the caller. By default nothing changes: two consecutive distinct complete trivial/no-change dependency reviews, with both original qualifying review records kept. A caller that adds the line `Backchain passes: one` beside the binding marker in the child request gets one dependency review/fix/check cycle: `required_trivial_reviews: 0`, an exit condition naming the cycle, its repaired findings, the `Confirm by` rule on the steps the cycle may change (a weak clause on any other step stays advisory) and the `backchain-check` receipt, and the one review record plus that receipt as the terminal evidence set. `references/convergence.md`, `references/caller-contract.md`, the skill card and the evals say so, with a new eval for the marker path. Standalone Backchain keeps the default two reviews.

### shiploop 0.53.0

- The plan packet's Backchain text now follows the run's `backchain_passes` option. With the default `one` it tells the host to write the planning child's start contract with `required_trivial_reviews: 0` and a one-cycle exit condition (one review/fix/check cycle has run, every finding of it is repaired within the edit bounds, every `Confirm by` clause on a step this cycle may change meets the planning guide's Outcomes rule, the printed `backchain-check` is ok on the final candidate with its receipt cited, domain evidence saved), and to put the line `Backchain passes: one` beside the binding marker in the child request. A pass that completes that cycle reports `exit_assessment: satisfied` even when it repaired the candidate, and Until Loop then completes the child instead of asking for two more reviews. The audit stages (spec, step-plan, carry-forward, product-acceptance) tell the host that a repair/revise child runs one cycle and to put the same marker line beside the binding marker in the child request. `--backchain-passes converge` prints the previous two-review text unchanged. ShipLoop's skill guide and Backchain planning guide now point to the packet's printed gate instead of stating two consecutive reviews. Improve's loops, the quality and test loops and the vendored Until Loop are unchanged.
- New run option `--backchain-passes one|converge|none` at `init` and `workspace start`, recorded as `backchain_passes` in `state.md` like `--lint` (default `one`). It sets how many passes the Backchain planning child may take: one review/fix/check cycle, two consecutive trivial reviews, or no whole loop at `plan`. With `none` the `plan` packet prints the read-only audit route and the audit resource with the loop-resource status line, says no whole `plan`/`draft` is requested in this run, and omits the six-file Backchain and Until Loop resource block; the four audit stages say the same in place of "only at `plan`", and a `repair`/`revise` after a finding still runs one pass. `one` and `converge` print what they printed before. A retry of `init` or `workspace start` cannot change it and no verb changes it mid-run. A saved run without the key is refused with the fresh-run hint: start the request again in a fresh `--run-dir` or `--workspace-root`. Improve's review loops are not covered by the option.

### shiploop-e2e-audit 0.6.1

- The Run Review exporter, contract, defaults and page template moved to the new shiploop-run-review skill; this skill's after-every-run step now points to it.

### shiploop-run-review 0.1.0

- Adds the ShipLoop Run Review skill (`/skill-craft:shiploop-run-review`): it exports a ShipLoop E2E run's measured numbers, has Claude write findings, advice and options for the run into a review file that `export.py --check` validates (`advise`, `export`, `check`), and publishes both to the owner's Run Review page (`publish`). The exporter, data contract, starting defaults and page template move here from shiploop-e2e-audit. The export is now `run-review-export/v2`: a counter the host cannot measure (refusals and glue on a Claude run) is left out with its reason instead of reading 0, a `metrics.json` that predates that record is refused, and a stage with no accept time reads n/a instead of 0 min.

### skill-craft 1.20.0

- Skills: shiploop 0.52.0

### shiploop 0.52.0

- At system-test, a required case that only a person can run and that has no route on this host is recorded as an open item (owner a person, due at handoff or at the stage whose external effect it gates), and the stage reports done once every other due check and ShipLoop's rerun pass, instead of ending the run blocked. The handoff lists each open item as unverified with who reports what, and the stage-readiness reference says the same; prompt and reference text only.
- A ShipLoop test run that never reached a verdict about the product is no longer
  counted as a product failure.

  - A command that times out, cannot start (the process could not be spawned; a
    command the shell cannot find or execute exits 126 or 127 and is still a
    failure), or is skipped because the invocation's
    budget ran out is recorded `disposition: could-not-run`. It still refuses the
    stage — nothing is accepted on unrun tests — but it does not spend one of the 7
    refused runs, so an environment problem can no longer rewrite a work item's
    step plan. A real failing check beside a timeout is still a failure.
  - Fixed: a command that could not start (`OSError`) was recorded as `failed`.
    The `error` status was computed and then overwritten, so a spawn failure was
    indistinguishable from a failing test.
  - At the 7-refused-run gate the packet now names the outcome the stage actually
    allows: `revise` back to the step plan at an INNER stage, and `replan` with
    corrective work items at the outer `system-test` and `release-verify`, which
    have no step plan to revise and where the navigator rejects `revise`.
  - A timeout is reported as reaching no verdict rather than as a product failure,
    since it can mean a deadlock, a broken test, a suite too slow for the budget,
    or an external dependency.
  - Because those attempts no longer reach the gate, the refusal names the routes
    out explicitly: a hang in the item's own code, test or fixture is run-fixable
    and is not a blocker, a recorded command that is wrong or too slow to fit the
    run's budget takes the stage's remedy, and `blocked` is only for what the user,
    an access grant or an outside dependency must supply. A skipped command is
    named as such: it never started because the commands before it used the run's
    budget, and they run in the same order every time, so a retry skips it again.
  - That remedy is accepted. At `test-green`, `regression` and `static-checks` the
    navigator used to require a stopped Until Loop packet for `revise`, which a
    `could-not-run` attempt never produces, so the route the refusal named was
    refused (and at `static-checks`, `blocked` too). ShipLoop's own record now
    supports it: when its latest test run for the action is `could-not-run` (and,
    at `static-checks`, where it was never opened, after 7 refused runs too),
    `revise` (and `blocked` at `static-checks`) is accepted without a new loop
    packet; `replan` with corrective work items at the outer stages and `revise`
    at the other INNER stages were already accepted. An ordinary `done` still needs
    a complete loop packet, and a later failed run closes the route again.
  - The outer-stage rerun packet says which stage recorded its commands
    (`system-test-author`, `release-plan`) instead of the step plan, and the
    `test-red` text no longer asks for the item's own code to be fixed. The
    `end-of-work review` gate, which is not a graph stage and has no remedy outcome,
    no longer says that a failing run ends in `blocked`.
  - Keepalive's stuck release (14 continuations without an accepted result) keeps
    its value, which is no longer paired with the 7-run cap for a command that
    cannot run; its comment says so and its notice names the outcomes above.

  Known limits, kept on purpose: a timed-out command's partial output is not read,
  so a suite that prints failures and then hangs is `could-not-run`; and at the
  `end-of-work review` gate, which reruns every item's recorded commands for the
  Improve import, a recorded command that cannot run has no remedy outcome.

  The per-invocation command timeout (600s) and budget (1800s) are unchanged.

### skill-craft 1.19.2

- Skills: shiploop 0.51.2

### shiploop 0.51.2

- The chain guide's `finish` row and worked example no longer say finish needs every worker's worktree removed. Since 0.49.0 a retried or lost attempt's workspace is kept and listed under `retained_superseded`; the old wording could lead a model to remove it directly or to stop.

### skill-craft 1.19.1

- Skills: plan-dispatcher 0.6.2, shiploop 0.51.1

### plan-dispatcher 0.6.2

- The skill card no longer says to retry only after confirming the old worker stopped without exception: it names the lost-worker case (host session ended, handle unavailable) and points to the protocol's limits, matching the protocol since 0.6.0.

### shiploop 0.51.1

- On an Ask-Agent run, step-plan now asks for each change that does not need another to be its own step with `deps: []`, joined by a later step that needs them. Before, a request that did not ask for parallel work got a linear plan (two independent modules in one step), so the default parallel chain had nothing to run at the same time. Inline runs are unchanged.

### skill-craft 1.19.0

- Skills: shiploop 0.51.0, shiploop-e2e-audit 0.6.0

### shiploop 0.51.0

- New `shiploop backchain-check --candidate PATH`: checks a Backchain candidate plan against Backchain's seven structural invariants (a Python port of Backchain's reference validator, packaged first) and records a receipt and a snapshot under the run's `backchain/<action>/`. Backchain stages tell the host to run it after each candidate revision and to treat a failure as a loop finding; nothing is refused.
- Every stage that can start a Backchain Until Loop child now states the contract size budget (the plan stage and the repair/revise route at spec, step-plan, carry-forward and product-acceptance), and an `improve-start` refusal lists each opening section's own byte size beside the bytes the sections may use. A GPT-6 Luna run built an 11.9 KB step-plan Backchain contract because only the plan stage carried the budget, and the refusal had compared whole contract fields with a per-section allowance.
- The Backchain loop text and the Backchain and Until Loop resource list now print only at the plan stage, where a whole loop may start. Spec, step-plan, carry-forward and product-acceptance print the read-only audit route, the audit resource and one line saying whether the files a repair/revise request needs are all present or which are missing; the identity and digest instructions restated at plan and the Improve-owner text are shorter. Prompt text only: no command, state field or exit rule changes.

### shiploop-e2e-audit 0.6.0

- The Grok adapter credits ShipLoop's new `backchain-check` verb as a direct ShipLoop command.
- Adds the Run Review page: a static template with its data contract, starting defaults and an exporter, so every E2E iteration can add the run's data to the owner's page without redoing the template.

### skill-craft 1.18.0

- Skills: plan-dispatcher 0.6.1, shiploop 0.50.0

### plan-dispatcher 0.6.1

- The protocol states the limit of `retry` with `native_status: "unavailable"`: it keeps the step's accepted result correct, but relies on the lost worker having ended with its host session. A step sharing a checkout, port, database or other external resource with its replacement waits for proof that the old worker stopped.

### shiploop 0.50.0

- The final report lists what the run left in your repository — merged attempt branches, kept (rejected or lost) attempt worktrees, and the run's own branch and workspace — with the command to remove each, and the completion packet says how many there are. ShipLoop still never deletes them itself. Commands use `git branch -d` wherever the branch is merged (it refuses to lose work) and never `--force`; nothing is offered for removal before the run is returned.
- The chain guide states when retrying a lost worker without proof that it stopped is safe: when native workers end with their host session. A step holding something outside its worktree (a port, a database, a deployment) waits for proof instead.

### skill-craft 1.17.0

- Skills: plan-dispatcher 0.6.0, shiploop 0.49.0

### plan-dispatcher 0.6.0

- `retry` accepts a worker whose host session ended: `confirmed_stopped: false` with `native_status: "unavailable"`, for when the worker's handle can no longer be looked up and nobody can prove it stopped. The retry is recorded as unconfirmed; the old attempt's work is kept and its late report is refused, so the fresh attempt is safe.

### shiploop 0.49.0

- A run resumed after its host session was lost can recover its chain without a person. When a worker's handle can no longer be looked up, `chain retry` accepts `confirmed_stopped: false` with `native_status: "unavailable"`; the old workspace is kept as evidence, its late callbacks are refused, and the step gets a fresh worker. Previously the run paused to ask whether it could retry.
- A chain step that needed a retry no longer blocks the chain from finishing. The retried attempt's Ask-Agent workspace is still kept as evidence (never deleted); `chain finish` now completes and lists it under `retained_superseded` instead of refusing forever.

## 2026-10-03

### skill-craft 1.16.1

- Skills: shiploop 0.48.1

### shiploop 0.48.1

- The credential check no longer refuses a label followed by a plain description (`session token: opaque UUID`, `auth: none required`, `auth: oauth2`, `signature: n/a.`), including punctuation or markdown around it; real secrets after the same labels are still refused. A GPT-6 Luna discovery result was refused twice for text that held no credential.
- `improve-start` refuses an Improve contract over 9,216 bytes before anything is written, counting bytes the way the Until Loop does and telling the model how far over it is, which opening section to shorten and how many bytes the sections may use; the opening and Backchain packets state that budget, and a step plan whose test command list could not fit the test loop's contract is refused where it is submitted. The Until Loop saves its whole state in 16,384 bytes, so a larger contract can start yet fail to save its first review report. A GPT-6 Luna run wrote 12-16 KB contracts and its plan stage could not close.

### skill-craft 1.16.0

- Skills: backchain 0.6.2, improve 0.3.0-rc.11, shiploop 0.48.0, shiploop-e2e-audit 0.5.4

### backchain 0.6.2

- Honor a caller's explicitly selected bundled Until Loop adapter card and resolve its runtime relative to that card. This lets ShipLoop planning use its selected package without searching for a nonexistent separate skill card or substituting another installation.
- Clarify in the native procedure that an explicitly selected bundled Until Loop ADAPTER.md is the selected card, with its own package-relative reference and adapter.

### improve 0.3.0-rc.11

- Clarify that Improve's whole-skill subcall applies to the current ShipLoop packet regardless of navigator protocol label.

### shiploop 0.48.0

- Reaching the research investigation allowance stops exploration, never the run: the model records open gaps as assumptions or open items, submits the result and continues, instead of pausing an unattended run (a GPT-6 Luna run paused itself at the allowance).
- Backchain-stage packets print the resolved Backchain and Until Loop resources from ShipLoop's installed plugin, identify missing resources by path, and name Until Loop's `ADAPTER.md` card correctly.
- Per-step flow replies expose dispatcher control only through bridge navigation.
  Raw dispatcher actions and continuation instructions are removed from the public response.
- The execution-checkout locator in worktree packets says it is a working directory, never a `--result` value; a GPT-6 Luna run passed it as the result path.
- Rename the current prompt module and navigator contract suites to version-neutral names. Update active consumers and suite labels, and share duplicated design-basis guidance without changing rendered packets.
- Terminal handoffs retry knowledge commits and worktree follow-up returns before saving completion, leaving the handoff pending when either required operation fails.
- The Improve packet names the Until Loop root, where its card's relative links resolve; a GPT-6 Luna run resolved `references/runtime-ephemeral.md` under the Improve skill, found nothing and paused, believing the runtime missing.

### shiploop-e2e-audit 0.5.4

- Update the audit harness module list to load ShipLoop's version-neutral prompt module.

## 2026-09-28

### skill-craft 1.15.0

- Skills: shiploop 0.47.0, shiploop-e2e-audit 0.5.3

### shiploop 0.47.0

- Keep a self-contained progress.html current during each run using a read-only
  background observer. Visualize generated implementation steps, dependency edges,
  and recorded execution status. Show the accepted plan, recorded activity, and embedded
  specification and architecture drafts with source and freshness labels. Add
  explicit dependency lists to generated inline step plans while preserving saved
  plans that omit dependency metadata. Add
  view commands for snapshots, foreground watching, background start, stop and
  status; preserve the terminal report and Markdown workflow authority.
- Keep startup guidance compatible with package-reference validation by describing
  the link without a placeholder target. Preserve the actual progress-file path
  when run directories contain URL or Markdown delimiter characters.
- Introduce the progress HTML file in the first startup message with a clickable
  absolute link and an explanation that it tracks changes during the run. Keep the
  link available in action packets for later reference.

### shiploop-e2e-audit 0.5.3

- Recognize ShipLoop's progress-view CLI command in the Grok audit adapter's
  direct-command inventory, keeping it aligned with the current CLI help.
  Revalidate the retained host-command shapes against the updated parser while
  preserving their capture provenance and expected attribution.

## 2026-09-27

### skill-craft 1.14.0

- Skills: ask-agent 0.9.0, improve-agent 0.1.3, plan-dispatcher 0.5.1

### ask-agent 0.9.0

- The current workspace is now the default route. An ordinary delegation runs a fresh worker in your own checkout and branch, with no second worktree or repository: `in-place` within a write set declared from the request for file changes, `report-only` for questions, digests and reviews. A separate helper-managed worktree now needs an explicit selection (`workspace_route: helper-managed` or asking for a separate worktree).

### improve-agent 0.1.3

- A standalone request explicitly selects Ask Agent's helper-managed route, since Ask Agent's default is now the current checkout.

### plan-dispatcher 0.5.1

- Git tasks explicitly select Ask Agent's helper-managed route, since it is no longer Ask Agent's default.

### skill-craft 1.13.0

- Skills: shiploop 0.46.0

### shiploop 0.46.0

- `workspace start` now checks, before creating anything, that the host sandbox lets
  it write the `.shiploop-runs` parent and the repository's Git directory. When a
  sandbox refuses (Codex `workspace-write`, a Grok sandbox profile, Claude's Bash
  sandbox) it exits 3 with a `SHIPLOOP-GRANT-NEEDED` block naming the blocked
  paths, the repair intent, the grant for the detected host and the exact rerun
  command. Every later run-bound command rechecks, so a harness restarted without
  its grants stops before a commit fails. `--workspace-root` is now optional: the
  default is a new `<repo-parent>/.shiploop-runs/<repo>-<stamp>`, so one grant of
  that parent covers every later run.

### skill-craft 1.12.2

- Skills: shiploop 0.45.2

### shiploop 0.45.2

- A completion refused for naming the wrong result file now names the file to use.

### skill-craft 1.12.1

- Skills: shiploop 0.45.1

### shiploop 0.45.1

- On the Ask-Agent route, ShipLoop now writes the Improve child's contract and
  starts the child itself, as it already did on the inline route. The parent
  writes the opening and runs `improve-start`. The improve-agent worker then
  continues the started child from the receipt's `next_argv`; it no longer
  hand-builds the contract or copies the binding line.

  A stopped child restarts with `improve-start --restart-stopped` on both
  routes. The frozen contract lists the `host-owner.md` owner record for a
  delegated child.

### skill-craft 1.12.0

- Skills: improve 0.3.0-rc.10, improve-agent 0.1.2, shiploop 0.45.0

### improve 0.3.0-rc.10

- The ShipLoop subcall guidance describes the new completion: write `review-<n>.md` per pass and `checks.md`; ShipLoop imports them, with optional `--notes` and `--final-result`.

### improve-agent 0.1.2

- Names the child's reviews directory as the locator to return, matching ShipLoop's derived Improve completion.

### shiploop 0.45.0

- A ShipLoop record without exactly one `shiploop-state` JSON fence is refused with its path, the fence count and the expected shape, instead of a bare "exactly one fence" message.
- `improve-complete --action <id>` no longer takes a completion record. Each review pass writes `reviews/review-<n>.md` and the check output `reviews/checks.md`; ShipLoop imports the last two passes (the last one when the first pass changed nothing) and `checks.md`, and writes the summary itself. The model supplies only optional `--notes` (lessons), `--final-result` (when the review changed a decision) and `--no-commit`. `parent-return.md` is the one command. The `--result` flag of `improve-complete` is removed; stopped and reconcile receipts are unchanged.
- After a verified workspace return, ShipLoop returns its own later knowledge commit (for example at release-verify) by the same route when everything changed since that return is `docs/shiploop/` or `SHIPLOOP.md`, keeping the earlier reviewed dispositions; handoff no longer finds a stale receipt and asks the model for a manual follow-up. Anything else changed, or a moved source, leaves the follow-up to handoff as before.
- Every run has a scratch directory, `<run>/scratch/`, named in each packet's locators; the common rule and the Improve packet send temporary files there (including the report piped to the Until Loop runtime), because `/tmp` is shared with other runs and a fixed `/tmp` name can read another run's file.

### skill-craft 1.11.1

- Skills: shiploop 0.44.1

### shiploop 0.44.1

- ShipLoop now commits the repository knowledge index `SHIPLOOP.md` with `docs/shiploop/` after any accepted stage that changed it, screens it for credentials, and keeps it on the workspace return. The model no longer commits it by hand.
- `workspace plan-return` first commits product files still uncommitted in the candidate onto the run branch, so a reviewed return fast-forwards instead of falling back to uncommitted working-tree changes. Run evidence, protected paths, caller exclusions and files that look like credentials are never committed. A release plan whose `consumer_entry` sources are absolute paths is refused with a clear message instead of crashing.

### skill-craft 1.11.0

- Skills: shiploop 0.44.0

### shiploop 0.44.0

- Milestone packets now carry a script-rendered run narrative: the goal, a progress bar per phase, what has been achieved (each step's new one-line `headline`), what is happening now, what comes next, and the observed pace with a labelled forecast from `<run>/timeline.json`. Where the host shows hook messages (the Claude Code terminal CLI) the status hook shows it as plain text; everywhere else, including the Claude desktop app, the model pastes the Markdown narrative as written, once per milestone. Results accept an optional `headline` of at most 100 characters.

### skill-craft 1.10.0

- Skills: shiploop 0.43.0

### shiploop 0.43.0

- The lint gate now blocks only an item's last implement step. Earlier steps
  report their findings without auto-fix, since a later step may resolve them
  (for example, an import the next step uses).

  Once a loop's receipt exists, the loop packet says not to run Start again and
  to continue from the receipt's `next_argv`.

  Paused, halted and blocked packets longer than 16,000 characters now print a
  pointer to the full packet file and what fits, so they stay under hosts'
  shell-output limits.
- ShipLoop runs unattended by default. An open decision takes a recorded default
  (an assumption with its alternatives) and the run continues; a step only a
  person can do becomes an open item while every independent stage continues.
  The run prompts the user (`blocked` + `awaiting`) only when nothing further can
  proceed without them, and a new `awaiting` must carry `no_default`, the reason
  no default would do; ShipLoop refuses one without it. Saved runs that are
  already waiting load and resume as before. Stage duties, the release-plan and
  release-verify guidance, SKILL.md and the delivery references say so, and the
  release-verify example is platform-neutral.

### skill-craft 1.9.0

- Skills: ask-agent 0.8.0, plan-dispatcher 0.5.0, shiploop 0.42.0

### ask-agent 0.8.0

- New explicit route `workspace_route: current` ("in place", `--in-place`, "just use the current worktree"): a fresh worker runs in the caller's own checkout and branch, with no helper worktree, receipt or close. It defaults to `report-only`; `in-place` writes need a declared write set. The helper's new read-only `current-state` command records a baseline and reports `unchanged`, `changed-within-write-set` or `drift`. An explicitly requested cheaper model or read-only agent type is honored and disclosed. Plan Dispatcher, ShipLoop and improve-agent keep the helper-managed route.

### plan-dispatcher 0.5.0

- Every action now carries its exact `call`: the argv plus an input whose
  `"<...>"` placeholders the caller fills. The settle call pre-fills the receipt
  digest, and the claim and start responses carry the follow-up calls. A
  completed run returns no `next_argv`.

  `init` accepts an optional `capacity`. The claim action then offers only free
  slots, and an over-capacity claim fails with `ECAPACITY`.

  Planning-blocked steps are no longer offered for claim, and a claim for one is
  refused. Cleaning up a rejected attempt's workspace or evidence no longer
  breaks the run. Concurrent writers wait briefly for the lock instead of failing
  with `ELOCKED`.

### shiploop 0.42.0

- Inline Improve packets no longer restate steps ShipLoop now performs (binding
  inputs, the binding line, start inputs, the runtime start command, the planning
  repeat clause); each remaining obligation is stated once. The delegated route
  keeps its manual start instructions.
- One commit path for every ShipLoop commit (knowledge home, the integrate item
  commit, `improve-commit`, the empty-repository baseline): it stages exactly the
  named paths, leaves any text file that looks like it holds a credential
  uncommitted and names it (never its value), and uses the configured identity or
  else the workspace identity. The knowledge-home commit gains that fallback.
  ShipLoop now also commits `docs/shiploop/` after any accepted stage that changed
  it (not only at the four closes), with the same credential and requirement-ID
  checks; packets tell the model not to commit it itself.
- The test loop, quality loop and Improve child contracts are built and
  serialized by one module (the test and quality contracts are byte-identical to
  before). An Improve child's exit condition now also requires the reviewed
  stage's own done-when criteria, so a review loop ends on what that stage must
  achieve, not only on two quiet passes.

### skill-craft 1.8.0

- Skills: plan-dispatcher 0.4.0, shiploop 0.41.0

### plan-dispatcher 0.4.0

- A verified BLOCKED result now routes the run to replanning. Settle it with
  `verification.disposition: "replan"` (only with `passed: false`). The run then
  starts no new work:

  - `claim`, a fresh `start` and a retry of that attempt fail with `EREPLAN`;
  - `next` returns `replan` and `release` actions plus a `replan` summary (steps,
    accepted, unfinished);
  - work already in flight can still settle.

  Rejected steps get a `retry` action with an attempt count, the reason and an
  exact `call`. There is no retry limit.

  A lock left by a process that no longer exists on this host is recovered
  automatically; any other holder is refused with a message that names what to
  do. A lost state file or settled receipt fails with `ESTATELOST` and names the
  recovery.

### shiploop 0.41.0

- The status hook now shows a two-line summary (where the run is; what finished and what comes next) instead of the full 11-line block, and the model no longer reprints the status block: it tells the user at most one line per step and shows the whole block only when asked. `shiploop status` and `status.md` still carry the full block.

### skill-craft 1.7.0

- Skills: shiploop 0.40.0

### shiploop 0.40.0

- Planning now keeps safeguards when it simplifies. The interaction-design guidance asks for the simplest placement that meets the request (a single-user product runs entirely in the client), the lightest channel for the freshness the request states, and native caching with a matching expiry. It also says simplicity removes machinery, never safeguards: personal-data handling, server-side checks on callers the product does not control, abuse limits on anonymous input, and background failures that reach someone who can act. Across 19 scenarios on seven environments this raised plan quality (winning about twice as many scenarios as it lost against the previous wording) without the privacy loss an earlier draft caused. The Apps Script card now states that executions run concurrently, that properties need a LockService lock for read-modify-write, that google.script.run is asynchronous, and when Session.getActiveUser() returns a blank email. Evidence: docs/shiploop-architecture-rubric-results-2026-09-26.md.

### skill-craft 1.6.0

- Skills: improve 0.3.0-rc.9, shiploop 0.39.0, shiploop-e2e-audit 0.5.2

### improve 0.3.0-rc.9

- The ShipLoop whole-skill subcall commits a review's changes through ShipLoop's
  `improve-commit` when the packet prints it (message written with a file tool).

### shiploop 0.39.0

- New `improve-commit` command for the inline Improve route: the parent writes the
  review's commit message to `commit-message.md` beside the receipt with a file
  tool, and ShipLoop stages and commits exactly the files the review changed and
  has not committed (earlier uncommitted work is left alone). Inline Improve
  packets print the command.
- `improve-start` prints only the runtime's JSON packet on stdout (its status and
  archive lines go to stderr), so a host can parse the output as JSON, as it can
  the runtime's own `start`.

### shiploop-e2e-audit 0.5.2

- The Grok adapter recognizes ShipLoop's `improve-commit` verb.

### skill-craft 1.5.1

- Skills: shiploop-e2e-audit 0.5.1

### shiploop-e2e-audit 0.5.1

- The Grok adapter recognizes ShipLoop's new `improve-start` verb, and the host
  trace fixtures are rebound to the adapter's new source hash.

## 2026-09-26

### skill-craft 1.5.0

- Skills: improve 0.3.0-rc.8, shiploop 0.38.0

### improve 0.3.0-rc.8

- The ShipLoop whole-skill subcall uses ShipLoop's `improve-start` command when
  the packet prints one: write the named opening file and run it instead of
  writing the start contract and starting the runtime by hand.

### shiploop 0.38.0

- `workspace start` on an empty, non-Git directory initializes it as a Git
  repository on `main` with one empty baseline commit (the user's identity when
  configured, otherwise the workspace identity). The model no longer writes Git
  setup commands for a new product, which on Grok's auto permission mode were
  cancelled and ended the session three times in one run.
- ShipLoop commits a work item's changes itself when `integrate` is accepted: the
  files the item changed that its step plan's `paths` declare, plus
  `docs/shiploop/`, with the item title and integrate summary as the message
  (the configured identity, else the workspace identity). It prints the commit
  and names every other changed file for the model to commit or delete. The
  model no longer writes the item commit, which headless hosts refused, and a
  run no longer ends with its product uncommitted in the execution worktree.
- `workspace start` creates one missing parent level of the workspace root (the
  usual `<beside the repo>/.shiploop-runs/<name>` layout) instead of refusing it;
  a deeper missing tree is still refused.
- The execution worktree branch is `shiploop/run-<id>` on every host instead of
  `codex/shiploop-<id>`, which named Codex on Grok and Claude runs. Workspace
  records made with the old name are refused.
- New `improve-start` command for the default inline route. The parent writes a
  four-section opening file (current context and desired improvements, scope,
  authority, environment) beside the receipt; ShipLoop freezes the Until Loop
  child contract from it (binding line first, workspace, work, exit and repeat
  conditions, commit policy, exclusions, and locators for the receipt, evidence
  directory, parent state, completion evidence and a written `parent-return.md`),
  stores it as `start.json`, starts the bound runtime with `--receipt` and its
  state under the run directory's `until-loop/`, and prints the child's first
  packet. The model no longer hand-writes a ~6 KB JSON contract per child.

  `improve-start --restart-stopped` restarts a stopped child: ShipLoop archives its
  `packet.json` and `reviews/` with a UTC stamp itself and starts the new child,
  instead of the model renaming them by hand.
- Keepalive binds a session to a run from a packet marker only when the command
  that printed it drives the run (`workspace start`, `init`, `next`, `resume`,
  `complete`, Improve bind/complete/reconcile). A session that merely reads a
  packet file, log or transcript containing a live marker is no longer bound and
  kept alive for a run it does not drive. The `--run-dir` fallback also reads only the command that ran, never its
  output, so callback text printed in a log or event dump no longer binds.

### skill-craft 1.4.0

- Skills: shiploop 0.37.0

### shiploop 0.37.0

- Packets now live in files. For an active run, ShipLoop writes the complete packet to `<run>/packets/<action>.md` and prints only a short head: the callback, goal and done-when, the result contract, the packet file's path, recovery and pause commands, the keepalive marker and the status block (about 3 KB instead of 20-50 KB). The host reads the file on demand and consults only the reference sections a step needs, instead of printing whole packets that Grok cut at about 20 KB and reading whole reference files into context. Paused, blocked, awaiting, halted and done packets still print whole. `next` rewrites the file and reprints the head.

### skill-craft 1.3.0

- Skills: shiploop 0.36.0, shiploop-e2e-audit 0.5.0

### shiploop 0.36.0

- Planning now has platform cards for Cloudflare Workers, Vercel and Next.js, AWS serverless, Google Cloud, a self-hosted Node.js and Express server, and web UI frameworks (Bootstrap, Material Design 3, React, Next.js, Vue, Svelte, Tailwind, and fitting them to Apps Script and Salesforce hosts). Each card covers identity, state, concurrency, channels, caching, secrets, background work and limits, with dated current facts and claims to check, all linked to official sources. The coding guidance index lists them. The architecture rubric, scenario catalog and results are in docs/shiploop-architecture-rubric.md.

### shiploop-e2e-audit 0.5.0

- Every workflow review now reflects on the harness itself in a required `harness_reflection` block: should the harness retain key learnings or keep state differently, is there more to learn from on subsequent passes, and are more evaluation criteria needed to re-evaluate ShipLoop's efficacy. Each answer comes from the run's evidence with concrete proposals. The template carries the three questions, and the validator reports a review without them as unverified and one with empty answers as invalid.

### skill-craft 1.2.0

- Skills: shiploop 0.35.0

### shiploop 0.35.0

- Packets now ask for composable design and a state lifecycle. Code craft adds "compose before you build" (reuse, compose or augment an existing unit before writing a new one, with a guard against fusing different rules), and the quality loop treats duplicated logic as a material finding. Intake asks who the actors are, whether state is shared or must persist, and what must stay hidden. The interaction-design guidance asks each state's owner, readers, concurrency, end of life, quotas and personal-data handling. The planning review checks platform claims that a decision depends on. The Apps Script card describes the mcp-gas-deploy layer, including that its `srv`/`apiExec` bridge runs client-built code. Evidence: docs/shiploop-composition-state-experiments-2026-09-26.md.

### skill-craft 1.1.0

- Skills: improve 0.3.0-rc.7, shiploop 0.34.0

### improve 0.3.0-rc.7

- The bundled Until Loop runtime is 0.7.0: `start --receipt <absolute file>` makes the runtime write every packet it returns to that file (atomically, mode 0600) before printing it, including the terminal packet, which it writes before deleting its state. In a ShipLoop subcall, start the bound runtime with the printed host receipt path as `--receipt`; ShipLoop imports only a packet the runtime wrote there.

### shiploop 0.34.0

- A completion criterion is now confirmed only by a command ShipLoop runs and sees pass. A done
  `step-plan` lists its `criteria` and names, in each test command's `criteria`, the ones that command
  confirms; an uncovered criterion is refused. A new `check` command kind (judged by exit code) covers
  content with no test runner, such as a README that must document a flag. `verify` reruns every
  recorded command. `system-test-author` must record `system_commands` and `release-plan`
  `consumer_checks` (or an empty list with the reason); ShipLoop runs them when `system-test` and
  `release-verify` report done and refuses unless each passes.
- Every packet now tells the host never to end its turn while a ShipLoop command is still running: keep the command in the foreground, or wait for it in the same turn when the host backgrounds it. A test-stage `complete` reruns the recorded tests and can take minutes, and a headless Grok session ends when the turn ends, which lost a callback in a live run. The keepalive self-install notice now says the current session is not protected (headless sessions never are).
- `next` always prints the full packet. It is the recovery command, and the script cannot know whether the host kept the run rules through a clear, a compaction or a fresh `shiploop-drive` session, so recovery no longer returns the short form with the original request and delegation rule behind a pointer to `rules.md`. `next --full` is removed. Every producer packet now prints its result path, result template and allowed outcomes directly under the callback line instead of at the end, so a host that keeps only the head of long output still has the contract the callback checks; the tail keeps the callback, pause and halt lines.
- Every producer packet now opens with the stage's goal, the conditions that confirm it and its fixed
  considerations for developing, testing, delivering and the assistive tools, right after the
  callback. Guidance that cannot apply to a stage is no longer printed there: the work-item paragraph
  appears only at plan and carry-forward, interaction design only from discovery to step-plan, the
  Code craft rubric only where code or tests are written or reviewed, and "the Improve child" only at
  stages that have one. implement and release no longer mention an Improve checkpoint they do not
  have. Packets are about 3% shorter overall.
- A done `step-plan` must list `steps: [{"id": "S1", "task": "..."}]`, every implementation step in the order to do them (one step is fine). On the inline route ShipLoop then issues one `implement` packet per step: each names its step, the steps already accepted and the ones still to come, and the callback after the last step moves to the test stages. Which steps are done is read from the run's history, so recovery after a lost context reprints the current step. A revised step plan starts its steps over. The ask-agent route is unchanged: a chain runs every step inside its one `implement` action.
- There is one packet form. `next --brief`, the short repeat packet, the per-run `rules.md` and `last-packet.json` display records and the Claude `SessionStart` compaction hook (`shiploop-keepalive-compacted`) are removed: every packet, including every `next`, prints in full, so nothing depends on what a host kept from an earlier packet. The Improve change gate's check that a one-pass review really left the candidate unchanged now runs; it previously failed silently and never refused.
- A context lost in the middle of a stage can now pick up where it left off. Every packet names the
  action's pass log (`notes/<action>.md`), where each pass records what it checked and what is left,
  and the run context index gains an "In progress" section (the action, its pass log, loop packets,
  ShipLoop test runs so far and revisions used) and a "Script records" section listing ShipLoop's own
  test runs, loop packets, lint records and Improve receipts. A result that cites a local file that
  does not exist is refused. `verify` now reads the item's implement, test-green, regression and
  static-checks results, and `handoff` reads product-acceptance and operations.
- A fixable problem is no longer reported as `blocked`. When a work item's goal proves wrong or
  unachievable while it is being built (test-spec through integration-verify), the stage reports
  the new outcome `revise`: the item goes back to `step-plan` with that result as evidence, at most
  twice per item, and then the user decides. A script-run test or quality loop that uses all its
  iterations, or three refused test runs, now routes to `revise`; a loop cancelled before its limit
  is refused, because a user's stop is `pause`. `blocked` stays for what only the user, an access
  grant or an outside dependency can resolve. Saved runs from earlier versions are refused; start a
  fresh run.
- Until Loop packets no longer depend on the host copying stdout before a context loss. The test-loop and quality-loop start commands pass `--receipt tests|quality/<action>-terminal.json`, and Improve children start with `--receipt` set to the printed Child latest packet receipt, so the bundled runtime (Until Loop 0.7.0) writes every packet there itself and the terminal packet before it deletes its state. ShipLoop now accepts a loop or Improve terminal packet only when it is a complete runtime packet whose `receipt` names that exact path and whose state file is gone; a hand-written object copied from the contract, a packet from a run started without the printed `--receipt`, or a copy of a still-live run is refused. The complete-packet Improve import now also requires the child's state file to be deleted, as the stopped import already did.
- ShipLoop's 34 stages are now described in one table (`scripts/shiploop_stage_spec.py`): each
  stage's goal, the conditions that confirm it, and its fixed considerations for developing,
  testing, delivering and the assistive tools (linters, test runners) the script runs around it.
  The stage sets that decide Improve reviews, lint gates, test runs, prompt blocks and "Read first"
  lists are derived from that table. Packets and run behaviour are unchanged.
- Keepalive now lets a turn end after 14 continuations with no accepted result (twice the per-action test-run refusal budget), with a notice to submit `blocked` or `revise`; a refused callback still counts as progress until then, and an accepted result starts the count again. When `handoff` is refused for want of a current workspace return, the refusal now says whether no return was made or the recorded one is stale (for example after ShipLoop's own `docs/shiploop/` commit at `release-verify`) and prints the exact `workspace plan-return` and `workspace return` commands. `system_commands` and `consumer_checks` can no longer name `criteria`, which nothing checked.
- ShipLoop's quality and test loops no longer have an iteration limit: they run until their exit
  condition holds. The loop contracts no longer tell the model to cancel at iteration 3 (quality) or
  4 (tests), a complete loop is `done` however many iterations it took, and a cancelled loop is always
  refused (a user's stop is the packet's `pause` command). A loop that stops blocked reports `blocked`,
  or `revise` when the item's goal proved wrong as planned. ShipLoop's own test reruns now allow 7
  refused runs before `done` is no longer accepted (was 3).

### skill-craft 1.0.1

- Skills: backchain 0.6.1, review-coverage 0.3.3

### backchain 0.6.1

- The trigger evals drop the `coexistence-devloop` case: DevLoop was archived on 2026-09-26.

### review-coverage 0.3.3

- The clean/residual×2 rule no longer refers to DevLoop or `docs/LOOP-ENGINEERING.md`, which were archived on 2026-09-26.

### skill-craft 1.0.0

- Skills: review-coverage 0.3.2, shiploop 0.33.1, skill-interop 0.2.6

### review-coverage 0.3.2

- The retired `## Post-Implementation Residual Loop` heading is no longer read. A plan that has only that heading now reports a missing `## Review Coverage` section, matching plan-oversight, which refuses it too.
- Review Coverage now ships in the one skill-craft plugin: install skill-craft@whichguy and invoke /skill-craft:review-coverage.

### shiploop 0.33.1

- A saved run without a recorded `lint` option is now refused with the fresh-run hint instead of being read as `off`; new runs always record the option. Run records containing U+2028, U+2029 or U+0085 in any text now read back correctly (the reader split lines on those characters). An isolated workspace's source fingerprint now hashes the index's staged entries rather than the raw index file, so a timestamp-only index rewrite no longer looks like a source change. Workspace manifests written with the old fingerprint are refused with instructions. Git commands in workspace operations honour `SHIPLOOP_GIT_TIMEOUT` (seconds, default 45).
- On Claude, the plugin adds a `SessionStart` hook with the `compact` matcher. After the host compacts a bound session, the hook clears the run's last-packet record, so the next `next` prints the full packet with the run rules instead of the short repeat packet.
- ShipLoop now ships in the one skill-craft plugin: install skill-craft@whichguy and invoke /skill-craft:shiploop (Codex $skill-craft:shiploop). The host matrix names the new identities.

### skill-interop 0.2.6

- The marketplace section describes the one skill-craft plugin (skill-craft@whichguy, /skill-craft:<leaf>) that now carries every skill.

### improve 0.3.0-rc.6

- A review loop with a gate of two or more trivial reviews now completes after its first review when that review is trivial and satisfied, and the bundled Until Loop runtime sees from Git that the workspace content (tracked and untracked files, excluding ignored and runtime files) is unchanged since `start`. A second pass would only have reviewed the same tree. The complete packet reports `progress.unchanged_first_pass: true`. Any change, or a workspace outside Git, still needs two consecutive trivial reviews.

### shiploop 0.33.0

- Each run now ends with a learnings commit. The feature's `outcome.md` carries `## Learned`, `## Key considerations` and `## Open for the next run` sections, which the `release-verify` close requires to be filled in and uses as its commit message body. Intake and discovery packets quote the checkout's last three commit messages as inherited learnings to weigh before planning.
- A repeated `next` for the same action now prints a short packet: status, callback, keepalive marker, what changed since it was last printed, the stage references and the full stage prompt. The run-level rules (locators, recovery, delegation rule and the original request) become a reference to the run's `rules.md`. `next --full` prints everything, and a new action, a status change or a changed rules block prints the full packet. Packets now point at material instead of asking for a reread: "Read first" is now "Results this stage builds on", and the context index and bound Until Loop card are opened only when they are not already in context.
- A done `release-plan` now records `consumer_entry` (how a person reaches the result, and the repository files that create it), and ShipLoop refuses a release plan without one or whose files are missing. A Salesforce `lightning__Tab` target alone therefore no longer passes as a navigation entry. `release-check` runs the dry-run deploy and each post-release confirm command once, before the real deploy, so a confirm that cannot tell present from absent is fixed first. The Salesforce guide says to confirm tabs with `sf org list metadata --metadata-type CustomTab`. After a replan whose corrective items changed only non-code paths, each outer stage's packet names the delta and the result it accepted before the replan, so unchanged rows are cited rather than redone.
- Planning knowledge now outlives the run. Planning stages keep `docs/shiploop/` in the product repository up to date: `README.md` (index), the living `spec.md` with stable `R-<n>` requirement IDs, `environment.md`, `test-strategy.md`, and this run's `features/<slug>/` record (spec delta, plan, test spec, system tests, release plan, outcome). At `prepare`, each `test-spec`, `release-plan` and `release-verify`, ShipLoop refuses `done` until that close's files exist. It screens the files for credentials, refuses a living spec that drops an earlier committed requirement ID, and commits exactly `docs/shiploop/`. The workspace return always keeps `docs/shiploop/**`. Every packet names the knowledge home and the files its stage keeps current, so the next run starts from them.
- An Improve child whose first review is trivial and leaves the candidate unchanged now completes after that one pass. The import accepts a receipt with that single review when the terminal packet reports `unchanged_first_pass`, and cross-checks the claim against the tree ShipLoop recorded at `improve-bind`. Packets explain the one-pass case.
- A done `step-plan` now declares `paths`: the files or globs the item will change. When the item records no test command and every declared path is documentation, configuration or navigation metadata (package catalog `references/path-classes.json`; an unmatched path counts as code), ShipLoop records `test-spec` through `regression` as not applicable to that item instead of issuing seven empty stages and an Improve review. `implement` is refused if the real change reaches code or goes outside `paths`. An Improve review must commit the edits it makes: `improve-complete` refuses while files the review changed are uncommitted, unless the receipt's `no_commit` gives the user's or repository's instruction. The end-of-work review reruns every item's recorded test commands only when it changed files. An unchanged Improve result no longer needs a restated `final_result`.
- A recorded test command now passes only when it ran tests. ShipLoop reads the runner's summary (Jest, Vitest, pytest, unittest, Mocha, cargo, go, dotnet) and refuses a command that exits 0 after running no test, fewer than `min_tests`, or without showing each of its `ids`. A filter that matches nothing, such as `npm test -- -t <name>` printing "2 skipped", no longer counts as green. Step-plan test commands accept optional `ids` and `min_tests`. `test-red` is now script-checked too: the focused commands must fail inside a test, not before any test runs. Characterisation tests that already pass declare `red_na`.
- A stage that needs a person now reports `blocked` with `awaiting`: a question (`kind: answer`, with optional options) or steps only a person can take (`kind: present`, such as opening a page in a signed-in browser, with what to report back). The run stops quietly: the keepalive allows the stop, and `status` prints "Waiting on you". `resume` then requires the user's own reply with `--answer` or `--observed`. It refuses a bare "continue", records the reply in `decisions/<action>.md`, and shows it in the next packet. `release-verify` uses this for browser cases the host cannot sign in to, instead of looping. The deploy question is now one yes/no question whose yes covers this run only unless the user says "standing". The delivery authority accepts an optional `scope` (`run` or `standing`), and `standing` must be a repo policy.

### shiploop 0.32.2

- ShipLoop now says when its keepalive is not working: if a host session prints a
  second packet and the keepalive has never bound that session to the run, the
  command warns once on stderr and names the fix for that host (for example,
  restart Grok so its leader loads the plugin hooks).

### shiploop 0.32.1

- Core guidance no longer names a specific platform. SKILL.md points at the
  platform cards the coding guide lists instead of hard-coding them, and the i18n
  and delivery-authority examples use neutral wording. Platform detail stays in
  `references/platforms/`.

### shiploop 0.32.0

- A blocked result must now say who can unblock it: `blocked_by` is `user` (a
  decision only the user can make), `access` (a sign-in or permission the user must
  grant) or `external` (a service outside the run). Anything the run can fix itself
  (a missing tool, a failed install, a broken baseline, a failing test) is refused
  as blocked and repaired in the stage instead. The run's status reason and the
  keepalive log start with that category. Saved runs are unaffected.

  Discovery now checks access for every planned verification surface (the deploy
  target and each post-deploy browser, API or remote check), proves a route the run
  can use without the user, and asks for any missing sign-in once, up front. For
  Salesforce, browser checks open the page through `sf org open --url-only` from the
  org's existing CLI authentication instead of asking the user to log in.

  Also fixes 0.31.1 writing its callback-attempt counter into a saved run that is
  refused as retired.

### shiploop-e2e-audit 0.4.6

- Synthetic blocked results in the DAG replay now carry `blocked_by`, which
  ShipLoop requires on every new blocked result.

### shiploop 0.31.2

- The keepalive binds a session from a `shiploop` command only when that command
  drives the run (`init`, `next`, `resume`, `complete`, `improve-*`). A read-only
  query such as `hook-status`, `status` or `report` from another session no longer
  claims the run and keeps that other session looping on it.

### shiploop 0.31.1

- The keepalive no longer lets a busy run stop. Its progress check now counts
  refused callbacks (the model is fixing and resubmitting) and each pass of an
  active Improve review, not only accepted results, and a still-running host
  background task (a deploy, an install) keeps the turn going with "wait for it in
  this turn". Each stop counts the turn's continuations: near Grok's cap of 8 the
  reason asks harder not to stop, and the log records "continuation N/8". A
  refused callback now says the run is still active, and a second session gets a
  notice naming the owner instead of a silent stop.

## 2026-09-25

### shiploop 0.31.0

- New house-style guide. Discovery extracts the repository's coding conventions
  from tool configuration and busy files, each rule with `path:line` evidence,
  frequency and status, into a short repository-owned record. Step planning
  records a per-item match contract naming the nearest existing exemplars in its
  step-plan result; test authoring and implementation reread it, verification
  checks the diff against it, and carry-forward keeps the record current.
  Test authoring now also lists the item's step plan under Read first.
- A request that names where to deliver ("deploy it to my Salesforce developer
  org") is now the grant for this run: discovery resolves it to exactly one target,
  records it, and the run never stops to ask again or plans a work item just to
  record approval. ShipLoop asks only when the request leaves it open (no target,
  several or no matching targets, an unnamed production or shared target, or a
  destructive change), and then once, at intake or discovery, while independent
  work continues. Discovery and plan packets now link that guidance.

  The keepalive also binds a session from a `shiploop … --run-dir` command itself,
  so a model that filters the packet output (hiding the run marker) no longer
  loses the keepalive after a pause or block.

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
