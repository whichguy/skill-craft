# Where ShipLoop's run-created skills should live, and how they reach the inner loop

Research for the owner's question of 2026-11-22: a named skills folder that ShipLoop owns, linked into each
host's project skill location, or a location declared in AGENTS.md, so that skills created during a run are clear
and are reused by the later work items of that run. Read-only research plus no-model Codex probes. Nothing
committed. Written 2026-11-22 by a research agent; every documentation page below was read on 2026-11-22.

## Answer in one paragraph

A named folder linked into the hosts' project skill folders works for sessions that start in the product
repository **after** the skill is committed there. Claude Code follows a linked skill folder (documented). Codex
follows relative, absolute and whole-directory links (measured, probes 01 and 03). But neither host would show a
skill created mid-run to the running session. ShipLoop's default route builds in a sibling worktree,
`<repo-parent>/.shiploop-runs/<repo>-<stamp>/worktree`, and no host treats that worktree as a project skill
location of a session started in the user's checkout (Codex: probe 05; Claude Code: its documented search covers
only the start directory, its parents up to the repository root, and folders below it). AGENTS.md cannot declare
a skill location that Claude Code or Codex loads. It is read as instructions only (probe 01 shows the text arriving
and no new root; probe 07 shows `skills.config` cannot add a skill either). And it is read at session start from
the session's own checkout, not from the worktree. So reuse inside the run needs ShipLoop's script to hand each
skill's name, description and path to the stage that should use it (option D). The agentskills.io client guide
describes this same pattern as file-read activation. Keep the named folder for clarity. Add links only if the owner
wants sessions outside ShipLoop to list the skills natively.

## What ShipLoop does today (verified)

| Fact | Where |
|---|---|
| `step-plan` lists each step's helper skills `{"name", "why", "locator", "stages"}`; implement's Step block, the test and document packets' "Skills for this stage" line and the review's "Skills for this review" line print them by value | `skills/shiploop/scripts/shiploop_navigator.py` `_skills_line`, `_document_step_lines`, `_review_skills_lines`; `references/testing-and-documentation.md` "Reusable product skills" |
| `step-plan` is told to "reread the host's skills and the repository's skill index (an earlier item may have added one)": the model must go and look | `skills/shiploop/scripts/shiploop_prompts.py`, step-plan `skills` bullet |
| `carry-forward` records `skill` = `{"decision": none/reuse/update/create, "reason", "path", "evidence", "index"}`; for update/create ShipLoop refuses a `path` that is not an existing `SKILL.md` with `name` and `description` frontmatter, or empty `evidence` | `_check_skill_decision` (called from `_inner_gates`) |
| On accept ShipLoop commits `path`'s parent folder plus the `index` files as their own commit (`feat(skill): ...`), before the knowledge close | `_skill_commit`, called in `accept_effects` before `_knowledge_close`; `shiploop_git.commit_paths` stages exactly the given paths |
| Default location `skills/<name>/SKILL.md` "in WORKTREE", unless the repository has a layout; registered as a line in `KNOWLEDGE/environment.md` `## Skills` plus a link from the repository skill index (README or AGENTS.md); never global | `shiploop_prompts.py` carry-forward "Skill decision" items 3 and 6; `references/carry-forward.md` "Decide on a reusable skill"; `shiploop_knowledge_home.py` `SECTIONS` (`environment.md` has `Skills`) |
| Packets list `environment.md` as path, size and outline only, not its text, so the `## Skills` entries are named, not handed over | `shiploop_knowledge_home.py` `READS` (and its comment) |
| A path with a part named `.git`, `.shiploop`, `.until-loop`, `.shiploop-improve`, `.worktrees`, `.shiploop-workspaces` or `.shiploop-runs` is a protected runtime path: never committed in a workspace and excluded from the return. So the named folder cannot be `.shiploop/skills` | `skills/shiploop/scripts/shiploop_workspace.py` `FORBIDDEN_PARTS`, `_forbidden`, `_normal_paths`, `never_committed` |
| The default start is `workspace start`. It creates `<main-checkout-parent>/.shiploop-runs/<name>-<stamp>/worktree` (`git worktree add`) and runs `init --repo <worktree> --execution-mode navigator-worktree`, so `state["repo"]` is the worktree. In-place `init` (`execution_mode` `navigator`) runs only when the user explicitly asks | `shiploop_workspace.py` `default_root`, `prepare`; `shiploop_protocol.py` workspace `start`; `shiploop_navigator.py` `new_state`; `skills/shiploop/SKILL.md` "Start or resume" |
| The host session stays where it was started. ShipLoop launches no model process: "A worktree isolates files, not the model session"; "Worktree creation is local and does not re-root the host conversation" | `skills/shiploop/SKILL.md`; `references/host-matrix.md` |
| E2E sessions start in the case checkout: `run.py` spawns hosts with `cwd=work` (`work = out / "work"`), and Codex gets `-C <cwd>` | `test/shiploop_e2e/run.py`; `test/shiploop_e2e/hosts.py` `CodexHost.argv` |
| The workspace return carries symlinks as their own kind (`symlink`, mode 120000). Read in source; not exercised here | `shiploop_workspace.py` `_untracked`, `_working_path_object_id`, `_file_row` |

