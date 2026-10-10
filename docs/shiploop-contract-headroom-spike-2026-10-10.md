# Spike: Improve contract byte headroom, and the bytes of a look-back (2026-10-10)

Task S of batch 1012, read-only. Base `658ff4e3` (the local `origin/main` ref and this worktree's HEAD are the same commit; nothing was fetched). Nothing under `skills/`, `agents/` or the existing tests changed. No model, host CLI, browser, server or live run was started.

Evidence: `docs/experiments/commit-spike-20261010/` holds `contract-headroom.json`, `look-back.json` and the two scripts that wrote them. Repeat with:

```sh
PYTHONDONTWRITEBYTECODE=1 SHIPLOOP_PROGRESS=off python3 docs/experiments/commit-spike-20261010/measure_contract_headroom.py
PYTHONDONTWRITEBYTECODE=1 SHIPLOOP_PROGRESS=off GIT_CONFIG_NOSYSTEM=1 python3 docs/experiments/commit-spike-20261010/measure_look_back.py
```

Both take `--runs-root` and `--out`; the second also takes `--rev` (the skill-craft revision, default the full id of `658ff4e3`), `--backchain` and `--backchain-rev`. The first runs in about a second, the second in about 15. The skill-craft and backchain histories are read at those pinned revisions, so the files do not change when the worktree's HEAD moves (an earlier version read whatever HEAD was and did). Two consecutive runs wrote byte-identical files, and so did a run from a later branch head. Full-history spaced samples (section 4.3) remain point estimates of a spread, not values: moving the skill-craft revision two commits forward changed the plan-label brief variant's maximum from 19,169 to 5,461 bytes and its median from 1,920.5 to 1,054.5.

Corrections made after an independent review are listed in section 8; where a number below differs from the first version of this journal, section 8 says so.

## 1. Questions and the short answers

**Q1. Does the Improve-commit rule (plan section 2.2) fit in the frozen Improve contract, whose size is capped at `CONTRACT_BUDGET` (9,216 bytes)? Which carrier should hold it?**

- The rule costs **about 910 bytes, not about 350**. The sentence with `<command>` and `<path>` left as placeholders is 237 bytes, so the plan's 350 is not that sentence either (the design audit, item 14, estimated about 180 for the same addition); the estimate is not reproducible. The real `improve-commit` command line is 488 to 551 characters and the message path 205 to 220, so the plan's sentence measures 915 to 991 bytes on its own and adds 874 to 950 bytes to a real contract.
- The brief's premise "spec contract at 8,775 of 9,216" is a Codex gpt-6-luna contract (the `v1161-battleship-luna` run on 1.16.1; `test/shiploop_e2e/LEARNINGS.md`, "Verification of F3/F1 on 1.16.1"), not a Sonnet or Grok one. Today's Sonnet and Grok spec contracts have a median of 5,658 and a maximum of 6,052 bytes. That Luna spec contract is also the median of the 19 Luna contracts in section 3.6's supplement, which is why 8,775 appears there.
- On the 92 Improve children of 17 saved runs (rebuilt with the real builder), **none is over budget today and none goes over with the full rule** on the inline route. The margin is thin at two stages: after the full rule the tightest child at `carry-forward` has 131 bytes left, and 733 at `system-test-author`.
- The full rule fails on a delegated (ask-agent) child at `carry-forward` (157 bytes over), and fails at both thin stages when the checkout path is 100 characters longer. The pointer wording fails only one cell of that kind: the 8,135-byte `carry-forward` child, by 53 bytes, at +100 characters.
- A shorter wording that points at `parent-return.md` for the command costs **234 bytes** and leaves at least 847 bytes at every stage (559 on the delegated route). **Recommendation: carry the rule in the frozen contract's `authority`, in the pointer wording, with `_improve_start` writing the exact `improve-commit` command into `parent-return.md`.** Section 3.8 gives it per stage. The wording keeps the plan's "commit each iteration's changes only with": without "'s changes only", read next to the contract's retained "no empty commit", it would tell a child to commit no-change iterations.

**Q2. How many bytes would the look-back add to a printed head, and how often is it non-empty?**

- The block in the plan's format (two latest subjects, quoted lessons sections) is 288 to 545 bytes when no recent commit records lessons and 439 to 1,932 bytes when one does. On 16 saved E2E product repositories (219 positions) the medians are 456 to 461 and 783 to 1,075.
- Against a printed head whose median is 1,470 characters in the saved Claude runs (1,265 in the plan), that is +31% when always printed and +53% to +73% when lessons are present. The saved Grok runs print heads about four times as large (median 6,028 characters), where the same block is +8% and +13% to +18% (section 4.5).
- **It is empty almost everywhere in a fresh E2E repository.** With the extractor the plan names (label-only), 16 of 219 positions are non-empty: the last commit of each run. With an extractor that also reads `Key learning(s): text` on a line or mid-paragraph, 96 of 219. None of the 29 commits in those repositories that say "Key learning" or "Key learnings" writes it as a section of its own: 24 write a line `Key learnings: <text>` (23) or `Key learning: <text>` (1) and 5 put it mid-paragraph. This matters for the Improve commit gate as much as for the look-back (section 4.6).
- **In the skill-craft repository the answer depends on the label spelling.** With the plan's labels read label-only, the newest lessons-bearing commit is 482 commits back from `658ff4e3`. This repository writes the singular `Key learning: <text>` more than any other form (117 commits, including the two commits that carry this spike), and when that is read the newest is 13 back: none of the newest 10, 2 of the newest 100 and 122 of the newest 500 carry one. Over the newest 500 (every 25th commit as HEAD) the block is non-empty at 10 of 20 positions with every spelling read against 1 of 20 with the plan's labels. The first version of this journal said 482 without the qualification (section 8).

Status: the measurements are **firm** for the saved runs they cover. The verdicts for a Luna-class model and for the delegated route are **interim** (see section 5).

## 2. Method

| Step | What | Reuse |
|---|---|---|
| Builders | Listed every place ShipLoop builds an Until Loop contract | grep of `skills/shiploop/scripts` |
| Rebuild | For each completed Improve child in a saved run: the child's binding from `state.md` `improve_results`, its saved `opening.md`, then `shiploop_navigator.improve_start_contract` | the real builder; compared with the child's saved `start.json` |
| Size | `shiploop_loop_contract.compact_bytes` and `text_bytes` | no second serializer |
| Wordings | Replaced the existing callback clause of the rebuilt `authority` with each candidate wording and re-measured | in situ, so escaping and the child's real paths count |
| Command | The `improve-commit` line each child's saved parent packet printed (`packets/<action>-improve.md`); built with `navigator._callback` when no packet printed one | the 79 built commands that could be compared equal the printed line; the 5 Grok ones differ in the script path (Grok prints its installed-plugin path) |
| Look-back | `shiploop_knowledge_home.recent_commits` and `_sections` on real repositories, at many points in history, with skill-craft and backchain read at pinned revisions | one parser; a thin label normaliser turns `Label:` and bare labels into `## Label` before `_sections`; a wrapper makes `recent_commits` read as if a given commit were HEAD (checked equal to the unwrapped call at HEAD) |
| Printed heads | `metrics.tool_results` of the E2E harness on each run's `events.jsonl` | the harness's one reader of host tool results (Claude and Grok); no second parser |

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

| stage | n | bytes median | bytes max | headroom min | headroom median | headroom max | model-written median | ShipLoop text and paths, median | allowance printed, median |
|---|---|---|---|---|---|---|---|---|---|
| spec | 8 | 5,658 | 6,052 | 3,164 | 3,558 | 3,779 | 1,284 | 4,416 | 4,796 |
| test-strategy | 8 | 5,454 | 5,965 | 3,251 | 3,762 | 4,058 | 756 | 4,687 | 4,525 |
| plan | 8 | 5,520 | 6,363 | 2,853 | 3,696 | 4,027 | 699 | 4,809 | 4,403 |
| step-plan | 8 | 5,398 | 5,902 | 3,314 | 3,818 | 4,291 | 810 | 4,577 | 4,635 |
| test-spec | 8 | 5,012 | 5,727 | 3,489 | 4,204 | 4,471 | 666 | 4,325 | 4,887 |
| system-test-author | 18 | 5,454 | 7,533 | 1,683 | 3,762 | 4,397 | 1,116 | 4,309 | 4,903 |
| release-plan | 16 | 5,384 | 6,124 | 3,092 | 3,832 | 4,329 | 984 | 4,389 | 4,823 |
| carry-forward | 18 | 5,502 | 8,135 | 1,081 | 3,714 | 4,256 | 1,176 | 4,344 | 4,868 |

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
| `pointer_to_parent_return` | Rule and lessons requirement in the contract, keeping the plan's "changes only with"; the command lives in `parent-return.md`, whose path the sentence names once | n/a | 234 / 234 / 234 |
| `full_plan_text` placed in `work` | Appended to the work string, old clause kept | n/a | 916 / 948 to 956 / 976 |

The plan's sentence with literal `<command>` and `<path>` is 237 bytes. That does not reproduce the plan's "about 350" (and the design audit estimated about 180 for the same addition), so the origin of the estimate is unknown; what matters is that a real command is a median 517 characters. The first version of this journal said 237 "is where 350 came from"; that was a guess stated as fact (section 8).

Effect on the printed allowance (median by stage): today 4,403 to 4,903; with the full wording 3,497 to 3,989 (about 19% lower); with the pointer wording 4,169 to 4,669 (about 5% lower). The parent packet's "about N bytes together" line recomputes by itself because `improve_opening_allowance` calls the builder.

### 3.6 Fit by stage

Tightest child left after the rule, in bytes (negative means over budget; "over" counts children over). "Delegated" adds the `host-owner.md` row. "+100" lengthens the worktree and run-directory paths by 100 characters everywhere, in the contract and in the wording.

| stage | today, tightest | full: left (over) | full, delegated | full, +100 chars | pointer: left | pointer, delegated | pointer, +100 chars | lessons-only: left |
|---|---|---|---|---|---|---|---|---|
| spec | 3,164 | 2,258 (0) | 1,975 | 858 | 2,930 | 2,647 | 1,830 | 3,023 |
| test-strategy | 3,251 | 2,345 (0) | 2,062 | 945 | 3,017 | 2,734 | 1,917 | 3,110 |
| plan | 2,853 | 1,947 (0) | 1,664 | 447 | 2,619 | 2,336 | 1,419 | 2,712 |
| step-plan | 3,314 | 2,408 (0) | 2,125 | 1,008 | 3,080 | 2,797 | 1,980 | 3,173 |
| test-spec | 3,489 | 2,583 (0) | 2,300 | 1,183 | 3,255 | 2,972 | 2,155 | 3,348 |
| system-test-author | 1,683 | 733 (0) | 445 | **-467** | 1,449 | 1,161 | 549 | 1,542 |
| release-plan | 3,092 | 2,166 (0) | 1,878 | 766 | 2,858 | 2,570 | 1,758 | 2,951 |
| carry-forward | 1,081 | **131** (0) | **-157** | **-1,069** | 847 | 559 | **-53** | 940 |

Every negative cell is one child: the 8,135-byte `carry-forward` contract and the 7,533-byte `system-test-author` contract, both from the Grok run `r1-battleship-grok-none` (openings of 3,755 and 3,188 bytes). A refusal there is the existing size guard working as designed. The pointer wording goes over in one cell only: that `carry-forward` child, by 53 bytes, when the paths are 100 characters longer.

Older runs, supplement (as frozen then by older builders, not rebuilt; they show only how large a model-written opening can get): Sonnet 115 contracts in 13 runs, none with less headroom than the full wording needs. Grok 10 contracts in 3 runs: 1 with less headroom than the full wording needs. Contracts with no recorded host or model (`unknown ?`): 7 in 1 run, median 7,541, maximum 9,204, 1 with less headroom than the full wording needs and 1 with less than the pointer wording needs. **Codex gpt-6-luna: 19 contracts in 3 runs, median 8,775 bytes, maximum 15,368, 3 over budget as saved, 14 of 19 with less headroom than the full wording needs, 4 of 19 with less than the pointer needs.** That agrees with `test/shiploop_e2e/LEARNINGS.md` (Luna overshot a printed allowance by up to 2.6 times and converged in at most three `improve-start` refusals). For a Luna-class model the full wording would add refusals; the pointer wording would add far fewer.

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
| carry-forward | **fits only the shorter rule** | full leaves 131 inline and is 157 over on the delegated route; pointer leaves 847 (559) |

No stage is "does not fit" on the saved Sonnet and Grok sample. The Luna supplement is the reason not to read "fits" as safe margin.

### 3.8 Carrier recommendation

One wording for all eight stages (the builder has one `authority` string; per-stage text would be new complexity), chosen by the two thinnest stages: the **pointer wording in the frozen `authority`**. The script must also write the exact `improve-commit` line into `parent-return.md` (`_improve_start` already writes that file beside the receipt and lists it as a resource), so the pointer is true. The sentence is `The child never runs a ShipLoop callback except improve-commit; its command and the parent return are in <pr>: commit each iteration's changes only with that command; the message has a 'Key learnings' section and optional 'Learned-from: <full commit ID> <what it contributed>' lines. The parent runs the return after the terminal packet.` Task B may paste it: it keeps the plan's "changes only with" so that, next to the retained "no empty commit", a no-change iteration is not told to commit. (The first version of this sentence said "commit each iteration with a 'Key learnings' section" and measured 204 bytes; section 8.)

| stage | carrier | the number |
|---|---|---|
| spec | frozen contract, `authority`, pointer wording | +234 on a 5,658 median (6,052 max); tightest of 8 leaves 2,930; the full wording would also fit (2,258) |
| test-strategy | same | +234 on 5,454 (5,965); leaves 3,017 |
| plan | same, and the only possible carrier today | 0 of 8 plan packets print the command; +234 on 5,520 (6,363); leaves 2,619 |
| step-plan | same | +234 on 5,398 (5,902); leaves 3,080 |
| test-spec | same | +234 on 5,012 (5,727); leaves 3,255 |
| system-test-author | same; the full wording is not advised | pointer leaves 1,449 (1,161 delegated); full leaves 733 and goes 467 over at +100 path characters |
| release-plan | same | +234 on 5,384 (6,124); leaves 2,858 |
| carry-forward | same; the full wording does not fit the delegated route | pointer leaves 847 (559 delegated); full leaves 131 inline and is 157 over delegated |

Also, at no contract cost: change the Improve card's conditional ("When the ShipLoop packet prints an `improve-commit` command") to include a command named by the contract's authority. Do not use the work string: same bytes as `authority`, printed twice per packet. The existing "no empty commit" in the same authority text contradicts the plan's remote-change commit through `improve-commit` (section 2.3); the audit's item 14 already says to keep that exception out of the frozen text and put it in the command's packet line and refusal, which this measurement supports (every extra clause comes out of a 4.4K to 4.9K allowance).

## 4. Measurement 2: look-back bytes

### 4.1 The prototype (outside `skills/`)

- Block, plan format (section 2.4): header, the two latest commits as `- <full 40-hex id> <subject>`, then the lessons sections of the two latest lesson-bearing commits among the newest 10, each line quoted with `    | `.
- Block, the brief's variant: the two latest messages in full, plus the lessons sections of the two latest lesson-bearing commits not already shown.
- Extractors (case-sensitive, non-empty sections only, a final trailer paragraph of known trailer tokens dropped, credential-line screening not modelled):
  - **label-only, strict** (`strict_sections`): the plan's three forms (a `## Label` heading, a `Label:` alone on its line, a bare known label line), labels `Key learnings` and `Learned`.
  - **label-only, broad** (`broad_sections`): the same forms, labels also `Key learning`, `Learnings`, `Learning`, `Lessons`, `Lessons learned`, `Lessons from this pass`. It still reads none of the `Key learning: <text>` commits, because they have text on the label's line.
  - **inline-aware, plan labels** (`strict_inline_aware`): label-only first, else `Label: text` on a line or mid-paragraph, up to the next Improve label or a blank line.
  - **inline-aware, all spellings** (`broad_inline_aware`): the same with the broad labels. This is the extractor that reads every spelling the survey below found in use.
- **Which labels real commits use.** The first version of this journal counted `Key learnings` 112, `Learned` 27 and `Learnings` 11 for skill-craft and missed the spelling this repository writes most. `label_survey` in the script now counts, per repository, every line-start label with "learn" or "lesson" in it (at most six words), split into *alone* (a heading, `Label:` or a bare line) and *with text* (text on the same line). Commits, not lines. Whole history; skill-craft at `658ff4e3`, backchain at `865547b9`, the 16 E2E product repositories pooled:

| Label as written | Form | skill-craft | backchain | 16 E2E repositories |
|---|---|---|---|---|
| `Key learning` | with text | **117** | 0 | 1 |
| `Key learnings` | alone | 112 | 10 | 0 |
| `Key learnings` | with text | 38 | 0 | 23 |
| `Learned` | alone | 27 | 0 | 16 |
| `Learnings` | alone / with text | 11 / 14 | 0 | 0 |
| `Learning` | with text | 10 | **22** | 0 |
| `Lessons from this pass` | alone | 0 | 3 | 0 |
| `Lessons` | with text | 1 | 0 | 0 |
| `What was learned` | alone | 4 | 0 | 0 |
| ten more one- or two-commit spellings | | 11 | 2 | 0 |

  `What was learned` and the ten others (`LEARNINGS:`, `Process learning:`, `Learnings and limits`, `Key learning from the review step:` and similar) are not read by `broad_inline_aware`: 15 commits in skill-craft, 2 in backchain, none in the E2E repositories (the script lists them under `labels_not_read_by_broad`). Cross-check: every commit with a line-start label in the broad set is read by `broad_inline_aware` (329 of 329 in skill-craft, 35 of 35 in backchain, 40 of 40 in the E2E repositories).

### 4.2 Commits that carry lessons

"Plan labels" are `Key learnings` and `Learned`; "all spellings" are the broad set of section 4.1 (it adds the singular `Key learning`, `Learnings`, `Learning`, `Lessons` and two longer forms).

| Repository | Commits | Subject-only | Label-only, plan labels | Inline-aware, plan labels | Inline-aware, all spellings |
|---|---|---|---|---|---|
| skill-craft at `658ff4e3` | 1,297 | 140 | 139 (10.7%) | 177 (13.6%) | **332 (25.6%)** |
| backchain at `865547b9` | 151 | 7 | 10 | 10 | 35 (23.2%) |
| 16 E2E product repositories | 9 to 30 each (219) | 5 to 17 | **1 each** (the release-verify commit, always last) | 44 in all: 1 in 9 repos, 2 in one, 3 to 9 in six | 45 in all: 1 in 9 repos, 2 in one, 4 to 9 in six |

How far back the newest lessons-bearing commit is, and how many of the newest 10 / 100 / 500 commits carry one (as of HEAD):

| Repository | Newest, commits back: plan labels (label-only) / all spellings | Newest 10 / 100 / 500, plan labels | Newest 10 / 100 / 500, all spellings |
|---|---|---|---|
| skill-craft at `658ff4e3` | **482 / 13** | 0 / 0 / 2 | 0 / 2 / 122 |
| backchain at `865547b9` | 19 / 19 | 0 / 9 / 10 | 0 / 34 / 35 |
| 16 E2E product repositories | 0 / 0 | 1 / 1 / 1 in each (at the end of the run) | same |

In the six Sonnet repositories where Improve commits say "Key learnings" (r2 and r3 Battleship and Checkers, and 20261010 battleship-1 and checkers-1) the inline-aware count is 3, 9, 4, 7, 6 and 4 with the plan labels and 4, 9, 4, 7, 6 and 4 with all spellings (the extra one is the singular). The 16 repositories contain 29 commits that say "Key learning" or "Key learnings"; **0 of the 29 write it as a section of its own**. 23 write a line `Key learnings: <text>`, 1 writes `Key learning: <text>` (in `20261008/r2-battleship-sonnet`), and 5 (all in `20261010/battleship-1`) put it mid-paragraph ("Review: ... Plan: ... Key learnings: ... Remaining work: ..." in one paragraph). In skill-craft 112 of the 162 that say `Key learnings` are sections (38 are a line with text, 12 mid-paragraph) and a further 117 write the singular `Key learning: <text>` on a line; in backchain 10 of 10 `Key learnings` are sections and 22 more write `Learning: <text>`.

### 4.3 Block bytes

E2E product repositories, every commit taken as HEAD (219 positions in 16 repositories, so each is a moment a packet could print the block):

| Extractor | Format | All positions: min / median / max | When lessons are in the newest 10 | When none |
|---|---|---|---|---|
| label-only strict | plan format | 288 / 461 / 1,932 | 652 / 1,075 / 1,932 (n=16) | 288 / 456 / 545 (n=203) |
| label-only strict | brief (full messages) | 239 / 507 / 3,194 | 970 / 1,861 / 3,194 | n/a |
| inline-aware | plan format | 288 / 499 / 1,932 | 439 / 783 / 1,932 (n=96) | 288 / 461 / 545 (n=123) |
| inline-aware | brief (full messages) | 239 / 615 / 3,194 | 654 / 1,139 / 3,194 | n/a |

Reading all spellings in the E2E repositories gives the same 96 positions and medians within 5 bytes (plan format 787 with lessons against 783; brief 1,133 against 1,139), because only one commit there uses a spelling the plan labels do not (the singular).

skill-craft (verbose, prose-heavy messages) and backchain, plan format and brief variant, with the plan's label-only extractor on the left and all spellings (inline-aware) on the right. Each row is a set of points, not a population: **read the spread, not the median** (section 8 shows a two-commit shift moving the first row's brief maximum from 19,169 to 5,461).

