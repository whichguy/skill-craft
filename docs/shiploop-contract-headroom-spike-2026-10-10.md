# Spike: Improve contract byte headroom, and the bytes of a look-back (2026-10-10)

Task S of batch 1012, read-only. Base `658ff4e3` (the local `origin/main` ref and this worktree's HEAD are the same commit; nothing was fetched). Nothing under `skills/`, `agents/` or the existing tests changed. No model, host CLI, browser, server or live run was started.

Evidence: `docs/experiments/commit-spike-20261010/` holds `contract-headroom.json`, `look-back.json` and the two scripts that wrote them. Repeat with:

```sh
PYTHONDONTWRITEBYTECODE=1 SHIPLOOP_PROGRESS=off python3 docs/experiments/commit-spike-20261010/measure_contract_headroom.py
PYTHONDONTWRITEBYTECODE=1 SHIPLOOP_PROGRESS=off GIT_CONFIG_NOSYSTEM=1 python3 docs/experiments/commit-spike-20261010/measure_look_back.py
```

Both take `--runs-root` and `--out`; the first runs in about a second, the second in about 25. Two consecutive runs wrote byte-identical files.

## 1. Questions and the short answers

**Q1. Does the Improve-commit rule (plan section 2.2) fit in the frozen Improve contract, whose size is capped at `CONTRACT_BUDGET` (9,216 bytes)? Which carrier should hold it?**

- The rule costs **about 910 bytes, not about 350**. The 350 estimate is the sentence with `<command>` and `<path>` left as placeholders (237 bytes). The real `improve-commit` command line is 488 to 551 characters and the message path 205 to 220, so the plan's sentence measures 915 to 991 bytes on its own and adds 874 to 950 bytes to a real contract.
- On the 92 Improve children of 17 saved runs (rebuilt with the real builder), **none is over budget today and none goes over with the full rule** on the inline route. The margin is thin at two stages: after the full rule the tightest child at `carry-forward` has 131 bytes left, and 733 at `system-test-author`.
- The full rule fails on a delegated (ask-agent) child at `carry-forward` (157 bytes over), and fails at both thin stages when the checkout path is 100 characters longer.
- A shorter wording that points at `parent-return.md` for the command costs **204 bytes** and leaves at least 877 bytes at every stage (589 on the delegated route). **Recommendation: carry the rule in the frozen contract's `authority`, in the pointer wording, with `_improve_start` writing the exact `improve-commit` command into `parent-return.md`.** Section 3.8 gives it per stage.

**Q2. How many bytes would the look-back add to a printed head, and how often is it non-empty?**

- The block in the plan's format (two latest subjects, quoted lessons sections) is 288 to 545 bytes when no recent commit records lessons and 439 to 1,932 bytes when one does. On 16 saved E2E product repositories (219 positions) the medians are 456 to 461 and 783 to 1,075.
- Against a printed head whose median is 1,470 characters in the saved runs (1,265 in the plan), that is +31% when always printed and +53% to +73% when lessons are present.
- **It is empty almost everywhere in a fresh E2E repository.** With the extractor the plan names (label-only), 16 of 219 positions are non-empty: the last commit of each run. With an extractor that also reads `Key learnings: text` on a line or mid-paragraph, 96 of 219. None of the 28 commits in those repositories that say "Key learnings" writes it as a section of its own: 23 write a line `Key learnings: <text>` and 5 put it mid-paragraph. This matters for the Improve commit gate as much as for the look-back (section 4.6).
- In the skill-craft repository itself the newest lessons-bearing commit is 482 commits back from HEAD.

Status: the measurements are **firm** for the saved runs they cover. The verdicts for a Luna-class model and for the delegated route are **interim** (see section 5).

## 2. Method

| Step | What | Reuse |
|---|---|---|
| Builders | Listed every place ShipLoop builds an Until Loop contract | grep of `skills/shiploop/scripts` |
| Rebuild | For each completed Improve child in a saved run: the child's binding from `state.md` `improve_results`, its saved `opening.md`, then `shiploop_navigator.improve_start_contract` | the real builder; compared with the child's saved `start.json` |
| Size | `shiploop_loop_contract.compact_bytes` and `text_bytes` | no second serializer |
| Wordings | Replaced the existing callback clause of the rebuilt `authority` with each candidate wording and re-measured | in situ, so escaping and the child's real paths count |
| Command | The `improve-commit` line each child's saved parent packet printed (`packets/<action>-improve.md`); built with `navigator._callback` when no packet printed one | the 79 built commands that could be compared equal the printed line; the 5 Grok ones differ in the script path (Grok prints its installed-plugin path) |
| Look-back | `shiploop_knowledge_home.recent_commits` and `_sections` on real repositories, at many points in history | one parser; a thin label normaliser turns `Label:` and bare labels into `## Label` before `_sections`; a wrapper makes `recent_commits` read as if a given commit were HEAD (checked equal to the unwrapped call at HEAD) |

Runs measured: 18 states under `20261008` (r1 to r3), `20261009` (s6) and `20261010`; 17 have completed Improve children (`r3-battleship-grok-none` has none). 92 children: 64 in 8 runs with `planning_review: stage` (all eight Improve stages), 28 in 9 runs with `none` (system-test-author, release-plan, carry-forward). 87 children are Claude Sonnet 5.5 and 5 are Grok 4.7. Every saved run used the inline route.

Fidelity: the rebuilt contract equals the saved `start.json` byte for byte for 88 of 92 children. The other four (r1 and r2 `test-strategy`) are 309 bytes larger when rebuilt: the stage's own done-when text, which `stage_exit` appends, grew between 20261008 and now. That is the same pressure the rule adds, from a different source: **any edit to a stage's `done_when` also consumes headroom** and needs the same check.

## 3. Measurement 1: Improve contract headroom

### 3.1 Where ShipLoop builds an Until Loop contract

| Builder | Used for | What its text says about committing |
|---|---|---|
| `shiploop_navigator.improve_start_contract` (called by `_improve_start` and `improve_opening_allowance`) | Every Improve child: spec, test-strategy, plan, step-plan, test-spec, system-test-author, release-plan, carry-forward. The plan stage adds a planning exit and repeat clause | "Commit policy: ... no empty commit ... The child never runs a ShipLoop callback: after the terminal packet the parent runs the return in `<parent-return.md>`" |
| `shiploop_test_loop._contract` (via `build_contract`; `listing_problem` sizes it) | test-green, regression and the other test-loop stages | "Do not commit, push, install or download anything" |
| `shiploop_quality.build_contract` | the static-checks quality loop | "Do not commit, push, install or download anything" |

The rule applies only to the first. From the saved contract files: the quality loop is 4,856 to 4,989 bytes (19 contracts, headroom at least 4,227) and the test loop 3,224 to 3,782 (37 contracts, headroom at least 5,434). Neither needs the rule.

### 3.2 What the contract says about committing today (the plan's claim, checked)

- **Confirmed:** 92 of 92 frozen contracts say "The child never runs a ShipLoop callback" and none names the `improve-commit` command line. The sentence is split across two string literals in `improve_start_contract`, so no test greps it; a change there trips no literal pin. The `DEFAULT_COMMIT_AUTHORITY` constants live only in two tests (`shiploop-actual-improve-cli`, `shiploop-full-runtime`) as sample runtime input; they are not the builder's text, so "update the pins" is not needed for this change.
- **The texts already disagree.** The non-inline (ask-agent) parent packet tells the worker to return "without executing ShipLoop callbacks other than improve-commit", while the frozen contract says it never runs a callback. The Improve card's rule ("When the ShipLoop packet prints an `improve-commit` command, write the commit message ... and run that command") is conditional on a printed command that a runtime packet never contains. The card's "Commit policy" bullet already requires a Key learnings label and says to cite prior commits.
- **The model is already carrying the rule by hand.** 83 of 92 openings name `improve-commit` in their own Authority section (for example "Commit scoped changes via improve-commit (message file commit-message.md)"); none mentions Key learnings (0 of 92). The opening's Authority section has a median of 145 bytes and a maximum of 400, which the model spends on this. Of the 9 that do not, 5 forbid committing outright ("Do not commit, push, ..."), 2 limit it and 2 say nothing about it.
- **The plan-stage child has no command anywhere.** All 8 saved `plan` parent packets print no `improve-commit` line (the `planning_reconcile` branch of `_render_improve` omits it). For that child the frozen contract is the only possible carrier.
- **The 35%.** It is 14 model-typed commits in Improve windows out of 26 `improve-commit` plus 14 (`docs/experiments/commit-audit-20261010/audit.json`, `saved_run_histories`). I checked the arithmetic and the text claim; I did not re-derive the commit classification from git.

### 3.3 What an Improve child receives, by place

| Place | Reaches the child | Counts against the budget | Copies per packet |
|---|---|---|---|
| `context.authority` | every active packet, via `until_loop_ephemeral._packet_context` | yes | 1 |
| `work` | every active packet in `_metadata` and again inside the `instruction` text built by `_active_packet` | yes | **2** |
| `context.resources` | locators only (never contents); a row costs its purpose text and its path plus 27 bytes of structure; the delegated route adds one row, 275 to 290 bytes | yes | 1 |
| Improve card `skills/improve/SKILL.md` (27,914 bytes) | only if the child opens it; named by a resource row and by the request's "Run the ShipLoop whole-skill subcall of the selected Improve card" | no | 0 |
| The parent packet (`_render_improve`) | the parent. In the inline route that is the same conversation until a context clear | no | 0 |
| `parent-return.md` beside the receipt | listed as a resource; the child opens it only if told | no (its resource row is already paid) | 0 |

Consequences: the same text costs the same bytes in `authority` and in `work`, but `work` is printed twice per packet. The card costs no contract bytes but is conditional and was already bypassed (the s6-after-spec probe: 3 children, 0 `improve-commit`s, per the audit). A file the contract already names costs only a pointer.

### 3.4 Headroom today, by stage (rebuilt with the real builder)

`headroom = CONTRACT_BUDGET - compact_bytes(contract)`; `allowance` is what `improve_opening_allowance` prints to the model for the four opening sections.

| stage | n | bytes median | bytes max | headroom min | headroom median | model-written median | ShipLoop text and paths, median | allowance printed, median |
|---|---|---|---|---|---|---|---|---|
| spec | 8 | 5,658 | 6,052 | 3,164 | 3,558 | 1,284 | 4,416 | 4,796 |
| test-strategy | 8 | 5,454 | 5,965 | 3,251 | 3,762 | 756 | 4,687 | 4,525 |
| plan | 8 | 5,520 | 6,363 | 2,853 | 3,696 | 699 | 4,809 | 4,403 |
| step-plan | 8 | 5,398 | 5,902 | 3,314 | 3,818 | 810 | 4,577 | 4,635 |
| test-spec | 8 | 5,012 | 5,727 | 3,489 | 4,204 | 666 | 4,325 | 4,887 |
| system-test-author | 18 | 5,454 | 7,533 | 1,683 | 3,762 | 1,116 | 4,309 | 4,903 |
| release-plan | 16 | 5,384 | 6,124 | 3,092 | 3,832 | 984 | 4,389 | 4,823 |
| carry-forward | 18 | 5,502 | 8,135 | 1,081 | 3,714 | 1,176 | 4,344 | 4,868 |

What varies:

- **The model-written opening is almost all of the variance.** Across all 92 children: 444 to 3,755 bytes (median 923) against a ShipLoop-fixed 4,189 to 4,833 (median 4,379). Median section sizes: Current context 480, Authority 145, Environment 173, Scope 143. The two largest contracts (8,135 and 7,533) are both the `r1-battleship-grok-none` run, whose openings are 3,755 and 3,188 bytes. The largest Sonnet contract is 6,363.
- **Path length.** The worktree path is 95 to 110 characters in these runs; it occurs 7 to 10 times in a contract and the run directory 1 to 3 times, so each extra path character costs about 9 bytes today and about 12 with the full wording (which prints the command and the message path again). The E2E harness paths are not short, but a user's checkout can be longer.
- **Resources.** Inline: 8 rows. The delegated route adds `host-owner.md`: +275 to +290 bytes. No saved run used it, so this is the real builder's row added to each child, not an observed run.
- **Request text.** `context.request` holds the model's "Current context" section: 639 to 2,736 bytes at `carry-forward` (median 997) and 850 to 1,559 at `spec`.
- ShipLoop's fixed text differs by stage (medians 4,309 at `system-test-author` to 4,809 at `plan`): each stage appends its own done-when criteria, and `plan` adds a planning exit and repeat clause.

### 3.5 What each wording adds, measured in situ

All wordings replace the existing clause "The child never runs a ShipLoop callback: after the terminal packet the parent runs the return in `<pr>`". `{command}` is the child's real `improve-commit` line, `{path}` its message path, `{pr}` its `parent-return.md` path. Exact texts are in `contract-headroom.json` `variant_text`.

| Wording | Idea | Text alone, median | Added to the contract: min / median / max |
|---|---|---|---|
| `full_plan_text` | The plan's sentence verbatim, then the existing return clause | 953 | 874 / 906 to 914 / 950 |
| `full_path_once` | Same, the message path stated once (the command already has `--message=`) | n/a | 677 / 701 to 707 / 722 |
| `lessons_only` | Only the lessons requirement; assumes the command is carried elsewhere (it is not today) | n/a | 141 / 141 / 141 |
| `pointer_to_parent_return` | Rule and lessons requirement in the contract; the command lives in `parent-return.md`, whose path the sentence names once | n/a | 204 / 204 / 204 |
| `full_plan_text` placed in `work` | Appended to the work string, old clause kept | n/a | 916 / 948 to 956 / 976 |

The plan's sentence with literal `<command>` and `<path>` is 237 bytes: that is where "about 350" came from. A real command is a median 517 characters.

Effect on the printed allowance (median by stage): today 4,403 to 4,903; with the full wording 3,497 to 3,989 (about 19% lower); with the pointer wording 4,199 to 4,699 (about 4% lower). The parent packet's "about N bytes together" line recomputes by itself because `improve_opening_allowance` calls the builder.

### 3.6 Fit by stage

Tightest child left after the rule, in bytes (negative means over budget; "over" counts children over). "Delegated" adds the `host-owner.md` row. "+100" lengthens the worktree and run-directory paths by 100 characters everywhere, in the contract and in the wording.

| stage | today, tightest | full: left (over) | full, delegated | full, +100 chars | pointer: left | pointer, delegated | pointer, +100 chars | lessons-only: left |
|---|---|---|---|---|---|---|---|---|
| spec | 3,164 | 2,258 (0) | 1,975 | 858 | 2,960 | 2,677 | 1,860 | 3,023 |
| test-strategy | 3,251 | 2,345 (0) | 2,062 | 945 | 3,047 | 2,764 | 1,947 | 3,110 |
| plan | 2,853 | 1,947 (0) | 1,664 | 447 | 2,649 | 2,366 | 1,449 | 2,712 |
| step-plan | 3,314 | 2,408 (0) | 2,125 | 1,008 | 3,110 | 2,827 | 2,010 | 3,173 |
| test-spec | 3,489 | 2,583 (0) | 2,300 | 1,183 | 3,285 | 3,002 | 2,185 | 3,348 |
| system-test-author | 1,683 | 733 (0) | 445 | **-467** | 1,479 | 1,191 | 579 | 1,542 |
| release-plan | 3,092 | 2,166 (0) | 1,878 | 766 | 2,888 | 2,600 | 1,788 | 2,951 |
| carry-forward | 1,081 | **131** (0) | **-157** | **-1,069** | 877 | 589 | **-23** | 940 |

Every negative cell is one child: the 8,135-byte `carry-forward` contract and the 7,533-byte `system-test-author` contract, both from the Grok run `r1-battleship-grok-none` (openings of 3,755 and 3,188 bytes). A refusal there is the existing size guard working as designed.

Older runs, supplement (as frozen then by older builders, not rebuilt; they show only how large a model-written opening can get): Sonnet 115 contracts in 13 runs, none with less headroom than the full wording needs. Grok 10 contracts in 3 runs: 1 with less headroom than the full wording needs. **Codex gpt-6-luna: 19 contracts in 3 runs, median 8,775 bytes, maximum 15,368, 3 over budget as saved, 14 of 19 with less headroom than the full wording needs, 4 of 19 with less than the pointer needs.** That agrees with `test/shiploop_e2e/LEARNINGS.md` (Luna overshot a printed allowance by up to 2.6 times and converged in at most three `improve-start` refusals). For a Luna-class model the full wording would add refusals; the pointer wording would add far fewer.

### 3.7 Verdicts

Definitions (no thresholds invented): **fits** means no sampled child is over budget on the inline route and on the delegated route. "Fits with the full rule" uses the full wording; "fits only the shorter rule" means the pointer wording fits both routes and the full wording does not; "does not fit" means a child is over even with the pointer.

| stage | verdict | number behind it |
|---|---|---|
| spec | fits with the full rule | tightest left 2,258 (delegated 1,975) |
| test-strategy | fits with the full rule | 2,345 (2,062) |
| plan | fits with the full rule | 1,947 (1,664) |
| step-plan | fits with the full rule | 2,408 (2,125) |
| test-spec | fits with the full rule | 2,583 (2,300) |
| system-test-author | fits with the full rule, thinly | 733 (445); one child over at +100 path characters |
| release-plan | fits with the full rule | 2,166 (1,878) |
| carry-forward | **fits only the shorter rule** | full leaves 131 inline and is 157 over on the delegated route; pointer leaves 877 (589) |

No stage is "does not fit" on the saved Sonnet and Grok sample. The Luna supplement is the reason not to read "fits" as safe margin.

### 3.8 Carrier recommendation

One wording for all eight stages (the builder has one `authority` string; per-stage text would be new complexity), chosen by the two thinnest stages: the **pointer wording in the frozen `authority`**. The script must also write the exact `improve-commit` line into `parent-return.md` (`_improve_start` already writes that file beside the receipt and lists it as a resource), so the pointer is true. The sentence is `The child never runs a ShipLoop callback except improve-commit; its command and the parent return are in <pr>: commit each iteration with a 'Key learnings' section and optional 'Learned-from: <full commit ID> <what it contributed>' lines in the message. The parent runs the return after the terminal packet.`

| stage | carrier | the number |
|---|---|---|
| spec | frozen contract, `authority`, pointer wording | +204 on a 5,658 median (6,052 max); tightest of 8 leaves 2,960; the full wording would also fit (2,258) |
| test-strategy | same | +204 on 5,454 (5,965); leaves 3,047 |
| plan | same, and the only possible carrier today | 0 of 8 plan packets print the command; +204 on 5,520 (6,363); leaves 2,649 |
| step-plan | same | +204 on 5,398 (5,902); leaves 3,110 |
| test-spec | same | +204 on 5,012 (5,727); leaves 3,285 |
| system-test-author | same; the full wording is not advised | pointer leaves 1,479 (1,191 delegated); full leaves 733 and goes 467 over at +100 path characters |
| release-plan | same | +204 on 5,384 (6,124); leaves 2,888 |
| carry-forward | same; the full wording does not fit the delegated route | pointer leaves 877 (589 delegated); full leaves 131 inline and is 157 over delegated |

Also, at no contract cost: change the Improve card's conditional ("When the ShipLoop packet prints an `improve-commit` command") to include a command named by the contract's authority. Do not use the work string: same bytes as `authority`, printed twice per packet. The existing "no empty commit" in the same authority text contradicts the plan's remote-change commit through `improve-commit` (section 2.3); the audit's item 14 already says to keep that exception out of the frozen text and put it in the command's packet line and refusal, which this measurement supports (every extra clause comes out of a 4.4K to 4.9K allowance).

## 4. Measurement 2: look-back bytes

### 4.1 The prototype (outside `skills/`)

- Block, plan format (section 2.4): header, the two latest commits as `- <full 40-hex id> <subject>`, then the lessons sections of the two latest lesson-bearing commits among the newest 10, each line quoted with `    | `.
- Block, the brief's variant: the two latest messages in full, plus the lessons sections of the two latest lesson-bearing commits not already shown.
- Extractors: **label-only, strict** (the plan's three forms: a `## Label` heading, a `Label:` alone on its line, a bare known label line; labels `Key learnings` and `Learned`), **label-only, broad** (also `Key learning`, `Learnings`, `Lessons`, `Lessons learned`, `Lessons from this pass`), and **inline-aware** (label-only first, else `Label: text` on a line or mid-paragraph, up to the next Improve label). Case-sensitive; non-empty sections only; a final trailer paragraph (known trailer tokens only) dropped. Credential-line screening is not modelled.
- Which labels real commits use (whole-history counts): skill-craft `Key learnings` 112, `Learned` 27, `Learnings` 11; backchain `Key learnings` 10, `Lessons from this pass` 3; the E2E repositories `Learned` once each (the release-verify knowledge commit) and `Key learnings` only as `Key learnings: <text>` on one line or mid-paragraph.

### 4.2 Commits that carry lessons

| Repository | Commits | Subject-only | Label-only lessons (strict) | Inline-aware | Newest lessons commit, commits back from HEAD | In newest 10 / 100 / 500 (strict) |
|---|---|---|---|---|---|---|
| skill-craft at `658ff4e3` | 1,297 | 140 | 139 (10.7%) | 177 (13.6%) | **482** | 0 / 0 / 2 |
| backchain (owner research repo) | 151 | 7 | 10 | 10 | 19 | 0 / 9 / 10 |
| 16 E2E product repositories | 9 to 30 each | 5 to 17 | **1 each** (the release-verify commit, always last) | 1 in 9 repos, 2 in one, 3 to 9 in six | 0 | 1 / 1 / 1 in each (at the end of the run) |

In the six Sonnet repositories where Improve commits say "Key learnings" (r2 and r3 Battleship and Checkers, and 20261010 battleship-1 and checkers-1) the inline-aware count is 3, 9, 4, 7, 6 and 4. The 16 repositories contain 28 commits that say "Key learnings"; **0 of the 28 write it as a section of its own**. 23 write a line `Key learnings: <text>` and 5 (all in `20261010/battleship-1`) put it mid-paragraph ("Review: ... Plan: ... Key learnings: ... Remaining work: ..." in one paragraph). In skill-craft 112 of 162 are sections (38 are a line with text, 12 mid-paragraph) and in backchain 10 of 10 are sections.

### 4.3 Block bytes

E2E product repositories, every commit taken as HEAD (219 positions in 16 repositories, so each is a moment a packet could print the block):

| Extractor | Format | All positions: min / median / max | When lessons are in the newest 10 | When none |
|---|---|---|---|---|
| label-only strict | plan format | 288 / 461 / 1,932 | 652 / 1,075 / 1,932 (n=16) | 288 / 456 / 545 (n=203) |
| label-only strict | brief (full messages) | 239 / 507 / 3,194 | 970 / 1,861 / 3,194 | n/a |
| inline-aware | plan format | 288 / 499 / 1,932 | 439 / 783 / 1,932 (n=96) | 288 / 461 / 545 (n=123) |
| inline-aware | brief (full messages) | 239 / 615 / 3,194 | 654 / 1,139 / 3,194 | n/a |

skill-craft (verbose, prose-heavy messages) and backchain, plan format and brief variant:

| Repository and sampling | Points | Plan format: min / median / max | Brief variant: min / median / max | Lessons within newest 10 (strict) | Within 500 |
|---|---|---|---|---|---|
| skill-craft, 10 evenly spaced over all history | 10 | 357 / 561 / 2,586 | 308 / 1,921 / 19,169 | 2 | 9 |
| skill-craft, 10 evenly spaced over the newest 100 | 10 | 528 / 642 / 769 | 1,508 / 4,681 / 7,207 | **0** | 10 |
| skill-craft, every 25th of the newest 500 | 20 | 513 / 610 / 1,416 | 1,433 / 6,642 / 10,656 | 1 | 20 |
| backchain, 10 evenly spaced | 10 | 310 / 433 / 1,584 | 539 / 3,202 / 5,901 | 3 | 9 |

Reading: the plan format is bounded (the subjects are short and a lessons section is a few lines). The brief's variant is cheap in an E2E repository (median 507 to 615) and about 7 times the plan format in skill-craft (4,681 against 642 at the median over the newest 100) because full messages there are long; **subjects plus lessons sections, not full messages, is the only form that stays small.** The block with no lessons is 288 to 818 bytes of header and two subjects.

### 4.4 How often the block is non-empty

| Where | Positions | Label-only strict | Inline-aware |
|---|---|---|---|
| 16 E2E repositories pooled | 219 | 16 (7%): always and only the final commit | 96 (44%) |
| of which the 6 Sonnet repositories whose Improve commits say Key learnings | 13 to 18 each | 1 each | 12 to 17 each |
| of which the other 10 (r1, Grok, hello) | 9 to 30 each | 1 each | 1 to 3 each |
| skill-craft, newest 100 | 10 | 0 | 0 |
| backchain, all history | 10 | 3 | 3 |

So in a fresh E2E repository the answer to "is the block ever non-empty" is: with the plan's extractor, only after the last stage; the in-run packets would print the empty-case block (about 460 bytes) or, if the block is printed only when lessons exist (the v4 plan statement), nothing.

### 4.5 Against the printed head

Printed heads from the saved runs' event logs (a Bash tool result that starts with the navigator head line; the counter itself belongs to another task): 368 heads in 16 saved runs (all Claude-shaped; one of them, `r2-battleship-grok-none`, resumed in Claude and its heads come from that phase), **median 1,470 characters** (quartiles 830 and 2,723, maximum 6,906; per-run medians 348 to 5,110). The plan's 1,265 is the figure the plan cites from the E2E fork's analysis. Taking 1,470:

| Block | Added to the head, median |
|---|---|
| plan format, no lessons (always printed) | +31% (456 to 461 bytes) |
| plan format, lessons present | +53% to +73% (783 to 1,075), up to +131% (1,932) |
| brief variant in an E2E repository | +34% to +42% overall, +77% to +127% with lessons |
| brief variant in a prose-heavy repository such as skill-craft | +318% (4,681 median over the newest 100) |

### 4.6 What this means for the plan

1. The "about 1K more" cost is a maximum: it is reached only when a lessons-bearing commit is in the newest 10, which today is rare in E2E repositories and absent in skill-craft's own recent history.
2. **The extractor decides both the look-back and the Improve gate, and the plan's three forms read none of the 28 real Improve messages.** Each of the 28 already carries a learning, none as a section of its own. A "no Key learnings section" refusal built on `lesson_sections` as specified would refuse all 28 on the first attempt unless `Label:` also accepts text on the same line, which would still miss the 5 mid-paragraph ones. Task B should either accept `Key learnings: <text>` at a line start (23 of 28) and after a sentence boundary (the other 5), or make the refusal text and the contract wording name the exact form to write. Test fixtures for the gate need both forms.
3. The look-back is worth building only once commits carry sections, and the pointer wording plus the Key learnings requirement is what makes that happen. Measure it again after slice B on the same harness; this spike is the baseline.

## 5. What was not measurable, and why

| Not measured | Why | Effect |
|---|---|---|
| Whether a child follows a contract-carried command | needs a live run | the wording is a hypothesis; the first live run after slice B tests it (`improve-commit` count and `model_commits`) |
| The 35% bypass rate itself | derived from commit classification in `audit.json`; I did not redo it from git | the arithmetic (14 of 40) and the contract text were checked |
| The delegated (ask-agent) route | no saved run used it | the cost is the real builder's `host-owner.md` row added to each child (+275 to +290); interim |
| Contracts for a Luna-class model under today's builder | only older, as-frozen contracts exist | the supplement shows direction, not today's bytes; interim |
| Real users' paths | the E2E harness path is the only source | sensitivity given per extra character (about 9, about 12 with the full wording) |
| Printed-head bytes for Grok | its event lines carry no Claude-shaped tool results; the two Grok-only runs gave none | the pooled median is Claude only |
| Look-back with credential screening or the `none yet` unborn line | not modelled | small effect; the unborn case is a one-line block |
| Look-back after slice B | the section form does not exist yet | this is the baseline |

## 6. Findings

| # | Finding | Status | Evidence |
|---|---|---|---|
| 1 | The rule costs 874 to 950 bytes in the contract, not about 350, because of the real command (median 517 characters) and message path (median 215) | firm | `contract-headroom.json` `improve_all_stages.command_chars`, `plan_sentence_text_bytes`, `improve_by_stage.*.variants` |
| 2 | Every Improve stage fits the full rule on the inline route for all 92 sampled children; `carry-forward` and `system-test-author` have 131 and 733 bytes left | firm for the sample | `improve_by_stage.*.variants.full_plan_text` |
| 3 | The pointer wording (204 bytes) fits every stage on both routes; recommended | firm for the sample, interim for the model's behaviour | same, `pointer_to_parent_return` |
| 4 | The delegated route puts `carry-forward` 157 bytes over with the full wording | interim (derived from the real row, no saved run) | `children_over_budget_ask_agent`, `min_headroom_after_ask_agent` |
| 5 | Luna-class openings leave 14 of 19 older contracts without room for the full wording | interim (older builders, as frozen) | `older_runs_saved_improve_contracts` |
| 6 | The plan-stage Improve child is told the command nowhere today | firm (8 of 8 saved packets) | `parent_packet_prints_improve_commit_by_stage` |
| 7 | 83 of 92 openings already restate "improve-commit" in their own Authority; the frozen text would let the template drop that | firm | `opening_authority_names_improve_commit` |
| 8 | A done-when edit also consumes contract headroom (309 bytes at test-strategy since 20261008) | firm | `different_from_saved` |
| 9 | The plan's three label forms read 0 of 28 real Improve "Key learnings" (23 are a one-line `Key learnings: text`, 5 mid-paragraph); a gate built on them would false-refuse the first attempt | firm for the saved E2E repositories | `look-back.json` `key_learnings_line_start_with_text_only`, `key_learnings_mid_paragraph_only` |
| 10 | The look-back block is 288 to 545 bytes when empty and 439 to 1,932 when not; non-empty at 7% (label-only) or 44% (inline-aware) of E2E positions; the brief's full-message variant is too large in prose-heavy repositories | firm for these repositories | section 4 |

## 7. For the batch (not done here)

- Task B: put the pointer wording in `improve_start_contract`, write the command into `parent-return.md` in `_improve_start` (its present text says the child never runs the return, which stays true for `improve-complete`), change the Improve card conditional, and decide the extractor form (finding 9). Re-run `measure_contract_headroom.py` after the edit: its in-situ numbers become the real ones, and a size test should assert that the largest saved child still fits.
- The E2E fork's packet diet is untouched by this spike. The look-back waits for the baseline this spike gives; if printed only when non-empty it costs nothing in the common E2E case today.
- Open question for the owner, not for this spike: whether Luna-class runs should be protected by the shorter wording only.