## Facts by host

"Doc" means the vendor page, read 2026-11-22. "Probe NN" means a render in `probe/out/summary.txt`, below. "Source"
means the open-source Codex code at tag `rust-v0.171.0`, read with `gh api` on 2026-11-22. Each cell is marked
unknown where it is not settled.

| Host (version here) | Project skill paths | Links followed | When discovery happens | What AGENTS.md can do |
|---|---|---|---|---|
| **Claude Code** (2.1.330) | `.claude/skills/<name>/SKILL.md` in the start directory and every parent up to the repository root. Folders below the start directory load the first time Claude reads or edits a file there. An `--add-dir`/`/add-dir` directory's own `.claude/skills/` also loads. Plugins load from `<plugin>/skills/`. There is no setting that adds a skills directory: `permissions.additionalDirectories` grants file access only [Doc skills: "Choose where skills load", "Load skills in monorepos and subdirectories", "Load skills from a directory outside the project"]. Claude Code does **not** read `.agents/skills`: no doc lists it, and in the 2.1.330 binary the string appears only in the `/import` code, which copies such skills into `.claude/skills` and skips one that is or sits under a link [binary strings check below] | A `<skill-name>` entry that is a link to a folder elsewhere is followed and loaded once [Doc skills, "Symlinked folders"]. A linked `.claude/skills` directory itself: **unknown** (not documented, not probed). A linked `.claude` or `.claude/worktrees` makes `--worktree` refuse [Doc worktrees, "Worktree creation fails on a symlinked path"] | The listing is built at start. Live change detection covers `~/.claude/skills/`, the project `.claude/skills/` and an `--add-dir` directory's `.claude/skills/` within the session. If a new skill does not appear, the user runs `/reload-skills` [Doc skills, "Edit a skill during a session"]. Whether a `.claude/skills` folder created mid-session is watched: **unknown** | Read natively since v2.1.277, by default only when no `CLAUDE.md` exists in the working directory or above. `@path` imports are expanded at session start [Doc memory, "AGENTS.md", "Import additional files"]. No skill location can be declared there. A CLAUDE.md that only tells Claude in words to read a file depends on Claude opening it [Doc memory, "Remove an earlier AGENTS.md workaround"] |
| **Codex** (codex-cli 0.171.0) | Repository: `.agents/skills` in every directory from cwd up to the repository root [Doc "Build skills"; probes 01, 02]. Also the **project `.codex/skills`** [probe 01; Source `host_roots.rs` `roots_from_layer_stack`, which takes the project config layer's folder plus `skills`]; the current page no longer names it. Not `.claude/skills`, not `skills/` [probe 01]. User: `$HOME/.agents/skills` and `$CODEX_HOME/skills` [probe 08; Source `dirs::home_dir`]. Admin `/etc/codex/skills`, plus system skills. No config key adds a root, and `skills.config` only toggles skills already found [Doc config reference; probe 07]. Runtime extra roots exist only through the app-server API `skills/extraRoots/set` [Source `app-server-protocol/src/protocol/common.rs`, `catalog_processor.rs`] | Yes: per-skill relative and absolute links [Doc "Build skills"; probe 01]. A whole `.agents/skills -> ../shiploop-skills` link is followed too, and the root is shown at its target path [probe 03] | The catalog (name, description, path) is part of the session's first input [prompt-input]. The doc says Codex detects changes automatically and to restart if not. Source: the app-server `SkillsWatcher` watches the roots computed from the thread's cwd and clears the cache, and the per-turn "world state" sends the whole `<skills_instructions>` block again when it changed. Incremental updates sit behind `skill_catalog_deltas`, default false [probe 09; Source `skills_watcher.rs`, `ext/skills/src/world_state.rs`]. Mid-session listing is **not measured** (it needs a model turn) | Instructions only: one chain built at start from the project root down to cwd [Doc AGENTS.md, "How Codex discovers guidance"]. An AGENTS.md naming `shiploop-skills/` arrived as text, and the folder did not become a root [probe 01, `01-main-root.agents-md-block.txt`] |
| **Grok Build** (1.0.92) | `./.grok/skills/`, walked up to the repository root. User `~/.grok/skills/`, `~/.agents/skills/`, plugin `skills/`, and extra paths under `[skills] paths` in `~/.grok/config.toml` (user config) [Doc x.ai "Skills, Plugins & Marketplaces"]. `.claude/skills`: likely. The doc says it is compatible with Claude Code with no setup, and the E2E harness turns Claude and Cursor skill folders off with `GROK_CLAUDE_SKILLS_ENABLED=false` and `GROK_CURSOR_SKILLS_ENABLED=false` [`hosts.py` `GrokHost.env`]. Project `.agents/skills`: **unknown** | **unknown** | **unknown** | Instruction files walked from cwd to the repository root; no skill declaration documented |
| **Cursor** (cursor-agent 2026.09.23) | `.agents/skills/` and `.cursor/skills/`, anywhere inside the repository; compatibility: `.claude/skills/` and `.codex/skills/` [Doc cursor.com "Agent Skills"] | **unknown** | Found when Cursor starts [same doc]; later changes **unknown** | Not documented for skills |
| **OpenCode** (1.19.4) | `.opencode/skills`; compatibility `.claude/skills` and `.agents/skills`, searched from the current directory up to the project root. A `skills` array in `opencode.json`/`.jsonc` adds local directories, so a committed project file **can** declare a skill location natively [Doc opencode.ai "Agent Skills"] | **unknown** (doc silent; `skills/skill-interop/references/host-paths.md` records that matching user-level links to one source selected one root in OpenCode 1.18.31) | Lists permitted skills at each model step [same doc]; rediscovery timing **unknown** | Not for skills; `opencode.json` `skills` is the native route |

### Worktrees (question 5)

- **Session in the main checkout, ShipLoop building in its sibling worktree (the default).** No host lists a skill
  from the worktree. Codex computes its roots from cwd: a skill created in the worktree does not appear from the
  main checkout, while one created in the main checkout does [probe 05]. For Claude Code the worktree lies outside
  the start directory and its parents, and it is not below the start directory. Cursor scans inside the
  repository, OpenCode and Grok from cwd up to the root. So a mid-run skill is only a file the model can open by
  path. After the workspace return (at release or handoff) the skill is in the user's checkout. Sessions started
  after that list it if it sits in a native folder, and a running Claude session can pick it up through live change
  detection.
- **Session started in the worktree.** Codex reads the worktree's own `.agents/skills` and `.codex/skills`,
  committed links included [probes 04, 06]. It does **not** fall back to the main checkout when the worktree has
  none [probe 11]. Claude Code searches up to the worktree root and, since v2.1.277, loads the main checkout's
  project skills when the worktree root has no `.claude/skills` [Doc worktrees, "What worktrees share with the main
  checkout"].
- **Claude-only side routes, not recommended.** First, the user types `/add-dir <WORKTREE>`. Claude Code then loads
  and live-watches `<WORKTREE>/.claude/skills` [Doc skills], and a same-named skill runs under a prefixed name. This
  is one user action per run, on Claude only. Second, the `EnterWorktree` tool with the worktree path. It asks the
  user's approval for paths outside `.claude/worktrees/`, then blocks edits and git in the main checkout, which the
  workspace return needs. Its doc does not say whether skills reload [Doc tools reference, "EnterWorktree tool
  behavior"; Doc worktrees, "How Claude Code enforces isolation"].

### Committed links (question 6)

- Git's `core.symlinks` defaults to true, except that `git clone` and `git init` probe the filesystem and set it
  false where links are unsupported. With it false, links are checked out as small plain files that hold the link
  text [local `man git-config`, git 2.54.0 (Apple Git-157)].
- Git for Windows turns link support off by default. It turns it on only when it detects Developer Mode on a recent
  Windows 10. Creating links needs SeCreateSymbolicLinkPrivilege (administrators by default) or Developer Mode
  [gitforwindows.org "Symbolic Links"]. Claude's memory doc says the same of a linked `CLAUDE.md`: a Windows clone
  gets a one-line text file, so it recommends an `@AGENTS.md` import instead [Doc memory].
- On such a clone a linked skill silently disappears: the host finds a file where a folder should be. ShipLoop
  itself supports linux and macos only (`skills/shiploop/SKILL.md` `platforms`), but other people's clones of a
  product repository may be on Windows.
- A different case to keep apart: skill-craft's own plugin packages must be real trees. A 2026-09-24 experiment
  found that Codex and Grok, installing a plugin from a local-folder marketplace, drop a linked skill folder
  [`docs/ARCHITECTURE.md`]. That is plugin installation, not project discovery, and probe 01 shows project links
  are followed.
- The usual alternatives: no links and a script that hands the path over; one real folder in the location most
  hosts read plus one link set; generated copies, which drift (skill-interop anti-pattern 2, "divergent copies");
  or a host setting that adds a path (OpenCode's `skills` array, Grok's user config).

## The options

| Option | Reaches the running inner loop (default worktree route) | Reaches later sessions natively | Costs and risks |
|---|---|---|---|
| **A.** Named ShipLoop folder, with per-skill links in `.claude/skills/<name>` and `.agents/skills/<name>` | **No**: the worktree is no skill root of the running session on any host | Claude Code (documented), Codex (measured), Cursor and OpenCode (they read both folders, so a skill may be listed twice: **unknown** how they dedupe), Grok likely | Windows clones lose the skills silently. `_skill_commit` would stage the link, not its target, if `path` went through a link (`folder = path.parent`, then `git add -A -- <link>`). The links must be created, committed (in `skill.index` or by the script) and returned, and kept in step on rename or delete. Never link `.claude` itself |
| **B.** Skills placed directly where several hosts read | **No**, for the same reason | No one folder covers both Claude Code (`.claude/skills` only) and Codex (`.agents/skills`, `.codex/skills`). `.agents/skills` covers Codex, Cursor and OpenCode and is the cross-client convention in the agentskills.io client guide. `.claude/skills` covers Claude Code, Cursor, OpenCode and probably Grok. The widest reach is a real folder in `.agents/skills` plus one Claude link set: A with one link set | Less clearly ShipLoop's: a frontmatter `metadata` marker plus the `## Skills` registry could carry that. The Windows caveat applies to the Claude links |
| **C.** AGENTS.md pointer only | **No**: no host loads skills from a path named there, and the running session read its AGENTS.md at start from the user's checkout | Only as an instruction the model may follow | This is roughly what ships today (an index link plus `## Skills` given as an outline). The same shape measured 0 of 3 in the platform-knowledge study: a page the project's file only named was not delivered (`docs/platform-knowledge-journal.md` section 50) |
| **D.** ShipLoop's script prints each product skill's name, description and absolute `SKILL.md` path, with the instruction for using it, into the stage that plans its use (`step-plan`) | **Yes**: no host discovery involved, every host, mid-run, in the worktree | No: only ShipLoop's own stages | The model reads the file (Claude: Read; Codex: cat), so host frontmatter features do not apply (`allowed-tools`, hooks, `${CLAUDE_SKILL_DIR}`, `$name` mentions). Product skills must be portable anyway. Where it is printed matters on Sol: at `step-plan` the lines new to a packet are mostly received, at `implement` poorly (journal section 47). A matching measurement: entries the script printed were delivered 6 of 6, a directive that pointed to them 3 of 3, a page only named 0 of 3 (sections 50 to 53; interim, one service). The downstream stages already print the step's chosen skills by value |

## Recommendation

**Build D, and keep one named folder. Add no links by default.**

1. **Named folder.** Use one fixed directory that ShipLoop knows, inside the product repository, registered in
   `environment.md` `## Skills`. It must not have a `FORBIDDEN_PARTS` part, so it cannot be `.shiploop/...`. The
   default I suggest is **`docs/shiploop/skills/<name>/SKILL.md`**. It sits inside ShipLoop's existing knowledge
   home in every product repository, beside the `## Skills` registry, cannot collide with a product's own `skills/`
   (skill-craft has one), and is returned normally. The alternative is `.agents/skills/<name>/`: Codex, Cursor and
   OpenCode list it natively, but it says less about who made it. The name is the owner's call.
2. **The script hands the skills over at `step-plan`.** Add a block that ShipLoop builds when it renders the
   packet. It scans the named folder plus the native project folders (`.claude/skills`, `.agents/skills`,
   `.codex/skills`, and the legacy `skills/`) in `state["repo"]` (the worktree, so it is live). It prints one line
   per skill: `name: description (absolute SKILL.md path)`, marking the ones this run created or updated (from the
   accepted carry-forward `skill` results). It follows the agentskills.io file-read instruction: when a step's task
   matches a skill's description, read that `SKILL.md` and list it in the step's `skills` with its path as
   `locator`. The existing `_skills_line` already carries the chosen skill to implement, test, document and review.
   A stronger form is offered as an option only (KISS): require a fit or no-fit row per listed skill in the
   step-plan result, which the script checks.
3. **Links only on the owner's word, and only for sessions outside ShipLoop.** If wanted, the script (not the
   model) creates relative per-skill links (`.claude/skills/<name> -> ../../docs/shiploop/skills/<name>` and
   `.agents/skills/<name>`) and commits them with the skill. Never link a whole `.claude` or `.claude/skills`, and
   note the Windows caveat.

**What would change in ShipLoop for D (files and symbols):**

- `skills/shiploop/scripts/shiploop_navigator.py`:
  - a new `_product_skill_lines(state, workitem)` (scan plus the same frontmatter rule as `_check_skill_decision`),
    added in `_stage_input_blocks` for `step-plan` beside the `concerns` block, and perhaps for `discovery` and
    `carry-forward`;
  - `_check_skill_decision`: make the named folder the default, or refuse other paths;
  - `_skill_commit`: only if links are adopted, stage the real folder and the links.
- `skills/shiploop/scripts/shiploop_knowledge_home.py`: a constant for the folder. Check that `_knowledge_close`,
  the section notices and lint leave it alone (not verified here).
- `skills/shiploop/scripts/shiploop_prompts.py`:
  - step-plan `skills` bullet: point at the printed block instead of "reread the host's skills and the repository's
    skill index";
  - carry-forward "Skill decision" items 3 ("Where") and 6 ("Register").
- References: `references/testing-and-documentation.md` (#reusable-product-skills), `references/carry-forward.md`
  ("Decide on a reusable skill"). Keep "do not assume every host automatically discovers every local skill folder"
  and add the worktree fact.
- Hermetic tests under `test/`, a `changes/shiploop/<slug>.md` note, and a ShipLoop E2E round with its
  `test/shiploop_e2e/LEARNINGS.md` entry before release (the repository's preflight rule).
- **Deciding test before building** (tests must be material):
  1. Census saved runs: how often carry-forward recorded `create` or `update`, and whether a later item's
     step-plan listed that skill. If skills are rarely created, D has little to deliver.
  2. If they are, run one small live rung: a two-item request whose procedure recurs, released against D, counting
     whether item 2's step-plan lists the skill item 1 made.

## Learnings and anything unexpected

1. **ShipLoop's worktree route decides the question.** Folder layout, links and AGENTS.md all act on sessions
   started in the checkout that holds the skill. A run's own inner loop never is one, on any host, until the
   workspace return.
2. **Codex still reads the project `.codex/skills`** (probe 01), through its project config layer, though its
   skills page names only `.agents/skills`.
3. **Codex shows a whole-directory link at its target.** With `.agents/skills -> ../shiploop-skills`, the root
   shown to the model is `.../shiploop-skills` (probe 03). Per-skill links are shown at the link path (probe 01).
4. **A recorded note did not reproduce.** The 2026-11-20 memory note (`~/.claude/projects/-Users-dadleet-src-skill-craft/memory/use-the-codex-harness.md`)
   says Codex 0.171.0 lists the real home's skills whatever `HOME` and `CODEX_HOME` say. Under `env -i` with a
   throwaway `HOME` and `CODEX_HOME`, no real-home root appeared in 10 renders. With the real `HOME` and a throwaway
   `CODEX_HOME`, `~/.agents/skills` appeared and `~/.codex/skills` did not (probe 08). The source resolves home
   through `dirs::home_dir()`, which honours `$HOME`. I did not re-run the earlier conditions (its binary, `PATH`,
   cwd). This bears on the E2E isolation conclusion behind keeping `hosts.py` unchanged, so it is worth a re-check
   before either claim is relied on.
5. **Codex has no worktree fallback** (probe 11); Claude Code v2.1.277+ has one.
6. **Claude Code reads AGENTS.md natively** (v2.1.277+), and this checkout has no `CLAUDE.md` at all; the brief
   said it is one line `@AGENTS.md`. This session's own context loaded `AGENTS.md` directly.
7. **Codex already has the mechanism ShipLoop would want, but only for app clients.** Its app-server takes runtime
   extra skill roots (`skills/extraRoots/set`). It is not reachable from `config.toml`, AGENTS.md or a model
   session.
8. **Today's step-plan gets only a pointer to its own registry.** `environment.md` `## Skills` is listed as an
   outline heading, not its text, which is the arm that measured 0 of 3 in the platform-knowledge study.
9. **A trap for option A.** `_skill_commit` commits `path`'s parent. Given a path through a link, it would commit
   the link and not the skill's files.
10. **Only OpenCode lets a committed project file name a skill folder natively** (`opencode.json` `skills`). Grok's
    `[skills] paths` is user config.

## Probe: Codex, no model call

`codex debug prompt-input` renders the model-visible input of a new session without calling a model. Every render
ran under `env -i` with a throwaway `HOME` and `CODEX_HOME` inside `probe/`; the one exception, render 08, used the
real `HOME`, read only. The files Codex created appeared in the throwaway `CODEX_HOME` (`installation_id`,
`shell_snapshots/`, `skills/.system/`, `tmp/`). A check for files changed after 18:05 found none in `~/.agents` or
`~/.codex/skills`. It needed no sign-in.

- Script: `probe/probe.sh`; extractor: `probe/extract.py`. Run `bash probe/probe.sh` to rebuild from scratch.
  `KEEP_SCAFFOLD=1` keeps the probe repositories and full renders, which are otherwise deleted to keep the
  evidence compact.
- Layout it builds:
  - repo `a`: real `.agents/skills/probe-agents-real`; the named folder `shiploop-skills/probe-linked-skill` and
    the relative link `.agents/skills/probe-linked-skill -> ../../shiploop-skills/probe-linked-skill`; an absolute
    link `.agents/skills/probe-abs-link -> <outside>/probe-abs-target`; `.codex/skills/probe-codex-dir`;
    `.claude/skills/probe-claude-dir`; `skills/probe-plain`; `sub/.agents/skills/probe-sub`; an `AGENTS.md` naming
    `shiploop-skills/`.
  - repo `b`: `.agents/skills -> ../shiploop-skills` holding `probe-dirlink`.
  - a linked worktree of `a` at `.shiploop-runs/a-probe/worktree`, placed as ShipLoop places its own.
  - repo `c`: only an untracked `.agents/skills` in the main checkout, and a worktree.
- Command per render (from `probe.sh`):

```sh
( cd "$cwd" && env -i PATH="/opt/homebrew/bin:/usr/bin:/bin" HOME="$ROOT/home" CODEX_HOME="$ROOT/codex-home" TERM=dumb \
    codex debug prompt-input "$@" "hello" ) > "$OUT/$label.json"
```

Output (`probe/out/summary.txt`, verbatim, codex-cli 0.171.0; "other skills listed: 4" are Codex's system skills):

```text
== 00-baseline-no-repo-skills (cwd outside) exit=0
   root r0 = codex-home/skills/.system
   other skills listed: 4
   AGENTS.md text in input: yes
== 01-main-root (cwd a) exit=0
   root r0 = work/a/.codex/skills
   root r1 = codex-home/skills/.system
   root r2 = work/a/.agents/skills
   listed probe-abs-link  (r2/probe-abs-link/SKILL.md)
   listed probe-agents-real  (r2/probe-agents-real/SKILL.md)
   listed probe-codex-dir  (r0/probe-codex-dir/SKILL.md)
   listed probe-linked-skill  (r2/probe-linked-skill/SKILL.md)
   other skills listed: 4
   AGENTS.md text in input: yes, names shiploop-skills/
== 02-main-sub (cwd a/sub) exit=0
   root r0 = work/a/.codex/skills
   root r1 = codex-home/skills/.system
   root r2 = work/a/.agents/skills
   root r3 = work/a/sub/.agents/skills
   listed probe-abs-link  (r2/probe-abs-link/SKILL.md)
   listed probe-agents-real  (r2/probe-agents-real/SKILL.md)
   listed probe-codex-dir  (r0/probe-codex-dir/SKILL.md)
   listed probe-linked-skill  (r2/probe-linked-skill/SKILL.md)
   listed probe-sub  (r3/probe-sub/SKILL.md)
   other skills listed: 4
   AGENTS.md text in input: yes, names shiploop-skills/
== 03-dirlink (cwd b) exit=0
   root r0 = codex-home/skills/.system
   root r1 = work/b/shiploop-skills
   listed probe-dirlink  (r1/probe-dirlink/SKILL.md)
   other skills listed: 4
   AGENTS.md text in input: no
== 04-wt-committed (cwd .shiploop-runs/a-probe/worktree) exit=0
   root r0 = work/.shiploop-runs/a-probe/worktree/.codex/skills
   root r1 = codex-home/skills/.system
   root r2 = work/.shiploop-runs/a-probe/worktree/.agents/skills
   listed probe-abs-link  (r2/probe-abs-link/SKILL.md)
   listed probe-agents-real  (r2/probe-agents-real/SKILL.md)
   listed probe-codex-dir  (r0/probe-codex-dir/SKILL.md)
   listed probe-linked-skill  (r2/probe-linked-skill/SKILL.md)
   other skills listed: 4
   AGENTS.md text in input: yes, names shiploop-skills/
== 05-main-after-wt-skill (cwd a) exit=0
   root r0 = work/a/.codex/skills
   root r1 = codex-home/skills/.system
   root r2 = work/a/.agents/skills
   listed probe-abs-link  (r2/probe-abs-link/SKILL.md)
   listed probe-agents-real  (r2/probe-agents-real/SKILL.md)
   listed probe-codex-dir  (r0/probe-codex-dir/SKILL.md)
   listed probe-linked-skill  (r2/probe-linked-skill/SKILL.md)
   listed probe-main-new  (r2/probe-main-new/SKILL.md)
   other skills listed: 4
   AGENTS.md text in input: yes, names shiploop-skills/
== 06-wt-after-wt-skill (cwd .shiploop-runs/a-probe/worktree) exit=0
   root r0 = work/.shiploop-runs/a-probe/worktree/.codex/skills
   root r1 = codex-home/skills/.system
   root r2 = work/.shiploop-runs/a-probe/worktree/.agents/skills
   listed probe-abs-link  (r2/probe-abs-link/SKILL.md)
   listed probe-agents-real  (r2/probe-agents-real/SKILL.md)
   listed probe-codex-dir  (r0/probe-codex-dir/SKILL.md)
   listed probe-linked-skill  (r2/probe-linked-skill/SKILL.md)
   listed probe-wt-new  (r2/probe-wt-new/SKILL.md)
   other skills listed: 4
   AGENTS.md text in input: yes, names shiploop-skills/
== 07-enable-by-path (cwd a) exit=0
   root r0 = work/a/.codex/skills
   root r1 = codex-home/skills/.system
   root r2 = work/a/.agents/skills
   listed probe-abs-link  (r2/probe-abs-link/SKILL.md)
   listed probe-agents-real  (r2/probe-agents-real/SKILL.md)
   listed probe-codex-dir  (r0/probe-codex-dir/SKILL.md)
   listed probe-linked-skill  (r2/probe-linked-skill/SKILL.md)
   listed probe-main-new  (r2/probe-main-new/SKILL.md)
   other skills listed: 4
   AGENTS.md text in input: yes, names shiploop-skills/
== 10-c-main-untracked (cwd c) exit=0
   root r0 = codex-home/skills/.system
   root r1 = work/c/.agents/skills
   listed probe-c-main-untracked  (r1/probe-c-main-untracked/SKILL.md)
   other skills listed: 4
   AGENTS.md text in input: no
== 11-c-wt-no-skills-dir (cwd .shiploop-runs/c-probe/worktree) exit=0
   root r0 = codex-home/skills/.system
   other skills listed: 4
   AGENTS.md text in input: no
== 08-real-home (cwd a, HOME=/Users/dadleet, CODEX_HOME throwaway) exit=0
   root r0 = work/a/.codex/skills
   root r1 = /Users/dadleet/.agents/skills
   root r2 = codex-home/skills/.system
   root r3 = work/a/.agents/skills
   listed probe-abs-link  (r3/probe-abs-link/SKILL.md)
   listed probe-agents-real  (r3/probe-agents-real/SKILL.md)
   listed probe-codex-dir  (r0/probe-codex-dir/SKILL.md)
   listed probe-linked-skill  (r3/probe-linked-skill/SKILL.md)
   listed probe-main-new  (r3/probe-main-new/SKILL.md)
   other skills listed: 6
   AGENTS.md text in input: yes, names shiploop-skills/
```

Not listed in any render: `probe-claude-dir` (`.claude/skills`), `probe-plain` (`skills/`), `probe-sub` from the
root, `probe-wt-new` from the main checkout, `probe-main-new` from the worktree, and `probe-c-main-untracked` from
its worktree. Render 07 gave `-c skills.config=[{path="<a>/skills/probe-plain/SKILL.md",enabled=true}]` and still
did not list `probe-plain`.

The rendered skill blocks are kept as `probe/out/*.skills-block.txt`, and the AGENTS.md block of render 01 as
`probe/out/01-main-root.agents-md-block.txt`. Default feature flags (`codex features list` in the throwaway
profile; `probe/out/09-features-default.txt`):

```text
catalog_apps_instructions                under development  false
command_sessions_world_state             under development  false
deferred_tool_world_state                stable             true
model_catalog_in_context                 under development  false
omit_skill_descriptions                  under development  false
skill_catalog_deltas                     under development  false
skill_env_var_dependency_prompt          removed            false
skill_mcp_dependency_install             stable             true
skill_search                             stable             true
skip_host_skill_discovery                under development  false
```

## Other checks run (no model, read only)

- **Claude Code binary strings.** Installed build: `/Users/dadleet/.local/share/claude/versions/2.1.330`. The
  `claude` on PATH is a zsh wrapper, `/Users/dadleet/.claude/tools/claude`. A Python scan for `.agents/skills`
  found 6 occurrences, all in the `/import` code. That code maps `~/.cursor/skills` and `~/.agents/skills` to
  `skillsOut: .claude/skills`, labels them "Not yet auto-imported", and reports a project `.agents/skills` that is,
  or sits under, a link as skipped for safety. There are 86 occurrences of `.claude/skills`. String presence is
  weak evidence; the docs are the primary source.
- **Codex source** at `rust-v0.171.0`, read with `gh api repos/openai/codex/contents/<path>?ref=rust-v0.171.0`:
  - `codex-rs/ext/skills/src/host_roots.rs`: `resolve_skill_roots` (with `extra_skill_roots`),
    `roots_from_layer_stack`, `repo_agents_skill_roots`, and the use of `dirs::home_dir`;
  - `codex-rs/app-server/src/skills_watcher.rs`: `SkillsWatcher`, `register_thread_config` (the roots come from
    `config.cwd`), and a cache clear plus a `SkillsChanged` notice on each event;
  - `codex-rs/ext/skills/src/world_state.rs`: `skills_world_state_section` sends the block again when its body
    changed;
  - `codex-rs/ext/skills/src/catalog_delta.rs`: added in #57262 on 2026-10-26, behind `skill_catalog_deltas`;
  - `codex-rs/app-server-protocol/src/protocol/common.rs`: `skills/extraRoots/set`.
- **Not run, by the brief's rules:** any Claude session (`claude -p`), any model session on any host, `grok
  inspect` (it can reach a leader process), and `opencode debug skill`.

## Sources (all read 2026-11-22)

- Claude Code: https://code.claude.com/docs/en/skills ; https://code.claude.com/docs/en/worktrees ;
  https://code.claude.com/docs/en/memory ; https://code.claude.com/docs/en/tools-reference
- Codex: https://developers.openai.com/codex/skills (308 to https://learn.chatgpt.com/docs/build-skills) ;
  https://developers.openai.com/codex/guides/agents-md (308 to https://learn.chatgpt.com/docs/agent-configuration/agents-md) ;
  https://developers.openai.com/codex/config-reference.md (308 to https://learn.chatgpt.com/docs/config-file/config-reference.md; first 100,000 characters read) ;
  https://github.com/openai/codex at tag rust-v0.171.0 (files above)
- Grok Build: https://docs.x.ai/build/features/skills-plugins-marketplaces
- Cursor: https://cursor.com/docs/context/skills
- OpenCode: https://opencode.ai/docs/skills/
- Agent Skills: https://agentskills.io/specification ; https://agentskills.io/client-implementation/adding-skills-support.md
- Git: local `man git-config` (git 2.54.0, Apple Git-157), `core.symlinks` ; https://gitforwindows.org/symbolic-links.html
- Secondary only (a search result, not opened): anthropics/claude-code issue 53950 reports `~/.agents/skills` not
  picked up on v2.1.119.
- Local:
  - `skills/shiploop/` (files and symbols named in the tables above);
  - `test/shiploop_e2e/hosts.py`, `test/shiploop_e2e/run.py`;
  - `docs/ARCHITECTURE.md`; `skills/skill-interop/references/host-paths.md`;
  - `docs/platform-knowledge-journal.md` sections 47 and 50 to 53.