| Repository and sampling | Points | Plan format, plan labels: min / median / max | Brief variant, plan labels | Lessons within newest 10 | Within 500 | Plan format, all spellings | Brief variant, all spellings | Within newest 10 | Within 500 |
|---|---|---|---|---|---|---|---|---|---|
| skill-craft, 10 evenly spaced over all history | 10 | 357 / 561 / 2,586 | 308 / 1,921 / 19,169 | 2 | 9 | 357 / 833 / 2,593 | 308 / 2,172 / 20,097 | 7 | 9 |
| skill-craft, 10 evenly spaced over the newest 100 | 10 | 528 / 642 / 769 | 1,508 / 4,681 / 7,207 | **0** | 10 | 597 / 673 / 1,980 | 2,256 / 4,681 / 7,207 | 1 | 10 |
| skill-craft, every 25th of the newest 500 | 20 | 513 / 610 / 1,416 | 1,433 / 6,642 / 10,656 | 1 | 20 | 519 / 1,091 / 3,215 | 1,433 / 6,642 / 11,678 | **10** | 20 |
| backchain, 10 evenly spaced | 10 | 310 / 433 / 1,584 | 539 / 3,202 / 5,901 | 3 | 9 | 310 / 590 / 1,584 | 539 / 3,202 / 5,901 | 5 | 9 |

Reading: the plan format is bounded (the subjects are short and a lessons section is a few lines). The brief's variant is cheap in an E2E repository (median 507 to 615) and about 7 times the plan format in skill-craft (4,681 against 642 at the median over the newest 100) because full messages there are long; **subjects plus lessons sections, not full messages, is the only form that stays small.** The block with no lessons is 288 to 818 bytes of header and two subjects.

### 4.4 How often the block is non-empty

| Where | Positions | Label-only, plan labels | Inline-aware, plan labels | Inline-aware, all spellings |
|---|---|---|---|---|
| 16 E2E repositories pooled | 219 | 16 (7%): always and only the final commit | 96 (44%) | 96 (44%) |
| of which the 6 Sonnet repositories whose Improve commits say Key learnings | 13 to 18 each | 1 each | 12 to 17 each | 12 to 17 each |
| of which the other 10 (the 2 r1 runs, the r2 Grok run and the 7 s6 runs, which build the hello case) | 9 to 30 each | 1 each | 1 to 3 each | 1 to 3 each |
| skill-craft, 10 points over the newest 100 | 10 | 0 | 0 | 1 |
| skill-craft, 20 points (every 25th of the newest 500) | 20 | 1 | 1 | 10 |
| backchain, 10 points over all history | 10 | 3 | 3 | 5 |

So in a fresh E2E repository the answer to "is the block ever non-empty" is: with the plan's extractor, only after the last stage; the in-run packets would print the empty-case block (about 460 bytes) or, if the block is printed only when lessons exist (the v4 plan statement), nothing.

### 4.5 Against the printed head

Printed heads from the saved runs' event logs: a tool result that starts with the navigator head line, read with the harness's own `metrics.tool_results` (Claude and Grok; the counter itself belongs to another task). The first version of this journal used a second, Claude-only parser and wrongly said Grok heads were not measurable (section 8). 421 heads in 18 saved runs (`printed_head.by_group` in `look-back.json`):

| Events carrying the head | Heads | Runs | Median characters | Quartiles | Max |
|---|---|---|---|---|---|
| Claude-shaped (`user` tool_result) | 368 | 16 | **1,470** | 830 / 2,723 | 6,906 |
| Grok-shaped (`tool_call_update`) | 53 | 3 | **6,028** | 5,292 / 6,301 | 7,068 |
| both | 421 | 18 | 1,562 | 972 / 3,924 | 7,068 |

`r2-battleship-grok-none` is in both rows: it ran in Grok and was resumed in Claude (9 Grok-shaped and 12 Claude-shaped heads). The plan's 1,265 is the figure the plan cites from the E2E fork's analysis.

**The pooled median mixes releases.** By ShipLoop version (from each run's `invocation.json`), Claude-shaped medians are 800 characters at 0.56.0 (41 heads, 2 runs), 1,535 at 0.57.0 (47, 3) and 1,499 at 0.58.0 (280, 11); Grok-shaped 5,622 (27, 1), 6,171 (9, 1) and 6,059 (17, 1). Per-run medians run from 348 (`20261008/r1-battleship-sonnet`) to 5,088 characters (`20261009/s6-after-spec`; 5,110 is the same median in bytes), and the two newest runs, `20261010`, give 1,163 and 772. Why a Grok head is about four times a Claude head was not investigated here: 31 of the 53 Grok heads end with the `=== end ShipLoop narrative ===` block against 23 of the 368 Claude heads, which does not explain a difference of that size.

Taking each host's median head:

| Block | Added to the Claude head (1,470) | Added to the Grok head (6,028) |
|---|---|---|
| plan format, no lessons (always printed) | +31% (456 to 461 bytes) | +8% |
| plan format, lessons present | +53% to +73% (783 to 1,075), up to +131% (1,932) | +13% to +18%, up to +32% |
| brief variant in an E2E repository | +34% to +42% overall, +77% to +127% with lessons | +8% to +10% overall, +19% to +31% with lessons |
| brief variant in a prose-heavy repository such as skill-craft | +318% (4,681 median over the newest 100) | +78% |

### 4.6 What this means for the plan

1. The "about 1K more" cost is a maximum: it is reached only when a lessons-bearing commit is in the newest 10. Today that is rare in E2E repositories (7% of positions with the plan's labels), and in skill-craft at `658ff4e3` it is absent from the newest 10 under every spelling (the newest is 13 commits back, written as the singular `Key learning:`). The first version said "absent in skill-craft's own recent history" for the plan's labels only; with the singular read, 10 of 20 sampled positions over the newest 500 are non-empty.
2. **The extractor decides both the look-back and the Improve gate, and the plan's three forms read none of the 29 real Improve "Key learning(s)" messages in the saved E2E repositories, and none of this repository's 117 singular `Key learning: <text>` commits.** Each already carries a learning, none as a section of its own. A "no Key learnings section" refusal built on `lesson_sections` as specified would refuse all 29 on the first attempt unless `Label:` also accepts text on the same line, which would still miss the 5 mid-paragraph ones. The spelling is part of it: this repository's most common form is the singular, backchain's is `Learning:`, and the Improve card says `Key learnings`. A rule that accepts only the plural would also refuse the two commits that carry this spike. Task B should either accept `Key learnings:` and `Key learning:` with text at a line start (24 of the 29, and 117 in skill-craft) and after a sentence boundary (the other 5), or make the refusal text and the contract wording name the one exact form to write (the contract wording already says `Key learnings`). Test fixtures for the gate need the plural line, the singular line, the mid-paragraph form and the heading form.
3. The look-back is worth building only once commits carry one readable form, and the pointer wording plus the Key learnings requirement is what makes that happen. Measure it again after slice B on the same harness; this spike is the baseline.

## 5. What was not measurable, and why

| Not measured | Why | Effect |
|---|---|---|
| Whether a child follows a contract-carried command | needs a live run | the wording is a hypothesis; the first live run after slice B tests it (`improve-commit` count and `model_commits`) |
| The 35% bypass rate itself | derived from commit classification in `audit.json`; I did not redo it from git | the arithmetic (14 of 40) and the contract text were checked |
| The delegated (ask-agent) route | no saved run used it | the cost is the real builder's `host-owner.md` row added to each child (+275 to +290); interim |
| Contracts for a Luna-class model under today's builder | only older, as-frozen contracts exist | the supplement shows direction, not today's bytes; interim |
| Real users' paths | the E2E harness path is the only source | sensitivity given per extra character (about 9, about 12 with the full wording) |
| Why a Grok head is about four times a Claude head | not investigated; the head format changed between releases and the hosts print differently | the Claude and Grok medians are reported separately (section 4.5); the Grok figure is from 3 runs |
| A pooled head median that holds for a future release | the pooled median mixes ShipLoop 0.56.0, 0.57.0 and 0.58.0 (Claude medians 800, 1,535, 1,499), and the E2E fork's packet diet will change heads again | interim; re-measure when the diet lands |
| Look-back with credential screening or the `none yet` unborn line | not modelled | small effect; the unborn case is a one-line block |
| Look-back after slice B | the section form does not exist yet | this is the baseline |

## 6. Findings

| # | Finding | Status | Evidence |
|---|---|---|---|
| 1 | The rule costs 874 to 950 bytes in the contract, not about 350, because of the real command (median 517 characters) and message path (median 215) | firm | `contract-headroom.json` `improve_all_stages.command_chars`, `plan_sentence_text_bytes`, `improve_by_stage.*.variants` |
| 2 | Every Improve stage fits the full rule on the inline route for all 92 sampled children; `carry-forward` and `system-test-author` have 131 and 733 bytes left | firm for the sample | `improve_by_stage.*.variants.full_plan_text` |
| 3 | The pointer wording (234 bytes, keeping "changes only with") fits every stage on both routes; recommended | firm for the sample, interim for the model's behaviour | same, `pointer_to_parent_return` |
| 4 | The delegated route puts `carry-forward` 157 bytes over with the full wording | interim (derived from the real row, no saved run) | `children_over_budget_ask_agent`, `min_headroom_after_ask_agent` |
| 5 | Luna-class openings leave 14 of 19 older contracts without room for the full wording | interim (older builders, as frozen) | `older_runs_saved_improve_contracts` |
| 6 | The plan-stage Improve child is told the command nowhere today | firm (8 of 8 saved packets) | `parent_packet_prints_improve_commit_by_stage` |
| 7 | 83 of 92 openings already restate "improve-commit" in their own Authority; the frozen text would let the template drop that | firm | `opening_authority_names_improve_commit` |
| 8 | A done-when edit also consumes contract headroom (309 bytes at test-strategy since 20261008) | firm | `different_from_saved` |
| 9 | The plan's three label forms read 0 of 29 real Improve "Key learning(s)" (24 are a one-line `Key learning(s): text`, 5 mid-paragraph) and none of skill-craft's 117 singular `Key learning: text` commits; a gate built on them would false-refuse the first attempt, and so would one that accepts only the plural | firm for the saved E2E repositories and skill-craft at `658ff4e3` | `look-back.json` `key_learnings_line_start_with_text_only`, `key_learnings_mid_paragraph_only`, `key_learning_singular_line_start_with_text`, `label_survey` |
| 10 | The look-back block is 288 to 545 bytes when empty and 439 to 1,932 when not; non-empty at 7% (label-only) or 44% (inline-aware) of E2E positions, and in skill-craft at 5% (plan labels) or 50% (all spellings) of positions over the newest 500; the brief's full-message variant is too large in prose-heavy repositories | firm for these repositories | section 4 |
| 11 | Claude-shaped heads have a median of 1,470 characters and Grok-shaped heads 6,028; the pooled figure mixes three ShipLoop releases | firm for the saved runs, interim as a basis for a future head | section 4.5, `printed_head.by_group` |

## 7. For the batch (not done here)

- Task B: put the pointer wording in `improve_start_contract`, write the command into `parent-return.md` in `_improve_start` (its present text says the child never runs the return, which stays true for `improve-complete`), change the Improve card conditional, and decide the extractor form and the one label spelling the contract and the gate name (finding 9: plural, singular, `Learning:`). Re-run `measure_contract_headroom.py` after the edit: its in-situ numbers become the real ones, and a size test should assert that the largest saved child still fits.
- The E2E fork's packet diet is untouched by this spike. The look-back waits for the baseline this spike gives; if printed only when non-empty it costs nothing in the common E2E case today.
- Open question for the owner, not for this spike: whether Luna-class runs should be protected by the shorter wording only.

## 8. Corrections after review (2026-10-10)

An independent reviewer reproduced these against the first version of this journal (`3c4657f8`). Status of each correction is firm unless marked. History is shared, so the messages of `2b57ec7a` and `3c4657f8` still carry the superseded figures below; this section supersedes them.

| # | First version said | Now | Evidence | Status |
|---|---|---|---|---|
| 1 | skill-craft's newest lessons-bearing commit is 482 back; "absent in skill-craft's own recent history"; label survey `Key learnings` 112, `Learned` 27, `Learnings` 11 | those figures hold only for the plan's labels read label-only. The repository's most common form is the singular `Key learning: <text>` (117 commits, none read by the plan's three forms), and backchain's is `Learning:` (22). With every spelling read the newest is 13 back, and the block is non-empty at 10 of 20 positions over the newest 500 (1 of 20 with the plan's labels) | `look-back.json` `repos.skill-craft.label_survey`, `newest_lesson_commit_index_at_head`, `lesson_commits_in_newest`; `repos.backchain (owner research repo).label_survey`; sections 4.1, 4.2, 4.6 | firm for `658ff4e3` |
| 2 | skill-craft rows measured at "`658ff4e3`" | the script read whatever HEAD the worktree was on, so a re-run at the branch head differed (1,299 commits, brief variant maximum 5,461 against 19,169, median 1,054.5 against 1,920.5, 1 against 2 non-empty positions in the newest 10). `--rev` (default the full id of `658ff4e3`) and `--backchain-rev` now pin both histories; the JSON records `repos.*.head` and `method.revisions` | re-run from the branch head matches the committed file | firm |
| 3 | printed heads: 368 Claude-shaped, median 1,470 characters; "Grok not measurable because its events carry no Claude-shaped tool results"; per-run medians 348 to 5,110 characters | the 368 and the 1,470 reproduce exactly. The Claude-only parser is replaced by `metrics.tool_results` (one reader, S-12), which also finds the Grok heads: 53 in 3 runs, median 6,028 characters. 5,110 was bytes; the characters are 5,088. The pooled median is tagged by release and event shape | section 4.5; `printed_head.by_group`, `per_run` | firm |
| 4 | the pointer wording says "commit each iteration with a 'Key learnings' section" and costs 204 bytes | the plan's sentence says "commit each iteration's changes only with <command>". The paraphrase dropped "'s changes only", which, read next to the retained "no empty commit", tells a child to commit no-change iterations. The wording now keeps it and costs 234 bytes; every pointer figure was re-measured (minimum left 847 inline, 559 delegated, 1 child 53 over at +100 path characters, allowance about 5% lower) | `contract-headroom.json` `variant_text`, `improve_by_stage.*.variants.pointer_to_parent_return`; sections 3.5, 3.6, 3.8 | firm |
| 5 | "237 is where 'about 350' came from"; the 8,775 premise left unexplained | the placeholder sentence is 237 bytes, the design audit estimated about 180, the plan says 350: the origin of 350 is not reproducible. 8,775 is a Codex Luna spec contract (1.16.1), not today's Sonnet or Grok one (median 5,658) | `test/shiploop_e2e/LEARNINGS.md`, "Verification of F3/F1 on 1.16.1"; `docs/experiments/commit-spec-design-20261010/design-and-audits.json` item 14 | firm |
| 6 | table 3.4 without the headroom maximum; usage without `--backchain`; "the other 10 (r1, Grok, hello)"; the `unknown ?` group of older contracts omitted | added: the headroom-max column, the flags, the exact label (2 r1 runs, the r2 Grok run and 7 s6 runs) and the `unknown ?` group (7 contracts, 1 run) | sections 3.4, 3.6, 4.4, the header | firm |
| 7 | the scripts had no guard against a silent false "fits" | `measure_contract_headroom.py` now asserts that the recommended wordings keep "changes only with" and that every wording adds bytes to every child, and exits naming the first reason when no child can be rebuilt. Three mutations went red (a wrong clause to replace: exit 1 with the reason; `apply_variant` returning the contract unchanged: exit 1 with "added no bytes"; the pointer wording without "changes only with": `AssertionError` at import). `measure_look_back.py` cross-checks its label survey against its broadest extractor (329 of 329, 35 of 35 and 40 of 40 commits with a broad label are read) | script output | firm |

Not changed, and why:

- **The quick tier is not fully green in a deeply nested worktree.** `test/shiploop-status-display.test.py` (`test_every_dry_run_packet_carries_the_block_inside_the_kept_head`) fails in this worktree with `8003 not less than 8000`: the worktree path is 94 characters and occurs once before the status-block end marker, so the marker lands at 8,003 against the 8,000 window. With the canonical 30-character checkout path it passes. The branch changes nothing under `skills/`, `agents/` or `test/`, so the failure is not from this diff; the test could compare against a path-independent bound, which is a separate change. `shiploop-chain-async` refuses to run with `GIT_CONFIG_NOSYSTEM` exported by the caller ("prepare refuses Git context environment overrides"), so the quick tier must be run without it; the look-back script's usage line sets it for that one command only.
- **The 88-of-92 fidelity check is reported, not asserted**: the four children that differ are listed under `different_from_saved` and explained (section 2), and a hard count would fail the first time a stage's text changed.
